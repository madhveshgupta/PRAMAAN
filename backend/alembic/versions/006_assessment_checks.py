"""compliance checklist: every check the engine ran, pass or fail

Revision ID: 006_assessment_checks
Revises: 005_audit_no_fk
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_assessment_checks"
down_revision: str | None = "005_audit_no_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A new type rather than a new member on `finding_status`. A finding is an observation
# about the document and an observation cannot be "not run"; a check can. Widening the
# findings enum would weaken the DB-level guarantee invariant #4 leans on.
CHECK_STATUS = postgresql.ENUM("pass", "partial", "insufficient_evidence", "flagged",
                               "not_run", name="check_status", create_type=False)
# Reused, not redefined — a check and the finding it produced must group under the same
# heading, so they share one vocabulary.
CATEGORY = postgresql.ENUM(name="finding_category", create_type=False)
SEVERITY = postgresql.ENUM(name="finding_severity", create_type=False)


def upgrade() -> None:
    """Record the checks that passed, not only the ones that failed.

    The engine ran roughly two dozen checks per DPR and persisted only the failures, so a
    reviewer could see three warnings with no way to tell whether the other twenty things
    were checked and confirmed or simply never looked at. The rational response to that is
    to read the whole document anyway, which defeats the tool.
    """
    CHECK_STATUS.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assessment_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Denormalised so `_clear` can wipe a DPR's derived rows by dpr_id exactly as it
        # already does for findings (invariant #12).
        sa.Column("dpr_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family", CATEGORY, nullable=False),
        sa.Column("check_id", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("severity", SEVERITY, nullable=False),
        sa.Column("status", CHECK_STATUS, nullable=False),
        sa.Column("evidence_score", sa.Float(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()),
                  server_default="[]", nullable=False),
        sa.Column("detail", sa.Text(), server_default="", nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dpr_id"], ["dprs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Re-running assess cannot double-write the checklist even if _clear is skipped:
        # idempotency enforced by the database rather than by hope.
        sa.UniqueConstraint("assessment_id", "check_id", name="uq_check_per_assessment"),
        sa.UniqueConstraint("assessment_id", "ordinal", name="uq_check_ordinal"),
    )
    op.create_index(op.f("ix_assessment_checks_assessment_id"),
                    "assessment_checks", ["assessment_id"])
    op.create_index(op.f("ix_assessment_checks_dpr_id"), "assessment_checks", ["dpr_id"])
    op.create_index("ix_assessment_checks_dpr", "assessment_checks", ["dpr_id", "ordinal"])

    # A finding no check row claims is one the checklist silently hides. A real FK makes
    # "every finding is reachable from the checklist" a single query rather than a hope.
    op.add_column("findings",
                  sa.Column("assessment_check_id", postgresql.UUID(as_uuid=True),
                            nullable=True))
    op.create_foreign_key("findings_assessment_check_id_fkey", "findings",
                          "assessment_checks", ["assessment_check_id"], ["id"],
                          ondelete="CASCADE")
    op.create_index(op.f("ix_findings_assessment_check_id"), "findings",
                    ["assessment_check_id"])

    # Frozen at assessment time. Re-deriving these from config/rubric.yaml months later
    # would silently rewrite the record of which checklist was actually applied — and that
    # record is what a sanctioning officer's decision was made against.
    op.add_column("assessments", sa.Column("rubric_profile", sa.String(60), nullable=True))
    op.add_column("assessments",
                  sa.Column("rubric_profile_label", sa.String(200), nullable=True))
    op.add_column("assessments",
                  sa.Column("rubric_profile_confidence", sa.Float(), nullable=True))
    # Text, not String: provenance lines in rubric.yaml run past 200 characters.
    op.add_column("assessments", sa.Column("rubric_provenance", sa.Text(), nullable=True))


def downgrade() -> None:
    for col in ("rubric_provenance", "rubric_profile_confidence",
                "rubric_profile_label", "rubric_profile"):
        op.drop_column("assessments", col)
    op.drop_index(op.f("ix_findings_assessment_check_id"), table_name="findings")
    op.drop_constraint("findings_assessment_check_id_fkey", "findings", type_="foreignkey")
    op.drop_column("findings", "assessment_check_id")
    op.drop_table("assessment_checks")
    # drop_table leaves the enum type behind.
    CHECK_STATUS.drop(op.get_bind(), checkfirst=True)
