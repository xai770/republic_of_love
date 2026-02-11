#!/bin/bash
# =============================================================================
# NIGHTLY PIPELINE - SHARED FUNCTIONS
# =============================================================================
# Source this at the start of each module:
#   source "$(dirname "$0")/common.sh"
# =============================================================================

# CRITICAL: Disable Python output buffering so logs appear in real-time
export PYTHONUNBUFFERED=1

# Navigate to project root and activate venv
cd /home/xai/Documents/ty_learn
source venv/bin/activate

# Database credentials (used by inline Python)
export DB_HOST="localhost"
export DB_NAME="turing"
export DB_USER="base_admin"
export DB_PASS="${DB_PASSWORD}"

# =============================================================================
# LOG FUNCTION - Fresh timestamp per call
# =============================================================================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# =============================================================================
# LOCK FILE MANAGEMENT
# =============================================================================
LOCKFILE="/tmp/nightly_fetch.lock"

acquire_lock() {
    if [ -f "$LOCKFILE" ]; then
        PID=$(cat "$LOCKFILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            log "⚠️  Already running (PID $PID) - exiting"
            exit 0
        else
            log "🧹 Stale lock file found, removing"
            rm -f "$LOCKFILE"
        fi
    fi
    echo $$ > "$LOCKFILE"
}

release_lock() {
    rm -f "$LOCKFILE"
}

# =============================================================================
# BERUFENET JOB PAUSE/RESUME
# =============================================================================
BERUFENET_PIDS=""
BERUFENET_PAUSED=0

pause_berufenet() {
    BERUFENET_PIDS=$(pgrep -f "postings__berufenet" 2>/dev/null || true)
    if [ -n "$BERUFENET_PIDS" ]; then
        log "⏸️  Pausing Berufenet job (PIDs: $BERUFENET_PIDS)..."
        kill -STOP $BERUFENET_PIDS 2>/dev/null || true
        BERUFENET_PAUSED=1
    fi
}

resume_berufenet() {
    if [ "$BERUFENET_PAUSED" = "1" ] && [ -n "$BERUFENET_PIDS" ]; then
        log "▶️  Resuming Berufenet job..."
        kill -CONT $BERUFENET_PIDS 2>/dev/null || true
    fi
}

# =============================================================================
# CLEANUP TRAP (call setup_cleanup in orchestrator)
# =============================================================================
cleanup() {
    resume_berufenet
    release_lock
}

setup_cleanup() {
    trap cleanup EXIT
}

# =============================================================================
# QUICK DB QUERY HELPER
# =============================================================================
db_query() {
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc "$1"
}
