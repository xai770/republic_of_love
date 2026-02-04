#!/bin/bash
# Nightly job posting fetch + summary + embedding pipeline
# Sources: Arbeitsagentur (AA), Deutsche Bank (DB)
# Cron: 0 20 * * * /home/xai/Documents/ty_learn/scripts/nightly_fetch.sh >> /var/log/ty_nightly.log 2>&1
#
# Pipeline Flowchart:
# ```mermaid
# flowchart TD
#     subgraph "1. FETCH (network-bound)"
#         A1[🇩🇪 AA API<br/>16 states] --> A2[💼 DB API]
#         A2 --> A3[🔄 Backfill missing<br/>job_descriptions]
#     end
#     
#     subgraph "2. ENRICH (GPU-bound)"
#         B1[📝 Extract summaries<br/>DB only]
#     end
#     
#     subgraph "3. EMBED (GPU-bound, parallel)"
#         C1[Worker 1] 
#         C2[Worker 2]
#         C3[Worker 3]
#     end
#     
#     A3 --> B1
#     B1 --> C1 & C2 & C3
#     C1 & C2 & C3 --> D[📊 Summary stats]
# ```

set -e
cd /home/xai/Documents/ty_learn
source venv/bin/activate

# CRITICAL: Disable Python output buffering so logs appear in real-time
export PYTHONUNBUFFERED=1

# ============================================================================
# LOCK FILE - Prevent concurrent runs
# ============================================================================
LOCKFILE="/tmp/nightly_fetch.lock"
if [ -f "$LOCKFILE" ]; then
    PID=$(cat "$LOCKFILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Already running (PID $PID) - exiting"
        exit 0
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🧹 Stale lock file found, removing"
        rm -f "$LOCKFILE"
    fi
fi
echo $$ > "$LOCKFILE"

# ============================================================================
# PAUSE CONFLICTING GPU JOBS (Berufenet LLM batch)
# ============================================================================
BERUFENET_PIDS=$(pgrep -f "postings__berufenet" 2>/dev/null || true)
if [ -n "$BERUFENET_PIDS" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⏸️  Pausing Berufenet job (PIDs: $BERUFENET_PIDS)..."
    kill -STOP $BERUFENET_PIDS 2>/dev/null || true
    BERUFENET_PAUSED=1
else
    BERUFENET_PAUSED=0
fi

# Cleanup function to resume Berufenet on exit (even on error)
cleanup() {
    if [ "$BERUFENET_PAUSED" = "1" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ▶️  Resuming Berufenet job..."
        kill -CONT $BERUFENET_PIDS 2>/dev/null || true
    fi
    rm -f "$LOCKFILE"
}
trap cleanup EXIT

# ============================================================================
# STATUS CHECK MODE - Show current state without running pipeline
# ============================================================================
if [ "$1" = "status" ] || [ "$1" = "--status" ]; then
    echo "=== NIGHTLY FETCH STATUS ==="
    echo ""
    
    # Check if running
    if [ -f "$LOCKFILE" ]; then
        PID=$(cat "$LOCKFILE" 2>/dev/null)
        if kill -0 "$PID" 2>/dev/null; then
            echo "🔄 Pipeline RUNNING (PID $PID)"
            echo ""
            # Show what's running
            echo "Active processes:"
            ps aux | grep -E "arbeitsagentur|deutsche_bank|job_description|embedding|extracted_summary" | grep -v grep | awk '{print "  " $11 " " $12 " " $13}'
            echo ""
        else
            echo "⏹️  Pipeline NOT running (stale lock file)"
        fi
    else
        echo "⏹️  Pipeline NOT running"
    fi
    
    # Show DB stats
    echo "📊 Database Status:"
    python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings')
    total = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND LENGTH(job_description) > 100')
    with_desc = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings WHERE source = 'arbeitsagentur' AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100) AND COALESCE(invalidated, false) = false''')
    missing_desc = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings_for_matching')
    eligible = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings_for_matching p WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = p.match_text)''')
    pending_embed = cur.fetchone()['cnt']
    
    print(f'   Total postings:       {total:,}')
    print(f'   With description:     {with_desc:,}')
    print(f'   Missing description:  {missing_desc:,}')
    print(f'   Eligible for match:   {eligible:,}')
    print(f'   Pending embeddings:   {pending_embed}')
"
    echo ""
    
    # Show recent log if exists
    if [ -f /var/log/ty_nightly.log ]; then
        echo "📜 Recent log (last 10 lines):"
        tail -10 /var/log/ty_nightly.log | sed 's/^/   /'
    fi
    
    exit 0
fi

# ============================================================================
# DEBUG MODE - Low-level process info, live logs, file descriptors
# ============================================================================
if [ "$1" = "debug" ] || [ "$1" = "--debug" ]; then
    echo "=== NIGHTLY FETCH DEBUG ==="
    echo ""
    
    # Find all related processes
    echo "🔍 ALL RELATED PROCESSES (full detail):"
    ps aux | head -1
    ps aux | grep -E "arbeitsagentur|deutsche_bank|job_description|embedding|extracted_summary|nightly_fetch" | grep -v grep
    echo ""
    
    # Check lock file
    echo "🔒 Lock file:"
    if [ -f "$LOCKFILE" ]; then
        echo "   EXISTS: $LOCKFILE"
        echo "   PID: $(cat $LOCKFILE)"
        echo "   Process alive: $(kill -0 $(cat $LOCKFILE) 2>/dev/null && echo 'YES' || echo 'NO')"
    else
        echo "   No lock file"
    fi
    echo ""
    
    # Show open files/connections for python processes
    echo "📂 Open files (Python processes):"
    for pid in $(pgrep -f "python3.*actors/"); do
        echo "   PID $pid: $(ls /proc/$pid/fd 2>/dev/null | wc -l) open file descriptors"
        # Show what it's doing
        echo "   Command: $(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' | cut -c1-100)"
        # Show last few lines of stdout if available
        if [ -f /proc/$pid/fd/1 ]; then
            echo "   Writing to: $(readlink /proc/$pid/fd/1 2>/dev/null)"
        fi
    done
    echo ""
    
    # Network connections
    echo "🌐 Network connections (Python):"
    ss -tp 2>/dev/null | grep python | head -10 || echo "   (none or ss not available)"
    echo ""
    
    # Recent log files in logs/
    echo "📜 Recent log files:"
    ls -lt logs/*.log 2>/dev/null | head -5 | awk '{print "   " $6 " " $7 " " $8 " " $9}'
    echo ""
    
    # Tail the most recent backfill log
    LATEST_LOG=$(ls -t logs/desc_backfill*.log logs/embed_backfill*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo "📄 Latest backfill log ($LATEST_LOG):"
        echo "   --- last 20 lines ---"
        tail -20 "$LATEST_LOG" 2>/dev/null | sed 's/^/   /'
        echo ""
    fi
    
    # Show /var/log/ty_nightly.log tail
    if [ -f /var/log/ty_nightly.log ]; then
        echo "📄 Cron log (/var/log/ty_nightly.log):"
        echo "   --- last 30 lines ---"
        tail -30 /var/log/ty_nightly.log | sed 's/^/   /'
    fi
    
    # CPU/Memory of related processes
    echo ""
    echo "💻 Resource usage:"
    ps -o pid,pcpu,pmem,etime,cmd --sort=-pcpu | grep -E "python3.*actors/|python3.*scripts/" | grep -v grep | head -5 | awk '{print "   " $0}'
    
    exit 0
fi

# ============================================================================
# TAIL MODE - Live follow of latest backfill log (Ctrl+C to exit)
# ============================================================================
if [ "$1" = "tail" ] || [ "$1" = "--tail" ]; then
    LATEST_LOG=$(ls -t logs/desc_backfill*.log logs/embed_backfill*.log 2>/dev/null | head -1)
    
    if [ -z "$LATEST_LOG" ]; then
        echo "❌ No backfill log found in logs/"
        exit 1
    fi
    
    echo "📄 Tailing: $LATEST_LOG"
    echo "   (Ctrl+C to exit)"
    echo "   ─────────────────────────────────────"
    tail -f "$LATEST_LOG"
    exit 0
fi

SINCE=${1:-1}        # Default: last 1 day
MAX_JOBS=${2:-1000}  # Default: 1000 jobs per city (AA) / total (DB)
FORCE=${3:-}         # Optional: pass "force" to skip preflight
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

FORCE_FLAG=""
if [ "$FORCE" = "force" ]; then
    FORCE_FLAG="--force"
fi

echo "$LOG_PREFIX Starting nightly fetch pipeline (since=$SINCE days, max_jobs=$MAX_JOBS${FORCE:+, FORCED})"

# ============================================================================
# STEP 1: FETCH POSTINGS (network-bound)
# ============================================================================

# 1a. Arbeitsagentur (German job board - state-by-state for reliability)
# Using --states (16 Bundesländer) instead of --nationwide for better progress tracking
# and more reliable batching (smaller queries, less likely to timeout)
# NOTE: Using --no-descriptions for speed - descriptions are backfilled in step 1c
echo "$LOG_PREFIX [1/6] Fetching Arbeitsagentur (16 states, metadata only)..."
python3 actors/postings__arbeitsagentur_CU.py --since $SINCE --states --max-jobs $MAX_JOBS --no-descriptions $FORCE_FLAG

# 1b. Deutsche Bank (corporate careers API - ~1 minute)
echo "$LOG_PREFIX [2/6] Fetching Deutsche Bank..."
python3 actors/postings__deutsche_bank_CU.py --max-jobs $MAX_JOBS

# 1c. Backfill missing job descriptions (scrape retries for failed fetches)
# ~30% of AA scrapes fail due to rate limiting - this catches them
# Use high batch limit to catch up on backlog (rate limiting will naturally throttle)
echo "$LOG_PREFIX [3/5] Backfilling missing job descriptions..."
python3 actors/postings__job_description_U.py --batch 50000

# ============================================================================
# STEP 2: EXTRACT SUMMARIES (GPU-bound, LLM) - DB ONLY
# ============================================================================
# AA postings don't need summaries - we use job_description directly for matching
# DB postings need summaries to strip corporate boilerplate
echo "$LOG_PREFIX [4/5] Extracting summaries (DB only)..."
python3 actors/postings__extracted_summary_U.py --batch 5000 --source deutsche_bank

# ============================================================================
# STEP 5: GENERATE EMBEDDINGS (GPU-bound, parallel)
# ============================================================================
# Content-addressed design means workers don't conflict - they skip already-embedded text
# NOTE: Embeddings use match_text = COALESCE(extracted_summary, job_description)
# No batch limit - process ALL pending (content-addressed = no duplicates)
echo "$LOG_PREFIX [5/5] Starting 3 parallel embedding workers..."
python3 actors/postings__embedding_U.py --batch 100000 &
PID1=$!
python3 actors/postings__embedding_U.py --batch 100000 &
PID2=$!
python3 actors/postings__embedding_U.py --batch 100000 &
PID3=$!

wait $PID1 $PID2 $PID3
echo "$LOG_PREFIX All embedding workers complete"

# Summary
echo "$LOG_PREFIX Pipeline complete. Summary:"
python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    cur.execute(\"SELECT COUNT(*) as cnt FROM postings WHERE source = 'arbeitsagentur'\")
    aa_postings = cur.fetchone()['cnt']
    
    cur.execute(\"SELECT COUNT(*) as cnt FROM postings WHERE source = 'deutsche_bank'\")
    db_postings = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings')
    total_postings = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND LENGTH(job_description) > 100')
    with_desc = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE extracted_summary IS NOT NULL')
    with_summary = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM embeddings')
    embeds = cur.fetchone()['cnt']
    
    # Count unembedded - use postings_for_matching view (same as embedding actor)
    # Embedding actor uses: e.text = p.match_text for existence check
    cur.execute('''
        SELECT COUNT(*) as cnt FROM postings_for_matching p 
        WHERE NOT EXISTS (
            SELECT 1 FROM embeddings e 
            WHERE e.text = p.match_text
        )
    ''')
    pending = cur.fetchone()['cnt']
    
    print(f'  AA postings:      {aa_postings:,}')
    print(f'  DB postings:      {db_postings:,}')
    print(f'  Total postings:   {total_postings:,}')
    print(f'  With description: {with_desc:,}')
    print(f'  With summary:     {with_summary:,}')
    print(f'  Embeddings:       {embeds:,}')
    print(f'  Pending embed:    {pending:,}')
"
