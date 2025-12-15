"""
MemBridge LLM Interface for v17 - Simple Implementation
======================================================

Direct replacement for v14 LLMInterface using MemBridge registry.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path
import sys
import requests
import time
import json

# Add membridge to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from membridge.registry import RegistrySystem, ConfigDrivenLLMCall
from membridge.models import MemBridgeConfig
from .models import JobSkills

logger = logging.getLogger('ty_extract_v17.membridge_llm')

@dataclass  
class LLMResponse:
    """Structured LLM response with metadata - compatible with v14"""
    content: str
    success: bool
    duration: float
    model_used: str
    error_message: Optional[str] = None

class MemBridgeLLMInterface:
    """
    Simple MemBridge LLM interface replacing v14.
    
    Maps v14 method calls to MemBridge call numbers:
    - extract_skills() → call_number 1 (skill_extraction + gemma3:1b)
    - extract_concise_description() → call_number 2 (concise_description + gemma3:1b)
    
    xai can change models by updating mb_template_registry table.
    """
    
    def __init__(self, config: Any) -> None:
        """Initialize MemBridge interface"""
        self.config = config
        
        # Initialize MemBridge components
        mb_config = MemBridgeConfig(prompt_registry_path="membridge/config/prompts")
        
        self.registry = RegistrySystem(
            db_path="data/membridge.db", 
            config=mb_config
        )
        
        self.mb_call = ConfigDrivenLLMCall(self.registry)
        
        # Store config for LLM calls
        self.llm_base_url = config.llm_base_url
        self.llm_timeout = config.llm_timeout
        
        logger.info(f"✅ MemBridge LLM Interface v17 initialized")
        logger.info(f"   • All calls logged to mb_log")
        logger.info(f"   • Config-driven via mb_template_registry")
    
    def _call_actual_llm(self, prompt: str, model: str, config: Optional[str] = None) -> str:
        """
        Make actual LLM call using ollama API (copied from v14 for compatibility)
        """
        try:
            # Parse config if provided
            llm_config = {}
            if config:
                try:
                    llm_config = json.loads(config)
                except:
                    llm_config = {}
            
            # Default LLM parameters
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": llm_config.get("temperature", 0.1),
                    "top_p": llm_config.get("top_p", 0.9),
                    "top_k": llm_config.get("top_k", 40),
                    "num_predict": llm_config.get("num_predict", 1000)
                }
            }
            
            logger.debug(f"🤖 Calling LLM: {model}")
            
            response = requests.post(
                f"{self.llm_base_url}/api/generate",
                json=payload,
                timeout=self.llm_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return str(result.get('response', ''))
            else:
                raise Exception(f"LLM API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")
            raise e
    
    def extract_skills(self, job_description: str, job_title: str) -> JobSkills:
        """
        Extract skills using MemBridge call number 1
        """
        logger.info(f"🤖 MemBridge skill extraction for: {job_title}")
        
        # Format input text (simplified for initial testing)
        input_text = f"Job Title: {job_title}\n\nJob Description:\n{job_description[:3000]}"
        
        try:
            # Call via MemBridge (call_number 1 = skill extraction)
            response = self.mb_call.call_llm(
                call_number=1,
                input_text=input_text,
                llm_function=self._call_actual_llm
            )
            
            if not response['success']:
                raise Exception(f"MemBridge call failed: {response.get('error', 'Unknown error')}")
            
            # Parse response
            skills = self._parse_skills_response(response['output'])
            
            logger.info(f"✅ MemBridge extracted {skills.total_count()} skills")
            
            return skills
            
        except Exception as e:
            logger.error(f"❌ MemBridge skill extraction failed: {e}")
            raise Exception(f"MemBridge skill extraction failed: {e}")
    
    def extract_concise_description(self, job_description: str, job_title: str) -> str:
        """
        Extract concise description using MemBridge call number 2
        """
        logger.info(f"🤖 MemBridge concise description for: {job_title}")
        
        # Format input text (simplified for initial testing)
        input_text = f"Job Title: {job_title}\n\nJob Description:\n{job_description[:2000]}"
        
        try:
            # Call via MemBridge (call_number 2 = concise description)
            response = self.mb_call.call_llm(
                call_number=2,
                input_text=input_text,
                llm_function=self._call_actual_llm
            )
            
            if not response['success']:
                raise Exception(f"MemBridge call failed: {response.get('error', 'Unknown error')}")
            
            # Clean up response
            description = str(response['output']).strip()
            if len(description) > 500:
                description = description[:500] + "..."
            
            logger.info(f"✅ MemBridge generated concise description")
            
            return description
            
        except Exception as e:
            logger.error(f"❌ MemBridge concise description failed: {e}")
            raise Exception(f"MemBridge concise description failed: {e}")
    
    def _parse_skills_response(self, response: str) -> JobSkills:
        """
        Parse skills response using simple pattern matching
        """
        # Initialize empty skills
        skills: Dict[str, List[str]] = {
            'technical': [],
            'business': [],
            'soft': [],
            'experience': [],
            'education': []
        }
        
        lines = response.strip().split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for category headers
            line_lower = line.lower()
            if 'technical' in line_lower and ':' in line:
                current_category = 'technical'
                # Extract skills from same line
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text and skills_text.lower() not in ['none', 'none specified']:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
                        
            elif 'business' in line_lower and ':' in line:
                current_category = 'business'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text and skills_text.lower() not in ['none', 'none specified']:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
                        
            elif 'soft' in line_lower and ':' in line:
                current_category = 'soft'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text and skills_text.lower() not in ['none', 'none specified']:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
                        
            elif 'experience' in line_lower and ':' in line:
                current_category = 'experience'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text and skills_text.lower() not in ['none', 'none specified']:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
                        
            elif 'education' in line_lower and ':' in line:
                current_category = 'education'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text and skills_text.lower() not in ['none', 'none specified']:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
                        
            elif current_category and (';' in line or ',' in line):
                # Continue extracting skills under current category
                separator = ';' if ';' in line else ','
                extracted = [s.strip() for s in line.split(separator) if s.strip()]
                if extracted:
                    skills[current_category].extend(extracted)
        
        # Ensure we have some skills (fallback for poor responses)
        total_skills = sum(len(skill_list) for skill_list in skills.values())
        if total_skills == 0:
            logger.warning("⚠️ No structured skills found, adding fallback skills")
            skills['technical'] = ['Data Analysis', 'Computer Skills']
            skills['business'] = ['Business Analysis'] 
            skills['soft'] = ['Communication']
            skills['experience'] = ['Professional Experience']
            skills['education'] = ['Relevant Education']
        
        return JobSkills(
            technical=skills['technical'],
            business=skills['business'],
            soft=skills['soft'],
            experience=skills['experience'],
            education=skills['education']
        )
