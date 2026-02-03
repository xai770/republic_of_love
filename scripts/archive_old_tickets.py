#!/usr/bin/env python3
"""
archive_old_tickets.py - Move tickets older than 1 month to archive

Policy: Tickets older than 1 month go to _archive_tickets_history
Rationale: Keep Turing lean; archived data is in the basement if needed

Usage:
    ./scripts/archive_old_tickets.py           # Dry run
    ./scripts/archive_old_tickets.py --execute # Actually archive

Author: Sandy
Date: 2026-01-28
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw as get_connection


def archive_tickets(execute: bool = False, age_days: int = 30):
    """Archive old tickets."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Count what would be archived
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'skipped') as skipped
        FROM tickets
        WHERE created_at < NOW() - INTERVAL '%s days'
          AND status IN ('completed', 'failed', 'skipped')
    """, (age_days,))
    
    row = cur.fetchone()
    total = int(row['total'])
    completed = int(row['completed'])
    failed = int(row['failed'])
    skipped = int(row['skipped'])
    
    print(f"Tickets older than {age_days} days:")
    print(f"  Completed: {completed:,}")
    print(f"  Failed:    {failed:,}")
    print(f"  Skipped:   {skipped:,}")
    print(f"  TOTAL:     {total:,}")
    print()
    
    if not execute:
        print("DRY RUN - No changes made. Use --execute to archive.")
        conn.close()
        return
    
    print("Archiving...")
    print("  (INSERT + DELETE in single transaction - atomic or nothing)")
    
    try:
        # Start explicit transaction
        cur.execute("BEGIN")
        
        # Insert into archive (map tickets columns to archive columns)
        cur.execute("""
            INSERT INTO _archive_tickets_history (
                task_log_id, posting_id, task_type_id, workflow_run_id,
                actor_id, actor_type, status, execution_order,
                parent_task_log_id, trigger_task_log_id, input_task_log_ids,
                input, output, error_message, retry_count, max_retries,
                enabled, invalidated, created_at, updated_at, started_at, completed_at,
                archive_reason
            )
            SELECT 
                t.ticket_id,
                t.subject_id,           -- posting_id = subject_id
                t.actor_id,             -- task_type_id = actor_id (close enough)
                t.batch_id,             -- workflow_run_id = batch_id
                t.actor_id,
                t.actor_type,
                t.status,
                t.execution_order,
                t.parent_ticket_id,
                NULL,                   -- no trigger_ticket_id in tickets
                t.input_ticket_ids,
                t.input,
                t.output,
                t.error_message,
                t.retry_count,
                t.max_retries,
                t.enabled,
                t.invalidated,
                t.created_at,
                t.updated_at,
                t.started_at,
                t.completed_at,
                'age > %s days'
            FROM tickets t
            WHERE t.created_at < NOW() - INTERVAL '%s days'
              AND t.status IN ('completed', 'failed', 'skipped')
        """, (age_days, age_days))
        
        archived = cur.rowcount
        print(f"  Inserted {archived:,} rows into archive")
        
        # Delete from tickets
        print(f"  Deleting from tickets (this may take a while)...")
        cur.execute("""
            DELETE FROM tickets
            WHERE created_at < NOW() - INTERVAL '%s days'
              AND status IN ('completed', 'failed', 'skipped')
        """, (age_days,))
        
        deleted = cur.rowcount
        print(f"  Deleted {deleted:,} rows from tickets")
        
        # Commit both operations together
        conn.commit()
        print("  Transaction committed.")
        
    except KeyboardInterrupt:
        print("\n  INTERRUPTED - Rolling back...")
        conn.rollback()
        print("  Rollback complete. No data lost.")
        conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Rolling back...")
        conn.rollback()
        print("  Rollback complete. No data lost.")
        conn.close()
        raise
    
    # Show new counts
    cur.execute("SELECT COUNT(*) FROM tickets")
    remaining = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM _archive_tickets_history")
    total_archived = cur.fetchone()[0]
    
    print()
    print(f"Done!")
    print(f"  Tickets remaining: {remaining:,}")
    print(f"  Total in archive:  {total_archived:,}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Archive old tickets")
    parser.add_argument('--execute', action='store_true', 
                       help='Actually archive (default is dry run)')
    parser.add_argument('--days', type=int, default=30,
                       help='Archive tickets older than N days (default: 30)')
    args = parser.parse_args()
    
    archive_tickets(execute=args.execute, age_days=args.days)


if __name__ == '__main__':
    main()
