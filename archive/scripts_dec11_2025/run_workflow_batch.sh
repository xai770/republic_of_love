#!/usr/bin/env bash
# Usage: ./scripts/run_workflow_batch.sh [workflow_id]
# Runs workflow in global batch mode with no iteration limit
# Logs to logs/wave_runner_YYYYMMDD_HHMMSS.log

WORKFLOW_ID=${1:-3001}
LOG_FILE="logs/wave_runner_$(date +%Y%m%d_%H%M%S).log"

echo "Running workflow ${WORKFLOW_ID} in global batch mode..."
echo "Log file: ${LOG_FILE}"
echo

python3 -c "
from core.database import get_connection
from core.wave_runner.runner import WaveRunner

conn = get_connection()
runner = WaveRunner(db_conn=conn, global_batch=True)

print(f'Running workflow ${WORKFLOW_ID} in global batch mode...')
print('No iteration limit - will run until complete.')
print()

result = runner.run()

print()
print('='*60)
print(f\"Status: {result.get('status')}\")
print(f\"Completed: {result.get('interactions_completed', 0)}\")
print(f\"Failed: {result.get('interactions_failed', 0)}\")
print(f\"Duration: {result.get('duration_ms', 0)/1000:.1f}s\")
print('='*60)
" 2>&1 | tee "$LOG_FILE"

echo
echo "Log saved to: $LOG_FILE"
