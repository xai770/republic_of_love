#!/usr/bin/env python3
"""
Requirements Extraction v2.0 Package

A modular system for extracting 5-dimensional requirements from job descriptions,
with enhanced German localization and improved validation.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

from .models import (
    TechnicalRequirement,
    BusinessRequirement,
    SoftSkillRequirement,
    ExperienceRequirement,
    EducationRequirement,
    FiveDimensionalRequirements
)

from .extractor import EnhancedRequirementsExtractor
from .location_validator import EnhancedLocationValidator
from .utils import (
    normalize_text,
    get_context,
    determine_proficiency,
    is_mandatory,
    extract_years_from_context,
    deduplicate_skills,
    consolidate_business_requirements,
    consolidate_education_requirements,
    group_soft_skills
)

__version__ = "2.0"
__author__ = "Investigation Team"

__all__ = [
    'TechnicalRequirement',
    'BusinessRequirement',
    'SoftSkillRequirement',
    'ExperienceRequirement',
    'EducationRequirement',
    'FiveDimensionalRequirements',
    'EnhancedRequirementsExtractor',
    'EnhancedLocationValidator',
    'normalize_text',
    'get_context',
    'determine_proficiency',
    'is_mandatory',
    'extract_years_from_context',
    'deduplicate_skills',
    'consolidate_business_requirements',
    'consolidate_education_requirements',
    'group_soft_skills'
]
