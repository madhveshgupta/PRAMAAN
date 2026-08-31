# Contributing to PRAMAAN

Read this before your first change. It is short on purpose.

---

## The prime directive

> **No number reaches the user without a verifiable pointer to where it came from.**

Concretely:

- Every extracted field carries `evidence[]` — a non-empty list of
  `{page, bbox, snippet, confidence, method}`.
- If the LLM returns a value whose claimed source span **cannot be re-located in the parsed
  document text**, that value is **rejected and logged**. It is never stored, never
  displayed, never scored.
- A finding with no evidence anchor is a bug, not a finding.

If you are ever tempted to store a value "just for now" without evidence, stop. That
shortcut breaks the one thing that makes this project defensible.

---

## Hard invariants

| # | Invariant | Why |
|---|---|---|
| 1 | Every extracted value and every finding has ≥1 evidence anchor. | The prime directive. |
| 2 | LLM output is **never** trusted for a number. Always span-verified against parsed text. | Hallucinated budgets are disqualifying in a government tool. |
| 3 | PDF parsing happens **only** in the background worker process, never in a request handler. | A 400-page PDF will time out any HTTP request. |
| 4 | The system **never auto-rejects** a DPR. It scores and flags; a named human with `can_sanction` decides. No finding may have status `fail`. | Adoption and ethics. Stated on the UI. |
| 5 | All LLM calls go through `backend/api/app/llm/provider.py`. No direct SDK calls elsewhere. | Makes a move to an on-prem model a one-file change. |
| 6 | Model predictions are always returned with SHAP attributions attached. | Explainability is an appraisal requirement, not a nice-to-have. |
| 7 | Money is stored in **paise as BIGINT**, never float. Display converts to ₹ Cr/Lakh. | Float rupees in a financial tool is indefensible. |
| 8 | Coordinates are stored **normalised 0–1** against page width/height. | The viewer renders at arbitrary zoom; pixel coordinates break. |
| 9 | Never train/test split randomly on the project panel data. Always split by time. | A random split leaks the future and the metrics become fiction. |
| 10 | Every DB schema change is an Alembic migration. Never edit a migration that has already run. | Someone else has already applied it. |
| 11 | **A claimed value must appear inside its verified evidence span.** Proving the quote exists is not enough. | A model can quote a real sentence and attach a fabricated number to it. Span-only verification accepts that. |
| 12 | **Ingest is idempotent — clear all derived rows before reprocessing a document.** | A crash plus a stale-lock reclaim appends duplicate spans, doubling char offsets and silently corrupting every highlight in the document. |
| 13 | Never invent a statistical parameter. If we cannot source a number from data, we do not model with it. | This is why Monte Carlo was rejected — its correlation matrix would have been fabricated. |

---

## Conventions

**Python** — `snake_case`, type hints everywhere. Pydantic schemas in
`backend/api/app/schemas/`. Business logic in `backend/api/app/services/`, never in a route
handler. Raise typed exceptions from services; one global handler maps them to HTTP.

**TypeScript** — `PascalCase` components, `camelCase` functions. Server components by
default; `"use client"` only where interactivity demands it. All API calls go through
`frontend/lib/api.ts`.

**API** — `/api/v1/...`, plural nouns, `snake_case` JSON keys (matches Pydantic, so there is
no translation layer). UUIDv4 primary keys everywhere.

**Comments** — explain *why*, never *what*. Match the density of the surrounding code.

---

## Never do these

- Never `pip install` or `npm install` without pinning it to an exact version in
  `requirements.txt` / `package.json` in the same change. With no container, the lockfile is
  the only thing keeping laptops in sync.
- Never commit `.env`, model artifacts over 50MB, or sample PDFs over 10MB.
- Never call an LLM inside a loop over pages. Batch it.
- Never render the whole PDF at once in the browser. Virtualise; render the visible page.
- Never store a float rupee value.
- Never write to `backend/storage/` directly. Go through
  `backend/api/app/services/storage.py`, so the filesystem can be swapped for S3 later
  without touching callers.
- Never build your own evidence anchor. Call `backend/worker/evidence/locate.py`. Three
  modules need the same text→geometry mapping; three implementations means three
  coordinate bugs.
- Never hardcode a threshold. It goes in the `settings` table, so it can change without a
  deploy.

---

## Testing

Run only the tests for the area you are touching — never the full suite in a working loop:

```bash
cd backend && .venv/bin/pytest tests/test_phase4.py -q
```

## Migrations

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "msg"
.venv/bin/alembic upgrade head
```

Never edit a migration that has already run.
