#!/usr/bin/env python3
"""
View Actor Code Status & History

Purpose: Check what code is deployed vs what's on disk
- Compare disk version to database version
- View backup history
- Show code diffs

Usage:
    # Check single actor status
    python3 tools/actor_code_status.py --actor-id 66
    
    # Check all actors
    python3 tools/actor_code_status.py --all
    
    # Show only actors with mismatches
    python3 tools/actor_code_status.py --all --show-diffs
    
    # View backup history for actor
    python3 tools/actor_code_status.py --actor-id 66 --history
    
    # Restore from backup
    python3 tools/actor_code_status.py --actor-id 66 --restore <backup_id>
"""

import sys
import os
import hashlib
import argparse
from datetime import datetime
import difflib

sys.path.insert(0, '/home/xai/Documents/ty_learn')
from core.database import get_connection


def hash_code(code: str) -> str:
    """Generate SHA256 hash of code"""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def load_code_from_disk(execution_path: str):
    """Load script code from disk"""
    if not execution_path.startswith('/'):
        base_dir = '/home/xai/Documents/ty_learn'
        full_path = os.path.join(base_dir, execution_path)
    else:
        full_path = execution_path
    
    if not os.path.exists(full_path):
        return None, f"File not found: {full_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except Exception as e:
        return None, f"Failed to read: {e}"


def show_diff(old_code, new_code, from_label="Database", to_label="Disk"):
    """Show unified diff between two code versions"""
    old_lines = old_code.splitlines(keepends=True) if old_code else []
    new_lines = new_code.splitlines(keepends=True) if new_code else []
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=from_label,
        tofile=to_label,
        lineterm=''
    )
    
    diff_text = '\n'.join(diff)
    if diff_text:
        print("\n" + "─" * 80)
        print(diff_text)
        print("─" * 80)
    else:
        print("    (no differences)")


def check_actor_status(cursor, actor_id, show_diff=False):
    """Check single actor's code status"""
    cursor.execute("""
        SELECT actor_id, actor_name, canonical_name, execution_path, 
               script_code, updated_at
        FROM actors
        WHERE actor_id = %s AND enabled = TRUE
    """, (actor_id,))
    
    actor = cursor.fetchone()
    if not actor:
        print(f"❌ Actor {actor_id} not found")
        return False
    
    print(f"\n{'='*80}")
    print(f"Actor {actor['actor_id']}: {actor['actor_name']}")
    print(f"Canonical: {actor['canonical_name']}")
    print(f"Path: {actor['execution_path']}")
    print(f"Last Updated: {actor['updated_at']}")
    print(f"{'='*80}\n")
    
    db_code = actor['script_code']
    disk_code, error = load_code_from_disk(actor['execution_path'])
    
    if error:
        print(f"❌ Disk: {error}")
        return False
    
    if not db_code:
        print("⚠️  Database: No code stored (NULL)")
        print(f"✓  Disk: {len(disk_code)} bytes")
        print("    → Run: python3 tools/update_actor_code.py --actor-id", actor_id)
        return False
    
    db_hash = hash_code(db_code)
    disk_hash = hash_code(disk_code)
    
    if db_hash == disk_hash:
        print(f"✅ Code in sync")
        print(f"   Database: {len(db_code)} bytes")
        print(f"   Disk:     {len(disk_code)} bytes")
        print(f"   Hash:     {db_hash[:16]}...")
        return True
    else:
        print(f"⚠️  Code MISMATCH")
        print(f"   Database: {len(db_code)} bytes (hash: {db_hash[:16]}...)")
        print(f"   Disk:     {len(disk_code)} bytes (hash: {disk_hash[:16]}...)")
        print(f"   → Run: python3 tools/update_actor_code.py --actor-id {actor_id}")
        
        if show_diff:
            show_diff(db_code, disk_code)
        
        return False


def show_backup_history(cursor, actor_id):
    """Show backup history for an actor"""
    cursor.execute("""
        SELECT backup_id, backed_up_at, code_hash, 
               LENGTH(script_code) as code_length
        FROM actor_code_backups
        WHERE actor_id = %s
        ORDER BY backed_up_at DESC
        LIMIT 20
    """, (actor_id,))
    
    backups = cursor.fetchall()
    
    if not backups:
        print(f"\nNo backups found for actor {actor_id}")
        return
    
    print(f"\n{'='*80}")
    print(f"Backup History (last 20)")
    print(f"{'='*80}\n")
    
    for backup in backups:
        print(f"Backup ID: {backup['backup_id']}")
        print(f"  Date: {backup['backed_up_at']}")
        print(f"  Size: {backup['code_length']} bytes")
        print(f"  Hash: {backup['code_hash'][:16]}...")
        print()


def restore_from_backup(conn, cursor, actor_id, backup_id):
    """Restore actor code from backup"""
    # Get backup
    cursor.execute("""
        SELECT script_code, code_hash
        FROM actor_code_backups
        WHERE backup_id = %s AND actor_id = %s
    """, (backup_id, actor_id))
    
    backup = cursor.fetchone()
    if not backup:
        print(f"❌ Backup {backup_id} not found for actor {actor_id}")
        return False
    
    # Get current code for new backup
    cursor.execute("""
        SELECT actor_name, script_code
        FROM actors
        WHERE actor_id = %s
    """, (actor_id,))
    
    actor = cursor.fetchone()
    if not actor:
        print(f"❌ Actor {actor_id} not found")
        return False
    
    # Backup current code
    if actor['script_code']:
        cursor.execute("""
            INSERT INTO actor_code_backups (actor_id, actor_name, script_code, 
                                           code_hash, backed_up_at, notes)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        """, (actor_id, actor['actor_name'], actor['script_code'],
              hash_code(actor['script_code']), 
              f'Pre-restore backup (restoring backup_id {backup_id})'))
    
    # Restore
    cursor.execute("""
        UPDATE actors
        SET script_code = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE actor_id = %s
    """, (backup['script_code'], actor_id))
    
    conn.commit()
    
    print(f"✅ Restored actor {actor_id} from backup {backup_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Check actor code status and history')
    parser.add_argument('--actor-id', type=int, help='Check specific actor')
    parser.add_argument('--all', action='store_true', help='Check all script actors')
    parser.add_argument('--show-diffs', action='store_true', help='Show code diffs for mismatches')
    parser.add_argument('--history', action='store_true', help='Show backup history')
    parser.add_argument('--restore', type=int, metavar='BACKUP_ID', help='Restore from backup')
    
    args = parser.parse_args()
    
    if not (args.actor_id or args.all):
        parser.print_help()
        print("\n❌ Error: Must specify --actor-id or --all")
        sys.exit(1)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if args.restore:
            if not args.actor_id:
                print("❌ Error: --restore requires --actor-id")
                sys.exit(1)
            
            restore_from_backup(conn, cursor, args.actor_id, args.restore)
            return
        
        if args.history:
            if not args.actor_id:
                print("❌ Error: --history requires --actor-id")
                sys.exit(1)
            
            show_backup_history(cursor, args.actor_id)
            return
        
        if args.actor_id:
            check_actor_status(cursor, args.actor_id, args.show_diffs)
        
        elif args.all:
            cursor.execute("""
                SELECT actor_id
                FROM actors
                WHERE actor_type = 'script' 
                  AND enabled = TRUE
                  AND execution_path IS NOT NULL
                ORDER BY actor_id
            """)
            
            actors = cursor.fetchall()
            
            in_sync = 0
            out_of_sync = 0
            errors = 0
            
            for actor in actors:
                result = check_actor_status(cursor, actor['actor_id'], args.show_diffs)
                if result is True:
                    in_sync += 1
                elif result is False:
                    out_of_sync += 1
                else:
                    errors += 1
            
            print(f"\n{'='*80}")
            print(f"Summary:")
            print(f"  ✅ In Sync:      {in_sync}")
            print(f"  ⚠️  Out of Sync:  {out_of_sync}")
            print(f"  ❌ Errors:       {errors}")
            print(f"{'='*80}\n")
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
