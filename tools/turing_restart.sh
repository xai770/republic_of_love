#!/usr/bin/env bash
# Restart the talent.yoga uvicorn server
# Usage: bash tools/turing_restart.sh

set -e

cd "$(dirname "$0")/.."

echo "⏹  Stopping uvicorn..."
pkill -f "uvicorn api.main:app" 2>/dev/null || true
sleep 1

echo "▶  Starting uvicorn on :8000..."
nohup /home/xai/.local/bin/uvicorn api.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    >> logs/uvicorn.log 2>&1 &

echo "✅ PID $! — logs at logs/uvicorn.log"
