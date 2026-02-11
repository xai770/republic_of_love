#!/usr/bin/env python3
"""
postings__external_description_U.py - Fetch Descriptions from External Job Sites

Actor type: Update (U)
Table: postings
Sources: jobvector.de, stepstone.de, etc. (via AA partner prefixes)

PURPOSE:
Fetches job descriptions for postings that AA redirects to external partner sites.
These are jobs where AA shows a 404 on the detail page because the content lives
on the partner's website (jobvector, stepstone, etc.).

Identification:
- AA job IDs like 12288-*, 18024-*, 13319-* are external partner jobs
- Native AA jobs (10001-*) and some partners (13092-*) have descriptions on AA
- This actor handles jobs where AA has NO description

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting with NULL description] --> B{External partner prefix?}
    B -->|No| Z1[⏭️ SKIP: Not external partner]
    B -->|Yes| C{Site config in owl?}
    C -->|No| Z2[⏭️ SKIP: Unknown site]
    C -->|Yes| D{Scrapeable?}
    D -->|No| Z3[⏭️ SKIP: Site not scrapeable]
    D -->|Yes| E{URL known?}
    E -->|No| Z4[⏭️ SKIP: No URL mapping]
    E -->|Yes| F[🔄 Scrape external site]
    F --> G{Success?}
    G -->|No| Z5[❌ FAIL: Scrape error]
    G -->|Yes| H[💾 Update job_description]
    H --> I[✅ SUCCESS]
```

Configuration:
- owl.external_job_site: Site configs with scraper settings
- owl.external_job_url_mapping: AA job ID → external URL mapping

Usage:
    python3 actors/postings__external_description_U.py --dry-run
    python3 actors/postings__external_description_U.py --limit 10 --prefix 12288
    python3 actors/postings__external_description_U.py --stats

Author: Arden (scaffolded)
Date: 2026-02-07
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection_raw, return_connection
from lib.scrapers import get_scraper, list_scrapers, SCRAPER_REGISTRY
from lib.scrapers.base import BaseScraper, ScraperResult

# ============================================================================
# LOGGING
# ============================================================================
def log(msg: str):
    """Print timestamped message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


# ============================================================================
# PREFIX ANALYSIS
# ============================================================================
def get_external_prefix_stats(conn) -> list:
    """
    Get stats on NULL description postings by AA prefix.
    
    Returns list of tuples: (prefix, count, sample_job_id) for non-native jobs.
    """
    query = """
        SELECT 
            split_part(external_id, '-', 2) AS prefix,
            COUNT(*) AS cnt,
            MIN(external_id) AS sample_id
        FROM postings
        WHERE source = 'arbeitsagentur'
          AND job_description IS NULL
          AND invalidated_at IS NULL
          AND external_id NOT LIKE 'aa-10001-%%'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 30
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        # Ensure we return list of tuples (handle both tuple and dict cursors)
        if rows and hasattr(rows[0], 'keys'):
            return [(r['prefix'], r['cnt'], r['sample_id']) for r in rows]
        return rows


def get_site_config(conn, prefix: str) -> Optional[dict]:
    """
    Get scraper config for a prefix from owl.
    
    Returns:
        dict with scraper name and metadata, or None if not configured
    """
    query = """
        SELECT canonical_name, metadata
        FROM owl 
        WHERE owl_type = 'external_job_site' 
          AND metadata->>'aa_prefix' = %s
          AND status = 'active'
    """
    with conn.cursor() as cur:
        cur.execute(query, (prefix,))
        row = cur.fetchone()
        if row:
            return {
                'scraper': row['canonical_name'],
                'config': row['metadata'] or {}
            }
    return None


def get_external_url(conn, posting_id: int, aa_job_id: str) -> Optional[str]:
    """
    Try to find the external URL for a posting.
    
    Checks:
    1. postings.external_url (if it's not an AA URL)
    2. owl.external_job_url_mapping
    """
    # Check postings table first
    with conn.cursor() as cur:
        cur.execute(
            "SELECT external_url FROM postings WHERE posting_id = %s",
            (posting_id,)
        )
        row = cur.fetchone()
        if row and row['external_url'] and 'arbeitsagentur.de' not in row['external_url']:
            return row['external_url']
    
    # Check owl mapping
    with conn.cursor() as cur:
        cur.execute("""
            SELECT metadata->>'external_url' AS ext_url
            FROM owl 
            WHERE owl_type = 'external_job_url_mapping'
              AND canonical_name = %s
              AND status = 'active'
        """, (aa_job_id,))
        row = cur.fetchone()
        if row and row['ext_url']:
            return row['ext_url']
    
    return None


# ============================================================================
# MAIN PROCESSING
# ============================================================================
def get_postings_to_process(conn, limit: int = None, prefix: str = None) -> list:
    """
    Get external partner postings that need description backfill.
    
    Args:
        conn: Database connection
        limit: Max postings to return
        prefix: Filter to specific AA prefix (e.g., '12288')
    """
    query = """
        SELECT 
            posting_id, 
            external_id,
            external_url,
            split_part(external_id, '-', 2) AS prefix
        FROM postings
        WHERE source = 'arbeitsagentur'
          AND job_description IS NULL
          AND invalidated_at IS NULL
          AND external_id NOT LIKE 'aa-10001-%%'
    """
    params = []
    
    if prefix:
        query += " AND external_id LIKE %s"
        params.append(f'aa-{prefix}-%')
    
    query += " ORDER BY first_seen_at DESC NULLS LAST"
    
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def update_description(conn, posting_id: int, description: str, metadata: dict = None) -> bool:
    """Update job description for a posting."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE postings 
                SET job_description = %s,
                    source_metadata = COALESCE(source_metadata, '{}'::jsonb) || %s::jsonb,
                    updated_at = NOW()
                WHERE posting_id = %s
            """, (
                description,
                psycopg2.extras.Json({
                    'external_scrape_at': datetime.now().isoformat(),
                    'external_scrape_metadata': metadata or {}
                }),
                posting_id
            ))
            conn.commit()
            return True
    except Exception as e:
        log(f"❌ DB update failed for posting {posting_id}: {e}")
        conn.rollback()
        return False


def process_posting(conn, posting: dict, dry_run: bool = False) -> dict:
    """
    Process a single posting - fetch description from external site.
    
    Returns:
        dict with keys: success, reason, posting_id
    """
    posting_id = posting['posting_id']
    external_id = posting['external_id']
    prefix = posting['prefix']
    aa_job_id = external_id.replace('aa-', '')  # e.g., '12288-4694816142-S'
    
    result = {
        'posting_id': posting_id,
        'prefix': prefix,
        'success': False,
        'reason': None
    }
    
    # 1. Check if we have site config
    site_config = get_site_config(conn, prefix)
    if not site_config:
        result['reason'] = 'UNKNOWN_SITE'
        return result
    
    # 2. Get scraper
    try:
        scraper = get_scraper(prefix, conn)
    except ValueError as e:
        result['reason'] = f'SCRAPER_ERROR: {e}'
        return result
    
    # 3. Check if scrapeable
    can_scrape, reason = scraper.can_scrape()
    if not can_scrape:
        result['reason'] = f'NOT_SCRAPEABLE: {reason}'
        return result
    
    # 4. Find external URL
    target_url = get_external_url(conn, posting_id, aa_job_id)
    if not target_url:
        # Try to build URL via scraper
        target_url = scraper.build_url(aa_job_id)
    
    if not target_url:
        result['reason'] = 'NO_URL_MAPPING'
        return result
    
    # 5. Dry run check
    if dry_run:
        result['success'] = True
        result['reason'] = f'DRY_RUN: Would scrape {target_url}'
        return result
    
    # 6. Scrape
    scrape_result = scraper.fetch_description(target_url)
    
    if not scrape_result.success:
        result['reason'] = f'SCRAPE_FAILED: {scrape_result.error}'
        return result
    
    # 7. Update database
    if update_description(conn, posting_id, scrape_result.description, scrape_result.metadata):
        result['success'] = True
        result['reason'] = 'SUCCESS'
    else:
        result['reason'] = 'DB_UPDATE_FAILED'
    
    return result


def run_stats(conn):
    """Show statistics on external partner jobs."""
    log("📊 External Partner Job Statistics")
    log("=" * 60)
    
    stats = get_external_prefix_stats(conn)
    
    total_null = sum(s[1] for s in stats)
    log(f"Total NULL descriptions (non-native): {total_null:,}")
    log("")
    log(f"{'Prefix':<10} {'Count':>8} {'Config?':>8} {'Scraper?':>10}")
    log("-" * 40)
    
    for prefix, count, sample_id in stats:
        site_config = get_site_config(conn, prefix)
        has_config = '✅' if site_config else '❌'
        has_scraper = '✅' if site_config and site_config['scraper'] in SCRAPER_REGISTRY else '❌'
        log(f"{prefix:<10} {count:>8,} {has_config:>8} {has_scraper:>10}")
    
    log("")
    log(f"Implemented scrapers: {', '.join(list_scrapers())}")


def run_batch(conn, limit: int, prefix: str = None, dry_run: bool = False):
    """Run batch processing."""
    postings = get_postings_to_process(conn, limit=limit, prefix=prefix)
    
    if not postings:
        log("No postings to process")
        return
    
    log(f"Processing {len(postings)} postings" + (" (DRY RUN)" if dry_run else ""))
    
    stats = {'success': 0, 'skipped': 0, 'failed': 0}
    by_reason = {}
    
    for i, posting in enumerate(postings, 1):
        result = process_posting(conn, posting, dry_run=dry_run)
        
        if result['success']:
            stats['success'] += 1
            status = '✅'
        elif 'SKIP' in str(result['reason']) or result['reason'] in ('UNKNOWN_SITE', 'NO_URL_MAPPING', 'NOT_SCRAPEABLE'):
            stats['skipped'] += 1
            status = '⏭️'
        else:
            stats['failed'] += 1
            status = '❌'
        
        reason_key = result['reason'].split(':')[0] if result['reason'] else 'UNKNOWN'
        by_reason[reason_key] = by_reason.get(reason_key, 0) + 1
        
        if i % 10 == 0 or i == len(postings):
            log(f"Progress: {i}/{len(postings)} - ✅ {stats['success']} | ⏭️ {stats['skipped']} | ❌ {stats['failed']}")
    
    log("")
    log("Results by reason:")
    for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
        log(f"  {reason}: {count}")
    
    # Cleanup Playwright
    BaseScraper.cleanup()


# ============================================================================
# CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description='Fetch descriptions from external job sites')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t update database')
    parser.add_argument('--limit', type=int, default=10, help='Max postings to process')
    parser.add_argument('--prefix', type=str, help='Filter to specific AA prefix (e.g., 12288)')
    args = parser.parse_args()
    
    conn = get_connection_raw()
    
    try:
        if args.stats:
            run_stats(conn)
        else:
            run_batch(conn, limit=args.limit, prefix=args.prefix, dry_run=args.dry_run)
    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
