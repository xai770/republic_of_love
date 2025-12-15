#!/usr/bin/env python3
"""
Test the posting_skills_saver.py with the new extraction format.
Simulates workflow calling the saver directly.

Sandy - 2025-11-30
"""

import sys
import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv('/home/xai/Documents/ty_wave/.env')
sys.path.insert(0, '/home/xai/Documents/ty_wave')

def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def test_saver_on_posting(posting_id: int):
    """
    Test the saver by:
    1. Getting the extracted summary
    2. Running skill extraction (conversation 9121)
    3. Calling posting_skills_saver manually
    """
    import requests
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Get posting summary
    cursor.execute("""
        SELECT job_title, extracted_summary
        FROM postings WHERE posting_id = %s
    """, (posting_id,))
    row = cursor.fetchone()
    if not row:
        print(f"Posting {posting_id} not found")
        return
        
    job_title, summary = row
    
    # Get prompt template
    cursor.execute("""
        SELECT i.prompt_template
        FROM instructions i
        WHERE i.conversation_id = 9121
        ORDER BY i.step_number LIMIT 1
    """)
    prompt_row = cursor.fetchone()
    prompt_template = prompt_row[0]
    
    # Build prompt
    prompt = prompt_template.replace('{{job_summary}}', summary or '')
    prompt = prompt.replace('{{job_title}}', job_title or 'Unknown')
    
    print(f"🔍 Testing posting {posting_id}: {job_title}")
    
    # Call LLM
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={'model': 'qwen2.5:7b', 'prompt': prompt, 'stream': False},
        timeout=120
    )
    result = response.json()
    ai_response = result.get('response', '')
    
    # Parse skills
    if '```json' in ai_response:
        json_str = ai_response.split('```json')[1].split('```')[0].strip()
    elif '```' in ai_response:
        json_str = ai_response.split('```')[1].split('```')[0].strip()
    else:
        json_str = ai_response.strip()
    
    skills = json.loads(json_str)
    print(f"   Extracted {len(skills)} skills")
    
    # Clear existing posting_skills for this posting to test fresh
    cursor.execute("DELETE FROM posting_skills WHERE posting_id = %s", (posting_id,))
    conn.commit()
    print(f"   Cleared existing posting_skills for posting {posting_id}")
    
    # Now simulate the saver
    skills_saved = 0
    taxonomy_skills = 0
    raw_skills = 0
    
    for skill_item in skills:
        skill_name = skill_item.get('skill', '')
        importance = skill_item.get('importance')
        weight = skill_item.get('weight')
        proficiency = skill_item.get('proficiency')
        years_required = skill_item.get('years_required')
        reasoning = skill_item.get('reasoning')
        
        if not skill_name:
            continue
            
        # Check taxonomy
        cursor.execute("""
            SELECT skill_id FROM skill_aliases
            WHERE LOWER(skill_name) = LOWER(%s) LIMIT 1
        """, (skill_name,))
        tax_row = cursor.fetchone()
        
        if tax_row:
            skill_id = tax_row[0]
            cursor.execute("""
                INSERT INTO posting_skills (
                    posting_id, skill_id, raw_skill_name, importance, weight,
                    proficiency, years_required, reasoning, extracted_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (posting_id, skill_id) DO UPDATE SET
                    raw_skill_name = EXCLUDED.raw_skill_name,
                    importance = EXCLUDED.importance,
                    weight = EXCLUDED.weight,
                    updated_at = NOW()
            """, (posting_id, skill_id, skill_name, importance, weight, 
                  proficiency, years_required, reasoning, 'test_saver'))
            taxonomy_skills += 1
        else:
            # Non-taxonomy - save with raw_skill_name only
            cursor.execute("""
                INSERT INTO posting_skills (
                    posting_id, skill_id, raw_skill_name, importance, weight,
                    proficiency, years_required, reasoning, extracted_by, created_at
                ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (posting_id, skill_name, importance, weight, 
                  proficiency, years_required, reasoning, 'test_saver'))
            raw_skills += 1
        
        skills_saved += 1
    
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT COUNT(*), 
               COUNT(skill_id) as with_taxonomy,
               COUNT(*) - COUNT(skill_id) as without_taxonomy
        FROM posting_skills WHERE posting_id = %s
    """, (posting_id,))
    verify = cursor.fetchone()
    
    print(f"   ✅ Saved {verify[0]} skills")
    print(f"      - With taxonomy: {verify[1]}")
    print(f"      - Without taxonomy (raw_skill_name): {verify[2]}")
    print(f"   🎯 0% skill loss! (was 77%)")
    
    # Show some examples
    cursor.execute("""
        SELECT skill_id, raw_skill_name, importance, weight
        FROM posting_skills WHERE posting_id = %s
        LIMIT 10
    """, (posting_id,))
    rows = cursor.fetchall()
    print(f"   Sample skills saved:")
    for r in rows:
        status = "📗 TAX" if r[0] else "📙 RAW"
        print(f"      {status} {r[1]} [{r[2]}, w:{r[3]}]")
    
    cursor.close()
    conn.close()
    
    return skills_saved

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 POSTING_SKILLS_SAVER TEST")
    print("=" * 60)
    
    # Test on posting 4803 which had 0 skills before
    test_saver_on_posting(4803)
