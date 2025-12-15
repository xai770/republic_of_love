#!/bin/bash
# Restart Workflow 3001 after system reboot or interruption
# Usage: ./scripts/_3001_restart.sh [--fetch] [--max-jobs N]
#
# Examples:
#   ./scripts/_3001_restart.sh                    # Just process pending work
#   ./scripts/_3001_restart.sh --fetch            # Fetch 50 new jobs + process
#   ./scripts/_3001_restart.sh --fetch --max-jobs 200   # Fetch 200 new jobs

cd /home/xai/Documents/ty_wave

echo "🔄 Restarting Workflow 3001..."
echo ""

# Step 1: Check if already running
if pgrep -f "run_workflow_3001" > /dev/null; then
    echo "⚠️  Workflow already running! Use _3001_stop.sh first."
    exit 1
fi

# Step 2: Reset stuck 'running' interactions
echo "📋 Cleaning up stale states..."

RUNNING_COUNT=$(sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM interactions WHERE status = 'running';" | tr -d ' ')

if [ "$RUNNING_COUNT" -gt 0 ]; then
    echo "   Resetting $RUNNING_COUNT stuck 'running' interactions to 'pending'..."
    sudo -u postgres psql -d turing -c "UPDATE interactions SET status = 'pending', updated_at = NOW() WHERE status = 'running';"
else
    echo "   No stuck interactions found. ✓"
fi

# Step 3: Reset interrupted workflow_runs
INTERRUPTED_COUNT=$(sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM workflow_runs WHERE status = 'interrupted' AND workflow_id = 3001;" | tr -d ' ')

if [ "$INTERRUPTED_COUNT" -gt 0 ]; then
    echo "   Resetting $INTERRUPTED_COUNT interrupted workflow_runs..."
    sudo -u postgres psql -d turing -c "UPDATE workflow_runs SET status = 'completed', updated_at = NOW() WHERE status = 'interrupted' AND workflow_id = 3001;"
else
    echo "   No interrupted workflow_runs. ✓"
fi

echo ""

# Step 4: Show current pending work
echo "📊 Pending work:"
./scripts/q.sh "SELECT COUNT(*) as pending_interactions FROM interactions WHERE status = 'pending';"

echo ""

# Step 5: Start the workflow
LOGFILE="logs/run_$(date +%Y%m%d_%H%M%S).log"
echo "🚀 Starting workflow..."
echo "   Log file: $LOGFILE"
echo "   Args: $@"
echo ""

nohup python3 scripts/prod/run_workflow_3001.py "$@" > "$LOGFILE" 2>&1 &
PID=$!

echo "   Started with PID: $PID"
echo ""

# Step 6: Wait a moment and verify it's running
sleep 3

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Workflow is running!"
    echo ""
    echo "Monitor with:"
    echo "   python3 tools/_workflow_flowchart.py"
    echo ""
    echo "Or check log:"
    echo "   tail -f $LOGFILE"
else
    echo "❌ Workflow failed to start! Check log:"
    echo "   cat $LOGFILE"
fi
