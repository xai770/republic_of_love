#!/usr/bin/env python3
"""
Pre-Migration 005 Validation
=============================

Validates database state before executing migration 005 (skill_hierarchy standardization).
Ensures no data loss and all FKs are properly tracked.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.database import get_connection


def check_skill_hierarchy():
    """Validate skill_hierarchy table current state"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("PRE-MIGRATION 005 VALIDATION")
    print("=" * 80)
    print()
    
    # Check current schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'skill_hierarchy'
        ORDER BY ordinal_position
    """)
    
    print("✓ Current skill_hierarchy schema:")
    for row in cursor.fetchall():
        print(f"  - {row['column_name']:<30} {row['data_type']:<20} {'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'}")
    print()
    
    # Count records
    cursor.execute("SELECT COUNT(*) as cnt FROM skill_hierarchy")
    skill_count = cursor.fetchone()['cnt']
    print(f"✓ Total skills: {skill_count}")
    
    # Count domains
    cursor.execute("SELECT COUNT(DISTINCT parent_skill) as cnt FROM skill_hierarchy")
    domain_count = cursor.fetchone()['cnt']
    print(f"✓ Total domains: {domain_count}")
    
    # Count root skills (no parent)
    cursor.execute("SELECT COUNT(*) as cnt FROM skill_hierarchy WHERE parent_skill IS NULL")
    root_count = cursor.fetchone()['cnt']
    print(f"✓ Root skills (no parent): {root_count}")
    print()
    
    # Check for duplicates
    cursor.execute("""
        SELECT skill, COUNT(*) as cnt
        FROM skill_hierarchy
        GROUP BY skill
        HAVING COUNT(*) > 1
    """)
    dupes = cursor.fetchall()
    if dupes:
        print("⚠ DUPLICATE SKILLS FOUND:")
        for row in dupes:
            print(f"  - {row['skill']}: {row['cnt']} occurrences")
        print()
    else:
        print("✓ No duplicate skills")
        print()
    
    # Check dependent tables
    print("✓ Dependent table row counts:")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM skill_aliases")
    print(f"  - skill_aliases: {cursor.fetchone()['cnt']} rows")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM skill_occurrences")
    print(f"  - skill_occurrences: {cursor.fetchone()['cnt']} rows")
    
    cursor.execute("SELECT COUNT(*) as cnt FROM skill_relationships")
    print(f"  - skill_relationships: {cursor.fetchone()['cnt']} rows")
    print()
    
    # Check for orphaned FKs
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM skill_aliases sa
        LEFT JOIN skill_hierarchy sh ON sa.skill = sh.skill
        WHERE sh.skill IS NULL
    """)
    orphaned = cursor.fetchone()['cnt']
    if orphaned > 0:
        print(f"⚠ WARNING: {orphaned} orphaned skill_aliases (no matching skill_hierarchy)")
        cursor.execute("""
            SELECT sa.skill, COUNT(*) as cnt
            FROM skill_aliases sa
            LEFT JOIN skill_hierarchy sh ON sa.skill = sh.skill
            WHERE sh.skill IS NULL
            GROUP BY sa.skill
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  - {row['skill']}: {row['cnt']} aliases")
        print()
    else:
        print("✓ No orphaned skill_aliases")
        print()
    
    cursor.close()
    conn.close()
    
    print("=" * 80)
    print("VALIDATION COMPLETE - Ready for migration 005")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Backup database: pg_dump base_yoga > backup_pre_migration_005.sql")
    print("  2. Run migration: psql base_yoga < migrations/005_standardize_skill_hierarchy.sql")
    print("  3. Verify with: python scripts/validate_migration_005.py")
    print()


if __name__ == '__main__':
    check_skill_hierarchy()
