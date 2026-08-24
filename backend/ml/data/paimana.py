"""Parse MoSPI PAIMANA Flash Reports into a project panel.

This is the training data, and it is real: every central-sector project of Rs 150 crore
and above, with what it was approved to cost and what it now costs, what it was meant to
be commissioned and when it now will be. Those differences are the labels.

Nothing here is synthetic. See answers.md Q2.

The layout is positional text rather than a machine-readable table, so records are read
with a regex over the linear text stream. Two details that will break a naive parser:

* The source spells it "Orignal". Do not correct it in header matching.
* Ministry and sector appear as standalone heading lines between record groups and must
  be carried down onto the rows that follow.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger("pramaan.paimana")

TABLE6_MARKER = "All Ongoing Projects"
TABLE3_MARKER = "Completed Projects"

# One record. Costs may or may not carry a parenthesised revision; dates always do.
RECORD = re.compile(
    r"^(?P<sl>\d{1,5})\n"
    r"(?P<name>.*?)\n"
    r"\((?P<agency>[^)]*)\)\n"
    r"\((?P<code>[^)]*)\)\n"
    r"\([^)]*\)\s*\([^)]*\)\n"
    r"(?P<state>[^\n]+)\n"
    r"(?P<approval>\d{2}/\d{4})\n"
    r"\((?P<approval_rev>[^)]*)\)\n"
    r"(?P<doc_orig>\d{2}/\d{4})\n"
    r"\((?P<doc_rev>[^)]*)\)\n"
    r"(?P<cost_orig>[\d,]+(?:\.\d+)?)\n"
    r"\((?P<cost_rev>[\d,.-]*)\)\n"
    r"(?P<expenditure>[\d,]+(?:\.\d+)?|-)\n"
    r"(?P<progress>[\d.]+|-)",
    re.M | re.S)

MINISTRY = re.compile(r"^(Ministry of [^\n]+|Department of [^\n]+|"
                      r"Department for [^\n]+)$", re.M)


@dataclass
class ProjectRecord:
    sl_no: int
    project_name: str
    agency: str
    project_code: str
    state: str
    ministry: str | None
    sector: str | None
    approval_mm_yyyy: str
    doc_original: str
    doc_revised: str | None
    cost_original_cr: float
    cost_revised_cr: float | None
    expenditure_cr: float | None
    physical_progress_pct: float | None
    report_period: str

    # ---- derived labels -------------------------------------------------------------
    @property
    def cost_overrun_pct(self) -> float | None:
        if not self.cost_original_cr or self.cost_revised_cr is None:
            return None
        return round((self.cost_revised_cr - self.cost_original_cr)
                     / self.cost_original_cr * 100, 4)

    @property
    def time_overrun_months(self) -> int | None:
        a, b = _months(self.doc_original), _months(self.doc_revised)
        return None if a is None or b is None else b - a

    @property
    def planned_duration_months(self) -> int | None:
        a, b = _months(self.approval_mm_yyyy), _months(self.doc_original)
        return None if a is None or b is None else b - a

    def to_row(self) -> dict:
        d = asdict(self)
        d["cost_overrun_pct"] = self.cost_overrun_pct
        d["time_overrun_months"] = self.time_overrun_months
        d["planned_duration_months"] = self.planned_duration_months
        return d


def _months(mm_yyyy: str | None) -> int | None:
    if not mm_yyyy or not re.fullmatch(r"\d{2}/\d{4}", mm_yyyy.strip()):
        return None
    mm, yyyy = mm_yyyy.strip().split("/")
    return int(yyyy) * 12 + int(mm)


def _num(text: str) -> float | None:
    t = (text or "").strip().replace(",", "")
    if t in {"", "-", "–"}:
        return None
    try:
        return float(t)
    except ValueError:
        return None


# Column headers and boilerplate that look like sector headings but are not.
_NOT_A_SECTOR = {
    "physical progress", "cumulative", "expenditure", "state", "project name",
    "revised cost", "orignal cost", "all ongoing projects", "sl.no",
}


def _looks_like_sector(line: str) -> bool:
    l = line.strip()
    if not l or re.search(r"\d", l) or "Page" in l:
        return False
    if l.lower() in _NOT_A_SECTOR or l.startswith(("Ministry of", "Department ")):
        return False
    return 1 <= len(l.split()) <= 6 and l[0].isupper()


def scan_headings(page_text: str) -> list[tuple[int, str, str | None]]:
    """Return (line_index, ministry, sector) for every heading on the page.

    Sector is the line immediately AFTER the ministry heading — not something to be
    searched for backwards from a record. An earlier heuristic scanned upwards and
    happily returned "Uttar Pradesh" (the previous record's state) or "Physical Progress"
    (a column header), which put state names in the sector column and made every
    sector-level statistic meaningless.
    """
    out = []
    lines = [l.strip() for l in page_text.splitlines()]
    for i, line in enumerate(lines):
        if MINISTRY.fullmatch(line):
            sector = next((lines[j] for j in range(i + 1, min(i + 4, len(lines)))
                           if _looks_like_sector(lines[j])), None)
            out.append((i, line, sector))
    return out


def _char_offset_of_line(page_text: str, line_index: int) -> int:
    lines = page_text.splitlines(keepends=True)
    return sum(len(l) for l in lines[:line_index])


def parse_report(pdf_path: str | Path, report_period: str) -> list[ProjectRecord]:
    import pymupdf

    records: list[ProjectRecord] = []
    with pymupdf.open(pdf_path) as doc:
        in_table = False
        ministry: str | None = None
        sector: str | None = None

        for i in range(doc.page_count):
            text = doc[i].get_text()
            if TABLE6_MARKER in text and "Sl.No" in text:
                in_table = True
            if not in_table:
                continue

            # Headings are scan state: a continuation page carries neither, so both the
            # ministry and its sector must persist from the last page that did.
            headings = [(_char_offset_of_line(text, idx), min_, sec)
                        for idx, min_, sec in scan_headings(text)]
            for rec in RECORD.finditer(text):
                g = rec.groupdict()
                cost_o = _num(g["cost_orig"])
                if cost_o is None:
                    continue
                for off, min_, sec in headings:
                    if off < rec.start():
                        ministry = min_
                        if sec:
                            sector = sec
                records.append(ProjectRecord(
                    sl_no=int(g["sl"]),
                    project_name=" ".join(g["name"].split())[:400],
                    agency=" ".join(g["agency"].split())[:200],
                    project_code=g["code"].strip(),
                    state=g["state"].strip()[:100],
                    ministry=ministry,
                    sector=sector,
                    approval_mm_yyyy=g["approval"],
                    doc_original=g["doc_orig"],
                    doc_revised=(g["doc_rev"] or "").strip() or None,
                    cost_original_cr=cost_o,
                    cost_revised_cr=_num(g["cost_rev"]),
                    expenditure_cr=_num(g["expenditure"]),
                    physical_progress_pct=_num(g["progress"]),
                    report_period=report_period))
    log.info("parsed %s records from %s", len(records), pdf_path)
    return records


def to_dataframe(records: list[ProjectRecord]):
    import pandas as pd
    return pd.DataFrame([r.to_row() for r in records])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    recs = parse_report("ml/data/raw/paimana_flash_report_2026-06.pdf", "2026-06")
    df = to_dataframe(recs)
    out = Path("ml/data/paimana_panel.csv")
    df.to_csv(out, index=False)
    print(f"\n{len(df)} records -> {out}")
    print(f"  with cost overrun label : {df['cost_overrun_pct'].notna().sum()}")
    print(f"  with time overrun label : {df['time_overrun_months'].notna().sum()}")
    print(f"  ministries              : {df['ministry'].nunique()}")
    print(f"  states                  : {df['state'].nunique()}")
