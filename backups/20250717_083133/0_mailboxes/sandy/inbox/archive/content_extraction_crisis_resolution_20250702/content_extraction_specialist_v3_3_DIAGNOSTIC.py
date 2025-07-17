#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - PRODUCTION DIAGNOSTIC
==========================================================

URGENT PRODUCTION FIX for Sandy's empty results issue

This version includes comprehensive diagnostics to identify why Sandy is getting empty results
when the specialist should be working correctly.
"""

import json
import requests
import time
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class SkillExtractionResult:
    """Production result with strict accuracy focus"""
    technical_skills: List[str]
    soft_skills: List[str] 
    business_skills: List[str]
    all_skills: List[str]
    processing_time: float
    model_used: str
    accuracy_confidence: str

class ContentExtractionSpecialistV33:
    """
    PRODUCTION-GRADE Skill Extraction Specialist
    
    Ultra-focused on precision and accuracy for production CV matching systems
    Conservative extraction - only explicitly mentioned skills
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
        print(f"🔧 DIAGNOSTIC: ContentExtractionSpecialistV33 initialized")
        print(f"   Ollama URL: {self.ollama_url}")
        print(f"   Preferred Model: {self.preferred_model}")

    def _call_ollama(self, prompt: str, model: str = None) -> str:
        import requests
        model = model or self.preferred_model
        payload = {"model": model, "prompt": prompt, "stream": False}
        print(f"🔧 DIAGNOSTIC: Calling Ollama with model: {model}")
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '').strip()
                print(f"🔧 DIAGNOSTIC: LLM response length: {len(llm_response)} chars")
                print(f"🔧 DIAGNOSTIC: LLM response preview: {llm_response[:200]}...")
                return llm_response
            else:
                print(f"🔧 DIAGNOSTIC: HTTP Error {response.status_code}")
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"🔧 DIAGNOSTIC: Exception in _call_ollama: {str(e)}")
            for fallback in self.fallback_models:
                if fallback != model:
                    try:
                        print(f"🔧 DIAGNOSTIC: Trying fallback model: {fallback}")
                        return self._call_ollama(prompt, fallback)
                    except:
                        continue
            raise Exception(f"All models failed: {str(e)}")

    def _parse_skills_strict(self, response: str) -> List[str]:
        """Ultra-strict parsing for production accuracy with diagnostics"""
        import re
        print(f"🔧 DIAGNOSTIC: Parsing response of {len(response)} chars")
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
            
            # Skip if too long (likely not a skill name)
            if len(line.split()) > 4:
                continue
                
            # Skip verbose indicators - COMMENTED OUT TO SEE IF THIS IS THE ISSUE
            # verbose_indicators = ['skills', 'abilities', 'knowledge', 'experience', 'understanding']
            # if any(indicator in line.lower() for indicator in verbose_indicators):
            #     continue
                
            # Clean skill names
            line = line.replace(' Skills', '').replace(' Abilities', '')
            line = line.replace(' Knowledge', '').replace(' Experience', '')
            line = line.strip()
            
            if line and len(line) > 1:
                skills.append(line)
                print(f"🔧 DIAGNOSTIC: Extracted skill: '{line}'")
                
        print(f"🔧 DIAGNOSTIC: Total skills extracted: {len(skills)}")
        return skills

    def extract_technical_skills(self, job_description: str) -> List[str]:
        print(f"🔧 DIAGNOSTIC: Starting technical skills extraction")
        prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED TECHNICAL SKILLS.

STRICT RULES:
- ONLY extract what is directly stated in the text
- NO inference or domain expansion
- NO related or implied skills
- Output ONLY clean skill names

LOOK FOR:
- Programming languages: Python, Java, VBA, R, SQL
- Software tools: Excel, Access, Oracle, StatPro, Aladdin, SimCorp Dimension, SAP
- Technical systems: GCP, AWS, Azure, Splunk, Tenable Nessus, Qualys, Rapid7
- Security frameworks: CVSS, MITRE ATT&CK, NIST, OWASP
- Development: CI/CD, DevSecOps

TEXT: {job_description}

TECHNICAL SKILLS (one per line, clean names only):"""
        response = self._call_ollama(prompt)
        result = self._parse_skills_strict(response)
        print(f"🔧 DIAGNOSTIC: Technical skills result: {result}")
        return result

    def extract_soft_skills(self, job_description: str) -> List[str]:
        print(f"🔧 DIAGNOSTIC: Starting soft skills extraction")
        prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED SOFT SKILLS.

STRICT RULES:
- ONLY extract what is directly stated in the text
- NO inference or expansion
- Output clean, short names

LOOK FOR:
- Communication (not "communication skills")
- Leadership (not "leadership abilities") 
- Management
- Teamwork
- Client Relations
- Sales
- German, English (languages)
- Presentation
- Documentation

TEXT: {job_description}

SOFT SKILLS (one per line, clean names only):"""
        response = self._call_ollama(prompt)
        result = self._parse_skills_strict(response)
        print(f"🔧 DIAGNOSTIC: Soft skills result: {result}")
        return result

    def extract_business_skills(self, job_description: str) -> List[str]:
        print(f"🔧 DIAGNOSTIC: Starting business skills extraction")
        prompt = f"""EXTRACT ONLY EXPLICITLY MENTIONED BUSINESS/DOMAIN SKILLS.

STRICT RULES:
- ONLY extract what is directly stated in the text
- NO inference or domain expansion
- Output clean, specific names

LOOK FOR:
- Investment Accounting
- Risk Analysis  
- Performance Measurement
- FX Trading
- Derivatives
- Financial Markets
- Quantitative Analysis
- Hedge Accounting
- Fund Accounting
- Asset Management Operations
- E-invoicing

TEXT: {job_description}

BUSINESS SKILLS (one per line, clean names only):"""
        response = self._call_ollama(prompt)
        result = self._parse_skills_strict(response)
        print(f"🔧 DIAGNOSTIC: Business skills result: {result}")
        return result

    def extract_skills(self, job_description: str) -> SkillExtractionResult:
        """Production-grade skill extraction with diagnostics"""
        print(f"🔧 DIAGNOSTIC: Starting extract_skills with {len(job_description)} char input")
        start_time = time.time()
        
        technical_skills = self.extract_technical_skills(job_description)
        soft_skills = self.extract_soft_skills(job_description) 
        business_skills = self.extract_business_skills(job_description)
        
        # Combine and deduplicate
        all_skills = []
        seen = set()
        
        for skill_list in [technical_skills, soft_skills, business_skills]:
            for skill in skill_list:
                skill_clean = skill.strip()
                if skill_clean and skill_clean.lower() not in seen:
                    all_skills.append(skill_clean)
                    seen.add(skill_clean.lower())
        
        processing_time = time.time() - start_time
        
        result = SkillExtractionResult(
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            business_skills=business_skills,
            all_skills=all_skills,
            processing_time=processing_time,
            model_used=self.preferred_model,
            accuracy_confidence="Production Grade v3.3 (Ultra-Focused)"
        )
        
        print(f"🔧 DIAGNOSTIC: Final result:")
        print(f"   Technical: {len(technical_skills)} skills")
        print(f"   Soft: {len(soft_skills)} skills") 
        print(f"   Business: {len(business_skills)} skills")
        print(f"   Total: {len(all_skills)} skills")
        print(f"   Processing time: {processing_time:.2f}s")
        
        return result

# ALTERNATIVE INTERFACES - Sandy might be using one of these
class ContentExtractionSpecialist:
    """Alternative interface - maybe Sandy is using this class name"""
    def __init__(self):
        self.specialist = ContentExtractionSpecialistV33()
        print(f"🔧 DIAGNOSTIC: ContentExtractionSpecialist (alternative interface) initialized")
    
    def extract_content(self, job_description: str):
        print(f"🔧 DIAGNOSTIC: extract_content called (alternative interface)")
        return self.specialist.extract_skills(job_description)

def extract_skills_pipeline(job_description: str):
    """Production pipeline interface"""
    print(f"🔧 DIAGNOSTIC: extract_skills_pipeline called")
    specialist = ContentExtractionSpecialistV33()
    result = specialist.extract_skills(job_description)
    return result.all_skills

if __name__ == "__main__":
    print("🔧 DIAGNOSTIC: Running diagnostic test")
    
    # Test with Sandy's exact reported case
    test_input = """DWS - Operations Specialist - Performance Measurement (m/f/d)

Your profile:
- Programming knowledge in VBA, Python or similar programming languages
- Excellent knowledge in investment accounting, FX, fixed income  
- Routine use of databases (Access/Oracle) and data analysis
- Perfect handling of MS Office, especially Excel and Access
- Fluent written and spoken English and German"""
    
    print("🔧 DIAGNOSTIC: Testing ContentExtractionSpecialistV33 directly")
    specialist = ContentExtractionSpecialistV33()
    result = specialist.extract_skills(test_input)
    
    print("\n🔧 DIAGNOSTIC: Final Results:")
    print(f"Technical Skills: {result.technical_skills}")
    print(f"Business Skills: {result.business_skills}")
    print(f"Soft Skills: {result.soft_skills}")
    print(f"All Skills: {result.all_skills}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    
    print("\n🔧 DIAGNOSTIC: Testing alternative interface")
    alt_specialist = ContentExtractionSpecialist()
    alt_result = alt_specialist.extract_content(test_input)
    print(f"Alternative interface result skills count: {len(alt_result.all_skills)}")
    
    print("\n🔧 DIAGNOSTIC: Testing pipeline function")
    pipeline_result = extract_skills_pipeline(test_input)
    print(f"Pipeline function result skills count: {len(pipeline_result)}")
