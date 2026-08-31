#!/usr/bin/env bash
# Production entrypoint. Migrates, then runs the API and the job worker side by side.
#
# They are separate PROCESSES (invariant #3: a 400-page PDF never parses inside a request
# handler) but they live on one host, because both read and write the same storage/ tree.
# Split them onto separate services only after services/storage.py moves to S3.
set -euo pipefail
cd "$(dirname "$0")/.."

alembic upgrade head

# Demo accounts. Every insert in seed.py is guarded by an existence check, so this is a
# no-op on an already-seeded database and safe to run on every boot. It lives here because
# Render's free plan gives no shell to run it by hand once, and a wiped-and-recreated free
# database would otherwise come back with an empty users table and no way to log in.
#
# It creates two known accounts with a published password (see seed.DEMO_PASSWORD).
# Set SEED_DEMO_USERS=0 before this stops being a demo.
if [ "${SEED_DEMO_USERS:-1}" != "0" ]; then
  python -m api.app.seed
fi

pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup INT TERM EXIT

python -m worker.run & pids+=($!)
uvicorn api.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" & pids+=($!)

# If either process dies the container should die with it, so the platform restarts both.
# `wait -n` would say this in one line, but it needs bash 4.3+ and macOS ships 3.2 — the
# script has to run on a developer's laptop as well as on the Linux host, so poll instead.
while :; do
  for p in "${pids[@]}"; do
    if ! kill -0 "$p" 2>/dev/null; then
      status=0
      wait "$p" || status=$?
      exit "$status"
    fi
  done
  sleep 5
done
