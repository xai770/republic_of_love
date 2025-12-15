#!/usr/bin/env python3
"""
Backfill Skills for Postings
Re-extracts skills for postings that have summaries but sparse skills (<3).
Uses conversation 9121 (Hybrid Job Skills Extraction) and saves ALL skills.

Sandy - 2025-11-30

Usage:
    python backfill_skills.py [--dry-run] [--limit N]
"""

import sys
import os
import json
import argparse
import time
import psycopg2
import requests
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

def extract_skills(prompt_template: str, summary: str, job_title: str, model: str = 'qwen2.5:7b') -> list:
    """Call LLM to extract skills from summary."""
    prompt = prompt_template.replace('{{job_summary}}', summary or '')
    prompt = prompt.replace('{{job_title}}', job_title or 'Unknown')
    
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={'model': model, 'prompt': prompt, 'stream': False},
        timeout=180
    )
    result = response.json()
    ai_response = result.get('response', '')
    
    # Parse JSON
    try:
        if '```json' in ai_response:
            json_str = ai_response.split('```json')[1].split('```')[0].strip()
        elif '```' in ai_response:
            json_str = ai_response.split('```')[1].split('```')[0].strip()
        else:
            json_str = ai_response.strip()
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return []

def save_skills(cursor, posting_id: int, skills: list) -> dict:
    """Save skills to posting_skills table. Returns stats."""
    taxonomy_count = 0
    raw_count = 0
    skill_names = []
    
    for skill_item in skills:
        if isinstance(skill_item, dict):
            skill_name = skill_item.get('skill', '')
            importance = skill_item.get('importance')
            weight = skill_item.get('weight')
            proficiency = skill_item.get('proficiency')
            years_required = skill_item.get('years_required')
            reasoning = skill_item.get('reasoning')
        else:
            skill_name = str(skill_item)
            importance = weight = proficiency = years_required = reasoning = None
        
        if not skill_name:
            continue
        
        skill_names.append(skill_name)
        
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
                    proficiency = EXCLUDED.proficiency,
                    years_required = EXCLUDED.years_required,
                    reasoning = EXCLUDED.reasoning,
                    updated_at = NOW()
            """, (posting_id, skill_id, skill_name, importance, weight, 
                  proficiency, years_required, reasoning, 'backfill_skills'))
            taxonomy_count += 1
        else:
            # Check if already exists with raw_skill_name
            cursor.execute("""
                SELECT posting_skill_id FROM posting_skills
                WHERE posting_id = %s AND skill_id IS NULL AND LOWER(raw_skill_name) = LOWER(%s)
            """, (posting_id, skill_name))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE posting_skills SET
                        importance = %s, weight = %s, proficiency = %s,
                        years_required = %s, reasoning = %s, updated_at = NOW()
                    WHERE posting_skill_id = %s
                """, (importance, weight, proficiency, years_required, reasoning, existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO posting_skills (
                        posting_id, skill_id, raw_skill_name, importance, weight,
                        proficiency, years_required, reasoning, extracted_by, created_at
                    ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (posting_id, skill_name, importance, weight, 
                      proficiency, years_required, reasoning, 'backfill_skills'))
            raw_count += 1
    
    # Update postings.skill_keywords
    cursor.execute("""
        UPDATE postings SET skill_keywords = %s::jsonb, updated_at = NOW()
        WHERE posting_id = %s
    """, (json.dumps(skill_names), posting_id))
    
    return {'taxonomy': taxonomy_count, 'raw': raw_count, 'total': len(skill_names)}

def main():
    parser = argparse.ArgumentParser(description='Backfill skills for postings')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of postings to process')
    args = parser.parse_args()
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Get prompt template
    cursor.execute("""
        SELECT i.prompt_template FROM instructions i
        WHERE i.conversation_id = 9121 ORDER BY i.step_number LIMIT 1
    """)
    prompt_template = cursor.fetchone()[0]
    
    # Get postings needing backfill
    query = """
        SELECT p.posting_id, p.job_title, p.extracted_summary,
               (SELECT COUNT(*) FROM posting_skills ps WHERE ps.posting_id = p.posting_id) as current_skills
        FROM postings p
        WHERE p.extracted_summary IS NOT NULL 
          AND LENGTH(p.extracted_summary) > 100
          AND (SELECT COUNT(*) FROM posting_skills ps WHERE ps.posting_id = p.posting_id) < 3
        ORDER BY p.posting_id
    """
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    cursor.execute(query)
    postings = cursor.fetchall()
    
    print(f"=" * 70)
    print(f"🔄 SKILLS BACKFILL - {len(postings)} postings to process")
    print(f"=" * 70)
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        for p in postings[:10]:
            print(f"   Would process posting {p[0]}: {p[1]} (currently {p[3]} skills)")
        if len(postings) > 10:
            print(f"   ... and {len(postings) - 10} more")
        return
    
    stats = {'processed': 0, 'total_skills': 0, 'taxonomy': 0, 'raw': 0, 'errors': 0}
    start_time = time.time()
    
    for i, (posting_id, job_title, summary, current_skills) in enumerate(postings):
        try:
            # Extract skills
            skills = extract_skills(prompt_template, summary, job_title)
            
            if skills:
                result = save_skills(cursor, posting_id, skills)
                conn.commit()
                
                stats['processed'] += 1
                stats['total_skills'] += result['total']
                stats['taxonomy'] += result['taxonomy']
                stats['raw'] += result['raw']
                
                print(f"[{i+1}/{len(postings)}] ✅ {posting_id}: {job_title[:40]} - {result['total']} skills (tax:{result['taxonomy']}, raw:{result['raw']})")
            else:
                print(f"[{i+1}/{len(postings)}] ⚠️  {posting_id}: No skills extracted")
                
        except Exception as e:
            stats['errors'] += 1
            print(f"[{i+1}/{len(postings)}] ❌ {posting_id}: {str(e)[:50]}")
            conn.rollback()
        
        # Rate limit
        if i > 0 and i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(postings) - i) / rate if rate > 0 else 0
            print(f"   📊 Progress: {i}/{len(postings)} ({rate:.1f}/s) ETA: {remaining/60:.1f}m")
    
    # Final stats
    elapsed = time.time() - start_time
    print(f"\n" + "=" * 70)
    print(f"📋 BACKFILL COMPLETE")
    print(f"=" * 70)
    print(f"Postings processed: {stats['processed']}")
    print(f"Total skills saved: {stats['total_skills']}")
    print(f"  - Taxonomy matched: {stats['taxonomy']}")
    print(f"  - Raw (non-taxonomy): {stats['raw']}")
    print(f"Errors: {stats['errors']}")
    print(f"Time: {elapsed:.1f}s ({stats['processed']/elapsed:.1f} postings/s)")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
