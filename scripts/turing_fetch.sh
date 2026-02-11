#!/bin/bash
# turing_fetch — Job posting fetch + classify + enrich pipeline
# Sources: Arbeitsagentur (AA), Deutsche Bank (DB)
# Safe to run anytime — idempotent, picks up where it left off.
# Cron: 0 20 * * * /home/xai/Documents/ty_learn/scripts/turing_fetch.sh >> /var/log/ty_fetch.log 2>&1
#
# Pipeline Flowchart:
# ```mermaid
# flowchart TD
#     subgraph "1. FETCH (network-bound)"
#         A1[🇩🇪 AA API<br/>16 states] --> A2[💼 DB API]
#     end
#
#     subgraph "2. BERUFENET (OWL-first)"
#         C1[🦉 OWL lookup<br/>instant] --> C2{hit?}
#         C2 -- yes --> C3[✅ verified='owl']
#         C2 -- no/phase2 --> C4[📐 embed + LLM<br/>~14/sec]
#         C4 --> C5[add OWL synonym]
#         C4 -- uncertain --> C6[owl_pending]
#     end
#
#     subgraph "3. ENRICH (turing_daemon)"
#         B1[job_description_backfill] --> B4[embedding_generator x3]
#         B5[🤖 owl_pending_auto_triage<br/>LLM picks best match] --> B6[new OWL synonyms]
#     end
#
#     A2 --> C1
#     C3 --> B1
#     C5 --> B1
#     C6 --> B5
#     B4 --> D[📊 Summary stats]
# ```

set -e
cd /home/xai/Documents/ty_learn
source venv/bin/activate

# CRITICAL: Disable Python output buffering so logs appear in real-time
export PYTHONUNBUFFERED=1

# ============================================================================
# LOGGING - Always append to logs/nightly_fetch.log
# ============================================================================
LOGFILE="logs/turing_fetch.log"
exec > >(tee -a "$LOGFILE") 2>&1

# Timestamp helper
ts() { echo "[$(date '+%Y-%m-%d %H:%M:%S')]" "$@"; }

# ============================================================================
# LOCK FILE - Prevent concurrent runs
# ============================================================================
LOCKFILE="/tmp/turing_fetch.lock"
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
# ============================================================================
# NOTIFICATION HELPER - Push alerts via ntfy.sh
# ============================================================================
# Subscribe on phone: ntfy.sh/ty-pipeline (install ntfy app from F-Droid/Play/App Store)
NTFY_TOPIC="ty-pipeline"

notify() {
    local title="$1"
    local message="$2"
    local priority="${3:-default}"  # low, default, high, urgent
    local tags="${4:-}"             # emoji tags: warning, white_check_mark, etc.
    
    curl -s \
        -H "Title: $title" \
        -H "Priority: $priority" \
        ${tags:+-H "Tags: $tags"} \
        -d "$message" \
        "https://ntfy.sh/$NTFY_TOPIC" > /dev/null 2>&1 || true
}

cleanup() {
    local EXIT_CODE=$?
    if [ "$BERUFENET_PAUSED" = "1" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ▶️  Resuming Berufenet job..."
        kill -CONT $BERUFENET_PIDS 2>/dev/null || true
    fi
    rm -f "$LOCKFILE"
    
    # Send notification on failure
    if [ $EXIT_CODE -ne 0 ]; then
        notify "Pipeline FAILED" "turing_fetch.sh crashed with exit code $EXIT_CODE at $(date '+%H:%M'). Check logs." "urgent" "rotating_light"
    fi
}
trap cleanup EXIT

# ============================================================================
# STATUS CHECK MODE - Show current state without running pipeline
# ============================================================================
if [ "$1" = "status" ] || [ "$1" = "--status" ]; then
    echo "=== TURING FETCH STATUS ==="
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
    
    cur.execute(\"\"\"SELECT COUNT(*) as cnt FROM postings WHERE job_description IS NOT NULL AND job_description != '[EXTERNAL_PARTNER]' AND LENGTH(job_description) > 100\"\"\")
    with_desc = cur.fetchone()['cnt']
    
    cur.execute(\"\"\"SELECT COUNT(*) as cnt FROM postings WHERE job_description = '[EXTERNAL_PARTNER]'\"\"\")
    external_partner = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings WHERE source = 'arbeitsagentur' AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100) AND COALESCE(invalidated, false) = false''')
    missing_desc = cur.fetchone()['cnt']
    
    cur.execute('SELECT COUNT(*) as cnt FROM postings_for_matching')
    eligible = cur.fetchone()['cnt']
    
    cur.execute('''SELECT COUNT(*) as cnt FROM postings_for_matching p WHERE NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.text = normalize_text_python(p.match_text))''')
    pending_embed = cur.fetchone()['cnt']
    
    print(f'   Total postings:       {total:,}')
    print(f'   With description:     {with_desc:,}')
    print(f'   External partner:     {external_partner:,}')
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
    echo "=== TURING FETCH DEBUG ==="
    echo ""
    
    # Find all related processes
    echo "🔍 ALL RELATED PROCESSES (full detail):"
    ps aux | head -1
    ps aux | grep -E "arbeitsagentur|deutsche_bank|job_description|embedding|extracted_summary|turing_fetch" | grep -v grep
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

FORCE_FLAG=""
if [ "$FORCE" = "force" ]; then
    FORCE_FLAG="--force"
fi

ts "Starting turing_fetch pipeline (since=$SINCE days, max_jobs=$MAX_JOBS${FORCE:+, FORCED})"

# ============================================================================
# PRE-FLIGHT SMOKE TESTS - Catch import errors before they kill a 2-hour run
# ============================================================================
ts "[0/4] Pre-flight smoke tests..."
python3 -c "
from actors.postings__arbeitsagentur_CU import main; print('  ✅ arbeitsagentur_CU')
from actors.postings__deutsche_bank_CU import main; print('  ✅ deutsche_bank_CU')
from actors.postings__berufenet_U import owl_lookup, process_batch; print('  ✅ berufenet_U (OWL-first)')
from core.turing_daemon import TuringDaemon; print('  ✅ turing_daemon')
from tools.populate_domain_gate import main; print('  ✅ populate_domain_gate')
from core.database import get_connection, get_connection_raw; print('  ✅ core.database')
print('All imports OK')
"
if [ $? -ne 0 ]; then
    ts "❌ PRE-FLIGHT FAILED - aborting pipeline"
    exit 1
fi

# ============================================================================
# STEP 1: FETCH POSTINGS (network-bound)
# ============================================================================

# 1a. Arbeitsagentur (German job board - state-by-state for reliability)
# Using --states (16 Bundesländer) instead of --nationwide for better progress tracking
# and more reliable batching (smaller queries, less likely to timeout)
# NOTE: Using --no-descriptions for speed - descriptions are backfilled in step 1c
ts "[1/4] Fetching Arbeitsagentur (16 states, metadata only)..."
python3 actors/postings__arbeitsagentur_CU.py --since $SINCE --states --max-jobs $MAX_JOBS --no-descriptions $FORCE_FLAG

# 1b. Deutsche Bank (corporate careers API - ~1 minute)
ts "[2/4] Fetching Deutsche Bank..."
python3 actors/postings__deutsche_bank_CU.py --max-jobs $MAX_JOBS

# ============================================================================
# STEP 3: BERUFENET CLASSIFICATION (OWL-first + optional embedding discovery)
# ============================================================================
# Berufenet maps job titles to German occupational classification (KldB)
# Phase 1: OWL lookup (instant, 11,746 known names in owl_names)
# Phase 2: Embedding + LLM for unknown titles (--phase2, ~14/sec, GPU-bound)
#          Confident matches auto-add as OWL synonyms (system learns!)
ts "[3/4] Running Berufenet classification (OWL-first)..."

# Phase 1: OWL lookup — instant, no GPU, handles known titles
PHASE1_BATCH=5000
while true; do
    ts "Berufenet OWL lookup batch..."
    OUTPUT=$(python3 actors/postings__berufenet_U.py --batch $PHASE1_BATCH 2>&1)
    echo "$OUTPUT" | while IFS= read -r line; do
        [[ -n "$line" ]] && ts "$line"
    done

    if echo "$OUTPUT" | grep -q "No unclassified titles remaining"; then
        ts "✅ Berufenet Phase 1 (OWL) complete"
        break
    fi
    # If no OWL hits and Phase 2 is off, all titles are NULL — stop looping
    if echo "$OUTPUT" | grep -q "NULL (Phase 2 off).*$PHASE1_BATCH"; then
        ts "⏭️  Berufenet Phase 1 done — remaining titles need Phase 2"
        break
    fi
    sleep 1
done

# Phase 2: Embedding + LLM discovery for unknown titles
# Adds new OWL synonyms automatically. Tested 2026-02-11: 927/6200 classified (78.5%).
PHASE2_BATCH=500
while true; do
    ts "Berufenet Phase 2 (embed+LLM) batch..."
    OUTPUT=$(python3 actors/postings__berufenet_U.py --batch $PHASE2_BATCH --phase2 2>&1)
    echo "$OUTPUT" | while IFS= read -r line; do
        [[ -n "$line" ]] && ts "$line"
    done
    if echo "$OUTPUT" | grep -q "No unclassified titles remaining"; then
        ts "✅ Berufenet Phase 2 complete"
        break
    fi
    sleep 1
done

# ============================================================================
# STEP 3b: DOMAIN GATE CASCADE (keyword patterns + LLM for non-KldB postings)
# ============================================================================
# KldB-based domain mapping runs in step 4 (turing_daemon), but many postings
# have no KldB code. This cascade classifies them via keyword patterns (~78%)
# and LLM fallback (~17%), achieving 95%+ domain coverage.
ts "[3b/4] Domain gate cascade (patterns + LLM)..."
python3 tools/populate_domain_gate.py --apply
ts "Domain cascade (KldB-based) complete"
python3 tools/populate_domain_gate.py --cascade --apply
ts "Domain cascade (keyword + LLM) complete"

# ============================================================================
# STEP 3c: QUALIFICATION BACKFILL (beruf → berufenet → KldB → qual level)
# ============================================================================
# Many AA postings have a 'beruf' field but no qualification_level.
# This maps beruf → berufenet (direct name or synonym) → KldB code → qual level.
ts "[3c/4] Qualification level backfill..."
python3 -c "
from core.database import get_connection
with get_connection() as conn:
    cur = conn.cursor()
    
    # Direct beruf → berufenet name match
    cur.execute('''
        UPDATE postings p
        SET qualification_level = CASE
                WHEN SUBSTRING(b.kldb_code FROM 7 FOR 1) IN ('1','2','3','4')
                THEN SUBSTRING(b.kldb_code FROM 7 FOR 1)::int
            END,
            berufenet_id = COALESCE(p.berufenet_id, b.berufenet_id),
            berufenet_name = COALESCE(p.berufenet_name, b.name),
            berufenet_kldb = COALESCE(p.berufenet_kldb, b.kldb_code)
        FROM berufenet b
        WHERE p.beruf IS NOT NULL
          AND p.qualification_level IS NULL
          AND LOWER(TRIM(p.beruf)) = LOWER(TRIM(b.name))
          AND b.kldb_code IS NOT NULL
          AND LENGTH(b.kldb_code) >= 7
    ''')
    direct = cur.rowcount
    
    # Synonym fallback
    cur.execute('''
        UPDATE postings p
        SET qualification_level = CASE
                WHEN SUBSTRING(b.kldb_code FROM 7 FOR 1) IN ('1','2','3','4')
                THEN SUBSTRING(b.kldb_code FROM 7 FOR 1)::int
            END,
            berufenet_id = COALESCE(p.berufenet_id, b.berufenet_id),
            berufenet_name = COALESCE(p.berufenet_name, b.name),
            berufenet_kldb = COALESCE(p.berufenet_kldb, b.kldb_code)
        FROM owl_names o
        JOIN berufenet b ON b.berufenet_id = o.berufenet_id
        WHERE p.beruf IS NOT NULL
          AND p.qualification_level IS NULL
          AND LOWER(TRIM(p.beruf)) = LOWER(TRIM(o.name))
          AND b.kldb_code IS NOT NULL
          AND LENGTH(b.kldb_code) >= 7
    ''')
    synonym = cur.rowcount
    
    conn.commit()
    print(f'  Qualification backfill: {direct:,} direct + {synonym:,} synonym = {direct+synonym:,} total')
"

# ============================================================================
# STEP 4: ENRICHMENT via Turing Daemon
# ============================================================================
# Turing daemon runs all enabled actors in parallel:
#   - job_description_backfill (prio 60): fetch missing descriptions (HTTP)
#   - embedding_generator      (prio 30): bge-m3 embeddings
#   - domain_gate_classifier   (prio 20): KldB → domain mapping
#   - owl_pending_auto_triage  (prio 10): LLM triage for owl_pending items
# Each actor has a work_query that self-discovers pending items.
# Tickets track completion so nothing is processed twice.
ts "[4/4] Running enrichment pipeline (turing_daemon)..."
python3 core/turing_daemon.py --limit 50000

# Summary
ts "Pipeline complete. Summary:"
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
    # Embedding actor uses: normalize_text_python() for text normalization
    cur.execute('''
        SELECT COUNT(*) as cnt FROM postings_for_matching p 
        WHERE NOT EXISTS (
            SELECT 1 FROM embeddings e 
            WHERE e.text = normalize_text_python(p.match_text)
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

# Send success notification
notify "Pipeline OK" "$(date '+%H:%M') — Pipeline complete. Check logs for stats." "low" "white_check_mark"

# Post pipeline summary to talent.yoga messages
ts "Sending pipeline health report to talent.yoga..."
python3 tools/pipeline_health.py --notify
