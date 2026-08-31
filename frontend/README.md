# PRAMAAN — Frontend

Next.js 16 (App Router) + TypeScript + Tailwind. Deploys independently of `backend/`.

The centrepiece is the **evidence viewer**: a pdf.js canvas with an absolutely-positioned
highlight overlay. Every score, finding, and prediction in the UI is a link that opens the
source PDF at the right page with the supporting region highlighted. Coordinates arrive
normalised 0–1 and are scaled at render time, so highlights stay correct at any zoom.

```
frontend/
├── app/
│   ├── (applicant)/    submission flow — upload, status, findings on your own DPR
│   └── (ministry)/     appraisal flow — queue, assessment, audit trail, sanction gate
├── components/
│   ├── viewer/         PdfViewer + highlight overlay
│   ├── applicant/      upload dialog, submission cards
│   ├── ministry/       assessment panels, risk charts (Recharts)
│   └── landing/        marketing page + GSAP animations
├── lib/
│   ├── api.ts          the single fetch wrapper — all calls go through it
│   ├── auth.tsx        auth context
│   └── motion.ts       shared animation primitives
└── public/
```

---

## Local development

```bash
npm install
cp .env.example .env.local
npm run dev            # http://localhost:3000
```

The backend must be running on port 8000 (`../backend/scripts/setup.sh`, then
`../scripts/dev.sh` from the repo root runs everything together).

---

## Environment

| Variable | Default | Notes |
|---|---|---|
| `API_PROXY_TARGET` | `http://localhost:8000` | Where the FastAPI backend lives. No trailing slash. |

That is the only variable, by design. `next.config.mjs` rewrites `/api/v1/*` to this
target, so the browser only ever talks to the frontend's own origin. That keeps CORS out
of the picture entirely and — more importantly — lets the viewer stream
`/api/v1/documents/:id/pdf` as a same-origin request, which is what makes pdf.js range
requests and auth cookies behave.

It is a **server-side** variable, deliberately not `NEXT_PUBLIC_` — the backend URL is
resolved by the Next server during the proxy hop and never shipped to the browser.

---

## Deploying

Deploy the backend first, then set `API_PROXY_TARGET` to its URL.

### Vercel

```
Root directory     frontend
Framework          Next.js  (auto-detected)
Build command      npm run build
Environment        API_PROXY_TARGET = https://your-api-host.onrender.com
```

`vercel.json` pins the build and install commands; `.nvmrc` pins Node 24.

### Anywhere else

```bash
npm ci && npm run build && npm start      # serves on $PORT, default 3000
```

Requires a Node runtime — this is **not** a static export. The `/api/v1/*` rewrite is a
server-side proxy and disappears under `next export`.

### After deploying

Set `CORS_ORIGINS` on the backend to this app's origin. The proxy means CORS is normally
never exercised, but it is the safety net if anything ever calls the API cross-origin.

---

## Conventions

- Server components by default. `"use client"` only where interactivity demands it.
- `PascalCase` components, `camelCase` functions.
- All API calls go through `lib/api.ts` — never a bare `fetch` to `/api/v1`.
- Never render the whole PDF at once. Virtualise; render the visible page.
- JSON keys from the API are `snake_case` and stay that way — there is no translation layer.
