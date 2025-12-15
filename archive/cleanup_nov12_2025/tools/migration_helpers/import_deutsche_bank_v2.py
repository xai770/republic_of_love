#!/usr/bin/env python3
"""
Deutsche Bank Job Importer (v2)
================================

Imports ALL German jobs from Deutsche Bank API with:
- Full API response stored in source_metadata (JSONB)
- Idempotent imports using ON CONFLICT
- Proper duplicate prevention via (source_id, external_job_id) constraint

Author: Arden & xai
Date: 2025-11-07
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from datetime import datetime
from core.database import get_connection

API_URL = "https://api-deutschebank.beesite.de/search/"
SOURCE_ID = 1  # Deutsche Bank

print()
print("=" * 70)
print("🚀 DEUTSCHE BANK JOB IMPORTER v2")
print("=" * 70)
print()

# Step 1: Fetch from API with ALL available fields
print("📥 Step 1: Fetching from Deutsche Bank API...")
print()

payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 1000,  # Get as many as possible
        "MatchedObjectDescriptor": [
            # Request ALL fields to ensure we get full results
            "PositionID", "PositionTitle", "PositionURI",
            "PositionLocation", "PublicationStartDate", "PublicationEndDate",
            "CareerLevel", "OrganizationName", "ApplyURI",
            "PublicationChannel", "PositionFormattedDescription"
        ],
        "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}]
    },
    "SearchCriteria": [
        {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}  # Germany
    ]
}

payload_json = json.dumps(payload, separators=(',', ':'))
url = f"{API_URL}?data={payload_json}"

print(f"   API URL: {API_URL}")
print(f"   Filter: German jobs only (Country=46)")
print()

response = requests.get(url, timeout=60)
data = response.json()
jobs = data.get("SearchResult", {}).get("SearchResultItems", [])

print(f"✅ Fetched {len(jobs)} jobs from API")
print()

# Step 2: Import to database with full metadata
print("💾 Step 2: Importing to database...")
print()

conn = get_connection()
cur = conn.cursor()

stats = {
    'new': 0,
    'updated': 0,
    'errors': 0,
    'skipped_no_id': 0
}

for i, job in enumerate(jobs, 1):
    try:
        # Get the MatchedObjectDescriptor (full job data from API)
        desc = job.get("MatchedObjectDescriptor", {})
        
        # External job ID (CRITICAL for uniqueness)
        external_job_id = desc.get("PositionID")
        
        if not external_job_id:
            print(f"[{i}/{len(jobs)}] ⚠️  Skipping job with no PositionID")
            stats['skipped_no_id'] += 1
            continue
        
        # Extract fields for columns
        job_title = desc.get("PositionTitle", "Untitled Position")
        
        # Location (array of objects)
        location_city = None
        location_country = None
        locations = desc.get("PositionLocation", [])
        if locations and isinstance(locations, list) and locations:
            loc = locations[0]
            if isinstance(loc, dict):
                location_city = loc.get("CityName")
                location_country = loc.get("CountryName")
        
        # Career Level (array of objects)
        employment_career_level = None
        career_levels = desc.get("CareerLevel", [])
        if career_levels and isinstance(career_levels, list) and career_levels:
            level = career_levels[0]
            if isinstance(level, dict):
                employment_career_level = level.get("Name")
        
        # Organization/Department
        organization = desc.get("OrganizationName")
        
        # Dates
        publication_start = desc.get("PublicationStartDate")
        publication_end = desc.get("PublicationEndDate")
        
        # URLs
        apply_uris = desc.get("ApplyURI", [])
        apply_uri = apply_uris[0] if apply_uris else None
        
        # CRITICAL: Remove /apply suffix to get job page URL
        external_url = None
        if apply_uri:
            external_url = apply_uri.replace('/apply', '') if apply_uri.endswith('/apply') else apply_uri
        
        position_uri = desc.get("PositionURI")
        
        # Store FULL API response in source_metadata
        source_metadata = {
            "raw_api_response": desc,  # Complete MatchedObjectDescriptor
            "api_fetch_timestamp": datetime.now().isoformat(),
            "api_url": API_URL,
            "search_criteria": payload["SearchCriteria"],
            "matched_object_id": job.get("MatchedObjectId")  # Top-level ID
        }
        
        # Insert or update using ON CONFLICT
        cur.execute("""
            INSERT INTO postings (
                source_id,
                external_job_id,
                posting_name,
                job_title,
                location_city,
                location_country,
                employment_career_level,
                external_url,
                posting_position_uri,
                posting_status,
                source_metadata,
                fetched_at,
                first_seen_at,
                last_seen_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW()
            )
            ON CONFLICT (source_id, external_job_id)
            DO UPDATE SET
                posting_name = EXCLUDED.posting_name,
                job_title = EXCLUDED.job_title,
                location_city = EXCLUDED.location_city,
                location_country = EXCLUDED.location_country,
                employment_career_level = EXCLUDED.employment_career_level,
                external_url = EXCLUDED.external_url,
                posting_position_uri = EXCLUDED.posting_position_uri,
                source_metadata = EXCLUDED.source_metadata,
                last_seen_at = NOW()
            RETURNING posting_id, (xmax = 0) AS inserted
        """, (
            SOURCE_ID,
            str(external_job_id),
            job_title,  # Use job_title for posting_name (required field)
            job_title,
            location_city,
            location_country,
            employment_career_level,
            external_url,
            position_uri,
            'active',
            json.dumps(source_metadata)
        ))
        
        result = cur.fetchone()
        posting_id = result[0]
        was_inserted = result[1]
        
        if was_inserted:
            stats['new'] += 1
            status = "NEW"
        else:
            stats['updated'] += 1
            status = "UPDATED"
        
        # Progress logging
        if i % 50 == 0 or i == len(jobs):
            print(f"[{i}/{len(jobs)}] {status}: {external_job_id} - {job_title[:50]}...")
        
        # Commit every 25 jobs
        if i % 25 == 0:
            conn.commit()
    
    except Exception as e:
        stats['errors'] += 1
        print(f"[{i}/{len(jobs)}] ❌ Error: {e}")
        continue

# Final commit
conn.commit()
conn.close()

# Final statistics
print()
print("=" * 70)
print("📊 IMPORT COMPLETE")
print("=" * 70)
print(f"Total jobs processed: {len(jobs)}")
print(f"✅ New jobs imported: {stats['new']}")
print(f"🔄 Existing jobs updated: {stats['updated']}")
print(f"⚠️  Skipped (no ID): {stats['skipped_no_id']}")
print(f"❌ Errors: {stats['errors']}")

if stats['new'] + stats['updated'] > 0:
    success_rate = ((stats['new'] + stats['updated']) / len(jobs)) * 100
    print(f"\n🎯 Success rate: {success_rate:.1f}%")

print()
print("💡 Next steps:")
print("   1. Run: python3 tools/fetch_workday_descriptions.py")
print("   2. Check: SELECT COUNT(*) FROM postings WHERE source_metadata IS NOT NULL;")
print()
print("✨ Done!")
