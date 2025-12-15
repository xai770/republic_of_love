#!/usr/bin/env python3
"""
Backfill job descriptions for postings that have URLs but no descriptions.

Usage: python3 scripts/backfill_descriptions.py --limit 100

This fetches the job description from the Workday page for each posting.

NOTE: Uses core.text_utils.sanitize_for_storage for encoding fixes.
      Do NOT duplicate encoding logic here - single source of truth.
"""

import sys
import os
import argparse
import requests
import time
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
from core.text_utils import sanitize_for_storage

load_dotenv()


class JobDescriptionParser(HTMLParser):
    """Extract job description from meta tag"""
    def __init__(self):
        super().__init__()
        self.description = None
        
    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            attrs_dict = dict(attrs)
            if attrs_dict.get('property') == 'og:description':
                self.description = attrs_dict.get('content', '')


def fetch_job_description(job_url: str) -> str:
    """Fetch full job description from Workday page."""
    try:
        response = requests.get(job_url, timeout=15)
        if response.status_code != 200:
            return None
        
        # Ensure proper UTF-8 decoding
        response.encoding = 'utf-8'
        
        parser = JobDescriptionParser()
        parser.feed(response.text)
        
        if parser.description:
            # Sanitize using single source of truth
            return sanitize_for_storage(parser.description)
        return None
        
    except Exception as e:
        print(f"    Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Backfill job descriptions')
    parser.add_argument('--limit', type=int, default=100, 
                        help='Max postings to process (default: 100)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between requests in seconds (default: 0.5)')
    args = parser.parse_args()
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST')
    )
    cur = conn.cursor()
    
    # Find postings without descriptions but with URLs
    cur.execute('''
        SELECT posting_id, posting_name, external_url
        FROM postings
        WHERE job_description IS NULL 
        AND external_url IS NOT NULL
        LIMIT %s
    ''', (args.limit,))
    
    postings = cur.fetchall()
    print(f"📥 Backfilling {len(postings)} job descriptions...")
    print(f"   Delay: {args.delay}s between requests")
    print("=" * 50)
    
    success = 0
    failed = 0
    skipped = 0
    
    for i, (posting_id, name, url) in enumerate(postings, 1):
        print(f"[{i}/{len(postings)}] {name[:50]}...")
        
        if not url:
            print(f"    Skipped: No URL")
            skipped += 1
            continue
        
        description = fetch_job_description(url)
        
        if description and len(description) >= 100:
            cur.execute('''
                UPDATE postings 
                SET job_description = %s
                WHERE posting_id = %s
            ''', (description, posting_id))
            conn.commit()
            print(f"    ✅ Saved ({len(description)} chars)")
            success += 1
        else:
            print(f"    ❌ Failed (desc too short or null)")
            failed += 1
        
        time.sleep(args.delay)
    
    print()
    print("=" * 50)
    print(f"✅ Success: {success}")
    print(f"❌ Failed:  {failed}")
    print(f"⏭️  Skipped: {skipped}")
    
    conn.close()


if __name__ == '__main__':
    main()
