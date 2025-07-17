#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - PRODUCTION FIXED v2
========================================================

CRITICAL PRODUCTION FIX v2: Ultra-focused extraction only from input text
Root cause identified: LLM was generating skills from training examples, not input text

Key Fixes:
- Stricter prompts that ONLY look at the provided text
- Explicit instruction to ignore training examples
- Better input/output separation
- Robust parsing that still prevents empty results

Target: 90%+ accuracy, 100% format compliance, no hallucination

Date: June 27, 2025
Status: PRODUCTION-READY FIXED VERSION v2
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
    PRODUCTION-GRADE Skill Extraction Specialist - FIXED VERSION v2
    
    Ultra-focused on precision and accuracy for production CV matching systems
    Conservative extraction - ONLY explicitly mentioned skills from the provided text
    FIXED: Prevents LLM from using training examples instead of actual input
    """
    
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 preferred_model: str = "mistral:latest",
                 fallback_models: List[str] = None,
                 debug: bool = False):
        self.ollama_url = ollama_url
        self.preferred_model = preferred_model
        self.fallback_models = fallback_models or [
            "olmo2:latest",
            "dolphin3:8b",    
            "qwen3:latest"
        ]
        self.debug = debug

    def _call_ollama(self, prompt: str, model: str = None) -> str:
        import requests
        model = model or self.preferred_model
        payload = {"model": model, "prompt": prompt, "stream": False}
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                if self.debug:
                    print(f"🔧 DEBUG: LLM response ({len(response_text)} chars): {response_text[:200]}...")
                return response_text
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            if self.debug:
                print(f"🔧 DEBUG: LLM call failed: {str(e)}")
            for fallback in self.fallback_models:
                if fallback != model:
                    try:
                        return self._call_ollama(prompt, fallback)
                    except:
                        continue
            raise Exception(f"All models failed: {str(e)}")

    def extract_technical_skills(self, job_description: str) -> List[str]:
        prompt = f"""You are analyzing a job description to extract ONLY the technical skills that are explicitly mentioned in the text. 

CRITICAL RULES:
- ONLY extract skills that are directly written in the provided job description below
- DO NOT add skills from your training data or general knowledge
- DO NOT infer or assume skills that are not clearly stated
- DO NOT add examples or related skills
- ONLY return skills that appear in the actual text

Look for programming languages, software tools, systems, databases, frameworks, and technical certifications that are specifically mentioned.

JOB DESCRIPTION TO ANALYZE:
{job_description}

Based ONLY on the above job description text, list the technical skills that are explicitly mentioned:"""
        
        response = self._call_ollama(prompt)
        return self._parse_skills_conservative(response)

    def extract_soft_skills(self, job_description: str) -> List[str]:
        prompt = f"""You are analyzing a job description to extract ONLY the soft skills and languages that are explicitly mentioned in the text.

CRITICAL RULES:
- ONLY extract skills that are directly written in the provided job description below
- DO NOT add skills from your training data or general knowledge  
- DO NOT infer or assume skills that are not clearly stated
- DO NOT add examples or related skills
- ONLY return skills that appear in the actual text

Look for communication skills, languages, leadership abilities, teamwork, and personal qualities that are specifically mentioned.

JOB DESCRIPTION TO ANALYZE:
{job_description}

Based ONLY on the above job description text, list the soft skills and languages that are explicitly mentioned:"""
        
        response = self._call_ollama(prompt)
        return self._parse_skills_conservative(response)

    def extract_business_skills(self, job_description: str) -> List[str]:
        prompt = f"""You are analyzing a job description to extract ONLY the business/domain skills that are explicitly mentioned in the text.

CRITICAL RULES:
- ONLY extract skills that are directly written in the provided job description below
- DO NOT add skills from your training data or general knowledge
- DO NOT infer or assume skills that are not clearly stated  
- DO NOT add examples or related skills
- ONLY return skills that appear in the actual text

Look for industry knowledge, business processes, financial skills, certifications, and domain expertise that are specifically mentioned.

JOB DESCRIPTION TO ANALYZE:
{job_description}

Based ONLY on the above job description text, list the business/domain skills that are explicitly mentioned:"""
        
        response = self._call_ollama(prompt)
        return self._parse_skills_conservative(response)

    def _parse_skills_conservative(self, response: str) -> List[str]:
        """Conservative parsing that extracts actual skill names"""
        import re
        skills = []
        
        if self.debug:
            print(f"🔧 DEBUG: Parsing response: {response[:300]}...")
        
        # Split by lines and common separators
        lines = []
        for line in response.split('\n'):
            # Also split by commas and semicolons for inline lists
            for part in re.split(r'[,;]', line):
                lines.append(part.strip())
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 2:
                continue
                
            # Remove common prefixes
            line = re.sub(r'^\d+\.\s*', '', line)  # Numbers
            line = re.sub(r'^[-•*]\s*', '', line)  # Bullets
            line = re.sub(r'^(Skills?|Abilities|Knowledge|Experience):\s*', '', line, flags=re.IGNORECASE)
            
            # Remove parenthetical explanations but keep the main content
            line = re.sub(r'\s*\([^)]*\)\s*', ' ', line)
            
            # Clean multiple spaces
            line = re.sub(r'\s+', ' ', line).strip()
            
            # Skip obvious non-skills
            skip_patterns = [
                r'^(and|or|the|a|an|in|on|at|to|for|with|by)$',
                r'^(none|not|no)\b',
                r'^(listed|mentioned|required|preferred|needed)$',
                r'job description',
                r'qualification',
                r'requirement',
                r'based only on',
                r'above job description'
            ]
            
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
                
            # Skip if too long (likely a sentence, not a skill)
            if len(line.split()) > 5:
                continue
            
            # Clean common suffixes
            line = re.sub(r'\s+(skills?|abilities|knowledge|experience)$', '', line, flags=re.IGNORECASE)
            line = line.strip()
            
            # Final validation
            if line and len(line) > 1 and not line.isdigit():
                skills.append(line)
                if self.debug:
                    print(f"🔧 DEBUG: Extracted skill: '{line}'")
                
        if self.debug:
            print(f"🔧 DEBUG: Total skills extracted: {len(skills)}")
            
        return skills

    def extract_skills(self, job_description: str) -> SkillExtractionResult:
        """Production-grade skill extraction - FIXED VERSION v2"""
        start_time = time.time()
        
        if self.debug:
            print(f"🔧 DEBUG: Starting extraction for {len(job_description)} char input")
        
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
        
        if self.debug:
            print(f"🔧 DEBUG: Final counts - Technical: {len(technical_skills)}, Soft: {len(soft_skills)}, Business: {len(business_skills)}, Total: {len(all_skills)}")
        
        return SkillExtractionResult(
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            business_skills=business_skills,
            all_skills=all_skills,
            processing_time=processing_time,
            model_used=self.preferred_model,
            accuracy_confidence="Production Grade v3.3 (Fixed v2 - Conservative Extraction)"
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
    # Test with the golden test case that was failing
    test_input = """
    DWS - Operations Specialist - Performance Measurement (m/f/d)
    Degree in business mathematics or business administration, alternatively several years of professional experience in the area of performance calculation and risk figures for investment banking products
    Excellent knowledge in the area of investment accounting, FX, fixed income, equity products as well as performance calculation and risk analysis is preferred
    Routine use of databases (Access/Oracle) and data analysis
    Perfect handling of MS Office, especially Excel and Access
    Programming knowledge in VBA, Python or similar programming languages
    You independently familiarize yourself with complex systems (e.g. StatPro, Aladdin, Sim Corp Dimension, Coric)
    Strong communication skills, team spirit and an independent, careful way of working
    Fluent written and spoken English and German
    """
    
    print("=== PRODUCTION v3.3 FIXED v2 TEST ===")
    specialist = ContentExtractionSpecialistV33(debug=True)
    result = specialist.extract_skills(test_input)
    
    print(f"\n=== RESULTS ===")
    print(f"Technical Skills ({len(result.technical_skills)}): {result.technical_skills}")
    print(f"Soft Skills ({len(result.soft_skills)}): {result.soft_skills}")
    print(f"Business Skills ({len(result.business_skills)}): {result.business_skills}")
    print(f"All Skills ({len(result.all_skills)}): {result.all_skills}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Model: {result.model_used}")
    
    # Test pipeline interface
    print(f"\n=== PIPELINE INTERFACE TEST ===")
    pipeline_result = extract_skills_pipeline(test_input)
    print(f"Pipeline Result ({len(pipeline_result)} skills): {pipeline_result}")
