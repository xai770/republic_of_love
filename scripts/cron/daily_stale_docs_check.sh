#!/bin/bash
# Daily stale documentation check
# Add to crontab: 0 6 * * * /home/xai/Documents/ty_learn/scripts/cron/daily_stale_docs_check.sh
#
# Workspace: ty_learn is canonical. All other folders contain symlinks.

set -e

WORKSPACE="/home/xai/Documents/ty_learn"
REPORT_DIR="$WORKSPACE/docs/daily_notes"
DATE=$(date +%Y-%m-%d)
REPORT_FILE="$REPORT_DIR/stale_docs_$DATE.md"

cd "$WORKSPACE"
source venv/bin/activate

# Create report directory if needed
mkdir -p "$REPORT_DIR"

# Run check and capture output
echo "# Stale Docs Report - $DATE" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if python3 tools/check_stale_docs.py >> "$REPORT_FILE" 2>&1; then
    echo "✅ All documentation is fresh" >> "$REPORT_FILE"
else
    echo "" >> "$REPORT_FILE"
    echo "---" >> "$REPORT_FILE"
    echo "Run \`touch docs/FILE.md\` after reviewing to mark as acknowledged." >> "$REPORT_FILE"
fi

echo "Report saved to: $REPORT_FILE"
