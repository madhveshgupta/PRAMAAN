"""Assessments, findings, and the reference data scoring depends on.

``findings.status`` has no 'fail' member. That is invariant #4 enforced by the database
rather than by application code: no evidence in a DPR is not proof a requirement was unmet,
and the system never renders that judgement. A human does.
"""
import uuid

from sqlalchemy import Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import TimestampMixin, fk_uuid, pg_enum, uuid_pk

__all__ = ["Assessment", "AssessmentCheck", "Finding", "FindingReview", "Setting"]

SEVERITY = pg_enum("critical", "high", "medium", "low", "info", name="finding_severity")
CATEGORY = pg_enum("completeness", "consistency", "financial",
                   "duplicate", "geo", "risk", "data_quality", name="finding_category")
# Deliberately no 'fail'.
FINDING_STATUS = pg_enum("pass", "partial", "insufficient_evidence", "flagged",
                         name="finding_status")
# The checklist's statuses. Separate from FINDING_STATUS, and deliberately so: a *finding*
# can never be "not run", and widening the findings enum to admit that value would weaken
# the DB-level guarantee that invariant #4 leans on.
#
# The line between the last two members is worth stating, because getting it wrong makes
# the checklist dishonest in a subtle way:
#   not_run               — the engine cannot run this check for ANY document. A statement
#                           about us. Nothing raises it today; the member stays so a future
#                           blocked check can be reported honestly rather than as a zero.
#   insufficient_evidence — the check ran, and THIS document did not give it what it
#                           needed. A statement about the document.
CHECK_STATUS = pg_enum("pass", "partial", "insufficient_evidence", "flagged", "not_run",
                       name="check_status")
MATCH_STATUS = pg_enum("auto", "confirmed", "rejected", name="match_status")
REVIEW_DECISION = pg_enum("accepted", "rejected", "amended", name="review_decision")


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    overall_score: Mapped[float | None] = mapped_column(Float)
    completeness_score: Mapped[float | None] = mapped_column(Float)
    consistency_score: Mapped[float | None] = mapped_column(Float)
    financial_score: Mapped[float | None] = mapped_column(Float)
    rubric_version: Mapped[str | None] = mapped_column(String(60))
    engine_version: Mapped[str | None] = mapped_column(String(60))
    # Frozen at assessment time rather than re-derived from config/rubric.yaml on read.
    # Re-deriving would silently rewrite history the next time the rubric changes, and this
    # record is what the sanction decision was made against. The key is stored
    # alongside the label because tests and callers need to look the profile up, and
    # parsing it back out of `rubric_version` would be fragile.
    rubric_profile: Mapped[str | None] = mapped_column(String(60))
    rubric_profile_label: Mapped[str | None] = mapped_column(String(200))
    rubric_profile_confidence: Mapped[float | None] = mapped_column(Float)
    rubric_provenance: Mapped[str | None] = mapped_column(Text)


class AssessmentCheck(Base, TimestampMixin):
    """One row per check the engine performed — including the ones that passed.

    Findings record what needs acting on. These record what was *examined*, which is a
    different question and the one a reviewer asks when deciding whether they still have to
    read all four hundred pages themselves. Passed checks carry evidence exactly as findings
    do, so "confirmed on page 208" is clickable rather than an assertion.

    Kept out of `findings` on purpose: several places count findings — the queue's
    `finding_count`, the portfolio ranking, the appraisal note — and none of them should
    change because the system started recording its successes.
    """
    __tablename__ = "assessment_checks"
    # Uniqueness makes idempotency a database guarantee rather than a consequence of
    # `_clear` having run first.
    __table_args__ = (
        Index("ix_assessment_checks_dpr", "dpr_id", "ordinal"),
        UniqueConstraint("assessment_id", "check_id", name="uq_check_per_assessment"),
        UniqueConstraint("assessment_id", "ordinal", name="uq_check_ordinal"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id = fk_uuid("assessments.id")
    dpr_id = fk_uuid("dprs.id")
    # The same vocabulary findings use, so a check and the finding it produced group under
    # one heading instead of appearing in two different places in the UI.
    family: Mapped[str] = mapped_column(CATEGORY, nullable=False)
    check_id: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    # The check's inherent importance, constant across outcomes — NOT the graded
    # consequence. `findings.severity` is downgraded for `partial` by SEVERITY_FOR_STATUS;
    # doing that here too would make "9 of 9 critical requirements confirmed" uncountable.
    severity: Mapped[str] = mapped_column(SEVERITY, nullable=False)
    status: Mapped[str] = mapped_column(CHECK_STATUS, nullable=False)
    # 0-1 evidence strength, for checks that produce one. Named apart from the 0-100
    # component scores on `assessments` — two adjacent columns called `score` on different
    # scales get misread.
    evidence_score: Mapped[float | None] = mapped_column(Float)
    # Empty only where there is genuinely nothing to point at — an absent section has no page.
    evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_dpr", "dpr_id", "severity"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    assessment_id = fk_uuid("assessments.id", nullable=True)
    # The checklist row this finding came out of. A finding no check row claims is one the
    # checklist would silently hide — the exact failure the checklist exists to prevent —
    # so this being NULL for any current finding is assertable with a single query.
    # Nullable because findings written before the checklist existed have no row to point at.
    assessment_check_id = fk_uuid("assessment_checks.id", nullable=True)
    dpr_id = fk_uuid("dprs.id")
    severity: Mapped[str] = mapped_column(SEVERITY, nullable=False)
    category: Mapped[str] = mapped_column(CATEGORY, nullable=False)
    status: Mapped[str] = mapped_column(FINDING_STATUS, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    # ARRAY of evidence anchors. Never empty (invariant #1).
    # F4 contradiction findings carry 3; F6 IRR findings carry 2 (claim + evidence).
    evidence: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Float)
    match_status: Mapped[str] = mapped_column(MATCH_STATUS, default="auto", nullable=False)
    score_impact: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class FindingReview(Base, TimestampMixin):
    __tablename__ = "finding_reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    finding_id = fk_uuid("findings.id")
    reviewer_id = fk_uuid("users.id")
    decision: Mapped[str] = mapped_column(REVIEW_DECISION, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Setting(Base):
    """Every configurable threshold in the system. Nothing is hardcoded."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by = fk_uuid("users.id", nullable=True, index=False)
