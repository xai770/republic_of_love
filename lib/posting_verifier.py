"""
Lazy posting verification — Google-style async staleness check.

When search results are about to be shown to a user, we check which postings
haven't been verified in the last 24 hours. Those are queued for background
verification. The verification checks the AA API (or external URL for non-AA
postings) to confirm the posting is still live.

Design:
- Verification happens AFTER returning search results (non-blocking)
- Uses a background thread with its own DB connection
- Rate-limited: max 5 verifications per search request, 0.3s delay between
- Updates last_validated_at on success, sets invalidated=true on 404/gone
- Next search by any user will no longer show invalidated postings

Usage:
    from lib.posting_verifier import queue_stale_verification
    queue_stale_verification(posting_ids)  # fire-and-forget from search endpoint
"""

import requests
import psycopg2
import psycopg2.extras
import threading
import logging
import time
import os

logger = logging.getLogger(__name__)

# AA API config (same as actors/postings__arbeitsagentur_CU.py)
AA_API_BASE = 'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service'
AA_API_HEADERS = {
    'X-API-Key': 'jobboerse-jobsuche',
    'Accept': 'application/json',
    'User-Agent': 'TalentYoga/1.0 (Job Aggregator)'
}

# Limits
MAX_VERIFY_PER_REQUEST = 5     # Don't verify more than 5 per search
VERIFY_DELAY = 0.3             # Seconds between AA API calls
REQUEST_TIMEOUT = 8            # HTTP timeout
STALE_HOURS = 24               # Consider stale after this many hours


def _get_db_connection():
    """Get a standalone DB connection for the background thread."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38'),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _verify_aa_posting(external_id: str) -> dict:
    """
    Check if an AA posting still exists via the search API.
    
    The detail API (/v4/jobdetails/{refnr}) doesn't work for all refnr formats.
    Instead, we search with was={refnr} and check if the exact refnr appears
    in results. This is reliable — if AA still indexes the posting, it will
    appear when searching for its own reference number.
    
    Args:
        external_id: e.g. "aa-10000-1205173046-S"
    
    Returns:
        {'exists': True/False/None, 'reason': str}
    """
    # Strip the "aa-" prefix to get the refnr
    refnr = external_id[3:] if external_id.startswith('aa-') else external_id
    
    url = f"{AA_API_BASE}/pc/v4/jobs"
    params = {'was': refnr, 'size': 5}
    try:
        resp = requests.get(url, headers=AA_API_HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Check if our exact refnr is in the results
            jobs = data.get('stellenangebote', [])
            for job in jobs:
                if job.get('refnr') == refnr:
                    return {'exists': True, 'reason': 'ok'}
            # Not found in search results — posting is gone
            if data.get('maxErgebnisse', 0) == 0:
                return {'exists': False, 'reason': 'not_in_search_results'}
            # Search returned results but none matched our refnr exactly
            return {'exists': False, 'reason': 'refnr_not_found'}
        elif resp.status_code == 429:
            return {'exists': None, 'reason': 'rate_limited'}
        else:
            return {'exists': None, 'reason': f'http_{resp.status_code}'}
    except requests.exceptions.Timeout:
        return {'exists': None, 'reason': 'timeout'}
    except requests.exceptions.RequestException as e:
        return {'exists': None, 'reason': f'error: {str(e)[:50]}'}


def _verify_url(url: str) -> dict:
    """Check if a non-AA posting URL is still live (HEAD then GET)."""
    try:
        resp = requests.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return {'exists': True, 'reason': 'ok'}
        elif resp.status_code == 404:
            return {'exists': False, 'reason': '404'}
        elif resp.status_code == 405:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                return {'exists': True, 'reason': 'ok'}
            return {'exists': False, 'reason': f'http_{resp.status_code}'}
        else:
            return {'exists': None, 'reason': f'http_{resp.status_code}'}
    except requests.exceptions.Timeout:
        return {'exists': None, 'reason': 'timeout'}
    except requests.exceptions.RequestException as e:
        return {'exists': None, 'reason': f'error: {str(e)[:50]}'}


def _verify_postings_background(posting_ids: list):
    """
    Background thread: verify a batch of postings and update the DB.
    
    For each posting:
    - AA postings (external_id starts with 'aa-'): check AA detail API
    - Other postings: HEAD/GET the external_url
    - If still live: update last_validated_at
    - If gone (404/410): set invalidated = true
    - If inconclusive (timeout/error): skip, will retry next search
    """
    conn = None
    try:
        conn = _get_db_connection()
        with conn.cursor() as cur:
            # Fetch posting details we need for verification
            cur.execute("""
                SELECT posting_id, external_id, external_url, source
                FROM postings
                WHERE posting_id = ANY(%s)
                  AND enabled = true
                  AND invalidated = false
                  AND (last_validated_at IS NULL 
                       OR last_validated_at < now() - interval '%s hours')
            """, (posting_ids, STALE_HOURS))
            stale = cur.fetchall()
        
        if not stale:
            return
        
        # Limit how many we verify per request
        to_verify = stale[:MAX_VERIFY_PER_REQUEST]
        verified = 0
        invalidated = 0
        
        for posting in to_verify:
            # Choose verification method based on source
            if posting['source'] == 'arbeitsagentur' and posting['external_id']:
                result = _verify_aa_posting(posting['external_id'])
            elif posting['external_url']:
                result = _verify_url(posting['external_url'])
            else:
                # No URL to check — just stamp it as validated
                result = {'exists': True, 'reason': 'no_url'}
            
            with conn.cursor() as cur:
                if result['exists'] is True:
                    # Still live — update validation timestamp
                    cur.execute("""
                        UPDATE postings
                        SET last_validated_at = now(),
                            updated_at = now()
                        WHERE posting_id = %s
                    """, (posting['posting_id'],))
                    verified += 1
                    
                elif result['exists'] is False:
                    # Gone — invalidate
                    cur.execute("""
                        UPDATE postings
                        SET invalidated = true,
                            invalidated_at = now(),
                            invalidated_reason = %s,
                            last_validated_at = now(),
                            updated_at = now()
                        WHERE posting_id = %s
                    """, (f"lazy_verify: {result['reason']}", posting['posting_id']))
                    invalidated += 1
                    logger.info(
                        "Invalidated posting %s: %s",
                        posting['posting_id'], result['reason']
                    )
                # else: inconclusive — skip, will retry next time
                
            conn.commit()
            
            # Rate limit
            if posting != to_verify[-1]:
                time.sleep(VERIFY_DELAY)
        
        if verified or invalidated:
            logger.info(
                "Lazy verification: %d verified, %d invalidated (of %d stale)",
                verified, invalidated, len(stale)
            )
            
    except Exception as e:
        logger.error("Background verification failed: %s", e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def find_stale_posting_ids(posting_ids: list, conn) -> list:
    """
    Given a list of posting IDs from search results, return those
    that haven't been verified in the last STALE_HOURS hours.
    
    Uses the caller's DB connection (read-only query).
    """
    if not posting_ids:
        return []
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id
            FROM postings
            WHERE posting_id = ANY(%s)
              AND (last_validated_at IS NULL 
                   OR last_validated_at < now() - interval '%s hours')
        """, (posting_ids, STALE_HOURS))
        return [row['posting_id'] for row in cur.fetchall()]


def queue_stale_verification(posting_ids: list):
    """
    Fire-and-forget: launch a background thread to verify stale postings.
    
    Call this after returning search results to the user.
    The thread gets its own DB connection, verifies up to MAX_VERIFY_PER_REQUEST
    postings, and updates last_validated_at / invalidated as needed.
    """
    if not posting_ids:
        return
    
    thread = threading.Thread(
        target=_verify_postings_background,
        args=(posting_ids,),
        daemon=True,
        name="posting-verifier",
    )
    thread.start()
