#!/usr/bin/env python3
"""
Domain Proposal Applier - WF3006 Entity Classification

Applies approved domain proposals:
- For NEW_DOMAIN: Creates the domain entity
- For SPLIT: Creates child domains and queues skill reassignment

Only processes proposals that have been approved by the grader.

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys


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


def apply_new_domain(cursor, proposal: dict) -> dict:
    """Create a new domain from an approved proposal."""
    name = proposal['suggested_name']
    description = proposal.get('suggested_description', '')
    
    # Check if already exists (idempotent)
    cursor.execute("""
        SELECT entity_id FROM entities
        WHERE entity_type = 'skill_domain' AND canonical_name = %s
    """, (name,))
    
    existing = cursor.fetchone()
    if existing:
        return {
            "status": "already_exists",
            "domain_id": existing[0],
            "domain_name": name
        }
    
    # Create the domain
    cursor.execute("""
        INSERT INTO entities (
            entity_type, canonical_name, description, 
            status, created_by
        ) VALUES ('skill_domain', %s, %s, 'active', 'wf3006_grader')
        RETURNING entity_id
    """, (name, description or proposal.get('reasoning', '')[:500]))
    
    domain_id = cursor.fetchone()[0]
    
    return {
        "status": "created",
        "domain_id": domain_id,
        "domain_name": name
    }


def apply_split(cursor, proposal: dict) -> dict:
    """
    Apply a domain split.
    Creates child domains and marks parent for deprecation.
    Skills remain in parent until reclassified.
    """
    parent_name = proposal['parent_domain']
    children = proposal.get('suggested_children', [])
    
    if not children:
        return {"status": "error", "error": "No children specified"}
    
    # Get parent domain ID
    cursor.execute("""
        SELECT entity_id FROM entities
        WHERE entity_type = 'skill_domain' AND canonical_name = %s
    """, (parent_name,))
    
    parent_row = cursor.fetchone()
    if not parent_row:
        return {"status": "error", "error": f"Parent domain '{parent_name}' not found"}
    
    parent_id = parent_row[0]
    
    # Create child domains
    created_children = []
    for child_name in children:
        cursor.execute("""
            INSERT INTO entities (
                entity_type, canonical_name, description, 
                status, created_by
            ) VALUES ('skill_domain', %s, %s, 'active', 'wf3006_grader')
            ON CONFLICT (entity_type, canonical_name) DO NOTHING
            RETURNING entity_id
        """, (child_name, f"Split from {parent_name}"))
        
        result = cursor.fetchone()
        if result:
            created_children.append({"name": child_name, "id": result[0]})
    
    # Mark parent as deprecated (but don't delete - skills still reference it)
    cursor.execute("""
        UPDATE entities
        SET status = 'deprecated',
            description = COALESCE(description, '') || ' [Split into: ' || %s || ']'
        WHERE entity_id = %s
    """, (", ".join(children), parent_id))
    
    # Get count of skills that need reassignment
    cursor.execute("""
        SELECT COUNT(*) FROM entity_relationships
        WHERE related_entity_id = %s AND relationship = 'is_a'
    """, (parent_id,))
    
    skills_to_reassign = cursor.fetchone()[0]
    
    return {
        "status": "split_applied",
        "parent_domain": parent_name,
        "parent_id": parent_id,
        "parent_status": "deprecated",
        "children_created": created_children,
        "skills_needing_reassignment": skills_to_reassign
    }


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Apply approved domain proposals.
    
    Args:
        interaction_data: Optional filters:
            - proposal_id: Specific proposal to apply
        db_conn: Database connection
        
    Returns:
        Results of applying proposals
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        proposal_id = interaction_data.get('proposal_id')
        
        # Get approved but not yet implemented proposals
        if proposal_id:
            cursor.execute("""
                SELECT proposal_id, proposal_type, suggested_name, 
                       suggested_description, parent_domain, suggested_children,
                       reasoning
                FROM domain_split_proposals
                WHERE proposal_id = %s AND status = 'approved'
            """, (proposal_id,))
        else:
            cursor.execute("""
                SELECT proposal_id, proposal_type, suggested_name, 
                       suggested_description, parent_domain, suggested_children,
                       reasoning
                FROM domain_split_proposals
                WHERE status = 'approved'
                ORDER BY created_at
            """)
        
        proposals = cursor.fetchall()
        
        if not proposals:
            return {
                "status": "no_proposals",
                "message": "No approved proposals to apply",
                "applied": 0
            }
        
        results = []
        applied = 0
        
        for row in proposals:
            (pid, ptype, suggested_name, suggested_desc, 
             parent_domain, suggested_children, reasoning) = row
            
            proposal = {
                "proposal_id": pid,
                "suggested_name": suggested_name,
                "suggested_description": suggested_desc,
                "parent_domain": parent_domain,
                "suggested_children": suggested_children,
                "reasoning": reasoning
            }
            
            if ptype == 'new_domain':
                result = apply_new_domain(cursor, proposal)
            elif ptype == 'split':
                result = apply_split(cursor, proposal)
            else:
                result = {"status": "error", "error": f"Unknown type: {ptype}"}
            
            # Update proposal status
            if result.get("status") in ("created", "split_applied", "already_exists"):
                cursor.execute("""
                    UPDATE domain_split_proposals
                    SET status = 'implemented'
                    WHERE proposal_id = %s
                """, (pid,))
                applied += 1
            
            result["proposal_id"] = pid
            result["proposal_type"] = ptype
            results.append(result)
        
        db_conn.commit()
        
        return {
            "status": "success",
            "applied": applied,
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
        except:
            pass
    
    result = execute(input_data)
    print(json.dumps(result, indent=2, default=str))
