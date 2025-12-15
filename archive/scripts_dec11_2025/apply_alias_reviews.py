#!/usr/bin/env python3
"""
Apply Entity Alias Reviews (RAQ-Compliant)

This script applies approved QA reviews to entity_aliases.
All changes are:
- Repeatable: Can re-run without side effects
- Auditable: Changes logged in entity_alias_reviews with timestamps
- QA-controlled: Only applies reviewed/approved changes

Usage:
    python3 scripts/apply_alias_reviews.py --list        # Show pending reviews
    python3 scripts/apply_alias_reviews.py --apply       # Apply pending reviews
    python3 scripts/apply_alias_reviews.py --dry-run     # Preview changes

Author: Arden
Date: December 8, 2025
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.database import get_connection


def list_pending_reviews(conn):
    """List all pending (unapplied) reviews."""
    cur = conn.cursor()
    
    cur.execute('''
        SELECT r.review_id, r.alias_id, r.action, r.reason, r.reviewer, r.reviewed_at,
               ea.alias, e.canonical_name
        FROM entity_alias_reviews r
        JOIN entity_aliases ea ON r.alias_id = ea.alias_id
        JOIN entities e ON ea.entity_id = e.entity_id
        WHERE r.applied_at IS NULL
        ORDER BY r.review_id
    ''')
    
    reviews = cur.fetchall()
    
    if not reviews:
        print("No pending reviews.")
        return
    
    print(f"\n📋 Pending Reviews: {len(reviews)}")
    print("=" * 80)
    
    for row in reviews:
        print(f"\n  Review #{row['review_id']}:")
        print(f"    Alias: \"{row['alias']}\" → \"{row['canonical_name']}\"")
        print(f"    Action: {row['action'].upper()}")
        print(f"    Reason: {row['reason']}")
        print(f"    Reviewer: {row['reviewer']} at {row['reviewed_at']}")
    
    cur.close()


def apply_reviews(conn, dry_run=False):
    """Apply all pending reviews."""
    cur = conn.cursor()
    
    cur.execute('''
        SELECT r.review_id, r.alias_id, r.old_entity_id, r.new_entity_id, r.action, r.reason,
               ea.alias, e.canonical_name
        FROM entity_alias_reviews r
        JOIN entity_aliases ea ON r.alias_id = ea.alias_id
        JOIN entities e ON ea.entity_id = e.entity_id
        WHERE r.applied_at IS NULL
        ORDER BY r.review_id
    ''')
    
    reviews = cur.fetchall()
    
    if not reviews:
        print("No pending reviews to apply.")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Applying {len(reviews)} reviews...")
    print("=" * 80)
    
    applied = 0
    for row in reviews:
        review_id = row['review_id']
        alias_id = row['alias_id']
        action = row['action']
        alias = row['alias']
        canonical = row['canonical_name']
        
        print(f"\n  Review #{review_id}: {action.upper()}")
        print(f"    Alias: \"{alias}\" → \"{canonical}\"")
        
        if action == 'reject' or action == 'delete':
            # Soft-delete the bad alias (preserve for audit)
            print(f"    → Soft-deleting alias_id={alias_id}")
            
            if not dry_run:
                # First clear entity_id from posting_skills that used this alias
                cur.execute('''
                    UPDATE posting_skills ps
                    SET entity_id = NULL
                    FROM entity_aliases ea
                    WHERE LOWER(ps.raw_skill_name) = LOWER(ea.alias)
                    AND ea.alias_id = %s
                    AND ps.entity_id = ea.entity_id
                ''', (alias_id,))
                cleared = cur.rowcount
                print(f"    → Cleared {cleared} posting_skills rows")
                
                # Soft-delete the alias (keep for audit trail)
                cur.execute('''
                    UPDATE entity_aliases 
                    SET deleted_at = NOW(), deleted_reason = %s
                    WHERE alias_id = %s
                ''', (row['reason'], alias_id))
                
                # Mark review as applied
                cur.execute('''
                    UPDATE entity_alias_reviews 
                    SET applied_at = NOW(), applied_by = 'apply_alias_reviews'
                    WHERE review_id = %s
                ''', (review_id,))
                
            applied += 1
            
        elif action == 'remap':
            # Remap alias to different entity
            new_entity_id = row['new_entity_id']
            if new_entity_id is None:
                print(f"    ⚠️  Cannot remap: new_entity_id is NULL")
                continue
                
            print(f"    → Remapping alias to entity_id={new_entity_id}")
            
            if not dry_run:
                # Update posting_skills first
                cur.execute('''
                    UPDATE posting_skills ps
                    SET entity_id = %s
                    FROM entity_aliases ea
                    WHERE LOWER(ps.raw_skill_name) = LOWER(ea.alias)
                    AND ea.alias_id = %s
                ''', (new_entity_id, alias_id))
                updated = cur.rowcount
                print(f"    → Updated {updated} posting_skills rows")
                
                # Update the alias
                cur.execute('''
                    UPDATE entity_aliases SET entity_id = %s WHERE alias_id = %s
                ''', (new_entity_id, alias_id))
                
                # Mark review as applied
                cur.execute('''
                    UPDATE entity_alias_reviews 
                    SET applied_at = NOW(), applied_by = 'apply_alias_reviews'
                    WHERE review_id = %s
                ''', (review_id,))
                
            applied += 1
            
        elif action == 'approve':
            # Mark as reviewed and OK, no changes needed
            print(f"    → Approved (no change needed)")
            
            if not dry_run:
                cur.execute('''
                    UPDATE entity_alias_reviews 
                    SET applied_at = NOW(), applied_by = 'apply_alias_reviews'
                    WHERE review_id = %s
                ''', (review_id,))
                
            applied += 1
    
    if not dry_run:
        conn.commit()
        print(f"\n✅ Applied {applied} reviews")
    else:
        print(f"\n📋 Would apply {applied} reviews (dry run, no changes made)")
    
    cur.close()


def main():
    parser = argparse.ArgumentParser(description='Apply Entity Alias Reviews (RAQ-Compliant)')
    parser.add_argument('--list', action='store_true', help='List pending reviews')
    parser.add_argument('--apply', action='store_true', help='Apply pending reviews')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    args = parser.parse_args()
    
    if not any([args.list, args.apply, args.dry_run]):
        args.list = True  # Default to listing
    
    conn = get_connection()
    
    try:
        if args.list or args.dry_run:
            list_pending_reviews(conn)
        
        if args.apply:
            apply_reviews(conn, dry_run=False)
        elif args.dry_run:
            apply_reviews(conn, dry_run=True)
            
    finally:
        conn.close()


if __name__ == '__main__':
    main()
