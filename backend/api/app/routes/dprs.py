"""DPR upload and status.

Invariant #3: nothing is parsed in the request handler. A 400-page PDF takes minutes and
no HTTP request survives that, so upload validates, stores, enqueues, and returns 202.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.config import get_settings
from api.app.db import get_db
from api.app.models import (AuditEvent, Document, DocumentPage, Dpr, TextSpan, User)
from api.app.security import current_user, scope_dprs
from api.app.services import storage
from worker import queue

router = APIRouter(prefix="/dprs", tags=["dprs"])

PDF_MAGIC = b"%PDF-"


def _visible(q, user: User):
    """Row scoping in SQL, not in the UI. See ``security.scope_dprs`` for the two rules."""
    return scope_dprs(q, user)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def upload_dpr(file: UploadFile = File(...),
               title: str = Form(...),
               self_check: bool = Form(False),
               db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> dict:
    settings = get_settings()

    head = file.file.read(len(PDF_MAGIC))
    if head != PDF_MAGIC:
        # Extensions are trivially faked; the magic bytes are not.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a PDF file")
    file.file.seek(0)

    tmp_key = f"uploads/tmp-{uuid.uuid4()}.pdf"
    try:
        size, sha = storage.put_stream(tmp_key, file.file, settings.max_upload_bytes)
    except ValueError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc

    # Same bytes already processed? Say so before spending any parsing compute.
    existing = db.scalar(select(Document).where(Document.sha256 == sha))
    if existing is not None:
        storage.delete(tmp_key)
        return {"dpr_id": str(existing.dpr_id), "document_id": str(existing.id),
                "duplicate_of_existing_upload": True}

    dpr = Dpr(title=title, submitted_by=user.id, organisation_id=user.organisation_id,
              status="processing", sha256=sha, is_self_check=self_check)
    db.add(dpr)
    db.flush()

    final_key = f"dprs/{dpr.id}/source.pdf"
    storage.put_bytes(final_key, storage.get_path(tmp_key).read_bytes())
    storage.delete(tmp_key)

    doc = Document(dpr_id=dpr.id, filename=file.filename or "upload.pdf",
                   storage_key=final_key, bytes=size, sha256=sha, status="queued")
    db.add(doc)
    db.flush()

    queue.enqueue(db, "ingest", dpr_id=dpr.id, document_id=doc.id)
    db.add(AuditEvent(actor_id=user.id, actor_role=user.role, dpr_id=dpr.id,
                      action="dpr.uploaded",
                      detail={"filename": doc.filename, "bytes": size,
                              "self_check": self_check}))
    db.commit()

    return {"dpr_id": str(dpr.id), "document_id": str(doc.id), "status": "queued"}


@router.get("")
def list_dprs(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    """List with scores and finding counts.

    Aggregated in two grouped queries rather than per row: a portfolio of forty DPRs
    should not cost eighty round trips.
    """
    from sqlalchemy import func

    from api.app.models import Assessment, Finding

    rows = db.scalars(_visible(select(Dpr), user).order_by(Dpr.created_at.desc())).all()
    ids = [d.id for d in rows]
    if not ids:
        return []

    scores = dict(db.execute(
        select(Assessment.dpr_id, Assessment.overall_score)
        .where(Assessment.dpr_id.in_(ids))).all())
    counts = {
        dpr_id: (total, critical)
        for dpr_id, total, critical in db.execute(
            select(Finding.dpr_id, func.count(),
                   func.count().filter(Finding.severity == "critical"))
            .where(Finding.dpr_id.in_(ids)).group_by(Finding.dpr_id)).all()
    }

    return [{"id": str(d.id), "title": d.title, "status": d.status,
             "is_self_check": d.is_self_check,
             "created_at": d.created_at.isoformat(),
             "overall_score": scores.get(d.id),
             "finding_count": counts.get(d.id, (0, 0))[0],
             "critical_count": counts.get(d.id, (0, 0))[1]}
            for d in rows]


@router.get("/{dpr_id}/status")
def dpr_status(dpr_id: uuid.UUID, db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> dict:
    dpr = db.scalar(_visible(select(Dpr).where(Dpr.id == dpr_id), user))
    if dpr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "DPR not found")
    doc = db.scalar(select(Document).where(Document.dpr_id == dpr_id))
    if doc is None:
        # Same KEYS as the normal branch, always. This used to return four of the eleven,
        # and every caller that read `spans` or `page_count` off it — the review workspace
        # header among them — crashed on a DPR whose document row never got written, which
        # is exactly what an upload that failed early leaves behind. A partial payload turns
        # one broken record into a broken screen.
        return {"dpr_id": str(dpr_id), "document_id": None,
                "stage": "no_document",
                "detail": "No document has been attached to this report yet",
                "percent": 0, "pages_done": 0, "page_count": None, "spans": 0,
                "is_self_check": dpr.is_self_check, "ocr_pages": 0, "error": None}

    # Real stage names, not a spinner: users tolerate a slow process they can watch.
    label = {"queued": "Queued", "parsing": "Reading text and tables",
             "ocr": "Reading scanned pages", "indexing": "Indexing",
             "ready": "Ready", "failed": "Failed"}.get(doc.status, doc.status)
    detail = label
    if doc.status == "parsing" and doc.page_count:
        detail = f"{label} — page {doc.pages_done} of {doc.page_count}"

    return {"dpr_id": str(dpr_id), "document_id": str(doc.id),
            "stage": doc.status, "detail": detail, "percent": doc.progress,
            "pages_done": doc.pages_done, "page_count": doc.page_count,
            "spans": db.query(TextSpan).filter(TextSpan.document_id == doc.id).count(),
            # A private rehearsal is scored the same but shown differently: the submitter
            # sees their score there, because it is their own document and it never enters
            # the ministry's ranking.
            "is_self_check": dpr.is_self_check,
            # How many pages had no text layer. Nothing to say when it is zero — this
            # exists so a poor scan can be reported as a poor scan, rather than silently
            # producing a weak assessment the author cannot explain.
            "ocr_pages": db.query(DocumentPage)
                           .filter(DocumentPage.document_id == doc.id,
                                   DocumentPage.ocr_used.is_(True)).count(),
            "error": doc.error}
