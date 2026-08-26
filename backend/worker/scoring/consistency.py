"""F4 — cross-document contradiction detection.

There is no machine learning here, and that is the point. A 300-page DPR is written by
several people over several months; the executive summary is drafted early, the cost
abstract revised, the annexure recalculated, and nobody reconciles them. A reader working
linearly cannot notice that page 4 and page 87 disagree. A computer holding the whole
document at once notices immediately.

The hard part is not detecting divergence. It is knowing that two numbers refer to the
**same thing**. "Cost excluding tax" versus "cost including GST" is a legitimate
difference, and flagging it would destroy a reviewer's trust faster than any other failure
in this product. So the rule is deliberately biased toward silence: when the qualifiers do
not match exactly, we say nothing.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models import ExtractedField
from worker.evidence.canonical import to_paise
from worker.evidence.locate import Evidence

log = logging.getLogger("pramaan.consistency")

# Context qualifiers that change what a number MEANS. Two mentions are only comparable
# when these match exactly.
# Each entry maps a signature TOKEN to its pattern. The token carries direction, not just
# category: "including tax" and "excluding tax" must produce DIFFERENT signatures, or the
# two figures get compared and a perfectly legitimate difference is reported as a
# contradiction — the single most damaging false positive this module could emit.
QUALIFIERS: dict[str, str] = {
    "tax:incl":      r"\bincl(?:uding|\.|usive)?\s*(?:of\s*)?(?:all\s+)?(?:tax|gst|duty|duties)",
    "tax:excl":      r"\bexcl(?:uding|\.|usive)?\s*(?:of\s*)?(?:tax|gst|duty|duties)",
    "esc:base":      r"\bbase\s+(?:cost|price)|\bat\s+current\s+price",
    "esc:applied":   r"\bescalat",
    "scope:phase":   r"\bphase[-\s]?(?:i{1,3}\b|[0-9])|\bstage[-\s]?(?:i{1,3}\b|[0-9])",
    "scope:conting": r"\bcontingenc",
    "head:civil":    r"\bcivil\s+works\b",
    "head:elec":     r"\belectrical\b",
    "head:land":     r"\bland\s+cost\b",
    "head:om":       r"\bo\s*&\s*m\s+cost\b",
    "head:super":    r"\bsupervision\b",
    "share:centre":  r"\bcentral\s+(?:assistance|share)",
    "share:state":   r"\bstate\s+share\b",
}
_COMPILED = {token: re.compile(pat, re.I) for token, pat in QUALIFIERS.items()}

# Only cluster mentions that are talking about the project's headline cost.
TOTAL_COST_CUE = re.compile(
    r"total\s+project\s+cost|total\s+cost\s+of\s+(?:the\s+)?project|"
    r"project\s+cost\s+is|total\s+project\s+cost:", re.I)

CONTEXT_WINDOW = 120


@dataclass
class Contradiction:
    field_label: str
    unit: str
    values: list[tuple[int, Evidence]]      # (canonical value, anchor)
    spread_pct: float


# Two kinds of dimension, and conflating them is what makes this rule hard.
#
# DIRECTIONAL — "including tax" vs "excluding tax". Absence is NEUTRAL: a figure that
#   simply does not say is not thereby a different figure. Only opposing directions block
#   a comparison.
# SCOPING — "Phase-I", "civil works", "state share". Presence ALONE changes what the
#   number refers to, so an unqualified total and a Phase-I subtotal are never comparable.
DIRECTIONAL = {"tax", "esc"}
SCOPING = {"scope", "head", "share"}


def qualifier_signature(context: str) -> frozenset[str]:
    """Which meaning-changing qualifiers appear near this number."""
    return frozenset(token for token, pat in _COMPILED.items() if pat.search(context))


def _dim(token: str) -> str:
    return token.split(":", 1)[0]


def comparable(a: frozenset[str], b: frozenset[str]) -> bool:
    """Do these two mentions refer to the same thing?

    Biased toward silence. A missed contradiction costs one finding; a false one costs the
    reviewer's trust in every other finding on the page.
    """
    for dim in DIRECTIONAL:
        ta = {t for t in a if _dim(t) == dim}
        tb = {t for t in b if _dim(t) == dim}
        if ta and tb and ta != tb:
            return False                      # opposing directions — different bases
    for dim in SCOPING:
        ta = {t for t in a if _dim(t) == dim}
        tb = {t for t in b if _dim(t) == dim}
        if ta != tb:
            return False                      # different scope, or one is a subtotal
    return True


def _cluster_key(field: ExtractedField) -> tuple[str, str, frozenset[str]] | None:
    """Group by (what it is, its unit, its qualifiers). Different signature means
    different entity, which means no comparison and no finding."""
    if field.field_key != "money_mention" or not field.evidence:
        return None
    snippet = field.evidence[0].get("snippet", "")
    if not TOTAL_COST_CUE.search(snippet):
        return None                     # not a headline-cost mention; out of scope
    return ("total_project_cost", "INR", qualifier_signature(snippet[:CONTEXT_WINDOW * 2]))


# How many anchors a passing row carries. A rendering cap, not a judgement threshold —
# hence a constant here rather than a row in `settings`.
MAX_AGREEMENT_ANCHORS = 6


@dataclass
class ConsistencyReport:
    """What F4 actually knows — not only what went wrong.

    The census below was computed and then thrown away, which left the checklist unable to
    state the true and useful thing: how many statements of the headline cost were found,
    how many were comparable with each other, and how closely they agreed.
    """
    contradictions: list[Contradiction]
    mentions_found: int                 # headline-cost mentions located at all
    compared: int                       # mentions inside the largest comparable group
    groups: int                         # maximal mutually-comparable sets
    max_spread_pct: float | None        # widest divergence seen, contradiction or not
    tolerance_pct: float
    anchors: list[Evidence]             # the compared mentions, page-ordered


def check_consistency(db: Session, dpr_id, tolerance_pct: float = 0.5
                      ) -> ConsistencyReport:
    fields = db.scalars(select(ExtractedField)
                        .where(ExtractedField.dpr_id == dpr_id)).all()

    mentions: list[tuple[frozenset[str], int, Evidence]] = []
    for f in fields:
        key = _cluster_key(f)
        if key is None:
            continue
        raw = f"{f.value_text} {'crore' if f.unit == 'INR_CRORE' else 'lakh' if f.unit == 'INR_LAKH' else ''}"
        paise = to_paise(raw)
        if paise is None:
            continue
        anchor = Evidence(**{k: v for k, v in f.evidence[0].items()
                             if k in {"page", "bbox", "snippet", "confidence",
                                      "method", "source"}})
        mentions.append((key[2], paise, anchor))

    # Group into maximal sets of mutually-comparable mentions rather than by exact
    # signature match, so an unqualified figure still meets a qualified one.
    groups: list[list[tuple[int, Evidence]]] = []
    group_sigs: list[frozenset[str]] = []
    for sig, paise, anchor in sorted(mentions, key=lambda m: m[2].page):
        for i, gsig in enumerate(group_sigs):
            if comparable(sig, gsig):
                groups[i].append((paise, anchor))
                group_sigs[i] = gsig | sig
                break
        else:
            groups.append([(paise, anchor)])
            group_sigs.append(sig)

    clusters = {("total_project_cost", "INR", group_sigs[i]): g
                for i, g in enumerate(groups)}

    out: list[Contradiction] = []
    spreads: list[float] = []
    for (label, unit, _sig), items in clusters.items():
        distinct = {v for v, _ in items}
        if len(distinct) < 2:
            continue
        lo, hi = min(distinct), max(distinct)
        spread = (hi - lo) / hi * 100
        spreads.append(spread)
        if spread <= tolerance_pct:
            continue                    # rounding, not disagreement
        items.sort(key=lambda t: t[1].page)
        out.append(Contradiction(label, unit, items, round(spread, 3)))

    # The anchors a passing row shows are the mentions that were actually compared: the
    # largest comparable group, page-ordered. A row claiming "three figures agree" that
    # cannot show the three is the kind of unfalsifiable claim invariant #1 forbids.
    largest = max(groups, key=len) if groups else []
    return ConsistencyReport(
        contradictions=out,
        mentions_found=len(mentions),
        compared=len(largest),
        groups=len(groups),
        max_spread_pct=round(max(spreads), 3) if spreads else None,
        tolerance_pct=tolerance_pct,
        anchors=[e for _v, e in sorted(largest, key=lambda t: t[1].page)
                 ][:MAX_AGREEMENT_ANCHORS])


def find_contradictions(db: Session, dpr_id, tolerance_pct: float = 0.5
                        ) -> list[Contradiction]:
    """Failures only. Kept because most callers want exactly this."""
    return check_consistency(db, dpr_id, tolerance_pct).contradictions


def format_message(c: Contradiction) -> str:
    """Written so a reviewer can act on it without opening the document — though they
    can, and the whole point is that they can."""
    parts = [f"₹{v / 10_000_000_00:.2f} Cr (p.{e.page})" for v, e in c.values]
    counts: dict[int, int] = defaultdict(int)
    for v, _ in c.values:
        counts[v] += 1
    majority = max(counts.values())
    tail = ""
    if majority > 1 and len(counts) > 1:
        odd = [f"p.{e.page}" for v, e in c.values if counts[v] < majority]
        tail = (f" {majority} of {len(c.values)} agree; "
                f"{', '.join(odd)} appears to be stale.")
    return ("Total project cost stated as " + ", ".join(parts) + "."
            + tail + f" Divergence {c.spread_pct:.2f}%.")


def format_agreement(r: ConsistencyReport) -> str:
    """The sentence a passing consistency row shows.

    The second half is not decoration. `_cluster_key` admits only mentions matching
    TOTAL_COST_CUE, and `comparable()` is deliberately biased toward silence — a Phase-I
    subtotal or a state-share figure is never compared against the headline total. Without
    saying so, this row reads as "every cost figure in this document agrees", which the
    module never checked. That would be the most damaging over-claim the checklist could
    make, and it would be made by the feature whose entire purpose is to earn trust.
    """
    pages = ", ".join(f"p.{e.page}" for e in r.anchors)
    spread = r.max_spread_pct if r.max_spread_pct is not None else 0.0
    out = (f"{r.compared} statements of the total project cost were located ({pages}) and "
           f"compared against one another. They agree to within {spread:.2f}% — under the "
           f"{r.tolerance_pct:.2f}% tolerance below which a difference is rounding rather "
           f"than disagreement.")
    remainder = r.mentions_found - r.compared
    if remainder > 0:
        out += (f" {remainder} further cost mention{'s' if remainder > 1 else ''} "
                f"carr{'y' if remainder > 1 else 'ies'} qualifiers that change what the "
                f"number means (a phase, head or share subtotal), so {'they were' if remainder > 1 else 'it was'} "
                f"deliberately not compared against the headline figure.")
    return out
