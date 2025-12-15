#!/usr/bin/env python3
"""
Batch Summary Extractor - Optimized Parallel Processing
========================================================
Extract job summaries for all postings that don't have them yet.

Uses workflow 3001 but SKIPS conversations that process already-populated fields:
- SKIP IHL scoring if ihl_score already exists
- SKIP skill extraction if posting_skills already exist  
- ONLY run summary extraction for postings with NULL extracted_summary

Optimization Strategy:
1. Single TuringOrchestrator instance (models stay loaded)
2. ThreadPoolExecutor with N workers (default: 3)
3. Each worker processes one posting at a time
4. Progress tracking every 10 postings
5. Graceful shutdown on Ctrl+C

Author: Arden & xai
Date: 2025-11-12
"""

import sys
import time
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection
from core.turing_orchestrator import TuringOrchestrator


# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested
    print("\n⚠️  Shutdown requested - finishing current tasks...")
    shutdown_requested = True


def process_single_posting(orch, posting_id: int, job_description: str, dry_run: bool = False):
    """
    Process a single posting through workflow 3001 with conditional branching
    
    Workflow 3001 now has intelligent branching (Migration 070):
    1. Extracts summary (conversations 2-8)
    2. Saves summary + checks IHL status (conversation 9 - script actor)
    3. BRANCHES based on IHL:
       - [HAS_IHL] → TERMINAL (done! ~40s total)
       - [NO_IHL] → Continue to skills + IHL (conversations 10-16, ~70s total)
    
    Args:
        orch: TuringOrchestrator instance (REUSED across all postings)
        posting_id: Posting to process
        job_description: Raw job text
        dry_run: If True, don't commit to database
        
    Returns:
        dict: Processing result with execution details
    """
    try:
        # Execute workflow 3001 - it handles EVERYTHING automatically!
        result = orch.execute_workflow(
            workflow_id=3001,
            inputs={
                'variations_param_1': job_description,  # Job description text
                'posting_id': posting_id,
                'user_id': 1,
                'max_jobs': 1,
                'source_id': 1
            },
            dry_run=dry_run
        )
        
        if result['status'] == 'success':
            # Check conversation path to see if IHL was skipped
            conversation_count = len(result.get('conversation_path', []))
            execution_time = result.get('execution_time_seconds', 0)
            
            # Conversation 9 is save_summary_check_ihl - check its output for branch
            branch_taken = None
            for conv in result.get('conversation_path', []):
                if conv.get('conversation_name') == 'Save Summary and Check IHL Status':
                    output = conv.get('output', '')
                    if '[HAS_IHL]' in output:
                        branch_taken = 'HAS_IHL'
                    elif '[NO_IHL]' in output:
                        branch_taken = 'NO_IHL'
                    break
            
            return {
                'posting_id': posting_id,
                'status': 'success',
                'conversations_executed': conversation_count,
                'execution_time': execution_time,
                'branch_taken': branch_taken,
                'ihl_skipped': branch_taken == 'HAS_IHL'
            }
        else:
            return {
                'posting_id': posting_id,
                'status': 'failed',
                'error': result.get('error_message', 'Unknown workflow error')
            }
            
    except Exception as e:
        return {
            'posting_id': posting_id,
            'status': 'error',
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Batch Summary Extractor - Optimized Parallel Processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process with 3 workers (default)
  python3 tools/batch_summary_extractor.py
  
  # Process first 10 postings (testing)
  python3 tools/batch_summary_extractor.py --limit 10
  
  # Dry run (no database saves)
  python3 tools/batch_summary_extractor.py --limit 5 --dry-run
  
  # Use 5 parallel workers for faster processing
  python3 tools/batch_summary_extractor.py --workers 5
        """
    )
    
    parser.add_argument('--workers', type=int, default=3,
                       help='Number of parallel workers (default: 3)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of postings to process')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run (no database changes)')
    parser.add_argument('--skip-ihl', action='store_true', default=True,
                       help='Skip IHL scoring if already done (default: True)')
    
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print('=' * 80)
    print('BATCH SUMMARY EXTRACTOR - Optimized Parallel Processing')
    print('=' * 80)
    print(f"Workers: {args.workers}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Limit: {args.limit or 'None (all pending)'}")
    print()
    
    # Get pending postings (those without extracted_summary)
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
        SELECT posting_id, job_description
        FROM postings
        WHERE extracted_summary IS NULL           -- Need summary
          AND job_description IS NOT NULL         -- Have raw text
          AND job_description != ''               -- Not empty
          AND ihl_score IS NOT NULL               -- Already scored (skip IHL conversations)
        ORDER BY posting_id
    """
    
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    cur.execute(query)
    postings = cur.fetchall()
    total = len(postings)
    
    if total == 0:
        print("✅ No postings need summary extraction!")
        return
    
    print(f"📊 Found {total} postings needing summary extraction")
    print()
    
    # Initialize TuringOrchestrator ONCE (reused across all workers)
    print("🎼 Initializing TuringOrchestrator...")
    orch = TuringOrchestrator(verbose=False)
    print("✅ Orchestrator ready")
    print()
    
    # Track results
    start_time = time.time()
    successful = 0
    failed = 0
    processed = 0
    
    print(f"🚀 Starting batch processing with {args.workers} workers...")
    print("=" * 80)
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_posting = {
            executor.submit(
                process_single_posting,
                orch,
                p['posting_id'],
                p['job_description'],
                args.dry_run
            ): p['posting_id'] for p in postings
        }
        
        # Process results as they complete
        for future in as_completed(future_to_posting):
            if shutdown_requested:
                print("\n⚠️  Cancelling remaining tasks...")
                executor.shutdown(wait=False, cancel_futures=True)
                break
            
            result = future.result()
            processed += 1
            
            if result['status'] == 'success':
                successful += 1
                conversations = result.get('conversations_executed', 0)
                exec_time = result.get('execution_time', 0)
                branch = result.get('branch_taken', 'UNKNOWN')
                skipped = " (IHL SKIPPED)" if result.get('ihl_skipped') else ""
                print(f"✅ [{processed}/{total}] Posting {result['posting_id']}: "
                      f"{conversations} convs, {exec_time:.1f}s, [{branch}]{skipped}")
            else:
                failed += 1
                error = result.get('error', 'Unknown')[:50]
                print(f"❌ [{processed}/{total}] Posting {result['posting_id']}: "
                      f"FAILED - {error}")
            
            # Progress report every 10 postings
            if processed % 10 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                remaining = total - processed
                eta_seconds = remaining / rate if rate > 0 else 0
                eta = timedelta(seconds=int(eta_seconds))
                
                print()
                print(f"📊 Progress: {processed}/{total} ({100*processed/total:.1f}%)")
                print(f"   Success: {successful} | Failed: {failed}")
                print(f"   Rate: {rate:.1f} postings/sec")
                print(f"   ETA: {eta}")
                print("=" * 80)
    
    # Final report
    elapsed = time.time() - start_time
    
    print()
    print("=" * 80)
    print("✅ BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total Processed: {processed}/{total}")
    print(f"Successful: {successful} ({100*successful/processed:.1f}%)")
    print(f"Failed: {failed} ({100*failed/processed:.1f}%)")
    print(f"Duration: {timedelta(seconds=int(elapsed))}")
    print(f"Average Rate: {processed/elapsed:.2f} postings/sec")
    
    if args.dry_run:
        print()
        print("⚠️  DRY RUN - No database changes made")
    
    if shutdown_requested:
        print()
        print("⚠️  Processing interrupted by user")


if __name__ == '__main__':
    main()
