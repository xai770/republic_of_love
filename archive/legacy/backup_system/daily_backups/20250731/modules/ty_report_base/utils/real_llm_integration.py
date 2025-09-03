"""
Real LLM Integration for ty_report_base
Phase 2b: From stub to production-ready LLM integration

"You're not just a builder now, Arden. You're a steward." - Misty
"""

import requests
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import logging
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass
class LLMGenerationMetrics:
    """Comprehensive metrics for LLM generation tracking"""
    prompt_version: str
    empathy_length: int
    raw_prompt_length: int
    wrapped_prompt_length: int
    generation_time_ms: float
    model_used: str
    temperature: float
    max_tokens: int
    actual_tokens_generated: int
    confidence_score: Optional[float] = None
    quality_flags: List[str] = field(default_factory=list)

class RealLLMIntegration:
    """Production LLM integration maintaining empathy and rigorous logging"""
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        self.config = model_config or self._default_config()
        self.model_name = self.config['model']
        self.generation_history: List[Dict[str, Any]] = []
        
        # Initialize model connection
        self._initialize_model()
        
        logger.info(f"Real LLM integration initialized: {self.model_name}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for LLM integration"""
        return {
            'model': 'ollama/llama2',  # Local model for privacy
            'temperature': 0.7,
            'max_tokens': 500,
            'timeout': 30,
            'base_url': 'http://localhost:11434',  # Ollama default
            'fallback_to_stub': True  # Graceful fallback if model unavailable
        }
    
    def _initialize_model(self):
        """Initialize connection to local LLM"""
        try:
            # Test connection to local model
            if 'ollama' in self.model_name:
                test_url = f"{self.config['base_url']}/api/generate"
                test_payload = {
                    "model": self.model_name.split('/')[-1],
                    "prompt": "Test connection",
                    "stream": False,
                    "options": {"num_predict": 10}
                }
                
                response = requests.post(test_url, json=test_payload, timeout=5)
                if response.status_code == 200:
                    self.model_available = True
                    logger.info(f"Successfully connected to {self.model_name}")
                else:
                    raise ConnectionError(f"Model responded with status {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Could not connect to {self.model_name}: {e}")
            if self.config['fallback_to_stub']:
                logger.info("Will fallback to LLM stub for graceful degradation")
                self.model_available = False
            else:
                raise
    
    def generate_content(self, wrapped_prompt: str, input_data: Dict[str, Any], 
                        section_name: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, LLMGenerationMetrics]:
        """
        Generate content using real LLM with comprehensive metrics
        
        Args:
            wrapped_prompt: Empathy-wrapped prompt
            input_data: Extraction data for context
            section_name: Which section we're generating
            context: Additional context for generation
            
        Returns:
            Tuple of (generated_content, metrics)
        """
        start_time = time.time()
        
        # Initialize metrics
        metrics = LLMGenerationMetrics(
            prompt_version="v1_phase2b",
            empathy_length=self._calculate_empathy_length(wrapped_prompt),
            raw_prompt_length=len(wrapped_prompt.split('\n\n')[-2]),  # Extract core prompt
            wrapped_prompt_length=len(wrapped_prompt),
            generation_time_ms=0,
            model_used=self.model_name,
            temperature=self.config['temperature'],
            max_tokens=self.config['max_tokens'],
            actual_tokens_generated=0
        )
        
        try:
            if self.model_available:
                content = self._generate_with_real_llm(wrapped_prompt, section_name, metrics)
            else:
                # Graceful fallback to enhanced stub
                content = self._generate_with_enhanced_stub(wrapped_prompt, input_data, section_name)
                metrics.model_used = "enhanced_stub_fallback"
            
            # Calculate final metrics
            metrics.generation_time_ms = (time.time() - start_time) * 1000
            metrics.actual_tokens_generated = len(content.split())
            
            # Quality assessment
            metrics.quality_flags = self._assess_content_quality(content, section_name)
            
            # Log generation details
            logger.info(
                f"Generated {metrics.actual_tokens_generated} tokens for {section_name} "
                f"in {metrics.generation_time_ms:.1f}ms using {metrics.model_used}"
            )
            
            # Store in history for analysis
            self.generation_history.append({
                'section': section_name,
                'metrics': metrics,
                'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16]
            })
            
            return content, metrics
            
        except Exception as e:
            logger.error(f"Generation failed for {section_name}: {e}")
            metrics.quality_flags.append("generation_error")
            
            # Emergency fallback
            fallback_content = f"[Generation unavailable for {section_name}. Error: {str(e)[:100]}...]"
            return fallback_content, metrics
    
    def _generate_with_real_llm(self, wrapped_prompt: str, section_name: str, 
                               metrics: LLMGenerationMetrics) -> str:
        """Generate content using real LLM model"""
        
        if 'ollama' in self.model_name:
            return self._generate_with_ollama(wrapped_prompt, section_name, metrics)
        else:
            raise NotImplementedError(f"Model type {self.model_name} not yet implemented")
    
    def _generate_with_ollama(self, wrapped_prompt: str, section_name: str,
                             metrics: LLMGenerationMetrics) -> str:
        """Generate content using Ollama local model"""
        
        payload = {
            "model": self.model_name.split('/')[-1],
            "prompt": wrapped_prompt,
            "stream": False,
            "options": {
                "temperature": self.config['temperature'],
                "num_predict": self.config['max_tokens'],
                "top_p": 0.9,
                "stop": ["Human:", "User:", "Assistant:"]
            }
        }
        
        try:
            response = requests.post(
                f"{self.config['base_url']}/api/generate",
                json=payload,
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                if content:
                    logger.debug(f"Ollama generated {len(content)} chars for {section_name}")
                    return str(content)
                else:
                    raise ValueError("Empty response from Ollama")
            else:
                raise ConnectionError(f"Ollama returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama timeout for {section_name}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    def _generate_with_enhanced_stub(self, wrapped_prompt: str, input_data: Dict[str, Any], 
                                   section_name: str) -> str:
        """Enhanced stub fallback with better context awareness"""
        # Since we require only authentic LLMs in Phase 2b, this fallback should not be used
        # If we reach here, something is wrong with the LLM integration
        logger.error("Fallback called in authentic-only mode - this should not happen")
        return f"ERROR: Authentic LLM required but not available for {section_name}"
    
    def _calculate_empathy_length(self, wrapped_prompt: str) -> int:
        """Calculate empathy wrapper length"""
        lines = wrapped_prompt.split('\n')
        empathy_lines = [line for line in lines if any(
            phrase in line.lower() for phrase in 
            ['hello, fellow being', 'guidance', 'gratitude', 'wisdom', 'kindness']
        )]
        return sum(len(line) for line in empathy_lines)
    
    def _assess_content_quality(self, content: str, section_name: str) -> List[str]:
        """Assess generated content quality"""
        flags = []
        
        # Length checks
        if len(content) < 50:
            flags.append("very_short_content")
        elif len(content) > 1000:
            flags.append("very_long_content")
        
        # Content quality checks
        if '[' in content and ']' in content:
            flags.append("placeholder_remnants")
        
        if content.count('.') < 2:
            flags.append("insufficient_detail")
        
        # Empathy presence check
        empathy_indicators = ['job seeker', 'career', 'opportunity', 'professional', 'position']
        if not any(indicator in content.lower() for indicator in empathy_indicators):
            flags.append("low_empathy_context")
        
        return flags
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generation performance"""
        if not self.generation_history:
            return {"status": "no_generations_yet"}
        
        total_generations = len(self.generation_history)
        avg_time = sum(g['metrics'].generation_time_ms for g in self.generation_history) / total_generations
        avg_tokens = sum(g['metrics'].actual_tokens_generated for g in self.generation_history) / total_generations
        
        all_flags = []
        for g in self.generation_history:
            all_flags.extend(g['metrics'].quality_flags)
        
        return {
            "total_generations": total_generations,
            "average_time_ms": round(avg_time, 2),
            "average_tokens": round(avg_tokens, 1),
            "model_used": self.model_name,
            "quality_flags_summary": dict(Counter(all_flags)) if all_flags else {},
            "model_available": self.model_available
        }
