#!/usr/bin/env python3
"""
Test job fetcher lifecycle management:
1. First run: Fetch 5 jobs (should insert 5 new)
2. Second run: Fetch same 5 jobs (should update last_seen_at on 5)
3. Third run: Fetch only 3 jobs (should invalidate 2 missing jobs)

This validates the complete posting lifecycle as documented in:
- docs/posting_sources/DEUTSCHE_BANK_CHALLENGES.md
- core/turing_job_fetcher.py (reference implementation)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import subprocess
import time

def run_fetch(max_jobs, run_description):
    """Run job fetcher with specified max_jobs"""
    print(f"\n{'='*80}")
    print(f"{run_description}")
    print(f"{'='*80}\n")
    
    conn = get_connection()
    
    try:
        # Start workflow from Job Fetcher
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=None,
            start_conversation_id=9144,
            params={
                "max_jobs": max_jobs,
                "skip_rate_limit": True,
                "search_text": ""
            }
        )
        
        workflow_run_id = result['workflow_run_id']
        print(f"Workflow run_id: {workflow_run_id}")
        
        # Run fetcher
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        start_time = time.time()
        wave_result = runner.run(max_iterations=1)
        duration = time.time() - start_time
        
        # Get results
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state FROM workflow_runs WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        
        state = cursor.fetchone()['state']
        
        # Get interaction output (has the actual stats)
        cursor.execute("""
            SELECT output FROM interactions
            WHERE workflow_run_id = %s AND conversation_id = 9144
        """, (workflow_run_id,))
        
        output = cursor.fetchone()['output']
        data = output.get('data', {})
        
        print(f"\n{'='*80}")
        print(f"RESULTS")
        print(f"{'='*80}")
        print(f"Duration: {duration:.2f}s")
        print(f"Jobs fetched (new): {data.get('jobs_fetched', 0)}")
        print(f"Jobs updated (existing): {data.get('jobs_updated', 0)}")
        print(f"Jobs invalidated (removed): {data.get('jobs_invalidated', 0)}")
        print(f"Total available in API: {data.get('total_available', 0)}")
        
        # Check database state
        cursor.execute("""
            SELECT 
                COUNT(*) as total_staging,
                COUNT(CASE WHEN promoted_to_posting_id IS NOT NULL THEN 1 END) as promoted
            FROM postings_staging
            WHERE source_website = 'deutsche_bank'
        """)
        staging = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN invalidated = FALSE THEN 1 END) as active,
                COUNT(CASE WHEN invalidated = TRUE THEN 1 END) as invalidated,
                MAX(last_seen_at) as most_recent_seen
            FROM postings
            WHERE source = 'deutsche_bank'
        """)
        postings = cursor.fetchone()
        
        print(f"\nDatabase State:")
        print(f"  Staging: {staging['total_staging']} total, {staging['promoted']} promoted")
        print(f"  Postings: {postings['total']} total, {postings['active']} active, {postings['invalidated']} invalidated")
        if postings['most_recent_seen']:
            print(f"  Most recent seen: {postings['most_recent_seen']}")
        
        cursor.close()
        
        return {
            'workflow_run_id': workflow_run_id,
            'new': data.get('jobs_fetched', 0),
            'updated': data.get('jobs_updated', 0),
            'invalidated': data.get('jobs_invalidated', 0),
            'duration': duration
        }
        
    finally:
        conn.close()

def promote_staging_to_postings():
    """Manually promote staging records to postings for testing"""
    print(f"\n{'='*80}")
    print(f"PROMOTING STAGING → POSTINGS")
    print(f"{'='*80}\n")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT staging_id, job_title, posting_url, raw_data
        FROM postings_staging
        WHERE source_website = 'deutsche_bank'
          AND promoted_to_posting_id IS NULL
        ORDER BY staging_id
    """)
    
    staging_records = cursor.fetchall()
    print(f"Found {len(staging_records)} staging records to promote")
    
    for record in staging_records:
        # Extract data from raw_data
        raw = record['raw_data']
        external_id = raw.get('external_id', 'unknown')
        job_description = raw.get('job_description', '')
        
        # Insert into postings
        cursor.execute("""
            INSERT INTO postings (
                source,
                external_url,
                posting_name,
                job_title,
                job_description,
                location_city,
                fetched_at,
                first_seen_at,
                last_seen_at,
                created_by_staging_id
            ) VALUES (
                'deutsche_bank',
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                %s
            )
            RETURNING posting_id
        """, (
            record['posting_url'],
            f"db_{external_id}",
            record['job_title'],
            job_description or '',
            raw.get('location', ''),
            record['staging_id']
        ))
        
        posting_id = cursor.fetchone()['posting_id']
        
        # Update staging record
        cursor.execute("""
            UPDATE postings_staging
            SET promoted_to_posting_id = %s,
                promoted_at = CURRENT_TIMESTAMP,
                validation_status = 'promoted'
            WHERE staging_id = %s
        """, (posting_id, record['staging_id']))
        
        print(f"  Promoted staging {record['staging_id']} → posting {posting_id}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Promoted {len(staging_records)} records to postings")

def main():
    """
    Test lifecycle:
    1. Fetch 5 jobs → should insert 5 new
    2. Promote to postings
    3. Fetch same 5 → should update last_seen_at on 5
    4. Fetch only 3 → should invalidate 2
    """
    
    results = []
    
    # RUN 1: Fetch 5 jobs (new inserts)
    result1 = run_fetch(5, "RUN 1: Fetch 5 jobs (expecting 5 NEW)")
    results.append(('Run 1 (new)', result1))
    
    # Promote to postings
    promote_staging_to_postings()
    
    time.sleep(2)
    
    # RUN 2: Fetch same 5 jobs (should update last_seen_at)
    result2 = run_fetch(5, "RUN 2: Re-fetch same 5 jobs (expecting 5 UPDATED)")
    results.append(('Run 2 (update)', result2))
    
    time.sleep(2)
    
    # RUN 3: Fetch only 3 jobs (should invalidate 2)
    result3 = run_fetch(3, "RUN 3: Fetch only 3 jobs (expecting 3 UPDATED, 2 INVALIDATED)")
    results.append(('Run 3 (invalidate)', result3))
    
    # Generate trace for final run
    print(f"\n{'='*80}")
    print(f"GENERATING TRACE FOR RUN 3 (INVALIDATION TEST)")
    print(f"{'='*80}\n")
    
    subprocess.run([
        "python3", "tools/generate_retrospective_trace.py",
        str(result3['workflow_run_id']),
        f"trace_fetcher_lifecycle_run_{result3['workflow_run_id']}"
    ])
    
    # Summary
    print(f"\n{'='*80}")
    print(f"LIFECYCLE TEST SUMMARY")
    print(f"{'='*80}\n")
    
    for name, result in results:
        print(f"{name}:")
        print(f"  New: {result['new']}, Updated: {result['updated']}, Invalidated: {result['invalidated']}")
        print(f"  Duration: {result['duration']:.2f}s")
        print()
    
    # Validate expectations
    print(f"VALIDATION:")
    success = True
    
    if result1['new'] != 5:
        print(f"  ❌ Run 1: Expected 5 new, got {result1['new']}")
        success = False
    else:
        print(f"  ✅ Run 1: 5 new jobs inserted")
    
    if result2['updated'] != 5:
        print(f"  ❌ Run 2: Expected 5 updated, got {result2['updated']}")
        success = False
    else:
        print(f"  ✅ Run 2: 5 jobs updated (last_seen_at)")
    
    if result3['updated'] != 3:
        print(f"  ❌ Run 3: Expected 3 updated, got {result3['updated']}")
        success = False
    else:
        print(f"  ✅ Run 3: 3 jobs updated")
    
    if result3['invalidated'] != 2:
        print(f"  ❌ Run 3: Expected 2 invalidated, got {result3['invalidated']}")
        success = False
    else:
        print(f"  ✅ Run 3: 2 jobs invalidated (removed from site)")
    
    if success:
        print(f"\n🎉 ALL TESTS PASSED - LIFECYCLE MANAGEMENT WORKING!")
        print(f"\nReady to discuss with Arden:")
        print(f"  - Posting lifecycle tracking fully implemented")
        print(f"  - Matches architecture in turing_job_fetcher.py")
        print(f"  - Documented in cheat sheet (Architecture Principle #7)")
        return 0
    else:
        print(f"\n⚠️  SOME TESTS FAILED - NEEDS ITERATION")
        print(f"Check trace: reports/trace_fetcher_lifecycle_run_{result3['workflow_run_id']}.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
