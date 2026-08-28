"""Generate the three synthetic sample DPRs:  python scripts/make_samples.py

These are test fixtures, not training data. Nothing is ever trained on them — see
answers.md Q2. They exist so the pipeline can be proven against documents whose defects
we know exactly, and they double as the demo.

The planted defects are REAL, not asserted. The bridge DPR's cash-flow table genuinely
computes to ~9.1% IRR against a claimed 14.2%, so F6's recomputation finds a true
discrepancy rather than one we hardcoded.
"""
from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpr_content import annexure_pages, filler_pages  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "samples"
OUT.mkdir(parents=True, exist_ok=True)

S = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=S["Heading1"], fontSize=17, spaceAfter=14)
H2 = ParagraphStyle("H2", parent=S["Heading2"], fontSize=13, spaceAfter=9)
BODY = ParagraphStyle("Body", parent=S["BodyText"], fontSize=10, leading=15)
TITLE = ParagraphStyle("T", parent=S["Title"], fontSize=22, alignment=TA_CENTER)

FILLER = (
    "The alignment has been fixed after detailed reconnaissance survey and consultation "
    "with the concerned district authorities. Soil investigation was carried out at "
    "chainages spaced at 500 m intervals and bore logs are enclosed at Annexure-II. "
    "The design conforms to the relevant IRC and IS codes in force. Quantities have been "
    "computed from the approved General Arrangement Drawings and cross-checked against "
    "the detailed measurement sheets."
)


def _grid(data, widths=None):
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde5ee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _filler_pages(n: int, start: int, heading: str) -> list:
    """Padding so the planted contradictions land on believable, far-apart pages."""
    out = []
    for i in range(n):
        out.append(Paragraph(f"{heading} {start + i}", H2))
        for _ in range(4):
            out.append(Paragraph(FILLER, BODY))
            out.append(Spacer(1, 5))
        out.append(PageBreak())
    return out


# --------------------------------------------------------------------------- bridge
def bridge_cashflow() -> list[tuple[int, float, float]]:
    """(year, cost, benefit) in Rs Cr. IRR of the net series is ~9.1%.

    The DPR will claim 14.2%. That claim is unsupported by this very table — which is
    exactly the defect F6 must catch, and it is arithmetically true, not staged.
    """
    rows = [(0, 165.0, 0.0), (1, 165.0, 0.0), (2, 82.5, 0.0)]
    for year in range(3, 23):
        rows.append((year, 4.2, 53.9))
    return rows


def build_bridge(path: Path) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="DPR - Brahmaputra Bridge",
                            author="Assam PWD", leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    f: list = []

    # ---- p.1-3 front matter
    f += [Spacer(1, 4 * cm),
          Paragraph("DETAILED PROJECT REPORT", TITLE), Spacer(1, 0.6 * cm),
          Paragraph("Construction of a Two-Lane Bridge across the Brahmaputra "
                    "at Dhubri, Assam", TITLE), Spacer(1, 2 * cm),
          Paragraph("Submitted by: Assam Public Works Department (Roads)", BODY),
          Paragraph("Executing Agency: Assam State Bridge Corporation Ltd.", BODY),
          Paragraph("Prepared by: Northeast Infra Consultants Pvt. Ltd.", BODY),
          PageBreak()]

    f += [Paragraph("Table of Contents", H1)]
    toc = [["Chapter", "Description", "Page"],
           ["1", "Executive Summary", "4"],
           ["2", "Project Background and Need", "6"],
           ["3", "Technical Design and Specifications", "12"],
           ["4", "Detailed Cost Abstract", "87"],
           ["5", "Financing Plan", "95"],
           ["6", "Implementation Schedule", "140"],
           ["7", "Rate Analysis", "142"],
           ["8", "Environmental and Social Aspects", "160"],
           ["9", "Financial and Economic Analysis", "61"],
           ["Annexure-IV", "Year-wise Cash Flow Statement", "198"],
           ["Annexure-V", "Cost Reconciliation Statement", "203"]]
    f += [_grid(toc, [2.2 * cm, 10 * cm, 2 * cm]), PageBreak()]
    f += [Paragraph("Abbreviations", H1),
          Paragraph("DPR - Detailed Project Report; IRC - Indian Roads Congress; "
                    "O&M - Operation and Maintenance; IRR - Internal Rate of Return; "
                    "BCR - Benefit Cost Ratio; DSR - Delhi Schedule of Rates.", BODY),
          PageBreak()]

    # ---- p.4  Executive summary  ← contradiction anchor 1
    f += [Paragraph("1. Executive Summary", H1),
          Paragraph("The proposed project envisages construction of a two-lane bridge of "
                    "total length 1,340 m across the river Brahmaputra at Dhubri, together "
                    "with approach roads of 4.6 km on either bank.", BODY), Spacer(1, 8),
          Paragraph("<b>The total project cost is estimated at Rs. 412.50 crore</b> "
                    "including all taxes and duties, at the price level of the current "
                    "financial year. The construction period is 30 months from the date of "
                    "award.", BODY), Spacer(1, 8),
          Paragraph("The project is expected to reduce travel distance by 62 km and save "
                    "approximately 2.4 hours per trip for freight traffic between the north "
                    "and south banks.", BODY),
          PageBreak()]
    f += _filler_pages(1, 5, "1.1 Salient Features - Sheet")

    # ---- p.6-60 background and design
    f += [Paragraph("2. Project Background and Need", H1),
          Paragraph(FILLER, BODY), PageBreak()]
    f += _filler_pages(5, 1, "2.1 Traffic Survey - Sheet")
    f += [Paragraph("3. Technical Design and Specifications", H1),
          Paragraph(FILLER, BODY), PageBreak()]
    f += _filler_pages(48, 1, "3.1 Design Computation Sheet")

    # ---- p.61  claimed IRR  ← the claim F6 will disprove
    f += [Paragraph("9. Financial and Economic Analysis", H1),
          Paragraph("The financial appraisal has been carried out over an evaluation "
                    "period of 22 years including the construction period, at a discount "
                    "rate of 12 per cent.", BODY), Spacer(1, 8),
          Paragraph("<b>The Internal Rate of Return of the project works out to 14.2 per "
                    "cent</b>, and the Benefit Cost Ratio is 1.64. The project is therefore "
                    "financially viable and is recommended for sanction.", BODY),
          Spacer(1, 8),
          Paragraph("The detailed year-wise cash flow statement on which this computation "
                    "is based is enclosed at Annexure-IV.", BODY),
          PageBreak()]
    f += _filler_pages(25, 1, "9.1 Sensitivity Analysis - Sheet")

    # ---- p.87  Cost abstract  ← contradiction anchor 2 (STALE figure)
    f += [Paragraph("4. Detailed Cost Abstract", H1),
          Paragraph("The abstract of cost for the project is summarised below. Quantities "
                    "are as per the approved drawings.", BODY), Spacer(1, 10)]
    abstract = [["S.No", "Description of Item", "Amount (Rs. Cr)"],
                ["1", "Substructure - piling, pile caps, piers", "128.40"],
                ["2", "Superstructure - PSC box girder", "146.80"],
                ["3", "Approach roads and embankment", "62.30"],
                ["4", "Protection works and river training", "38.90"],
                ["5", "Utilities, lighting and signage", "14.60"],
                ["6", "Contingencies @ 3%", "11.70"],
                ["7", "Supervision and quality control", "15.50"],
                ["", "TOTAL PROJECT COST", "418.20"]]
    f += [_grid(abstract, [1.6 * cm, 9.4 * cm, 3.6 * cm]), Spacer(1, 10),
          Paragraph("<b>The total project cost of the scheme is Rs. 418.20 crore.</b> "
                    "This abstract supersedes the preliminary estimate.", BODY),
          PageBreak()]
    f += _filler_pages(7, 1, "4.1 Detailed Measurement Sheet")

    # ---- p.95  Financing plan (note: no O&M funding section anywhere - planted gap)
    f += [Paragraph("5. Financing Plan", H1),
          Paragraph("The project is proposed to be funded through central assistance under "
                    "the scheme, with the state share met from the state budget.", BODY),
          Spacer(1, 10)]
    f += [_grid([["Source", "Share (%)", "Amount (Rs. Cr)"],
                 ["Central assistance", "80", "330.00"],
                 ["State share", "20", "82.50"],
                 ["", "Total", "412.50"]], [7 * cm, 3.3 * cm, 4.3 * cm]),
          PageBreak()]
    f += _filler_pages(44, 1, "5.1 Fund Release Schedule - Sheet")

    # ---- p.140  schedule
    f += [Paragraph("6. Implementation Schedule", H1),
          _grid([["Milestone", "Month"],
                 ["Award of work", "M0"],
                 ["Completion of substructure", "M14"],
                 ["Completion of superstructure", "M26"],
                 ["Commissioning", "M30"]], [9 * cm, 4 * cm]),
          PageBreak()]
    f += _filler_pages(1, 1, "6.1 Bar Chart - Sheet")

    # ---- p.142  Rate analysis  ← inflated bituminous rate (row 18)
    f += [Paragraph("7. Rate Analysis", H1),
          Paragraph("Rates have been derived from the prevailing schedule of rates with "
                    "appropriate lead and lift adjustments.", BODY), Spacer(1, 10)]
    rates = [["S.No", "Item of Work", "Unit", "Rate (Rs.)"]]
    base = [("Earthwork in excavation, ordinary soil", "cum", "312"),
            ("Plain cement concrete M15", "cum", "5,480"),
            ("Reinforced cement concrete M35", "cum", "8,940"),
            ("HYSD reinforcement steel Fe500", "MT", "72,600"),
            ("Structural steel work in built-up sections", "MT", "94,200"),
            ("Formwork for foundations", "sqm", "486"),
            ("Formwork for piers and abutments", "sqm", "612"),
            ("Granular sub-base, close graded", "cum", "1,842"),
            ("Wet mix macadam", "cum", "2,110"),
            ("Prime coat with bituminous primer", "sqm", "48"),
            ("Tack coat", "sqm", "22"),
            ("Dense bituminous macadam", "cum", "7,320"),
            ("Brick masonry in CM 1:6", "cum", "6,180"),
            ("Cement plaster 12 mm thick", "sqm", "268"),
            ("Providing and laying PSC girders", "MT", "88,400"),
            ("Elastomeric bearings", "each", "42,600"),
            ("Strip seal expansion joint", "rm", "18,900")]
    for i, (desc, unit, rate) in enumerate(base, start=1):
        rates.append([str(i), desc, unit, rate])
    # Row 18 — quoted ~38% above the DSR-2023 benchmark of Rs 6,700/cum
    rates.append(["18", "Bituminous concrete, grading II", "cum", "9,240"])
    rates.append(["19", "Road marking, thermoplastic", "sqm", "412"])
    f += [_grid(rates, [1.4 * cm, 8.6 * cm, 1.8 * cm, 2.8 * cm]), PageBreak()]
    f += _filler_pages(17, 1, "7.1 Lead Statement - Sheet")

    # ---- p.160  environment (clearance NOT obtained - negation defect)
    f += [Paragraph("8. Environmental and Social Aspects", H1),
          Paragraph("The project falls within the notified river bed area. "
                    "<b>Environmental clearance from the State Environment Impact "
                    "Assessment Authority is yet to be obtained</b> and the application "
                    "is under process.", BODY), Spacer(1, 8),
          Paragraph("Land acquisition for the approach roads is in progress. 62 per cent "
                    "of the required land has been acquired.", BODY),
          PageBreak()]
    f += _filler_pages(37, 1, "8.1 Social Impact Sheet")

    # ---- p.198  Annexure-IV cash flow  ← what F6 recomputes from
    f += [Paragraph("Annexure-IV: Year-wise Cash Flow Statement", H1),
          Paragraph("All figures in Rs. crore.", BODY), Spacer(1, 8)]
    cf = [["Year", "Capital Cost", "O&M Cost", "Gross Benefit", "Net Cash Flow"]]
    for year, cost, benefit in bridge_cashflow():
        cap = cost if year <= 2 else 0.0
        om = 0.0 if year <= 2 else cost
        cf.append([str(year), f"{cap:.2f}" if cap else "-",
                   f"{om:.2f}" if om else "-",
                   f"{benefit:.2f}" if benefit else "-",
                   f"{benefit - cost:.2f}"])
    f += [_grid(cf, [1.6 * cm, 3.2 * cm, 2.6 * cm, 3.2 * cm, 3.2 * cm]), PageBreak()]
    f += _filler_pages(4, 1, "Annexure-IV Continuation Sheet")

    # ---- p.203  Reconciliation  ← contradiction anchor 3 (agrees with p.4)
    f += [Paragraph("Annexure-V: Cost Reconciliation Statement", H1),
          Paragraph("The sanctioned estimate has been reconciled against the detailed "
                    "measurement sheets.", BODY), Spacer(1, 8),
          Paragraph("<b>Total project cost: Rs. 412.50 crore</b> (Rupees four hundred "
                    "twelve crore and fifty lakh only), inclusive of taxes.", BODY),
          PageBreak()]
    f += _filler_pages(6, 1, "Annexure-V Continuation Sheet")

    # --- back matter -----------------------------------------------------------------
    # Appended AFTER everything above so every planted defect keeps its documented page:
    # p.4 and p.203 (cost), p.61 (IRR claim), p.87 (stale cost), p.142 (rate),
    # p.160 (negation), p.198 (cash flow). The demo script cites those numbers.
    f += annexure_pages(38, "Annexure-VI: Detailed Measurement", seed=11)
    f += annexure_pages(34, "Annexure-VII: Bore Logs and Test Results", seed=12)
    f += annexure_pages(22, "Annexure-VIII: Land Schedule", seed=13)
    f += filler_pages(18, "Annexure-IX: Construction Programme", seed=14)

    doc.build(f)


# ---------------------------------------------------------------------- water supply
def build_watersupply(path: Path) -> None:
    """The control case. Complete, internally consistent, honest IRR. If the system
    flags this heavily, the system is wrong."""
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="DPR - Shillong Water Supply",
                            author="Meghalaya UDA", leftMargin=2 * cm, rightMargin=2 * cm)
    f: list = [Spacer(1, 4 * cm),
               Paragraph("DETAILED PROJECT REPORT", TITLE), Spacer(1, 0.6 * cm),
               Paragraph("Augmentation of Water Supply to Greater Shillong", TITLE),
               Spacer(1, 2 * cm),
               Paragraph("Submitted by: Meghalaya Urban Development Authority", BODY),
               PageBreak()]

    f += [Paragraph("1. Executive Summary", H1),
          Paragraph("The project provides for augmentation of the existing water supply "
                    "system serving Greater Shillong, raising capacity from 42 MLD to "
                    "68 MLD.", BODY), Spacer(1, 8),
          Paragraph("<b>The total project cost is estimated at Rs. 286.40 crore</b>, "
                    "inclusive of taxes. Implementation period is 24 months.", BODY),
          PageBreak()]

    f += [Paragraph("2. Cost Abstract", H1),
          _grid([["S.No", "Description", "Amount (Rs. Cr)"],
                 ["1", "Intake works and raw water main", "58.20"],
                 ["2", "Water treatment plant, 26 MLD", "94.60"],
                 ["3", "Clear water transmission main", "61.40"],
                 ["4", "Service reservoirs (4 nos.)", "38.90"],
                 ["5", "Distribution network augmentation", "24.10"],
                 ["6", "Contingencies @ 3%", "9.20"],
                 ["", "TOTAL PROJECT COST", "286.40"]], [1.6 * cm, 9.4 * cm, 3.6 * cm]),
          PageBreak()]

    f += [Paragraph("3. Operation and Maintenance Plan", H1),
          Paragraph("The annual O&M cost of the augmented system is estimated at "
                    "Rs. 8.60 crore, comprising power, chemicals, staff and routine "
                    "maintenance.", BODY), Spacer(1, 8),
          Paragraph("<b>O&M expenditure will be met from the water tariff revenue of the "
                    "Shillong Municipal Board, under budget head 2215-01-800.</b> The "
                    "Board has passed resolution No. 47 of 2026 committing this recurring "
                    "provision for the design life of the asset.", BODY),
          PageBreak()]

    f += [Paragraph("4. Environmental Clearance", H1),
          Paragraph("<b>Environmental clearance has been obtained</b> from the State "
                    "Environment Impact Assessment Authority vide letter no. "
                    "MEG/SEIAA/2026/118 dated 12 March 2026. A copy is enclosed.", BODY),
          Spacer(1, 8),
          Paragraph("Land required for the treatment plant is in the possession of the "
                    "Authority. No private land acquisition is involved.", BODY),
          PageBreak()]

    f += [Paragraph("5. Financial Analysis", H1),
          Paragraph("Evaluated over 25 years at a discount rate of 12 per cent, the "
                    "Internal Rate of Return is 13.8 per cent and the Benefit Cost Ratio "
                    "is 1.42. Assumptions are stated at Annexure-II.", BODY),
          PageBreak()]

    f += [Paragraph("6. Implementation Schedule and Risk Register", H1),
          _grid([["Milestone", "Month"], ["Award", "M0"], ["Intake works complete", "M10"],
                 ["WTP commissioned", "M20"], ["Full commissioning", "M24"]],
                [9 * cm, 4 * cm]), Spacer(1, 10),
          Paragraph("Principal risks identified: monsoon disruption to intake "
                    "construction, delay in power connection for the WTP, and cost "
                    "escalation in imported membrane modules. Mitigation measures are "
                    "detailed at Annexure-III.", BODY),
          PageBreak()]

    # A clean control has to be the same *size* as the defective one, or the engine could
    # be separating them on length rather than on content.
    f += filler_pages(52, "7. Hydraulic Design and Network Analysis", seed=21)
    f += filler_pages(44, "8. Treatment Process Design", seed=22)
    f += filler_pages(38, "9. Water Quality Testing", seed=23)
    f += filler_pages(30, "10. Environmental and Social Assessment", seed=24)
    f += annexure_pages(46, "Annexure-IV: Pipeline Schedule", seed=25)
    f += annexure_pages(40, "Annexure-V: Detailed Measurement", seed=26)
    f += annexure_pages(34, "Annexure-VI: Test Certificates", seed=27)
    f += filler_pages(22, "Annexure-VII: Consultation Records", seed=28)

    doc.build(f)


# ------------------------------------------------------------------------- scanned
def build_scanned(path: Path) -> None:
    """A long report whose front section is scanned.

    Deliberately NOT 300 image-only pages. Real DPRs of this kind are mixed — an older
    scanned proposal with typed annexures appended — and a wholly-scanned 300-page document
    would take ~15 minutes to OCR, which tests patience rather than the pipeline. The
    scanned block is large enough to exercise the OCR path properly and the rest is text.
    """
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont

    pages_text = [
        ["DETAILED PROJECT REPORT", "", "Upgradation of Tura-Williamnagar Road",
         "to Two-Lane Standard", "", "Meghalaya Public Works Department"],
        ["1. Executive Summary", "",
         "The project covers upgradation of 48.60 km of the",
         "Tura-Williamnagar road to two-lane standard with",
         "paved shoulders.", "",
         "The total project cost is estimated at Rs. 194.80 crore.",
         "The construction period is 24 months."],
        ["2. Cost Abstract", "",
         "Earthwork and embankment          38.20",
         "Granular sub-base and base        52.60",
         "Bituminous courses                61.40",
         "Cross drainage works              28.10",
         "Contingencies                     14.50",
         "                        TOTAL    194.80"],
    ]
    images = []
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Courier New.ttf", 30)
    except OSError:
        font = ImageFont.load_default()

    for lines in pages_text:
        img = PILImage.new("RGB", (1240, 1754), "white")   # ~150 DPI A4
        d = ImageDraw.Draw(img)
        y = 180
        for line in lines:
            d.text((110, y), line, fill=(15, 15, 15), font=font)
            y += 52
        # light speckle so it reads as a real scan rather than a clean render
        for n in range(900):
            x, yy = (n * 137) % 1240, (n * 613) % 1754
            d.point((x, yy), fill=(205, 205, 205))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        images.append(buf)

    # Drawn straight onto the canvas: a platypus frame reserves margins, so a
    # genuinely full-bleed page image will not fit through the flowable machinery.
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.utils import ImageReader

    scan_path = path.with_name("_scan_front.pdf")
    c = pdfcanvas.Canvas(str(scan_path), pagesize=A4)
    c.setTitle("DPR - Tura Road (scanned)")
    for _rep in range(9):                     # ~27 scanned pages
        for buf in images:
            buf.seek(0)
            c.drawImage(ImageReader(buf), 0, 0, width=A4[0], height=A4[1])
            c.showPage()
    c.save()

    # typed annexures, as a separate document then merged
    tail_path = path.with_name("_scan_tail.pdf")
    td = SimpleDocTemplate(str(tail_path), pagesize=A4, leftMargin=2 * cm,
                           rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    tf: list = []
    tf += filler_pages(70, "Chapter 3: Pavement Design", seed=41)
    tf += annexure_pages(80, "Annexure-I: Detailed Measurement", seed=42)
    tf += filler_pages(60, "Annexure-II: Cross Sections", seed=43)
    tf += annexure_pages(70, "Annexure-III: Rate Analysis", seed=44)
    td.build(tf)

    import pymupdf
    merged = pymupdf.open()
    for part in (scan_path, tail_path):
        with pymupdf.open(part) as src:
            merged.insert_pdf(src)
    merged.save(str(path))
    merged.close()
    scan_path.unlink(missing_ok=True)
    tail_path.unlink(missing_ok=True)


def main() -> None:
    build_bridge(OUT / "dpr_bridge_defective.pdf")
    build_watersupply(OUT / "dpr_watersupply_good.pdf")
    build_scanned(OUT / "dpr_road_scanned.pdf")

    import pymupdf
    print(f"\nGenerated in {OUT}:")
    for p in sorted(OUT.glob("*.pdf")):
        with pymupdf.open(p) as d:
            pages = d.page_count
            chars = sum(len(page.get_text().strip()) for page in d)
        kind = "TEXT" if chars > 500 else "SCAN (no text layer)"
        print(f"  {p.name:32} {pages:>4} pages  {p.stat().st_size // 1024:>5} KB  {kind}")


if __name__ == "__main__":
    main()
