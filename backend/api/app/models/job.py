"""The Postgres-backed job queue.

This replaces Celery + Redis. Jobs are claimed with SELECT ... FOR UPDATE SKIP LOCKED, so
several workers can run concurrently without stepping on each other, and a stale lock is
reclaimed from a worker that died mid-run.

Two traps that this table's design has to survive, both found during review:
  * A 300-page parse can outlast the stale window, so the worker heartbeats `locked_at`.
  * Reclaiming a job must not duplicate work — ingest clears its derived rows before
    reparsing (invariant #12).
"""
import uuid
from datetime import datetime

from sqlalchemy import Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.app.db import Base
from api.app.models.base import TZDateTime, TimestampMixin, fk_uuid, pg_enum, uuid_pk

JOB_KIND = pg_enum("noop", "ingest", "extract", "assess", "predict", name="job_kind")
JOB_STATUS = pg_enum("queued", "running", "done", "failed", name="job_status")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(JOB_KIND, nullable=False)
    dpr_id = fk_uuid("dprs.id", nullable=True)
    document_id = fk_uuid("documents.id", nullable=True)
    status: Mapped[str] = mapped_column(JOB_STATUS, default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(120))
    locked_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime)
