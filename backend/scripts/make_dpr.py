"""Generate infrastructure DPRs against a real government template.

Structure follows the KIIFB "Template for Preparation of Detailed Project Report (DPR) in
r/o Bridges" — chapters 1 through 3.17 and Annexures I-VII, in the template's own order and
wording. A copy of that template is at docs/reference/. Survey content follows IRC:SP:19.

These are synthetic documents and labelled as such. What is NOT invented is the *shape*:
every chapter here exists because the template requires it, which is the difference between
a test fixture and a guess about what a DPR looks like.

Two are produced:
  * a sound report, which should score well; and
  * one carrying four defects, so detection can be measured rather than asserted.

The defects are arithmetically real. The defective report's own cash-flow annexure computes
to a different IRR than the figure it claims.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy_financial as npf
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dpr_content import annexure_pages, filler_pages  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "samples"
OUT.mkdir(parents=True, exist_ok=True)

S = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=S["Heading1"], fontSize=15, spaceBefore=4, spaceAfter=10)
H2 = ParagraphStyle("h2", parent=S["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6)
H3 = ParagraphStyle("h3", parent=S["Heading3"], fontSize=10.5, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("b", parent=S["BodyText"], fontSize=9.5, leading=14, spaceAfter=5)
TITLE = ParagraphStyle("t", parent=S["Title"], fontSize=19, alignment=TA_CENTER)


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


def cashflow(defective: bool) -> list[tuple[int, float, float]]:
    """(year, outflow, benefit) in Rs crore over a 30-year evaluation period.

    Sound: returns ~13.5%, a plausible figure for a bridge. Defective: the same annexure
    computes to ~7.9% while the report's chapter 3.9 claims 14.2%.
    """
    rows = [(0, 148.0, 0.0), (1, 165.0, 0.0), (2, 99.5, 0.0)]
    # Calibrated so the sound report returns ~13.5%, clearing the 12% threshold it
    # claims to clear. A report that fails its own stated test would itself be a
    # finding, which would muddy what the defective version is meant to demonstrate.
    base = 74.12 if not defective else 47.83
    for y in range(3, 31):
        decay = 1.0 - (y - 3) * 0.004
        rows.append((y, 5.8, round(base * decay, 2)))
    return rows


def irr_of(rows) -> float:
    return float(npf.irr([b - a for _y, a, b in rows]) * 100)


# --------------------------------------------------------------------------- the document
def build(path: Path, *, defective: bool) -> dict:
    cf = cashflow(defective)
    true_irr = irr_of(cf)
    claimed_irr = 14.2 if defective else round(true_irr, 1)
    cost_headline = "412.50"
    cost_stale = "418.20" if defective else cost_headline

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=2.1 * cm, rightMargin=2.1 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="DPR — Two-lane bridge across the Brahmaputra at Dhubri",
        author="Assam Public Works Department")
    f: list = []

    # ---- cover -----------------------------------------------------------------------
    f += [Spacer(1, 3.4 * cm),
          Paragraph("DETAILED PROJECT REPORT", TITLE), Spacer(1, 0.5 * cm),
          Paragraph("Construction of a Two-Lane Major Bridge across the River Brahmaputra "
                    "at Dhubri, including Approach Roads", TITLE), Spacer(1, 1.8 * cm),
          Paragraph("Submitted by: Assam Public Works Department (Roads &amp; Bridges)", BODY),
          Paragraph("Implementing agency / SPV: Assam State Bridge Corporation Limited", BODY),
          Paragraph("DPR prepared by: Northeast Infrastructure Consultants Private Limited", BODY),
          Paragraph("Prepared in accordance with the Template for Preparation of Detailed "
                    "Project Report in respect of Bridges, and IRC:SP:19 for surveys and "
                    "investigations.", BODY),
          PageBreak()]

    # ---- table of contents -----------------------------------------------------------
    f += [Paragraph("Table of Contents", H1)]
    toc = [["Sl.No.", "Contents", "Page"],
           ["1", "SALIENT FEATURES", "3"],
           ["2", "EXECUTIVE SUMMARY", "6"],
           ["3", "CHAPTERS", ""],
           ["3.1", "INTRODUCTION", "8"],
           ["3.2", "STATUS OF FEASIBILITY STUDIES", "14"],
           ["3.3", "REQUIREMENT / DEMAND ANALYSIS", "18"],
           ["3.4", "ENGINEERING SURVEYS AND INVESTIGATIONS", "26"],
           ["3.5", "FUNCTIONAL DESIGN", "58"],
           ["3.6", "ENGINEERING DESIGN", "74"],
           ["3.7", "FINANCIAL ESTIMATES & COST PROJECTIONS", "126"],
           ["3.8", "REVENUE STREAMS", "140"],
           ["3.9", "COST BENEFIT ANALYSIS & INVESTMENT CRITERIA", "146"],
           ["3.10", "ENVIRONMENTAL & SUSTAINABILITY ASPECTS", "156"],
           ["3.11", "RISK ASSESSMENT AND MITIGATION MEASURES", "170"],
           ["3.12", "PROJECT MANAGEMENT ORGANISATION", "178"],
           ["3.13", "CONTRACT MANAGEMENT STRATEGY", "184"],
           ["3.14", "IMPLEMENTATION SCHEDULE & WBS", "190"],
           ["3.15", "STATUTORY CLEARANCES", "198"],
           ["3.16", "QUALITY MANAGEMENT PLAN", "206"],
           ["3.17", "OPERATIONS & MAINTENANCE PLAN", "214"],
           ["", "ANNEXURE I — KEY MAP OF THE PROJECT LOCATION", "220"],
           ["", "ANNEXURE II — APPROVED ALIGNMENT DRAWING", "228"],
           ["", "ANNEXURE III — GENERAL ARRANGEMENT DRAWING", "240"],
           ["", "ANNEXURE IV — DETAILED ESTIMATE", "252"],
           ["", "ANNEXURE V — GEO-TECHNICAL INVESTIGATION REPORT", "286"],
           ["", "ANNEXURE VI — HYDRAULIC INVESTIGATION REPORT", "312"],
           ["", "ANNEXURE VII — COPIES OF STATUTORY APPROVALS", "330"]]
    f += [grid(toc, [1.8 * cm, 11.6 * cm, 1.8 * cm]), PageBreak()]

    # ---- 1. SALIENT FEATURES (the template lists 27 entries) --------------------------
    f += [Paragraph("1. SALIENT FEATURES", H1)]
    sal = [["Sl.", "Particular", "Detail"],
           ["1", "Title of the project", "Construction of a two-lane major bridge across "
                                        "the Brahmaputra at Dhubri with approach roads"],
           ["2", "District / Taluk / Local body / Constituency",
                 "Dhubri / Dhubri Sadar / Dhubri Municipal Board / Dhubri LAC"],
           ["3", "Implementing agency / SPV", "Assam State Bridge Corporation Limited"],
           ["4", "DPR prepared by", "Northeast Infrastructure Consultants Pvt. Ltd."],
           ["5", "Project outlay", f"Rs. {cost_headline} crore"],
           ["6", "Budget provision", "Rs. 120.00 crore in the current financial year"],
           ["7", "Budget speech reference", "Para 74, State Budget Speech 2026-27"],
           ["8", "Administrative sanction", "AS accorded vide G.O. (Rt) No. 812/2026/PWD "
                                            "dated 14 April 2026"],
           ["9", "Nature of the project", "New bridge"],
           ["10", "Present status of existing bridges / roads",
                  "Nearest crossing is a seasonal ferry; the next fixed crossing is 62 km "
                  "upstream"],
           ["11", "Need for the project", "To provide an all-weather crossing and remove a "
                                          "62 km detour for freight and emergency traffic"],
           ["12", "Length of the bridge / approaches", "1,340 m bridge; 4.60 km approaches"],
           ["13", "Carriageway width", "2-lane, 7.5 m with 1.5 m footpaths"],
           ["14", "Design discharge / HFL", "63,400 cumec; HFL 30.42 m"],
           ["15", "Land required / acquisition status",
                  "18.62 ha; 62 per cent acquired, balance under award"],
           ["16", "Basis of estimate and Schedule of Rates",
                  "Assam PWD SoR 2025-26 with lead and lift; detailed estimate attached at "
                  "Annexure IV"],
           ["17", "Details of revenue streams", "Nil — free-use public asset"],
           ["18", "Cost Benefit Analysis (BCR)", "1.64"],
           ["19", "Details of project risks", "Chapter 3.11 — 14 risks identified"],
           ["20", "Project management organisation", "Chapter 3.12"],
           ["21", "Contract management strategy", "EPC — Chapter 3.13"],
           ["22", "Implementation Schedule and WBS",
                  "30 months from zero date — Chapter 3.14"],
           ["23", "Details of statutory clearances", "Chapter 3.15"],
           ["24", "Quality control infrastructure and mechanism", "Chapter 3.16"],
           ["25", "O&amp;M arrangements after completion", "Chapter 3.17"],
           ["26", "Details of attached drawings", "Annexures I, II and III"],
           ["27", "Other attachments", "Annexures IV to VII"]]
    f += [grid(sal, [1.1 * cm, 5.4 * cm, 8.7 * cm]), PageBreak()]
    f += filler_pages(2, "1.1 Salient Features (continued)", seed=1)

    # ---- 2. EXECUTIVE SUMMARY — headline cost anchor ---------------------------------
    f += [Paragraph("2. EXECUTIVE SUMMARY", H1),
          Paragraph("The project provides for construction of a two-lane major bridge of "
                    "total length 1,340 m across the river Brahmaputra at Dhubri, together "
                    "with 4.60 km of approach roads on either bank and associated river "
                    "training works.", BODY),
          Paragraph(f"<b>The total project cost is estimated at Rs. {cost_headline} crore</b> "
                    f"inclusive of all taxes and duties, at the price level of the current "
                    f"financial year. The construction period is 30 months from the zero "
                    f"date.", BODY),
          Paragraph("The project removes a 62 km detour for traffic between the north and "
                    "south banks and provides the first all-weather crossing in the "
                    "district. The benefit cost ratio works out to 1.64.", BODY),
          PageBreak()]
    f += filler_pages(2, "2.1 Executive Summary (continued)", seed=2)

    # ---- 3.1 INTRODUCTION -------------------------------------------------------------
    f += [Paragraph("3.1 INTRODUCTION", H1),
          Paragraph("The project area lies on the Brahmaputra in Dhubri district of western "
                    "Assam, at the confluence of the alluvial plains with the Meghalaya "
                    "plateau margin. The terrain is flat with an average elevation of 28 m "
                    "above mean sea level. The regional geology comprises recent alluvium "
                    "of Holocene age overlying Tertiary sediments.", BODY),
          Paragraph("3.1.1 Project Definition, Concept and Scope", H2),
          Paragraph("The project comprises the following sub-components: a 1,340 m "
                    "pre-stressed concrete box girder bridge on well foundations; 4.60 km "
                    "of two-lane approach roads with paved shoulders; river training and "
                    "bank protection works on both banks; and associated drainage, lighting "
                    "and signage.", BODY),
          Paragraph("<b>Land required is 18.62 hectares, of which 11.54 hectares has been "
                    "acquired.</b> Acquisition of the balance 7.08 hectares is under award "
                    "under the Right to Fair Compensation and Transparency in Land "
                    "Acquisition, Rehabilitation and Resettlement Act, 2013.", BODY),
          Paragraph("3.1.2 Project Background", H2),
          Paragraph("There is no existing bridge at the proposed location. Crossing is "
                    "presently by a seasonal ferry operated by the Inland Water Transport "
                    "Department, which is suspended during high flood and in dense fog. The "
                    "nearest fixed crossing is 62 km upstream.", BODY),
          Paragraph("3.1.3 Project Details", H2),
          Paragraph("The bridge is located at chainage 0+000 to 1+340 on the proposed "
                    "alignment. The adjoining land on the south bank is predominantly "
                    "agricultural; the north bank approach passes through the periphery of "
                    "Dhubri town. Two schools and one place of worship lie within 200 m of "
                    "the alignment and have been avoided by a realignment of 140 m at "
                    "chainage 3+200. Existing utilities along the approach include an 11 kV "
                    "overhead line and a 200 mm water main, both to be shifted.", BODY),
          Paragraph("3.1.4 Objective and Scope of the Work", H2),
          Paragraph("The objective is to provide an all-weather road connection between the "
                    "north and south banks. The main works are the bridge substructure and "
                    "superstructure, approach roads and embankment, river training works, "
                    "and utility shifting.", BODY),
          PageBreak()]
    f += filler_pages(5, "3.1.5 Site Appreciation", seed=3)

    # ---- 3.2 FEASIBILITY --------------------------------------------------------------
    f += [Paragraph("3.2 STATUS OF FEASIBILITY STUDIES", H1),
          Paragraph("A pre-feasibility study was carried out in 2021 by the State Technical "
                    "Agency, which examined three crossing locations and recommended the "
                    "present site on hydraulic and geotechnical grounds. The study concluded "
                    "the project to be technically feasible with a preliminary cost of "
                    "Rs. 358 crore at 2021 price level. The present estimate reflects "
                    "revised quantities following detailed investigation and price "
                    "escalation to the current year.", BODY),
          PageBreak()]
    f += filler_pages(3, "3.2.1 Pre-feasibility Findings", seed=4)

    # ---- 3.3 DEMAND ANALYSIS ----------------------------------------------------------
    f += [Paragraph("3.3 REQUIREMENT / DEMAND ANALYSIS", H1),
          Paragraph("The problem addressed is the absence of an all-weather crossing. "
                    "Approximately 42,000 residents of eleven revenue villages on the north "
                    "bank depend on the ferry for access to the district hospital, the "
                    "sub-divisional court and the wholesale market, all located on the south "
                    "bank.", BODY),
          Paragraph("Classified traffic volume counts were carried out over seven "
                    "continuous days at three locations in March 2026, in accordance with "
                    "IRC:SP:19. Origin-destination and axle load surveys were carried out "
                    "concurrently.", BODY), Spacer(1, 6),
          grid([["Vehicle class", "Existing ferry (PCU/day)", "Diverted (PCU/day)",
                 "Generated (PCU/day)", "Total on opening"],
                ["Two-wheeler", "1,840", "620", "410", "2,870"],
                ["Car / jeep / taxi", "760", "1,240", "380", "2,380"],
                ["Bus", "110", "240", "60", "410"],
                ["LCV", "290", "480", "140", "910"],
                ["Truck (2-axle)", "180", "760", "210", "1,150"],
                ["Truck (multi-axle)", "40", "520", "180", "740"],
                ["", "Total", "", "", "8,460"]],
               [3.4 * cm, 3.2 * cm, 2.9 * cm, 2.9 * cm, 2.8 * cm]),
          Spacer(1, 6),
          Paragraph("Traffic has been projected at 6.2 per cent per annum for the first ten "
                    "years and 4.8 per cent thereafter, derived from district vehicle "
                    "registration growth over the period 2016 to 2025 and the state domestic "
                    "product series. Projected traffic on the design year is 27,400 PCU per "
                    "day, within the capacity of a two-lane facility.", BODY),
          PageBreak()]
    f += filler_pages(6, "3.3.1 Origin-Destination Survey", seed=5)

    # ---- 3.4 SURVEYS AND INVESTIGATIONS ----------------------------------------------
    f += [Paragraph("3.4 ENGINEERING SURVEYS AND INVESTIGATIONS", H1),
          Paragraph("3.4.1 Topographic and Levelling Survey", H2),
          Paragraph("Topographic survey was carried out by differential GPS supplemented by "
                    "total station traverse. Twelve ground control points were established "
                    "along the alignment at intervals not exceeding 500 m and connected to "
                    "GTS benchmark no. 412/A at Dhubri, reduced level 27.842 m. Levelling "
                    "was closed with a misclosure of 8 mm over a 6.4 km circuit, within the "
                    "permissible limit.", BODY),
          Paragraph("3.4.2 Soil and Materials Survey", H2),
          Paragraph("Eighteen boreholes were drilled to depths between 45 m and 62 m by "
                    "rotary drilling. Standard penetration tests were conducted at 1.5 m "
                    "intervals and undisturbed samples collected in cohesive strata. "
                    "California Bearing Ratio tests on subgrade samples returned soaked CBR "
                    "values between 4.2 and 6.8 per cent.", BODY), Spacer(1, 5),
          grid([["Borehole", "Chainage", "Depth (m)", "Founding strata", "SPT N at founding"],
                ["BH-01", "0+040", "52.0", "Dense sand", "48"],
                ["BH-04", "0+320", "58.5", "Dense sand", "52"],
                ["BH-09", "0+700", "62.0", "Dense sand with gravel", "58"],
                ["BH-14", "1+080", "54.5", "Dense sand", "46"],
                ["BH-18", "1+320", "47.0", "Stiff clay over sand", "41"]],
               [2.4 * cm, 2.4 * cm, 2.4 * cm, 4.6 * cm, 3.6 * cm]),
          Spacer(1, 6),
          Paragraph("Borrow areas have been identified at three locations within a lead of "
                    "11 km, with a combined assessed quantity of 4.2 lakh cubic metres "
                    "against a requirement of 2.8 lakh cubic metres. Coarse aggregate is "
                    "available from an approved quarry at a lead of 34 km. Construction "
                    "water will be drawn from the river under permission from the Water "
                    "Resources Department.", BODY),
          PageBreak()]
    f += filler_pages(26, "3.4.3 Survey and Investigation Records", seed=6)

    # ---- 3.5 FUNCTIONAL DESIGN --------------------------------------------------------
    f += [Paragraph("3.5 FUNCTIONAL DESIGN", H1),
          Paragraph("Three alignment options were examined. Option A crosses at the "
                    "narrowest section but requires a 2.1 km approach through built-up "
                    "area with 38 structures affected. Option B, the proposed alignment, "
                    "crosses 900 m downstream where the channel is stable and the approach "
                    "traverses agricultural land with 6 structures affected. Option C avoids "
                    "all structures but adds 3.4 km of approach and crosses a zone of active "
                    "bank erosion.", BODY), Spacer(1, 5),
          grid([["Criterion", "Option A", "Option B (proposed)", "Option C"],
                ["Bridge length (m)", "1,180", "1,340", "1,510"],
                ["Approach length (km)", "2.10", "4.60", "8.00"],
                ["Structures affected", "38", "6", "0"],
                ["Land acquisition (ha)", "9.40", "18.62", "31.80"],
                ["Bank stability", "Marginal", "Stable", "Active erosion"],
                ["Estimated cost (Rs cr)", "396", "412.50", "489"]],
               [4.0 * cm, 3.4 * cm, 4.0 * cm, 3.4 * cm]),
          Spacer(1, 6),
          Paragraph("Option B is proposed. Although not the shortest crossing, it minimises "
                    "displacement, sits on a stable reach with a documented history of "
                    "hydraulic behaviour, and permits an economical span arrangement.", BODY),
          PageBreak()]
    f += filler_pages(14, "3.5.1 Alignment Studies", seed=7)

    # ---- 3.6 ENGINEERING DESIGN -------------------------------------------------------
    f += [Paragraph("3.6 ENGINEERING DESIGN", H1),
          Paragraph("The design conforms to IRC:6-2017 for loads and stresses, IRC:112-2020 "
                    "for concrete road bridges, IRC:78-2014 for foundations and substructure, "
                    "and IS:456-2000. The limit state method has been adopted throughout.",
                    BODY), Spacer(1, 5),
          grid([["Element", "Provision"],
                ["Superstructure", "Pre-stressed concrete box girder, 22 spans"],
                ["Span arrangement", "2 × 40 m + 18 × 60 m + 2 × 40 m"],
                ["Substructure", "RCC circular piers, 3.5 m diameter"],
                ["Foundation", "Well foundation, 9.0 m external diameter"],
                ["Founding level", "RL −24.5 m, 6.0 m into dense sand"],
                ["Bearings", "Pot-PTFE"],
                ["Expansion joints", "Strip seal, 80 mm movement"],
                ["Design load", "IRC Class 70R and Class A"],
                ["Seismic zone", "Zone V, importance factor 1.5"],
                ["Design life", "100 years"]], [5.2 * cm, 10.4 * cm]),
          PageBreak()]
    f += filler_pages(46, "3.6.1 Design Computations", seed=8)

    # ---- 3.7 FINANCIAL ESTIMATES — the cost abstract ---------------------------------
    f += [Paragraph("3.7 FINANCIAL ESTIMATES AND COST PROJECTIONS", H1),
          Paragraph("Rates are derived from the Assam PWD Schedule of Rates 2025-26 with "
                    "lead and lift adjustments. Items not covered by the Schedule have been "
                    "rate-analysed and are placed at Annexure IV. The abstract of cost is "
                    "summarised below.", BODY), Spacer(1, 6)]
    abstract = [["Sl.", "Description of item", "Amount (Rs. crore)"],
                ["1", "Substructure — wells, well caps, piers", "128.40"],
                ["2", "Superstructure — PSC box girder", "146.80"],
                ["3", "Approach roads and embankment", "62.30"],
                ["4", "River training and bank protection", "38.90"],
                ["5", "Utilities, lighting and signage", "14.60"],
                ["6", "Contingencies at 3 per cent", "11.70"],
                ["7", "Quality control and supervision", "9.80"],
                ["", "TOTAL PROJECT COST", cost_stale]]
    f += [grid(abstract, [1.3 * cm, 10.0 * cm, 4.3 * cm]), Spacer(1, 8),
          Paragraph(f"<b>The total project cost of the scheme is Rs. {cost_stale} crore.</b> "
                    f"This abstract supersedes the preliminary estimate of the 2021 "
                    f"pre-feasibility study.", BODY),
          PageBreak()]
    f += filler_pages(12, "3.7.1 Rate Analysis", seed=9)

    # ---- 3.8 REVENUE ------------------------------------------------------------------
    f += [Paragraph("3.8 REVENUE STREAMS", H1),
          Paragraph("The bridge is proposed as a toll-free public asset. No user charge is "
                    "envisaged. Accordingly the appraisal in Chapter 3.9 is an economic "
                    "rather than a financial one, and the benefit stream comprises vehicle "
                    "operating cost savings, travel time savings and accident cost savings "
                    "rather than revenue.", BODY),
          PageBreak()]
    f += filler_pages(4, "3.8.1 Benefit Stream Basis", seed=10)

    # ---- 3.9 COST BENEFIT — the IRR claim --------------------------------------------
    f += [Paragraph("3.9 COST BENEFIT ANALYSIS AND INVESTMENT CRITERIA", H1),
          Paragraph("The economic appraisal has been carried out over a 30-year evaluation "
                    "period including the construction period, at a social discount rate of "
                    "12 per cent. Benefits comprise vehicle operating cost savings from the "
                    "removal of the 62 km detour, travel time savings valued at the "
                    "prevailing wage rate, and ferry operating cost avoided.", BODY),
          Spacer(1, 5),
          grid([["Investment criterion", "Value"],
                ["Economic Internal Rate of Return", f"{claimed_irr:.1f} per cent"],
                ["Net Present Value at 12 per cent", "Rs. 96.40 crore"],
                ["Benefit Cost Ratio", "1.64"],
                ["Payback period", "11.4 years"]], [8.6 * cm, 7.0 * cm]),
          Spacer(1, 6),
          Paragraph(f"<b>The Internal Rate of Return of the project works out to "
                    f"{claimed_irr:.1f} per cent</b>, against the threshold of 12 per cent "
                    f"applied for projects of this class. The project is therefore "
                    f"economically viable and is recommended for sanction.", BODY),
          Paragraph("The detailed year-wise cash flow statement on which this computation is "
                    "based is enclosed at Annexure IV-A.", BODY),
          PageBreak()]
    f += filler_pages(8, "3.9.1 Sensitivity Analysis", seed=11)

    # ---- 3.10 ENVIRONMENT — negation defect goes here --------------------------------
    f += [Paragraph("3.10 ENVIRONMENTAL AND SUSTAINABILITY ASPECTS", H1),
          Paragraph("The project falls within the notified river bed area of the "
                    "Brahmaputra. An Environmental Impact Assessment has been carried out by "
                    "an accredited consultant. Principal impacts are turbidity during well "
                    "sinking, loss of 212 riparian trees, and temporary disruption to "
                    "fishing activity.", BODY)]
    if defective:
        f += [Paragraph("<b>Environmental clearance from the State Environment Impact "
                        "Assessment Authority is yet to be obtained</b> and the application "
                        "is under process. Forest clearance is not required as no notified "
                        "forest land is involved.", BODY)]
    else:
        f += [Paragraph("<b>Environmental clearance has been obtained</b> from the State "
                        "Environment Impact Assessment Authority vide letter no. "
                        "ASM/SEIAA/2026/0417 dated 8 March 2026, a copy of which is at "
                        "Annexure VII. Forest clearance is not required as no notified "
                        "forest land is involved.", BODY)]
    f += [Paragraph("Compensatory afforestation of 424 saplings in a ratio of 1:2 is "
                    "provided for in the estimate. Sustainability measures include use of "
                    "ground granulated blast furnace slag in mass concrete and solar "
                    "lighting on the approaches.", BODY),
          PageBreak()]
    f += filler_pages(12, "3.10.1 Environmental Management Plan", seed=12)

    # ---- 3.11 RISK --------------------------------------------------------------------
    f += [Paragraph("3.11 RISK ASSESSMENT AND MITIGATION MEASURES", H1),
          grid([["Sl.", "Risk", "Likelihood", "Impact", "Mitigation"],
                ["1", "Monsoon disruption to well sinking", "High", "High",
                 "Programme well sinking in the lean period"],
                ["2", "Delay in balance land acquisition", "Medium", "High",
                 "Award proceedings advanced; possession of 62% already taken"],
                ["3", "Escalation in steel and cement", "Medium", "Medium",
                 "Price adjustment clause in the contract"],
                ["4", "Change in river course", "Low", "High",
                 "River training works and annual bathymetric survey"],
                ["5", "Contractor default", "Low", "High",
                 "Pre-qualification and performance security"]],
               [1.1 * cm, 4.4 * cm, 2.1 * cm, 1.8 * cm, 6.2 * cm]),
          Spacer(1, 6),
          Paragraph("Fourteen risks have been identified in total. Each has been assessed "
                    "for likelihood and impact, and a mitigation plan documented covering "
                    "avoidance, transfer and elimination as appropriate.", BODY),
          PageBreak()]
    f += filler_pages(6, "3.11.1 Risk Register", seed=13)

    # ---- 3.12-3.13 --------------------------------------------------------------------
    f += [Paragraph("3.12 PROJECT MANAGEMENT ORGANISATION", H1),
          Paragraph("The project will be implemented by Assam State Bridge Corporation "
                    "Limited through a dedicated Project Implementation Unit headed by a "
                    "Chief Engineer. The unit comprises one Superintending Engineer, three "
                    "Executive Engineers and supporting technical staff. An Authority "
                    "Engineer will be appointed for construction supervision. Monthly "
                    "progress review will be conducted by the Principal Secretary, PWD.",
                    BODY),
          PageBreak()]
    f += filler_pages(5, "3.12.1 Organisation Structure", seed=14)
    f += [Paragraph("3.13 CONTRACT MANAGEMENT STRATEGY", H1),
          Paragraph("The work is proposed to be executed on an Engineering, Procurement and "
                    "Construction basis in a single package. Bidding will follow the "
                    "standard bidding document of the Public Works Department. A price "
                    "adjustment clause for steel, cement and bitumen is proposed in view of "
                    "the 30-month construction period. Arbitration will be governed by the "
                    "Arbitration and Conciliation Act, 1996.", BODY),
          PageBreak()]
    f += filler_pages(5, "3.13.1 Contract Packaging", seed=15)

    # ---- 3.14 SCHEDULE ----------------------------------------------------------------
    f += [Paragraph("3.14 IMPLEMENTATION SCHEDULE AND WORK BREAKDOWN STRUCTURE", H1),
          Paragraph("The zero date is taken as the date of issue of the work order. The "
                    "construction period is 30 months.", BODY), Spacer(1, 5),
          grid([["WBS", "Milestone", "Month from zero date"],
                ["1.0", "Award of work and mobilisation", "M0 – M2"],
                ["2.0", "Completion of land acquisition", "M4"],
                ["3.0", "Well foundations complete", "M14"],
                ["4.0", "Substructure complete", "M20"],
                ["5.0", "Superstructure complete", "M27"],
                ["6.0", "Approach roads complete", "M28"],
                ["7.0", "Testing and commissioning", "M30"]],
               [2.2 * cm, 8.4 * cm, 5.0 * cm]),
          Spacer(1, 6),
          Paragraph("The critical path runs through well sinking, which is dependent on the "
                    "lean-season window. A bar chart is placed at the end of this chapter.",
                    BODY),
          PageBreak()]
    f += filler_pages(6, "3.14.1 Bar Chart and Critical Path", seed=16)

    # ---- 3.15 CLEARANCES --------------------------------------------------------------
    f += [Paragraph("3.15 STATUTORY CLEARANCES", H1),
          grid([["Sl.", "Clearance", "Authority", "Status"],
                ["1", "Environmental clearance", "State EIAA",
                 "Under process" if defective else "Obtained, 8 March 2026"],
                ["2", "Forest clearance", "State Forest Dept.", "Not applicable"],
                ["3", "Waterway clearance", "Inland Waterways Authority",
                 "Obtained, 22 January 2026"],
                ["4", "Railway NOC", "NF Railway", "Not applicable"],
                ["5", "Pollution Control Board consent", "Assam PCB",
                 "Consent to establish obtained"],
                ["6", "Approval of river training works", "Water Resources Dept.",
                 "Obtained, 3 February 2026"]],
               [1.1 * cm, 5.0 * cm, 4.8 * cm, 4.7 * cm]),
          PageBreak()]
    f += filler_pages(6, "3.15.1 Clearance Correspondence", seed=17)

    # ---- 3.16 QUALITY -----------------------------------------------------------------
    f += [Paragraph("3.16 QUALITY MANAGEMENT PLAN", H1),
          Paragraph("Quality assurance will be exercised by the Authority Engineer through a "
                    "site laboratory established at the project site and equipped in "
                    "accordance with the Ministry's guidelines. Third party quality control "
                    "will be entrusted to an institution of national repute, proposed to be "
                    "the National Institute of Technology, Silchar. A quality assurance plan "
                    "covering the frequency of testing for each item of work is placed at "
                    "the end of this chapter.", BODY),
          PageBreak()]
    f += filler_pages(6, "3.16.1 Testing Frequency Schedule", seed=18)

    # ---- 3.17 O&M — omitted entirely in the defective version ------------------------
    if not defective:
        f += [Paragraph("3.17 OPERATIONS AND MAINTENANCE PLAN", H1),
              Paragraph("The completed bridge will be handed over to the Dhubri Roads "
                        "Division of the Public Works Department for operation and "
                        "maintenance.", BODY),
              Paragraph("<b>The annual recurring requirement for operation and maintenance "
                        "is estimated at Rs. 1.86 crore, to be met from budget head "
                        "3054-04-105 (Maintenance and Repairs — Bridges) of the Public "
                        "Works Department.</b> The Finance Department has conveyed its "
                        "concurrence to the inclusion of this recurring provision vide "
                        "letter no. FIN/PWD/2026/338 dated 19 May 2026.", BODY),
              Paragraph("A routine maintenance schedule covering bearing inspection, "
                        "expansion joint servicing, drainage clearance and painting is "
                        "placed at the end of this chapter. Principal foreseeable issues are "
                        "silt accumulation at the guide bunds and periodic bearing "
                        "replacement at year 25.", BODY),
              PageBreak()]
        f += filler_pages(5, "3.17.1 Maintenance Schedule", seed=19)
    else:
        # The chapter is simply absent. This is the most common real omission and the one
        # that most reliably shortens an asset's life.
        f += filler_pages(6, "3.16.2 Quality Assurance Records", seed=19)

    # ---- ANNEXURES --------------------------------------------------------------------
    f += [Paragraph("ANNEXURE I — KEY MAP OF THE PROJECT LOCATION", H1),
          Paragraph("Key map showing the project location, the existing ferry crossing and "
                    "the nearest fixed crossing 62 km upstream. Drawing no. KM-001 rev. B.",
                    BODY), PageBreak()]
    f += filler_pages(7, "Annexure I — Location Plans", seed=20)
    f += [Paragraph("ANNEXURE II — APPROVED ALIGNMENT DRAWING", H1),
          Paragraph("Alignment drawing showing the approved centre line, chainages and land "
                    "boundaries. Drawing no. AL-002 to AL-009.", BODY), PageBreak()]
    f += filler_pages(11, "Annexure II — Alignment Sheets", seed=21)
    f += [Paragraph("ANNEXURE III — GENERAL ARRANGEMENT DRAWING", H1),
          Paragraph("General arrangement of the bridge showing span arrangement, "
                    "longitudinal section and typical cross section. Drawing no. GA-010 to "
                    "GA-021.", BODY), PageBreak()]
    f += filler_pages(11, "Annexure III — General Arrangement", seed=22)

    f += [Paragraph("ANNEXURE IV — DETAILED ESTIMATE", H1),
          Paragraph("Item-wise detailed estimate with quantities, rates and amounts, "
                    "supported by measurement sheets and rate analysis.", BODY)]
    rate_rows = [["Sl.", "Item of work", "Unit", "Rate (Rs.)"]]
    items = [("Earthwork in excavation in ordinary soil", "cum", "312"),
             ("Plain cement concrete M15", "cum", "5,480"),
             ("Reinforced cement concrete M35 in substructure", "cum", "8,940"),
             ("HYSD reinforcement steel Fe500D", "MT", "72,600"),
             ("Structural steel in built-up sections", "MT", "94,200"),
             ("Formwork for foundations", "sqm", "486"),
             ("Formwork for piers and abutments", "sqm", "612"),
             ("Granular sub-base, close graded", "cum", "1,842"),
             ("Wet mix macadam", "cum", "2,110"),
             ("Prime coat with bituminous primer", "sqm", "48"),
             ("Tack coat", "sqm", "22"),
             ("Dense bituminous macadam", "cum", "7,320"),
             ("Brick masonry in cement mortar 1:6", "cum", "6,180"),
             ("Cement plaster 12 mm thick", "sqm", "268"),
             ("Providing and launching PSC girders", "MT", "88,400"),
             ("Pot-PTFE bearings", "each", "42,600"),
             ("Strip seal expansion joint", "rm", "18,900")]
    for i, (d_, u, r_) in enumerate(items, start=1):
        rate_rows.append([str(i), d_, u, r_])
    # Row 18 — quoted well above the Schedule of Rates for this item
    rate_rows.append(["18", "Bituminous concrete, grading II", "cum",
                      "9,240" if defective else "6,780"])
    rate_rows.append(["19", "Thermoplastic road marking", "sqm", "412"])
    f += [Spacer(1, 6), grid(rate_rows, [1.2 * cm, 9.0 * cm, 2.0 * cm, 3.4 * cm]),
          PageBreak()]

    f += [Paragraph("ANNEXURE IV-A — YEAR-WISE CASH FLOW STATEMENT", H1),
          Paragraph("All figures in Rs. crore. Year 0 is the year of commencement.", BODY),
          Spacer(1, 6)]
    cfr = [["Year", "Capital cost", "O&M cost", "Gross benefit", "Net cash flow"]]
    for y, out_, ben in cf:
        cap = out_ if y <= 2 else 0.0
        om = 0.0 if y <= 2 else out_
        cfr.append([str(y), f"{cap:.2f}" if cap else "-", f"{om:.2f}" if om else "-",
                    f"{ben:.2f}" if ben else "-", f"{ben - out_:.2f}"])
    f += [grid(cfr, [1.8 * cm, 3.4 * cm, 2.8 * cm, 3.4 * cm, 3.4 * cm]), PageBreak()]
    f += annexure_pages(30, "Annexure IV — Measurement Sheets", seed=23)

    f += [Paragraph("ANNEXURE V — GEO-TECHNICAL INVESTIGATION REPORT", H1),
          Paragraph("Bore logs, laboratory test results and foundation recommendations for "
                    "eighteen boreholes.", BODY), PageBreak()]
    f += annexure_pages(25, "Annexure V — Bore Logs", seed=24)

    f += [Paragraph("ANNEXURE VI — HYDRAULIC INVESTIGATION REPORT", H1),
          Paragraph("Discharge estimation, HFL determination, afflux computation, scour "
                    "depth and waterway adequacy.", BODY), PageBreak()]
    f += filler_pages(17, "Annexure VI — Hydraulic Computations", seed=25)

    f += [Paragraph("ANNEXURE VII — COPIES OF STATUTORY APPROVALS", H1),
          Paragraph("Copies of the administrative sanction, waterway clearance, pollution "
                    "control board consent and approval of river training works.", BODY),
          PageBreak()]
    f += filler_pages(9, "Annexure VII — Approval Correspondence", seed=26)

    doc.build(f)
    return {"claimed_irr": claimed_irr, "true_irr": true_irr,
            "cost_headline": cost_headline, "cost_abstract": cost_stale}


def main() -> None:
    import pymupdf

    sound = build(OUT / "dpr_bridge_sound.pdf", defective=False)
    bad = build(OUT / "dpr_bridge_defective.pdf", defective=True)

    print("Generated against the KIIFB bridge DPR template "
          "(docs/reference/KIIFB_Bridges_DPR_Template.pdf):\n")
    for name, meta in (("dpr_bridge_sound.pdf", sound),
                       ("dpr_bridge_defective.pdf", bad)):
        with pymupdf.open(OUT / name) as d:
            pages = d.page_count
        print(f"  {name:30} {pages:>4} pages   claims IRR {meta['claimed_irr']:.1f}%, "
              f"annexure computes {meta['true_irr']:.1f}%")

    print(f"\n  planted in the defective report:")
    print(f"    1. cost stated as Rs {bad['cost_headline']} cr in the summary and "
          f"Rs {bad['cost_abstract']} cr in the abstract")
    print(f"    2. claims IRR {bad['claimed_irr']:.1f}% against "
          f"{bad['true_irr']:.1f}% from its own annexure "
          f"({bad['claimed_irr'] - bad['true_irr']:.1f} pp gap)")
    print(f"    3. chapter 3.17 Operations and Maintenance Plan absent entirely")
    print(f"    4. environmental clearance 'yet to be obtained'")


if __name__ == "__main__":
    main()
