"""Render sector DPRs from their real government templates.

Each report follows the chapter structure of the KIIFB template for its sector — Buildings
for the hospital, General for the water supply scheme — in that template's own numbering.
Copies of the templates are in docs/reference/.

Defects are declared per document rather than hardcoded, so the corpus exercises different
failure modes instead of the same four repeatedly. Every defect is arithmetically real: a
report that claims an IRR its own annexure does not support genuinely does not support it.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy_financial as npf
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.lib.units import cm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpr_content import annexure_pages, filler_pages          # noqa: E402
from dpr_specs import SPECS, Spec                              # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "samples"
OUT.mkdir(parents=True, exist_ok=True)

S = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=S["Heading1"], fontSize=15, spaceBefore=4, spaceAfter=10)
H2 = ParagraphStyle("h2", parent=S["Heading2"], fontSize=11.5, spaceBefore=9, spaceAfter=5)
BODY = ParagraphStyle("b", parent=S["BodyText"], fontSize=9.5, leading=14, spaceAfter=5)
TITLE = ParagraphStyle("t", parent=S["Title"], fontSize=18, alignment=TA_CENTER)


@dataclass
class Defects:
    """What is wrong with this particular report. Empty means a sound one."""
    cost_contradiction: bool = False   # summary and abstract disagree
    irr_unsupported: bool = False      # headline IRR the annexure does not support
    drop: tuple[str, ...] = ()         # chapter keys omitted entirely
    clearance_pending: bool = False    # a clearance stated as not yet obtained
    om_unfunded: bool = False          # O&M chapter present but names no funding source

    @property
    def any(self) -> bool:
        return (self.cost_contradiction or self.irr_unsupported or bool(self.drop)
                or self.clearance_pending or self.om_unfunded)


def grid(data, widths=None):
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8f9aa4")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde5ee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def cashflow(spec: Spec, benefit: float) -> list[tuple[int, float, float]]:
    rows = [(y, c, 0.0) for y, c in spec.capex]
    start = len(spec.capex)
    om = round(sum(c for _y, c in spec.capex) * 0.021, 2)
    for y in range(start, spec.horizon + 1):
        rows.append((y, om, round(benefit * (1.0 - (y - start) * 0.004), 2)))
    return rows


def solve_benefit(spec: Spec, target_irr: float) -> float:
    lo, hi = 1.0, 400.0
    for _ in range(90):
        mid = (lo + hi) / 2
        irr = npf.irr([b - a for _y, a, b in cashflow(spec, mid)])
        if irr is None or (irr * 100) < target_irr:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def build(spec: Spec, path: Path, defects: Defects) -> dict:
    sound_irr, bad_irr = 13.8, 7.6
    benefit = solve_benefit(spec, bad_irr if defects.irr_unsupported else sound_irr)
    cf = cashflow(spec, benefit)
    true_irr = float(npf.irr([b - a for _y, a, b in cf]) * 100)
    claimed_irr = 14.6 if defects.irr_unsupported else round(true_irr, 1)
    abstract_total = spec.stale_cost if defects.cost_contradiction else spec.cost_crore

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.1 * cm, rightMargin=2.1 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"DPR — {spec.title}", author=spec.applicant)
    f: list = []

    # cover
    f += [Spacer(1, 3.4 * cm), Paragraph("DETAILED PROJECT REPORT", TITLE),
          Spacer(1, 0.5 * cm), Paragraph(spec.title, TITLE), Spacer(1, 0.3 * cm),
          Paragraph(spec.subtitle, BODY), Spacer(1, 1.6 * cm),
          Paragraph(f"Submitted by: {spec.applicant}", BODY),
          Paragraph(f"Implementing agency / SPV: {spec.agency}", BODY),
          Paragraph(f"DPR prepared by: {spec.consultant}", BODY),
          Paragraph(f"Prepared in accordance with the {spec.template}.", BODY),
          PageBreak()]

    # contents
    toc = [["Sl.No.", "Contents", "Page"], ["1", "SALIENT FEATURES", "3"],
           ["2", "EXECUTIVE SUMMARY", "6"]]
    for ch in spec.chapters:
        if ch.key and ch.key in defects.drop:
            continue
        toc.append([ch.number, ch.title, ""])
    for a, _d, _n in spec.annexures:
        toc.append(["", a.split(" — ")[0], ""])
    f += [Paragraph("TABLE OF CONTENTS", H1),
          grid(toc, [1.8 * cm, 11.6 * cm, 1.8 * cm]), PageBreak()]

    # 1. salient features
    f += [Paragraph("1. SALIENT FEATURES", H1),
          grid([["Sl.", "Particular", "Detail"]] + spec.salient,
               [1.1 * cm, 5.4 * cm, 8.7 * cm]), PageBreak()]
    f += filler_pages(2, "1.1 Salient Features (continued)", seed=101,
                      sector=spec.sector)

    # 2. executive summary — carries the headline cost
    f += [Paragraph("2. EXECUTIVE SUMMARY", H1),
          Paragraph(f"The project provides for {spec.subtitle.lower()}. "
                    f"{spec.chapters[0].body[0][:220] if spec.chapters[0].body else ''}", BODY),
          Paragraph(f"<b>The total project cost is estimated at Rs. {spec.cost_crore} "
                    f"crore</b> inclusive of all taxes and duties, at the price level of "
                    f"the current financial year. The implementation period is "
                    f"{spec.duration_months} months from the zero date.", BODY),
          PageBreak()]
    f += filler_pages(2, "2.1 Executive Summary (continued)", seed=102,
                      sector=spec.sector)

    # chapters
    seed = 110
    for ch in spec.chapters:
        seed += 1
        if ch.key and ch.key in defects.drop:
            # Omitted entirely. The filler keeps the page count comparable so detection is
            # not simply noticing that one report is shorter.
            f += filler_pages(ch.filler + 2, f"{ch.number}A Supplementary Notes",
                              seed=seed, sector=spec.sector)
            continue

        f += [Paragraph(f"{ch.number} {ch.title}", H1)]
        for para in ch.body:
            f += [Paragraph(para, BODY)]

        if ch.key == "cost":
            f += [Paragraph("Rates are derived from the Schedule of Rates in force with "
                            "lead and lift adjustments. Items outside the Schedule have "
                            "been rate-analysed and are placed at the detailed estimate.",
                            BODY), Spacer(1, 6),
                  grid([["Sl.", "Description of item", "Amount (Rs. crore)"]]
                       + spec.cost_heads
                       + [["", "TOTAL PROJECT COST", abstract_total]],
                       [1.3 * cm, 10.0 * cm, 4.3 * cm]),
                  Spacer(1, 8),
                  Paragraph(f"<b>The total project cost of the scheme is "
                            f"Rs. {abstract_total} crore.</b>", BODY)]

        elif ch.key == "cba":
            f += [Paragraph(f"The appraisal has been carried out over a {spec.horizon} year "
                            f"evaluation period at a discount rate of 12 per cent.", BODY),
                  Spacer(1, 5),
                  grid([["Investment criterion", "Value"],
                        ["Internal Rate of Return", f"{claimed_irr:.1f} per cent"],
                        ["Net Present Value at 12 per cent", "Rs. 74.20 crore"],
                        ["Benefit Cost Ratio", "1.44"],
                        ["Payback period", "12.1 years"]], [8.6 * cm, 7.0 * cm]),
                  Spacer(1, 6),
                  Paragraph(f"<b>The Internal Rate of Return of the project works out to "
                            f"{claimed_irr:.1f} per cent</b>, against the threshold of 12 "
                            f"per cent applied to projects of this class. The project is "
                            f"therefore viable and is recommended for sanction.", BODY),
                  Paragraph("The year-wise cash flow statement on which this computation "
                            "rests is enclosed at the annexure.", BODY)]

        elif ch.key == "risk":
            f += [grid([["Sl.", "Risk", "Likelihood", "Impact", "Mitigation"],
                        ["1", "Delay in balance land acquisition", "Medium", "High",
                         "Award proceedings advanced ahead of the zero date"],
                        ["2", "Escalation in cement and steel", "Medium", "Medium",
                         "Price adjustment clause in the contract"],
                        ["3", "Monsoon disruption to earthwork", "High", "Medium",
                         "Programme earthwork in the dry season"],
                        ["4", "Contractor default", "Low", "High",
                         "Pre-qualification and performance security"],
                        ["5", "Utility shifting delay", "Medium", "Medium",
                         "Deposit work sanctioned in advance"]],
                       [1.1 * cm, 4.4 * cm, 2.1 * cm, 1.8 * cm, 6.2 * cm]),
                  Spacer(1, 6),
                  Paragraph("Each risk has been assessed for likelihood and impact and a "
                            "mitigation plan documented covering avoidance, transfer and "
                            "elimination as appropriate.", BODY)]

        elif ch.key == "schedule":
            f += [Paragraph(f"The zero date is the date of issue of the work order. The "
                            f"implementation period is {spec.duration_months} months.", BODY),
                  Spacer(1, 5),
                  grid([["WBS", "Milestone", "Month from zero date"],
                        ["1.0", "Award and mobilisation", "M0 – M2"],
                        ["2.0", "Site preparation complete", "M4"],
                        ["3.0", "Substructure / foundation complete",
                         f"M{spec.duration_months // 3}"],
                        ["4.0", "Superstructure complete",
                         f"M{spec.duration_months * 2 // 3}"],
                        ["5.0", "Services and finishes",
                         f"M{spec.duration_months - 3}"],
                        ["6.0", "Testing and commissioning", f"M{spec.duration_months}"]],
                       [2.2 * cm, 8.4 * cm, 5.0 * cm])]

        elif ch.key == "clearances":
            status_env = ("Application under process" if defects.clearance_pending
                          else "Obtained, 12 February 2026")
            f += [grid([["Sl.", "Clearance", "Authority", "Status"],
                        ["1", "Consent to establish", "State Pollution Control Board",
                         status_env],
                        ["2", "Building permit / layout approval", "Local body",
                         "Obtained, 3 March 2026"],
                        ["3", "Fire safety clearance", "Directorate of Fire Services",
                         "Obtained, 19 March 2026"],
                        ["4", "Ground water abstraction", "CGWA",
                         "Not applicable"]],
                       [1.1 * cm, 5.0 * cm, 4.8 * cm, 4.7 * cm])]
            if defects.clearance_pending:
                f += [Spacer(1, 6),
                      Paragraph("<b>Consent to establish from the State Pollution Control "
                                "Board is yet to be obtained.</b> The application was "
                                "submitted and is under process.", BODY)]

        elif ch.key == "om":
            f += [Paragraph(f"The completed asset will be handed over to {spec.agency} for "
                            f"operation and maintenance.", BODY)]
            if defects.om_unfunded:
                f += [Paragraph("The annual recurring requirement for operation and "
                                "maintenance is estimated at Rs. 9.80 crore. The source of "
                                "this recurring provision is yet to be identified and will "
                                "be worked out in consultation with the Finance "
                                "Department.", BODY)]
            else:
                f += [Paragraph("<b>The annual recurring requirement for operation and "
                                "maintenance is estimated at Rs. 9.80 crore, to be met from "
                                "the maintenance budget head of the department.</b> The "
                                "Finance Department has conveyed concurrence to the "
                                "inclusion of this recurring provision.", BODY),
                      Paragraph("A routine maintenance schedule covering inspection, "
                                "servicing and periodic replacement is placed at the end of "
                                "this chapter.", BODY)]

        f += [PageBreak()]
        f += filler_pages(int(ch.filler * 1.9) + 3,
                          f"{ch.number}.x {ch.title.title()} — Working Papers",
                          seed=seed, sector=spec.sector)

    # annexures
    seed = 200
    for i, (heading, blurb, pages) in enumerate(spec.annexures):
        seed += 1
        f += [Paragraph(heading, H1), Paragraph(blurb, BODY), PageBreak()]
        if "ESTIMATE" in heading or "NETWORK" in heading or "TEST" in heading:
            f += annexure_pages(int(pages * 1.35), heading.split(" — ")[0], seed=seed,
                                sector=spec.sector)
        else:
            f += filler_pages(int(pages * 1.35), heading.split(" — ")[0], seed=seed,
                              sector=spec.sector)
        # the cash flow rides with the detailed estimate
        if "DETAILED ESTIMATE" in heading:
            f += [Paragraph(f"{heading.split(' — ')[0]}-A — YEAR-WISE CASH FLOW STATEMENT",
                            H1),
                  Paragraph("All figures in Rs. crore. Year 0 is the year of "
                            "commencement.", BODY), Spacer(1, 6)]
            rows = [["Year", "Capital cost", "O&M cost", "Gross benefit", "Net cash flow"]]
            for y, out_, ben in cf:
                cap = out_ if y < len(spec.capex) else 0.0
                om = 0.0 if y < len(spec.capex) else out_
                rows.append([str(y), f"{cap:.2f}" if cap else "-",
                             f"{om:.2f}" if om else "-", f"{ben:.2f}" if ben else "-",
                             f"{ben - out_:.2f}"])
            f += [grid(rows, [1.8 * cm, 3.4 * cm, 2.8 * cm, 3.4 * cm, 3.4 * cm]),
                  PageBreak()]

    doc.build(f)
    return {"claimed_irr": claimed_irr, "true_irr": true_irr,
            "cost": spec.cost_crore, "abstract": abstract_total}


PROFILES = [
    ("hospital", "sound", Defects()),
    ("hospital", "defective", Defects(cost_contradiction=True,
                                      drop=("risk", "quality"),
                                      clearance_pending=True)),
    ("water", "sound", Defects()),
    ("water", "defective", Defects(irr_unsupported=True, om_unfunded=True,
                                   drop=("environment",))),
]


def main() -> None:
    import pymupdf

    print("Generated from the KIIFB templates in docs/reference/:\n")
    for slug, variant, defects in PROFILES:
        spec = SPECS[slug]
        path = OUT / f"dpr_{slug}_{variant}.pdf"
        meta = build(spec, path, defects)
        with pymupdf.open(path) as d:
            pages = d.page_count
        flaws = []
        if defects.cost_contradiction:
            flaws.append(f"cost {meta['cost']} vs {meta['abstract']}")
        if defects.irr_unsupported:
            flaws.append(f"IRR claims {meta['claimed_irr']:.1f}% "
                         f"vs {meta['true_irr']:.1f}%")
        if defects.drop:
            flaws.append("omits " + ", ".join(defects.drop))
        if defects.clearance_pending:
            flaws.append("clearance pending")
        if defects.om_unfunded:
            flaws.append("O&M source unidentified")
        print(f"  {path.name:30} {pages:>4} pages   "
              f"{'; '.join(flaws) if flaws else 'no planted defects'}")


if __name__ == "__main__":
    main()
