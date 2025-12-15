#!/bin/bash
# Setup automatic daily backups for base.yoga (BY)

SCRIPT_DIR="/home/xai/Documents/ty_learn/scripts"
CRON_JOB="0 2 * * * $SCRIPT_DIR/backup_by.sh >> /home/xai/Documents/ty_learn/logs/backup_by.log 2>&1"

echo "🕐 Setting up automatic daily backups for BY..."
echo ""
echo "Schedule: Every day at 2:00 AM"
echo "Log: /home/xai/Documents/ty_learn/logs/backup_by.log"
echo ""

# Create logs directory
mkdir -p /home/xai/Documents/ty_learn/logs

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_by.sh"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep backup_by
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added!"
    echo ""
    echo "Installed job:"
    echo "$CRON_JOB"
fi

echo ""
echo "💡 To view all cron jobs:"
echo "   crontab -l"
echo ""
echo "💡 To remove automatic backups:"
echo "   crontab -e  # then delete the line with backup_by.sh"
echo ""
echo "💡 Manual backup anytime:"
echo "   ./scripts/backup_by.sh"
