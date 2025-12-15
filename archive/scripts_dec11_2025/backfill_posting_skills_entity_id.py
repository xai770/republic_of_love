#!/usr/bin/env python3
"""
Backfill entity_id for posting_skills rows.

Phase A: Run SkillResolver on existing posting_skills with NULL entity_id.
- Updates entity_id where resolver finds a match
- Queues unmatched skills to entities_pending for WF3005

Usage:
    python3 scripts/backfill_posting_skills_entity_id.py [--dry-run]

Author: Sandy
Date: December 8, 2025
"""

import sys
import argparse
sys.path.insert(0, '/home/xai/Documents/ty_wave')

import psycopg2
from core.wave_runner.actors.entity_skill_resolver import SkillResolver


def backfill(dry_run=False):
    """Backfill entity_id for posting_skills rows."""
    
    conn = psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password='base_yoga_secure_2025',
        host='localhost'
    )
    
    cursor = conn.cursor()
    
    # Get unique skills that need resolution
    cursor.execute("""
        SELECT DISTINCT raw_skill_name 
        FROM posting_skills 
        WHERE entity_id IS NULL 
          AND raw_skill_name IS NOT NULL
        ORDER BY raw_skill_name
    """)
    
    unique_skills = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(unique_skills)} unique skills to resolve")
    
    if dry_run:
        print("DRY RUN - no changes will be made")
    
    # Create resolver
    resolver = SkillResolver(conn)
    
    resolved_count = 0
    pending_count = 0
    updated_rows = 0
    
    for skill_name in unique_skills:
        entity_id = resolver.resolve(skill_name, {"source": "backfill"})
        
        if entity_id:
            resolved_count += 1
            
            if not dry_run:
                # Update posting_skills rows one by one to handle duplicates
                # Get all rows that would be updated
                cursor.execute("""
                    SELECT posting_skill_id, posting_id 
                    FROM posting_skills 
                    WHERE entity_id IS NULL 
                      AND LOWER(raw_skill_name) = LOWER(%s)
                """, (skill_name,))
                
                candidates = cursor.fetchall()
                rows = 0
                skipped = 0
                
                for ps_id, post_id in candidates:
                    # Check if this posting already has this entity
                    cursor.execute("""
                        SELECT 1 FROM posting_skills 
                        WHERE posting_id = %s AND entity_id = %s
                    """, (post_id, entity_id))
                    
                    if cursor.fetchone():
                        # Already exists - skip (could delete duplicate, but safer to leave)
                        skipped += 1
                    else:
                        cursor.execute("""
                            UPDATE posting_skills 
                            SET entity_id = %s, updated_at = NOW()
                            WHERE posting_skill_id = %s
                        """, (entity_id, ps_id))
                        rows += 1
                
                updated_rows += rows
                if skipped:
                    print(f"  ✓ '{skill_name}' → entity_id={entity_id} ({rows} rows, {skipped} skipped)")
                else:
                    print(f"  ✓ '{skill_name}' → entity_id={entity_id} ({rows} rows)")
            else:
                print(f"  [DRY] '{skill_name}' → entity_id={entity_id}")
        else:
            pending_count += 1
            print(f"  ⏳ '{skill_name}' → queued to entities_pending")
    
    if not dry_run:
        conn.commit()
    
    print(f"\n=== Summary ===")
    print(f"Unique skills:   {len(unique_skills)}")
    print(f"Resolved:        {resolved_count}")
    print(f"Queued pending:  {pending_count}")
    print(f"Rows updated:    {updated_rows}")
    
    # Show pending count for WF3005 trigger
    cursor.execute("SELECT COUNT(*) FROM entities_pending WHERE status = 'pending'")
    total_pending = cursor.fetchone()[0]
    print(f"\nTotal in entities_pending: {total_pending}")
    if total_pending >= 50:
        print("→ WF3005 trigger threshold reached!")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill entity_id for posting_skills")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()
    
    backfill(dry_run=args.dry_run)
