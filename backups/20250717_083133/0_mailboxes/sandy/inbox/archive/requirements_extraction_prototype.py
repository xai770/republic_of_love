#!/usr/bin/env python3
"""
5-Dimensional Requirements Extraction Prototype
==============================================

This script prototypes the enhanced requirements extraction and location validation
based on the issues identified in Sandy's Daily Job Analysis Report.

Key improvements:
1. 5-dimensional requirements extraction (tech, business, soft skills, experience, education)
2. Regex-based location validation as fallback
3. Structured output for better analysis

Author: Investigation Team
Date: 2025-07-08
"""

import json
import re
import sys
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class TechnicalRequirement:
    skill: str
    proficiency_level: str  # "basic", "intermediate", "advanced", "expert"
    category: str  # "programming", "platform", "tool", "framework", "database", etc.
    is_mandatory: bool
    confidence: float

@dataclass
class BusinessRequirement:
    domain: str  # "banking", "fintech", "retail", etc.
    experience_type: str  # "client_facing", "product_management", "sales", etc.
    years_required: int
    is_mandatory: bool
    confidence: float

@dataclass
class SoftSkillRequirement:
    skill: str
    context: str  # where/how it's applied
    importance: str  # "critical", "important", "preferred"
    confidence: float

@dataclass
class ExperienceRequirement:
    type: str  # "industry", "role", "project", "team_lead", etc.
    description: str
    years_required: int
    is_mandatory: bool
    confidence: float

@dataclass
class EducationRequirement:
    level: str  # "bachelor", "master", "phd", "certification", "apprenticeship"
    field: str
    is_mandatory: bool
    alternatives: List[str]
    confidence: float

@dataclass
class FiveDimensionalRequirements:
    technical: List[TechnicalRequirement]
    business: List[BusinessRequirement]
    soft_skills: List[SoftSkillRequirement]
    experience: List[ExperienceRequirement]
    education: List[EducationRequirement]

class RequirementsExtractor:
    """Enhanced requirements extractor using pattern matching and keyword analysis."""
    
    def __init__(self):
        # Technical skills patterns
        self.tech_patterns = {
            'programming': r'\b(Python|Java|SQL|SAS|R|JavaScript|C\+\+|C#|Scala|Go|Rust)\b',
            'platform': r'\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitLab)\b',
            'analytics': r'\b(Tableau|Power BI|Qlik|Pandas|NumPy|Scikit-learn|TensorFlow)\b',
            'database': r'\b(Oracle|PostgreSQL|MySQL|MongoDB|Cassandra|Redis)\b',
            'tool': r'\b(Adobe|Salesforce|CRM|ERP|JIRA|Confluence)\b'
        }
        
        # Experience patterns
        self.experience_patterns = {
            'years': r'(\d+)\+?\s*Jahre?\s*(Erfahrung|Berufserfahrung)',
            'banking': r'\b(Bank|Banking|Finanz|Finance|Treasury|Credit|Risk)\b',
            'leadership': r'\b(Team|Lead|Manager|Führung|Verantwortung)\b'
        }
        
        # Education patterns
        self.education_patterns = {
            'degree': r'\b(Bachelor|Master|Diplom|PhD|Promotion|Studium)\b',
            'field': r'\b(Informatik|Wirtschaftsinformatik|BWL|VWL|Mathematik|Physik)\b',
            'certification': r'\b(Zertifikat|Zertifizierung|Certification)\b'
        }

    def extract_requirements(self, job_description: str) -> FiveDimensionalRequirements:
        """Extract 5-dimensional requirements from job description."""
        
        # Clean and normalize text
        text = self._normalize_text(job_description)
        
        # Extract each dimension
        technical = self._extract_technical_requirements(text)
        business = self._extract_business_requirements(text)
        soft_skills = self._extract_soft_skills(text)
        experience = self._extract_experience_requirements(text)
        education = self._extract_education_requirements(text)
        
        return FiveDimensionalRequirements(
            technical=technical,
            business=business,
            soft_skills=soft_skills,
            experience=experience,
            education=education
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better pattern matching."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Convert to lowercase for some operations (keep original for display)
        return text
    
    def _extract_technical_requirements(self, text: str) -> List[TechnicalRequirement]:
        """Extract technical skills and tools."""
        requirements = []
        
        for category, pattern in self.tech_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group()
                
                # Determine proficiency level from context
                context = self._get_context(text, match.start(), match.end())
                proficiency = self._determine_proficiency(context)
                is_mandatory = self._is_mandatory(context)
                
                requirements.append(TechnicalRequirement(
                    skill=skill,
                    proficiency_level=proficiency,
                    category=category,
                    is_mandatory=is_mandatory,
                    confidence=0.8  # Pattern-based confidence
                ))
        
        return requirements
    
    def _extract_business_requirements(self, text: str) -> List[BusinessRequirement]:
        """Extract business domain and industry experience."""
        requirements = []
        
        # Banking/Finance domain detection
        banking_match = re.search(self.experience_patterns['banking'], text, re.IGNORECASE)
        if banking_match:
            requirements.append(BusinessRequirement(
                domain="banking",
                experience_type="industry_knowledge",
                years_required=self._extract_years_from_context(text, banking_match),
                is_mandatory=True,
                confidence=0.9
            ))
        
        return requirements
    
    def _extract_soft_skills(self, text: str) -> List[SoftSkillRequirement]:
        """Extract soft skills and competencies."""
        soft_skills = []
        
        # Common soft skills in German job postings
        skill_patterns = {
            'communication': r'\b(Kommunikation|communication|Präsentation|presentation)\b',
            'teamwork': r'\b(Teamwork|Zusammenarbeit|collaboration|Team)\b',
            'analytical': r'\b(analytisch|analytical|Analyse|analysis|konzeptionell)\b',
            'initiative': r'\b(Initiative|Eigeninitiative|proaktiv|proactive)\b',
            'problem_solving': r'\b(Lösungsorientierung|problem solving|Problemlösung)\b'
        }
        
        for skill_name, pattern in skill_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                context = self._get_context(text, match.start(), match.end())
                
                soft_skills.append(SoftSkillRequirement(
                    skill=skill_name,
                    context=context[:100],  # First 100 chars of context
                    importance="important",
                    confidence=0.7
                ))
        
        return soft_skills
    
    def _extract_experience_requirements(self, text: str) -> List[ExperienceRequirement]:
        """Extract experience requirements."""
        requirements = []
        
        # Years of experience
        years_matches = re.finditer(self.experience_patterns['years'], text, re.IGNORECASE)
        for match in years_matches:
            years = int(match.group(1))
            context = self._get_context(text, match.start(), match.end())
            
            requirements.append(ExperienceRequirement(
                type="general",
                description=context[:200],
                years_required=years,
                is_mandatory=True,
                confidence=0.9
            ))
        
        return requirements
    
    def _extract_education_requirements(self, text: str) -> List[EducationRequirement]:
        """Extract education requirements."""
        requirements = []
        
        # Degree requirements
        degree_matches = re.finditer(self.education_patterns['degree'], text, re.IGNORECASE)
        for match in degree_matches:
            degree = match.group()
            context = self._get_context(text, match.start(), match.end())
            
            # Try to find field
            field_match = re.search(self.education_patterns['field'], context, re.IGNORECASE)
            field = field_match.group() if field_match else "unspecified"
            
            requirements.append(EducationRequirement(
                level=degree.lower(),
                field=field,
                is_mandatory=self._is_mandatory(context),
                alternatives=[],
                confidence=0.8
            ))
        
        return requirements
    
    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Get context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _determine_proficiency(self, context: str) -> str:
        """Determine proficiency level from context."""
        context_lower = context.lower()
        if any(word in context_lower for word in ['expert', 'fortgeschritten', 'senior']):
            return 'expert'
        elif any(word in context_lower for word in ['gut', 'good', 'solid', 'fundiert']):
            return 'advanced'
        elif any(word in context_lower for word in ['basic', 'grundlagen', 'kenntnis']):
            return 'intermediate'
        else:
            return 'intermediate'  # Default
    
    def _is_mandatory(self, context: str) -> bool:
        """Determine if requirement is mandatory from context."""
        context_lower = context.lower()
        mandatory_indicators = ['muss', 'required', 'erforderlich', 'zwingend']
        optional_indicators = ['wünschenswert', 'preferred', 'von vorteil', 'nice to have']
        
        if any(word in context_lower for word in mandatory_indicators):
            return True
        elif any(word in context_lower for word in optional_indicators):
            return False
        else:
            return True  # Default to mandatory
    
    def _extract_years_from_context(self, text: str, match) -> int:
        """Extract years of experience from context."""
        context = self._get_context(text, match.start(), match.end())
        years_match = re.search(r'(\d+)', context)
        return int(years_match.group(1)) if years_match else 0

class LocationValidator:
    """Regex-based location validation as fallback to LLM."""
    
    def __init__(self):
        # German city patterns
        self.german_cities = [
            'Berlin', 'Hamburg', 'München', 'Munich', 'Köln', 'Cologne', 'Frankfurt',
            'Stuttgart', 'Düsseldorf', 'Dortmund', 'Essen', 'Leipzig', 'Bremen',
            'Dresden', 'Hannover', 'Nürnberg', 'Nuremberg', 'Duisburg', 'Bochum'
        ]
        
        # State patterns
        self.german_states = [
            'Bayern', 'Bavaria', 'Baden-Württemberg', 'Nordrhein-Westfalen',
            'Hessen', 'Niedersachsen', 'Sachsen', 'Rheinland-Pfalz',
            'Schleswig-Holstein', 'Brandenburg', 'Sachsen-Anhalt', 'Thüringen'
        ]
    
    def validate_location(self, metadata_location: Dict[str, Any], job_text: str) -> Tuple[bool, float, str]:
        """
        Validate if metadata location appears in job text.
        
        Returns:
            - is_valid: bool indicating if location was found
            - confidence: float confidence score
            - details: string with validation details
        """
        city = metadata_location.get('city', '')
        state = metadata_location.get('state', '')
        country = metadata_location.get('country', '')
        
        validation_results = []
        
        # Check city
        if city:
            city_found = self._search_location_in_text(city, job_text)
            validation_results.append(('city', city, city_found))
        
        # Check state
        if state:
            state_found = self._search_location_in_text(state, job_text)
            validation_results.append(('state', state, state_found))
        
        # Check country
        if country:
            country_found = self._search_location_in_text(country, job_text)
            validation_results.append(('country', country, country_found))
        
        # Calculate overall validation
        found_count = sum(1 for _, _, found in validation_results if found)
        total_count = len(validation_results)
        
        if total_count == 0:
            return False, 0.0, "No location information to validate"
        
        confidence = found_count / total_count
        is_valid = confidence >= 0.5  # At least half of location components found
        
        details = f"Found {found_count}/{total_count} location components: " + \
                 ", ".join([f"{comp}:{loc}:{found}" for comp, loc, found in validation_results])
        
        return is_valid, confidence, details
    
    def _search_location_in_text(self, location: str, text: str) -> bool:
        """Search for location in text using regex."""
        # Create case-insensitive pattern with word boundaries
        pattern = r'\b' + re.escape(location) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

def test_prototype():
    """Test the prototype with the sample job."""
    
    # Load sample job
    job_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox/job59428.json')
    
    if not job_file.exists():
        print(f"Error: Job file not found: {job_file}")
        return
    
    with open(job_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    job_description = job_data['job_content']['description']
    metadata_location = job_data['job_content']['location']
    
    print("=== 5-DIMENSIONAL REQUIREMENTS EXTRACTION PROTOTYPE ===\n")
    
    # Test requirements extraction
    extractor = RequirementsExtractor()
    requirements = extractor.extract_requirements(job_description)
    
    print("TECHNICAL REQUIREMENTS:")
    for req in requirements.technical:
        print(f"  - {req.skill} ({req.category}, {req.proficiency_level}, mandatory: {req.is_mandatory})")
    
    print(f"\nBUSINESS REQUIREMENTS:")
    for req in requirements.business:
        print(f"  - {req.domain} experience: {req.years_required} years")
    
    print(f"\nSOFT SKILLS:")
    for req in requirements.soft_skills:
        print(f"  - {req.skill} ({req.importance})")
    
    print(f"\nEXPERIENCE REQUIREMENTS:")
    for req in requirements.experience:
        print(f"  - {req.type}: {req.years_required} years")
    
    print(f"\nEDUCATION REQUIREMENTS:")
    for req in requirements.education:
        print(f"  - {req.level} in {req.field} (mandatory: {req.is_mandatory})")
    
    # Test location validation
    print("\n=== LOCATION VALIDATION ===\n")
    
    validator = LocationValidator()
    is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
    
    print(f"Metadata Location: {metadata_location}")
    print(f"Validation Result: {is_valid}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Details: {details}")
    
    # Export results as JSON
    results = {
        'job_id': job_data['job_metadata']['job_id'],
        'requirements': asdict(requirements),
        'location_validation': {
            'is_valid': is_valid,
            'confidence': confidence,
            'details': details,
            'metadata_location': metadata_location
        }
    }
    
    output_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/outbox/prototype_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults exported to: {output_file}")

if __name__ == "__main__":
    test_prototype()
