#!/usr/bin/env python3
"""
Orphan Fetcher V2 - WF3006 Entity Classification

Enhanced version that includes:
- Reasoning history for reclassification learning
- Similar classified skills for context
- Dynamic domain loading for prompts

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys

# Batch size for LLM processing
DEFAULT_BATCH_SIZE = 10


def get_db_connection():
    """Get database connection using standard env vars."""
    import psycopg2
    
    # Load .env if exists
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


def get_reasoning_history(cursor, entity_id: int) -> list:
    """Get previous reasoning attempts for this skill."""
    cursor.execute("""
        SELECT model, role, reasoning, confidence, suggested_domain, 
               was_overturned, overturn_reason, created_at
        FROM classification_reasoning
        WHERE entity_id = %s
        ORDER BY created_at
    """, (entity_id,))
    
    rows = cursor.fetchall()
    return [{
        'model': r[0],
        'role': r[1],
        'reasoning': r[2],
        'confidence': float(r[3]) if r[3] else None,
        'suggested_domain': r[4],
        'was_overturned': r[5],
        'overturn_reason': r[6],
        'timestamp': r[7].isoformat() if r[7] else None
    } for r in rows]


def get_similar_classified(cursor, skill_name: str, limit: int = 3) -> list:
    """Get similar skills that have already been classified."""
    # Simple trigram similarity - requires pg_trgm extension
    cursor.execute("""
        SELECT e.entity_id, e.canonical_name, d.canonical_name as domain_name,
               similarity(e.canonical_name, %s) as sim
        FROM entities e
        JOIN entity_relationships er ON e.entity_id = er.entity_id 
            AND er.relationship = 'is_a'
        JOIN entities d ON er.related_entity_id = d.entity_id 
            AND d.entity_type = 'skill_domain'
        WHERE e.entity_type = 'skill'
          AND e.status = 'active'
          AND e.canonical_name %% %s  -- trigram similarity operator
        ORDER BY sim DESC
        LIMIT %s
    """, (skill_name, skill_name, limit))
    
    rows = cursor.fetchall()
    return [{
        'entity_id': r[0],
        'name': r[1],
        'domain': r[2],
        'similarity': float(r[3])
    } for r in rows]


def get_available_domains(cursor) -> list:
    """Get all available domains with examples for LLM context."""
    cursor.execute("""
        SELECT domain_id, domain_name, domain_description, 
               skill_count, example_skills
        FROM v_domains_with_examples
        ORDER BY domain_name
    """)
    
    rows = cursor.fetchall()
    return [{
        'domain_id': r[0],
        'name': r[1],
        'description': r[2],
        'skill_count': r[3],
        'examples': r[4] or []
    } for r in rows]


def format_history_for_prompt(history: list) -> str:
    """Format reasoning history for LLM context."""
    if not history:
        return ""
    
    lines = ["PREVIOUS CLASSIFICATION ATTEMPTS:"]
    for h in history:
        status = "❌ OVERTURNED" if h['was_overturned'] else "✓"
        lines.append(f"  - {h['role']} ({h['model']}): {h['suggested_domain']} "
                    f"(conf: {h['confidence']}) {status}")
        lines.append(f"    Reasoning: {h['reasoning'][:200]}...")
        if h['was_overturned'] and h['overturn_reason']:
            lines.append(f"    Overturn reason: {h['overturn_reason']}")
    
    return "\n".join(lines)


def format_similar_for_prompt(similar: list) -> str:
    """Format similar skills for LLM context."""
    if not similar:
        return ""
    
    lines = ["SIMILAR ALREADY-CLASSIFIED SKILLS:"]
    for s in similar:
        lines.append(f"  - {s['name']} → {s['domain']} (similarity: {s['similarity']:.2f})")
    
    return "\n".join(lines)


def format_domains_for_prompt(domains: list) -> str:
    """Format domains for LLM prompt."""
    lines = ["AVAILABLE DOMAINS:"]
    for d in domains:
        examples = d['examples'][:3] if d['examples'] else []
        example_str = ", ".join(examples) if examples else "no examples yet"
        lines.append(f"  - {d['name']} ({d['skill_count']} skills)")
        lines.append(f"    Description: {d['description'] or 'No description'}")
        lines.append(f"    Examples: {example_str}")
    
    return "\n".join(lines)


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Fetch next batch of orphan skills with enrichment data.
    
    Args:
        interaction_data: Input config with:
            - batch_size: Number of skills to fetch (default 10)
            - include_history: Include reasoning history (default True)
            - include_similar: Include similar classified skills (default True)
        db_conn: Database connection
        
    Returns:
        Dict with orphan skills and context for classification
    """
    close_conn = False
    if not db_conn:
        db_conn = get_db_connection()
        close_conn = True
    
    try:
        cursor = db_conn.cursor()
        
        # Parse input options
        batch_size = interaction_data.get('batch_size', DEFAULT_BATCH_SIZE)
        include_history = interaction_data.get('include_history', True)
        include_similar = interaction_data.get('include_similar', True)
        
        # Fetch orphan skills from view
        cursor.execute("""
            SELECT entity_id, canonical_name, description, 
                   has_history, attempt_count
            FROM v_orphan_skills
            ORDER BY 
                attempt_count DESC,  -- Prioritize skills that failed before
                entity_id
            LIMIT %s
        """, (batch_size,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "status": "NO_ORPHANS",
                "skills": [],
                "batch_count": 0,
                "remaining": 0,
                "domains": [],
                "domains_text": "",
                "message": "All skills have been classified"
            }
        
        # Get domains for context
        domains = get_available_domains(cursor)
        domains_text = format_domains_for_prompt(domains)
        
        # Enrich each skill
        skills = []
        for row in rows:
            entity_id, name, description, has_history, attempt_count = row
            
            skill = {
                'entity_id': entity_id,
                'name': name,
                'description': description or '',
                'has_history': has_history,
                'attempt_count': attempt_count
            }
            
            # Get reasoning history if requested and exists
            if include_history and has_history:
                history = get_reasoning_history(cursor, entity_id)
                skill['history'] = history
                skill['history_text'] = format_history_for_prompt(history)
            else:
                skill['history'] = []
                skill['history_text'] = ""
            
            # Get similar classified skills if requested
            if include_similar:
                try:
                    similar = get_similar_classified(cursor, name)
                    skill['similar'] = similar
                    skill['similar_text'] = format_similar_for_prompt(similar)
                except Exception:
                    # pg_trgm might not be installed
                    skill['similar'] = []
                    skill['similar_text'] = ""
            else:
                skill['similar'] = []
                skill['similar_text'] = ""
            
            skills.append(skill)
        
        # Count remaining orphans
        cursor.execute("SELECT COUNT(*) FROM v_orphan_skills")
        remaining = cursor.fetchone()[0]
        
        # Build formatted text for LLM
        skills_text_parts = []
        for s in skills:
            parts = [f"SKILL: {s['entity_id']}|{s['name']}"]
            if s['description']:
                parts.append(f"Description: {s['description']}")
            if s['history_text']:
                parts.append(s['history_text'])
            if s['similar_text']:
                parts.append(s['similar_text'])
            skills_text_parts.append("\n".join(parts))
        
        skills_text = "\n\n---\n\n".join(skills_text_parts)
        
        return {
            "status": "HAS_ORPHANS",
            "skills": skills,
            "skills_text": skills_text,
            "batch_count": len(skills),
            "remaining": remaining,
            "domains": domains,
            "domains_text": domains_text,
            "skill_ids": [s['entity_id'] for s in skills]
        }
        
    except Exception as e:
        if db_conn:
            db_conn.rollback()
        return {"status": "error", "error": str(e)}
    
    finally:
        if close_conn and db_conn:
            db_conn.close()


if __name__ == "__main__":
    # Read input from stdin (passed by ScriptExecutor)
    input_data = {}
    if not sys.stdin.isatty():
        try:
            input_data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            pass
    
    result = execute(input_data)
    print(json.dumps(result, indent=2, default=str))
