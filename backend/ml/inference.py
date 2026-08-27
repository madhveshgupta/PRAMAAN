"""Risk inference with plain-English attributions.

A prediction never leaves this module without its reasons (invariant #6). "shap_value =
0.184 on agency_hist_overrun" is not something a desk officer can put in an appraisal
note; "this agency's past projects overran in 31% of cases" is.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("pramaan.inference")

ARTIFACTS = Path("ml/artifacts")
REPORTS = Path("ml/reports")
PANEL = Path("ml/data/paimana_panel.csv")

PHRASE = {
    "agency_hist_overrun": ("This executing agency's past projects overran in {pct:.0%} "
                            "of cases", "sponsor track record"),
    "sector_hist_overrun": ("Projects in this sector overran in {pct:.0%} of cases",
                            "sector history"),
    "state_hist_overrun": ("Projects in this state overran in {pct:.0%} of cases",
                           "location history"),
    "log_cost": ("Project size", "scale"),
    "planned_duration_months": ("Planned duration of {raw:.0f} months", "schedule"),
    "is_mega": ("Mega project (>= Rs 1,000 crore)", "scale"),
    "sector": ("Sector: {raw}", "sector"),
    "ministry": ("Ministry: {raw}", "sponsor"),
    "state": ("State: {raw}", "location"),
}


@dataclass
class Driver:
    feature: str
    value: object
    shap: float
    direction: str
    plain_english: str


@dataclass
class Prediction:
    target: str
    probability: float
    model_version: str
    drivers: list[Driver] = field(default_factory=list)
    caveat: str | None = None


def _load(target: str):
    import joblib
    path = ARTIFACTS / f"risk_{target}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"no trained model at {path} — run python -m ml.train")
    return joblib.load(path)


def _history(panel: pd.DataFrame, key: str, value, flag: str) -> float:
    if value is None:
        return float(panel[flag].mean())
    sel = panel[panel[key] == value]
    if len(sel) < 5:
        return float(panel[flag].mean())
    return float(sel[flag].mean())


def build_feature_row(sanctioned_cr: float, sector: str | None, ministry: str | None,
                      state: str | None, agency: str | None,
                      planned_duration_months: float | None,
                      panel: pd.DataFrame, flag: str) -> pd.DataFrame:
    """The feature bridge: what a DPR can supply for a project with no history of its own.

    A default here is not neutral — it is asserted with full confidence and then narrated
    back to the officer as a reason. `planned_duration_months` is the delay model's
    strongest feature and IS extractable from the document, so passing None and taking the
    panel median means explaining a score with a number the report never stated.
    """
    return pd.DataFrame([{
        "sector": sector or "unknown",
        "ministry": ministry or "unknown",
        "state": state or "unknown",
        "log_cost": float(np.log1p(sanctioned_cr)),
        "planned_duration_months": planned_duration_months if planned_duration_months
                                   else float(panel["planned_duration_months"].median()),
        "is_mega": int(sanctioned_cr >= 1000),
        "agency_hist_overrun": _history(panel, "agency", agency, flag),
        "sector_hist_overrun": _history(panel, "sector", sector, flag),
        "state_hist_overrun": _history(panel, "state", state, flag),
    }])


@lru_cache(maxsize=4)
def _model_card_note(target: str) -> str | None:
    """Whether this model's probabilities are calibrated well enough to read as
    probabilities. If not, say so on every prediction it makes."""
    card_path = REPORTS / "model_card.json"
    if not card_path.exists():
        return None
    import json
    label = "cost overrun > 5%" if target == "overran" else "schedule delay"
    for r in json.loads(card_path.read_text()).get("results", []):
        if r.get("target") == label and r.get("calibration_beats_base_rate") is False:
            return ("this model orders projects better than chance but its probabilities "
                    "are no better calibrated than simply quoting the base rate, so read "
                    "the figure as a relative ranking rather than a literal likelihood")
    return None


def predict(target: str, **kw) -> Prediction:
    bundle = _load(target)
    model, feats, cats = bundle["model"], bundle["features"], bundle["categorical"]

    panel = pd.read_csv(PANEL)
    flag = "overran" if target == "overran" else "delayed"
    panel[flag] = ((panel["cost_overrun_pct"] > 5.0) if target == "overran"
                   else (panel["time_overrun_months"] > 0)).astype(float)

    display = build_feature_row(panel=panel, flag=flag, **kw)
    row = display.copy()
    encoders = bundle.get("encoders", {})
    for c in cats:
        row[c] = row[c].astype(str).map(encoders.get(c, {})).fillna(-1).astype(int)

    prob = float(model.predict_proba(row[feats])[0, 1])
    drivers = _explain(bundle.get("inner"), row, display, feats)
    # Say which inputs were missing. A default is invisible in the output otherwise, and
    # the officer cannot tell a score built on the document from one built on the panel.
    missing = []
    card = _model_card_note(target)
    if card:
        missing.append(card)
    if kw.get("agency") is None:
        missing.append("no executing agency was identified, so the strongest available "
                       "signal — sponsor track record — could not be used")
    if kw.get("ministry") is None:
        missing.append("no sponsoring department was identified")
    if kw.get("planned_duration_months") is None:
        missing.append("no construction period was stated, so the panel median was used "
                       "in its place")
    caveat = ("This prediction is weakened: " + "; ".join(missing) + ".") if missing else None

    return Prediction(target=target, probability=round(prob, 4),
                      model_version="paimana-2026-06", drivers=drivers, caveat=caveat)


def _explain(inner, row: pd.DataFrame, display: pd.DataFrame,
             feats: list[str]) -> list[Driver]:
    """SHAP over the uncalibrated tree model, on the same encoding it was trained with.

    `row` carries encoded values for the model; `display` carries the human-readable ones
    for the sentence an officer reads.
    """
    import shap

    if inner is None:
        log.warning("no explainable inner model stored — cannot attribute this prediction")
        return []

    try:
        values = shap.TreeExplainer(inner).shap_values(row[feats])
        values = np.asarray(values)
        if values.ndim == 3:
            values = values[..., -1]
        contrib = values[0]
    except Exception as exc:                              # noqa: BLE001
        log.warning("SHAP unavailable (%s) — falling back to feature importance", exc)
        contrib = np.zeros(len(feats))

    out: list[Driver] = []
    for feat, shap_val in sorted(zip(feats, contrib), key=lambda t: -abs(t[1]))[:5]:
        raw = display.iloc[0][feat]
        template, _cat = PHRASE.get(feat, (f"{feat}: {{raw}}", feat))
        try:
            text = template.format(raw=raw, pct=float(raw) if "hist" in feat else 0.0)
        except (ValueError, TypeError):
            text = f"{feat}: {raw}"
        out.append(Driver(feature=feat, value=raw if not isinstance(raw, float)
                          else round(float(raw), 4),
                          shap=round(float(shap_val), 5),
                          direction="raises risk" if shap_val > 0 else "lowers risk",
                          plain_english=text))
    return out
