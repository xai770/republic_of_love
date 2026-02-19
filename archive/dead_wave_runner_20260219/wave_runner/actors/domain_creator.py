#!/usr/bin/env python3
"""
Domain Creator - WF3006 Entity Classification

Creates new skill domains when none of the existing domains fit.
Includes rate limiting (Sandy's guardrail: 1 domain/week max).

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys


# Configuration - Sandy's guardrails
MAX_DOMAINS_PER_WEEK = 1
MIN_SKILLS_FOR_NEW_DOMAIN = 10


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


def find_similar_domains(cursor, name: str, threshold: float = 0.5) -> list:
    """Find similar existing domains using trigram similarity."""
    try:
        cursor.execute("""
            SELECT entity_id, canonical_name, 
                   similarity(canonical_name, %s) as sim
            FROM entities
            WHERE entity_type = 'skill_domain'
              AND status = 'active'
              AND canonical_name %% %s
            ORDER BY sim DESC
            LIMIT 3
        """, (name, name))
        
        rows = cursor.fetchall()
        return [{'entity_id': r[0], 'canonical_name': r[1], 'similarity': float(r[2])} 
                for r in rows if r[2] >= threshold]
    except Exception:
        # pg_trgm might not be installed
        return []


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Create a new skill domain.
    
    Args:
        interaction_data: Contains:
            - suggested_name: Domain name (snake_case)
            - suggested_description: What skills belong here
            - example_skills: List of example skill names
            - reasoning: Why new domain needed
            - requesting_skill_id: Skill that triggered this
        db_conn: Database connection
        
    Returns:
        Created domain info or rate limit notice
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        name = interaction_data.get('suggested_name', '').strip().lower().replace(' ', '_')
        description = interaction_data.get('suggested_description', '')
        example_skills = interaction_data.get('example_skills', [])
        reasoning = interaction_data.get('reasoning', '')
        requesting_skill_id = interaction_data.get('requesting_skill_id')
        
        if not name:
            return {"status": "error", "error": "suggested_name required"}
        
        # Check for exact match
        cursor.execute("""
            SELECT entity_id FROM entities
            WHERE entity_type = 'skill_domain'
              AND canonical_name = %s
        """, (name,))
        
        existing = cursor.fetchone()
        if existing:
            return {
                "status": "ALREADY_EXISTS",
                "domain_id": existing[0],
                "domain_name": name,
                "message": f"Domain '{name}' already exists"
            }
        
        # Check for similar domains
        similar = find_similar_domains(cursor, name)
        if similar:
            return {
                "status": "SIMILAR_EXISTS",
                "similar_domains": similar,
                "suggestion": f"Consider using '{similar[0]['canonical_name']}' instead",
                "message": f"Found {len(similar)} similar domain(s)"
            }
        
        # Check rate limit
        cursor.execute("SELECT count_domains_created_this_week()")
        domains_this_week = cursor.fetchone()[0]
        
        if domains_this_week >= MAX_DOMAINS_PER_WEEK:
            # Create proposal instead of domain
            cursor.execute("""
                INSERT INTO domain_split_proposals (
                    proposal_type, suggested_name, suggested_description,
                    example_skills, reasoning, confidence,
                    proposed_by, triggering_skill_id, status
                ) VALUES ('new_domain', %s, %s, %s, %s, 0.8, 'wf3006', %s, 'pending')
                RETURNING proposal_id
            """, (name, description, example_skills, reasoning, requesting_skill_id))
            
            proposal_id = cursor.fetchone()[0]
            db_conn.commit()
            
            return {
                "status": "RATE_LIMITED",
                "proposal_id": proposal_id,
                "domains_this_week": domains_this_week,
                "max_per_week": MAX_DOMAINS_PER_WEEK,
                "message": f"Domain creation rate limited. Proposal #{proposal_id} created for human review."
            }
        
        # Check orphan count justification
        cursor.execute("SELECT COUNT(*) FROM v_orphan_skills")
        orphan_count = cursor.fetchone()[0]
        
        # Actually create the domain
        cursor.execute("""
            INSERT INTO entities (
                entity_type, canonical_name, description, 
                status, created_by
            ) VALUES ('skill_domain', %s, %s, 'active', 'wf3006')
            RETURNING entity_id
        """, (name, description or reasoning[:500]))
        
        domain_id = cursor.fetchone()[0]
        
        # Log the creation in reasoning table
        if requesting_skill_id:
            cursor.execute("""
                INSERT INTO classification_reasoning (
                    entity_id, model, role, reasoning, 
                    suggested_domain, confidence
                ) VALUES (%s, 'wf3006', 'domain_creator', %s, %s, 0.8)
            """, (requesting_skill_id, 
                  f"Created new domain '{name}': {reasoning[:200]}", 
                  name))
        
        db_conn.commit()
        
        return {
            "status": "CREATED",
            "domain_id": domain_id,
            "domain_name": name,
            "description": description,
            "domains_this_week": domains_this_week + 1,
            "orphan_count": orphan_count,
            "message": f"New domain '{name}' created (ID: {domain_id})"
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
