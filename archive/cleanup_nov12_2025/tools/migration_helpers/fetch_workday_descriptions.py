#!/usr/bin/env python3
"""
Fetch Job Descriptions from Workday URLs
=========================================

According to the cheat sheet, descriptions come from Workday, not careers.db.com.
This script fetches descriptions from the external_url field (Workday pages).

Extract from: <meta property="og:description" content="...">

Author: Arden & xai
Date: November 6, 2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

def fetch_description_from_workday(url: str) -> str:
    """
    Fetch job description from job page URL.
    Extract from og:description meta tag.
    
    Note: If URL ends with /apply, remove it to get the job page.
    """
    try:
        # Remove /apply suffix to get the actual job page
        job_url = url.replace('/apply', '') if url.endswith('/apply') else url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(job_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"    ⚠️  HTTP {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: og:description meta tag (most reliable for Workday)
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        # Method 2: Regular description meta tag
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        return None
        
    except Exception as e:
        print(f"    ⚠️  Error: {e}")
        return None


def fetch_descriptions_for_jobs(posting_ids: list) -> dict:
    """
    Fetch descriptions for specific posting IDs.
    Returns dict with stats: {'success': N, 'failed': N}
    """
    if not posting_ids:
        return {'success': 0, 'failed': 0}
    
    print(f"\n📥 Fetching descriptions for {len(posting_ids)} new jobs...")
    
    try:
        conn = psycopg2.connect(
            dbname='turing',
            user='base_admin',
            password='base_yoga_secure_2025',
            host='localhost',
            cursor_factory=RealDictCursor
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return {'success': 0, 'failed': 0}
    
    # Get job details for these posting IDs
    cur.execute("""
        SELECT posting_id, external_job_id, job_title, external_url
        FROM postings
        WHERE posting_id = ANY(%s)
          AND external_url LIKE '%%workday%%'
        ORDER BY posting_id
    """, (posting_ids,))
    
    jobs = cur.fetchall()
    stats = {'success': 0, 'failed': 0}
    
    for idx, job in enumerate(jobs, 1):
        posting_id = job['posting_id']
        job_id = job['external_job_id']
        title = job['job_title']
        url = job['external_url']
        
        print(f"  [{idx}/{len(jobs)}] {job_id}: {title[:50]}...")
        
        description = fetch_description_from_workday(url)
        
        if description and len(description) > 200:
            cur.execute("""
                UPDATE postings
                SET job_description = %s,
                    last_seen_at = NOW()
                WHERE posting_id = %s
            """, (description, posting_id))
            stats['success'] += 1
            print(f"    ✅ Saved {len(description)} chars")
        else:
            stats['failed'] += 1
            if description:
                print(f"    ⚠️  Too short ({len(description)} chars)")
            else:
                print(f"    ❌ No description found")
        
        # Rate limiting
        time.sleep(0.2)
    
    conn.commit()
    conn.close()
    
    return stats


def main():
    print()
    print("=" * 70)
    print("📝 FETCHING JOB DESCRIPTIONS FROM WORKDAY")
    print("=" * 70)
    print()
    
    print("🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(
            dbname='turing',
            user='base_admin',
            password='base_yoga_secure_2025',
            host='localhost',
            cursor_factory=RealDictCursor
        )
        cur = conn.cursor()
        print("✅ Connected to database 'turing'\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Get jobs that have external_url but no description
    print("📋 Querying for Workday jobs without valid descriptions...")
    print("   Filters:")
    print("   - posting_status = 'active' (skip expired)")
    print("   - external_url LIKE '%workday%' (Workday jobs only)")
    print("   - job_description IS NULL OR LENGTH < 200 (invalid descriptions)")
    print()
    
    try:
        cur.execute("""
            SELECT posting_id, external_job_id, job_title, external_url
            FROM postings
            WHERE posting_status = 'active'
              AND external_url LIKE '%workday%'
              AND (job_description IS NULL 
                   OR job_description = '' 
                   OR LENGTH(job_description) < 200)
            ORDER BY posting_id
        """)
        
        jobs = cur.fetchall()
        print(f"✅ Query complete: Found {len(jobs)} jobs to process\n")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return
    
    if not jobs:
        print("✅ All jobs with Workday URLs already have descriptions!")
        return
    
    print(f"📥 Found {len(jobs)} jobs to process")
    print(f"⏱️  Estimated time: ~{len(jobs) * 0.2 / 60:.1f} minutes (at 5 req/sec)")
    print(f"🌐 Rate limit: 0.2s delay between requests\n")
    print("Starting fetch process...\n")
    
    stats = {'success': 0, 'failed': 0, 'total': len(jobs)}
    
    for idx, job in enumerate(jobs, 1):
        posting_id = job['posting_id']
        job_id = job['external_job_id']
        title = job['job_title']
        url = job['external_url']
        
        print(f"[{idx}/{len(jobs)}] {job_id}: {title[:50]}...")
        print(f"    🔗 URL: {url}")
        
        description = fetch_description_from_workday(url)
        
        # Validate description length (must be > 200 chars to be valid)
        if description and len(description) > 200:
            # Update database
            cur.execute("""
                UPDATE postings
                SET job_description = %s,
                    last_seen_at = NOW()
                WHERE posting_id = %s
            """, (description, posting_id))
            
            stats['success'] += 1
            print(f"    ✅ Saved {len(description)} chars")
            
            # Commit every 10 successful fetches
            if stats['success'] % 10 == 0:
                conn.commit()
                print(f"    💾 Committed {stats['success']} descriptions\n")
        elif description and len(description) <= 200:
            stats['failed'] += 1
            print(f"    ⚠️  Too short ({len(description)} chars) - likely login page")
        else:
            stats['failed'] += 1
            print(f"    ❌ No description found")
        
        # Progress every 50 jobs
        if idx % 50 == 0:
            success_rate = (stats['success'] / idx) * 100
            print(f"\n📊 Progress: {idx}/{len(jobs)} ({success_rate:.1f}% success)\n")
        
        # Rate limiting - 5 requests per second max
        time.sleep(0.2)
    
    # Final commit
    conn.commit()
    conn.close()
    
    # Final statistics
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    print(f"Total jobs: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    
    if stats['success'] > 0:
        success_rate = (stats['success'] / stats['total']) * 100
        print(f"\n🎯 Success rate: {success_rate:.1f}%")
    
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
