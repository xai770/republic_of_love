#!/usr/bin/env python3
"""
Watchdog: Cleanup Stuck Interactions
====================================

Automatically marks interactions as 'failed' if they've been in 'running' 
state for longer than the configured timeout.

This prevents stuck interactions from blocking workflow progression when:
- Runner process crashes or is killed
- System runs out of memory (OOM killer)
- Ollama/model processes crash
- User interrupts with Ctrl+C
- Network issues cause indefinite hangs

Run via cron:
    */5 * * * * cd /home/xai/Documents/ty_wave && python3 scripts/watchdog_cleanup.py >> logs/watchdog.log 2>&1

Author: Sandy
Date: November 26, 2025
"""

import sys
import psycopg2
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection


# Configuration
MAX_INTERACTION_RUNTIME_MINUTES = 15  # 3x the normal 5min timeout
MAX_WORKFLOW_RUNTIME_HOURS = 2        # No workflow should run longer than this
DRY_RUN = False  # Set to True to see what would be cleaned without actually doing it


def cleanup_stuck_interactions(conn, dry_run=False):
    """
    Mark interactions stuck in 'running' state as failed.
    
    Returns:
        Number of interactions cleaned up
    """
    cursor = conn.cursor()
    
    # Find stuck interactions
    cursor.execute(f"""
        SELECT 
            interaction_id,
            conversation_id,
            actor_id,
            EXTRACT(EPOCH FROM (NOW() - started_at))::int as stuck_seconds
        FROM interactions
        WHERE status = 'running'
          AND started_at < NOW() - interval '{MAX_INTERACTION_RUNTIME_MINUTES} minutes'
        ORDER BY started_at;
    """)
    
    stuck = cursor.fetchall()
    
    if not stuck:
        print(f"[{datetime.now()}] ✅ No stuck interactions found")
        return 0
    
    print(f"[{datetime.now()}] ⚠️  Found {len(stuck)} stuck interactions:")
    for row in stuck:
        # Note: get_connection() returns RealDictCursor, so row is a dict not tuple
        interaction_id = row['interaction_id']
        seconds = row['stuck_seconds']
        minutes = seconds / 60
        print(f"  - Interaction {interaction_id}: stuck for {minutes:.1f} minutes")
    
    if dry_run:
        print(f"[{datetime.now()}] 🔍 DRY RUN - Would mark {len(stuck)} as failed (not actually doing it)")
        return 0
    
    # Mark them as failed
    cursor.execute(f"""
        UPDATE interactions
        SET 
            status = 'failed',
            completed_at = NOW(),
            output = jsonb_set(
                COALESCE(output, '{{}}'::jsonb),
                '{{error}}',
                '"Auto-failed by watchdog: exceeded max runtime of {MAX_INTERACTION_RUNTIME_MINUTES} minutes"'::jsonb
            )
        WHERE status = 'running'
          AND started_at < NOW() - interval '{MAX_INTERACTION_RUNTIME_MINUTES} minutes'
        RETURNING interaction_id;
    """)
    
    cleaned = cursor.fetchall()
    conn.commit()
    
    print(f"[{datetime.now()}] ✅ Marked {len(cleaned)} stuck interactions as failed")
    return len(cleaned)


def cleanup_stuck_workflows(conn, dry_run=False):
    """
    Mark workflow runs as 'completed' if they have no running interactions
    but are stuck in 'running' status.
    
    Returns:
        Number of workflow runs cleaned up
    """
    cursor = conn.cursor()
    
    # Find stuck workflow runs
    cursor.execute(f"""
        SELECT 
            wr.workflow_run_id,
            wr.posting_id,
            EXTRACT(EPOCH FROM (NOW() - wr.started_at))::int as stuck_seconds
        FROM workflow_runs wr
        WHERE wr.status = 'running'
          AND wr.started_at < NOW() - interval '{MAX_WORKFLOW_RUNTIME_HOURS} hours'
          AND NOT EXISTS (
              SELECT 1 FROM interactions 
              WHERE workflow_run_id = wr.workflow_run_id 
                AND status = 'running'
          )
        ORDER BY wr.started_at;
    """)
    
    stuck = cursor.fetchall()
    
    if not stuck:
        print(f"[{datetime.now()}] ✅ No stuck workflow runs found")
        return 0
    
    print(f"[{datetime.now()}] ⚠️  Found {len(stuck)} stuck workflow runs:")
    for row in stuck:
        # Note: get_connection() returns RealDictCursor, so row is a dict not tuple
        wf_id = row['workflow_run_id']
        posting_id = row['posting_id']
        seconds = row['stuck_seconds']
        hours = seconds / 3600
        print(f"  - Workflow {wf_id} (posting {posting_id}): stuck for {hours:.1f} hours")
    
    if dry_run:
        print(f"[{datetime.now()}] 🔍 DRY RUN - Would mark {len(stuck)} as completed (not actually doing it)")
        return 0
    
    # Mark them as completed
    cursor.execute(f"""
        UPDATE workflow_runs
        SET 
            status = 'completed',
            completed_at = NOW()
        WHERE status = 'running'
          AND started_at < NOW() - interval '{MAX_WORKFLOW_RUNTIME_HOURS} hours'
          AND NOT EXISTS (
              SELECT 1 FROM interactions 
              WHERE workflow_run_id = workflow_runs.workflow_run_id 
                AND status = 'running'
          )
        RETURNING workflow_run_id;
    """)
    
    cleaned = cursor.fetchall()
    conn.commit()
    
    print(f"[{datetime.now()}] ✅ Marked {len(cleaned)} stuck workflow runs as completed")
    return len(cleaned)


def main():
    """Main watchdog execution"""
    print(f"\n{'='*80}")
    print(f"WATCHDOG CLEANUP - {datetime.now()}")
    print(f"{'='*80}")
    print(f"Configuration:")
    print(f"  - Max interaction runtime: {MAX_INTERACTION_RUNTIME_MINUTES} minutes")
    print(f"  - Max workflow runtime: {MAX_WORKFLOW_RUNTIME_HOURS} hours")
    print(f"  - Dry run: {DRY_RUN}")
    print(f"{'='*80}\n")
    
    try:
        # Connect to database
        conn = get_connection()
        
        # Cleanup stuck interactions first
        interactions_cleaned = cleanup_stuck_interactions(conn, dry_run=DRY_RUN)
        
        # Then cleanup stuck workflows
        workflows_cleaned = cleanup_stuck_workflows(conn, dry_run=DRY_RUN)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"WATCHDOG SUMMARY:")
        print(f"  - Interactions cleaned: {interactions_cleaned}")
        print(f"  - Workflows cleaned: {workflows_cleaned}")
        print(f"  - Total cleaned: {interactions_cleaned + workflows_cleaned}")
        print(f"{'='*80}\n")
        
        conn.close()
        
        # Exit code indicates if cleanup was needed
        return 0 if (interactions_cleaned + workflows_cleaned) == 0 else 1
        
    except Exception as e:
        print(f"[{datetime.now()}] ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
