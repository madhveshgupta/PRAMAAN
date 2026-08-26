"""audit append-only via trigger, not rule

Revision ID: 003_audit_trigger
Revises: 002_tz_timestamps
"""
from collections.abc import Sequence

from alembic import op

revision: str = "003_audit_trigger"
down_revision: str | None = "002_tz_timestamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the append-only RULEs with a TRIGGER.

    A rule rewrites the query, and Postgres enforces foreign keys using an internal query
    against the referencing table. With DO INSTEAD NOTHING on audit_events, any delete of a
    referenced row failed with "referential integrity query gave unexpected result" — so a
    DPR could not be deleted once anything had been audited against it.

    A trigger raises on a genuine UPDATE or DELETE while leaving the FK machinery alone,
    which is the behaviour actually wanted: immutable to users, while the database can still
    maintain its own integrity.
    """
    op.execute("DROP RULE IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP RULE IF EXISTS audit_events_no_delete ON audit_events")
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_immutable() RETURNS trigger AS $fn$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only: % is not permitted', TG_OP;
        END;
        $fn$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_events_no_change
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_immutable();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_change ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_immutable()")
    op.execute("CREATE RULE audit_events_no_update AS ON UPDATE TO audit_events "
               "DO INSTEAD NOTHING")
    op.execute("CREATE RULE audit_events_no_delete AS ON DELETE TO audit_events "
               "DO INSTEAD NOTHING")
