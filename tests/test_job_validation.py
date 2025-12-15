#!/usr/bin/env python3
"""
Test job description validation (Defense in Depth)
Tests both layers:
1. Job Fetcher validation (prevents bad data entering staging)
2. Validation conversation (catches bad data in postings table)

Date: November 26, 2025
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def test_validation_conversation():
    """Test that validation conversation stops workflow for invalid posting"""
    
    print("=" * 80)
    print("TEST: Job Description Validation (Posting 4794)")
    print("=" * 80)
    print()
    print("Posting 4794: 'Generic Role' with 88 characters (below 100 threshold)")
    print("Expected: Workflow stops at step 2 (Validate Job Description)")
    print("Expected output: [TOO_SHORT]")
    print()
    
    # Connect to database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='turing',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    # Start workflow for posting 4794
    result = start_workflow(
        db_conn=conn,
        workflow_id=3001,
        posting_id=4794,
        params={}
    )
    
    workflow_run_id = result['workflow_run_id']
    print(f"✅ Workflow run: {workflow_run_id}")
    print(f"✅ Seed interaction: {result['seed_interaction_id']}")
    print()
    
    # Run workflow with trace
    runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
    
    print("⚡ Executing workflow...")
    runner_result = runner.run(
        max_iterations=5,  # Should stop at validation (step 2)
        trace=True,
        trace_file=f'reports/trace_validation_test_run_{workflow_run_id}.md'
    )
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"📄 Trace report: reports/trace_validation_test_run_{workflow_run_id}.md")
    print(f"📊 Interactions completed: {runner_result['interactions_completed']}")
    print(f"📊 Interactions failed: {runner_result['interactions_failed']}")
    print()
    print("Expected result:")
    print("- Step 1: Fetch Jobs (should be skipped - no staging_ids)")
    print("- Step 2: Validate Job Description → [TOO_SHORT]")
    print("- Workflow STOPS (no step 3)")
    print()
    
    conn.close()

if __name__ == '__main__':
    test_validation_conversation()
