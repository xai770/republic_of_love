"""
MemBridge LLM Interface for v17
===============================

Clean integration replacing v14 LLMInterface with MemBridge registry system.
All LLM calls now go through MemBridge for logging, validation, and config-driven operation.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import yaml
import sys

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
    MemBridge-powered LLM interface replacing v14 LLMInterface.
    
    Features:
    - All calls logged to mb_log
    - Config-driven model/prompt selection
    - Validation layer for inputs/outputs
    - Simple table access for xai
    
    Usage:
        llm = MemBridgeLLMInterface(config)
        skills = llm.extract_skills("Job description", "Job Title")
    """
    
    def __init__(self, config: Any) -> None:
        """Initialize MemBridge LLM interface"""
        self.config = config
        
        # Load MemBridge configuration
        self.membridge_config, self.db_path = self._load_membridge_config()
        
        # Initialize registry system
        self.registry = RegistrySystem(
            db_path=self.db_path,
            config=self.membridge_config
        )
        
        # Initialize config-driven caller
        self.caller = ConfigDrivenLLMCall(self.registry)
        
        logger.info(f"✅ MemBridge LLM Interface initialized")
        logger.info(f"   • Database: {self.db_path}")
        logger.info(f"   • Validation: {'enabled' if self.membridge_config.validation_enabled else 'disabled'}")
    
    def _load_membridge_config(self) -> tuple[MemBridgeConfig, str]:
        """Load MemBridge configuration from membridge/config/membridge.yaml"""
        config_path = Path(__file__).parent.parent.parent / "config" / "membridge.yaml"
        
        if not config_path.exists():
            raise Exception(f"MemBridge config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        mb_config = config_data['membridge']
        
        # Build absolute database path
        db_path = Path(__file__).parent.parent.parent / mb_config['database_path']
        
        return MemBridgeConfig(
            prompt_registry_path="membridge/config/prompts",
            validation_enabled=mb_config['validation']['enabled']
        ), str(db_path)
    
    def extract_skills(self, job_description: str, job_title: str) -> JobSkills:
        """
        Extract skills using MemBridge registry system
        
        Args:
            job_description: Job description text
            job_title: Job title
            
        Returns:
            JobSkills object with extracted skills
        """
        logger.info(f"🤖 MemBridge skill extraction for: {job_title}")
        
        # Use call number 1 (skill extraction with gemma3:1b by default)
        # xai can change this in mb_template_registry to test different models
        call_number = 1
        
        # Prepare input variables
        variables = {
            "job_title": job_title,
            "job_description": job_description[:3000]  # v14 compatibility
        }
        
        try:
            # Make config-driven call via MemBridge
            response = self.caller.call_llm(
                call_number=call_number,
                input_text=f"Job Title: {job_title}\n\nJob Description: {job_description[:3000]}"
            )
            
            if not response['success']:
                raise Exception(f"MemBridge call failed: {response.get('error', 'Unknown error')}")
            
            # Parse response using v14-compatible method
            skills = self._parse_skills_response(response['output'])
            
            logger.info(f"✅ MemBridge extracted {skills.total_count()} skills for: {job_title}")
            
            return skills
            
        except Exception as e:
            logger.error(f"❌ MemBridge skill extraction failed: {e}")
            raise Exception(f"MemBridge skill extraction failed: {e}")
    
    def extract_concise_description(self, job_description: str, job_title: str) -> str:
        """
        Extract concise description using MemBridge registry system
        
        Args:
            job_description: Job description text
            job_title: Job title
            
        Returns:
            Concise description string
        """
        logger.info(f"🤖 MemBridge concise description for: {job_title}")
        
        # Use call number 2 (concise description with gemma3:1b by default)
        call_number = 2
        
        # Prepare input variables
        variables = {
            "job_title": job_title,
            "job_description": job_description[:2000]  # v14 compatibility
        }
        
        try:
            # Make config-driven call via MemBridge
            response = self.caller.call_llm(
                call_number=call_number,
                input_text=f"Job Title: {job_title}\n\nJob Description: {job_description[:2000]}"
            )
            
            if not response['success']:
                raise Exception(f"MemBridge call failed: {response.get('error', 'Unknown error')}")
            
            # Clean up response (v14 compatibility)
            description = response['output'].strip()
            if len(description) > 500:
                description = description[:500] + "..."
            
            logger.info(f"✅ MemBridge generated concise description for: {job_title}")
            
            return description  # type: ignore[no-any-return]
            
        except Exception as e:
            logger.error(f"❌ MemBridge concise description failed: {e}")
            raise Exception(f"MemBridge concise description failed: {e}")
    
    def _parse_skills_response(self, response: str) -> JobSkills:
        """
        Parse skills response - reusing v14 parsing logic for compatibility
        
        This ensures v17 produces identical results to v14 for the same inputs.
        """
        # Import v14 parsing logic
        v14_llm_path = Path(__file__).parent.parent / "v14" / "llm_interface.py"
        
        if v14_llm_path.exists():
            # Use v14 parsing logic for exact compatibility
            spec = __import__('importlib.util', fromlist=['spec_from_file_location']).spec_from_file_location(
                "v14_llm", v14_llm_path
            )
            v14_module = __import__('importlib.util', fromlist=['module_from_spec']).module_from_spec(spec)
            spec.loader.exec_module(v14_module)
            
            # Create temporary v14 LLMInterface for parsing
            v14_llm = v14_module.LLMInterface.__new__(v14_module.LLMInterface)
            return v14_llm._parse_skills_response(response)  # type: ignore[no-any-return]
        else:
            # Fallback: simple parsing
            return self._simple_skills_parse(response)
    
    def _simple_skills_parse(self, response: str) -> JobSkills:
        """Simple fallback skills parsing"""
        # Initialize empty skills
        skills: Dict[str, Any] = {
            'technical': [],
            'business': [],
            'soft': [],
            'experience': [],
            'education': []
        }
        
        # Basic parsing - look for category patterns
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
                    if skills_text:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
            elif 'business' in line_lower and ':' in line:
                current_category = 'business'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
            elif 'soft' in line_lower and ':' in line:
                current_category = 'soft'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
            elif 'experience' in line_lower and ':' in line:
                current_category = 'experience'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
            elif 'education' in line_lower and ':' in line:
                current_category = 'education'
                if ':' in line:
                    skills_text = line.split(':', 1)[1].strip()
                    if skills_text:
                        skills[current_category].extend([s.strip() for s in skills_text.split(';') if s.strip()])
            elif current_category and ';' in line:
                # Continue extracting skills under current category
                skills[current_category].extend([s.strip() for s in line.split(';') if s.strip()])
        
        return JobSkills(
            technical=skills['technical'],
            business=skills['business'],
            soft=skills['soft'],
            experience=skills['experience'],
            education=skills['education']
        )
