#!/usr/bin/env python3
"""
Run Posting Validator - Check active postings for removed jobs.

This script validates active postings by checking if their URLs are still live.
Any posting that returns 404 or redirects to an error page is marked as invalidated.

All changes are recorded in the interactions table for full audit trail.

Usage:
    # Full validation (all active postings)
    python scripts/run_posting_validator.py
    
    # Dry run (check but don't update)
    python scripts/run_posting_validator.py --dry-run
    
    # Limit for testing
    python scripts/run_posting_validator.py --limit 10 --dry-run
"""

import sys
import os
import argparse
from datetime import datetime

# Setup paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='Validate active postings')
    parser.add_argument('--dry-run', action='store_true', help='Check URLs but do not update database')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of postings to check')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    args = parser.parse_args()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025')
    )
    conn.autocommit = False
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print(f"\n{'='*70}")
    print(f"POSTING VALIDATOR")
    print(f"{'='*70}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry run: {args.dry_run}")
    print(f"Limit: {args.limit or 'all'}")
    print(f"{'='*70}\n")
    
    # Create workflow run for audit trail
    cursor.execute("""
        INSERT INTO workflow_runs (workflow_id, status, environment)
        VALUES (3001, 'running', 'production')
        RETURNING workflow_run_id
    """)
    workflow_run_id = cursor.fetchone()['workflow_run_id']
    
    # Get conversation and actor IDs
    cursor.execute("""
        SELECT c.conversation_id, c.actor_id
        FROM conversations c
        WHERE c.canonical_name = 'validate_postings'
    """)
    conv = cursor.fetchone()
    if not conv:
        print("ERROR: validate_postings conversation not found!")
        conn.rollback()
        return
    
    conversation_id = conv['conversation_id']
    actor_id = conv['actor_id']
    
    # Create the interaction
    config = {
        'limit': args.limit,
        'dry_run': args.dry_run,
        'delay': args.delay
    }
    
    cursor.execute("""
        INSERT INTO interactions (
            conversation_id, workflow_run_id, actor_id, actor_type,
            status, execution_order, input, created_at
        )
        VALUES (%s, %s, %s, 'script', 'running', 1, %s, CURRENT_TIMESTAMP)
        RETURNING interaction_id
    """, (conversation_id, workflow_run_id, actor_id, psycopg2.extras.Json({'config': config})))
    interaction_id = cursor.fetchone()['interaction_id']
    conn.commit()
    
    print(f"📋 Created interaction {interaction_id} (workflow_run {workflow_run_id})")
    
    # Run the actor via subprocess to match how wave_runner does it
    import subprocess
    import json
    
    input_data = {
        'workflow_run_id': workflow_run_id,
        'interaction_id': interaction_id,
        'config': config
    }
    
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(project_root, 'core/wave_runner/actors/posting_validator.py')],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            
            # Update interaction with result
            cursor.execute("""
                UPDATE interactions
                SET status = 'completed',
                    output = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE interaction_id = %s
            """, (psycopg2.extras.Json(output), interaction_id))
            
            # Update workflow run
            cursor.execute("""
                UPDATE workflow_runs
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE workflow_run_id = %s
            """, (workflow_run_id,))
            
            conn.commit()
            
            # Display results
            data = output.get('data', {})
            print(f"\n{'='*70}")
            print(f"RESULTS")
            print(f"{'='*70}")
            print(f"Total checked:  {data.get('total_checked', 0)}")
            print(f"Still live:     {data.get('still_live', 0)}")
            print(f"Removed:        {data.get('removed_count', 0)}")
            print(f"Errors:         {data.get('errors', 0)}")
            
            if data.get('removed_postings'):
                print(f"\nRemoved postings:")
                for p in data['removed_postings'][:20]:
                    print(f"  - {p['posting_id']}: {p.get('job_title', 'N/A')[:50]} ({p['reason']})")
            
            if data.get('dry_run'):
                print(f"\n[DRY RUN] Would invalidate {data.get('removed_count', 0)} postings")
            else:
                print(f"\n✅ Invalidated {data.get('invalidated', 0)} postings")
                
        else:
            error_output = json.loads(result.stdout) if result.stdout else {'error': result.stderr}
            cursor.execute("""
                UPDATE interactions
                SET status = 'failed',
                    output = %s,
                    error_message = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE interaction_id = %s
            """, (psycopg2.extras.Json(error_output), error_output.get('error', 'Unknown error'), interaction_id))
            
            cursor.execute("""
                UPDATE workflow_runs
                SET status = 'failed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE workflow_run_id = %s
            """, (workflow_run_id,))
            conn.commit()
            
            print(f"\n❌ Validation failed: {error_output.get('error', 'Unknown error')}")
            
    except subprocess.TimeoutExpired:
        cursor.execute("""
            UPDATE interactions
            SET status = 'failed',
                error_message = 'Timeout after 3600 seconds',
                completed_at = CURRENT_TIMESTAMP
            WHERE interaction_id = %s
        """, (interaction_id,))
        cursor.execute("""
            UPDATE workflow_runs
            SET status = 'failed',
            WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        conn.commit()
        print(f"\n❌ Validation timed out")
    
    print(f"\n{'='*70}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interaction: {interaction_id}")
    print(f"{'='*70}\n")
    
    conn.close()


if __name__ == '__main__':
    main()
