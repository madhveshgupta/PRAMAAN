"""F3 — compliance evidence.

Statuses are PASS / PARTIAL / INSUFFICIENT_EVIDENCE. **Never FAIL**, and the reasoning
matters: no evidence in a DPR is not proof a requirement was unmet. Perhaps the section
exists under a title we did not recognise; perhaps our parser missed a page. This module
reports what evidence it found and how strong it is. A human decides what that means.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models import DocumentPage, TextSpan
from worker.evidence.locate import Evidence

log = logging.getLogger("pramaan.completeness")

RUBRIC_PATH = Path(__file__).resolve().parents[2] / "config" / "rubric.yaml"

# Cues that a requirement is acknowledged but NOT satisfied. Keyword matching alone scores
# "clearance has not yet been obtained" as PASS, which is a defect in a government tool.
# Deliberately narrow. A bare "no" or "not" fires on sentences that mean the OPPOSITE of
# a problem — "No private land acquisition is involved" says the requirement is satisfied
# trivially, and downgrading it would be a false accusation. Each cue below has to
# indicate an obligation that is acknowledged but NOT yet discharged.
NEGATION_CUES = [
    r"\byet to be\b", r"\byet to\b",
    r"\b(?:is|are|has|have|was|were)\s+not\s+(?:been\s+)?(?:obtained|acquired|secured|"
    r"received|submitted|granted|approved|completed|available)\b",
    r"\bnot\s+(?:yet\s+)?(?:obtained|acquired|secured|received|granted|approved)\b",
    r"\b(?:is|are)\s+(?:still\s+)?pending\b", r"\bremains?\s+pending\b",
    r"\bawaited\b", r"\bawaiting\b",
    r"\bshall be (?:obtained|acquired|secured|submitted)\b",
    r"\bwill be (?:obtained|acquired|secured|submitted)\b",
    r"\bto be (?:obtained|acquired|secured|submitted)\b",
    r"\bunder process\b", r"\bin progress\b", r"\bunder consideration\b",
]
_NEG = re.compile("|".join(NEGATION_CUES), re.I)


# Front matter mentions a section without containing it. A contents line reading
# "4  Detailed Cost Abstract ..... 87" is a pointer, not the cost abstract; a glossary
# entry "O&M - Operation and Maintenance" is a definition, not an O&M plan. Anchoring a
# PASS to either is a false positive of the worst kind: it tells a reviewer a required
# section exists when it does not.
FRONT_MATTER = re.compile(
    r"table of contents|list of (tables|figures|annexure)|abbreviations?\b", re.I)


def _looks_like_prose(text: str) -> bool:
    """Does this read as written argument, or as a row of a table?

    A section is prose. A column heading that happens to contain the right words is not,
    and treating one as evidence of a chapter is how "O&M cost" in a cash-flow table gets
    mistaken for an Operations and Maintenance Plan.

    Heuristic: prose has a reasonable share of alphabetic words and few numeric tokens.
    """
    tokens = text.split()
    if len(tokens) < 12:
        return False
    alpha = sum(1 for t in tokens if t.isalpha() and len(t) > 2)
    numeric = sum(1 for t in tokens
                  if any(c.isdigit() for c in t) or t in {"-", "–", "|"})
    return alpha >= 8 and numeric <= len(tokens) * 0.35


def _is_front_matter(page) -> bool:
    text = page.full_text
    if FRONT_MATTER.search(text[:600]):
        return True
    # A contents page is mostly short lines ending in a page number.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) >= 6:
        numbered = sum(1 for ln in lines if re.search(r"\s\d{1,3}\s*$", ln))
        return numbered / len(lines) > 0.6
    return False


# A line that POINTS at a section is not the section. A table of contents is caught by
# _is_front_matter, but a summary table is not front matter — the salient-features table is
# legitimate content, and one of its rows reads "24  Quality control mechanism   Chapter 16".
# Anchoring a finding there tells the reviewer the right thing and sends them to the wrong
# page, which is worse than useless in a tool whose whole claim is that its evidence is
# clickable.
#
# The pointer must be TRAILING. "Chapter 16 — Quality Management Plan" is a heading whose
# subject is the chapter; "Quality control mechanism ... Chapter 16" is a reference to it.
# Position is what separates them, so a document that titles its chapters "Chapter 16 …" is
# not penalised. Bare trailing numbers are deliberately excluded: "… — Sheet 10" ends in a
# number and is ordinary content.
CROSS_REFERENCE = re.compile(
    r"(?:chapter|section|clause|para(?:graph)?|annexure|appendix|schedule|page)\s+"
    r"(?:no\.?\s*)?[ivxlc\d][ivxlc\d.\-]*\s*$", re.I)


def _is_cross_reference(line: str, match_start: int) -> bool:
    """Does `line` end in a pointer to another part of the document, after the match?"""
    m = CROSS_REFERENCE.search(line)
    return bool(m) and match_start < m.start()


# A cost-abstract row — "8  Quality control and supervision   1.40" — is a budget head, not
# a chapter. _looks_like_prose cannot catch it: the match sits at the foot of the table, so
# the window after it runs into the closing sentence ("The total project cost of the scheme
# is Rs. 192.70 crore") and reads as prose. The row itself is the reliable signal.
#
# Deliberately narrow, for the reason B46 records: a test that rejects real headings costs
# far more than this bug. A trailing DECIMAL amount is required, so "… — Sheet 10" and
# "3.6 ENGINEERING DESIGN" are untouched, and the line must be short enough to be a row
# rather than a sentence.
TABLE_ROW = re.compile(r"^\s*\d{1,3}(?:\.\d+)?[\s.)]+\S.*?\s\d{1,3}(?:,\d{2,3})*\.\d{1,2}\s*$")


def _is_table_row(line: str) -> bool:
    return bool(TABLE_ROW.match(line)) and len(line.split()) <= 10


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    lo = text.rfind("\n", 0, pos) + 1
    hi = text.find("\n", pos)
    return lo, (len(text) if hi == -1 else hi)


def _first_real_match(text: str, pats: list[re.Pattern]):
    """First heading match on the page that is not a trailing cross-reference."""
    hits = sorted((m for p in pats for m in p.finditer(text)), key=lambda m: m.start())
    for m in hits:
        lo, hi = _line_bounds(text, m.start())
        line = text[lo:hi]
        if not _is_cross_reference(line, m.start() - lo) and not _is_table_row(line):
            return m
    return None


@dataclass
class ItemResult:
    item_id: str
    section: str
    severity: str
    status: str                       # pass | partial | insufficient_evidence
    score: float
    evidence: Evidence | None
    note: str | None = None
    negation_cue: str | None = None


@lru_cache(maxsize=1)
def load_rubric() -> dict:
    return yaml.safe_load(RUBRIC_PATH.read_text())


# A document must look like a project report before it is scored as one. Running five real
# documents through the engine surfaced a tender/bid document that scored 78 — a number
# that means nothing, because none of the checks applied to it. Reporting "we do not think
# this is a DPR" is far more useful than a confident, meaningless score.
DPR_MARKERS = [
    r"detailed project report", r"\bDPR\b", r"project cost", r"means of finance",
    r"cost estimate", r"project proposal", r"feasibility report",
]
NOT_DPR_MARKERS = [
    r"request for proposal", r"\bRFP\b", r"invitation (?:to|for) bid", r"tender document",
    r"notice inviting tender", r"\bNIT\b", r"bidder shall", r"seal and sign of bidder",
    r"earnest money deposit", r"\bEMD\b", r"pre.bid (?:meeting|query)",
]


def classify_document(full_text: str) -> tuple[str, float, str | None]:
    """Return (profile_key, confidence, warning).

    Cue density decides the sector. A document that reads as a tender rather than a
    project report is reported as such rather than scored against a rubric none of whose
    items apply.
    """
    rubric = load_rubric()
    lowered = full_text.lower()

    dpr_hits = sum(1 for p in DPR_MARKERS if re.search(p, lowered, re.I))
    bid_hits = sum(1 for p in NOT_DPR_MARKERS if re.search(p, lowered, re.I))

    warning = None
    if bid_hits >= 3 and bid_hits > dpr_hits:
        warning = (f"This document reads as a tender or bid document, not a project "
                   f"report ({bid_hits} tender markers against {dpr_hits} DPR markers). "
                   f"Compliance scoring may not be meaningful for it.")

    # Absolute hits, not a ratio. A ratio punishes profiles with long cue lists: a water
    # supply DPR fires "water supply" and "MLD" unambiguously, but that is only 2/10 of
    # the infrastructure cues and a ratio threshold pushed it to `generic`. Two distinct
    # sector cues is real evidence; the ratio is kept only to break ties.
    best, best_hits, best_ratio = "generic", 0, 0.0
    for key, prof in rubric["profiles"].items():
        cues = prof.get("cues") or []
        if not cues:
            continue
        hits = sum(1 for c in cues if re.search(c, lowered, re.I))
        ratio = hits / len(cues)
        if (hits, ratio) > (best_hits, best_ratio):
            best, best_hits, best_ratio = key, hits, ratio

    if best_hits < 2:
        best = "generic"
        if warning is None:
            warning = ("The sector of this document could not be identified, so it was "
                       "scored against a minimal generic checklist. Sector-specific "
                       "requirements were not applied.")
    return best, round(best_ratio, 3), warning


def _heading_spans(db: Session, document_id) -> list[TextSpan]:
    """Headings are visually distinct, and the parser kept font_size precisely so this
    works: anything meaningfully larger than the body text is a candidate heading.

    Body size is the size covering the most CHARACTERS, not the median span size. The
    median counts a two-character table cell the same as a full line of prose, and a real
    DPR is mostly dense tables — across all six samples the median reported 7.6pt when the
    body prose was 9.5pt. Every prose span then cleared the threshold and qualified as a
    heading, which defeats the entire purpose of pass 1: any sentence merely *mentioning*
    a requirement outscored the chapter that actually answered it.
    """
    rows = db.execute(select(TextSpan.font_size, TextSpan.text)
                      .where(TextSpan.document_id == document_id)
                      .where(TextSpan.font_size.isnot(None))).all()
    if not rows:
        return []
    weight: dict[float, int] = {}
    for size, text in rows:
        weight[round(size, 1)] = weight.get(round(size, 1), 0) + len(text or "")
    body = max(weight, key=weight.__getitem__)
    return list(db.scalars(select(TextSpan).where(
        TextSpan.document_id == document_id,
        TextSpan.font_size > body * 1.15).order_by(TextSpan.page_no)))


def _anchor(db: Session, document_id, page_no: int, start: int, end: int,
            snippet: str, confidence: float) -> Evidence | None:
    spans = list(db.scalars(select(TextSpan).where(
        TextSpan.document_id == document_id, TextSpan.page_no == page_no,
        TextSpan.char_start < end, TextSpan.char_end > start)))
    if not spans:
        return None
    return Evidence(page=page_no,
                    bbox=[min(s.bbox[0] for s in spans), min(s.bbox[1] for s in spans),
                          max(s.bbox[2] for s in spans), max(s.bbox[3] for s in spans)],
                    snippet=snippet[:400], confidence=round(confidence, 4),
                    method="rule_match")


def _score_item(db: Session, document_id, item: dict, pages: list[DocumentPage],
                headings: list[TextSpan], strong: float) -> ItemResult:
    detect = item.get("detect", {})
    head_pats = [re.compile(p, re.I) for p in detect.get("headings", [])]
    must = [re.compile(p, re.I) for p in detect.get("must_contain", [])]

    front = {p.page_no for p in pages if _is_front_matter(p)}
    by_page = {p.page_no: p for p in pages}
    best_page, best_score, best_offsets, best_content = None, 0.0, (0, 0), 0

    # --- pass 1: a REAL heading, identified by font size, on a real content page.
    #
    # This is the only route to a clear PASS, and that is deliberate. An earlier version
    # allowed a heading-shaped phrase found anywhere in the running text to score 0.60,
    # which in a 172-page document is near-certain for almost any rubric item: real DPRs
    # came back scoring a flat 100.0 with zero findings, not because they were complete
    # but because the checks could not fail. A requirement is only demonstrably present
    # when the document has an actual heading for it AND the expected content beneath.
    for span in headings:
        if span.page_no in front:
            continue
        hit = next((p.search(span.text) for p in head_pats if p.search(span.text)), None)
        if (hit is None or _is_cross_reference(span.text, hit.start())
                or _is_table_row(span.text)):
            continue
        page = by_page.get(span.page_no)
        text = page.full_text if page else ""
        content_hits = sum(1 for p in must if p.search(text))
        score = 0.55 + 0.45 * (content_hits / max(1, len(must)))
        if score > best_score:
            best_score, best_content = score, content_hits
            best_page, best_offsets = span.page_no, (span.char_start, span.char_end)

    # --- pass 2: fallback for documents whose headings are not visually distinct.
    # Capped below the PASS threshold: without a real heading this is corroboration, not
    # proof, and it should surface to a reviewer as PARTIAL rather than silently pass.
    if best_score < strong:
        for page in pages:
            text = page.full_text
            if not text.strip():
                continue
            m = _first_real_match(text, head_pats)
            content_hits = sum(1 for p in must if p.search(text))
            if m is None or not content_hits:
                continue
            score = 0.40 + 0.25 * (content_hits / max(1, len(must)))
            if page.page_no in front:
                score = min(score, 0.30)      # a contents line points at a section
            if score > best_score:
                best_score, best_content = score, content_hits
                best_page = page.page_no
                best_offsets = (m.start(), m.end())

    if best_page is None:
        return ItemResult(item["id"], item["section"], item["severity"],
                          "insufficient_evidence", 0.0, None,
                          note="No evidence of this section was found anywhere in the "
                               "document. This is not proof the requirement is unmet.")

    page = next(p for p in pages if p.page_no == best_page)
    start, end = best_offsets
    # Text following the match — used both for the table-vs-prose test and the negation
    # guard below.
    body, _bs, _be = _widen(page.full_text, start,
                            min(len(page.full_text), end + 700), pad=40)
    # Widen for readability — a one-word snippet is useless to a reviewer — and anchor to
    # the SAME range. Previously the snippet was widened while the bbox stayed on the bare
    # match, so the evidence quoted a sentence while the highlight covered two words.
    snippet, w_start, w_end = _widen(page.full_text, start, end)
    ev = _anchor(db, document_id, best_page, w_start, w_end, snippet, best_score)

    # The negation guard must read the section's CONTENT, not just its title. Once pass 1
    # started anchoring to the heading span, the widened snippet covered the heading only
    # — and "Environmental Clearance ... is yet to be obtained" stopped being caught,
    # because the disqualifying phrase sits in the body beneath the title.

    # A match inside a table row is a column heading, not a chapter. Without this, "O&M
    # cost" in a cash-flow annexure reads as an Operations and Maintenance Plan — and that
    # is the single highest-value item in the rubric, so a false pass there is expensive.
    #
    # Tested against the text FOLLOWING the match, not the match itself: a real heading is
    # legitimately short ("3.6 ENGINEERING DESIGN" is four tokens), so testing the heading
    # rejected every genuine section. What separates a chapter from a column heading is
    # whether prose follows it.
    if not _looks_like_prose(body):
        return ItemResult(item["id"], item["section"], item["severity"],
                          "insufficient_evidence", round(best_score, 4), ev,
                          note=(f"The words appear on page {best_page}, but inside a table "
                                f"rather than in a section — the match is a column heading "
                                f"or list entry, not the chapter itself. No section "
                                f"answering this requirement was found."))

    # A heading with no corroborating content is a mention, not a section. A glossary that
    # defines "O&M" while the document contains no O&M plan would otherwise tell a reviewer
    # a critical section exists when it does not.
    if best_content == 0 and best_score <= 0.60:
        return ItemResult(item["id"], item["section"], item["severity"],
                          "insufficient_evidence", round(best_score, 4), None,
                          note=(f"The phrase appears on page {best_page}, but none of the "
                                f"content this section should contain was found alongside "
                                f"it. This looks like a passing mention rather than the "
                                f"section itself."))

    status = "pass" if best_score >= strong else "partial"
    cue = None

    # --- negation guard: can only downgrade, never upgrade.
    m = _NEG.search(body) or _NEG.search(snippet)
    if m:
        cue = m.group(0)
        if status == "pass":
            status = "partial"

    note = None
    if cue:
        note = (f"Evidence found, but it contains a negation or future-tense cue "
                f"(\"{cue}\"). This may indicate the requirement is acknowledged but not "
                f"yet satisfied. Reviewer judgement required.")

    return ItemResult(item["id"], item["section"], item["severity"], status,
                      round(best_score, 4), ev, note=note, negation_cue=cue)


def _widen(text: str, start: int, end: int, pad: int = 160) -> tuple[str, int, int]:
    """Grow a match out to readable context, bounded by line breaks.

    Bounded deliberately: on a contents page or a numbered index the neighbouring lines are
    unrelated entries, and running the snippet across them makes the evidence quote things
    the highlight does not cover.
    """
    lo, hi = max(0, start - pad // 3), min(len(text), end + pad)

    cut = text.rfind("\n", lo, start)
    if cut != -1:
        lo = cut + 1
    cut = text.find("\n", end, hi)
    if cut != -1:
        hi = cut

    # Trim whitespace symmetrically so the reported offsets still address the trimmed text.
    while lo < hi and text[lo].isspace():
        lo += 1
    while hi > lo and text[hi - 1].isspace():
        hi -= 1
    return text[lo:hi], lo, hi


@dataclass
class CompletenessReport:
    score: float
    items: list[ItemResult]
    profile: str
    profile_label: str
    profile_confidence: float
    provenance: str
    warning: str | None = None


def assess_completeness(db: Session, document_id, strong_threshold: float = 0.75
                        ) -> CompletenessReport:
    rubric = load_rubric()
    pages = list(db.scalars(select(DocumentPage)
                            .where(DocumentPage.document_id == document_id)
                            .order_by(DocumentPage.page_no)))
    headings = _heading_spans(db, document_id)

    # Sample rather than concatenate: a 172-page document does not need to be held in one
    # string to work out what sector it belongs to.
    sample = "\n".join(p.full_text for p in pages[:40])
    profile_key, confidence, warning = classify_document(sample)
    profile = rubric["profiles"][profile_key]

    weights = rubric["severity_weights"]
    values = rubric["status_values"]

    results = [_score_item(db, document_id, item, pages, headings, strong_threshold)
               for item in profile["items"]]

    earned = sum(weights[r.severity] * values[r.status] for r in results)
    possible = sum(weights[r.severity] for r in results)
    return CompletenessReport(
        score=round(earned / possible * 100, 1) if possible else 0.0,
        items=results, profile=profile_key, profile_label=profile["label"],
        profile_confidence=confidence, provenance=profile["provenance"],
        warning=warning)
