#!/usr/bin/env python3
"""
Deutsche Bank Worldwide Job Import
===================================

Import ALL Deutsche Bank jobs from around the world.
Filters out Finanzberater (financial advisory) jobs.

Strategy:
1. Fetch jobs without country filter (get all)
2. Skip Finanzberater jobs (no accessible descriptions)
3. Import only Workday jobs with accessible descriptions

Author: Arden & xai
Date: November 7, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from core.database import get_connection
from tools.fetch_workday_descriptions import fetch_descriptions_for_jobs

API_URL = "https://api-deutschebank.beesite.de/search/"

print()
print("=" * 70)
print("🌍 IMPORTING DEUTSCHE BANK JOBS WORLDWIDE")
print("=" * 70)
print()

# Step 1: Fetch from API (NO country filter = worldwide)
print("📥 Step 1: Fetching ALL jobs worldwide from API...")
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 5000,  # Get as many as possible
        "MatchedObjectDescriptor": [
            "PositionID", "PositionTitle", "PositionURI",
            "PositionLocation",  # CRITICAL: Must request this field
            "PublicationStartDate",
            "CareerLevel", "OrganizationName", "ApplyURI"
        ],
        "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}]
    },
    # NO SearchCriteria = all countries
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
print("   Filters:")
print("   - Skipping Finanzberater jobs (no accessible descriptions)")
print("   - Skipping duplicates (by external_job_id)")
print()

from psycopg2.extras import RealDictCursor
conn = get_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

stats = {
    'new': 0, 
    'duplicate': 0, 
    'errors': 0, 
    'skipped_finanzberater': 0,
    'updated_last_seen': 0
}

# Track which job IDs we see in the API (to detect removed jobs later)
api_job_ids = set()

# Track new posting IDs for description fetching
new_posting_ids = []

# Track countries
countries = {}

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
        if apply_uri and 'finanzberatung' in apply_uri.lower():
            stats['skipped_finanzberater'] += 1
            continue
        
        # Track this job ID as seen in the API
        api_job_ids.add(str(job_id))
        
        # Check if exists
        cur.execute("""
            SELECT posting_id FROM postings 
            WHERE source_id = 1 AND external_job_id = %s
        """, (str(job_id),))
        
        existing = cur.fetchone()
        if existing:
            # Update last_seen_at to mark job as still active
            cur.execute("""
                UPDATE postings
                SET last_seen_at = NOW()
                WHERE posting_id = %s
                  AND posting_status = 'active'
            """, (existing['posting_id'],))
            stats['duplicate'] += 1
            stats['updated_last_seen'] += 1
        else:
            # Extract location
            locations = desc.get("PositionLocation", [])
            location = locations[0] if locations else {}
            
            country = location.get("CountryName") if isinstance(location, dict) else None
            if country:
                countries[country] = countries.get(country, 0) + 1
            
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
                ) RETURNING posting_id
            """, (
                str(job_id),
                job_title,  # posting_name (required)
                job_title,  # job_title
                "",  # Empty description for now
                location.get("CityName") if isinstance(location, dict) else None,
                country,
                career_level,
                external_url,  # Workday URL
                json.dumps(desc),  # Store full API response in metadata
            ))
            
            # Get the new posting_id for description fetching
            new_posting_id = cur.fetchone()['posting_id']
            new_posting_ids.append(new_posting_id)
            
            stats['new'] += 1
        
        # Progress every 100 jobs
        if i % 100 == 0:
            conn.commit()  # Commit periodically
            print(f"  Progress: {i}/{len(jobs)} ({stats['new']} new, {stats['duplicate']} duplicates, {stats['skipped_finanzberater']} finanzberater skipped)")
            
    except Exception as e:
        conn.rollback()  # Rollback on error to continue
        stats['errors'] += 1
        if stats['errors'] <= 10:  # Show first 10 errors with details
            print(f"  ❌ Error with job {job_id}: {type(e).__name__}: {str(e)[:100]}")

conn.commit()  # Final commit
conn.close()

print()
print("=" * 70)
print("🔍 CHECKING FOR REMOVED JOBS...")
print("=" * 70)

# Find jobs that are still marked active but weren't in the API response
from psycopg2.extras import RealDictCursor
conn = get_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get all active Deutsche Bank jobs from database
cur.execute("""
    SELECT posting_id, external_job_id, job_title
    FROM postings
    WHERE source_id = 1 
      AND posting_status = 'active'
      AND external_url LIKE '%workday%'
""")

removed_count = 0
removed_jobs = []

for row in cur.fetchall():
    posting_id = row['posting_id']
    ext_job_id = row['external_job_id']
    title = row['job_title']
    
    if ext_job_id not in api_job_ids:
        # Job not in API anymore - mark as withdrawn
        cur.execute("""
            UPDATE postings
            SET posting_status = 'withdrawn',
                status_checked_at = NOW()
            WHERE posting_id = %s
        """, (posting_id,))
        removed_count += 1
        removed_jobs.append((ext_job_id, title[:50]))
        
        if removed_count <= 10:  # Show first 10
            print(f"  ❌ Withdrawn: {ext_job_id} - {title[:50]}...")

if removed_count > 10:
    print(f"  ... and {removed_count - 10} more")

conn.commit()
conn.close()

print()
print("=" * 70)
print("✅ IMPORT COMPLETE!")
print("=" * 70)
print(f"Total jobs processed: {len(jobs)}")
print(f"New jobs added: {stats['new']}")
print(f"Existing jobs seen: {stats['duplicate']}")
print(f"Last_seen_at updated: {stats['updated_last_seen']}")
print(f"Finanzberater skipped: {stats['skipped_finanzberater']}")
print(f"Jobs withdrawn (removed from source): {removed_count}")
print(f"Errors: {stats['errors']}")
print()
print("📍 Countries represented:")
for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
    print(f"   {country}: {count} jobs")
print("=" * 70)

# Fetch descriptions for new jobs
if new_posting_ids:
    print()
    print("=" * 70)
    print("� FETCHING DESCRIPTIONS FOR NEW JOBS")
    print("=" * 70)
    desc_stats = fetch_descriptions_for_jobs(new_posting_ids)
    print()
    print(f"✅ Descriptions fetched: {desc_stats['success']}/{len(new_posting_ids)}")
    if desc_stats['failed'] > 0:
        print(f"⚠️  Failed to fetch: {desc_stats['failed']}")
    print("=" * 70)

print()
