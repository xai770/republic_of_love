"""
TY_EXTRACT V14 - Main Pipeline
=============================

Clean, efficient job extraction pipeline with LLM integration.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .config import Config  
else:
    try:
        from .config import Config
    except ImportError:
        try:
            from config import Config
        except ImportError:
            Config = Any  # type: ignore[misc]

from .models import JobLocation, JobSkills, ExtractedJob, PipelineResult
from .membridge_llm_interface_simple import MemBridgeLLMInterface
from .reports import ReportGenerator

logger = logging.getLogger('ty_extract_v14.pipeline')

class TyExtractPipeline:
    """
    Main job extraction pipeline with clean processing logic
    
    Example:
        config = Config.load_from_external()
        pipeline = TyExtractPipeline(config)
        result = pipeline.run()
        print(f"Extracted {result.total_jobs} jobs")
    """
    
    def __init__(self, config: Config):
        """
        Initialize pipeline with configuration
        
        Args:
            config: Pipeline configuration (must be loaded from external files)
        """
        self.config = config
        self.llm = MemBridgeLLMInterface(config)
        self.report_generator = ReportGenerator(config)
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Pipeline initialized with external config")
    
    def run(self) -> PipelineResult:
        """
        Run the complete extraction pipeline
        
        Returns:
            Pipeline execution result
        """
        start_time = time.time()
        logger.info("🚀 Starting pipeline execution")
        
        try:
            # Find job files
            job_files = self._find_job_files()
            if not job_files:
                logger.warning("No job files found")
                return PipelineResult(
                    jobs=[],
                    success=False,
                    duration=time.time() - start_time,
                    error_message="No job files found in data directory"
                )
            
            logger.info(f"📁 Found {len(job_files)} job files")
            
            # Process jobs (limit to first few for testing)
            jobs_to_process = job_files[:self.config.max_jobs] if hasattr(self.config, 'max_jobs') else job_files[:1]
            extracted_jobs = []
            
            for job_file in jobs_to_process:
                try:
                    logger.info(f"📄 Processing {job_file.name}")
                    job = self._process_job_file(job_file)
                    if job:
                        extracted_jobs.append(job)
                        logger.info(f"✅ Extracted job: {job.title}")
                    else:
                        logger.warning(f"⚠️ Failed to extract job from {job_file.name}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {job_file.name}: {e}")
                    continue
            
            # Generate reports if jobs were extracted
            reports_generated = {}
            if extracted_jobs:
                logger.info("📊 Generating reports")
                reports_generated = self.report_generator.generate_reports(extracted_jobs)
            
            duration = time.time() - start_time
            result = PipelineResult(
                jobs=extracted_jobs,
                success=len(extracted_jobs) > 0,
                duration=duration,
                error_message=None if extracted_jobs else "No jobs successfully extracted"
            )
            
            logger.info(f"🏁 Pipeline completed: {len(extracted_jobs)} jobs in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            return PipelineResult(
                jobs=[],
                success=False, 
                duration=duration,
                error_message=str(e)
            )
    
    def _find_job_files(self) -> List[Path]:
        """Find all job JSON files in data directory"""
        
        job_files = []
        
        # Look for JSON files in data directory and subdirectories
        data_dir = Path(self.config.data_dir)
        
        if not data_dir.exists():
            logger.error(f"Data directory does not exist: {data_dir}")
            return []
        
        # Search for JSON files
        for pattern in ['*.json', 'postings/*.json', '**/job*.json']:
            found_files = list(data_dir.glob(pattern))
            job_files.extend(found_files)
        
        # Remove duplicates and sort
        unique_files = list(set(job_files))
        unique_files.sort()
        
        logger.info(f"📁 Found {len(unique_files)} job files")
        return unique_files
    
    def _process_job_file(self, job_file: Path) -> Optional[ExtractedJob]:
        """
        Process a single job file
        
        Args:
            job_file: Path to job JSON file
            
        Returns:
            Extracted job or None if processing failed
        """
        try:
            # Load job data
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Extract basic information
            job_content = job_data.get('job_content', {})
            job_metadata = job_data.get('job_metadata', {})
            
            # Create location
            location_data = job_content.get('location', {})
            location = JobLocation(
                city=location_data.get('city', 'Unknown'),
                country=location_data.get('country', 'Unknown'),
                is_remote=location_data.get('remote_options', False)
            )
            
            # Extract skills using LLM
            description = job_content.get('description', '')
            skills = self._extract_skills_with_llm(description)
            
            # Create extracted job
            job = ExtractedJob(
                job_id=job_metadata.get('job_id', job_file.stem),
                title=job_content.get('title', 'Unknown Title'),
                company=job_content.get('organization', {}).get('name', 'Unknown Company'),
                division=job_content.get('organization', {}).get('division'),
                description=description,
                url=job_content.get('url'),
                location=location,
                skills=skills,
                concise_description=self._create_concise_description(job_content),
                processed_at=datetime.now(),
                pipeline_version=self.config.pipeline_version
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to process job file {job_file}: {e}")
            return None
    
    def _extract_skills_with_llm(self, description: str) -> JobSkills:
        """
        Extract skills from job description using LLM with quality validation
        
        Args:
            description: Job description text
            
        Returns:
            Extracted skills organized by category
            
        Raises:
            Exception: If extraction fails or produces insufficient results
        """
        try:
            # Use actual LLM extraction - this will take realistic time (5-30+ seconds)
            logger.info("🤖 Calling LLM for skill extraction...")
            skills = self.llm.extract_skills(description, "Job Analysis")
            
            # ENHANCED VALIDATION: Ensure meaningful skill extraction
            total_skills = skills.total_count()
            logger.info(f"✅ LLM extracted {total_skills} skills")
            
            # Quality gates as recommended by Sage
            if total_skills == 0:
                raise Exception("No skills extracted - complete parsing failure")
            
            if total_skills < 3:
                logger.warning(f"⚠️ Low skill count ({total_skills}) - possible parsing issues")
                
            # Validate that at least some categories have content
            non_empty_categories = sum(1 for category in [skills.technical, skills.business, 
                                                         skills.soft, skills.experience, skills.education] 
                                     if len(category) > 0)
            
            if non_empty_categories < 2:
                raise Exception(f"Insufficient category diversity - only {non_empty_categories} categories populated")
            
            # Log detailed quality metrics
            logger.info(f"📊 Skills quality metrics:")
            logger.info(f"   • Technical: {len(skills.technical)} skills")
            logger.info(f"   • Business: {len(skills.business)} skills") 
            logger.info(f"   • Soft: {len(skills.soft)} skills")
            logger.info(f"   • Experience: {len(skills.experience)} skills")
            logger.info(f"   • Education: {len(skills.education)} skills")
            logger.info(f"   • Categories populated: {non_empty_categories}/5")
            
            return skills
            
        except Exception as e:
            logger.error(f"❌ LLM skill extraction failed: {e}")
            # FAIL-FAST: Don't mask extraction failures
            raise Exception(f"Skills extraction validation failed: {e}")
    
    def _extract_skills_fallback(self, description: str) -> JobSkills:
        """
        REMOVED - V14 uses only LLM, no fallbacks
        """
        raise NotImplementedError("V14 does not use fallbacks - only LLM processing")
    
    def _create_concise_description(self, job_content: Dict[str, Any]) -> str:
        """
        Create a concise description using LLM - NO FALLBACKS
        
        Args:
            job_content: Job content dictionary
            
        Returns:
            LLM-generated concise description string
        """
        try:
            title = job_content.get('title', '')
            description = job_content.get('description', '')
            
            if not description:
                raise Exception("No job description available for LLM processing")
            
            # Use actual LLM for concise description
            logger.info("🤖 Calling LLM for concise description...")
            concise: str = self.llm.extract_concise_description(description, title)
            logger.info("✅ LLM generated concise description")
            return concise
            
        except Exception as e:
            logger.error(f"❌ LLM concise description failed: {e}")
            # NO FALLBACK - fail if LLM fails
            raise Exception(f"LLM concise description failed: {e}")


