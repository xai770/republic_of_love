#!/usr/bin/env python3
"""
Main requirements extraction module.

This module contains the core logic for extracting 5-dimensional requirements
from job descriptions, with enhanced patterns for German job postings and
improved deduplication for business and education requirements.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import re
from typing import List, Set, Dict, Any
from dataclasses import asdict

from .models import (
    TechnicalRequirement, BusinessRequirement, SoftSkillRequirement,
    ExperienceRequirement, EducationRequirement, FiveDimensionalRequirements
)
from .utils import (
    normalize_text, get_context, determine_proficiency, is_mandatory,
    extract_years_from_context, deduplicate_skills, consolidate_business_requirements,
    consolidate_education_requirements, group_soft_skills
)


class EnhancedRequirementsExtractor:
    """Enhanced requirements extractor with German localization and improved patterns."""
    
    def __init__(self):
        # Enhanced technical skills patterns
        self.tech_patterns = {
            'programming': r'\b(Python|Java|SQL|SAS|R|JavaScript|C\+\+|C#|Scala|Go|Rust|PHP|Ruby|Perl|Swift|Kotlin|VBA|MATLAB|Fortran|COBOL|Assembly)\b',
            'platform': r'\b(AWS|Azure|GCP|Google Cloud|Docker|Kubernetes|Jenkins|GitLab|GitHub|Terraform|Ansible|Vagrant|OpenStack)\b',
            'analytics': r'\b(Tableau|Power BI|Qlik|QlikView|Pandas|NumPy|Scikit-learn|TensorFlow|PyTorch|Spark|Hadoop|Jupyter|RStudio)\b',
            'database': r'\b(Oracle|PostgreSQL|MySQL|MongoDB|Cassandra|Redis|SQL Server|DB2|SQLite|MariaDB|DynamoDB|Elasticsearch)\b',
            'tool': r'\b(Adobe|Photoshop|Illustrator|Salesforce|CRM|ERP|SAP|JIRA|Confluence|SharePoint|Slack|Teams|Zoom|Figma|Sketch)\b',
            'security': r'\b(NSX|Firewall|VPN|SIEM|CISSP|CISO|Penetration|Vulnerability|Encryption|PKI|Zero Trust|LDAP|Active Directory|OAuth|SAML)\b',
            'network': r'\b(TCP/IP|BGP|OSPF|VLAN|Router|Switch|Load Balancer|Proxy|DNS|DHCP|VPN|SD-WAN|MPLS|QoS)\b',
            'finance_tools': r'\b(Bloomberg|Reuters|MUREX|Calypso|Summit|Aladdin|Risk Management|Treasury|Trading|Portfolio|Quantitative|Derivatives)\b',
            'framework': r'\b(React|Angular|Vue|Django|Flask|Spring|Express|Laravel|Rails|ASP\.NET|Node\.js|Bootstrap|jQuery)\b',
            'methodology': r'\b(Agile|Scrum|Kanban|DevOps|CI/CD|Lean|Six Sigma|ITIL|Prince2|Waterfall|Continuous Integration|Continuous Deployment)\b'
        }
        
        # Enhanced experience patterns with German
        self.experience_patterns = {
            'years_german': r'(\d+)\+?\s*Jahre?\s*(Erfahrung|Berufserfahrung|Praxis|Kenntnisse|Expertise)',
            'years_english': r'(\d+)\+?\s*years?\s*(experience|of experience|expertise|background)',
            'banking_german': r'\b(Bank|Banking|Finanz|Finance|Treasury|Credit|Risk|Kredit|Bankenumfeld|Finanzbranche|Kapitalmarkt|Investment|Asset Management|Wealth Management)\b',
            'leadership_german': r'\b(Team|Lead|Manager|Führung|Verantwortung|Leitung|Senior|Projektleitung|Teamleitung|Vorgesetzter)\b',
            'senior_level': r'\b(Senior|Lead|Principal|Expert|Spezialist|Experte|Chief|Director|Head|Architekt|Consultant)\b',
            'client_facing': r'\b(Client|Kunde|Customer|Kundenkontakt|Beratung|Consulting|Sales|Vertrieb|Account|Relationship)\b',
            'project_management': r'\b(Projekt|Project|Management|Planung|Planning|Koordination|Coordination|Durchführung|Implementation)\b'
        }
        
        # Enhanced education patterns
        self.education_patterns = {
            'degree_german': r'\b(Bachelor|Master|Diplom|PhD|Promotion|Doktor|Studium|BA|MA|MSc|BSc|FH|Universität|Hochschule|Fachhochschule)\b',
            'field_german': r'\b(Informatik|Computer Science|Wirtschaftsinformatik|BWL|VWL|Betriebswirtschaft|Volkswirtschaft|Mathematik|Physik|Ingenieur|Engineering|Finance|Banking|Wirtschaft|Economics|Statistics|Statistik)\b',
            'certification': r'\b(Zertifikat|Zertifizierung|Certification|CISSP|PMP|CISA|CFA|FRM|Certified|Certificate|Prince2|Scrum Master|AWS Certified|Azure Certified)\b'
        }
        
        # Soft skills mapping and deduplication
        self.soft_skills_groups = {
            'communication': {
                'patterns': r'\b(Kommunikation|communication|Präsentation|presentation|verbal|schriftlich|written|speaking|listening)\b',
                'keywords': ['communication', 'kommunikation', 'presentation', 'verbal', 'written']
            },
            'teamwork': {
                'patterns': r'\b(Teamwork|Zusammenarbeit|collaboration|Team|kooperativ|cooperative|teamfähig)\b',
                'keywords': ['teamwork', 'zusammenarbeit', 'collaboration', 'cooperative']
            },
            'analytical': {
                'patterns': r'\b(analytisch|analytical|Analyse|analysis|konzeptionell|conceptual|logical|logisch)\b',
                'keywords': ['analytical', 'analysis', 'conceptual', 'logical']
            },
            'initiative': {
                'patterns': r'\b(Initiative|Eigeninitiative|proaktiv|proactive|self-motivated|selbstständig|independent)\b',
                'keywords': ['initiative', 'proactive', 'self-motivated', 'independent']
            },
            'problem_solving': {
                'patterns': r'\b(Lösungsorientierung|problem solving|Problemlösung|troubleshooting|solution-oriented|kreativ|creative)\b',
                'keywords': ['problem solving', 'solution-oriented', 'troubleshooting', 'creative']
            },
            'leadership': {
                'patterns': r'\b(Führung|leadership|Management|mentor|guide|Leitung|Verantwortung|responsibility)\b',
                'keywords': ['leadership', 'management', 'mentoring', 'responsibility']
            },
            'flexibility': {
                'patterns': r'\b(Flexibilität|flexibility|adaptability|Anpassungsfähigkeit|versatile|vielseitig)\b',
                'keywords': ['flexibility', 'adaptability', 'versatile']
            },
            'customer_service': {
                'patterns': r'\b(Kundenservice|customer service|client facing|kundenorientiert|customer-oriented|Beratung|consulting)\b',
                'keywords': ['customer service', 'client facing', 'customer-oriented', 'consulting']
            }
        }

    def extract_requirements(self, job_description: str) -> FiveDimensionalRequirements:
        """Extract 5-dimensional requirements from job description."""
        
        # Clean and normalize text
        text = normalize_text(job_description)
        
        # Extract each dimension
        technical = self._extract_technical_requirements(text)
        business = self._extract_business_requirements(text)
        soft_skills = self._extract_soft_skills_deduplicated(text)
        experience = self._extract_experience_requirements(text)
        education = self._extract_education_requirements(text)
        
        # Apply deduplication and consolidation
        business = self._consolidate_business_requirements(business)
        education = self._consolidate_education_requirements(education)
        
        return FiveDimensionalRequirements(
            technical=technical,
            business=business,
            soft_skills=soft_skills,
            experience=experience,
            education=education
        )
    
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
                context = get_context(text, match.start(), match.end())
                proficiency = determine_proficiency(context)
                is_mandatory_req = is_mandatory(context)
                
                requirements.append(TechnicalRequirement(
                    skill=skill,
                    proficiency_level=proficiency,
                    category=category,
                    is_mandatory=is_mandatory_req,
                    confidence=0.8,
                    context=context[:100]
                ))
        
        return requirements
    
    def _extract_business_requirements(self, text: str) -> List[BusinessRequirement]:
        """Extract business domain and industry experience with enhanced patterns."""
        requirements = []
        
        # Banking/Finance domain detection
        banking_matches = list(re.finditer(self.experience_patterns['banking_german'], text, re.IGNORECASE))
        for match in banking_matches:
            context = get_context(text, match.start(), match.end())
            years = extract_years_from_context(context)
            
            requirements.append(BusinessRequirement(
                domain="banking",
                experience_type="industry_knowledge",
                years_required=years,
                is_mandatory=True,
                confidence=0.9,
                context=context[:150]
            ))
        
        # Client-facing experience
        client_matches = list(re.finditer(self.experience_patterns['client_facing'], text, re.IGNORECASE))
        for match in client_matches:
            context = get_context(text, match.start(), match.end())
            years = extract_years_from_context(context)
            
            requirements.append(BusinessRequirement(
                domain="client_services",
                experience_type="client_facing",
                years_required=years,
                is_mandatory=is_mandatory(context),
                confidence=0.8,
                context=context[:150]
            ))
        
        # Project management experience
        project_matches = list(re.finditer(self.experience_patterns['project_management'], text, re.IGNORECASE))
        for match in project_matches:
            context = get_context(text, match.start(), match.end())
            years = extract_years_from_context(context)
            
            requirements.append(BusinessRequirement(
                domain="project_management",
                experience_type="project_leadership",
                years_required=years,
                is_mandatory=is_mandatory(context),
                confidence=0.8,
                context=context[:150]
            ))
        
        # Network security domain
        if re.search(r'\b(Security|Sicherheit|Network|Netzwerk|Firewall|NSX|Cybersecurity|InfoSec)\b', text, re.IGNORECASE):
            requirements.append(BusinessRequirement(
                domain="network_security",
                experience_type="technical_domain",
                years_required=0,
                is_mandatory=True,
                confidence=0.8,
                context="Network security related role"
            ))
        
        # Investment/Finance domain
        if re.search(r'\b(Investment|Portfolio|Asset|Risk Management|Treasury|Trading|Capital Markets|Derivatives)\b', text, re.IGNORECASE):
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
                context = get_context(text, match.start(), match.end())
                
                found_skills[skill_group] = SoftSkillRequirement(
                    skill=skill_group.replace('_', ' ').title(),
                    context=context[:100],
                    importance="important",
                    confidence=0.7
                )
        
        return list(found_skills.values())
    
    def _extract_experience_requirements(self, text: str) -> List[ExperienceRequirement]:
        """Extract experience requirements with improved German patterns."""
        requirements = []
        found_types = set()  # Prevent duplicates
        
        # Years of experience - German patterns
        for pattern_name, pattern in [('years_german', self.experience_patterns['years_german']),
                                     ('years_english', self.experience_patterns['years_english'])]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                years = int(match.group(1))
                context = get_context(text, match.start(), match.end())
                
                exp_type = f"general_experience_{years}years"
                if exp_type not in found_types:
                    found_types.add(exp_type)
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
            if "senior_level" not in found_types:
                found_types.add("senior_level")
                context = get_context(text, match.start(), match.end())
                
                requirements.append(ExperienceRequirement(
                    type="senior_level",
                    description="Senior level experience required",
                    years_required=5,  # Estimate for senior roles
                    is_mandatory=True,
                    confidence=0.8
                ))
        
        # Leadership experience
        leadership_matches = re.finditer(self.experience_patterns['leadership_german'], text, re.IGNORECASE)
        for match in leadership_matches:
            if "leadership" not in found_types:
                found_types.add("leadership")
                context = get_context(text, match.start(), match.end())
                years = extract_years_from_context(context)
                
                requirements.append(ExperienceRequirement(
                    type="leadership",
                    description="Team leadership and management experience",
                    years_required=years or 2,  # Default to 2 years if not specified
                    is_mandatory=is_mandatory(context),
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
            
            context = get_context(text, match.start(), match.end())
            
            # Try to find field
            field_match = re.search(self.education_patterns['field_german'], context, re.IGNORECASE)
            field = field_match.group() if field_match else "unspecified"
            
            # Normalize degree names
            degree_normalized = self._normalize_degree(degree)
            
            requirements.append(EducationRequirement(
                level=degree_normalized,
                field=field,
                is_mandatory=is_mandatory(context),
                alternatives=[],
                confidence=0.8
            ))
        
        # Certification requirements
        cert_matches = re.finditer(self.education_patterns['certification'], text, re.IGNORECASE)
        for match in cert_matches:
            cert = match.group()
            cert_key = f"cert_{cert.lower()}"
            
            if cert_key not in found_degrees:
                found_degrees.add(cert_key)
                context = get_context(text, match.start(), match.end())
                
                requirements.append(EducationRequirement(
                    level="certification",
                    field=cert,
                    is_mandatory=is_mandatory(context),
                    alternatives=[],
                    confidence=0.8
                ))
        
        return requirements
    
    def _normalize_degree(self, degree: str) -> str:
        """Normalize degree names to standard forms."""
        degree_mapping = {
            'bachelor': 'bachelor',
            'ba': 'bachelor',
            'bsc': 'bachelor',
            'master': 'master',
            'ma': 'master',
            'msc': 'master',
            'diplom': 'diploma',
            'phd': 'phd',
            'promotion': 'phd',
            'doktor': 'phd',
            'studium': 'degree',
            'fh': 'university_applied_sciences',
            'universität': 'university',
            'hochschule': 'university',
            'fachhochschule': 'university_applied_sciences'
        }
        
        return degree_mapping.get(degree.lower(), degree)
    
    def _consolidate_business_requirements(self, requirements: List[BusinessRequirement]) -> List[BusinessRequirement]:
        """Consolidate duplicate business requirements."""
        if not requirements:
            return []
        
        # Convert to dict for consolidation
        req_dicts = [asdict(req) for req in requirements]
        consolidated_dicts = consolidate_business_requirements(req_dicts)
        
        # Convert back to objects
        return [BusinessRequirement(**req_dict) for req_dict in consolidated_dicts]
    
    def _consolidate_education_requirements(self, requirements: List[EducationRequirement]) -> List[EducationRequirement]:
        """Consolidate duplicate education requirements."""
        if not requirements:
            return []
        
        # Convert to dict for consolidation
        req_dicts = [asdict(req) for req in requirements]
        consolidated_dicts = consolidate_education_requirements(req_dicts)
        
        # Convert back to objects
        return [EducationRequirement(**req_dict) for req_dict in consolidated_dicts]
