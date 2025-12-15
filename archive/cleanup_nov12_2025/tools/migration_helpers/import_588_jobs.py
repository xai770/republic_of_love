#!/usr/bin/env python3
"""
Deutsche Bank Job Import Script
================================

Fetches and imports Deutsche Bank job postings from their API.
Filters out Finanzberater (financial advisory) jobs as they:
- Require authentication to view descriptions
- Are generic sales positions (not tech/professional roles)
- Have URLs that return 404 or login pages

Only imports jobs with valid Workday URLs that have accessible descriptions.

Author: Arden & xai
Date: November 7, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from core.database import get_connection

API_URL = "https://api-deutschebank.beesite.de/search/"

print()
print("=" * 70)
print("🚀 IMPORTING ALL 588 GERMAN JOBS")
print("=" * 70)
print()

# Step 1: Fetch from API
print("📥 Step 1: Fetching from API...")
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 1000,
        "MatchedObjectDescriptor": [
            "PositionID", "PositionTitle", "PositionURI",
            "PositionLocation", "PublicationStartDate",
            "CareerLevel", "OrganizationName", "ApplyURI"
        ],
        "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}]
    },
    "SearchCriteria": [
        {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
    ]
}

payload_json = json.dumps(payload, separators=(',', ':'))
url = f"{API_URL}?data={payload_json}"

response = requests.get(url, timeout=60)
data = response.json()
jobs = data.get("SearchResult", {}).get("SearchResultItems", [])

print(f"✅ Fetched {len(jobs)} jobs from API")
print()

# Step 2: Quick insert to database
print("💾 Step 2: Saving to database...")
print()

conn = get_connection()
cur = conn.cursor()

stats = {'new': 0, 'duplicate': 0, 'errors': 0, 'skipped_finanzberater': 0}

for i, job in enumerate(jobs, 1):
    try:
        desc = job.get("MatchedObjectDescriptor", {})
        job_id = desc.get("PositionID")
        
        if not job_id:
            continue
        
        # Get ApplyURI to check job type
        apply_uris = desc.get("ApplyURI", [])
        apply_uri = apply_uris[0] if apply_uris else None
        
        # FILTER: Skip Finanzberater jobs (financial advisory positions)
        # These jobs require authentication and have no accessible descriptions
        if apply_uri and 'finanzberatung' in apply_uri.lower():
            stats['skipped_finanzberater'] += 1
            if stats['skipped_finanzberater'] <= 3:  # Show first 3
                print(f"  ⏭️  Skipping Finanzberater job: {job_id} - {desc.get('PositionTitle', '')[:50]}")
            continue
        
        # Check if exists
        cur.execute("""
            SELECT posting_id FROM postings 
            WHERE source_id = 1 AND external_job_id = %s
        """, (str(job_id),))
        
        if cur.fetchone():
            stats['duplicate'] += 1
        else:
            # Extract location
            locations = desc.get("PositionLocation", [])
            location = locations[0] if locations else {}
            
            # Extract career level
            career_levels = desc.get("CareerLevel", [])
            career_level = career_levels[0].get("Name") if career_levels else None
            
            # Get job title - make unique if needed
            base_title = desc.get("PositionTitle", "Unknown Position")
            
            # Check if this title already exists for this source
            cur.execute("""
                SELECT posting_id FROM postings
                WHERE source_id = 1 AND posting_name = %s
            """, (base_title,))
            
            if cur.fetchone():
                # Make title unique by appending job ID
                job_title = f"{base_title} (ID: {job_id})"
            else:
                job_title = base_title
            
            # Get Workday ApplyURI and remove /apply suffix
            # ApplyURI points to application form, we want the job description page
            apply_uris = desc.get("ApplyURI", [])
            apply_uri = apply_uris[0] if apply_uris else None
            
            # CRITICAL: Remove /apply suffix to get job page, not application page
            if apply_uri and apply_uri.endswith('/apply'):
                external_url = apply_uri.replace('/apply', '')
            else:
                external_url = apply_uri
            
            cur.execute("""
                INSERT INTO postings (
                    source_id, external_job_id, posting_name, job_title, job_description,
                    location_city, location_country,
                    employment_career_level, external_url, posting_status, 
                    first_seen_at, last_seen_at, source_metadata
                ) VALUES (
                    1, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW(), %s
                )
            """, (
                str(job_id),
                job_title,  # posting_name (required)
                job_title,  # job_title
                "",  # Empty description for now
                location.get("CityName") if isinstance(location, dict) else None,
                location.get("CountryName") if isinstance(location, dict) else None,
                career_level,
                external_url,  # Workday URL
                json.dumps(desc),  # Store full API response in metadata
            ))
            stats['new'] += 1
        
        # Progress every 100 jobs
        if i % 100 == 0:
            conn.commit()  # Commit periodically
            print(f"  Progress: {i}/{len(jobs)} ({stats['new']} new, {stats['duplicate']} duplicates)")
            
    except Exception as e:
        conn.rollback()  # Rollback on error to continue
        stats['errors'] += 1
        if stats['errors'] <= 5:  # Only show first 5 errors
            print(f"  ❌ Error with job {job_id}: {e}")

conn.commit()  # Final commit
conn.close()

print()
print("=" * 70)
print("✅ IMPORT COMPLETE!")
print("=" * 70)
print(f"Total jobs processed: {len(jobs)}")
print(f"New jobs added: {stats['new']}")
print(f"Duplicates skipped: {stats['duplicate']}")
print(f"Finanzberater skipped: {stats['skipped_finanzberater']}")
print(f"Errors: {stats['errors']}")
print("=" * 70)
print()

if stats['new'] > 0:
    print(f"💡 Next step: Extract skills from {stats['new']} new jobs")
    print()
    print("   python3 -c 'from core.turing_orchestrator import TuringOrchestrator;")
    print("              TuringOrchestrator().process_pending_tasks(max_tasks=None)'")
    print()
