"""Canonicalisation — the layer that decides whether two things are "the same".

Split deliberately in two:

* **Prose** normalisation is lossy and forgiving, and feeds fuzzy matching.
* **Numeric** canonicalisation is exact and feeds strict comparison.

Never fuzzy-match a number. ``412.50`` and ``4l2.5O`` score highly under partial_ratio and
mean different things — which is exactly how an OCR error becomes a confidently wrong
figure in a financial appraisal.
"""
from __future__ import annotations

import re
import unicodedata

# Indian currency appears in all of these forms in a single document.
_CRORE = re.compile(r"\bcr(?:ore)?s?\b", re.I)
_LAKH = re.compile(r"\bl(?:a|à)kh?s?\b", re.I)
_CURRENCY_WORD = re.compile(r"(?:₹|\bRs\.?|\bINR\b|\brupees?\b)", re.I)
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

PAISE_PER_RUPEE = 100
PAISE_PER_LAKH = 100_000 * PAISE_PER_RUPEE
PAISE_PER_CRORE = 10_000_000 * PAISE_PER_RUPEE


def normalise_prose(text: str) -> str:
    """Collapse whitespace, unify currency spellings, casefold. For fuzzy matching only."""
    t = unicodedata.normalize("NFKC", text)
    t = _CURRENCY_WORD.sub("rs", t)
    t = re.sub(r"[‐-―−]", "-", t)     # dash variants
    t = re.sub(r"[‘’“”]", "'", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().casefold()


def parse_number(raw: str) -> float | None:
    """'41,250.75' -> 41250.75. Returns None when there is no clean number."""
    m = _NUMBER.search(raw.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def to_paise(raw: str) -> int | None:
    """Canonicalise any Indian money expression to an integer number of paise.

    All of these resolve to the same integer, which is what makes the value-in-span check
    work across the wildly inconsistent notation real DPRs use:
        'Rs. 412.50 crore'  '₹412.5 Cr'  '41,250 lakh'  '412,50,00,000'
    """
    if raw is None:
        return None
    text = unicodedata.normalize("NFKC", str(raw))
    value = parse_number(text)
    if value is None:
        return None
    if _CRORE.search(text):
        return int(round(value * PAISE_PER_CRORE))
    if _LAKH.search(text):
        return int(round(value * PAISE_PER_LAKH))
    return int(round(value * PAISE_PER_RUPEE))


def repair_linebreak_numbers(text: str) -> str:
    """'Rs. 412.\\n50 crore' -> 'Rs. 412.50 crore'.

    A number split across a line break is a genuine value that must verify, not a
    mismatch. Only joins where a digit-dot meets a digit, so ordinary sentences are safe.
    """
    return re.sub(r"(\d[\d,]*\.)\s*\n\s*(\d)", r"\1\2", text)


def numbers_in(text: str) -> set[float]:
    """Every distinct numeric literal in a string, comma-stripped."""
    out: set[float] = set()
    for m in _NUMBER.finditer(text.replace(" ", "")):
        try:
            out.add(float(m.group(0).replace(",", "")))
        except ValueError:
            continue
    return out


def money_values_in(text: str) -> set[int]:
    """Every money expression in a string, as paise.

    Each numeric literal is re-read together with the trailing unit word so that
    'Rs 412.50 crore and Rs 8.60 crore' yields two correct values rather than one.
    """
    out: set[int] = set()
    for m in _NUMBER.finditer(text):
        tail = text[m.end():m.end() + 24]
        paise = to_paise(m.group(0) + " " + tail)
        if paise is not None:
            out.add(paise)
    return out
