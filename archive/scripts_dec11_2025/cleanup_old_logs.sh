#!/bin/bash
# Cleanup old log files - events in Turing are the source of truth
# Run daily via cron: 0 2 * * * /home/xai/Documents/ty_wave/scripts/cleanup_old_logs.sh

# Follow symlink to actual log directory
LOG_DIR="$(readlink -f /home/xai/Documents/ty_wave/logs)"
RETENTION_DAYS=7  # Keep last week for debugging

echo "$(date): Starting log cleanup (retention: ${RETENTION_DAYS} days)"

# Count files before
BEFORE=$(find "$LOG_DIR" -type f -name "*.log" 2>/dev/null | wc -l)
SIZE_BEFORE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

# Delete logs older than retention period
DELETED=$(find "$LOG_DIR" -type f -name "*.log" -mtime +${RETENTION_DAYS} -delete -print 2>/dev/null | wc -l)

# Count files after
AFTER=$(find "$LOG_DIR" -type f -name "*.log" 2>/dev/null | wc -l)
SIZE_AFTER=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)

echo "$(date): Cleanup complete"
echo "  Deleted: $DELETED files"
echo "  Files: $BEFORE -> $AFTER"
echo "  Size: $SIZE_BEFORE -> $SIZE_AFTER"
echo ""
