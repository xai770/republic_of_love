#!/usr/bin/env python3
"""
Classification Resetter - WF3006 Entity Classification

Resets a skill's classification to orphan status for reclassification.
Marks previous reasoning as overturned with explanation.

Uses: Manual corrections, learning from mistakes, taxonomy changes.

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys
from datetime import datetime


def get_db_connection():
    """Get database connection using standard env vars."""
    import psycopg2
    
    env_file = os.path.join(os.path.dirname(__file__), '../../../.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'base_yoga_secure_2025')
    )


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Reset a skill's classification for reclassification.
    
    Args:
        interaction_data: Contains:
            - entity_id: Skill to reset
            - reason: Why resetting (for learning)
            - reset_by: Who initiated (human:name or wf3006)
        db_conn: Database connection
        
    Returns:
        Reset status and updated orphan count
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        entity_id = interaction_data.get('entity_id')
        reason = interaction_data.get('reason', 'Manual reset requested')
        reset_by = interaction_data.get('reset_by', 'human:unknown')
        
        if not entity_id:
            return {"status": "error", "error": "entity_id required"}
        
        # Get current classification info before reset
        cursor.execute("""
            SELECT er.related_entity_id, d.canonical_name as domain_name,
                   rd.decision_id, rd.confidence, rd.reasoning
            FROM entity_relationships er
            JOIN entities d ON er.related_entity_id = d.entity_id
            LEFT JOIN registry_decisions rd ON er.entity_id = rd.subject_entity_id
                AND rd.target_entity_id = er.related_entity_id
            WHERE er.entity_id = %s 
              AND er.relationship = 'is_a'
              AND d.entity_type = 'skill_domain'
        """, (entity_id,))
        
        current = cursor.fetchone()
        
        if not current:
            return {
                "status": "already_orphan",
                "entity_id": entity_id,
                "message": "Skill is already an orphan (no domain assignment)"
            }
        
        domain_id, domain_name, decision_id, confidence, original_reasoning = current
        
        # Get skill name
        cursor.execute("""
            SELECT canonical_name FROM entities WHERE entity_id = %s
        """, (entity_id,))
        skill_name = cursor.fetchone()[0]
        
        # Step 1: Mark previous reasoning as overturned
        cursor.execute("""
            UPDATE classification_reasoning
            SET was_overturned = TRUE,
                overturn_reason = %s
            WHERE entity_id = %s
              AND was_overturned = FALSE
        """, (reason, entity_id))
        overturned_count = cursor.rowcount
        
        # Step 2: Add reset reasoning entry
        cursor.execute("""
            INSERT INTO classification_reasoning (
                entity_id, decision_id, model, role,
                reasoning, confidence, suggested_domain
            ) VALUES (%s, %s, %s, 'reset', %s, 0, NULL)
        """, (entity_id, decision_id, reset_by, 
              f"Reset from '{domain_name}': {reason}"))
        
        # Step 3: Delete the relationship
        cursor.execute("""
            DELETE FROM entity_relationships
            WHERE entity_id = %s 
              AND related_entity_id = %s
              AND relationship = 'is_a'
        """, (entity_id, domain_id))
        
        # Step 4: Update decision status to rejected
        if decision_id:
            cursor.execute("""
                UPDATE registry_decisions
                SET review_status = 'rejected',
                    review_notes = COALESCE(review_notes, '') || 
                                   E'\n[RESET ' || NOW()::text || '] ' || %s,
                    applied_at = NULL
                WHERE decision_id = %s
            """, (reason, decision_id))
        
        db_conn.commit()
        
        # Get new orphan count
        cursor.execute("SELECT COUNT(*) FROM v_orphan_skills")
        orphan_count = cursor.fetchone()[0]
        
        return {
            "status": "reset",
            "entity_id": entity_id,
            "skill_name": skill_name,
            "previous_domain": domain_name,
            "reset_reason": reason,
            "reset_by": reset_by,
            "reasoning_overturned": overturned_count,
            "orphan_count": orphan_count,
            "message": f"'{skill_name}' reset from '{domain_name}' - now orphan"
        }
        
    except Exception as e:
        if db_conn:
            db_conn.rollback()
        return {"status": "error", "error": str(e)}
    
    finally:
        if close_conn and db_conn:
            db_conn.close()


if __name__ == "__main__":
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except:
            pass
    
    # Also accept command line args for testing
    if len(sys.argv) > 1:
        input_data['entity_id'] = int(sys.argv[1])
    if len(sys.argv) > 2:
        input_data['reason'] = sys.argv[2]
    
    result = execute(input_data)
    print(json.dumps(result, indent=2, default=str))
