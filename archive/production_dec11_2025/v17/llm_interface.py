"""
LLM Interface for TY_EXTRACT V14
===============================

Clean, efficient LLM integration with proper error handling and type safety.
"""

import requests
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .config import Config
from .models import JobSkills

logger = logging.getLogger('ty_extract_v14.llm')

@dataclass
class LLMResponse:
    """Structured LLM response with metadata"""
    content: str
    success: bool
    duration: float
    model_used: str
    error_message: Optional[str] = None

class LLMInterface:
    """
    Clean LLM interface with consistent behavior and proper error handling
    
    Example:
        llm = LLMInterface(config)
        skills = llm.extract_skills("Job description here", "Job Title")
        description = llm.extract_concise_description("Job description", "Job Title")
    """
    
    def __init__(self, config: Config):
        """
        Initialize LLM interface
        
        Args:
            config: Configuration object with LLM settings
        """
        self.config = config
        self.base_url = config.llm_base_url
        self.model = config.llm_model
        self.timeout = config.llm_timeout
        
        # Test connection on initialization
        self._test_connection()
        
        logger.info(f"✅ LLM Interface initialized: {self.model} at {self.base_url}")
    
    def _test_connection(self) -> bool:
        """Test connection to LLM service"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ LLM service connection verified")
                return True
            else:
                logger.warning(f"⚠️ LLM service returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to LLM service: {e}")
            return False
    
    def _call_llm(self, prompt: str) -> LLMResponse:
        """
        Make a call to the LLM service
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            LLMResponse with result and metadata
        """
        import time
        start_time = time.time()
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 1000
                }
            }
            
            logger.debug(f"🤖 Calling LLM: {self.model}")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = str(result.get('response', ''))
                
                logger.debug(f"✅ LLM call completed in {duration:.1f}s")
                
                return LLMResponse(
                    content=content,
                    success=True,
                    duration=duration,
                    model_used=self.model
                )
            else:
                error_msg = f"LLM API returned status {response.status_code}"
                logger.error(f"❌ {error_msg}")
                
                return LLMResponse(
                    content="",
                    success=False,
                    duration=duration,
                    model_used=self.model,
                    error_message=error_msg
                )
                
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"LLM call failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            return LLMResponse(
                content="",
                success=False,
                duration=duration,
                model_used=self.model,
                error_message=error_msg
            )
    
    def extract_skills(self, job_description: str, job_title: str) -> JobSkills:
        """
        Extract skills from a job posting using LLM
        
        Args:
            job_description: The job description text
            job_title: The job title
            
        Returns:
            JobSkills object with extracted skills
            
        Example:
            skills = llm.extract_skills("Python developer needed...", "Senior Python Developer")
        """
        # Get template from external config
        template = self.config.get_template('skill_extraction')
        
        # Format template with variables
        prompt = template.format(
            job_title=job_title,
            job_description=job_description[:3000]
        )
        
        logger.info(f"🤖 Extracting skills for: {job_title}")
        
        response = self._call_llm(prompt)
        
        if not response.success:
            logger.error(f"❌ Skills extraction failed: {response.error_message}")
            # NO FALLBACK - fail if LLM fails
            raise Exception(f"LLM skills extraction failed: {response.error_message}")
        
        # Parse the structured response
        skills = self._parse_skills_response(response.content)
        
        logger.info(f"✅ Extracted {skills.total_count()} skills for: {job_title}")
        
        return skills
    
    def _parse_skills_response(self, response: str) -> JobSkills:
        """
        Parse structured skills response from LLM with enhanced fuzzy matching
        
        Args:
            response: LLM response text
            
        Returns:
            JobSkills object
            
        Raises:
            Exception: If parsing fails completely or no skills extracted
        """
        # Initialize empty skills
        skills: Dict[str, List[str]] = {
            'technical': [],
            'business': [],
            'soft': [],
            'experience': [],
            'education': []
        }
        
        # Category matching patterns (case-insensitive, flexible)
        category_patterns = {
            'technical': ['technical', 'tech', 'technical skills', 'technical requirements'],
            'business': ['business', 'business skills', 'domain', 'industry'],
            'soft': ['soft', 'soft skills', 'interpersonal', 'communication'],
            'experience': ['experience', 'experience requirements', 'years', 'background'],
            'education': ['education', 'education requirements', 'degree', 'qualification']
        }
        
        try:
            lines = response.strip().split('\n')
            current_category = None
            
            # First pass: Look for category headers and extract skills
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for category headers with fuzzy matching
                detected_category = self._detect_category(line, category_patterns)
                if detected_category:
                    current_category = detected_category
                    # Extract skills from same line if they exist
                    extracted_skills = self._extract_skills_from_line(line, fuzzy=True)
                    if extracted_skills:
                        skills[current_category].extend(extracted_skills)
                elif current_category:
                    # Continue extracting skills under current category
                    extracted_skills = self._extract_skills_from_line(line, fuzzy=True)
                    if extracted_skills:
                        skills[current_category].extend(extracted_skills)
            
            # Second pass: If no structured format found, try extracting from full text
            if not any(skills.values()):
                logger.warning("⚠️ No structured format found, attempting fuzzy extraction")
                skills = self._fuzzy_extract_skills(response)
            
            # Validation: Ensure we extracted meaningful skills
            total_skills = sum(len(skill_list) for skill_list in skills.values())
            if total_skills == 0:
                raise Exception("No skills could be extracted from LLM response")
                
            # Log detailed extraction results
            logger.info(f"✅ Skills extracted - Technical: {len(skills['technical'])}, "
                       f"Business: {len(skills['business'])}, Soft: {len(skills['soft'])}, "
                       f"Experience: {len(skills['experience'])}, Education: {len(skills['education'])}")
            
        except Exception as e:
            logger.error(f"❌ Critical error parsing skills response: {e}")
            logger.error(f"Raw LLM response: {response[:200]}...")
            raise Exception(f"Skills parsing failed: {e}")
        
        return JobSkills(
            technical=skills['technical'],
            business=skills['business'],
            soft=skills['soft'],
            experience=skills['experience'],
            education=skills['education']
        )
    
    def _detect_category(self, line: str, category_patterns: Dict[str, List[str]]) -> Optional[str]:
        """
        Detect skill category from line using fuzzy matching
        
        Args:
            line: Text line to analyze
            category_patterns: Dictionary of category patterns
            
        Returns:
            Detected category name or None
        """
        line_lower = line.lower()
        
        for category, patterns in category_patterns.items():
            for pattern in patterns:
                if pattern in line_lower:
                    # Additional validation: line should contain common separators
                    if any(sep in line for sep in [':', '-', '•', '*', '1.', '2.']):
                        return category
        
        return None
    
    def _extract_skills_from_line(self, line: str, prefix: str = '', fuzzy: bool = False) -> List[str]:
        """
        Extract skills from a single line with enhanced parsing
        
        Args:
            line: Text line to parse
            prefix: Prefix to remove (legacy support)
            fuzzy: Enable fuzzy parsing for various formats
            
        Returns:
            List of extracted skills
        """
        # Handle legacy prefix removal
        if prefix:
            content = line.replace(prefix, '').strip()
        else:
            content = line.strip()
        
        # Remove common prefixes and separators
        for separator in [':', '-', '•', '*']:
            if separator in content:
                content = content.split(separator, 1)[1].strip()
                break
        
        if not content or content.lower() in ['none', 'n/a', 'not specified', 'not applicable']:
            return []
        
        # Multiple splitting strategies
        skills = []
        
        # Strategy 1: Semicolon separation
        if ';' in content:
            skills = [skill.strip() for skill in content.split(';') if skill.strip()]
        # Strategy 2: Comma separation
        elif ',' in content:
            skills = [skill.strip() for skill in content.split(',') if skill.strip()]
        # Strategy 3: Bullet points or numbered lists
        elif any(marker in content for marker in ['•', '*', '-', '1.', '2.', '3.']):
            # Remove common list markers and split
            for marker in ['•', '*', '-']:
                content = content.replace(marker, ',')
            # Remove numbers like "1.", "2.", etc.
            import re
            content = re.sub(r'\d+\.', ',', content)
            skills = [skill.strip() for skill in content.split(',') if skill.strip()]
        # Strategy 4: Single skill or natural language
        else:
            # If it looks like a single skill, take it
            if len(content.split()) <= 5:  # Short phrases are likely skills
                skills = [content]
            else:
                # Try to extract key phrases from longer text
                skills = self._extract_skills_from_text(content)
        
        # Clean up and validate skills
        cleaned_skills = []
        for skill in skills:
            skill = skill.strip().strip('.,')
            if len(skill) > 2 and skill.lower() not in ['and', 'or', 'with', 'the']:
                cleaned_skills.append(skill)
        
        return cleaned_skills
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """
        Extract skills from natural language text using keyword patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted skills
        """
        # Common skill keywords and patterns
        skill_patterns = [
            r'\b(?:proficiency|experience|knowledge)\s+(?:in|with|of)\s+([^,.]+)',
            r'\b([A-Za-z][A-Za-z0-9\s]{2,20})\s+(?:skills?|experience|knowledge)',
            r'\b(?:strong|excellent|good)\s+([^,.]{3,20})\s+skills?',
            r'\b([A-Za-z][A-Za-z0-9\s]{2,15})\s+(?:required|preferred|needed)'
        ]
        
        import re
        extracted_skills = []
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                skill = match.strip()
                if len(skill) > 2:
                    extracted_skills.append(skill)
        
        return extracted_skills[:5]  # Limit to prevent noise
    
    def _fuzzy_extract_skills(self, response: str) -> Dict[str, List[str]]:
        """
        Fallback method for extracting skills when no clear structure is found
        
        Args:
            response: Full LLM response text
            
        Returns:
            Dictionary of categorized skills
        """
        skills: Dict[str, List[str]] = {
            'technical': [],
            'business': [],
            'soft': [],
            'experience': [],
            'education': []
        }
        
        # Technical skill indicators
        tech_keywords = ['programming', 'software', 'development', 'database', 'system', 
                        'technology', 'coding', 'framework', 'language', 'tool']
        
        # Business skill indicators  
        business_keywords = ['management', 'business', 'strategy', 'analysis', 'finance',
                           'marketing', 'sales', 'operations', 'project', 'process']
        
        # Soft skill indicators
        soft_keywords = ['communication', 'leadership', 'teamwork', 'problem-solving',
                        'analytical', 'creative', 'interpersonal', 'collaboration']
        
        # Extract potential skills and categorize
        words = response.lower().split()
        potential_skills = []
        
        # Simple keyword-based extraction
        for i, word in enumerate(words):
            if word in tech_keywords and i > 0:
                potential_skills.append(('technical', words[i-1:i+2]))
            elif word in business_keywords and i > 0:
                potential_skills.append(('business', words[i-1:i+2]))
            elif word in soft_keywords and i > 0:
                potential_skills.append(('soft', words[i-1:i+2]))
        
        # Add basic fallback skills if nothing found
        if not potential_skills:
            skills['technical'] = ['Data Analysis', 'Computer Skills']
            skills['business'] = ['Business Analysis', 'Process Improvement']
            skills['soft'] = ['Communication', 'Problem Solving']
            skills['experience'] = ['Professional Experience']
            skills['education'] = ['Relevant Education']
        
        return skills

    def extract_concise_description(self, job_description: str, job_title: str) -> str:
        """
        Extract a concise description from a job posting
        
        Args:
            job_description: The job description text
            job_title: The job title
            
        Returns:
            Concise description string
            
        Example:
            description = llm.extract_concise_description("Long job posting...", "Developer")
        """
        # Get template from external config
        template = self.config.get_template('concise_description')
        
        # Format template with variables
        prompt = template.format(
            job_title=job_title,
            job_description=job_description[:2000]
        )
        
        logger.info(f"🤖 Extracting concise description for: {job_title}")
        
        response = self._call_llm(prompt)
        
        if not response.success:
            logger.error(f"❌ Concise description extraction failed: {response.error_message}")
            # NO FALLBACK - fail if LLM fails
            raise Exception(f"LLM concise description failed: {response.error_message}")
        
        description = response.content.strip()
        
        # Clean up the response
        if len(description) > 500:
            description = description[:500] + "..."
        
        logger.info(f"✅ Generated concise description for: {job_title}")
        
        return description
