"""
TY_EXTRACT V11.0 - NO FALLBACK EXTRACTOR
========================================

PHILOSOPHY: FAIL FAST, NO LIES, NO MOCKS
- If LLM fails -> CRASH
- If data missing -> CRASH  
- If extraction incomplete -> CRASH
- Better honest failure than fake success
"""

import logging
from typing import Dict, Any, Optional
from gemma_concise_extractor_v11 import GemmaConciseExtractor

logger = logging.getLogger(__name__)

class NoFallbackExtractor:
    """V11.0 Extractor that FAILS FAST with no fallbacks"""
    
    def __init__(self):
        # Initialize V11.0 extractor
        self.v11_extractor = GemmaConciseExtractor(model_name="qwen3:latest")
        
        # CRITICAL: If LLM not available, CRASH immediately
        if not self.v11_extractor.is_available:
            raise RuntimeError("❌ CRITICAL: qwen3:latest not available. V11.0 requires LLM - NO FALLBACKS!")
        
        logger.info("✅ V11.0 NoFallback extractor initialized - LLM required, no compromises")
    
    def extract_job_data(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract job data with V11.0 standards - FAIL FAST
        
        Returns:
            Dict with extracted data or CRASHES
        """
        # Debug the complete job structure first
        logger.info(f"🔍 Complete job keys: {list(job.keys())}")
        logger.info(f"🔍 Job type: {type(job)}")
        logger.info(f"🔍 Job content keys: {list(job.get('job_content', {}).keys())}")
        
        # Handle nested job structure - CRASH if not found
        job_content = job.get('job_content')
        job_metadata = job.get('job_metadata') 
        
        if not job_content:
            raise ValueError("❌ CRITICAL: job_content missing from job data")
        if not job_metadata:
            raise ValueError("❌ CRITICAL: job_metadata missing from job data")
        
        job_title = job_content.get('title')
        description = job_content.get('description')
        job_id = job_metadata.get('job_id')
        
        # CRITICAL: Require essential data
        if not job_title:
            raise ValueError("❌ CRITICAL: Job title missing - cannot proceed")
        if not description:
            raise ValueError("❌ CRITICAL: Job description missing - cannot proceed")
        if not job_id:
            raise ValueError("❌ CRITICAL: Job ID missing - cannot proceed")
        
        logger.info(f"🔍 V11.0 extraction starting: {job_title}")
        
        # Extract concise description using V11.0 template
        try:
            result = self.v11_extractor.extract_concise_description(description)
            
            if not result.get("success"):
                raise RuntimeError(f"❌ V11.0 extraction failed: {result.get('error', 'Unknown error')}")
            
            concise_description = result.get("content")
            if not concise_description:
                raise RuntimeError("❌ V11.0 extraction returned empty result")
            
            logger.info(f"✅ V11.0 extraction successful: {len(concise_description)} chars")
            
            # Extract organization info from job_content (where it's actually nested)
            organization = job_content.get('organization', {})
            logger.info(f"🔍 Organization data: {organization}")
            company_name = organization.get('name')
            logger.info(f"🔍 Company name extracted: '{company_name}'")
            
            if not company_name:
                raise ValueError("❌ CRITICAL: Company name missing - cannot proceed")
            
            # Return clean structured data - NO DEFAULTS
            return {
                "job_id": job_id,
                "position_title": job_title,  
                "company": company_name,
                "full_content": description,
                "concise_description": concise_description,
                "processing_timestamp": self._get_timestamp(),
                "extraction_method": "v11.0_qwen3_template"
            }
            
        except Exception as e:
            logger.error(f"❌ V11.0 extraction FAILED for {job_title}: {e}")
            raise RuntimeError(f"V11.0 extraction failed: {e}") from e
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


class MinimalLocationValidator:
    """Location validation without fallbacks"""
    
    def validate_location(self, location: str) -> Dict[str, Any]:
        """Validate location or CRASH"""
        if not location or location.strip() == "":
            raise ValueError("❌ CRITICAL: Empty location - cannot validate")
        
        # Simple validation - extend as needed
        cleaned_location = location.strip()
        
        return {
            "authoritative_location": cleaned_location,
            "conflict_detected": False,
            "confidence_score": 1.0,
            "validation_method": "v11.0_direct"
        }
