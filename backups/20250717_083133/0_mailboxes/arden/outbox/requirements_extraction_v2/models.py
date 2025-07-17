#!/usr/bin/env python3
"""
Data models for the 5-dimensional requirements extraction system.

This module contains all the dataclasses that represent the different types
of requirements extracted from job descriptions.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

from dataclasses import dataclass
from typing import List, Any


@dataclass
class TechnicalRequirement:
    """Represents a technical skill or tool requirement."""
    skill: str
    proficiency_level: str  # "basic", "intermediate", "advanced", "expert"
    category: str  # "programming", "platform", "tool", "framework", "database", "security", etc.
    is_mandatory: bool
    confidence: float
    context: str  # Context where found


@dataclass
class BusinessRequirement:
    """Represents a business domain or industry experience requirement."""
    domain: str  # "banking", "fintech", "network-security", etc.
    experience_type: str  # "client_facing", "product_management", "sales", etc.
    years_required: int
    is_mandatory: bool
    confidence: float
    context: str


@dataclass
class SoftSkillRequirement:
    """Represents a soft skill requirement."""
    skill: str
    context: str  # where/how it's applied
    importance: str  # "critical", "important", "preferred"
    confidence: float


@dataclass
class ExperienceRequirement:
    """Represents a general experience requirement."""
    type: str  # "industry", "role", "project", "team_lead", etc.
    description: str
    years_required: int
    is_mandatory: bool
    confidence: float


@dataclass
class EducationRequirement:
    """Represents an education or certification requirement."""
    level: str  # "bachelor", "master", "phd", "certification", "apprenticeship"
    field: str
    is_mandatory: bool
    alternatives: List[str]
    confidence: float


@dataclass
class FiveDimensionalRequirements:
    """Container for all five dimensions of requirements."""
    technical: List[TechnicalRequirement]
    business: List[BusinessRequirement]
    soft_skills: List[SoftSkillRequirement]
    experience: List[ExperienceRequirement]
    education: List[EducationRequirement]
