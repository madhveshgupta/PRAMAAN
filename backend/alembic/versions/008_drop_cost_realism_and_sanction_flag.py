"""drop the cost-realism component and the per-user sanction flag

Revision ID: 008_drop_cost_realism
Revises: 007_risk_integrity

Two removals that both need schema.

1. **Cost realism.** F5 was only ever reported as `not_run`: it needs published Schedule
   of Rates data that was never obtained, and we do not benchmark against invented rates.
   A component that can never be scored is not a component — it is a permanent apology in
   the middle of the score. The column, the enum member, the checklist rows it wrote and
   the `benchmark_rates` reference table it would have read all go.

2. **`users.can_sanction`.** The flag existed to give one seeded account an appraise-only
   mode. With that account gone nothing distinguishes two ministry users, and a permission
   column no row ever varies is a gate that only *looks* enforced. Appraisal and sanction
   remain two distinct acts writing two distinct audit events; both are open to the
   ministry role, which is checked in the route.

Dropping an enum member means rebuilding the type, so the `cost_realism` rows are deleted
first. They carry no evidence and no finding — `not_run` rows never do — so nothing
citable is lost.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_drop_cost_realism"
down_revision: str | None = "007_risk_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WITHOUT = ("completeness", "consistency", "financial", "duplicate", "geo", "risk",
           "data_quality")
WITH = ("completeness", "consistency", "cost_realism", "financial", "duplicate", "geo",
        "risk", "data_quality")


def _rebuild_category(members: tuple[str, ...]) -> None:
    """Postgres cannot drop an enum member, so swap the type under both columns."""
    new = postgresql.ENUM(*members, name="finding_category_new")
    new.create(op.get_bind(), checkfirst=False)
    for table, col in (("findings", "category"), ("assessment_checks", "family")):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE finding_category_new "
                   f"USING {col}::text::finding_category_new")
    op.execute("DROP TYPE finding_category")
    op.execute("ALTER TYPE finding_category_new RENAME TO finding_category")


def upgrade() -> None:
    # Order matters: the rows referencing the member must go before the member does.
    op.execute("DELETE FROM findings WHERE category = 'cost_realism'")
    op.execute("DELETE FROM assessment_checks WHERE family = 'cost_realism'")
    _rebuild_category(WITHOUT)

    op.drop_column("assessments", "cost_realism_score")
    op.drop_table("benchmark_rates")

    # Settings are seeded rows, not schema, but leaving a weight for a component that no
    # longer exists would silently shrink every overall score by a quarter.
    op.execute("DELETE FROM settings WHERE key = 'price_deviation_bands'")
    op.execute("""
        UPDATE settings
           SET value = '{"v": {"completeness": 0.34, "consistency": 0.33,
                               "financial": 0.33}}'::jsonb,
               description = 'Overall quality score weighting across the three scored '
                             'components. Even split is a placeholder — M3 and M4 to agree.'
         WHERE key = 'component_weights'
    """)

    op.drop_column("users", "can_sanction")


def downgrade() -> None:
    # Restores the shape, not the data: the deleted checklist rows and the flag's former
    # per-user values are gone. Re-running `assess` rewrites the checklist.
    op.add_column("users", sa.Column("can_sanction", sa.Boolean(), nullable=False,
                                     server_default=sa.true()))
    op.execute("""
        UPDATE settings
           SET value = '{"v": {"completeness": 0.25, "consistency": 0.25,
                               "cost_realism": 0.25, "financial": 0.25}}'::jsonb
         WHERE key = 'component_weights'
    """)
    op.create_table(
        "benchmark_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_code", sa.String(length=60), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("rate_paise", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_year", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("cost_index", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("assessments", sa.Column("cost_realism_score", sa.Float(), nullable=True))
    _rebuild_category(WITH)
