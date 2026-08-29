"""Assessment stage: extracted fields in, scored findings out.

Every finding produced here carries at least one evidence anchor (invariant #1) and a
status drawn from PASS / PARTIAL / INSUFFICIENT_EVIDENCE / FLAGGED. There is no FAIL —
the system reports what it found and how strong the evidence is; a human decides what
that means (invariant #4).

No machine learning anywhere in this stage. That is deliberate: the quality score has to
be defensible rule by rule, and rules are.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.app.models import (Assessment, AssessmentCheck, Document, Dpr,
                            ExtractedField, Finding, Job, Setting)
from worker import queue
from worker.scoring import (checklist, completeness, consistency, financial,
                            template_check)

log = logging.getLogger("pramaan.assess")

ENGINE_VERSION = "assess-1.0"


def _setting(db: Session, key: str, default):
    row = db.get(Setting, key)
    if row is None:
        return default
    return row.value.get("v", default) if isinstance(row.value, dict) else default


def _clear(db: Session, dpr_id) -> None:
    # Children before parents. The FKs cascade, but being explicit keeps the order of
    # deletion readable rather than implied.
    db.execute(delete(Finding).where(Finding.dpr_id == dpr_id))
    db.execute(delete(AssessmentCheck).where(AssessmentCheck.dpr_id == dpr_id))
    db.execute(delete(Assessment).where(Assessment.dpr_id == dpr_id))


SEVERITY_FOR_STATUS = {"insufficient_evidence": {"critical": "critical", "high": "high",
                                                 "medium": "medium", "low": "low"},
                       "partial": {"critical": "high", "high": "medium",
                                   "medium": "low", "low": "info"}}


def handle_assess(db: Session, job: Job) -> None:
    doc = db.get(Document, job.document_id)
    if doc is None or doc.status != "ready":
        raise ValueError("document not ready for assessment")
    dpr_id = doc.dpr_id

    _clear(db, dpr_id)
    db.commit()

    strong = float(_setting(db, "evidence_strong_threshold", 0.75))
    tolerance = float(_setting(db, "contradiction_tolerance_pct", 0.5))
    weights = _setting(db, "component_weights",
                       {"completeness": .25, "consistency": .25,
                        "cost_realism": .25, "financial": .25})

    assessment = Assessment(dpr_id=dpr_id,
                            rubric_version=completeness.load_rubric()["version"],
                            engine_version=ENGINE_VERSION)
    db.add(assessment)
    db.flush()

    # (finding, the check_id of the checklist row it came out of). Every finding must
    # name its row: one that does not is a finding the checklist would hide.
    findings: list[tuple[Finding, str]] = []
    checks: list[checklist.Check] = []

    # ---- 4a completeness -------------------------------------------------------------
    report = completeness.assess_completeness(db, doc.id, strong)
    comp_score, items = report.score, report.items
    log.info("scored against profile '%s' (confidence %.2f)", report.profile,
             report.profile_confidence)
    # Frozen here, not re-derived on read: this is the record of which checklist the
    # decision was actually made against.
    assessment.rubric_version = f"{completeness.load_rubric()['version']}/{report.profile}"
    assessment.rubric_profile = report.profile
    assessment.rubric_profile_label = report.profile_label
    assessment.rubric_profile_confidence = report.profile_confidence
    assessment.rubric_provenance = report.provenance

    # Checked before anything else: if the form is not filled in, every other finding is
    # about the shape of the document rather than its content.
    tmpl = template_check.check(db, doc.id)
    if tmpl.is_template:
        findings.append((Finding(
            assessment_id=assessment.id, dpr_id=dpr_id, severity="critical",
            category="data_quality", status="flagged",
            rule_id="F3-UNFILLED-TEMPLATE",
            title="Document appears to be an unfilled model template",
            message=tmpl.message,
            suggested_action="Return to the applicant for completion before appraisal.",
            evidence=[]), "F3-UNFILLED-TEMPLATE"))

    if report.warning:
        findings.append((Finding(
            assessment_id=assessment.id, dpr_id=dpr_id, severity="high",
            category="data_quality", status="flagged",
            rule_id="F3-PROFILE-UNCERTAIN",
            title="Document type could not be confidently identified",
            message=report.warning,
            suggested_action="Confirm the document type before relying on the "
                             "compliance score.",
            evidence=[]), "F3-PROFILE-UNCERTAIN"))

    checks += checklist.document_quality_checks(tmpl, report)
    checks += checklist.completeness_checks(report)

    for r in items:
        if r.status == "pass":
            continue                      # a satisfied requirement is not a finding
        severity = SEVERITY_FOR_STATUS[r.status][r.severity]
        if r.note:
            message = r.note
        elif r.status == "insufficient_evidence":
            message = (f"No evidence of the '{r.section}' section was found anywhere in "
                       f"this document. That is not proof the requirement is unmet — the "
                       f"section may exist under a title we did not recognise.")
        else:
            message = (f"Evidence for '{r.section}' was found on page "
                       f"{r.evidence.page if r.evidence else '?'}, but it is weaker than "
                       f"the threshold for a clear pass (score {r.score:.2f}). Some of the "
                       f"content this section should contain was not located alongside it.")
        findings.append((Finding(
            assessment_id=assessment.id, dpr_id=dpr_id, severity=severity,
            category="completeness", status=r.status,
            rule_id=f"F3-{r.item_id.upper()}",
            title=f"{r.section} — {r.status.replace('_', ' ')}",
            message=message,
            suggested_action=None,
            evidence=[r.evidence.to_dict()] if r.evidence else [],
            score_impact=0.0), f"F3-{r.item_id.upper()}"))

    # ---- 4b consistency --------------------------------------------------------------
    cons = consistency.check_consistency(db, dpr_id, tolerance)
    cons_findings = cons.contradictions
    checks += checklist.consistency_checks(cons)
    for c in cons_findings:
        findings.append((Finding(
            assessment_id=assessment.id, dpr_id=dpr_id, severity="high",
            category="consistency", status="flagged",
            rule_id="F4-NUMERIC-DIVERGENCE",
            title="Cost figure inconsistent across document",
            message=consistency.format_message(c),
            suggested_action="Reconcile the figures and reissue the affected annexure.",
            evidence=[e.to_dict() for _v, e in c.values]), "F4-COST-AGREEMENT"))
    cons_score = 100.0 if not cons_findings else max(0.0, 100.0 - 35.0 * len(cons_findings))

    # ---- 4c cost realism — BLOCKED ---------------------------------------------------
    # F5 needs published Schedule of Rates data that has not been obtained. We do not
    # ship invented benchmark rates, so the component is reported as unavailable rather
    # than scored on nothing. See IMPLEMENTATION-FINAL/M4_FINAL.md §1.
    cost_score = None
    checks += checklist.cost_realism_checks()

    # ---- 4d financial ----------------------------------------------------------------
    fin = financial.recompute(db, doc.id)
    fin_score = 100.0
    # Hoisted out of the branch chain below: all three financial checklist rows cite the
    # table, and the "not attempted" rows quote the tolerance they would have used.
    tol = float(_setting(db, "irr_tolerance_pp", 1.0))
    table_anchor = (financial.anchor_for_table(db, doc.id, fin.cashflow)
                    if fin.cashflow else None)
    claimed = db.scalar(select(ExtractedField).where(
        ExtractedField.dpr_id == dpr_id,
        ExtractedField.field_key == "claimed_irr_pct"))
    claimed_pct = (float(claimed.value_numeric)
                   if claimed is not None and claimed.value_numeric is not None else None)
    claim_anchor = (claimed.evidence[0]
                    if claimed is not None and claimed.evidence else None)
    checks += checklist.financial_checks(fin, claimed_pct, claim_anchor, table_anchor, tol)

    if fin.problems and fin.cashflow is None:
        # Nothing to point at and nothing to complain about: many DPRs legitimately carry
        # no year-wise cash flow. Absence is handled by the completeness rubric, not here.
        log.info("no cash-flow table in dpr %s — financial recomputation not applicable",
                 dpr_id)
    elif fin.problems:
        findings.append((Finding(
            assessment_id=assessment.id, dpr_id=dpr_id, severity="info",
            category="data_quality", status="flagged",
            rule_id="F6-CASHFLOW-UNREADABLE",
            title="Cash-flow table could not be reliably read",
            message=("The financial recomputation was not attempted because the cash-flow "
                     "table did not pass its data-quality checks: "
                     + "; ".join(fin.problems)
                     + ". This is a limitation of our reading of the document, NOT a "
                       "finding about the project's finances."),
            evidence=[table_anchor.to_dict()] if table_anchor else []), "F6-CASHFLOW-TABLE"))
    elif fin.computed_irr is not None:
        if claimed_pct is not None:
            gap = abs(claimed_pct - fin.computed_irr)
            if gap > tol:
                evidence = []
                if claim_anchor:
                    evidence.append(claim_anchor)              # the claim
                if table_anchor:
                    evidence.append(table_anchor.to_dict())    # what contradicts it
                findings.append((Finding(
                    assessment_id=assessment.id, dpr_id=dpr_id, severity="critical",
                    category="financial", status="flagged",
                    rule_id="F6-IRR-UNSUPPORTED",
                    title="Claimed IRR not supported by the document's own figures",
                    message=(f"The report claims an IRR of {claimed_pct}%. "
                             f"Recomputed from the cash-flow statement in this same "
                             f"document: {fin.computed_irr}%. "
                             f"Difference {gap:.2f} percentage points."
                             + (" Multiple IRR roots exist for this series "
                                f"({fin.irr_roots}) — manual review required."
                                if fin.irr_ambiguous else "")),
                    suggested_action="Reconcile the headline IRR with the cash-flow annexure.",
                    evidence=evidence), "F6-IRR-RECOMPUTED"))
                fin_score = max(0.0, 100.0 - min(60.0, gap * 10))

        if fin.irr_ambiguous:
            findings.append((Finding(
                assessment_id=assessment.id, dpr_id=dpr_id, severity="medium",
                category="financial", status="flagged",
                rule_id="F6-IRR-AMBIGUOUS",
                title="IRR is ambiguous for this cash-flow series",
                message=(f"The series changes sign more than once, so several IRR values "
                         f"satisfy it: {fin.irr_roots}. Reporting a single figure would be "
                         f"misleading. Manual review required."),
                evidence=[table_anchor.to_dict()] if table_anchor else []), "F6-IRR-AMBIGUOUS"))

    # ---- aggregate -------------------------------------------------------------------
    parts = {"completeness": comp_score, "consistency": cons_score, "financial": fin_score}
    if cost_score is not None:
        parts["cost_realism"] = cost_score
    live = {k: v for k, v in parts.items() if v is not None}
    total_w = sum(weights.get(k, 0.25) for k in live)
    overall = sum(v * weights.get(k, 0.25) for k, v in live.items()) / total_w if total_w else 0.0

    assessment.completeness_score = comp_score
    assessment.consistency_score = cons_score
    assessment.cost_realism_score = cost_score
    assessment.financial_score = round(fin_score, 1)
    if tmpl.is_template:
        # Structure without content is not quality. Cap the headline score so a blank
        # form cannot present as a strong submission.
        overall = min(overall, 35.0)
    assessment.overall_score = round(overall, 1)

    # Writes the checklist first, then the findings linked to the rows that produced them.
    # The anchoring rule invariant #1 needs — and the record of anything withheld under it
    # — lives in checklist.persist, so a withheld finding is visible to a reviewer instead
    # of only to whoever reads the log.
    kept = checklist.persist(db, assessment, checks, findings)

    dpr = db.get(Dpr, dpr_id)
    if dpr:
        dpr.status = "under_review"
    queue.enqueue(db, "predict", dpr_id=dpr_id, document_id=doc.id)
    db.commit()

    log.info("assessed dpr %s: overall %.1f (completeness %.1f, consistency %.1f, "
             "financial %.1f, cost_realism %s) — %s findings",
             dpr_id, overall, comp_score, cons_score, fin_score,
             "BLOCKED" if cost_score is None else cost_score, len(kept))
