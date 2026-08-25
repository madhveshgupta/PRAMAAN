"""The compliance checklist — every check the engine ran, pass or fail.

Findings record what needs acting on. These record what was *examined*, which is the
question a reviewer actually asks when deciding whether they still have to read four
hundred pages themselves. Before this existed the engine ran roughly two dozen checks and
persisted only the failures, so three warnings on screen were indistinguishable from three
warnings plus twenty things nobody looked at.

Two rules hold the design together:

* **A passing row carries its evidence**, exactly as a finding does. "Confirmed on page
  208" has to be clickable, or the checklist is just a longer assertion.
* **Where a check produced a finding, the check's detail IS the finding's message** — the
  same string, assigned in `persist`. Two views of one fact cannot drift if there is only
  one fact.

The outcome→row mapping lives here rather than in `worker/tasks/assess.py` so that module
stays orchestration, matching the rest of `scoring/`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from api.app.models import Assessment, AssessmentCheck, Finding
from worker.evidence.locate import Evidence
from worker.scoring import template_check
from worker.scoring.completeness import CompletenessReport
from worker.scoring.consistency import ConsistencyReport, format_agreement
from worker.scoring.financial import FinancialResult

log = logging.getLogger("pramaan.checklist")

# Display order. `data_quality` runs first for the reason assess.py already gives about the
# unfilled-template check: if the form is not filled in, every other row is about the shape
# of the document rather than its content.
FAMILY_ORDER: tuple[str, ...] = ("data_quality", "completeness", "consistency",
                                 "cost_realism", "financial")

# The single source of truth for why F5 does not run. `api/app/routes/assessments.py` reads
# it back off the persisted row rather than repeating the literal.
COST_REALISM_UNAVAILABLE = (
    "Requires published Schedule of Rates data, which has not been obtained. "
    "We do not benchmark against invented rates.")


@dataclass
class Check:
    """One checklist row, built from the same branch that decides the finding."""
    family: str
    check_id: str
    label: str
    severity: str
    status: str
    detail: str
    evidence: list[dict] = field(default_factory=list)
    evidence_score: float | None = None


def _anchors(items) -> list[dict]:
    return [e.to_dict() if isinstance(e, Evidence) else e for e in items if e]


# ─────────────────────────────────────────────────────────────── document quality
def document_quality_checks(tmpl: template_check.TemplateVerdict,
                            report: CompletenessReport) -> list[Check]:
    checks: list[Check] = []

    # judge_cells returns TemplateVerdict(False, total, 1.0, 1.0) when there are too few
    # cells to judge. Those 1.0s are sentinels, not measurements — rendering them would
    # print "100% of this document's 12 table cells contain something", a falsehood
    # produced by the feature whose whole job is to be trustworthy. Test the count first.
    if tmpl.total_cells < template_check.MIN_CELLS:
        detail = (f"This document has only {tmpl.total_cells:,} table cells — too few to "
                  f"judge whether a form has been filled in. No verdict was reached.")
        status = "insufficient_evidence"
    elif tmpl.is_template:
        detail, status = tmpl.message or "", "flagged"
    else:
        detail = (f"{tmpl.filled_ratio:.0%} of this document's {tmpl.total_cells:,} table "
                  f"cells contain something, and {tmpl.numeric_ratio:.0%} contain a "
                  f"number. This is a completed submission, not a blank form.")
        status = "pass"
    checks.append(Check("data_quality", "F3-UNFILLED-TEMPLATE",
                        "Document is a completed report, not a blank template",
                        "critical", status, detail))

    if report.warning:
        checks.append(Check("data_quality", "F3-PROFILE-UNCERTAIN",
                            "Document sector identified, so the right checklist applies",
                            "high", "flagged", report.warning))
    else:
        checks.append(Check(
            "data_quality", "F3-PROFILE-UNCERTAIN",
            "Document sector identified, so the right checklist applies", "high", "pass",
            f"Scored as a {report.profile_label} "
            f"({report.profile_confidence:.0%} cue match). "
            f"Checklist source: {report.provenance}"))
    return checks


# ─────────────────────────────────────────────────────────────── completeness (the rubric)
def completeness_checks(report: CompletenessReport) -> list[Check]:
    """One row per rubric item — including, and especially, the ones that passed."""
    out: list[Check] = []
    for r in report.items:
        if r.status == "pass":
            page = r.evidence.page if r.evidence else None
            detail = (f"Found on page {page} with the content this section should carry."
                      if page else "Found, with the content this section should carry.")
        else:
            detail = r.note or ""
        out.append(Check("completeness", f"F3-{r.item_id.upper()}", r.section,
                         r.severity, r.status, detail,
                         evidence=_anchors([r.evidence]), evidence_score=r.score))
    return out


# ─────────────────────────────────────────────────────────────── consistency
def consistency_checks(r: ConsistencyReport) -> list[Check]:
    label = "Total project cost agrees wherever the document states it"
    if r.mentions_found == 0:
        return [Check("consistency", "F4-COST-AGREEMENT", label, "high",
                      "insufficient_evidence",
                      "No statement of the total project cost was located, so no "
                      "cross-document comparison was possible. That is a limit of what we "
                      "found, not a finding about the project.")]
    if r.compared < 2:
        page = r.anchors[0].page if r.anchors else "?"
        return [Check("consistency", "F4-COST-AGREEMENT", label, "high", "partial",
                      f"The total project cost is stated once, on page {page}. A single "
                      f"statement cannot disagree with itself, so nothing was cross-checked.",
                      evidence=_anchors(r.anchors))]
    if r.contradictions:
        # detail is replaced by the finding's own message in persist().
        return [Check("consistency", "F4-COST-AGREEMENT", label, "high", "flagged", "",
                      evidence=_anchors(r.anchors))]
    return [Check("consistency", "F4-COST-AGREEMENT", label, "high", "pass",
                  format_agreement(r), evidence=_anchors(r.anchors))]


# ─────────────────────────────────────────────────────────────── cost realism (blocked)
def cost_realism_checks() -> list[Check]:
    """The most important row in the checklist for trust: the system stating plainly what
    it does NOT check, and why."""
    return [Check("cost_realism", "F5-COST-REALISM",
                  "Unit rates benchmarked against a published Schedule of Rates",
                  "high", "not_run", COST_REALISM_UNAVAILABLE)]


# ─────────────────────────────────────────────────────────────── financial
def financial_checks(fin: FinancialResult, claimed_pct: float | None,
                     claim_anchor: dict | None, table_anchor: Evidence | None,
                     tolerance_pp: float) -> list[Check]:
    """Three checks, one per rule_id assess.py can raise. A finding whose check row is
    missing would be a finding the checklist silently hides."""
    tbl = _anchors([table_anchor])

    # --- A. was the cash-flow table found and readable? Family is data_quality because
    # that is the categorisation the existing F6-CASHFLOW-UNREADABLE finding already makes:
    # it is a limit of our reading, not a claim about the project's finances.
    if fin.cashflow is None:
        table = Check("data_quality", "F6-CASHFLOW-TABLE",
                      "Year-wise cash-flow statement located and readable", "info",
                      "insufficient_evidence",
                      "No year-indexed cash-flow table was found. Many DPRs legitimately "
                      "carry no year-wise cash flow, so this is not itself a finding; "
                      "whether the annexure is required is a completeness question.")
    elif fin.problems:
        table = Check("data_quality", "F6-CASHFLOW-TABLE",
                      "Year-wise cash-flow statement located and readable", "info",
                      "flagged", "", evidence=tbl)
    else:
        cf = fin.cashflow
        table = Check("data_quality", "F6-CASHFLOW-TABLE",
                      "Year-wise cash-flow statement located and readable", "info", "pass",
                      f"A year-indexed cash-flow table was found on page {cf.page_no}, "
                      f"covering {len(cf.years)} periods (years {min(cf.years)}–"
                      f"{max(cf.years)}). It passed every data-quality check: a complete "
                      f"and ascending year series, at least one sign change, and plausible "
                      f"magnitudes.", evidence=tbl)

    # --- B. does the claimed IRR survive recomputation from those cash flows?
    label_b = "Claimed IRR reconciled against the document's own cash flows"
    if fin.cashflow is None:
        irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical",
                    "insufficient_evidence",
                    "Not attempted: no cash-flow table was found. Recomputing an IRR from "
                    "a table we could not read would produce a confident wrong number.")
    elif fin.problems:
        irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical",
                    "insufficient_evidence",
                    "Not attempted: the cash-flow table did not pass its data-quality "
                    "checks, so any recomputed rate would be meaningless.", evidence=tbl)
    elif fin.computed_irr is None:
        # Silent before the checklist existed: assess.py guards on `computed_irr is not
        # None` and simply falls through, logging nothing.
        irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical",
                    "insufficient_evidence",
                    "The cash-flow series passed its data-quality checks, but no internal "
                    "rate of return could be solved for it.", evidence=tbl)
    elif claimed_pct is None:
        irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical", "partial",
                    f"The document's own cash flows recompute to an IRR of "
                    f"{fin.computed_irr}%. The document states no IRR of its own, so there "
                    f"was nothing to reconcile it against; the recomputed figure is shown "
                    f"for reference.", evidence=tbl)
    else:
        gap = abs(claimed_pct - fin.computed_irr)
        both = _anchors([claim_anchor]) + tbl
        if gap > tolerance_pp:
            irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical", "flagged",
                        "", evidence=both)
        else:
            claim_page = (claim_anchor or {}).get("page", "?")
            tbl_page = fin.cashflow.page_no
            irr = Check("financial", "F6-IRR-RECOMPUTED", label_b, "critical", "pass",
                        f"The report claims an IRR of {claimed_pct}% (page {claim_page}). "
                        f"Recomputed from the cash-flow statement on page {tbl_page} of "
                        f"this same document: {fin.computed_irr}%. Difference "
                        f"{gap:.2f} percentage points, within the {tolerance_pp} pp "
                        f"tolerance.", evidence=both)

    # --- C. is that IRR the only one the series admits?
    label_c = "The cash-flow series has a single, unambiguous IRR"
    if fin.computed_irr is None:
        unique = Check("financial", "F6-IRR-AMBIGUOUS", label_c, "medium",
                       "insufficient_evidence",
                       "Not reached — the IRR was not computed.", evidence=tbl)
    elif fin.irr_ambiguous:
        unique = Check("financial", "F6-IRR-AMBIGUOUS", label_c, "medium", "flagged", "",
                       evidence=tbl)
    else:
        # _all_roots can return [] on LinAlgError while irr_ambiguous stays False.
        rate = fin.irr_roots[0] if fin.irr_roots else fin.computed_irr
        unique = Check("financial", "F6-IRR-AMBIGUOUS", label_c, "medium", "pass",
                       f"The series changes sign once, so exactly one internal rate of "
                       f"return satisfies it ({rate}%). A series with several roots would "
                       f"make any single reported IRR misleading.", evidence=tbl)

    return [table, irr, unique]


# Findings that legitimately have nothing to point at: "this is not a DPR" is about the
# whole file, not a region of it. Lifted out of assess.py so persist() can apply the same
# rule while recording what it withheld.
DOCUMENT_LEVEL = {"F3-PROFILE-UNCERTAIN", "F3-UNFILLED-TEMPLATE"}


def _is_anchored(f: Finding) -> bool:
    return (bool(f.evidence) or f.status == "insufficient_evidence"
            or f.rule_id in DOCUMENT_LEVEL)


def persist(db: Session, assessment: Assessment, checks: list[Check],
            findings: list[tuple[Finding, str]]) -> list[Finding]:
    """Write the checklist, then the findings it produced, linked to their rows.

    `findings` is (finding, check_id). An unknown check_id raises rather than being
    dropped: a finding with no checklist row is one the checklist would silently hide,
    which is precisely the failure this feature exists to prevent. Better to fail the job
    loudly than to ship a checklist that lies by omission.
    """
    order = {f: i for i, f in enumerate(FAMILY_ORDER)}
    checks = sorted(checks, key=lambda c: order.get(c.family, len(order)))

    rows: dict[str, AssessmentCheck] = {}
    for i, c in enumerate(checks):
        rows[c.check_id] = AssessmentCheck(
            assessment_id=assessment.id, dpr_id=assessment.dpr_id, family=c.family,
            check_id=c.check_id, label=c.label, severity=c.severity, status=c.status,
            evidence_score=c.evidence_score, evidence=c.evidence, detail=c.detail,
            ordinal=i)
    db.add_all(rows.values())
    db.flush()                      # rows must exist before findings can reference them

    kept: list[Finding] = []
    # A check can produce more than one finding — find_contradictions returns one per
    # non-comparable cluster — so messages accumulate. Assigning would let the last
    # contradiction silently erase the others.
    messages: dict[str, list[str]] = {}
    for finding, check_id in findings:
        row = rows.get(check_id)
        if row is None:
            raise ValueError(f"finding {finding.rule_id} has no checklist row "
                             f"({check_id}) — the checklist would hide it")
        finding.assessment_check_id = row.id
        # One fact, one string. A non-pass row says exactly what its findings say, so the
        # two views cannot drift as either is edited.
        messages.setdefault(check_id, []).append(finding.message)
        row.detail = " ".join(messages[check_id])
        if not _is_anchored(finding):
            # Previously a bare log.error and the reviewer never learned the finding
            # existed. Surfacing the withholding on the row keeps the checklist a complete
            # index of what happened, including our own failures.
            log.error("withholding unanchored finding %s", finding.rule_id)
            row.detail += (" A finding was raised for this item but could not be anchored "
                           "to a page, and was withheld rather than shown without a source.")
            continue
        kept.append(finding)

    db.add_all(kept)
    return kept
