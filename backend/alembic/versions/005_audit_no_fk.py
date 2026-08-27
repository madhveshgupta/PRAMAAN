"""audit_events.dpr_id is a plain reference, not a foreign key

Revision ID: 005_audit_no_fk
Revises: 004_audit_survives
"""
from collections.abc import Sequence

from alembic import op

revision: str = "005_audit_no_fk"
down_revision: str | None = "004_audit_survives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the FK from audit_events to dprs.

    Two previous attempts deadlocked against the append-only trigger, and that is the
    signal rather than an inconvenience:

      * ON DELETE CASCADE wanted to DELETE audit rows — refused, correctly.
      * ON DELETE SET NULL wanted to UPDATE them — also refused, also correctly.

    Both were asking the audit trail to change because something else changed. An audit
    trail is a record of what happened; it must not be rewritten as a side effect of what
    happens later to the things it describes. Standard practice for audit logs is to
    denormalise for exactly this reason.

    `dpr_id` stays as a plain UUID for lookups, and `detail` already carries the score,
    versions and decision, so an event remains readable even if its DPR is gone. The price
    is that a dangling dpr_id is possible — which is the correct trade: a pointer to a
    deleted record is honest, and silently deleting the record of a decision is not.
    """
    op.execute("ALTER TABLE audit_events DROP CONSTRAINT IF EXISTS audit_events_dpr_id_fkey")


def downgrade() -> None:
    op.execute("ALTER TABLE audit_events ADD CONSTRAINT audit_events_dpr_id_fkey "
               "FOREIGN KEY (dpr_id) REFERENCES dprs(id) ON DELETE SET NULL")
