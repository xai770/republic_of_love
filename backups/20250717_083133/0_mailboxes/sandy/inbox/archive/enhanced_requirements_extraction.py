#!/usr/bin/env python3
"""
Enhanced 5-Dimensional Requirements Extraction v2.0
==================================================

This enhanced version addresses the critical issues discovered in the batch analysis:
1. German location validation patterns
2. Improved experience extraction
3. Soft skills deduplication
4. Enhanced business requirements detection
5. Network security and finance-specific patterns

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import json
import re
import sys
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict

@dataclass
class TechnicalRequirement:
    skill: str
    proficiency_level: str  # "basic", "intermediate", "advanced", "expert"
    category: str  # "programming", "platform", "tool", "framework", "database", "security", etc.
    is_mandatory: bool
    confidence: float
    context: str  # Context where found

@dataclass
class BusinessRequirement:
    domain: str  # "banking", "fintech", "network-security", etc.
    experience_type: str  # "client_facing", "product_management", "sales", etc.
    years_required: int
    is_mandatory: bool
    confidence: float
    context: str

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

class EnhancedRequirementsExtractor:
    """Enhanced requirements extractor with German localization and improved patterns."""
    
    def __init__(self):
        # Enhanced technical skills patterns
        self.tech_patterns = {
            'programming': r'\b(Python|Java|SQL|SAS|R|JavaScript|C\+\+|C#|Scala|Go|Rust|PHP|Ruby|Perl|Swift|Kotlin)\b',
            'platform': r'\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitLab|Terraform|Ansible)\b',
            'analytics': r'\b(Tableau|Power BI|Qlik|Pandas|NumPy|Scikit-learn|TensorFlow|Spark|Hadoop)\b',
            'database': r'\b(Oracle|PostgreSQL|MySQL|MongoDB|Cassandra|Redis|SQL Server|DB2)\b',
            'tool': r'\b(Adobe|Salesforce|CRM|ERP|JIRA|Confluence|SharePoint|SAP)\b',
            'security': r'\b(NSX|Firewall|VPN|SIEM|CISSP|CISO|Penetration|Vulnerability|Encryption|PKI|Zero Trust)\b',
            'network': r'\b(TCP/IP|BGP|OSPF|VLAN|Router|Switch|Load Balancer|Proxy|DNS|DHCP)\b',
            'finance_tools': r'\b(Bloomberg|Reuters|MUREX|Calypso|Summit|Aladdin|Risk Management|Treasury)\b'
        }
        
        # Enhanced experience patterns with German
        self.experience_patterns = {
            'years_german': r'(\d+)\+?\s*Jahre?\s*(Erfahrung|Berufserfahrung|Praxis)',
            'years_english': r'(\d+)\+?\s*years?\s*(experience|of experience)',
            'banking_german': r'\b(Bank|Banking|Finanz|Finance|Treasury|Credit|Risk|Kredit|Bankenumfeld)\b',
            'leadership_german': r'\b(Team|Lead|Manager|Führung|Verantwortung|Leitung|Senior)\b',
            'senior_level': r'\b(Senior|Lead|Principal|Expert|Spezialist|Experte)\b'
        }
        
        # Enhanced education patterns
        self.education_patterns = {
            'degree_german': r'\b(Bachelor|Master|Diplom|PhD|Promotion|Studium|BA|MA|MSc|BSc|FH|Universität)\b',
            'field_german': r'\b(Informatik|Wirtschaftsinformatik|BWL|VWL|Mathematik|Physik|Ingenieur|Finance|Banking)\b',
            'certification': r'\b(Zertifikat|Zertifizierung|Certification|CISSP|PMP|CISA|CFA|FRM)\b'
        }
        
        # Soft skills mapping and deduplication
        self.soft_skills_groups = {
            'communication': {
                'patterns': r'\b(Kommunikation|communication|Präsentation|presentation|verbal|schriftlich)\b',
                'keywords': ['communication', 'kommunikation', 'presentation', 'verbal', 'written']
            },
            'teamwork': {
                'patterns': r'\b(Teamwork|Zusammenarbeit|collaboration|Team|kooperativ)\b',
                'keywords': ['teamwork', 'zusammenarbeit', 'collaboration', 'cooperative']
            },
            'analytical': {
                'patterns': r'\b(analytisch|analytical|Analyse|analysis|konzeptionell|logical)\b',
                'keywords': ['analytical', 'analysis', 'conceptual', 'logical']
            },
            'initiative': {
                'patterns': r'\b(Initiative|Eigeninitiative|proaktiv|proactive|self-motivated)\b',
                'keywords': ['initiative', 'proactive', 'self-motivated']
            },
            'problem_solving': {
                'patterns': r'\b(Lösungsorientierung|problem solving|Problemlösung|troubleshooting)\b',
                'keywords': ['problem solving', 'solution-oriented', 'troubleshooting']
            },
            'leadership': {
                'patterns': r'\b(Führung|leadership|Management|mentor|guide)\b',
                'keywords': ['leadership', 'management', 'mentoring']
            }
        }

    def extract_requirements(self, job_description: str) -> FiveDimensionalRequirements:
        """Extract 5-dimensional requirements from job description."""
        
        # Clean and normalize text
        text = self._normalize_text(job_description)
        
        # Extract each dimension
        technical = self._extract_technical_requirements(text)
        business = self._extract_business_requirements(text)
        soft_skills = self._extract_soft_skills_deduplicated(text)
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
        return text
    
    def _extract_technical_requirements(self, text: str) -> List[TechnicalRequirement]:
        """Extract technical skills and tools with enhanced patterns."""
        requirements = []
        found_skills = set()  # Prevent duplicates
        
        for category, pattern in self.tech_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.group().strip()
                skill_lower = skill.lower()
                
                # Skip if already found
                if skill_lower in found_skills:
                    continue
                found_skills.add(skill_lower)
                
                # Get context and determine properties
                context = self._get_context(text, match.start(), match.end())
                proficiency = self._determine_proficiency(context)
                is_mandatory = self._is_mandatory(context)
                
                requirements.append(TechnicalRequirement(
                    skill=skill,
                    proficiency_level=proficiency,
                    category=category,
                    is_mandatory=is_mandatory,
                    confidence=0.8,
                    context=context[:100]
                ))
        
        return requirements
    
    def _extract_business_requirements(self, text: str) -> List[BusinessRequirement]:
        """Extract business domain and industry experience with enhanced patterns."""
        requirements = []
        
        # Banking/Finance domain detection
        banking_matches = list(re.finditer(self.experience_patterns['banking_german'], text, re.IGNORECASE))
        if banking_matches:
            for match in banking_matches:
                context = self._get_context(text, match.start(), match.end())
                years = self._extract_years_from_context(context)
                
                requirements.append(BusinessRequirement(
                    domain="banking",
                    experience_type="industry_knowledge",
                    years_required=years,
                    is_mandatory=True,
                    confidence=0.9,
                    context=context[:150]
                ))
        
        # Network security domain
        if re.search(r'\b(Security|Sicherheit|Network|Netzwerk|Firewall|NSX)\b', text, re.IGNORECASE):
            requirements.append(BusinessRequirement(
                domain="network_security",
                experience_type="technical_domain",
                years_required=0,
                is_mandatory=True,
                confidence=0.8,
                context="Network security related role"
            ))
        
        # Investment/Finance domain
        if re.search(r'\b(Investment|Portfolio|Asset|Risk Management|Treasury|Trading)\b', text, re.IGNORECASE):
            requirements.append(BusinessRequirement(
                domain="investment_finance",
                experience_type="financial_markets",
                years_required=0,
                is_mandatory=True,
                confidence=0.8,
                context="Investment and finance related role"
            ))
        
        return requirements
    
    def _extract_soft_skills_deduplicated(self, text: str) -> List[SoftSkillRequirement]:
        """Extract soft skills with deduplication and grouping."""
        found_skills = {}  # skill_group -> best_match
        
        for skill_group, skill_data in self.soft_skills_groups.items():
            pattern = skill_data['patterns']
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            if matches:
                # Take the first match for this skill group
                match = matches[0]
                context = self._get_context(text, match.start(), match.end())
                
                found_skills[skill_group] = SoftSkillRequirement(
                    skill=skill_group,
                    context=context[:100],
                    importance="important",
                    confidence=0.7
                )
        
        return list(found_skills.values())
    
    def _extract_experience_requirements(self, text: str) -> List[ExperienceRequirement]:
        """Extract experience requirements with improved German patterns."""
        requirements = []
        
        # Years of experience - German patterns
        for pattern_name, pattern in [('years_german', self.experience_patterns['years_german']),
                                     ('years_english', self.experience_patterns['years_english'])]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                years = int(match.group(1))
                context = self._get_context(text, match.start(), match.end())
                
                requirements.append(ExperienceRequirement(
                    type="general_experience",
                    description=f"{years} years of professional experience",
                    years_required=years,
                    is_mandatory=True,
                    confidence=0.9
                ))
        
        # Senior level experience
        senior_matches = re.finditer(self.experience_patterns['senior_level'], text, re.IGNORECASE)
        for match in senior_matches:
            context = self._get_context(text, match.start(), match.end())
            
            requirements.append(ExperienceRequirement(
                type="senior_level",
                description="Senior level experience required",
                years_required=5,  # Estimate for senior roles
                is_mandatory=True,
                confidence=0.8
            ))
        
        return requirements
    
    def _extract_education_requirements(self, text: str) -> List[EducationRequirement]:
        """Extract education requirements with improved German patterns."""
        requirements = []
        found_degrees = set()
        
        # Degree requirements
        degree_matches = re.finditer(self.education_patterns['degree_german'], text, re.IGNORECASE)
        for match in degree_matches:
            degree = match.group().lower()
            
            # Skip duplicates
            if degree in found_degrees:
                continue
            found_degrees.add(degree)
            
            context = self._get_context(text, match.start(), match.end())
            
            # Try to find field
            field_match = re.search(self.education_patterns['field_german'], context, re.IGNORECASE)
            field = field_match.group() if field_match else "unspecified"
            
            requirements.append(EducationRequirement(
                level=degree,
                field=field,
                is_mandatory=self._is_mandatory(context),
                alternatives=[],
                confidence=0.8
            ))
        
        return requirements
    
    def _get_context(self, text: str, start: int, end: int, window: int = 150) -> str:
        """Get context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _determine_proficiency(self, context: str) -> str:
        """Determine proficiency level from context."""
        context_lower = context.lower()
        if any(word in context_lower for word in ['expert', 'fortgeschritten', 'senior', 'spezialist']):
            return 'expert'
        elif any(word in context_lower for word in ['gut', 'good', 'solid', 'fundiert', 'profound']):
            return 'advanced'
        elif any(word in context_lower for word in ['basic', 'grundlagen', 'kenntnis', 'knowledge']):
            return 'intermediate'
        else:
            return 'intermediate'  # Default
    
    def _is_mandatory(self, context: str) -> bool:
        """Determine if requirement is mandatory from context."""
        context_lower = context.lower()
        mandatory_indicators = ['muss', 'required', 'erforderlich', 'zwingend', 'notwendig']
        optional_indicators = ['wünschenswert', 'preferred', 'von vorteil', 'nice to have', 'idealerweise']
        
        if any(word in context_lower for word in mandatory_indicators):
            return True
        elif any(word in context_lower for word in optional_indicators):
            return False
        else:
            return True  # Default to mandatory
    
    def _extract_years_from_context(self, context: str) -> int:
        """Extract years of experience from context."""
        # Try German pattern first
        years_match = re.search(r'(\d+)\+?\s*Jahre?', context, re.IGNORECASE)
        if not years_match:
            # Try English pattern
            years_match = re.search(r'(\d+)\+?\s*years?', context, re.IGNORECASE)
        
        return int(years_match.group(1)) if years_match else 0

class EnhancedLocationValidator:
    """Enhanced location validator with comprehensive German patterns."""
    
    def __init__(self):
        # Comprehensive German location patterns
        self.german_cities = {
            'Frankfurt': ['Frankfurt', 'Frankfurt am Main', 'Frankfurt/Main', 'FFM'],
            'München': ['München', 'Munich', 'Muenchen'],
            'Berlin': ['Berlin'],
            'Hamburg': ['Hamburg'],
            'Köln': ['Köln', 'Cologne'],
            'Stuttgart': ['Stuttgart'],
            'Düsseldorf': ['Düsseldorf', 'Duesseldorf'],
        }
        
        self.german_states = {
            'Hessen': ['Hessen', 'Hesse'],
            'Bayern': ['Bayern', 'Bavaria', 'Bavarian'],
            'Baden-Württemberg': ['Baden-Württemberg', 'Baden-Wuerttemberg', 'BW'],
            'Nordrhein-Westfalen': ['Nordrhein-Westfalen', 'NRW', 'North Rhine-Westphalia'],
            'Niedersachsen': ['Niedersachsen', 'Lower Saxony'],
            'Berlin': ['Berlin'],
            'Hamburg': ['Hamburg'],
            'Bremen': ['Bremen'],
        }
        
        self.country_variants = {
            'Deutschland': ['Deutschland', 'Germany', 'DE', 'German', 'deutsche'],
        }
    
    def validate_location(self, metadata_location: Dict[str, Any], job_text: str) -> Tuple[bool, float, str]:
        """
        Enhanced location validation with German variants.
        
        Returns:
            - is_valid: bool indicating if location was found
            - confidence: float confidence score
            - details: string with validation details
        """
        city = metadata_location.get('city', '')
        state = metadata_location.get('state', '')
        country = metadata_location.get('country', '')
        
        validation_results = []
        
        # Check city with variants
        if city:
            city_variants = self.german_cities.get(city, [city])
            city_found = any(self._search_location_in_text(variant, job_text) for variant in city_variants)
            validation_results.append(('city', city, city_found))
        
        # Check state with variants
        if state:
            state_variants = self.german_states.get(state, [state])
            state_found = any(self._search_location_in_text(variant, job_text) for variant in state_variants)
            validation_results.append(('state', state, state_found))
        
        # Check country with variants
        if country:
            country_variants = self.country_variants.get(country, [country])
            country_found = any(self._search_location_in_text(variant, job_text) for variant in country_variants)
            validation_results.append(('country', country, country_found))
        
        # Calculate overall validation
        found_count = sum(1 for _, _, found in validation_results if found)
        total_count = len(validation_results)
        
        if total_count == 0:
            return False, 0.0, "No location information to validate"
        
        confidence = found_count / total_count
        
        # More lenient validation: if city is found, that's often sufficient for German jobs
        if city and validation_results[0][2]:  # City found
            confidence = max(confidence, 0.8)  # Boost confidence if city found
        
        is_valid = confidence >= 0.6  # Lower threshold for German locations
        
        details = f"Found {found_count}/{total_count} location components: " + \
                 ", ".join([f"{comp}:{loc}:{found}" for comp, loc, found in validation_results])
        
        return is_valid, confidence, details
    
    def _search_location_in_text(self, location: str, text: str) -> bool:
        """Search for location in text using regex with word boundaries."""
        # Create case-insensitive pattern with word boundaries
        pattern = r'\b' + re.escape(location) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

def test_enhanced_prototype():
    """Test the enhanced prototype with improved patterns."""
    
    # Load sample job
    job_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/inbox/job59428.json')
    
    if not job_file.exists():
        print(f"Error: Job file not found: {job_file}")
        return
    
    with open(job_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    job_description = job_data['job_content']['description']
    metadata_location = job_data['job_content']['location']
    
    print("=== ENHANCED 5-DIMENSIONAL REQUIREMENTS EXTRACTION v2.0 ===\n")
    
    # Test enhanced requirements extraction
    extractor = EnhancedRequirementsExtractor()
    requirements = extractor.extract_requirements(job_description)
    
    print("TECHNICAL REQUIREMENTS:")
    for req in requirements.technical:
        print(f"  - {req.skill} ({req.category}, {req.proficiency_level}, mandatory: {req.is_mandatory})")
    
    print(f"\nBUSINESS REQUIREMENTS:")
    for req in requirements.business:
        print(f"  - {req.domain} ({req.experience_type}): {req.years_required} years")
    
    print(f"\nSOFT SKILLS (DEDUPLICATED):")
    for req in requirements.soft_skills:
        print(f"  - {req.skill} ({req.importance})")
    
    print(f"\nEXPERIENCE REQUIREMENTS:")
    for req in requirements.experience:
        print(f"  - {req.type}: {req.description}")
    
    print(f"\nEDUCATION REQUIREMENTS:")
    for req in requirements.education:
        print(f"  - {req.level} in {req.field} (mandatory: {req.is_mandatory})")
    
    # Test enhanced location validation
    print("\n=== ENHANCED LOCATION VALIDATION ===\n")
    
    validator = EnhancedLocationValidator()
    is_valid, confidence, details = validator.validate_location(metadata_location, job_description)
    
    print(f"Metadata Location: {metadata_location}")
    print(f"Validation Result: {is_valid}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Details: {details}")
    
    # Export enhanced results
    results = {
        'job_id': job_data['job_metadata']['job_id'],
        'version': '2.0_enhanced',
        'requirements': asdict(requirements),
        'location_validation': {
            'is_valid': is_valid,
            'confidence': confidence,
            'details': details,
            'metadata_location': metadata_location
        },
        'improvements': {
            'german_patterns': True,
            'soft_skills_deduplication': True,
            'enhanced_experience_extraction': True,
            'business_domain_detection': True
        }
    }
    
    output_file = Path('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/arden@republic_of_love/outbox/enhanced_prototype_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nEnhanced results exported to: {output_file}")

if __name__ == "__main__":
    test_enhanced_prototype()
