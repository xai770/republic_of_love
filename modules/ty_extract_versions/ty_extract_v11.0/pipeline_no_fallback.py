"""
TY_EXTRACT V11.0 - NO FALLBACK PIPELINE
=======================================

PHILOSOPHY: FAIL FAST, NO COMPROMISES
- LLM required or crash
- Data missing -> crash
- Extraction failed -> crash
- Better to know we failed than lie about success
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from config import get_config, get_data_dir, get_output_dir
from extractors_no_fallback import NoFallbackExtractor, MinimalLocationValidator
from generators_no_fallback import NoFallbackExcelGenerator, NoFallbackMarkdownGenerator
from job_api_fetcher_v6 import JobApiFetcher

logger = logging.getLogger(__name__)

class NoFallbackPipeline:
    """V11.0 Pipeline with NO FALLBACKS - honest results only"""
    
    def __init__(self):
        try:
            self.config = get_config()
            self.data_dir = get_data_dir()
            self.output_dir = get_output_dir()
            
            # Initialize V11.0 components - CRASH if any fail
            logger.info("🚀 Initializing V11.0 NO FALLBACK pipeline...")
            
            self.job_fetcher = JobApiFetcher()
            self.extractor = NoFallbackExtractor()  # CRASH if LLM unavailable
            self.location_validator = MinimalLocationValidator()
            self.excel_generator = NoFallbackExcelGenerator(self.output_dir)
            self.markdown_generator = NoFallbackMarkdownGenerator(self.output_dir)
            
            logger.info("✅ V11.0 Pipeline initialized - NO FALLBACKS active")
            
        except Exception as e:
            logger.error(f"❌ V11.0 Pipeline initialization FAILED: {e}")
            raise RuntimeError(f"V11.0 pipeline startup failed: {e}") from e
    
    def run(self, max_jobs: int = 1, fetch_fresh: bool = False) -> Dict[str, Any]:
        """Run V11.0 pipeline - FAIL FAST on any error"""
        
        start_time = datetime.now()
        logger.info(f"🚀 V11.0 Pipeline starting: {max_jobs} jobs (NO FALLBACKS)")
        
        try:
            # Fetch fresh jobs if requested
            if fetch_fresh:
                logger.info("📥 Fetching fresh jobs...")
                self.job_fetcher.fetch_jobs(max_jobs=max_jobs, quick_mode=True)
            
            # Load jobs - CRASH if none available
            job_data = self._load_jobs(max_jobs)
            if not job_data:
                raise RuntimeError("❌ CRITICAL: No job data available")
            
            logger.info(f"✅ Loaded {len(job_data)} jobs for V11.0 processing")
            
            # Process each job - CRASH on any failure
            processed_jobs = []
            for i, job in enumerate(job_data, 1):
                job_title = job.get('job_content', {}).get('title', 'NO TITLE')
                logger.info(f"🔄 V11.0 processing job {i}/{len(job_data)}: {job_title}")
                
                try:
                    processed_job = self._process_job(job)
                    processed_jobs.append(processed_job)
                    logger.info(f"✅ Job {i} processed successfully")
                    
                except Exception as e:
                    logger.error(f"❌ Job {i} processing FAILED: {e}")
                    raise RuntimeError(f"V11.0 job processing failed at job {i}: {e}") from e
            
            # Generate reports - CRASH on any failure
            try:
                excel_path = self.excel_generator.generate_report(processed_jobs, self.config)
                markdown_path = self.markdown_generator.generate_report(processed_jobs, self.config)
                
            except Exception as e:
                logger.error(f"❌ Report generation FAILED: {e}")
                raise RuntimeError(f"V11.0 report generation failed: {e}") from e
            
            # Calculate results
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "SUCCESS",
                "jobs_processed": len(processed_jobs),
                "duration_seconds": duration,
                "excel_report": excel_path,
                "markdown_report": markdown_path,
                "pipeline_version": "11.0_no_fallback",
                "extraction_method": "qwen3_template_2025_07_20"
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ V11.0 Pipeline FAILED after {duration:.1f}s: {e}")
            raise RuntimeError(f"V11.0 pipeline failed: {e}") from e
    
    def _load_jobs(self, max_jobs: int) -> List[Dict[str, Any]]:
        """Load jobs - CRASH if data issues"""
        
        # Find job files
        json_files = list(self.data_dir.glob("job*.json"))
        if not json_files:
            raise RuntimeError("❌ CRITICAL: No job JSON files found")
        
        # Load jobs
        jobs = []
        for json_file in json_files[:max_jobs]:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                    
                # CRITICAL: Validate nested structure
                job_content = job_data.get('job_content')
                job_metadata = job_data.get('job_metadata')
                
                if not job_content:
                    raise ValueError(f"Job missing job_content: {json_file}")
                if not job_metadata:
                    raise ValueError(f"Job missing job_metadata: {json_file}")
                if not job_content.get('title'):
                    raise ValueError(f"Job missing title: {json_file}")
                if not job_content.get('description'):
                    raise ValueError(f"Job missing description: {json_file}")
                if not job_metadata.get('job_id'):
                    raise ValueError(f"Job missing job_id: {json_file}")
                    
                jobs.append(job_data)
                
            except Exception as e:
                logger.error(f"❌ Failed to load {json_file}: {e}")
                raise RuntimeError(f"Job loading failed: {json_file}") from e
        
        return jobs
    
    def _process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process single job - CRASH on any error"""
        
        job_title = job['job_content']['title']  # CRASH if missing
        
        try:
            # Extract using V11.0 - CRASH if fails
            extracted_data = self.extractor.extract_job_data(job)
            
            # Validate location if present
            location_data = job.get('job_content', {}).get('location')
            if location_data and location_data.get('city'):
                location_str = f"{location_data['city']}, {location_data.get('country', '')}"
                location_result = self.location_validator.validate_location(location_str)
                extracted_data['validated_location'] = location_result['authoritative_location']
                extracted_data['location_validation_result'] = location_result
            
            logger.info(f"✅ V11.0 extraction completed: {job_title}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Job processing FAILED: {job_title}: {e}")
            raise RuntimeError(f"Job processing failed: {job_title}") from e
