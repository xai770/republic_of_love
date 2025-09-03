#!/usr/bin/env python3
"""
Job API Fetcher v6.1
====================

Fetches job postings from Deutsche Bank API and creates structured JSON format
for requirements extraction pipelines.

Features:
- Deutsche Bank API integration with pagination
- Job description extraction via API and web scraping
- Structured JSON output format
- Duplicate detection and incremental updates
- Comprehensive error handling

Author: Sandy
Version: 6.1.0
Date: July 18, 2025
"""

import json
import logging
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import sys
import re
from urllib.parse import urljoin
import hashlib
from bs4 import BeautifulSoup

# Add project root to path
# Configure logging
logger = logging.getLogger(__name__)

# Self-contained config for ty_extract
def get_ty_extract_config():
    """Get configuration for ty_extract pipeline"""
    return {
        'data_dir': 'data/postings',
        'output_dir': 'output',
        'pipeline_version': '7.0',
        'extractor_version': '1.0.0'
    }

class JobApiFetcher:
    """
    Fetches job postings from Deutsche Bank API with structured JSON output
    """
    
    def __init__(self):
        self.config = get_ty_extract_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Directory setup
        self.data_dir = Path(self.config['data_dir'])
        self.scan_progress_file = self.data_dir.parent / "job_scans" / "search_api_scan_progress.json"
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scan_progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # API Configuration
        self.api_base_url = "https://api-deutschebank.beesite.de/search/"
        self.career_site_base = "https://careers.db.com"
        self.api_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        self.logger.info("Job API Fetcher v6.1 initialized")
    
    def _cleanup_legacy_method(self):
        """Removed legacy _setup_logging method"""
        pass
    
    def create_job_structure(self, 
                           job_api_data: Dict[str, Any], 
                           job_description: str = "", 
                           specialist_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create structured JSON format for job data
        """
        descriptor = job_api_data.get("MatchedObjectDescriptor", {})
        job_id = job_api_data.get("MatchedObjectId", "unknown")
        
        # Extract location data
        location_data = descriptor.get("PositionLocation", [{}])[0] if descriptor.get("PositionLocation") else {}
        
        # Extract employment details
        employment_type = descriptor.get("PositionOfferingType", [{}])[0].get("Name", "") if descriptor.get("PositionOfferingType") else ""
        schedule = descriptor.get("PositionSchedule", [{}])[0].get("Name", "") if descriptor.get("PositionSchedule") else ""
        career_level = descriptor.get("CareerLevel", [{}])[0].get("Name", "") if descriptor.get("CareerLevel") else ""
        
        # Create processing log entry
        now = datetime.now().isoformat()
        processing_log = [
            {
                "timestamp": now,
                "action": "job_fetched",
                "processor": "job_api_fetcher_v6.1",
                "status": "success",
                "details": f"Successfully fetched job {job_id} from Deutsche Bank API"
            }
        ]
        
        # Add description enrichment log if we got it
        if job_description:
            processing_log.append({
                "timestamp": now,
                "action": "description_enriched", 
                "processor": "web_scraper",
                "status": "success",
                "details": f"Successfully fetched job description ({len(job_description)} characters)"
            })
        else:
            processing_log.append({
                "timestamp": now,
                "action": "description_enriched",
                "processor": "web_scraper", 
                "status": "partial_failure",
                "details": "Job description not available from source",
                "warning": "Description field will be empty"
            })
        
        # Add specialist analysis log if available
        if specialist_analysis:
            processing_log.append({
                "timestamp": now,
                "action": "specialist_analysis",
                "processor": "direct_specialist_manager",
                "status": "success",
                "details": f"Specialist analysis completed with {specialist_analysis.get('specialist_used', 'unknown')} specialist"
            })
        
        # Create the structured job data
        job_data = {
            "job_metadata": {
                "job_id": job_id,
                "version": "1.0",
                "created_at": now,
                "last_modified": now,
                "source": "deutsche_bank_api",
                "processor": "job_api_fetcher_v6.1",
                "status": "fetched"
            },
            
            "job_content": {
                "title": descriptor.get("PositionTitle", ""),
                "description": job_description,
                "requirements": self._extract_requirements(job_description),
                "location": {
                    "city": location_data.get("CityName", ""),
                    "state": location_data.get("CountrySubDivisionName", ""),
                    "country": location_data.get("CountryName", ""),
                    "remote_options": False  # Default, could be parsed from description
                },
                "employment_details": {
                    "type": employment_type,
                    "schedule": schedule,
                    "career_level": career_level,
                    "salary_range": None,  # Not available in API
                    "benefits": []  # Could be extracted from description
                },
                "organization": {
                    "name": "Deutsche Bank",
                    "division": descriptor.get("OrganizationName", ""),
                    "division_id": descriptor.get("UserArea", {}).get("ProDivision")
                },
                "posting_details": {
                    "publication_date": descriptor.get("PublicationStartDate", ""),
                    "position_uri": descriptor.get("PositionURI", ""),
                    "hiring_year": descriptor.get("PositionHiringYear", "")
                }
            },
            
            "evaluation_results": {
                # Will be populated later during evaluation
                "cv_to_role_match": None,
                "match_confidence": None,
                "evaluation_date": None,
                "evaluator": None,
                "domain_knowledge_assessment": None,
                "decision": {
                    "apply": None,
                    "rationale": None,
                    "estimated_prep_time": None
                },
                "strengths": [],
                "weaknesses": []
            },
            
            "processing_log": processing_log,
            
            "raw_source_data": {
                "api_response": job_api_data,
                "specialist_analysis": specialist_analysis or {},
                "description_source": "web_scraping" if job_description else "unavailable"
            }
        }
        
        return job_data
    
    def _extract_requirements(self, description: str) -> List[str]:
        """
        Extract requirements from job description using pattern matching
        """
        if not description:
            return []
            
        requirements = []
        
        # Look for common requirement patterns
        patterns = [
            r"(?:require[sd]?|must have|essential|mandatory):\s*(.+?)(?:\n|$)",
            r"(?:qualifications?|requirements?):\s*(.+?)(?:\n|$)",
            r"(?:experience in|experience with|knowledge of)\s+(.+?)(?:\n|,|$)",
            r"(?:minimum|at least)\s+(\d+\+?\s*years?.+?)(?:\n|,|$)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                clean_req = match.strip().rstrip('.,;')
                if clean_req and len(clean_req) > 10:  # Filter out too short matches
                    requirements.append(clean_req)
        
        return list(set(requirements))  # Remove duplicates
    
    def _should_skip_existing_job(self, job_file: Path, job_id: str, allow_processed: bool = False) -> bool:
        """
        Check if an existing job file should be skipped because it contains valuable analysis data.
        
        Args:
            job_file (Path): Path to the existing job file
            job_id (str): Job ID for logging
            allow_processed (bool): If True, will not skip processed jobs
            
        Returns:
            bool: True if the job should be skipped (has valuable data), False if it should be updated
        """
        if allow_processed:
            return False
            
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                existing_job = json.load(f)
            
            # Check for valuable analysis fields that indicate processing has been done
            valuable_fields = [
                'llama32_evaluation',
                'cv_analysis', 
                'skill_match',
                'domain_match',
                'ai_processed',
                'evaluation_results',
                'job_insights'
            ]
            
            # If any valuable fields exist, skip this job
            for field in valuable_fields:
                if existing_job.get(field):
                    logger.debug(f"Skipping job {job_id} - contains valuable {field} data")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking job {job_id}: {str(e)}")
            return False  # Don't skip on error
    
    def fetch_job_description(self, job_id: str, position_uri: str = "") -> str:
        """
        Fetch full job description using API endpoint
        """
        try:
            # Use the API endpoint for job details
            api_url = f"https://api-deutschebank.beesite.de/jobhtml/{job_id}.json"
            
            self.logger.info(f"Fetching description for job {job_id} from API")
            
            response = requests.get(api_url, headers=self.api_headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    job_data = response.json()
                    
                    # Extract HTML content
                    html_content = job_data.get('html', '').strip()
                    
                    if html_content:
                        # Clean the HTML and extract meaningful text
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text content
                        text = soup.get_text()
                        
                        # Clean up whitespace
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        if text and len(text) > 100:  # Ensure we got substantial content
                            self.logger.info(f"Successfully extracted {len(text)} characters from job {job_id}")
                            return text
                        else:
                            self.logger.warning(f"Job {job_id} returned insufficient content")
                            return ""
                    else:
                        self.logger.warning(f"Job {job_id} returned empty HTML content")
                        return ""
                        
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON response for job {job_id}")
                    return ""
            else:
                self.logger.warning(f"API request failed for job {job_id}: {response.status_code}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error fetching description for job {job_id}: {str(e)}")
            return ""
    
    def fetch_jobs(self, max_jobs: int = 60, quick_mode: bool = False, search_criteria: Optional[Dict] = None, force_reprocess: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch jobs from Deutsche Bank API with pagination
        
        Args:
            max_jobs (int): Maximum number of jobs to fetch
            quick_mode (bool): If True, skip delays between requests
            search_criteria (Optional[Dict]): Search criteria for filtering jobs
            force_reprocess (bool): If True, refetch existing jobs
            
        Returns:
            List[Dict[str, Any]]: List of structured job data
        """
        
        # Extract location criteria for Frankfurt focus
        location_criteria = search_criteria.get("criteria", {}).get("locations", {}) if search_criteria else {}
        country_codes = location_criteria.get("country_codes", [46])  # Germany
        city_codes = location_criteria.get("city_codes", [1698])      # Frankfurt
        
        self.logger.info(f"Fetching up to {max_jobs} jobs (quick_mode: {quick_mode})")
        self.logger.info(f"Using search criteria: Country codes {country_codes}, City codes {city_codes}")
        
        # Prepare API request with search criteria
        search_criteria_list = []
        
        # Add country filter
        if country_codes:
            search_criteria_list.append({
                "CriterionName": "PositionLocation.CountryCode",
                "CriterionValue": country_codes
            })
        
        # Add city filter
        if city_codes:
            search_criteria_list.append({
                "CriterionName": "PositionLocation.CityCode", 
                "CriterionValue": city_codes
            })
        
        # Track existing jobs to avoid duplicates
        existing_job_ids = set()
        enhanced_jobs = []
        current_job_count = 0
        allow_processed = False  # We want fresh data
        
        # Scan existing jobs to build ID set
        for job_file in self.data_dir.glob("job*.json"):
            job_id = job_file.stem.replace("job", "")
            existing_job_ids.add(job_id)
        
        # Fetch jobs with pagination
        for page in range(1, 50):  # Reasonable upper limit
            self.logger.info(f"Fetching page {page} of jobs...")
            
            # API request parameters
            api_params = {
                "MatchedObjectDescriptor": {
                    "MatchedObjectDescriptorValue": [
                        "PositionTitle",
                        "PositionFormattedDescription.Content",  
                        "PositionLocation.CountryName",
                        "PositionLocation.CountrySubDivisionName", 
                        "PositionLocation.CityName",
                        "OrganizationName",
                        "PositionOfferingType.Name",
                        "PositionSchedule.Name",
                        "CareerLevel.Name",
                        "PublicationStartDate",
                        "PositionHiringYear",
                        "UserArea.ProDivision"
                    ],
                    "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}]
                },
                "SearchCriteria": search_criteria_list
            }
            
            try:
                response = requests.post(
                    self.api_base_url,
                    json=api_params,
                    headers=self.api_headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.logger.error(f"API request failed: {response.status_code}")
                    break
                
                data = response.json()
                
                if "SearchResult" not in data or "SearchResultItems" not in data["SearchResult"]:
                    self.logger.error("Invalid API response structure")
                    break
                
                jobs = data["SearchResult"]["SearchResultItems"]
                self.logger.info(f"Received {len(jobs)} jobs from API")
                
                if not jobs:  # No more jobs found
                    break
                
                for job in jobs:
                    job_id = job.get("MatchedObjectId", "")
                    if not job_id:
                        continue
                        
                    # Skip if we already have enough jobs
                    if current_job_count >= max_jobs:
                        break
                        
                    # Skip if we've already seen this job and we're not reprocessing
                    if job_id in existing_job_ids and not allow_processed and not force_reprocess:
                        continue
                    
                    try:
                        job_file = self.data_dir / f"job{job_id}.json"
                        if job_file.exists() and not force_reprocess:
                            if allow_processed:
                                self.logger.info(f"Job {job_id} exists and allow_processed=True - using it")
                                with open(job_file, 'r', encoding='utf-8') as f:
                                    existing_job = json.load(f)
                                    enhanced_jobs.append(existing_job)
                                    current_job_count += 1
                                continue
                            else:
                                should_skip = self._should_skip_existing_job(job_file, job_id, allow_processed)
                                if should_skip:
                                    continue
                                
                        # Get job description
                        descriptor = job.get("MatchedObjectDescriptor", {})
                        api_description = descriptor.get("PositionFormattedDescription", {}).get("Content", "")
                        
                        if not api_description:
                            position_uri = descriptor.get("PositionURI", "")
                            if position_uri:
                                api_description = self.fetch_job_description(job_id, position_uri)
                        
                        # Create and save job
                        job_data = self.create_job_structure(
                            job_api_data=job,
                            job_description=api_description
                        )
                        
                        with open(job_file, 'w', encoding='utf-8') as f:
                            json.dump(job_data, f, indent=2, ensure_ascii=False)
                        
                        enhanced_jobs.append(job_data)
                        current_job_count += 1
                        
                        self.logger.info(f"Saved job {job_id}: {job_data['job_content']['title']}")
                        
                        # Be nice to the servers
                        if not quick_mode:
                            time.sleep(self.config.job_search.search_delay_seconds)
                            
                    except Exception as e:
                        self.logger.error(f"Error processing job {job_id}: {e}")
                        continue
                
                # If no new jobs were found in this batch, move to next page
                if current_job_count >= max_jobs:
                    self.logger.info(f"Reached target job count: {max_jobs}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break
                
        self.logger.info(f"Fetched {len(enhanced_jobs)} jobs total")
        return enhanced_jobs
