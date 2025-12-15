#!/usr/bin/env python3
"""
Pending Skills Applier - WF3005 Step 0c

Parses LLM triage decisions for pending skills and applies them:
- NEW: Create new entity + alias, mark pending as 'approved'
- ALIAS: Create alias pointing to existing entity, mark as 'merged'
- SKIP: Mark pending as 'rejected'

Author: Sandy
Date: December 8, 2025
"""

import json
import re
from datetime import datetime


def _merge_graded_decisions(triage_text: str, grading_text: str) -> str:
    """
    Merge grading results with original triage decisions.
    
    Returns JSON lines where:
    - NEW/SKIP decisions pass through ungraded
    - ALIAS decisions with PASS use original triage
    - ALIAS decisions with FAIL use corrected decision from grader
    """
    # Parse original triage decisions
    triage_decisions = {}
    for line in triage_text.strip().split('\n'):
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            d = json.loads(line)
            if 'pending_id' in d:
                triage_decisions[d['pending_id']] = d
        except json.JSONDecodeError:
            continue
    
    # Parse grading results (only covers ALIAS decisions)
    grading_results = {}
    for line in grading_text.strip().split('\n'):
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            grade = json.loads(line)
            pending_id = grade.get('pending_id')
            if pending_id:
                grading_results[pending_id] = grade
        except json.JSONDecodeError:
            continue
    
    # Build result: all triage decisions, with grading corrections applied
    result_lines = []
    for pending_id, decision in triage_decisions.items():
        triage_type = decision.get('decision', '').upper()
        
        if triage_type in ('NEW', 'SKIP'):
            # NEW and SKIP pass through ungraded
            result_lines.append(json.dumps(decision))
        elif triage_type == 'ALIAS':
            # ALIAS decisions get grading check
            if pending_id in grading_results:
                grade = grading_results[pending_id]
                if grade.get('grade') == 'PASS':
                    # Use original triage decision
                    result_lines.append(json.dumps(decision))
                elif grade.get('grade') == 'FAIL':
                    # Use corrected decision
                    corrected = {
                        'pending_id': pending_id,
                        'decision': grade.get('corrected_decision', 'SKIP'),
                        'reasoning': grade.get('reasoning', 'Grader corrected decision')
                    }
                    if grade.get('canonical_name'):
                        corrected['canonical_name'] = grade['canonical_name']
                    if grade.get('target_entity_id'):
                        corrected['target_entity_id'] = grade['target_entity_id']
                    result_lines.append(json.dumps(corrected))
            else:
                # No grading for this ALIAS (shouldn't happen, but pass through)
                result_lines.append(json.dumps(decision))
        else:
            # Unknown decision type, pass through
            result_lines.append(json.dumps(decision))
    
    return '\n'.join(result_lines)


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Apply pending skill triage decisions.
    
    Parses JSON decisions from parent interaction output and:
    - Creates entities for NEW decisions
    - Creates aliases for ALIAS decisions
    - Marks rejected for SKIP decisions
    
    Args:
        interaction_data: Contains interaction_id to find parent
        db_conn: Database connection
        
    Returns:
        Summary of applied decisions
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        cursor = db_conn.cursor()
        
        # Get triage and grading outputs from input data
        # (provided by wave_runner as conversation outputs)
        triage_text = interaction_data.get('conversation_9244_output', '')
        grading_text = interaction_data.get('conversation_9252_output', '')
        
        # Also check parent_response as fallback (direct parent output)
        if not grading_text and interaction_data.get('parent_response'):
            grading_text = interaction_data.get('parent_response', '')
        
        if not triage_text:
            return {"status": "error", "error": "No triage output (conversation_9244_output) in input"}
        
        # Build verified decisions by merging grading with triage
        response_text = _merge_graded_decisions(triage_text, grading_text)
        
        # Parse decisions from response (JSON objects, one per line)
        decisions = []
        
        # Handle both raw JSON and markdown code blocks
        clean_response = response_text
        if '```json' in clean_response:
            clean_response = re.sub(r'```json\s*', '', clean_response)
            clean_response = re.sub(r'```\s*', '', clean_response)
        elif '```' in clean_response:
            clean_response = re.sub(r'```\s*', '', clean_response)
        
        for line in clean_response.strip().split('\n'):
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
                "message": "No decisions parsed from LLM output",
                "applied": 0,
                "raw_response": response_text[:300]
            }
        
        new_count = 0
        alias_count = 0
        skip_count = 0
        errors = []
        
        for decision in decisions:
            try:
                pending_id = decision.get('pending_id')
                action = decision.get('decision', '').upper()
                confidence = decision.get('confidence', 0.8)
                reasoning = decision.get('reasoning', '')
                
                if not pending_id:
                    errors.append(f"Missing pending_id: {decision}")
                    continue
                
                # Get the raw_value for this pending_id (accept both 'pending' and 'processing' status)
                cursor.execute("""
                    SELECT raw_value FROM entities_pending 
                    WHERE pending_id = %s AND status IN ('pending', 'processing')
                """, (pending_id,))
                
                pending_row = cursor.fetchone()
                if not pending_row:
                    errors.append(f"Pending {pending_id} not found or already processed")
                    continue
                
                raw_value = pending_row[0]
                
                if action == 'NEW':
                    # Create new entity
                    canonical_name = decision.get('canonical_name', raw_value)
                    
                    # Check if entity with this name already exists
                    cursor.execute("""
                        SELECT entity_id FROM entities 
                        WHERE LOWER(canonical_name) = LOWER(%s) AND entity_type = 'skill'
                    """, (canonical_name,))
                    
                    existing = cursor.fetchone()
                    if existing:
                        # Already exists - treat as ALIAS
                        target_entity_id = existing[0]
                        # Create alias if not exists
                        cursor.execute("""
                            INSERT INTO entity_aliases (entity_id, alias)
                            VALUES (%s, %s)
                            ON CONFLICT (alias, language) DO NOTHING
                        """, (target_entity_id, raw_value.lower()))
                        
                        # Mark as merged
                        cursor.execute("""
                            UPDATE entities_pending
                            SET status = 'merged',
                                resolved_entity_id = %s,
                                resolution_notes = %s,
                                processed_at = NOW(),
                                processed_by = 'wf3005_pending_applier'
                            WHERE pending_id = %s
                        """, (target_entity_id, f"Auto-merged: {reasoning}", pending_id))
                        
                        alias_count += 1
                    else:
                        # Create new entity
                        cursor.execute("""
                            INSERT INTO entities (canonical_name, entity_type, status, created_at)
                            VALUES (%s, 'skill', 'active', NOW())
                            RETURNING entity_id
                        """, (canonical_name,))
                        
                        new_entity_id = cursor.fetchone()[0]
                        
                        # Create alias (lowercase)
                        cursor.execute("""
                            INSERT INTO entity_aliases (entity_id, alias)
                            VALUES (%s, %s)
                            ON CONFLICT (alias, language) DO NOTHING
                        """, (new_entity_id, raw_value.lower()))
                        
                        # Also add canonical as alias if different
                        if raw_value.lower() != canonical_name.lower():
                            cursor.execute("""
                                INSERT INTO entity_aliases (entity_id, alias)
                                VALUES (%s, %s)
                                ON CONFLICT (alias, language) DO NOTHING
                            """, (new_entity_id, canonical_name.lower()))
                        
                        # Mark pending as approved
                        cursor.execute("""
                            UPDATE entities_pending
                            SET status = 'approved',
                                resolved_entity_id = %s,
                                resolution_notes = %s,
                                processed_at = NOW(),
                                processed_by = 'wf3005_pending_applier'
                            WHERE pending_id = %s
                        """, (new_entity_id, reasoning, pending_id))
                        
                        new_count += 1
                
                elif action == 'ALIAS':
                    target_entity_id = decision.get('target_entity_id')
                    
                    if not target_entity_id:
                        errors.append(f"ALIAS decision missing target_entity_id: {decision}")
                        continue
                    
                    # Verify target exists
                    cursor.execute("""
                        SELECT 1 FROM entities WHERE entity_id = %s
                    """, (target_entity_id,))
                    
                    if not cursor.fetchone():
                        errors.append(f"Target entity {target_entity_id} not found")
                        continue
                    
                    # Create alias
                    cursor.execute("""
                        INSERT INTO entity_aliases (entity_id, alias)
                        VALUES (%s, %s)
                        ON CONFLICT (alias, language) DO NOTHING
                    """, (target_entity_id, raw_value.lower()))
                    
                    # Mark as merged
                    cursor.execute("""
                        UPDATE entities_pending
                        SET status = 'merged',
                            resolved_entity_id = %s,
                            resolution_notes = %s,
                            processed_at = NOW(),
                            processed_by = 'wf3005_pending_applier'
                        WHERE pending_id = %s
                    """, (target_entity_id, reasoning, pending_id))
                    
                    alias_count += 1
                
                elif action == 'SKIP':
                    # Mark as rejected
                    cursor.execute("""
                        UPDATE entities_pending
                        SET status = 'rejected',
                            resolution_notes = %s,
                            processed_at = NOW(),
                            processed_by = 'wf3005_pending_applier'
                        WHERE pending_id = %s
                    """, (reasoning, pending_id))
                    
                    skip_count += 1
                
                else:
                    errors.append(f"Unknown action '{action}' for pending_id {pending_id}")
            
            except Exception as e:
                errors.append(f"Error processing decision: {e}")
                continue
        
        db_conn.commit()
        
        total_applied = new_count + alias_count + skip_count
        
        return {
            "status": "success" if total_applied > 0 else "warning",
            "total_parsed": len(decisions),
            "new_entities": new_count,
            "aliases_created": alias_count,
            "rejected": skip_count,
            "errors": errors[:5] if errors else []
        }
        
    except Exception as e:
        db_conn.rollback()
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import sys
    import json
    import os
    import psycopg2
    
    # Read input from stdin
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
