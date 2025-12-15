#!/usr/bin/env python3
"""
Entity Orphan Fetcher - WF3005 Step 1

Fetches a batch of skill entities that have no domain classification.
Returns skills from `entities` table that have no 'is_a' relationship 
to a skill_domain entity in `entity_relationships`.

Author: Sandy
Date: December 8, 2025
"""

import json
from datetime import datetime

# Batch size for LLM processing - smaller batches = less dropout
# LLMs tend to skip items when given too many at once
BATCH_SIZE = 10


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Fetch next batch of unclassified skill entities.
    
    Args:
        interaction_data: Input data (may contain batch_size)
        db_conn: Database connection
        
    Returns:
        Dict with orphan skills for classification
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        # Parse optional batch_size from input
        batch_size = BATCH_SIZE
        if isinstance(interaction_data, dict):
            batch_size = interaction_data.get('batch_size', BATCH_SIZE)
        
        # Get skill entities not yet classified:
        # 1. No 'is_a' relationship to domain in entity_relationships
        # 2. No pending decision in registry_decisions
        cursor.execute("""
            SELECT e.entity_id, e.canonical_name, e.description
            FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er
                  JOIN entities domain ON er.related_entity_id = domain.entity_id
                  WHERE er.entity_id = e.entity_id
                    AND er.relationship = 'is_a'
                    AND domain.entity_type = 'skill_domain'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM registry_decisions rd
                  WHERE rd.subject_entity_id = e.entity_id
                    AND rd.decision_type = 'skill_domain_mapping'
              )
            ORDER BY e.entity_id
            LIMIT %s
        """, (batch_size,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "status": "complete",
                "has_more": False,
                "batch_size": 0,
                "orphan_skills": "",
                "skill_ids": [],
                "sample_skills": "",
                "message": "All skill entities have been classified"
            }
        
        # Format skills for LLM prompt
        # Format: "entity_id|name: description"
        orphan_skills = []
        skill_ids = []
        for row in rows:
            entity_id, name, description = row
            skill_ids.append(entity_id)
            desc_part = f" ({description[:50]}...)" if description and len(description) > 50 else (f" ({description})" if description else "")
            orphan_skills.append(f"{entity_id}|{name}{desc_part}")
        
        orphan_skills_text = "\n".join(orphan_skills)
        
        # Count remaining
        cursor.execute("""
            SELECT COUNT(*) FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relationships er
                  JOIN entities domain ON er.related_entity_id = domain.entity_id
                  WHERE er.entity_id = e.entity_id
                    AND er.relationship = 'is_a'
                    AND domain.entity_type = 'skill_domain'
              )
        """)
        remaining = cursor.fetchone()[0]
        
        # Get sample of existing skills for ALIAS matching (conv 9241 needs this)
        cursor.execute("""
            SELECT e.entity_id, e.canonical_name
            FROM entities e
            WHERE e.entity_type = 'skill'
              AND e.status = 'active'
              AND EXISTS (
                  SELECT 1 FROM entity_relationships er
                  WHERE er.entity_id = e.entity_id
                    AND er.relationship = 'is_a'
              )
            ORDER BY e.entity_id
            LIMIT 50
        """)
        sample_rows = cursor.fetchall()
        sample_skills = "\n".join([f"{r[0]}|{r[1]}" for r in sample_rows])
        
        return {
            "status": "success",
            "has_more": remaining > batch_size,
            "batch_size": len(rows),
            "remaining": remaining,
            "orphan_skills": orphan_skills_text,
            "skill_ids": skill_ids,
            "sample_skills": sample_skills
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
