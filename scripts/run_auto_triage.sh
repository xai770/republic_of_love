#!/bin/bash
# Bulk auto-triage: run LLM on all pending owl_pending items
# 2026-02-11

LOG="/home/xai/Documents/ty_learn/logs/auto_triage_$(date +%Y%m%d_%H%M%S).log"
echo "=== Auto-triage started $(date) ===" | tee "$LOG"

BATCH=0
while true; do
    BATCH=$((BATCH + 1))
    echo "--- Batch $BATCH ($(date)) ---" | tee -a "$LOG"

    RESULT=$(curl -s -o /dev/null -w '%{redirect_url}' \
        -X POST http://localhost:8000/admin/owl-triage/auto \
        -d 'batch_size=50&page=1' 2>&1)

    echo "  $RESULT" | tee -a "$LOG"

    # Check if no pending items left
    if echo "$RESULT" | grep -q "No+pending+items"; then
        echo "=== All done at batch $BATCH ($(date)) ===" | tee -a "$LOG"
        break
    fi

    # Check for errors
    if echo "$RESULT" | grep -q "flash_type=error"; then
        echo "=== Error at batch $BATCH, stopping ($(date)) ===" | tee -a "$LOG"
        break
    fi

    # Brief pause to avoid hammering
    sleep 1
done

echo "=== Auto-triage finished $(date) ===" | tee -a "$LOG"
