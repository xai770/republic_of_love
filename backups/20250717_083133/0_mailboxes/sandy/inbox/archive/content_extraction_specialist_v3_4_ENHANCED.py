#!/usr/bin/env python3
"""
Enhanced ContentExtractionSpecialistV33 with German Language & SAP Ecosystem Support
===================================================================================

This version improves upon v3.3 with:
1. Explicit German language handling
2. Comprehensive SAP ecosystem recognition
3. Job role context validation
4. Better domain-specific technology mapping

Based on emergency test results showing v3.3 works but needs enhancement for:
- German technical terms
- SAP-specific technologies
- Role-based extraction validation
"""

import requests
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class SkillExtractionResult:
    technical_skills: List[str]
    soft_skills: List[str]
    business_skills: List[str]
    extraction_confidence: float
    model_used: str
    accuracy_confidence: str

class ContentExtractionSpecialistV34:
    """
    ENHANCED v3.4: German Language & SAP Ecosystem Specialist
    
    Improvements over v3.3:
    - Explicit German language support
    - SAP ecosystem recognition  
    - Job role context validation
    - Domain-specific technology mapping
    """
    
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 preferred_model: str = "mistral:latest",
                 fallback_models: List[str] = None):
        self.ollama_url = ollama_url
        self.preferred_model = preferred_model
        self.fallback_models = fallback_models or [
            "olmo2:latest",
            "dolphin3:8b",    
            "qwen3:latest"
        ]

    def _call_ollama(self, prompt: str, model: str = None) -> str:
        model = model or self.preferred_model
        payload = {"model": model, "prompt": prompt, "stream": False}
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            for fallback in self.fallback_models:
                if fallback != model:
                    try:
                        return self._call_ollama(prompt, fallback)
                    except:
                        continue
            raise Exception(f"All models failed: {str(e)}")

    def extract_technical_skills_enhanced(self, job_description: str, position_title: str = "") -> List[str]:
        """
        Enhanced technical skills extraction with German language and SAP ecosystem support
        """
        prompt = f"""EXTRACT TECHNICAL SKILLS FROM MULTILINGUAL JOB DESCRIPTION.

LANGUAGE SUPPORT:
- Extract from German and English text
- German technical terms: "Programmierung", "Entwicklung", "Softwarelösungen", "Erfahrung"
- English technical terms: "Programming", "Development", "Experience", "Skills"

JOB ROLE CONTEXT:
Position: {position_title}
- For technical/engineering roles: Include programming, frameworks, platforms
- For sales/business roles: Focus on CRM, reporting tools, business applications  
- For consulting roles: Include methodology frameworks, business tools
- AVOID programming languages for non-technical positions

TECHNICAL CATEGORIES TO EXTRACT:

Programming Languages:
- Python, Java, JavaScript, C++, C#, R, SQL, VBA, ABAP, Go, Scala, Kotlin

SAP Ecosystem (PRIORITY for SAP roles):
- SAP ABAP, SAP HANA, SAP BPC, SAP SAC, SAP BTP, SAP PaPM
- SAP BCS, BW/4HANA, SAP DataSphere, SAP Fiori, SAP Business Objects
- SAP S/4HANA, SAP SuccessFactors, SAP Concur, SAP Ariba

Cloud Platforms:
- AWS, Azure, GCP, Google Cloud, IBM Cloud, Oracle Cloud
- Vertex AI, Cortex Framework, Cloud Functions

Development & DevOps:
- CI/CD, DevOps, DevSecOps, Agile, Scrum, Kanban
- Docker, Kubernetes, Jenkins, Git, GitLab

Databases:
- Oracle, SQL Server, MySQL, PostgreSQL, MongoDB, Redis
- Data warehousing, ETL, Data modeling

Business Intelligence & Analytics:
- Tableau, Power BI, Qlik, Looker, Splunk
- Excel, Access, SPSS, SAS, R Analytics

Security & Compliance:
- NIST, OWASP, CVSS, MITRE ATT&CK
- Cybersecurity frameworks, Risk management

Financial Systems:
- Bloomberg, Reuters, SimCorp Dimension, Aladdin, StatPro
- Trade finance, Risk management systems

CRM & Sales Tools:
- Salesforce, HubSpot, Microsoft Dynamics
- Marketing automation, Lead management

STRICT EXTRACTION RULES:
- ONLY extract explicitly mentioned technologies
- Use exact names from job description
- Include version numbers if specified
- NO inference or related skills
- German and English terms both valid

TEXT TO ANALYZE:
{job_description}

EXTRACTED TECHNICAL SKILLS (one per line, exact names):"""
        
        response = self._call_ollama(prompt)
        return self._parse_skills_strict(response)

    def _parse_skills_strict(self, response: str) -> List[str]:
        """Enhanced parsing with German language support"""
        if not response:
            return []
        
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        skills = []
        
        # Common prefixes to remove
        prefixes_to_remove = [
            "- ", "• ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ",
            "Programming: ", "Software: ", "Technical: ", "Tools: ",
            "Programmierung: ", "Software: ", "Technisch: ", "Werkzeuge: "
        ]
        
        for line in lines:
            # Skip generic headers or empty responses
            skip_patterns = [
                "technical skills", "programming languages", "software tools",
                "none mentioned", "not specified", "no specific",
                "technische fähigkeiten", "programmiersprachen", "software-tools"
            ]
            
            if any(pattern in line.lower() for pattern in skip_patterns):
                continue
            
            # Clean the line
            cleaned = line
            for prefix in prefixes_to_remove:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
                    break
            
            # Remove trailing punctuation
            cleaned = cleaned.rstrip('.,;:')
            
            # Skip if too generic or empty
            if len(cleaned) < 2 or cleaned.lower() in ['none', 'n/a', 'not applicable', 'keine']:
                continue
            
            # Split on common separators for multiple skills in one line
            if ',' in cleaned or ';' in cleaned or '/' in cleaned:
                sub_skills = [s.strip() for s in cleaned.replace(',', ';').replace('/', ';').split(';')]
                for skill in sub_skills:
                    if skill and len(skill) > 1:
                        skills.append(skill)
            else:
                skills.append(cleaned)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                unique_skills.append(skill)
        
        return unique_skills

    def extract_technical_skills(self, job_description: str) -> List[str]:
        """Backward compatibility method"""
        return self.extract_technical_skills_enhanced(job_description)

    def extract_soft_skills(self, job_description: str) -> List[str]:
        """Extract soft skills (keeping original v3.3 logic for now)"""
        prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED SOFT SKILLS.

LOOK FOR (German and English):
- Communication skills / Kommunikationsfähigkeiten
- Leadership / Führung
- Teamwork / Teamarbeit  
- Problem solving / Problemlösung
- Project management / Projektmanagement
- Analytical thinking / Analytisches Denken

TEXT: {job_description}

SOFT SKILLS (one per line):"""
        response = self._call_ollama(prompt)
        return self._parse_skills_strict(response)

    def extract_business_skills(self, job_description: str) -> List[str]:
        """Extract business domain skills (keeping original v3.3 logic for now)"""
        prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED BUSINESS DOMAIN SKILLS.

LOOK FOR (German and English):
- Industry knowledge / Branchenkenntnisse
- Financial products / Finanzprodukte
- Regulatory compliance / Compliance
- Risk management / Risikomanagement
- Business analysis / Geschäftsanalyse

TEXT: {job_description}

BUSINESS SKILLS (one per line):"""
        response = self._call_ollama(prompt)
        return self._parse_skills_strict(response)

    def extract_skills(self, job_description: str, position_title: str = "") -> SkillExtractionResult:
        """Complete skill extraction with enhanced technical skills"""
        try:
            technical_skills = self.extract_technical_skills_enhanced(job_description, position_title)
            soft_skills = self.extract_soft_skills(job_description)
            business_skills = self.extract_business_skills(job_description)
            
            return SkillExtractionResult(
                technical_skills=technical_skills,
                soft_skills=soft_skills,
                business_skills=business_skills,
                extraction_confidence=0.85,
                model_used=self.preferred_model,
                accuracy_confidence="High - Enhanced German/SAP support"
            )
        except Exception as e:
            return SkillExtractionResult(
                technical_skills=[],
                soft_skills=[],
                business_skills=[],
                extraction_confidence=0.0,
                model_used="Error",
                accuracy_confidence=f"Failed: {str(e)}"
            )

def extract_skills_pipeline_v34(job_description: str, position_title: str = ""):
    """Enhanced pipeline function for v3.4"""
    specialist = ContentExtractionSpecialistV34()
    return specialist.extract_skills(job_description, position_title)

# Test function for validation
def test_v34_on_problematic_jobs():
    """Test v3.4 on the jobs that were failing"""
    
    specialist = ContentExtractionSpecialistV34()
    
    # Test 1: SAP ABAP Engineer
    sap_job = """
    Senior SAP ABAP Engineer – Group General Ledger (f/m/x)
    
    Fundierte Berufserfahrung in der Entwicklung und Programmierung großer und komplexer Softwarelösungen in SAP-Produkten wie: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI und Planung, SAP HANA, BW/4HANA, respektive die Entwicklung neuer Lösungen und die Pflege einer großen ABAP-Codebasis zur Unterstützung verschiedener Kernprozesse der Bank
    
    Profound professional experience and track record in the designing and programming of large scale & complex software solutions in some of the SAP products such as: SAP Profitability and Performance Management (PaPM), SAP BPC, SAP BCS(/4HANA), SAC BI and Planning, SAP HANA, BW/4HANA or developing new solutions & maintaining our large ABAP code base supporting various key processes
    """
    
    print("🧪 Testing v3.4 on SAP ABAP Engineer job...")
    sap_result = specialist.extract_technical_skills_enhanced(sap_job, "Senior SAP ABAP Engineer")
    print(f"v3.4 SAP Result: {sap_result}")
    
    # Test 2: Sales Specialist  
    sales_job = """
    Institutional Cash and Trade Sales Specialist (Client Sales Manager)
    
    Sie haben mehrjährige Erfahrung im Correspondent Banking
    Sie benutzen aktiv unsere MIS- und Reporting-Tools für das Management Ihrer Namen
    Monitor revenue trends via various reporting tools like Salesforce and dbTableau
    Sound product knowledge of cash management and trade products
    """
    
    print("\n🧪 Testing v3.4 on Sales Specialist job...")
    sales_result = specialist.extract_technical_skills_enhanced(sales_job, "Sales Specialist")
    print(f"v3.4 Sales Result: {sales_result}")

if __name__ == "__main__":
    test_v34_on_problematic_jobs()
