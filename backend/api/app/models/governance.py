"""Audit trail and the retraining feedback queue.

``audit_events`` is append-only, and that is enforced by database rules rather than by
application logic — see the rules created in migration 001. Nobody can alter the record,
Ministry included, which is exactly what makes it worth having.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import TimestampMixin, fk_uuid, uuid_pk


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_id = fk_uuid("users.id", nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40))
    # Deliberately NOT a foreign key. The record of what happened must not be rewritten
    # or removed because the thing it describes was later deleted — and both CASCADE and
    # SET NULL try to do exactly that, which the append-only trigger correctly refuses.
    # `detail` carries the score, versions and decision, so an event stays readable on its
    # own. See migration 005.
    dpr_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)


class TrainingFeedback(Base, TimestampMixin):
    __tablename__ = "training_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    finding_id = fk_uuid("findings.id")
    rule_id: Mapped[str] = mapped_column(String(120), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
