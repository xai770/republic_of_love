#!/bin/bash
# Backfill Watchdog - Auto-resume backfills after system restart, crash, or network hang
# 
# Add to crontab:
#   @reboot /home/xai/Documents/ty_learn/scripts/backfill_watchdog.sh
#   */10 * * * * /home/xai/Documents/ty_learn/scripts/backfill_watchdog.sh
#
# This script:
# 1. Checks if backfills are needed
# 2. Detects STUCK processes (running but no progress for 10+ minutes)
# 3. Kills stuck processes and restarts them

set -e
cd /home/xai/Documents/ty_learn
source venv/bin/activate
export PYTHONUNBUFFERED=1

LOCKFILE="/tmp/backfill_watchdog.lock"
LOG="/home/xai/Documents/ty_learn/logs/watchdog_backfill.log"
PROGRESS_FILE="/tmp/backfill_progress.txt"
STUCK_THRESHOLD_MINUTES=10

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

# Prevent concurrent watchdog runs
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        exit 0
    fi
    rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Get current description count (used to detect progress)
get_desc_count() {
    python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND LENGTH(job_description) > 100')
    print(cur.fetchone()['cnt'])
" 2>/dev/null || echo "0"
}

# Check if process is stuck (running but no progress)
is_process_stuck() {
    local PROCESS_NAME="$1"
    local PID=$(pgrep -f "$PROCESS_NAME" 2>/dev/null | head -1)
    
    if [ -z "$PID" ]; then
        return 1  # Not running, so not stuck
    fi
    
    # Get current desc count
    local CURRENT_COUNT=$(get_desc_count)
    
    # Read last known count and timestamp
    if [ -f "$PROGRESS_FILE" ]; then
        local LAST_DATA=$(cat "$PROGRESS_FILE")
        local LAST_COUNT=$(echo "$LAST_DATA" | cut -d'|' -f1)
        local LAST_TIME=$(echo "$LAST_DATA" | cut -d'|' -f2)
        local NOW=$(date +%s)
        local ELAPSED=$(( (NOW - LAST_TIME) / 60 ))
        
        if [ "$CURRENT_COUNT" = "$LAST_COUNT" ] && [ "$ELAPSED" -ge "$STUCK_THRESHOLD_MINUTES" ]; then
            log "STUCK DETECTED: No progress in ${ELAPSED} minutes (count stuck at $CURRENT_COUNT)"
            return 0  # Stuck!
        fi
    fi
    
    # Save current progress
    echo "${CURRENT_COUNT}|$(date +%s)" > "$PROGRESS_FILE"
    return 1  # Not stuck
}

# Kill stuck process
kill_stuck_process() {
    local PROCESS_NAME="$1"
    local PID=$(pgrep -f "$PROCESS_NAME" 2>/dev/null | head -1)
    
    if [ -n "$PID" ]; then
        log "Killing stuck process $PROCESS_NAME (PID $PID)"
        kill -9 "$PID" 2>/dev/null || true
        sleep 2
        # Clear progress file to reset stuck detection
        rm -f "$PROGRESS_FILE"
    fi
}

# Check if description backfill is needed
check_desc_backfill() {
    MISSING=$(python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute('''SELECT COUNT(*) as cnt FROM postings 
        WHERE source = 'arbeitsagentur' 
        AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100)
        AND COALESCE(invalidated, false) = false
        AND COALESCE(processing_failures, 0) < 3''')
    print(cur.fetchone()['cnt'])
" 2>/dev/null || echo "0")

    # Check if stuck
    if is_process_stuck "postings__job_description_U"; then
        kill_stuck_process "postings__job_description_U"
        # Fall through to restart
    elif pgrep -f "postings__job_description_U" > /dev/null; then
        return 1  # Running and making progress
    fi
    
    if [ "$MISSING" -gt 100 ]; then
        return 0  # Needs backfill
    fi
    return 1
}

# Check if embedding backfill is needed
check_embed_backfill() {
    PENDING=$(python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute('''SELECT COUNT(*) as cnt FROM postings_for_matching p 
        WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = p.match_text)''')
    print(cur.fetchone()['cnt'])
" 2>/dev/null || echo "0")

    if pgrep -f "postings__embedding_U" > /dev/null; then
        return 1  # Already running (embeddings are fast, don't need stuck detection)
    fi
    
    if [ "$PENDING" -gt 50 ]; then
        return 0  # Needs backfill
    fi
    return 1
}

# Main logic
log "Watchdog check started"

if check_desc_backfill; then
    log "Starting description backfill ($MISSING missing)"
    nohup python3 actors/postings__job_description_U.py --batch 20000 \
        >> logs/desc_backfill_$(date +%Y%m%d_%H%M).log 2>&1 &
    log "Description backfill started with PID $!"
    # Initialize progress tracking
    echo "$(get_desc_count)|$(date +%s)" > "$PROGRESS_FILE"
fi

if check_embed_backfill; then
    log "Starting embedding backfill ($PENDING pending)"
    nohup python3 actors/postings__embedding_U.py --batch 50000 \
        >> logs/embed_backfill_$(date +%Y%m%d_%H%M).log 2>&1 &
    log "Embedding backfill started with PID $!"
fi

log "Watchdog check complete"
