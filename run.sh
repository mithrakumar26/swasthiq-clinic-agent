#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Starting backend at http://localhost:8000"
(cd "$ROOT/backend" && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload) &
BACK_PID=$!
cleanup(){ kill $BACK_PID 2>/dev/null || true; }
trap cleanup EXIT INT TERM
cd "$ROOT/frontend"
npm install
npm run dev
