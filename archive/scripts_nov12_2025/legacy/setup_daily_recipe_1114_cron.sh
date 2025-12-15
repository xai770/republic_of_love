#!/bin/bash
# Setup cron job for daily Recipe 1114 processing
# Run this once to configure automated daily runs

SCRIPT_DIR="/home/xai/Documents/ty_learn"
LOG_DIR="$SCRIPT_DIR/logs"
CRON_TIME="0 2 * * *"  # 2 AM daily

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "🔧 Recipe 1114 Daily Cron Setup"
echo "================================"
echo ""
echo "This will configure Recipe 1114 to run automatically every day at 2 AM."
echo "The script will:"
echo "  - Process all job postings with NULL extracted_summary"
echo "  - Log output to logs/recipe_1114_daily.log"
echo "  - Rotate logs to prevent disk space issues"
echo ""

# Check if cron job already exists
existing_cron=$(crontab -l 2>/dev/null | grep "daily_recipe_1114.py")

if [ ! -z "$existing_cron" ]; then
    echo "⚠️  Cron job already exists:"
    echo "   $existing_cron"
    echo ""
    read -p "Remove existing and reinstall? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 1
    fi
    
    # Remove existing cron job
    crontab -l 2>/dev/null | grep -v "daily_recipe_1114.py" | crontab -
    echo "✅ Removed existing cron job"
fi

# Create the cron job
(crontab -l 2>/dev/null; echo "$CRON_TIME cd $SCRIPT_DIR && python3 scripts/daily_recipe_1114.py >> $LOG_DIR/recipe_1114_daily.log 2>&1") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "📋 Configuration:"
echo "   Schedule: Daily at 2:00 AM"
echo "   Script: $SCRIPT_DIR/scripts/daily_recipe_1114.py"
echo "   Log: $LOG_DIR/recipe_1114_daily.log"
echo ""
echo "📊 To check cron jobs:"
echo "   crontab -l"
echo ""
echo "📝 To view logs:"
echo "   tail -f $LOG_DIR/recipe_1114_daily.log"
echo ""
echo "🧪 To test manually (dry run):"
echo "   cd $SCRIPT_DIR"
echo "   python3 scripts/daily_recipe_1114.py --dry-run"
echo ""
echo "🚀 To run manually now:"
echo "   cd $SCRIPT_DIR"
echo "   python3 scripts/daily_recipe_1114.py"
echo ""
echo "⚙️  To change schedule, edit with: crontab -e"
echo "   Current: $CRON_TIME (2 AM daily)"
echo "   Hourly: 0 * * * *"
echo "   Every 6 hours: 0 */6 * * *"
echo "   Weekly (Sunday 2 AM): 0 2 * * 0"
echo ""
