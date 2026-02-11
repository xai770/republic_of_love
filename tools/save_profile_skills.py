import os
#!/usr/bin/env python3
"""
Save Profile Skills Actor
==========================
Purpose: Script actor that saves extracted skills to profile_skills table

Input: JSON with profile_id, taxonomy_skills, and raw_skills
Output: JSON with counts and [SUCCESS]/[FAIL] markers

Usage:
    echo '{"profile_id": 1, "taxonomy_skills": [...], "raw_skills": [...]}' | python3 save_profile_skills.py

Author: Base Yoga Team
Date: 2025-11-04
"""

import sys
import json
import psycopg2
import psycopg2.extras
from datetime import datetime


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host='localhost',
        database='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', '')
    )


def get_or_create_skill_alias(cursor, skill_name: str) -> int:
    """
    Get skill_id from skill_aliases, or create if doesn't exist.
    
    Args:
        cursor: Database cursor
        skill_name: Canonical skill name from taxonomy
        
    Returns:
        skill_id: Primary key from skill_aliases
    """
    # Check if skill exists
    cursor.execute("""
        SELECT skill_id 
        FROM skill_aliases 
        WHERE LOWER(skill_name) = LOWER(%s)
        LIMIT 1
    """, (skill_name,))
    
    row = cursor.fetchone()
    if row:
        return row['skill_id']
    
    # Create new skill alias
    cursor.execute("""
        INSERT INTO skill_aliases (
            skill_name,
            skill_alias,
            confidence,
            display_name
        )
        VALUES (%s, %s, 1.0, %s)
        RETURNING skill_id
    """, (skill_name, skill_name, skill_name))
    
    result = cursor.fetchone()
    return result['skill_id']


def save_skills(profile_id: int, taxonomy_skills: list, raw_skills: list, workflow_run_id: int = None) -> dict:
    """
    Save skills to profile_skills table.
    
    Args:
        profile_id: Profile to link skills to
        taxonomy_skills: List of canonical taxonomy skill names
        raw_skills: List of dicts with skill, proficiency, years_experience, context
        workflow_run_id: Optional workflow_run_id for audit trail
        
    Returns:
        dict: Result with counts and status
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Start transaction
        conn.autocommit = False
        
        # Delete existing skills for this profile (if any)
        cursor.execute("""
            DELETE FROM profile_skills 
            WHERE profile_id = %s
        """, (profile_id,))
        deleted_count = cursor.rowcount
        
        # Build skill map from raw_skills (for proficiency/years lookup)
        skill_map = {}
        for raw_skill in raw_skills:
            if isinstance(raw_skill, dict):
                skill_name = raw_skill.get('skill', '').lower()
                skill_map[skill_name] = {
                    'proficiency': raw_skill.get('proficiency'),
                    'years_experience': raw_skill.get('years_experience'),
                    'context': raw_skill.get('context')
                }
        
        # Insert taxonomy-mapped skills
        inserted_count = 0
        skill_details = []
        
        for taxonomy_skill in taxonomy_skills:
            # Get or create skill_id
            skill_id = get_or_create_skill_alias(cursor, taxonomy_skill)
            
            # Try to find matching raw skill for proficiency/years
            raw_match = skill_map.get(taxonomy_skill.lower())
            
            proficiency = raw_match.get('proficiency') if raw_match else None
            years_exp = raw_match.get('years_experience') if raw_match else None
            context = raw_match.get('context') if raw_match else None
            
            # Insert into profile_skills
            cursor.execute("""
                INSERT INTO profile_skills (
                    profile_id,
                    skill_id,
                    proficiency_level,
                    years_experience,
                    evidence_text,
                    is_implicit,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, FALSE, NOW())
                RETURNING profile_skill_id
            """, (
                profile_id,
                skill_id,
                proficiency,
                years_exp,
                context
            ))
            
            profile_skill_id = cursor.fetchone()['profile_skill_id']
            inserted_count += 1
            
            skill_details.append({
                'profile_skill_id': profile_skill_id,
                'skill_name': taxonomy_skill,
                'skill_id': skill_id,
                'proficiency': proficiency,
                'years_experience': years_exp
            })
        
        # Update profiles.skill_keywords JSONB (for backward compatibility with old matching code)
        cursor.execute("""
            UPDATE profiles
            SET skill_keywords = %s::jsonb,
                updated_at = NOW()
            WHERE profile_id = %s
        """, (json.dumps(taxonomy_skills), profile_id))
        
        # Commit transaction
        conn.commit()
        
        result = {
            'status': 'success',
            'profile_id': profile_id,
            'deleted_count': deleted_count,
            'inserted_count': inserted_count,
            'skills': skill_details,
            'workflow_run_id': workflow_run_id
        }
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        
        return {
            'status': 'error',
            'error': str(e),
            'profile_id': profile_id
        }


def main():
    """
    Main entry point - reads JSON from stdin, saves skills, outputs result.
    
    Expected input format:
    {
        "profile_id": 1,
        "taxonomy_skills": ["SKILL_1", "SKILL_2"],
        "raw_skills": [
            {"skill": "Skill 1", "proficiency": "expert", "years_experience": 10, "context": "..."},
            {"skill": "Skill 2", "proficiency": "advanced", "years_experience": 5, "context": "..."}
        ],
        "workflow_run_id": 1234  // optional
    }
    
    Output format:
    {
        "status": "success",
        "profile_id": 1,
        "deleted_count": 5,
        "inserted_count": 10,
        "skills": [...],
        "message": "[SUCCESS] Saved 10 skills for profile_id=1"
    }
    """
    try:
        # Read input from stdin (could be JSON or YAML-like format)
        input_text = sys.stdin.read().strip()
        
        # Try JSON first (backward compatibility)
        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError:
            # Parse YAML-like format: "key: value" on separate lines
            input_data = {}
            current_key = None
            current_value = []
            
            for line in input_text.split('\n'):
                # Check if this is a key: value line
                if ':' in line and not line.strip().startswith('{') and not line.strip().startswith('['):
                    # Save previous multi-line value if exists
                    if current_key:
                        value_text = '\n'.join(current_value).strip()
                        # Strip markdown code fences
                        value_text = value_text.replace('```json', '').replace('```', '').strip()
                        try:
                            input_data[current_key] = json.loads(value_text)
                        except (json.JSONDecodeError, ValueError):
                            input_data[current_key] = value_text
                    
                    # Start new key
                    key, value = line.split(':', 1)
                    current_key = key.strip()
                    current_value = [value.strip()]
                elif current_key:
                    # Continue multi-line value
                    current_value.append(line)
            
            # Don't forget the last key
            if current_key:
                value_text = '\n'.join(current_value).strip()
                # Strip markdown code fences
                value_text = value_text.replace('```json', '').replace('```', '').strip()
                try:
                    input_data[current_key] = json.loads(value_text)
                except (json.JSONDecodeError, ValueError):
                    input_data[current_key] = value_text
        
        # Validate required fields
        if 'profile_id' not in input_data:
            raise ValueError("Missing required field: profile_id")
        
        profile_id = int(input_data['profile_id'])
        
        # Parse taxonomy_skills (might be JSON string or list)
        taxonomy_skills = input_data.get('taxonomy_skills', [])
        if isinstance(taxonomy_skills, str):
            taxonomy_skills = json.loads(taxonomy_skills)
        
        # Parse raw_skills (might be JSON string or list)
        raw_skills = input_data.get('raw_skills', [])
        if isinstance(raw_skills, str):
            raw_skills = json.loads(raw_skills)
        
        workflow_run_id = input_data.get('workflow_run_id')
        
        # Save skills
        result = save_skills(profile_id, taxonomy_skills, raw_skills, workflow_run_id)
        
        # Add success/fail marker
        if result['status'] == 'success':
            result['message'] = f"[SUCCESS] Saved {result['inserted_count']} skills for profile_id={profile_id}"
        else:
            result['message'] = f"[FAIL] Error saving skills: {result.get('error')}"
        
        # Output JSON
        print(json.dumps(result, indent=2))
        
        return 0 if result['status'] == 'success' else 1
        
    except Exception as e:
        error_result = {
            'status': 'error',
            'error': str(e),
            'message': f"[FAIL] {str(e)}"
        }
        print(json.dumps(error_result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
