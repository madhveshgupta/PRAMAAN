#!/usr/bin/env bash
# Run the whole stack locally: api + worker (backend/) and web (frontend/).
# Prefixed output, Ctrl-C stops all three.
set -uo pipefail
cd "$(dirname "$0")/.."

[ -d backend/.venv ] || { echo "No backend/.venv — run ./backend/scripts/setup.sh first"; exit 1; }

# LightGBM needs libomp on macOS and homebrew keeps it keg-only, so it is not on the
# default loader path. Harmless elsewhere.
if [ -d /opt/homebrew/opt/libomp/lib ]; then
  export DYLD_LIBRARY_PATH="/opt/homebrew/opt/libomp/lib:${DYLD_LIBRARY_PATH:-}"
fi
pg_isready -q || { echo "Postgres is not running."; exit 1; }

PIDS=()
cleanup() { echo; echo "stopping..."; for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done; wait 2>/dev/null; }
trap cleanup INT TERM EXIT

prefix() { while IFS= read -r line; do printf "\033[%sm%-7s\033[0m %s\n" "$2" "$1" "$line"; done; }

# Both python processes run with backend/ as the working directory: .env, storage/ and the
# ml/ data paths are all resolved relative to it.
(cd backend && .venv/bin/uvicorn api.app.main:app --reload --port 8000) 2>&1 | prefix api 36 &
PIDS+=($!)
(cd backend && .venv/bin/python -m worker.run) 2>&1 | prefix worker 35 &
PIDS+=($!)

if [ -d frontend/node_modules ]; then
  (cd frontend && npm run dev) 2>&1 | prefix web 33 &
  PIDS+=($!)
else
  echo "frontend/ not installed — skipping (cd frontend && npm install)"
fi

echo "  api    http://localhost:8000/api/v1/health"
echo "  docs   http://localhost:8000/docs"
[ -d frontend/node_modules ] && echo "  web    http://localhost:3000"
wait
