#!/bin/bash
# Backfill Watchdog - Auto-resume backfills after system restart or crash
# 
# Add to crontab:
#   @reboot /home/xai/Documents/ty_learn/scripts/backfill_watchdog.sh
#   */10 * * * * /home/xai/Documents/ty_learn/scripts/backfill_watchdog.sh
#
# This script checks if backfills are needed and no process is running,
# then starts them automatically.

set -e
cd /home/xai/Documents/ty_learn
source venv/bin/activate
export PYTHONUNBUFFERED=1

LOCKFILE="/tmp/backfill_watchdog.lock"
LOG="/home/xai/Documents/ty_learn/logs/watchdog_backfill.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

# Prevent concurrent runs
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        exit 0
    fi
    rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Check if description backfill is needed and not running
check_desc_backfill() {
    # Count missing descriptions
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

    # Check if process is running
    if pgrep -f "postings__job_description_U" > /dev/null; then
        return 1  # Already running
    fi
    
    if [ "$MISSING" -gt 100 ]; then
        return 0  # Needs backfill
    fi
    return 1
}

# Check if embedding backfill is needed and not running
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
        return 1  # Already running
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
fi

if check_embed_backfill; then
    log "Starting embedding backfill ($PENDING pending)"
    nohup python3 actors/postings__embedding_U.py --batch 50000 \
        >> logs/embed_backfill_$(date +%Y%m%d_%H%M).log 2>&1 &
    log "Embedding backfill started with PID $!"
fi

log "Watchdog check complete"
