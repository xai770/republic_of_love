#!/usr/bin/env python3
"""
Postings Job Description Update - Re-scrape missing job descriptions

PURPOSE:
Re-fetches job descriptions from source websites for postings where
job_description is NULL. Currently supports arbeitsagentur.de.
This actor exists because the initial bulk fetch may have failed to
scrape descriptions due to rate limiting or network issues.

PREREQUISITE: None (works on postings that exist but lack descriptions)

Input:  postings.posting_id (via work_query where job_description IS NULL)
Output: postings.job_description

Output Fields:
    - success: bool - Whether description was fetched
    - description_length: int - Length of fetched description
    - skip_reason: str - Why skipped (if applicable)
    - error: str - Error message if failed

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Has external_url?}
    B -->|No| Z1[⏭️ SKIP: NO_URL]
    B -->|Yes| C{Supported source?}
    C -->|No| Z2[⏭️ SKIP: UNSUPPORTED_SOURCE]
    C -->|Yes| D[🌐 Fetch HTML page]
    D --> E{HTTP 200?}
    E -->|No| Z3[❌ FAIL: HTTP error]
    E -->|Yes| F[🔍 Parse description]
    F --> G{Found description?}
    G -->|No| Z4[❌ FAIL: NO_DESCRIPTION_FOUND]
    G -->|Yes| H{Length > 100?}
    H -->|No| Z5[❌ FAIL: DESCRIPTION_TOO_SHORT]
    H -->|Yes| I[💾 Save to postings]
    I --> J[✅ SUCCESS]
```

PIPELINE POSITION:
This is a remediation actor - fills gaps in the posting pipeline.
```
[API fetch] → job_description (THIS ACTOR fills gaps) → extracted_summary → embeddings
```

RAQ Config:
- state_tables: postings.job_description
- compare_output_field: output->>'description_length'

Usage:
    # Via pull_daemon (recommended):
    # Enable task_type, daemon will find work via work_query
    
    # Direct test:
    ./tools/turing/turing-harness run postings__job_description_U --input '{"posting_id": 20417}'
    
    # Standalone:
    python3 actors/postings__job_description_U.py 20417

Author: Arden
Date: 2026-01-27
Task Type ID: TBD (create in task_types table)
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import psycopg2
import psycopg2.extras

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent

from core.database import get_connection, get_connection_raw, return_connection
from lib.scrapers.arbeitsagentur import ArbeitsagenturScraper
from lib.scrapers.base import BaseScraper

from core.logging_config import get_logger
logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
ACTOR_ID = 1299  # job_description_backfill
TASK_TYPE_ID = 1299  # job_description_backfill

# Scraping settings
MIN_DESCRIPTION_LENGTH = 100

# Rate limit handling
CONSECUTIVE_403_THRESHOLD = 3  # Pause after this many 403s in a row
RATE_LIMIT_PAUSE_SECONDS = 30   # Shorter pause - VPN rotation gives new IP
MAX_RATE_LIMIT_RETRIES = 10    # More retries - ProtonVPN has many IPs

# VPN script location (OpenVPN via vpn.sh)
VPN_SCRIPT = PROJECT_ROOT / "scripts" / "vpn.sh"

# Supported sources for this actor (AA-native postings only)
# External partner sites are handled by postings__external_description_U.py
SUPPORTED_SOURCES = {'arbeitsagentur'}

def _get_source_for_url(url: str) -> str:
    """Determine the actual source based on URL, not the source column."""
    if 'arbeitsagentur.de/jobsuche/jobdetail/' in url:
        return 'arbeitsagentur'
    # External job boards that AA links to - we can't scrape these (yet)
    # Return None to indicate unsupported
    return None


def _rotate_vpn() -> bool:
    """
    Rotate VPN via vpn.sh rotate (OpenVPN to ProtonVPN German servers).
    
    ProtonVPN's de config load-balances across German servers.
    Each reconnect gets a new IP address.
    
    Returns True on success, False on failure.
    """
    import subprocess
    
    if not VPN_SCRIPT.exists():
        logger.warning("VPN script not found - cannot rotate")
        return False
    
    logger.info("ROTATING VPN (reconnect for new IP)")
    
    try:
        result = subprocess.run(
            ["bash", str(VPN_SCRIPT), "rotate"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            logger.info("VPN rotated - new IP")
            return True
        else:
            logger.warning("VPN rotation failed: %s", result.stderr[:100])
            return False
    except subprocess.TimeoutExpired:
        logger.warning("VPN rotation timed out")
        return False
    except Exception as e:
        logger.error("VPN rotation error: %s", e)
        return False


# ============================================================================
# ACTOR CLASS
# ============================================================================
class PostingsJobDescriptionU:
    """
    Re-scrape job descriptions for postings where job_description is NULL.
    
    Three-Phase Structure (Directive #13 - Belt & Suspenders):
    1. PREFLIGHT: Validate posting exists and has external_url
    2. PROCESS: Fetch HTML and extract description
    3. QA: Validate description length and content
    
    Uses ArbeitsagenturScraper (lib/scrapers/) for AA's SPA pages.
    Browser lifecycle managed by BaseScraper — no inline Playwright.
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection_raw()
            self._owns_connection = True
        self.input_data: Dict[str, Any] = {}
        self._scraper = ArbeitsagenturScraper(db_conn=db_conn)
    
    def __del__(self):
        if self._owns_connection and self.conn:
            return_connection(self.conn)
    
    @classmethod
    def _close_browser(cls):
        """Clean up browser resources (call at end of batch processing)."""
        BaseScraper.cleanup()
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Called by pull_daemon.
        
        Returns:
            Dict with success status and description info
        """
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        
        if not posting_id:
            return {'success': False, 'error': 'No posting_id in input'}
        
        try:
            # ----------------------------------------------------------------
            # PHASE 1: PREFLIGHT
            # ----------------------------------------------------------------
            preflight = self._preflight(posting_id)
            if not preflight['ok']:
                return {
                    'success': False,
                    'skip_reason': preflight['reason'],
                    'error': preflight.get('message', preflight['reason']),
                    'posting_id': posting_id,
                }
            
            posting = preflight['data']
            source = posting.get('actual_source', posting['source'])
            external_url = posting['external_url']
            
            # ----------------------------------------------------------------
            # PHASE 2: PROCESS - Fetch and parse
            # ----------------------------------------------------------------
            result = self._fetch_description(source, external_url)
            
            if not result['success']:
                error = result.get('error', 'Fetch failed')
                http_status = result.get('http_status')
                
                # Handle terminal failures (don't retry these)
                if result.get('skip_external') or 'EXTERNAL_PARTNER' in error:
                    # External partner redirect - description not on AA
                    # Set job_description to marker so we don't keep retrying
                    self._set_external_marker(posting_id)
                    return {
                        'success': False,
                        'error': 'EXTERNAL_PARTNER',
                        'skip_reason': 'EXTERNAL_PARTNER',
                        'posting_id': posting_id,
                    }
                elif http_status == 404:
                    # Job removed from AA - invalidate the posting
                    self._invalidate_posting(posting_id, 'Job removed from AA (404)')
                    return {
                        'success': False,
                        'error': 'Job removed (404)',
                        'http_status': 404,
                        'posting_id': posting_id,
                    }
                else:
                    # Transient failure - increment counter for retry backoff
                    self._increment_failures(posting_id)
                    return {
                        'success': False,
                        'error': error,
                        'http_status': http_status,
                        'posting_id': posting_id,
                    }
            
            description = result['description']
            
            # ----------------------------------------------------------------
            # PHASE 3: QA - Validate description
            # ----------------------------------------------------------------
            if len(description) < MIN_DESCRIPTION_LENGTH:
                self._increment_failures(posting_id)
                return {
                    'success': False,
                    'error': f'Description too short ({len(description)} chars)',
                    'posting_id': posting_id,
                }
            
            # ----------------------------------------------------------------
            # SAVE
            # ----------------------------------------------------------------
            self._save_description(posting_id, description)
            
            return {
                'success': True,
                '_consistency': '1/1',
                'posting_id': posting_id,
                'description_length': len(description),
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'posting_id': posting_id,
            }
    
    # ========================================================================
    # PHASE 1: PREFLIGHT
    # ========================================================================
    
    def _preflight(self, posting_id: int) -> Dict:
        """Validate posting exists and has required fields."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT posting_id, source, external_url, job_description, processing_failures
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        posting = cur.fetchone()
        
        if not posting:
            return {'ok': False, 'reason': 'NOT_FOUND', 'message': f'Posting {posting_id} not found'}
        
        # Already has sufficient description - skip (idempotency)
        # Match work_query threshold: only process if NULL or < MIN_DESCRIPTION_LENGTH
        desc = posting['job_description'] or ''
        if len(desc) >= MIN_DESCRIPTION_LENGTH:
            return {'ok': False, 'reason': 'ALREADY_HAS_DESCRIPTION', 'message': f'Posting already has description ({len(desc)} chars)'}
        
        if not posting['external_url']:
            return {'ok': False, 'reason': 'NO_URL', 'message': 'Posting has no external_url'}
        
        # Determine actual source from URL (AA links to external job boards)
        actual_source = _get_source_for_url(posting['external_url'])
        if not actual_source:
            # URL points to external job board - mark and skip
            self._set_external_marker(posting_id)
            return {
                'ok': False, 
                'reason': 'EXTERNAL_JOB_BOARD', 
                'message': f"URL points to external job board, not scrapeable: {posting['external_url'][:50]}..."
            }
        
        if actual_source not in SUPPORTED_SOURCES:
            return {'ok': False, 'reason': 'UNSUPPORTED_SOURCE', 'message': f'Source {actual_source} not supported'}
        
        # Override source with actual source for fetching
        posting = dict(posting)  # Make mutable copy
        posting['actual_source'] = actual_source
        
        # Check failure count - skip if too many failures
        if (posting.get('processing_failures') or 0) >= 3:
            return {'ok': False, 'reason': 'TOO_MANY_FAILURES', 'message': 'Posting has failed 3+ times'}
        
        return {'ok': True, 'data': posting}
    
    # ========================================================================
    # PHASE 2: PROCESS
    # ========================================================================
    
    def _fetch_description(self, source: str, url: str) -> Dict:
        """
        Fetch and parse job description from source website.
        
        Delegates to ArbeitsagenturScraper (lib/scrapers/) which handles
        Playwright lifecycle, SPA hydration, and external partner detection.
        """
        if source != 'arbeitsagentur':
            return {'success': False, 'error': f'Unsupported source: {source}'}
        
        result = self._scraper.fetch_description(url)
        
        # Convert ScraperResult to the dict format the actor expects
        if result.success:
            return {
                'success': True,
                'description': result.description,
            }
        
        # Map scraper metadata to actor-level fields
        meta = result.metadata or {}
        out = {
            'success': False,
            'error': result.error or 'Fetch failed',
        }
        
        if meta.get('http_status'):
            out['http_status'] = meta['http_status']
        
        if meta.get('is_external_partner'):
            out['skip_external'] = True
            out['error'] = 'EXTERNAL_PARTNER'
        
        return out
    
    # ========================================================================
    # SAVE
    # ========================================================================
    
    def _save_description(self, posting_id: int, description: str):
        """Save description to postings table."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET job_description = %s,
                updated_at = NOW()
            WHERE posting_id = %s
        """, (description, posting_id))
        self.conn.commit()
    
    def _increment_failures(self, posting_id: int):
        """Increment processing_failures counter on posting."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET processing_failures = COALESCE(processing_failures, 0) + 1,
                updated_at = NOW()
            WHERE posting_id = %s
        """, (posting_id,))
        self.conn.commit()
    
    def _invalidate_posting(self, posting_id: int, reason: str):
        """Mark posting as invalidated (job removed from source)."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET invalidated = true,
                invalidated_reason = %s,
                invalidated_at = NOW(),
                updated_at = NOW()
            WHERE posting_id = %s
        """, (reason, posting_id))
        self.conn.commit()
    
    def _set_external_marker(self, posting_id: int):
        """
        Mark posting as having external description (not on AA).
        
        Sets job_description to a marker value so we don't keep retrying.
        These postings have descriptions on external job boards that we can't scrape.
        """
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE postings
            SET job_description = '[EXTERNAL_PARTNER]',
                updated_at = NOW()
            WHERE posting_id = %s
        """, (posting_id,))
        self.conn.commit()


# ============================================================================
# STANDALONE ENTRY POINT
# ============================================================================
def main():
    """
    Test the actor directly.
    
    Usage:
        python3 actors/postings__job_description_U.py              # random subject
        python3 actors/postings__job_description_U.py 20417        # specific posting_id
        python3 actors/postings__job_description_U.py --batch 100  # process batch
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-scrape job descriptions for AA postings')
    parser.add_argument('posting_id', nargs='?', type=int, help='Posting ID to process')
    parser.add_argument('--batch', type=int, default=0, help='Process N postings (creates tickets)')
    args = parser.parse_args()
    
    with get_connection() as conn:
        actor = PostingsJobDescriptionU(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if args.posting_id:
            # Single posting mode
            actor.input_data = {'posting_id': args.posting_id}
            result = actor.process()
            logger.info("Result: %s", json.dumps(result, indent=2))
        
        elif args.batch > 0:
            # Batch mode - find work and process (only AA-hosted URLs)
            # Order by DESC to get newest (most likely to still exist) first
            # Also skip already invalidated postings
            cur.execute("""
                SELECT posting_id FROM postings 
                WHERE source = 'arbeitsagentur'
                  AND job_description IS NULL
                  AND external_url LIKE '%%arbeitsagentur.de/jobsuche/jobdetail/%%'
                  AND COALESCE(processing_failures, 0) < 3
                  AND COALESCE(invalidated, false) = false
                ORDER BY posting_id DESC
                LIMIT %s
            """, (args.batch,))
            
            rows = cur.fetchall()
            if not rows:
                logger.info("No postings need description scraping")
                return
            
            logger.info("Processing %s postings...", len(rows))
            success = 0
            failed = 0
            skipped = 0
            invalidated = 0
            
            # Rate limit tracking
            consecutive_403s = 0
            vpn_rotation_count = 0
            
            for i, row in enumerate(rows, 1):
                actor.input_data = {'posting_id': row['posting_id']}
                result = actor.process()
                
                http_status = result.get('http_status')
                
                # ============================================================
                # HANDLE 404: Job removed from AA - invalidate and continue
                # ============================================================
                if http_status == 404:
                    actor._invalidate_posting(row['posting_id'], 'HTTP 404 - Job removed from Arbeitsagentur')
                    invalidated += 1
                    consecutive_403s = 0  # Reset 403 counter on non-403
                    logger.info("[%s/%s]%s: INVALIDATED (job removed)", i, len(rows), row['posting_id'])
                    time.sleep(0.2)
                    continue
                
                # ============================================================
                # HANDLE 403: Rate limited - pause, retry, rotate VPN
                # ============================================================
                if http_status == 403:
                    consecutive_403s += 1
                    logger.warning("[%s/%s]%s: 403 Forbidden (%s/%s)", i, len(rows), row['posting_id'], consecutive_403s, CONSECUTIVE_403_THRESHOLD)
                    
                    if consecutive_403s >= CONSECUTIVE_403_THRESHOLD:
                        logger.error("RATE LIMIT HIT -%s consecutive 403s", consecutive_403s)
                        
                        # Rotate VPN and retry
                        vpn_rotation_count += 1
                        if vpn_rotation_count > MAX_RATE_LIMIT_RETRIES:
                            # ================================================
                            # FAIL LOUD - all retries exhausted
                            # ================================================
                            logger.info("=" * 60)
                            logger.error("FATAL: RATE LIMIT PERSISTS AFTER ALL VPN ROTATIONS")
                            logger.info("Rotated through %s VPN endpoints", vpn_rotation_count - 1)
                            logger.info("Still getting 403 Forbidden from AA")
                            logger.info("Stats: %s success,%s invalidated,%s failed", success, invalidated, failed)
                            logger.info("=" * 60)
                            sys.exit(1)
                        
                        # Pause then rotate VPN
                        logger.info("Pausing %s s before VPN rotation #%s...", RATE_LIMIT_PAUSE_SECONDS, vpn_rotation_count)
                        time.sleep(RATE_LIMIT_PAUSE_SECONDS)
                        
                        _rotate_vpn()
                        consecutive_403s = 0  # Reset counter after VPN change
                        
                        # Retry current posting
                        logger.info("Retrying posting %s...", row['posting_id'])
                        i -= 1  # Will re-process this posting
                    else:
                        failed += 1
                    time.sleep(1)  # Brief pause even on single 403
                    continue
                
                # ============================================================
                # NORMAL PROCESSING
                # ============================================================
                consecutive_403s = 0  # Reset on any non-403 response
                
                if result.get('success'):
                    success += 1
                    logger.info("[%s/%s]%s: %s chars", i, len(rows), row['posting_id'], result.get('description_length'))
                elif result.get('skip_reason'):
                    skipped += 1
                    logger.info("[%s/%s]%s: %s", i, len(rows), row['posting_id'], result.get('skip_reason'))
                else:
                    failed += 1
                    logger.error("[%s/%s]%s: %s", i, len(rows), row['posting_id'], result.get('error'))
                
                # Rate limit - be nice to the server
                time.sleep(0.2)
            
            logger.info("\nDone: %s success,%s invalidated,%s skipped,%s failed", success, invalidated, skipped, failed)
        
        else:
            # Find a random test subject
            cur.execute("""
                SELECT posting_id FROM postings 
                WHERE source = 'arbeitsagentur'
                  AND job_description IS NULL
                  AND external_url IS NOT NULL
                LIMIT 1
            """)
            row = cur.fetchone()
            
            if row:
                actor.input_data = {'posting_id': row['posting_id']}
                result = actor.process()
                logger.info("Result for posting %s:", row['posting_id'])
                logger.info("%s", json.dumps(result, indent=2))
            else:
                logger.info("No postings need description scraping")


if __name__ == '__main__':
    main()
