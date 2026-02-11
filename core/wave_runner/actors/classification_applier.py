#!/usr/bin/env python3
"""
Classification Applier - WF3006 Entity Classification

Applies approved/auto_approved decisions to entity_relationships.
This creates the actual skill->domain relationships.

Separate from entity_decision_applier to:
1. Use standard cursor (not RealDictCursor)
2. Be standalone callable
3. Log applied decisions for audit

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
        password=os.getenv('DB_PASSWORD', '')
    )


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Apply pending approved decisions to entity_relationships.
    
    Args:
        interaction_data: Optional filters:
            - decision_ids: List of specific decision IDs to apply
            - batch_size: Max decisions to process (default 100)
        db_conn: Database connection
        
    Returns:
        Summary of applied decisions
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        # Parse options
        decision_ids = interaction_data.get('decision_ids')
        batch_size = interaction_data.get('batch_size', 100)
        
        # Build query for pending decisions
        if decision_ids:
            cursor.execute("""
                SELECT 
                    decision_id,
                    subject_entity_id,
                    target_entity_id,
                    decision_type,
                    confidence,
                    reasoning,
                    model
                FROM registry_decisions
                WHERE decision_id = ANY(%s)
                  AND review_status IN ('approved', 'auto_approved')
                  AND applied_at IS NULL
                ORDER BY decision_id
            """, (decision_ids,))
        else:
            cursor.execute("""
                SELECT 
                    decision_id,
                    subject_entity_id,
                    target_entity_id,
                    decision_type,
                    confidence,
                    reasoning,
                    model
                FROM registry_decisions
                WHERE review_status IN ('approved', 'auto_approved')
                  AND applied_at IS NULL
                  AND decision_type = 'skill_domain_mapping'
                ORDER BY decision_id
                LIMIT %s
            """, (batch_size,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "status": "success",
                "message": "No pending decisions to apply",
                "applied": 0,
                "skipped": 0,
                "remaining": 0
            }
        
        applied = 0
        skipped = 0
        errors = []
        applied_details = []
        
        for row in rows:
            decision_id = row[0]
            subject_entity_id = row[1]
            target_entity_id = row[2]
            decision_type = row[3]
            confidence = row[4]
            reasoning = row[5]
            model = row[6]
            
            try:
                # Check if relationship already exists
                cursor.execute("""
                    SELECT 1 FROM entity_relationships
                    WHERE entity_id = %s 
                      AND related_entity_id = %s 
                      AND relationship = 'is_a'
                """, (subject_entity_id, target_entity_id))
                
                if cursor.fetchone():
                    # Already exists - just mark as applied
                    cursor.execute("""
                        UPDATE registry_decisions
                        SET applied_at = NOW(),
                            review_notes = COALESCE(review_notes, '') || ' [Already existed]'
                        WHERE decision_id = %s
                    """, (decision_id,))
                    skipped += 1
                    continue
                
                # Build provenance
                provenance = {
                    "source": "wf3006_classification_applier",
                    "decision_id": decision_id,
                    "decision_type": decision_type,
                    "model": model,
                    "confidence": float(confidence) if confidence else None,
                    "applied_at": datetime.now().isoformat()
                }
                
                # Insert the relationship
                cursor.execute("""
                    INSERT INTO entity_relationships 
                    (entity_id, related_entity_id, relationship, provenance, created_by)
                    VALUES (%s, %s, 'is_a', %s, 'wf3006')
                """, (subject_entity_id, target_entity_id, json.dumps(provenance)))
                
                # Mark decision as applied
                cursor.execute("""
                    UPDATE registry_decisions
                    SET applied_at = NOW()
                    WHERE decision_id = %s
                """, (decision_id,))
                
                # Get entity names for logging
                cursor.execute("""
                    SELECT 
                        (SELECT canonical_name FROM entities WHERE entity_id = %s) as skill_name,
                        (SELECT canonical_name FROM entities WHERE entity_id = %s) as domain_name
                """, (subject_entity_id, target_entity_id))
                names = cursor.fetchone()
                
                applied_details.append({
                    "decision_id": decision_id,
                    "skill": names[0],
                    "domain": names[1],
                    "confidence": float(confidence) if confidence else None
                })
                
                applied += 1
                
            except Exception as e:
                errors.append({
                    "decision_id": decision_id,
                    "subject_entity_id": subject_entity_id,
                    "target_entity_id": target_entity_id,
                    "error": str(e)
                })
                # Don't rollback individual errors - continue processing
        
        db_conn.commit()
        
        # Count remaining
        cursor.execute("""
            SELECT COUNT(*) FROM registry_decisions
            WHERE review_status IN ('approved', 'auto_approved')
              AND applied_at IS NULL
              AND decision_type = 'skill_domain_mapping'
        """)
        remaining = cursor.fetchone()[0]
        
        return {
            "status": "success" if applied > 0 else "no_changes",
            "applied": applied,
            "skipped": skipped,
            "errors": len(errors),
            "remaining": remaining,
            "applied_details": applied_details[:10],  # Limit output
            "error_details": errors[:5] if errors else None
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
        except (json.JSONDecodeError, ValueError):
            pass
    
    result = execute(input_data)
    print(json.dumps(result, indent=2, default=str))
