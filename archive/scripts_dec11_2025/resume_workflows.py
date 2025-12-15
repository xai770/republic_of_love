#!/usr/bin/env python3
"""
Resume Workflow 3001 for all unprocessed postings.
Processes postings that need summary/skills/IHL.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from datetime import datetime
import time

load_dotenv()

def main():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    from core.wave_runner.workflow_starter import start_workflow
    from core.wave_runner.runner import WaveRunner
    
    cursor = conn.cursor()
    
    # Get postings that need processing
    cursor.execute("""
        SELECT posting_id 
        FROM postings 
        WHERE invalidated = false 
          AND source = 'db'
          AND (extracted_summary IS NULL OR skill_keywords IS NULL OR ihl_score IS NULL)
          AND job_description IS NOT NULL
          AND LENGTH(job_description) >= 100
        ORDER BY posting_id
    """)
    
    posting_ids = [row[0] for row in cursor.fetchall()]
    total = len(posting_ids)
    
    print(f"\n{'='*70}")
    print(f"WORKFLOW 3001 BATCH PROCESSOR")
    print(f"{'='*70}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Postings to process: {total}")
    print(f"{'='*70}\n")
    
    completed = 0
    failed = 0
    start_time = time.time()
    
    for idx, posting_id in enumerate(posting_ids, 1):
        try:
            print(f"\n[{idx}/{total}] Processing posting {posting_id}...")
            
            result = start_workflow(
                conn,
                workflow_id=3001,
                posting_id=posting_id,
                start_conversation_id=9193  # Start from Validate (skip fetch)
            )
            
            runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
            wave_result = runner.run(max_iterations=30)
            
            if wave_result['interactions_failed'] == 0:
                completed += 1
                print(f"  ✅ Completed ({wave_result['interactions_completed']} interactions, {wave_result['duration_ms']/1000:.1f}s)")
            else:
                failed += 1
                print(f"  ❌ Failed ({wave_result['interactions_failed']} failures)")
                
        except Exception as e:
            failed += 1
            print(f"  🔥 Error: {e}")
        
        # Progress stats
        elapsed = time.time() - start_time
        rate = idx / elapsed * 60 if elapsed > 0 else 0
        remaining = (total - idx) / rate if rate > 0 else 0
        
        print(f"  📊 Progress: {idx}/{total} ({100*idx/total:.1f}%) | Rate: {rate:.1f}/min | ETA: {remaining:.0f} min")
    
    print(f"\n{'='*70}")
    print(f"BATCH COMPLETE")
    print(f"{'='*70}")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    print(f"Duration: {(time.time()-start_time)/60:.1f} minutes")
    print(f"{'='*70}\n")
    
    conn.close()

if __name__ == '__main__':
    main()
