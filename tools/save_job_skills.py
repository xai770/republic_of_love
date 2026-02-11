#!/usr/bin/env python3
"""
Save Job Skills - Script Actor for Workflow 2001
=================================================

PURPOSE:
    Saves extracted skills to job_skills table with taxonomy linking.
    Used as final step in Workflow 2001 job processing pipeline.

INPUT (via stdin):
    Simple format:
        POSTING_ID:123
        SKILLS:[...]
    OR JSON format:
    {
        "posting_id": 123,
        "skills": [...],  // From session_r10_output (skills extraction)
        "taxonomy_mapping": {...}  // From session_r30_output (taxonomy mapping)
    }

OUTPUT (to stdout):
    JSON with:
    {
        "status": "SUCCESS|FAILED",
        "skills_saved": 15,
        "skill_ids": [1, 2, 3, ...],
        "errors": []
    }

AUTHOR: Arden (GitHub Copilot)
DATE: 2025-11-09
"""

import sys
import json
import psycopg2
import psycopg2.extras
from typing import Dict, Any, List

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'turing',
    'user': 'base_admin',
    'password': os.getenv('DB_PASSWORD', '')
}


def parse_input(stdin_text: str) -> Dict[str, Any]:
    """Parse input from either simple format or JSON"""
    stdin_text = stdin_text.strip()
    
    # Try JSON first
    if stdin_text.startswith('{'):
        return json.loads(stdin_text)
    
    # Parse simple format: KEY:value (where value might be multi-line JSON)
    data = {}
    lines = stdin_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if ':' in line:
            key, value_start = line.split(':', 1)
            key = key.strip().lower()
            value_start = value_start.strip()
            
            if key == 'posting_id':
                data['posting_id'] = int(value_start)
                i += 1
            elif key in ('skills', 'taxonomy_mapping'):
                # Multi-line JSON - collect until we have valid JSON
                json_lines = [value_start]
                i += 1
                while i < len(lines):
                    json_lines.append(lines[i])
                    try:
                        # Try to parse accumulated JSON
                        json_str = '\n'.join(json_lines)
                        data[key] = json.loads(json_str)
                        i += 1
                        break  # Successfully parsed, move on
                    except json.JSONDecodeError:
                        # Need more lines
                        i += 1
                        continue
            else:
                i += 1
        else:
            i += 1
    
    return data


def save_job_skills(posting_id: int, skills: List[Dict[str, Any]], 
                    taxonomy_mapping: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Save skills to job_skills table
    
```
    
    Args:
        posting_id: Posting ID to save skills for
        skills: List of skill dicts from skills extraction
        taxonomy_mapping: Optional taxonomy mapping from simple_skill_mapper
        
    Returns:
        Result dict with status, skills_saved, skill_ids, errors
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    skill_ids_saved = []
    errors = []
    
    try:
        # Start transaction
        conn.autocommit = False
        
        for skill_data in skills:
            try:
                # Extract skill info
                skill_name = skill_data.get('skill') or skill_data.get('skill_name')
                if not skill_name:
                    errors.append(f"Skill data missing 'skill' or 'skill_name': {skill_data}")
                    continue
                
                # Look up skill_id from skill_aliases (canonical taxonomy)
                cursor.execute("""
                    SELECT skill_id 
                    FROM skill_aliases 
                    WHERE skill_alias = %s OR skill_name = %s
                    LIMIT 1
                """, (skill_name, skill_name))
                
                result = cursor.fetchone()
                skill_id = result['skill_id'] if result else None
                
                if not skill_id:
                    errors.append(f"Skill '{skill_name}' not found in taxonomy")
                    continue
                
                # Insert into job_skills
                cursor.execute("""
                    INSERT INTO job_skills (
                        posting_id,
                        skill_id,
                        importance,
                        weight,
                        proficiency,
                        years_required,
                        reasoning,
                        extracted_by,
                        created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (posting_id, skill_id) DO UPDATE SET
                        importance = EXCLUDED.importance,
                        weight = EXCLUDED.weight,
                        proficiency = EXCLUDED.proficiency,
                        years_required = EXCLUDED.years_required,
                        reasoning = EXCLUDED.reasoning,
                        updated_at = NOW()
                    RETURNING job_skill_id
                """, (
                    posting_id,
                    skill_id,
                    skill_data.get('importance'),
                    skill_data.get('weight'),
                    skill_data.get('proficiency'),
                    skill_data.get('years_required') or skill_data.get('years'),
                    skill_data.get('reasoning'),
                    'workflow_2001'
                ))
                
                job_skill_id = cursor.fetchone()['job_skill_id']
                skill_ids_saved.append(job_skill_id)
                
            except Exception as e:
                errors.append(f"Error saving skill '{skill_name}': {str(e)}")
                continue
        
        # Commit transaction
        conn.commit()
        
        return {
            'status': 'SUCCESS' if skill_ids_saved else 'FAILED',
            'skills_saved': len(skill_ids_saved),
            'skill_ids': skill_ids_saved,
            'errors': errors,
            'message': f"Saved {len(skill_ids_saved)} skills for posting {posting_id}"
        }
        
    except Exception as e:
        conn.rollback()
        return {
            'status': 'FAILED',
            'skills_saved': 0,
            'skill_ids': [],
            'errors': [str(e)],
            'message': f"Failed to save skills: {str(e)}"
        }
    finally:
        cursor.close()
        conn.close()


def main():
    """
    Script actor entry point
    Reads JSON from stdin, outputs JSON to stdout
    """
    try:
        # Read input from stdin
        stdin_text = sys.stdin.read()
        input_data = parse_input(stdin_text)
        
        # Extract parameters
        posting_id = input_data.get('posting_id')
        skills = input_data.get('skills', [])
        taxonomy_mapping = input_data.get('taxonomy_mapping')
        
        # Validate
        if not posting_id:
            result = {
                'status': 'FAILED',
                'skills_saved': 0,
                'skill_ids': [],
                'errors': ['Missing posting_id in input'],
                'message': 'Missing posting_id'
            }
        elif not skills:
            result = {
                'status': 'SUCCESS',
                'skills_saved': 0,
                'skill_ids': [],
                'errors': [],
                'message': f'No skills to save for posting {posting_id}'
            }
        else:
            # Parse skills if they're a JSON string
            if isinstance(skills, str):
                skills = json.loads(skills)
            
            # Save skills
            result = save_job_skills(posting_id, skills, taxonomy_mapping)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if result['status'] == 'SUCCESS' else 1)
        
    except Exception as e:
        error_result = {
            'status': 'FAILED',
            'skills_saved': 0,
            'skill_ids': [],
            'errors': [str(e)],
            'message': f'Script error: {str(e)}'
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
