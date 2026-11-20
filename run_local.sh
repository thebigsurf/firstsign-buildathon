#!/usr/bin/env bash
# Builds the frontend if needed and serves app + API on http://localhost:8000.
# Usage: bash run_local.sh        (add DEMO_OFFLINE=1 to use canned results without Gemini)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ ! -f frontend/dist/index.html ]; then
  echo "Building frontend..."
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
fi
python -m pip install -q -r backend/requirements.txt
cd backend
echo "FirstSign on http://localhost:${PORT:-8000}"
exec python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
