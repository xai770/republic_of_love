#!/usr/bin/env python3
"""
Reprocess Postings - Trigger workflow for specific postings at specific step
============================================================================

Usage:
    # Reprocess 239 postings from extraction step
    python tools/admin/reprocess_postings.py --workflow 3001 --conversation 3335 --query "phi4_garbage"
    
    # Reprocess single posting
    python tools/admin/reprocess_postings.py --workflow 3001 --conversation 3335 --posting-ids 10529,10530
    
    # Dry run - show what would be created
    python tools/admin/reprocess_postings.py --workflow 3001 --conversation 3335 --query "phi4_garbage" --dry-run

Named queries:
    phi4_garbage: 239 postings with garbage phi4-mini extracts
    missing_summary: Postings with NULL extracted_summary
    
Author: Arden
Date: 2025-12-09
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
import psycopg2.extras
from core.wave_runner.workflow_starter import start_workflow

# Named queries for common reprocessing scenarios
NAMED_QUERIES = {
    'phi4_garbage': """
        SELECT DISTINCT p.posting_id
        FROM postings p
        JOIN interactions i ON i.posting_id = p.posting_id
        WHERE i.conversation_id = 3335 
          AND i.status = 'completed'
          AND i.output->>'model' = 'phi4-mini:latest'
          AND i.output->>'response' NOT LIKE '%**Role:**%' 
          AND i.output->>'response' NOT LIKE '%Role:%'
        ORDER BY p.posting_id
    """,
    'missing_summary': """
        SELECT posting_id FROM postings 
        WHERE extracted_summary IS NULL
        ORDER BY posting_id
    """,
    'all_postings': """
        SELECT posting_id FROM postings ORDER BY posting_id
    """,
}

# Conversation names for user-friendly display
CONVERSATION_NAMES = {
    3335: 'session_a_qwen25_extract (Extract summary)',
    3337: 'session_c_qwen25_grade (Grade summary)',
    3341: 'format_standardization (Format output)',
    9144: 'Fetch Jobs from API',
    9193: 'Validate Job Description',
}


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', ''),
        host='localhost'
    )


def get_posting_ids(conn, query_name=None, posting_ids=None):
    """Get posting IDs from named query or explicit list."""
    if posting_ids:
        return posting_ids
    
    if query_name not in NAMED_QUERIES:
        print(f"Unknown query: {query_name}")
        print(f"Available queries: {', '.join(NAMED_QUERIES.keys())}")
        sys.exit(1)
    
    cursor = conn.cursor()
    cursor.execute(NAMED_QUERIES[query_name])
    return [row[0] for row in cursor.fetchall()]


def mark_old_interactions_stale(conn, posting_ids, start_conversation_id):
    """
    Mark existing interactions as 'stale' from the start conversation onwards.
    This includes the start conversation AND all downstream conversations.
    
    For WF3001 starting at 3335 (extract), this marks:
    - 3335 (gemma3_extract)
    - 3336 (mistral_grade)
    - 3337 (qwen25_grade) 
    - 3338 (qwen25_improve)
    - 3339 (qwen25_regrade)
    - 3341 (format_standardization)
    - 9168 (save_summary)
    """
    # Conversation chains for WF3001
    # Starting from extract, all downstream need to be stale
    # NOTE: 9168 is Save Summary - must be included or it will skip on staleness check
    DOWNSTREAM_CHAINS = {
        3335: [3335, 3336, 3337, 3338, 3339, 3341, 9168],  # extract → all grading → format → save
        3337: [3337, 3338, 3339, 3341, 9168],  # grade → improve → regrade → format → save
        3341: [3341, 9168],  # format → save
        9168: [9168],  # just save
    }
    
    conversations_to_stale = DOWNSTREAM_CHAINS.get(start_conversation_id, [start_conversation_id])
    
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE interactions
        SET status = 'invalidated', updated_at = NOW()
        WHERE posting_id = ANY(%s)
          AND conversation_id = ANY(%s)
          AND status IN ('completed', 'pending', 'failed')
    """, (posting_ids, conversations_to_stale))
    
    return cursor.rowcount


def create_reprocess_interactions(conn, workflow_id, conversation_id, posting_ids, dry_run=False):
    """
    Create new interactions for reprocessing.
    Uses start_workflow to properly initialize.
    """
    results = {
        'created': 0,
        'skipped': 0,
        'errors': []
    }
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    for posting_id in posting_ids:
        try:
            if dry_run:
                results['created'] += 1
                continue
            
            # Use start_workflow with custom start_conversation_id
            result = start_workflow(
                db_conn=conn,
                workflow_id=workflow_id,
                posting_id=posting_id,
                start_conversation_id=conversation_id
            )
            
            results['created'] += 1
            
        except Exception as e:
            results['errors'].append({
                'posting_id': posting_id,
                'error': str(e)
            })
    
    if not dry_run:
        conn.commit()
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Reprocess postings through workflow')
    parser.add_argument('--workflow', type=int, required=True, help='Workflow ID (e.g., 3001)')
    parser.add_argument('--conversation', type=int, required=True, help='Starting conversation ID')
    parser.add_argument('--query', type=str, help='Named query for posting IDs')
    parser.add_argument('--posting-ids', type=str, help='Comma-separated posting IDs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--mark-stale', action='store_true', help='Mark old interactions as stale first')
    
    args = parser.parse_args()
    
    # Parse posting IDs if provided
    explicit_ids = None
    if args.posting_ids:
        explicit_ids = [int(x.strip()) for x in args.posting_ids.split(',')]
    
    if not args.query and not explicit_ids:
        print("Error: Must provide --query or --posting-ids")
        sys.exit(1)
    
    conn = get_db_connection()
    
    # Get posting IDs
    posting_ids = get_posting_ids(conn, args.query, explicit_ids)
    
    conv_name = CONVERSATION_NAMES.get(args.conversation, f'Conversation {args.conversation}')
    
    print(f"\n{'=' * 60}")
    print(f"REPROCESS POSTINGS")
    print(f"{'=' * 60}")
    print(f"Workflow:     {args.workflow}")
    print(f"Start at:     {conv_name}")
    print(f"Postings:     {len(posting_ids)}")
    print(f"Mode:         {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print(f"{'=' * 60}\n")
    
    if len(posting_ids) == 0:
        print("No postings to process.")
        return
    
    # Show sample
    print(f"Sample posting IDs: {posting_ids[:5]}{'...' if len(posting_ids) > 5 else ''}")
    print()
    
    # Optional: Mark old interactions as stale
    if args.mark_stale and not args.dry_run:
        stale_count = mark_old_interactions_stale(conn, posting_ids, args.conversation)
        print(f"Marked {stale_count} old interactions as 'stale'")
        conn.commit()
    
    # Create new interactions
    print("Creating workflow runs and seed interactions...")
    results = create_reprocess_interactions(
        conn, 
        args.workflow, 
        args.conversation, 
        posting_ids,
        args.dry_run
    )
    
    print(f"\nResults:")
    print(f"  Created:  {results['created']}")
    print(f"  Skipped:  {results['skipped']}")
    print(f"  Errors:   {len(results['errors'])}")
    
    if results['errors']:
        print(f"\nFirst 5 errors:")
        for err in results['errors'][:5]:
            print(f"  - Posting {err['posting_id']}: {err['error']}")
    
    if args.dry_run:
        print(f"\n⚠️  DRY RUN - No changes made. Remove --dry-run to execute.")
    else:
        print(f"\n✓ Done! Run wave_runner to process the new interactions.")
        print(f"  cd /home/xai/Documents/ty_wave && python run_workflow_3001.py")
    
    conn.close()


if __name__ == '__main__':
    main()
