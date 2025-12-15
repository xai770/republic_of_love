#!/usr/bin/env python3
"""
Pending Skills Fetcher - WF3005 Step 0a

Fetches a batch of pending skills from entities_pending that need
LLM triage (NEW/ALIAS/SKIP decision).

This step runs BEFORE entity_orphan_fetcher to ensure new skills
get promoted to the entities table first.

Author: Sandy
Date: December 8, 2025
"""

import json
from datetime import datetime

# Batch size - smaller for quality triage
BATCH_SIZE = 20


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Fetch next batch of pending skills for LLM triage.
    
    Args:
        interaction_data: Input data (may contain batch_size)
        db_conn: Database connection
        
    Returns:
        Dict with pending skills and existing entities for matching
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        # Parse optional batch_size from input
        batch_size = BATCH_SIZE
        if isinstance(interaction_data, dict):
            batch_size = interaction_data.get('batch_size', BATCH_SIZE)
        
        # Get pending skills that need triage - use FOR UPDATE SKIP LOCKED to prevent
        # multiple runs from grabbing the same skills, and mark them as 'processing'
        cursor.execute("""
            WITH claimed AS (
                SELECT pending_id, entity_type, raw_value, source_context
                FROM entities_pending
                WHERE status = 'pending'
                  AND entity_type = 'skill'
                ORDER BY pending_id
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE entities_pending ep
            SET status = 'processing', processed_at = NOW()
            FROM claimed c
            WHERE ep.pending_id = c.pending_id
            RETURNING c.pending_id, c.entity_type, c.raw_value, c.source_context
        """, (batch_size,))
        
        rows = cursor.fetchall()
        db_conn.commit()  # Commit the status change
        
        if not rows:
            return {
                "status": "complete",
                "has_more": False,
                "batch_size": 0,
                "pending_skills": "",
                "pending_ids": [],
                "existing_skills": "",
                "message": "No pending skills to process"
            }
        
        # Format pending skills for LLM prompt
        # Format: "pending_id|raw_value"
        pending_skills = []
        pending_ids = []
        for row in rows:
            pending_id, entity_type, raw_value, source_context = row
            pending_ids.append(pending_id)
            pending_skills.append(f"{pending_id}|{raw_value}")
        
        pending_skills_text = "\n".join(pending_skills)
        
        # Get existing skill entities for ALIAS matching
        cursor.execute("""
            SELECT e.entity_id, e.canonical_name
            FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
            ORDER BY e.canonical_name
            LIMIT 100
        """)
        
        existing_skills = []
        for row in cursor.fetchall():
            entity_id, canonical_name = row
            existing_skills.append(f"{entity_id}|{canonical_name}")
        
        existing_skills_text = "\n".join(existing_skills) if existing_skills else "(no existing skills yet)"
        
        # Count remaining
        cursor.execute("""
            SELECT COUNT(*) FROM entities_pending
            WHERE status = 'pending' AND entity_type = 'skill'
        """)
        remaining = cursor.fetchone()[0]
        
        return {
            "status": "success",
            "has_more": remaining > batch_size,
            "batch_size": len(rows),
            "remaining": remaining,
            "pending_skills": pending_skills_text,
            "pending_ids": pending_ids,
            "existing_skills": existing_skills_text
        }
        
    except Exception as e:
        db_conn.rollback()
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import sys
    import json
    import os
    import psycopg2
    
    # Read input from stdin (passed by ScriptExecutor)
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except:
            pass
    
    # Load .env if exists
    env_file = os.path.join(os.path.dirname(__file__), '../../../.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    
    # Create DB connection
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025')
    )
    
    try:
        result = execute(input_data, conn)
        print(json.dumps(result))
    finally:
        conn.close()
