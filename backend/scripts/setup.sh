#!/usr/bin/env bash
# PRAMAAN backend one-time setup. Run from anywhere; it operates on backend/.
# Must work on a teammate's laptop from a clean clone —
# that is Phase 1's real exit gate, not /health returning green.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PYTHON:-python3}
DB=${PGDATABASE:-pramaan}

say()  { printf "\n\033[1m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[33m  ! %s\033[0m\n" "$*"; }
ok()   { printf "\033[32m  ✔ %s\033[0m\n" "$*"; }

say "Checking native dependencies"
command -v "$PY" >/dev/null || { echo "python3 not found"; exit 1; }
ok "$($PY --version)"

if ! command -v psql >/dev/null; then
  echo "psql not found. Install Postgres:"
  echo "  macOS:  brew install postgresql@16 && brew services start postgresql@16"
  echo "  Debian: sudo apt install postgresql-16"
  echo "  Then re-run. If psql is installed but not on PATH, add its bin/ directory."
  exit 1
fi
ok "psql $(psql --version | awk '{print $3}')"

pg_isready -q || { echo "Postgres is installed but not running."; \
  echo "  macOS: brew services start postgresql@16"; exit 1; }
ok "Postgres accepting connections"

# Optional native deps. The app degrades gracefully; we say so rather than failing.
command -v tesseract >/dev/null \
  && ok "tesseract $(tesseract --version 2>&1 | head -1 | awk '{print $2}')" \
  || warn "tesseract missing — OCR path disabled (scanned PDFs will parse as empty). brew install tesseract"

$PY - <<'EOF' 2>/dev/null && echo "  ✔ libomp present (lightgbm usable)" || echo "  ! libomp missing — lightgbm (Phase 7) will not import. brew install libomp"
import ctypes.util, sys
sys.exit(0 if ctypes.util.find_library("omp") else 1)
EOF

say "Creating virtualenv"
[ -d .venv ] || $PY -m venv .venv
ok ".venv ready"

say "Installing Python dependencies (pinned)"
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt
ok "$(.venv/bin/python -m pip list --format=freeze | wc -l | tr -d ' ') packages installed"

say "Database"
if psql -lqt | cut -d'|' -f1 | grep -qw "$DB"; then ok "database '$DB' exists"
else createdb "$DB" && ok "database '$DB' created"; fi

# pgvector is optional: it enables F3's semantic fallback and F10 duplicate detection.
if psql -d "$DB" -tAc "SELECT 1 FROM pg_available_extensions WHERE name='vector'" | grep -q 1; then
  psql -d "$DB" -qc "CREATE EXTENSION IF NOT EXISTS vector" && ok "pgvector enabled"
else
  warn "pgvector unavailable — semantic fallback (F3) and duplicate detection (F10) run in Python instead. brew install pgvector"
fi

say "Migrations"
.venv/bin/alembic upgrade head
ok "schema at $(.venv/bin/alembic current 2>/dev/null | tail -1)"

say "Seeding"
.venv/bin/python -m api.app.seed

say "Sample DPRs"
if [ -f samples/dpr_bridge_defective.pdf ]; then ok "already generated"
else .venv/bin/python scripts/make_samples.py; fi

[ -f .env ] || { cp .env.example .env; ok ".env created from .env.example"; }
mkdir -p storage

printf "\n\033[32m✔ Backend ready.\033[0m\n"
printf "  Frontend:  cd ../frontend && npm install && cp .env.example .env.local\n"
printf "  Run all:   ./scripts/dev.sh   (from the repo root)\n\n"
