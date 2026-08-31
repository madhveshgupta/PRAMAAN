# PRAMAAN

> **P**roject **R**eport **A**ppraisal, **M**odelling **A**nd **AN**alytics
> प्रमाण — *"evidence / proof"*. Every finding this system produces carries its proof.

An appraisal platform for **Detailed Project Reports (DPRs)** — the 200–600 page proposals
behind government infrastructure spending. Upload one and it returns a quality score, a
risk prediction, and a cost/schedule outcome range — with every single number linked to the
exact page and highlighted region of the source PDF it came from.

**The system never approves or rejects.** It scores, flags, and cites. A named human with
sanction authority decides.

---

## What it produces

| Output | How it is derived |
|---|---|
| **Quality & compliance score** | Rule-based rubric in `backend/config/rubric.yaml`, applied to fields extracted from the PDF. |
| **Risk prediction** | LightGBM classifiers trained on real MoSPI/PAIMANA project outcomes. Every prediction ships with SHAP attributions. |
| **Cost / schedule range (P50 / P80 / P95)** | Reference class forecasting — percentiles read off what actually happened to comparable historical projects. No simulated parameters. |
| **Evidence anchor** | For all of the above: `{page, bbox, snippet, confidence, method}`, rendered as a click-through highlight in the PDF viewer. |

A value whose claimed source span cannot be re-located in the parsed document text is
**rejected and logged** — never stored, never displayed, never scored.

---

## Repository layout

```
.
├── backend/        FastAPI API + background worker + ML.  Deploys on its own.
├── frontend/       Next.js 16 app (App Router) + pdf.js evidence viewer.  Deploys on its own.
├── scripts/dev.sh  Runs api + worker + web together for local development.
├── CONTRIBUTING.md Invariants, conventions, and the phase gate.
└── internal/       Plans, design docs, prototypes, scratch.  Local only — gitignored.
```

The two deployables are fully independent: each has its own `.env.example`, its own
dependency manifest, and its own README with deploy steps. Nothing at the repo root is
required at runtime.

---

## Quickstart

**Prerequisites:** PostgreSQL 16 (the only external service), Python 3.14, Node 24.
Optional: `pgvector` (semantic fallback + duplicate detection), `tesseract` (OCR for
scanned pages), `libomp` (LightGBM on macOS). The app degrades gracefully without them.

```bash
# 1. Backend — venv, deps, database, migrations, seed, sample DPRs
./backend/scripts/setup.sh

# 2. Frontend
cd frontend && npm install && cp .env.example .env.local && cd ..

# 3. Run all three processes together
./scripts/dev.sh
```

| | |
|---|---|
| Web | http://localhost:3000 |
| API health | http://localhost:8000/api/v1/health |
| API docs | http://localhost:8000/docs |

Demo logins are printed by the seed step. Two roles ship: an **applicant**, who submits and
self-checks, and a **ministry** user, who appraises, ranks and sanctions. Appraisal and
sanction stay two distinct acts writing two distinct audit events, even though one role
performs both.

Sample DPRs with planted defects are generated into `backend/samples/`.

---

## Deploying

The two halves deploy separately and talk over HTTP.

1. **Backend first** — it needs a Postgres database and a persistent disk for uploaded
   PDFs and page rasters. See [backend/README.md](backend/README.md).
2. **Frontend second** — set `API_PROXY_TARGET` to the deployed backend URL. See
   [frontend/README.md](frontend/README.md).
3. **Back to the backend** — set `CORS_ORIGINS` to the deployed frontend origin.

Next proxies `/api/v1/*` to the backend, so the browser stays on one origin and CORS is
only a fallback. `backend/render.yaml` is a working blueprint for step 1.

---

## Architecture in one paragraph

A PDF upload writes a row and enqueues a job in a **Postgres-backed queue** (`jobs` table,
`FOR UPDATE SKIP LOCKED`). A **standalone worker process** — never a request handler —
parses the document with PyMuPDF, extracts fields via an LLM behind a single provider
module, span-verifies every returned value against the parsed text, scores it against the
rubric, and runs the risk models. The frontend reads the results and renders each evidence
anchor as an absolutely-positioned highlight over a pdf.js canvas.

**No Docker.** Everything runs as native processes; Postgres is the single external
dependency. Rationale and the full invariant list are in
[CONTRIBUTING.md](CONTRIBUTING.md).

---

## Non-negotiables

These are enforced across the codebase — read [CONTRIBUTING.md](CONTRIBUTING.md) first:

- Every extracted value carries ≥1 evidence anchor. A finding without one is a bug.
- LLM output is never trusted for a number, and the claimed value must appear **inside** its
  verified span — proving the quote exists is not enough.
- Money is stored as **paise in BIGINT**, never float. Coordinates are normalised 0–1.
- Model training splits by **time**, never randomly. A random split leaks the future.
- No statistical parameter is invented. If it cannot be sourced from data, it is not modelled.
- No finding may have status `fail`. The system flags; a human decides.
