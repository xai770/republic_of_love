"""
TY_EXTRACT LLM Core
==================

Minimal LLM integration for skill extraction using Ollama
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class LLMExtractor:
    """Minimal LLM extractor using Ollama"""
    
    def __init__(self, model_name: str = "gemma3n:latest"):
        self.model_name = model_name
        self.model = model_name  # For compatibility with _call_ollama
        self.ollama_url = "http://localhost:11434"
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()  # Initialize session for API calls
        
        self.logger.info(f"LLMExtractor initialized with model: {model_name}")
        
    def extract_skills_llm(self, job_description: str, job_title: str) -> Dict[str, Any]:
        """Extract skills using LLM analysis"""
        
        prompt = f"""
Analyze this job posting and extract skills in exactly this JSON format:

Job Title: {job_title}
Job Description: {job_description}

Please extract and categorize skills into:
1. Technical Skills: Programming languages, software, tools, technologies
2. Business Skills: Domain knowledge, processes, methodologies, business functions
3. Soft Skills: Communication, leadership, teamwork, problem-solving abilities
4. Experience Requirements: Years of experience, specific backgrounds, levels
5. Education Requirements: Degrees, certifications, qualifications

Return ONLY a JSON object with these exact keys:
{{
    "technical_requirements": "skill1; skill2; skill3",
    "business_requirements": "skill1; skill2; skill3", 
    "soft_skills": "skill1; skill2; skill3",
    "experience_requirements": "req1; req2; req3",
    "education_requirements": "req1; req2; req3"
}}

Extract real skills mentioned in the job description. Use semicolon separation. Be specific and accurate.
"""
        
        try:
            logger.info(f"🤖 LLM extraction starting for: {job_title}")
            print(f"🤖 LLM extraction starting for: {job_title}")
            
            response = self._call_ollama(prompt)
            
            logger.info(f"📝 LLM raw response received, length: {len(response)}")
            print(f"📝 LLM raw response received, length: {len(response)}")
            
            parsed_result = self._parse_llm_response(response)
            
            logger.info(f"✅ LLM extraction completed for: {job_title}")
            print(f"✅ LLM extraction completed for: {job_title}")
            
            return parsed_result
        except Exception as e:
            logger.error(f"❌ LLM extraction failed for job '{job_title}': {e}")
            print(f"❌ LLM extraction failed for job '{job_title}': {e}")
            return self._create_empty_response()
    
    def _call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama"""
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.01,  # Very low temperature for maximum consistency
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        response = self.session.post(
            f"{self.ollama_url}/api/generate",
            json=data,
            timeout=120  # Increased timeout for LLM processing
        )
        
        logger.info(f"🔄 Ollama response status: {response.status_code}")
        print(f"🔄 Ollama response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ Ollama API error: {response.status_code}")
            print(f"❌ Ollama API error: {response.status_code}")
            raise Exception(f"Ollama API error: {response.status_code}")
        
        result = response.json()
        llm_text = result.get('response', '')
        
        logger.info(f"📝 LLM response length: {len(llm_text)}")
        print(f"📝 LLM response length: {len(llm_text)}")
        
        return llm_text
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON"""
        try:
            # Look for JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in LLM response")
                return self._create_empty_response()
            
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Validate required keys
            required_keys = [
                'technical_requirements', 'business_requirements', 
                'soft_skills', 'experience_requirements', 'education_requirements'
            ]
            
            for key in required_keys:
                if key not in data:
                    data[key] = 'Not specified'
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._create_empty_response()
    
    def _create_empty_response(self) -> Dict[str, Any]:
        """Create empty response when LLM fails"""
        return {
            'technical_requirements': 'LLM extraction failed',
            'business_requirements': 'LLM extraction failed',
            'soft_skills': 'LLM extraction failed',
            'experience_requirements': 'LLM extraction failed',
            'education_requirements': 'LLM extraction failed'
        }
    
    def test_connection(self) -> bool:
        """Test if Ollama is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def extract_concise_description(self, job_description: str, job_title: str) -> str:
        """Extract concise job description using LLM"""
        
        prompt = f"""
Analyze this job posting and create a concise, professional summary that captures the key responsibilities and role overview.

Job Title: {job_title}
Job Description: {job_description}

Instructions:
1. Create a 2-3 sentence summary of the main responsibilities
2. Focus on what the person will actually DO in this role
3. Include the most important aspects of the job
4. Keep it professional and clear
5. Return ONLY the summary text, no additional formatting

Summary:
"""
        
        self.logger.info(f"🤖 LLM concise description extraction starting for: {job_title}")
        print(f"🤖 LLM concise description extraction starting for: {job_title}")
        
        try:
            response = self._call_ollama(prompt)
            
            if response and len(response.strip()) > 20:
                # Clean up the response
                description = response.strip()
                
                # Remove common prefixes that might be added by the LLM
                prefixes_to_remove = [
                    "Summary:", "Description:", "Overview:", "Job Summary:", 
                    "Role Summary:", "Position Summary:", "The role involves",
                    "This position", "The position", "The candidate will"
                ]
                
                for prefix in prefixes_to_remove:
                    if description.startswith(prefix):
                        description = description[len(prefix):].strip()
                        break
                
                # Ensure it starts with a capital letter
                if description and description[0].islower():
                    description = description[0].upper() + description[1:]
                
                self.logger.info(f"✅ LLM concise description completed for: {job_title}")
                print(f"✅ LLM concise description completed for: {job_title}")
                
                return f"**Role Overview:** {description}"
            else:
                self.logger.warning(f"⚠️ LLM returned insufficient content for concise description")
                return f"**Position:** {job_title}"
                
        except Exception as e:
            self.logger.error(f"❌ LLM concise description extraction failed: {e}")
            return f"**Position:** {job_title}"
