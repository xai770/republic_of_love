#!/usr/bin/env python3
"""
Workflow 3001 Step 1: db_job_fetcher
Fetches job postings from Deutsche Bank Workday API and stores in postings_staging.
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_wave')

from core.wave_runner.script_actor_template import ScriptActorBase
import requests
import json
import re
from html.parser import HTMLParser


class JobDescriptionParser(HTMLParser):
    """Extract job description from meta tag"""
    def __init__(self):
        super().__init__()
        self.description = None
        
    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            attrs_dict = dict(attrs)
            if attrs_dict.get('property') == 'og:description':
                self.description = attrs_dict.get('content', '')


class DBJobFetcher(ScriptActorBase):
    """Fetch jobs from Deutsche Bank Workday API and write to staging"""
    
    # Deutsche Bank Workday API endpoint
    API_URL = 'https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebSite/jobs'
    
    # API enforces max 20 jobs per request (undocumented limit)
    MAX_JOBS_PER_REQUEST = 20
    
    def _lookup_country_from_db(self, cursor, location_text: str) -> str:
        """
        Look up country from city_country_map table.
        
        Args:
            cursor: Database cursor
            location_text: Location text from API (e.g. "Pune - Business Bay")
            
        Returns:
            Country name or None
        """
        if not location_text:
            return None
        
        # Skip "X Locations" patterns - these need individual location lookup
        if 'Locations' in location_text or 'locations' in location_text:
            return None
        
        # Extract potential city names from location text
        # "Pune - Business Bay" -> try "Pune", "Business Bay"
        # "Singapore, One Raffles Quay" -> try "Singapore", "One Raffles Quay"
        # "Frankfurt Taunusanlage 12" -> try "Frankfurt" (first word)
        # "California/Santa Ana" -> try "California", "Santa Ana"
        # "Kuala Lumpur Menara IMC" -> try "Kuala Lumpur" (first two words for known patterns)
        parts = [p.strip() for p in location_text.replace(' - ', ',').replace('-', ',').replace('/', ',').split(',')]
        
        # Build candidate list with various parsing strategies
        candidates = []
        for part in parts:
            if len(part) >= 2:
                candidates.append(part)
                words = part.split()
                # Add first word
                if len(words) > 1 and len(words[0]) >= 2:
                    candidates.append(words[0])
                # Add first two words (for "Kuala Lumpur", "Sao Paulo", "Hong Kong" etc)
                if len(words) >= 2:
                    two_words = ' '.join(words[:2])
                    if two_words != part:
                        candidates.append(two_words)
                # Add first three words (for "Sao Paulo Edificio" type patterns)
                if len(words) >= 3:
                    three_words = ' '.join(words[:3])
                    if three_words != part:
                        candidates.append(three_words)
        
        for candidate in candidates:
            # Query city_country_map - prefer larger cities (by population)
            cursor.execute("""
                SELECT country FROM city_country_map 
                WHERE LOWER(city_ascii) = LOWER(%s) OR LOWER(city) = LOWER(%s)
                ORDER BY population DESC NULLS LAST
                LIMIT 1
            """, (candidate, candidate))
            result = cursor.fetchone()
            if result:
                return result['country']
        
        return None
    
    def _extract_country(self, cursor, job_description: str, location_city: str) -> str:
        """
        Extract country from job description or city name.
        
        Args:
            cursor: Database cursor
            job_description: Full job description text
            location_city: City name from API
            
        Returns:
            Country name or None
        """
        # First try to extract from job description "Location: City, Country" pattern
        if job_description:
            desc_lower = job_description.lower()
            for country in ['india', 'singapore', 'germany', 'united kingdom', 'united states', 'japan', 'hong kong']:
                if 'location:' in desc_lower and country in desc_lower:
                    return country.title()
        
        # Fall back to city_country_map table lookup
        return self._lookup_country_from_db(cursor, location_city)
    
    def fetch_job_description(self, job_url: str) -> dict:
        """
        Fetch full job description from job detail page.
        
        Args:
            job_url: Full URL to job posting
            
        Returns:
            dict with 'description' and 'raw_html' fields
        """
        try:
            response = requests.get(job_url, timeout=15)
            if response.status_code != 200:
                return {
                    'description': None,
                    'error': f"HTTP {response.status_code}"
                }
            
            html = response.text
            
            # Parse description from meta tag
            parser = JobDescriptionParser()
            parser.feed(html)
            
            return {
                'description': parser.description,
                'raw_html_length': len(html)
            }
            
        except Exception as e:
            return {
                'description': None,
                'error': str(e)
            }
    
    def process(self):
        """
        Fetch jobs from Workday API and write to postings_staging.
        
        Expected input:
        {
            "max_jobs": 20,
            "search_text": "",
            "interaction_id": 123,
            "skip_rate_limit": false
        }
        
        Returns:
        {
            "status": "success" | "[RATE_LIMITED]" | "[FAILED]",
            "jobs_fetched": 10,
            "staging_ids": [101, 102, ...],
            "jobs_preview": [...]
        }
        """
        # Extract parameters (DB API limit is 20)
        max_jobs = self.input_data.get('max_jobs', 20)
        search_text = self.input_data.get('search_text', '')
        interaction_id = self.input_data.get('interaction_id')
        skip_rate_limit = self.input_data.get('skip_rate_limit', True)  # Disabled rate limit
        
        cursor = self.db_conn.cursor()
        
        # Check rate limit unless skipped
        if not skip_rate_limit:
            cursor.execute("""
                SELECT COUNT(*) as count FROM postings
                WHERE source = 'deutsche_bank'
                  AND DATE(first_seen_at) = CURRENT_DATE
            """)
            
            row = cursor.fetchone()
            if row and row['count'] > 0:
                return {
                    "status": "[RATE_LIMITED]",
                    "message": f"Already fetched {row['count']} jobs today",
                    "jobs_fetched": 0
                }
        
        # Fetch jobs from Workday API with pagination (max 20 per request)
        all_posting_ids = []
        all_seen_urls = []  # Track ALL URLs seen in API (for invalidation detection)
        total_jobs_processed = 0  # Track all jobs processed, not just inserted
        total_jobs_new = 0  # New insertions
        total_jobs_updated = 0  # Existing jobs (last_seen_at updated)
        invalidated_jobs = []  # Jobs removed from site
        
        # Validation stats (Defense in Depth - Nov 26, 2025)
        stats = {
            'jobs_skipped_no_description': 0,
            'jobs_skipped_short_description': 0,
            'jobs_skipped_no_title': 0
        }
        
        total_available = 0
        offset = 0
        batch_num = 1
        consecutive_zero_batches = 0  # Track batches with no new jobs
        MAX_ZERO_BATCHES = 5  # Stop after 5 consecutive batches with no new jobs
        
        try:
            # Keep fetching until we have max_jobs NEW insertions or exhausted API
            while total_jobs_new < max_jobs:
                # Always fetch max batch size - we need to scan through existing jobs
                batch_size = self.MAX_JOBS_PER_REQUEST
                
                payload = {
                    "appliedFacets": {},
                    "limit": batch_size,
                    "offset": offset,
                    "searchText": search_text
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                # DEBUG: Write to file
                with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                    f.write(f"\n=== Batch {batch_num} ===\n")
                    f.write(f"Payload: {json.dumps(payload)}\n")
                
                response = requests.post(
                    self.API_URL,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=30,
                    verify=True
                )
                
                with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                    f.write(f"Status: {response.status_code}\n")
                
                if response.status_code != 200:
                    # Log response for debugging
                    try:
                        error_detail = response.json()
                    except:
                        error_detail = response.text[:200]
                        
                    return {
                        "status": "[FAILED]",
                        "error": f"API returned {response.status_code} on batch {batch_num}: {error_detail}",
                        "jobs_fetched": len(all_posting_ids),
                        "batches_completed": batch_num - 1
                    }
                
                data = response.json()
                jobs = data.get('jobPostings', [])
                total_available = data.get('total', 0)
                
                if not jobs:
                    # No more jobs available
                    break
                
                # Insert jobs from this batch into postings table
                batch_posting_ids = []
                for idx, job in enumerate(jobs, 1):
                    total_jobs_processed += 1  # Count every job we process
                    
                    # Stop if we've inserted enough NEW jobs
                    if total_jobs_new >= max_jobs:
                        break
                    
                    try:
                        # Build full URL - externalPath is like "/job/Mumbai-Nirlon-Kno.../R0403060"
                        external_path = job.get('externalPath') or ''
                        job_url = f"https://db.wd3.myworkdayjobs.com/DBWebSite{external_path}"
                        all_seen_urls.append(job_url)  # Track for invalidation check
                        
                        bulletFields = job.get('bulletFields', [])
                        job_id = bulletFields[0] if bulletFields and len(bulletFields) > 0 else external_path or 'unknown'
                        
                        # Validate externalPath exists (required for posting_position_uri NOT NULL)
                        if not external_path:
                            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                                f.write(f"  Job {idx}/{len(jobs)}: SKIPPED - no externalPath\n")
                            continue
                        
                        # Check if job already exists in postings table by external_job_id (unique)
                        cursor.execute("""
                            SELECT posting_id 
                            FROM postings
                            WHERE external_job_id = %s AND invalidated = false
                        """, (job_id,))
                        
                        existing_posting = cursor.fetchone()
                        
                        if existing_posting:
                            # Job exists - update last_seen_at
                            cursor.execute("""
                                UPDATE postings
                                SET last_seen_at = CURRENT_TIMESTAMP,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE posting_id = %s
                            """, (existing_posting['posting_id'],))
                            total_jobs_updated += 1
                            
                            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                                f.write(f"  Job {idx}/{len(jobs)}: EXISTS (posting_id={existing_posting['posting_id']}) - updated last_seen_at\n")
                            
                            continue  # Skip to next job
                        
                        # New job - fetch full description from detail page
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            f.write(f"  Job {idx}/{len(jobs)}: NEW - Fetching description for {job['title'][:50]}...\n")
                            f.write(f"    external_path: {external_path}\n")
                        
                        job_details = self.fetch_job_description(job_url)
                        
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            desc_len = len(job_details.get('description', '')) if job_details.get('description') else 0
                            f.write(f"    Description: {desc_len} chars" + 
                                  (f", Error: {job_details.get('error')}" if job_details.get('error') else '') + "\n")
                        
                        # DEFENSE IN DEPTH: Validate job data before insertion (Nov 26, 2025)
                        job_description = (job_details.get('description') or '').strip()
                        
                        if not job_description:
                            logger.warning(f"Skipping job {job_id}: job_description is NULL")
                            stats['jobs_skipped_no_description'] = stats.get('jobs_skipped_no_description', 0) + 1
                            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                                f.write(f"    SKIPPED: No description\n")
                            continue
                        
                        if len(job_description) < 100:
                            logger.warning(f"Skipping job {job_id}: job_description too short ({len(job_description)} chars)")
                            stats['jobs_skipped_short_description'] = stats.get('jobs_skipped_short_description', 0) + 1
                            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                                f.write(f"    SKIPPED: Description too short ({len(job_description)} chars)\n")
                            continue
                        
                        if not job.get('title'):
                            logger.warning(f"Skipping job {job_id}: job_title is NULL")
                            stats['jobs_skipped_no_title'] = stats.get('jobs_skipped_no_title', 0) + 1
                            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                                f.write(f"    SKIPPED: No title\n")
                            continue
                        
                        # Extract location_country from job description or city
                        location_city = job.get('locationsText', '')
                        location_country = self._extract_country(cursor, job_details.get('description', ''), location_city)
                        
                        # Insert directly into postings table with status='pending'
                        cursor.execute("""
                            INSERT INTO postings (
                                posting_name,
                                job_title,
                                job_description,
                                location_city,
                                location_country,
                                external_job_id,
                                external_id,
                                external_url,
                                source,
                                posting_status,
                                first_seen_at,
                                last_seen_at,
                                source_metadata,
                                created_by_interaction_id
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
                                %s::jsonb, %s
                            ) RETURNING posting_id
                        """, (
                            job['title'],  # posting_name
                            job['title'],  # job_title
                            job_details.get('description'),  # job_description
                            location_city,  # location_city
                            location_country,  # location_country
                            job_id,  # external_job_id
                            job_id,  # external_id (same as external_job_id)
                            job_url,  # external_url
                            'deutsche_bank',  # source
                            json.dumps({
                                'posted_on': job.get('postedOn', ''),
                                'external_path': external_path,
                                'api_response': job,
                                'description_fetch_error': job_details.get('error')
                            }),  # source_metadata
                            interaction_id  # created_by_interaction_id
                        ))
                        
                        posting_id = cursor.fetchone()['posting_id']
                        batch_posting_ids.append(posting_id)
                        total_jobs_new += 1
                        
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            f.write(f"    Inserted posting_id: {posting_id}\n")
                        
                    except Exception as e:
                        # Log insertion errors
                        error_msg = str(e)
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            f.write(f"  Insert error: {error_msg}\n")
                        # Rollback to recover from aborted transaction
                        try:
                            self.db_conn.rollback()
                        except:
                            pass
                        continue
                
                # Commit this batch (only if we have jobs to commit)
                if batch_posting_ids:
                    try:
                        self.db_conn.commit()
                    except Exception as e:
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            f.write(f"Commit error: {str(e)}\n")
                        self.db_conn.rollback()
                        batch_posting_ids = []
                all_posting_ids.extend(batch_posting_ids)
                
                with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                    f.write(f"Batch {batch_num}: Inserted {len(batch_posting_ids)} jobs\n")
                
                # Track consecutive zero batches
                if len(batch_posting_ids) == 0:
                    consecutive_zero_batches += 1
                    if consecutive_zero_batches >= MAX_ZERO_BATCHES:
                        with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                            f.write(f"\n=== STOPPING: {MAX_ZERO_BATCHES} consecutive batches with no new jobs ===\n")
                        break
                else:
                    consecutive_zero_batches = 0  # Reset counter
                
                # Check if we got fewer jobs than requested (last page)
                if len(jobs) < batch_size:
                    break
                
                # Safety: Stop if offset exceeds total_available (API pagination wrapped)
                if total_available > 0 and offset >= total_available:
                    with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                        f.write(f"\n=== STOPPING: offset {offset} >= total_available {total_available} ===\n")
                    break
                
                # Prepare for next batch
                offset += len(jobs)
                batch_num += 1
            
            # NOTE: We do NOT invalidate jobs based on API listing.
            # The API only returns 20 jobs at a time, so we can never see all jobs.
            # Invalidation is handled separately by checking each URL directly.
            # See: scripts/invalidate_removed_postings.py
            
            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                f.write(f"\n=== Fetch Complete ===\n")
                f.write(f"Total URLs seen in API: {len(all_seen_urls)}\n")
                f.write(f"New postings: {total_jobs_new}\n")
                f.write(f"Updated postings: {total_jobs_updated}\n")
            
            # Commit all changes
            self.db_conn.commit()
            
            # Get ALL postings that need processing (no summary yet)
            # This ensures both new AND existing postings get workflow runs
            cursor.execute("""
                SELECT posting_id
                FROM postings
                WHERE posting_status = 'pending'
                  AND extracted_summary IS NULL
                  AND job_description IS NOT NULL
                ORDER BY posting_id
            """)
            postings_to_process = [row['posting_id'] for row in cursor.fetchall()]
            
            with open('/tmp/db_job_fetcher_debug.txt', 'a') as f:
                f.write(f"Postings to process (no summary): {len(postings_to_process)}\n")
                f.write(f"New in this fetch: {len(all_posting_ids)}\n")
            
            # Fetch full details of inserted jobs for trace report
            cursor.execute("""
                SELECT 
                    posting_id,
                    posting_name,
                    job_title,
                    location_city,
                    external_url,
                    source_metadata,
                    first_seen_at
                FROM postings
                WHERE posting_id = ANY(%s)
                ORDER BY posting_id
            """, (all_posting_ids,))
            
            full_jobs = cursor.fetchall()
            
            return {
                "status": "success",
                "jobs_fetched": total_jobs_new,
                "jobs_updated": total_jobs_updated,
                "jobs_skipped_no_description": stats['jobs_skipped_no_description'],
                "jobs_skipped_short_description": stats['jobs_skipped_short_description'],
                "jobs_skipped_no_title": stats['jobs_skipped_no_title'],
                "total_available": total_available,
                "batches_fetched": batch_num,
                "posting_ids": postings_to_process,  # ALL postings needing processing, not just new ones
                "posting_ids_new": all_posting_ids,  # Keep track of just-inserted ones
                "jobs_full_data": [
                    {
                        "posting_id": job['posting_id'],
                        "posting_name": job['posting_name'],
                        "job_title": job['job_title'],
                        "location": job['location_city'],
                        "external_url": job['external_url'],
                        "source_metadata": job['source_metadata'],
                        "first_seen_at": job['first_seen_at'].isoformat() if job['first_seen_at'] else None
                    }
                    for job in full_jobs
                ]
            }
            
        except Exception as e:
            self.db_conn.rollback()
            import traceback
            return {
                "status": "[FAILED]",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "jobs_fetched": 0
            }


if __name__ == '__main__':
    actor = DBJobFetcher()
    actor.run()
