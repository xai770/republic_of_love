#!/usr/bin/env python3
"""
Fetch All German Jobs from Deutsche Bank API
=============================================

Fetches ALL jobs from Germany using pagination and proper country filtering.
The web UI shows 588 German jobs but we only have 75 - this fixes that.

Usage:
    python3 tools/fetch_all_german_jobs.py

Author: Arden & xai
Date: November 6, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import time
from typing import List, Dict, Any
from core.turing_job_fetcher import TuringJobFetcher

# Deutsche Bank API Configuration
API_URL = "https://api-deutschebank.beesite.de/search/"
API_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def fetch_all_german_jobs(max_jobs: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch all jobs from Germany using pagination
    
    The API returns 50 jobs per call, so we need to paginate.
    SearchCriteria with Country filter limits to German jobs.
    
    Args:
        max_jobs: Maximum total jobs to fetch (safety limit)
        
    Returns:
        List of all German jobs
    """
    all_jobs = []
    page = 1
    batch_size = 50
    
    print("=" * 70)
    print("🇩🇪 FETCHING ALL GERMAN JOBS FROM DEUTSCHE BANK API")
    print("=" * 70)
    print()
    
    while len(all_jobs) < max_jobs:
        first_item = (page - 1) * batch_size + 1
        
        # API Payload with Country=Germany filter
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": first_item,
                "CountItem": batch_size,
                "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}]
            },
            "SearchCriteria": [
                {
                    "CriterionName": "Country",
                    "CriterionValue": ["46"]  # 46 = Germany in their system
                }
            ]
        }
        
        print(f"📄 Page {page}: Fetching items {first_item}-{first_item + batch_size - 1}...", end=" ")
        
        try:
            response = requests.post(
                API_URL,
                headers=API_HEADERS,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ API returned {response.status_code}")
                break
            
            data = response.json()
            search_result = data.get("SearchResult", {})
            jobs = search_result.get("SearchResultItems", [])
            total_count = search_result.get("SearchResultCount", 0)
            
            if not jobs:
                print("✅ No more jobs")
                break
            
            # Flatten job structure (merge MatchedObjectDescriptor)
            for job in jobs:
                if "MatchedObjectDescriptor" in job:
                    descriptor = job.pop("MatchedObjectDescriptor")
                    job.update(descriptor)
            
            all_jobs.extend(jobs)
            
            print(f"✅ Got {len(jobs)} jobs (Total: {len(all_jobs)}/{total_count})")
            
            # If we got fewer than batch_size, we've reached the end
            if len(jobs) < batch_size:
                print(f"\n✨ Reached end of results (page returned {len(jobs)} < {batch_size})")
                break
            
            # If we've reached the total count, stop
            if len(all_jobs) >= total_count:
                print(f"\n✨ Fetched all {total_count} available jobs")
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting - be nice to the API
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print()
    print("=" * 70)
    print(f"✅ FETCHED {len(all_jobs)} GERMAN JOBS")
    print("=" * 70)
    print()
    
    return all_jobs


def save_jobs_to_database(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Save fetched jobs to Turing database using TuringJobFetcher logic
    
    Args:
        jobs: List of job dicts from API
        
    Returns:
        Stats dict with counts
    """
    print("💾 SAVING JOBS TO DATABASE")
    print("=" * 70)
    
    fetcher = TuringJobFetcher(source_id=1)
    cursor = fetcher.conn.cursor()
    
    stats = {
        'fetched': len(jobs),
        'new': 0,
        'duplicate': 0,
        'error': 0,
        'updated': 0
    }
    
    # Start fetch run
    fetch_run_id = fetcher._start_fetch_run()
    
    try:
        seen_external_ids = []
        
        for i, job_data in enumerate(jobs, 1):
            try:
                external_id = job_data.get("MatchedObjectId")
                seen_external_ids.append(external_id)
                
                # Check if exists
                cursor.execute("SELECT posting_exists(%s, %s)", (1, external_id))
                result = cursor.fetchone()
                existing_id = result['posting_exists'] if result else None
                
                if existing_id:
                    # Update last_seen
                    cursor.execute("SELECT update_posting_seen(%s, true)", (existing_id,))
                    stats['duplicate'] += 1
                    
                    if i % 50 == 0:
                        print(f"  [{i}/{len(jobs)}] Processed {stats['new']} new, {stats['duplicate']} existing...")
                else:
                    # Fetch description and insert
                    apply_uri = job_data.get("ApplyURI")
                    description = fetcher._fetch_job_description(external_id, apply_uri)
                    
                    posting_id = fetcher._insert_posting(job_data, description, fetch_run_id)
                    stats['new'] += 1
                    
                    # Show progress every 10 new jobs
                    if stats['new'] % 10 == 0 or i % 50 == 0:
                        print(f"  [{i}/{len(jobs)}] ✅ {stats['new']} new jobs saved ({stats['duplicate']} duplicates)")
                    
            except Exception as e:
                stats['error'] += 1
                print(f"  ❌ Error processing job {external_id}: {e}")
        
        # Mark missing jobs as filled
        print(f"\n🔄 Marking missing jobs as 'filled'...")
        fetcher._mark_missing_as_filled(seen_external_ids)
        
        # Complete fetch run
        fetcher._complete_fetch_run(fetch_run_id, stats)
        
        fetcher.conn.commit()
        
        print()
        print("=" * 70)
        print("✅ DATABASE SAVE COMPLETE")
        print("=" * 70)
        print(f"📊 New jobs: {stats['new']}")
        print(f"📊 Duplicates: {stats['duplicate']}")
        print(f"📊 Errors: {stats['error']}")
        print("=" * 70)
        
        return stats
        
    except Exception as e:
        fetcher._fail_fetch_run(fetch_run_id, str(e))
        fetcher.conn.rollback()
        raise
    finally:
        fetcher.conn.close()


def main():
    """Main entry point"""
    print()
    print("🚀 DEUTSCHE BANK GERMANY JOBS IMPORTER")
    print("=" * 70)
    print()
    
    # Step 1: Fetch all German jobs from API
    jobs = fetch_all_german_jobs(max_jobs=1000)
    
    if not jobs:
        print("❌ No jobs fetched. Exiting.")
        return 1
    
    print(f"\n✅ Fetched {len(jobs)} German jobs from API")
    print()
    
    # Step 2: Save to database
    stats = save_jobs_to_database(jobs)
    
    print()
    print("🎉 ALL DONE!")
    print()
    print(f"📊 Summary:")
    print(f"   • Total fetched from API: {len(jobs)}")
    print(f"   • New jobs added to database: {stats['new']}")
    print(f"   • Existing jobs (duplicates): {stats['duplicate']}")
    print(f"   • Errors: {stats['error']}")
    print()
    
    if stats['new'] > 0:
        print("💡 Next steps:")
        print("   1. Run TuringOrchestrator to extract skills from new jobs")
        print("   2. Run matching engine to find matches for all profiles")
        print()
        print("   python3 -c 'from core.turing_orchestrator import TuringOrchestrator; ")
        print("              orchestrator = TuringOrchestrator(); ")
        print("              orchestrator.process_pending_tasks(max_tasks=None)'")
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
