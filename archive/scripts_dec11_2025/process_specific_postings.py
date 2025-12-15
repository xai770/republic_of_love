#!/usr/bin/env python3
"""
Process Specific Posting IDs with Optimized Batch Processing
=============================================================

Processes a specific range of posting IDs with parallel workers.
Uses WaveRunner for wave batching optimization.

Usage:
    python3 scripts/process_specific_postings.py --start 4920 --end 5100 --workers 5

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
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


def process_single_posting(posting_id: int, workflow_id: int = 3001):
    """Process a single posting through the workflow."""
    conn = get_connection()
    start_time = time.time()
    
    try:
        # Start workflow
        result = start_workflow(
            conn,
            workflow_id=workflow_id,
            posting_id=posting_id
        )
        
        workflow_run_id = result['workflow_run_id']
        
        # Run workflow
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        wave_result = runner.run(max_iterations=100)
        
        duration = time.time() - start_time
        
        # Check validation result
        cursor = conn.cursor()
        cursor.execute("""
            SELECT output
            FROM interactions
            WHERE workflow_run_id = %s AND conversation_id = 9193
        """, (workflow_run_id,))
        
        validation_result = cursor.fetchone()
        if validation_result:
            output = validation_result[0]
            if '[NO_DESCRIPTION]' in str(output) or '[TOO_SHORT]' in str(output):
                return {
                    'posting_id': posting_id,
                    'status': 'rejected',
                    'duration': duration,
                    'workflow_run_id': workflow_run_id
                }
        
        # Check completion
        if wave_result['interactions_failed'] > 0:
            return {
                'posting_id': posting_id,
                'status': 'failed',
                'duration': duration,
                'workflow_run_id': workflow_run_id
            }
        
        return {
            'posting_id': posting_id,
            'status': 'completed',
            'duration': duration,
            'workflow_run_id': workflow_run_id,
            'interactions': wave_result['interactions_completed']
        }
        
    except Exception as e:
        duration = time.time() - start_time
        return {
            'posting_id': posting_id,
            'status': 'error',
            'duration': duration,
            'error': str(e)
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Process specific posting IDs')
    parser.add_argument('--start', type=int, required=True, help='Start posting_id')
    parser.add_argument('--end', type=int, required=True, help='End posting_id (inclusive)')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers')
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"PROCESSING POSTINGS {args.start}-{args.end} ({args.workers} WORKERS)")
    print(f"{'='*80}\n")
    
    # Get posting IDs in range
    conn = get_connection()
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
    conn.close()
    
    print(f"Found {len(posting_ids)} postings to process\n")
    
    if len(posting_ids) == 0:
        print("⚠️  No postings found in range")
        return 1
    
    # Process with parallel workers
    stats = {'completed': 0, 'rejected': 0, 'failed': 0, 'error': 0}
    start_batch = time.time()
    durations = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_posting = {
            executor.submit(process_single_posting, posting_id): posting_id 
            for posting_id in posting_ids
        }
        
        for idx, future in enumerate(as_completed(future_to_posting), 1):
            result = future.result()
            posting_id = future_to_posting[future]
            
            stats[result['status']] += 1
            durations.append(result['duration'])
            
            avg_duration = sum(durations) / len(durations)
            eta_seconds = (len(posting_ids) - idx) * avg_duration / args.workers
            eta = timedelta(seconds=int(eta_seconds))
            
            status_emoji = {
                'completed': '✅',
                'rejected': '⚠️',
                'failed': '❌',
                'error': '🔥'
            }.get(result['status'], '❓')
            
            print(f"[{idx}/{len(posting_ids)}] Posting {posting_id}: {status_emoji} {result['status'].upper()} ({result['duration']:.1f}s)")
            print(f"   Progress: {idx/len(posting_ids)*100:.1f}% | Avg: {avg_duration:.1f}s/job | ETA: {eta}")
            
            if idx % 10 == 0:
                print(f"\n📊 Stats: ✅ {stats['completed']} | ⚠️ {stats['rejected']} | ❌ {stats['failed']} | 🔥 {stats['error']}\n")
    
    # Final summary
    total_duration = time.time() - start_batch
    print(f"\n{'='*80}")
    print("BATCH COMPLETE")
    print(f"{'='*80}\n")
    print(f"Total time: {timedelta(seconds=int(total_duration))}")
    print(f"Average: {total_duration/len(posting_ids):.1f}s per job")
    print(f"\nFinal stats:")
    print(f"  ✅ Completed: {stats['completed']}")
    print(f"  ⚠️  Rejected: {stats['rejected']}")
    print(f"  ❌ Failed: {stats['failed']}")
    print(f"  🔥 Errors: {stats['error']}")
    print(f"\nSuccess rate: {stats['completed']/len(posting_ids)*100:.1f}%\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
