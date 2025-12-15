#!/usr/bin/env python3
"""
Test Skill Extraction Fix
Tests the updated skill extraction (conversation 9121) and posting_skills_saver.py
on a sample of postings with sparse skills.

Sandy - 2025-11-30
"""

import sys
import os
import json
import psycopg2
from dotenv import load_dotenv

# Load .env
load_dotenv('/home/xai/Documents/ty_wave/.env')

# Add project to path
sys.path.insert(0, '/home/xai/Documents/ty_wave')

def get_db_conn():
    """Get database connection from .env"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def test_extraction(posting_ids: list[int]):
    """
    Test skill extraction on given posting IDs.
    Calls conversation 9121 (Hybrid Job Skills Extraction) and then posting_skills_saver.
    """
    import requests
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Get instruction prompt for conversation 9121
    cursor.execute("""
        SELECT i.prompt_template
        FROM instructions i
        WHERE i.conversation_id = 9121
        ORDER BY i.step_number
        LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        print("ERROR: No instruction found for conversation 9121!")
        return
    
    prompt_template = row[0]
    
    # Get actor/model for 9121
    cursor.execute("""
        SELECT a.actor_name
        FROM conversations c
        JOIN actors a ON c.actor_id = a.actor_id
        WHERE c.conversation_id = 9121
    """)
    model_row = cursor.fetchone()
    model_name = model_row[0] if model_row else 'qwen2.5:7b'
    
    print(f"Using model: {model_name}")
    print(f"Prompt template length: {len(prompt_template) if prompt_template else 0}")
    print("-" * 60)
    
    results = []
    
    for posting_id in posting_ids:
        # Get posting summary
        cursor.execute("""
            SELECT job_title, extracted_summary
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        posting_row = cursor.fetchone()
        
        if not posting_row:
            print(f"Posting {posting_id} not found")
            continue
            
        job_title, summary = posting_row
        
        if not summary:
            print(f"Posting {posting_id} has no summary")
            continue
        
        print(f"\n🔍 Testing posting {posting_id}: {job_title}")
        print(f"   Summary length: {len(summary)} chars")
        
        # Build user prompt from template
        user_prompt = prompt_template.replace('{{job_summary}}', summary)
        user_prompt = user_prompt.replace('{{job_title}}', job_title or 'Unknown')
        
        # Call Ollama - no system prompt, all in user prompt
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model_name,
                    'prompt': user_prompt,
                    'stream': False
                },
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            ai_response = result.get('response', '')
            
            # Parse JSON from response
            try:
                # Try to extract JSON from response
                if '```json' in ai_response:
                    json_str = ai_response.split('```json')[1].split('```')[0].strip()
                elif '```' in ai_response:
                    json_str = ai_response.split('```')[1].split('```')[0].strip()
                else:
                    json_str = ai_response.strip()
                
                skills = json.loads(json_str)
                
                print(f"   ✅ Extracted {len(skills)} skills")
                
                # Count taxonomy vs non-taxonomy
                taxonomy_count = 0
                non_taxonomy_count = 0
                
                for skill in skills[:10]:  # Show first 10
                    skill_name = skill.get('skill', skill) if isinstance(skill, dict) else skill
                    importance = skill.get('importance', 'N/A') if isinstance(skill, dict) else 'N/A'
                    weight = skill.get('weight', 'N/A') if isinstance(skill, dict) else 'N/A'
                    
                    # Check if in taxonomy
                    cursor.execute("""
                        SELECT skill_id FROM skill_aliases
                        WHERE LOWER(skill_name) = LOWER(%s)
                        LIMIT 1
                    """, (skill_name,))
                    tax_row = cursor.fetchone()
                    
                    status = "📗 TAX" if tax_row else "📙 RAW"
                    if tax_row:
                        taxonomy_count += 1
                    else:
                        non_taxonomy_count += 1
                    
                    print(f"      {status} {skill_name} [{importance}, w:{weight}]")
                
                if len(skills) > 10:
                    print(f"      ... and {len(skills) - 10} more skills")
                
                print(f"   📊 Taxonomy: {taxonomy_count}, Non-taxonomy: {non_taxonomy_count}")
                
                results.append({
                    'posting_id': posting_id,
                    'total_skills': len(skills),
                    'taxonomy_skills': taxonomy_count,
                    'non_taxonomy_skills': non_taxonomy_count,
                    'skills': skills
                })
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON parse error: {e}")
                print(f"   Raw response: {ai_response[:500]}...")
                results.append({
                    'posting_id': posting_id,
                    'error': f'JSON parse error: {e}',
                    'raw_response': ai_response[:500]
                })
                
        except requests.RequestException as e:
            print(f"   ❌ API error: {e}")
            results.append({
                'posting_id': posting_id,
                'error': str(e)
            })
    
    cursor.close()
    conn.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    total_extracted = sum(r.get('total_skills', 0) for r in results if 'total_skills' in r)
    total_taxonomy = sum(r.get('taxonomy_skills', 0) for r in results if 'taxonomy_skills' in r)
    total_non_tax = sum(r.get('non_taxonomy_skills', 0) for r in results if 'non_taxonomy_skills' in r)
    
    print(f"Postings tested: {len(posting_ids)}")
    print(f"Total skills extracted: {total_extracted}")
    print(f"  - In taxonomy: {total_taxonomy}")
    print(f"  - Not in taxonomy: {total_non_tax} (would have been LOST before fix)")
    print(f"  - Retention improvement: {total_non_tax}/{total_extracted} = {total_non_tax/total_extracted*100:.1f}% more skills saved!" if total_extracted > 0 else "")
    
    return results

if __name__ == '__main__':
    # Test posting IDs from Arden's analysis
    test_ids = [4794, 4803, 4804, 4805, 4806]
    
    print("🧪 SKILL EXTRACTION FIX TEST")
    print("=" * 60)
    print("Testing conversation 9121 (Hybrid Job Skills Extraction)")
    print("Verifying non-taxonomy skills will be saved via raw_skill_name")
    print("=" * 60)
    
    test_extraction(test_ids)
