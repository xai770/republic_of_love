#!/usr/bin/env python3
"""
Entity Decision Saver - WF3005 Step 9

Parses validated skill classification decisions from parent interaction
and saves them to registry_decisions.

Since script actors receive only `interaction.input` (not parent outputs),
this script queries the parent interaction's output directly from DB.

Author: Sandy
Date: December 8, 2025
"""

import json
import re
from datetime import datetime


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Parse decisions from parent interaction and save to registry_decisions.
    
    Queries parent_interaction_id to get validated output, then parses
    and saves decisions.
    
    Args:
        interaction_data: Contains interaction_id to find parent
        db_conn: Database connection
        
    Returns:
        Summary of saved decisions
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        # Get interaction_id from input
        interaction_id = interaction_data.get('interaction_id')
        if not interaction_id:
            return {"status": "error", "error": "No interaction_id in input"}
        
        # Get parent interaction's output (c4_validate)
        # But we actually want the c2_classify output (the classifier) which has clean data
        # The debate panel (triage/skeptic/optimist/editor) filters too much
        # Walk up to find c2_classify output
        cursor.execute("""
            WITH RECURSIVE ancestors AS (
                -- Start from current interaction
                SELECT interaction_id, parent_interaction_id, conversation_id, output, 0 as depth
                FROM interactions
                WHERE interaction_id = %s
                
                UNION ALL
                
                -- Walk up the chain
                SELECT i.interaction_id, i.parent_interaction_id, i.conversation_id, i.output, a.depth + 1
                FROM interactions i
                JOIN ancestors a ON i.interaction_id = a.parent_interaction_id
                WHERE a.depth < 10
            )
            SELECT a.output
            FROM ancestors a
            JOIN conversations c ON a.conversation_id = c.conversation_id
            WHERE c.canonical_name = 'w3005_c2_classify'
        """, (interaction_id,))
        
        row = cursor.fetchone()
        if not row or not row[0]:
            return {"status": "error", "error": "No parent output found"}
        
        parent_output = row[0]
        
        # The c4_validate output has format:
        # {"model": "...", "response": "...", "latency_ms": ...}
        # where response contains JSON lines with validated decisions
        response_text = parent_output.get('response', '')
        
        # Parse decisions from response (multiple JSON objects per line)
        decisions = []
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('{'):
                continue
            try:
                decision = json.loads(line)
                decisions.append(decision)
            except json.JSONDecodeError:
                continue
        
        if not decisions:
            return {
                "status": "warning",
                "message": "No decisions parsed from parent output",
                "saved": 0,
                "raw_response": response_text[:200]
            }
        
        saved = 0
        skipped = 0
        errors = []
        
        for decision in decisions:
            try:
                # Map from classifier output format to registry_decisions format
                # Classifier outputs: entity_id, parent_id (domain_id), confidence, reasoning
                skill_id = decision.get('entity_id')
                domain_id = decision.get('parent_id')
                confidence = decision.get('confidence', 0.85)
                reasoning = decision.get('reasoning', '')
                model = 'gemma3:4b'  # The classifier model
                
                if not skill_id or not domain_id:
                    errors.append(f"Missing entity_id or parent_id: {decision}")
                    continue
                
                # Verify entities exist
                cursor.execute("SELECT 1 FROM entities WHERE entity_id = %s", (skill_id,))
                if not cursor.fetchone():
                    errors.append(f"Skill entity {skill_id} not found")
                    continue
                
                cursor.execute("SELECT 1 FROM entities WHERE entity_id = %s", (domain_id,))
                if not cursor.fetchone():
                    errors.append(f"Domain entity {domain_id} not found")
                    continue
                
                # Check if decision already exists
                cursor.execute("""
                    SELECT decision_id FROM registry_decisions 
                    WHERE subject_entity_id = %s 
                      AND target_entity_id = %s 
                      AND decision_type = 'skill_domain_mapping'
                """, (skill_id, domain_id))
                
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Auto-approve high confidence decisions (>=0.85)
                # Lower confidence requires human review
                AUTO_APPROVE_THRESHOLD = 0.85
                review_status = 'auto_approved' if confidence >= AUTO_APPROVE_THRESHOLD else 'pending'
                
                # Insert new decision
                cursor.execute("""
                    INSERT INTO registry_decisions (
                        decision_type,
                        subject_entity_id,
                        target_entity_id,
                        model,
                        temperature,
                        confidence,
                        reasoning,
                        review_status
                    ) VALUES (
                        'skill_domain_mapping',
                        %s, %s, %s, 0.0, %s, %s, %s
                    )
                """, (skill_id, domain_id, model, confidence, reasoning, review_status))
                
                saved += 1
                
            except Exception as e:
                errors.append(f"Error saving decision: {e}")
                db_conn.rollback()
        
        db_conn.commit()
        
        result = {
            "status": "success" if saved > 0 else "warning",
            "saved": saved,
            "skipped": skipped,
            "total_parsed": len(decisions)
        }
        
        if errors:
            result["errors"] = errors[:5]  # Limit output
        
        return result
        
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
