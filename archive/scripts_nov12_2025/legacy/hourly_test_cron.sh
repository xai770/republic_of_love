#!/bin/bash
# =============================================================================
# Hourly AI Model Testing - Production Cron Script
# =============================================================================
# Add this to your crontab for hourly automated testing:
# 0 * * * * /path/to/ty_learn/scripts/hourly_test_cron.sh >> /var/log/ai_testing.log 2>&1
#
# This will run every hour and test all your models automatically.
# Perfect for your AI workstation under your desk! 🖥️

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/hourly_test_$(date +%Y%m%d).log"
RESULTS_DIR="$PROJECT_DIR/hourly_results"

# Ensure directories exist
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$RESULTS_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to send notification (customize for your system)
notify() {
    local message="$1"
    local status="$2"
    
    # Log the notification
    log "$status: $message"
    
    # Uncomment and customize these for your notification system:
    # echo "$message" | mail -s "AI Test $status" your-email@domain.com
    # curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"$message\"}" YOUR_SLACK_WEBHOOK
    # notify-send "AI Testing" "$message"
}

# Main execution
main() {
    log "🚀 Starting hourly AI model testing suite"
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Run the unified test suite
    if python3 scripts/unified_test_runner.py; then
        
        # Get the latest session results
        SESSION_ID=$(python3 -c "
import sqlite3
conn = sqlite3.connect('data/llmcore.db')
cursor = conn.cursor()
cursor.execute('SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1')
result = cursor.fetchone()
print(result[0] if result else 'NONE')
conn.close()
")
        
        if [ "$SESSION_ID" != "NONE" ]; then
            # Run monitoring query and capture results
            MONITORING_RESULT=$(sqlite3 data/llmcore.db -header -column "
                WITH latest_session AS (
                    SELECT session_id FROM unified_test_results ORDER BY created_at DESC LIMIT 1
                ),
                session_stats AS (
                    SELECT 
                        COUNT(*) as total_tests,
                        ROUND(AVG(is_correct) * 100, 1) as accuracy,
                        COUNT(DISTINCT model_name) as models,
                        SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as errors
                    FROM unified_test_results r
                    JOIN latest_session l ON r.session_id = l.session_id
                )
                SELECT 
                    total_tests || ' tests completed' as summary,
                    accuracy || '% overall accuracy' as performance,
                    models || ' models tested' as coverage,
                    errors || ' errors encountered' as health,
                    CASE 
                        WHEN accuracy >= 40 AND errors = 0 THEN 'HEALTHY ✅'
                        WHEN accuracy >= 30 AND errors <= 5 THEN 'WARNING ⚠️' 
                        ELSE 'ALERT 🚨'
                    END as status
                FROM session_stats;
            ")
            
            # Extract status for conditional logic
            STATUS=$(echo "$MONITORING_RESULT" | tail -n 1 | awk '{print $1}')
            
            log "📊 Test Results:"
            log "$MONITORING_RESULT"
            
            # Move results to archive
            if [ -f "hourly_test_summary_${SESSION_ID}.json" ]; then
                mv "hourly_test_summary_${SESSION_ID}.json" "$RESULTS_DIR/"
                log "📁 Results archived to $RESULTS_DIR/hourly_test_summary_${SESSION_ID}.json"
            fi
            
            # Send appropriate notification based on status
            case "$STATUS" in
                "HEALTHY")
                    notify "Hourly AI testing completed successfully. $MONITORING_RESULT" "SUCCESS"
                    ;;
                "WARNING")
                    notify "Hourly AI testing completed with warnings. $MONITORING_RESULT" "WARNING"
                    ;;
                *)
                    notify "Hourly AI testing requires attention. $MONITORING_RESULT" "ALERT"
                    ;;
            esac
            
        else
            notify "Hourly AI testing completed but no results found in database" "ERROR"
        fi
        
    else
        notify "Hourly AI testing failed to execute properly" "ERROR"
        exit 1
    fi
    
    log "✅ Hourly testing cycle completed"
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up old logs (keeping last 7 days)"
    find "$PROJECT_DIR/logs" -name "hourly_test_*.log" -mtime +7 -delete 2>/dev/null || true
    find "$RESULTS_DIR" -name "hourly_test_summary_*.json" -mtime +30 -delete 2>/dev/null || true
}

# Error handling
trap 'log "❌ Error occurred in hourly testing script"; notify "Hourly AI testing script encountered an error" "ERROR"; exit 1' ERR

# Execute main function
main "$@"

# Cleanup old files
cleanup

log "🎉 Hourly testing cycle complete - see you next hour!"

# Exit successfully
exit 0