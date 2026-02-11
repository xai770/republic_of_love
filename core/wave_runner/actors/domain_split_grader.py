#!/usr/bin/env python3
"""
Domain Split Grader - WF3006 Entity Classification

Reviews domain split proposals using two-LLM grading pattern (like WF3001).
- Proposer: gemma3:4b suggests the split
- Grader: qwen2.5:7b reviews and approves/rejects

Auto-approves if grader agrees with proposal.

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys
import subprocess

# Model assignments (different models = diverse perspectives)
GRADER_MODEL = "qwen2.5:7b"
LLM_TIMEOUT = 300


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


def call_llm(prompt: str, model: str = GRADER_MODEL) -> dict:
    """Call Ollama LLM."""
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "success": False}
        
        return {"response": result.stdout.strip(), "success": True}
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def grade_new_domain_proposal(proposal: dict, existing_domains: list) -> dict:
    """
    Grade a NEW_DOMAIN proposal using the grader model.
    
    Returns grading result with approve/reject decision.
    """
    domains_text = "\n".join([
        f"  - {d['name']}: {d.get('description', '')} ({d.get('skill_count', 0)} skills)"
        for d in existing_domains
    ])
    
    prompt = f"""You are an expert taxonomy grader reviewing a proposal for a NEW skill domain.

## EXISTING DOMAINS
{domains_text}

## PROPOSAL TO REVIEW
**Suggested Name:** {proposal.get('suggested_name')}
**Description:** {proposal.get('suggested_description', 'No description')}
**Reasoning:** {proposal.get('reasoning', 'No reasoning provided')}
**Example Skills:** {proposal.get('example_skills', [])}

## YOUR TASK
Review this proposal. Consider:
1. Does this domain overlap significantly with existing domains?
2. Is the domain name clear and follows the naming convention (snake_case)?
3. Is there a genuine gap in the taxonomy that this fills?
4. Would the example skills actually fit better in an existing domain?

Respond with JSON ONLY:
```json
{{
  "approve": true/false,
  "reasoning": "Your detailed reasoning for approval/rejection",
  "confidence": 0.0-1.0,
  "alternative_suggestion": "If rejecting, suggest which existing domain to use instead, or null"
}}
```"""

    result = call_llm(prompt)
    
    if not result.get("success"):
        return {"error": result.get("error"), "approve": False}
    
    response_text = result.get("response", "")
    try:
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response_text, "parse_error": True, "approve": False}


def grade_split_proposal(proposal: dict, affected_skills: list) -> dict:
    """
    Grade a SPLIT domain proposal using the grader model.
    
    Returns grading result with approve/reject decision.
    """
    skills_sample = affected_skills[:20]  # Limit for prompt
    skills_text = "\n".join([f"  - {s['name']}" for s in skills_sample])
    if len(affected_skills) > 20:
        skills_text += f"\n  ... and {len(affected_skills) - 20} more"
    
    prompt = f"""You are an expert taxonomy grader reviewing a proposal to SPLIT a domain.

## SPLIT PROPOSAL
**Parent Domain:** {proposal.get('parent_domain')}
**Suggested Children:** {proposal.get('suggested_children', [])}
**Reasoning:** {proposal.get('reasoning', 'No reasoning provided')}
**Affected Skills:** {proposal.get('affected_skill_count', 0)}

## SAMPLE OF AFFECTED SKILLS
{skills_text}

## YOUR TASK
Review this split proposal. Consider:
1. Are the suggested child domains distinct and non-overlapping?
2. Would the split improve clarity of the taxonomy?
3. Are there enough skills to justify the split (>30 total recommended)?
4. Would the affected skills clearly map to one of the children?

Respond with JSON ONLY:
```json
{{
  "approve": true/false,
  "reasoning": "Your detailed reasoning for approval/rejection",
  "confidence": 0.0-1.0,
  "suggested_modifications": "Any improvements to the proposed children names/structure, or null"
}}
```"""

    result = call_llm(prompt)
    
    if not result.get("success"):
        return {"error": result.get("error"), "approve": False}
    
    response_text = result.get("response", "")
    try:
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    return {"raw_response": response_text, "parse_error": True, "approve": False}


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Grade pending domain proposals.
    
    Args:
        interaction_data: Contains:
            - proposal_id: Specific proposal to grade (optional)
            - batch_size: Max proposals to grade (default 5)
        db_conn: Database connection
        
    Returns:
        Grading results for each proposal
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        proposal_id = interaction_data.get('proposal_id')
        batch_size = interaction_data.get('batch_size', 5)
        
        # Get pending proposals
        if proposal_id:
            cursor.execute("""
                SELECT proposal_id, proposal_type, suggested_name, 
                       suggested_description, example_skills, parent_domain,
                       suggested_children, affected_skill_count, reasoning,
                       confidence
                FROM domain_split_proposals
                WHERE proposal_id = %s AND status = 'pending'
            """, (proposal_id,))
        else:
            cursor.execute("""
                SELECT proposal_id, proposal_type, suggested_name, 
                       suggested_description, example_skills, parent_domain,
                       suggested_children, affected_skill_count, reasoning,
                       confidence
                FROM domain_split_proposals
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT %s
            """, (batch_size,))
        
        proposals = cursor.fetchall()
        
        if not proposals:
            return {
                "status": "no_proposals",
                "message": "No pending proposals to grade",
                "graded": 0
            }
        
        # Get existing domains for context
        cursor.execute("""
            SELECT domain_id, domain_name as name, domain_description as description, 
                   skill_count
            FROM v_domains_with_examples
        """)
        existing_domains = [
            {"name": r[1], "description": r[2], "skill_count": r[3]}
            for r in cursor.fetchall()
        ]
        
        results = []
        approved = 0
        rejected = 0
        
        for row in proposals:
            (pid, ptype, suggested_name, suggested_desc, example_skills,
             parent_domain, suggested_children, affected_count, reasoning, 
             proposer_confidence) = row
            
            proposal = {
                "proposal_id": pid,
                "proposal_type": ptype,
                "suggested_name": suggested_name,
                "suggested_description": suggested_desc,
                "example_skills": example_skills,
                "parent_domain": parent_domain,
                "suggested_children": suggested_children,
                "affected_skill_count": affected_count,
                "reasoning": reasoning
            }
            
            # Grade based on type
            if ptype == 'new_domain':
                grading = grade_new_domain_proposal(proposal, existing_domains)
            elif ptype == 'split':
                # Get affected skills for context
                cursor.execute("""
                    SELECT e.entity_id, e.canonical_name as name
                    FROM entities e
                    JOIN entity_relationships er ON e.entity_id = er.entity_id
                    JOIN entities d ON er.related_entity_id = d.entity_id
                    WHERE d.canonical_name = %s AND er.relationship = 'is_a'
                    LIMIT 30
                """, (parent_domain,))
                affected_skills = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
                grading = grade_split_proposal(proposal, affected_skills)
            else:
                grading = {"approve": False, "reasoning": f"Unknown proposal type: {ptype}"}
            
            # Update proposal status based on grading
            if grading.get("approve"):
                new_status = "approved"
                approved += 1
            else:
                new_status = "rejected"
                rejected += 1
            
            cursor.execute("""
                UPDATE domain_split_proposals
                SET status = %s,
                    reviewed_by = %s,
                    review_notes = %s,
                    reviewed_at = NOW()
                WHERE proposal_id = %s
            """, (new_status, GRADER_MODEL, 
                  grading.get("reasoning", str(grading)), pid))
            
            results.append({
                "proposal_id": pid,
                "type": ptype,
                "name": suggested_name or parent_domain,
                "grader_approved": grading.get("approve", False),
                "grader_confidence": grading.get("confidence"),
                "grader_reasoning": grading.get("reasoning"),
                "new_status": new_status
            })
        
        db_conn.commit()
        
        return {
            "status": "success",
            "graded": len(results),
            "approved": approved,
            "rejected": rejected,
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
