#!/bin/bash

# =============================================================================
# Workflow 3001: Complete Job Processing Pipeline
# =============================================================================
# Runs the compiled version of workflow 3001 for daily job processing
#
# Pipeline:
# 1. Fetch Jobs from Deutsche Bank API
# 2-8. Self-healing Summary Extraction (workflow 1114)
# 9-10. Skills Extraction & Taxonomy Mapping
# 11-12. Hybrid Skills Extraction & Save
# 13-15. Fake Job Detection (workflow 1124)
# =============================================================================

LOG_DIR="/home/xai/Documents/ty_wave/logs"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/workflow_3001_${DATE_STAMP}.log"

mkdir -p "$LOG_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo "Workflow 3001: Complete Job Processing" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd /home/xai/Documents/ty_wave

# Run the workflow (processes all pending postings)
python3 scripts/prod/run_workflow_3001.py --resume 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "========================================" | tee -a "$LOG_FILE"
echo "Completed: $(date)" | tee -a "$LOG_FILE"
echo "Exit Code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
