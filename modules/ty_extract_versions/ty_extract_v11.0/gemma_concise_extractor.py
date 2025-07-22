"""
V11.0 Concise Description Extractor - 2025-07-20 Template
=========================================================

Uses the exact validated template from 2025-07-20 that produces proper 
"Your Tasks"/"Your Profile" format with qwen3:latest (validation winner).
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GemmaConciseExtractor:
    """
    V11.0 qwen3:latest extractor using validated 2025-07-20 template
    
    Produces proper "Your Tasks"/"Your Profile" format that matches
    the expected CV-ready structure.
    """
    
    def __init__(self, model_name: str = "qwen3:latest"):
        """
        Initialize the V11.0 extractor with qwen3:latest
        
        Args:
            model_name: Ollama model name (qwen3:latest is validation winner)
        """
        self.model_name = model_name
        self.is_available = self._check_availability()
        
        # Load the exact 2025-07-20 validated template
        self.template_prompt = self._load_2025_template()
        
        if self.is_available:
            logger.info(f"✅ V11.0 extractor initialized with model: {model_name}")
            logger.info(f"✅ Using 2025-07-20 validated template ({len(self.template_prompt)} chars)")
        else:
            logger.warning(f"⚠️ V11.0 extractor not available - Ollama or model missing")
    
    def _load_2025_template(self) -> str:
        """Load the exact 2025-07-20 validated template"""
        return """Hello. Please help me to create a concise role description, according to this template:
# Template

```
## {job_title} - Requirements & Responsibilities

  ### Your Tasks
* [Category]: [Detailed responsibility description]
* [Category]: [Detailed responsibility description]
* [Category]: [Detailed responsibility description]
* [Continue as needed for 5-8 key areas]

### Your Profile
* Education & Experience: [Requirements and preferred experience]
* Technical Skills: [Specific systems, software, tools mentioned]
* Language Skills: [Language requirements with proficiency levels]
* [Other categories as relevant]: [Additional requirements]

## Extraction Rules:

**Your Tasks Section:**
- Focus on ROLE RESPONSIBILITIES (what they will DO)
- Use action verbs (develop, implement, verify, analyze, collaborate)
- Organize by logical categories (Process Management, Data Analysis, etc.)
- Include specific processes mentioned
- 5-8 bullet points maximum

**Your Profile Section:**
- Focus on CANDIDATE REQUIREMENTS (what they must HAVE)
- Be specific about systems/tools (e.g., SimCorp Dimension, SAP)
- Include experience levels where specified
- Separate education, technical skills, languages
- Include both required and preferred qualifications

## Quality Standards:
- Comprehensive (both role AND requirements)
- Structured (clear sections)
- CV-Ready (suitable for recruitment)
- Professional business language

## CRITICAL: CV Matching Focus
- NEVER include "What We Offer", "Benefits", or "Company Culture" sections
- ONLY extract job requirements and responsibilities  
- Focus purely on candidate requirements and job tasks
```

# Input
```"""
    
    def _check_availability(self) -> bool:
        """Check if Ollama and the model are available"""
        try:
            # Check if ollama command exists
            result = subprocess.run(['which', 'ollama'], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                logger.debug("Ollama command not found")
                return False
            
            # Check if model exists
            result = subprocess.run(['ollama', 'list'], 
                                   capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.debug("Failed to list Ollama models")
                return False
            
            if self.model_name.split(':')[0] not in result.stdout:
                logger.debug(f"Model {self.model_name} not found in Ollama")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Availability check failed: {e}")
            return False
    
    def extract_concise_description(self, job_description: str) -> Dict[str, Any]:
        """
        Extract concise job description using 2025-07-20 validated template
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Dictionary with extraction results and metadata
        """
        if not self.is_available:
            return self._create_error_response("V11.0 extractor not available")
        
        if not job_description or not job_description.strip():
            return self._create_error_response("Empty job description provided")
        
        try:
            # Use the validated 2025-07-20 template with qwen3:latest
            logger.info(f"🤖 Using V11.0 extraction with {self.model_name}")
            
            full_prompt = f"{self.template_prompt}\n\n{job_description}\n\n```"
            
            # Execute with qwen3:latest
            result = subprocess.run([
                "ollama", "run", self.model_name
            ], input=full_prompt, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.error(f"❌ {self.model_name} execution failed: {result.stderr}")
                return self._create_error_response(f"LLM execution failed: {result.stderr}")
            
            # Clean and validate the output
            extracted_content = self._clean_output(result.stdout.strip())
            
            logger.info(f"✅ V11.0 extraction successful - {len(extracted_content)} chars")
            
            return {
                "success": True,
                "content": extracted_content,
                "model_used": self.model_name,
                "template": "2025-07-20_validated",
                "extraction_type": "concise_cv_ready"
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {self.model_name} extraction timeout")
            return self._create_error_response("Extraction timeout")
            
        def _clean_output(self, raw_output: str) -> str:
        """Clean the LLM output to extract just the job description"""
        lines = raw_output.split('\n')
        cleaned_lines = []
        
        # Skip thinking/reasoning lines and extract the actual content
        in_content = False
        for line in lines:
            # Start capturing after we see the job title format
            if '##' in line and ('Requirements' in line or 'Responsibilities' in line):
                in_content = True
            
            if in_content:
                cleaned_lines.append(line)
        
        if cleaned_lines:
            return '\n'.join(cleaned_lines).strip()
        
        # Fallback: return the raw output if we can't find the structured content
        return raw_output.strip()
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "content": "",
            "model_used": self.model_name,
            "template": "2025-07-20_validated",
            "extraction_type": "error"
        }
    
    def is_ready(self) -> bool:
        """Check if the extractor is ready for use"""
        return self.is_available


def extract_with_qwen3(job_description: str, model_name: str = "qwen3:latest") -> Dict[str, Any]:
    """Convenience function for V11.0 qwen3-based extraction using 2025-07-20 template"""
    
    Args:
        job_description: Raw job description text
        model_name: Ollama model name to use (qwen3:latest recommended)
        
    Returns:
        Dictionary with extraction results
    """
    extractor = GemmaConciseExtractor(model_name)
    return extractor.extract_concise_description(job_description)
            
            # Success response
            return {
                "status": "success",
                "concise_description": step2_result.strip(),
                "intermediate_extraction": step1_result.strip(),
                "extraction_method": "gemma_two_step",
                "model_used": self.model_name,
                "steps_completed": 2
            }
            
        except Exception as e:
            logger.error(f"Gemma extraction failed: {e}")
            return self._create_error_response(f"Extraction failed: {str(e)}")
    
    def _run_step1_extraction(self, job_description: str) -> Optional[str]:
        """
        Step 1: Initial extraction (replicates xai's first prompt)
        """
        prompt = ("Please extract the requirements and responsibilities from the following job description. "
                 "Present them in two clear sections: \"Your Tasks\" and \"Your Profile\".")
        
        return self._execute_ollama_prompt(prompt, job_description)
    
    def _run_step2_requirements(self, step1_output: str) -> Optional[str]:
        """
        Step 2: Requirements focus (replicates xai's second prompt)
        """
        prompt = ("I only need the requirements, not what the company does or is or wants to give me. "
                 "Only the stuff I need to bring to the table please. "
                 "Also, can you please translate this into English?")
        
        return self._execute_ollama_prompt(prompt, step1_output)
    
    def _execute_ollama_prompt(self, prompt: str, content: str) -> Optional[str]:
        """
        Execute a prompt using Ollama API with controlled temperature
        
        Args:
            prompt: The prompt to send
            content: The content to process
            
        Returns:
            Model response or None if failed
        """
        try:
            import requests
            
            # Combine prompt and content
            full_prompt = f"{prompt}\n\n{content}"
            
            # Use Ollama API for better temperature control
            data = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.01,  # Very low temperature for consistency
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=data,
                timeout=1200  # 20 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API call failed: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Ollama API call timed out")
            return None
        except Exception as e:
            logger.error(f"Ollama API call error: {e}")
            return None
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response structure"""
        return {
            "status": "error",
            "concise_description": None,
            "intermediate_extraction": None,
            "extraction_method": "gemma_two_step",
            "model_used": self.model_name,
            "error": error_message,
            "steps_completed": 0
        }
    
    def is_ready(self) -> bool:
        """Check if the extractor is ready for use"""
        return self.is_available


def extract_with_gemma(job_description: str, model_name: str = "gemma3n:latest") -> Dict[str, Any]:
    """
    Convenience function for Gemma-based extraction
    
    Args:
        job_description: Raw job description text
        model_name: Ollama model name to use
        
    Returns:
        Dictionary with extraction results
    """
    extractor = GemmaConciseExtractor(model_name)
    return extractor.extract_concise_description(job_description)
