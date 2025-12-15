#!/usr/bin/env python3
"""
Full Workflow 3001 Test - 3 Postings End-to-End

Tests complete workflow execution on 3 postings through all conversations.
Starts from Extract Summary (not job fetcher) with 3 real postings.

This is the final validation before RUN Phase.

Run with: python3 scripts/test_full_workflow_3_postings.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test with these 3 postings (created from job fetcher staging records)
TEST_POSTING_IDS = [4795, 4796, 4797]

def main():
    print("=" * 80)
    print("FULL WORKFLOW 3001 TEST - 3 POSTINGS END-TO-END")
    print("=" * 80)
    print(f"Test Postings: {TEST_POSTING_IDS}")
    print("Start: Extract Summary (3335)")
    print("Includes: Extract → Grade → (Improve/Regrade if needed) → Format → Save → Skills → IHL")
    print("Trace: ENABLED for all 3 runs")
    print("=" * 80)
    print()
    
    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verify postings exist
    cursor.execute('''
    SELECT posting_id, job_title, LENGTH(job_description) as desc_len
    FROM postings
    WHERE posting_id = ANY(%s)
    ORDER BY posting_id
    ''', (TEST_POSTING_IDS,))
    
    postings = cursor.fetchall()
    print("Posting details:")
    for p in postings:
        print(f"  {p['posting_id']}: {p['job_title']} ({p['desc_len']} chars)")
    print()
    
    if len(postings) != len(TEST_POSTING_IDS):
        print(f"ERROR: Expected {len(TEST_POSTING_IDS)} postings, found {len(postings)}")
        return
    
    cursor.close()
    
    # Run workflow for each posting
    results_summary = []
    
    for posting_id in TEST_POSTING_IDS:
        print("=" * 80)
        print(f"TESTING POSTING {posting_id}")
        print("=" * 80)
        
        # Start workflow from Extract Summary (conversation 3335)
        result = start_workflow(
            db_conn=conn,
            workflow_id=3001,
            posting_id=posting_id,
            start_conversation_id=3335  # Extract Summary
        )
        
        workflow_run_id = result['workflow_run_id']
        print(f"✓ Workflow run created: {workflow_run_id}")
        
        # Create runner and execute with trace
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        trace_file = f'reports/trace_posting_{posting_id}_run_{workflow_run_id}.md'
        
        print(f"✓ Trace file: {trace_file}")
        print("✓ Executing...")
        
        run_results = runner.run(
            max_iterations=20,  # Should be enough for full pipeline
            trace=True,
            trace_file=trace_file
        )
        
        print(f"✓ Complete: {run_results.get('total_interactions', 0)} interactions in {run_results.get('duration', 0):.1f}s")
        print()
        
        results_summary.append({
            'posting_id': posting_id,
            'workflow_run_id': workflow_run_id,
            'interactions': run_results.get('total_interactions', 0),
            'failures': run_results.get('failures', 0),
            'duration': run_results.get('duration', 0),
            'trace_file': trace_file
        })
    
    # Print summary
    print()
    print("=" * 80)
    print("FINAL SUMMARY - ALL 3 POSTINGS")
    print("=" * 80)
    print()
    
    total_interactions = 0
    total_failures = 0
    total_duration = 0
    
    for result in results_summary:
        total_interactions += result['interactions']
        total_failures += result['failures']
        total_duration += result['duration']
        
        status = "✅ SUCCESS" if result['failures'] == 0 else f"⚠️  {result['failures']} FAILURES"
        print(f"Posting {result['posting_id']} (Run {result['workflow_run_id']}):")
        print(f"  {status}")
        print(f"  Interactions: {result['interactions']}")
        print(f"  Duration: {result['duration']:.1f}s")
        print(f"  Trace: {result['trace_file']}")
        print()
    
    print("-" * 80)
    print(f"Total Interactions: {total_interactions}")
    print(f"Total Failures: {total_failures}")
    print(f"Total Duration: {total_duration:.1f}s")
    print(f"Average per posting: {total_duration/len(TEST_POSTING_IDS):.1f}s")
    print("=" * 80)
    
    # Query aggregate statistics
    cursor = conn.cursor()
    
    workflow_run_ids = [r['workflow_run_id'] for r in results_summary]
    
    # Count interactions by conversation across all runs
    cursor.execute('''
    SELECT c.conversation_name, COUNT(*) as count
    FROM interactions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE i.workflow_run_id = ANY(%s)
    GROUP BY c.conversation_name
    ORDER BY MIN(i.interaction_id)
    ''', (workflow_run_ids,))
    
    print()
    print("Aggregate interaction counts (all 3 postings):")
    for row in cursor.fetchall():
        print(f"  {row['conversation_name']}: {row['count']}")
    print()
    
    # Check for any failures
    cursor.execute('''
    SELECT COUNT(*) as failed_count
    FROM interactions
    WHERE workflow_run_id = ANY(%s) AND status = 'failed'
    ''', (workflow_run_ids,))
    
    failed_count = cursor.fetchone()['failed_count']
    if failed_count > 0:
        print(f"⚠️  WARNING: {failed_count} interactions failed across all runs")
    else:
        print("✅ All interactions completed successfully across all 3 postings!")
    
    print()
    print("=" * 80)
    print("VALIDATION COMPLETE - READY FOR RUN PHASE")
    print("=" * 80)
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
