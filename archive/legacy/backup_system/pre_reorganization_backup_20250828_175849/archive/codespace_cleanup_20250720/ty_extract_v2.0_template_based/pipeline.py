"""
TY_EXTRACT Core Pipeline
=======================

Minimal pipeline that matches run_daily_report.py outputs with drastically
reduced complexity.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import get_config, get_data_dir, get_output_dir
from extractors import MinimalExtractor, MinimalLocationValidator
from generators_fixed import ExcelGenerator, MarkdownGenerator  # Use fixed generators
from job_api_fetcher_v6 import JobApiFetcher

logger = logging.getLogger(__name__)

class TyPipeline:
    """Minimal pipeline that matches run_daily_report.py outputs"""
    
    def __init__(self):
        self.config = get_config()
        self.data_dir = get_data_dir()
        self.output_dir = get_output_dir()
        
        # Initialize components
        self.job_fetcher = JobApiFetcher()
        self.extractor = MinimalExtractor()
        self.location_validator = MinimalLocationValidator()
        self.excel_generator = ExcelGenerator(self.output_dir)
        self.markdown_generator = MarkdownGenerator(self.output_dir)
        
        logger.info("TyPipeline initialized successfully")
    
    def run(self, max_jobs: int = 1, fetch_fresh: bool = False) -> Dict[str, Any]:
        """Run the pipeline on the specified number of jobs"""
        
        start_time = datetime.now()
        logger.info(f"TyPipeline: Starting report generation for {max_jobs} jobs...")
        
        # Fetch fresh jobs if requested
        if fetch_fresh:
            logger.info("Fetching fresh jobs from API...")
            try:
                self.job_fetcher.fetch_jobs(max_jobs=max_jobs, quick_mode=True)
                logger.info("✅ Fresh jobs fetched successfully")
            except Exception as e:
                logger.error(f"❌ Failed to fetch fresh jobs: {e}")
                logger.info("Continuing with existing job data...")
        
        # Load job data
        job_data = self._load_job_data(max_jobs)
        if not job_data:
            logger.error("No jobs found to process")
            return {"error": "No jobs available for processing"}
        
        # Process jobs
        processed_jobs = []
        for i, job in enumerate(job_data, 1):
            print(f"\n🔄 Processing job {i}/{len(job_data)}: {job.get('title', 'Unknown Title')}")
            
            processed_job = self._process_single_job(job)
            if processed_job:
                processed_jobs.append(processed_job)
            else:
                logger.warning(f"❌ Failed to process job {i}")
        
        if not processed_jobs:
            logger.error("No jobs were successfully processed")
            return {"error": "Failed to process any jobs"}
        
        # Generate reports
        try:
            excel_path = self.excel_generator.generate_report(processed_jobs, self.config)
            markdown_path = self.markdown_generator.generate_report(processed_jobs, self.config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Calculate skills summary
            total_technical = sum(len(job.get('technical_requirements', '').split(';')) for job in processed_jobs)
            total_business = sum(len(job.get('business_requirements', '').split(';')) for job in processed_jobs)
            total_soft = sum(len(job.get('soft_skills', '').split(';')) for job in processed_jobs)
            
            logger.info("✅ TyPipeline: Report generation completed successfully")
            
            return {
                "jobs": processed_jobs,
                "metadata": {
                    "total_jobs_processed": len(processed_jobs),
                    "total_skills_extracted": total_technical + total_business + total_soft,
                    "pipeline_version": self.config['pipeline_version'],
                    "extractor_version": self.config['extractor_version'],
                    "duration": duration,
                    "excel_report": excel_path,
                    "markdown_report": markdown_path
                },
                "summary": {
                    "skills_by_category": {
                        "Technical": total_technical,
                        "Business": total_business,
                        "Soft": total_soft
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            return {"error": f"Report generation failed: {e}"}
    
    def _load_job_data(self, max_jobs: int) -> List[Dict[str, Any]]:
        """Load job data from JSON files"""
        
        json_files = list(self.data_dir.glob("*.json"))
        if not json_files:
            logger.error(f"No JSON files found in {self.data_dir}")
            return []
        
        # Take only the requested number of jobs (same as baseline pipeline)
        json_files = json_files[:max_jobs]
        
        job_data = []
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                # Extract job information from the nested structure
                if 'job_content' in raw_data:
                    job_content = raw_data['job_content']
                    job_metadata = raw_data.get('job_metadata', {})
                    organization = job_content.get('organization', {})
                    location_data = job_content.get('location', {})
                    
                    job_data.append({
                        'id': job_metadata.get('job_id', json_file.stem),
                        'title': job_content.get('title', 'Unknown Position'),
                        'description': job_content.get('description', ''),
                        'location': location_data,
                        'company': organization.get('name', 'Company not specified'),
                        'division': organization.get('division', ''),
                        'url': f"https://jobs.db.com/job/{job_metadata.get('job_id', '')}",
                        'metadata': job_metadata
                    })
                    
                    logger.info(f"✅ Loaded: {json_file.name}")
                else:
                    logger.warning(f"⚠️ Invalid job structure in {json_file.name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load {json_file.name}: {e}")
        
        logger.info(f"✅ Loaded {len(job_data)} jobs for processing")
        return job_data
    
    def _process_single_job(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single job with minimal extraction"""
        
        job_title = job.get('title', 'Unknown Title')
        job_description = job.get('description', '')
        
        if not job_description:
            logger.warning(f"No description found for job: {job_title}")
            return None
        
        try:
            # Extract job data using minimal extractor
            extracted_data = self.extractor.extract_job_data(job_description, job_title)
            
            # Validate location
            location_metadata = str(job.get('location', ''))
            location_validation = self.location_validator.validate_location(location_metadata, job_description, job_title)
            
            # Create comprehensive job data
            processed_job = {
            "job_id": job.get('id', 'Unknown ID'),
            "position_title": job_title,  # Changed from "title" to "position_title"
            "company": job.get('company', 'Company not specified'),
            "division": job.get('division', ''),
            "full_content": job_description,  # Changed from "description" to "full_content"
            "validated_location": location_validation['validated_location'],
            "metadata_location": location_validation['metadata_location'],
            "location_validation_result": location_validation['location_validation_result'],
            "url": job.get('url', ''),
            
            # Extracted requirements - Fixed field mapping to match markdown generator expectations
            "technical_skills": extracted_data['technical_requirements'],  # Changed from technical_requirements
            "business_skills": extracted_data['business_requirements'],   # Changed from business_requirements
            "soft_skills": extracted_data['soft_skills'],                 # This was already correct
            "experience_required": extracted_data['experience_requirements'],  # Changed from experience_requirements
            "education_required": extracted_data['education_requirements'],     # Changed from education_requirements
            "concise_description": extracted_data['concise_description'],
            "extracted_skills": extracted_data['extracted_skills'],
            
            # Metadata
            "processed_at": datetime.now().isoformat(),
            "processing_timestamp": datetime.now().isoformat(),
            "pipeline_version": self.config['pipeline_version'],
            "extraction_method": "comprehensive"
            }
            
            logger.info(f"✅ Successfully processed job: {job_title}")
            return processed_job
        
        except Exception as e:
            logger.error(f"❌ Error processing job '{job_title}': {e}")
            return None

