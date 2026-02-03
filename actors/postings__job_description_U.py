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
import requests
from bs4 import BeautifulSoup

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection

# ============================================================================
# CONFIGURATION
# ============================================================================
ACTOR_ID = None  # TODO: Set after registering in actors table
TASK_TYPE_ID = None  # TODO: Set after creating task_type

# Scraping settings
REQUEST_TIMEOUT = 30
MIN_DESCRIPTION_LENGTH = 100
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
MAX_FETCH_RETRIES = 3  # Exponential backoff: 1s, 2s, 4s
RETRY_BASE_DELAY = 1.0  # Base delay in seconds

# Rate limit handling
CONSECUTIVE_403_THRESHOLD = 3  # Pause after this many 403s in a row
RATE_LIMIT_PAUSE_SECONDS = 300  # 5 minute pause when rate limited
MAX_RATE_LIMIT_RETRIES = 3     # Try this many VPN rotations before giving up

# WireGuard configs - German endpoints for AA (prefer DE, fallback to others)
WIREGUARD_CONFIGS = [
    'wg-DE-13.conf', 'wg-DE-17.conf', 'wg-DE-190.conf', 'wg-DE-194.conf',
    'wg-DE-198.conf', 'wg-DE-222.conf', 'wg-DE-226.conf', 'wg-DE-232.conf',
    'wg-DE-236.conf', 'wg-DE-263.conf', 'wg-DE-363.conf', 'wg-DE-580.conf',
    'wg-DE-667.conf', 'wg-DE-680.conf', 'wg-DE-767.conf', 'wg-DE-780.conf',
]
WIREGUARD_CONFIG_DIR = PROJECT_ROOT / 'config'

# Source-specific selectors
SOURCE_SELECTORS = {
    'arbeitsagentur': {
        'url_pattern': 'arbeitsagentur.de/jobsuche/jobdetail/',
        'selector': {'id': 'detail-beschreibung-text-container'},
    },
    # Add more sources here as needed
}

def _get_source_for_url(url: str) -> str:
    """Determine the actual source based on URL, not the source column."""
    if 'arbeitsagentur.de/jobsuche/jobdetail/' in url:
        return 'arbeitsagentur'
    # External job boards that AA links to - we can't scrape these (yet)
    # Return None to indicate unsupported
    return None


def _rotate_wireguard(current_index: int) -> int:
    """
    Switch to next WireGuard config. Returns new index.
    
    Uses wg-quick to bring down current interface and bring up next one.
    Requires sudoers NOPASSWD for wg-quick commands.
    """
    import subprocess
    import random
    
    # If first rotation, pick random starting point to spread load
    if current_index < 0:
        next_index = random.randint(0, len(WIREGUARD_CONFIGS) - 1)
    else:
        next_index = (current_index + 1) % len(WIREGUARD_CONFIGS)
    
    next_config = WIREGUARD_CONFIGS[next_index]
    config_path = WIREGUARD_CONFIG_DIR / next_config
    interface_name = next_config.replace('.conf', '')
    
    print(f"\n🔄 ROTATING VPN → {next_config}")
    
    # Bring down any existing WG interface (ignore errors)
    for cfg in WIREGUARD_CONFIGS:
        iface = cfg.replace('.conf', '')
        subprocess.run(['sudo', 'wg-quick', 'down', iface], 
                      capture_output=True, timeout=10)
    
    # Bring up new interface
    try:
        result = subprocess.run(
            ['sudo', 'wg-quick', 'up', str(config_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"  ⚠️  wg-quick up failed: {result.stderr}")
            return next_index  # Return index anyway, will try next on failure
        print(f"  ✅ VPN active: {interface_name}")
        time.sleep(2)  # Let connection stabilize
        return next_index
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  wg-quick timed out")
        return next_index
    except Exception as e:
        print(f"  ⚠️  VPN rotation error: {e}")
        return next_index


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
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        if db_conn:
            self.conn = db_conn
            self._owns_connection = False
        else:
            self.conn = get_connection()
            self._owns_connection = True
        self.input_data: Dict[str, Any] = {}
    
    def __del__(self):
        if self._owns_connection and self.conn:
            self.conn.close()
    
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
                # Increment failure counter on posting
                self._increment_failures(posting_id)
                return {
                    'success': False,
                    'error': result.get('error', 'Fetch failed'),
                    'http_status': result.get('http_status'),  # Pass through for 403/404 handling
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
        
        # Already has description - skip (idempotency)
        if posting['job_description']:
            return {'ok': False, 'reason': 'ALREADY_HAS_DESCRIPTION', 'message': 'Posting already has description'}
        
        if not posting['external_url']:
            return {'ok': False, 'reason': 'NO_URL', 'message': 'Posting has no external_url'}
        
        # Determine actual source from URL (AA links to external job boards)
        actual_source = _get_source_for_url(posting['external_url'])
        if not actual_source:
            return {
                'ok': False, 
                'reason': 'EXTERNAL_JOB_BOARD', 
                'message': f"URL points to external job board, not scrapeable: {posting['external_url'][:50]}..."
            }
        
        if actual_source not in SOURCE_SELECTORS:
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
        
        Uses exponential backoff retry (1s, 2s, 4s) for transient failures.
        """
        config = SOURCE_SELECTORS.get(source)
        if not config:
            return {'success': False, 'error': f'No config for source: {source}'}
        
        last_error = None
        
        for attempt in range(MAX_FETCH_RETRIES):
            try:
                response = requests.get(
                    url,
                    timeout=REQUEST_TIMEOUT,
                    headers={'User-Agent': USER_AGENT}
                )
                
                if response.status_code == 429:  # Rate limited
                    last_error = 'Rate limited (429)'
                    time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                    continue
                
                # Return HTTP status for 403/404 handling by batch processor
                if response.status_code == 403:
                    return {'success': False, 'error': 'HTTP 403', 'http_status': 403}
                
                if response.status_code == 404:
                    return {'success': False, 'error': 'HTTP 404 - Job removed from AA', 'http_status': 404}
                
                if response.status_code != 200:
                    return {'success': False, 'error': f'HTTP {response.status_code}', 'http_status': response.status_code}
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find description container using source-specific selector
                selector = config['selector']
                container = soup.find('div', selector)
                
                if container:
                    # Primary: Server-side rendered description container
                    description = container.get_text(separator='\n', strip=True)
                else:
                    # Fallback: og:description meta tag (truncated but usable)
                    # AA's SPA sometimes doesn't server-render the full container
                    og_meta = soup.find('meta', {'property': 'og:description'})
                    if og_meta and og_meta.get('content'):
                        description = og_meta['content'].strip()
                        # Clean up HTML entities
                        description = description.replace('&nbsp;', ' ')
                        description = description.replace('&#160;', ' ')
                    else:
                        return {'success': False, 'error': 'Description container not found'}
                
                if not description:
                    return {'success': False, 'error': 'Empty description'}
                
                return {'success': True, 'description': description}
                
            except requests.Timeout:
                last_error = 'Request timeout'
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                continue
            except requests.RequestException as e:
                last_error = f'Request error: {e}'
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                continue
            except Exception as e:
                # Parse errors don't retry - the page structure is wrong
                return {'success': False, 'error': f'Parse error: {e}'}
        
        # All retries exhausted
        return {'success': False, 'error': f'Failed after {MAX_FETCH_RETRIES} attempts: {last_error}'}
    
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
            print(f"Result: {json.dumps(result, indent=2)}")
        
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
                print("No postings need description scraping")
                return
            
            print(f"Processing {len(rows)} postings...")
            success = 0
            failed = 0
            skipped = 0
            invalidated = 0
            
            # Rate limit tracking
            consecutive_403s = 0
            vpn_rotation_count = 0
            current_vpn_index = -1  # -1 = not using VPN yet
            
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
                    print(f"  [{i}/{len(rows)}] 🗑️  {row['posting_id']}: INVALIDATED (job removed)")
                    time.sleep(0.2)
                    continue
                
                # ============================================================
                # HANDLE 403: Rate limited - pause, retry, rotate VPN
                # ============================================================
                if http_status == 403:
                    consecutive_403s += 1
                    print(f"  [{i}/{len(rows)}] ⚠️  {row['posting_id']}: 403 Forbidden ({consecutive_403s}/{CONSECUTIVE_403_THRESHOLD})")
                    
                    if consecutive_403s >= CONSECUTIVE_403_THRESHOLD:
                        print(f"\n🛑 RATE LIMIT HIT - {consecutive_403s} consecutive 403s")
                        
                        # Rotate VPN and retry
                        vpn_rotation_count += 1
                        if vpn_rotation_count > MAX_RATE_LIMIT_RETRIES:
                            # ================================================
                            # FAIL LOUD - all retries exhausted
                            # ================================================
                            print("\n" + "=" * 60)
                            print("💥 FATAL: RATE LIMIT PERSISTS AFTER ALL VPN ROTATIONS")
                            print(f"   Rotated through {vpn_rotation_count - 1} VPN endpoints")
                            print(f"   Still getting 403 Forbidden from AA")
                            print(f"   Stats: {success} success, {invalidated} invalidated, {failed} failed")
                            print("=" * 60 + "\n")
                            sys.exit(1)
                        
                        # Pause then rotate VPN
                        print(f"⏳ Pausing {RATE_LIMIT_PAUSE_SECONDS}s before VPN rotation #{vpn_rotation_count}...")
                        time.sleep(RATE_LIMIT_PAUSE_SECONDS)
                        
                        current_vpn_index = _rotate_wireguard(current_vpn_index)
                        consecutive_403s = 0  # Reset counter after VPN change
                        
                        # Retry current posting
                        print(f"🔄 Retrying posting {row['posting_id']}...")
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
                    print(f"  [{i}/{len(rows)}] ✅ {row['posting_id']}: {result.get('description_length')} chars")
                elif result.get('skip_reason'):
                    skipped += 1
                    print(f"  [{i}/{len(rows)}] ⏭️  {row['posting_id']}: {result.get('skip_reason')}")
                else:
                    failed += 1
                    print(f"  [{i}/{len(rows)}] ❌ {row['posting_id']}: {result.get('error')}")
                
                # Rate limit - be nice to the server
                time.sleep(0.2)
            
            print(f"\nDone: {success} success, {invalidated} invalidated, {skipped} skipped, {failed} failed")
        
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
                print(f"Result for posting {row['posting_id']}:")
                print(json.dumps(result, indent=2))
            else:
                print("No postings need description scraping")


if __name__ == '__main__':
    main()
