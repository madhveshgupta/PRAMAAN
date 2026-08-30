"""Phase 3 exit gate — the adversarial suite.

These are the most important tests in the codebase. If the guard leaks, the product's
central claim — that no number reaches a user without a verifiable pointer — is false.
"""
import pytest
from sqlalchemy import select

from api.app.models import Document, ExtractedField, ExtractionRejection
from worker.evidence.canonical import money_values_in, repair_linebreak_numbers, to_paise
from worker.evidence.locate import locate, locate_all
from worker.extractors.verify import Candidate, value_in_span, verify

TRUE_SPAN = "The total project cost is estimated at Rs. 412.50 crore"


@pytest.fixture(scope="module")
def doc():
    from api.app.db import SessionLocal
    db = SessionLocal()
    d = db.scalars(select(Document).where(Document.status == "ready")
                   .order_by(Document.created_at)).first()
    assert d is not None, "run Phase 2 ingestion first"
    yield db, d
    db.close()


# ------------------------------------------------------------ canonicalisation
@pytest.mark.parametrize("text", [
    "Rs. 412.50 crore", "₹412.5 Cr", "41,250 lakh", "412,50,00,000", "INR 412.50 crores",
])
def test_all_indian_money_notations_canonicalise_identically(text):
    assert to_paise(text) == 41_250_000_0000


def test_number_split_across_a_line_break_is_repaired():
    """A genuine value broken by pagination must verify, not read as a mismatch."""
    broken = "cost is Rs. 412.\n50 crore"
    assert to_paise(repair_linebreak_numbers(broken)) == to_paise("Rs. 412.50 crore")


def test_two_amounts_in_one_sentence_are_both_recovered():
    vals = money_values_in("Rs 412.50 crore and Rs 8.60 crore")
    assert to_paise("Rs 412.50 crore") in vals
    assert to_paise("Rs 8.60 crore") in vals


# ------------------------------------------------------------------- locator
def test_locator_anchors_real_text_with_geometry(doc):
    db, d = doc
    r = locate("Rs. 412.50 crore", d.id, db, page_hint=6)
    assert r, r.failure
    assert r.evidence.page in (3, 6)
    assert all(0.0 <= v <= 1.0 for v in r.evidence.bbox)
    assert r.evidence.bbox[2] > r.evidence.bbox[0]


def test_locator_rejects_text_that_is_not_in_the_document(doc):
    db, d = doc
    r = locate("Rs. 999.99 crore", d.id, db, page_hint=6)
    assert not r
    assert r.failure.reason == "span_not_found"


def test_locate_all_returns_every_occurrence(doc):
    """F4 and F6 need multi-anchor findings; one occurrence is not enough."""
    db, d = doc
    hits = locate_all("Rs. 412.50 crore", d.id, db)
    assert len(hits) >= 2, "the headline cost appears in more than one place"


# -------------------------------------------- THE attack: real quote, fake value
def test_real_quote_with_fabricated_value_is_rejected(doc):
    """Invariant #11. The span verifies; the number is invented. A span-only checker
    accepts this, which is exactly why the value check exists."""
    db, d = doc
    v = verify(Candidate("total_project_cost", "500.00", "INR_CRORE",
                         TRUE_SPAN, 6, "money"), d.id, db)
    assert v.rejected
    assert v.reason == "value_not_in_span"


def test_honest_claim_is_accepted(doc):
    db, d = doc
    v = verify(Candidate("total_project_cost", "412.50", "INR_CRORE",
                         TRUE_SPAN, 6, "money"), d.id, db)
    assert v.accepted
    assert v.evidence.page == 6


def test_equivalent_notation_still_verifies(doc):
    """41,250 lakh IS 412.50 crore. Rejecting it would punish honest formatting."""
    db, d = doc
    v = verify(Candidate("total_project_cost", "41250 lakh", "INR_LAKH",
                         TRUE_SPAN, 6, "money"), d.id, db)
    assert v.accepted


def test_single_digit_fabrication_is_caught(doc):
    db, d = doc
    v = verify(Candidate("total_project_cost", "412.60", "INR_CRORE",
                         TRUE_SPAN, 6, "money"), d.id, db)
    assert v.rejected


def test_wholly_invented_quote_is_rejected(doc):
    db, d = doc
    v = verify(Candidate("total_project_cost", "999.99", "INR_CRORE",
                         "The total project cost is estimated at Rs. 999.99 crore",
                         6, "money"), d.id, db)
    assert v.rejected
    assert v.reason == "span_not_found"


def test_ocr_style_corruption_is_rejected_for_a_numeric_field(doc):
    """'4l2.5O' must never fuzzy-match its way to 412.50 — that is how an OCR error
    becomes a confident wrong figure in a financial appraisal."""
    db, d = doc
    v = verify(Candidate("total_project_cost", "4l2.5O", "INR_CRORE",
                         TRUE_SPAN, 6, "money"), d.id, db)
    assert v.rejected


def test_paraphrase_instead_of_a_quote_is_rejected(doc):
    db, d = doc
    v = verify(Candidate("total_project_cost", "412.50", "INR_CRORE",
                         "the cost of this project is about four hundred crore",
                         6, "money"), d.id, db)
    assert v.rejected


def test_value_in_span_unit_awareness():
    """A structured extractor reports scale separately; forgetting it rejects honest values."""
    assert value_in_span("412.50", TRUE_SPAN, "money", "INR_CRORE")
    assert not value_in_span("412.50", TRUE_SPAN, "money", "INR")


# ------------------------------------------------------------- stored output
def test_every_found_field_carries_evidence(doc):
    """Invariant #1, checked against what is actually in the database."""
    db, d = doc
    rows = db.scalars(select(ExtractedField)
                      .where(ExtractedField.dpr_id == d.dpr_id)).all()
    assert rows
    for f in rows:
        if f.status == "found":
            assert f.evidence, f"{f.field_key} stored as found with no evidence"
            for e in f.evidence:
                assert 0.0 <= min(e["bbox"]) and max(e["bbox"]) <= 1.0
                assert e["page"] >= 1


def test_missing_llm_marks_not_extracted_not_not_found(doc):
    """'we failed to read it' and 'the document lacks it' are different claims, and the
    compliance engine scores them differently. Conflating them blames the DPR for our gap."""
    db, d = doc
    om = db.scalar(select(ExtractedField).where(
        ExtractedField.dpr_id == d.dpr_id,
        ExtractedField.field_key == "om_arrangement"))
    assert om is not None
    assert om.status in {"not_extracted", "found", "not_found"}
    from api.app.llm import provider
    if not provider.available():
        assert om.status == "not_extracted"


def test_the_three_contradicting_cost_figures_were_all_extracted(doc):
    """What F4 will cluster in Phase 4."""
    db, d = doc
    rows = db.scalars(select(ExtractedField).where(
        ExtractedField.dpr_id == d.dpr_id,
        ExtractedField.field_key == "money_mention")).all()
    pages = {e["page"] for f in rows for e in f.evidence}
    assert {6, 115} <= pages, f"expected the summary and abstract anchors, got {pages}"
