#!/bin/bash
# Run Berufenet classification in batches until complete
# Usage: ./scripts/run_berufenet_full.sh

cd /home/xai/Documents/ty_learn
PYTHON="/home/xai/Documents/ty_learn/venv/bin/python"

BATCH_SIZE=2000
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/berufenet_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

echo "Starting Berufenet classification at $(date)" | tee "$LOG_FILE"
echo "Batch size: $BATCH_SIZE" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run batches until no more unprocessed titles
while true; do
    OUTPUT=$($PYTHON actors/postings__berufenet_U.py --batch $BATCH_SIZE 2>&1)
    echo "$OUTPUT" | tee -a "$LOG_FILE"
    
    # Check if no more to process
    if echo "$OUTPUT" | grep -q "No unprocessed titles remaining"; then
        echo "✅ All titles processed!" | tee -a "$LOG_FILE"
        break
    fi
    
    # Small pause between batches
    sleep 2
done

echo "" | tee -a "$LOG_FILE"
echo "Phase 1 completed at $(date)" | tee -a "$LOG_FILE"

# Show intermediate stats
$PYTHON actors/postings__berufenet_U.py --stats | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "PHASE 2: LLM Verification" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Starting LLM verification at $(date)" | tee -a "$LOG_FILE"

# Process pending_llm titles with LLM verification
LLM_BATCH_SIZE=200
while true; do
    # Check how many pending_llm remain
    PENDING=$($PYTHON -c "
from core.database import get_connection_raw
conn = get_connection_raw()
cur = conn.cursor()
cur.execute(\"SELECT COUNT(DISTINCT job_title) FROM postings WHERE berufenet_verified = 'pending_llm'\")
print(cur.fetchone()['count'])
" 2>/dev/null)
    
    if [ "$PENDING" = "0" ] || [ -z "$PENDING" ]; then
        echo "✅ All LLM verifications complete!" | tee -a "$LOG_FILE"
        break
    fi
    
    echo "Pending LLM: $PENDING titles" | tee -a "$LOG_FILE"
    
    # Run LLM verification batch
    OUTPUT=$($PYTHON actors/postings__berufenet_U.py --batch $LLM_BATCH_SIZE --with-llm --pending-only 2>&1)
    echo "$OUTPUT" | tee -a "$LOG_FILE"
    
    sleep 2
done

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "FINAL RESULTS" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Completed at $(date)" | tee -a "$LOG_FILE"

# Show final stats
$PYTHON actors/postings__berufenet_U.py --stats | tee -a "$LOG_FILE"
