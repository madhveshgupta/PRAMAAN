"""Shared realistic page content for the sample DPRs.

A 300-page document built from one repeated paragraph parses unrealistically well: the
same words in the same layout on every page make heading detection, table extraction and
reading order easier than they are in life. So this generates *varied* content — different
page archetypes, different table shapes, different prose — closer to what an appraiser
actually receives.

Content is **sector-keyed**. An earlier version had a single bridge-derived pool, which put
traffic volume counts and river training works inside a district hospital DPR — the filler
was the largest part of the document, so that one shortcut made two of the six samples read
as obvious forgeries. Each sector now draws prose, tables, computations and drawing numbers
from its own pool, referencing the codes that actually govern it: IRC for bridges, NBC and
IS 456 for buildings, CPHEEO and IS 10500 for water supply.

Deterministic (seeded) so page numbers stay stable across regeneration. The planted defects
in the sample DPRs depend on landing at known pages, and the demo script cites them.
"""
from __future__ import annotations

import random

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

_S = getSampleStyleSheet()
H2 = ParagraphStyle("f_h2", parent=_S["Heading2"], fontSize=12, spaceAfter=7)
H3 = ParagraphStyle("f_h3", parent=_S["Heading3"], fontSize=10.5, spaceBefore=8, spaceAfter=5)
BODY = ParagraphStyle("f_body", parent=_S["BodyText"], fontSize=9.5, leading=14)
SMALL = ParagraphStyle("f_sm", parent=BODY, fontSize=8)

PROSE_BRIDGE = [
    "The alignment has been fixed after detailed reconnaissance survey and in consultation "
    "with the concerned district authorities. Ground control points were established at "
    "intervals of 500 m and connected to the nearest GTS benchmark.",
    "Soil investigation was carried out by rotary drilling at the locations shown on the "
    "layout plan. Standard penetration tests were conducted at 1.5 m intervals and "
    "undisturbed samples collected in the cohesive strata for laboratory testing.",
    "Quantities have been computed from the approved General Arrangement Drawings and "
    "cross-checked against the detailed measurement sheets enclosed at the Annexure. "
    "Rates are as per the schedule in force with lead and lift adjustments applied.",
    "The design conforms to the relevant IRC and IS codes in force on the date of this "
    "report. Load combinations have been considered in accordance with IRC:6 and the "
    "limit state method adopted throughout.",
    "Consultations were held with the Gram Panchayat and the affected households. Minutes "
    "of the consultation meetings, along with the attendance register, are placed at the "
    "Annexure to this chapter.",
    "Hydrological analysis was carried out using the discharge records of the nearest "
    "gauging station for the period of record available. The design discharge corresponds "
    "to a return period of 100 years as required for a structure of this class.",
    "Material sources have been identified within an economic lead. Test results for "
    "coarse aggregate, fine aggregate and water from the identified sources are enclosed "
    "and satisfy the specification requirements.",
    "The construction methodology envisages work in two seasons with the river training "
    "works taken up in the lean period. A detailed programme is placed at the Annexure.",
]

TABLES_BRIDGE = [
    ("Detailed Measurement Sheet",
     ["Item", "L (m)", "B (m)", "D (m)", "Nos", "Quantity"],
     lambda r: [f"Item {r.randint(100, 899)}", f"{r.uniform(2, 40):.2f}",
                f"{r.uniform(0.3, 6):.2f}", f"{r.uniform(0.2, 3):.2f}",
                str(r.randint(1, 24)), f"{r.uniform(1, 400):.3f}"]),
    ("Bore Log Summary",
     ["Depth (m)", "Strata", "N value", "Sample"],
     lambda r: [f"{r.uniform(0.5, 30):.1f}",
                r.choice(["Silty clay", "Medium sand", "Coarse sand", "Weathered rock",
                          "Clayey silt", "Gravelly sand"]),
                str(r.randint(4, 60)), r.choice(["UDS", "SPT", "DS"])]),
    ("Traffic Volume Count",
     ["Hour", "2-Wheeler", "Car/Jeep", "Bus", "LCV", "Truck", "PCU"],
     lambda r: [f"{r.randint(0, 23):02d}:00", str(r.randint(20, 400)),
                str(r.randint(10, 260)), str(r.randint(0, 40)), str(r.randint(0, 90)),
                str(r.randint(0, 120)), str(r.randint(80, 1400))]),
    ("Lead Statement",
     ["Material", "Source", "Lead (km)", "Rate (Rs)"],
     lambda r: [r.choice(["Coarse aggregate", "Fine sand", "Cement", "Steel", "Bitumen",
                          "Boulder", "Murram"]),
                r.choice(["Quarry A", "Quarry B", "River bed", "Depot", "Plant"]),
                f"{r.uniform(2, 90):.1f}", f"{r.randint(180, 9400):,}"]),
    ("Land Schedule",
     ["Survey No.", "Village", "Area (ha)", "Class", "Status"],
     lambda r: [f"{r.randint(10, 480)}/{r.randint(1, 9)}",
                r.choice(["Dhubri", "Gauripur", "Agomani", "Golakganj"]),
                f"{r.uniform(0.05, 2.4):.3f}",
                r.choice(["Agricultural", "Homestead", "Waste"]),
                r.choice(["Awarded", "Under award", "Notified"])]),
]

PROSE_BUILDING = [
    "The space programme has been developed from the functional brief agreed with the "
    "user department. Departmental areas, circulation and the gross-to-carpet ratio are "
    "tabulated in the area statement enclosed at the Annexure.",
    "Soil investigation was carried out by rotary drilling at the locations shown on the "
    "layout plan. The safe bearing capacity adopted for design is based on the lower of "
    "the shear and settlement criteria as reported in the geotechnical report.",
    "The structural design conforms to IS 456 for reinforced concrete and IS 1893 for "
    "earthquake resistant design. The site falls in seismic zone V and the importance "
    "factor applicable to a hospital building has been adopted.",
    "Building services comprise electrical distribution, water supply and sanitation, "
    "HVAC for the identified conditioned areas, medical gas pipeline and vertical "
    "transportation. Connected load and demand factors are given in the load schedule.",
    "Fire safety provisions follow Part 4 of the National Building Code. Means of egress, "
    "travel distances, staircase widths and the fire fighting installations have been "
    "designed for the occupancy classification of the block.",
    "Quantities have been computed from the approved architectural and structural drawings "
    "and cross-checked against the detailed measurement sheets enclosed at the Annexure. "
    "Rates are as per the schedule of rates in force with lead and lift adjustments.",
    "Barrier-free access has been provided in accordance with the Harmonised Guidelines "
    "and Standards for Universal Accessibility. Ramps, lifts, signage and accessible "
    "toilets are provided on every floor of the block.",
    "Consultations were held with the head of each clinical department on adjacency, "
    "patient flow and equipment layout. Minutes of the consultation meetings are placed "
    "at the Annexure to this chapter.",
]

PROSE_WATER = [
    "The design period has been adopted as 30 years in accordance with the CPHEEO Manual "
    "on Water Supply and Treatment. The base year population is taken from the latest "
    "Census and projected by the incremental increase method.",
    "The per-capita supply level adopted is that prescribed by the CPHEEO Manual for a "
    "town with piped supply and full sewerage, with the applicable allowance for "
    "unaccounted-for water added to arrive at the gross demand.",
    "The yield of the source has been assessed from the discharge records of the nearest "
    "gauging station for the period of record available. The lean-season yield exceeds "
    "the design draw-off with the margin required for a source of this class.",
    "The treatment train comprises aeration, flash mixing, clariflocculation, rapid "
    "gravity filtration and disinfection by chlorination. Unit sizing and the design "
    "loading rates adopted are given in the design computations.",
    "The distribution network has been analysed as a looped system. Residual pressure at "
    "every node satisfies the minimum prescribed at peak demand, and pipe sizes have been "
    "optimised against the head available from the service reservoir.",
    "Pipe material has been selected on the basis of working pressure, laying condition "
    "and life-cycle cost. Ductile iron conforming to IS 8329 has been adopted for the "
    "transmission main and HDPE conforming to IS 4984 for the distribution laterals.",
    "Raw and treated water samples were tested for the parameters specified in IS 10500. "
    "The test reports of the accredited laboratory are enclosed at the Annexure and the "
    "treated water meets the acceptable limits for every parameter tested.",
    "Recurring operation and maintenance covers energy for pumping, treatment chemicals, "
    "establishment and periodic replacement. The energy component has been worked out "
    "from the pump duty and the operating hours assumed for the design year.",
]

TABLES_BUILDING = [
    ("Room Data Sheet",
     ["Room", "Department", "Carpet area (sqm)", "Occupancy", "Floor finish"],
     lambda r: [f"Room {r.randint(100, 899)}",
                r.choice(["General Medicine", "Surgery", "Paediatrics", "Radiology",
                          "Pathology", "Obstetrics", "Casualty"]),
                f"{r.uniform(9, 92):.2f}", str(r.randint(1, 30)),
                r.choice(["Vitrified tile", "Antistatic vinyl", "Kota stone",
                          "Epoxy screed", "Ceramic tile"])]),
    ("Departmental Area Statement",
     ["Department", "Floor", "Units", "Area per unit (sqm)", "Total (sqm)"],
     lambda r: (lambda u, a: [
         r.choice(["OPD", "IPD Ward", "Operation Theatre", "ICU", "Diagnostics",
                   "Pharmacy", "Administration", "Staff Quarters"]),
         r.choice(["Ground", "First", "Second", "Third"]), str(u),
         f"{a:.2f}", f"{u * a:.2f}"])(r.randint(1, 18), r.uniform(12, 140))),
    ("Bore Log Summary",
     ["Depth (m)", "Strata", "N value", "Sample"],
     lambda r: [f"{r.uniform(0.5, 30):.1f}",
                r.choice(["Silty clay", "Medium sand", "Coarse sand", "Weathered rock",
                          "Clayey silt", "Gravelly sand"]),
                str(r.randint(4, 60)), r.choice(["UDS", "SPT", "DS"])]),
    ("Electrical Load Schedule",
     ["Panel", "Description", "Connected load (kW)", "Demand factor", "Demand (kVA)"],
     lambda r: (lambda kw, df: [
         f"DB-{r.randint(1, 40):02d}",
         r.choice(["Lighting", "Power outlets", "HVAC", "Lifts", "Medical equipment",
                   "Pumps", "Sterilisation"]),
         f"{kw:.2f}", f"{df:.2f}", f"{kw * df / 0.9:.2f}"])(
             r.uniform(2, 180), r.uniform(0.4, 0.95))),
    ("Equipment Schedule",
     ["Item", "Department", "Nos", "Unit rate (Rs)", "Amount (Rs)"],
     lambda r: (lambda n, rate: [
         r.choice(["Hospital bed", "OT table", "Ventilator", "X-ray unit", "Autoclave",
                   "Ultrasound", "Defibrillator", "Patient monitor"]),
         r.choice(["ICU", "OT", "Ward", "Radiology", "CSSD", "Casualty"]),
         str(n), f"{rate:,}", f"{n * rate:,}"])(
             r.randint(1, 40), r.randint(18000, 2400000))),
    ("Detailed Measurement Sheet",
     ["Item", "L (m)", "B (m)", "D (m)", "Nos", "Quantity"],
     lambda r: [f"Item {r.randint(100, 899)}", f"{r.uniform(2, 40):.2f}",
                f"{r.uniform(0.3, 6):.2f}", f"{r.uniform(0.2, 3):.2f}",
                str(r.randint(1, 24)), f"{r.uniform(1, 400):.3f}"]),
]

TABLES_WATER = [
    ("Population Projection",
     ["Year", "Ward", "Population", "Rate (lpcd)", "Demand (MLD)"],
     lambda r: (lambda pop, lpcd: [
         str(r.choice([2026, 2031, 2036, 2041, 2046, 2051, 2056])),
         f"Ward {r.randint(1, 24)}", f"{pop:,}", str(lpcd),
         f"{pop * lpcd / 1_000_000:.3f}"])(
             r.randint(1800, 46000), r.choice([70, 100, 135, 150]))),
    ("Pipeline Schedule",
     ["Chainage (m)", "Dia (mm)", "Material", "Class", "Length (m)"],
     lambda r: [f"{r.randint(0, 24000):,}",
                str(r.choice([100, 150, 200, 250, 300, 400, 500, 600])),
                r.choice(["DI", "HDPE", "MS", "PVC-O"]),
                r.choice(["K-7", "K-9", "PN 6", "PN 10", "PN 16"]),
                f"{r.uniform(40, 1800):.1f}"]),
    ("Hydraulic Node Analysis",
     ["Node", "Ground level (m)", "Demand (lps)", "Head (m)", "Residual (m)"],
     lambda r: (lambda gl, hd: [
         f"N-{r.randint(1, 220):03d}", f"{gl:.2f}", f"{r.uniform(0.2, 24):.2f}",
         f"{gl + hd:.2f}", f"{hd:.2f}"])(r.uniform(28, 96), r.uniform(7, 26))),
    ("Pump Schedule",
     ["Pump", "Duty", "Discharge (lps)", "Head (m)", "Rating (kW)"],
     lambda r: (lambda q, h: [
         f"P-{r.randint(1, 12):02d}",
         r.choice(["Raw water", "Clear water", "Backwash", "Sludge", "Booster"]),
         f"{q:.1f}", f"{h:.1f}", f"{q * h * 9.81 / (1000 * 0.72):.2f}"])(
             r.uniform(15, 320), r.uniform(12, 88))),
    ("Water Quality Test Results",
     ["Parameter", "Unit", "Raw water", "Treated", "IS 10500 limit"],
     lambda r: r.choice([
         ["Turbidity", "NTU", f"{r.uniform(8, 240):.1f}", f"{r.uniform(0.2, 0.9):.2f}", "1"],
         ["pH", "-", f"{r.uniform(6.4, 8.4):.1f}", f"{r.uniform(6.9, 8.1):.1f}", "6.5-8.5"],
         ["Total hardness", "mg/l", f"{r.uniform(90, 480):.0f}", f"{r.uniform(60, 190):.0f}", "200"],
         ["Iron", "mg/l", f"{r.uniform(0.4, 4.2):.2f}", f"{r.uniform(0.02, 0.28):.2f}", "1.0"],
         ["Total coliform", "MPN/100ml", str(r.randint(2, 900)), "Absent", "Absent"],
         ["Residual chlorine", "mg/l", "Nil", f"{r.uniform(0.2, 0.8):.2f}", "0.2 min"]])),
    ("Bore Log Summary",
     ["Depth (m)", "Strata", "N value", "Sample"],
     lambda r: [f"{r.uniform(0.5, 30):.1f}",
                r.choice(["Silty clay", "Medium sand", "Coarse sand", "Weathered rock",
                          "Clayey silt", "Gravelly sand"]),
                str(r.randint(4, 60)), r.choice(["UDS", "SPT", "DS"])]),
]

# Per-sector pools. `bridge` reproduces the original single pool exactly, so the bridge
# samples and the page numbers pinned in tests/test_phase2.py do not move.
PROSE_BY_SECTOR = {
    "bridge": PROSE_BRIDGE, "building": PROSE_BUILDING, "water": PROSE_WATER,
}
TABLES_BY_SECTOR = {
    "bridge": TABLES_BRIDGE, "building": TABLES_BUILDING, "water": TABLES_WATER,
}
# What a design computation sheet in this sector actually computes. Quantity and unit are
# paired, not drawn independently — an earlier version printed "Velocity = 97.097 lps",
# which is the kind of detail that tells a reader immediately the document is generated.
COMPUTE_BY_SECTOR = {
    "bridge": [("Moment", "kNm"), ("Shear", "kN"), ("Deflection", "mm"),
               ("Bearing pressure", "kPa"), ("Settlement", "mm")],
    "building": [("Moment", "kNm"), ("Shear", "kN"), ("Axial load", "kN"),
                 ("Bearing pressure", "kPa"), ("Deflection", "mm")],
    "water": [("Head loss", "m"), ("Velocity", "m/s"), ("Discharge", "lps"),
              ("Residual pressure", "m"), ("Detention time", "hr")],
}
DRAWING_BY_SECTOR = {
    "bridge": ["GA", "ST", "HY", "LA"],
    "building": ["AR", "ST", "EL", "PH"],
    "water": ["WS", "PL", "HY", "ST"],
}


def _grid(header, rows, widths=None):
    t = Table([header] + rows, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9aa4ad")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde5ee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def filler_pages(n: int, chapter: str, seed: int = 0, start: int = 1,
                 sector: str = "bridge") -> list:
    """`n` pages of varied, plausible DPR content under one chapter heading.

    Alternates prose, tables and computation sheets so the parser meets the same variety it
    would in a real document rather than one repeated layout. `sector` selects the content
    pool — a hospital DPR must not contain traffic volume counts.
    """
    r = random.Random(seed)
    prose = PROSE_BY_SECTOR[sector]
    tables = TABLES_BY_SECTOR[sector]
    computations = COMPUTE_BY_SECTOR[sector]
    prefixes = DRAWING_BY_SECTOR[sector]
    out: list = []
    for i in range(n):
        sheet = start + i
        kind = i % 3
        out.append(Paragraph(f"{chapter} — Sheet {sheet}", H2))

        if kind == 0:                                   # prose page
            for _ in range(4):
                out.append(Paragraph(r.choice(prose), BODY))
                out.append(Spacer(1, 5))
            out.append(Paragraph(
                f"Reference: drawing no. {r.choice(prefixes)}-"
                f"{r.randint(100, 999)}, revision {r.choice('ABC')}.", SMALL))

        elif kind == 1:                                 # data table page
            title, header, gen = tables[r.randrange(len(tables))]
            out.append(Paragraph(title, H3))
            rows = [gen(r) for _ in range(r.randint(16, 26))]
            out.append(_grid(header, rows))
            out.append(Spacer(1, 6))
            out.append(Paragraph(r.choice(prose), BODY))

        else:                                           # computation page
            out.append(Paragraph("Design Computation", H3))
            for _ in range(r.randint(5, 8)):
                a, b = r.uniform(1, 90), r.uniform(0.4, 12)
                quantity, unit = r.choice(computations)
                out.append(Paragraph(
                    f"{quantity} "
                    f"= {a:.3f} × {b:.3f} = {a * b:.3f} "
                    f"{unit} &nbsp;&nbsp;"
                    f"(permissible {a * b * r.uniform(1.05, 1.9):.3f}) — "
                    f"{'safe' if r.random() > 0.08 else 'revise section'}", BODY))
            out.append(Spacer(1, 5))
            out.append(Paragraph(r.choice(prose), BODY))

        out.append(PageBreak())
    return out


def annexure_pages(n: int, label: str, seed: int = 0,
                   sector: str = "bridge") -> list:
    """Dense back-matter — what actually makes a real DPR 300+ pages."""
    r = random.Random(seed)
    out: list = []
    for i in range(n):
        tables = TABLES_BY_SECTOR[sector]
        title, header, gen = tables[(i + seed) % len(tables)]
        out.append(Paragraph(f"{label} — {title}, page {i + 1}", H2))
        rows = [gen(r) for _ in range(r.randint(22, 30))]
        out.append(_grid(header, rows))
        out.append(PageBreak())
    return out
