#!/usr/bin/env python3
"""
Batch Recipe 1121 Runner
========================

Runs Recipe 1121 (hybrid job skills extraction) on all non-TEST postings.

Usage:
    python3 scripts/batch_recipe_1121.py
"""

import sys
import time
import psycopg2.extras
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.recipe_engine import BYRecipeEngine
from core.database import get_connection


def get_postings_to_process():
    """Get all non-TEST postings that need skill extraction"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT posting_id, posting_name, job_title, job_description
        FROM postings
        WHERE posting_name NOT LIKE 'TEST_%'
        AND job_description IS NOT NULL
        AND LENGTH(job_description) > 100
        AND skill_keywords IS NULL
        ORDER BY posting_id
    """)
    
    postings = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return postings


def main():
    print("=" * 80)
    print("BATCH RECIPE 1121 - HYBRID JOB SKILLS EXTRACTION")
    print("=" * 80)
    print()
    
    # Get postings to process
    postings = get_postings_to_process()
    total = len(postings)
    
    if total == 0:
        print("✅ No postings to process! All non-TEST postings already have skill_keywords.")
        return
    
    print(f"📋 Found {total} postings to process")
    print()
    
    # Confirm
    response = input(f"Process {total} postings with Recipe 1121? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return
    
    print()
    print("🚀 Starting batch processing...")
    print()
    
    # Initialize engine
    engine = BYRecipeEngine()
    
    # Process each posting
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    for idx, posting in enumerate(postings, 1):
        posting_id = posting['posting_id']
        job_title = posting['job_title']
        
        print(f"[{idx}/{total}] Processing posting {posting_id}: {job_title[:60]}...")
        
        try:
            # Run Recipe 1121 on this posting
            success = engine.execute_recipe(
                recipe_id=1121,
                test_data=posting['job_description'],
                batch_id=1,
                difficulty_level=1,
                strict=True,
                execution_mode='production',
                job_id=posting_id,
                profile_id=None
            )
            
            if success:
                success_count += 1
                print(f"  ✅ Success ({success_count}/{total})")
            else:
                error_count += 1
                print(f"  ❌ Failed ({error_count}/{total})")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error: {e}")
        
        print()
        
        # Progress update every 10 jobs
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            remaining = (total - idx) * avg_time
            print(f"  📊 Progress: {idx}/{total} ({idx*100/total:.1f}%)")
            print(f"  ⏱️  Elapsed: {elapsed/60:.1f}m, Estimated remaining: {remaining/60:.1f}m")
            print()
    
    # Final summary
    elapsed = time.time() - start_time
    print("=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"✅ Successful: {success_count}/{total} ({success_count*100/total:.1f}%)")
    print(f"❌ Failed: {error_count}/{total} ({error_count*100/total:.1f}%)")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"⏱️  Average per job: {elapsed/total:.1f} seconds")
    print()


if __name__ == '__main__':
    main()
