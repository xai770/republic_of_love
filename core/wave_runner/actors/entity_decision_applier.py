#!/usr/bin/env python3
"""
Entity Registry - Decision Applier (WF3005 Step 9)

Applies approved/auto_approved decisions from registry_decisions to entity_relationships.
Marks decisions as applied after successful insertion.

This is the final step that actually modifies the skill hierarchy.
"""

import json
from datetime import datetime


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Apply pending approved decisions to entity_relationships.
    
    Reads from registry_decisions where:
    - review_status IN ('approved', 'auto_approved')
    - applied_at IS NULL
    
    For each decision:
    1. INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, provenance)
    2. UPDATE registry_decisions SET applied_at = NOW()
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        # Get pending approved decisions
        cursor.execute("""
            SELECT 
                decision_id,
                subject_entity_id,
                target_entity_id,
                decision_type,
                confidence,
                reasoning
            FROM registry_decisions
            WHERE review_status IN ('approved', 'auto_approved')
              AND applied_at IS NULL
            ORDER BY decision_id
        """)
        
        pending = cursor.fetchall()
        
        if not pending:
            return {
                "status": "success",
                "message": "No pending decisions to apply",
                "applied": 0,
                "skipped": 0
            }
        
        applied = 0
        skipped = 0
        errors = []
        
        for row in pending:
            decision_id = row['decision_id']
            subject_entity_id = row['subject_entity_id']
            target_entity_id = row['target_entity_id']
            decision_type = row['decision_type']
            confidence = row['confidence']
            reasoning = row['reasoning']
            
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
                
                # Insert the relationship
                provenance = {
                    "source": "wf3005_decision_applier",
                    "decision_id": decision_id,
                    "decision_type": decision_type,
                    "confidence": float(confidence) if confidence else None,
                    "applied_at": datetime.now().isoformat()
                }
                
                cursor.execute("""
                    INSERT INTO entity_relationships 
                    (entity_id, related_entity_id, relationship, provenance)
                    VALUES (%s, %s, 'is_a', %s)
                """, (subject_entity_id, target_entity_id, json.dumps(provenance)))
                
                # Mark decision as applied
                cursor.execute("""
                    UPDATE registry_decisions
                    SET applied_at = NOW()
                    WHERE decision_id = %s
                """, (decision_id,))
                
                applied += 1
                
            except Exception as e:
                errors.append({
                    "decision_id": decision_id,
                    "subject_entity_id": subject_entity_id,
                    "target_entity_id": target_entity_id,
                    "error": str(e)
                })
                db_conn.rollback()
        
        db_conn.commit()
        
        return {
            "status": "success",
            "applied": applied,
            "skipped": skipped,
            "errors": errors if errors else None,
            "message": f"Applied {applied} decisions, skipped {skipped} (already exist)"
        }
        
    except Exception as e:
        db_conn.rollback()
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # CLI mode for testing
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from dotenv import load_dotenv
    
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', ''),
        cursor_factory=RealDictCursor
    )
    
    result = execute({}, db_conn=conn)
    print(json.dumps(result, indent=2))
    conn.close()
