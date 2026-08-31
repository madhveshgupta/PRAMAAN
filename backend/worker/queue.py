"""Postgres-backed job queue. This is what replaced Celery + Redis.

The whole mechanism is one UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED).
SKIP LOCKED lets several workers poll concurrently without blocking each other, and the
staleness clause reclaims jobs from a worker that died mid-run.

Two details matter more than they look:

* ``heartbeat`` must be called during long work. A 300-page parse can outlast
  STALE_AFTER, and without a heartbeat the reclaim fires mid-run and a second worker
  starts the same document.
* Reclaim must be *safe*, not merely rare. Handlers are required to be idempotent —
  ingest clears its derived rows before reparsing (invariant #12). The heartbeat lowers
  the probability of a reclaim; idempotency makes one harmless. Both are needed.
"""
from __future__ import annotations

import logging
import os
import socket
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.app.models import Job
from api.app.models.base import utcnow

log = logging.getLogger("pramaan.queue")

STALE_AFTER = timedelta(minutes=10)
HEARTBEAT_EVERY = timedelta(seconds=30)

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

_CLAIM = text("""
UPDATE jobs
   SET status      = 'running',
       locked_by   = :worker,
       locked_at   = now(),
       started_at  = COALESCE(started_at, now()),
       attempts    = attempts + 1
 WHERE id = (
       SELECT id FROM jobs
        WHERE status = 'queued'
           OR (status = 'running' AND locked_at < now() - :stale)
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1)
RETURNING id
""")


def enqueue(db: Session, kind: str, *, dpr_id=None, document_id=None,
            payload: dict | None = None) -> Job:
    job = Job(kind=kind, dpr_id=dpr_id, document_id=document_id, payload=payload or {})
    db.add(job)
    db.flush()
    return job


def claim(db: Session) -> Job | None:
    """Atomically take the oldest available job, or reclaim a stale one."""
    row = db.execute(_CLAIM, {"worker": WORKER_ID, "stale": STALE_AFTER}).first()
    if row is None:
        db.rollback()
        return None
    db.commit()
    # populate_existing: the worker session is long-lived and may already hold a stale
    # copy of this row in its identity map. Without it we hand back pre-claim values.
    return db.get(Job, row[0], populate_existing=True)


def heartbeat(db: Session, job: Job) -> None:
    """Say 'still alive'. Call this at least every HEARTBEAT_EVERY during long work."""
    job.locked_at = utcnow()
    db.commit()


def complete(db: Session, job: Job) -> None:
    job.status = "done"
    job.finished_at = utcnow()
    job.error = None
    db.commit()


def fail(db: Session, job: Job, error: str) -> None:
    """Retry until max_attempts, then park as failed."""
    job.error = error[:4000]
    if job.attempts >= job.max_attempts:
        job.status = "failed"
        job.finished_at = utcnow()
        log.error("job %s (%s) failed permanently after %s attempts: %s",
                  job.id, job.kind, job.attempts, error)
    else:
        job.status = "queued"
        job.locked_by = None
        job.locked_at = None
        log.warning("job %s (%s) attempt %s failed, requeued: %s",
                    job.id, job.kind, job.attempts, error)
    db.commit()


def depth(db: Session) -> dict[str, int]:
    rows = db.execute(text(
        "SELECT status, count(*) FROM jobs GROUP BY status")).all()
    return {status: n for status, n in rows}
