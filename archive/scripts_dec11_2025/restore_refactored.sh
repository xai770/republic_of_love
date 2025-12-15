#!/bin/bash
# Restore refactored executor after rollback
# Created: November 19, 2025
# Usage: ./scripts/restore_refactored.sh

set -e  # Exit on error

echo "🔄 RESTORE: Switching back to refactored workflow executor"

# Step 1: Stop current workflow
echo "Stopping current workflow..."
pkill -f "workflow_executor.*3001" || true
sleep 2

# Step 2: Check if refactored version exists
cd /home/xai/Documents/ty_wave/core
if [ ! -f workflow_executor_refactored.py ]; then
    echo "❌ ERROR: Refactored executor not found at core/workflow_executor_refactored.py"
    echo "   Has it been deleted or renamed?"
    exit 1
fi

# Step 3: Swap back to refactored version
echo "Switching to refactored executor..."
mv workflow_executor.py workflow_executor_legacy.py
mv workflow_executor_refactored.py workflow_executor.py

# Step 4: Restart workflow
echo "Restarting workflow with refactored executor..."
cd /home/xai/Documents/ty_wave
LOG_FILE="logs/workflow_3001_restored_$(date +%Y%m%d_%H%M%S).log"

nohup python3 -m core.workflow_executor --workflow 3001 \
  > "$LOG_FILE" 2>&1 &

WORKFLOW_PID=$!

echo ""
echo "✅ Restore complete!"
echo "   - Refactored executor now active"
echo "   - Legacy executor saved as workflow_executor_legacy.py"
echo "   - Workflow restarted as PID: $WORKFLOW_PID"
echo "   - Log file: $LOG_FILE"
echo ""
echo "To monitor: tail -f $LOG_FILE"
