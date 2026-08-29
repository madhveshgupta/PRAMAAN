"""Phase 1 exit gate: stack runs, both roles authenticate, the sanction gate bites,
the audit trail is immutable, and the job queue claims/completes/reclaims correctly."""
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from api.app.models import AuditEvent, Job, User
from api.app.models.base import utcnow
from api.app.security import RequireRole, decode_token, require_sanction
from tests.conftest import login


# --------------------------------------------------------------- health
def test_health_is_green(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok", body
    assert body["db"] == "ok"
    assert body["storage"] == "ok"


# --------------------------------------------------------------- auth
@pytest.mark.parametrize("email,role", [
    ("applicant@demo.gov.in", "applicant"),
    ("ministry@demo.gov.in", "ministry"),
    ("officer@demo.gov.in", "ministry"),
])
def test_each_seeded_user_logs_in_with_correct_role(client, email, role):
    body = login(client, email)
    assert body["role"] == role
    assert decode_token(body["access_token"])["role"] == role


def test_wrong_password_is_rejected(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "ministry@demo.gov.in", "password": "wrong"})
    assert r.status_code == 401


def test_unknown_email_gives_the_same_error_as_wrong_password(client):
    """Don't leak which addresses exist."""
    a = client.post("/api/v1/auth/login",
                    json={"email": "nobody@demo.gov.in", "password": "x"})
    b = client.post("/api/v1/auth/login",
                    json={"email": "ministry@demo.gov.in", "password": "x"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(client):
    tokens = login(client, "ministry@demo.gov.in")
    r = client.get("/api/v1/auth/me",
                   headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401


# --------------------------------------------------- separation of duties
def test_can_sanction_flag_is_carried_in_the_token(client):
    assert login(client, "ministry@demo.gov.in")["can_sanction"] is True
    assert login(client, "officer@demo.gov.in")["can_sanction"] is False


def test_sanction_gate_refuses_the_appraise_only_ministry_user(db):
    """The gate must reject the request, not merely hide a button."""
    officer = db.query(User).filter_by(email="officer@demo.gov.in").one()
    with pytest.raises(HTTPException) as exc:
        require_sanction(officer)
    assert exc.value.status_code == 403

    js = db.query(User).filter_by(email="ministry@demo.gov.in").one()
    assert require_sanction(js) is js


def test_role_dependency_refuses_the_wrong_role(db):
    applicant = db.query(User).filter_by(email="applicant@demo.gov.in").one()
    with pytest.raises(HTTPException) as exc:
        RequireRole("ministry")(applicant)
    assert exc.value.status_code == 403


# ------------------------------------------------------- audit immutability
def test_audit_events_reject_update_and_delete(db):
    """M4's requirement: enforced by the DATABASE, not by application code.
    Nobody can rewrite the record — Ministry included.

    The guard RAISES rather than silently ignoring the write. A silent no-op leaves the
    caller believing it succeeded, which is the wrong failure mode for a tamper attempt.
    """
    import sqlalchemy.exc

    ev = AuditEvent(action="test.probe", actor_role="ministry", detail={"n": 1})
    db.add(ev)
    db.commit()
    ev_id = ev.id

    with pytest.raises(sqlalchemy.exc.DatabaseError, match="append-only"):
        db.execute(text("UPDATE audit_events SET action = 'tampered' WHERE id = :i"),
                   {"i": ev_id})
    db.rollback()

    with pytest.raises(sqlalchemy.exc.DatabaseError, match="append-only"):
        db.execute(text("DELETE FROM audit_events WHERE id = :i"), {"i": ev_id})
    db.rollback()

    assert db.execute(text("SELECT action FROM audit_events WHERE id = :i"),
                      {"i": ev_id}).scalar() == "test.probe"


def test_deleting_a_dpr_does_not_erase_its_audit_trail(db):
    """The record of a decision must outlive the record it was about. Both CASCADE and
    SET NULL tried to rewrite the trail and were correctly refused; the FK was dropped."""
    from api.app.models import Dpr

    dpr = Dpr(title="audit-survival probe", status="draft")
    db.add(dpr)
    db.flush()
    db.add(AuditEvent(action="probe.decided", actor_role="ministry", dpr_id=dpr.id,
                      detail={"score_at_decision": 61.0}))
    db.commit()
    dpr_id = dpr.id

    db.execute(text("DELETE FROM dprs WHERE id = :i"), {"i": dpr_id})
    db.commit()

    surviving = db.execute(text(
        "SELECT detail FROM audit_events WHERE dpr_id = :i AND action = 'probe.decided'"),
        {"i": dpr_id}).scalar()
    assert surviving is not None, "deleting a DPR erased the record of its decision"
    assert surviving["score_at_decision"] == 61.0


# ---------------------------------------------------- invariant #4 in the schema
def test_finding_status_enum_has_no_fail_member(db):
    """The system never renders 'fail'. Enforced by the type, not by convention."""
    members = db.execute(text(
        "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE t.typname = 'finding_status'")).scalars().all()
    assert set(members) == {"pass", "partial", "insufficient_evidence", "flagged"}
    assert "fail" not in members


# ----------------------------------------------------------------- job queue
def test_queue_claims_runs_and_completes(db):
    from worker import queue
    from worker.run import _handle_noop, run_once

    job = queue.enqueue(db, "noop")
    db.commit()
    job_id = job.id

    assert run_once(db, {"noop": _handle_noop}) is True
    db.expire_all()
    assert db.get(Job, job_id).status == "done"


def test_stale_job_is_reclaimed(db):
    """A worker that dies mid-run must not strand its job forever."""
    from worker import queue

    job = queue.enqueue(db, "noop")
    job.status = "running"
    job.locked_by = "dead-worker:1"
    job.locked_at = utcnow() - timedelta(minutes=30)   # well past STALE_AFTER
    db.commit()
    job_id = job.id

    claimed = queue.claim(db)
    assert claimed is not None and claimed.id == job_id
    assert claimed.locked_by == queue.WORKER_ID
    assert claimed.attempts == 1
    queue.complete(db, claimed)


def test_failed_job_retries_then_parks(db):
    from worker import queue

    job = queue.enqueue(db, "noop")
    job.max_attempts = 2
    db.commit()

    job.attempts = 1
    queue.fail(db, job, "boom")
    assert job.status == "queued", "should retry while attempts remain"

    job.attempts = 2
    queue.fail(db, job, "boom again")
    assert job.status == "failed", "should park after max_attempts"
