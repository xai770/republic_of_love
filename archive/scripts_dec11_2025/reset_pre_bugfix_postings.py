#!/usr/bin/env python3
"""
Reset postings that were processed before the TEMPLATE_SUBSTITUTION_BUG fix.

This script:
1. Deletes checkpoints for postings processed before Nov 17 05:48:34
2. Sets extracted_summary to NULL for those postings
3. Reports what was cleaned up

Run this before restarting workflow 3001 to reprocess with the fixed template system.
"""

import sys
import psycopg2
from datetime import datetime

# Bug fix timestamp
BUG_FIX_TIME = '2025-11-17 05:48:34'


def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        dbname="turing",
        user="base_admin",
        password="base_yoga_secure_2025",
        host="localhost",
        port=5432
    )


def reset_postings(dry_run=True):
    """Reset postings processed before bug fix"""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get affected postings
    cur.execute('''
        SELECT posting_id, job_title, updated_at, LENGTH(extracted_summary) as summary_len
        FROM postings
        WHERE extracted_summary IS NOT NULL
          AND updated_at < %s
        ORDER BY posting_id
    ''', (BUG_FIX_TIME,))
    
    affected_postings = cur.fetchall()
    
    if not affected_postings:
        print("✅ No postings need reset - all were processed after the bug fix!")
        conn.close()
        return 0
    
    print(f"Found {len(affected_postings)} postings processed before bug fix ({BUG_FIX_TIME})")
    print()
    
    # Show sample
    print("Sample of affected postings:")
    print("=" * 80)
    for posting_id, title, updated_at, summary_len in affected_postings[:10]:
        print(f"  {posting_id:5d} | {updated_at} | {summary_len:6,} chars | {title[:50]}...")
    
    if len(affected_postings) > 10:
        print(f"  ... and {len(affected_postings) - 10} more")
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - showing what would be deleted:")
        print()
        
        # Count checkpoints that would be deleted
        posting_ids = [p[0] for p in affected_postings]
        cur.execute('''
            SELECT COUNT(*)
            FROM posting_state_checkpoints
            WHERE posting_id = ANY(%s)
        ''', (posting_ids,))
        
        checkpoint_count = cur.fetchone()[0]
        print(f"  - Would delete {checkpoint_count:,} checkpoints")
        print(f"  - Would nullify {len(affected_postings)} extracted_summary fields")
        print()
        print("Run with --execute flag to perform the reset.")
        
    else:
        print("⚠️  EXECUTING RESET...")
        print()
        
        # Delete checkpoints
        posting_ids = [p[0] for p in affected_postings]
        cur.execute('''
            DELETE FROM posting_state_checkpoints
            WHERE posting_id = ANY(%s)
        ''', (posting_ids,))
        
        checkpoint_count = cur.rowcount
        print(f"  ✅ Deleted {checkpoint_count:,} checkpoints")
        
        # Nullify extracted_summary
        cur.execute('''
            UPDATE postings
            SET extracted_summary = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE posting_id = ANY(%s)
        ''', (posting_ids,))
        
        updated_count = cur.rowcount
        print(f"  ✅ Nullified {updated_count} extracted_summary fields")
        
        # Commit changes
        conn.commit()
        print()
        print(f"✅ Reset complete! {len(affected_postings)} postings ready for reprocessing.")
    
    conn.close()
    return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset postings processed before bug fix')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually perform the reset (default is dry-run)')
    
    args = parser.parse_args()
    
    if args.execute:
        response = input("⚠️  This will delete checkpoints and nullify summaries. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return 1
    
    return reset_postings(dry_run=not args.execute)


if __name__ == '__main__':
    sys.exit(main())
