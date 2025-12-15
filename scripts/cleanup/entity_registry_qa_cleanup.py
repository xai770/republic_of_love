#!/usr/bin/env python3
"""
Entity Registry QA Cleanup Script

Created: 2025-12-09
Author: Arden (QA Audit)

## FINDINGS FROM QA AUDIT

### Problem 1: Case-Variant Duplicates
The initial entity seed (2025-12-08 08:10:03) created 20 skills in a single batch.
This batch included BOTH "Team Leadership" (8442) AND "team leadership" (8447).
These were inserted before any case-insensitive dedup logic existed.

WF3005 is NOT at fault - it correctly checks for duplicates with:
    SELECT entity_id FROM entities WHERE LOWER(canonical_name) = LOWER(%s)
    
But the duplicates already existed from the seed.

### Problem 2: Naming Issues
Three skills have placeholder or example notation in their names:
- "Technical Expertise in [Specific Technology]" - placeholder brackets
- "Programming languages (e.g., Python, Java)" - example notation
- "Version control systems (e.g., Git)" - example notation

### Problem 3: Empty Domain
- "corporate_culture" domain has 0 skills assigned

## FIXES APPLIED

1. Merge case-variant duplicates (keep Title Case, merge lowercase into it)
2. Add UNIQUE constraint on LOWER(canonical_name) + entity_type
3. Clean up naming issues (remove placeholders/examples or make specific)
4. Flag empty domain for review

Usage:
    python3 scripts/cleanup/entity_registry_qa_cleanup.py --dry-run
    python3 scripts/cleanup/entity_registry_qa_cleanup.py --apply
"""

import argparse
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Import our cursor-agnostic utilities to avoid RealDictCursor vs tuple bugs
from core.database import fetch_scalar


def get_connection():
    """Get database connection."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )


def find_case_duplicates(cursor):
    """Find entities that are exact case-variant duplicates."""
    cursor.execute("""
        SELECT e1.entity_id as keep_id, e1.canonical_name as keep_name,
               e2.entity_id as merge_id, e2.canonical_name as merge_name
        FROM entities e1
        JOIN entities e2 ON LOWER(e1.canonical_name) = LOWER(e2.canonical_name)
        WHERE e1.entity_id < e2.entity_id
          AND e1.entity_type = 'skill'
          AND e2.entity_type = 'skill'
          AND e1.status = 'active'
          AND e2.status = 'active'
        ORDER BY e1.canonical_name
    """)
    return cursor.fetchall()


def find_naming_issues(cursor):
    """Find entities with placeholder or example notation in names."""
    cursor.execute("""
        SELECT entity_id, canonical_name,
            CASE 
                WHEN canonical_name LIKE '%[%]%' THEN 'PLACEHOLDER_BRACKETS'
                WHEN canonical_name LIKE '%(e.g.%' THEN 'EXAMPLE_NOTATION'
                WHEN LENGTH(canonical_name) > 50 THEN 'TOO_LONG'
            END as issue_type
        FROM entities
        WHERE entity_type = 'skill'
          AND status = 'active'
          AND (canonical_name LIKE '%[%]%' 
               OR canonical_name LIKE '%(e.g.%'
               OR LENGTH(canonical_name) > 50)
        ORDER BY canonical_name
    """)
    return cursor.fetchall()


def find_empty_domains(cursor):
    """Find domains with no skills assigned."""
    cursor.execute("""
        SELECT d.entity_id, d.canonical_name, COUNT(er.entity_id) as skill_count
        FROM entities d
        LEFT JOIN entity_relationships er 
            ON d.entity_id = er.related_entity_id AND er.relationship = 'is_a'
        WHERE d.entity_type = 'skill_domain'
        GROUP BY d.entity_id, d.canonical_name
        HAVING COUNT(er.entity_id) = 0
        ORDER BY d.canonical_name
    """)
    return cursor.fetchall()


def merge_duplicate(cursor, keep_id, merge_id, dry_run=True):
    """
    Merge duplicate entity into the keeper.
    
    Steps:
    1. Update all entity_relationships pointing to merge_id → keep_id
    2. Update all entity_aliases to point to keep_id
    3. Update all posting_skills referencing merge_id → keep_id
    4. Update all registry_decisions referencing merge_id
    5. Create alias from merge_id's canonical_name → keep_id
    6. Mark merge_id as 'merged' status
    """
    actions = []
    
    # 1. Update entity_relationships where merge_id is the entity
    cursor.execute("""
        SELECT COUNT(*) FROM entity_relationships WHERE entity_id = %s
    """, (merge_id,))
    rel_count = fetch_scalar(cursor)
    if rel_count > 0:
        actions.append(f"  - Update {rel_count} entity_relationships (entity_id)")
        if not dry_run:
            cursor.execute("""
                UPDATE entity_relationships 
                SET entity_id = %s 
                WHERE entity_id = %s
                AND NOT EXISTS (
                    SELECT 1 FROM entity_relationships er2 
                    WHERE er2.entity_id = %s 
                    AND er2.related_entity_id = entity_relationships.related_entity_id
                    AND er2.relationship = entity_relationships.relationship
                )
            """, (keep_id, merge_id, keep_id))
            # Delete any that would be duplicates
            cursor.execute("""
                DELETE FROM entity_relationships WHERE entity_id = %s
            """, (merge_id,))
    
    # 2. Update entity_relationships where merge_id is the related_entity
    cursor.execute("""
        SELECT COUNT(*) FROM entity_relationships WHERE related_entity_id = %s
    """, (merge_id,))
    rel_count2 = fetch_scalar(cursor)
    if rel_count2 > 0:
        actions.append(f"  - Update {rel_count2} entity_relationships (related_entity_id)")
        if not dry_run:
            cursor.execute("""
                UPDATE entity_relationships 
                SET related_entity_id = %s 
                WHERE related_entity_id = %s
            """, (keep_id, merge_id))
    
    # 3. Update posting_skills
    cursor.execute("""
        SELECT COUNT(*) FROM posting_skills WHERE entity_id = %s
    """, (merge_id,))
    ps_count = fetch_scalar(cursor)
    if ps_count > 0:
        actions.append(f"  - Update {ps_count} posting_skills")
        if not dry_run:
            cursor.execute("""
                UPDATE posting_skills SET entity_id = %s WHERE entity_id = %s
            """, (keep_id, merge_id))
    
    # 4. Update registry_decisions (subject)
    cursor.execute("""
        SELECT COUNT(*) FROM registry_decisions WHERE subject_entity_id = %s
    """, (merge_id,))
    rd_count = fetch_scalar(cursor)
    if rd_count > 0:
        actions.append(f"  - Update {rd_count} registry_decisions (subject)")
        if not dry_run:
            cursor.execute("""
                UPDATE registry_decisions SET subject_entity_id = %s WHERE subject_entity_id = %s
            """, (keep_id, merge_id))
    
    # 5. Update registry_decisions (target)
    cursor.execute("""
        SELECT COUNT(*) FROM registry_decisions WHERE target_entity_id = %s
    """, (merge_id,))
    rd_count2 = fetch_scalar(cursor)
    if rd_count2 > 0:
        actions.append(f"  - Update {rd_count2} registry_decisions (target)")
        if not dry_run:
            cursor.execute("""
                UPDATE registry_decisions SET target_entity_id = %s WHERE target_entity_id = %s
            """, (keep_id, merge_id))
    
    # 6. Create alias from merged entity's name
    cursor.execute("SELECT canonical_name FROM entities WHERE entity_id = %s", (merge_id,))
    merge_name = fetch_scalar(cursor)
    actions.append(f"  - Create alias: '{merge_name.lower()}' → entity {keep_id}")
    if not dry_run:
        cursor.execute("""
            INSERT INTO entity_aliases (entity_id, alias, language)
            VALUES (%s, %s, 'en')
            ON CONFLICT (alias, language) DO NOTHING
        """, (keep_id, merge_name.lower()))
    
    # 7. Mark merged entity as inactive
    actions.append(f"  - Mark entity {merge_id} as 'merged' (merged_into = {keep_id})")
    if not dry_run:
        cursor.execute("""
            UPDATE entities 
            SET status = 'merged', merged_into_entity_id = %s 
            WHERE entity_id = %s
        """, (keep_id, merge_id))
    
    return actions


def add_unique_constraint(cursor, dry_run=True):
    """Add unique constraint on LOWER(canonical_name) + entity_type for active entities."""
    # Check if constraint already exists
    cursor.execute("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_entities_canonical_lower_unique'
    """)
    if cursor.fetchone():
        return ["  - Unique constraint already exists, skipping"]
    
    action = "  - CREATE UNIQUE INDEX idx_entities_canonical_lower_unique ON entities (LOWER(canonical_name), entity_type) WHERE status = 'active'"
    if not dry_run:
        cursor.execute("""
            CREATE UNIQUE INDEX idx_entities_canonical_lower_unique 
            ON entities (LOWER(canonical_name), entity_type) 
            WHERE status = 'active'
        """)
    return [action]


def rename_entity(cursor, entity_id, old_name, new_name, dry_run=True):
    """Rename an entity to clean up placeholder/example notation."""
    actions = [f"  - Rename entity {entity_id}: '{old_name}' → '{new_name}'"]
    if not dry_run:
        cursor.execute("""
            UPDATE entities SET canonical_name = %s WHERE entity_id = %s
        """, (new_name, entity_id))
        # Also update entity_names if exists
        cursor.execute("""
            UPDATE entity_names SET display_name = %s 
            WHERE entity_id = %s AND is_primary = true
        """, (new_name, entity_id))
        # Create alias from old name
        cursor.execute("""
            INSERT INTO entity_aliases (entity_id, alias, language)
            VALUES (%s, %s, 'en')
            ON CONFLICT (alias, language) DO NOTHING
        """, (entity_id, old_name.lower()))
    return actions


def run_audit(dry_run=True):
    """Run the full QA audit and cleanup."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("=" * 70)
    print("ENTITY REGISTRY QA CLEANUP")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLYING CHANGES'}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)
    
    all_actions = []
    
    # 1. Find and merge case duplicates
    print("\n📋 PHASE 1: Case-Variant Duplicates")
    print("-" * 50)
    duplicates = find_case_duplicates(cursor)
    
    if duplicates:
        print(f"Found {len(duplicates)} case-variant duplicate(s):\n")
        for dup in duplicates:
            print(f"  KEEP: {dup['keep_id']} '{dup['keep_name']}'")
            print(f"  MERGE: {dup['merge_id']} '{dup['merge_name']}'")
            actions = merge_duplicate(cursor, dup['keep_id'], dup['merge_id'], dry_run)
            for action in actions:
                print(action)
            all_actions.extend(actions)
            print()
        if not dry_run:
            conn.commit()
            print("  ✓ Phase 1 committed")
    else:
        print("  ✓ No case-variant duplicates found")
    
    # 2. Add unique constraint
    print("\n📋 PHASE 2: Add Unique Constraint")
    print("-" * 50)
    try:
        actions = add_unique_constraint(cursor, dry_run)
        for action in actions:
            print(action)
        all_actions.extend(actions)
        if not dry_run:
            conn.commit()
            print("  ✓ Phase 2 committed")
    except Exception as e:
        print(f"  ⚠️  Skipped: {e}")
        print("  Note: Run as postgres to create indexes")
        conn.rollback()
    
    # 3. Fix naming issues
    print("\n📋 PHASE 3: Naming Issues")
    print("-" * 50)
    naming_issues = find_naming_issues(cursor)
    
    # Define renames (old → new)
    renames = {
        "Technical Expertise in [Specific Technology]": "Technical Expertise",
        "Programming languages (e.g., Python, Java)": "Programming Languages",
        "Version control systems (e.g., Git)": "Version Control Systems",
    }
    
    if naming_issues:
        print(f"Found {len(naming_issues)} naming issue(s):\n")
        for issue in naming_issues:
            old_name = issue['canonical_name']
            new_name = renames.get(old_name)
            if new_name:
                actions = rename_entity(cursor, issue['entity_id'], old_name, new_name, dry_run)
                for action in actions:
                    print(action)
                all_actions.extend(actions)
            else:
                print(f"  ⚠️  No rename defined for: '{old_name}' (entity {issue['entity_id']})")
        print()
    else:
        print("  ✓ No naming issues found")
    
    # 4. Report empty domains
    print("\n📋 PHASE 4: Empty Domains")
    print("-" * 50)
    empty_domains = find_empty_domains(cursor)
    
    if empty_domains:
        print(f"Found {len(empty_domains)} empty domain(s):\n")
        for domain in empty_domains:
            print(f"  ⚠️  '{domain['canonical_name']}' (entity {domain['entity_id']}) - 0 skills")
            print(f"      Consider: Delete domain, or assign skills to it")
    else:
        print("  ✓ All domains have skills assigned")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total actions: {len(all_actions)}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes made to database")
        print("   Run with --apply to make these changes")
    else:
        conn.commit()
        print("\n✅ All changes committed to database")
        print("   Run entity_registry_exporter.py to regenerate INDEX.md")
    
    conn.close()
    return all_actions


def main():
    parser = argparse.ArgumentParser(
        description='Entity Registry QA Cleanup - Fix duplicates and naming issues'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would be done without making changes (default)')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply the changes to the database')
    
    args = parser.parse_args()
    
    # --apply overrides --dry-run
    dry_run = not args.apply
    
    run_audit(dry_run=dry_run)


if __name__ == '__main__':
    main()
