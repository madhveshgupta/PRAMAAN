"""The evidence locator — the single place where text becomes geometry.

M2's extraction verifier, M3's compliance evidence and M4's line-item anchoring all need
the same operation: take a piece of text, find where it lives in the parsed document, and
return a box a viewer can draw. Three implementations would mean three subtly different
coordinate behaviours, and those bugs surface as "the highlight is slightly off" — the
hardest class to attribute and the easiest to ship.

So it is written once, here. Never construct an evidence anchor by hand.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Literal

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models import DocumentPage, TextSpan
from worker.evidence.canonical import normalise_prose, repair_linebreak_numbers

log = logging.getLogger("pramaan.locate")

Mode = Literal["strict", "fuzzy"]
DEFAULT_FUZZY_THRESHOLD = 90
NEARBY_RADIUS = 2


@dataclass
class Evidence:
    """The anchor. Exactly the shape the frontend renders and the API returns."""
    page: int                       # 1-indexed
    bbox: list[float]               # normalised [x0,y0,x1,y1], top-left origin
    snippet: str
    confidence: float
    method: str
    source: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LocateFailure:
    reason: str
    best_score: float = 0.0
    best_page: int | None = None


@dataclass
class LocateResult:
    evidence: Evidence | None = None
    failure: LocateFailure | None = None
    candidates: list[Evidence] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.evidence is not None


def _union_bbox(spans: list[TextSpan]) -> list[float]:
    return [min(s.bbox[0] for s in spans), min(s.bbox[1] for s in spans),
            max(s.bbox[2] for s in spans), max(s.bbox[3] for s in spans)]


def _spans_overlapping(db: Session, document_id, page_no: int,
                       start: int, end: int) -> list[TextSpan]:
    return list(db.scalars(select(TextSpan).where(
        TextSpan.document_id == document_id,
        TextSpan.page_no == page_no,
        TextSpan.char_start < end,
        TextSpan.char_end > start).order_by(TextSpan.char_start)))


def _page_order(pages: list[DocumentPage], page_hint: int | None) -> list[DocumentPage]:
    """Search the hinted page and its neighbours first — a correct hint should not cost a
    full-document scan, and a wrong one should still be recoverable."""
    if page_hint is None:
        return pages
    near = [p for p in pages if abs(p.page_no - page_hint) <= NEARBY_RADIUS]
    rest = [p for p in pages if abs(p.page_no - page_hint) > NEARBY_RADIUS]
    near.sort(key=lambda p: abs(p.page_no - page_hint))
    return near + rest


def _exact_offsets(haystack: str, needle: str) -> list[int]:
    out, i = [], haystack.find(needle)
    while i != -1:
        out.append(i)
        i = haystack.find(needle, i + 1)
    return out


def locate(needle: str, document_id, db: Session, *,
           page_hint: int | None = None,
           mode: Mode = "fuzzy",
           threshold: int = DEFAULT_FUZZY_THRESHOLD,
           method: str = "llm_verified",
           allow_ambiguous: bool = False) -> LocateResult:
    """Find `needle` in the parsed document and return a drawable anchor.

    mode="strict" — exact match after canonicalisation. Use for numbers, dates, currency.
    mode="fuzzy"  — rapidfuzz partial_ratio >= threshold. Prose only.

    Returns a result whose ``evidence`` is None when nothing was found. **Callers must
    treat that as a rejection, never as a warning**: a value we cannot point at does not
    get stored (invariant #1).
    """
    needle = (needle or "").strip()
    if not needle:
        return LocateResult(failure=LocateFailure("empty_needle"))

    pages = list(db.scalars(select(DocumentPage)
                            .where(DocumentPage.document_id == document_id)
                            .order_by(DocumentPage.page_no)))
    if not pages:
        return LocateResult(failure=LocateFailure("document_not_parsed"))

    norm_needle = normalise_prose(needle)
    hits: list[Evidence] = []
    best_score, best_page = 0.0, None

    for page in _page_order(pages, page_hint):
        raw = repair_linebreak_numbers(page.full_text)
        if not raw.strip():
            continue

        offsets = _exact_offsets(raw, needle)
        score = 100.0

        if not offsets:
            # Case/whitespace-insensitive retry before giving up on an exact match.
            norm_hay = normalise_prose(raw)
            norm_offsets = _exact_offsets(norm_hay, norm_needle)
            if norm_offsets:
                # Re-find in the raw text so offsets address real spans.
                probe = needle.strip().split()
                if probe:
                    offsets = _exact_offsets(raw, probe[0])
                    offsets = [o for o in offsets
                               if normalise_prose(raw[o:o + len(needle) + 8])
                               .startswith(norm_needle[:max(8, len(norm_needle) // 2)])]
            if not offsets and mode == "fuzzy":
                score = fuzz.partial_ratio(norm_needle, normalise_prose(raw))
                if score > best_score:
                    best_score, best_page = score, page.page_no
                if score >= threshold:
                    anchor = _fuzzy_offsets(raw, needle)
                    offsets = [anchor] if anchor is not None else []

        for off in offsets:
            spans = _spans_overlapping(db, document_id, page.page_no,
                                       off, off + len(needle))
            if not spans:
                continue
            hits.append(Evidence(page=page.page_no, bbox=_union_bbox(spans),
                                 snippet=needle, confidence=round(score / 100.0, 4),
                                 method=method))
        if hits and page_hint is not None and page.page_no == page_hint:
            break        # the hint was right; stop looking

    if not hits:
        return LocateResult(failure=LocateFailure(
            "span_not_found", best_score=best_score, best_page=best_page))

    if len(hits) > 1 and not allow_ambiguous:
        # The same sentence on several pages — a running header, or a genuinely repeated
        # figure. Anchoring to an arbitrary one would put the highlight in a plausible but
        # wrong place, so the caller decides.
        distinct_pages = {h.page for h in hits}
        if len(distinct_pages) > 1:
            return LocateResult(failure=LocateFailure(
                "ambiguous_occurrence", best_score=100.0), candidates=hits)

    return LocateResult(evidence=hits[0], candidates=hits)


def _fuzzy_offsets(haystack: str, needle: str) -> int | None:
    """Approximate start offset of the best fuzzy window. Coarse on purpose — the bbox is
    a union over overlapping spans, so being a few characters out still highlights the
    right line."""
    window = len(needle)
    if window >= len(haystack):
        return 0
    best, best_at = 0.0, None
    step = max(1, window // 4)
    for start in range(0, len(haystack) - window + 1, step):
        score = fuzz.ratio(normalise_prose(needle),
                           normalise_prose(haystack[start:start + window]))
        if score > best:
            best, best_at = score, start
    return best_at


def locate_all(needle: str, document_id, db: Session, **kw) -> list[Evidence]:
    """Every occurrence, for findings that legitimately have several anchors —
    F4's cost contradiction carries three, F6's IRR finding carries two."""
    return locate(needle, document_id, db, allow_ambiguous=True, **kw).candidates
