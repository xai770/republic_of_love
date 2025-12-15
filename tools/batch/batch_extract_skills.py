#!/usr/bin/env python3
"""
Batch Skills Extraction for Deutsche Bank Jobs
Runs Workflow 2001 (or just the skills extraction part) on all active jobs

Usage:
    python3 tools/batch_extract_skills.py
"""

import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'turing',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def get_jobs_needing_skills():
    """Get Deutsche Bank jobs that need skills extraction"""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT posting_id, external_job_id, job_title
        FROM postings 
        WHERE source_id = 1
          AND posting_status = 'active'
          AND job_description IS NOT NULL
          AND LENGTH(job_description) > 200
          AND (skill_keywords IS NULL OR jsonb_array_length(skill_keywords) = 0)
        ORDER BY posting_id
    """)
    
    jobs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jobs

def check_has_skills(posting_id):
    """Check if job already has skills extracted"""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT skill_keywords IS NOT NULL 
               AND jsonb_array_length(skill_keywords) > 0 as has_skills
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result['has_skills'] if result else False

def extract_skills_for_job(posting_id):
    """Run workflow 1121 for a single job (skills extraction only)"""
    # Double-check job doesn't already have skills (may have been processed since query)
    if check_has_skills(posting_id):
        return True  # Already has skills, count as success
    
    cmd = [
        'python3',
        '/home/xai/Documents/ty_learn/scripts/by_recipe_runner.py',
        '--recipe-id', '1121',  # Use Recipe 1121 directly (skills only)
        '--job-id', str(posting_id),
        '--execution-mode', 'production'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout per job
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    ⏰ Timeout (3 minutes exceeded)")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("DEUTSCHE BANK - SKILLS EXTRACTION BATCH RUNNER")
    print("=" * 70)
    print()
    
    # Get jobs needing extraction
    print("📊 Loading jobs without skills...")
    jobs = get_jobs_needing_skills()
    total = len(jobs)
    print(f"✅ Found {total} jobs needing skills extraction")
    print()
    
    if total == 0:
        print("🎉 All jobs already have skills extracted!")
        return
    
    # Process each job
    print("🚀 Starting batch processing...")
    print("━" * 70)
    print()
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    for i, job in enumerate(jobs, 1):
        posting_id = job['posting_id']
        job_id = job['external_job_id']
        title = job['job_title'][:50]
        
        print(f"[{i}/{total}] Job {job_id}: {title}...")
        
        success = extract_skills_for_job(posting_id)
        
        if success:
            success_count += 1
            print(f"    ✅ Success")
        else:
            error_count += 1
            print(f"    ⚠️  Failed")
        
        # Show progress
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        remaining = (total - i) / rate if rate > 0 else 0
        
        print(f"    📊 Progress: {i}/{total} | Success: {success_count} | Failed: {error_count} | ETA: {int(remaining/60)}m {int(remaining%60)}s")
        print()
    
    # Final summary
    elapsed = time.time() - start_time
    print("=" * 70)
    print("✅ BATCH PROCESSING COMPLETE")
    print("=" * 70)
    print(f"Total jobs processed: {total}")
    print(f"Successful: {success_count}")
    print(f"Failed: {error_count}")
    print(f"Total time: {int(elapsed/60)}m {int(elapsed%60)}s")
    print(f"Average: {elapsed/total:.1f}s per job")
    print("=" * 70)

if __name__ == '__main__':
    main()
