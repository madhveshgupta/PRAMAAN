"""Decision workflow, audit trail and the report export.

Two things here are load-bearing rather than decorative:

* Both steps are gated on the ministry role **in the route**. A UI that hides the button
  is presentation; this is access control.
* Appraisal and sanction are written as two distinct audit events, even when the same
  person performs both. Collapsing them would leave the trail unable to answer the only
  question an auditor actually asks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from api.app.db import get_db
from api.app.models import (Assessment, AuditEvent, Dpr, Finding, FindingReview,
                            OutcomeRange, RiskPrediction, User)
from api.app.security import RequireRole, current_user, visible_dpr_or_404
from api.app.services.report import build_appraisal_note

router = APIRouter(tags=["governance"])

DECISIONS = {"approved": "approve", "returned": "return for revision",
             "rejected": "reject", "approved_with_conditions": "approve with conditions"}


@router.post("/dprs/{dpr_id}/recommendation")
def write_recommendation(dpr_id: uuid.UUID, recommendation: str, note: str | None = None,
                         db: Session = Depends(get_db),
                         user: User = Depends(RequireRole("ministry"))) -> dict:
    """The appraisal step. Available to any ministry user — appraising and deciding are
    different acts, recorded as two distinct audit events."""
    if recommendation not in {"recommend", "recommend_with_conditions", "return"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid recommendation")
    # Raises 404 for a report this user may not see; the row itself is not needed here.
    visible_dpr_or_404(db, dpr_id, user)

    db.add(AuditEvent(actor_id=user.id, actor_role=user.role, dpr_id=dpr_id,
                      action="dpr.appraised",
                      detail={"recommendation": recommendation, "note": note}))
    db.commit()
    return {"dpr_id": str(dpr_id), "recommendation": recommendation}


@router.post("/dprs/{dpr_id}/decision")
def record_decision(dpr_id: uuid.UUID, decision: str, note: str,
                    db: Session = Depends(get_db),
                    user: User = Depends(RequireRole("ministry"))) -> dict:
    """The sanction step. Ministry only; a note is always required."""
    if decision not in DECISIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid decision")
    if not note.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "A recorded reason is required for every decision")
    dpr = visible_dpr_or_404(db, dpr_id, user)

    assessment = db.scalar(select(Assessment).where(Assessment.dpr_id == dpr_id)
                           .order_by(Assessment.created_at.desc()))
    dpr.status = "approved" if decision.startswith("approved") else decision

    # Pin what was true at the moment of decision — an audit years later must see what the
    # deciding user saw, not what today's rubric would compute.
    db.add(AuditEvent(
        actor_id=user.id, actor_role=user.role, dpr_id=dpr_id, action="dpr.decided",
        detail={"decision": decision, "note": note,
                "score_at_decision": assessment.overall_score if assessment else None,
                "rubric_version": assessment.rubric_version if assessment else None,
                "engine_version": assessment.engine_version if assessment else None}))
    db.commit()
    return {"dpr_id": str(dpr_id), "decision": decision, "status": dpr.status}


@router.get("/audit")
def audit_trail(dpr_id: uuid.UUID | None = None, limit: int = 200,
                db: Session = Depends(get_db),
                user: User = Depends(RequireRole("ministry"))) -> list[dict]:
    q = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit, 1000))
    if dpr_id:
        visible_dpr_or_404(db, dpr_id, user)
        q = q.where(AuditEvent.dpr_id == dpr_id)
    else:
        # Events outlive the DPR they describe (migrations 004/005 dropped the FK on
        # purpose), so exclude by id rather than joining: an event whose DPR is gone is
        # not a self-check and must stay in the trail.
        q = q.where(or_(AuditEvent.dpr_id.is_(None),
                        AuditEvent.dpr_id.notin_(select(Dpr.id).where(Dpr.is_self_check))))
    events = db.scalars(q).all()

    # The trail outlives the reports it describes, so an event's `dpr_id` is not a promise
    # that the report is still here — and the UI was offering "Open the report" on every
    # one of them, which walked the officer into an empty review screen. Resolve the titles
    # that still exist in one query; the ones that come back absent are the ones with
    # nothing to open.
    titles: dict[uuid.UUID, str] = {}
    ids = {e.dpr_id for e in events if e.dpr_id}
    if ids:
        titles = dict(db.execute(select(Dpr.id, Dpr.title).where(Dpr.id.in_(ids))).all())

    return [{"id": str(e.id), "at": e.created_at.isoformat(), "action": e.action,
             "actor_role": e.actor_role, "actor_id": str(e.actor_id) if e.actor_id else None,
             "dpr_id": str(e.dpr_id) if e.dpr_id else None,
             "dpr_title": titles.get(e.dpr_id) if e.dpr_id else None,
             "detail": e.detail}
            for e in events]


@router.get("/dprs/{dpr_id}/decision")
def latest_decision(dpr_id: uuid.UUID, db: Session = Depends(get_db),
                    user: User = Depends(current_user)) -> dict:
    """The decision on this report, for the organisation that submitted it.

    The reason for a decision has always been mandatory and permanently pinned in the audit
    trail — but the audit trail is ministry-only, so the person the decision is *about* had
    no way to read it. A report could come back with no explanation reachable anywhere in
    the product.

    What this deliberately does NOT return: `score_at_decision`, `rubric_version`,
    `engine_version`. Those sit in the same audit record and are the ministry's own
    assessment, not the applicant's business.
    """
    dpr = visible_dpr_or_404(db, dpr_id, user)
    if user.role == "applicant" and dpr.organisation_id != user.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "DPR not found")

    event = db.scalar(select(AuditEvent)
                      .where(AuditEvent.dpr_id == dpr_id,
                             AuditEvent.action == "dpr.decided")
                      .order_by(AuditEvent.created_at.desc()))
    # Undecided is the normal state for most reports, not an error — the screen has to be
    # able to say "still with the ministry" rather than render a 404.
    if event is None:
        return {"dpr_id": str(dpr_id), "status": dpr.status, "decision": None}

    officer = db.get(User, event.actor_id) if event.actor_id else None
    detail = event.detail or {}
    return {
        "dpr_id": str(dpr_id),
        "status": dpr.status,
        "decision": {
            "outcome": detail.get("decision"),
            "reason": detail.get("note"),
            "at": event.created_at.isoformat(),
            "by": officer.full_name if officer else None,
            "by_role": event.actor_role,
        },
    }


@router.get("/dprs/{dpr_id}/report.pdf")
def appraisal_note(dpr_id: uuid.UUID, db: Session = Depends(get_db),
                   user: User = Depends(RequireRole("ministry"))) -> Response:
    """Ministry only. This is the ministry's own appraisal document — it carries the score,
    the component breakdown and the internal reasoning. The submitting organisation gets the
    decision and its recorded reason from /decision instead."""
    dpr = visible_dpr_or_404(db, dpr_id, user)

    assessment = db.scalar(select(Assessment).where(Assessment.dpr_id == dpr_id)
                           .order_by(Assessment.created_at.desc()))
    findings = db.scalars(select(Finding).where(Finding.dpr_id == dpr_id)).all()
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings = sorted(findings, key=lambda f: order.get(f.severity, 9))

    reviews = {}
    for fr in db.scalars(select(FindingReview).where(
            FindingReview.finding_id.in_([f.id for f in findings] or [uuid.uuid4()]))).all():
        reviews[fr.finding_id] = {"decision": fr.decision, "note": fr.note}

    risk = db.scalar(select(RiskPrediction).where(RiskPrediction.dpr_id == dpr_id)
                     .order_by(RiskPrediction.created_at.desc()))
    outcome = db.scalar(select(OutcomeRange).where(OutcomeRange.dpr_id == dpr_id)
                        .order_by(OutcomeRange.created_at.desc()))

    pdf, digest = build_appraisal_note(
        dpr=dpr, assessment=assessment, findings=findings, reviews=reviews,
        risk=risk, outcome=outcome, generated_by=f"{user.full_name} ({user.role})")

    db.add(AuditEvent(actor_id=user.id, actor_role=user.role, dpr_id=dpr_id,
                      action="report.exported",
                      detail={"sha256": digest,
                              "at": datetime.now(timezone.utc).isoformat()}))
    db.commit()

    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="appraisal-{dpr_id}.pdf"',
                             "X-Content-SHA256": digest})
