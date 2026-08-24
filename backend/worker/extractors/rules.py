"""Deterministic extractors — run first, always.

Every regex hit already knows its own character offsets, so its evidence anchor costs
nothing: no model call, no verification round-trip, confidence 0.98. This covers most of
the numeric content of a DPR, which is precisely the content where a hallucinated value
would do the most damage.

Anything resolved here is never sent to the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MONEY = re.compile(
    r"(?:₹|\bRs\.?|\bINR\b)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr\b|lakh|lakhs|lac)?",
    re.I)
PERCENT = re.compile(r"([\d]+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)", re.I)
IRR = re.compile(
    r"(?:internal\s+rate\s+of\s+return|IRR|EIRR|FIRR)[^.\n]{0,60}?"
    r"([\d]+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)", re.I)
BCR = re.compile(
    r"(?:benefit\s*[-/ ]?\s*cost\s+ratio|BCR)[^.\n]{0,40}?([\d]+(?:\.\d+)?)", re.I)
DISCOUNT = re.compile(
    r"discount\s+rate\s+of\s+([\d]+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)", re.I)
DURATION = re.compile(
    r"(?:construction|implementation|completion)\s+period[^.\n]{0,40}?"
    r"(\d{1,3})\s*months?", re.I)
LENGTH_KM = re.compile(r"([\d]+(?:\.\d+)?)\s*(?:km|kilometre|kilometer)s?\b", re.I)
CAPACITY_MLD = re.compile(r"([\d]+(?:\.\d+)?)\s*MLD\b", re.I)

# Who is actually building it, and under whom. Both sit in the salient-features table that
# every template opens with, so they are structured rows rather than prose — which is why a
# regex is honest here. They matter more than their size suggests: sponsor track record is
# the strongest signal the risk model has, and without an agency it falls back to the panel
# mean, i.e. to no signal at all.
#
# The value must start with a capital and stay on one line. Without that, "Department" in a
# sentence like "consulted the department on adjacency" reads as a department name.
AGENCY = re.compile(
    r"Implementing\s+agency(?:\s*/\s*SPV)?\s*[:\-]?\s*"
    r"([A-Z][^\n]{3,80}?)\s*(?=\n|$)", re.I)
# Two shapes, because templates differ. Buildings and General give it its own salient row
# ("Department  Health and Family Welfare"); the Bridges template folds it into the
# applicant's name ("Assam Public Works Department (Roads & Bridges)"). Both name the
# sponsoring body, which is what the risk model wants.
DEPARTMENT = re.compile(
    r"(?:^|\n)\s*(?:\d{1,2}[.)]?\s+)?(?:Department|Ministry)\s*[:\-]?\s+"
    r"([A-Z(][^\n]{3,70}?)\s*(?=\n|$)")
DEPARTMENT_INLINE = re.compile(
    r"\b((?:[A-Z][A-Za-z&.]*\s+){1,4}(?:Department|Ministry)"
    r"(?:\s*\([^)\n]{2,40}\))?)")


@dataclass
class RuleHit:
    field_key: str
    value: str
    unit: str | None
    kind: str
    page_no: int
    char_start: int
    char_end: int
    snippet: str


def _sentence_around(text: str, start: int, end: int, pad: int = 90) -> tuple[str, int, int]:
    """Widen a match to readable context — a bare '412.50' is a useless snippet for a
    reviewer, and a useless highlight."""
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    for stop in (". ", "\n"):
        cut = text.rfind(stop, lo, start)
        if cut != -1:
            lo = cut + len(stop)
            break
    for stop in (". ", "\n"):
        cut = text.find(stop, end, hi)
        if cut != -1:
            hi = cut + 1
            break
    return text[lo:hi].strip(), lo, hi


_UNIT = {"crore": "INR_CRORE", "cr": "INR_CRORE",
         "lakh": "INR_LAKH", "lakhs": "INR_LAKH", "lac": "INR_LAKH"}


# Salient features sit in the opening pages of every template we support.
ORG_PAGE_LIMIT = 8
# Column headings run together as capitalised words and often carry a unit; an
# organisation name does not.
_HEADERISH = re.compile(r"\(s?q?m\)|\bUnits?\b|\bTotal\b|\bArea\b|\bNos\b|\d", re.I)


def _looks_like_org(value: str) -> bool:
    return 1 < len(value.split()) <= 9 and not _HEADERISH.search(value)


def extract_page(page_no: int, full_text: str) -> list[RuleHit]:
    """Every deterministic hit on one page, each already carrying its offsets."""
    hits: list[RuleHit] = []

    def add(field_key, value, unit, kind, m):
        snippet, lo, hi = _sentence_around(full_text, m.start(), m.end())
        hits.append(RuleHit(field_key, value, unit, kind, page_no, lo, hi, snippet))

    for m in MONEY.finditer(full_text):
        scale = (m.group(2) or "").lower().rstrip(".")
        add("money_mention", m.group(1), _UNIT.get(scale, "INR"), "money", m)

    for m in IRR.finditer(full_text):
        add("claimed_irr_pct", m.group(1), "PERCENT", "percent", m)
    for m in BCR.finditer(full_text):
        add("claimed_bcr", m.group(1), None, "number", m)
    for m in DISCOUNT.finditer(full_text):
        add("discount_rate_pct", m.group(1), "PERCENT", "percent", m)
    for m in DURATION.finditer(full_text):
        add("construction_months", m.group(1), "MONTHS", "duration", m)
    for m in LENGTH_KM.finditer(full_text):
        add("length_km", m.group(1), "KM", "number", m)
    for m in CAPACITY_MLD.finditer(full_text):
        add("capacity_mld", m.group(1), "MLD", "number", m)

    # Organisation names are prose values: there is no separable number to cross-check, so
    # verification rests on the span alone (see verify.value_in_span).
    for m in AGENCY.finditer(full_text):
        if page_no <= ORG_PAGE_LIMIT:
            add("implementing_agency", m.group(1).strip(" .:-"), None, "prose", m)
    # Only from the front matter. Every template puts the sponsoring body in its
    # salient-features table in the first few pages; deeper in the document "Department"
    # heads a column of floor areas, and that table header was being read as a ministry.
    if page_no <= ORG_PAGE_LIMIT:
        dept = (list(DEPARTMENT.finditer(full_text))
                or list(DEPARTMENT_INLINE.finditer(full_text)))
        for m in dept:
            value = m.group(1).strip(" .:-")
            if _looks_like_org(value):
                add("department_ministry", value, None, "prose", m)

    return hits
