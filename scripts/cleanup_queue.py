#!/usr/bin/env python3
"""
Queue Cleanup - Remove stale entries where work is already done.

Usage:
    python scripts/cleanup_queue.py --dry-run   # Preview what will be deleted
    python scripts/cleanup_queue.py             # Actually delete stale entries
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

import psycopg2


def get_stale_entries(conn):
    """Find queue entries where the work is already done."""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            q.queue_id, 
            q.posting_id, 
            q.start_step, 
            q.status,
            q.created_at,
            CASE 
                WHEN q.start_step = 'skills_extraction' THEN 'skill_keywords already set'
                WHEN q.start_step = 'ihl_analyst' THEN 'ihl_score already set'
                WHEN q.start_step = 'extract_summary' THEN 'extracted_summary already set'
            END as reason
        FROM queue q
        JOIN postings p ON q.posting_id = p.posting_id
        WHERE 
            (q.start_step = 'skills_extraction' AND p.skill_keywords IS NOT NULL) OR
            (q.start_step = 'ihl_analyst' AND p.ihl_score IS NOT NULL) OR
            (q.start_step = 'extract_summary' AND p.extracted_summary IS NOT NULL)
        ORDER BY q.start_step, q.created_at
    """)
    return cur.fetchall()


def delete_stale_entries(conn, dry_run=True):
    """Delete stale queue entries."""
    stale = get_stale_entries(conn)
    
    if not stale:
        print("✓ No stale queue entries found")
        return 0
    
    # Group by step
    by_step = {}
    for qid, pid, step, status, created, reason in stale:
        by_step.setdefault(step, []).append((qid, pid, status, created))
    
    print(f"\nFound {len(stale)} stale queue entries:\n")
    for step, entries in sorted(by_step.items()):
        oldest = min(e[3] for e in entries)
        newest = max(e[3] for e in entries)
        statuses = set(e[2] for e in entries)
        print(f"  {step}: {len(entries)} entries")
        print(f"    statuses: {', '.join(statuses)}")
        print(f"    oldest: {oldest}")
        print(f"    newest: {newest}")
    
    print()
    
    if dry_run:
        print("🔍 DRY RUN - no changes made")
        print("   Run without --dry-run to delete these entries")
        return len(stale)
    
    # Actually delete
    cur = conn.cursor()
    queue_ids = [row[0] for row in stale]
    cur.execute("DELETE FROM queue WHERE queue_id = ANY(%s)", (queue_ids,))
    deleted = cur.rowcount
    conn.commit()
    
    print(f"✓ Deleted {deleted} stale queue entries")
    return deleted


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up stale queue entries')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Preview only, do not delete')
    args = parser.parse_args()
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    
    try:
        delete_stale_entries(conn, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
