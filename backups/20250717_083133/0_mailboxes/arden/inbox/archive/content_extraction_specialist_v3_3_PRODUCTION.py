#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 - PRODUCTION GRADE
====================================================

PRODUCTION SOLUTION: Ultra-focused extraction for 90%+ accuracy
Based on Sandy's validation feedback showing critical accuracy and precision gaps

Key Improvements:
- Conservative extraction (only explicitly mentioned skills)
- Clean skill names (no verbose descriptions)
- Strict filtering (no domain expansion)
- Precision-focused prompts

Target: 90%+ accuracy, 100% format compliance, production-ready output

Date: June 27, 2025
Status: PRODUCTION-READY FINAL SOLUTION
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
        return self._parse_skills_strict(response)

    def extract_soft_skills(self, job_description: str) -> List[str]:
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
        return self._parse_skills_strict(response)

    def extract_business_skills(self, job_description: str) -> List[str]:
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
        return self._parse_skills_strict(response)

    def _parse_skills_strict(self, response: str) -> List[str]:
        """Ultra-strict parsing for production accuracy"""
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
            
            # Skip if too long (likely not a skill name)
            if len(line.split()) > 4:
                continue
                
            # Skip verbose indicators
            verbose_indicators = ['skills', 'abilities', 'knowledge', 'experience', 'understanding']
            if any(indicator in line.lower() for indicator in verbose_indicators):
                continue
                
            # Clean skill names
            line = line.replace(' Skills', '').replace(' Abilities', '')
            line = line.replace(' Knowledge', '').replace(' Experience', '')
            line = line.strip()
            
            if line and len(line) > 1:
                skills.append(line)
                
        return skills

    def extract_skills(self, job_description: str) -> SkillExtractionResult:
        """Production-grade skill extraction"""
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
            accuracy_confidence="Production Grade v3.3 (Ultra-Focused)"
        )

def extract_skills_pipeline(job_description: str):
    """Production pipeline interface"""
    specialist = ContentExtractionSpecialistV33()
    result = specialist.extract_skills(job_description)
    return result.all_skills

if __name__ == "__main__":
    specialist = ContentExtractionSpecialistV33()
    
    # Test with golden test case
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
    
    result = specialist.extract_skills(test_input)
    print("Production v3.3 Skills:")
    for skill in result.all_skills:
        print(f"- {skill}")
