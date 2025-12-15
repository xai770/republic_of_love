#!/usr/bin/env python3
"""
Batch Run Recipe 1121 on jobs with extracted summaries
Processes all jobs that have summaries from Recipe 1114
"""

import sys
import json
import psycopg2
from universal_executor import UniversalExecutor

DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def get_jobs_with_summaries():
    """Get list of job_ids that have extracted_summary"""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id, LENGTH(COALESCE(extracted_summary, job_description)) as content_length
            FROM postings
            WHERE skill_keywords::text = '[]' OR skill_keywords IS NULL
            ORDER BY job_id
        """)
        jobs = cur.fetchall()
    conn.close()
    return jobs

def run_recipe_1121(executor, job_id):
    """Execute Recipe 1121 for a single job"""
    
    # Get job data
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id, job_description, extracted_summary
            FROM postings WHERE job_id = %s
        """, (job_id,))
        row = cur.fetchone()
    conn.close()
    
    if not row:
        return {'status': 'error', 'message': f'Job {job_id} not found'}
    
    job_id, job_desc, summary = row
    
    # Fetch instructions
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                i.instruction_id,
                i.step_number,
                i.prompt_template,
                COALESCE(i.delegate_actor_id, s.actor_id) as actor_id
            FROM instructions i
            JOIN sessions s ON i.session_id = s.session_id
            WHERE s.session_id = 9121
            ORDER BY i.step_number
        """)
        instructions = cur.fetchall()
    conn.close()
    
    # Execute pipeline
    context = {
        'job_id': job_id,
        'job_description': job_desc or '',
        'extracted_summary': summary or ''
    }
    previous_response = summary or job_desc
    
    try:
        for instr_id, step_num, prompt_template, actor_id in instructions:
            # Render prompt
            prompt = prompt_template
            prompt = prompt.replace('{{job_id}}', str(job_id))
            prompt = prompt.replace('{{job_description}}', context['job_description'])
            prompt = prompt.replace('{{extracted_summary}}', context['extracted_summary'])
            prompt = prompt.replace('{{PREVIOUS_RESPONSE}}', previous_response)
            
            # Execute with progress
            print(f"  → Step {step_num} ({actor_id})...", end='', flush=True)
            response = executor.call_actor(actor_id, prompt, context)
            print(f" ✓")
            previous_response = response
        
        # Parse final skills array
        cleaned = previous_response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
        
        skills = json.loads(cleaned.strip())
        
        # Save to postings.skill_keywords
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE postings 
                SET skill_keywords = %s::jsonb
                WHERE job_id = %s
            """, (json.dumps(skills), job_id))
            conn.commit()
        conn.close()
        
        return {
            'status': 'success',
            'job_id': job_id,
            'skills_count': len(skills),
            'skills': skills
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'job_id': job_id,
            'message': str(e)
        }

def main():
    executor = UniversalExecutor()
    
    jobs = get_jobs_with_summaries()
    print(f"🎯 Processing {len(jobs)} jobs with extracted summaries")
    print("=" * 80)
    
    results = []
    for i, (job_id, summary_length) in enumerate(jobs, 1):
        print(f"\n[{i}/{len(jobs)}] Job {job_id} (summary: {summary_length} chars)")
        
        result = run_recipe_1121(executor, job_id)
        results.append(result)
        
        if result['status'] == 'success':
            print(f"  ✅ SUCCESS: {result['skills_count']} skills extracted")
            for skill in result['skills'][:5]:
                print(f"     - {skill}")
            if result['skills_count'] > 5:
                print(f"     ... and {result['skills_count'] - 5} more")
        else:
            print(f"  ❌ ERROR: {result.get('message', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 BATCH SUMMARY:")
    print("-" * 80)
    
    successes = [r for r in results if r['status'] == 'success']
    errors = [r for r in results if r['status'] == 'error']
    
    print(f"✅ Successful: {len(successes)}")
    print(f"❌ Failed: {len(errors)}")
    
    if successes:
        total_skills = sum(r['skills_count'] for r in successes)
        avg_skills = total_skills / len(successes)
        print(f"📦 Total skills extracted: {total_skills}")
        print(f"📊 Average skills per job: {avg_skills:.1f}")
    
    if errors:
        print(f"\n❌ Failed jobs:")
        for r in errors:
            print(f"   - {r['job_id']}: {r.get('message', 'Unknown')}")
    
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
