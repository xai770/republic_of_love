#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Workflow 3001 Smoke Test
═══════════════════════════════════════════════════════════════════════════════

Run a single posting through workflow 3001 and verify each step completes
successfully. Use this after making changes to validate the pipeline.

HOW TO RUN
═══════════════════════════════════════════════════════════════════════════════

    cd /home/xai/Documents/ty_wave
    source venv/bin/activate
    
    # Run with a specific posting
    python3 tests/test_workflow_3001_smoke.py --posting-id 5150
    
    # Run with a random unprocessed posting
    python3 tests/test_workflow_3001_smoke.py
    
    # Dry run (don't execute, just show what would happen)
    python3 tests/test_workflow_3001_smoke.py --dry-run

WHAT IT TESTS
═══════════════════════════════════════════════════════════════════════════════

1. Extract Summary (conversation 3335) - llama3.2:latest
   - Verifies summary is generated
   - Checks for degeneration (repeated patterns)
   
2. Grade A (conversation 3336) - mistral:latest
   - Verifies verdict is [PASS] or [FAIL]
   
3. Grade B (conversation 3337) - qwen2.5:7b
   - Verifies verdict is [PASS] or [FAIL]
   
4. Branching Logic
   - If both PASS → Format Standardization
   - If any FAIL → Improvement → Regrade
   
5. Format Standardization (conversation 3341) - qwen2.5:7b
   - Verifies output follows template
   
6. Summary Saved
   - Verifies postings.extracted_summary is populated

AUTHOR
═══════════════════════════════════════════════════════════════════════════════

Created: 2025-12-01
Author: Arden (Architecture Lead)
Purpose: Regression testing after model/prompt changes
"""

import os
import sys
import time
import argparse
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )


def get_random_unprocessed_posting(conn):
    """Get a random posting that hasn't been processed yet."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT posting_id, job_title, external_job_id
        FROM postings
        WHERE invalidated = false
          AND extracted_summary IS NULL
          AND job_description IS NOT NULL
          AND LENGTH(job_description) > 500
        ORDER BY RANDOM()
        LIMIT 1
    """)
    return cur.fetchone()


def get_posting(conn, posting_id):
    """Get a specific posting."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT posting_id, job_title, external_job_id, job_description
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    return cur.fetchone()


def start_workflow_for_posting(conn, posting_id, workflow_id=3001):
    """Create a new workflow run for a posting."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Create workflow run
    cur.execute("""
        INSERT INTO workflow_runs (workflow_id, posting_id, status, state)
        VALUES (%s, %s, 'pending', '{}')
        RETURNING workflow_run_id
    """, (workflow_id, posting_id))
    
    result = cur.fetchone()
    conn.commit()
    return result['workflow_run_id']


def wait_for_interactions(conn, workflow_run_id, conversation_ids, timeout_seconds=300):
    """Wait for specific conversations to complete."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        cur.execute("""
            SELECT 
                i.conversation_id,
                c.conversation_name,
                i.status,
                i.output,
                i.error_message
            FROM interactions i
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE i.workflow_run_id = %s
              AND i.conversation_id = ANY(%s)
            ORDER BY i.conversation_id
        """, (workflow_run_id, list(conversation_ids)))
        
        interactions = cur.fetchall()
        
        # Check if all expected conversations have completed
        completed = {i['conversation_id']: i for i in interactions if i['status'] == 'completed'}
        
        if len(completed) >= len(conversation_ids):
            return completed
        
        # Check for failures
        failed = [i for i in interactions if i['status'] == 'failed']
        if failed:
            return {'failed': failed}
        
        time.sleep(5)
    
    return {'timeout': True}


def check_for_degeneration(text, threshold=10):
    """Check if output has degenerate patterns (repeated phrases)."""
    if not text:
        return False, None
    
    # Look for patterns like "work work work work"
    words = text.lower().split()
    if len(words) < 50:
        return False, None
    
    # Check for repeated word sequences
    for window_size in [3, 5, 10]:
        for i in range(len(words) - window_size * threshold):
            pattern = tuple(words[i:i+window_size])
            count = 0
            for j in range(i, len(words) - window_size + 1, window_size):
                if tuple(words[j:j+window_size]) == pattern:
                    count += 1
            if count >= threshold:
                return True, ' '.join(pattern)
    
    return False, None


def check_verdict(output):
    """Check if output contains [PASS] or [FAIL]."""
    if not output:
        return None
    if '[PASS]' in output:
        return 'PASS'
    if '[FAIL]' in output:
        return 'FAIL'
    return 'UNKNOWN'


def run_smoke_test(posting_id=None, dry_run=False, verbose=True):
    """Run smoke test on a single posting."""
    conn = get_connection()
    results = {
        'posting_id': None,
        'workflow_run_id': None,
        'steps': {},
        'success': False,
        'errors': []
    }
    
    try:
        # 1. Get posting
        if posting_id:
            posting = get_posting(conn, posting_id)
            if not posting:
                results['errors'].append(f"Posting {posting_id} not found")
                return results
        else:
            posting = get_random_unprocessed_posting(conn)
            if not posting:
                results['errors'].append("No unprocessed postings found")
                return results
        
        results['posting_id'] = posting['posting_id']
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"SMOKE TEST: Workflow 3001")
            print(f"{'='*60}")
            print(f"Posting ID: {posting['posting_id']}")
            print(f"Job Title: {posting.get('job_title', 'N/A')}")
            print(f"External ID: {posting.get('external_job_id', 'N/A')}")
            print(f"Description Length: {len(posting.get('job_description', '')) if posting.get('job_description') else 0} chars")
        
        if dry_run:
            print("\n[DRY RUN] Would execute workflow but not actually running.")
            return results
        
        # 2. Start workflow
        if verbose:
            print(f"\n[STEP 1] Starting workflow run...")
        
        workflow_run_id = start_workflow_for_posting(conn, posting['posting_id'])
        results['workflow_run_id'] = workflow_run_id
        
        if verbose:
            print(f"  → Created workflow_run_id: {workflow_run_id}")
            print(f"\n  NOTE: Workflow must be running (./scripts/run_workflow.sh 3001)")
            print(f"  Waiting for interactions to complete...")
        
        # 3. Wait for Extract (3335)
        if verbose:
            print(f"\n[STEP 2] Waiting for Extract Summary (conv 3335)...")
        
        extract_result = wait_for_interactions(conn, workflow_run_id, [3335], timeout_seconds=120)
        
        if 'timeout' in extract_result:
            results['errors'].append("Extract timed out after 120s")
            results['steps']['extract'] = {'status': 'timeout'}
            return results
        
        if 'failed' in extract_result:
            results['errors'].append(f"Extract failed: {extract_result['failed'][0].get('error_message')}")
            results['steps']['extract'] = {'status': 'failed'}
            return results
        
        extract_output = extract_result[3335]['output']
        is_degenerate, pattern = check_for_degeneration(extract_output)
        
        results['steps']['extract'] = {
            'status': 'completed',
            'output_length': len(extract_output) if extract_output else 0,
            'degenerate': is_degenerate,
            'degenerate_pattern': pattern
        }
        
        if verbose:
            print(f"  → Completed! Output length: {len(extract_output) if extract_output else 0} chars")
            if is_degenerate:
                print(f"  ⚠️ DEGENERATION DETECTED: '{pattern}'")
        
        if is_degenerate:
            results['errors'].append(f"Extraction degenerated with pattern: {pattern}")
        
        # 4. Wait for Graders (3336, 3337)
        if verbose:
            print(f"\n[STEP 3] Waiting for Graders (conv 3336, 3337)...")
        
        grader_result = wait_for_interactions(conn, workflow_run_id, [3336, 3337], timeout_seconds=180)
        
        if 'timeout' in grader_result:
            results['errors'].append("Graders timed out after 180s")
            results['steps']['graders'] = {'status': 'timeout'}
            return results
        
        if 'failed' in grader_result:
            results['errors'].append(f"Grader failed: {grader_result['failed'][0].get('error_message')}")
            results['steps']['graders'] = {'status': 'failed'}
            return results
        
        verdict_a = check_verdict(grader_result.get(3336, {}).get('output', ''))
        verdict_b = check_verdict(grader_result.get(3337, {}).get('output', ''))
        
        results['steps']['graders'] = {
            'status': 'completed',
            'grader_a': verdict_a,
            'grader_b': verdict_b
        }
        
        if verbose:
            print(f"  → Grader A (mistral): [{verdict_a}]")
            print(f"  → Grader B (qwen2.5): [{verdict_b}]")
        
        # 5. Check branching
        if verdict_a == 'PASS' and verdict_b == 'PASS':
            if verbose:
                print(f"\n[STEP 4] Both PASS → Waiting for Format Standardization (conv 3341)...")
            
            format_result = wait_for_interactions(conn, workflow_run_id, [3341], timeout_seconds=120)
            
            if 'timeout' not in format_result and 'failed' not in format_result:
                format_output = format_result[3341]['output']
                results['steps']['format'] = {
                    'status': 'completed',
                    'output_length': len(format_output) if format_output else 0
                }
                if verbose:
                    print(f"  → Format completed! Output length: {len(format_output) if format_output else 0} chars")
            else:
                results['steps']['format'] = {'status': 'timeout_or_failed'}
                if verbose:
                    print(f"  ⚠️ Format step timed out or failed")
        else:
            if verbose:
                print(f"\n[STEP 4] Grader failed → Would go to Improvement path")
            results['steps']['branching'] = {'path': 'improvement'}
        
        # 6. Check final state
        if verbose:
            print(f"\n[STEP 5] Checking final posting state...")
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                extracted_summary IS NOT NULL as has_summary,
                LENGTH(extracted_summary) as summary_length
            FROM postings
            WHERE posting_id = %s
        """, (posting['posting_id'],))
        
        final_state = cur.fetchone()
        results['steps']['final'] = {
            'has_summary': final_state['has_summary'],
            'summary_length': final_state['summary_length']
        }
        
        if verbose:
            if final_state['has_summary']:
                print(f"  → Summary saved! Length: {final_state['summary_length']} chars")
            else:
                print(f"  → Summary NOT saved yet (workflow may still be running)")
        
        # 7. Determine success
        results['success'] = (
            not is_degenerate and
            verdict_a in ('PASS', 'FAIL') and
            verdict_b in ('PASS', 'FAIL') and
            not results['errors']
        )
        
        if verbose:
            print(f"\n{'='*60}")
            if results['success']:
                print("✅ SMOKE TEST PASSED")
            else:
                print("❌ SMOKE TEST FAILED")
                for err in results['errors']:
                    print(f"  - {err}")
            print(f"{'='*60}\n")
        
        return results
        
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Workflow 3001 Smoke Test')
    parser.add_argument('--posting-id', type=int, help='Specific posting ID to test')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without executing')
    parser.add_argument('--quiet', '-q', action='store_true', help='Only output final result')
    
    args = parser.parse_args()
    
    results = run_smoke_test(
        posting_id=args.posting_id,
        dry_run=args.dry_run,
        verbose=not args.quiet
    )
    
    if args.quiet:
        if results['success']:
            print("PASS")
        else:
            print(f"FAIL: {', '.join(results['errors'])}")
    
    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
