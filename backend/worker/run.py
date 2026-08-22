"""The worker process:  python -m worker.run

Polls the jobs table, dispatches by kind, heartbeats during long work, and shuts down
cleanly on SIGINT/SIGTERM so a Ctrl-C does not leave a job locked.
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from api.app.db import SessionLocal
from api.app.models import Job
from worker import queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S")
log = logging.getLogger("pramaan.worker")

POLL_SECONDS = 2.0
_shutdown = False


def _handle_signal(signum, _frame):
    global _shutdown
    log.info("signal %s received — finishing current job then exiting", signum)
    _shutdown = True


Handler = Callable[[Session, Job], None]


def _handle_noop(db: Session, job: Job) -> None:
    """Proves the loop works end to end without needing the rest of the pipeline."""
    log.info("noop job %s handled", job.id)


def _handlers() -> dict[str, Handler]:
    """Imported lazily so a worker still starts when a later phase's deps are absent."""
    table: dict[str, Handler] = {"noop": _handle_noop}
    try:
        from worker.tasks.ingest import handle_ingest
        table["ingest"] = handle_ingest
    except ImportError as exc:            # pragma: no cover - phase-dependent
        log.debug("ingest handler unavailable: %s", exc)
    try:
        from worker.tasks.extract import handle_extract
        table["extract"] = handle_extract
    except ImportError as exc:            # pragma: no cover
        log.debug("extract handler unavailable: %s", exc)
    try:
        from worker.tasks.assess import handle_assess
        table["assess"] = handle_assess
    except ImportError as exc:            # pragma: no cover
        log.debug("assess handler unavailable: %s", exc)
    try:
        from worker.tasks.predict import handle_predict
        table["predict"] = handle_predict
    except ImportError as exc:            # pragma: no cover
        log.debug("predict handler unavailable: %s", exc)
    return table


def run_once(db: Session, handlers: dict[str, Handler]) -> bool:
    """Claim and run at most one job. Returns True if one was handled."""
    job = queue.claim(db)
    if job is None:
        return False

    handler = handlers.get(job.kind)
    if handler is None:
        queue.fail(db, job, f"no handler registered for kind={job.kind!r}")
        return True

    log.info("claimed %s job %s (attempt %s)", job.kind, job.id, job.attempts)
    try:
        handler(db, job)
    except Exception as exc:                       # noqa: BLE001 - worker must not die
        db.rollback()
        log.exception("job %s raised", job.id)
        queue.fail(db, job, f"{type(exc).__name__}: {exc}")
    else:
        queue.complete(db, job)
        log.info("completed %s job %s", job.kind, job.id)
    return True


def main() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    handlers = _handlers()
    log.info("worker %s started — handlers: %s",
             queue.WORKER_ID, ", ".join(sorted(handlers)))

    db = SessionLocal()
    try:
        while not _shutdown:
            try:
                if not run_once(db, handlers):
                    time.sleep(POLL_SECONDS)
            except Exception:                      # noqa: BLE001
                db.rollback()
                log.exception("poll loop error — backing off")
                time.sleep(POLL_SECONDS * 3)
    finally:
        db.close()
    log.info("worker stopped cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
