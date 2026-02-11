#!/usr/bin/env python3
"""
Scraper Health Check

Tests all scrapers against known "canary" URLs to detect site changes
before they cause nightly pipeline failures.

Run daily before nightly_fetch.sh to catch issues early.

Usage:
    python3 scripts/scraper_health_check.py           # Check all scrapers
    python3 scripts/scraper_health_check.py --quick   # Only test essential scrapers
    python3 scripts/scraper_health_check.py --fix     # Update canary URLs that changed

Author: Arden
Date: 2026-02-10
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection_raw, return_connection
from lib.scrapers import SCRAPER_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Canary URLs - known-good URLs for each scraper
# These should be stable job postings that won't expire quickly
# Updated from database on 2026-02-10
CANARY_URLS = {
    'jsonld_generic': {
        'url': 'https://www.kalaydo.de/jobs/16073703/?utm_id=ba',
        'min_chars': 500,
        'description': 'Kalaydo.de job posting with JSON-LD'
    },
    'persyjobs': {
        'url': 'https://www.persy.jobs/persy/l/job-i9lga-b',
        'min_chars': 500,
        'description': 'Persy.jobs posting (highest volume partner)'
    },
    'compleet': {
        'url': 'https://jobboard.compleet.com/?externalId=4713634883',
        'min_chars': 500,
        'description': 'Compleet via germanpersonnel API'
    },
    'interamt': {
        'url': 'https://www.interamt.de/koop/app/stelle?id=1409810',
        'min_chars': 500,
        'description': 'Interamt.de public sector'
    },
    'helixjobs': {
        'url': 'https://helixjobs.com/_/jobad?prj=157p99043&source=ba',
        'min_chars': 500,
        'description': 'HelixJobs STEM posting'
    },
    'article_generic': {
        'url': 'https://hokify.de/job/28776094?utm_source=arbeitsagentur',
        'min_chars': 500,
        'description': 'Hokify.de via article/main extraction'
    },
    'jobware': {
        'url': 'https://www.jobware.de/job/060495217?jw_chl_seg=ARBEITSAGENTUR',
        'min_chars': 500,
        'description': 'Jobware.de Angular SPA'
    },
    'bewerbungjobs': {
        'url': 'https://bewerbung.jobs/bf6cab2d-5fcc-444b-af58-fb410b1db4ae',
        'min_chars': 500,
        'description': 'Bewerbung.jobs HTML extraction'
    },
    'jobfish': {
        'url': 'https://www.job.fish/heyrecruit/92152_17623_69700d27d1e01',
        'min_chars': 500,
        'description': 'Job.fish (Cloudflare protected)'
    },
}


def get_canary_urls_from_db(conn) -> Dict[str, dict]:
    """
    Load canary URLs from owl table (owl_type='scraper_canary').
    Falls back to hardcoded CANARY_URLS if not in DB.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_name, metadata
        FROM owl
        WHERE owl_type = 'scraper_canary'
          AND metadata->>'url' IS NOT NULL
    """)
    
    db_canaries = {}
    for row in cur.fetchall():
        name = row['canonical_name']
        meta = row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata'])
        db_canaries[name] = meta
    
    # Merge with hardcoded (DB takes precedence)
    result = CANARY_URLS.copy()
    result.update(db_canaries)
    return result


def check_scraper(scraper_name: str, canary: dict, timeout: int = 30) -> dict:
    """
    Test a single scraper against its canary URL.
    
    Returns:
        dict with: success, chars, error, latency_ms
    """
    url = canary.get('url')
    min_chars = canary.get('min_chars', 100)
    
    if not url:
        return {'success': False, 'error': 'No canary URL configured', 'chars': 0, 'latency_ms': 0}
    
    if scraper_name not in SCRAPER_REGISTRY:
        return {'success': False, 'error': f'Scraper {scraper_name} not in registry', 'chars': 0, 'latency_ms': 0}
    
    scraper_class = SCRAPER_REGISTRY[scraper_name]
    
    try:
        # Instantiate scraper (handle both signatures)
        try:
            scraper = scraper_class(config={}, db_conn=None)
        except TypeError:
            scraper = scraper_class()
        
        # Time the scrape
        start = datetime.now()
        result = scraper.scrape(url)
        latency_ms = (datetime.now() - start).total_seconds() * 1000
        
        if not result.get('success'):
            return {
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'chars': 0,
                'latency_ms': latency_ms
            }
        
        description = result.get('description', '')
        chars = len(description)
        
        if chars < min_chars:
            return {
                'success': False,
                'error': f'Too short: {chars} chars (need {min_chars})',
                'chars': chars,
                'latency_ms': latency_ms
            }
        
        return {
            'success': True,
            'chars': chars,
            'latency_ms': latency_ms,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'chars': 0,
            'latency_ms': 0
        }


def run_health_checks(quick: bool = False) -> List[dict]:
    """
    Run health checks on all (or essential) scrapers.
    
    Args:
        quick: If True, only test high-volume scrapers
        
    Returns:
        List of results with scraper name and status
    """
    conn = get_connection_raw()
    try:
        canaries = get_canary_urls_from_db(conn)
    finally:
        return_connection(conn)
    
    # Essential scrapers for quick mode (highest volume)
    essential = {'jsonld_generic', 'persyjobs', 'compleet', 'helixjobs'}
    
    results = []
    for scraper_name in SCRAPER_REGISTRY.keys():
        if quick and scraper_name not in essential:
            continue
            
        canary = canaries.get(scraper_name, {})
        if not canary.get('url'):
            results.append({
                'scraper': scraper_name,
                'success': None,  # Unknown - no canary
                'error': 'No canary URL',
                'chars': 0,
                'latency_ms': 0
            })
            continue
        
        logger.info(f"Testing {scraper_name}...")
        result = check_scraper(scraper_name, canary)
        result['scraper'] = scraper_name
        results.append(result)
        
        if result['success']:
            logger.info(f"  ✅ {scraper_name}: {result['chars']} chars in {result['latency_ms']:.0f}ms")
        else:
            logger.error(f"  ❌ {scraper_name}: {result['error']}")
    
    return results


def save_canary_url(conn, scraper_name: str, url: str, min_chars: int = 500, description: str = ''):
    """Save a canary URL to the database."""
    cur = conn.cursor()
    
    metadata = {
        'url': url,
        'min_chars': min_chars,
        'description': description,
        'updated_at': datetime.now().isoformat()
    }
    
    # Upsert
    cur.execute("""
        INSERT INTO owl (owl_type, canonical_name, metadata, description, created_at)
        VALUES ('scraper_canary', %s, %s, %s, NOW())
        ON CONFLICT (owl_type, canonical_name) DO UPDATE
        SET metadata = EXCLUDED.metadata, description = EXCLUDED.description
    """, (scraper_name, json.dumps(metadata), description))
    conn.commit()
    logger.info(f"Saved canary URL for {scraper_name}")


def main():
    parser = argparse.ArgumentParser(description='Check scraper health with canary URLs')
    parser.add_argument('--quick', action='store_true', help='Only test essential scrapers')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--save-canaries', action='store_true', help='Save hardcoded canaries to DB')
    args = parser.parse_args()
    
    if args.save_canaries:
        conn = get_connection_raw()
        try:
            for name, canary in CANARY_URLS.items():
                save_canary_url(conn, name, canary['url'], canary.get('min_chars', 500), canary.get('description', ''))
            logger.info(f"Saved {len(CANARY_URLS)} canary URLs to database")
        finally:
            return_connection(conn)
        return 0
    
    logger.info("=" * 60)
    logger.info("SCRAPER HEALTH CHECK")
    logger.info("=" * 60)
    
    results = run_health_checks(quick=args.quick)
    
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    
    # Summary
    passed = sum(1 for r in results if r['success'] is True)
    failed = sum(1 for r in results if r['success'] is False)
    unknown = sum(1 for r in results if r['success'] is None)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  ✅ Passed:  {passed}")
    logger.info(f"  ❌ Failed:  {failed}")
    logger.info(f"  ⚪ Unknown: {unknown} (no canary URL)")
    
    if failed > 0:
        logger.error("")
        logger.error("FAILED SCRAPERS:")
        for r in results:
            if r['success'] is False:
                logger.error(f"  - {r['scraper']}: {r['error']}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
