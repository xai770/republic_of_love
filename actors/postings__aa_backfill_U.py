#!/usr/bin/env python3
"""
postings__aa_backfill_U.py - Backfill Missing AA Job Descriptions

Actor type: Update (U)
Table: postings
Source: arbeitsagentur.de

Re-fetches job descriptions from arbeitsagentur.de for postings where 
job_description is NULL. Uses simple requests.get() + BeautifulSoup
(NOT Playwright) since AA server-renders the description into the HTML.

Usage:
    python3 actors/postings__aa_backfill_U.py --dry-run
    python3 actors/postings__aa_backfill_U.py --limit 50
    python3 actors/postings__aa_backfill_U.py --order newest --limit 12000  # Nightly

Features:
    - VPN rotation on 403/429 errors via vpn.sh
    - Detects expired/removed jobs (invalidates them)
    - Handles both native AA (10001-*) and external partner jobs
    - Logs to logs/aa_backfill.log
"""

import argparse
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import psycopg2
import psycopg2.extras
import requests
from bs4 import BeautifulSoup


def strip_html(text: str) -> str:
    """Strip HTML tags from text, preserving whitespace structure."""
    if not text or '<' not in text:
        return text
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator='\n', strip=True)

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent

from core.database import get_connection_raw, return_connection

# ============================================================================
# LOGGING
# ============================================================================
LOG_LOCK = threading.Lock()

def log(msg: str):
    """Print timestamped message to stdout (thread-safe)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with LOG_LOCK:
        print(line, flush=True)

def tlog(msg: str):
    """Print timestamped message to stdout (alias for log)."""
    log(msg)

# ============================================================================
# CONFIGURATION
# ============================================================================
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
REQUEST_TIMEOUT = 30
MIN_DESCRIPTION_LENGTH = 100
MAX_CONSECUTIVE_RATE_LIMITS = 3
DELAY_BETWEEN_REQUESTS = 0.1  # Seconds - AA rate limits by request count, not speed. VPN rotation handles 403s.
REQUESTS_PER_IP = 550  # AA rate limits at ~600 requests per IP - rotate proactively at 550 for safety margin

# VPN script location
VPN_SCRIPT = PROJECT_ROOT / "scripts" / "vpn.sh"

# Thread synchronization for VPN rotation
VPN_LOCK = threading.Lock()
VPN_ROTATING = threading.Event()  # Set when VPN rotation is in progress
REQUEST_COUNTER = [0]  # Mutable counter for proactive VPN rotation
REQUEST_COUNTER_LOCK = threading.Lock()


def rotate_vpn() -> bool:
    """Rotate VPN via vpn.sh switch de. Thread-safe - only one rotation at a time."""
    if not VPN_SCRIPT.exists():
        log("⚠️  VPN script not found - cannot rotate")
        return False
    
    with VPN_LOCK:
        VPN_ROTATING.set()  # Signal other threads to pause
        try:
            result = subprocess.run(
                ["bash", str(VPN_SCRIPT), "switch", "de"],
                capture_output=True,
                text=True,
                timeout=60  # Increased timeout for VPN switch
            )
            if result.returncode == 0:
                log("🔄 VPN rotated successfully")
                time.sleep(2)  # Wait for connection to stabilize
                return True
            else:
                log(f"⚠️  VPN rotation failed: {result.stderr}")
                return False
        except Exception as e:
            log(f"⚠️  VPN rotation error: {e}")
            return False
        finally:
            VPN_ROTATING.clear()  # Allow threads to resume


def fetch_description(external_url: str, fetch_external: bool = False) -> Tuple[Optional[str], str]:
    """
    Fetch job description from AA detail page.
    
    Returns:
        Tuple of (description, status)
        - description: The job description text or None
        - status: One of:
            - 'SUCCESS' - Description found
            - 'NOT_FOUND' - Job doesn't exist anymore
            - 'EXTERNAL_PARTNER' - Job is hosted externally (skipped)
            - 'NO_DESCRIPTION' - Page loaded but no description found
            - 'RATE_LIMITED' - Got 403/429
            - 'ERROR' - Other error
    """
    import json as json_lib
    
    # Extract refnr from URL
    match = re.search(r'/jobdetail/([^\/?]+)', external_url)
    if not match:
        return None, 'INVALID_URL'
    
    refnr = match.group(1)
    
    # Check if it's an external partner job (not 10001-* prefix)
    is_external_partner = not refnr.startswith('10001-')
    if is_external_partner and not fetch_external:
        return 'EXTERNAL_PARTNER', 'EXTERNAL_PARTNER'
    
    try:
        response = requests.get(
            external_url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False  # Don't follow redirects
        )
        
        # Rate limited
        if response.status_code in (403, 429):
            return None, 'RATE_LIMITED'
        
        # Redirect = job moved/deleted
        if response.status_code in (301, 302, 303, 307, 308):
            return None, 'NOT_FOUND'
        
        # 404 = job deleted from AA
        if response.status_code == 404:
            return None, 'NOT_FOUND'
        
        if response.status_code != 200:
            return None, f'HTTP_{response.status_code}'
        
        html = response.text
        
        # Check if job doesn't exist (AA shows "Dieses Stellenangebot gibt es nicht")
        if 'jobdetails-not-found' in html or 'nicht oder nicht mehr' in html:
            return None, 'NOT_FOUND'
        
        # METHOD 1: Try ng-state JSON (works for both native and external partner jobs)
        ng_match = re.search(r'<script id="ng-state"[^>]*>(.+?)</script>', html, re.DOTALL)
        if ng_match:
            try:
                ng_data = json_lib.loads(ng_match.group(1))
                desc = ng_data.get('jobdetail', {}).get('stellenangebotsBeschreibung', '')
                if desc and len(desc) >= MIN_DESCRIPTION_LENGTH:
                    # Strip HTML - staffing agencies embed CSS/HTML in descriptions
                    desc = strip_html(desc)
                    if len(desc) >= MIN_DESCRIPTION_LENGTH:
                        return desc, 'SUCCESS'
            except json_lib.JSONDecodeError:
                pass  # Fall through to DOM parsing
        
        # METHOD 2: Parse DOM for description container (native AA jobs)
        soup = BeautifulSoup(html, 'html.parser')
        desc_container = soup.find('div', {'id': 'detail-beschreibung-text-container'})
        if desc_container:
            description = desc_container.get_text(separator='\n', strip=True)
            if len(description) >= MIN_DESCRIPTION_LENGTH:
                return description, 'SUCCESS'
            else:
                # Very short description - might be truncated
                return description if len(description) > 20 else None, 'SHORT_DESCRIPTION'
        
        # Fallback: Check for external redirect hint
        # AA shows these jobs but they link out to external sites
        ext_link = soup.find('a', {'id': 'detailansicht-bewerbungslink-extern'})
        if ext_link:
            return 'EXTERNAL_PARTNER', 'EXTERNAL_PARTNER'
        
        # Check og:description as last resort
        og_meta = soup.find('meta', {'property': 'og:description'})
        if og_meta and og_meta.get('content'):
            desc = og_meta['content'].strip()
            if len(desc) >= MIN_DESCRIPTION_LENGTH:
                return desc, 'SUCCESS'
        
        return None, 'NO_DESCRIPTION'
        
    except requests.Timeout:
        return None, 'TIMEOUT'
    except requests.RequestException as e:
        return None, f'REQUEST_ERROR: {str(e)[:50]}'
    except Exception as e:
        return None, f'ERROR: {str(e)[:50]}'


def get_postings_to_process(conn, limit: int = None, min_chars: int = 300, native_only: bool = True, order: str = 'oldest') -> list:
    """
    Get postings that need description backfill.
    
    Args:
        conn: Database connection
        limit: Max postings to return
        min_chars: Include postings with descriptions shorter than this (truncated)
        native_only: Only include native AA jobs (10001-*), not external partners
        order: 'newest' (first_seen_at DESC) or 'oldest' (posting_id ASC)
               Use 'newest' for nightly runs - fresh jobs get filled first!
    """
    query = f"""
        SELECT posting_id, external_url, external_id
        FROM postings
        WHERE source = 'arbeitsagentur'
          AND external_url LIKE '%%jobdetail/%%'
          AND (
              job_description IS NULL
              OR LENGTH(job_description) < {min_chars}
          )
          AND invalidated_at IS NULL
    """
    if native_only:
        query += " AND external_id LIKE 'aa-10001-%%'"
    
    # Order matters! newest = process fresh jobs first (higher success rate)
    if order == 'newest':
        query += " ORDER BY first_seen_at DESC NULLS LAST"
    else:
        query += " ORDER BY posting_id"
    
    if limit:
        query += f" LIMIT {limit}"
    
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        return cur.fetchall()


def update_posting_description(conn, posting_id: int, description: str) -> bool:
    """Update posting with fetched description."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE postings
                SET job_description = %s,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (description, posting_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        log(f"  ❌ DB update error: {e}")
        return False


def invalidate_posting(conn, posting_id: int, reason: str) -> bool:
    """Mark posting as invalidated (job removed from AA)."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE postings
                SET invalidated = true,
                    invalidated_at = NOW(),
                    invalidated_reason = %s,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (reason, posting_id))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        log(f"  ❌ DB invalidate error: {e}")
        return False


# ============================================================================
# PULL DAEMON ACTOR CLASS
# ============================================================================
# Wrapper class so core/turing_daemon.py can import and call process() per subject.

class PostingsAABackfillU:
    """Pull daemon-compatible wrapper for single-posting description fetch."""

    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}

    def process(self) -> dict:
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        if not posting_id:
            return {'success': False, 'error': 'No posting_id/subject_id'}

        conn = self.conn
        own_conn = False
        if conn is None:
            conn = get_connection_raw()
            own_conn = True

        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT posting_id, external_url
                FROM postings
                WHERE posting_id = %s
            """, (posting_id,))
            posting = cur.fetchone()

            if not posting:
                return {'success': False, 'skip_reason': 'posting_not_found'}

            external_url = posting.get('external_url')
            if not external_url:
                return {'success': False, 'skip_reason': 'no_external_url'}

            # Fetch description using simple requests + BeautifulSoup
            description, status = fetch_description(external_url)

            if status == 'SUCCESS' and description:
                # Strip HTML and save
                description = strip_html(description)
                update_posting_description(conn, posting_id, description)
                return {'success': True, 'posting_id': posting_id, 'chars': len(description)}

            elif status == 'NOT_FOUND':
                # Job removed from AA - invalidate
                invalidate_posting(conn, posting_id, 'NOT_FOUND_ON_AA')
                return {'success': False, 'skip_reason': 'not_found_invalidated'}

            elif status == 'EXTERNAL_PARTNER':
                # Mark for external partner scraping
                cur.execute("""
                    UPDATE postings SET job_description = '[EXTERNAL_PARTNER]', updated_at = NOW()
                    WHERE posting_id = %s
                """, (posting_id,))
                conn.commit()
                return {'success': False, 'skip_reason': 'external_partner'}

            elif status == 'RATE_LIMITED':
                return {'success': False, 'error': 'Rate limited by AA'}

            elif status == 'SHORT_DESCRIPTION' and description:
                # Short but valid - save it anyway, just mark as skip (no retry needed)
                description = strip_html(description)
                update_posting_description(conn, posting_id, description)
                return {'success': True, 'posting_id': posting_id, 'chars': len(description), 'note': 'short'}

            else:
                return {'success': False, 'skip_reason': f'{status}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if own_conn and conn:
                return_connection(conn)


def main():
    parser = argparse.ArgumentParser(description='Backfill AA job descriptions')
    parser.add_argument('--limit', type=int, help='Max postings to process')
    parser.add_argument('--batch-size', type=int, default=50, help='Print stats every N postings')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t update database')
    parser.add_argument('--min-chars', type=int, default=300, help='Also re-fetch descriptions shorter than this')
    parser.add_argument('--no-vpn', action='store_true', help='Disable VPN rotation')
    parser.add_argument('--include-partners', action='store_true', help='Include external partner jobs (usually skip)')
    parser.add_argument('--order', choices=['newest', 'oldest'], default='oldest',
                        help='Process order: newest (first_seen_at DESC) or oldest (posting_id ASC). Use newest for nightly!')
    parser.add_argument('--workers', type=int, default=1, 
                        help='Number of parallel workers (default: 1). Try 3-5 to find rate limit threshold.')
    args = parser.parse_args()
    
    print("=" * 70)
    tlog("🔍 AA Job Description Backfill (Simple HTTP)")
    print("=" * 70)
    tlog(f"Min description chars: {args.min_chars}")
    tlog(f"VPN rotation: {'disabled' if args.no_vpn else 'enabled'}")
    tlog(f"Order: {args.order} first")
    tlog(f"Workers: {args.workers}")
    tlog(f"Dry run: {args.dry_run}")
    print()
    
    conn = get_connection_raw()
    
    try:
        postings = get_postings_to_process(conn, args.limit, args.min_chars, not args.include_partners, args.order)
        total = len(postings)
        tlog(f"📋 Found {total} postings to process")
        print()
        
        if total == 0:
            tlog("✅ Nothing to do!")
            return
        
        # Thread-safe stats
        stats_lock = threading.Lock()
        stats = {
            'success': 0,
            'external_partner': 0,
            'not_found': 0,
            'rate_limited': 0,
            'no_description': 0,
            'error': 0,
            'skipped': 0,
            'processed': 0,
        }
        consecutive_rate_limits = [0]  # List so it's mutable in nested function
        
        def process_posting(i: int, posting: dict) -> None:
            """Process a single posting (called by each worker thread)."""
            nonlocal consecutive_rate_limits
            
            posting_id = posting['posting_id']
            external_url = posting['external_url']
            external_id = posting['external_id']
            
            # Wait if VPN is being rotated
            while VPN_ROTATING.is_set():
                time.sleep(0.5)
            
            # Proactive VPN rotation before hitting rate limit
            # Only one thread should trigger rotation
            should_rotate = False
            with REQUEST_COUNTER_LOCK:
                REQUEST_COUNTER[0] += 1
                if REQUEST_COUNTER[0] >= REQUESTS_PER_IP and not args.no_vpn:
                    should_rotate = True
                    REQUEST_COUNTER[0] = 0  # Reset immediately to prevent other threads triggering
            
            if should_rotate:
                log(f"🔄 Proactive VPN rotation at {REQUESTS_PER_IP} requests...")
                rotate_vpn()
            
            req_start = time.time()
            
            # Pass fetch_external=True if we're including partners
            description, status = fetch_description(external_url, fetch_external=args.include_partners)
            
            elapsed = time.time() - req_start
            
            # Thread-safe stats update
            with stats_lock:
                stats['processed'] += 1
                progress = stats['processed']
            
            # Get own connection for DB updates (connections aren't thread-safe)
            thread_conn = None
            if not args.dry_run:
                thread_conn = get_connection_raw()
            
            try:
                if status == 'SUCCESS':
                    log(f"[{progress}/{total}] {external_id} ✅ {len(description)} chars ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['success'] += 1
                        consecutive_rate_limits[0] = 0
                    if thread_conn:
                        update_posting_description(thread_conn, posting_id, description)
                        
                elif status == 'EXTERNAL_PARTNER':
                    log(f"[{progress}/{total}] {external_id} ⏭️  EXTERNAL_PARTNER ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['external_partner'] += 1
                    if thread_conn:
                        update_posting_description(thread_conn, posting_id, 'EXTERNAL_PARTNER')
                        
                elif status == 'NOT_FOUND':
                    log(f"[{progress}/{total}] {external_id} 🗑️  Job removed from AA ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['not_found'] += 1
                    if thread_conn:
                        invalidate_posting(thread_conn, posting_id, 'Job removed from arbeitsagentur.de')
                        
                elif status == 'RATE_LIMITED':
                    log(f"[{progress}/{total}] {external_id} ⚠️  Rate limited ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['rate_limited'] += 1
                        consecutive_rate_limits[0] += 1
                        rl_count = consecutive_rate_limits[0]
                    
                    # Trigger VPN rotation if too many rate limits (only one thread does this)
                    if rl_count >= MAX_CONSECUTIVE_RATE_LIMITS and not args.no_vpn:
                        log(f"🔄 {rl_count} rate limits - rotating VPN...")
                        if rotate_vpn():
                            with stats_lock:
                                consecutive_rate_limits[0] = 0
                        else:
                            log("⏸️  VPN rotation failed - pausing 60s...")
                            time.sleep(60)
                            with stats_lock:
                                consecutive_rate_limits[0] = 0
                            
                elif status == 'NO_DESCRIPTION':
                    log(f"[{progress}/{total}] {external_id} ⚠️  No description in HTML ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['no_description'] += 1
                        
                elif status == 'SHORT_DESCRIPTION' and description:
                    # Save short descriptions too - they're valid, just small
                    log(f"[{progress}/{total}] {external_id} ✅ {len(description)} chars (short) ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['success'] += 1
                    if thread_conn:
                        update_posting_description(thread_conn, posting_id, description)
                    
                else:
                    log(f"[{progress}/{total}] {external_id} ❌ {status} ({elapsed:.1f}s)")
                    with stats_lock:
                        stats['error'] += 1
            finally:
                if thread_conn:
                    return_connection(thread_conn)
            
            # Batch stats (roughly every batch_size)
            if progress % args.batch_size == 0:
                with stats_lock:
                    log(f"📊 Progress: {progress}/{total} | ✅{stats['success']} 🗑️{stats['not_found']} ⚠️{stats['rate_limited']} ❌{stats['error']}")
        
        # Run with thread pool
        log(f"🚀 Starting with {args.workers} workers")
        start_time = time.time()
        
        if args.workers == 1:
            # Sequential (original behavior)
            for i, posting in enumerate(postings, 1):
                process_posting(i, posting)
                time.sleep(DELAY_BETWEEN_REQUESTS)
        else:
            # Parallel with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = []
                for i, posting in enumerate(postings, 1):
                    future = executor.submit(process_posting, i, posting)
                    futures.append(future)
                    # Small stagger to avoid thundering herd on startup
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                
                # Wait for all to complete
                for future in as_completed(futures):
                    try:
                        future.result()  # Raises exception if worker had one
                    except Exception as e:
                        log(f"❌ Worker exception: {e}")
        
        elapsed_total = time.time() - start_time
        rate = stats['processed'] / elapsed_total * 3600 if elapsed_total > 0 else 0
        
        # Final stats
        log("=" * 70)
        log("📊 FINAL RESULTS")
        log("=" * 70)
        log(f"Total processed: {stats['processed']} in {elapsed_total:.0f}s ({rate:.0f}/hour)")
        log(f"✅ Descriptions fetched: {stats['success']}")
        log(f"⏭️  External partner: {stats['external_partner']}")
        log(f"🗑️  Jobs removed: {stats['not_found']}")
        log(f"⚠️  Rate limited: {stats['rate_limited']}")
        log(f"❌ No description: {stats['no_description']}")
        log(f"❌ Errors: {stats['error']}")
        
        if args.dry_run:
            log("⚠️  DRY RUN - no changes made to database")
            
    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
