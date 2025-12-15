#!/usr/bin/env python3
"""
Update Country Data for Existing Jobs
======================================

Re-fetch Deutsche Bank jobs and update location_country field
which was missing due to API response not including PositionLocation.

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
print("🌍 UPDATING COUNTRY DATA FOR DEUTSCHE BANK JOBS")
print("=" * 70)
print()

# Fetch from API with PositionLocation
print("📥 Fetching jobs with location data...")
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 5000,
        "MatchedObjectDescriptor": [
            "PositionID", "PositionLocation"
        ]
    }
}

payload_json = json.dumps(payload, separators=(',', ':'))
url = f"{API_URL}?data={payload_json}"

response = requests.get(url, timeout=60)
data = response.json()
jobs = data.get("SearchResult", {}).get("SearchResultItems", [])

print(f"✅ Fetched {len(jobs)} jobs from API\n")

# Update database
conn = get_connection()
cur = conn.cursor()

stats = {'updated': 0, 'not_found': 0, 'no_location': 0}
countries = {}

for i, job in enumerate(jobs, 1):
    desc = job.get("MatchedObjectDescriptor", {})
    job_id = str(desc.get("PositionID"))
    
    if not job_id:
        continue
    
    # Extract location
    locations = desc.get("PositionLocation", [])
    if locations and len(locations) > 0:
        location = locations[0]
        city = location.get("CityName")
        country = location.get("CountryName")
        
        # Check if job exists in our database
        cur.execute("""
            SELECT posting_id FROM postings
            WHERE source_id = 1 AND external_job_id = %s
        """, (job_id,))
        
        row = cur.fetchone()
        if row:
            # Update location
            cur.execute("""
                UPDATE postings
                SET location_city = %s,
                    location_country = %s
                WHERE posting_id = %s
            """, (city, country, row[0]))
            
            stats['updated'] += 1
            if country:
                countries[country] = countries.get(country, 0) + 1
        else:
            stats['not_found'] += 1
    else:
        stats['no_location'] += 1
    
    # Progress every 200 jobs
    if i % 200 == 0:
        conn.commit()
        print(f"  Progress: {i}/{len(jobs)} ({stats['updated']} updated)")

conn.commit()
conn.close()

print()
print("=" * 70)
print("✅ UPDATE COMPLETE!")
print("=" * 70)
print(f"Jobs updated: {stats['updated']}")
print(f"Jobs not found in DB: {stats['not_found']}")
print(f"Jobs with no location: {stats['no_location']}")
print()
print("📍 Countries:")
for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
    print(f"   {country}: {count} jobs")
print("=" * 70)
print()
