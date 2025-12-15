#!/usr/bin/env python3
"""
Process Multiple Postings with TRUE Wave Batching
==================================================

This script demonstrates the CORRECT way to use WaveRunner for batch processing:
1. Start workflows for ALL postings first (creates pending interactions)
2. Run ONE WaveRunner instance WITHOUT posting_id filter
3. WaveRunner groups ALL pending interactions by model
4. Load each model once, process all interactions for that model, unload

This achieves true wave batching:
- Wave 1: ALL gemma3:1b interactions across all postings
- Wave 2: ALL mistral interactions across all postings
- Wave 3: ALL gemma2 interactions across all postings
- Wave 4: ALL qwen interactions across all postings

Expected speedup: 12-15x (4.6x from mistral + 3x from batching)

Author: Sandy
Date: November 27, 2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import time
import argparse
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description='Process postings with true wave batching')
    parser.add_argument('--start', type=int, required=True, help='Start posting_id')
    parser.add_argument('--end', type=int, required=True, help='End posting_id (inclusive)')
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"TRUE WAVE BATCHING - Processing {args.start}-{args.end}")
    print(f"{'='*80}\n")
    
    conn = get_connection()
    
    # Step 1: Get posting IDs
    print("Step 1: Fetching posting IDs...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT posting_id
        FROM postings
        WHERE posting_id BETWEEN %s AND %s
          AND job_description IS NOT NULL
        ORDER BY posting_id
    """, (args.start, args.end))
    
    rows = cursor.fetchall()
    posting_ids = [row[0] if isinstance(row, tuple) else row['posting_id'] for row in rows]
    
    print(f"Found {len(posting_ids)} postings\n")
    
    if len(posting_ids) == 0:
        print("⚠️  No postings found")
        return 1
    
    # Step 2: Start workflows for ALL postings (creates pending interactions)
    print(f"Step 2: Starting workflows for {len(posting_ids)} postings...")
    print("(This creates pending interactions but doesn't execute them yet)\n")
    
    workflow_run_ids = []
    start_time = time.time()
    
    for idx, posting_id in enumerate(posting_ids, 1):
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=posting_id
        )
        workflow_run_ids.append(result['workflow_run_id'])
        
        if idx % 20 == 0:
            print(f"  Started {idx}/{len(posting_ids)} workflows...")
    
    startup_duration = time.time() - start_time
    print(f"\n✅ Started {len(workflow_run_ids)} workflows in {startup_duration:.1f}s")
    print(f"   Average: {startup_duration/len(workflow_run_ids)*1000:.0f}ms per workflow\n")
    
    # Step 3: Count pending interactions
    print("Step 3: Counting pending interactions...")
    cursor.execute("""
        SELECT 
            a.actor_name,
            a.execution_config->>'model' as model,
            COUNT(*) as pending
        FROM interactions i
        JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.status = 'pending'
          AND i.workflow_run_id = ANY(%s)
        GROUP BY a.actor_name, a.execution_config->>'model'
        ORDER BY COUNT(*) DESC
    """, (workflow_run_ids,))
    
    print("\nPending interactions by model:")
    for row in cursor.fetchall():
        actor_name = row[0] if isinstance(row, tuple) else row['actor_name']
        model = row[1] if isinstance(row, tuple) else row['model']
        pending = row[2] if isinstance(row, tuple) else row['pending']
        model_str = model if model else 'script'
        print(f"  {actor_name:30} ({model_str:15}): {pending:4} interactions")
    
    # Step 4: Run ONE WaveRunner WITHOUT posting_id filter
    # This groups ALL pending interactions by model (TRUE wave batching!)
    print(f"\n{'='*80}")
    print("Step 4: Executing with TRUE WAVE BATCHING")
    print(f"{'='*80}\n")
    print("WaveRunner will:")
    print("  1. Group ALL pending interactions by model")
    print("  2. Load model ONCE, process entire batch")
    print("  3. Move to next model")
    print("  4. Repeat until all interactions complete\n")
    
    processing_start = time.time()
    
    # Create WaveRunner in GLOBAL BATCH mode (pools ALL pending interactions!)
    runner = WaveRunner(conn, global_batch=True)
    
    result = runner.run(max_iterations=500)
    
    processing_duration = time.time() - processing_start
    
    # Step 5: Report results
    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}\n")
    
    total_duration = startup_duration + processing_duration
    
    print(f"Startup time:     {startup_duration:.1f}s")
    print(f"Processing time:  {processing_duration:.1f}s")
    print(f"Total time:       {total_duration:.1f}s\n")
    
    print(f"Interactions completed: {result['interactions_completed']}")
    print(f"Interactions failed:    {result['interactions_failed']}")
    print(f"Iterations:             {result['iterations']}\n")
    
    if result['interactions_completed'] > 0:
        avg_per_interaction = processing_duration / result['interactions_completed']
        print(f"Average: {avg_per_interaction:.2f}s per interaction")
        print(f"Average: {total_duration/len(posting_ids):.1f}s per posting\n")
    
    # Check workflow completion status
    cursor.execute("""
        SELECT 
            status,
            COUNT(*) as count
        FROM workflow_runs
        WHERE workflow_run_id = ANY(%s)
        GROUP BY status
    """, (workflow_run_ids,))
    
    print("Workflow completion status:")
    for row in cursor.fetchall():
        status = row[0] if isinstance(row, tuple) else row['status']
        count = row[1] if isinstance(row, tuple) else row['count']
        emoji = {'completed': '✅', 'running': '🔄', 'failed': '❌'}.get(status, '❓')
        print(f"  {emoji} {status:10}: {count}")
    
    conn.close()
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
