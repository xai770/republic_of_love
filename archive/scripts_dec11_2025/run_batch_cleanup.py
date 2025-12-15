#!/usr/bin/env python3
"""
Batch cleanup runner - processes pending interactions.

Usage: ./scripts/run_workflow.sh run_batch_cleanup.py

DO NOT run directly - use the wrapper!
"""

import sys
import os

# Unbuffered output for nohup
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Add project root to path
sys.path.insert(0, '/home/xai/Documents/ty_wave')

# ═══════════════════════════════════════════════════════════════
# WORKFLOW GUARD - Must be first!
# ═══════════════════════════════════════════════════════════════
from core.workflow_guard import require_wrapper, complete_workflow_interaction

interaction_id = require_wrapper(
    script_name="run_batch_cleanup.py",
    description="Batch cleanup - processes ALL pending interactions in global batch mode"
)

from dotenv import load_dotenv
import psycopg2

load_dotenv()

print(f"🚀 Starting WaveRunner batch cleanup")
print(f"PID: {os.getpid()}")
print(f"Workflow Interaction: {interaction_id}")
print(f"=" * 50)

# Connect to database
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST')
)

from core.wave_runner.runner import WaveRunner

runner = WaveRunner(
    db_conn=conn,
    global_batch=True,
    runner_id=f'batch_{interaction_id}',
    trigger_interaction_id=interaction_id  # Links all child work back to this run
)

print("Runner initialized, starting execution...")
sys.stdout.flush()

try:
    stats = runner.run(max_iterations=2000)
    
    print()
    print("=" * 50)
    print("RUN COMPLETE")
    print(f"Completed: {stats['interactions_completed']}")
    print(f"Failed: {stats['interactions_failed']}")
    print(f"Iterations: {stats['iterations']}")
    
    # Record successful completion
    complete_workflow_interaction(interaction_id, output=stats)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    complete_workflow_interaction(interaction_id, error=str(e))
    raise
finally:
    conn.close()
