#!/bin/bash
# Log rotation for Turing project
# Keeps logs from getting too large
# Run daily via cron: 0 3 * * * /home/xai/Documents/ty_learn/scripts/rotate_logs.sh

set -e
cd /home/xai/Documents/ty_learn/logs

# Rotate large logs (>10MB) - keep 3 backups
rotate_if_large() {
    local file=$1
    local max_size=$((10 * 1024 * 1024))  # 10MB
    
    if [ -f "$file" ] && [ $(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null) -gt $max_size ]; then
        echo "Rotating $file"
        [ -f "${file}.2" ] && rm -f "${file}.2"
        [ -f "${file}.1" ] && mv "${file}.1" "${file}.2"
        [ -f "${file}" ] && mv "${file}" "${file}.1"
        touch "$file"
    fi
}

# Rotate main logs
rotate_if_large aa_backfill.log
rotate_if_large nightly_fetch.log
rotate_if_large reaper.log

# Delete old timestamped logs (>7 days)
find . -name "*.log" -mtime +7 -type f -delete 2>/dev/null || true

echo "[$(date)] Log rotation complete"
