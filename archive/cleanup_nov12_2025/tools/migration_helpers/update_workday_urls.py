#!/usr/bin/env python3
"""
Update Workday URLs for Jobs Without Descriptions
==================================================

Re-fetch jobs from API to get ApplyURI (Workday URLs), then
fetch descriptions from those Workday pages.

Author: Arden & xai
Date: November 6, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import requests
from bs4 import BeautifulSoup
from core.database import get_connection

API_URL = "https://api-deutschebank.beesite.de/search/"

print()
print("=" * 70)
print("🔄 UPDATING WORKDAY URLs AND FETCHING DESCRIPTIONS")
print("=" * 70)
print()

# Step 1: Fetch from API WITH ApplyURI
print("📥 Step 1: Fetching jobs with ApplyURI from API...")
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 1000,
        "MatchedObjectDescriptor": [
            "PositionID", "PositionTitle", "ApplyURI"
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

# Build lookup dict: external_job_id -> workday_url
job_urls = {}
for job in jobs:
    desc = job.get("MatchedObjectDescriptor", {})
    job_id = str(desc.get("PositionID", ""))
    apply_uris = desc.get("ApplyURI", [])
    
    if job_id and apply_uris:
        job_urls[job_id] = apply_uris[0]  # Take first URL

print(f"📋 Found Workday URLs for {len(job_urls)} jobs")
print()

# Step 2: Get jobs from DB that need descriptions
print("💾 Step 2: Finding jobs that need descriptions...")
conn = get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT posting_id, external_job_id, job_title
    FROM postings
    WHERE posting_status = 'active'
      AND (job_description IS NULL OR job_description = '')
      AND (external_url IS NULL OR external_url = '')
    ORDER BY posting_id
""")

jobs_to_update = cur.fetchall()
print(f"📋 Found {len(jobs_to_update)} jobs needing updates")
print()

# Step 3: Update URLs and fetch descriptions
print("🔄 Step 3: Updating URLs and fetching descriptions...")
print()

stats = {
    'url_updated': 0,
    'desc_fetched': 0,
    'desc_failed': 0,
    'no_url': 0
}

for idx, (posting_id, external_job_id, job_title) in enumerate(jobs_to_update, 1):
    print(f"[{idx}/{len(jobs_to_update)}] Processing {external_job_id}: {job_title[:50]}")
    
    # Get Workday URL
    workday_url = job_urls.get(external_job_id)
    
    if not workday_url:
        stats['no_url'] += 1
        print(f"    ⚠️  No Workday URL found")
        continue
    
    # Update URL in database
    cur.execute("""
        UPDATE postings
        SET external_url = %s
        WHERE posting_id = %s
    """, (workday_url, posting_id))
    stats['url_updated'] += 1
    
    # Fetch description from Workday
    try:
        response = requests.get(workday_url, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try og:description meta tag
            meta_desc = soup.find('meta', property='og:description')
            description = None
            
            if meta_desc:
                description = meta_desc.get('content', '').strip()
            
            if description and len(description) > 100:
                # Update description
                cur.execute("""
                    UPDATE postings
                    SET job_description = %s,
                        last_seen_at = NOW()
                    WHERE posting_id = %s
                """, (description, posting_id))
                
                stats['desc_fetched'] += 1
                print(f"    ✅ Fetched description ({len(description)} chars)")
            else:
                stats['desc_failed'] += 1
                print(f"    ⚠️  No description in page")
        else:
            stats['desc_failed'] += 1
            print(f"    ❌ HTTP {response.status_code}")
            
    except Exception as e:
        stats['desc_failed'] += 1
        print(f"    ❌ Error: {e}")
    
    # Commit every 10 jobs
    if idx % 10 == 0:
        conn.commit()
        print(f"\n    💾 Progress saved: {stats['desc_fetched']} descriptions fetched\n")
    
    # Rate limiting
    time.sleep(0.5)  # 2 requests per second

# Final commit
conn.commit()
conn.close()

print()
print("=" * 70)
print("✅ UPDATE COMPLETE!")
print("=" * 70)
print(f"URLs updated: {stats['url_updated']}")
print(f"Descriptions fetched: {stats['desc_fetched']}")
print(f"Failed: {stats['desc_failed']}")
print(f"No URL found: {stats['no_url']}")
print("=" * 70)
print()

if stats['desc_fetched'] > 0:
    print(f"💡 Next: Run skill extraction on {stats['desc_fetched']} jobs")
    print()
