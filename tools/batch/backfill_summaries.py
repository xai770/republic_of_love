#!/usr/bin/env python3
"""
Backfill Summaries from LLM Interactions
=========================================
Extract the formatted summaries from Step 9 (Format Standardization) outputs
that are already in llm_interactions table and save them to postings.

This avoids re-running the entire extraction pipeline when we already have
the summaries - we just need to save them to the right place.

Author: xai & Arden
Date: 2025-11-14
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection, return_connection
from psycopg2.extras import RealDictCursor


def backfill_summaries():
    """
    Extract formatted summaries from llm_interactions and save to postings table
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find all Format Standardization outputs (Step 9, conversation_id=3341)
    # that have status='SUCCESS' and corresponding postings with NULL extracted_summary
    
    print("Finding summaries to backfill...")
    cur.execute('''
        SELECT 
            psc.posting_id,
            li.response_received as formatted_summary,
            li.started_at
        FROM posting_state_checkpoints psc
        JOIN llm_interactions li ON li.workflow_run_id = psc.workflow_run_id
        JOIN conversation_runs cr ON li.conversation_run_id = cr.conversation_run_id
        WHERE psc.conversation_id = 3341  -- Format Standardization
          AND cr.conversation_id = 3341
          AND li.status = 'SUCCESS'
          AND psc.posting_id IN (
              SELECT posting_id 
              FROM postings 
              WHERE extracted_summary IS NULL 
                 OR extracted_summary = '{session_4_output}'
          )
        ORDER BY psc.posting_id
    ''')
    
    summaries = cur.fetchall()
    total = len(summaries)
    
    if total == 0:
        print("✅ No summaries to backfill - all postings already have summaries!")
        return
    
    print(f"Found {total} summaries to backfill")
    print()
    
    # Update postings with the formatted summaries
    updated = 0
    failed = 0
    
    for i, row in enumerate(summaries, 1):
        posting_id = row['posting_id']
        summary = row['formatted_summary']
        
        if not summary or summary.strip() == '':
            print(f"⚠️  [{i}/{total}] Posting {posting_id}: Empty summary, skipping")
            failed += 1
            continue
        
        try:
            cur.execute('''
                UPDATE postings
                SET extracted_summary = %s,
                    summary_extracted_at = %s,
                    summary_extraction_status = 'completed'
                WHERE posting_id = %s
            ''', (summary, row['started_at'], posting_id))
            
            updated += 1
            
            if i % 100 == 0:
                conn.commit()
                print(f"✅ [{i}/{total}] Processed {i} postings...")
        
        except Exception as e:
            print(f"❌ [{i}/{total}] Posting {posting_id}: Error - {e}")
            failed += 1
    
    conn.commit()
    return_connection(conn)
    
    print()
    print("=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"Total summaries found: {total}")
    print(f"Successfully updated: {updated}")
    print(f"Failed/Skipped: {failed}")
    print()
    
    if updated > 0:
        print(f"✅ {updated} postings now have extracted summaries!")


if __name__ == '__main__':
    backfill_summaries()
