#!/usr/bin/env python3
"""
Job Status Validator
====================

Checks if jobs are still active on their source sites and updates posting_status.

For Deutsche Bank:
- Workday jobs: Check if URL returns 200 and has content
- DB Finanzberatung: Check if job ID still in their system
- API: Query API with specific job ID to see if still listed

This is CRITICAL for data quality - we don't want to show expired jobs!

Author: Arden & xai
Date: November 7, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

API_URL = "https://api-deutschebank.beesite.de/search/"

def check_workday_job_exists(url: str) -> tuple[bool, str]:
    """
    Check if a Workday job still exists.
    Returns: (exists: bool, reason: str)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
        
        # Workday returns 410 Gone for expired jobs
        if response.status_code == 410:
            return False, "HTTP 410 Gone"
        
        # Redirect to search page = job doesn't exist
        if response.status_code in [301, 302, 303, 307, 308]:
            return False, f"Redirected (HTTP {response.status_code})"
        
        # 404 = Not found
        if response.status_code == 404:
            return False, "HTTP 404 Not Found"
        
        # Any other non-200 status
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        # Check page content for "no job openings" messages
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for "no job openings" or similar messages
        page_text = soup.get_text().lower()
        if "no job openings" in page_text or "there are no job openings" in page_text:
            return False, "Job not found (page says 'no job openings')"
        
        # Check if og:title exists with actual content (real job pages have this)
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if not og_title:
            return False, "No og:title meta tag (likely error page)"
        
        title_content = og_title.get('content', '').strip()
        if not title_content or title_content == 'None':
            return False, "Empty og:title (job expired/removed)"
        
        # Job exists!
        return True, "Active"
        
    except requests.Timeout:
        return None, "Timeout"
    except requests.RequestException as e:
        return None, f"Network error: {e}"
    except Exception as e:
        return None, f"Error: {e}"


def check_api_job_exists(external_job_id: str) -> tuple[bool, str]:
    """
    Check if a job still exists in Deutsche Bank API.
    Query API with specific PositionID.
    Returns: (exists: bool, reason: str)
    """
    try:
        payload = {
            "LanguageCode": "en",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 10,
                "MatchedObjectDescriptor": ["PositionID", "PositionTitle"]
            },
            "SearchCriteria": [
                {"CriterionName": "PositionID", "CriterionValue": [str(external_job_id)]}
            ]
        }
        
        payload_json = json.dumps(payload, separators=(',', ':'))
        url = f"{API_URL}?data={payload_json}"
        
        response = requests.get(url, timeout=30)
        data = response.json()
        
        jobs = data.get("SearchResult", {}).get("SearchResultItems", [])
        
        if jobs and len(jobs) > 0:
            return True, "Found in API"
        else:
            return False, "Not found in API"
            
    except Exception as e:
        return None, f"API error: {e}"


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate job posting status')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without changing database')
    parser.add_argument('--posting-id', type=int, help='Check specific posting ID only')
    parser.add_argument('--verbose', action='store_true', help='Show all checks, not just changes')
    args = parser.parse_args()
    
    print()
    print("=" * 70)
    print("🔍 JOB STATUS VALIDATOR")
    if args.dry_run:
        print("   [DRY RUN MODE - No database changes]")
    print("=" * 70)
    print()
    
    print("🔌 Connecting to database...")
    conn = psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', ''),
        host='localhost',
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()
    print("✅ Connected\n")
    
    # Build query based on arguments
    query = """
        SELECT posting_id, external_job_id, job_title, external_url,
               last_seen_at, first_seen_at, posting_status
        FROM postings
        WHERE source_id = 1
          AND posting_status IN ('active', 'filled')
    """
    
    params = []
    if args.posting_id:
        query += " AND posting_id = %s"
        params.append(args.posting_id)
        print(f"📋 Checking specific posting ID: {args.posting_id}...")
    else:
        print("📋 Querying active/filled Deutsche Bank jobs...")
    
    query += " ORDER BY last_seen_at DESC NULLS LAST"
    
    cur.execute(query, params)
    jobs = cur.fetchall()
    
    if not jobs:
        print("❌ No jobs found matching criteria")
        return
    
    print(f"✅ Found {len(jobs)} jobs to validate\n")
    
    stats = {
        'active': 0,
        'expired': 0,
        'error': 0,
        'api_check': 0,
        'workday_check': 0
    }
    
    print("Starting validation...\n")
    
    for idx, job in enumerate(jobs, 1):
        posting_id = job['posting_id']
        job_id = job['external_job_id']
        title = job['job_title'] or 'Untitled'
        url = job['external_url']
        current_status = job['posting_status']
        
        # Try to extract job_id from posting_position_uri if missing
        if not job_id and not url:
            # Extract from source_metadata if possible
            cur.execute("""
                SELECT 
                    source_metadata->>'posting_position_uri' as uri,
                    source_metadata->>'external_job_id' as meta_job_id
                FROM postings 
                WHERE posting_id = %s
            """, (posting_id,))
            meta = cur.fetchone()
            
            if meta and meta['uri']:
                # Extract ID from URI like "/index.php?ac=jobad&id=56411"
                import re
                match = re.search(r'id=(\d+)', meta['uri'])
                if match:
                    job_id = match.group(1)
            
            if meta and meta['meta_job_id']:
                job_id = meta['meta_job_id']
        
        if idx % 50 == 0:
            print(f"\n[{idx}/{len(jobs)}] Progress checkpoint")
            print(f"   Active: {stats['active']} | Expired: {stats['expired']} | Errors: {stats['error']}\n")
        
        # Skip if still no way to validate
        if not url and not job_id:
            stats['error'] += 1
            if args.verbose:
                print(f"[{idx}/{len(jobs)}] ⚠️  SKIP: {title[:50]} - No URL or Job ID to validate")
            continue
        
        # Check based on what we have
        if url and 'workday' in url.lower():
            stats['workday_check'] += 1
            exists, reason = check_workday_job_exists(url)
        elif job_id:
            # For non-Workday jobs or jobs without URL, check via API
            stats['api_check'] += 1
            exists, reason = check_api_job_exists(job_id)
        else:
            # No URL and no job_id - can't validate
            stats['error'] += 1
            if args.verbose:
                print(f"[{idx}/{len(jobs)}] ⚠️  SKIP: {title[:50]} - Cannot validate")
            continue
        
        if exists is True:
            # Job still active - update last_seen_at
            stats['active'] += 1
            if not args.dry_run:
                cur.execute("""
                    UPDATE postings 
                    SET last_seen_at = NOW()
                    WHERE posting_id = %s
                """, (posting_id,))
            
            if args.verbose or idx <= 10 or idx % 100 == 0:
                print(f"[{idx}/{len(jobs)}] ✅ ACTIVE: {job_id or 'no-id'} - {title[:50]}")
        
        elif exists is False:
            # Job expired/removed
            stats['expired'] += 1
            if not args.dry_run:
                cur.execute("""
                    UPDATE postings 
                    SET posting_status = 'expired'
                    WHERE posting_id = %s
                """, (posting_id,))
            
            print(f"[{idx}/{len(jobs)}] ❌ EXPIRED: {job_id or 'no-id'} - {title[:50]}")
            print(f"   Reason: {reason}")
            if args.dry_run:
                print(f"   [DRY RUN] Would mark as expired")
        
        else:
            # Error checking (network issue, etc.) - these stay as-is
            stats['error'] += 1
            if args.verbose or idx <= 10:
                print(f"[{idx}/{len(jobs)}] ⚠️  ERROR: {job_id or 'no-id'} - {reason}")
        
        # Commit every 25 jobs
        if not args.dry_run and idx % 25 == 0:
            conn.commit()
        
        # Rate limiting
        time.sleep(0.5)  # 2 req/sec to be nice to their servers
    
    # Final commit
    if not args.dry_run:
        conn.commit()
    conn.close()
    
    # Final report
    print("\n" + "=" * 70)
    print("📊 VALIDATION COMPLETE")
    print("=" * 70)
    print(f"Total jobs checked: {len(jobs)}")
    print(f"✅ Still active: {stats['active']}")
    print(f"❌ Expired/Removed: {stats['expired']}")
    print(f"⚠️  Errors/Skipped: {stats['error']}")
    print(f"\nValidation methods:")
    print(f"   🌐 Workday URL checks: {stats['workday_check']}")
    print(f"   🔍 API checks: {stats['api_check']}")
    
    if stats['expired'] > 0:
        expiration_rate = (stats['expired'] / len(jobs)) * 100
        print(f"\n📉 Expiration rate: {expiration_rate:.1f}%")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes were made to database")
    
    print("\n💡 Next steps:")
    print("   1. Review expired jobs: SELECT * FROM postings WHERE posting_status = 'expired';")
    print("   2. Run this validator regularly (daily?) to keep data fresh")
    print("   3. For jobs without URLs, consider querying API by job title pattern")
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
