"""audit events outlive the DPR they describe

Revision ID: 004_audit_survives
Revises: 003_audit_trigger
"""
from collections.abc import Sequence

from alembic import op

revision: str = "004_audit_survives"
down_revision: str | None = "003_audit_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Stop deleting the record of what happened when the thing it happened to is removed.

    `audit_events.dpr_id` was ON DELETE CASCADE, inherited from the generic FK helper used
    across the schema. That is exactly wrong here: deleting a DPR would erase the trail of
    who assessed it, who decided on it and when — the one thing an audit trail exists to
    prevent. It also deadlocked against the append-only trigger, so a DPR could not be
    deleted at all once anything had been audited against it.

    SET NULL keeps the event. Its `detail` JSONB already carries the score, the versions and
    the decision, so the record stays meaningful without the parent row.
    """
    op.execute("ALTER TABLE audit_events DROP CONSTRAINT audit_events_dpr_id_fkey")
    op.execute("ALTER TABLE audit_events ADD CONSTRAINT audit_events_dpr_id_fkey "
               "FOREIGN KEY (dpr_id) REFERENCES dprs(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE audit_events DROP CONSTRAINT audit_events_dpr_id_fkey")
    op.execute("ALTER TABLE audit_events ADD CONSTRAINT audit_events_dpr_id_fkey "
               "FOREIGN KEY (dpr_id) REFERENCES dprs(id) ON DELETE CASCADE")
