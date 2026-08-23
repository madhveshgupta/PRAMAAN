"""Table extraction with per-cell coordinates.

DPR financial data lives almost entirely in tables, and a cell we cannot point at is a
cell we cannot cite. Cell bboxes are normalised into the *same* coordinate space as text
spans, so a finding anchored to a table cell highlights identically to one anchored to
prose.

Camelot is deliberately not used: it needs Ghostscript, which is a native dependency we
cannot assume on a teammate's laptop now that there is no container. pdfplumber covers
ruled tables, which is what DPR cost abstracts are.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("pramaan.tables")


@dataclass
class ParsedCell:
    row_idx: int
    col_idx: int
    text: str
    bbox: list[float]


@dataclass
class ParsedTable:
    page_no: int
    bbox: list[float]
    n_rows: int
    n_cols: int
    extractor: str
    cells: list[ParsedCell] = field(default_factory=list)


def _norm(x0, top, x1, bottom, w, h) -> list[float]:
    def c(v):
        return 0.0 if v < 0 else 1.0 if v > 1 else round(v, 6)
    return [c(x0 / w), c(top / h), c(x1 / w), c(bottom / h)]


def parse_tables(pdf_path: str, page_no: int) -> list[ParsedTable]:
    """Extract tables from one page. Returns [] rather than raising — a page whose tables
    we cannot read must not fail the whole document."""
    try:
        import pdfplumber
    except ImportError:                                  # pragma: no cover
        log.warning("pdfplumber unavailable — table extraction skipped")
        return []

    out: list[ParsedTable] = []
    try:
        with pdfplumber.open(pdf_path, pages=[page_no]) as pdf:
            if not pdf.pages:
                return []
            page = pdf.pages[0]
            w, h = float(page.width), float(page.height)
            for finder in page.find_tables():
                rows = finder.rows
                if not rows:
                    continue
                n_cols = max(len(r.cells) for r in rows)
                tbl = ParsedTable(
                    page_no=page_no,
                    bbox=_norm(*finder.bbox, w, h),
                    n_rows=len(rows), n_cols=n_cols, extractor="pdfplumber")
                for r_idx, row in enumerate(rows):
                    for c_idx, cell in enumerate(row.cells):
                        if cell is None:      # merged span — no own geometry
                            continue
                        # pdfplumber occasionally reports a cell a fraction of a point
                        # outside the page, and crop() then refuses the whole table. Clamp
                        # rather than lose every cell on the page over a rounding edge.
                        x0 = max(0.0, min(float(cell[0]), w))
                        top = max(0.0, min(float(cell[1]), h))
                        x1 = max(0.0, min(float(cell[2]), w))
                        bottom = max(0.0, min(float(cell[3]), h))
                        if x1 - x0 < 0.5 or bottom - top < 0.5:
                            continue
                        from worker.parsers.text import sanitise
                        text = sanitise(page.crop((x0, top, x1, bottom))
                                        .extract_text(x_tolerance=1) or "").strip()
                        tbl.cells.append(ParsedCell(
                            row_idx=r_idx, col_idx=c_idx, text=text,
                            bbox=_norm(x0, top, x1, bottom, w, h)))
                if tbl.cells:
                    out.append(tbl)
    except Exception as exc:                             # noqa: BLE001
        log.warning("table extraction failed on page %s: %s", page_no, exc)
    return out
