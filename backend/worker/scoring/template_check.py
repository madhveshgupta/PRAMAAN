"""Detect an unfilled model template submitted as if it were a completed DPR.

Ministries publish blank model templates for applicants to fill in. Two of the real
documents in our corpus are exactly that — NHB's Fig and Mint templates, with every
section heading present and almost every value cell empty.

That matters because a compliance rubric scores *structure*, and a blank template has
perfect structure. Both scored 83.3 before this check existed: high marks for a document
containing almost no information. An appraiser needs to be told "this form is not filled
in" before any other finding, because every other finding is meaningless until it is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.models import TableCell

_DIGIT = re.compile(r"\d")

# Below this fill ratio, with correspondingly few numeric cells, the document is a form
# rather than a submission. Calibrated against the real corpus: completed documents ran
# 82-99% filled, the two known blank templates 33%.
FILL_THRESHOLD = 0.55
NUMERIC_THRESHOLD = 0.15
MIN_CELLS = 200          # too few tables to judge; say nothing rather than guess


@dataclass
class TemplateVerdict:
    is_template: bool
    total_cells: int
    filled_ratio: float
    numeric_ratio: float
    message: str | None = None


def judge_cells(cells: list[str | None]) -> TemplateVerdict:
    """The decision, over table-cell contents alone.

    Split out from `check` so the rule can be exercised without a database and a 300-page
    fixture — the judgement is about the cells, not about where they came from.
    """
    total = len(cells)
    if total < MIN_CELLS:
        return TemplateVerdict(False, total, 1.0, 1.0)

    filled = [c for c in cells if (c or "").strip()]
    numeric = [c for c in filled if _DIGIT.search(c)]
    fill_ratio = len(filled) / total
    num_ratio = len(numeric) / total

    if fill_ratio >= FILL_THRESHOLD or num_ratio >= NUMERIC_THRESHOLD:
        return TemplateVerdict(False, total, round(fill_ratio, 3), round(num_ratio, 3))

    return TemplateVerdict(
        True, total, round(fill_ratio, 3), round(num_ratio, 3),
        message=(f"Only {fill_ratio:.0%} of this document's {total:,} table cells contain "
                 f"anything at all, and just {num_ratio:.0%} contain a number. This looks "
                 f"like an unfilled model template rather than a completed project report. "
                 f"The compliance score below reflects the presence of section headings, "
                 f"not the presence of information — treat it as unreliable until the "
                 f"form is filled in."))


def check(db: Session, document_id) -> TemplateVerdict:
    """Same judgement, over a stored document's table cells."""
    return judge_cells(list(db.scalars(select(TableCell.text)
                                       .where(TableCell.document_id == document_id))))
