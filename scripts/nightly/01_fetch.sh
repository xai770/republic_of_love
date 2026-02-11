#!/bin/bash
# =============================================================================
# STEP 1: FETCH POSTINGS (Arbeitsagentur + Deutsche Bank)
# =============================================================================
# Network-bound: ~5 minutes
# Sources: AA (16 Bundesländer), DB (corporate API)
# NOTE: AA fetched with --no-descriptions (backfilled in step 2)
# =============================================================================

source "$(dirname "$0")/common.sh"

SINCE=${1:-1}        # Days to look back
MAX_JOBS=${2:-1000}  # Max jobs per source
FORCE_FLAG=${3:-}    # Optional: --force

# 1a. Arbeitsagentur (16 states for reliable batching)
log "[1a/6] Fetching Arbeitsagentur (16 states, metadata only)..."
python3 actors/postings__arbeitsagentur_CU.py \
    --since "$SINCE" \
    --states \
    --max-jobs "$MAX_JOBS" \
    --no-descriptions \
    $FORCE_FLAG </dev/null

# 1b. Deutsche Bank (corporate careers API)
log "[1b/6] Fetching Deutsche Bank..."
python3 actors/postings__deutsche_bank_CU.py \
    --max-jobs "$MAX_JOBS" </dev/null

log "Step 1 complete: fetch"
