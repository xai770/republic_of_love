#!/usr/bin/env python3
"""
Arbeitsagentur Job Fetcher - Fetches job postings from the German Federal Employment Agency

Fetches job postings from the Arbeitsagentur (Bundesagentur für Arbeit) public API
and inserts new postings into the database. Uses the unofficial but public API
documented at https://github.com/bundesAPI/jobsuche-api

Input:  Arbeitsagentur REST API (external)
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
    E -->|Yes| F[🔄 Process Jobs]
    F --> G[💾 Insert New Postings]
    G --> H[✅ SUCCESS]
```

Usage:
    # Via cron (daily at 7 AM):
    0 7 * * * cd /home/xai/Documents/ty_learn && ./venv/bin/python3 actors/postings__arbeitsagentur_CU.py
    
    # Manual run:
    python3 actors/postings__arbeitsagentur_CU.py
    
    # With options:
    python3 actors/postings__arbeitsagentur_CU.py --max-jobs 200 --search "Python Developer"

Author: Arden
Date: 2026-01-25
Task Type ID: 95876

NOTE: This is a "source" actor - it creates subjects rather than processing them.
      Triggered by cron, not by pull_daemon's work_query.
---
"""

import argparse
import json
import time
from datetime import datetime
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

from core.logging_config import get_logger
logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
ACTOR_ID = 1297  # postings__arbeitsagentur_CU actor ID

# Arbeitsagentur API configuration
# Docs: https://github.com/bundesAPI/jobsuche-api
API_BASE_URL = 'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service'
API_KEY = 'jobboerse-jobsuche'  # Public API key (not secret)

API_HEADERS = {
    'X-API-Key': API_KEY,
    'Accept': 'application/json',
    'User-Agent': 'TalentYoga/1.0 (Job Aggregator)'
}

# =============================================================================
# SEARCH PROFILES - Configurable job category sampling
# =============================================================================
# Each profile contains search terms for different job categories
# Use --profile to select which categories to fetch

SEARCH_PROFILES = {
    # Original IT-focused searches
    'it': [
        {'was': 'Software Engineer', 'wo': 'Berlin'},
        {'was': 'Data Engineer', 'wo': 'München'},
        {'was': 'Python Developer', 'wo': 'Hamburg'},
        {'was': 'DevOps', 'wo': 'Frankfurt'},
    ],
    
    # Education & Social Work (for Mysti and pedagogy professionals!)
    'education': [
        {'was': 'Erzieher', 'wo': 'Berlin'},
        {'was': 'Erzieher', 'wo': 'Hamburg'},
        {'was': 'Erzieher', 'wo': 'München'},
        {'was': 'Paedagoge', 'wo': 'Berlin'},
        {'was': 'Paedagoge', 'wo': 'Köln'},
        {'was': 'Sozialpaedagoge', 'wo': 'Berlin'},
        {'was': 'Sozialpaedagoge', 'wo': 'Frankfurt'},
        {'was': 'Lehrer', 'wo': 'Berlin'},
        {'was': 'Lehrer', 'wo': 'München'},
        {'was': 'Heilpaedagoge', 'wo': 'Berlin'},
        {'was': 'Heilpaedagoge', 'wo': 'Hamburg'},
        {'was': 'Dozent', 'wo': 'Berlin'},
        {'was': 'Kita', 'wo': 'Berlin'},
        {'was': 'Kita', 'wo': 'München'},
    ],
    
    # Healthcare
    'healthcare': [
        {'was': 'Krankenpfleger', 'wo': 'Berlin'},
        {'was': 'Krankenpfleger', 'wo': 'München'},
        {'was': 'Arzt', 'wo': 'Berlin'},
        {'was': 'Therapeut', 'wo': 'Hamburg'},
        {'was': 'Altenpflege', 'wo': 'Frankfurt'},
    ],
    
    # Technical/Engineering
    'technical': [
        {'was': 'Ingenieur', 'wo': 'Stuttgart'},
        {'was': 'Ingenieur', 'wo': 'München'},
        {'was': 'Techniker', 'wo': 'Berlin'},
        {'was': 'Elektriker', 'wo': 'Hamburg'},
        {'was': 'Mechaniker', 'wo': 'Frankfurt'},
    ],
    
    # Business/Office
    'business': [
        {'was': 'Kaufmann', 'wo': 'Berlin'},
        {'was': 'Kaufmann', 'wo': 'Frankfurt'},
        {'was': 'Buchhalter', 'wo': 'München'},
        {'was': 'Projektmanager', 'wo': 'Berlin'},
        {'was': 'Projektmanager', 'wo': 'Hamburg'},
    ],
    
    # Trades/Crafts
    'trades': [
        {'was': 'Koch', 'wo': 'Berlin'},
        {'was': 'Koch', 'wo': 'München'},
        {'was': 'Baecker', 'wo': 'Hamburg'},
        {'was': 'Friseur', 'wo': 'Köln'},
        {'was': 'Handwerker', 'wo': 'Berlin'},
    ],
}

# Combined profile for representative sampling
SEARCH_PROFILES['all'] = (
    SEARCH_PROFILES['education'] +
    SEARCH_PROFILES['healthcare'] + 
    SEARCH_PROFILES['technical'] +
    SEARCH_PROFILES['business'] +
    SEARCH_PROFILES['it'] +
    SEARCH_PROFILES['trades']
)

# Default to IT for backward compatibility
DEFAULT_SEARCH_QUERIES = SEARCH_PROFILES['it']

DEFAULT_MAX_JOBS = 100  # Per search query
DEFAULT_BATCH_SIZE = 100  # API pagination size (max allowed by API)
DESCRIPTION_FETCH_DELAY = 0.15  # Seconds between scrape requests (be nice!)

# German to English mapping for common terms
GERMAN_EMPLOYMENT_TYPES = {
    'vz': 'Full-time',
    'tz': 'Part-time',
    'ho': 'Remote/Telearbeit',
    'mj': 'Mini-job',
    'snw': 'Shift/Night/Weekend',
}

# =============================================================================
# CITY LISTS - For geographic coverage
# =============================================================================
# Top 20 German cities by population (Dec 2024)
TOP_20_CITIES = [
    'Berlin', 'Hamburg', 'München', 'Köln', 'Frankfurt am Main',
    'Düsseldorf', 'Stuttgart', 'Leipzig', 'Dortmund', 'Bremen',
    'Essen', 'Dresden', 'Nürnberg', 'Hannover', 'Duisburg',
    'Mannheim', 'Karlsruhe', 'Münster', 'Augsburg', 'Wiesbaden',
]

# Top 50 for full coverage (expand later)
TOP_50_CITIES = TOP_20_CITIES + [
    'Bonn', 'Gelsenkirchen', 'Mönchengladbach', 'Aachen', 'Braunschweig',
    'Kiel', 'Chemnitz', 'Magdeburg', 'Freiburg im Breisgau', 'Krefeld',
    'Halle', 'Mainz', 'Lübeck', 'Erfurt', 'Oberhausen',
    'Rostock', 'Kassel', 'Hagen', 'Potsdam', 'Saarbrücken',
    'Hamm', 'Ludwigshafen am Rhein', 'Oldenburg', 'Mülheim an der Ruhr',
    'Leverkusen', 'Darmstadt', 'Osnabrück', 'Solingen', 'Paderborn', 'Heidelberg',
]

# All 16 German states (Bundesländer) - for state-based batching
# This is more reliable than a single nationwide query (smaller batches, better progress visibility)
BUNDESLAENDER = [
    'Baden-Württemberg',
    'Bayern',
    'Berlin',
    'Brandenburg',
    'Bremen',
    'Hamburg',
    'Hessen',
    'Mecklenburg-Vorpommern',
    'Niedersachsen',
    'Nordrhein-Westfalen',
    'Rheinland-Pfalz',
    'Saarland',
    'Sachsen',
    'Sachsen-Anhalt',
    'Schleswig-Holstein',
    'Thüringen',
]


# ============================================================================
# ACTOR CLASS
# ============================================================================
class ArbeitsagenturJobFetcher:
    """
    Arbeitsagentur Job Fetcher - Source actor for German job postings.
    
    Uses the public (unofficial) API of the German Federal Employment Agency.
    The API requires only an X-API-Key header with the value 'jobboerse-jobsuche'.
    
    Follows the three-phase pattern:
    1. PREFLIGHT: Check if already ran today
    2. PROCESS: Call API, parse jobs
    3. SAVE: Insert new postings
    """
    
    def __init__(self, db_conn, max_jobs: int = DEFAULT_MAX_JOBS, 
                 search_queries: List[Dict] = None, fetch_descriptions: bool = True,
                 since_days: int = None):
        """
        Initialize with database connection.
        
        NOTE: Connection should be passed in (not created here) to allow
        proper context management in main().
        
        Args:
            db_conn: Database connection
            max_jobs: Maximum jobs to fetch per search query
            search_queries: List of search dicts with 'was' and 'wo' keys
            fetch_descriptions: If True, scrape full descriptions from HTML pages
            since_days: Only fetch jobs published in last N days (uses veroeffentlichtseit)
        """
        self.conn = db_conn
        self.max_jobs = max_jobs
        self.search_queries = search_queries or DEFAULT_SEARCH_QUERIES
        self.fetch_descriptions = fetch_descriptions
        self.since_days = since_days
        
        # Stats tracking
        self.fetched_ids: Set[str] = set()
        self.description_fetch_count = 0
        self.description_errors = 0
    
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
            all_jobs = []
            
            for query in self.search_queries:
                logger.info("Fetching: %s in %s...", query.get('was'), query.get('wo'))
                jobs = self._fetch_jobs(query)
                
                if jobs:
                    logger.info("Found %s jobs", len(jobs))
                    all_jobs.extend(jobs)
                else:
                    logger.warning("No jobs found or API error")
                
                # Rate limit - be nice to the API
                time.sleep(0.5)
            
            if not all_jobs:
                return {
                    'success': False,
                    'error': 'No jobs fetched from any search',
                }
            
            # Dedupe by refnr (same job might appear in multiple searches)
            unique_jobs = {}
            for job in all_jobs:
                refnr = job.get('refnr')
                if refnr and refnr not in unique_jobs:
                    unique_jobs[refnr] = job
            
            logger.info("Total unique jobs: %s (from %s results)", len(unique_jobs), len(all_jobs))
            
            # ----------------------------------------------------------------
            # PHASE 3: SAVE - Insert new postings
            # ----------------------------------------------------------------
            stats = self._save_postings(list(unique_jobs.values()))
            
            return {
                'success': True,
                '_consistency': '1/1',
                'stats': stats,
                'message': f"Fetched {stats['fetched']}, new: {stats['new']}, existing: {stats['existing']}, errors: {stats['errors']}",
            }
            
        except Exception as e:
            self.conn.rollback()
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
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
            WHERE actor_id = %s
              AND status = 'completed'
              AND completed_at > NOW() - INTERVAL '20 hours'
            ORDER BY completed_at DESC
            LIMIT 1
        """, (ACTOR_ID,))
        
        row = cur.fetchone()
        if row:
            return {
                'ok': False,
                'reason': 'ALREADY_RAN_TODAY',
                'message': f"Already ran at {row['completed_at']} (ticket {row['ticket_id']})",
            }
        
        # Check 2: API health check
        if not self._check_api_health():
            return {
                'ok': False,
                'reason': 'API_UNREACHABLE',
                'message': 'Arbeitsagentur API is not responding',
            }
        
        return {'ok': True}
    
    def _check_api_health(self) -> bool:
        """Quick test to see if the API is responding."""
        try:
            url = f"{API_BASE_URL}/pc/v4/jobs?was=test&size=1"
            logger.debug("Health check: GET %s...", url[:60])
            response = requests.get(url, headers=API_HEADERS, timeout=10)
            logger.debug("Health check response: %s", response.status_code)
            return response.status_code == 200
        except requests.Timeout:
            logger.error("Health check TIMEOUT (10s)")
            return False
        except Exception as e:
            logger.error("Health check error: %s", e)
            return False
    
    # ========================================================================
    # PHASE 2: PROCESS - Fetch from API
    # ========================================================================
    
    def _fetch_jobs(self, search_params: Dict) -> List[Dict]:
        """
        Fetch jobs from Arbeitsagentur API with pagination.
        
        Args:
            search_params: Dict with 'was' (what), 'wo' (where), etc.
            
        Returns:
            List of normalized job dicts
        """
        all_jobs = []
        page = 1
        total_fetched = 0
        
        while total_fetched < self.max_jobs:
            # Build URL with parameters
            params = {
                'wo': search_params.get('wo', ''),
                'page': page,
                'size': DEFAULT_BATCH_SIZE,
                'angebotsart': 1,  # 1 = ARBEIT (regular jobs)
            }
            
            # Only add 'was' if specified (empty = all jobs in that city)
            if search_params.get('was'):
                params['was'] = search_params['was']
            
            # Date filter: only jobs published in last N days
            if self.since_days:
                params['veroeffentlichtseit'] = self.since_days
            
            # Add optional filters
            if search_params.get('arbeitszeit'):
                params['arbeitszeit'] = search_params['arbeitszeit']
            if search_params.get('umkreis'):
                params['umkreis'] = search_params['umkreis']
            
            url = f"{API_BASE_URL}/pc/v4/jobs"
            
            try:
                # Debug: show what we're fetching
                param_str = '&'.join(f"{k}={v}" for k,v in params.items())
                logger.info("GET %s?%s...", url, param_str[:80])
                
                response = requests.get(url, params=params, headers=API_HEADERS, timeout=30)
                
                logger.info("Response: %s (%s bytes)", response.status_code, len(response.content))
                
                if response.status_code != 200:
                    logger.error("API error: %s", response.status_code)
                    logger.info("Response body: %s", response.text[:200])
                    break
                
                data = response.json()
                jobs = data.get('stellenangebote', [])
                max_results = data.get('maxErgebnisse', 0)
                
                logger.info("Page %s: %s jobs (max available: %s)", page, len(jobs), max_results)
                
                if not jobs:
                    logger.info("No more jobs on this page")
                    break
                
                # Normalize each job
                for job in jobs:
                    normalized = self._normalize_job(job, search_params)
                    if normalized:
                        all_jobs.append(normalized)
                        self.fetched_ids.add(normalized['refnr'])
                
                total_fetched += len(jobs)
                
                # Progress update
                logger.info("Fetched %s/%s jobs", total_fetched, min(max_results, self.max_jobs))
                
                # Check if we've got all available jobs
                if total_fetched >= max_results or total_fetched >= self.max_jobs:
                    logger.info("Done fetching (reached limit)")
                    break
                
                page += 1
                time.sleep(0.2)  # Rate limit between pages
                
            except requests.Timeout:
                logger.error("Request TIMEOUT (30s) on page %s", page)
                break
            except requests.RequestException as e:
                logger.error("Request error: %s: %s", type(e).__name__, e)
                break
            except json.JSONDecodeError as e:
                logger.error("JSON decode error: %s", e)
                break
        
        return all_jobs
    
    def _fetch_description_from_page(self, refnr: str) -> Optional[str]:
        """
        Scrape the full job description from the Arbeitsagentur detail page.
        
        The API only returns metadata - full descriptions are in the HTML.
        We scrape the <div id="detail-beschreibung-text-container">.
        
        Args:
            refnr: Job reference number (e.g., "10000-1205173046-S")
            
        Returns:
            Full job description text or None if scraping fails
        """
        url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"
        
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Primary: Server-side rendered description container
            desc_container = soup.find('div', {'id': 'detail-beschreibung-text-container'})
            
            if desc_container:
                # Get text, preserving paragraph breaks
                description = desc_container.get_text(separator='\n', strip=True)
                self.description_fetch_count += 1
                return description
            
            # Fallback: og:description meta tag (truncated ~300 chars but usable)
            # AA's SPA sometimes doesn't server-render the full container
            og_meta = soup.find('meta', {'property': 'og:description'})
            if og_meta and og_meta.get('content'):
                description = og_meta['content'].strip()
                # Clean up HTML entities
                description = description.replace('&nbsp;', ' ').replace('&#160;', ' ')
                if len(description) >= 50:  # Minimum viable description
                    self.description_fetch_count += 1
                    return description
            
            return None
            
        except Exception as e:
            self.description_errors += 1
            return None
    
    def _normalize_job(self, raw_job: Dict, search_context: Dict) -> Optional[Dict]:
        """
        Normalize API response to our internal format.
        
        Args:
            raw_job: Raw job dict from API
            search_context: The search parameters used (for metadata)
            
        Returns:
            Normalized job dict or None if invalid
        """
        try:
            refnr = raw_job.get('refnr')
            if not refnr:
                return None
            
            # Extract location
            arbeitsort = raw_job.get('arbeitsort', {})
            location_city = arbeitsort.get('ort', '')
            location_postal_code = arbeitsort.get('plz', '')  # German PLZ (e.g., 80333)
            location_state = arbeitsort.get('region', '')  # Bundesland (e.g., Bayern, Hessen)
            location_country = arbeitsort.get('land', 'Deutschland')
            
            title = raw_job.get('titel', '')
            beruf = raw_job.get('beruf', '')  # Occupation category
            employer = raw_job.get('arbeitgeber', '')
            
            # Try to fetch full description from HTML page
            # Directive #8: FAIL LOUD - no synthetic fallbacks
            job_description = None
            if self.fetch_descriptions:
                job_description = self._fetch_description_from_page(refnr)
                time.sleep(DESCRIPTION_FETCH_DELAY)  # Rate limit - be nice!
            
            # If scrape failed, job_description stays None
            # Downstream actors will skip postings without real descriptions
            # This is intentional - synthetic descriptions are useless
            
            return {
                'refnr': refnr,
                'external_id': f"aa-{refnr}",
                'title': title,
                'beruf': beruf,
                'employer': employer,
                'location_city': location_city,
                'location_postal_code': location_postal_code,
                'location_state': location_state,
                'location_country': location_country,
                'external_url': f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
                'published_date': raw_job.get('aktuelleVeroeffentlichungsdatum'),
                'entry_date': raw_job.get('eintrittsdatum'),
                'job_description': job_description,
                'search_context': search_context,
                'raw_data': raw_job,  # Full API response for future re-processing
            }
            
        except Exception as e:
            logger.error("Error normalizing job: %s", e)
            return None
    
    # ========================================================================
    # PHASE 3: SAVE
    # ========================================================================
    
    def _save_postings(self, jobs: List[Dict]) -> Dict:
        """
        Save jobs to the postings table.
        
        Uses external_job_id (refnr) for deduplication.
        """
        stats = {
            'fetched': len(jobs),
            'new': 0,
            'existing': 0,
            'errors': 0,
        }
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        for i, job in enumerate(jobs, 1):
            try:
                # Check if job already exists (by refnr)
                cur.execute("""
                    SELECT posting_id, posting_status, job_description
                    FROM postings
                    WHERE external_job_id = %s
                """, (job['refnr'],))
                
                existing = cur.fetchone()
                
                if existing:
                    # Update last_seen_at for existing job
                    # Also update description if we have a better one (longer than metadata-only)
                    new_desc = job.get('job_description', '')
                    old_desc = existing.get('job_description', '') or ''
                    
                    if new_desc and len(new_desc) > len(old_desc) + 50:
                        # We have a significantly better description - update it
                        cur.execute("""
                            UPDATE postings 
                            SET last_seen_at = NOW(),
                                job_description = %s
                            WHERE posting_id = %s
                        """, (new_desc, existing['posting_id']))
                        stats['existing'] += 1
                        stats['descriptions_updated'] = stats.get('descriptions_updated', 0) + 1
                    else:
                        cur.execute("""
                            UPDATE postings 
                            SET last_seen_at = NOW()
                            WHERE posting_id = %s
                        """, (existing['posting_id'],))
                        stats['existing'] += 1
                    continue
                
                # Insert new posting
                cur.execute("""
                    INSERT INTO postings (
                        external_id, external_job_id, posting_name, job_title, beruf,
                        location_city, location_postal_code, location_state, location_country, 
                        source, external_url, source_metadata, job_description,
                        first_seen_at, last_seen_at, posting_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')
                    RETURNING posting_id
                """, (
                    job['external_id'],
                    job['refnr'],
                    job['employer'] or job['title'],  # posting_name = employer or title
                    job['title'],
                    job.get('beruf', ''),  # Occupation category for berufenet lookup
                    job['location_city'],
                    job['location_postal_code'],
                    job['location_state'],
                    job['location_country'],
                    'arbeitsagentur',
                    job['external_url'],
                    json.dumps({
                        'search_context': job['search_context'],
                        'published_date': job['published_date'],
                        'entry_date': job['entry_date'],
                        'raw_api_response': job['raw_data'],  # Store full API response!
                    }),
                    job['job_description'],
                ))
                
                stats['new'] += 1
                
                if stats['new'] % 25 == 0:
                    self.conn.commit()
                    logger.info("[%s/%s]%s new postings inserted...", i, len(jobs), stats['new'])
                
            except Exception as e:
                self.conn.rollback()
                stats['errors'] += 1
                logger.error("Error inserting job %s: %s: %s", job['refnr'], type(e).__name__, e)
        
        self.conn.commit()
        return stats


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch job postings from Arbeitsagentur (German Federal Employment Agency)'
    )
    parser.add_argument(
        '--max-jobs', type=int, default=DEFAULT_MAX_JOBS,
        help=f'Maximum jobs to fetch per search query (default: {DEFAULT_MAX_JOBS})'
    )
    parser.add_argument(
        '--profile', type=str, choices=list(SEARCH_PROFILES.keys()),
        help=f'Search profile: {", ".join(SEARCH_PROFILES.keys())}. Use "education" for pedagogy jobs, "all" for representative sample.'
    )
    parser.add_argument(
        '--search', type=str, 
        help='Custom search term (overrides --profile)'
    )
    parser.add_argument(
        '--location', type=str, default='Berlin',
        help='Location for custom search (default: Berlin)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Print what would be fetched without inserting'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Run even if already ran today'
    )
    parser.add_argument(
        '--no-descriptions', action='store_true',
        help='Skip scraping full descriptions (faster, but less data)'
    )
    parser.add_argument(
        '--list-profiles', action='store_true',
        help='List available search profiles and exit'
    )
    parser.add_argument(
        '--since', type=int, default=None,
        help='Only fetch jobs published in last N days (uses veroeffentlichtseit API param)'
    )
    parser.add_argument(
        '--cities', type=str, choices=['top20', 'top50'],
        help='Fetch from top N German cities (no job title filter, use with --since)'
    )
    parser.add_argument(
        '--nationwide', action='store_true',
        help='Fetch all jobs Germany-wide (wo=Deutschland), no city filter. Use with --since.'
    )
    parser.add_argument(
        '--states', action='store_true',
        help='Fetch by state (Bundesland) - 16 separate queries. More reliable than --nationwide.'
    )
    parser.add_argument(
        '--state', type=str,
        help='Fetch jobs from a single state (e.g., --state Bayern). Use with --since.'
    )
    
    args = parser.parse_args()
    
    # List profiles and exit
    if args.list_profiles:
        logger.info("Available search profiles:\n")
        for name, queries in SEARCH_PROFILES.items():
            if name != 'all':
                logger.info("%s: %s searches", name, len(queries))
                for q in queries[:3]:
                    logger.info("%s in %s", q['was'], q['wo'])
                if len(queries) > 3:
                    logger.info("... and %s more", len(queries)-3)
        logger.info("all: %s searches (combined)", len(SEARCH_PROFILES['all']))
        logger.info("--states: 16 Bundesländer (recommended for nightly)")
        logger.info("" + ", ".join(BUNDESLAENDER[:4]) + "...")
        return
    
    # Build search queries based on args
    if args.states:
        # State-based fetch (16 queries, one per Bundesland) - recommended for reliability
        search_queries = [{'wo': state} for state in BUNDESLAENDER]
        profile_name = 'all states (16 Bundesländer)'
    elif args.state:
        # Single state fetch
        if args.state not in BUNDESLAENDER:
            logger.error("Unknown state: %s", args.state)
            logger.info("Valid states: %s", ', '.join(BUNDESLAENDER))
            return
        search_queries = [{'wo': args.state}]
        profile_name = f'state: {args.state}'
    elif args.nationwide:
        # Germany-wide fetch (single query, no city filter)
        search_queries = [{'wo': 'Deutschland'}]
        profile_name = 'nationwide (Deutschland)'
    elif args.cities:
        # City-based fetch (all jobs, no title filter)
        cities = TOP_20_CITIES if args.cities == 'top20' else TOP_50_CITIES
        search_queries = [{'wo': city} for city in cities]  # No 'was' = all jobs
        profile_name = f'{args.cities} cities'
    elif args.search:
        search_queries = [{'was': args.search, 'wo': args.location}]
        profile_name = 'custom'
    elif args.profile:
        search_queries = SEARCH_PROFILES[args.profile]
        profile_name = args.profile
    else:
        search_queries = DEFAULT_SEARCH_QUERIES
        profile_name = 'it (default)'
    
    fetch_descriptions = not args.no_descriptions
    
    since_days = args.since
    
    logger.info("Arbeitsagentur Job Fetcher")
    logger.info("Profile: %s", profile_name)
    logger.info("Max jobs per query: %s", args.max_jobs)
    logger.info("Searches: %s", len(search_queries))
    logger.info("Since: %s", f'last {since_days}days' if since_days else 'all time')
    logger.info("Fetch descriptions: %s", 'Yes (scraping HTML)' if fetch_descriptions else 'No (metadata only)')
    logger.info("Time: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("%s\n", '='*60)
    
    if args.dry_run:
        logger.warning("DRY RUN MODE - No database changes\n")
        # Test API without database
        _test_api_health(search_queries, since_days)
        return
    
    # Run with database connection
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if already ran today BEFORE creating ticket (avoid ticket spam)
        if not args.force:
            cur.execute("""
                SELECT ticket_id, completed_at
                FROM tickets
                WHERE actor_id = %s
                  AND status = 'completed'
                  AND completed_at > NOW() - INTERVAL '20 hours'
                ORDER BY completed_at DESC
                LIMIT 1
            """, (ACTOR_ID,))
            row = cur.fetchone()
            if row:
                logger.info("SKIPPED: ALREADY_RAN_TODAY")
                logger.info("Already ran at %s (ticket %s)", row['completed_at'], row['ticket_id'])
                logger.info("%s\n", '='*60)
                return
        
        # Create ticket for auditability
        cur.execute("""
            INSERT INTO tickets (
                actor_id,
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
        """, (ACTOR_ID, json.dumps({
            'max_jobs': args.max_jobs,
            'search_queries': search_queries,
            'force': args.force,
            'fetch_descriptions': fetch_descriptions
        })))
        
        ticket_id = cur.fetchone()['ticket_id']
        conn.commit()
        logger.info("ticket_id: %s", ticket_id)
        
        # Run the actor
        actor = ArbeitsagenturJobFetcher(
            db_conn=conn, 
            max_jobs=args.max_jobs, 
            search_queries=search_queries,
            fetch_descriptions=fetch_descriptions,
            since_days=since_days
        )
        
        if args.force:
            # Skip preflight, run directly
            logger.warning("FORCE MODE - Skipping preflight checks\n")
            all_jobs = []
            for query in search_queries:
                logger.info("Fetching: %s in %s...", query.get('was'), query.get('wo'))
                jobs = actor._fetch_jobs(query)
                if jobs:
                    logger.info("Found %s jobs", len(jobs))
                    all_jobs.extend(jobs)
                time.sleep(0.5)
            
            # Dedupe and save
            unique_jobs = {j['refnr']: j for j in all_jobs}
            logger.info("Total unique jobs: %s", len(unique_jobs))
            if fetch_descriptions:
                logger.info("Descriptions scraped: %s, errors: %s", actor.description_fetch_count, actor.description_errors)
            stats = actor._save_postings(list(unique_jobs.values()))
            result = {
                'success': True,
                'stats': stats,
                'descriptions_fetched': actor.description_fetch_count,
                'description_errors': actor.description_errors,
                'message': f"Fetched {stats['fetched']}, new: {stats['new']}, existing: {stats['existing']}, descriptions: {actor.description_fetch_count}"
            }
        else:
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
            logger.info("SUCCESS: %s", result.get('message'))
        else:
            error = result.get('error') or result.get('skip_reason') or 'Unknown error'
            status = 'completed' if result.get('skip_reason') else 'failed'
            cur.execute("""
                UPDATE tickets
                SET status = %s,
                    output = %s,
                    completed_at = NOW()
                WHERE ticket_id = %s
            """, (status, json.dumps(result), ticket_id))
            logger.error("%s: %s", '⏭️ SKIPPED' if result.get('skip_reason') else '❌ FAILED', error)
            if result.get('message'):
                logger.info("%s", result['message'])
        
        conn.commit()
    
    logger.info("%s\n", '='*60)


def _test_api_health(search_queries: List[Dict], since_days: int = None):
    """Test API health without database (for dry-run mode)."""
    # Quick API health check
    try:
        url = f"{API_BASE_URL}/pc/v4/jobs?was=test&size=1"
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        if response.status_code == 200:
            logger.info("API is healthy")
        else:
            logger.error("API returned status %s", response.status_code)
            return
    except Exception as e:
        logger.error("API error: %s", e)
        return
    
    # Test first search
    query = search_queries[0]
    was_text = query.get('was') or '(all jobs)'
    logger.info("Testing search: %s in %s...", was_text, query.get('wo'))
    
    try:
        url = f"{API_BASE_URL}/pc/v4/jobs"
        params = {
            'wo': query.get('wo', ''),
            'page': 1,
            'size': 5,
            'angebotsart': 1,
        }
        # Only add 'was' if specified
        if query.get('was'):
            params['was'] = query['was']
        # Add date filter if specified
        if since_days:
            params['veroeffentlichtseit'] = since_days
            
        response = requests.get(url, params=params, headers=API_HEADERS, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('stellenangebote', [])
            total = data.get('maxErgebnisse', 0)
            logger.info("Found %s total jobs, sample of %s:", total, len(jobs))
            for job in jobs[:3]:
                logger.info("%s@%s", job.get('titel'), job.get('arbeitgeber'))
        else:
            logger.error("Search returned status %s", response.status_code)
    except Exception as e:
        logger.error("Search error: %s", e)


if __name__ == '__main__':
    main()
