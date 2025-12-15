"""
TY_EXTRACT V14 - Clean Job Extraction Pipeline
=============================================

A clean, intuitive, and efficient job extraction pipeline with:
- Consistent naming throughout
- Clear configuration management
- Comprehensive type hints
- Excellent documentation
- Optimized performance

Author: xai & Arden
Version: 14.0.0
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# Version info
__version__ = "14.0.0"
__author__ = "xai & Arden"

# Package exports
__all__ = [
    "Config",
    "JobLocation", 
    "JobSkills",
    "ExtractedJob",
    "PipelineResult",
    "LLMInterface",
    "TyExtractPipeline",
    "ReportGenerator"
]

# Import main classes for easy access
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
else:
    try:
        from .config import Config
    except (ImportError, AttributeError):
        Config = None  # type: ignore[misc]

from .models import JobLocation, JobSkills, ExtractedJob, PipelineResult  
from .llm_interface import LLMInterface
from .pipeline import TyExtractPipeline
from .reports import ReportGenerator
