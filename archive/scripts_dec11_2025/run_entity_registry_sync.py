#!/usr/bin/env python3
"""
Entity Registry Sync - Run WF3005 after WF3001 completes

This script:
1. Checks if any WF3001 runs are still in-progress
2. If WF3001 is done AND pending skills exist → runs WF3005
3. After WF3005 → runs backfill for entity_id

Usage:
    python scripts/run_entity_registry_sync.py              # Auto-detect and run
    python scripts/run_entity_registry_sync.py --force      # Run WF3005 even if WF3001 running
    python scripts/run_entity_registry_sync.py --check-only # Just check status

Safe to run via cron after WF3001 batch:
    30 6 * * * cd /home/xai/Documents/ty_learn && python scripts/run_entity_registry_sync.py >> logs/entity_sync.log 2>&1

Author: Arden
Date: December 8, 2025
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.database import get_connection


def check_wf3001_status(conn):
    """Check if any WF3001 runs are in-progress."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as cnt 
        FROM workflow_runs 
        WHERE workflow_id = 3001 
        AND status IN ('running', 'pending', 'in_progress')
    """)
    in_progress = cur.fetchone()['cnt']
    cur.close()
    return in_progress


def check_pending_skills(conn):
    """Check how many skills are pending for WF3005."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM entities_pending WHERE status = 'pending'")
    pending = cur.fetchone()['cnt']
    cur.close()
    return pending


def run_wf3005(runs=1):
    """Run WF3005 to process pending skills."""
    print(f"[{datetime.now()}] Running WF3005 ({runs} run(s))...")
    
    result = subprocess.run(
        [sys.executable, 'scripts/run_wf3005.py', '--runs', str(runs)],
        cwd='/home/xai/Documents/ty_learn',
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"[{datetime.now()}] WF3005 completed successfully")
        return True
    else:
        print(f"[{datetime.now()}] WF3005 failed: {result.stderr}")
        return False


def run_backfill(conn):
    """Backfill entity_id for posting_skills with new aliases."""
    cur = conn.cursor()
    
    cur.execute("""
        WITH candidates AS (
            SELECT ps.posting_skill_id, ea.entity_id as new_entity_id, ps.posting_id
            FROM posting_skills ps
            JOIN entity_aliases ea ON LOWER(ps.raw_skill_name) = LOWER(ea.alias)
            WHERE ps.entity_id IS NULL
            AND ea.deleted_at IS NULL
        )
        UPDATE posting_skills ps
        SET entity_id = c.new_entity_id
        FROM candidates c
        WHERE ps.posting_skill_id = c.posting_skill_id
        AND NOT EXISTS (
            SELECT 1 FROM posting_skills ps2 
            WHERE ps2.posting_id = c.posting_id 
            AND ps2.entity_id = c.new_entity_id
        )
    """)
    
    updated = cur.rowcount
    conn.commit()
    cur.close()
    
    print(f"[{datetime.now()}] Backfill: updated {updated} posting_skills rows")
    return updated


def main():
    parser = argparse.ArgumentParser(description='Entity Registry Sync')
    parser.add_argument('--force', action='store_true', help='Run even if WF3001 is in-progress')
    parser.add_argument('--check-only', action='store_true', help='Just check status, do not run')
    parser.add_argument('--runs', type=int, default=5, help='Number of WF3005 runs (default: 5)')
    
    args = parser.parse_args()
    
    conn = get_connection()
    
    try:
        # Check status
        wf3001_running = check_wf3001_status(conn)
        pending_skills = check_pending_skills(conn)
        
        print(f"[{datetime.now()}] Status Check:")
        print(f"  WF3001 in-progress: {wf3001_running}")
        print(f"  Pending skills: {pending_skills}")
        
        if args.check_only:
            return
        
        # Safety check
        if wf3001_running > 0 and not args.force:
            print(f"[{datetime.now()}] ⚠️  WF3001 still running ({wf3001_running} runs). Use --force to override.")
            return
        
        # Run WF3005 if pending skills exist
        if pending_skills > 0:
            success = run_wf3005(runs=args.runs)
            if success:
                run_backfill(conn)
        else:
            print(f"[{datetime.now()}] ✅ No pending skills. Nothing to do.")
        
        # Final status
        remaining = check_pending_skills(conn)
        print(f"[{datetime.now()}] Final pending skills: {remaining}")
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
