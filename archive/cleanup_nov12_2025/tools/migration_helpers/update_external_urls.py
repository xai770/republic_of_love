#!/usr/bin/env python3
"""
Update External URLs for Existing Jobs
=======================================

Fetch ApplyURI from API and update external_url field for existing jobs.

Author: Arden & xai
Date: November 6, 2025
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
print("🔗 UPDATING EXTERNAL URLS FOR EXISTING JOBS")
print("=" * 70)
print()

# Fetch from API
print("📥 Fetching jobs from API...")
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 1000,
        "MatchedObjectDescriptor": ["PositionID", "ApplyURI"]
    },
    "SearchCriteria": [
        {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
    ]
}

url = f"{API_URL}?data={json.dumps(payload)}"
response = requests.get(url, timeout=60)
data = response.json()

jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
print(f"✅ Fetched {len(jobs)} jobs from API\n")

# Update database
conn = get_connection()
cur = conn.cursor()

stats = {'updated': 0, 'no_url': 0, 'not_found': 0}

print("💾 Updating database...")
for idx, job in enumerate(jobs, 1):
    desc = job.get("MatchedObjectDescriptor", {})
    job_id = desc.get("PositionID")
    apply_uris = desc.get("ApplyURI", [])
    
    if not job_id:
        continue
    
    # Check if job exists
    cur.execute("""
        SELECT posting_id FROM postings
        WHERE source_id = 1 AND external_job_id = %s
    """, (str(job_id),))
    
    result = cur.fetchone()
    if not result:
        stats['not_found'] += 1
        continue
    
    posting_id = result['posting_id'] if isinstance(result, dict) else result[0]
    
    if apply_uris:
        external_url = apply_uris[0]
        
        cur.execute("""
            UPDATE postings
            SET external_url = %s,
                last_seen_at = NOW()
            WHERE posting_id = %s
        """, (external_url, posting_id))
        
        stats['updated'] += 1
    else:
        stats['no_url'] += 1
    
    # Progress and commit every 100
    if idx % 100 == 0:
        conn.commit()
        print(f"  Progress: {idx}/{len(jobs)} ({stats['updated']} updated)")

conn.commit()
conn.close()

# Results
print("\n" + "="*70)
print("✅ UPDATE COMPLETE!")
print("="*70)
print(f"Jobs updated: {stats['updated']}")
print(f"Jobs without URL: {stats['no_url']}")
print(f"Jobs not found in DB: {stats['not_found']}")
print("\n✨ Done!")
