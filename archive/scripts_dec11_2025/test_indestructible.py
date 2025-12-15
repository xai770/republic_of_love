#!/usr/bin/env python3
"""
Test script for indestructible workflows.

This script:
1. Starts workflow 3001 for a few postings (or fetches new ones)
2. Runs the Wave Runner
3. We can then kill it (Ctrl+C or kill -TERM) to test resume

Usage:
    python3 scripts/test_indestructible.py                    # Use 5 existing postings
    python3 scripts/test_indestructible.py --fetch 5         # Fetch 5 new jobs first
    python3 scripts/test_indestructible.py --posting-ids 4914,4915,4916  # Specific postings

Author: Sandy (GitHub Copilot)
Date: November 30, 2025
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        cursor_factory=RealDictCursor
    )


def find_unprocessed_postings(conn, limit: int = 5):
    """Find postings that haven't completed workflow 3001."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.posting_id, p.job_title
        FROM postings p
        WHERE p.job_description IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM workflow_runs wr 
              WHERE wr.posting_id = p.posting_id 
                AND wr.workflow_id = 3001
                AND wr.status = 'completed'
          )
        ORDER BY p.posting_id DESC
        LIMIT %s
    """, (limit,))
    return cursor.fetchall()


def start_workflows_for_postings(conn, posting_ids: list):
    """Start workflow 3001 for each posting."""
    workflow_run_ids = []
    
    for posting_id in posting_ids:
        print(f"  Starting workflow for posting {posting_id}...")
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=posting_id,
            start_conversation_id=9184,  # Check if Summary Exists (skip fetcher)
        )
        workflow_run_ids.append(result['workflow_run_id'])
        print(f"    → workflow_run_id: {result['workflow_run_id']}")
    
    return workflow_run_ids


def main():
    parser = argparse.ArgumentParser(description='Test indestructible workflows')
    parser.add_argument('--fetch', type=int, help='Fetch N new jobs from API first')
    parser.add_argument('--posting-ids', type=str, help='Comma-separated posting IDs')
    parser.add_argument('--limit', type=int, default=5, help='Number of postings to process')
    parser.add_argument('--max-iterations', type=int, default=100, help='Max runner iterations')
    
    args = parser.parse_args()
    
    conn = get_connection()
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTING INDESTRUCTIBLE WORKFLOWS")
    print(f"{'='*70}")
    print(f"PID: {os.getpid()}")
    print(f"\n💡 To test graceful shutdown, press Ctrl+C or run:")
    print(f"   kill -TERM {os.getpid()}")
    print(f"\n💡 After killing, check status with:")
    print(f"   python3 scripts/resume_workflows.py")
    print(f"{'='*70}\n")
    
    try:
        if args.fetch:
            # Fetch new jobs first
            print(f"📥 Fetching {args.fetch} new jobs from API...")
            result = start_workflow(
                conn,
                workflow_id=3001,
                posting_id=None,
                start_conversation_id=9144,  # Job Fetcher
                params={
                    "max_jobs": args.fetch,
                    "skip_rate_limit": True,
                }
            )
            print(f"   Fetch workflow_run_id: {result['workflow_run_id']}")
            
            # Run fetcher only
            runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
            runner.run(max_iterations=1)
            print(f"   ✅ Jobs fetched!")
            
        # Get posting IDs
        if args.posting_ids:
            posting_ids = [int(x.strip()) for x in args.posting_ids.split(',')]
        else:
            print(f"🔍 Finding {args.limit} unprocessed postings...")
            postings = find_unprocessed_postings(conn, args.limit)
            if not postings:
                print("❌ No unprocessed postings found!")
                return 1
            posting_ids = [p['posting_id'] for p in postings]
            print(f"   Found: {posting_ids}")
        
        # Start workflows
        print(f"\n🚀 Starting workflows for {len(posting_ids)} postings...")
        workflow_run_ids = start_workflows_for_postings(conn, posting_ids)
        
        # Run in global batch mode
        print(f"\n🌊 Running Wave Runner in global batch mode...")
        print(f"   This will process ALL pending interactions across ALL running workflows")
        print(f"   Max iterations: {args.max_iterations}")
        print(f"{'='*70}")
        
        runner = WaveRunner(
            conn, 
            global_batch=True,
            runner_id=f'test_indestructible_{os.getpid()}'
        )
        
        result = runner.run(max_iterations=args.max_iterations)
        
        print(f"\n{'='*70}")
        print(f"✅ WORKFLOW EXECUTION COMPLETED")
        print(f"{'='*70}")
        print(f"   Interactions completed: {result['interactions_completed']}")
        print(f"   Interactions failed: {result['interactions_failed']}")
        print(f"   Iterations: {result['iterations']}")
        print(f"   Duration: {result['duration_ms']/1000:.2f}s")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"⚠️  INTERRUPTED (Ctrl+C)")
        print(f"{'='*70}")
        print(f"The runner should have handled this gracefully.")
        print(f"Check workflow status with:")
        print(f"   python3 scripts/resume_workflows.py")
        return 0
        
    except SystemExit:
        print(f"\n\n{'='*70}")
        print(f"⚠️  SYSTEM EXIT (Signal received)")
        print(f"{'='*70}")
        return 0
        
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
