#!/usr/bin/env python3
"""
Migrate posting_skills and profile_skills from old skill_id to new entity_id

This script:
1. Adds entity_id column to posting_skills and profile_skills
2. Populates entity_id using skill_entity_map
3. Validates all mappings
4. Drops old skill_id FK constraint
5. Makes entity_id NOT NULL and adds FK to entities

Run with --dry-run first to see what would happen.
Run with --execute to actually perform the migration.

Usage:
    python3 scripts/migrate_skills_to_entities.py --dry-run
    python3 scripts/migrate_skills_to_entities.py --execute
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


def get_db_connection():
    """Get database connection."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "turing"),
        user=os.getenv("DB_USER", "base_admin"),
        password=os.getenv("DB_PASSWORD", "")
    )


def check_current_state(cursor) -> dict:
    """Check current state of tables."""
    
    state = {}
    
    # Check if entity_id column already exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'posting_skills' AND column_name = 'entity_id'
    """)
    state['posting_skills_has_entity_id'] = cursor.fetchone() is not None
    
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'profile_skills' AND column_name = 'entity_id'
    """)
    state['profile_skills_has_entity_id'] = cursor.fetchone() is not None
    
    # Row counts
    cursor.execute("SELECT COUNT(*) FROM posting_skills")
    state['posting_skills_count'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM profile_skills")
    state['profile_skills_count'] = cursor.fetchone()[0]
    
    # Check mappability
    cursor.execute("""
        SELECT COUNT(DISTINCT ps.skill_id) 
        FROM posting_skills ps 
        WHERE NOT EXISTS (SELECT 1 FROM skill_entity_map sem WHERE sem.skill_id = ps.skill_id)
    """)
    state['posting_unmappable'] = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ps.skill_id) 
        FROM profile_skills ps 
        WHERE NOT EXISTS (SELECT 1 FROM skill_entity_map sem WHERE sem.skill_id = ps.skill_id)
    """)
    state['profile_unmappable'] = cursor.fetchone()[0]
    
    return state


def migrate_table(cursor, table_name: str, dry_run: bool) -> dict:
    """Migrate a single table from skill_id to entity_id."""
    
    result = {
        'table': table_name,
        'steps': [],
        'success': True
    }
    
    # Step 1: Add entity_id column if not exists
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' AND column_name = 'entity_id'
    """)
    
    if cursor.fetchone() is None:
        sql = f"ALTER TABLE {table_name} ADD COLUMN entity_id INTEGER"
        result['steps'].append(f"ADD COLUMN: {sql}")
        if not dry_run:
            cursor.execute(sql)
        column_just_added = True
    else:
        result['steps'].append("SKIP: entity_id column already exists")
        column_just_added = False
    
    # Step 2: Populate entity_id from skill_entity_map
    sql = f"""
        UPDATE {table_name} t
        SET entity_id = sem.entity_id
        FROM skill_entity_map sem
        WHERE t.skill_id = sem.skill_id
          AND t.entity_id IS NULL
    """
    result['steps'].append(f"POPULATE: {sql.strip()}")
    if not dry_run:
        cursor.execute(sql)
        result['rows_updated'] = cursor.rowcount
    else:
        # In dry run, estimate rows to update
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        result['rows_updated'] = cursor.fetchone()[0]
    
    # Step 3: Check for any NULLs remaining (skip in dry run if column just added)
    if dry_run and column_just_added:
        result['steps'].append(f"VALIDATE (dry-run): Will check all rows have entity_id after populate")
    else:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE entity_id IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            result['steps'].append(f"WARNING: {null_count} rows still have NULL entity_id")
            result['success'] = False
            return result
        
        result['steps'].append(f"VALIDATED: All rows have entity_id")
    
    # Step 4: Find and drop old FK constraint on skill_id
    cursor.execute(f"""
        SELECT constraint_name 
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu USING (constraint_name)
        WHERE tc.table_name = '{table_name}' 
          AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'skill_id'
    """)
    fk_row = cursor.fetchone()
    
    if fk_row:
        fk_name = fk_row[0]
        sql = f"ALTER TABLE {table_name} DROP CONSTRAINT {fk_name}"
        result['steps'].append(f"DROP FK: {sql}")
        if not dry_run:
            cursor.execute(sql)
    else:
        result['steps'].append("SKIP: No FK constraint on skill_id found")
    
    # Step 5: Make entity_id NOT NULL
    sql = f"ALTER TABLE {table_name} ALTER COLUMN entity_id SET NOT NULL"
    result['steps'].append(f"SET NOT NULL: {sql}")
    if not dry_run:
        cursor.execute(sql)
    
    # Step 6: Add FK to entities
    cursor.execute(f"""
        SELECT constraint_name 
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu USING (constraint_name)
        WHERE tc.table_name = '{table_name}' 
          AND tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = 'entities'
    """)
    
    if cursor.fetchone() is None:
        fk_name = f"fk_{table_name}_entity_id"
        sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} FOREIGN KEY (entity_id) REFERENCES entities(entity_id)"
        result['steps'].append(f"ADD FK: {sql}")
        if not dry_run:
            cursor.execute(sql)
    else:
        result['steps'].append("SKIP: FK to entities already exists")
    
    # Step 7: Add index on entity_id
    idx_name = f"idx_{table_name}_entity_id"
    cursor.execute(f"""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = '{idx_name}'
    """)
    
    if cursor.fetchone() is None:
        sql = f"CREATE INDEX {idx_name} ON {table_name}(entity_id)"
        result['steps'].append(f"CREATE INDEX: {sql}")
        if not dry_run:
            cursor.execute(sql)
    else:
        result['steps'].append(f"SKIP: Index {idx_name} already exists")
    
    return result


def deprecate_old_tables(cursor, dry_run: bool) -> list:
    """Add comments marking old tables as deprecated."""
    
    deprecated = [
        ('skill_aliases', 'DEPRECATED: Use entities + entity_aliases. Kept for FK compatibility during migration.'),
        ('skill_hierarchy', 'DEPRECATED: Use entity_relationships. Kept for reference.'),
        ('skill_occurrences', 'DEPRECATED: Use entity-based tracking.'),
    ]
    
    results = []
    for table, comment in deprecated:
        sql = f"COMMENT ON TABLE {table} IS '{comment}'"
        results.append(sql)
        if not dry_run:
            cursor.execute(sql)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Migrate skills to entities")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--execute", action="store_true", help="Actually perform the migration")
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("ERROR: Must specify --dry-run or --execute")
        sys.exit(1)
    
    if args.dry_run and args.execute:
        print("ERROR: Cannot specify both --dry-run and --execute")
        sys.exit(1)
    
    dry_run = args.dry_run
    
    print(f"\n{'='*60}")
    print(f"SKILLS TO ENTITIES MIGRATION {'(DRY RUN)' if dry_run else '(EXECUTING)'}")
    print(f"{'='*60}\n")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check current state
        print("📊 CURRENT STATE:")
        state = check_current_state(cursor)
        for k, v in state.items():
            print(f"   {k}: {v}")
        
        if state['posting_unmappable'] > 0 or state['profile_unmappable'] > 0:
            print("\n❌ ERROR: Some skill_ids cannot be mapped to entity_ids!")
            print("   Fix skill_entity_map first.")
            sys.exit(1)
        
        print("\n" + "-"*60)
        
        # Migrate posting_skills
        print("\n📦 MIGRATING posting_skills:")
        result = migrate_table(cursor, 'posting_skills', dry_run)
        for step in result['steps']:
            print(f"   {step}")
        if 'rows_updated' in result:
            print(f"   → Rows updated: {result['rows_updated']}")
        
        print("\n" + "-"*60)
        
        # Migrate profile_skills
        print("\n📦 MIGRATING profile_skills:")
        result = migrate_table(cursor, 'profile_skills', dry_run)
        for step in result['steps']:
            print(f"   {step}")
        if 'rows_updated' in result:
            print(f"   → Rows updated: {result['rows_updated']}")
        
        print("\n" + "-"*60)
        
        # Deprecate old tables
        print("\n🏚️  DEPRECATING OLD TABLES:")
        deprecations = deprecate_old_tables(cursor, dry_run)
        for sql in deprecations:
            print(f"   {sql}")
        
        print("\n" + "="*60)
        
        if dry_run:
            print("\n🔍 DRY RUN COMPLETE - No changes made")
            print("   Run with --execute to perform migration")
            conn.rollback()
        else:
            conn.commit()
            print("\n✅ MIGRATION COMPLETE!")
            print("\n   Next steps:")
            print("   1. Update workflows to use entity_id instead of skill_id")
            print("   2. Eventually drop skill_id column from posting_skills/profile_skills")
            print("   3. Eventually drop deprecated tables (skill_aliases, skill_hierarchy, etc.)")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
