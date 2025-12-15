#!/bin/bash
# Stop Workflow 3001 gracefully
# Usage: ./scripts/_3001_stop.sh

cd /home/xai/Documents/ty_wave

echo "🛑 Stopping Workflow 3001..."

# Find and kill the runner process
PID=$(pgrep -f "run_workflow_3001")

if [ -z "$PID" ]; then
    echo "   No running workflow found."
else
    echo "   Found PID: $PID"
    kill $PID
    sleep 2
    
    # Check if it stopped
    if pgrep -f "run_workflow_3001" > /dev/null; then
        echo "   ⚠️  Process still running, sending SIGKILL..."
        kill -9 $PID
    else
        echo "   ✅ Process stopped gracefully."
    fi
fi

echo ""
echo "📊 Current status:"
./scripts/q.sh "SELECT status, COUNT(*) FROM interactions WHERE status IN ('running', 'pending') GROUP BY status;"
