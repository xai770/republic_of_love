"""
Gemma Concise Description Extractor
==================================

A specialist that replicates the two-step extraction process from simple_gemma_extractor.sh
using Ollama's Gemma model to extract concise job requirements.
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
    Gemma-based concise job description extractor
    
    Replicates the exact two-step process from simple_gemma_extractor.sh:
    1. Initial extraction of requirements and responsibilities
    2. Requirements-only focus with English translation
    """
    
    def __init__(self, model_name: str = "gemma3n:latest"):
        """
        Initialize the Gemma extractor
        
        Args:
            model_name: Ollama model name to use
        """
        self.model_name = model_name
        self.is_available = self._check_availability()
        
        if self.is_available:
            logger.info(f"✅ Gemma extractor initialized with model: {model_name}")
        else:
            logger.warning(f"⚠️ Gemma extractor not available - Ollama or model missing")
    
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
        Extract concise job description using two-step Gemma process
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Dictionary with extraction results and metadata
        """
        if not self.is_available:
            return self._create_error_response("Gemma extractor not available")
        
        if not job_description or not job_description.strip():
            return self._create_error_response("Empty job description provided")
        
        try:
            # Step 1: Initial extraction
            step1_result = self._run_step1_extraction(job_description)
            if not step1_result:
                return self._create_error_response("Step 1 extraction failed")
            
            # Step 2: Requirements focus
            step2_result = self._run_step2_requirements(step1_result)
            if not step2_result:
                return self._create_error_response("Step 2 requirements extraction failed")
            
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
        Execute a prompt using Ollama
        
        Args:
            prompt: The prompt to send
            content: The content to process
            
        Returns:
            Model response or None if failed
        """
        try:
            # Combine prompt and content
            full_prompt = f"{prompt}\n\n{content}"
            
            # Execute with ollama
            result = subprocess.run(
                ['ollama', 'run', self.model_name],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=1200  # 20 minute timeout (10x increase)
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Ollama execution failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Ollama execution timed out")
            return None
        except Exception as e:
            logger.error(f"Ollama execution error: {e}")
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
