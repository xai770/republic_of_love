#!/usr/bin/env python3
"""
Deutsche Bank Job Fetcher - Fetches job postings from Deutsche Bank API

Fetches up to max_jobs postings from the Deutsche Bank careers API and inserts
new postings into the database. Downstream pull-based actors (session_a_extract_summary,
sect_decompose, lily_cps_extract, lucy_lookup) automatically pick up new work.

Input:  Deutsche Bank API (external)
Output: postings table (new rows)

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Fetch Cycle] --> B{Already ran today?}
    B -->|Yes| Z1[⏭️ SKIP: already_ran_today]
    B -->|No| C{🔌 API Health Check}
    C -->|Fail| Z2[❌ FAIL: api_unreachable]
    C -->|OK| D[📡 Fetch Jobs from API]
    D --> E{API Success?}
    E -->|No| Z3[❌ FAIL: api_error]
    E -->|Yes| F[🔄 Process Jobs + Fetch Descriptions]
    F --> G{📊 Success Rate OK?}
    G -->|below 70%| Z4[⚠️ WARN: low_success_rate]
    G -->|OK| H[💾 Insert New Postings]
    H --> I{🗑️ Stale Check Safe?}
    I -->|over 50% would invalidate| Z5[⚠️ SKIP: staleness_safety]
    I -->|OK| J[🗑️ Invalidate Stale]
    J --> K[✅ SUCCESS]
    K --> L[Pull daemon picks up new work]
```

Usage:
    # Via cron (normal - daily at 6 AM):
    0 6 * * * cd /home/xai/Documents/ty_learn && ./venv/bin/python3 actors/db_job_fetcher.py
    
    # Manual run:
    python3 actors/db_job_fetcher.py
    
    # With options:
    python3 actors/db_job_fetcher.py --max-jobs 200

Author: Arden
Date: 2026-01-16
Task Type ID: 9384

NOTE: This is a "source" actor - it creates subjects rather than processing them.
      Triggered by cron, not by pull_daemon's work_query.
      Execution is still logged to tickets for auditability.
---
"""

import argparse
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set

import psycopg2
import psycopg2.extras
import requests
from bs4 import BeautifulSoup

# ============================================================================
# SETUP
# ============================================================================

from core.database import get_connection
from core.constants import Status
from core.text_utils import sanitize_for_storage

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 9384  # db_job_fetcher

# Workday API (where our data comes from - uses R-format IDs)
API_URL = 'https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebSite/jobs'
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

DEFAULT_MAX_JOBS = 100
# Workday API enforces max 20 jobs per request (undocumented limit)
DEFAULT_BATCH_SIZE = 20  # API pagination batch size - MUST be 20 or less
STALENESS_DAYS = 2  # Invalidate postings not seen for this many days

# QA thresholds
MIN_DESCRIPTION_SUCCESS_RATE = 0.70  # Warn if <70% of new jobs get descriptions
MAX_STALE_PERCENTAGE = 0.50  # Skip staleness if >50% would be invalidated (likely bug)


# ============================================================================
# ACTOR CLASS
# ============================================================================
class WorkdayDBJobFetcher:
    """
    Deutsche Bank Job Fetcher - Source actor for the pipeline.
    
    Unlike other thick actors, this one:
    - Is triggered by cron, not work_query
    - Creates subjects (postings) rather than processing them
    - Has no input subject_id - it's the pipeline entry point
    
    Still follows the three-phase pattern:
    1. PREFLIGHT: Check if already ran today
    2. PROCESS: Call API, parse jobs, fetch descriptions from Workday
    3. SAVE: Insert new postings, update last_seen_at, invalidate stale
    
    CRITICAL SAFEGUARDS (prevent false invalidations):
    - Track sync completeness: only invalidate if fetched_count >= api_total
    - Never invalidate from partial fetch: incomplete sync = no invalidations
    - Verify before invalidating: check if job still exists before marking invalid
    """
    
    def __init__(self, db_conn=None, max_jobs: int = DEFAULT_MAX_JOBS):
        """Initialize with database connection."""
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection()
            self._owns_connection = True
        self.max_jobs = max_jobs
        self.input_data: Dict[str, Any] = {}
        
        # Sync tracking - critical for preventing false invalidations
        self.api_total: int = 0  # Total jobs reported by API
        self.fetched_ids: Set[str] = set()  # All job IDs we fetched
        self.sync_complete: bool = False  # Did we get all jobs?
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point.
        
        Returns:
            Dict with success, stats, and any errors
        """
        try:
            # ----------------------------------------------------------------
            # PHASE 1: PREFLIGHT - Did we already run today?
            # ----------------------------------------------------------------
            preflight = self._preflight()
            if not preflight['ok']:
                return {
                    'success': False,
                    'skip_reason': preflight['reason'],
                    'message': preflight.get('message'),
                }
            
            # ----------------------------------------------------------------
            # PHASE 2: PROCESS - Fetch from API
            # ----------------------------------------------------------------
            jobs = self._fetch_from_api()
            
            if jobs is None:
                return {
                    'success': False,
                    'error': 'API request failed',
                }
            
            # Check sync completeness
            self.sync_complete = len(self.fetched_ids) >= self.api_total
            if not self.sync_complete:
                print(f"  ⚠️  INCOMPLETE SYNC: fetched {len(self.fetched_ids)}/{self.api_total} - invalidations disabled")
            
            # ----------------------------------------------------------------
            # PHASE 3: SAVE - Insert new postings, update seen, prune stale
            # ----------------------------------------------------------------
            stats = self._save_postings(jobs)
            
            # QA Check: Success rate for new jobs
            new_attempted = stats['new'] + stats['no_description']
            if new_attempted > 0:
                success_rate = stats['new'] / new_attempted
                stats['description_success_rate'] = round(success_rate, 2)
                
                if success_rate < MIN_DESCRIPTION_SUCCESS_RATE:
                    print(f"  ⚠️  Low description success rate: {success_rate:.0%} (threshold: {MIN_DESCRIPTION_SUCCESS_RATE:.0%})")
                    stats['qa_warning'] = f'Low description success rate: {success_rate:.0%}'
            
            # Invalidate stale postings (with safety check)
            stale_stats = self._invalidate_stale_postings()
            stats.update(stale_stats)
            
            revalidated_msg = f", revalidated: {stats['revalidated']}" if stats['revalidated'] > 0 else ""
            return {
                'success': True,
                '_consistency': '1/1',
                'stats': stats,
                'message': f"Fetched {stats['fetched']}, new: {stats['new']}{revalidated_msg}, skipped (no desc): {stats['no_description']}, stale invalidated: {stats['stale_invalidated']}",
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                'success': False,
                'error': str(e),
            }
    
    # ========================================================================
    # PHASE 1: PREFLIGHT
    # ========================================================================
    
    def _preflight(self) -> Dict:
        """
        Preflight checks before fetching.
        
        1. Check if already ran today (prevent duplicate runs)
        2. API health check (don't waste time if API is down)
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check 1: Already ran today?
        cur.execute("""
            SELECT ticket_id, completed_at
            FROM tickets
            WHERE task_type_id = %s
              AND status = 'completed'
              AND completed_at > NOW() - INTERVAL '20 hours'
            ORDER BY completed_at DESC
            LIMIT 1
        """, (TASK_TYPE_ID,))
        
        row = cur.fetchone()
        if row:
            return {
                'ok': False,
                'reason': 'ALREADY_RAN_TODAY',
                'message': f"Already ran at {row['completed_at']} (ticket {row['ticket_id']})",
            }
        
        # Check 2: API health check (quick test request)
        if not self._check_api_health():
            return {
                'ok': False,
                'reason': 'API_UNREACHABLE',
                'message': 'Deutsche Bank API is not responding',
            }
        
        return {'ok': True}
    
    def _check_api_health(self) -> bool:
        """
        Quick health check - can we reach the Workday API?
        
        Fetches 1 job to verify API is responding.
        """
        try:
            payload = {
                "appliedFacets": {},
                "limit": 1,
                "offset": 0,
                "searchText": ""
            }
            response = requests.post(API_URL, headers=API_HEADERS, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('total', 0) > 0:
                    print("  ✅ API health check passed")
                    return True
            print(f"  ❌ API health check failed: status {response.status_code}")
            return False
        except Exception as e:
            print(f"  ❌ API health check failed: {e}")
            return False
    
    # ========================================================================
    # PHASE 2: PROCESS - API FETCH
    # ========================================================================
    
    def _fetch_from_api(self) -> Optional[List[Dict]]:
        """
        Fetch jobs from Deutsche Bank Workday API with pagination.
        
        Returns list of job dicts or None on failure.
        Note: Workday API enforces max 20 jobs per request.
        
        IMPORTANT: Updates self.api_total and self.fetched_ids for sync tracking.
        """
        all_jobs = []
        offset = 0
        rate_limit_errors = 0
        self.fetched_ids = set()  # Reset for this run
        
        while len(all_jobs) < self.max_jobs:
            remaining = self.max_jobs - len(all_jobs)
            batch_size = min(DEFAULT_BATCH_SIZE, remaining)  # Max 20 per request
            
            payload = {
                "appliedFacets": {},
                "limit": batch_size,
                "offset": offset,
                "searchText": ""
            }
            
            try:
                response = requests.post(
                    API_URL, 
                    headers=API_HEADERS, 
                    json=payload, 
                    timeout=30
                )
                
                if response.status_code == 400:
                    # Rate limited - wait and retry with exponential backoff
                    rate_limit_errors += 1
                    if rate_limit_errors >= 5:
                        print(f"  ⚠️  Rate limited 5 times, stopping")
                        break
                    wait_time = 15 * rate_limit_errors  # 15s, 30s, 45s, 60s
                    print(f"  ⚠️  Rate limited (attempt {rate_limit_errors}/5), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    print(f"  ⚠️  API returned {response.status_code}")
                    break
                
                rate_limit_errors = 0  # Reset on success
                data = response.json()
                jobs = data.get('jobPostings', [])
                api_total = data.get('total', 0)
                
                # Track API's reported total (use max seen, as it can vary)
                if api_total > 0:
                    self.api_total = max(self.api_total, api_total)
                
                if not jobs:
                    break
                
                for job in jobs:
                    parsed = self._parse_job_item(job)
                    if parsed:
                        all_jobs.append(parsed)
                        self.fetched_ids.add(parsed['external_id'])  # Track for sync
                
                print(f"  📡 Fetched {len(all_jobs)}/{self.api_total} (offset {offset})")
                offset += len(jobs)
                
                if len(all_jobs) >= self.api_total:
                    break  # Got all available jobs
                
                time.sleep(2)  # Rate limit protection - 2s between requests
                    
            except requests.RequestException as e:
                print(f"  ❌ API error: {e}")
                return None
        
        return all_jobs[:self.max_jobs]
    
    def _parse_job_item(self, item: Dict) -> Optional[Dict]:
        """Parse a single job item from Workday API response."""
        # Get job ID from bulletFields (R-format)
        bullet_fields = item.get('bulletFields', [])
        job_id = bullet_fields[0] if bullet_fields else None
        
        if not job_id:
            # Fallback to externalPath
            external_path = item.get('externalPath', '')
            if external_path:
                job_id = external_path.split('/')[-1] if '/' in external_path else external_path
            else:
                return None
        
        # Build apply URL from externalPath
        external_path = item.get('externalPath', '')
        apply_uri = f"https://db.wd3.myworkdayjobs.com/DBWebSite{external_path}" if external_path else ''
        
        return {
            'external_id': str(job_id),
            'title': item.get('title', 'Unknown'),
            'location': item.get('locationsText', 'Unknown'),
            'apply_uri': apply_uri,
            'description': None,  # Fetched separately from Workday page
            'raw_data': item
        }
    
    # ========================================================================
    # PHASE 3: SAVE
    # ========================================================================
    
    def _save_postings(self, jobs: List[Dict]) -> Dict:
        """
        Insert new postings into database.
        
        Returns stats dict with counts.
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        stats = {
            'fetched': len(jobs),
            'new': 0,
            'existing': 0,
            'revalidated': 0,
            'no_description': 0,
            'errors': 0
        }
        
        for i, job in enumerate(jobs, 1):
            try:
                # Check if job already exists
                cur.execute(
                    "SELECT posting_id, invalidated FROM postings WHERE external_id = %s",
                    (job['external_id'],)
                )
                existing = cur.fetchone()
                
                if existing:
                    # Update last_seen_at for existing posting
                    # Also re-validate if it was invalidated (job came back!)
                    if existing['invalidated']:
                        cur.execute("""
                            UPDATE postings 
                            SET last_seen_at = NOW(),
                                invalidated = FALSE,
                                invalidated_reason = NULL,
                                invalidated_at = NULL,
                                posting_status = 'active'
                            WHERE posting_id = %s
                        """, (existing['posting_id'],))
                        stats['revalidated'] += 1
                    else:
                        cur.execute(
                            "UPDATE postings SET last_seen_at = NOW() WHERE posting_id = %s",
                            (existing['posting_id'],)
                        )
                    stats['existing'] += 1
                    continue
                
                # NEW JOB: Fetch description from Workday before inserting
                apply_url = job.get('apply_uri', '')
                description = None
                
                if apply_url:
                    description = self._fetch_description_from_workday(apply_url)
                    # Rate limit - be nice to Workday
                    time.sleep(0.2)
                
                if not description:
                    # No description = don't insert (shell posting is useless)
                    stats['no_description'] += 1
                    if i % 20 == 0 or i == len(jobs):
                        print(f"  ⚠️  [{i}/{len(jobs)}] Skipped {stats['no_description']} jobs (no description)")
                    continue
                
                # Insert new posting WITH description
                cur.execute("""
                    INSERT INTO postings (
                        external_id, external_job_id, posting_name, job_title, location_city, 
                        source, external_url, source_metadata, job_description,
                        first_seen_at, last_seen_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING posting_id
                """, (
                    job['external_id'],
                    job['external_id'],  # external_job_id = external_id
                    job['title'],  # posting_name = title
                    job['title'],
                    job['location'],
                    'deutsche_bank',
                    apply_url or 'https://careers.db.com',  # NOT NULL
                    json.dumps(job['raw_data']),
                    description
                ))
                
                row = cur.fetchone()
                posting_id = row['posting_id']
                stats['new'] += 1
                
                if stats['new'] % 10 == 0:
                    self.conn.commit()  # Periodic commit
                    print(f"  ✅ [{i}/{len(jobs)}] {stats['new']} new postings inserted...")
                
            except Exception as e:
                self.conn.rollback()
                stats['errors'] += 1
                print(f"  ❌ Error inserting job {job['external_id']}: {type(e).__name__}: {e}")
        
        self.conn.commit()
        return stats
    
    def _fetch_description_from_workday(self, url: str) -> Optional[str]:
        """
        Fetch job description from Workday URL (db.wd3.myworkdayjobs.com).
        
        Returns description text or None if unavailable.
        """
        job_url = url.rstrip('/').removesuffix('/apply')
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            }
            response = requests.get(job_url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for og:description meta tag
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content', '').strip()
                if len(description) > 50:
                    return sanitize_for_storage(description)
            
            return None
            
        except Exception:
            return None
    
    def _invalidate_stale_postings(self) -> Dict:
        """
        Invalidate postings not seen in API for STALENESS_DAYS+ days.
        
        THREE-LAYER SAFETY (prevent false invalidations):
        1. SYNC CHECK: Only invalidate if we completed a full sync
        2. RATIO CHECK: Skip if >50% would be invalidated (likely bug)
        3. VERIFY CHECK: Confirm each job is actually gone before invalidating
        """
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # ====================================================================
        # SAFETY LAYER 1: Sync completeness check
        # ====================================================================
        if not self.sync_complete:
            print(f"  🛡️  SAFETY: Sync incomplete ({len(self.fetched_ids)}/{self.api_total}) - skipping ALL invalidations")
            print(f"       This prevents false invalidations from partial fetches")
            return {
                'stale_invalidated': 0, 
                'stale_skipped': True, 
                'skip_reason': 'incomplete_sync',
                'fetched': len(self.fetched_ids),
                'api_total': self.api_total
            }
        
        # ====================================================================
        # SAFETY LAYER 2: Ratio check
        # ====================================================================
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE last_seen_at < NOW() - INTERVAL '2 days') as stale_count,
                COUNT(*) as total_active
            FROM postings
            WHERE source = 'deutsche_bank'
              AND invalidated IS NOT TRUE
        """)
        
        counts = cur.fetchone()
        stale_count = counts['stale_count']
        total_active = counts['total_active']
        
        if total_active == 0:
            return {'stale_invalidated': 0, 'stale_skipped': False}
        
        stale_ratio = stale_count / total_active
        
        if stale_ratio > MAX_STALE_PERCENTAGE:
            print(f"  🛡️  SAFETY: Would invalidate {stale_count}/{total_active} ({stale_ratio:.0%}) - skipping")
            print(f"       This exceeds {MAX_STALE_PERCENTAGE:.0%} threshold - likely a bug")
            return {'stale_invalidated': 0, 'stale_skipped': True, 'skip_reason': 'ratio_exceeded', 'stale_would_invalidate': stale_count}
        
        # ====================================================================
        # SAFETY LAYER 3: Verify each job before invalidating
        # ====================================================================
        # Get candidates for invalidation
        cur.execute("""
            SELECT posting_id, external_id, posting_name
            FROM postings
            WHERE source = 'deutsche_bank'
              AND invalidated IS NOT TRUE
              AND last_seen_at < NOW() - INTERVAL '2 days'
        """)
        candidates = cur.fetchall()
        
        if not candidates:
            return {'stale_invalidated': 0, 'stale_skipped': False}
        
        print(f"  🔍 Verifying {len(candidates)} stale candidates before invalidation...")
        
        actually_invalidated = 0
        verified_still_exists = 0
        
        for candidate in candidates:
            external_id = candidate['external_id']
            
            # If we saw this job in our complete sync, it's NOT stale
            if external_id in self.fetched_ids:
                verified_still_exists += 1
                # Update last_seen_at since we know it exists
                cur.execute(
                    "UPDATE postings SET last_seen_at = NOW() WHERE posting_id = %s",
                    (candidate['posting_id'],)
                )
                continue
            
            # Double-check: verify job is actually gone with single API call
            if self._verify_job_still_exists(external_id):
                verified_still_exists += 1
                cur.execute(
                    "UPDATE postings SET last_seen_at = NOW() WHERE posting_id = %s",
                    (candidate['posting_id'],)
                )
                continue
            
            # Confirmed gone - safe to invalidate
            cur.execute("""
                UPDATE postings
                SET invalidated = TRUE,
                    invalidated_reason = 'Verified removed from source',
                    invalidated_at = NOW(),
                    posting_status = 'invalid'
                WHERE posting_id = %s
            """, (candidate['posting_id'],))
            actually_invalidated += 1
        
        self.conn.commit()
        
        if verified_still_exists > 0:
            print(f"  ✅ Kept {verified_still_exists} jobs (verified still online)")
        if actually_invalidated > 0:
            print(f"  🗑️  Invalidated {actually_invalidated} jobs (verified removed)")
        
        return {
            'stale_invalidated': actually_invalidated, 
            'stale_skipped': False,
            'verified_still_exists': verified_still_exists
        }
    
    def _verify_job_still_exists(self, external_id: str) -> bool:
        """
        Verify if a specific job still exists on Workday.
        
        Makes a single API call to check if the job ID appears in results.
        Returns True if job exists, False if confirmed gone.
        """
        try:
            # Search for the specific job ID
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": external_id  # Search for the job ID
            }
            
            response = requests.post(API_URL, headers=API_HEADERS, json=payload, timeout=10)
            
            if response.status_code != 200:
                # API error - assume job exists to be safe (don't invalidate)
                return True
            
            data = response.json()
            jobs = data.get('jobPostings', [])
            
            # Check if our job ID is in the results
            for job in jobs:
                bf = job.get('bulletFields', [])
                if bf and bf[0] == external_id:
                    return True  # Found it!
            
            # Not found in search results - confirmed gone
            return False
            
        except Exception:
            # On any error, assume job exists (be conservative)
            return True


# ============================================================================
# STANDALONE EXECUTION (for cron)
# ============================================================================
def main():
    """
    Main entry point for cron execution.
    
    Creates a ticket for auditability, runs the actor, records result.
    
    Usage:
        python3 actors/postings__row_CU.py
        python3 actors/postings__row_CU.py --max-jobs 200
    """
    parser = argparse.ArgumentParser(description='Fetch jobs from Deutsche Bank API')
    parser.add_argument('--max-jobs', type=int, default=DEFAULT_MAX_JOBS,
                        help=f'Max jobs to fetch (default: {DEFAULT_MAX_JOBS})')
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"📥 Deutsche Bank Job Fetcher")
    print(f"   Max jobs: {args.max_jobs}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Create ticket for auditability
        cur.execute("""
            INSERT INTO tickets (
                task_type_id,
                actor_type,
                subject_type,
                subject_id,
                status,
                input,
                execution_order,
                started_at
            ) VALUES (
                %s, 'thick', 'fetch_cycle', 0, 'running',
                %s, 1, NOW()
            )
            RETURNING ticket_id
        """, (TASK_TYPE_ID, json.dumps({'max_jobs': args.max_jobs})))
        
        ticket_id = cur.fetchone()['ticket_id']
        conn.commit()
        
        print(f"  ticket_id: {ticket_id}")
        
        # Run the actor
        actor = WorkdayDBJobFetcher(conn, max_jobs=args.max_jobs)
        result = actor.process()
        
        # Record result
        if result.get('success'):
            cur.execute("""
                UPDATE tickets
                SET status = 'completed',
                    output = %s,
                    completed_at = NOW()
                WHERE ticket_id = %s
            """, (json.dumps(result), ticket_id))
            print(f"\n✅ SUCCESS: {result.get('message')}")
        else:
            error = result.get('error') or result.get('skip_reason') or 'Unknown error'
            # 'skipped' isn't a valid status - use 'completed' for skips, 'failed' for errors
            status = 'completed' if result.get('skip_reason') else 'failed'
            cur.execute("""
                UPDATE tickets
                SET status = %s,
                    output = %s,
                    completed_at = NOW()
                WHERE ticket_id = %s
            """, (status, json.dumps(result), ticket_id))
            print(f"\n{'⏭️ SKIPPED' if result.get('skip_reason') else '❌ FAILED'}: {error}")
        
        conn.commit()
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
