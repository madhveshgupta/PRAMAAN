"""Ingestion: PDF in, queryable geometry out.

Structure worth understanding before changing anything here:

* **Idempotent by construction** (invariant #12). Every derived row for the document is
  deleted before parsing starts. A worker that dies at page 150 and has its job reclaimed
  would otherwise *append* a second set of spans, doubling `full_text` and every char
  offset — which puts every highlight in that document slightly wrong, and "slightly
  wrong" survives inspection all the way to a demo.
* **Per-page commit.** A 400-page document never sits in memory at once, and progress is
  visible while it runs.
* **Heartbeat.** A long parse can outlast the stale-lock window; without a beat the
  reclaim fires mid-run and a second worker starts the same document.
"""
from __future__ import annotations

import logging

import pymupdf
from sqlalchemy import delete
from sqlalchemy.orm import Session

from api.app.models import (Document, DocumentPage, Dpr, Job, Table, TableCell, TextSpan)
from api.app.models.base import utcnow
from api.app.services import storage
from worker import queue
from worker.parsers import ocr as ocr_mod
from worker.parsers import raster, tables, text

log = logging.getLogger("pramaan.ingest")

STAGES = ("extracting_text", "extracting_tables", "ocr_if_needed", "indexing", "ready")


def _clear_derived(db: Session, document_id) -> int:
    """Invariant #12. Returns how many spans were removed, for the log."""
    removed = db.query(TextSpan).filter(TextSpan.document_id == document_id).count()
    db.execute(delete(TableCell).where(TableCell.document_id == document_id))
    db.execute(delete(Table).where(Table.document_id == document_id))
    db.execute(delete(TextSpan).where(TextSpan.document_id == document_id))
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
    storage.delete_prefix(f"rasters/{document_id}")
    return removed


def handle_ingest(db: Session, job: Job) -> None:
    doc = db.get(Document, job.document_id)
    if doc is None:
        raise ValueError(f"document {job.document_id} not found")

    pdf_path = storage.get_path(doc.storage_key)

    # --- idempotency: start from a clean slate every time, including a retry
    removed = _clear_derived(db, doc.id)
    if removed:
        log.info("re-ingest of %s — cleared %s existing spans first", doc.id, removed)
    doc.status, doc.stage, doc.progress, doc.pages_done, doc.error = \
        "parsing", STAGES[0], 0, 0, None
    db.commit()

    ocr_ready = ocr_mod.tesseract_available()
    if not ocr_ready:
        log.warning("tesseract unavailable — scanned pages will be recorded as "
                    "unreadable rather than silently empty")

    last_beat = utcnow()
    pages_needing_ocr = 0

    try:
        with pymupdf.open(pdf_path) as pdf:
            if pdf.needs_pass:
                raise ValueError("PDF is password protected")
            doc.page_count = pdf.page_count
            db.commit()

            for index in range(pdf.page_count):
                page_no = index + 1
                page = pdf[index]

                try:
                    parsed = text.parse_page(page, page_no)
                except Exception as exc:                 # noqa: BLE001
                    # One unreadable page must not lose the other 399.
                    log.warning("page %s unparseable, skipped: %s", page_no, exc)
                    continue

                ocr_conf = None
                ocr_used = False
                if parsed.needs_ocr:
                    pages_needing_ocr += 1
                    result = ocr_mod.ocr_page(page, parsed)
                    ocr_used = result.available
                    ocr_conf = result.confidence

                text.verify_offsets(parsed)      # the identity, checked on every page

                raster_key = raster.render_page(page, doc.id, page_no)

                db.add(DocumentPage(
                    document_id=doc.id, page_no=page_no,
                    width_pt=parsed.width_pt, height_pt=parsed.height_pt,
                    rotation=parsed.rotation, full_text=parsed.full_text,
                    ocr_used=ocr_used, ocr_confidence=ocr_conf, raster_key=raster_key))

                db.bulk_save_objects([
                    TextSpan(document_id=doc.id, page_no=s.page_no, bbox=s.bbox,
                             text=s.text, char_start=s.char_start, char_end=s.char_end,
                             font_size=s.font_size, is_bold=s.is_bold)
                    for s in parsed.spans])

                for tbl in tables.parse_tables(str(pdf_path), page_no):
                    row = Table(document_id=doc.id, page_no=tbl.page_no, bbox=tbl.bbox,
                                n_rows=tbl.n_rows, n_cols=tbl.n_cols,
                                extractor=tbl.extractor)
                    db.add(row)
                    db.flush()
                    db.bulk_save_objects([
                        TableCell(table_id=row.id, document_id=doc.id, page_no=page_no,
                                  row_idx=c.row_idx, col_idx=c.col_idx, text=c.text,
                                  bbox=c.bbox)
                        for c in tbl.cells])

                doc.pages_done = page_no
                doc.progress = int(page_no / pdf.page_count * 100)
                doc.stage = STAGES[2] if parsed.needs_ocr else STAGES[0]
                db.commit()                              # per-page commit

                if utcnow() - last_beat >= queue.HEARTBEAT_EVERY:
                    queue.heartbeat(db, job)
                    last_beat = utcnow()
                    log.info("… page %s/%s", page_no, pdf.page_count)

        # Clear the error on completion as well as on entry. Resetting only at the start
        # lets a failure written by an earlier, slower path outlive the success that
        # replaced it — which is how a complete 318-page document sat in the UI for days
        # reporting a fatal IntegrityError it had already recovered from.
        doc.stage, doc.status, doc.progress, doc.error = STAGES[4], "ready", 100, None
        if pages_needing_ocr and not ocr_ready:
            doc.error = (f"{pages_needing_ocr} page(s) have no text layer and tesseract "
                         f"is not installed — their content is unavailable")
        db.commit()

        if doc.dpr_id:
            dpr = db.get(Dpr, doc.dpr_id)
            if dpr:
                dpr.status = "processing"
            queue.enqueue(db, "extract", dpr_id=doc.dpr_id, document_id=doc.id)
            db.commit()

        log.info("ingested %s: %s pages, %s spans", doc.id, doc.page_count,
                 db.query(TextSpan).filter(TextSpan.document_id == doc.id).count())

    except Exception as exc:                             # noqa: BLE001
        db.rollback()
        doc = db.get(Document, job.document_id)
        db.refresh(doc)
        # Do not stamp a failure onto a document someone else has already finished. Two
        # workers once held ingest jobs for the same document: both cleared and re-inserted
        # the pages, the loser hit `uq_doc_page`, and its IntegrityError landed on a
        # document the winner had taken to `ready` — so a complete 318-page report showed a
        # fatal error for days. Migration 007 makes the race unrepresentable; this makes the
        # failure path safe even if it somehow recurs.
        if doc.status == "ready":
            log.warning("ingest of %s failed (%s) but the document is already ready — "
                        "another worker completed it; not overwriting", doc.id, exc)
            db.commit()
            return
        doc.status, doc.error = "failed", f"{type(exc).__name__}: {exc}"[:4000]
        # The DPR row carries the status the UI lists. Leaving it on "processing" left a
        # failed upload spinning forever with no way for the user to learn what happened.
        if doc.dpr_id:
            dpr = db.get(Dpr, doc.dpr_id)
            if dpr:
                dpr.status = "returned"
        db.commit()
        raise
