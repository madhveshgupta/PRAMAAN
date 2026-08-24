# Training data sources

## MoSPI PAIMANA Flash Reports
Portal: https://paimana-proj.mospi.gov.in
Source of truth: projects ≥ ₹150 crore reported by Central Line Ministries on the CRIP
portal (https://paimana-crip.mospi.gov.in/home).

| File | Period | Pages | Notes |
|---|---|---|---|
| `paimana_flash_report_2026-06.pdf` | June 2026 | 162 | Verified extractable. 1,847 ongoing projects. |

Original URL for the June 2026 report:
https://www.mospi.gov.in/uploads/publications_reports/publications_reports1785229543014_f9b01e19-0a7a-4975-9276-34e02259c2e0_FlashReport_June_2026_.pdf

### Tables of interest (Appendix, page 20 onward)
- **Table 3 — Completed Projects** ← uncensored labels, highest value for training
- **Table 4 — Newly Added Projects**
- **Table 5 — Ongoing Projects, North Eastern Region**
- **Table 6 — All Ongoing Projects** ← the main panel

### Table 6 column layout (verified by direct extraction, Phase 0)
```
Sl.No | Project Name (Agency) (Project Code) (Legacy OCMS Code) (PMGID)
      | State
      | Date of Approval (Start Date) MM/YYYY        -- original (revised)
      | Orignal/Target DoC (Revised DoC) MM/YYYY     -- [sic] typo is in the source
      | Orignal Cost / Revised Cost in Rs. Crore     -- [sic]
      | Cumulative Expenditure in Rs. Crore
      | Physical Progress (%)
```
Rows are grouped under Ministry and Sector headings — the parser must carry the current
heading down as it walks rows.

**Note the source's own spelling of "Orignal".** Do not "fix" it in the parser's header
matching or matching will fail.

### Extraction approach (Phase 7)
The PDF has a real text layer (no OCR needed). PyMuPDF `get_text("dict")` recovers the rows
with coordinates; column assignment is by x-position clustering, not by delimiter.

### To extend the panel
MoSPI publishes monthly. Pull ~24 prior reports from
https://www.mospi.gov.in/publication/flash-report-central-sector-projects
and key on Project Code to build the panel. The same project across months is what makes
this a panel rather than a snapshot — and the month-over-month revisions are the signal.
