#!/bin/bash
#
# Turing Database Backup Script
# Runs daily via cron at 3 AM
# Requires: /etc/sudoers.d/xai-postgres for passwordless pg_dump
#

BACKUP_DIR="/home/xai/Documents/ty_wave/backups"
TMP_DIR="/var/lib/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/home/xai/Documents/ty_wave/logs/backup_${TIMESTAMP}.log"

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $LOG_FILE)"

echo "=====================================" | tee -a "$LOG_FILE"
echo "PostgreSQL Backup Started: $TIMESTAMP" | tee -a "$LOG_FILE"
echo "=====================================" | tee -a "$LOG_FILE"

# Full backup (custom format, compressed)
echo "Creating full backup..." | tee -a "$LOG_FILE"
sudo -u postgres pg_dump -d turing -Fc -f "${TMP_DIR}/turing_full_${TIMESTAMP}.backup" 2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    cp "${TMP_DIR}/turing_full_${TIMESTAMP}.backup" "$BACKUP_DIR/"
    sudo rm -f "${TMP_DIR}/turing_full_${TIMESTAMP}.backup"
    echo "✓ Full backup complete: turing_full_${TIMESTAMP}.backup" | tee -a "$LOG_FILE"
else
    echo "✗ Full backup FAILED!" | tee -a "$LOG_FILE"
    exit 1
fi

# SQL backup (human readable)
echo "Creating SQL backup..." | tee -a "$LOG_FILE"
sudo -u postgres pg_dump -d turing -f "${TMP_DIR}/turing_sql_${TIMESTAMP}.sql" 2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    cp "${TMP_DIR}/turing_sql_${TIMESTAMP}.sql" "$BACKUP_DIR/"
    sudo rm -f "${TMP_DIR}/turing_sql_${TIMESTAMP}.sql"
    echo "✓ SQL backup complete: turing_sql_${TIMESTAMP}.sql" | tee -a "$LOG_FILE"
else
    echo "✗ SQL backup FAILED!" | tee -a "$LOG_FILE"
fi

# Cleanup old backups (keep last 7 days)
echo "Cleaning up old backups (keeping last 7 days)..." | tee -a "$LOG_FILE"
find "$BACKUP_DIR" -name "turing_*.backup" -mtime +7 -delete
find "$BACKUP_DIR" -name "turing_*.sql" -mtime +7 -delete
echo "✓ Cleanup complete" | tee -a "$LOG_FILE"

# Show backup sizes
echo "" | tee -a "$LOG_FILE"
echo "Backup directory:" | tee -a "$LOG_FILE"
ls -lh "$BACKUP_DIR"/turing_*${TIMESTAMP}* 2>/dev/null | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Total backup size:" | tee -a "$LOG_FILE"
du -sh "$BACKUP_DIR" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=====================================" | tee -a "$LOG_FILE"
echo "Backup Complete: $(date)" | tee -a "$LOG_FILE"
echo "=====================================" | tee -a "$LOG_FILE"
