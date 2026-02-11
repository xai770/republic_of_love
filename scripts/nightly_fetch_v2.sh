#!/bin/bash
# =============================================================================
# NIGHTLY FETCH PIPELINE - ORCHESTRATOR
# =============================================================================
# Thin wrapper that calls modular step scripts
#
# Sources: Arbeitsagentur (AA), Deutsche Bank (DB)
# Schedule: Daily at 20:00 CET
# Cron: 0 20 * * * /home/xai/Documents/ty_learn/scripts/nightly_fetch.sh >> /var/log/ty_nightly.log 2>&1
#
# Usage:
#   ./nightly_fetch.sh           # Run full pipeline
#   ./nightly_fetch.sh status    # Show current state without running
#   ./nightly_fetch.sh tail      # Follow log output
#
# =============================================================================
# PIPELINE STEPS
# =============================================================================
#
#   Step 1: FETCH      - AA (16 states) + DB API          ~5 min
#   Step 2: BACKFILL   - Job descriptions + partners      ~2 hr
#   Step 3: CLASSIFY   - Berufenet lookup + auto-match    ~1 min
#   Step 4: ENRICH     - Summaries (DB) + embeddings      ~3 hr
#
# Total: ~5-6 hours
#
# =============================================================================

set -e
SCRIPT_DIR="$(dirname "$0")/nightly"

# Source common for lock/cleanup
source "$SCRIPT_DIR/common.sh"

# =============================================================================
# STATUS MODE
# =============================================================================
if [ "$1" = "status" ] || [ "$1" = "--status" ]; then
    bash "$SCRIPT_DIR/status.sh"
    exit 0
fi

# =============================================================================
# TAIL MODE
# =============================================================================
if [ "$1" = "tail" ] || [ "$1" = "--tail" ]; then
    LATEST_LOG=$(ls -t logs/desc_backfill*.log logs/embed_backfill*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        echo "❌ No backfill log found in logs/"
        exit 1
    fi
    echo "📄 Tailing: $LATEST_LOG (Ctrl+C to exit)"
    tail -f "$LATEST_LOG"
    exit 0
fi

# =============================================================================
# MAIN PIPELINE
# =============================================================================

SINCE=${1:-1}
MAX_JOBS=${2:-1000}
FORCE=${3:-}

FORCE_FLAG=""
[ "$FORCE" = "force" ] && FORCE_FLAG="--force"

# Acquire lock and setup cleanup
acquire_lock
pause_berufenet
setup_cleanup

log "🚀 Starting nightly fetch pipeline (since=$SINCE days, max_jobs=$MAX_JOBS${FORCE:+, FORCED})"

# Step 1: Fetch postings
bash "$SCRIPT_DIR/01_fetch.sh" "$SINCE" "$MAX_JOBS" "$FORCE_FLAG"

# Step 2: Backfill descriptions
bash "$SCRIPT_DIR/02_backfill.sh"

# Step 3: Berufenet classification
bash "$SCRIPT_DIR/03_classify.sh"

# Step 4: Enrich (summaries + embeddings)
bash "$SCRIPT_DIR/04_enrich.sh"

# Summary
bash "$SCRIPT_DIR/summary.sh"

log "✅ Pipeline complete"
