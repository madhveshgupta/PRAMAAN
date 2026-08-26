"""Extraction stage: parsed geometry in, evidence-anchored fields out.

Order matters. Deterministic rules run first and resolve most numeric content for free,
with exact anchors and no model call. Only what rules cannot reach is sent to the LLM, and
whatever the LLM returns must survive the verification guard before it is stored.

Nothing reaches `extracted_fields` without evidence (invariant #1).
"""
from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.app.llm import provider
from api.app.models import (Document, DocumentPage, Dpr, DprExtraction, ExtractedField,
                            ExtractionRejection, Job, TextSpan)
from worker import queue
from worker.evidence.locate import Evidence
from worker.extractors import rules
from worker.extractors.verify import Candidate, record_rejection, verify

log = logging.getLogger("pramaan.extract")

CONFIDENCE = {"regex": 0.98, "llm_verified": 0.90, "ocr_regex": 0.70}


def _anchor_from_rule(db: Session, document_id, hit: rules.RuleHit) -> Evidence | None:
    """Rule hits already know their offsets, so the anchor is a direct span lookup —
    no search, no fuzzy matching, no chance of landing on the wrong occurrence."""
    spans = list(db.scalars(select(TextSpan).where(
        TextSpan.document_id == document_id,
        TextSpan.page_no == hit.page_no,
        TextSpan.char_start < hit.char_end,
        TextSpan.char_end > hit.char_start)))
    if not spans:
        return None
    return Evidence(
        page=hit.page_no,
        bbox=[min(s.bbox[0] for s in spans), min(s.bbox[1] for s in spans),
              max(s.bbox[2] for s in spans), max(s.bbox[3] for s in spans)],
        snippet=hit.snippet, confidence=CONFIDENCE["regex"], method="regex")


def _clear_previous(db: Session, dpr_id) -> None:
    """Re-extraction replaces, never appends — the same reasoning as invariant #12."""
    db.execute(delete(ExtractedField).where(ExtractedField.dpr_id == dpr_id))
    db.execute(delete(ExtractionRejection).where(ExtractionRejection.dpr_id == dpr_id))
    db.execute(delete(DprExtraction).where(DprExtraction.dpr_id == dpr_id))


def handle_extract(db: Session, job: Job) -> None:
    # Per-document, not cumulative: the counter is a module global, so without this every
    # later DPR inherits the totals of every earlier one in the same worker process.
    provider.reset_usage()
    doc = db.get(Document, job.document_id)
    if doc is None or doc.status != "ready":
        raise ValueError(f"document {job.document_id} is not ready for extraction")
    dpr_id = doc.dpr_id

    _clear_previous(db, dpr_id)
    db.commit()

    pages = list(db.scalars(select(DocumentPage)
                            .where(DocumentPage.document_id == doc.id)
                            .order_by(DocumentPage.page_no)))

    stored = 0
    ocr_pages = {p.page_no for p in pages if p.ocr_used}

    # ---- pass 1: deterministic rules -------------------------------------------------
    for page in pages:
        for hit in rules.extract_page(page.page_no, page.full_text):
            anchor = _anchor_from_rule(db, doc.id, hit)
            if anchor is None:
                continue
            method = "ocr_regex" if page.page_no in ocr_pages else "regex"
            confidence = CONFIDENCE[method]
            if page.ocr_confidence is not None:
                confidence *= page.ocr_confidence
            anchor.method = method
            anchor.confidence = round(confidence, 4)

            numeric = None
            try:
                numeric = float(hit.value.replace(",", ""))
            except ValueError:
                pass

            db.add(ExtractedField(
                dpr_id=dpr_id, field_key=hit.field_key, value_text=hit.value,
                value_numeric=numeric, unit=hit.unit, evidence=[anchor.to_dict()],
                confidence=anchor.confidence, method=method,
                status="found" if confidence >= 0.75 else "needs_human_verification"))
            stored += 1
    db.commit()
    log.info("rules extracted %s fields for dpr %s", stored, dpr_id)

    # ---- pass 2: LLM for what rules cannot reach --------------------------------------
    llm_fields = 0
    if provider.available():
        try:
            llm_fields = _llm_pass(db, dpr_id, doc.id, pages)
        except provider.LLMUnavailable as exc:
            log.warning("LLM pass skipped: %s", exc)
    else:
        log.warning("no LLM configured — prose fields (land status, O&M arrangement, "
                    "risk register) will be marked not_extracted, NOT absent")
        for key in ("project_objective", "land_acquisition_status",
                    "environment_clearance_status", "om_arrangement", "risk_register"):
            db.add(ExtractedField(
                dpr_id=dpr_id, field_key=key, evidence=[], confidence=0.0,
                status="not_extracted"))
        db.commit()

    _populate_feature_bridge(db, dpr_id, pages)

    db.add(DprExtraction(dpr_id=dpr_id, model_version="rules-1.0",
                         payload={"rule_fields": stored, "llm_fields": llm_fields,
                                  "llm_usage": dict(provider.USAGE)}))
    dpr = db.get(Dpr, dpr_id)
    if dpr:
        dpr.status = "assessed"
    queue.enqueue(db, "assess", dpr_id=dpr_id, document_id=doc.id)
    db.commit()
    log.info("extraction complete for dpr %s: %s rule + %s llm fields",
             dpr_id, stored, llm_fields)


PROMPT = """Extract the following fields from this excerpt of an Indian government \
Detailed Project Report.

RULES — these are not negotiable:
1. You may NOT return a value on its own. Every field must include `verbatim_span`: text \
copied EXACTLY, character for character, from the excerpt below.
2. If a field is not present in this excerpt, return it with "status": "not_found" and no \
value. Do not infer, estimate, or carry a figure over from elsewhere.
3. `verbatim_span` must contain the value you report.

Return JSON only:
{{"fields":[{{"field":"...","value":"...","unit":"...","verbatim_span":"...","status":"found|not_found"}}]}}

FIELDS: {fields}

EXCERPT (page {page}):
\"\"\"{text}\"\"\""""


# What kind of value each LLM field carries, which decides how hard verification can push.
# This must never be hardcoded at the call site: `kind="prose"` there routed EVERY field to
# the one arm of `value_in_span` that returns True unconditionally, so invariant #11 — the
# check added precisely because a model can quote a real sentence and attach a fabricated
# number to it — never fired on the only path that needs it. The numeric arms existed and
# were unreachable. Any numeric field added here gets checked from the first run.
FIELD_KIND: dict[str, str] = {
    "land_acquisition_status": "prose",
    "environment_clearance_status": "prose",
    "om_arrangement": "prose",
    "project_objective": "prose",
    "risk_register": "prose",
    "implementing_agency": "prose",
    "department_ministry": "prose",
}


def _llm_pass(db: Session, dpr_id, document_id, pages: list[DocumentPage]) -> int:
    """Retrieval-scoped, never the whole document. Only sections whose text suggests the
    field might be there are sent, which keeps both cost and hallucination surface down."""
    import json

    targets = {
        "land_acquisition_status": ["land acquisition", "land required", "acquired"],
        "environment_clearance_status": ["environmental clearance", "environment clearance"],
        "om_arrangement": ["operation and maintenance", "o&m", "post-commissioning"],
        "project_objective": ["executive summary", "the project envisages", "objective"],
        # Was listed in the not_extracted fallback but never in `targets`, so no code path
        # could ever produce it — always not_extracted, for every document.
        "risk_register": ["risk register", "risk assessment", "mitigation measure"],
    }

    stored = 0
    for field_key, cues in targets.items():
        page = next((p for p in pages
                     if any(c in p.full_text.lower() for c in cues)), None)
        if page is None:
            db.add(ExtractedField(dpr_id=dpr_id, field_key=field_key, evidence=[],
                                  confidence=0.0, status="not_found"))
            continue

        prompt = PROMPT.format(fields=field_key, page=page.page_no,
                               text=page.full_text[:6000])
        try:
            raw = provider.complete(prompt)
            payload = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        except Exception as exc:                        # noqa: BLE001
            log.warning("LLM output unusable for %s: %s", field_key, exc)
            db.add(ExtractedField(dpr_id=dpr_id, field_key=field_key, evidence=[],
                                  confidence=0.0, status="not_extracted"))
            continue

        for item in payload.get("fields", []):
            if item.get("status") == "not_found" or not item.get("verbatim_span"):
                db.add(ExtractedField(dpr_id=dpr_id, field_key=field_key, evidence=[],
                                      confidence=0.0, status="not_found"))
                continue
            cand = Candidate(field_key=field_key, value=str(item.get("value", "")),
                             unit=item.get("unit"), verbatim_span=item["verbatim_span"],
                             page_hint=page.page_no,
                             kind=FIELD_KIND.get(field_key, "prose"))
            verdict = verify(cand, document_id, db)
            if verdict.rejected:
                record_rejection(db, dpr_id, cand, verdict)
                db.add(ExtractedField(dpr_id=dpr_id, field_key=field_key, evidence=[],
                                      confidence=0.0, status="not_extracted"))
                continue
            db.add(ExtractedField(
                dpr_id=dpr_id, field_key=field_key, value_text=cand.value,
                unit=cand.unit, evidence=[verdict.evidence.to_dict()],
                confidence=verdict.evidence.confidence, method="llm_verified",
                status="found"))
            stored += 1
    db.commit()
    return stored


# --------------------------------------------------------------------- feature bridge
# The risk model is tabular and keyed on sector and state. Those live on the `dprs` row,
# and nothing was populating them — so every prediction ran against "unknown", widening
# the peer group to every project in the panel and discarding the strongest signals the
# model has. This is the join between the document half of the system and the ML half.

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu", "Ladakh",
    "Puducherry", "Chandigarh",
]

# Mapped onto the sector vocabulary the PAIMANA panel actually uses, so a lookup is
# possible. Inventing our own sector names would leave every peer query empty.
SECTOR_CUES = {
    "Roads & Highways": [r"\bhighway", r"\broad\b", r"carriageway", r"\bbridge\b",
                         r"bituminous", r"\bIRC\b"],
    "Railways": [r"\brailway", r"\brail line", r"\bmetro\b", r"broad gauge"],
    "Waste & Water": [r"water supply", r"\bMLD\b", r"sewerage", r"water treatment",
                      r"\bWTP\b"],
    "Water Resources": [r"irrigation", r"\bdam\b", r"canal", r"reservoir"],
    "Electricity Generation": [r"thermal power", r"power plant", r"\bMW\b", r"hydro"],
    "Transmission & Distribution": [r"transmission line", r"substation", r"\bkV\b"],
    "Aviation & Aviation Infrastructure": [r"\bairport", r"terminal building", r"runway"],
    "Construction": [r"data cent", r"\bbuilding\b", r"campus"],
    "Healthcare": [r"\bhospital", r"health cent"],
    "Education": [r"\bschool\b", r"\buniversity\b", r"\bcollege\b"],
}


def _populate_feature_bridge(db: Session, dpr_id, pages) -> None:
    """Fill dprs.sector_id and dprs.state from the document, for the risk model."""
    import re

    from api.app.models import Sector

    dpr = db.get(Dpr, dpr_id)
    if dpr is None:
        return
    sample = " ".join(p.full_text for p in pages[:30])

    if not dpr.state:
        best, best_n = None, 0
        for st in INDIAN_STATES:
            n = len(re.findall(rf"\b{re.escape(st)}\b", sample, re.I))
            if n > best_n:
                best, best_n = st, n
        if best_n >= 2:
            dpr.state = best

    if not dpr.sector_id:
        best, best_n = None, 0
        for name, cues in SECTOR_CUES.items():
            n = sum(len(re.findall(c, sample, re.I)) for c in cues)
            if n > best_n:
                best, best_n = name, n
        if best and best_n >= 3:
            sector = db.scalar(select(Sector).where(Sector.name == best))
            if sector is None:
                sector = Sector(name=best)
                db.add(sector)
                db.flush()
            dpr.sector_id = sector.id
    db.commit()
    log.info("feature bridge: dpr %s sector=%s state=%s", dpr_id,
             dpr.sector_id is not None, dpr.state)
