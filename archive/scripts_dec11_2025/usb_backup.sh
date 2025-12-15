#!/bin/bash
# USB Backup Script - Incremental with auto-detection
# Looks for either BACKUP or BACKUP2 USB drives
# Run manually or via cron: 0 2 * * * /home/xai/Documents/ty_learn/scripts/usb_backup.sh
#
# Backup Strategy:
#   - Documents: incremental rsync (only changed files)
#   - PostgreSQL: daily full dump (small, ~20MB)
#   - Weekly: full verification sync
#
# Usage:
#   ./usb_backup.sh              # Normal incremental backup
#   ./usb_backup.sh --full       # Force full sync (weekly verification)
#   ./usb_backup.sh --check      # Just check if USB is available

set -euo pipefail

# Configuration
BACKUP_LABELS=("BACKUP" "BACKUP2")
SOURCE_DIR="/home/xai/Documents"
DB_NAME="turing"
LOG_FILE="/home/xai/Documents/ty_learn/logs/usb_backup.log"
LOCK_FILE="/tmp/usb_backup.lock"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "$timestamp - $1" | tee -a "$LOG_FILE"
}

error() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

success() {
    log "${GREEN}$1${NC}"
}

warn() {
    log "${YELLOW}WARNING: $1${NC}"
}

# Find mounted USB with one of our labels
find_backup_usb() {
    for label in "${BACKUP_LABELS[@]}"; do
        local mount_point="/media/xai/$label"
        if mountpoint -q "$mount_point" 2>/dev/null; then
            echo "$mount_point"
            return 0
        fi
        # Try to mount if device exists but not mounted
        local device=$(blkid -L "$label" 2>/dev/null || true)
        if [[ -n "$device" ]]; then
            log "Found unmounted device $device with label $label, attempting mount..."
            sudo mkdir -p "$mount_point"
            if sudo mount "$device" "$mount_point" 2>/dev/null; then
                sudo chown xai:xai "$mount_point"
                echo "$mount_point"
                return 0
            fi
        fi
    done
    return 1
}

# Check for existing backup process
check_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error "Another backup is running (PID $pid)"
        else
            warn "Stale lock file found, removing..."
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
    trap "rm -f $LOCK_FILE" EXIT
}

# Incremental rsync backup
backup_documents() {
    local dest="$1"
    local mode="$2"
    
    local rsync_opts="-avh --delete --stats"
    
    if [[ "$mode" == "full" ]]; then
        log "Running FULL sync (verification mode)..."
        rsync_opts="$rsync_opts --checksum"
    else
        log "Running incremental sync..."
    fi
    
    # Exclude patterns for cleaner backup
    local excludes=(
        "--exclude=__pycache__"
        "--exclude=*.pyc"
        "--exclude=.pytest_cache"
        "--exclude=*.log"
        "--exclude=node_modules"
        "--exclude=.git/objects/pack/*.pack"  # Large git packs (we keep refs)
    )
    
    rsync $rsync_opts "${excludes[@]}" "$SOURCE_DIR/" "$dest/Documents/" 2>&1 | tee -a "$LOG_FILE"
}

# PostgreSQL backup
backup_database() {
    local dest="$1"
    local backup_file="$dest/turing_$(date +%Y%m%d_%H%M%S).backup"
    local temp_file="/tmp/turing_backup_$$.backup"
    
    log "Backing up PostgreSQL database '$DB_NAME'..."
    
    # Dump to temp first (postgres user can't write to USB directly)
    cd /tmp
    if sudo -u postgres pg_dump "$DB_NAME" -F c > "$temp_file" 2>&1; then
        cp "$temp_file" "$backup_file"
        rm -f "$temp_file"
        
        local size=$(du -h "$backup_file" | cut -f1)
        success "Database backup complete: $backup_file ($size)"
        
        # Keep only last 7 database backups
        log "Cleaning old database backups (keeping last 7)..."
        ls -t "$dest"/turing_*.backup 2>/dev/null | tail -n +8 | xargs -r rm -f
    else
        rm -f "$temp_file"
        warn "Database backup failed - continuing with Documents backup"
    fi
}

# Main backup routine
do_backup() {
    local mode="${1:-incremental}"
    
    log "=========================================="
    log "USB Backup Started (mode: $mode)"
    log "=========================================="
    
    # Find USB
    local usb_mount
    if ! usb_mount=$(find_backup_usb); then
        error "No backup USB found! Insert BACKUP or BACKUP2 drive."
    fi
    
    success "Found backup USB at: $usb_mount"
    
    # Check available space
    local avail=$(df -BG "$usb_mount" | tail -1 | awk '{print $4}' | tr -d 'G')
    log "Available space: ${avail}GB"
    
    if [[ "$avail" -lt 2 ]]; then
        error "Insufficient space on USB (need at least 2GB free)"
    fi
    
    # Run backups
    backup_documents "$usb_mount" "$mode"
    backup_database "$usb_mount"
    
    # Write backup metadata
    cat > "$usb_mount/BACKUP_INFO.txt" << EOF
Last Backup: $(date '+%Y-%m-%d %H:%M:%S')
Hostname: $(hostname)
Mode: $mode
Source: $SOURCE_DIR
Documents Size: $(du -sh "$usb_mount/Documents" 2>/dev/null | cut -f1)
Database Backups: $(ls "$usb_mount"/turing_*.backup 2>/dev/null | wc -l)
EOF
    
    success "=========================================="
    success "Backup completed successfully!"
    success "=========================================="
    
    # Sync to ensure writes are flushed
    sync
}

# Entry point
main() {
    check_lock
    
    case "${1:-}" in
        --check)
            if usb_mount=$(find_backup_usb); then
                echo "Backup USB available at: $usb_mount"
                cat "$usb_mount/BACKUP_INFO.txt" 2>/dev/null || echo "No previous backup info found"
                exit 0
            else
                echo "No backup USB found"
                exit 1
            fi
            ;;
        --full)
            do_backup "full"
            ;;
        *)
            do_backup "incremental"
            ;;
    esac
}

main "$@"
