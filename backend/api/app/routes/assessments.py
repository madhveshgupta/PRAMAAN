"""Assessment and findings API — everything the review workspace renders.

The findings payload ships complete, anchors included, in one response. That is
deliberate: the jump from clicking a finding to seeing the highlight must involve no
network round-trip, or the interaction stops feeling like an instrument.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db import get_db
from api.app.models import (Assessment, AuditEvent, Document, DocumentPage, Dpr,
                            ExtractedField, ExtractionRejection, Finding, FindingReview,
                            User)
from api.app.security import RequireRole, current_user, visible_dpr_or_404
from api.app.services import checklist as checklist_service
from api.app.services import storage

router = APIRouter(tags=["assessment"])

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _authorised(db: Session, dpr_id: uuid.UUID, user: User) -> Dpr:
    """404 rather than 403 — do not confirm the existence of a DPR the caller cannot see.
    Covers another organisation's report and, for the ministry, a self-check."""
    return visible_dpr_or_404(db, dpr_id, user)


@router.get("/dprs/{dpr_id}/assessment")
def get_assessment(dpr_id: uuid.UUID, db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    _authorised(db, dpr_id, user)
    a = db.scalar(select(Assessment).where(Assessment.id.isnot(None),
                                           Assessment.dpr_id == dpr_id)
                  .order_by(Assessment.created_at.desc()))
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not assessed yet")
    return {
        "dpr_id": str(dpr_id),
        "overall_score": a.overall_score,
        "components": [
            {"key": "completeness", "label": "Completeness", "score": a.completeness_score},
            {"key": "consistency", "label": "Consistency", "score": a.consistency_score},
            # None means "not scored", never zero. F5 has no reference data, and scoring
            # it zero would penalise the DPR for a gap that is ours.
            {"key": "cost_realism", "label": "Cost realism", "score": a.cost_realism_score,
             # Read off the persisted check row, so the wording has one home and an old
             # assessment keeps the wording that was true when it ran.
             "unavailable_reason": None if a.cost_realism_score is not None else
             checklist_service.cost_realism_reason(db, a.id)},
            {"key": "financial", "label": "Financial sanity", "score": a.financial_score},
        ],
        "rubric_version": a.rubric_version,
        "engine_version": a.engine_version,
        "profile": {"key": a.rubric_profile, "label": a.rubric_profile_label,
                    "confidence": a.rubric_profile_confidence,
                    "provenance": a.rubric_provenance},
        # So the header can say "24 checks · 21 confirmed" without opening the tab. A score
        # with no sense of how much was examined is the black box this replaces.
        "check_tally": checklist_service.tally(db, a.id),
        "advisory_notice": ("Advisory assessment. Sanctioning authority rests with the "
                            "competent authority."),
    }


@router.get("/dprs/{dpr_id}/checklist")
def get_checklist(dpr_id: uuid.UUID, db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> dict:
    """Every check the engine ran, pass or fail.

    Findings answer "what needs acting on". This answers "what was examined" — the question
    a reviewer asks before deciding whether they still have to read the document themselves.
    """
    _authorised(db, dpr_id, user)
    a = db.scalar(select(Assessment).where(Assessment.dpr_id == dpr_id)
                  .order_by(Assessment.created_at.desc()))
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not assessed yet")
    return checklist_service.build(db, a)


@router.get("/dprs/{dpr_id}/findings")
def list_findings(dpr_id: uuid.UUID, severity: str | None = None,
                  category: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> list[dict]:
    _authorised(db, dpr_id, user)
    q = select(Finding).where(Finding.dpr_id == dpr_id)
    if severity:
        q = q.where(Finding.severity == severity)
    if category:
        q = q.where(Finding.category == category)
    rows = sorted(db.scalars(q).all(), key=lambda f: SEVERITY_ORDER.get(f.severity, 9))

    # The latest review per finding, in ONE query rather than one per finding. This loop
    # used to issue a SELECT inside it, so a report with forty findings cost forty-one round
    # trips — on the endpoint whose whole purpose, per the note below, is to ship complete so
    # that clicking a finding costs no further request.
    latest: dict[uuid.UUID, FindingReview] = {}
    if rows:
        for r in db.scalars(
                select(FindingReview)
                .where(FindingReview.finding_id.in_([f.id for f in rows]))
                .order_by(FindingReview.created_at.asc())):
            latest[r.finding_id] = r      # ascending, so the last write per id wins

    out = []
    for f in rows:
        review = latest.get(f.id)
        out.append({
            "id": str(f.id), "severity": f.severity, "category": f.category,
            "status": f.status, "rule_id": f.rule_id, "title": f.title,
            "message": f.message, "suggested_action": f.suggested_action,
            "evidence": f.evidence,           # ships complete — no round-trip to highlight
            "anchor_count": len(f.evidence),
            "match_confidence": f.match_confidence, "match_status": f.match_status,
            "review": ({"decision": review.decision, "note": review.note,
                        "at": review.created_at.isoformat()} if review else None),
        })
    return out


@router.post("/findings/{finding_id}/review")
def review_finding(finding_id: uuid.UUID, decision: str, note: str | None = None,
                   db: Session = Depends(get_db),
                   user: User = Depends(RequireRole("ministry"))) -> dict:
    if decision not in {"accepted", "rejected", "amended"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid decision")
    if decision in {"rejected", "amended"} and not (note or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "A note is required when rejecting or amending a finding")
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")

    db.add(FindingReview(finding_id=finding_id, reviewer_id=user.id,
                         decision=decision, note=note))
    db.add(AuditEvent(actor_id=user.id, actor_role=user.role, dpr_id=finding.dpr_id,
                      action="finding.reviewed",
                      detail={"finding_id": str(finding_id), "rule_id": finding.rule_id,
                              "decision": decision}))
    db.commit()
    return {"finding_id": str(finding_id), "decision": decision}


@router.get("/dprs/{dpr_id}/extraction")
def get_extraction(dpr_id: uuid.UUID, db: Session = Depends(get_db),
                   user: User = Depends(RequireRole("ministry"))) -> dict:
    """Ministry only. This is a reviewer's working view — which figure the engine took as
    the cost, and what it refused to record. The submitting organisation sees the findings
    those figures produced, each with its page, which is the actionable half."""
    _authorised(db, dpr_id, user)
    fields = db.scalars(select(ExtractedField)
                        .where(ExtractedField.dpr_id == dpr_id)
                        .order_by(ExtractedField.field_key)).all()
    rejected = db.scalars(select(ExtractionRejection)
                          .where(ExtractionRejection.dpr_id == dpr_id)).all()
    return {
        "fields": [{"field_key": f.field_key, "value": f.value_text, "unit": f.unit,
                    "status": f.status, "confidence": f.confidence, "method": f.method,
                    "evidence": f.evidence,
                    "needs_verification": f.status == "needs_human_verification"}
                   for f in fields],
        # Surfaced as a reliability feature, not hidden as an error log.
        "blocked_values": [{"field_key": r.field_key, "claimed_value": r.claimed_value,
                            "reason": r.reason} for r in rejected],
        # Whether a model was involved at all. Without this the UI cannot tell "we checked
        # and blocked nothing" from "there was nothing to check", and it was claiming the
        # former on documents where no model had run.
        "llm_fields": sum(1 for f in fields if f.method == "llm_verified"),
    }


@router.get("/dprs/{dpr_id}/risk")
def get_risk(dpr_id: uuid.UUID, db: Session = Depends(get_db),
             user: User = Depends(RequireRole("ministry"))) -> dict:
    """Risk prediction with its reasons. A probability without attributions is not
    something an officer can put in an appraisal note (invariant #6).

    Ministry only, and deliberately so. This is a judgement about the *applicant* — it is
    driven by their agency's past overrun record, not by anything in the document they just
    submitted. It is not actionable by them and it is an input to the ministry's ranking,
    so it stays on the ministry's side of the line.
    """
    from api.app.models import OutcomeRange, RiskPrediction

    _authorised(db, dpr_id, user)
    r = db.scalar(select(RiskPrediction).where(RiskPrediction.dpr_id == dpr_id)
                  .order_by(RiskPrediction.created_at.desc()))
    o = db.scalar(select(OutcomeRange).where(OutcomeRange.dpr_id == dpr_id)
                  .order_by(OutcomeRange.created_at.desc()))
    if r is None and o is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No risk analysis for this DPR")

    payload: dict = {"dpr_id": str(dpr_id)}
    if r is not None:
        payload["prediction"] = {
            "model_version": r.model_version,
            "delay_probability": r.delay_probability,
            "overrun_probability": r.overrun_probability,
            # One set per probability. Naming them apart is the point: the delay figure
            # used to be printed above the cost model's reasons.
            "overrun_drivers": r.shap_drivers,
            "delay_drivers": r.delay_drivers,
            "drivers": r.delay_drivers or r.shap_drivers,   # legacy key
            "caveat": (r.features_used or {}).get("caveat"),
        }
    if o is not None:
        crore = 10_000_000_00      # paise per crore
        payload["outcome_range"] = {
            "method": o.method,
            # Always shown. "80% of 340 projects" and "80% of 6" are different claims.
            "peer_count": o.peer_count,
            "peer_criteria": o.peer_criteria,
            "cost_p50_cr": round(o.cost_p50 / crore, 2) if o.cost_p50 else None,
            "cost_p80_cr": round(o.cost_p80 / crore, 2) if o.cost_p80 else None,
            "cost_p95_cr": round(o.cost_p95 / crore, 2) if o.cost_p95 else None,
            "months_p50": o.months_p50, "months_p80": o.months_p80,
            "peer_distribution": o.peer_distribution,
        }
    return payload


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db),
              user: User = Depends(RequireRole("ministry"))) -> list[dict]:
    """Ranked by quality-adjusted risk. A ministry with forty proposals and a fixed budget
    does not need forty scores, it needs an order."""
    from sqlalchemy import func

    from api.app.models import OutcomeRange, RiskPrediction

    rows = db.scalars(select(Dpr).where(~Dpr.is_self_check)).all()   # see security.scope_dprs
    ids = [d.id for d in rows] or [uuid.uuid4()]

    scores = dict(db.execute(select(Assessment.dpr_id, Assessment.overall_score)
                             .where(Assessment.dpr_id.in_(ids))).all())
    # The checklist tally, per report, in two queries for the whole portfolio. The dashboard
    # was fetching this one report at a time from the browser.
    assessment_ids = dict(db.execute(select(Assessment.dpr_id, Assessment.id)
                                     .where(Assessment.dpr_id.in_(ids))).all())
    tallies = checklist_service.tally_many(db, list(assessment_ids.values()))
    risks = dict(db.execute(select(RiskPrediction.dpr_id, RiskPrediction.delay_probability)
                            .where(RiskPrediction.dpr_id.in_(ids))).all())
    ranges = {r.dpr_id: r for r in db.scalars(
        select(OutcomeRange).where(OutcomeRange.dpr_id.in_(ids))).all()}
    counts = dict(db.execute(
        select(Finding.dpr_id, func.count()).where(Finding.dpr_id.in_(ids),
                                                   Finding.severity == "critical")
        .group_by(Finding.dpr_id)).all())

    out = []
    for d in rows:
        quality = scores.get(d.id)
        risk = risks.get(d.id)
        rng = ranges.get(d.id)
        composite = None
        if quality is not None:
            composite = round(0.5 * quality + 0.5 * (100 - (risk or 0) * 100), 1)
        out.append({
            "id": str(d.id), "title": d.title, "status": d.status,
            "quality_score": quality,
            "delay_probability": risk,
            "composite": composite,
            "critical_findings": counts.get(d.id, 0),
            "p80_cost_cr": round(rng.cost_p80 / 10_000_000_00, 2)
                           if rng and rng.cost_p80 else None,
            "peer_count": rng.peer_count if rng else None,
            # None, never an empty tally: a report assessed before the checklist existed has
            # no rows, and reporting that as "0 checks passed" would be a claim about the
            # report rather than about our record of it.
            "check_tally": tallies.get(assessment_ids.get(d.id)),
        })
    return sorted(out, key=lambda r: (r["composite"] is None, r["composite"]))


@router.get("/documents/{document_id}/pages/{page_no}")
def page_raster(document_id: uuid.UUID, page_no: int, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    _authorised(db, doc.dpr_id, user)
    page = db.scalar(select(DocumentPage).where(
        DocumentPage.document_id == document_id, DocumentPage.page_no == page_no))
    if page is None or not page.raster_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page raster not available")
    return FileResponse(storage.get_path(page.raster_key), media_type="image/webp")


@router.get("/documents/{document_id}/pdf")
def source_pdf(document_id: uuid.UUID, db: Session = Depends(get_db),
               user: User = Depends(current_user)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    _authorised(db, doc.dpr_id, user)
    return FileResponse(storage.get_path(doc.storage_key), media_type="application/pdf",
                        filename=doc.filename)
