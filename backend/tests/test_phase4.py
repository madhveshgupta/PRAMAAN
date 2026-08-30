"""Phase 4 exit gate — every planted defect caught, and the clean control left alone.

The false-positive tests matter as much as the detection tests. A tool that cries wolf on
a legitimate difference loses a reviewer's trust in everything else on the page.
"""
import pytest
from sqlalchemy import select

from api.app.models import (Assessment, AssessmentCheck, Document, Dpr,
                            Finding)
from worker.scoring.completeness import _NEG, assess_completeness, classify_document
from worker.scoring.consistency import comparable, qualifier_signature
from worker.scoring.financial import CashFlow, recompute, sanity_check


@pytest.fixture(scope="module")
def db():
    from api.app.db import SessionLocal
    s = SessionLocal()
    yield s
    s.close()


# Named explicitly, and ordered. These used to be `.first()` on an unordered query over
# "%defective%" / "%sound%", which returned whichever row Postgres handed back first — fine
# while the bridge pair was the only corpus, and quietly wrong once four more documents
# joined it. Assessing a DPR UPDATEs its row, which moves it in the heap, so the fixtures
# could change which document they meant between runs without anything failing loudly.
# Every assertion below is about the bridge: 14.2% claimed IRR, the `infrastructure`
# profile, pages 6 and 115.
@pytest.fixture(scope="module")
def bridge(db):
    d = db.scalar(select(Dpr).where(Dpr.title.like("Dhubri Bridge%defective%")))
    assert d is not None, "run the Phase 2/3 pipeline first"
    return d


@pytest.fixture(scope="module")
def control(db):
    d = db.scalar(select(Dpr).where(Dpr.title.like("Dhubri Bridge%sound%")))
    assert d is not None
    return d


def _findings(db, dpr, rule_prefix=None):
    q = select(Finding).where(Finding.dpr_id == dpr.id)
    rows = db.scalars(q).all()
    if rule_prefix:
        rows = [f for f in rows if f.rule_id.startswith(rule_prefix)]
    return rows


# ---------------------------------------------------------------- planted defects
def test_cost_contradiction_found_with_three_anchors(db, bridge):
    """The demo centrepiece: p.4 and p.203 agree, p.87 is stale."""
    hits = _findings(db, bridge, "F4-")
    assert len(hits) == 1, f"expected exactly one contradiction, got {len(hits)}"
    pages = sorted(e["page"] for e in hits[0].evidence)
    assert len(pages) >= 2, "a contradiction needs at least two anchors to be shown"
    for e in hits[0].evidence:
        assert all(0.0 <= v <= 1.0 for v in e["bbox"])
    assert "418.20" in hits[0].message and "412.50" in hits[0].message


def test_irr_claim_is_disproved_from_the_documents_own_table(db, bridge):
    """Two anchors: the claim on p.61, the cash flows that contradict it on p.198."""
    hits = _findings(db, bridge, "F6-IRR-UNSUPPORTED")
    assert len(hits) == 1
    f = hits[0]
    assert f.severity == "critical"
    assert len(f.evidence) == 2, "the IRR finding needs the claim AND the annexure"
    assert "14.2" in f.message


def test_recomputed_irr_is_actually_right(db, bridge):
    """Not asserted — arithmetically true from the generated cash-flow series."""
    doc = db.scalar(select(Document).where(Document.dpr_id == bridge.id))
    r = recompute(db, doc.id)
    assert r.usable
    assert 7.0 < r.computed_irr < 9.0, r.computed_irr
    assert r.cashflow.page_no > 200


def test_missing_om_funding_is_caught(db, bridge):
    """The highest-value check in the rubric. The bridge DPR has no O&M section at all —
    only a glossary line defining the abbreviation, which must not count."""
    hits = [f for f in _findings(db, bridge) if "om_plan" in f.rule_id.lower()]
    assert len(hits) == 1
    assert hits[0].status == "insufficient_evidence"
    assert hits[0].severity == "critical"


def test_negation_downgrades_environmental_clearance(db, bridge):
    """'Clearance is yet to be obtained' must never score PASS."""
    hits = [f for f in _findings(db, bridge) if "ENVIRONMENT" in f.rule_id]
    assert len(hits) == 1
    assert hits[0].status == "partial"
    assert "negation" in hits[0].message.lower()


def test_cost_realism_is_reported_as_blocked_not_scored_as_zero(db, bridge):
    """F5 has no Schedule of Rates data. Scoring it zero would punish the DPR for our
    missing reference data; scoring it 100 would be a lie. It is left unscored."""
    a = db.scalar(select(Assessment).where(Assessment.dpr_id == bridge.id))
    assert a.cost_realism_score is None
    assert not _findings(db, bridge, "F5-")


# --------------------------------------------------------------- the control case
def test_clean_dpr_scores_well_above_the_defective_one(db, bridge, control):
    a = db.scalar(select(Assessment).where(Assessment.dpr_id == bridge.id))
    b = db.scalar(select(Assessment).where(Assessment.dpr_id == control.id))
    assert b.overall_score > 85, f"control scored only {b.overall_score}"
    assert b.overall_score - a.overall_score > 25


def test_clean_dpr_has_no_contradiction_or_irr_finding(db, control):
    assert not _findings(db, control, "F4-")
    assert not _findings(db, control, "F6-IRR")


def test_clean_dpr_om_section_is_recognised(db, control):
    """The control DPR names its O&M funding source explicitly. Flagging it would be a
    false accusation, and false accusations cost more trust than missed findings."""
    hits = [f for f in _findings(db, control) if "om_plan" in f.rule_id.lower()]
    assert not hits, "control DPR's O&M section was wrongly flagged"


def test_no_land_acquisition_required_is_not_read_as_a_negation(db, control):
    """'No private land acquisition is involved' means the requirement is satisfied
    trivially. A blunt \\bno\\b cue used to downgrade it."""
    assert not _NEG.search("No private land acquisition is involved.")
    assert _NEG.search("Environmental clearance is yet to be obtained")


# --------------------------------------------------- false-positive guards (F4)
@pytest.mark.parametrize("a,b,should_compare", [
    ("cost excluding taxes Rs 412.50 crore", "cost including GST Rs 487.20 crore", False),
    ("base cost Rs 412.50 crore", "cost with escalation Rs 441.00 crore", False),
    ("Phase-I cost is Rs 180.00 crore", "the cost is Rs 412.50 crore", False),
    ("state share Rs 82.50 crore", "the cost is Rs 412.50 crore", False),
    ("Rs 412.50 crore including all taxes", "of the scheme is Rs 418.20 crore", True),
])
def test_qualifier_rule_only_compares_like_with_like(a, b, should_compare):
    assert comparable(qualifier_signature(a), qualifier_signature(b)) is should_compare


def test_rounding_does_not_fire_a_contradiction(db, bridge):
    """412 vs 412.5 is 0.12% — under the tolerance. Only 412.5 vs 418.2 (1.36%) fires."""
    from worker.scoring.consistency import find_contradictions
    hits = find_contradictions(db, bridge.id, tolerance_pct=2.0)
    assert not hits, "a 1.36% divergence fired at a 2% tolerance"


# ------------------------------------------------------- financial sanity guard
def test_malformed_cashflow_produces_a_warning_not_a_financial_finding():
    """A garbled table yields a wildly wrong IRR that looks like a real finding. The
    guard must stop before the maths, not after."""
    gap = CashFlow(years=[0, 1, 2, 5, 6], net=[-100, -100, 50, 50, 50],
                   table_id=None, page_no=1)
    assert any("missing year" in p for p in sanity_check(gap))

    flat = CashFlow(years=[0, 1, 2, 3], net=[10, 10, 10, 10], table_id=None, page_no=1)
    assert any("sign change" in p for p in sanity_check(flat))


# ------------------------------------------------------------------- invariants
def test_no_finding_anywhere_has_status_fail(db):
    for f in db.scalars(select(Finding)).all():
        assert f.status != "fail"


def test_every_finding_with_a_locatable_section_carries_an_anchor(db):
    """Invariant #1. Two classes legitimately have nothing to point at: an
    'insufficient_evidence' finding IS that we found nothing, and a document-level finding
    ("this is not a DPR") is about the whole file. Everything else must cite."""
    DOCUMENT_LEVEL = {"F3-PROFILE-UNCERTAIN", "F3-UNFILLED-TEMPLATE"}
    for f in db.scalars(select(Finding)).all():
        if f.status == "insufficient_evidence" or f.rule_id in DOCUMENT_LEVEL:
            continue
        assert f.evidence, f"{f.rule_id} has no evidence anchor"
        for e in f.evidence:
            assert e["page"] >= 1
            assert all(0.0 <= v <= 1.0 for v in e["bbox"])


# ------------------------------------------------ sector awareness (real documents)


def test_infrastructure_dpr_is_classified_correctly(db, bridge):
    doc = db.scalar(select(Document).where(Document.dpr_id == bridge.id))
    assert assess_completeness(db, doc.id).profile == "infrastructure"


def test_a_real_dpr_does_not_score_a_suspicious_perfect_100(db):
    """Loose matching once gave every real DPR a flat 100.0 with zero findings — not
    because they were complete, but because the checks could not fail."""
    for title in ("NHB Fig%", "NHB Mint%"):
        d = db.scalars(select(Dpr).where(Dpr.title.like(title))).first()
        if d is None:
            continue
        a = db.scalar(select(Assessment).where(Assessment.dpr_id == d.id))
        assert a.overall_score < 100.0, f"{title} scored a perfect 100"
        assert _findings(db, d), f"{title} produced no findings at all"


def test_classifier_prefers_absolute_cue_hits_over_ratio():
    """Two unambiguous sector cues is real evidence. A ratio threshold punished profiles
    with long cue lists and pushed genuine matches to `generic`."""
    from worker.scoring.completeness import classify_document

    bridge = ("Construction of a two-lane major bridge across the river. IRC:6 loads have "
              "been adopted. The approach road and carriageway are designed for the "
              "projected traffic. Chainage 0+000 to 1+340.")
    key, conf, warning = classify_document(bridge)
    assert key == "infrastructure", f"classified as {key}"
    assert warning is None


def test_a_blank_template_is_recognised_as_unfilled():
    """A checklist scores structure, and a blank form has perfect structure. Without this
    an unfilled template scores well for containing nothing."""
    from worker.scoring.template_check import judge_cells

    # A blank form: the labels are there, the values are not.
    labels = ["Rate of Interest", "Project Cost", "Means of Finance", "IRR", "NPV", "BCR"]
    blank = [labels[i % len(labels)] if i % 6 == 0 else "" for i in range(300)]
    assert judge_cells(blank).is_template

    # The same form, completed.
    filled = [labels[i % len(labels)] if i % 6 == 0 else f"{i * 3.7:.2f}"
              for i in range(300)]
    assert not judge_cells(filled).is_template

    # Too few cells to judge — say nothing rather than guess.
    assert not judge_cells([""] * 20).is_template


def test_a_tender_document_is_flagged_rather_than_scored():
    """A bid document is not a project report. Scoring one against a DPR rubric produces a
    confident number about the wrong kind of document."""
    from worker.scoring.completeness import classify_document

    tender = ("Seal and Sign of bidder. REQUEST FOR PROPOSAL. The bidder shall submit the "
              "bid document along with earnest money deposit. Bids received after the due "
              "date shall be rejected. The bidder must satisfy the eligibility criteria. "
              "Technical bid and financial bid shall be submitted separately.")
    key, conf, warning = classify_document(tender)
    assert warning is not None
    assert "tender" in warning.lower() or "bid" in warning.lower()


# ---------------------------------------------------------------- the compliance checklist
#
# The checklist exists so a reviewer can see that the twenty things they are NOT being
# warned about were actually examined. That only helps if the two views of the assessment
# agree — a section shown as confirmed while a finding says it is missing would destroy
# the trust the feature exists to build. These tests are that agreement.

def _checks(db, dpr, family=None):
    q = select(AssessmentCheck).where(AssessmentCheck.dpr_id == dpr.id)
    rows = sorted(db.scalars(q).all(), key=lambda c: c.ordinal)
    return [c for c in rows if family is None or c.family == family]


@pytest.mark.parametrize("which", ["bridge", "control"])
def test_every_finding_is_reachable_from_the_checklist(db, bridge, control, which):
    """A finding with no checklist row is one the checklist silently hides — and a reviewer
    trusting the checklist would never learn it existed."""
    dpr = {"bridge": bridge, "control": control}[which]
    orphans = [f.rule_id for f in _findings(db, dpr) if f.assessment_check_id is None]
    assert orphans == [], f"findings with no checklist row: {orphans}"


def test_completeness_checks_and_findings_agree_both_ways(db, bridge, control):
    """pass ⟺ no finding; not pass ⟺ exactly one finding. Either direction failing means
    the two views disagree about the same document."""
    for dpr in (bridge, control):
        for c in _checks(db, dpr, "completeness"):
            linked = [f for f in _findings(db, dpr) if f.assessment_check_id == c.id]
            if c.status == "pass":
                assert not linked, f"{c.check_id} passed but raised {len(linked)} finding(s)"
            else:
                # A finding withheld for lack of an anchor says so on the row instead.
                assert len(linked) == 1 or "withheld" in c.detail, \
                    f"{c.check_id} is {c.status} with {len(linked)} findings"


def test_a_check_and_its_finding_file_under_the_same_heading(db, bridge):
    """Otherwise one fact appears under two different headings in the UI."""
    for f in _findings(db, bridge):
        c = db.get(AssessmentCheck, f.assessment_check_id)
        assert c.family == f.category, f"{f.rule_id}: {c.family} vs {f.category}"


def test_checklist_covers_every_item_of_the_rubric_that_was_applied(db, control):
    """This is what proves the claim "every check the engine ran" — the count must equal
    the profile's own item count, read from the profile frozen on the assessment."""
    a = db.scalar(select(Assessment).where(Assessment.dpr_id == control.id))
    from worker.scoring.completeness import load_rubric
    expected = len(load_rubric()["profiles"][a.rubric_profile]["items"])
    assert len(_checks(db, control, "completeness")) == expected


def test_a_passing_check_still_cites_a_page(db, control):
    """A pass with no page to click is the same black box in a friendlier colour. Rows that
    are legitimately about the whole document are exempt, as findings already are."""
    from worker.scoring.checklist import DOCUMENT_LEVEL
    for c in _checks(db, control):
        if c.status == "pass" and c.check_id not in DOCUMENT_LEVEL:
            assert c.evidence, f"{c.check_id} passed without citing anything"


def test_the_irr_pass_row_shows_both_the_claim_and_the_table(db, control):
    """The mirror of test_irr_claim_is_disproved_from_the_documents_own_table: the
    reconciliation should be inspectable when it SUCCEEDS, not only when it fails."""
    c = next(x for x in _checks(db, control) if x.check_id == "F6-IRR-RECOMPUTED")
    assert c.status == "pass"
    assert len({e["page"] for e in c.evidence}) == 2, "claim and cash-flow table"


def test_cost_realism_says_not_run_and_gives_the_reason(db, control):
    """`not_run` is reserved for a check the engine cannot run for ANY document. It must
    never read as though this DPR were at fault."""
    rows = _checks(db, control, "cost_realism")
    assert len(rows) == 1 and rows[0].status == "not_run"
    assert "Schedule of Rates" in rows[0].detail


def test_no_check_anywhere_has_status_fail(db):
    """Invariant #4, extended to the checklist."""
    assert all(c.status != "fail" for c in db.scalars(select(AssessmentCheck)))


def test_the_clean_control_confirms_far_more_than_it_flags(db, control):
    """The product claim, as a test. If this fails the feature has stopped doing its job."""
    rows = _checks(db, control)
    passed = sum(1 for c in rows if c.status == "pass")
    problems = sum(1 for c in rows if c.status in {"flagged", "partial",
                                                   "insufficient_evidence"})
    assert passed >= 20 and problems == 0


def test_reassessing_does_not_duplicate_the_checklist(db, control):
    """Invariant #12 applied to the checklist. The unique constraint would raise anyway —
    this proves `_clear` removes the old rows rather than the write merely colliding."""
    from types import SimpleNamespace
    from worker.tasks.assess import handle_assess

    doc = db.scalar(select(Document).where(Document.dpr_id == control.id))
    before = len(_checks(db, control))
    handle_assess(db, SimpleNamespace(document_id=doc.id))
    db.expire_all()
    after = _checks(db, control)
    assert len(after) == before
    assert len({c.check_id for c in after}) == len(after), "duplicate check_id"
    assert sorted(c.ordinal for c in after) == list(range(len(after))), "ordinals not dense"
