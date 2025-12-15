#!/usr/bin/env python3
"""
Add more variations to Recipe 1111 for comprehensive grader testing
====================================================================

Add 3 more job postings (for total of 5 test cases):
- job50579.json (Consultant DBMC)
- job59021.json 
- job61127.json
"""

import sqlite3
import json

DB_PATH = "/home/xai/Documents/ty_learn/data/llmcore.db"

def add_test_variations():
    """Add 3 more variations from different job postings"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get Recipe 1111 ID
    recipe_id = 1111
    
    # Job postings to add (pick ones not yet used)
    job_files = [
        'data/postings/job59021.json', 
        'data/postings/job61127.json',
        'data/postings/job62800.json'
    ]
    
    variation_ids = []
    
    for job_file in job_files:
        # Load job posting
        with open(job_file, 'r') as f:
            job_data = json.load(f)
        
        posting_text = job_data.get('posting_text', '')
        job_id = job_data.get('job_id', job_file.split('/')[-1].replace('.json', ''))
        
        # Check if variation already exists
        cursor.execute("""
            SELECT variation_id FROM variations 
            WHERE variations_param_1 = ?
        """, (posting_text,))
        
        existing = cursor.fetchone()
        
        if existing:
            variation_id = existing[0]
            print(f"✅ Using existing variation {variation_id} for {job_id}")
        else:
            # Create new variation
            cursor.execute("""
                INSERT INTO variations (recipe_id, variations_param_1, difficulty_level)
                VALUES (?, ?, 1)
            """, (recipe_id, posting_text))
            variation_id = cursor.lastrowid
            print(f"✅ Created variation {variation_id} for {job_id}")
        
        variation_ids.append(variation_id)
        
        # Create recipe_run
        cursor.execute("""
            INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
            VALUES (?, ?, 7, 'PENDING')
        """, (recipe_id, variation_id))
        
        recipe_run_id = cursor.lastrowid
        print(f"   Recipe Run {recipe_run_id}: {posting_text[:60]}...")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ ADDED 3 MORE TEST VARIATIONS")
    print(f"{'='*70}")
    print(f"Recipe 1111 now has 5+ test cases")
    print(f"New variation IDs: {variation_ids}")
    print(f"\nNext: python3 recipe_run_test_runner_v32.py --max-runs 3")
    print(f"{'='*70}")

if __name__ == "__main__":
    add_test_variations()
