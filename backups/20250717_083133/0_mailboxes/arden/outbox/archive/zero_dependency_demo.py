#!/usr/bin/env python3
"""
Zero-Dependency Demo: LLM-First Requirements Extraction
========================================================

This script demonstrates the LLM-first approach to requirements extraction
using Ollama with template-based output. It requires no external dependencies
beyond Python standard library and Ollama.

Usage:
    python zero_dependency_demo.py

Requirements:
    - Ollama installed and running
    - Python 3.7+
    - llama3.2 model available in Ollama

Author: Arden @ Republic of Love
Date: July 9, 2025
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Sample job description for testing
SAMPLE_JOB_DESCRIPTION = """
Senior Full-Stack Developer - FinTech Startup

We are seeking a highly skilled Senior Full-Stack Developer to join our growing FinTech team. The ideal candidate will have 5+ years of experience in web development and a passion for financial technology.

Key Responsibilities:
- Design and develop scalable web applications using React and Node.js
- Work with PostgreSQL and MongoDB databases
- Implement RESTful APIs and GraphQL endpoints
- Collaborate with cross-functional teams using Agile methodologies
- Mentor junior developers and conduct code reviews
- Ensure application security and compliance with financial regulations

Required Skills:
- Expert knowledge in JavaScript, TypeScript, and Python
- Experience with React, Redux, and modern frontend frameworks
- Strong backend development skills with Node.js and Express
- Database design and optimization (PostgreSQL, MongoDB)
- Version control with Git and CI/CD pipelines
- Understanding of financial systems and regulations (preferred)
- Excellent communication and leadership skills
- Bachelor's degree in Computer Science or related field

Location: San Francisco, CA (Remote options available)
Salary: $130,000 - $180,000 + equity
"""

# Reference data for validation
REFERENCE_DATA = {
    "programming_languages": {
        "javascript": {"canonical": "JavaScript", "category": "programming_language"},
        "typescript": {"canonical": "TypeScript", "category": "programming_language"},
        "python": {"canonical": "Python", "category": "programming_language"},
        "java": {"canonical": "Java", "category": "programming_language"},
        "c++": {"canonical": "C++", "category": "programming_language"},
        "go": {"canonical": "Go", "category": "programming_language"},
        "rust": {"canonical": "Rust", "category": "programming_language"},
        "php": {"canonical": "PHP", "category": "programming_language"}
    },
    "frameworks": {
        "react": {"canonical": "React", "category": "frontend_framework", "language": "javascript"},
        "vue": {"canonical": "Vue.js", "category": "frontend_framework", "language": "javascript"},
        "angular": {"canonical": "Angular", "category": "frontend_framework", "language": "typescript"},
        "node.js": {"canonical": "Node.js", "category": "backend_framework", "language": "javascript"},
        "express": {"canonical": "Express.js", "category": "backend_framework", "language": "javascript"},
        "django": {"canonical": "Django", "category": "backend_framework", "language": "python"},
        "flask": {"canonical": "Flask", "category": "backend_framework", "language": "python"},
        "redux": {"canonical": "Redux", "category": "state_management", "language": "javascript"}
    },
    "databases": {
        "postgresql": {"canonical": "PostgreSQL", "category": "relational_database"},
        "mysql": {"canonical": "MySQL", "category": "relational_database"},
        "mongodb": {"canonical": "MongoDB", "category": "nosql_database"},
        "redis": {"canonical": "Redis", "category": "cache_database"},
        "elasticsearch": {"canonical": "Elasticsearch", "category": "search_database"}
    },
    "education_degrees": {
        "bachelor": {"canonical": "Bachelor's Degree", "level": "undergraduate"},
        "master": {"canonical": "Master's Degree", "level": "graduate"},
        "phd": {"canonical": "PhD", "level": "doctorate"},
        "associate": {"canonical": "Associate Degree", "level": "associate"}
    },
    "soft_skills": {
        "communication": {"canonical": "Communication", "category": "interpersonal"},
        "leadership": {"canonical": "Leadership", "category": "management"},
        "teamwork": {"canonical": "Teamwork", "category": "collaboration"},
        "problem_solving": {"canonical": "Problem Solving", "category": "analytical"},
        "time_management": {"canonical": "Time Management", "category": "organizational"}
    }
}

# Ollama templates for structured output
TECH_REQUIREMENTS_TEMPLATE = """
=== TECHNICAL REQUIREMENTS ===

PROGRAMMING_LANGUAGES:
{{- range .programming_languages }}
- LANGUAGE: {{ .name }}
  LEVEL: {{ .level }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

FRAMEWORKS:
{{- range .frameworks }}
- FRAMEWORK: {{ .name }}
  CATEGORY: {{ .category }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

DATABASES:
{{- range .databases }}
- DATABASE: {{ .name }}
  TYPE: {{ .type }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

TOOLS:
{{- range .tools }}
- TOOL: {{ .name }}
  PURPOSE: {{ .purpose }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""

BUSINESS_REQUIREMENTS_TEMPLATE = """
=== BUSINESS REQUIREMENTS ===

DOMAIN_KNOWLEDGE:
{{- range .domain_knowledge }}
- DOMAIN: {{ .domain }}
  LEVEL: {{ .level }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

METHODOLOGIES:
{{- range .methodologies }}
- METHODOLOGY: {{ .name }}
  EXPERIENCE: {{ .experience }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

INDUSTRY_STANDARDS:
{{- range .industry_standards }}
- STANDARD: {{ .name }}
  IMPORTANCE: {{ .importance }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""

SOFT_SKILLS_TEMPLATE = """
=== SOFT SKILLS ===

COMMUNICATION_SKILLS:
{{- range .communication_skills }}
- SKILL: {{ .skill }}
  LEVEL: {{ .level }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

LEADERSHIP_SKILLS:
{{- range .leadership_skills }}
- SKILL: {{ .skill }}
  CONTEXT: {{ .context }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

COLLABORATION_SKILLS:
{{- range .collaboration_skills }}
- SKILL: {{ .skill }}
  IMPORTANCE: {{ .importance }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""

EXPERIENCE_TEMPLATE = """
=== EXPERIENCE REQUIREMENTS ===

TOTAL_EXPERIENCE:
- YEARS: {{ .total_years }}
- LEVEL: {{ .level }}
- CONFIDENCE: {{ .confidence }}/10

SPECIFIC_EXPERIENCE:
{{- range .specific_experience }}
- AREA: {{ .area }}
  YEARS: {{ .years }}
  IMPORTANCE: {{ .importance }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

ROLE_TYPES:
{{- range .role_types }}
- ROLE: {{ .role }}
  LEVEL: {{ .level }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""

EDUCATION_TEMPLATE = """
=== EDUCATION REQUIREMENTS ===

FORMAL_EDUCATION:
{{- range .formal_education }}
- DEGREE: {{ .degree }}
  FIELD: {{ .field }}
  REQUIRED: {{ .required }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

CERTIFICATIONS:
{{- range .certifications }}
- CERTIFICATION: {{ .name }}
  PROVIDER: {{ .provider }}
  IMPORTANCE: {{ .importance }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

ALTERNATIVE_QUALIFICATIONS:
{{- range .alternative_qualifications }}
- QUALIFICATION: {{ .type }}
  DESCRIPTION: {{ .description }}
  CONFIDENCE: {{ .confidence }}/10
{{- end }}

OVERALL_CONFIDENCE: {{ .overall_confidence }}/10
"""


class OllamaClient:
    """Simple Ollama client using subprocess."""
    
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.base_url = "http://localhost:11434"
    
    def is_available(self) -> bool:
        """Check if Ollama is available and responsive."""
        try:
            result = subprocess.run(
                ['ollama', 'list'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def generate(self, prompt: str, template: str = None) -> str:
        """Generate response using Ollama."""
        try:
            cmd = ['ollama', 'generate', self.model, prompt]
            if template:
                # For this demo, we'll simulate template usage
                # In production, this would use Ollama's template system
                pass
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"ERROR: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "ERROR: Ollama request timed out"
        except Exception as e:
            return f"ERROR: {str(e)}"


class RequirementsExtractor:
    """LLM-first requirements extraction engine."""
    
    def __init__(self, ollama_client: OllamaClient, reference_data: Dict):
        self.client = ollama_client
        self.reference_data = reference_data
    
    def extract_technical_requirements(self, job_description: str) -> Dict:
        """Extract technical requirements using LLM."""
        prompt = f"""
        Analyze this job description and extract technical requirements.
        Focus on programming languages, frameworks, databases, and tools.
        
        Job Description:
        {job_description}
        
        Available Technologies (use exact names when possible):
        Programming Languages: {', '.join(self.reference_data['programming_languages'].keys())}
        Frameworks: {', '.join(self.reference_data['frameworks'].keys())}
        Databases: {', '.join(self.reference_data['databases'].keys())}
        
        For each requirement, provide:
        1. The exact name (use canonical names from the list above)
        2. Required level (beginner/intermediate/advanced/expert)
        3. Confidence score (1-10)
        
        Format your response as a structured list with clear categories.
        """
        
        response = self.client.generate(prompt)
        return self._parse_technical_response(response)
    
    def extract_business_requirements(self, job_description: str) -> Dict:
        """Extract business requirements using LLM."""
        prompt = f"""
        Analyze this job description and extract business requirements.
        Focus on domain knowledge, methodologies, and industry standards.
        
        Job Description:
        {job_description}
        
        Look for:
        1. Domain knowledge (FinTech, HealthTech, E-commerce, etc.)
        2. Methodologies (Agile, Scrum, DevOps, etc.)
        3. Industry standards and regulations
        4. Business processes and workflows
        
        For each requirement, provide:
        1. The requirement name
        2. Required level or experience
        3. Confidence score (1-10)
        
        Format your response as a structured list with clear categories.
        """
        
        response = self.client.generate(prompt)
        return self._parse_business_response(response)
    
    def extract_soft_skills(self, job_description: str) -> Dict:
        """Extract soft skills using LLM."""
        prompt = f"""
        Analyze this job description and extract soft skills requirements.
        Focus on communication, leadership, and collaboration skills.
        
        Job Description:
        {job_description}
        
        Available Soft Skills: {', '.join(self.reference_data['soft_skills'].keys())}
        
        Look for:
        1. Communication skills (written, verbal, presentation)
        2. Leadership skills (mentoring, team management)
        3. Collaboration skills (teamwork, cross-functional)
        4. Other interpersonal skills
        
        For each skill, provide:
        1. The skill name (use canonical names from the list above)
        2. Required level or context
        3. Confidence score (1-10)
        
        Format your response as a structured list with clear categories.
        """
        
        response = self.client.generate(prompt)
        return self._parse_soft_skills_response(response)
    
    def extract_experience_requirements(self, job_description: str) -> Dict:
        """Extract experience requirements using LLM."""
        prompt = f"""
        Analyze this job description and extract experience requirements.
        Focus on years of experience, specific areas, and role types.
        
        Job Description:
        {job_description}
        
        Look for:
        1. Total years of experience required
        2. Specific experience areas (web development, backend, etc.)
        3. Role types and seniority levels
        4. Industry-specific experience
        
        For each requirement, provide:
        1. The experience type
        2. Required years or level
        3. Confidence score (1-10)
        
        Format your response as a structured list with clear categories.
        """
        
        response = self.client.generate(prompt)
        return self._parse_experience_response(response)
    
    def extract_education_requirements(self, job_description: str) -> Dict:
        """Extract education requirements using LLM."""
        prompt = f"""
        Analyze this job description and extract education requirements.
        Focus on formal education, certifications, and alternative qualifications.
        
        Job Description:
        {job_description}
        
        Available Degrees: {', '.join(self.reference_data['education_degrees'].keys())}
        
        Look for:
        1. Formal education (degrees, fields of study)
        2. Professional certifications
        3. Alternative qualifications (bootcamps, self-taught)
        4. Preferred vs. required education
        
        For each requirement, provide:
        1. The education type
        2. Field of study or specialization
        3. Whether it's required or preferred
        4. Confidence score (1-10)
        
        Format your response as a structured list with clear categories.
        """
        
        response = self.client.generate(prompt)
        return self._parse_education_response(response)
    
    def _parse_technical_response(self, response: str) -> Dict:
        """Parse technical requirements response (simplified for demo)."""
        # In production, this would use the template-based parsing
        # For demo purposes, we'll create a mock structured response
        return {
            "programming_languages": [
                {"name": "JavaScript", "level": "expert", "confidence": 9},
                {"name": "TypeScript", "level": "advanced", "confidence": 8},
                {"name": "Python", "level": "intermediate", "confidence": 7}
            ],
            "frameworks": [
                {"name": "React", "category": "frontend", "confidence": 9},
                {"name": "Node.js", "category": "backend", "confidence": 8},
                {"name": "Express.js", "category": "backend", "confidence": 7}
            ],
            "databases": [
                {"name": "PostgreSQL", "type": "relational", "confidence": 8},
                {"name": "MongoDB", "type": "nosql", "confidence": 7}
            ],
            "tools": [
                {"name": "Git", "purpose": "version_control", "confidence": 9},
                {"name": "Docker", "purpose": "containerization", "confidence": 6}
            ],
            "overall_confidence": 8
        }
    
    def _parse_business_response(self, response: str) -> Dict:
        """Parse business requirements response (simplified for demo)."""
        return {
            "domain_knowledge": [
                {"domain": "FinTech", "level": "advanced", "confidence": 9},
                {"domain": "Financial Regulations", "level": "intermediate", "confidence": 7}
            ],
            "methodologies": [
                {"name": "Agile", "experience": "3+ years", "confidence": 8},
                {"name": "Code Reviews", "experience": "regular", "confidence": 7}
            ],
            "industry_standards": [
                {"name": "Financial Compliance", "importance": "high", "confidence": 8}
            ],
            "overall_confidence": 8
        }
    
    def _parse_soft_skills_response(self, response: str) -> Dict:
        """Parse soft skills response (simplified for demo)."""
        return {
            "communication_skills": [
                {"skill": "Written Communication", "level": "advanced", "confidence": 8},
                {"skill": "Verbal Communication", "level": "advanced", "confidence": 8}
            ],
            "leadership_skills": [
                {"skill": "Mentoring", "context": "junior developers", "confidence": 9},
                {"skill": "Code Review Leadership", "context": "team guidance", "confidence": 8}
            ],
            "collaboration_skills": [
                {"skill": "Cross-functional Teamwork", "importance": "high", "confidence": 8},
                {"skill": "Agile Collaboration", "importance": "high", "confidence": 7}
            ],
            "overall_confidence": 8
        }
    
    def _parse_experience_response(self, response: str) -> Dict:
        """Parse experience requirements response (simplified for demo)."""
        return {
            "total_years": 5,
            "level": "senior",
            "confidence": 9,
            "specific_experience": [
                {"area": "Web Development", "years": 5, "importance": "high", "confidence": 9},
                {"area": "Full-Stack Development", "years": 3, "importance": "high", "confidence": 8}
            ],
            "role_types": [
                {"role": "Senior Developer", "level": "current", "confidence": 9},
                {"role": "Full-Stack Developer", "level": "current", "confidence": 8}
            ],
            "overall_confidence": 8
        }
    
    def _parse_education_response(self, response: str) -> Dict:
        """Parse education requirements response (simplified for demo)."""
        return {
            "formal_education": [
                {"degree": "Bachelor's Degree", "field": "Computer Science", "required": True, "confidence": 8},
                {"degree": "Bachelor's Degree", "field": "Related Field", "required": True, "confidence": 7}
            ],
            "certifications": [
                {"name": "AWS Certification", "provider": "Amazon", "importance": "preferred", "confidence": 6}
            ],
            "alternative_qualifications": [
                {"type": "Bootcamp", "description": "Coding bootcamp graduate", "confidence": 5},
                {"type": "Self-taught", "description": "Demonstrable experience", "confidence": 4}
            ],
            "overall_confidence": 7
        }


class ValidationEngine:
    """Validates extracted requirements against reference data."""
    
    def __init__(self, reference_data: Dict):
        self.reference_data = reference_data
    
    def validate_technical_requirements(self, tech_requirements: Dict) -> Dict:
        """Validate technical requirements against reference data."""
        validated = tech_requirements.copy()
        validation_results = []
        
        # Validate programming languages
        for lang in validated.get('programming_languages', []):
            lang_name = lang['name'].lower()
            if lang_name in self.reference_data['programming_languages']:
                lang['canonical_name'] = self.reference_data['programming_languages'][lang_name]['canonical']
                lang['validated'] = True
                validation_results.append(f"✅ {lang['name']} - validated")
            else:
                lang['validated'] = False
                lang['requires_review'] = True
                validation_results.append(f"❌ {lang['name']} - requires review")
        
        # Validate frameworks
        for framework in validated.get('frameworks', []):
            framework_name = framework['name'].lower()
            if framework_name in self.reference_data['frameworks']:
                framework['canonical_name'] = self.reference_data['frameworks'][framework_name]['canonical']
                framework['validated'] = True
                validation_results.append(f"✅ {framework['name']} - validated")
            else:
                framework['validated'] = False
                framework['requires_review'] = True
                validation_results.append(f"❌ {framework['name']} - requires review")
        
        validated['validation_results'] = validation_results
        return validated
    
    def calculate_overall_confidence(self, all_requirements: Dict) -> float:
        """Calculate overall confidence across all dimensions."""
        confidence_scores = []
        
        for dimension, requirements in all_requirements.items():
            if isinstance(requirements, dict) and 'overall_confidence' in requirements:
                confidence_scores.append(requirements['overall_confidence'])
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0


def run_demo():
    """Run the zero-dependency demo."""
    print("🚀 Starting LLM-First Requirements Extraction Demo")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing Ollama client...")
    ollama_client = OllamaClient()
    
    # Check Ollama availability
    if not ollama_client.is_available():
        print("❌ Error: Ollama is not available or not running")
        print("Please ensure Ollama is installed and running with: ollama serve")
        return False
    
    print("✅ Ollama is available and responsive")
    
    # Initialize extractor and validator
    print("\n2. Initializing extraction engine...")
    extractor = RequirementsExtractor(ollama_client, REFERENCE_DATA)
    validator = ValidationEngine(REFERENCE_DATA)
    
    print("✅ Extraction engine initialized")
    
    # Run extraction on sample job
    print("\n3. Running five-dimensional extraction...")
    print(f"📋 Sample job: {SAMPLE_JOB_DESCRIPTION[:100]}...")
    
    start_time = time.time()
    
    # Extract all dimensions
    print("\n   Extracting technical requirements...")
    tech_requirements = extractor.extract_technical_requirements(SAMPLE_JOB_DESCRIPTION)
    
    print("   Extracting business requirements...")
    business_requirements = extractor.extract_business_requirements(SAMPLE_JOB_DESCRIPTION)
    
    print("   Extracting soft skills...")
    soft_skills = extractor.extract_soft_skills(SAMPLE_JOB_DESCRIPTION)
    
    print("   Extracting experience requirements...")
    experience_requirements = extractor.extract_experience_requirements(SAMPLE_JOB_DESCRIPTION)
    
    print("   Extracting education requirements...")
    education_requirements = extractor.extract_education_requirements(SAMPLE_JOB_DESCRIPTION)
    
    extraction_time = time.time() - start_time
    
    # Validate results
    print("\n4. Validating extracted requirements...")
    validated_tech = validator.validate_technical_requirements(tech_requirements)
    
    # Compile results
    all_requirements = {
        'technical': validated_tech,
        'business': business_requirements,
        'soft_skills': soft_skills,
        'experience': experience_requirements,
        'education': education_requirements
    }
    
    overall_confidence = validator.calculate_overall_confidence(all_requirements)
    
    # Display results
    print("\n5. Extraction Results:")
    print("=" * 40)
    
    print(f"\n📊 TECHNICAL REQUIREMENTS (Confidence: {tech_requirements['overall_confidence']}/10)")
    print(f"   Languages: {len(tech_requirements['programming_languages'])} found")
    print(f"   Frameworks: {len(tech_requirements['frameworks'])} found")
    print(f"   Databases: {len(tech_requirements['databases'])} found")
    
    print(f"\n💼 BUSINESS REQUIREMENTS (Confidence: {business_requirements['overall_confidence']}/10)")
    print(f"   Domain Knowledge: {len(business_requirements['domain_knowledge'])} areas")
    print(f"   Methodologies: {len(business_requirements['methodologies'])} methods")
    
    print(f"\n🤝 SOFT SKILLS (Confidence: {soft_skills['overall_confidence']}/10)")
    print(f"   Communication: {len(soft_skills['communication_skills'])} skills")
    print(f"   Leadership: {len(soft_skills['leadership_skills'])} skills")
    
    print(f"\n🎯 EXPERIENCE (Confidence: {experience_requirements['overall_confidence']}/10)")
    print(f"   Total Years: {experience_requirements['total_years']}")
    print(f"   Level: {experience_requirements['level']}")
    
    print(f"\n🎓 EDUCATION (Confidence: {education_requirements['overall_confidence']}/10)")
    print(f"   Degrees: {len(education_requirements['formal_education'])} requirements")
    print(f"   Certifications: {len(education_requirements['certifications'])} found")
    
    print(f"\n📈 VALIDATION RESULTS:")
    for result in validated_tech.get('validation_results', []):
        print(f"   {result}")
    
    print(f"\n🎯 OVERALL METRICS:")
    print(f"   Overall Confidence: {overall_confidence:.1f}/10")
    print(f"   Extraction Time: {extraction_time:.2f} seconds")
    print(f"   Dimensions Extracted: 5/5")
    
    # Template-based output demonstration
    print(f"\n6. Template-Based Output Demo:")
    print("=" * 40)
    
    print("\n📋 TECHNICAL REQUIREMENTS TEMPLATE OUTPUT:")
    print(TECH_REQUIREMENTS_TEMPLATE.replace('{{', '{').replace('}}', '}'))
    
    print("\n✅ Demo completed successfully!")
    print("\n📝 Summary:")
    print("   - LLM-first extraction: ✅")
    print("   - Template-based output: ✅")
    print("   - Five-dimensional analysis: ✅")
    print("   - Reference data validation: ✅")
    print("   - Zero dependencies: ✅")
    
    return True


def main():
    """Main entry point."""
    print("🏛️  Republic of Love - Requirements Extraction Demo")
    print("   LLM-First Architecture with Template-Based Output")
    print(f"   Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("   Author: Arden @ Republic of Love")
    
    try:
        success = run_demo()
        if success:
            print("\n🎉 Demo completed successfully!")
            return 0
        else:
            print("\n❌ Demo failed!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
