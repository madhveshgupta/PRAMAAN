"""OCR fallback for pages with no text layer.

Uses ``image_to_data`` rather than ``image_to_string`` — we need word-level boxes, not
just text, or an OCR'd page produces evidence we cannot highlight.

Tesseract is an optional native dependency. When it is absent we say so on the page
record instead of failing the document: the page is marked ``needs_ocr`` with zero
confidence, and every downstream consumer can see that its content is unavailable rather
than silently believing the page was blank.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pymupdf

from worker.parsers.text import ParsedPage, ParsedSpan, sanitise

log = logging.getLogger("pramaan.ocr")

OCR_DPI = 300
MIN_WORD_CONFIDENCE = 40.0


@dataclass
class OcrResult:
    available: bool
    confidence: float | None = None
    reason: str | None = None


def tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:                                    # noqa: BLE001
        return False


def ocr_page(page: pymupdf.Page, parsed: ParsedPage) -> OcrResult:
    """Fill `parsed` in place from OCR. Returns what happened, honestly."""
    if not tesseract_available():
        return OcrResult(False, reason="tesseract binary not installed")

    import pytesseract
    from PIL import Image

    try:
        zoom = OCR_DPI / 72.0
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as exc:                             # noqa: BLE001
        log.warning("OCR failed on page %s: %s", parsed.page_no, exc)
        return OcrResult(False, reason=f"{type(exc).__name__}: {exc}")

    # Past this point we are committed to replacing the page's content.

    # OCR REPLACES the page, it does not augment it. A page reaches here because its text
    # layer was too sparse to use, and whatever few spans that layer produced carry offsets
    # into a full_text we are about to overwrite. Leaving them attached orphans their
    # offsets — every highlight derived from them then lands somewhere arbitrary.
    #
    # This stayed invisible while tesseract was uninstalled (ocr_page returned early) and
    # surfaced the moment it became available, on real documents with figure-heavy pages.
    parsed.spans.clear()

    parts: list[str] = []
    cursor = 0
    confidences: list[float] = []
    W, H = float(pix.width), float(pix.height)

    for i, word in enumerate(data["text"]):
        text = sanitise(word or "").strip()
        if not text:
            continue
        conf = float(data["conf"][i])
        if conf < MIN_WORD_CONFIDENCE:
            continue
        confidences.append(conf)
        left, top = float(data["left"][i]), float(data["top"][i])
        width, height = float(data["width"][i]), float(data["height"][i])
        start = cursor
        parts.append(text)
        cursor += len(text)
        parsed.spans.append(ParsedSpan(
            page_no=parsed.page_no,
            bbox=[round(left / W, 6), round(top / H, 6),
                  round((left + width) / W, 6), round((top + height) / H, 6)],
            text=text, char_start=start, char_end=cursor))
        parts.append(" ")
        cursor += 1

    parsed.full_text = "".join(parts)
    mean = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
    return OcrResult(True, confidence=round(mean, 4))
