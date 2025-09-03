"""
Real LLM Integration for ty_report_base - Phase 2b
No stubs, no mocks, no fallbacks. Only authentic intelligence.

Misty's guidance: "Accuracy of generation > verbosity"
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import subprocess
import requests

logger = logging.getLogger(__name__)

class AuthenticLLMIntegration:
    """Real LLM integration - no synthetic responses"""
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        Initialize with real model configuration
        
        Args:
            model_config: Configuration for actual LLM
                - provider: "openai", "anthropic", "local_ollama", etc.
                - model_name: Specific model identifier
                - api_key: Authentication if needed
                - endpoint: API endpoint or local server
                - max_tokens: Response length limit
                - temperature: Generation randomness (0.0-1.0)
        """
        self.config = model_config
        self.provider = model_config.get('provider')
        self.model_name = model_config.get('model_name')
        
        # Validate configuration
        if not self.provider or not self.model_name:
            raise ValueError("Must specify provider and model_name for real LLM integration")
        
        # Initialize based on provider
        self._initialize_provider()
        
        logger.info(f"Authentic LLM initialized: {self.provider}/{self.model_name}")
    
    def _initialize_provider(self):
        """Initialize connection to real LLM provider"""
        
        if self.provider == "openai":
            self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OpenAI API key required for authentic integration")
            self.endpoint = "https://api.openai.com/v1/chat/completions"
            
        elif self.provider == "anthropic":
            self.api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("Anthropic API key required for authentic integration")
            self.endpoint = "https://api.anthropic.com/v1/messages"
            
        elif self.provider == "local_ollama":
            self.endpoint = self.config.get('endpoint', 'http://localhost:11434/api/generate')
            # Test connection to local Ollama
            try:
                response = requests.get('http://localhost:11434/api/tags', timeout=5)
                if response.status_code != 200:
                    raise ConnectionError("Cannot connect to local Ollama server")
            except requests.RequestException as e:
                raise ConnectionError(f"Local Ollama not accessible: {e}")
                
        elif self.provider == "local_llamacpp":
            self.endpoint = self.config.get('endpoint', 'http://localhost:8080/completion')
            # Test connection to llama.cpp server
            try:
                response = requests.get(self.endpoint.replace('/completion', '/health'), timeout=5)
            except requests.RequestException as e:
                raise ConnectionError(f"Local llama.cpp server not accessible: {e}")
                
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def generate_authentic_content(self, prompt: str, input_data: Dict[str, Any], 
                                 section_name: str) -> str:
        """
        Generate authentic content using real LLM
        
        Args:
            prompt: The empathy-wrapped prompt
            input_data: Real extraction data
            section_name: Section being generated
            
        Returns:
            Authentic LLM-generated content
        """
        start_time = time.time()
        
        try:
            # Prepare context-rich prompt with real data
            enriched_prompt = self._enrich_prompt_with_data(prompt, input_data, section_name)
            
            # Generate using real LLM
            if self.provider == "openai":
                content = self._generate_openai(enriched_prompt)
            elif self.provider == "anthropic":
                content = self._generate_anthropic(enriched_prompt)
            elif self.provider == "local_ollama":
                content = self._generate_ollama(enriched_prompt)
            elif self.provider == "local_llamacpp":
                content = self._generate_llamacpp(enriched_prompt)
            else:
                raise ValueError(f"Provider {self.provider} not implemented")
            
            generation_time = (time.time() - start_time) * 1000
            
            # Log authentic generation
            logger.info(f"Authentic {self.provider} generation for {section_name}: "
                       f"{len(content)} chars in {generation_time:.1f}ms")
            
            return content
            
        except Exception as e:
            logger.error(f"Authentic LLM generation failed for {section_name}: {e}")
            # No fallback - if real LLM fails, we fail transparently
            raise RuntimeError(f"Cannot generate authentic content: {e}")
    
    def _enrich_prompt_with_data(self, prompt: str, input_data: Dict[str, Any], 
                                section_name: str) -> str:
        """Enrich prompt with actual extraction data"""
        
        blocks = input_data.get('blocks', [])
        if not blocks:
            return prompt + "\n\nNote: No extraction data available for analysis."
        
        # Add real data context
        data_context = "\n\nExtraction Data for Analysis:\n"
        
        for i, block in enumerate(blocks[:3]):  # Limit to first 3 blocks to avoid prompt bloat
            data_context += f"\nJob {i+1}:\n"
            if 'title' in block:
                data_context += f"- Position: {block['title']}\n"
            if 'company' in block:
                data_context += f"- Company: {block['company']}\n"
            if 'requirements' in block and block['requirements']:
                reqs = block['requirements'][:4]  # First 4 requirements
                data_context += f"- Key Requirements: {', '.join(reqs)}\n"
            if 'extraction_confidence' in block:
                data_context += f"- Extraction Confidence: {block['extraction_confidence']:.1%}\n"
        
        # Add configuration context
        config = input_data.get('config', {})
        if config:
            data_context += f"\nReport Configuration:\n"
            data_context += f"- Empathy Level: {config.get('empathy_level', 'standard')}\n"
            data_context += f"- QA Mode: {config.get('qa_mode', 'basic')}\n"
            data_context += f"- Version: {config.get('version', 'unknown')}\n"
        
        return prompt + data_context
    
    def _generate_openai(self, prompt: str) -> str:
        """Generate using OpenAI API"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.get('max_tokens', 500),
            "temperature": self.config.get('temperature', 0.7)
        }
        
        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        return str(content).strip() if content else ""
    
    def _generate_anthropic(self, prompt: str) -> str:
        """Generate using Anthropic Claude API"""
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model_name,
            "max_tokens": self.config.get('max_tokens', 500),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.get('temperature', 0.7)
        }
        
        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        text_content = result['content'][0]['text']
        return str(text_content).strip() if text_content else ""
    
    def _generate_ollama(self, prompt: str) -> str:
        """Generate using local Ollama"""
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.get('temperature', 0.7),
                "num_predict": self.config.get('max_tokens', 500)
            }
        }
        
        response = requests.post(self.endpoint, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['response']
        return str(response_text).strip() if response_text else ""
    
    def _generate_llamacpp(self, prompt: str) -> str:
        """Generate using local llama.cpp server"""
        
        payload = {
            "prompt": prompt,
            "n_predict": self.config.get('max_tokens', 500),
            "temperature": self.config.get('temperature', 0.7),
            "stop": ["</s>", "\n\nUser:", "\n\nAssistant:"]
        }
        
        response = requests.post(self.endpoint, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result['content']
        return str(content).strip() if content else ""
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the active model"""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "endpoint": getattr(self, 'endpoint', 'not_applicable'),
            "max_tokens": self.config.get('max_tokens'),
            "temperature": self.config.get('temperature'),
            "is_local": self.provider in ['local_ollama', 'local_llamacpp'],
            "requires_api_key": self.provider in ['openai', 'anthropic']
        }
