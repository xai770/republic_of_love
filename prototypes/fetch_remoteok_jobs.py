#!/usr/bin/env python3
"""
RemoteOK Job Fetcher - Technology Demonstrator

Fetches remote jobs from RemoteOK API and inserts into postings table.
This is a standalone script to validate the data pipeline before building Workflow 3004.

Usage:
    python3 tools/fetch_remoteok_jobs.py [--limit N] [--dry-run]

Author: Arden
Date: 2025-11-16
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
import requests
from core.database import get_connection, return_connection

class RemoteOKFetcher:
    """Fetch and process jobs from RemoteOK API"""
    
    API_URL = "https://remoteok.com/api"
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'fetched': 0,
            'inserted': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from RemoteOK API"""
        print(f"🌐 Fetching jobs from {self.API_URL}...")
        
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            
            jobs = response.json()
            
            # First element is legal notice, skip it
            if jobs and isinstance(jobs[0], dict) and 'legal' in jobs[0]:
                jobs = jobs[1:]
            
            self.stats['fetched'] = len(jobs)
            print(f"✅ Fetched {len(jobs)} jobs from RemoteOK")
            
            return jobs
            
        except requests.RequestException as e:
            print(f"❌ Failed to fetch jobs: {e}")
            return []
    
    def job_exists(self, cursor, slug: str) -> bool:
        """Check if job already exists in database"""
        cursor.execute("""
            SELECT posting_id 
            FROM postings 
            WHERE external_id = %s AND source = 'remoteok'
        """, (slug,))
        
        return cursor.fetchone() is not None
    
    def insert_job(self, cursor, job: Dict) -> Optional[int]:
        """Insert job into postings table"""
        try:
            # Extract fields - map to actual schema columns
            posting_name = job.get('company', 'Unknown')[:255]  # Company name
            job_title = job.get('position', 'Untitled')[:255]
            job_description = job.get('description', '')
            location_city = job.get('location', 'Remote')[:255]
            external_id = job.get('slug', f"remoteok_{job.get('id', 'unknown')}")
            external_url = job.get('url', '')
            
            # Store full JSON for reference
            raw_data = json.dumps(job)
            
            # Insert using actual schema columns
            cursor.execute("""
                INSERT INTO postings (
                    posting_name,
                    job_title,
                    job_description,
                    location_city,
                    source,
                    external_id,
                    external_url,
                    fetched_at,
                    raw_data,
                    enabled,
                    posting_status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING posting_id
            """, (
                posting_name,
                job_title,
                job_description,
                location_city,
                'remoteok',
                external_id,
                external_url,
                datetime.now(),
                raw_data,
                True,  # enabled
                'active'  # posting_status
            ))
            
            posting_id = cursor.fetchone()[0]
            return posting_id
            
        except Exception as e:
            import traceback
            print(f"❌ Error inserting job {job.get('slug', 'unknown')}: {e}")
            print(f"   Details: {traceback.format_exc()}")
            self.stats['errors'] += 1
            return None
    
    def process_jobs(self, jobs: List[Dict], limit: Optional[int] = None):
        """Process and insert jobs into database"""
        if not jobs:
            print("⚠️  No jobs to process")
            return
        
        if limit:
            jobs = jobs[:limit]
            print(f"📊 Processing first {limit} jobs (limit applied)")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            for i, job in enumerate(jobs, 1):
                slug = job.get('slug', f"unknown_{i}")
                
                # Check if exists
                if self.job_exists(cursor, slug):
                    self.stats['skipped'] += 1
                    if i <= 5:  # Show first few
                        print(f"⏭️  [{i}/{len(jobs)}] Skipped: {job.get('position', 'N/A')} (already exists)")
                    continue
                
                # Insert new job
                if self.dry_run:
                    print(f"🔍 [DRY RUN] Would insert: {job.get('company', 'N/A')} - {job.get('position', 'N/A')}")
                    self.stats['inserted'] += 1
                else:
                    posting_id = self.insert_job(cursor, job)
                    if posting_id:
                        self.stats['inserted'] += 1
                        if i <= 5:  # Show first few
                            print(f"✅ [{i}/{len(jobs)}] Inserted posting_id={posting_id}: {job.get('company', 'N/A')} - {job.get('position', 'N/A')}")
            
            if not self.dry_run:
                conn.commit()
                print(f"\n💾 Database committed")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Transaction failed: {e}")
            
        finally:
            return_connection(conn)
    
    def print_summary(self):
        """Print execution summary"""
        print("\n" + "="*80)
        print("📊 REMOTEOK FETCH SUMMARY")
        print("="*80)
        print(f"  Fetched:  {self.stats['fetched']} jobs from API")
        print(f"  Inserted: {self.stats['inserted']} new jobs")
        print(f"  Skipped:  {self.stats['skipped']} duplicates")
        print(f"  Errors:   {self.stats['errors']} failures")
        print("="*80)
        
        if self.stats['inserted'] > 0 and not self.dry_run:
            print("\n🎯 Next Steps:")
            print("  1. Review inserted jobs in database:")
            print("     SELECT posting_id, company_name, job_title, location")
            print("     FROM postings WHERE source='remoteok' ORDER BY fetched_at DESC LIMIT 10;")
            print("\n  2. Run Workflow 3001 to extract skills:")
            print("     python3 runners/workflow_3001_runner.py --source remoteok")
            print("\n  3. Check extraction results:")
            print("     SELECT posting_id, company_name, skill_keywords, ihl_score")
            print("     FROM postings WHERE source='remoteok' AND skill_keywords IS NOT NULL;")
    
    def show_sample(self, jobs: List[Dict], count: int = 3):
        """Show sample jobs for inspection"""
        print("\n" + "="*80)
        print(f"📋 SAMPLE JOBS (first {count})")
        print("="*80)
        
        for i, job in enumerate(jobs[:count], 1):
            print(f"\n{i}. {job.get('position', 'N/A')}")
            print(f"   Company: {job.get('company', 'N/A')}")
            print(f"   Location: {job.get('location', 'N/A')}")
            print(f"   Tags: {', '.join(job.get('tags', [])[:5])}")
            
            salary_min = job.get('salary_min', 0)
            salary_max = job.get('salary_max', 0)
            if salary_min or salary_max:
                print(f"   Salary: ${salary_min:,} - ${salary_max:,}")
            
            # Show description snippet
            desc = job.get('description', '')
            if desc:
                # Remove HTML tags for display
                import re
                clean_desc = re.sub('<[^<]+?>', '', desc)
                snippet = clean_desc[:150].strip()
                if len(clean_desc) > 150:
                    snippet += "..."
                print(f"   Description: {snippet}")
        
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description='Fetch jobs from RemoteOK API')
    parser.add_argument('--limit', type=int, help='Limit number of jobs to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without actually inserting')
    parser.add_argument('--sample', action='store_true', help='Show sample jobs and exit (no insertion)')
    
    args = parser.parse_args()
    
    fetcher = RemoteOKFetcher(dry_run=args.dry_run)
    
    # Fetch jobs
    jobs = fetcher.fetch_jobs()
    
    if not jobs:
        print("❌ No jobs fetched. Exiting.")
        sys.exit(1)
    
    # Show sample if requested
    if args.sample:
        fetcher.show_sample(jobs, count=5)
        sys.exit(0)
    
    # Process jobs
    fetcher.process_jobs(jobs, limit=args.limit)
    
    # Print summary
    fetcher.print_summary()


if __name__ == '__main__':
    main()
