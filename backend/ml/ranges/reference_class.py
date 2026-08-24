"""Outcome ranges by reference class forecasting.

Not a Monte Carlo simulation, deliberately. A simulation needs a correlation matrix
between cost heads that we have no empirical basis for, which would mean inventing the
parameters behind the single most quotable number in the product (invariant #13).

Instead we look up what actually happened to comparable projects and read the percentiles
off. Every number in the resulting sentence is a real project that really finished.

The peer count is always returned and must always be displayed. "80% of 340 comparable
projects" and "80% of 6" are very different claims, and hiding the difference would be
exactly the false precision this system exists to remove.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PANEL = Path("ml/data/paimana_panel.csv")
MIN_PEERS = 30


@dataclass
class OutcomeRange:
    peer_count: int
    peer_criteria: dict
    widened: list[str] = field(default_factory=list)
    cost_p50: float | None = None
    cost_p80: float | None = None
    cost_p95: float | None = None
    months_p50: float | None = None
    months_p80: float | None = None
    months_p95: float | None = None
    overrun_pcts: dict = field(default_factory=dict)
    caveat: str | None = None


def _cost_band(cr: float) -> str:
    if cr < 500:
        return "<500"
    if cr < 2000:
        return "500-2000"
    return ">=2000"


def compute(sanctioned_cr: float, sector: str | None = None, state: str | None = None,
            panel: pd.DataFrame | None = None) -> OutcomeRange:
    df = panel if panel is not None else pd.read_csv(PANEL)
    df = df.dropna(subset=["cost_overrun_pct"])
    band = _cost_band(sanctioned_cr)
    df = df.assign(_band=df["cost_original_cr"].map(_cost_band))

    # Widen progressively until the peer group is large enough to mean anything.
    ladder = [
        ({"sector": sector, "cost_band": band, "state": state}, "sector + cost band + state"),
        ({"sector": sector, "cost_band": band}, "sector + cost band"),
        ({"sector": sector}, "sector only"),
        ({}, "all projects"),
    ]
    widened: list[str] = []
    peers, criteria = df, {}
    for spec, label in ladder:
        sel = df
        if spec.get("sector"):
            sel = sel[sel["sector"] == spec["sector"]]
        if spec.get("cost_band"):
            sel = sel[sel["_band"] == spec["cost_band"]]
        if spec.get("state"):
            sel = sel[sel["state"] == spec["state"]]
        criteria = {k: v for k, v in spec.items() if v}
        peers = sel
        if len(sel) >= MIN_PEERS:
            break
        widened.append(label)

    q = peers["cost_overrun_pct"].quantile([0.5, 0.8, 0.95])
    months = peers["time_overrun_months"].dropna()
    mq = months.quantile([0.5, 0.8, 0.95]) if len(months) >= 10 else None

    caveat = None
    if len(peers) < MIN_PEERS:
        caveat = (f"Only {len(peers)} comparable projects were found even after widening "
                  f"the criteria. Treat these percentiles as indicative, not reliable.")

    return OutcomeRange(
        peer_count=int(len(peers)), peer_criteria=criteria or {"scope": "all projects"},
        widened=widened,
        cost_p50=round(sanctioned_cr * (1 + q.loc[0.5] / 100), 2),
        cost_p80=round(sanctioned_cr * (1 + q.loc[0.8] / 100), 2),
        cost_p95=round(sanctioned_cr * (1 + q.loc[0.95] / 100), 2),
        months_p50=None if mq is None else round(float(mq.loc[0.5]), 1),
        months_p80=None if mq is None else round(float(mq.loc[0.8]), 1),
        months_p95=None if mq is None else round(float(mq.loc[0.95]), 1),
        overrun_pcts={"p50": round(float(q.loc[0.5]), 2),
                      "p80": round(float(q.loc[0.8]), 2),
                      "p95": round(float(q.loc[0.95]), 2)},
        caveat=caveat)


def describe(r: OutcomeRange, sanctioned_cr: float) -> str:
    crit = ", ".join(f"{k}={v}" for k, v in r.peer_criteria.items())
    return (f"Sanctioned Rs {sanctioned_cr:,.2f} Cr. Of {r.peer_count} comparable projects "
            f"({crit}), 80% finished at or below Rs {r.cost_p80:,.2f} Cr "
            f"(P50 Rs {r.cost_p50:,.2f} Cr, P95 Rs {r.cost_p95:,.2f} Cr).")
