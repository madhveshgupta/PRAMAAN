"""Text extraction with geometry — the substrate everything else stands on.

Most PDF pipelines call ``page.get_text()``, take the string, and discard the geometry.
We must not: without per-span coordinates the click-to-highlight feature cannot exist, and
that feature is the product.

Two contracts this module must satisfy exactly:

1. ``full_text[char_start:char_end] == span.text`` for every span, guaranteed by
   construction rather than checked afterwards.
2. ``bbox`` is normalised to [0,1] against page width/height, top-left origin, and already
   de-rotated — so the viewer can multiply by whatever size it rendered at and be correct
   at every zoom level.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf

# A page yielding less than this many non-whitespace characters is treated as an image
# and routed to OCR.
OCR_CHAR_THRESHOLD = 50

# PostgreSQL text columns cannot hold a NUL byte, and PDFs do contain them — usually from
# a font mapping that produced no glyph. One stray NUL anywhere in a 200-page document
# aborted the whole insert and failed the ingestion.
#
# Stripped rather than replaced: a NUL is not a character the document meant to contain,
# so removing it keeps `full_text` faithful to what a reader sees. Other C0 control codes
# go the same way, except tab/newline/carriage-return which are real layout.
_CONTROL = {c: None for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)}
_CONTROL[0x7F] = None


def sanitise(text: str) -> str:
    """Remove characters Postgres cannot store. Length changes here are fine — offsets are
    computed AFTER sanitising, from the cleaned string."""
    return text.translate(_CONTROL) if text else text


@dataclass
class ParsedSpan:
    page_no: int
    bbox: list[float]
    text: str
    char_start: int
    char_end: int
    font_size: float | None = None
    is_bold: bool = False


@dataclass
class ParsedPage:
    page_no: int
    width_pt: float
    height_pt: float
    rotation: int
    full_text: str = ""
    spans: list[ParsedSpan] = field(default_factory=list)
    needs_ocr: bool = False


def _normalise_bbox(bbox, width: float, height: float, rotation: int) -> list[float]:
    """Normalise to [0,1] and de-rotate.

    PyMuPDF reports span rects in unrotated page space, while a viewer renders the page
    rotated. Correcting here rather than at render time means every consumer — the API,
    the viewer, the exported report — gets coordinates that already agree.
    """
    x0, y0, x1, y1 = bbox
    if rotation:
        r = rotation % 360
        if r == 90:
            x0, y0, x1, y1 = y0, width - x1, y1, width - x0
            width, height = height, width
        elif r == 180:
            x0, y0, x1, y1 = width - x1, height - y1, width - x0, height - y0
        elif r == 270:
            x0, y0, x1, y1 = height - y1, x0, height - y0, x1
            width, height = height, width

    def clamp(v: float) -> float:
        return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v

    nx0, nx1 = clamp(x0 / width), clamp(x1 / width)
    ny0, ny1 = clamp(y0 / height), clamp(y1 / height)
    if nx1 < nx0:
        nx0, nx1 = nx1, nx0
    if ny1 < ny0:
        ny0, ny1 = ny1, ny0
    return [round(nx0, 6), round(ny0, 6), round(nx1, 6), round(ny1, 6)]


def _reading_order(blocks: list[dict], page_width: float) -> list[dict]:
    """Order text blocks the way a person reads them.

    PyMuPDF returns blocks in creation order, which on a two-column page interleaves the
    columns. Interleaved text corrupts ``full_text``, which corrupts the char offsets,
    which puts every highlight on that page in the wrong place — a failure that looks like
    "the highlight is slightly off" and survives casual inspection.

    Heuristic: if blocks cluster into two horizontal bands with a clear gutter, read the
    left column fully before the right. Otherwise fall back to top-to-bottom.
    """
    text_blocks = [b for b in blocks if b.get("type") == 0 and b.get("lines")]
    if len(text_blocks) < 4:
        return sorted(text_blocks, key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))

    mid = page_width / 2
    left = [b for b in text_blocks if b["bbox"][2] <= mid * 1.05]
    right = [b for b in text_blocks if b["bbox"][0] >= mid * 0.95]

    # Column ordering is only safe when EVERY block sits cleanly on one side. A block that
    # straddles the gutter — a full-width heading, or a table spanning both columns —
    # belongs to neither set, and an earlier "90% is close enough" rule silently DROPPED
    # it: the text disappeared from full_text altogether, so nothing downstream could find
    # or cite it. Losing text is far worse than reading two columns in the wrong order,
    # so anything less than a clean split falls back to top-to-bottom.
    covered = len(left) + len(right)
    if left and right and covered == len(text_blocks):
        return (sorted(left, key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0])) +
                sorted(right, key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0])))
    return sorted(text_blocks, key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))


def parse_page(page: pymupdf.Page, page_no: int) -> ParsedPage:
    width, height = page.rect.width, page.rect.height
    rotation = page.rotation or 0
    out = ParsedPage(page_no=page_no, width_pt=width, height_pt=height, rotation=rotation)

    data = page.get_text("dict")
    parts: list[str] = []
    cursor = 0

    for block in _reading_order(data.get("blocks", []), width):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = sanitise(span.get("text", ""))
                if not text.strip():
                    continue
                start = cursor
                parts.append(text)
                cursor += len(text)
                out.spans.append(ParsedSpan(
                    page_no=page_no,
                    bbox=_normalise_bbox(span["bbox"], width, height, rotation),
                    text=text, char_start=start, char_end=cursor,
                    font_size=round(span.get("size", 0.0), 2),
                    is_bold=bool(span.get("flags", 0) & 2 ** 4)))
                parts.append(" ")          # separator counted in the offsets above
                cursor += 1
        if out.spans:
            parts.append("\n")
            cursor += 1

    out.full_text = "".join(parts)
    out.needs_ocr = len(out.full_text.strip()) < OCR_CHAR_THRESHOLD
    return out


def verify_offsets(page: ParsedPage) -> None:
    """Assert the identity that everything downstream depends on.

    Called on every page during ingestion. Drifting offsets are the single most dangerous
    silent failure in the system, so this is cheap insurance, not a debug aid.
    """
    for span in page.spans:
        actual = page.full_text[span.char_start:span.char_end]
        if actual != span.text:
            raise AssertionError(
                f"char offset drift on page {page.page_no}: "
                f"full_text[{span.char_start}:{span.char_end}]={actual!r} != {span.text!r}")
