"""
Content Extraction Specialist v2.0 - Skill Matching Optimized
===========================================================

Version 2.0 optimized for Sandy's CV-to-job skill matching pipeline.

Key improvements:
- Standardized output format for automated parsing
- Removed redundant boilerplate content
- Consistent section headers and structure
- Enhanced for skill matching algorithms
- Language consistency (English only)

Usage:
    from llm_factory.modules.quality_validation.specialists_versioned.content_extraction.v2_0 import ContentExtractionSpecialistV2
    
    specialist = ContentExtractionSpecialistV2()
    result = specialist.extract_content_optimized(job_description)
"""

from .src.content_extraction_specialist_v2 import (
    ContentExtractionSpecialistV2,
    ExtractionResultV2,
    extract_job_content_v2
)

__all__ = [
    'ContentExtractionSpecialistV2',
    'ExtractionResultV2', 
    'extract_job_content_v2'
]

__version__ = "2.0.0"
__author__ = "LLM Factory Team"
__description__ = "Optimized content extraction for CV-to-job skill matching"
