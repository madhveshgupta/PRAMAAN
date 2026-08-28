"""The appraisal note — a tamper-evident PDF export.

The question a public-sector system faces years later is not "was this decision correct"
but "can you reconstruct how it was reached". So the note pins everything that produced
it: the rubric version, the engine version, the model version, and a SHA-256 of its own
content printed on the document.

Every finding carries its page citation. A reviewer's note that cites a page is usable in
an appraisal file; one that cites a score is not.
"""
from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, Image)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.spider import SpiderChart

_S = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_S["Heading1"], fontSize=18, spaceAfter=8, textColor=colors.HexColor("#0f172a"))
H2 = ParagraphStyle("h2", parent=_S["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1e293b"))
H3 = ParagraphStyle("h3", parent=_S["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#334155"))
BODY = ParagraphStyle("b", parent=_S["BodyText"], fontSize=9.5, leading=14, alignment=TA_LEFT, textColor=colors.HexColor("#334155"))
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8, textColor=colors.HexColor("#64748b"))

SEVERITY_COLOUR = {
    "critical": colors.HexColor("#e11d48"),
    "high": colors.HexColor("#2563eb"),
    "medium": colors.HexColor("#d97706"),
    "low": colors.HexColor("#475569"),
    "info": colors.HexColor("#0ea5e9"),
}


def _kv(rows: list[tuple[str, str]]) -> Table:
    t = Table([[Paragraph(f"<b>{k}</b>", BODY), Paragraph(v, BODY)] for k, v in rows],
              colWidths=[5.2 * cm, 11 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e3e8ec")),
    ]))
    return t


def _content_digest(dpr, assessment, findings, reviews, risk, outcome) -> str:
    """Hash what the note SAYS, not how the PDF encodes it.

    Hashing the rendered bytes was the obvious first move and it does not work: ReportLab
    compresses content streams, so a placeholder cannot be found and swapped afterwards,
    and two renders of identical data differ anyway (timestamps, object ordering).

    Hashing a canonical projection of the underlying data is also the more useful
    guarantee. An auditor can recompute it from the database years later and confirm the
    note reflects the assessment it claims to — which is the actual question, rather than
    whether two byte streams happen to match.
    """
    import json

    payload = {
        "dpr": str(dpr.id),
        "title": dpr.title,
        "status": dpr.status,
        "assessment": None if assessment is None else {
            "overall": assessment.overall_score,
            "completeness": assessment.completeness_score,
            "consistency": assessment.consistency_score,
            "cost_realism": assessment.cost_realism_score,
            "financial": assessment.financial_score,
            "rubric_version": assessment.rubric_version,
            "engine_version": assessment.engine_version,
        },
        "findings": [
            {"rule_id": f.rule_id, "severity": f.severity, "status": f.status,
             "title": f.title,
             "pages": sorted(e["page"] for e in (f.evidence or [])),
             "review": reviews.get(f.id)}
            for f in sorted(findings, key=lambda x: x.rule_id)
        ],
        "risk": None if risk is None else {
            "model_version": risk.model_version,
            "delay_probability": risk.delay_probability,
        },
        "outcome": None if outcome is None else {
            "peer_count": outcome.peer_count,
            "p50": outcome.cost_p50, "p80": outcome.cost_p80, "p95": outcome.cost_p95,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_appraisal_note(*, dpr, assessment, findings, reviews, risk, outcome,
                         generated_by: str) -> tuple[bytes, str]:
    """Render the note. Returns (pdf_bytes, sha256_of_content)."""
    import os
    digest = _content_digest(dpr, assessment, findings, reviews, risk, outcome)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"Appraisal note — {dpr.title}")
    f: list = []
    now = datetime.now(timezone.utc)

    # ---- 1. Logo & Header
    logo_path = os.path.join(os.path.dirname(__file__), "../../../web/public/pramaan-logo.png")
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=4*cm, height=1.2*cm, kind='proportional')
            img.hAlign = 'LEFT'
            f.append(img)
            f.append(Spacer(1, 15))
        except Exception:
            pass

    f.append(Paragraph("Appraisal Note", H1))
    f.append(Paragraph("Advisory assessment. Sanctioning authority rests with the "
                       "competent authority.", SMALL))
    f.append(Spacer(1, 10))

    f.append(_kv([
        ("Project", dpr.title),
        ("DPR reference", str(dpr.id)),
        ("Status at generation", dpr.status.replace("_", " ").title()),
        ("Generated", now.strftime("%d %B %Y, %H:%M UTC")),
        ("Generated by", generated_by),
    ]))
    f.append(Spacer(1, 15))

    # ---- 2. Executive Summary & Assessment Profile
    if assessment is not None:
        f.append(Paragraph("Executive Summary", H2))
        
        # Pull counts for critical and high
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for fd in findings:
            counts[fd.severity] = counts.get(fd.severity, 0) + 1
        
        summary_text = (f"This detailed project report contains <b>{len(findings)}</b> findings in total. "
                        f"There are <b><font color='#e11d48'>{counts['critical']} critical</font></b> and "
                        f"<b><font color='#2563eb'>{counts['high']} high</font></b> severity issues that "
                        f"require immediate attention.")
        f.append(Paragraph(summary_text, BODY))
        f.append(Spacer(1, 10))

        # Render Assessment Table & Radar Chart side-by-side using a Table
        f.append(Paragraph("Assessment Profile", H3))
        
        # Chart
        drawing = Drawing(150, 150)
        sc = SpiderChart()
        sc.x = 25
        sc.y = 25
        sc.width = 100
        sc.height = 100
        # Replace None with 0 for rendering
        c1 = assessment.completeness_score or 0
        c2 = assessment.consistency_score or 0
        c3 = assessment.cost_realism_score or 0
        c4 = assessment.financial_score or 0
        
        sc.data = [[c1, c2, c3, c4]]
        sc.labels = ['Completeness', 'Consistency', 'Cost Realism', 'Financial']
        sc.strands[0].fillColor = colors.Color(14/255.0, 165/255.0, 233/255.0, alpha=0.2)
        sc.strands[0].strokeColor = colors.HexColor("#0284c7")
        sc.strands[0].strokeWidth = 2
        drawing.add(sc)
        
        # Table
        rows = [["Component", "Score"]]
        for label, val in [
            ("Overall", assessment.overall_score),
            ("Completeness", assessment.completeness_score),
            ("Consistency", assessment.consistency_score),
            ("Cost realism", assessment.cost_realism_score),
            ("Financial sanity", assessment.financial_score),
        ]:
            rows.append([label, "not scored" if val is None else f"{val:.1f}"])
        t = Table(rows, colWidths=[6 * cm, 2.5 * cm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155"))
        ]))
        
        # Combine Chart and Table in one master layout table
        layout_t = Table([[t, drawing]], colWidths=[9 * cm, 6 * cm], hAlign="LEFT")
        layout_t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        
        f.append(layout_t)
        f.append(Spacer(1, 15))

    # ---- 3. Findings grouped by Severity
    f.append(Paragraph(f"Detailed Findings", H2))
    if not findings:
        f.append(Paragraph("No findings were raised.", BODY))
    else:
        # Group findings
        grouped = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
        for fd in findings:
            grouped[fd.severity].append(fd)
        
        for sev in ["critical", "high", "medium", "low", "info"]:
            if not grouped[sev]:
                continue
                
            f.append(Paragraph(f"<font color='{SEVERITY_COLOUR[sev]}'>{sev.upper()} SEVERITY</font>", H3))
            
            for fd in grouped[sev]:
                pages = ", ".join(f"p.{e['page']}" for e in (fd.evidence or []))
                cite = f" &nbsp;<font color='#0284c7'>[{pages}]</font>" if pages else \
                       " &nbsp;<font color='#94a3b8'>[no specific page — see note]</font>"
                decision = reviews.get(fd.id)
                block = [
                    Paragraph(f"<b>{fd.title}</b>{cite}", BODY),
                    Paragraph(fd.message, BODY),
                ]
                if decision:
                    block.append(Paragraph(
                        f"<i>Decision: <b>{decision['decision'].title().replace('_', ' ')}</b>"
                        f"{' — ' + decision['note'] if decision.get('note') else ''}</i>", SMALL))
                block.append(Spacer(1, 8))
                f.append(KeepTogether(block))

    # ---- 4. Risk Analysis
    if risk or outcome:
        f.append(Paragraph("Risk analysis", H2))
        if risk:
            f.append(Paragraph(
                f"Schedule delay probability "
                f"<b>{(risk.delay_probability or 0) * 100:.0f}%</b> "
                f"(model {risk.model_version}). Principal factors:", BODY))
            for d in (risk.delay_drivers or risk.shap_drivers or [])[:4]:
                f.append(Paragraph(f"• {d.get('plain_english')} "
                                   f"<font color='#64748b'>({d.get('direction')})</font>",
                                   BODY))
        if outcome:
            crore = 10_000_000_00
            f.append(Spacer(1, 5))
            f.append(Paragraph(
                f"Of <b>{outcome.peer_count}</b> comparable projects, 80% finished at or "
                f"below <b>Rs {outcome.cost_p80 / crore:,.2f} crore</b> "
                f"(P50 Rs {outcome.cost_p50 / crore:,.2f} Cr, "
                f"P95 Rs {outcome.cost_p95 / crore:,.2f} Cr). These are observed outcomes "
                f"of real projects, not a simulation.", BODY))

    # ---- 5. Integrity Block
    f.append(Spacer(1, 20))
    f.append(Paragraph("Integrity", H2))
    f.append(Paragraph(
        "The SHA-256 below is computed over the assessment this note reports. An auditor "
        "can recompute it from the record and confirm the note reflects what the system actually found.", SMALL))
    f.append(Spacer(1, 4))
    f.append(Paragraph(f"<font face='Courier' size='7.5'>SHA-256: {digest}</font>", BODY))
    f.append(Spacer(1, 3))
    f.append(Paragraph(
        f"Rubric {getattr(assessment, 'rubric_version', 'n/a')} · "
        f"engine {getattr(assessment, 'engine_version', 'n/a')} · "
        f"risk model {getattr(risk, 'model_version', 'n/a')}", SMALL))

    doc.build(f)
    return buf.getvalue(), digest
