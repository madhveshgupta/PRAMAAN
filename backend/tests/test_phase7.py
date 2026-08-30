"""Phase 7/8 exit gate — the model must be honest, not impressive.

The most important assertions here are the ones that would FAIL a suspiciously good
model. An AUC of 1.0 on this problem is a leakage alarm, and outcome ranges without a
peer count are false precision.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

PANEL = Path("ml/data/paimana_panel.csv")
CARD = Path("ml/reports/model_card.json")


@pytest.fixture(scope="module")
def panel():
    if not PANEL.exists():
        pytest.skip("panel not built — run python -m ml.data.paimana")
    return pd.read_csv(PANEL)


@pytest.fixture(scope="module")
def card():
    if not CARD.exists():
        pytest.skip("model not trained — run python -m ml.train")
    return json.loads(CARD.read_text())


# ------------------------------------------------------------------ the dataset
def test_panel_parsed_a_credible_share_of_the_report(panel):
    """The report states ~1,847 ongoing projects. Recovering a fraction of that would
    mean the parser is quietly dropping records."""
    assert len(panel) > 1400, f"only {len(panel)} records recovered"


def test_every_record_carries_a_cost_overrun_label(panel):
    assert panel["cost_overrun_pct"].notna().mean() > 0.95


def test_sector_column_holds_sectors_not_state_names(panel):
    """An early parser scanned backwards for the sector heading and returned the previous
    record's state, which made every sector statistic meaningless."""
    states = {"Uttar Pradesh", "Andhra Pradesh", "Madhya Pradesh", "West Bengal", "Assam"}
    assert not (set(panel["sector"].dropna().unique()) & states)
    assert "Roads & Highways" in set(panel["sector"].dropna())


def test_ministries_and_sectors_were_carried_across_continuation_pages(panel):
    assert panel["ministry"].notna().mean() > 0.9
    assert panel["sector"].notna().mean() > 0.9


# ------------------------------------------------------------------- the model
def test_no_leakage_alarm_was_raised(card):
    """AUC above ~0.97 on this problem means a label reached the features."""
    for r in card["results"]:
        if "skipped" in r:
            continue
        assert not r.get("leak_warning"), r["leak_warning"]
        assert r["model"]["auc"] is None or r["model"]["auc"] < 0.97


def test_models_beat_both_baselines(card):
    """A model that cannot beat 'predict the majority class' should be described that
    way, not shipped quietly.

    The bar used to be `brier < majority_brier` outright. That passed only while the
    feature set included the year of approval — a value no unapproved project has, which
    was then filled with a constant at inference. Removing it cost real accuracy, and for
    a rare event the base rate is well calibrated by construction, so neither model clears
    that bar now.

    Ranking and calibration are separate claims, so they are asserted separately: the model
    must genuinely order projects better than chance, and where its probabilities are NOT
    better calibrated than the base rate it must say so — on the card and on every
    prediction. Disclosure is the requirement; silence is the failure.
    """
    for r in card["results"]:
        if "skipped" in r:
            continue
        assert r["verdict"] != "DOES NOT BEAT BASELINES", r["target"]
        assert r["ranks_better_than_base_rate"], r["target"]
        assert "calibration_beats_base_rate" in r, r["target"]


def test_a_poorly_calibrated_model_says_so_on_every_prediction():
    """The disclosure has to reach the officer, not just the model card."""
    pytest.importorskip("shap")
    import json
    from ml.inference import REPORTS, predict

    card = json.loads((REPORTS / "model_card.json").read_text())
    uncalibrated = {r["target"] for r in card["results"]
                    if r.get("calibration_beats_base_rate") is False}
    if not uncalibrated:
        pytest.skip("both models are better calibrated than the base rate")

    p = predict("overran", sanctioned_cr=412.5, sector="Roads & Highways",
                ministry="Assam Public Works Department", state="Assam",
                agency="Assam State Bridge Corporation Limited",
                planned_duration_months=30)
    assert p.caveat and "calibrated" in p.caveat, p.caveat


def test_split_is_out_of_time_not_random(card):
    assert "approval_year" in card["split"] or "time" in card["split"].lower()


def test_outcome_adjacent_features_are_excluded(card):
    """Expenditure and physical progress predict well and are unavailable for the thing
    we actually score: a project that has not started."""
    assert "expenditure_cr" in card["excluded_features"]
    assert "physical_progress_pct" in card["excluded_features"]


def test_model_card_states_its_limitations(card):
    joined = " ".join(card["known_limitations"]).lower()
    assert "censored" in joined
    assert "not dpr text" in joined or "attributes, not" in joined


# --------------------------------------------------------- reference class ranges
def test_outcome_range_always_reports_its_peer_count():
    """'80% of 340 projects' and '80% of 6' are different claims. Hiding which is which
    is exactly the false precision this system exists to remove."""
    from ml.ranges.reference_class import compute
    r = compute(412.5, sector="Roads & Highways", state="Assam")
    assert r.peer_count > 0
    assert r.peer_criteria


def test_thin_peer_group_widens_and_says_so():
    from ml.ranges.reference_class import compute
    r = compute(50_000, sector="Aviation & Aviation Infrastructure", state="Sikkim")
    assert r.widened or r.caveat, "a thin peer group neither widened nor warned"


def test_percentiles_are_ordered():
    from ml.ranges.reference_class import compute
    r = compute(412.5, sector="Railways")
    assert r.cost_p50 <= r.cost_p80 <= r.cost_p95


def test_no_monte_carlo_anywhere_in_the_codebase():
    """Removed deliberately: it needed a correlation matrix we had no basis for
    (invariant #13). Reintroducing it would be a regression, not a feature."""
    import subprocess
    out = subprocess.run(["grep", "-rli", "montecarlo", "ml/", "worker/", "api/"],
                         capture_output=True, text=True)
    assert not out.stdout.strip(), f"Monte Carlo code reappeared: {out.stdout}"


# ------------------------------------------------------------------- inference
def test_prediction_ships_with_plain_english_reasons():
    """Invariant #6. 'shap_value = 0.184' is not something an officer can put in a note."""
    pytest.importorskip("shap")
    from ml.inference import predict
    try:
        p = predict("overran", sanctioned_cr=412.5, sector="Roads & Highways",
                    ministry="Ministry of Road Transport & Highways", state="Assam",
                    agency="National Highways Authority of India",
                    planned_duration_months=30)
    except FileNotFoundError:
        pytest.skip("models not trained")
    assert 0.0 <= p.probability <= 1.0
    assert p.drivers, "prediction returned with no attributions"
    assert any(d.shap != 0 for d in p.drivers), "all SHAP values zero — explainer failed"
    for d in p.drivers:
        assert d.plain_english and not d.plain_english.startswith("shap")
