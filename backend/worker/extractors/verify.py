"""The verification guard — the most important function in the codebase.

An LLM asked for a project's budget will always return one, including when the document
has none. In a tool that informs how public money is spent, a fabricated figure is a
disqualifying defect. So the model is never allowed to return a bare value: it must quote,
and the quote is checked.

Checking the quote exists is **not sufficient**, and this is the part that is easy to get
wrong. The model can quote a genuinely-present sentence and attach an invented number to
it — the span verifies, and a span-only checker accepts the fabrication. So the claimed
value must also appear *inside* the verified span. That is invariant #11.

A rejection here is the system working, not failing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from worker.evidence.canonical import money_values_in, numbers_in, to_paise
from worker.evidence.locate import Evidence, locate

log = logging.getLogger("pramaan.verify")

# Field kinds whose value must match exactly. Fuzzy-matching a number is unsafe.
NUMERIC_KINDS = {"money", "number", "percent", "date", "duration"}


@dataclass
class Candidate:
    field_key: str
    value: str
    unit: str | None
    verbatim_span: str
    page_hint: int | None = None
    kind: str = "prose"          # money | number | percent | date | duration | prose


@dataclass
class Verdict:
    accepted: bool
    evidence: Evidence | None = None
    reason: str | None = None
    best_score: float = 0.0

    @property
    def rejected(self) -> bool:
        return not self.accepted


# A structured extractor reports magnitude in a separate `unit` field, so the bare value
# string ("412.50") carries no scale. Re-attach it before canonicalising, or a crore is
# read as rupees and every honest money value is wrongly rejected.
UNIT_WORD = {"INR_CRORE": "crore", "INR_LAKH": "lakh", "INR": "", "RS": ""}


def value_in_span(claimed: str, span_text: str, kind: str, unit: str | None = None) -> bool:
    """Invariant #11: is the claimed value actually present in the quoted text?

    Money is compared in canonical paise so that 'Rs. 412.50 crore' in the value and
    '₹412.5 Cr' in the span are recognised as the same figure — while 500 against a span
    containing only 412.50 is not.
    """
    if kind == "money":
        scale = UNIT_WORD.get((unit or "").upper().strip(), "")
        # Only append the unit when the value string does not already carry one.
        if scale and to_paise(claimed) == to_paise(claimed.rstrip() + " x"):
            claimed = f"{claimed} {scale}"
        claimed_paise = to_paise(claimed)
        if claimed_paise is None:
            return False
        return claimed_paise in money_values_in(span_text)

    if kind in NUMERIC_KINDS:
        claimed_nums = numbers_in(claimed)
        if not claimed_nums:
            return False
        return claimed_nums <= numbers_in(span_text)

    return True          # prose fields carry no separable value to cross-check


def verify(candidate: Candidate, document_id, db: Session, *,
           fuzzy_threshold: int = 90, method: str = "llm_verified") -> Verdict:
    """Run the full guard. Returns a Verdict; a rejection carries its reason for the log."""
    if not candidate.verbatim_span or not candidate.verbatim_span.strip():
        return Verdict(False, reason="no_span_quoted")

    # Numbers and dates must match exactly; only prose is fuzzy-matched.
    mode = "strict" if candidate.kind in NUMERIC_KINDS else "fuzzy"

    result = locate(candidate.verbatim_span, document_id, db,
                    page_hint=candidate.page_hint, mode=mode,
                    threshold=fuzzy_threshold, method=method)

    if not result:
        f = result.failure
        return Verdict(False, reason=f.reason, best_score=f.best_score)

    ev = result.evidence

    # ---- invariant #11 -----------------------------------------------------
    if not value_in_span(candidate.value, candidate.verbatim_span,
                         candidate.kind, candidate.unit):
        log.info("blocked fabricated value: %s claimed %r, quote does not contain it",
                 candidate.field_key, candidate.value)
        return Verdict(False, reason="value_not_in_span")

    ev.snippet = candidate.verbatim_span
    return Verdict(True, evidence=ev)


def record_rejection(db: Session, dpr_id, candidate: Candidate, verdict: Verdict) -> None:
    """Log the block. This table is a reliability feature surfaced in Ministry settings,
    not an error log: 'the AI tried to state a figure it could not evidence, and was
    blocked, 47 times this month.' The figure is illustrative — nothing in the codebase
    aggregates this table yet, and it has had no rows to aggregate."""
    from api.app.models import ExtractionRejection
    db.add(ExtractionRejection(
        dpr_id=dpr_id, field_key=candidate.field_key,
        claimed_value=candidate.value, claimed_span=candidate.verbatim_span,
        reason=verdict.reason or "unknown", best_fuzzy_score=verdict.best_score))
