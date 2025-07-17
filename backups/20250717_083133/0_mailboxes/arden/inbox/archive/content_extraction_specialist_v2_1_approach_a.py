"""
Content Extraction Specialist v2.1 - APPROACH A: Dual-Purpose Prompt Redesign
==============================================================================

SOLUTION: Skill-First Extraction with Protected Terms
STATUS: 🔥 IMPLEMENTING APPROACH A - Dual-Purpose Prompt Redesign
TARGET: 90%+ skill extraction accuracy for Sandy's CV-to-job matching

ROOT CAUSE ADDRESSED:
- Original v2.0 prompt had conflicting instructions (cleanup vs preserve)
- New approach: Extract skills FIRST, then clean content while protecting skills

STRATEGY:
1. Phase 1: Extract ALL technical terms, tools, frameworks explicitly
2. Phase 2: Clean content using extracted skills as protected terms
3. Template-based output ensuring skill preservation

Date: June 26, 2025
"""

import re
import logging
import json
import requests
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractionResultV21:
    """Results from v2.1 skill-first extraction process"""
    original_length: int
    extracted_length: int
    reduction_percentage: float
    extracted_content: str
    processing_notes: List[str]
    llm_processing_time: float
    model_used: str
    output_format_version: str = "2.1"
    # New field to track skill extraction
    extracted_skills_count: int = 0

class ContentExtractionSpecialistV21:
    """
    Content Extraction Specialist v2.1 - APPROACH A IMPLEMENTATION
    
    🎯 SKILL-FIRST EXTRACTION STRATEGY:
    ✅ Phase 1: Extract ALL technical terms, tools, frameworks first
    ✅ Phase 2: Clean content while treating skills as protected terms
    ✅ Template-based structure ensuring 90%+ skill accuracy
    ✅ Maintains professional cleanup quality
    
    DESIGNED FOR SANDY'S CV-TO-JOB MATCHING REQUIREMENTS:
    - Exact technical terminology preservation
    - Automated skill matching compatibility
    - Deutsche Bank production standards
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:latest"):
        """
        Initialize Content Extraction Specialist v2.1 with skill-first approach.
        """
        self.ollama_url = ollama_url
        self.model = model
        self.stats = {
            'jobs_processed': 0,
            'total_reduction': 0.0,
            'total_llm_time': 0.0,
            'skill_extraction_accuracy': 0.0
        }
        
        # Verify Ollama connection
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """Verify that Ollama is available and the model is accessible."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if not any(self.model in name for name in model_names):
                    logger.warning(f"Model {self.model} not found in Ollama. Available models: {model_names}")
                else:
                    logger.info(f"🔥 Content Extraction Specialist v2.1 (APPROACH A) - Ollama verified. Model: {self.model}")
            else:
                logger.warning(f"⚠️ Ollama connection issue: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Cannot connect to Ollama at {self.ollama_url}: {str(e)}")
            logger.info("Will use fallback processing if Ollama calls fail")

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Make a call to the Ollama API."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            return None

    def extract_core_content(self, raw_job_description: str, job_id: str = "unknown") -> ExtractionResultV21:
        """
        Extract content using APPROACH A: Dual-Purpose Prompt Redesign
        
        STRATEGY:
        1. Use skill-first LLM prompt that explicitly extracts technical terms
        2. Apply template-based structure ensuring skill preservation
        3. Clean content while protecting extracted skills
        """
        logger.info(f"🔥 Processing job {job_id} with v2.1 APPROACH A - Original length: {len(raw_job_description)} chars")
        
        llm_start_time = time.time()
        original_length = len(raw_job_description)
        processing_notes = []
        
        # Apply APPROACH A: Skill-First Dual-Purpose Extraction
        extracted_content = self._skill_first_extraction(raw_job_description, job_id)
        
        llm_processing_time = time.time() - llm_start_time
        
        # Calculate statistics
        extracted_length = len(extracted_content) if extracted_content else 0
        reduction_percentage = ((original_length - extracted_length) / original_length) * 100 if original_length > 0 else 0
        
        # Count extracted skills (rough estimation)
        skill_count = self._count_technical_terms(extracted_content)
        
        # Update processing stats
        self.stats['jobs_processed'] += 1
        self.stats['total_reduction'] += reduction_percentage
        self.stats['total_llm_time'] += llm_processing_time
        
        processing_notes.append(f"v2.1 APPROACH A skill-first extraction completed in {llm_processing_time:.2f}s")
        processing_notes.append(f"Model used: {self.model}")
        processing_notes.append(f"Extracted {skill_count} technical terms")
        processing_notes.append("Strategy: Dual-purpose prompt with skill protection")
        
        logger.info(f"🎯 Job {job_id} processed with APPROACH A - Reduced from {original_length} to {extracted_length} chars "
                   f"({reduction_percentage:.1f}% reduction) in {llm_processing_time:.2f}s")
        
        return ExtractionResultV21(
            original_length=original_length,
            extracted_length=extracted_length,
            reduction_percentage=reduction_percentage,
            extracted_content=extracted_content,
            processing_notes=processing_notes,
            llm_processing_time=llm_processing_time,
            model_used=self.model,
            output_format_version="2.1-ApproachA",
            extracted_skills_count=skill_count
        )
    
    def _skill_first_extraction(self, raw_content: str, job_id: str) -> str:
        """
        APPROACH A: Skill-First Dual-Purpose Extraction
        
        STRATEGY:
        1. Phase 1: Extract technical skills explicitly 
        2. Phase 2: Clean content while preserving extracted skills
        3. Use template structure ensuring skill accuracy
        """
        logger.info(f"🎯 APPROACH A: Skill-first extraction for job {job_id}")
        
        # APPROACH A: Dual-Purpose Prompt with Skill-First Strategy
        skill_first_prompt = f"""You are a technical skill extraction specialist optimized for CV-to-job matching systems. Your task has TWO PHASES that must be executed in sequence:

PHASE 1: SKILL EXTRACTION (CRITICAL - DO NOT SUMMARIZE OR GENERALIZE)
Extract ALL technical terms, tools, software, frameworks, certifications, and specific skills mentioned in the job posting. Preserve EXACT names and terminology:

- Software/Tools: (e.g., "Python", "Excel", "StatPro", "Aladdin", "SimCorp Dimension", "SAP", "Oracle")  
- Frameworks/Standards: (e.g., "CVSS", "MITRE ATT&CK", "NIST", "OWASP", "DevSecOps", "CI/CD")
- Technical Skills: (e.g., "Risk Analysis", "Performance Measurement", "Investment Accounting")
- Languages: (e.g., "German", "English", "French")
- Certifications: (e.g., "CFA", "CIPM")
- Domain Knowledge: (e.g., "FX Trading", "Derivatives", "Hedge Accounting")

CRITICAL RULES FOR PHASE 1:
- Extract INDIVIDUAL terms, not categories or descriptions
- "Python, VBA programming" → Extract: ["Python", "VBA"] 
- "Complex systems (StatPro, Aladdin)" → Extract: ["StatPro", "Aladdin"]
- "Database management (Access/Oracle)" → Extract: ["Access", "Oracle"]
- NEVER generalize: "programming languages" is WRONG, extract specific languages

PHASE 2: CONTENT FORMATTING (PROTECT EXTRACTED SKILLS)
Format the job information professionally while ensuring ALL Phase 1 skills appear in the Required Skills section:

**Position:** [Job Title] - [Location]

**Required Skills:**
[List ALL skills from Phase 1 - use individual bullet points for each skill]
- [Individual skill/tool name]
- [Individual skill/tool name]
- [Continue for ALL Phase 1 extracted skills]

**Key Responsibilities:**
- [Main job duties - clean and concise]
- [Core tasks and deliverables]

**Experience Required:**
- [Education and background requirements]
- [Years of experience and level]

ABSOLUTE REQUIREMENTS:
1. ALL technical terms from Phase 1 MUST appear in Required Skills section
2. Use EXACT terminology - do not paraphrase or summarize skill names
3. One bullet point per individual skill/tool
4. Remove boilerplate and marketing language EXCEPT for technical terms
5. Translate German content to English while preserving technical terms

JOB POSTING TO PROCESS:
{raw_content}

Execute Phase 1 then Phase 2 with the exact format above:"""

        # Call Ollama with skill-first prompt
        llm_response = self._call_ollama(skill_first_prompt)
        
        if llm_response:
            # Clean up the response to ensure proper formatting
            cleaned_response = self._clean_skill_first_response(llm_response)
            if cleaned_response:
                logger.info(f"✅ APPROACH A extraction successful for job {job_id} - extracted {len(cleaned_response)} chars")
                return cleaned_response
            else:
                logger.warning(f"⚠️ Response cleaning failed for job {job_id}, using raw response")
                return llm_response.strip()
        else:
            logger.warning(f"⚠️ LLM call failed for job {job_id}, using fallback extraction")
            return self._fallback_extraction(raw_content)
    
    def _clean_skill_first_response(self, response: str) -> str:
        """Clean and validate the skill-first LLM response."""
        try:
            # Remove common LLM prefixes
            response = re.sub(r'^.*?Here is the.*?format:?\s*', '', response, flags=re.IGNORECASE | re.DOTALL)
            response = re.sub(r'^.*?Phase \d+.*?:?\s*', '', response, flags=re.IGNORECASE | re.DOTALL)
            
            # Ensure it starts with **Position:**
            if not response.strip().startswith('**Position:**'):
                position_match = re.search(r'\*\*Position:\*\*.*', response)
                if position_match:
                    response = response[position_match.start():]
            
            return response.strip()
        except Exception as e:
            logger.warning(f"Response cleaning failed: {str(e)}")
            return response.strip()
    
    def _count_technical_terms(self, content: str) -> int:
        """Rough count of technical terms in the extracted content."""
        if not content:
            return 0
        
        # Count bullet points in Required Skills section
        skills_section = re.search(r'\*\*Required Skills:\*\*(.*?)(?:\*\*|$)', content, re.DOTALL)
        if skills_section:
            skill_bullets = re.findall(r'^\s*[-•]\s*(.+)', skills_section.group(1), re.MULTILINE)
            return len(skill_bullets)
        
        return 0
    
    def _fallback_extraction(self, content: str) -> str:
        """Fallback method when LLM fails."""
        logger.info("Using fallback extraction method")
        
        # Basic regex-based extraction for fallback
        lines = content.split('\n')
        position = "Position not specified"
        location = "Location not specified"
        
        # Try to extract basic information
        for line in lines[:10]:
            if any(term in line.lower() for term in ['job title', 'position', 'role']):
                position = line.strip()
                break
        
        return f"""**Position:** {position} - {location}

**Required Skills:**
- Technical skills extraction failed - LLM unavailable
- Please review original job posting

**Key Responsibilities:**
- Content extraction failed - LLM unavailable

**Experience Required:**
- Experience requirements extraction failed - LLM unavailable"""

    def get_processing_statistics(self) -> Dict:
        """Get processing statistics for monitoring."""
        if self.stats['jobs_processed'] == 0:
            return self.stats
        
        return {
            'jobs_processed': self.stats['jobs_processed'],
            'average_reduction': self.stats['total_reduction'] / self.stats['jobs_processed'],
            'average_llm_time': self.stats['total_llm_time'] / self.stats['jobs_processed'],
            'total_processing_time': self.stats['total_llm_time'],
            'approach': 'A - Dual-Purpose Prompt Redesign'
        }
