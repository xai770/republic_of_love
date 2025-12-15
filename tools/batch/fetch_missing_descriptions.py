#!/usr/bin/env python3
"""
Fetch Missing Job Descriptions
================================

Fetches descriptions from careers.db.com for jobs that don't have them.
URL format: https://careers.db.com/professionals/search-roles/#/professional/job/{job_id}

Author: Arden & xai
Date: November 6, 2025
Updated: December 10, 2025 - Uses core.text_utils for encoding (single source of truth)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests
from bs4 import BeautifulSoup
from core.database import get_connection
from core.text_utils import sanitize_for_storage
import time


def fetch_description_from_url(job_id: str) -> str:
    """
    Fetch job description from careers.db.com
    
    The page is a single-page app (React), so we need to check if the
    content is in the HTML or if we need to use a different approach.
    """
    url = f"https://careers.db.com/professionals/search-roles/#/professional/job/{job_id}"
    
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'utf-8'  # Ensure proper decoding
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Look for og:description meta tag
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content', '').strip()
            if len(description) > 50:  # Meaningful description
                return sanitize_for_storage(description)
        
        # Method 2: Look for description meta tag
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content', '').strip()
            if len(description) > 50:
                return description
        
        # Method 3: Look for job description div/section
        # Common class names in career sites
        for class_name in ['job-description', 'description', 'content', 'job-detail', 'posting-description']:
            desc_div = soup.find(['div', 'section'], class_=class_name)
            if desc_div:
                description = desc_div.get_text(strip=True)
                if len(description) > 100:
                    return description
        
        return None
        
    except Exception as e:
        return None


def main():
    """Main entry point"""
    print()
    print("=" * 70)
    print("📄 FETCHING MISSING JOB DESCRIPTIONS")
    print("=" * 70)
    print()
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get jobs without descriptions
    cur.execute("""
        SELECT posting_id, external_job_id, job_title, location_city
        FROM postings
        WHERE posting_status = 'active'
          AND (job_description IS NULL OR job_description = '')
          AND external_job_id IS NOT NULL
        ORDER BY posting_id
    """)
    
    jobs = cur.fetchall()
    
    print(f"Found {len(jobs)} jobs without descriptions")
    print()
    
    if not jobs:
        print("✅ All jobs have descriptions!")
        return 0
    
    stats = {
        'success': 0,
        'failed': 0,
        'total': len(jobs)
    }
    
    for i, job in enumerate(jobs, 1):
        posting_id = job[0]
        job_id = job[1]
        title = job[2]
        city = job[3]
        
        # Progress every 50 jobs
        if i % 50 == 1 or i == len(jobs):
            print(f"[{i}/{len(jobs)}] Processing: {title[:50]}... ({city})")
        
        # Fetch description
        description = fetch_description_from_url(job_id)
        
        if description:
            # Update database
            cur.execute("""
                UPDATE postings
                SET job_description = %s
                WHERE posting_id = %s
            """, (description, posting_id))
            stats['success'] += 1
            
            # Commit every 10 successful fetches
            if stats['success'] % 10 == 0:
                conn.commit()
                print(f"  ✅ {stats['success']} descriptions fetched so far...")
        else:
            stats['failed'] += 1
        
        # Rate limiting - be nice to the server
        time.sleep(0.2)  # 200ms between requests = 5 req/sec
    
    # Final commit
    conn.commit()
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ DESCRIPTION FETCH COMPLETE!")
    print("=" * 70)
    print(f"Total jobs: {stats['total']}")
    print(f"Successful: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {100*stats['success']/stats['total']:.1f}%")
    print("=" * 70)
    print()
    
    if stats['success'] > 0:
        print("💡 Next: Extract skills from jobs with descriptions")
        print()
        print("   python3 -c 'from core.turing_orchestrator import TuringOrchestrator;")
        print("              TuringOrchestrator().process_pending_tasks(max_tasks=None)'")
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
