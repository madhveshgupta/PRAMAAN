"""Sector specifications for the sample DPRs.

Each spec names the real government template it follows and lists that template's own
chapters, in its own numbering and wording. The three templates differ — Bridges numbers
its chapters 3.1 to 3.17 under a single "CHAPTERS" heading, Buildings uses 1 to 18 with
sub-sections, General uses a flat 1 to 18 — and the samples reproduce those differences
rather than flattening them into one shape.

Copies of all three are in docs/reference/.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chapter:
    number: str
    title: str
    body: list[str] = field(default_factory=list)   # paragraphs
    table: tuple[str, list[list[str]], list[float]] | None = None
    filler: int = 4                                  # continuation pages after it
    key: str | None = None                           # marks a chapter defects can target


@dataclass
class Spec:
    slug: str
    title: str
    subtitle: str
    template: str
    applicant: str
    agency: str
    consultant: str
    cost_crore: str
    stale_cost: str          # what the cost abstract says in the defective variant
    duration_months: int
    salient: list[list[str]]
    chapters: list[Chapter]
    cost_heads: list[list[str]]
    annexures: list[tuple[str, str, int]]
    cashflow_base: tuple[float, float]   # (sound, defective) benefit scale
    capex: list[tuple[int, float]]
    horizon: int = 30
    sector: str = "bridge"   # which dpr_content pool the filler draws from


# ─────────────────────────────────────────────────────────── district hospital (Buildings)
HOSPITAL = Spec(
    sector="building",
    slug="hospital",
    title="Construction of a 200-Bed District Hospital Block at Nalbari, Assam",
    subtitle="including Diagnostic Wing and Staff Quarters",
    template="KIIFB Buildings DPR Template (chapters 1-18)",
    applicant="Assam Public Works Department (Buildings)",
    agency="Assam Health Infrastructure Development Society",
    consultant="Brahmaputra Architects and Engineers LLP",
    cost_crore="186.40", stale_cost="192.70", duration_months=28,
    salient=[
        ["1", "Title of the project", "Construction of a 200-bed district hospital block "
                                      "at Nalbari with diagnostic wing and staff quarters"],
        ["2", "Department", "Health and Family Welfare"],
        ["3", "District / Taluk / Local body / Constituency",
              "Nalbari / Nalbari / Nalbari Municipal Board / Nalbari LAC"],
        ["4", "Implementing agency / SPV", "Assam Health Infrastructure Development Society"],
        ["5", "DPR prepared by", "Brahmaputra Architects and Engineers LLP"],
        ["6", "Project outlay", "Rs. 186.40 crore"],
        ["7", "Budget provision", "Rs. 62.00 crore in the current financial year"],
        ["8", "Budget speech reference", "Para 118, State Budget Speech 2026-27"],
        ["9", "Administrative sanction", "AS accorded vide G.O. No. HLB/294/2026 dated "
                                         "22 March 2026"],
        ["10", "Nature of the project", "New building"],
        ["11", "Present status of existing building",
               "Existing 60-bed block constructed in 1974; structurally distressed, "
               "assessed as beyond economical repair"],
        ["12", "Need for the project",
               "Bed occupancy of the existing block exceeds 140 per cent; the district "
               "refers 3,400 cases a year to Guwahati for want of capacity"],
        ["13", "Plinth area", "18,640 sqm across four blocks"],
        ["14", "Number of floors", "Ground plus four"],
        ["15", "Land available / required", "3.20 ha available in departmental possession; "
                                            "no acquisition required"],
        ["16", "Basis of estimate", "Assam PWD Schedule of Rates 2025-26; detailed estimate "
                                    "at Annexure IV"],
        ["17", "Details of revenue streams", "User charges as per state schedule; "
                                             "estimated Rs. 4.20 crore per annum"],
        ["18", "Cost Benefit Analysis", "BCR 1.38"],
        ["19", "Details of project risks", "Chapter 11 — 11 risks identified"],
        ["20", "Project management organisation", "Chapter 12"],
        ["21", "Contract management strategy", "Item rate — Chapter 13"],
        ["22", "Implementation schedule and WBS", "28 months from zero date — Chapter 14"],
        ["23", "Details of statutory clearances", "Chapter 15"],
        ["24", "Quality control mechanism", "Chapter 16"],
        ["25", "O&M arrangements after completion", "Chapter 17"],
        ["26", "Details of attached drawings", "Annexures I to III"],
        ["27", "Other attachments", "Annexures IV to VII"],
    ],
    chapters=[
        Chapter("3", "PROJECT BACKGROUND", filler=3, body=[
            "3.1 Introduction — Nalbari district has a population of 7.7 lakh served by a "
            "single district hospital constructed in 1974 with a sanctioned strength of 60 "
            "beds. The block is a load-bearing masonry structure showing distress in the "
            "form of differential settlement and corrosion of embedded steel.",
            "3.2 Project Objective — to provide a 200-bed secondary care facility meeting "
            "Indian Public Health Standards for a district hospital, with diagnostic "
            "services presently unavailable within the district.",
            "3.3 Methodology — the requirement was assessed from five years of hospital "
            "records, referral registers and the district health profile. Space "
            "programming follows the Indian Public Health Standards 2022 for district "
            "hospitals.",
            "3.4 Overview of the Project Area — the site is 3.20 hectares of departmental "
            "land adjoining the existing hospital campus, level and with existing access "
            "from the district road.",
        ]),
        Chapter("4", "PROJECT FEASIBILITY STUDIES", key="demand", filler=5, body=[
            "4.1 Requirement / Demand Analysis — average bed occupancy over the last three "
            "years is 141 per cent against the sanctioned 60 beds. Outpatient attendance "
            "has grown from 218 to 396 per day over five years. The district referred "
            "3,412 cases to tertiary facilities in Guwahati in the last year, of which an "
            "assessed 61 per cent could have been managed locally with the proposed "
            "diagnostic and surgical capacity.",
            "4.2 Existing Situation Assessment — the structural assessment carried out by "
            "the Assam Engineering College concluded that retrofitting the existing block "
            "would cost 68 per cent of replacement value with a residual life of 15 years, "
            "and recommended replacement.",
            "4.3 Stakeholders Consultation — consultations were held with the District "
            "Health Society, the Indian Medical Association district branch and three "
            "resident welfare associations. Minutes are at Annexure VII.",
            "4.4 Environmental and Sustainability Aspects — the project is a building "
            "project below the threshold requiring prior environmental clearance under the "
            "EIA Notification 2006 as amended. Consent to establish has been obtained from "
            "the Assam Pollution Control Board. Biomedical waste will be handled through "
            "the existing common facility. The design provides for rainwater harvesting "
            "across 14,200 sqm of roof area and a 180 kWp rooftop solar installation.",
        ]),
        Chapter("5", "SITE SURVEYS AND INVESTIGATIONS", key="surveys", filler=8, body=[
            "5.1 Ocular / Reconnaissance Survey — carried out in January 2026. The site is "
            "level with a fall of 0.8 m across its length and no waterlogging observed.",
            "5.2 Topographical Survey — total station survey on a 10 m grid, connected to "
            "the GTS benchmark at Nalbari town, reduced level 47.216 m.",
            "5.3 Soil Investigation — nine boreholes to 20 m depth. Safe bearing capacity "
            "assessed at 180 kN/sqm at 2.5 m founding depth. Ground water encountered at "
            "4.2 m below existing ground level.",
            "5.4 Hydro-Geological Study — the aquifer is unconfined at 12 to 18 m. A "
            "borewell yield of 42,000 litres per day has been assessed against a "
            "requirement of 168,000 litres per day, the balance to be drawn from the "
            "municipal supply.",
            "5.5 Primary Surveys — utility mapping identified an 11 kV overhead line "
            "crossing the northern boundary, to be shifted under a deposit work.",
        ]),
        Chapter("6", "FUNCTIONAL DESIGN", filler=6, body=[
            "Space programming follows Indian Public Health Standards 2022. Three massing "
            "options were examined. The proposed option separates outpatient, inpatient and "
            "diagnostic flows with distinct entries, places the operation theatre complex "
            "on the second floor directly above the emergency and diagnostic block, and "
            "keeps the service core on the north to limit heat gain."]),
        Chapter("7", "ENGINEERING DESIGN", key="design", filler=22, body=[
            "The structure is a reinforced concrete moment resisting frame designed to "
            "IS:456-2000, IS:1893 (Part 1)-2016 for seismic zone V with importance factor "
            "1.5, and IS:875 for loads. Foundations are isolated footings on the assessed "
            "safe bearing capacity, with combined footings where column spacing requires. "
            "Fire safety follows the National Building Code 2016 Part 4."]),
        Chapter("8", "FINANCIAL ESTIMATES AND COST PROJECTIONS", key="cost", filler=8),
        Chapter("9", "REVENUE STREAMS", filler=3, body=[
            "User charges are levied as per the state schedule of rates for government "
            "hospitals, with exemptions for beneficiaries of the state health assurance "
            "scheme. Estimated annual collection is Rs. 4.20 crore, retained by the "
            "Hospital Management Society under the Rogi Kalyan Samiti framework."]),
        Chapter("10", "COST BENEFIT ANALYSIS AND INVESTMENT CRITERIA", key="cba", filler=5),
        Chapter("11", "RISK ASSESSMENT AND MITIGATION MEASURES", key="risk", filler=4),
        Chapter("12", "PROJECT MANAGEMENT ORGANISATION", filler=3, body=[
            "Implementation is by the Assam Health Infrastructure Development Society "
            "through a project management unit headed by a Superintending Engineer, with "
            "two Executive Engineers and an architect on deputation. Progress is reviewed "
            "fortnightly by the Mission Director and monthly by the Commissioner of Health."]),
        Chapter("13", "CONTRACT MANAGEMENT STRATEGY", filler=3, body=[
            "The work is proposed on an item rate basis in three packages — civil, "
            "electromechanical, and medical gas and HVAC — using the standard bidding "
            "document of the Public Works Department. A price adjustment clause is proposed "
            "for cement and steel."]),
        Chapter("14", "IMPLEMENTATION SCHEDULE AND WBS", key="schedule", filler=4),
        Chapter("15", "STATUTORY CLEARANCES", key="clearances", filler=4),
        Chapter("16", "QUALITY MANAGEMENT PLAN", key="quality", filler=4, body=[
            "Quality assurance is exercised by the project management unit through a site "
            "laboratory. Third party quality audit is entrusted to the Assam Engineering "
            "College. Cube testing is at the frequency prescribed in IS:456, and every "
            "consignment of reinforcement steel is tested for tensile strength and "
            "elongation before use."]),
        Chapter("17", "OPERATIONS AND MAINTENANCE PLAN", key="om", filler=4),
    ],
    cost_heads=[
        ["1", "Civil works — main hospital block", "88.20"],
        ["2", "Civil works — diagnostic wing", "24.60"],
        ["3", "Civil works — staff quarters", "18.40"],
        ["4", "Electrical, HVAC and medical gas", "31.80"],
        ["5", "Lifts, fire fighting and BMS", "9.40"],
        ["6", "External development and site works", "7.20"],
        ["7", "Contingencies at 3 per cent", "5.40"],
        ["8", "Quality control and supervision", "1.40"],
    ],
    annexures=[
        ("ANNEXURE I — SITE PLAN AND KEY MAP", "Site plan showing the proposed block "
         "against the existing hospital campus. Drawing SP-001.", 6),
        ("ANNEXURE II — ARCHITECTURAL DRAWINGS", "Floor plans, elevations and sections. "
         "Drawings AR-010 to AR-042.", 14),
        ("ANNEXURE III — STRUCTURAL DRAWINGS", "Foundation layout, framing plans and "
         "reinforcement details. Drawings ST-050 to ST-088.", 14),
        ("ANNEXURE IV — DETAILED ESTIMATE", "Item-wise estimate with quantities, rates and "
         "amounts, supported by measurement sheets.", 34),
        ("ANNEXURE V — SOIL INVESTIGATION REPORT", "Bore logs, laboratory results and "
         "foundation recommendations for nine boreholes.", 22),
        ("ANNEXURE VI — SERVICES DRAWINGS", "Electrical, plumbing, HVAC and medical gas "
         "layouts. Drawings SE-100 to SE-146.", 18),
        ("ANNEXURE VII — CONSULTATION AND APPROVAL RECORDS", "Minutes of stakeholder "
         "consultations and copies of approvals obtained.", 10),
    ],
    cashflow_base=(0.0, 0.0),        # solved at build time
    capex=[(0, 62.0), (1, 74.5), (2, 49.9)],
)


# ────────────────────────────────────────────────── piped water supply scheme (General)
WATER = Spec(
    sector="water",
    slug="water",
    title="Augmentation of Piped Water Supply to Sivasagar Town and Adjoining Panchayats",
    subtitle="raising capacity from 24 MLD to 46 MLD",
    template="KIIFB General DPR Template (chapters 1-18)",
    applicant="Assam Public Health Engineering Department",
    agency="Assam Jal Board",
    consultant="Luit Water Infrastructure Consultants Pvt. Ltd.",
    cost_crore="264.80", stale_cost="271.30", duration_months=24,
    salient=[
        ["1", "Title of the project", "Augmentation of piped water supply to Sivasagar "
                                      "town and adjoining panchayats"],
        ["2", "District / Taluk / Local body",
              "Sivasagar / Sivasagar / Sivasagar Municipal Board and 9 Gram Panchayats"],
        ["3", "Implementing agency / SPV", "Assam Jal Board"],
        ["4", "DPR prepared by", "Luit Water Infrastructure Consultants Pvt. Ltd."],
        ["5", "Project outlay", "Rs. 264.80 crore"],
        ["6", "Budget provision", "Rs. 88.00 crore in the current financial year"],
        ["7", "Administrative sanction", "AS accorded vide G.O. No. PHE/412/2026 dated "
                                         "5 February 2026"],
        ["8", "Nature of the project", "Augmentation of an existing scheme"],
        ["9", "Present status", "Existing 24 MLD scheme commissioned in 2003; supply "
                                "restricted to 90 minutes per day"],
        ["10", "Need for the project", "Design population of 3.42 lakh by 2041 against a "
                                       "present service of 1.96 lakh at 78 lpcd"],
        ["11", "Design capacity", "46 MLD"],
        ["12", "Service level proposed", "135 lpcd, 24x7 supply"],
        ["13", "Source", "River Dikhow, intake at Nazira"],
        ["14", "Land required / status", "6.40 ha; 4.10 ha in departmental possession, "
                                         "2.30 ha under acquisition"],
        ["15", "Basis of estimate", "Assam PHED Schedule of Rates 2025-26"],
        ["16", "Details of revenue streams", "Water tariff; estimated Rs. 11.60 crore per "
                                             "annum at full coverage"],
        ["17", "Cost Benefit Analysis", "BCR 1.52"],
        ["18", "Details of project risks", "Chapter 12 — 13 risks identified"],
        ["19", "Implementation schedule", "24 months from zero date"],
        ["20", "Statutory clearances", "Chapter 16"],
        ["21", "O&M arrangements", "Chapter 18"],
        ["22", "Attached drawings and other attachments", "Annexures I to VII"],
    ],
    chapters=[
        Chapter("3", "INTRODUCTION", filler=4, body=[
            "Sivasagar town is served by a surface water scheme commissioned in 2003 with "
            "a design capacity of 24 MLD drawn from the river Dikhow. The distribution "
            "network covers 68 per cent of the municipal area and none of the nine "
            "adjoining panchayats now proposed for inclusion.",
            "Supply is presently restricted to 90 minutes in the morning at an assessed "
            "78 litres per capita per day against the norm of 135. Non-revenue water is "
            "assessed at 38 per cent, largely through leakage in cast iron mains laid "
            "before 1990."]),
        Chapter("4", "STATUS OF FEASIBILITY STUDIES", filler=3, body=[
            "A feasibility study was carried out in 2023 under the state water sector "
            "programme, which examined three source options — augmentation from the Dikhow, "
            "a well field in the Disang valley, and conjunctive use. Surface augmentation "
            "was recommended on yield reliability and capital cost."]),
        Chapter("5", "REQUIREMENT / DEMAND ANALYSIS", key="demand", filler=6, body=[
            "Population has been projected by the geometric increase method from the 2011 "
            "and 2021 census figures, cross-checked against the arithmetic and incremental "
            "increase methods. The design population for 2041 is 3.42 lakh including the "
            "nine panchayats.",
            "Demand at 135 lpcd with 15 per cent allowance for losses works out to 53.1 MLD "
            "at the design year. Phase I capacity of 46 MLD meets demand to 2036, with the "
            "intake and clear water main sized for the full 53 MLD to avoid a second "
            "disruption."]),
        Chapter("6", "FUNCTIONAL DESIGN", filler=5, body=[
            "The scheme comprises an intake well and jack well at Nazira, a raw water "
            "rising main of 1,100 mm diameter over 8.4 km, a conventional water treatment "
            "plant of 46 MLD, a clear water transmission main, four service reservoirs "
            "totalling 12.4 ML, and 214 km of distribution network."]),
        Chapter("7", "ENGINEERING DESIGN", key="design", filler=20, body=[
            "The treatment plant follows a conventional train of cascade aeration, "
            "flash mixing, clariflocculation, rapid gravity filtration and chlorination, "
            "designed to CPHEEO Manual on Water Supply and Treatment 1999 as amended. "
            "Hydraulic design of the network is by the Hardy Cross method verified in "
            "EPANET for the design year demand under fire flow conditions."]),
        Chapter("8", "FINANCIAL ESTIMATES AND COST PROJECTIONS", key="cost", filler=7),
        Chapter("9", "REVENUE STREAMS", filler=3, body=[
            "Water tariff is levied by the Municipal Board at Rs. 6.20 per kilolitre for "
            "domestic connections with a telescopic slab above 20 kl per month, and "
            "Rs. 22.00 per kilolitre for commercial connections. At full coverage and 85 "
            "per cent collection efficiency the annual revenue is Rs. 11.60 crore against "
            "an O&M requirement of Rs. 9.80 crore."]),
        Chapter("10", "COST BENEFIT ANALYSIS AND INVESTMENT CRITERIA", key="cba", filler=5),
        Chapter("11", "ENVIRONMENTAL AND SUSTAINABILITY ASPECTS", key="environment",
                filler=6),
        Chapter("12", "RISK ASSESSMENT AND MITIGATION MEASURES", key="risk", filler=4),
        Chapter("13", "PROJECT MANAGEMENT ORGANISATION", filler=3, body=[
            "The Assam Jal Board implements through a circle office at Sivasagar headed by "
            "a Superintending Engineer. A third party inspection agency is engaged for "
            "pipeline laying, which is dispersed across 214 km and cannot be supervised "
            "departmentally at the required frequency."]),
        Chapter("14", "CONTRACT MANAGEMENT STRATEGY", filler=3, body=[
            "The intake, rising main and treatment plant are proposed as a single "
            "design-build-operate package with a five year operation period. Distribution "
            "network laying is proposed as three geographic item rate packages."]),
        Chapter("15", "IMPLEMENTATION SCHEDULE AND WBS", key="schedule", filler=4),
        Chapter("16", "STATUTORY CLEARANCES", key="clearances", filler=4),
        Chapter("17", "QUALITY MANAGEMENT PLAN", key="quality", filler=4, body=[
            "Quality control covers pipe testing at the manufacturer's works, hydrostatic "
            "testing of laid mains in 500 m sections, and daily water quality testing at "
            "the plant laboratory against IS:10500. A third party agency audits at monthly "
            "intervals."]),
        Chapter("18", "OPERATIONS AND MAINTENANCE PLAN", key="om", filler=4),
    ],
    cost_heads=[
        ["1", "Intake well, jack well and raw water pumping", "38.60"],
        ["2", "Raw water rising main, 1100 mm, 8.4 km", "44.20"],
        ["3", "Water treatment plant, 46 MLD", "71.40"],
        ["4", "Clear water transmission main", "32.80"],
        ["5", "Service reservoirs, 4 nos., 12.4 ML", "26.90"],
        ["6", "Distribution network, 214 km", "38.10"],
        ["7", "Contingencies at 3 per cent", "7.90"],
        ["8", "Quality control and supervision", "4.90"],
    ],
    annexures=[
        ("ANNEXURE I — KEY MAP AND SERVICE AREA PLAN", "Service area, intake location and "
         "reservoir zones. Drawing WS-001.", 6),
        ("ANNEXURE II — HYDRAULIC NETWORK ANALYSIS", "EPANET output for the design year "
         "under peak and fire flow conditions.", 24),
        ("ANNEXURE III — TREATMENT PLANT DRAWINGS", "Unit process layout, hydraulic flow "
         "diagram and structural drawings. WTP-010 to WTP-052.", 16),
        ("ANNEXURE IV — DETAILED ESTIMATE", "Item-wise estimate with quantities and rates, "
         "supported by measurement sheets.", 32),
        ("ANNEXURE V — WATER QUALITY TEST REPORTS", "Raw water analysis over four seasons "
         "against IS:10500 parameters.", 20),
        ("ANNEXURE VI — PIPELINE ALIGNMENT SHEETS", "Longitudinal sections and alignment "
         "for the rising and transmission mains.", 22),
        ("ANNEXURE VII — CLEARANCES AND CONSULTATION RECORDS", "Copies of approvals and "
         "minutes of consultations with the Municipal Board and Gram Panchayats.", 10),
    ],
    cashflow_base=(0.0, 0.0),
    capex=[(0, 92.0), (1, 104.0), (2, 68.8)],
)

SPECS = {"hospital": HOSPITAL, "water": WATER}
