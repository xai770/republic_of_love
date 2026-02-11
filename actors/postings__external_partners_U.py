#!/usr/bin/env python3
"""
External Partner Job Description Scraper

PURPOSE:
Fetches job descriptions from external partner sites (jobvector.de, etc.)
for postings where job_description = '[EXTERNAL_PARTNER]'.

These are jobs that AA has indexed from partner sites but can't provide
descriptions for - we need to scrape the partner site directly.

PREREQUISITE: postings__aa_backfill_U.py marks them as '[EXTERNAL_PARTNER]'

Input:  postings.posting_id (where job_description = '[EXTERNAL_PARTNER]')
Output: postings.job_description (scraped from partner site)

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting with EXTERNAL_PARTNER] --> B{Has external_url?}
    B -->|No| Z1[⏭️ SKIP: NO_URL]
    B -->|Yes| C[🔍 Extract AA prefix]
    C --> D{Scraper available?}
    D -->|No| Z2[⏭️ SKIP: NO_SCRAPER]
    D -->|Yes| E[🌐 Scrape partner site]
    E --> F{Success?}
    F -->|No| Z3[❌ FAIL: Scrape error]
    F -->|Yes| G{Length > 100?}
    G -->|No| Z4[❌ FAIL: TOO_SHORT]
    G -->|Yes| H[💾 Update job_description]
    H --> I[✅ SUCCESS]
```

PIPELINE POSITION:
Runs after postings__aa_backfill_U.py, before embeddings.
```
[AA API] → aa_backfill (marks EXTERNAL_PARTNER) → THIS ACTOR → embeddings
```

Supported Partners:
    - 12288: jobvector.de (STEM jobs)
    - (add more as scrapers are implemented)

Usage:
    # Process all external partner postings
    python3 actors/postings__external_partners_U.py --batch 100
    
    # Test with specific posting
    python3 actors/postings__external_partners_U.py --posting-id 13961
    
    # Dry run (don't save)
    python3 actors/postings__external_partners_U.py --batch 10 --dry-run

Author: Arden
Date: 2026-02-07
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import psycopg2
import psycopg2.extras
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.scrapers import get_scraper, SCRAPER_REGISTRY
from lib.scrapers.base import ScraperResult
from core.database import get_connection_raw, return_connection


def strip_html(text: str) -> str:
    """Strip HTML tags from text, preserving whitespace structure."""
    if not text or '<' not in text:
        return text
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator='\n', strip=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

MIN_DESCRIPTION_LENGTH = 100

# Rate limit between requests (ms)
REQUEST_DELAY_MS = 1000

# Logging - don't use basicConfig as it pollutes root logger when imported by daemon
logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE FUNCTIONS (use core.database for connections)
# ============================================================================


def get_external_partner_postings(
    conn, 
    limit: int = 100,
    posting_id: Optional[int] = None
) -> List[Dict]:
    """
    Get postings that need external partner scraping.
    
    Finds postings with:
    - job_description = '[EXTERNAL_PARTNER]' (marked by aa_backfill), or
    - NULL description with external URL (direct partner links)
    
    Args:
        conn: Database connection
        limit: Max postings to return
        posting_id: Specific posting to process (for testing)
        
    Returns:
        List of posting dicts with posting_id, external_id, external_url
    """
    with conn.cursor() as cur:
        if posting_id:
            cur.execute("""
                SELECT posting_id, external_id, external_url,
                       source_metadata->'raw_api_response'->>'externeUrl' as partner_url
                FROM postings
                WHERE posting_id = %s
            """, (posting_id,))
        else:
            # Find postings that need external scraping:
            # 1. Marked [EXTERNAL_PARTNER] by aa_backfill
            # 2. NULL description with direct partner URL (not AA jobdetail)
            # 3. NULL description with externeUrl in AA metadata (partner behind "Externe Seite" button)
            cur.execute("""
                SELECT posting_id, external_id, external_url,
                       source_metadata->'raw_api_response'->>'externeUrl' as partner_url
                FROM postings
                WHERE (
                    job_description = '[EXTERNAL_PARTNER]'
                    OR (
                        job_description IS NULL 
                        AND external_url IS NOT NULL
                        AND external_url NOT LIKE '%%arbeitsagentur.de/jobsuche/jobdetail/%%'
                    )
                    OR (
                        (job_description IS NULL OR LENGTH(COALESCE(job_description, '')) < 100)
                        AND source_metadata->'raw_api_response'->>'externeUrl' IS NOT NULL
                        AND source_metadata->'raw_api_response'->>'externeUrl' NOT LIKE '%%arbeitsagentur.de%%'
                    )
                )
                  AND COALESCE(invalidated, false) = false
                ORDER BY first_seen_at DESC
                LIMIT %s
            """, (limit,))
        
        return cur.fetchall()


def get_supported_prefixes(conn) -> Dict[str, str]:
    """
    Get mapping of AA prefix → scraper name from owl.
    
    Returns:
        Dict like {'12288': 'jobvector', '12345': 'stepstone'}
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT metadata->>'aa_prefix' as prefix, canonical_name
            FROM owl
            WHERE owl_type = 'external_job_site'
              AND status = 'active'
              AND metadata->>'aa_prefix' IS NOT NULL
        """)
        return {row['prefix']: row['canonical_name'] for row in cur.fetchall()}


def update_job_description(
    conn, 
    posting_id: int, 
    description: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Update posting with scraped description.
    
    Args:
        conn: Database connection
        posting_id: Posting to update
        description: Scraped job description
        metadata: Optional metadata from scraper (title, etc.)
        
    Returns:
        True if updated successfully
    """
    with conn.cursor() as cur:
        # Build update with optional metadata
        if metadata:
            cur.execute("""
                UPDATE postings 
                SET job_description = %s,
                    source_metadata = COALESCE(source_metadata, '{}'::jsonb) || %s,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (description, psycopg2.extras.Json(metadata), posting_id))
        else:
            cur.execute("""
                UPDATE postings 
                SET job_description = %s,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (description, posting_id))
        
        conn.commit()
        return cur.rowcount > 0


def extract_aa_prefix(external_id: str) -> Optional[str]:
    """
    Extract AA partner prefix from external_id.
    
    Format: aa-{prefix}-{id}-S
    
    Examples:
        'aa-12288-4694816142-S' → '12288'
        'aa-14225-9d57f4b023e5c822-S' → '14225'
        'aa-10001-1234567890-S' → '10001'  (native AA)
        
    Returns:
        Prefix string or None if invalid format
    """
    if not external_id:
        return None
    
    # Format: aa-{prefix}-{id}-S
    match = re.match(r'^aa-(\d+)-', external_id)
    return match.group(1) if match else None


def detect_scraper_from_url(external_url: str) -> Optional[str]:
    """
    Detect which scraper to use based on the external_url domain.
    
    Returns:
        Scraper name ('jobvector', 'stepstone', etc.) or None
    """
    if not external_url:
        return None
    
    url_lower = external_url.lower()
    
    if 'jobvector.de' in url_lower:
        return 'jobvector'
    if 'helixjobs.com' in url_lower:
        return 'helixjobs'
    if 'gute-jobs.de' in url_lower:
        return 'gutejobs'
    if 'jobboerse-direkt.de' in url_lower:
        return 'jobboersedirekt'
    if 'hogapage.de' in url_lower:
        return 'hogapage'
    if 'europersonal.com' in url_lower:
        return 'europersonal'
    if 'finest-jobs.com' in url_lower:
        return 'finestjobs'
    if 'persy.jobs' in url_lower:
        return 'persyjobs'
    if 'jobexport.de' in url_lower:
        return 'jobexport'
    
    # JSON-LD sites (use generic scraper)
    jsonld_domains = [
        'jobanzeiger.de',      # muenchner-, stuttgarter-, mannheimer-, etc.
        'jobblitz.de',
        'kalaydo.de',
        'regio-jobanzeiger.de',
        'yourfirm.de',
        'stellenanzeigen.de',
        'empfehlungsbund.de',
    ]
    for domain in jsonld_domains:
        if domain in url_lower:
            return 'jsonld_generic'
    
    # Playwright-required sites (SPA or Cloudflare)
    if 'germantechjobs.de' in url_lower:
        return 'playwright_jsonld'
    if 'job.fish' in url_lower:
        return 'jobfish'
    if 'jobware.de' in url_lower:
        return 'jobware'
    if 'bewerbung.jobs' in url_lower:
        return 'bewerbungjobs'
    if 'compleet.com' in url_lower:
        return 'compleet'
    if 'interamt.de' in url_lower:
        return 'interamt'
    
    # Article/main extraction sites (no JSON-LD)
    article_domains = [
        'hokify.de',
        'crabster.de',
        'awo-jobs.de',
        'jobs4us.de',
    ]
    for domain in article_domains:
        if domain in url_lower:
            return 'article_generic'
    
    if 'stepstone.de' in url_lower:
        return 'stepstone'
    if 'hays.de' in url_lower:
        return 'hays'
    
    return None


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_posting(
    conn,
    posting: Dict,
    supported_prefixes: Dict[str, str],
    dry_run: bool = False
) -> Tuple[str, Optional[str]]:
    """
    Process a single external partner posting.
    
    Args:
        conn: Database connection
        posting: Posting dict with posting_id, external_id, external_url
        supported_prefixes: Map of prefix → scraper name
        dry_run: If True, don't save to database
        
    Returns:
        Tuple of (status, error_message)
        Status: 'SUCCESS', 'SKIP_NO_URL', 'SKIP_NO_SCRAPER', 'FAIL_SCRAPE', 'FAIL_TOO_SHORT'
    """
    posting_id = posting['posting_id']
    external_id = posting['external_id']
    external_url = posting['external_url']
    partner_url = posting.get('partner_url')  # externeUrl from AA metadata
    
    # Use partner_url (from AA metadata) if external_url points to AA
    scrape_url = external_url
    if partner_url and (not external_url or 'arbeitsagentur.de/jobsuche/jobdetail/' in (external_url or '')):
        scrape_url = partner_url
        logger.info(f"  {posting_id}: Using partner URL: {partner_url[:80]}")
    
    # Check URL
    if not scrape_url:
        return 'SKIP_NO_URL', 'No external_url or partner_url'
    
    # Strategy 1: Detect scraper from URL domain (most reliable)
    scraper_name = detect_scraper_from_url(scrape_url)
    
    # Strategy 2: Fall back to prefix-based lookup
    if not scraper_name:
        prefix = extract_aa_prefix(external_id)
        if prefix and prefix in supported_prefixes:
            scraper_name = supported_prefixes[prefix]
    
    # Strategy 3: Auto-detect pattern for unknown domains
    # Try JSON-LD first (Google requires it), then article/main
    auto_detected = False
    auto_description = None
    if not scraper_name:
        for pattern in ['jsonld_generic', 'article_generic']:
            scraper_class = SCRAPER_REGISTRY.get(pattern)
            if scraper_class:
                test_scraper = scraper_class()
                try:
                    result = test_scraper.scrape(scrape_url)
                    if result.get('success') and len(result.get('description', '')) >= MIN_DESCRIPTION_LENGTH:
                        scraper_name = pattern
                        auto_detected = True
                        auto_description = result.get('description', '')
                        logger.info(f"  {posting_id}: Auto-detected pattern '{pattern}' for {scrape_url[:60]}")
                        break
                except Exception as e:
                    logger.debug(f"  {posting_id}: Pattern '{pattern}' failed: {e}")
                    continue
    
    if not scraper_name:
        return 'SKIP_NO_SCRAPER', f'No scraper for URL {scrape_url[:80]}'
    
    # Check if scraper is implemented
    if scraper_name not in SCRAPER_REGISTRY:
        return 'SKIP_NO_SCRAPER', f'Scraper {scraper_name} not implemented'
    
    # If auto-detected, we already have the description
    if auto_detected and auto_description:
        description = auto_description
        result_metadata = {'auto_detected': True}
    else:
        # Create scraper instance directly (no DB lookup needed for URL-detected scrapers)
        scraper_class = SCRAPER_REGISTRY[scraper_name]
        try:
            scraper = scraper_class(config={}, db_conn=conn)
        except TypeError:
            # Some scrapers (europersonal, finestjobs) don't accept config/db_conn
            scraper = scraper_class()
        
        # Scrape the partner site - all scrapers now have scrape() -> dict
        try:
            raw = scraper.scrape(scrape_url)
            if not raw.get('success'):
                return 'FAIL_SCRAPE', raw.get('error', 'Unknown scrape error')
            description = raw.get('description', '')
            result_metadata = raw.get('metadata')
        except Exception as e:
            return 'FAIL_SCRAPE', f'Scraper exception: {e}'
    
    # Strip HTML - external partner sites often include CSS/HTML bloat
    description = strip_html(description)
    
    # Validate length
    if not description or len(description) < MIN_DESCRIPTION_LENGTH:
        return 'FAIL_TOO_SHORT', f'Description only {len(description or "")} chars'
    
    # Save to database
    if not dry_run:
        metadata = result_metadata or {}
        metadata['scraped_by'] = scraper_name
        metadata['scraped_at'] = datetime.now().isoformat()
        
        success = update_job_description(conn, posting_id, description, metadata)
        if not success:
            return 'FAIL_DB', 'Database update failed'
    
    return 'SUCCESS', None


# ============================================================================
# PULL DAEMON ACTOR CLASS
# ============================================================================
# Wrapper class so core/pull_daemon.py can import and call process() per subject.

class PostingsExternalPartnersU:
    """Pull daemon-compatible wrapper for single-posting partner scraping."""

    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}

    def process(self) -> Dict:
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        if not posting_id:
            return {'success': False, 'error': 'No posting_id/subject_id'}

        conn = self.conn
        own_conn = False
        if conn is None:
            conn = get_connection_raw()
            own_conn = True

        try:
            # Fetch the posting
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT posting_id, external_id, external_url,
                       source_metadata->'raw_api_response'->>'externeUrl' AS partner_url
                FROM postings
                WHERE posting_id = %s
            """, (posting_id,))
            posting = cur.fetchone()

            if not posting:
                return {'success': False, 'skip_reason': 'posting_not_found'}

            supported_prefixes = get_supported_prefixes(conn)
            status, error = process_posting(conn, dict(posting), supported_prefixes)

            if status == 'SUCCESS':
                return {'success': True, 'posting_id': posting_id}
            elif status.startswith('SKIP'):
                return {'success': False, 'skip_reason': status, 'error': error}
            else:
                # Detect permanent failures (404/410 = job removed from partner site)
                error_str = str(error or '')
                if '404' in error_str or '410' in error_str:
                    # Invalidate the posting - job no longer exists
                    cur.execute("""
                        UPDATE postings SET posting_status = 'invalid', updated_at = NOW()
                        WHERE posting_id = %s
                    """, (posting_id,))
                    conn.commit()
                    return {'success': False, 'skip_reason': 'job_expired_invalidated', 'error': error_str}
                return {'success': False, 'error': f'{status}: {error}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if own_conn and conn:
                return_connection(conn)


def main():
    parser = argparse.ArgumentParser(
        description='Scrape job descriptions from external partner sites'
    )
    parser.add_argument('--batch', type=int, default=100, help='Number of postings to process')
    parser.add_argument('--posting-id', type=int, help='Process specific posting (for testing)')
    parser.add_argument('--dry-run', action='store_true', help="Don't save to database")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    conn = get_connection_raw()
    
    # Get supported scrapers
    supported_prefixes = get_supported_prefixes(conn)
    logger.info(f"Supported partner prefixes: {list(supported_prefixes.keys())}")
    
    if not supported_prefixes:
        logger.warning("No external_job_site entries found in owl. Add them first.")
        return 1
    
    # Get postings to process
    postings = get_external_partner_postings(conn, args.batch, args.posting_id)
    logger.info(f"Found {len(postings)} external partner postings to process")
    
    if not postings:
        logger.info("Nothing to do")
        return 0
    
    # Stats
    stats = {
        'SUCCESS': 0,
        'SKIP_NO_URL': 0,
        'SKIP_NO_SCRAPER': 0,
        'SKIP_INVALID_ID': 0,
        'FAIL_SCRAPE': 0,
        'FAIL_TOO_SHORT': 0,
        'FAIL_DB': 0,
    }
    
    start_time = time.time()
    
    for i, posting in enumerate(postings):
        posting_id = posting['posting_id']
        external_id = posting['external_id']
        
        # Rate limit
        if i > 0:
            time.sleep(REQUEST_DELAY_MS / 1000)
        
        status, error = process_posting(conn, posting, supported_prefixes, args.dry_run)
        stats[status] = stats.get(status, 0) + 1
        
        if status == 'SUCCESS':
            logger.info(f"[{i+1}/{len(postings)}] ✅ {posting_id} ({external_id})")
        elif status.startswith('SKIP'):
            logger.debug(f"[{i+1}/{len(postings)}] ⏭️  {posting_id}: {status} - {error}")
        else:
            logger.warning(f"[{i+1}/{len(postings)}] ❌ {posting_id}: {status} - {error}")
    
    elapsed = time.time() - start_time
    
    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Processed: {len(postings)} postings in {elapsed:.1f}s")
    logger.info(f"  SUCCESS:        {stats['SUCCESS']}")
    logger.info(f"  SKIP_NO_SCRAPER: {stats['SKIP_NO_SCRAPER']}")
    logger.info(f"  FAIL_SCRAPE:    {stats['FAIL_SCRAPE']}")
    logger.info(f"  FAIL_TOO_SHORT: {stats['FAIL_TOO_SHORT']}")
    
    if stats['SUCCESS'] > 0:
        rate = stats['SUCCESS'] / elapsed
        logger.info(f"Rate: {rate:.1f} descriptions/sec")
    
    return_connection(conn)
    return 0


if __name__ == '__main__':
    sys.exit(main())
