"""
Job Extraction Pipeline V7.0
============================

Production-ready pipeline for comprehensive job requirements extraction.
Migrated from Sandy's V7.0 implementation with clean architecture.

🎯 CRITICAL REQUIREMENT: MUST CONFORM TO enhanced_data_dictionary_v4.2.md

REQUIRED OUTPUT FORMAT (12 streamlined columns):
✅ Core Data: Job ID, Position Title, Company, Full Content, Metadata Location
✅ Enhanced Requirements: Concise Description, Validated Location, 5D Requirements Display
✅ Skills Competency: Technical, Business, Soft Skills, Experience, Education  
✅ Processing Metadata: Processing Timestamp, Pipeline Version, Extraction Method

Author: Arden (migrated from Sandy V7.0)
Version: 7.0
Date: 2025-07-19
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .specialists.gemma_concise_extractor import GemmaConciseExtractor
from .specialists.location_validation_v3 import LocationValidationSpecialistV3
from .specialists.job_analyzer_v1 import JobAnalyzerV1
from .specialists.translation_specialist_v1 import TranslationSpecialistV1
from .generators.excel_generator_v4 import ExcelGenerator_v4
from .generators.markdown_generator_v1 import MarkdownGenerator_v1
from .config import Config

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """Production pipeline for comprehensive job requirements extraction"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the extraction pipeline
        
        Args:
            config: Configuration object (uses default if None)
        """
        self.config = config or Config()
        
        # Initialize specialists
        self.gemma_extractor = GemmaConciseExtractor()
        self.location_validator = LocationValidationSpecialistV3()
        self.job_analyzer = JobAnalyzerV1()
        self.translation_specialist = TranslationSpecialistV1()
        
        # Initialize generators
        output_dir = Path(self.config.output_directory)
        output_dir.mkdir(exist_ok=True)
        self.excel_generator = ExcelGenerator_v4(reports_path=output_dir)
        self.markdown_generator = MarkdownGenerator_v1(output_dir=output_dir)
        
        logger.info("ExtractionPipeline V7.0 initialized successfully")
    
    def process_jobs(self, job_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process jobs and generate comprehensive reports
        
        Args:
            job_data: List of job dictionaries to process
            
        Returns:
            Processing results with metadata
        """
        logger.info(f"ExtractionPipeline: Starting processing for {len(job_data)} jobs...")
        
        if not job_data:
            logger.error("No jobs provided to process")
            return {"error": "No jobs available for processing"}
        
        # Process each job
        processed_jobs = []
        for i, job in enumerate(job_data, 1):
            print("\\n" + "=" * 100)
            logger.info(f"🔄 Processing job {i}/{len(job_data)}: {job.get('title', 'Unknown Title')}")
            print("=" * 100 + "\\n")
            
            processed_job = self._process_single_job(job)
            if processed_job:
                processed_jobs.append(processed_job)
            else:
                logger.warning(f"❌ Failed to process job {i}")
        
        if not processed_jobs:
            logger.error("No jobs were successfully processed")
            return {"error": "Failed to process any jobs"}
        
        # Generate reports
        report_results = self._generate_reports(processed_jobs)
        
        # Create return data structure
        report_data = self._create_report_data(processed_jobs)
        
        logger.info("✅ ExtractionPipeline: Processing completed successfully")
        logger.info("=" * 80)
        
        return {
            "jobs": report_data,
            "metadata": {
                "total_jobs_processed": len(processed_jobs),
                "total_skills_extracted": self._count_total_skills(processed_jobs),
                "pipeline_version": "7.0",
                "extractor_version": "1.0"
            },
            "summary": {
                "skills_by_category": self._summarize_skills_by_category(processed_jobs)
            },
            "reports": report_results
        }
    
    def _process_single_job(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single job with comprehensive extraction
        
        Args:
            job: Job dictionary containing title, description, etc.
            
        Returns:
            Processed job data or None if processing failed
        """
        job_title = job.get('title', 'Unknown Title')
        job_description = job.get('description', '')
        
        if not job_description:
            logger.warning(f"No description found for job: {job_title}")
            return None
        
        try:
            # 1. Translation (if needed)
            logger.info(f"Checking language and translating if needed for: {job_title}")
            translation_result = self.translation_specialist.translate_if_needed(job_description)
            processing_text = translation_result['final_text']
            
            if translation_result['was_translated']:
                logger.info(f"✅ German job description translated to English for: {job_title}")
            else:
                logger.debug(f"No translation needed for: {job_title}")
            
            # 2. Basic information extraction
            logger.info(f"Extracting basic info for: {job_title}")
            basic_info = self.gemma_extractor.extract_concise_description(processing_text)
            if not basic_info or basic_info.get('status') != 'success':
                logger.warning(f"Failed to extract basic info for: {job_title}")
                basic_info = {"concise_description": "Extraction failed", "status": "failed"}
            
            # 3. Location validation
            logger.info(f"Validating location for: {job_title}")
            location_metadata = str(job.get('location', ''))
            location_result = self.location_validator.validate_location(location_metadata, processing_text)
            
            if location_result:
                validated_location = location_result.authoritative_location or "Validation pending"
                location_info = {
                    "validated_location": validated_location,
                    "confidence_score": location_result.confidence_score,
                    "conflict_detected": location_result.conflict_detected,
                    "processing_time": location_result.processing_time
                }
            else:
                logger.warning(f"Failed to validate location for: {job_title}")
                location_info = {"validated_location": "Validation pending"}
            
            # 4. Comprehensive job analysis (5D requirements)
            logger.info(f"Analyzing job comprehensively for: {job_title}")
            job_analysis = self.job_analyzer.analyze_job(processing_text)
            
            # Extract fields for Enhanced Data Dictionary v4.2 compliance
            concise_description = basic_info.get('concise_description', 'Not extracted') if basic_info else 'Not extracted'
            validated_location = location_result.authoritative_location if location_result else 'Validation pending'
            technical_requirements = job_analysis.get('technical_requirements', 'Not extracted')
            business_requirements = job_analysis.get('business_requirements', 'Not extracted')
            soft_skills = job_analysis.get('soft_skills', 'Not extracted')
            experience_requirements = job_analysis.get('experience_requirements', 'Not extracted')
            education_requirements = job_analysis.get('education_requirements', 'Not extracted')
            extracted_skills = job_analysis.get('extracted_skills', {})
            
            # Create comprehensive job data structure
            processed_job = {
                # Core identification
                "job_id": job.get('id', job.get('job_id', 'Unknown ID')),
                "position_title": job_title,
                "company": job.get('company', 'Company not specified'),
                "full_content": job_description,
                "metadata_location": str(location_result),
                
                # Enhanced requirements (5D)
                "concise_description": concise_description,
                "validated_location": validated_location,
                "technical_requirements": technical_requirements,
                "business_requirements": business_requirements,
                "soft_skills": soft_skills,
                "experience_requirements": experience_requirements,
                "education_requirements": education_requirements,
                
                # Processing metadata
                "processing_timestamp": datetime.now().isoformat(),
                "pipeline_version": "7.0",
                "extraction_method": "comprehensive",
                
                # Original data and detailed analysis
                "original_data": job,
                "basic_info": basic_info,
                "location_info": location_result,
                "job_analysis": job_analysis,
                "translation_info": translation_result,
                "extracted_skills": extracted_skills
            }
            
            logger.info(f"Successfully processed job: {job_title}")
            return processed_job
            
        except Exception as e:
            logger.error(f"Error processing job '{job_title}': {e}")
            return None
    
    def _generate_reports(self, processed_jobs: List[Dict]) -> Dict[str, str]:
        """Generate Excel and Markdown reports
        
        Args:
            processed_jobs: List of processed job data
            
        Returns:
            Dictionary with report file paths
        """
        results = {}
        
        # Generate Excel report
        try:
            logger.info("🔄 Generating Excel report...")
            excel_path = self.excel_generator.generate_report(processed_jobs)
            results['excel'] = str(excel_path)
            logger.info(f"✅ Excel report generated: {excel_path}")
        except Exception as e:
            logger.error(f"❌ Failed to generate Excel report: {e}")
            results['excel'] = f"Error: {e}"
        
        # Generate Markdown report
        try:
            logger.info("🔄 Generating Markdown report...")
            markdown_path = self.markdown_generator.generate_report(processed_jobs)
            results['markdown'] = str(markdown_path)
            logger.info(f"✅ Markdown report generated: {markdown_path}")
        except Exception as e:
            logger.error(f"❌ Failed to generate Markdown report: {e}")
            results['markdown'] = f"Error: {e}"
        
        return results
    
    def _create_report_data(self, processed_jobs: List[Dict]) -> List[Dict]:
        """Create streamlined report data according to enhanced_data_dictionary_v4.2
        
        Args:
            processed_jobs: List of processed job data
            
        Returns:
            List of streamlined job data for reports
        """
        report_data = []
        
        for job in processed_jobs:
            report_entry = {
                'job_id': job.get('job_id', ''),
                'position_title': job.get('position_title', ''),
                'company': job.get('company', ''),
                'full_content': job.get('full_content', ''),
                'metadata_location': job.get('metadata_location', ''),
                'concise_description': job.get('concise_description', ''),
                'validated_location': job.get('validated_location', ''),
                'technical_requirements': job.get('technical_requirements', ''),
                'business_requirements': job.get('business_requirements', ''),
                'soft_skills': job.get('soft_skills', ''),
                'experience_requirements': job.get('experience_requirements', ''),
                'education_requirements': job.get('education_requirements', ''),
                'processing_timestamp': job.get('processing_timestamp', ''),
                'pipeline_version': job.get('pipeline_version', ''),
                'extraction_method': job.get('extraction_method', '')
            }
            report_data.append(report_entry)
        
        return report_data
    
    def _count_total_skills(self, processed_jobs: List[Dict]) -> int:
        """Count total skills extracted across all jobs
        
        Args:
            processed_jobs: List of processed job data
            
        Returns:
            Total number of skills extracted
        """
        total_skills = 0
        for job in processed_jobs:
            total_skills += len(job.get('technical_requirements', '').split(';'))
            total_skills += len(job.get('business_requirements', '').split(';'))
            total_skills += len(job.get('soft_skills', '').split(';'))
        return total_skills
    
    def _summarize_skills_by_category(self, processed_jobs: List[Dict]) -> Dict[str, int]:
        """Summarize skills by category
        
        Args:
            processed_jobs: List of processed job data
            
        Returns:
            Dictionary with skill counts by category
        """
        return {
            "Technical": len([skill for job in processed_jobs 
                           for skill in job.get('technical_requirements', '').split(';') if skill.strip()]),
            "Business": len([skill for job in processed_jobs 
                           for skill in job.get('business_requirements', '').split(';') if skill.strip()]),
            "Soft": len([skill for job in processed_jobs 
                       for skill in job.get('soft_skills', '').split(';') if skill.strip()])
        }


def create_extraction_pipeline(config: Optional[Config] = None) -> ExtractionPipeline:
    """Factory function to create ExtractionPipeline
    
    Args:
        config: Configuration object (uses default if None)
        
    Returns:
        Initialized ExtractionPipeline instance
    """
    return ExtractionPipeline(config)
