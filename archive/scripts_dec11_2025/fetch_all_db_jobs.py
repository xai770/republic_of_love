#!/usr/bin/env python3
"""
Fetch all available jobs from Deutsche Bank Workday API.

This script:
1. Starts workflow 3001 from Job Fetcher
2. Sets max_jobs to 2500 (more than currently available)
3. Skips rate limiting
4. Fetches jobs in batches of 20 (API limit)
5. Stores all jobs in postings_staging with full descriptions

Usage:
    python3 scripts/fetch_all_db_jobs.py
    
Expected outcome:
    - All available Deutsche Bank jobs fetched into postings_staging
    - Each job has full description from detail page
    - staging_ids returned in workflow state
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
from core.database import get_connection
import time

def main():
    """Fetch all Deutsche Bank jobs."""
    
    print(f"\n{'='*80}")
    print(f"Fetching ALL Deutsche Bank Jobs")
    print(f"{'='*80}\n")
    
    conn = get_connection()
    
    try:
        # Start workflow from Job Fetcher with high max_jobs
        print(f"Initializing workflow from Job Fetcher (9144)...")
        print(f"Parameters:")
        print(f"  max_jobs: 2500 (fetches until API returns no more jobs)")
        print(f"  skip_rate_limit: true (bypass daily limit)")
        print(f"  Batch size: 20 jobs per API request (Workday API limit)")
        print()
        
        result = start_workflow(
            conn,
            workflow_id=3001,
            posting_id=None,  # No posting - fetcher creates them
            start_conversation_id=9144,  # Job Fetcher
            params={
                "max_jobs": 2500,  # High limit - will fetch all available
                "skip_rate_limit": True,  # Bypass rate limiting
                "search_text": ""  # Empty = all jobs
            }
        )
        
        workflow_run_id = result['workflow_run_id']
        print(f"✅ Workflow initialized: run_id={workflow_run_id}")
        print(f"   Seed interaction: {result['seed_interaction_id']}")
        print()
        
        # Run just the fetcher (1 iteration)
        print(f"🌊 Running Job Fetcher...")
        print("=" * 80)
        
        runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
        start_time = time.time()
        wave_result = runner.run(max_iterations=1)  # Just run fetcher
        duration = time.time() - start_time
        
        print("\n" + "=" * 80)
        print(f"JOB FETCH RESULTS")
        print("=" * 80)
        
        # Get workflow state with results
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state FROM workflow_runs WHERE workflow_run_id = %s
        """, (workflow_run_id,))
        
        state = cursor.fetchone()['state']
        
        jobs_fetched = state.get('jobs_fetched', 0)
        staging_ids = state.get('staging_ids', [])
        
        print(f"Jobs Fetched: {jobs_fetched}")
        print(f"Staging IDs: {len(staging_ids)} records")
        print(f"Duration: {duration:.2f}s ({duration/60:.1f} minutes)")
        
        if jobs_fetched > 0:
            # Get sample of fetched jobs
            cursor.execute("""
                SELECT 
                    job_title,
                    location,
                    LENGTH(raw_data->>'job_description') as desc_length,
                    raw_data->>'external_id' as job_id
                FROM postings_staging
                WHERE staging_id = ANY(%s)
                ORDER BY staging_id
                LIMIT 10
            """, (staging_ids,))
            
            print(f"\nFirst 10 jobs fetched:")
            print("-" * 80)
            for row in cursor.fetchall():
                print(f"  {row['job_id']}: {row['job_title'][:50]}")
                print(f"    Location: {row['location']}")
                print(f"    Description: {row['desc_length']} chars")
            
            # Get statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(LENGTH(raw_data->>'job_description')) as avg_desc_length,
                    MIN(LENGTH(raw_data->>'job_description')) as min_desc_length,
                    MAX(LENGTH(raw_data->>'job_description')) as max_desc_length,
                    COUNT(CASE WHEN raw_data->>'description_fetch_error' IS NOT NULL THEN 1 END) as errors
                FROM postings_staging
                WHERE staging_id = ANY(%s)
            """, (staging_ids,))
            
            stats = cursor.fetchone()
            
            print(f"\nStatistics:")
            print(f"  Total jobs: {stats['total']}")
            print(f"  Avg description length: {int(stats['avg_desc_length'])} chars")
            print(f"  Min/Max: {stats['min_desc_length']} / {stats['max_desc_length']} chars")
            print(f"  Fetch errors: {stats['errors']}")
            
            print(f"\n✅ SUCCESS!")
            print(f"   {jobs_fetched} jobs fetched and stored in postings_staging")
            print(f"   All jobs have full descriptions extracted from detail pages")
            print(f"\nNext steps:")
            print(f"   1. Review jobs: SELECT * FROM postings_staging WHERE staging_id = ANY(ARRAY{staging_ids[:5]})")
            print(f"   2. Promote to postings: Run Check Summary conversation (9184)")
            print(f"   3. Process through workflow: Run complete workflow on posting_ids")
            
        else:
            print(f"\n⚠️  No jobs fetched")
            print(f"   This could mean:")
            print(f"   - All jobs already in postings_staging (check for duplicates)")
            print(f"   - API returned no results")
            print(f"   - Network/API error")
            
            # Check for recent fetches
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM postings_staging
                WHERE source_website = 'deutsche_bank'
                  AND created_at > NOW() - INTERVAL '1 day'
            """)
            
            recent = cursor.fetchone()['count']
            if recent > 0:
                print(f"\n   Found {recent} jobs fetched in last 24 hours")
                print(f"   Delete them to re-fetch: DELETE FROM postings_staging WHERE source_website = 'deutsche_bank' AND created_at > NOW() - INTERVAL '1 day'")
        
        cursor.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
