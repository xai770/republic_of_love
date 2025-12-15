#!/bin/bash
# ALWAYS runs workflow scripts in background with nohup
#
# Usage: 
#   ./scripts/run_workflow.sh 3001                    # workflow ID (legacy)
#   ./scripts/run_workflow.sh run_batch_cleanup.py    # any script in scripts/
#
# This wrapper exists because agents forget to use nohup.
# It forces the correct pattern automatically.
#
# The Python scripts will REFUSE to run without the secret
# handshake that only this wrapper provides.

ARG="${1:-3001}"
cd /home/xai/Documents/ty_learn
source venv/bin/activate

# Secret handshake - Python scripts check for this
export TURING_HANDSHAKE="turing_says_use_nohup_635864"

# Determine what we're running
if [[ "$ARG" == *.py ]]; then
    # It's a script name
    SCRIPT="scripts/$ARG"
    SCRIPT_NAME="${ARG%.py}"
    LOG_FILE="logs/${SCRIPT_NAME}_$(date +%Y%m%d_%H%M%S).log"
    
    if [[ ! -f "$SCRIPT" ]]; then
        echo "❌ Script not found: $SCRIPT"
        exit 1
    fi
    
    echo "🚀 Starting $ARG in background..."
    echo "📝 Log file: $LOG_FILE"
    
    nohup python3 "$SCRIPT" "${@:2}" > "$LOG_FILE" 2>&1 &
else
    # It's a workflow ID - use unified CLI tool
    WORKFLOW_ID="$ARG"
    LOG_FILE="logs/workflow_${WORKFLOW_ID}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "🚀 Starting workflow $WORKFLOW_ID in background..."
    echo "📝 Log file: $LOG_FILE"
    
    # Use tools/run_workflow.py - the canonical workflow runner
    nohup python3 tools/run_workflow.py "$WORKFLOW_ID" "${@:2}" > "$LOG_FILE" 2>&1 &
fi

PID=$!
echo "✅ Started! PID: $PID"
echo ""
echo "Monitor with:"
echo "  tail -f $LOG_FILE"
echo "  ./scripts/status.sh"
echo ""
echo "Stop with:"
echo "  kill $PID"
