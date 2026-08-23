"""Page rasters for the viewer.

Rendered once at ingest and cached, so a review session never re-rasterises. WebP at
150 DPI keeps a 300-page document to a few megabytes while staying legible at the zoom
levels a reviewer actually uses.
"""
from __future__ import annotations

import io
import logging

import pymupdf

from api.app.services import storage

log = logging.getLogger("pramaan.raster")

RASTER_DPI = 150


def render_page(page: pymupdf.Page, document_id, page_no: int) -> str | None:
    """Render and store one page. Returns the storage key, or None on failure —
    a page we cannot rasterise should not fail the document."""
    key = f"rasters/{document_id}/{page_no:05d}.webp"
    try:
        zoom = RASTER_DPI / 72.0
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        from PIL import Image
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=80, method=4)
        storage.put_bytes(key, buf.getvalue())
        return key
    except Exception as exc:                             # noqa: BLE001
        log.warning("raster failed for page %s: %s", page_no, exc)
        return None
