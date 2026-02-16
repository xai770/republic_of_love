#!/usr/bin/env bash
# Start the talent.yoga BI dashboard (Streamlit).
# Cloudflare proxies bi.talent.yoga → localhost:8501
#
# Usage:
#   bash scripts/start_bi.sh          # foreground
#   bash scripts/start_bi.sh --daemon  # background (nohup)

set -euo pipefail
cd "$(dirname "$0")/.."

PORT=8501
LOG="logs/bi_app.log"
APP="tools/bi_app.py"

# Check if already running
if pgrep -f "streamlit run.*${APP}" > /dev/null 2>&1; then
    echo "BI app already running (PID $(pgrep -f "streamlit run.*${APP}" | head -1))"
    exit 0
fi

STREAMLIT="$(command -v streamlit 2>/dev/null || echo "./venv/bin/streamlit")"

if [[ "${1:-}" == "--daemon" ]]; then
    nohup "$STREAMLIT" run "$APP" \
        --server.port "$PORT" \
        --server.headless true \
        --server.address 0.0.0.0 \
        >> "$LOG" 2>&1 &
    echo "BI dashboard started (PID $!, port $PORT, log $LOG)"
else
    exec "$STREAMLIT" run "$APP" \
        --server.port "$PORT" \
        --server.headless true \
        --server.address 0.0.0.0
fi
