#!/usr/bin/env python3
"""
Technical Requirements Extraction Specialist - FIXED VERSION
============================================================

This is a corrected version of the technical extraction specialist that:
1. Actually reads the job description text
2. Doesn't fall back to hardcoded examples
3. Properly extracts network, programming, and other technical skills

Date: July 10, 2025
Status: HOTFIX for technical requirements extraction
"""

import json
import requests
import time
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class TechnicalSkillsResult:
    """Result with technical skills focus"""
    technical_skills: List[str]
    all_skills: List[str]
    processing_time: float
    model_used: str
    confidence: str

class TechnicalRequirementsExtractor:
    """
    FIXED Technical Requirements Extraction Specialist
    
    Focuses on extracting actual technical skills from job descriptions
    without falling back to hardcoded examples
    """
    
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 model: str = "mistral:latest"):
        self.ollama_url = ollama_url
        self.model = model
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama LLM with error handling"""
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False}
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    def extract_technical_skills(self, job_description: str) -> List[str]:
        """Extract technical skills from job description - FIXED VERSION"""
        
        prompt = f"""You are a technical skills extraction expert. Your job is to find ONLY the technical skills, tools, and technologies that are explicitly mentioned in the following job description.

CRITICAL INSTRUCTIONS:
- Read the job description carefully
- Extract ONLY technical skills that are directly mentioned in the text
- Include programming languages, software tools, technical systems, frameworks
- Include network technologies, security tools, cloud platforms
- Do NOT include soft skills or business skills
- Do NOT include job responsibilities or requirements
- Output each skill on a new line
- Use clean, short names (e.g., "Python" not "Python programming")

JOB DESCRIPTION TO ANALYZE:
{job_description}

TECHNICAL SKILLS FOUND (one per line):"""

        response = self._call_ollama(prompt)
        return self._parse_skills_clean(response)
    
    def _parse_skills_clean(self, response: str) -> List[str]:
        """Clean parsing without aggressive filtering"""
        import re
        skills = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line or len(line) < 2:
                continue
                
            # Remove any prefixes/bullets  
            line = re.sub(r'^\d+\.\s*', '', line)
            line = re.sub(r'^[-•*]\s*', '', line)
            
            # Remove parenthetical explanations
            line = re.sub(r'\s*\([^)]*\)', '', line)
            
            # Clean whitespace
            line = re.sub(r'\s+', ' ', line).strip()
            
            # Skip if empty after cleaning
            if not line:
                continue
            
            # Skip obvious non-technical terms
            skip_terms = ['experience', 'years', 'degree', 'education', 'fluent', 'strong', 'good']
            if any(term in line.lower() for term in skip_terms):
                continue
                
            # Clean common suffixes
            line = line.replace(' Skills', '').replace(' Technology', '')
            line = line.replace(' Tools', '').replace(' Software', '')
            line = line.strip()
            
            if line and len(line) > 1:
                skills.append(line)
                
        return skills
    
    def extract_all_skills(self, job_description: str) -> TechnicalSkillsResult:
        """Extract technical skills with timing and metadata"""
        start_time = time.time()
        
        technical_skills = self.extract_technical_skills(job_description)
        
        processing_time = time.time() - start_time
        
        return TechnicalSkillsResult(
            technical_skills=technical_skills,
            all_skills=technical_skills,  # For compatibility
            processing_time=processing_time,
            model_used=self.model,
            confidence="Fixed Technical Extractor v1.0"
        )

def test_fixed_extractor():
    """Test the fixed extractor on our problem jobs"""
    print("🔧 TESTING FIXED TECHNICAL REQUIREMENTS EXTRACTOR")
    print("=" * 70)
    
    extractor = TechnicalRequirementsExtractor()
    
    # Test Job #2 (Network Security) that failed before
    network_job = """Senior Engineer (f/m/x) – Network Security Deployment. Fachliche Kenntnisse im Bereich Netzwerk (Layer2/3, Routing und Switching); Netzwerk Security (Firewall, Proxy); Cloud. Deployment von sämtlichen Technologien (Router, Switche, Firewall, Proxy, etc.)"""
    
    print("🎯 Testing Network Security Job...")
    result = extractor.extract_all_skills(network_job)
    
    print(f"⏱️ Processing Time: {result.processing_time:.2f}s")
    print("🔧 Technical Skills Found:")
    for skill in result.technical_skills:
        print(f"  ✅ {skill}")
    
    print(f"\n📈 Total: {len(result.technical_skills)} technical skills")
    
    # Check if we found the expected skills
    expected = ["Layer2/3", "Routing", "Switching", "Firewall", "Proxy", "Cloud", "Router"]
    found_count = 0
    for exp in expected:
        if any(exp.lower() in skill.lower() for skill in result.technical_skills):
            found_count += 1
            print(f"✅ Found: {exp}")
        else:
            print(f"❌ Missing: {exp}")
    
    accuracy = (found_count / len(expected)) * 100
    print(f"\n📊 Accuracy: {accuracy:.1f}% ({found_count}/{len(expected)})")

if __name__ == "__main__":
    test_fixed_extractor()
