#!/bin/bash
# Rollback to legacy executor if refactored version has issues
# Created: November 19, 2025
# Usage: ./scripts/rollback_to_legacy.sh

set -e  # Exit on error

echo "⚠️  ROLLBACK: Switching to legacy workflow executor"

# Step 1: Stop current workflow
echo "Stopping current workflow..."
pkill -f "workflow_executor.*3001" || true
sleep 2

# Step 2: Backup current refactored version
cd /home/xai/Documents/ty_wave/core
BACKUP_DIR="../core_backup_rollback_$(date +%Y%m%d_%H%M%S)"

echo "Backing up refactored version to $BACKUP_DIR..."
mkdir -p "$BACKUP_DIR"
cp workflow_executor.py "$BACKUP_DIR/"
cp wave_executor.py "$BACKUP_DIR/" 2>/dev/null || true
cp posting_state.py "$BACKUP_DIR/" 2>/dev/null || true

# Step 3: Check if legacy executor exists
if [ ! -f workflow_executor_legacy.py ]; then
    echo "❌ ERROR: Legacy executor not found at core/workflow_executor_legacy.py"
    echo "   Create it first by copying the pre-refactor version"
    exit 1
fi

# Step 4: Swap executors
echo "Switching to legacy executor..."
mv workflow_executor.py workflow_executor_refactored.py
cp workflow_executor_legacy.py workflow_executor.py

# Step 5: Restart workflow
echo "Restarting workflow with legacy executor..."
cd /home/xai/Documents/ty_wave
LOG_FILE="logs/workflow_3001_rollback_$(date +%Y%m%d_%H%M%S).log"

nohup python3 -m core.workflow_executor --workflow 3001 \
  > "$LOG_FILE" 2>&1 &

WORKFLOW_PID=$!

echo ""
echo "✅ Rollback complete!"
echo "   - Refactored version backed up to: $BACKUP_DIR"
echo "   - Legacy executor now active"
echo "   - Workflow restarted as PID: $WORKFLOW_PID"
echo "   - Log file: $LOG_FILE"
echo ""
echo "To monitor: tail -f $LOG_FILE"
echo "To restore refactored version: ./scripts/restore_refactored.sh"
