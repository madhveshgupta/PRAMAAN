"""separate delay drivers, promote overrun probability, and stop concurrent ingest

Revision ID: 007_risk_integrity
Revises: 006_assessment_checks
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_risk_integrity"
down_revision: str | None = "006_assessment_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Two unrelated integrity fixes that both need schema.

    1. A prediction stored one set of SHAP drivers and printed it under both probabilities,
       so the delay figure was explained by the cost model's reasons. Each model now keeps
       its own. `overrun_probability` moves out of the features_used JSON into a column.
    2. Two workers could hold ingest jobs for the same document at once; both cleared the
       derived rows and both inserted page 1..n, so one lost on `uq_doc_page` and stamped an
       IntegrityError over a document the winner had already taken to `ready`. That stale
       error is cleared below; the overlap itself is prevented in `handle_ingest` with a
       Postgres advisory lock, not with a unique index on queued jobs — a *queued* retry is
       legitimate and invariant #12 depends on it, so only concurrent execution is barred.
    """
    op.add_column("risk_predictions",
                  sa.Column("overrun_probability", sa.Float(), nullable=True))
    op.add_column("risk_predictions",
                  sa.Column("delay_drivers", postgresql.JSONB(astext_type=sa.Text()),
                            server_default="[]", nullable=False))
    # Carry forward what is already stored, so existing rows keep their value.
    op.execute("""
        UPDATE risk_predictions
           SET overrun_probability = (features_used->>'overrun_probability')::float
         WHERE features_used ? 'overrun_probability'
    """)

    # A document that reached `ready` is not carrying a fatal error, whatever a losing
    # worker wrote afterwards.
    op.execute("UPDATE documents SET error = NULL WHERE status = 'ready'")


def downgrade() -> None:
    op.drop_column("risk_predictions", "delay_drivers")
    op.drop_column("risk_predictions", "overrun_probability")
