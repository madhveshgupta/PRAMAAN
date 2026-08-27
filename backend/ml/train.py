"""Train the risk models on the PAIMANA panel:  python -m ml.train

Three things here matter more than the model choice.

**Split by time, never at random** (invariant #9). We have one monthly report, so there is
no month dimension to split on — but every project carries its approval date, and training
on older approvals to predict newer ones is a genuine out-of-time test. It is weaker than
a multi-month panel and is reported as such.

**Outcome-adjacent features are excluded.** Cumulative expenditure and physical progress
are strong predictors and completely unavailable for the thing we actually score: a DPR
for a project that has not started. Including them would produce excellent metrics for a
model that cannot be used.

**Historical rates are computed leave-one-out.** An agency's past-overrun rate that
includes the row being predicted is just the label in disguise.

Metrics are always reported against two baselines. A model that cannot beat "predict no
overrun" should be described that way, not shipped quietly.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("pramaan.train")

PANEL = Path("ml/data/paimana_panel.csv")
ARTIFACTS = Path("ml/artifacts")
REPORTS = Path("ml/reports")

OVERRUN_THRESHOLD_PCT = 5.0     # below this is rounding, not an overrun
CATEGORICAL = ["sector", "ministry", "state"]

# Deliberately absent: expenditure_cr, physical_progress_pct — and now approval_year.
#
# approval_year goes for the same reason as the other two: a DPR describes a project that has
# NOT been approved, so it has no approval year. At inference there was nothing real to pass,
# and the constant that filled the gap became the largest-magnitude SHAP driver in every
# prediction — the model's principal stated reason was a number no document contained.
NUMERIC = ["log_cost", "planned_duration_months", "is_mega",
           "agency_hist_overrun", "sector_hist_overrun", "state_hist_overrun"]


MIN_GROUP_FOR_RATE = 5


def fit_group_rates(train: pd.DataFrame, key: str, flag: str) -> tuple[pd.Series, float]:
    """Historical rates learned from the TRAINING split only.

    Two separate leaks were live here and both produced an AUC of 1.0 — a number that
    should always be read as an alarm rather than a result:

    1. Rates computed across the whole panel let a test row's own label reach its own
       features through its group.
    2. Leave-one-out within a small group is barely disguised label copying: for an agency
       with two projects, the LOO rate for one row IS the other row's label.

    So rates are fitted on training rows only, and groups with fewer than
    MIN_GROUP_FOR_RATE members fall back to the global training rate — a group of two
    tells us almost nothing anyway.
    """
    grp = train.groupby(key, observed=True)[flag]
    rates, counts = grp.mean(), grp.count()
    prior = float(train[flag].mean())
    rates = rates.where(counts >= MIN_GROUP_FOR_RATE, prior)
    return rates, prior


def apply_group_rates(frame: pd.DataFrame, key: str, rates: pd.Series,
                      prior: float) -> pd.Series:
    return frame[key].map(rates).astype(float).fillna(prior)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = d[d["cost_original_cr"] > 0].copy()

    d["overran"] = (d["cost_overrun_pct"] > OVERRUN_THRESHOLD_PCT).astype(int)
    d["delayed"] = (d["time_overrun_months"] > 0).astype(float)

    d["log_cost"] = np.log1p(d["cost_original_cr"])
    d["is_mega"] = (d["cost_original_cr"] >= 1000).astype(int)
    d["approval_year"] = d["approval_mm_yyyy"].str.split("/").str[1].astype(float)

    for c in CATEGORICAL:
        d[c] = d[c].fillna("unknown").astype(str)
    return d


def time_split(d: pd.DataFrame, quantile: float = 0.75):
    """Older approvals train, newer approvals test."""
    cut = d["approval_year"].quantile(quantile)
    return d[d["approval_year"] <= cut], d[d["approval_year"] > cut], cut


def _metrics(y_true, y_prob, y_pred) -> dict:
    from sklearn.metrics import (accuracy_score, brier_score_loss, f1_score,
                                 precision_score, recall_score, roc_auc_score)
    out = {"n": int(len(y_true)), "positive_rate": round(float(np.mean(y_true)), 4),
           "accuracy": round(accuracy_score(y_true, y_pred), 4),
           "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
           "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
           "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
           "brier": round(brier_score_loss(y_true, y_prob), 4)}
    out["auc"] = (round(roc_auc_score(y_true, y_prob), 4)
                  if len(np.unique(y_true)) > 1 else None)
    return out


def train_target(d: pd.DataFrame, target: str, label: str) -> dict:
    import lightgbm as lgb
    from sklearn.metrics import brier_score_loss, roc_auc_score

    d = d.dropna(subset=[target])
    train, test, cut = time_split(d)
    if len(test) < 40 or train[target].nunique() < 2 or test[target].nunique() < 2:
        return {"target": label, "skipped": "insufficient out-of-time data"}

    # Fit history on train, apply to both. Doing this inside the split — never before it —
    # is what keeps the test set genuinely unseen.
    train, test = train.copy(), test.copy()
    for key, col in [("agency", "agency_hist_overrun"),
                     ("sector", "sector_hist_overrun"),
                     ("state", "state_hist_overrun")]:
        rates, prior = fit_group_rates(train, key, target)
        train[col] = apply_group_rates(train, key, rates, prior)
        test[col] = apply_group_rates(test, key, rates, prior)

    feats = CATEGORICAL + NUMERIC
    from sklearn.calibration import CalibratedClassifierCV

    # Stable integer encoding, saved with the model. Training on pandas `category` dtype
    # and then explaining a freshly-built row makes LightGBM reject the input ("train and
    # valid dataset categorical_feature do not match"), which silently dropped SHAP to a
    # zero-filled fallback — a prediction with no reasons, in violation of invariant #6.
    encoders = {c: {v: i for i, v in enumerate(sorted(train[c].astype(str).unique()))}
                for c in CATEGORICAL}
    for frame in (train, test):
        for c in CATEGORICAL:
            frame[c] = frame[c].astype(str).map(encoders[c]).fillna(-1).astype(int)

    base = lgb.LGBMClassifier(
        n_estimators=400, learning_rate=0.05, num_leaves=15, min_child_samples=25,
        subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0, verbose=-1, random_state=42)

    # Calibrated so the number we display means what it says. The product tells an officer
    # "73% probability of overrun"; an uncalibrated score that merely ranks correctly would
    # make that sentence false, and it is a sentence they may put in an appraisal note.
    model = CalibratedClassifierCV(base, method="isotonic", cv=3)
    model.fit(train[feats], train[target])

    prob = model.predict_proba(test[feats])[:, 1]

    # A 0.5 cutoff is meaningless when the base rate is a few per cent: the model never
    # crosses it and F1 comes out at zero for a model that ranks well. We report at the
    # training base rate instead, and say so.
    cutoff = float(train[target].mean())
    pred = (prob >= cutoff).astype(int)
    model_m = _metrics(test[target], prob, pred)
    model_m["decision_threshold"] = round(cutoff, 4)
    model_m["threshold_note"] = ("Reported at the training base rate, not 0.5. With a low "
                                 "base rate a 0.5 cutoff yields no positive predictions "
                                 "even for a well-ranked model.")

    # ---- baseline 1: predict the majority class (usually "no overrun")
    majority = int(train[target].mode()[0])
    base_const = _metrics(test[target], np.full(len(test), train[target].mean()),
                          np.full(len(test), majority))

    # ---- baseline 2: the sector's historical rate
    rate = train.groupby("sector", observed=True)[target].mean()
    sector_prob = test["sector"].map(rate).fillna(train[target].mean()).to_numpy()
    base_sector = _metrics(test[target], sector_prob, (sector_prob >= 0.5).astype(int))

    beats = []
    if model_m["auc"] and base_sector["auc"] and model_m["auc"] > base_sector["auc"] + 0.02:
        beats.append("sector-rate baseline (AUC)")
    if model_m["brier"] < base_const["brier"]:
        beats.append("majority-class baseline (Brier)")

    leak_warning = None
    if model_m["auc"] and model_m["auc"] > 0.97:
        leak_warning = (f"AUC {model_m['auc']} is implausibly high for this problem and "
                        f"should be treated as a leakage alarm, not a result. Do not "
                        f"report it until the feature construction has been re-audited.")

    # Importances come from the underlying LGBM; the calibrator wraps it.
    inner = base.fit(train[feats], train[target], categorical_feature=CATEGORICAL)
    importance = sorted(zip(feats, inner.feature_importances_), key=lambda t: -t[1])[:8]

    return {"target": label, "train_n": len(train), "test_n": len(test),
            "split_on": f"approval_year <= {cut:.0f} trains, later tests",
            "model": model_m, "baseline_majority": base_const,
            "baseline_sector_rate": base_sector,
            "beats_baselines": beats, "leak_warning": leak_warning,
            # Ranking and calibration are different questions and this model answers them
            # differently. For a rare event, always predicting the base rate is
            # well-calibrated by construction, so a Brier score that does not beat it means
            # the per-project probability is not trustworthy as a probability — even while
            # the ordering it induces is genuinely informative. Recorded so the officer is
            # told, rather than left to assume the number means what it looks like.
            "ranks_better_than_base_rate": bool(model_m["auc"] > base_const["auc"]),
            "calibration_beats_base_rate": bool(model_m["brier"] < base_const["brier"]),
            "verdict": ("usable" if len(beats) == 2 else
                        "marginal" if beats else "DOES NOT BEAT BASELINES"),
            "top_features": [(f, int(v)) for f, v in importance],
            "model_obj": model, "inner_obj": inner, "encoders": encoders,
            "features": feats}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(PANEL)
    d = build_features(raw)
    log.info("panel: %s rows, %s usable after feature build", len(raw), len(d))

    results = []
    refused: list[str] = []
    for target, label in [("overran", "cost overrun > 5%"), ("delayed", "schedule delay")]:
        r = train_target(d, target, label)
        results.append(r)
        if "skipped" in r:
            log.info("\n%s: SKIPPED (%s)", label, r["skipped"])
            continue
        m, bs, bm = r["model"], r["baseline_sector_rate"], r["baseline_majority"]
        log.info("\n%s  (train %s / test %s)", label, r["train_n"], r["test_n"])
        log.info("   model            AUC %-7s Brier %-7s F1 %-6s (threshold %.3f)",
                 m["auc"], m["brier"], m["f1"], m["decision_threshold"])
        log.info("                    precision %-6s recall %s", m["precision"], m["recall"])
        log.info("   sector baseline  AUC %-7s Brier %-7s", bs["auc"], bs["brier"])
        log.info("   majority baseline AUC %-6s Brier %-7s", bm["auc"], bm["brier"])
        log.info("   VERDICT: %s", r["verdict"])
        if r.get("leak_warning"):
            # Refuse, do not merely warn. A warning above an unconditional save means the
            # suspect model ships anyway and gets served — the gate was decorative.
            log.error("   ** %s", r["leak_warning"])
            if "--force" not in sys.argv:
                log.error("   REFUSING TO SAVE risk_%s — re-audit feature construction, "
                          "or pass --force if you have and still want the artifact.", target)
                refused.append(target)
                continue

        import joblib
        joblib.dump({"model": r.pop("model_obj"), "features": r["features"],
                     "categorical": CATEGORICAL, "encoders": r.pop("encoders"),
                     "inner": r.pop("inner_obj")},
                    ARTIFACTS / f"risk_{target}.joblib")

    if refused:
        log.error("NOT SAVED: %s — the artifacts on disk are unchanged.",
                  ", ".join(refused))

    card = {"refused_for_leakage": refused,
            "trained_on": "MoSPI PAIMANA Flash Report, June 2026",
            "records_parsed": int(len(raw)), "records_used": int(len(d)),
            "split": "out-of-time by project approval year",
            "excluded_features": ["expenditure_cr", "physical_progress_pct",
                                  "approval_year"],
            "excluded_because": ("outcome-adjacent — unavailable for an unstarted "
                                 "project, which is exactly what a DPR describes"),
            "known_limitations": [
                "Single monthly report, so the out-of-time split uses approval year "
                "rather than report month. A multi-month panel would be stronger.",
                "cost_revised_cr is right-censored: an ongoing project can overrun "
                "further, so cost overrun is a floor, not a final figure.",
                "76% of projects show zero recorded cost overrun, so the cost target is "
                "heavily zero-inflated and schedule delay carries more signal.",
                "MoSPI records project attributes, not DPR text. Risk is predicted from "
                "project structure and sponsor track record, never from prose quality.",
            ],
            "results": results}
    (REPORTS / "model_card.json").write_text(json.dumps(card, indent=2, default=str))
    log.info("\nmodel card -> %s", REPORTS / "model_card.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
