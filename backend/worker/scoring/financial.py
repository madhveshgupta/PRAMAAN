"""F6 — financial recomputation.

DPRs state an IRR. Almost nobody recomputes it from the cash flows in the annexure. When a
summary is written to a target and the annexure is never reconciled to it, the claimed
viability is fiction — and it is fiction that gets projects sanctioned.

The ordering here is not incidental. **Sanity-check the table before computing anything.**
A malformed table produces a wildly wrong IRR that looks exactly like a real finding, and
reporting "claimed 14.2%, actual 2.1%" when the truth is "we misread the table" is a worse
outcome than reporting nothing at all.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import numpy_financial as npf
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models import Table, TableCell
from worker.evidence.locate import Evidence

log = logging.getLogger("pramaan.financial")

YEAR_HEADERS = {"year", "yr", "period"}
COST_HEADERS = {"capital cost", "cost", "capital", "o&m cost", "outflow", "expenditure"}
BENEFIT_HEADERS = {"gross benefit", "benefit", "benefits", "inflow", "revenue"}
NET_HEADERS = {"net cash flow", "net", "net flow"}


@dataclass
class CashFlow:
    years: list[int]
    net: list[float]
    table_id: object
    page_no: int


@dataclass
class FinancialResult:
    cashflow: CashFlow | None = None
    computed_irr: float | None = None
    irr_ambiguous: bool = False
    irr_roots: list[float] = field(default_factory=list)
    npv: float | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.cashflow is not None and not self.problems


def _num(text: str) -> float | None:
    t = (text or "").strip().replace(",", "").replace("−", "-")
    if t in {"", "-", "–", "—", "n/a", "na"}:
        return 0.0
    try:
        return float(t)
    except ValueError:
        return None


def find_cashflow_table(db: Session, document_id) -> CashFlow | None:
    """Locate a year-indexed cash-flow table anywhere in the document."""
    tables = db.scalars(select(Table).where(Table.document_id == document_id)).all()
    for tbl in tables:
        cells = db.scalars(select(TableCell).where(TableCell.table_id == tbl.id)
                           .order_by(TableCell.row_idx, TableCell.col_idx)).all()
        if not cells:
            continue
        header = {c.col_idx: (c.text or "").strip().lower()
                  for c in cells if c.row_idx == 0}
        if not any(h in YEAR_HEADERS for h in header.values()):
            continue

        year_col = next((i for i, h in header.items() if h in YEAR_HEADERS), None)
        net_col = next((i for i, h in header.items() if h in NET_HEADERS), None)
        cost_cols = [i for i, h in header.items() if h in COST_HEADERS]
        ben_cols = [i for i, h in header.items() if h in BENEFIT_HEADERS]
        if year_col is None or (net_col is None and not (cost_cols and ben_cols)):
            continue

        by_row: dict[int, dict[int, str]] = {}
        for c in cells:
            by_row.setdefault(c.row_idx, {})[c.col_idx] = c.text

        years, nets = [], []
        for r in sorted(by_row):
            if r == 0:
                continue
            row = by_row[r]
            yr = _num(row.get(year_col, ""))
            if yr is None:
                continue
            if net_col is not None:
                val = _num(row.get(net_col, ""))
            else:
                cost = sum(_num(row.get(i, "")) or 0.0 for i in cost_cols)
                ben = sum(_num(row.get(i, "")) or 0.0 for i in ben_cols)
                val = ben - cost
            if val is None:
                continue
            years.append(int(yr))
            nets.append(val)

        if len(years) >= 3:
            return CashFlow(years=years, net=nets, table_id=tbl.id, page_no=tbl.page_no)
    return None


def sanity_check(cf: CashFlow) -> list[str]:
    """Run BEFORE any IRR maths. A problem here means we emit a data-quality warning,
    never a financial finding — we do not accuse a DPR of bad numbers when the truth is
    that we could not read its table."""
    problems: list[str] = []

    if len(cf.net) < 3:
        problems.append("fewer than three periods of cash flow")

    expected = list(range(min(cf.years), max(cf.years) + 1))
    if cf.years != expected:
        missing = sorted(set(expected) - set(cf.years))
        if missing:
            problems.append(f"missing year(s) in the series: {missing[:8]}")
        elif cf.years != sorted(cf.years):
            problems.append("years are not in ascending order")

    signs = [np.sign(v) for v in cf.net if v != 0]
    if not signs:
        problems.append("every net cash flow is zero")
    elif len(set(signs)) == 1:
        problems.append("no sign change in the series — IRR is undefined")

    if any(abs(v) > 1e7 for v in cf.net):
        problems.append("implausible magnitude — units may have been misread")

    return problems


def _all_roots(net: list[float]) -> list[float]:
    """Every real IRR root in a plausible range. Non-conventional flows can have several,
    and silently picking one is how a tool reports a confident wrong number."""
    coeffs = list(reversed(net))
    try:
        roots = np.roots(coeffs)
    except (np.linalg.LinAlgError, ValueError):
        return []
    out = []
    for r in roots:
        if abs(r.imag) > 1e-9 or r.real <= 0:
            continue
        rate = 1.0 / r.real - 1.0
        if -0.99 < rate < 10.0:
            out.append(float(round(rate * 100, 4)))
    return sorted(set(out))


def recompute(db: Session, document_id, discount_rate: float = 0.12) -> FinancialResult:
    cf = find_cashflow_table(db, document_id)
    if cf is None:
        return FinancialResult(problems=["no year-indexed cash-flow table was found"])

    problems = sanity_check(cf)
    if problems:
        # Deliberately stop here. A wrong IRR from a garbled table looks exactly like a
        # real finding, which is worse than no finding.
        return FinancialResult(cashflow=cf, problems=problems)

    roots = _all_roots(cf.net)
    irr = npf.irr(cf.net)
    irr_pct = None if irr is None or np.isnan(irr) else round(float(irr) * 100, 3)

    return FinancialResult(
        cashflow=cf, computed_irr=irr_pct,
        irr_ambiguous=len(roots) > 1, irr_roots=roots,
        npv=round(float(npf.npv(discount_rate, cf.net)), 3))


def anchor_for_table(db: Session, document_id, cf: CashFlow) -> Evidence | None:
    """Anchor to the cash-flow table, with a snippet taken FROM the table.

    A descriptive label like "Year-wise cash flow statement" reads as a quotation while
    being text we wrote. The evidence contract is that a snippet is what is actually
    there — so the snippet is built from the table's own header and first data row.
    """
    tbl = db.get(Table, cf.table_id)
    if tbl is None:
        return None

    cells = db.scalars(select(TableCell).where(TableCell.table_id == tbl.id)
                       .order_by(TableCell.row_idx, TableCell.col_idx)).all()
    by_row: dict[int, list[str]] = {}
    for c in cells:
        if c.row_idx <= 1 and (c.text or "").strip():
            by_row.setdefault(c.row_idx, []).append(c.text.strip())
    snippet = " | ".join(" ".join(by_row[r]) for r in sorted(by_row)) or "cash flow table"

    return Evidence(page=tbl.page_no, bbox=list(tbl.bbox),
                    snippet=snippet[:220], confidence=0.95, method="table_cell",
                    source=f"table:{tbl.id}")
