#!/usr/bin/env python3
"""
Test Workflow 3001 Failure Path (WALK Phase Task 2)

Tests the Improve → Regrade → Ticket pathway using deliberately poor posting.
Posting ID 4793: "Generic Role" with minimal description.

Expected behavior:
1. Fetch Jobs → Extract Summary
2. Grade A → FAIL (poor quality)
3. Grade B → FAIL (confirms poor quality)
4. Branch to Improve Summary (conversation 9145)
5. Regrade Summary (conversation 9146)
6. If still fails → Create Ticket (conversation 9147)

Run with: nohup python3 scripts/test_failure_path.py > logs/test_failure_path.log 2>&1 &
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()

def main():
    print("=" * 80)
    print("WALK Phase - Validation: Test Duplicate Ticket Fix")
    print("=" * 80)
    print(f"Posting ID: 4794 (TEST_FAIL_VALIDATION)")
    print(f"Job: Generic Role - deliberately poor quality")
    print(f"Expected: Trigger Improve → Regrade → Ticket pathway")
    print(f"CRITICAL: Should create only ONE ticket (not two)")
    print("=" * 80)
    print()
    
    # Connect to database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='turing',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    # Start workflow from beginning (Fetch Jobs)
    print("Starting Workflow 3001 from step 1 (Fetch Jobs)...")
    result = start_workflow(
        db_conn=conn,
        workflow_id=3001,
        posting_id=4794,
        start_conversation_id=9144  # Fetch Jobs from Deutsche Bank API
    )
    
    workflow_run_id = result['workflow_run_id']
    
    print(f"\n✓ Workflow run created: {workflow_run_id}")
    print(f"✓ Starting execution with trace enabled...")
    print()
    
    # Create runner and execute with trace enabled
    runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
    trace_file = f'reports/trace_failure_run_{workflow_run_id}.md'
    results = runner.run(
        max_iterations=20,  # Allow enough for full failure path
        trace=True,
        trace_file=trace_file
    )
    
    print()
    print("=" * 80)
    print("Execution Complete")
    print("=" * 80)
    print(f"Workflow Run ID: {workflow_run_id}")
    print(f"Total Interactions: {results.get('total_interactions', 0)}")
    print(f"Failures: {results.get('failures', 0)}")
    print(f"Duration: {results.get('duration', 0):.1f}s")
    print(f"Trace Report: {trace_file}")
    print()
    print("Verification queries:")
    print(f"  ./scripts/q.sh \"SELECT jsonb_object_keys(state) FROM workflow_runs WHERE workflow_run_id = {workflow_run_id};\"")
    print(f"  ./scripts/q.sh \"SELECT i.interaction_id, c.conversation_name FROM interactions i JOIN conversations c ON i.conversation_id = c.conversation_id WHERE i.workflow_run_id = {workflow_run_id} ORDER BY i.interaction_id;\"")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()
