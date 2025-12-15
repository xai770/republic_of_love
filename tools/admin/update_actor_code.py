#!/usr/bin/env python3
"""
Actor Code Update Management

Purpose: Deploy new script code versions to actors safely
- Load code from disk
- Store in database with version tracking
- Create backup before update
- Verify code is syntactically valid

Usage:
    # Update single actor
    python3 tools/update_actor_code.py --actor-id 66
    
    # Update by canonical name
    python3 tools/update_actor_code.py --actor-name check_fetch_needed
    
    # Update all script actors from disk
    python3 tools/update_actor_code.py --all
    
    # Dry run (show what would be updated)
    python3 tools/update_actor_code.py --all --dry-run
    
    # Force update even if code hasn't changed
    python3 tools/update_actor_code.py --actor-id 66 --force
"""

import sys
import os
import hashlib
import argparse
from datetime import datetime

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


def hash_code(code: str) -> str:
    """Generate SHA256 hash of code for change detection"""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def validate_python_syntax(code: str) -> tuple[bool, str]:
    """
    Check if Python code is syntactically valid
    
    Returns:
        (is_valid, error_message)
    """
    try:
        compile(code, '<string>', 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def get_actors_to_update(cursor, actor_id=None, actor_name=None, all_actors=False):
    """Get list of actors to update"""
    if actor_id:
        cursor.execute("""
            SELECT actor_id, actor_name, actor_type, 
                   execution_path, script_code, updated_at
            FROM actors
            WHERE actor_id = %s AND enabled = TRUE
        """, (actor_id,))
    elif actor_name:
        cursor.execute("""
            SELECT actor_id, actor_name, actor_type, 
                   execution_path, script_code, updated_at
            FROM actors
            WHERE actor_name = %s AND enabled = TRUE
        """, (actor_name,))
    elif all_actors:
        cursor.execute("""
            SELECT actor_id, actor_name, actor_type, 
                   execution_path, script_code, updated_at
            FROM actors
            WHERE actor_type = 'script' 
              AND enabled = TRUE
              AND execution_path IS NOT NULL
            ORDER BY actor_id
        """)
    else:
        return []
    
    return cursor.fetchall()


def load_code_from_disk(execution_path: str) -> tuple[bool, str, str]:
    """
    Load script code from disk
    
    Returns:
        (success, code, error_message)
    """
    # Resolve path
    if not execution_path.startswith('/'):
        base_dir = '/home/xai/Documents/ty_learn'
        full_path = os.path.join(base_dir, execution_path)
    else:
        full_path = execution_path
    
    # Check file exists
    if not os.path.exists(full_path):
        return False, "", f"File not found: {full_path}"
    
    # Read code
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        return False, "", f"Failed to read file: {e}"
    
    if not code.strip():
        return False, "", "File is empty"
    
    return True, code, ""


def update_actor_code(conn, cursor, actor, new_code, force=False, dry_run=False):
    """
    Update actor's script_code in database
    
    Returns:
        (updated, message)
    """
    actor_id = actor['actor_id']
    actor_name = actor['actor_name']
    old_code = actor['script_code']
    
    # Check if code changed
    if old_code:
        old_hash = hash_code(old_code)
        new_hash = hash_code(new_code)
        
        if old_hash == new_hash and not force:
            return False, "Code unchanged (use --force to update anyway)"
    
    # Validate syntax
    is_valid, error = validate_python_syntax(new_code)
    if not is_valid:
        return False, f"❌ Syntax error: {error}"
    
    if dry_run:
        return True, "Would update (dry-run)"
    
    # Backup old code if exists
    if old_code:
        backup_table = "actor_code_backups"
        cursor.execute(f"""
            INSERT INTO {backup_table} (actor_id, actor_name, script_code, 
                                       code_hash, backed_up_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (actor_id, actor_name, old_code, hash_code(old_code)))
    
    # Update actor
    cursor.execute("""
        UPDATE actors
        SET script_code = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE actor_id = %s
    """, (new_code, actor_id))
    
    conn.commit()
    
    return True, "✅ Updated successfully"


def ensure_backup_table_exists(cursor):
    """Create actor_code_backups table if it doesn't exist"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actor_code_backups (
            backup_id SERIAL PRIMARY KEY,
            actor_id INTEGER NOT NULL,
            actor_name TEXT NOT NULL,
            script_code TEXT NOT NULL,
            code_hash VARCHAR(64) NOT NULL,
            backed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_actor_code_backups_actor_id 
        ON actor_code_backups(actor_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_actor_code_backups_backed_up_at 
        ON actor_code_backups(backed_up_at DESC)
    """)


def main():
    parser = argparse.ArgumentParser(description='Update actor script code from disk')
    parser.add_argument('--actor-id', type=int, help='Update specific actor by ID')
    parser.add_argument('--actor-name', type=str, help='Update specific actor by canonical name')
    parser.add_argument('--all', action='store_true', help='Update all script actors')
    parser.add_argument('--force', action='store_true', help='Force update even if code unchanged')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    if not (args.actor_id or args.actor_name or args.all):
        parser.print_help()
        print("\n❌ Error: Must specify --actor-id, --actor-name, or --all")
        sys.exit(1)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Ensure backup table exists
        ensure_backup_table_exists(cursor)
        conn.commit()
        
        # Get actors to update
        actors = get_actors_to_update(cursor, args.actor_id, args.actor_name, args.all)
        
        if not actors:
            print("❌ No actors found matching criteria")
            sys.exit(1)
        
        print(f"\n{'='*80}")
        print(f"Actor Code Update - {'DRY RUN' if args.dry_run else 'LIVE'}")
        print(f"{'='*80}\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for actor in actors:
            actor_id = actor['actor_id']
            actor_name = actor['actor_name']
            execution_path = actor['execution_path']
            
            print(f"[{actor_id}] {actor_name}")
            print(f"     Path: {execution_path}")
            
            # Load code from disk
            success, new_code, error = load_code_from_disk(execution_path)
            
            if not success:
                print(f"     ❌ {error}")
                error_count += 1
                print()
                continue
            
            # Update actor
            updated, message = update_actor_code(
                conn, cursor, actor, new_code, 
                force=args.force, dry_run=args.dry_run
            )
            
            print(f"     {message}")
            print()
            
            if updated:
                updated_count += 1
            else:
                skipped_count += 1
        
        # Summary
        print(f"{'='*80}")
        print(f"Summary:")
        print(f"  ✅ Updated: {updated_count}")
        print(f"  ⏭  Skipped: {skipped_count}")
        print(f"  ❌ Errors:  {error_count}")
        print(f"{'='*80}\n")
        
        if args.dry_run:
            print("⚠️  This was a DRY RUN - no changes were made")
            print("    Run without --dry-run to apply updates\n")
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
