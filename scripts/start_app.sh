#!/usr/bin/env bash
# Start the talent.yoga FastAPI app with uvicorn.
# Usage: bash scripts/start_app.sh [--reload]

set -euo pipefail
cd "$(dirname "$0")/.."

RELOAD=""
if [[ "${1:-}" == "--reload" ]]; then
    RELOAD="--reload"
fi

exec uvicorn api.main:app --host 0.0.0.0 --port 8000 $RELOAD
