#!/usr/bin/env python3
"""
Fetch jobs from external APIs and create workflow_runs.

Usage: ./scripts/run_workflow.sh fetch_jobs.py --source db --max 250

This script:
1. Fetches jobs from Deutsche Bank API (or other sources)
2. Inserts new postings into the database
3. Creates workflow_runs for each new posting (workflow 3001)
4. Workflow 3001 picks them up and processes them

DO NOT run directly - use the wrapper!

Author: Sandy (ℶ)
Date: 2025-11-30
"""

import sys
import os
import argparse
import json
import requests
from datetime import datetime

# Unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Add project root to path
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

# Parse args BEFORE guard (so --help works without wrapper)
parser = argparse.ArgumentParser(
    description='Fetch jobs from external APIs',
    formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument('--source', default='db', choices=['db'], 
                    help='Source: db (Deutsche Bank)')
parser.add_argument('--max', type=int, default=100, 
                    help='Max jobs to fetch (default: 100)')
parser.add_argument('--batch-size', type=int, default=250,
                    help='API batch size (default: 250, max: 1000)')
parser.add_argument('--start', type=int, default=1,
                    help='API start position (default: 1)')
args = parser.parse_args()

# ═══════════════════════════════════════════════════════════════
# WORKFLOW GUARD - Must use wrapper!
# ═══════════════════════════════════════════════════════════════
from core.workflow_guard import require_wrapper, complete_workflow_interaction

interaction_id = require_wrapper(
    script_name="fetch_jobs.py",
    description=f"Fetch up to {args.max} jobs from {args.source}"
)

print(f"📥 Job Fetcher")
print(f"   Source: {args.source}")
print(f"   Max jobs: {args.max}")
print(f"   Interaction: #{interaction_id}")
print("=" * 50)


def fetch_from_deutsche_bank_api(max_jobs: int, batch_size: int = 250, start_pos: int = 1) -> list:
    """
    Fetch jobs from Deutsche Bank API with pagination.
    
    Returns list of job dicts with keys:
    - external_id
    - title
    - location
    - apply_uri
    - raw_data (full API response for this job)
    """
    api_url = 'https://api-deutschebank.beesite.de/search/'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    all_jobs = []
    batch_size = min(batch_size, 1000)  # API max is 1000
    
    start = start_pos
    while len(all_jobs) < max_jobs:
        remaining = max_jobs - len(all_jobs)
        count = min(batch_size, remaining)
        
        payload = {
            'LanguageCode': 'en',
            'SearchParameters': {
                'FirstItem': start,
                'CountItem': count,
                'Sort': [{'Criterion': 'PublicationStartDate', 'Direction': 'DESC'}]
            },
            'SearchCriteria': []
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"  ⚠️  API returned {response.status_code}")
                break
                
            data = response.json()
            items = data.get('SearchResult', {}).get('SearchResultItems', [])
            
            if not items:
                print(f"  No more jobs at position {start}")
                break
            
            for item in items:
                # Flatten MatchedObjectDescriptor into top level
                if 'MatchedObjectDescriptor' in item:
                    descriptor = item.pop('MatchedObjectDescriptor')
                    item.update(descriptor)
                
                job_id = item.get('MatchedObjectId')
                if not job_id:
                    continue
                
                # Extract location
                locations = item.get('PositionLocation', [])
                location = locations[0].get('CityName', 'Unknown') if locations else 'Unknown'
                
                # Get apply URI
                apply_uri = item.get('ApplyURI', '')
                if isinstance(apply_uri, list):
                    apply_uri = apply_uri[0] if apply_uri else ''
                
                all_jobs.append({
                    'external_id': str(job_id),
                    'title': item.get('PositionTitle', 'Unknown'),
                    'location': location,
                    'apply_uri': apply_uri,
                    'raw_data': item
                })
            
            print(f"  Fetched batch {start}-{start+len(items)-1}: {len(items)} jobs")
            start += len(items)
            
            if len(items) < count:
                # No more jobs available
                break
                
        except Exception as e:
            print(f"  ❌ API error: {e}")
            break
    
    return all_jobs[:max_jobs]


def insert_jobs_and_create_workflow_runs(conn, jobs: list, source: str) -> dict:
    """
    Insert new jobs into postings table and start workflows for them.
    
    Uses start_workflow() to properly create workflow_run + seed interaction.
    
    Returns stats dict.
    """
    from core.wave_runner.workflow_starter import start_workflow
    
    cur = conn.cursor()
    
    stats = {
        'fetched': len(jobs),
        'new': 0,
        'duplicate': 0,
        'workflow_runs_created': 0,
        'errors': 0
    }
    
    for job in jobs:
        try:
            # Check if job already exists
            cur.execute(
                "SELECT posting_id FROM postings WHERE external_id = %s",
                (job['external_id'],)
            )
            existing = cur.fetchone()
            
            if existing:
                stats['duplicate'] += 1
                continue
            
            # Insert new posting
            cur.execute("""
                INSERT INTO postings (
                    external_id, posting_name, job_title, location_city, source, 
                    external_url, raw_data, fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING posting_id
            """, (
                job['external_id'],
                job['title'],  # posting_name = title
                job['title'],
                job['location'],
                source,
                job['apply_uri'],
                json.dumps(job['raw_data'])
            ))
            
            posting_id = cur.fetchone()[0]
            conn.commit()
            stats['new'] += 1
            
            # Start workflow for this posting (creates workflow_run + seed interaction)
            try:
                result = start_workflow(
                    db_conn=conn,
                    workflow_id=3001,
                    posting_id=posting_id
                )
                stats['workflow_runs_created'] += 1
            except Exception as e:
                print(f"  ⚠️  Workflow start failed for posting {posting_id}: {e}")
                # Posting was created, workflow can be started manually later
            
        except Exception as e:
            conn.rollback()
            stats['errors'] += 1
            print(f"  ❌ Error inserting job {job['external_id']}: {e}")
    
    return stats


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

try:
    # Connect to database
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    
    # Fetch jobs based on source
    if args.source == 'db':
        print(f"\n📡 Fetching from Deutsche Bank API...")
        jobs = fetch_from_deutsche_bank_api(args.max, args.batch_size, args.start)
    else:
        raise ValueError(f"Unknown source: {args.source}")
    
    print(f"\n📦 Processing {len(jobs)} fetched jobs...")
    
    # Insert and create workflow runs
    stats = insert_jobs_and_create_workflow_runs(conn, jobs, args.source)
    
    # Summary
    print()
    print("=" * 50)
    print("✅ FETCH COMPLETE")
    print(f"   Fetched from API: {stats['fetched']}")
    print(f"   New postings:     {stats['new']}")
    print(f"   Duplicates:       {stats['duplicate']}")
    print(f"   Workflow runs:    {stats['workflow_runs_created']}")
    print(f"   Errors:           {stats['errors']}")
    
    conn.close()
    
    # Record success
    complete_workflow_interaction(interaction_id, output=stats)
    
except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    complete_workflow_interaction(interaction_id, error=str(e))
    raise
