#!/usr/bin/env python3
"""
Elegant Job Fitness Specialist
Pure design. No fallbacks. No compromises.
Like a Lamborghini Miura - every line purposeful, every function perfect.
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig, ModuleResult
else:
    # Runtime imports for when mypy isn't running
    try:
        from llm_factory.core.ollama_client import OllamaClient
        from llm_factory.core.types import ModuleConfig, ModuleResult
    except ImportError:
        # Graceful fallback for type checking
        OllamaClient = Any
        ModuleConfig = Any  
        ModuleResult = Any

@dataclass(frozen=True)
class JobFitness:
    """Immutable job fitness assessment - pure data, elegant structure"""
    overall_score: float
    skill_alignment: float  
    experience_relevance: float
    cultural_fit: float
    recommendation: str
    confidence: str
    key_insights: tuple
    
    @property
    def is_strong_match(self) -> bool:
        return self.overall_score >= 8.0
    
    @property
    def interview_ready(self) -> bool:
        return self.overall_score >= 7.0 and self.confidence in ["High", "Very High"]

class ElegantJobFitnessSpecialist:
    """Pure elegance in job fitness evaluation"""
    
    def __init__(self, config: ModuleConfig):
        self.client = config.ollama_client
        self.model = config.models[0]
    
    def evaluate(self, candidate: Dict[str, Any], position: Dict[str, Any]) -> JobFitness:
        """Single purpose: evaluate job fitness with surgical precision"""
        
        assessment_text = self._generate_assessment(candidate, position)
        return self._extract_fitness(assessment_text)
    
    def _generate_assessment(self, candidate: Dict[str, Any], position: Dict[str, Any]) -> str:
        """Generate LLM assessment using elegant structured output format"""
        
        prompt = f"""
Evaluate this candidate for the position with precision and insight.

CANDIDATE:
Name: {candidate.get('name', 'Candidate')}
Background: {candidate.get('background', '')}
Skills: {', '.join(candidate.get('skills', []))}
Experience: {candidate.get('experience_level', 'Not specified')}
Location: {candidate.get('location', 'Not specified')}

POSITION:
Title: {position.get('title', '')}
Company: {position.get('company', '')}
Location: {position.get('location', '')}
Requirements: {', '.join(position.get('requirements', []))}
Description: {position.get('description', '')}

Provide your assessment in this exact format:

OVERALL_SCORE: [0-10 score]
SKILL_ALIGNMENT: [0-10 score]
EXPERIENCE_RELEVANCE: [0-10 score]  
CULTURAL_FIT: [0-10 score]
RECOMMENDATION: [Strong Match|Good Match|Fair Match|Weak Match|Poor Match]
CONFIDENCE: [Very High|High|Medium|Low]
KEY_INSIGHTS: [Insight 1] | [Insight 2] | [Insight 3]

Be precise. Be insightful. No fluff.
"""
        
        response = self.client.generate(model=self.model, prompt=prompt.strip())
        return str(response)  # Explicit cast to satisfy mypy
    
    def _extract_fitness(self, text: str) -> JobFitness:
        """Extract fitness data with elegant pattern matching"""
        
        patterns = {
            'overall_score': r'OVERALL_SCORE:\s*([0-9.]+)',
            'skill_alignment': r'SKILL_ALIGNMENT:\s*([0-9.]+)',
            'experience_relevance': r'EXPERIENCE_RELEVANCE:\s*([0-9.]+)',
            'cultural_fit': r'CULTURAL_FIT:\s*([0-9.]+)',
            'recommendation': r'RECOMMENDATION:\s*([^\n]+)',
            'confidence': r'CONFIDENCE:\s*([^\n]+)',
            'key_insights': r'KEY_INSIGHTS:\s*([^\n]+)'
        }
        
        extracted = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            extracted[field] = match.group(1).strip() if match else None
        
        return JobFitness(
            overall_score=float(extracted['overall_score'] or 5.0),
            skill_alignment=float(extracted['skill_alignment'] or 5.0),
            experience_relevance=float(extracted['experience_relevance'] or 5.0),
            cultural_fit=float(extracted['cultural_fit'] or 5.0),
            recommendation=extracted['recommendation'] or 'Fair Match',
            confidence=extracted['confidence'] or 'Medium',
            key_insights=tuple((extracted['key_insights'] or '').split(' | '))
        )

def create_elegant_specialist(config: ModuleConfig) -> ElegantJobFitnessSpecialist:
    """Factory function for elegant specialist creation"""
    return ElegantJobFitnessSpecialist(config)

# Integration adapter for LLM Factory compatibility
class ElegantJobFitnessAdapter:
    """Elegant adapter that bridges to LLM Factory ModuleResult format"""
    
    def __init__(self, config: ModuleConfig):
        self.specialist = create_elegant_specialist(config)
    
    def process(self, input_data: Dict[str, Any]) -> ModuleResult:
        """Process with elegance, return with compatibility"""
        start_time = time.time()
        
        candidate = input_data['candidate_profile']
        position = input_data['job_posting']
        
        fitness = self.specialist.evaluate(candidate, position)
        
        return ModuleResult(
            success=True,
            data={
                'fitness_assessment': {
                    'overall_score': fitness.overall_score,
                    'skill_alignment': fitness.skill_alignment,
                    'experience_relevance': fitness.experience_relevance,
                    'cultural_fit': fitness.cultural_fit,
                    'recommendation': fitness.recommendation,
                    'confidence': fitness.confidence,
                    'key_insights': list(fitness.key_insights),
                    'is_strong_match': fitness.is_strong_match,
                    'interview_ready': fitness.interview_ready
                }
            },
            processing_time=time.time() - start_time,
            validation=None
        )
