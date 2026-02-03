#!/usr/bin/env python3
"""
Sync actor script code to database with automatic requeue of failed items.

Usage:
    python3 tools/sync_actor.py actors/owl_names__lookup_R__lucy.py
    python3 tools/sync_actor.py --all  # Sync all actors with drift
"""

import sys
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import hashlib

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def sync_actor(conn, script_path: str):
    """Sync an actor and requeue failed items."""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Read the file
    full_path = os.path.join(os.getcwd(), script_path)
    if not os.path.exists(full_path):
        print(f"❌ File not found: {full_path}")
        return False
    
    with open(full_path, 'r') as f:
        new_code = f.read()
    
    new_hash = hashlib.sha256(new_code.encode()).hexdigest()[:16]
    
    # Get current actor info
    cursor.execute("""
        SELECT actor_id, actor_name, script_code_hash
        FROM actors 
        WHERE script_file_path = %s
    """, (script_path,))
    
    actors = cursor.fetchall()
    if not actors:
        print(f"❌ No actors found with script_file_path = {script_path}")
        return False
    
    # Check if code actually changed
    old_hash = actors[0]['script_code_hash'] if actors else None
    if old_hash == new_hash:
        print(f"⏭️  No changes detected (hash: {new_hash})")
        return True
    
    # Update actors
    actor_ids = []
    for actor in actors:
        actor_ids.append(actor['actor_id'])
        cursor.execute("""
            UPDATE actors 
            SET script_code = %s, 
                script_code_hash = %s,
                script_synced_at = NOW()
            WHERE actor_id = %s
        """, (new_code, new_hash, actor['actor_id']))
        print(f"✅ Synced: {actor['actor_name']} (id={actor['actor_id']})")
    
    # Find workflows using these actors
    cursor.execute("""
        SELECT DISTINCT wc.workflow_id, w.workflow_name
        FROM workflow_task_types wc
        JOIN workflows w ON wc.workflow_id = w.workflow_id
        JOIN task_types c ON wc.task_type_id = c.task_type_id
        WHERE c.actor_id = ANY(%s)
    """, (actor_ids,))
    
    workflows = cursor.fetchall()
    if not workflows:
        conn.commit()
        return True
    
    workflow_ids = [w['workflow_id'] for w in workflows]
    print(f"📋 Affects workflows: {[w['workflow_name'] for w in workflows]}")
    
    # Reset FAILED queue items for these workflows
    cursor.execute("""
        UPDATE queue 
        SET status = 'pending', error_message = NULL
        WHERE workflow_id = ANY(%s) AND status = 'failed'
        RETURNING queue_id, subject_id, reason
    """, (workflow_ids,))
    
    reset_items = cursor.fetchall()
    if reset_items:
        print(f"🔄 Reset {len(reset_items)} failed queue items to pending")
        for item in reset_items[:5]:  # Show first 5
            print(f"   - queue_id={item['queue_id']} subject={item['subject_id']} ({item['reason']})")
        if len(reset_items) > 5:
            print(f"   ... and {len(reset_items) - 5} more")
    
    # Also reset FAILED workflow_runs (so they can be requeued)
    cursor.execute("""
        UPDATE workflow_runs 
        SET status = 'stopped'
        WHERE workflow_id = ANY(%s) AND status = 'failed'
        RETURNING workflow_run_id
    """, (workflow_ids,))
    
    reset_runs = cursor.fetchall()
    if reset_runs:
        print(f"🔄 Cancelled {len(reset_runs)} failed workflow runs")
    
    conn.commit()
    print(f"💾 Changes committed (old hash: {old_hash} → new: {new_hash})")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/sync_actor.py <script_path>")
        print("       python3 tools/sync_actor.py --all")
        sys.exit(1)
    
    conn = get_conn()
    
    if sys.argv[1] == '--all':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT DISTINCT script_file_path 
            FROM actors 
            WHERE script_file_path IS NOT NULL
        """)
        for row in cursor.fetchall():
            print(f"\n--- {row['script_file_path']} ---")
            sync_actor(conn, row['script_file_path'])
    else:
        sync_actor(conn, sys.argv[1])
    
    conn.close()


if __name__ == '__main__':
    main()
