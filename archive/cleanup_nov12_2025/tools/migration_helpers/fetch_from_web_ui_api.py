#!/usr/bin/env python3
"""
Fetch Jobs Using the Web UI API Endpoint
=========================================

Uses the SAME API that the careers.db.com website uses.
This is a GET endpoint with JSON in the URL parameter.

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
from urllib.parse import urlencode, quote

# Web UI API Configuration
API_BASE_URL = "https://api-deutschebank.beesite.de/search/"

def build_search_payload(
    country_code: str = "46",  # 46 = Germany
    first_item: int = 1,
    count_item: int = 1000,  # Request many at once
    language: str = "en"
) -> Dict[str, Any]:
    """
    Build the search payload matching the web UI format
    
    Args:
        country_code: Country code (46 = Germany, seen in URL ?country=46)
        first_item: Starting position (1-indexed)
        count_item: Number of items to fetch
        language: Language code
        
    Returns:
        Dict ready to be JSON-encoded
    """
    payload = {
        "LanguageCode": language,
        "SearchParameters": {
            "FirstItem": first_item,
            "CountItem": count_item,
            "MatchedObjectDescriptor": [
                "Facet:ProfessionCategory",
                "Facet:UserArea.ProDivision",
                "Facet:Profession",
                "Facet:PositionLocation.CountrySubDivision",
                "Facet:PositionOfferingType.Code",
                "Facet:PositionSchedule.Code",
                "Facet:PositionLocation.City",
                "Facet:PositionLocation.Country",
                "Facet:JobCategory.Code",
                "Facet:CareerLevel.Code",
                "Facet:PositionHiringYear",
                "Facet:PositionFormattedDescription.Content",
                "PositionID",
                "PositionTitle",
                "PositionURI",
                "ScoreThreshold",
                "OrganizationName",
                "PositionFormattedDescription.Content",
                "PositionLocation.CountryName",
                "PositionLocation.CountrySubDivisionName",
                "PositionLocation.CityName",
                "PositionLocation.Longitude",
                "PositionLocation.Latitude",
                "PositionIndustry.Name",
                "JobCategory.Name",
                "CareerLevel.Name",
                "PositionSchedule.Name",
                "PositionOfferingType.Name",
                "PublicationStartDate",
                "UserArea.GradEduInstCountry",
                "PositionImport",
                "PositionHiringYear",
                "PositionID"
            ],
            "Sort": [
                {
                    "Criterion": "PublicationStartDate",
                    "Direction": "DESC"
                }
            ]
        },
        "SearchCriteria": []
    }
    
    # Add country filter if specified
    if country_code:
        payload["SearchCriteria"].append({
            "CriterionName": "PositionLocation.Country",
            "CriterionValue": [country_code]
        })
    
    return payload


def fetch_jobs_web_ui_api(
    country_code: str = "46",
    max_jobs: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetch jobs using the web UI GET API
    
    The web UI doesn't paginate - it just increases CountItem!
    So we fetch ALL jobs in ONE request.
    
    Args:
        country_code: Country code (46 = Germany)
        max_jobs: Maximum jobs to fetch (used as CountItem)
        
    Returns:
        List of job dicts
    """
    print("=" * 70)
    print("🌐 FETCHING FROM WEB UI API (GET ENDPOINT)")
    print("=" * 70)
    print(f"Country Code: {country_code}")
    print(f"Requesting up to: {max_jobs} jobs in ONE request")
    print()
    
    # Build payload - the web UI just increases CountItem, no pagination needed!
    payload = build_search_payload(
        country_code=country_code,
        first_item=1,
        count_item=max_jobs  # Request ALL jobs at once
    )
    
    # Construct URL with JSON in query parameter
    payload_json = json.dumps(payload, separators=(',', ':'))
    url = f"{API_BASE_URL}?data={payload_json}"
    
    print(f"� Fetching ALL jobs...", end=" ")
    
    try:
        response = requests.get(url, timeout=60)  # Longer timeout for large response
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}")
            return []
        
        data = response.json()
        
        # Parse response
        search_result = data.get("SearchResult", {})
        jobs = search_result.get("SearchResultItems", [])
        total_count = search_result.get("SearchResultCount", 0)
        
        print(f"✅ Got {len(jobs)}/{total_count} jobs!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    
    print()
    print("=" * 70)
    print(f"✅ FETCHED {len(jobs)} JOBS TOTAL")
    print("=" * 70)
    print()
    
    return jobs


def transform_to_turing_format(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform web UI API format to match our existing TuringJobFetcher format
    
    Web UI uses different field names than the POST API we were using before.
    """
    transformed = []
    
    print("🔄 Transforming API format to Turing format...")
    
    for job in jobs:
        # Web UI API has MatchedObjectDescriptor at top level (not nested)
        desc = job.get("MatchedObjectDescriptor", {})
        
        # Map to our expected format
        turing_job = {
            "MatchedObjectId": desc.get("PositionID"),
            "PositionTitle": desc.get("PositionTitle"),
            "PositionURI": desc.get("PositionURI"),
            "OrganizationName": desc.get("OrganizationName", "Deutsche Bank"),
            "PublicationStartDate": desc.get("PublicationStartDate"),
            "PositionFormattedDescription": desc.get("PositionFormattedDescription", {}),
            
            # Location info
            "Locations": [{
                "CityName": desc.get("PositionLocation", [{}])[0].get("CityName") if desc.get("PositionLocation") else None,
                "CountryName": desc.get("PositionLocation", [{}])[0].get("CountryName") if desc.get("PositionLocation") else None,
                "CountryCode": desc.get("PositionLocation", [{}])[0].get("CountryCode") if desc.get("PositionLocation") else None,
                "Latitude": desc.get("PositionLocation", [{}])[0].get("Latitude") if desc.get("PositionLocation") else None,
                "Longitude": desc.get("PositionLocation", [{}])[0].get("Longitude") if desc.get("PositionLocation") else None,
            }],
            
            # Career level
            "CareerLevel": desc.get("CareerLevel", [{}])[0] if desc.get("CareerLevel") else {},
            
            # Job category
            "JobCategory": desc.get("JobCategory", [{}])[0] if desc.get("JobCategory") else {},
            
            # ApplyURI (construct from PositionURI)
            # PositionURI is often a relative path like /index.php?ac=jobad&id=67096
        }
        
        # Fix relative URLs
        position_uri = turing_job.get("PositionURI")
        if position_uri and position_uri.startswith('/'):
            position_uri = f"https://careers.db.com{position_uri}"
        
        turing_job["ApplyURI"] = position_uri
        
        transformed.append(turing_job)
    
    print(f"✅ Transformed {len(transformed)} jobs")
    return transformed


def save_to_database(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Save jobs to Turing database
    """
    from core.turing_job_fetcher import TuringJobFetcher
    
    print()
    print("💾 SAVING TO DATABASE")
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
    
    fetch_run_id = fetcher._start_fetch_run()
    
    try:
        seen_external_ids = []
        
        for i, job_data in enumerate(jobs, 1):
            try:
                external_id = job_data.get("MatchedObjectId")
                if not external_id:
                    continue
                
                seen_external_ids.append(external_id)
                
                # Check if exists
                cursor.execute("SELECT posting_exists(%s, %s)", (1, external_id))
                result = cursor.fetchone()
                existing_id = result['posting_exists'] if result else None
                
                if existing_id:
                    cursor.execute("SELECT update_posting_seen(%s, true)", (existing_id,))
                    stats['duplicate'] += 1
                    
                    if i % 50 == 0:
                        print(f"  [{i}/{len(jobs)}] {stats['new']} new, {stats['duplicate']} existing")
                else:
                    # Skip description fetching for speed - many URLs return 404
                    # We can extract skills from the job title and metadata instead
                    description = ""
                    
                    posting_id = fetcher._insert_posting(job_data, description, fetch_run_id)
                    stats['new'] += 1
                    
                    if stats['new'] % 50 == 0 or i % 100 == 0:
                        print(f"  [{i}/{len(jobs)}] ✅ {stats['new']} new, {stats['duplicate']} existing")
                    
            except Exception as e:
                stats['error'] += 1
                print(f"  ❌ Error processing job {external_id}: {e}")
        
        print(f"\n🔄 Marking missing jobs as filled...")
        fetcher._mark_missing_as_filled(seen_external_ids)
        
        fetcher._complete_fetch_run(fetch_run_id, stats)
        fetcher.conn.commit()
        
        print()
        print("=" * 70)
        print("✅ DATABASE SAVE COMPLETE")
        print("=" * 70)
        print(f"📊 New: {stats['new']}")
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
    print("🚀 DEUTSCHE BANK WEB UI API FETCHER")
    print("=" * 70)
    print()
    print("This uses the SAME API endpoint as careers.db.com")
    print("Should be able to fetch all 588 German jobs!")
    print()
    
    # Fetch jobs from web UI API
    jobs = fetch_jobs_web_ui_api(country_code="46", max_jobs=1000)
    
    if not jobs:
        print("❌ No jobs fetched. Exiting.")
        return 1
    
    print(f"\n✅ Fetched {len(jobs)} jobs from Web UI API")
    
    # Transform to Turing format
    turing_jobs = transform_to_turing_format(jobs)
    
    # Save to database
    stats = save_to_database(turing_jobs)
    
    print()
    print("🎉 ALL DONE!")
    print()
    print(f"📊 Summary:")
    print(f"   • Fetched from API: {len(jobs)}")
    print(f"   • New in database: {stats['new']}")
    print(f"   • Duplicates: {stats['duplicate']}")
    print(f"   • Errors: {stats['error']}")
    print()
    
    if stats['new'] > 0:
        print("💡 Next: Run TuringOrchestrator to extract skills")
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
