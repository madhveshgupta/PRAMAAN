"""Risk predictions and peer-based outcome ranges.

There is no Monte Carlo here, deliberately. It needed a correlation matrix between cost
heads that we had no empirical basis for — see answers.md Q4 and invariant #13. Outcome
ranges are read off what actually happened to comparable projects, and ``peer_count`` is
always surfaced because a percentile computed from six projects is not the same claim as
one computed from 340.
"""
import uuid

from sqlalchemy import ARRAY, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import Money, TimestampMixin, fk_uuid, uuid_pk


class RiskPrediction(Base, TimestampMixin):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    # Both probabilities are first-class columns. `overrun_probability` used to be stashed
    # inside features_used, which made it unqueryable and easy to miss.
    overrun_probability: Mapped[float | None] = mapped_column(Float)
    delay_probability: Mapped[float | None] = mapped_column(Float)
    # Magnitudes, not probabilities. Left NULL deliberately: nothing in the pipeline
    # computes them, and a column filled with a plausible-looking guess is worse than one
    # that is honestly empty.
    cost_overrun_pct: Mapped[float | None] = mapped_column(Float)
    cost_overrun_ci: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    expected_delay_months: Mapped[float | None] = mapped_column(Float)
    # [{feature, value, shap, direction, plain_english}] — invariant #6.
    # One set per model: a probability explained by a different model's drivers is not an
    # explanation of anything.
    shap_drivers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    delay_drivers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    features_used: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class OutcomeRange(Base, TimestampMixin):
    __tablename__ = "outcome_ranges"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    method: Mapped[str] = mapped_column(String(40), nullable=False)  # reference_class | quantile_regression
    peer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    peer_criteria: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    cost_p50: Mapped[int | None] = mapped_column(Money)
    cost_p80: Mapped[int | None] = mapped_column(Money)
    cost_p95: Mapped[int | None] = mapped_column(Money)
    months_p50: Mapped[float | None] = mapped_column(Float)
    months_p80: Mapped[float | None] = mapped_column(Float)
    months_p95: Mapped[float | None] = mapped_column(Float)
    peer_distribution: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ProjectEmbedding(Base, TimestampMixin):
    """Scope embeddings for F10 duplicate detection.

    Stored as a float array rather than a pgvector column: pgvector is optional in this
    deployment (it is not installed on every dev machine), and at our scale — a few
    thousand projects — cosine similarity in Python is fast enough. Swap to pgvector with
    an ivfflat index if the corpus grows.
    """
    __tablename__ = "project_embeddings"

    id: Mapped[uuid.UUID] = uuid_pk()
    dpr_id = fk_uuid("dprs.id")
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    scope_text: Mapped[str | None] = mapped_column(String(4000))
