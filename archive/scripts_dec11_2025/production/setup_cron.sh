#!/bin/bash
#
# Setup Daily Cron Job
# ====================
# Configures cron to run daily job processing every morning at 8:00 AM
#
# Usage: ./scripts/setup_cron.sh
#

SCRIPT_PATH="/home/xai/Documents/ty_learn/scripts/daily_job_processing.sh"
CRON_TIME="0 8 * * *"  # 8:00 AM every day
CRON_ENTRY="$CRON_TIME $SCRIPT_PATH"

echo "=================================================================="
echo "CRON SETUP: Daily Job Processing"
echo "=================================================================="
echo ""
echo "This will configure the system to run daily job processing:"
echo "  📅 Schedule: Every day at 8:00 AM"
echo "  📂 Script: $SCRIPT_PATH"
echo ""
echo "The script will:"
echo "  1. Fetch new jobs from Deutsche Bank API"
echo "  2. Extract skills from pending jobs"
echo "  3. Save skills to database"
echo ""

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current cron entries for this script:"
    crontab -l 2>/dev/null | grep "$SCRIPT_PATH"
    echo ""
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled"
        exit 0
    fi
    
    # Remove existing entry
    crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab -
    echo "🗑️  Removed existing entry"
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "📋 Current crontab:"
echo "------------------------------------------------------------------"
crontab -l | grep "$SCRIPT_PATH"
echo "------------------------------------------------------------------"
echo ""
echo "📝 To view all cron jobs:    crontab -l"
echo "📝 To edit cron jobs:        crontab -e"
echo "📝 To remove this cron job:  crontab -l | grep -v '$SCRIPT_PATH' | crontab -"
echo ""
echo "📄 Logs will be saved to: /home/xai/Documents/ty_learn/logs/"
echo ""
echo "=================================================================="
echo "✨ Setup complete! First run will be tomorrow at 8:00 AM"
echo "=================================================================="
