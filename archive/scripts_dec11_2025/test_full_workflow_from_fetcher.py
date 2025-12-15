#!/usr/bin/env python3
"""
Test full workflow 3001 starting from Job Fetcher.
Fetches 3 jobs, processes through complete workflow, generates comprehensive trace.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import subprocess
import time

def main():
    """Test complete workflow starting from job fetcher."""
    
    print(f"\n{'='*80}")
    print(f"Testing FULL Workflow 3001 - Starting from Job Fetcher")
    print(f"{'='*80}\n")
    
    conn = get_connection()
    
    try:
        # Start workflow from Job Fetcher (no posting_id needed, fetcher creates them)
        print(f"Initializing workflow from Job Fetcher (9144)...")
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=None,  # No posting yet - fetcher will create them
            start_conversation_id=9144,  # Job Fetcher
            params={
                "jobs_to_fetch": 3,
                "rate_limit": False  # Turn off rate limiting as requested
            }
        )
        
        workflow_run_id = result['workflow_run_id']
        print(f"✅ Workflow initialized: run_id={workflow_run_id}")
        print(f"   Seed interaction: {result['seed_interaction_id']}")
        print(f"   First conversation: {result['first_conversation_name']}")
        
        # Run Wave Runner
        print(f"\n🌊 Running Wave Runner...")
        print("=" * 80)
        
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        start_time = time.time()
        wave_result = runner.run(max_iterations=50)  # Generous limit for 3 jobs
        duration = time.time() - start_time
        
        print("\n" + "=" * 80)
        print(f"WORKFLOW RUN {workflow_run_id} RESULTS")
        print("=" * 80)
        print(f"Interactions completed: {wave_result['interactions_completed']}")
        print(f"Interactions failed: {wave_result['interactions_failed']}")
        print(f"Iterations: {wave_result['iterations']}")
        print(f"Duration: {duration:.2f}s")
        
        # Get final workflow state
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, state FROM workflow_runs WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        
        wf_result = cursor.fetchone()
        print(f"\nWorkflow Status: {wf_result['status']}")
        
        state = wf_result['state']
        print(f"\nFinal Workflow State:")
        if 'jobs_fetched' in state:
            print(f"  Jobs Fetched: {state['jobs_fetched']}")
        if 'staging_ids' in state:
            print(f"  Staging IDs: {state['staging_ids']}")
        if 'posting_ids' in state:
            print(f"  Posting IDs: {state['posting_ids']}")
        
        # Get interaction type breakdown
        cursor.execute("""
            SELECT c.conversation_name, COUNT(*) as count
            FROM interactions i
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE i.workflow_run_id = %s
            GROUP BY c.conversation_name
            ORDER BY count DESC
        """, (workflow_run_id,))
        
        print(f"\nInteraction breakdown:")
        for row in cursor.fetchall():
            print(f"  {row['conversation_name']}: {row['count']}")
        
        cursor.close()
        
        # Generate comprehensive trace
        trace_name = f"trace_full_workflow_3_jobs_run_{workflow_run_id}"
        print(f"\nGenerating comprehensive trace: {trace_name}")
        subprocess.run([
            "python3", "tools/generate_retrospective_trace.py",
            str(workflow_run_id),
            trace_name
        ])
        
        if wave_result['interactions_failed'] == 0 and wf_result['status'] == 'completed':
            print(f"\n✅ COMPLETE SUCCESS!")
            print("All 3 jobs fetched and processed through full workflow with 0 failures")
            print("VALIDATION COMPLETE - READY FOR RUN PHASE")
        else:
            print(f"\n⚠️ Workflow completed with some issues - check trace for details")
        
    except Exception as e:
        print(f"\n❌ ERROR running workflow: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

