"""
Data Models for TY_EXTRACT V14
==============================

Clean, consistent data structures with comprehensive type hints.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class JobSkills:
    """
    Extracted skills from a job posting - consistent naming throughout
    
    Example:
        skills = JobSkills(
            technical=["Python", "SQL", "Docker"],
            business=["Project Management", "Agile"],
            soft=["Communication", "Leadership"]
        )
    """
    technical: List[str]
    business: List[str] 
    soft: List[str]
    experience: List[str]
    education: List[str]
    
    def total_count(self) -> int:
        """Total number of skills across all categories"""
        return len(self.technical) + len(self.business) + len(self.soft) + len(self.experience) + len(self.education)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary for serialization"""
        return {
            'technical': self.technical,
            'business': self.business,
            'soft': self.soft,
            'experience': self.experience,
            'education': self.education
        }

@dataclass
class JobLocation:
    """
    Structured job location information
    
    Example:
        location = JobLocation(
            city="Frankfurt",
            country="Germany",
            is_remote=False
        )
    """
    city: str
    country: str
    is_remote: bool = False
    metadata: Optional[str] = None
    
    def display_name(self) -> str:
        """Human-readable location string"""
        if self.is_remote:
            return f"{self.city}, {self.country} (Remote)"
        return f"{self.city}, {self.country}"

@dataclass
class ExtractedJob:
    """
    Complete extracted job information with consistent field names
    
    Example:
        job = ExtractedJob(
            job_id="12345",
            title="Senior Python Developer",
            company="TechCorp",
            skills=job_skills,
            location=job_location
        )
    """
    # Basic job information
    job_id: str
    title: str
    company: str
    division: Optional[str]
    description: str
    url: Optional[str]
    
    # Extracted data
    skills: JobSkills
    location: JobLocation
    concise_description: str
    
    # Metadata
    processed_at: datetime
    pipeline_version: str
    extraction_method: str = "llm_extraction"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for report generation"""
        return {
            # Basic information
            'job_id': self.job_id,
            'title': self.title,
            'company': self.company,
            'division': self.division or '',
            'description': self.description,
            'url': self.url or '',
            
            # Skills (consistent naming - no mapping needed)
            'technical_skills': self.skills.technical,
            'business_skills': self.skills.business,
            'soft_skills': self.skills.soft,
            'experience_skills': self.skills.experience,
            'education_skills': self.skills.education,
            
            # Location
            'location_city': self.location.city,
            'location_country': self.location.country,
            'location_display': self.location.display_name(),
            'is_remote': self.location.is_remote,
            
            # Other
            'concise_description': self.concise_description,
            'processed_at': self.processed_at.isoformat(),
            'pipeline_version': self.pipeline_version,
            'extraction_method': self.extraction_method,
            'total_skills': self.skills.total_count()
        }

@dataclass
class PipelineResult:
    """
    Complete pipeline execution result
    
    Example:
        result = PipelineResult(
            jobs=[job1, job2],
            success=True,
            duration=45.2,
            total_skills=156
        )
    """
    jobs: List[ExtractedJob]
    success: bool
    duration: float
    error_message: Optional[str] = None
    
    # Summary statistics
    total_jobs: int = 0
    total_skills: int = 0
    
    def __post_init__(self):
        """Calculate summary statistics"""
        self.total_jobs = len(self.jobs)
        self.total_skills = sum(job.skills.total_count() for job in self.jobs)
    
    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.jobs:
            return {
                'technical': 0,
                'business': 0,  
                'soft': 0,
                'experience': 0,
                'education': 0
            }
        
        return {
            'technical': sum(len(job.skills.technical) for job in self.jobs),
            'business': sum(len(job.skills.business) for job in self.jobs),
            'soft': sum(len(job.skills.soft) for job in self.jobs),
            'experience': sum(len(job.skills.experience) for job in self.jobs),
            'education': sum(len(job.skills.education) for job in self.jobs)
        }
