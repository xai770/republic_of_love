#!/bin/bash
# Generic Workflow Restart Script
# Usage: ./scripts/restart_workflow.sh <workflow_id>
# Example: ./scripts/restart_workflow.sh 3001

WORKFLOW_ID=${1:-3001}

echo "🔄 Restarting Workflow $WORKFLOW_ID"
echo "=================================="

# Change to project directory
cd /home/xai/Documents/ty_wave || exit 1

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Kill existing workflow process (if any)
echo "🛑 Stopping existing workflow processes..."
pkill -f "workflow_executor.*${WORKFLOW_ID}"
sleep 2

# Start workflow in background
LOG_FILE="/tmp/workflow_${WORKFLOW_ID}.log"
echo "🚀 Starting workflow $WORKFLOW_ID..."
echo "📝 Logging to: $LOG_FILE"

# Ensure we're in the correct directory and use nohup properly
cd /home/xai/Documents/ty_wave || exit 1
nohup bash -c "source venv/bin/activate && python3 -m core.workflow_executor --workflow $WORKFLOW_ID" > "$LOG_FILE" 2>&1 &

WORKFLOW_PID=$!

# Wait a moment and check if process is running
sleep 1
if ps -p $WORKFLOW_PID > /dev/null; then
    echo "✅ Workflow $WORKFLOW_ID started successfully!"
    echo "   PID: $WORKFLOW_PID"
    echo "   Log: $LOG_FILE"
    echo ""
    echo "📊 Monitor with:"
    echo "   python3 tools/monitor_workflow.py --workflow $WORKFLOW_ID"
    echo ""
    echo "📋 View logs:"
    echo "   tail -f $LOG_FILE"
else
    echo "❌ Failed to start workflow $WORKFLOW_ID"
    echo "   Check log: $LOG_FILE"
    exit 1
fi
