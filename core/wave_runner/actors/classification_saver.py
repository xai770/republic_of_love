#!/usr/bin/env python3
"""
Classification Saver - WF3006 Entity Classification

Enhanced decision saver that:
1. Saves decision to registry_decisions (with auto_approve threshold)
2. Saves reasoning chain to classification_reasoning (for learning)
3. Handles NEW_DOMAIN and SUGGEST_SPLIT actions
4. Rate limits domain creation (1 per week)

Author: Arden
Date: December 15, 2025
"""

import json
import re
import os
import sys
from datetime import datetime

# Configuration
AUTO_APPROVE_THRESHOLD = 0.85  # Auto-approve decisions >= this confidence
MAX_DOMAINS_PER_WEEK = 1       # Sandy's guardrail
MIN_SKILLS_FOR_NEW_DOMAIN = 10 # Sandy's guardrail - orphans needed before new domain


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


def parse_llm_decision(response_text: str) -> dict:
    """
    Parse LLM classification response.
    
    Expected JSON format:
    {
        "entity_id": 12345,
        "action": "CLASSIFY",  # or "NEW_DOMAIN", "SUGGEST_SPLIT", "SKIP"
        "domain": "technology",
        "confidence": 0.92,
        "reasoning": "..."
    }
    """
    # Try to find JSON in response
    try:
        # Look for JSON block
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    # Try parsing the whole response
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
    return None


def save_reasoning(cursor, entity_id: int, decision_id: int, 
                   model: str, role: str, reasoning: str,
                   confidence: float, suggested_domain: str,
                   workflow_run_id: int = None, interaction_id: int = None):
    """Save reasoning to classification_reasoning table."""
    cursor.execute("""
        INSERT INTO classification_reasoning (
            entity_id, decision_id, model, role,
            reasoning, confidence, suggested_domain,
            workflow_run_id, interaction_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING reasoning_id
    """, (entity_id, decision_id, model, role, 
          reasoning, confidence, suggested_domain,
          workflow_run_id, interaction_id))
    
    return cursor.fetchone()[0]


def handle_classify_action(cursor, decision: dict, model: str,
                           workflow_run_id: int = None, 
                           interaction_id: int = None) -> dict:
    """Handle standard CLASSIFY action - save decision and reasoning."""
    entity_id = decision.get('entity_id')
    domain_name = decision.get('domain')
    confidence = decision.get('confidence', 0.80)
    reasoning = decision.get('reasoning', '')
    
    # Look up domain entity by name
    cursor.execute("""
        SELECT entity_id FROM entities
        WHERE entity_type = 'skill_domain'
          AND canonical_name = %s
          AND status = 'active'
    """, (domain_name,))
    
    row = cursor.fetchone()
    if not row:
        return {
            "status": "error",
            "error": f"Domain '{domain_name}' not found",
            "entity_id": entity_id
        }
    
    domain_id = row[0]
    
    # Check if decision already exists
    cursor.execute("""
        SELECT decision_id FROM registry_decisions 
        WHERE subject_entity_id = %s 
          AND decision_type = 'skill_domain_mapping'
    """, (entity_id,))
    
    existing = cursor.fetchone()
    if existing:
        return {
            "status": "skipped",
            "message": "Decision already exists",
            "entity_id": entity_id,
            "decision_id": existing[0]
        }
    
    # Determine review status
    review_status = 'auto_approved' if confidence >= AUTO_APPROVE_THRESHOLD else 'pending'
    
    # Insert decision
    cursor.execute("""
        INSERT INTO registry_decisions (
            decision_type, subject_entity_id, target_entity_id,
            model, temperature, confidence, reasoning, review_status
        ) VALUES (
            'skill_domain_mapping', %s, %s, %s, 0.0, %s, %s, %s
        )
        RETURNING decision_id
    """, (entity_id, domain_id, model, confidence, reasoning, review_status))
    
    decision_id = cursor.fetchone()[0]
    
    # Save reasoning for learning
    save_reasoning(
        cursor, entity_id, decision_id, model, 'classifier',
        reasoning, confidence, domain_name,
        workflow_run_id, interaction_id
    )
    
    return {
        "status": "saved",
        "action": "CLASSIFY",
        "entity_id": entity_id,
        "decision_id": decision_id,
        "domain": domain_name,
        "domain_id": domain_id,
        "confidence": confidence,
        "review_status": review_status
    }


def handle_new_domain_action(cursor, decision: dict, model: str,
                              workflow_run_id: int = None) -> dict:
    """Handle NEW_DOMAIN action - rate limited domain creation."""
    entity_id = decision.get('entity_id')
    suggested_name = decision.get('suggested_domain_name', decision.get('domain'))
    reasoning = decision.get('reasoning', '')
    confidence = decision.get('confidence', 0.70)
    
    # Check rate limit
    cursor.execute("SELECT count_domains_created_this_week()")
    domains_this_week = cursor.fetchone()[0]
    
    if domains_this_week >= MAX_DOMAINS_PER_WEEK:
        # Create proposal instead
        cursor.execute("""
            INSERT INTO domain_split_proposals (
                proposal_type, suggested_name, reasoning, confidence,
                proposed_by, triggering_skill_id, workflow_run_id
            ) VALUES ('new_domain', %s, %s, %s, 'wf3006', %s, %s)
            RETURNING proposal_id
        """, (suggested_name, reasoning, confidence, entity_id, workflow_run_id))
        
        proposal_id = cursor.fetchone()[0]
        
        return {
            "status": "rate_limited",
            "action": "NEW_DOMAIN",
            "entity_id": entity_id,
            "message": f"Domain creation rate limited ({domains_this_week}/{MAX_DOMAINS_PER_WEEK} this week)",
            "proposal_id": proposal_id
        }
    
    # Check orphan count for new domain justification
    cursor.execute("SELECT COUNT(*) FROM v_orphan_skills")
    orphan_count = cursor.fetchone()[0]
    
    if orphan_count < MIN_SKILLS_FOR_NEW_DOMAIN:
        return {
            "status": "rejected",
            "action": "NEW_DOMAIN",
            "entity_id": entity_id,
            "message": f"Not enough orphans ({orphan_count}/{MIN_SKILLS_FOR_NEW_DOMAIN}) to justify new domain"
        }
    
    # Create the new domain
    cursor.execute("""
        INSERT INTO entities (
            entity_type, canonical_name, description, status, created_by
        ) VALUES ('skill_domain', %s, %s, 'active', 'wf3006')
        RETURNING entity_id
    """, (suggested_name, reasoning[:500]))
    
    new_domain_id = cursor.fetchone()[0]
    
    # Now classify the skill into the new domain
    cursor.execute("""
        INSERT INTO registry_decisions (
            decision_type, subject_entity_id, target_entity_id,
            model, temperature, confidence, reasoning, review_status
        ) VALUES (
            'skill_domain_mapping', %s, %s, %s, 0.0, %s, %s, 'pending'
        )
        RETURNING decision_id
    """, (entity_id, new_domain_id, model, confidence, reasoning))
    
    decision_id = cursor.fetchone()[0]
    
    return {
        "status": "created",
        "action": "NEW_DOMAIN",
        "entity_id": entity_id,
        "decision_id": decision_id,
        "new_domain_id": new_domain_id,
        "domain": suggested_name,
        "review_status": "pending"  # New domains always need review
    }


def handle_suggest_split_action(cursor, decision: dict, 
                                 workflow_run_id: int = None) -> dict:
    """Handle SUGGEST_SPLIT action - always requires human approval."""
    entity_id = decision.get('entity_id')
    parent_domain = decision.get('parent_domain')
    suggested_children = decision.get('suggested_children', [])
    reasoning = decision.get('reasoning', '')
    confidence = decision.get('confidence', 0.70)
    
    # Count affected skills
    cursor.execute("""
        SELECT COUNT(*) FROM entity_relationships er
        JOIN entities d ON er.related_entity_id = d.entity_id
        WHERE d.canonical_name = %s AND er.relationship = 'is_a'
    """, (parent_domain,))
    affected_count = cursor.fetchone()[0]
    
    # Create proposal for human review
    cursor.execute("""
        INSERT INTO domain_split_proposals (
            proposal_type, parent_domain, suggested_children,
            affected_skill_count, reasoning, confidence,
            proposed_by, triggering_skill_id, workflow_run_id
        ) VALUES ('split', %s, %s, %s, %s, %s, 'wf3006', %s, %s)
        RETURNING proposal_id
    """, (parent_domain, suggested_children, affected_count,
          reasoning, confidence, entity_id, workflow_run_id))
    
    proposal_id = cursor.fetchone()[0]
    
    return {
        "status": "proposal_created",
        "action": "SUGGEST_SPLIT",
        "entity_id": entity_id,
        "proposal_id": proposal_id,
        "parent_domain": parent_domain,
        "suggested_children": suggested_children,
        "affected_skills": affected_count
    }


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Parse and save classification decision with reasoning.
    
    Args:
        interaction_data: Contains:
            - response: LLM response text with decision JSON
            - model: Model that made the decision
            - workflow_run_id: Optional run ID for tracking
            - interaction_id: Optional interaction ID
        db_conn: Database connection
        
    Returns:
        Result of saving operation
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        # Parse input
        response_text = interaction_data.get('response', '')
        model = interaction_data.get('model', 'gemma3:4b')
        workflow_run_id = interaction_data.get('workflow_run_id')
        interaction_id = interaction_data.get('interaction_id')
        
        # Parse decisions - may be multiple per response
        decisions = []
        
        # Try to parse multiple JSON objects (one per line or array)
        for line in response_text.strip().split('\n'):
            parsed = parse_llm_decision(line)
            if parsed:
                decisions.append(parsed)
        
        # Also try parsing as array
        if not decisions:
            try:
                arr = json.loads(response_text)
                if isinstance(arr, list):
                    decisions = arr
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Try single JSON in whole response
        if not decisions:
            parsed = parse_llm_decision(response_text)
            if parsed:
                decisions = [parsed]
        
        if not decisions:
            return {
                "status": "error",
                "error": "Could not parse any decisions from response",
                "raw_response": response_text[:500]
            }
        
        # Process each decision
        results = []
        for decision in decisions:
            action = decision.get('action', 'CLASSIFY').upper()
            
            if action == 'CLASSIFY':
                result = handle_classify_action(
                    cursor, decision, model,
                    workflow_run_id, interaction_id
                )
            elif action == 'NEW_DOMAIN':
                result = handle_new_domain_action(
                    cursor, decision, model, workflow_run_id
                )
            elif action == 'SUGGEST_SPLIT':
                result = handle_suggest_split_action(
                    cursor, decision, workflow_run_id
                )
            elif action == 'SKIP':
                result = {
                    "status": "skipped",
                    "action": "SKIP",
                    "entity_id": decision.get('entity_id'),
                    "reason": decision.get('reasoning', 'Model chose to skip')
                }
            else:
                result = {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                    "entity_id": decision.get('entity_id')
                }
            
            results.append(result)
        
        db_conn.commit()
        
        # Summarize
        saved = sum(1 for r in results if r.get('status') == 'saved')
        created = sum(1 for r in results if r.get('status') == 'created')
        proposals = sum(1 for r in results if r.get('status') == 'proposal_created')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        errors = sum(1 for r in results if r.get('status') == 'error')
        
        return {
            "status": "success" if (saved + created + proposals) > 0 else "warning",
            "total_processed": len(results),
            "saved": saved,
            "domains_created": created,
            "proposals_created": proposals,
            "skipped": skipped,
            "errors": errors,
            "results": results
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
