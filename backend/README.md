# PRAMAAN — Backend

FastAPI API, a standalone job worker, and the ML stack. Deploys independently of
`frontend/`. Everything in this directory is resolved relative to **this** directory —
run all commands from here.

```
backend/
├── api/            FastAPI app — routes, models, schemas, services, llm/
│   └── app/
│       ├── routes/     auth · dprs · assessments · governance   (thin; no logic)
│       ├── services/   business logic, incl. storage.py (the only writer to storage/)
│       ├── llm/        provider.py — the ONLY place an LLM SDK is imported
│       ├── models/     SQLAlchemy 2.x
│       ├── schemas/    Pydantic v2
│       └── config.py   environment settings (business thresholds live in the DB)
├── worker/         background pipeline — never runs inside a request handler
│   ├── parsers/    PyMuPDF text+bbox, pdfplumber tables, Tesseract OCR fallback
│   ├── extractors/ LLM field extraction + span verification
│   ├── evidence/   locate.py — the single text→geometry mapping. Do not reimplement.
│   ├── scoring/    rubric application
│   └── queue.py    Postgres queue: FOR UPDATE SKIP LOCKED
├── ml/
│   ├── data/       PAIMANA panel builder + the historical project panel (committed)
│   ├── train.py    features, time split, calibration, baselines, model card
│   ├── inference.py  predict + SHAP → plain English
│   ├── ranges/     reference class forecasting (P50/P80/P95) — uses no model
│   ├── artifacts/  trained models (committed — a deploy cannot train on boot)
│   └── reports/    model_card.json — the measured numbers behind every claim
├── config/         rubric.yaml, settings_defaults.yaml
├── alembic/        migrations — never edit one that has already run
├── samples/        synthetic DPRs with planted defects (test fixtures + demo data)
├── tests/          one file per build phase
└── scripts/        setup.sh, start.sh, sample generators
```

---

## Local setup

**Prerequisites**

| | |
|---|---|
| PostgreSQL 16+ | required — the only external service |
| Python 3.14 | required (pinned in `.python-version`) |
| `pgvector` | optional — enables semantic fallback (F3) and duplicate detection (F10) |
| `tesseract` | optional — enables the OCR path for scanned pages (F1) |
| `libomp` | required by LightGBM only (macOS: `brew install libomp`) |

```bash
brew install postgresql@16 pgvector && brew services start postgresql@16
./scripts/setup.sh      # venv · deps · createdb · migrate · seed · generate samples · .env
```

`setup.sh` copies `.env.example` to `.env` on first run. Fill in `GEMINI_API_KEY`, or set
`DEMO_MODE=true` to serve every LLM response from the committed cache in `ml/llm_cache/`
without touching the network.

**Run** (two processes — they are separate by design, see invariant #3):

```bash
.venv/bin/uvicorn api.app.main:app --reload --port 8000
.venv/bin/python -m worker.run
```

Or `../scripts/dev.sh` from the repo root to run both plus the frontend.

---

## Environment

Copy `.env.example` → `.env`. Nothing here is a business threshold — those live in the
`settings` table so they change without a deploy.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://localhost:5432/pramaan` | |
| `STORAGE_ROOT` | `./storage` | Uploaded PDFs and page rasters. Must be a persistent volume in production. |
| `JWT_SECRET` | dev placeholder | **Change it.** 32 bytes minimum. |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | `60` / `14` | |
| `MAX_UPLOAD_MB` | `100` | |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated. Only consulted on a split deploy; in dev the frontend proxies and is same-origin. |
| `GEMINI_API_KEY` | — | `GOOGLE_API_KEY` is accepted as an alias. |
| `LLM_MODEL` | `gemini-3.6-flash` | Pinned, not `-latest`: the response cache is keyed by model name. |
| `LLM_THINKING_LEVEL` | `LOW` | Set to `""` for a 2.5-family model, which rejects the parameter. |
| `LLM_TIMEOUT_SECONDS` | `90` | A hung call must not wedge the worker. |
| `DEMO_MODE` | `false` | Serve LLM responses from the committed cache only. Never hits the network. |

---

## Deploying

**What it needs:** a Postgres 16 database, a persistent disk mounted at `STORAGE_ROOT`,
and Python 3.14.

`render.yaml` is a working Render blueprint — point Render at this repo and it provisions
the database, the disk, and the service. Set `CORS_ORIGINS` and `GEMINI_API_KEY` by hand
(they are marked `sync: false`).

For other platforms, `Procfile` declares the processes and `scripts/start.sh` is the
single-container entrypoint (migrate, then API + worker side by side).

```
Root directory   backend
Build            pip install -r requirements.txt
Start            ./scripts/start.sh
Health check     /api/v1/health
```

**The API and the worker must share one filesystem.** Both read and write `STORAGE_ROOT`,
and most managed platforms attach a disk to exactly one service — split them onto separate
services and the worker gets its own empty disk while every highlight 404s. Run them
together (which `start.sh` does) until `api/app/services/storage.py` is swapped to S3; the
indirection exists for exactly that move, and no caller changes.

`/api/v1/health` reports database reachability, storage reachability, queue depth, and
whether the worker has polled in the last two minutes — the worker is a separate process
and easy to forget to start.

---

## Testing

Run only the phase you are working on — never the full suite:

```bash
.venv/bin/pytest tests/test_phase4.py -q
```

## Migrations

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "msg"
```

Every schema change is a migration. **Never edit a migration that has already run** —
other people have already applied it.

## Retraining

```bash
.venv/bin/python -m ml.train        # writes ml/artifacts/ + ml/reports/model_card.json
```

The split is by **time**, never random — a random split leaks the future and turns the
metrics into fiction. Read `ml/reports/model_card.json` before trusting any number the
models produce.
