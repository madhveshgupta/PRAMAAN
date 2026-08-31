"""Assembling the compliance checklist for the API.

Kept out of the route handler for the usual reason: business logic belongs in a service.
Each family's rows are read back in the order the engine wrote them, so an old assessment
renders as it ran rather than as today's rubric would compute it.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.models import Assessment, AssessmentCheck, Finding
from worker.scoring.checklist import FAMILY_ORDER

FAMILY_LABEL: dict[str, str] = {
    "data_quality": "Document quality",
    "completeness": "Required sections",
    "consistency": "Cross-document consistency",
    "financial": "Financial recomputation",
}

# Raw enum values as keys so the frontend never maintains a translation table.
STATUSES = ("pass", "partial", "insufficient_evidence", "flagged", "not_run")


def tally(db: Session, assessment_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(AssessmentCheck.status, func.count())
        .where(AssessmentCheck.assessment_id == assessment_id)
        .group_by(AssessmentCheck.status)).all()
    out = {s: 0 for s in STATUSES}
    for status, n in rows:
        out[status] = n
    out["total"] = sum(out[s] for s in STATUSES)
    return out


def tally_many(db: Session,
               assessment_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """`tally` for a whole portfolio, in one grouped query.

    The ministry dashboard needs the tally for every report at once. It used to get it by
    calling the per-report checklist endpoint in a loop from the browser, which is forty
    HTTP requests and forty assessment rebuilds to draw one bar. Grouping by assessment is
    the same aggregate the single-report version does, with the id carried through.
    """
    if not assessment_ids:
        return {}
    rows = db.execute(
        select(AssessmentCheck.assessment_id, AssessmentCheck.status, func.count())
        .where(AssessmentCheck.assessment_id.in_(assessment_ids))
        .group_by(AssessmentCheck.assessment_id, AssessmentCheck.status)).all()

    out = {aid: {s: 0 for s in STATUSES} for aid in assessment_ids}
    for aid, status, n in rows:
        out[aid][status] = n
    for aid, counts in out.items():
        counts["total"] = sum(counts[s] for s in STATUSES)
    return out


def build(db: Session, a: Assessment) -> dict:
    checks = list(db.scalars(
        select(AssessmentCheck)
        .where(AssessmentCheck.assessment_id == a.id)
        .order_by(AssessmentCheck.ordinal)))

    # Which findings each row produced, so the UI can jump from a checklist row to the
    # finding that explains it.
    links: dict[uuid.UUID, list[str]] = {}
    for check_id, finding_id in db.execute(
            select(Finding.assessment_check_id, Finding.id)
            .where(Finding.assessment_id == a.id,
                   Finding.assessment_check_id.isnot(None))).all():
        links.setdefault(check_id, []).append(str(finding_id))

    families = []
    for key in FAMILY_ORDER:
        rows = [c for c in checks if c.family == key]
        if not rows:
            continue
        families.append({
            "key": key,
            "label": FAMILY_LABEL.get(key, key.replace("_", " ").title()),
            "checks": [{
                "check_id": c.check_id, "label": c.label, "severity": c.severity,
                "status": c.status, "detail": c.detail,
                "evidence": c.evidence,        # ships complete — no round-trip to highlight
                "anchor_count": len(c.evidence),
                "evidence_score": c.evidence_score,
                "finding_ids": links.get(c.id, []),
            } for c in rows],
        })

    return {
        "dpr_id": str(a.dpr_id),
        "rubric_version": a.rubric_version,
        "profile": {"key": a.rubric_profile, "label": a.rubric_profile_label,
                    "confidence": a.rubric_profile_confidence,
                    "provenance": a.rubric_provenance},
        "tally": tally(db, a.id),
        "families": families,
        # An assessment from before the checklist existed has no rows. Say so plainly
        # rather than 404-ing on a DPR that visibly has a score — that reads as a bug.
        "stale": not checks,
        "advisory_notice": ("Advisory assessment. Sanctioning authority rests with the "
                            "competent authority."),
    }
