"""Prediction stage: risk probabilities and peer-based outcome ranges.

Everything here is post-MVP by design. A dataset problem must not be able to take down the
demo, so if the models are missing or the panel is unavailable this stage logs and exits
rather than failing the DPR.
"""
from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.app.models import (Dpr, ExtractedField, Job, OutcomeRange, RiskPrediction,
                            Sector)

log = logging.getLogger("pramaan.predict")

MODEL_VERSION = "paimana-2026-06"


def _sanctioned_cr(db: Session, dpr_id) -> float | None:
    """Largest credible 'total project cost' mention, in Rs crore."""
    rows = db.scalars(select(ExtractedField).where(
        ExtractedField.dpr_id == dpr_id,
        ExtractedField.field_key == "money_mention",
        ExtractedField.status == "found")).all()
    values = []
    for r in rows:
        if r.value_numeric is None:
            continue
        v = float(r.value_numeric)
        if r.unit == "INR_LAKH":
            v /= 100.0
        elif r.unit == "INR":
            v /= 10_000_000.0
        values.append(v)
    return max(values) if values else None


def _prose_field(db: Session, dpr_id, key: str) -> str | None:
    """Most recent successfully extracted text value for a field, or None."""
    row = db.scalars(select(ExtractedField)
                     .where(ExtractedField.dpr_id == dpr_id,
                            ExtractedField.field_key == key,
                            ExtractedField.status == "found")
                     .order_by(ExtractedField.created_at.desc())).first()
    return (row.value_text or None) if row else None


def _planned_months(db: Session, dpr_id) -> float | None:
    """The stated construction period, in months.

    Taken from the document rather than defaulted. This is the delay model's single
    strongest feature, and it was being extracted successfully and then discarded in favour
    of the panel median — so every DPR was scored, and explained, on a duration none of them
    stated. The smallest credible value wins: a report quotes its headline period alongside
    longer figures for defect-liability and O&M, and the headline is what was asked for.
    """
    rows = db.scalars(select(ExtractedField).where(
        ExtractedField.dpr_id == dpr_id,
        ExtractedField.field_key == "construction_months",
        ExtractedField.status == "found")).all()
    months = [float(r.value_numeric) for r in rows
              if r.value_numeric is not None and 3 <= float(r.value_numeric) <= 180]
    return min(months) if months else None


def handle_predict(db: Session, job: Job) -> None:
    dpr = db.get(Dpr, job.dpr_id)
    if dpr is None:
        raise ValueError("dpr not found")

    sanctioned = _sanctioned_cr(db, dpr.id)
    if sanctioned is None:
        log.info("no cost figure extracted for dpr %s — risk prediction skipped", dpr.id)
        return

    sector = None
    if dpr.sector_id:
        s = db.get(Sector, dpr.sector_id)
        sector = s.name if s else None

    db.execute(delete(RiskPrediction).where(RiskPrediction.dpr_id == dpr.id))
    db.execute(delete(OutcomeRange).where(OutcomeRange.dpr_id == dpr.id))

    # ---- risk probabilities ---------------------------------------------------------
    try:
        from ml.inference import predict as run_predict

        agency = _prose_field(db, dpr.id, "implementing_agency")
        ministry = _prose_field(db, dpr.id, "department_ministry")
        months = _planned_months(db, dpr.id)

        common = dict(sanctioned_cr=sanctioned, sector=sector, ministry=ministry,
                      state=dpr.state, agency=agency, planned_duration_months=months)
        overrun = run_predict("overran", **common)
        delay = run_predict("delayed", **common)

        def drivers_of(p):
            return [{"feature": d.feature, "value": str(d.value), "shap": d.shap,
                     "direction": d.direction, "plain_english": d.plain_english}
                    for d in p.drivers]

        db.add(RiskPrediction(
            dpr_id=dpr.id, model_version=MODEL_VERSION,
            overrun_probability=overrun.probability,
            delay_probability=delay.probability,
            # Each probability carries ITS OWN model's reasons. Previously the overrun
            # model's drivers were stored and then printed under the delay probability, in
            # both the API and the appraisal note — the number and its explanation came
            # from two different models.
            shap_drivers=drivers_of(overrun),
            delay_drivers=drivers_of(delay),
            # The vector actually scored, so a reader can see which values were real.
            features_used={**{k: v for k, v in common.items()},
                           "caveat": overrun.caveat}))
    except FileNotFoundError as exc:
        log.warning("risk models unavailable (%s) — run python -m ml.train", exc)
    except Exception as exc:                              # noqa: BLE001
        log.warning("risk prediction failed for dpr %s: %s", dpr.id, exc)

    # ---- outcome range --------------------------------------------------------------
    try:
        from ml.ranges.reference_class import compute

        r = compute(sanctioned, sector=sector, state=dpr.state)
        db.add(OutcomeRange(
            dpr_id=dpr.id, method="reference_class", peer_count=r.peer_count,
            peer_criteria={**r.peer_criteria, "widened_past": r.widened,
                           "caveat": r.caveat},
            cost_p50=int(r.cost_p50 * 10_000_000_00) if r.cost_p50 else None,
            cost_p80=int(r.cost_p80 * 10_000_000_00) if r.cost_p80 else None,
            cost_p95=int(r.cost_p95 * 10_000_000_00) if r.cost_p95 else None,
            months_p50=r.months_p50, months_p80=r.months_p80, months_p95=r.months_p95,
            peer_distribution=r.overrun_pcts))
    except FileNotFoundError:
        log.warning("PAIMANA panel not built — run python -m ml.data.paimana")
    except Exception as exc:                              # noqa: BLE001
        log.warning("outcome range failed for dpr %s: %s", dpr.id, exc)

    db.commit()
    log.info("prediction complete for dpr %s (sanctioned Rs %.2f Cr)", dpr.id, sanctioned)
