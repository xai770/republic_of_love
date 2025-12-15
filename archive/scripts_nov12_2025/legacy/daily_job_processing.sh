#!/bin/bash
#
# Daily Job Processing Script
# ===========================
# Runs every morning to:
# 1. Fetch new jobs from Deutsche Bank API
# 2. Extract skills from all pending jobs
# 3. Save skills to database
#
# Author: Arden & xai
# Date: 2025-11-06

set -e  # Exit on error

# Configuration
PROJECT_DIR="/home/xai/Documents/ty_learn"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_job_processing_$(date +%Y%m%d_%H%M%S).log"
PYTHON="/usr/bin/python3"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "=================================================================="
echo "DAILY JOB PROCESSING - $(date)"
echo "=================================================================="
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Step 1: Fetch new jobs from API
echo "📥 Step 1: Fetching new jobs from Deutsche Bank API..."
echo "------------------------------------------------------------------"
$PYTHON core/turing_job_fetcher.py
if [ $? -eq 0 ]; then
    echo "✅ Job fetch completed successfully"
else
    echo "❌ Job fetch failed"
    exit 1
fi
echo ""

# Step 2: Process all pending jobs with TuringOrchestrator
echo "🎼 Step 2: Processing pending jobs with TuringOrchestrator..."
echo "------------------------------------------------------------------"
$PYTHON << 'PYEOF'
from core.turing_orchestrator import TuringOrchestrator
import time

start_time = time.time()
orchestrator = TuringOrchestrator(verbose=True)
results = orchestrator.process_pending_tasks(max_tasks=None, dry_run=False)
elapsed = time.time() - start_time

print()
print('=' * 70)
print('📊 ORCHESTRATOR RESULTS')
print('=' * 70)
print(f'⏱️  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)')
print(f'📋 Tasks found: {results["tasks_found"]}')
print(f'📊 Tasks processed: {results["tasks_processed"]}')
print(f'✅ Successful: {results["success_count"]}')
print(f'❌ Failed: {results["tasks_processed"] - results["success_count"]}')
if results["tasks_processed"] > 0:
    print(f'📈 Success rate: {100*results["success_count"]/results["tasks_processed"]:.1f}%')
print('=' * 70)
PYEOF

if [ $? -eq 0 ]; then
    echo "✅ Job processing completed successfully"
else
    echo "❌ Job processing failed"
    exit 1
fi
echo ""

# Step 3: Save extracted skills to database
echo "💾 Step 3: Saving extracted skills to database..."
echo "------------------------------------------------------------------"
$PYTHON tools/save_extracted_skills.py
if [ $? -eq 0 ]; then
    echo "✅ Skills saved successfully"
else
    echo "❌ Skills saving failed"
    exit 1
fi
echo ""

# Summary
echo "=================================================================="
echo "✨ DAILY JOB PROCESSING COMPLETE - $(date)"
echo "=================================================================="
echo ""
echo "📊 Final Status:"
$PYTHON << 'PYEOF'
from core.database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM postings WHERE posting_status = 'active'")
total_active = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM posting_processing_status WHERE skills_extracted = TRUE")
processed = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM job_skills")
total_skills = cursor.fetchone()[0]

conn.close()

print(f"   Active jobs: {total_active}")
print(f"   Jobs with skills: {processed}")
print(f"   Total skills: {total_skills}")
PYEOF

echo ""
echo "📄 Log saved to: $LOG_FILE"
echo "=================================================================="
