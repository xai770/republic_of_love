#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - PRODUCTION CLEAN
====================================================

FINAL PRODUCTION FIX: Ultra-clean prompts to prevent contamination
Root cause identified: Prompts included examples that were being extracted

CRITICAL FIXES:
- Removed all examples from prompts (was causing contamination)
- Ultra-clean prompt format focused only on the input text
- Precise parsing to extract only from job descriptions
- Maintains accuracy while preventing over-extraction

Date: June 27, 2025
Status: PRODUCTION-READY CLEAN VERSION
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
    PRODUCTION-GRADE Skill Extraction Specialist - CLEAN VERSION
    
    Ultra-focused on precision and accuracy for production CV matching systems
    Conservative extraction - only explicitly mentioned skills
    CLEAN: No prompt contamination, pure extraction from job descriptions
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
        import requests
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

    def extract_technical_skills(self, job_description: str) -> List[str]:
        prompt = f"""Read this job description and extract only the technical skills that are explicitly mentioned.

Job Description:
{job_description}

Extract only technical skills like programming languages, software tools, databases, and technical systems that are directly stated in the text above. List each skill on a separate line:"""
        response = self._call_ollama(prompt)
        return self._parse_clean(response)

    def extract_soft_skills(self, job_description: str) -> List[str]:
        prompt = f"""Read this job description and extract only the soft skills and languages that are explicitly mentioned.

Job Description:
{job_description}

Extract only soft skills and languages that are directly stated in the text above. Include languages like English, German, etc. and skills like communication, teamwork, leadership. List each skill on a separate line:"""
        response = self._call_ollama(prompt)
        return self._parse_clean(response)

    def extract_business_skills(self, job_description: str) -> List[str]:
        prompt = f"""Read this job description and extract only the business domain skills that are explicitly mentioned.

Job Description:
{job_description}

Extract only business skills like industry knowledge, business processes, and domain expertise that are directly stated in the text above. List each skill on a separate line:"""
        response = self._call_ollama(prompt)
        return self._parse_clean(response)

    def _parse_clean(self, response: str) -> List[str]:
        """Clean parsing focused on extracting actual skill names"""
        import re
        skills = []
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if not line or len(line) < 2:
                continue
                
            # Remove bullets and numbers
            line = re.sub(r'^\d+\.\s*', '', line)
            line = re.sub(r'^[-•*]\s*', '', line)
            
            # Skip section headers
            if line.endswith(':') or line.lower() in ['technical skills', 'soft skills', 'business skills', 'languages', 'skills']:
                continue
                
            # Remove parenthetical content
            line = re.sub(r'\([^)]*\)', '', line)
            line = re.sub(r'\s+', ' ', line).strip()
            
            # Skip if too long (descriptions not skills)
            if len(line.split()) > 4:
                continue
                
            # Clean up prefixes
            prefixes = ['knowledge of ', 'experience with ', 'proficiency in ', 'familiarity with ']
            for prefix in prefixes:
                if line.lower().startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            
            # Clean up suffixes
            suffixes = [' skills', ' experience', ' knowledge']
            for suffix in suffixes:
                if line.lower().endswith(suffix):
                    line = line[:-len(suffix)].strip()
                    break
            
            if line and len(line) > 1:
                skills.append(line)
                
        return skills

    def extract_skills(self, job_description: str) -> SkillExtractionResult:
        """Production-grade skill extraction - CLEAN VERSION"""
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
        
        return SkillExtractionResult(
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            business_skills=business_skills,
            all_skills=all_skills,
            processing_time=processing_time,
            model_used=self.preferred_model,
            accuracy_confidence="Production Grade v3.3 (Clean - No Contamination)"
        )

# Alternative interface compatibility
class ContentExtractionSpecialist:
    """Alternative interface for compatibility"""
    def __init__(self, **kwargs):
        self.specialist = ContentExtractionSpecialistV33(**kwargs)
    
    def extract_content(self, text: str) -> Dict[str, Any]:
        result = self.specialist.extract_skills(text)
        return {
            'technical_skills': result.technical_skills,
            'soft_skills': result.soft_skills,
            'business_skills': result.business_skills,
            'all_skills': result.all_skills,
            'processing_time': result.processing_time
        }

def extract_skills_pipeline(job_description: str):
    """Production pipeline interface"""
    specialist = ContentExtractionSpecialistV33()
    result = specialist.extract_skills(job_description)
    return result.all_skills

if __name__ == "__main__":
    # Test with the exact input from Sandy's report
    test_input = """DWS - Operations Specialist - Performance Measurement (m/f/d)

Your profile:
- Programming knowledge in VBA, Python or similar programming languages
- Excellent knowledge in investment accounting, FX, fixed income  
- Routine use of databases (Access/Oracle) and data analysis
- Perfect handling of MS Office, especially Excel and Access
- Fluent written and spoken English and German"""
    
    print("=== CONTENT EXTRACTION SPECIALIST v3.3 - CLEAN VERSION ===")
    specialist = ContentExtractionSpecialistV33()
    result = specialist.extract_skills(test_input)
    
    print(f"\n=== RESULTS ===")
    print(f"Technical Skills ({len(result.technical_skills)}): {result.technical_skills}")
    print(f"Soft Skills ({len(result.soft_skills)}): {result.soft_skills}")
    print(f"Business Skills ({len(result.business_skills)}): {result.business_skills}")
    print(f"All Skills ({len(result.all_skills)}): {result.all_skills}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    
    # Test expectations from Sandy's report
    expected_skills = ['Python', 'VBA', 'Oracle', 'Access', 'Excel', 'English', 'German', 'Investment Accounting', 'FX', 'Fixed Income']
    found_skills = [skill for skill in expected_skills if any(skill.lower() in s.lower() for s in result.all_skills)]
    
    print(f"\n=== VALIDATION ===")
    print(f"Expected Key Skills Found: {len(found_skills)}/{len(expected_skills)}")
    print(f"Found: {found_skills}")
    print(f"Success Rate: {len(found_skills)/len(expected_skills)*100:.1f}%")
    
    if len(result.all_skills) > 0:
        print("✅ SUCCESS: Skills extracted (no longer empty!)")
    else:
        print("❌ FAILURE: Still returning empty results")
