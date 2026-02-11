#!/bin/bash
# =============================================================================
# STEP 4: ENRICH (Summaries + Embeddings)
# =============================================================================
# GPU-bound: ~5 min summaries, ~3 hr embeddings
#
# 4a. Extract summaries (DB only - strip corporate boilerplate)
# 4b. Generate embeddings (3 parallel workers)
# =============================================================================

source "$(dirname "$0")/common.sh"

# 4a. Extract summaries (Deutsche Bank only)
# AA postings use job_description directly for matching
log "[4a/6] Extracting summaries (DB only)..."
python3 actors/postings__extracted_summary_U.py \
    --batch 5000 \
    --source deutsche_bank </dev/null

# 4b. Generate embeddings (parallel workers)
# Content-addressed design means workers don't conflict
log "[4b/6] Starting 3 parallel embedding workers..."
setsid python3 actors/postings__embedding_U.py --batch 100000 </dev/null &
PID1=$!
setsid python3 actors/postings__embedding_U.py --batch 100000 </dev/null &
PID2=$!
setsid python3 actors/postings__embedding_U.py --batch 100000 </dev/null &
PID3=$!

wait $PID1 $PID2 $PID3
log "All embedding workers complete"

log "Step 4 complete: enrich"
