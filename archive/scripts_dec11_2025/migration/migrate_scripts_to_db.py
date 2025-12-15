#!/usr/bin/env python3
"""
Migration Script: Load all script actor code into database
Date: 2025-10-31
Purpose: Migrate script actors from file-based to database-stored code
"""

import os
import psycopg2
from pathlib import Path

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'turing',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

# Script actor mappings: actor_id -> file_path
SCRIPT_MAPPINGS = {
    6: 'scripts/dynatax_lookup_terms.py',
    7: 'scripts/dynatax_update_dictionary.py',  # MISSING
    10: 'scripts/dynatax_migrate_subdivisions.py',
    11: 'scripts/dynatax_extract_terms.py',
    19: 'scripts/build_job_skill_graph.py',
    33: 'scripts/score_instruction.py',
    34: 'scripts/dynatax_check_thresholds.py',  # MISSING?
    35: 'scripts/dynatax_flag_unknowns.py',  # MISSING?
    36: 'scripts/validate_response.py',
    41: 'scripts/import_to_skillbridge.sh',  # MISSING
    42: 'scripts/validate_skillbridge.py',  # MISSING
    46: 'scripts/db_update_summary.py',
    47: 'tools/taxonomy_gopher.py'
}

def get_language_from_extension(filepath):
    """Determine script language from file extension"""
    ext = Path(filepath).suffix.lower()
    if ext == '.py':
        return 'python'
    elif ext == '.sh':
        return 'bash'
    elif ext == '.js':
        return 'javascript'
    else:
        return 'unknown'

def migrate_scripts():
    """Load all script files into database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    base_path = Path('/home/xai/Documents/ty_learn')
    
    migrated = 0
    missing = 0
    errors = 0
    
    print("=" * 70)
    print("SCRIPT MIGRATION TO DATABASE")
    print("=" * 70)
    print()
    
    for actor_id, relative_path in SCRIPT_MAPPINGS.items():
        full_path = base_path / relative_path
        
        # Get actor name
        cur.execute("SELECT actor_name FROM actors WHERE actor_id = %s", (actor_id,))
        result = cur.fetchone()
        if not result:
            print(f"❌ Actor ID {actor_id}: NOT FOUND in database")
            errors += 1
            continue
            
        actor_name = result[0]
        
        # Check if file exists
        if not full_path.exists():
            print(f"⚠️  {actor_name} (ID {actor_id}): MISSING FILE - {relative_path}")
            missing += 1
            continue
        
        try:
            # Read script content
            with open(full_path, 'r', encoding='utf-8') as f:
                script_code = f.read()
            
            # Determine language
            script_language = get_language_from_extension(relative_path)
            
            # Update actor with script code
            cur.execute("""
                UPDATE actors 
                SET script_code = %s,
                    script_language = %s,
                    script_version = 1,
                    execution_path = %s
                WHERE actor_id = %s
            """, (script_code, script_language, str(relative_path), actor_id))
            
            code_length = len(script_code)
            print(f"✅ {actor_name} (ID {actor_id}): Migrated {code_length:,} chars [{script_language}]")
            print(f"   Path: {relative_path}")
            migrated += 1
            
        except Exception as e:
            print(f"❌ {actor_name} (ID {actor_id}): ERROR - {e}")
            errors += 1
    
    # Commit changes
    conn.commit()
    cur.close()
    conn.close()
    
    # Summary
    print()
    print("=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"✅ Migrated: {migrated} scripts")
    print(f"⚠️  Missing:  {missing} files")
    print(f"❌ Errors:   {errors}")
    print()
    
    if migrated > 0:
        print("✨ Scripts now stored in database!")
        print("   - Can't be accidentally deleted")
        print("   - Version tracked via actors_history")
        print("   - Audit trail for all executions")
    
    if missing > 0:
        print()
        print("⚠️  Missing files should be:")
        print("   1. Recreated if still needed")
        print("   2. Or actors disabled if obsolete")

if __name__ == '__main__':
    migrate_scripts()
