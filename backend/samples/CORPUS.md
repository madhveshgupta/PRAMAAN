# Test corpus

Six generated DPRs across three sectors, 2,203 pages, built against three published
government templates — plus the one supplied document that survived review, which is the
sole basis of the risk model.

## Training data — the only supplied document retained

| File | What it is |
|---|---|
| `ml/data/raw/paimana_flash_report_2026-06.pdf` | MoSPI PAIMANA Flash Report, June 2026. Every central sector project of ₹150 crore and above, with approved cost against revised cost and original against revised commissioning date. **1,604 usable project records** — the sole basis of the risk model. |

Everything else that was supplied has been withdrawn. Two of those files were unfilled model
templates, one was a tender document, and none was a completed infrastructure DPR — so none
of them could serve as a test of whether the engine reads a real report correctly.

## The three specifications the rubric is built from

Each is a published government template, kept in `docs/reference/`. **Every rubric item is
traceable to a numbered chapter one of these templates actually requires** — none is written
from assumption.

| Template | Chapters | Rubric profile | Items |
|---|---|---|---:|
| `KIIFB_Bridges_DPR_Template.pdf` | 1–3.17 + Annexures I–VII | `infrastructure` | 21 |
| `KIIFB_Buildings_DPR_Template.pdf` | 1–18 | `building_kiifb` | 18 |
| `KIIFB_General_DPR_Template.pdf` | 1–18 | `general_kiifb` | 19 |

The templates are not interchangeable, and the rubric reproduces the differences rather than
flattening them. Chapter 11, *Environmental and Sustainability Aspects*, exists in the General
template and not in Buildings — a water scheme abstracts and discharges, an office block does
not. Bridges number their chapters 3.1–3.17 under a single heading; the other two use a flat
1–18. Survey requirements under the Bridges template follow IRC:SP:19, which it references.

A fourth profile, `horticulture_nhb` (21 items from the National Horticulture Board model
DPR), is configured but has no sample document in this corpus.

## Generated documents

A template states what the chapters are. It cannot show whether the engine reads a *filled*
report correctly, because every field in it is empty. So each template gets a matched pair:
one complete and internally consistent report, and one with defects planted at known places.

| File | Pages | Sector | Profile chosen | Score | Findings |
|---|---:|---|---|---:|---:|
| `dpr_bridge_sound.pdf` | 318 | Bridge | `infrastructure` | **100** | 0 |
| `dpr_bridge_defective.pdf` | 318 | Bridge | `infrastructure` | 64.2 | 5 |
| `dpr_hospital_sound.pdf` | 386 | Building | `building_kiifb` | **100** | 0 |
| `dpr_hospital_defective.pdf` | 376 | Building | `building_kiifb` | 84.0 | 4 |
| `dpr_water_sound.pdf` | 406 | Water supply | `general_kiifb` | **100** | 0 |
| `dpr_water_defective.pdf` | 399 | Water supply | `general_kiifb` | 76.6 | 3 |

**All three sound reports score 100 with zero findings**, across 1,110 pages. That number is
the one worth watching: it is what makes the defective reports' findings mean something, and
it is the first thing to break when a detector is loosened.

The sound half of each pair is not decoration. Twice during the build a "fix" that caught a
defect also collapsed the clean report's score — once from 100 to 20.6. Only testing both
directions surfaced that.

### The planted defects, and where each is caught

**`dpr_bridge_defective.pdf`** — 4 planted, 4 caught

| Defect | Detected as | Anchors |
|---|---|---|
| Cost is ₹412.50 cr in the executive summary, ₹418.20 cr in the cost abstract | `F4-NUMERIC-DIVERGENCE` | p.6, p.115 |
| Chapter 3.9 claims 14.2% IRR; the cash-flow annexure computes to **7.9%** | `F6-IRR-UNSUPPORTED` | p.133, p.234 |
| Chapter 3.17 Operations and Maintenance Plan absent entirely | `F3-OM_PLAN` — *insufficient evidence* | p.234 |
| Environmental clearance "yet to be obtained"; clearances "under process" | `F3-ENVIRONMENT`, `F3-STATUTORY_CLEARANCES` — *partial* | p.142, p.181 |

**`dpr_hospital_defective.pdf`** — 4 planted, 4 caught

| Defect | Detected as | Anchors |
|---|---|---|
| Cost is ₹186.40 cr in the executive summary, ₹192.70 cr in the cost abstract | `F4-NUMERIC-DIVERGENCE` | p.6, p.110 |
| Chapter 11 Risk Assessment absent entirely | `F3-RISK_ASSESSMENT` — *insufficient evidence* | — |
| Chapter 16 Quality Management Plan absent entirely | `F3-QUALITY_PLAN` — *insufficient evidence* | — |
| Consent to establish "yet to be obtained… under process" | `F3-STATUTORY_CLEARANCES` — *partial* | p.186 |

**`dpr_water_defective.pdf`** — 3 planted, 3 caught

| Defect | Detected as | Anchors |
|---|---|---|
| Chapter 10 claims 14.6% IRR; the cash-flow annexure computes to **7.6%** | `F6-IRR-UNSUPPORTED` | p.125, p.327 |
| Chapter 11 Environmental and Sustainability Aspects absent entirely | `F3-ENVIRONMENT` — *insufficient evidence* | — |
| O&M chapter present, but "the source of this recurring provision is yet to be identified" | `F3-OM_PLAN` — *partial* | p.208 |

**The financial defects are arithmetically real, not asserted.** The defective cash flows
genuinely return 7.9% and 7.6%. The sound reports clear the 12% threshold they claim to
clear — an earlier draft of the bridge report returned 11.1%, which would have made the
*sound* document fail its own stated test.

## Why the reports are generated rather than real

Because no completed DPR was available, and because a test fixture needs known ground truth.
We cannot know what defects a real report contains without appraising it by hand first —
which is the work being automated. The generated pairs give documents whose defects are known
exactly, so detection can be **measured** rather than asserted.

What is **not** invented is the shape. Every chapter exists because a published template
requires it, in that template's own numbering and wording. Content is sector-specific and
cites the codes that actually govern each sector — IRC for bridges, NBC and IS 456 for
buildings, CPHEEO and IS 10500 for water supply. An earlier version drew all filler from a
single bridge-derived pool, which put traffic volume counts and river training works inside a
district hospital report; that is recorded as B49.

What this corpus does **not** give is confidence about real-world prose, layout and scan
quality. Real DPRs are often scanned, inconsistently formatted, and paginated by hand. That
gap remains open and should be stated plainly rather than implied away.

## Regenerating

```bash
python scripts/make_dpr.py           # the bridge pair
python scripts/make_dpr_sectors.py   # the hospital and water pairs
```

Both are seeded, so page numbers are stable across runs — the planted defects depend on
landing at known pages, and `tests/test_phase2.py` pins two of them.
