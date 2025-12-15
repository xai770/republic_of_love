#!/usr/bin/env python3
"""
Process the 181 jobs already fetched in workflow 267
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import time

conn = get_connection()
cursor = conn.cursor()

# Get staging_ids from workflow 267
cursor.execute("""
    SELECT jsonb_array_elements_text(state->'staging_ids')::int as staging_id
    FROM workflow_runs 
    WHERE workflow_run_id = 267
    ORDER BY 1
""")

staging_ids = [row['staging_id'] for row in cursor.fetchall()]
print(f"Found {len(staging_ids)} staging IDs from workflow 267")
print(f"Starting processing...\n")

completed = 0
failed = 0
start_time = time.time()

for idx, staging_id in enumerate(staging_ids, 1):
    try:
        # Get posting_id
        cursor.execute("SELECT posting_id FROM postings WHERE created_by_staging_id = %s", (staging_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"[{idx}/{len(staging_ids)}] Staging {staging_id}: No posting found")
            failed += 1
            continue
            
        posting_id = row['posting_id']
        
        # Check if already processed
        cursor.execute("""
            SELECT workflow_run_id 
            FROM workflow_runs 
            WHERE workflow_id = 3001 AND posting_id = %s AND status = 'completed'
            LIMIT 1
        """, (posting_id,))
        
        if cursor.fetchone():
            print(f"[{idx}/{len(staging_ids)}] Posting {posting_id}: Already processed ✓")
            completed += 1
            continue
        
        # Start workflow
        print(f"[{idx}/{len(staging_ids)}] Processing posting {posting_id}...", end='', flush=True)
        job_start = time.time()
        
        result = start_workflow(
            db_conn=conn,
            workflow_id=3001,
            posting_id=posting_id
        )
        
        workflow_run_id = result['workflow_run_id']
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        result = runner.run(max_iterations=100)
        
        duration = time.time() - job_start
        
        if result['status'] == 'completed':
            completed += 1
            print(f" ✅ Done in {duration:.1f}s")
        else:
            failed += 1
            print(f" ❌ Failed: {result.get('error', 'Unknown')}")
            
        # Progress stats every 10 jobs
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = len(staging_ids) - idx
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60
            
            print(f"\n📊 Progress: {idx}/{len(staging_ids)} ({100*idx/len(staging_ids):.1f}%)")
            print(f"   Completed: {completed} | Failed: {failed}")
            print(f"   Rate: {rate:.2f} jobs/sec | ETA: {eta_minutes:.1f} min\n")
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted at job {idx}/{len(staging_ids)}")
        print(f"   Completed: {completed} | Failed: {failed}")
        sys.exit(1)
    except Exception as e:
        failed += 1
        print(f" ❌ Error: {e}")

# Final stats
total_time = time.time() - start_time
print(f"\n{'='*80}")
print(f"FINAL STATS")
print(f"{'='*80}")
print(f"Total: {len(staging_ids)}")
print(f"Completed: {completed}")
print(f"Failed: {failed}")
print(f"Duration: {total_time/60:.1f} minutes")
print(f"Rate: {len(staging_ids)/total_time:.2f} jobs/sec")
