#!/usr/bin/env python3
"""
Batch IHL Scorer - Parallel Processing
=======================================
Process multiple postings in parallel using TuringOrchestrator.
Includes the _save_ihl_score() hook for database persistence.
"""

import sys
import time
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.turing_orchestrator import TuringOrchestrator

DB_CONFIG = {
    'host': 'localhost',
    'database': 'turing',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}


def process_single_posting(orch, posting_id, job_description):
    """Process a single posting through workflow 1124"""
    try:
        result = orch.execute_workflow(
            workflow_id=1124,
            inputs={'posting_id': posting_id, 'job_description': job_description},
            dry_run=False
        )
        
        if result['status'] == 'success':
            # Call the save hook manually
            workflow_run_id = result.get('workflow_run_id')
            if workflow_run_id:
                try:
                    orch._save_ihl_score(1124, posting_id, workflow_run_id)
                    return {'posting_id': posting_id, 'status': 'success', 'saved': True}
                except Exception as e:
                    return {'posting_id': posting_id, 'status': 'success', 'saved': False, 'error': str(e)}
        
        return {'posting_id': posting_id, 'status': 'failed', 'error': result.get('error', 'Unknown')}
        
    except Exception as e:
        return {'posting_id': posting_id, 'status': 'error', 'error': str(e)}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch IHL Scorer with Parallel Processing')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of postings to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no database changes)')
    
    args = parser.parse_args()
    
    print('=' * 70)
    print('BATCH IHL SCORER - Parallel Processing')
    print('=' * 70)
    print()
    
    # Get pending postings
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    query = """
        SELECT posting_id, job_description
        FROM postings
        WHERE ihl_score IS NULL
          AND job_description IS NOT NULL
          AND job_description != ''
        ORDER BY posting_id
    """
    
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    cur.execute(query)
    postings = cur.fetchall()
    conn.close()
    
    if not postings:
        print('✅ No postings need IHL scoring!')
        return
    
    print(f'Found {len(postings)} postings to process')
    print(f'Workers: {args.workers}')
    print(f'Estimated time: ~{len(postings) * 68 / args.workers / 60:.1f} minutes')
    print()
    
    if args.dry_run:
        print('⚠️  DRY RUN MODE - No changes will be saved')
        print()
    
    # Initialize orchestrator (verbose=False for cleaner parallel output)
    orch = TuringOrchestrator(verbose=False)
    
    # Process in parallel
    start_time = time.time()
    results = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all jobs
        future_to_posting = {
            executor.submit(process_single_posting, orch, posting_id, job_desc): posting_id
            for posting_id, job_desc in postings
        }
        
        # Process results as they complete
        for future in as_completed(future_to_posting):
            posting_id = future_to_posting[future]
            try:
                result = future.result()
                results.append(result)
                completed += 1
                
                # Progress update every 5 postings
                if completed % 5 == 0 or completed == len(postings):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = len(postings) - completed
                    eta = remaining / rate if rate > 0 else 0
                    
                    print(f'[{completed}/{len(postings)}] ', end='')
                    
                    if result['status'] == 'success' and result.get('saved'):
                        print(f'✅ Posting {posting_id}')
                    elif result['status'] == 'success':
                        print(f'⚠️  Posting {posting_id} (not saved: {result.get("error", "unknown")})')
                    else:
                        print(f'❌ Posting {posting_id} ({result.get("error", "unknown")[:50]})')
                    
                    if completed % 5 == 0:
                        print(f'    Progress: {completed}/{len(postings)} | Rate: {rate:.2f}/s | ETA: {int(eta/60)}m {int(eta%60)}s')
                        print()
                
            except Exception as e:
                print(f'❌ Posting {posting_id} - Exception: {e}')
                results.append({'posting_id': posting_id, 'status': 'exception', 'error': str(e)})
    
    # Summary
    elapsed = time.time() - start_time
    success = sum(1 for r in results if r['status'] == 'success' and r.get('saved'))
    partial = sum(1 for r in results if r['status'] == 'success' and not r.get('saved'))
    failed = sum(1 for r in results if r['status'] != 'success')
    
    print()
    print('=' * 70)
    print('BATCH COMPLETE')
    print('=' * 70)
    print(f'Total processed: {len(results)}')
    print(f'Success (saved): {success}')
    print(f'Success (not saved): {partial}')
    print(f'Failed: {failed}')
    print(f'Duration: {elapsed:.1f}s ({elapsed/60:.1f} minutes)')
    print(f'Average: {elapsed/len(results):.1f}s per posting')
    print()
    
    # Verify in database
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM postings WHERE ihl_score IS NOT NULL")
    scored = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM postings WHERE job_description IS NOT NULL AND job_description != ''")
    total = cur.fetchone()[0]
    conn.close()
    
    print(f'IHL Coverage: {scored}/{total} ({scored/total*100:.1f}%)')
    print('=' * 70)


if __name__ == '__main__':
    main()
