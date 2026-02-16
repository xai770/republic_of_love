#!/usr/bin/env bash
# backup_all.sh — Unified backup script for talent.yoga
#
# Consolidates all backup/maintenance tasks that were scattered across cron:
#   1. PostgreSQL dump (pg_dump → backups/turing_YYYYMMDD.sql.gz)
#   2. Schema export (pg_dump --schema-only → sql/schema.sql)
#   3. USB rsync (incremental daily, full on Sundays)
#   4. Stale posting invalidation (postings not seen in 14 days)
#   5. Log rotation
#   6. Signal notification on failure
#
# Usage:
#   bash scripts/backup_all.sh           # daily (incremental)
#   bash scripts/backup_all.sh --full    # weekly full (verify checksums)
#
# Designed to be called by:
#   - systemd timer (config/systemd/talent-yoga-backup.timer, 02:00 daily)
#   - OR cron (0 2 * * * /home/xai/Documents/ty_learn/scripts/backup_all.sh)

set -euo pipefail
cd "$(dirname "$0")/.."

FULL_MODE=false
if [[ "${1:-}" == "--full" ]]; then
    FULL_MODE=true
fi

# Timestamp helper
ts() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

BACKUP_DIR="backups"
USB_MOUNT="/media/xai/BACKUP1"
USB_BACKUP_DIR="$USB_MOUNT/ty_archive/ty_learn"
PG_USER="base_admin"
PG_DB="turing"
DATE=$(date '+%Y%m%d')
ERRORS=0

mkdir -p "$BACKUP_DIR" logs

# ============================================================================
# 1. PostgreSQL dump
# ============================================================================
ts "Step 1: PostgreSQL dump..."
PG_DUMP_FILE="$BACKUP_DIR/turing_${DATE}.sql.gz"
if [[ -f "$PG_DUMP_FILE" ]]; then
    ts "  Already exists: $PG_DUMP_FILE — skipping"
else
    if PGPASSWORD="${DB_PASSWORD:-$(grep DB_PASSWORD .env 2>/dev/null | cut -d= -f2)}" \
       pg_dump -h localhost -U "$PG_USER" "$PG_DB" | gzip > "$PG_DUMP_FILE"; then
        SIZE=$(du -h "$PG_DUMP_FILE" | cut -f1)
        ts "  ✅ PG dump: $PG_DUMP_FILE ($SIZE)"
    else
        ts "  ❌ PG dump FAILED"
        ((ERRORS++)) || true
    fi
fi

# Prune old dumps (keep last 7 days)
find "$BACKUP_DIR" -name "turing_*.sql.gz" -mtime +7 -delete 2>/dev/null || true

# ============================================================================
# 2. Schema export
# ============================================================================
ts "Step 2: Schema export..."
SCHEMA_FILE="sql/schema.sql"
mkdir -p sql
if PGPASSWORD="${DB_PASSWORD:-$(grep DB_PASSWORD .env 2>/dev/null | cut -d= -f2)}" \
   pg_dump -h localhost -U "$PG_USER" "$PG_DB" --schema-only > "$SCHEMA_FILE"; then
    LINES=$(wc -l < "$SCHEMA_FILE")
    ts "  ✅ Schema export: $SCHEMA_FILE ($LINES lines)"
else
    ts "  ❌ Schema export FAILED"
    ((ERRORS++)) || true
fi

# ============================================================================
# 3. USB rsync (if drive is mounted)
# ============================================================================
if mountpoint -q "$USB_MOUNT" 2>/dev/null; then
    ts "Step 3: USB rsync → $USB_BACKUP_DIR..."
    mkdir -p "$USB_BACKUP_DIR"

    RSYNC_OPTS="-a --delete --exclude=venv --exclude=.git --exclude=node_modules --exclude='*.pyc' --exclude=__pycache__"

    if $FULL_MODE; then
        ts "  Full backup (with checksums)..."
        RSYNC_OPTS="$RSYNC_OPTS --checksum"
    fi

    if rsync $RSYNC_OPTS ./ "$USB_BACKUP_DIR/"; then
        SIZE=$(du -sh "$USB_BACKUP_DIR" | cut -f1)
        ts "  ✅ USB rsync complete ($SIZE)"
    else
        ts "  ❌ USB rsync FAILED"
        ((ERRORS++)) || true
    fi

    # Also copy today's PG dump
    if [[ -f "$PG_DUMP_FILE" ]]; then
        cp "$PG_DUMP_FILE" "$USB_BACKUP_DIR/../" 2>/dev/null || true
    fi
else
    ts "Step 3: USB drive not mounted at $USB_MOUNT — skipping rsync"
fi

# ============================================================================
# 4. Stale posting invalidation (postings not seen in 14 days)
# ============================================================================
ts "Step 4: Stale posting invalidation..."
INVALIDATED=$(PGPASSWORD="${DB_PASSWORD:-$(grep DB_PASSWORD .env 2>/dev/null | cut -d= -f2)}" \
    psql -h localhost -U "$PG_USER" "$PG_DB" -t -A -c "
    UPDATE postings
    SET invalidated = true,
        invalidated_reason = 'stale_14d',
        invalidated_at = NOW()
    WHERE NOT invalidated
      AND last_seen_at < NOW() - INTERVAL '14 days'
      AND last_seen_at IS NOT NULL
    RETURNING posting_id
" 2>/dev/null | wc -l || echo "0")
ts "  Invalidated $INVALIDATED stale postings"

# ============================================================================
# 5. Log rotation
# ============================================================================
ts "Step 5: Log rotation..."
if [[ -x scripts/rotate_logs.sh ]]; then
    bash scripts/rotate_logs.sh 2>/dev/null || true
    ts "  ✅ Log rotation complete"
else
    ts "  ⚠️  rotate_logs.sh not found — skipping"
fi

# Also run logrotate if config exists
if [[ -f config/logrotate.conf ]]; then
    /usr/sbin/logrotate --state logs/.logrotate.state config/logrotate.conf 2>/dev/null || true
fi

# ============================================================================
# 6. Summary + notification
# ============================================================================
ts "Backup complete. Errors: $ERRORS"

if [[ $ERRORS -gt 0 ]]; then
    # Send Signal alert on failure
    python3 -c "
from lib.signal_notify import send_alert
send_alert('Backup completed with $ERRORS errors. Check logs/backup_all.log')
" 2>/dev/null || true
    exit 1
fi
