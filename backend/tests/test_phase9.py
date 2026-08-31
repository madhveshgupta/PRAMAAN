"""Phase 9 exit gate — governance, reporting and offline safety.

The access-control tests matter most. A UI that hides the sanction button is presentation;
these assert the route itself refuses.
"""
import uuid

import pytest
from sqlalchemy import select, text

from api.app.models import AuditEvent, Dpr, User
from tests.conftest import login


@pytest.fixture(scope="module")
def dpr_id():
    from api.app.db import SessionLocal
    db = SessionLocal()
    # Pinned rather than "first defective one": assessing a DPR updates its row and moves
    # it in the heap, so an unordered .first() can change which document a run is about.
    d = db.scalar(select(Dpr).where(Dpr.title.like("Dhubri Bridge%defective%")))
    if d is None:
        pytest.skip("pipeline not run")
    out = str(d.id)
    db.close()
    return out


def _auth(client, email):
    return {"Authorization": f"Bearer {login(client, email)['access_token']}"}


# --------------------------------------------------- access control
def test_ministry_may_record_an_appraisal(client, dpr_id):
    """Appraisal and sanction stay two distinct acts even though one role performs both."""
    r = client.post(f"/api/v1/dprs/{dpr_id}/recommendation",
                    params={"recommendation": "recommend_with_conditions",
                            "note": "IRR needs reconciliation"},
                    headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 200


def test_applicant_cannot_record_an_appraisal(client, dpr_id):
    """The route refuses. Hiding the button is not access control."""
    r = client.post(f"/api/v1/dprs/{dpr_id}/recommendation",
                    params={"recommendation": "recommend", "note": "x"},
                    headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 403


def test_ministry_can_sanction(client, dpr_id):
    r = client.post(f"/api/v1/dprs/{dpr_id}/decision",
                    params={"decision": "returned",
                            "note": "Reconcile the cost abstract and resubmit"},
                    headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 200
    assert r.json()["status"] == "returned"


def test_applicant_cannot_reach_the_decision_route(client, dpr_id):
    r = client.post(f"/api/v1/dprs/{dpr_id}/decision",
                    params={"decision": "approved", "note": "x"},
                    headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 403


def test_a_decision_without_a_reason_is_refused(client, dpr_id):
    r = client.post(f"/api/v1/dprs/{dpr_id}/decision",
                    params={"decision": "approved", "note": "   "},
                    headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 400


# ------------------------------------------------------------ audit trail
def test_appraisal_and_sanction_are_separate_audit_events(client, dpr_id, db):
    """Collapsing them would leave the trail unable to answer the only question an
    auditor actually asks: who appraised this, and who approved it."""
    events = client.get("/api/v1/audit", params={"dpr_id": dpr_id},
                        headers=_auth(client, "ministry@demo.gov.in")).json()
    actions = {e["action"] for e in events}
    assert "dpr.appraised" in actions
    assert "dpr.decided" in actions


def test_decision_event_pins_the_score_and_versions(client, dpr_id):
    events = client.get("/api/v1/audit", params={"dpr_id": dpr_id},
                        headers=_auth(client, "ministry@demo.gov.in")).json()
    decided = next(e for e in events if e["action"] == "dpr.decided")
    assert "rubric_version" in decided["detail"]
    assert "score_at_decision" in decided["detail"]


def test_applicant_cannot_read_the_audit_trail(client):
    r = client.get("/api/v1/audit", headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 403


def test_audit_trail_is_immutable_even_for_ministry(db):
    """Enforced by a DB trigger, not by a role check. A Ministry user cannot rewrite the
    record either — which is exactly what makes the record worth having."""
    import sqlalchemy.exc

    ev = AuditEvent(action="phase9.probe", actor_role="ministry", detail={})
    db.add(ev); db.commit()

    with pytest.raises(sqlalchemy.exc.DatabaseError, match="append-only"):
        db.execute(text("UPDATE audit_events SET action='tampered' WHERE id=:i"),
                   {"i": ev.id})
    db.rollback()
    assert db.execute(text("SELECT action FROM audit_events WHERE id=:i"),
                      {"i": ev.id}).scalar() == "phase9.probe"


# ----------------------------------------------------------- the report
def test_appraisal_note_renders_with_a_matching_hash(client, dpr_id):
    r = client.get(f"/api/v1/dprs/{dpr_id}/report.pdf",
                   headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
    digest = r.headers["X-Content-SHA256"]
    assert len(digest) == 64

    import re

    import pymupdf
    with pymupdf.open(stream=r.content, filetype="pdf") as doc:
        text_all = "".join(p.get_text() for p in doc)
    printed = re.search(r"SHA-256:\s*([0-9a-f]{64})", text_all)
    assert printed, "no hash printed on the note"
    assert printed.group(1) == digest, "printed hash does not match the header"


def test_report_cites_pages_for_its_findings(client, dpr_id):
    import pymupdf
    r = client.get(f"/api/v1/dprs/{dpr_id}/report.pdf",
                   headers=_auth(client, "ministry@demo.gov.in"))
    with pymupdf.open(stream=r.content, filetype="pdf") as doc:
        text_all = "".join(p.get_text() for p in doc)
    assert "[p." in text_all, "findings were exported without page citations"
    assert "Sanctioning authority rests with the competent authority" in text_all


def test_exporting_the_report_is_itself_audited(client, dpr_id):
    client.get(f"/api/v1/dprs/{dpr_id}/report.pdf",
               headers=_auth(client, "ministry@demo.gov.in"))
    events = client.get("/api/v1/audit", params={"dpr_id": dpr_id},
                        headers=_auth(client, "ministry@demo.gov.in")).json()
    assert any(e["action"] == "report.exported" for e in events)


# --------------------------------------------------------- offline safety
def test_demo_mode_refuses_to_reach_the_network():
    """A cache miss under DEMO_MODE must fail loudly. Silently calling out is the one
    failure a conference network can turn into a dead demo."""
    from api.app.config import get_settings
    from api.app.llm import provider

    get_settings.cache_clear()
    original = provider.get_settings

    class Fake:
        demo_mode = True
        llm_api_key = ""
        llm_model = "test-model"

    provider.get_settings = lambda: Fake()
    try:
        with pytest.raises(provider.LLMUnavailable) as exc:
            provider.complete("a prompt that was never cached")
        assert "DEMO_MODE" in str(exc.value)
    finally:
        provider.get_settings = original
        get_settings.cache_clear()


def test_llm_usage_is_counted_so_the_cost_question_has_an_answer():
    from api.app.llm import provider
    assert set(provider.USAGE) >= {"calls", "cache_hits", "input_tokens", "output_tokens"}


# ------------------------------------------------------------- portfolio
def test_portfolio_ranks_and_shows_peer_counts(client):
    rows = client.get("/api/v1/portfolio",
                      headers=_auth(client, "ministry@demo.gov.in")).json()
    assert rows
    scored = [r["composite"] for r in rows if r["composite"] is not None]
    assert scored == sorted(scored), "portfolio is not ranked"
    for r in rows:
        if r["p80_cost_cr"] is not None:
            assert r["peer_count"], "a projected cost was shown without its peer count"


def test_applicant_cannot_see_the_portfolio(client):
    r = client.get("/api/v1/portfolio", headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 403


# ------------------------------------- what the submitting organisation may and may not see
#
# The applicant sees everything about their document and nothing about the ministry's
# judgement of them. These assert the server enforces that, because hiding a tab does not:
# the data was one request away, and this project's own rule is that scoping belongs in the
# query, not the interface.

@pytest.mark.parametrize("path", ["risk", "extraction", "report.pdf"])
def test_applicant_is_refused_the_ministrys_own_views(client, dpr_id, path):
    """Risk is a prediction about the applicant's track record, extraction is a reviewer's
    working view, and the appraisal note carries the score. None is theirs."""
    r = client.get(f"/api/v1/dprs/{dpr_id}/{path}",
                   headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 403, f"{path} leaked to the applicant"


@pytest.mark.parametrize("path", ["risk", "extraction", "report.pdf"])
def test_ministry_still_reaches_all_of_them(client, dpr_id, path):
    """The lock must not have been applied with a bucket."""
    r = client.get(f"/api/v1/dprs/{dpr_id}/{path}",
                   headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 200, path


def test_applicant_can_read_their_own_decision_and_its_reason(client, dpr_id):
    """A recorded reason has always been mandatory, but it lived only in the audit trail —
    which is ministry-only. The person the decision is about could not read it anywhere."""
    r = client.get(f"/api/v1/dprs/{dpr_id}/decision",
                   headers=_auth(client, "applicant@demo.gov.in"))
    assert r.status_code == 200
    body = r.json()
    assert "decision" in body and "status" in body
    if body["decision"]:
        assert body["decision"]["reason"], "a decision without its reason is not a decision"


def test_the_decision_carries_no_score(client, dpr_id):
    """The audit record holds `score_at_decision` beside the reason. The reason is theirs;
    the score is not."""
    body = client.get(f"/api/v1/dprs/{dpr_id}/decision",
                      headers=_auth(client, "applicant@demo.gov.in")).text
    for leaked in ("score_at_decision", "rubric_version", "engine_version"):
        assert leaked not in body, leaked


def test_undecided_is_a_state_not_an_error(client, db):
    """Most reports have no decision yet. The screen has to be able to say so, so this
    returns null rather than 404."""
    from api.app.models import AuditEvent, Dpr
    decided = {e.dpr_id for e in db.scalars(
        select(AuditEvent).where(AuditEvent.action == "dpr.decided"))}
    # Ministry-visible rows only. A self-check is invisible to the ministry by design, so
    # picking one would assert a 404 that says nothing about the decision state.
    undecided = next((d for d in db.scalars(select(Dpr).where(~Dpr.is_self_check))
                      if d.id not in decided), None)
    if undecided is None:
        pytest.skip("every sample DPR has been decided")
    r = client.get(f"/api/v1/dprs/{undecided.id}/decision",
                   headers=_auth(client, "ministry@demo.gov.in"))
    assert r.status_code == 200 and r.json()["decision"] is None


def test_a_self_check_never_reaches_the_ministry(client, db):
    """A self-check is a private rehearsal. The applicant UI promises in as many words that
    the ministry does not see it, and the promise has to hold at the API, not just in the
    screens — the enforcement used to live only in the portfolio ranking, which left the
    report list, its assessment, its risk score and its audit trail readable to any
    ministry account.

    404, not 403: confirming that a hidden report exists is itself the leak.
    """
    private = db.scalar(select(Dpr).where(Dpr.is_self_check))
    if private is None:
        pytest.skip("no self-check DPR in the corpus")

    ministry = _auth(client, "ministry@demo.gov.in")
    listed = client.get("/api/v1/dprs", headers=ministry).json()
    assert str(private.id) not in {row["id"] for row in listed}
    assert all(row["is_self_check"] is False for row in listed)

    for path in (f"/api/v1/dprs/{private.id}/status",
                 f"/api/v1/dprs/{private.id}/assessment",
                 f"/api/v1/dprs/{private.id}/risk",
                 f"/api/v1/dprs/{private.id}/decision",
                 f"/api/v1/dprs/{private.id}/report.pdf",
                 f"/api/v1/audit?dpr_id={private.id}"):
        assert client.get(path, headers=ministry).status_code == 404, path

    # Nor may the ministry act on one — appraising or sanctioning a rehearsal is worse
    # than reading it.
    assert client.post(f"/api/v1/dprs/{private.id}/recommendation?recommendation=recommend",
                       headers=ministry).status_code == 404
    assert client.post(f"/api/v1/dprs/{private.id}/decision?decision=approved&note=x",
                       headers=ministry).status_code == 404

    # The unfiltered trail must not mention it either.
    trail = client.get("/api/v1/audit", headers=ministry).json()
    assert str(private.id) not in {e["dpr_id"] for e in trail if e["dpr_id"]}


def test_the_owning_applicant_still_sees_their_own_self_check(client, db):
    """The rule hides a rehearsal from the ministry, not from the person rehearsing."""
    private = db.scalar(select(Dpr).where(Dpr.is_self_check))
    if private is None:
        pytest.skip("no self-check DPR in the corpus")
    owner = db.scalar(select(User).where(User.organisation_id == private.organisation_id,
                                         User.role == "applicant"))
    if owner is None:
        pytest.skip("no applicant in the submitting organisation")

    headers = _auth(client, owner.email)
    listed = client.get("/api/v1/dprs", headers=headers).json()
    assert str(private.id) in {row["id"] for row in listed}
    assert client.get(f"/api/v1/dprs/{private.id}/status",
                      headers=headers).status_code == 200
