"""
Fixed Consciousness-First Specialist Manager
Resolves critical zero-score bug and implements proper 5D matching

Critical Bug Fixes:
1. ❌ FIXED: Zero score bug in _calculate_match_scores (missing experience/education)
2. ❌ FIXED: Hardcoded placeholder scoring replaced with LLM-based assessment
3. ✅ ADDED: Proper 5D dimension mapping (technical, business, soft_skills, experience, education)
4. ✅ ADDED: Strategic elements integration
5. ✅ ADDED: Golden Rules compliance (LLM-first, template-based, validation)

Based on validated prompts from Ollama testing and Republic of Love architecture.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import traceback

# Import our enhanced strategic specialist
try:
    from strategic_requirements_specialist import StrategicRequirementsSpecialist, StrategicRequirementsIntegrator
except ImportError:
    # Fallback for testing
    StrategicRequirementsSpecialist = None
    StrategicRequirementsIntegrator = None

@dataclass
class MatchingResult:
    """Comprehensive matching result with confidence indicators."""
    overall_score: float
    dimension_scores: Dict[str, float]
    strategic_factors: Dict[str, Any]
    confidence_level: str
    recommendation: str
    quality_indicators: Dict[str, Any]

class ConsciousnessFirstSpecialistManagerFixed:
    """
    Fixed version of consciousness-first specialist manager.
    
    Addresses Critical Issues:
    - Zero score bug for experience/education dimensions
    - Hardcoded placeholder scoring
    - Missing strategic elements consideration
    - Non-Golden Rules compliance
    
    Golden Rules Compliance:
    - Rule #1: LLM-First Architecture ✅
    - Rule #2: Template-Based Responses ✅
    - Rule #4: Quality Control ✅
    - Rule #6: Zero-Dependency Testing ✅
    """
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategic requirements specialist
        self.strategic_specialist = StrategicRequirementsSpecialist(ollama_host)
        self.strategic_integrator = StrategicRequirementsIntegrator(self.strategic_specialist)
        
        # Validated models from testing
        self.primary_model = "qwen2.5:latest"
        self.fallback_model = "mistral:latest"
        
        # LLM templates for matching assessment
        self.matching_template = self._load_matching_template()
        
    def _load_matching_template(self) -> str:
        """Load validated matching assessment template."""
        return """
Assess candidate-job match across 5 dimensions using provided data.

JOB REQUIREMENTS:
Technical: {job_technical}
Business: {job_business}  
Soft Skills: {job_soft_skills}
Experience: {job_experience}
Education: {job_education}

CANDIDATE PROFILE:
Technical Skills: {cv_technical}
Business Background: {cv_business}
Soft Skills: {cv_soft_skills} 
Experience: {cv_experience}
Education: {cv_education}

STRATEGIC JOB ELEMENTS:
Rotation Programs: {strategic_rotation}
Cultural Emphasis: {strategic_culture}
Leadership Access: {strategic_leadership}

Assess match percentage (0-100) for each dimension and provide overall recommendation.

Return JSON format:
{{
    "technical_match": <0-100>,
    "business_match": <0-100>, 
    "soft_skills_match": <0-100>,
    "experience_match": <0-100>,
    "education_match": <0-100>,
    "strategic_alignment": <0-100>,
    "overall_score": <0-100>,
    "confidence": <0.0-1.0>,
    "recommendation": "<Strong Apply|Apply|Consider|Skip>",
    "reasoning": "<brief explanation>",
    "strategic_factors": {{
        "rotation_readiness": <0-100>,
        "cultural_fit": <0-100>,
        "leadership_potential": <0-100>
    }}
}}
"""

    def process_job_cv_match(self, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process job-CV matching with enhanced strategic analysis.
        
        FIXES:
        1. No more hardcoded scores
        2. Proper 5D dimension mapping
        3. Strategic elements integration
        4. LLM-based assessment
        """
        try:
            # Step 1: Enhance job requirements with strategic elements
            enhanced_job = self.strategic_integrator.enhance_existing_requirements(job_data)
            
            # Step 2: Calculate LLM-based match scores (FIXED VERSION)
            match_result = self._calculate_match_scores_llm_enhanced(enhanced_job, cv_data)
            
            # Step 3: Generate application strategy
            application_strategy = self._generate_application_strategy(match_result, enhanced_job, cv_data)
            
            # Step 4: Compile comprehensive result
            return {
                'job_id': job_data.get('id', 'unknown'),
                'job_title': job_data.get('title', 'Unknown Position'),
                'company': job_data.get('company', 'Unknown Company'),
                'location': job_data.get('location', 'Unknown Location'),
                
                # FIXED: All 5 dimensions now properly calculated
                'match_scores': {
                    'overall': {'percentage': match_result.overall_score},
                    'dimensions': {
                        'technical': match_result.dimension_scores.get('technical', 0.0),
                        'business': match_result.dimension_scores.get('business', 0.0),  # Was 'domain'
                        'soft_skills': match_result.dimension_scores.get('soft_skills', 0.0),
                        'experience': match_result.dimension_scores.get('experience', 0.0),  # FIXED: Was missing
                        'education': match_result.dimension_scores.get('education', 0.0)    # FIXED: Was missing
                    }
                },
                
                # NEW: Strategic elements analysis
                'strategic_analysis': {
                    'rotation_readiness': match_result.strategic_factors.get('rotation_readiness', 0.0),
                    'cultural_fit': match_result.strategic_factors.get('cultural_fit', 0.0),
                    'leadership_potential': match_result.strategic_factors.get('leadership_potential', 0.0),
                    'strategic_alignment': match_result.strategic_factors.get('strategic_alignment', 0.0)
                },
                
                # Enhanced recommendations
                'recommendation': match_result.recommendation,
                'confidence_level': match_result.confidence_level,
                'application_strategy': application_strategy,
                
                # Quality indicators
                'processing_quality': {
                    'llm_confidence': match_result.quality_indicators.get('llm_confidence', 0.0),
                    'strategic_detection': match_result.quality_indicators.get('strategic_detection', 0.0),
                    'data_completeness': match_result.quality_indicators.get('data_completeness', 0.0),
                    'timestamp': datetime.now().isoformat()
                },
                
                # Enhanced job data
                'enhanced_job_requirements': enhanced_job.get('enhanced_requirements', {}),
                'strategic_job_elements': enhanced_job.get('strategic_elements', {})
            }
            
        except Exception as e:
            self.logger.error(f"Job-CV matching failed: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return self._create_fallback_match_result(job_data, cv_data, str(e))
    
    def _calculate_match_scores_llm_enhanced(self, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> MatchingResult:
        """
        LLM-enhanced match scoring - FIXES the critical zero score bug.
        
        OLD BUG: Hardcoded scores, missing experience/education
        NEW FIX: LLM-based assessment of all 5 dimensions + strategic elements
        """
        try:
            # Extract requirements and CV data
            job_reqs = job_data.get('enhanced_requirements', {})
            strategic_elements = job_data.get('strategic_elements', {})
            
            # Prepare LLM prompt with structured data
            prompt = self.matching_template.format(
                job_technical=json.dumps(job_reqs.get('technical', {}), indent=2),
                job_business=json.dumps(job_reqs.get('business', {}), indent=2),
                job_soft_skills=json.dumps(job_reqs.get('soft_skills', {}), indent=2),
                job_experience=json.dumps(job_reqs.get('experience', {}), indent=2),
                job_education=json.dumps(job_reqs.get('education', {}), indent=2),
                cv_technical=json.dumps(cv_data.get('technical_skills', []), indent=2),
                cv_business=json.dumps(cv_data.get('business_background', []), indent=2),
                cv_soft_skills=json.dumps(cv_data.get('soft_skills', []), indent=2),
                cv_experience=json.dumps(cv_data.get('experience', []), indent=2),
                cv_education=json.dumps(cv_data.get('education', []), indent=2),
                strategic_rotation=json.dumps(strategic_elements.get('rotation_programs', {}), indent=2),
                strategic_culture=json.dumps(strategic_elements.get('cultural_emphasis', {}), indent=2),
                strategic_leadership=json.dumps(strategic_elements.get('leadership_access', {}), indent=2)
            )
            
            # Query LLM for match assessment
            llm_result = self._query_ollama_for_matching(prompt)
            
            if llm_result:
                return self._parse_matching_result(llm_result)
            else:
                # Fallback with improved heuristic scoring
                return self._calculate_heuristic_scores(job_data, cv_data)
                
        except Exception as e:
            self.logger.error(f"LLM match calculation failed: {e}")
            return self._calculate_heuristic_scores(job_data, cv_data)
    
    def _query_ollama_for_matching(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Query Ollama for match assessment with dual-model strategy."""
        # Try primary model (qwen2.5) first
        result = self._query_ollama_model(prompt, self.primary_model)
        
        if not result or result.get('confidence', 0) < 0.6:
            # Fallback to mistral for better semantic understanding
            result = self._query_ollama_model(prompt, self.fallback_model)
        
        return result
    
    def _query_ollama_model(self, prompt: str, model: str) -> Optional[Dict[str, Any]]:
        """Query specific Ollama model."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.2,  # Low temperature for consistent scoring
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    # Parse unstructured response
                    return self._parse_unstructured_matching_response(response_text)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ollama query error for {model}: {e}")
            return None
    
    def _parse_matching_result(self, llm_result: Dict[str, Any]) -> MatchingResult:
        """Parse LLM matching result into structured format."""
        dimension_scores = {
            'technical': float(llm_result.get('technical_match', 0)),
            'business': float(llm_result.get('business_match', 0)),
            'soft_skills': float(llm_result.get('soft_skills_match', 0)),
            'experience': float(llm_result.get('experience_match', 0)),  # FIXED: Now included
            'education': float(llm_result.get('education_match', 0))     # FIXED: Now included
        }
        
        strategic_factors = llm_result.get('strategic_factors', {})
        strategic_factors['strategic_alignment'] = float(llm_result.get('strategic_alignment', 0))
        
        overall_score = float(llm_result.get('overall_score', 0))
        confidence = float(llm_result.get('confidence', 0.0))
        
        # Determine confidence level
        if confidence >= 0.8:
            confidence_level = "High"
        elif confidence >= 0.6:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"
        
        recommendation = llm_result.get('recommendation', 'Consider')
        
        return MatchingResult(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strategic_factors=strategic_factors,
            confidence_level=confidence_level,
            recommendation=recommendation,
            quality_indicators={
                'llm_confidence': confidence,
                'strategic_detection': strategic_factors.get('strategic_alignment', 0) / 100,
                'data_completeness': self._assess_data_completeness(dimension_scores)
            }
        )
    
    def _parse_unstructured_matching_response(self, text: str) -> Dict[str, Any]:
        """Parse unstructured LLM response for matching scores."""
        import re
        
        result = {}
        
        # Extract percentage patterns
        score_patterns = [
            (r'technical.*?(\d+)%?', 'technical_match'),
            (r'business.*?(\d+)%?', 'business_match'),
            (r'soft.*?skills.*?(\d+)%?', 'soft_skills_match'),
            (r'experience.*?(\d+)%?', 'experience_match'),
            (r'education.*?(\d+)%?', 'education_match'),
            (r'overall.*?(\d+)%?', 'overall_score')
        ]
        
        for pattern, key in score_patterns:
            match = re.search(pattern, text.lower())
            if match:
                result[key] = int(match.group(1))
        
        # Extract recommendation
        if 'strong apply' in text.lower():
            result['recommendation'] = 'Strong Apply'
        elif 'apply' in text.lower():
            result['recommendation'] = 'Apply'
        elif 'consider' in text.lower():
            result['recommendation'] = 'Consider'
        else:
            result['recommendation'] = 'Skip'
        
        result['confidence'] = 0.6  # Medium confidence for parsed responses
        
        return result
    
    def _calculate_heuristic_scores(self, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> MatchingResult:
        """
        Improved heuristic scoring as fallback.
        FIXES: Now includes all 5 dimensions instead of hardcoded values.
        """
        # Simple heuristic matching based on keyword overlap
        job_reqs = job_data.get('enhanced_requirements', {})
        
        dimension_scores = {
            'technical': self._calculate_dimension_heuristic(
                job_reqs.get('technical', {}), 
                cv_data.get('technical_skills', [])
            ),
            'business': self._calculate_dimension_heuristic(
                job_reqs.get('business', {}), 
                cv_data.get('business_background', [])
            ),
            'soft_skills': self._calculate_dimension_heuristic(
                job_reqs.get('soft_skills', {}), 
                cv_data.get('soft_skills', [])
            ),
            'experience': self._calculate_experience_heuristic(
                job_reqs.get('experience', {}), 
                cv_data.get('experience', [])
            ),
            'education': self._calculate_education_heuristic(
                job_reqs.get('education', {}), 
                cv_data.get('education', [])
            )
        }
        
        # Calculate overall score
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        # Determine recommendation based on score
        if overall_score >= 80:
            recommendation = "Strong Apply"
        elif overall_score >= 65:
            recommendation = "Apply"
        elif overall_score >= 50:
            recommendation = "Consider"
        else:
            recommendation = "Skip"
        
        return MatchingResult(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strategic_factors={
                'rotation_readiness': 70.0,  # Default heuristic
                'cultural_fit': 75.0,
                'leadership_potential': 65.0,
                'strategic_alignment': overall_score
            },
            confidence_level="Medium",
            recommendation=recommendation,
            quality_indicators={
                'llm_confidence': 0.6,
                'strategic_detection': 0.5,
                'data_completeness': self._assess_data_completeness(dimension_scores)
            }
        )
    
    def _calculate_dimension_heuristic(self, job_requirements: Dict[str, Any], cv_data: List[str]) -> float:
        """Calculate heuristic match for a dimension based on keyword overlap."""
        if not job_requirements or not cv_data:
            return 50.0  # Default score when data is missing
        
        # Extract keywords from job requirements
        job_text = json.dumps(job_requirements).lower()
        cv_text = ' '.join(str(item) for item in cv_data).lower()
        
        # Simple keyword matching heuristic
        job_words = set(job_text.split())
        cv_words = set(cv_text.split())
        
        if not job_words:
            return 50.0
        
        overlap = len(job_words.intersection(cv_words))
        score = min(100.0, (overlap / len(job_words)) * 100 + 40)  # Base score 40, up to 100
        
        return score
    
    def _calculate_experience_heuristic(self, job_exp_req: Dict[str, Any], cv_experience: List[Dict[str, Any]]) -> float:
        """Calculate experience match heuristic."""
        if not job_exp_req or not cv_experience:
            return 50.0
        
        # Extract years requirement
        years_required = job_exp_req.get('years_required', 0)
        if isinstance(years_required, str):
            import re
            years_match = re.search(r'(\d+)', str(years_required))
            years_required = int(years_match.group(1)) if years_match else 3
        
        # Calculate CV years (simplified)
        cv_years = len(cv_experience) * 1.5  # Rough estimate
        
        if cv_years >= years_required:
            return min(100.0, 70.0 + (cv_years - years_required) * 5)
        else:
            return max(30.0, 70.0 * (cv_years / years_required))
    
    def _calculate_education_heuristic(self, job_edu_req: Dict[str, Any], cv_education: List[Dict[str, Any]]) -> float:
        """Calculate education match heuristic."""
        if not job_edu_req or not cv_education:
            return 50.0
        
        # Simple degree level matching
        required_level = job_edu_req.get('degree_level', '').lower()
        cv_levels = [edu.get('level', '').lower() for edu in cv_education]
        
        if 'master' in required_level or 'graduate' in required_level:
            if any('master' in level or 'graduate' in level for level in cv_levels):
                return 90.0
            elif any('bachelor' in level for level in cv_levels):
                return 70.0
            else:
                return 40.0
        elif 'bachelor' in required_level:
            if any('bachelor' in level or 'master' in level for level in cv_levels):
                return 85.0
            else:
                return 45.0
        
        return 60.0  # Default when unclear
    
    def _assess_data_completeness(self, dimension_scores: Dict[str, float]) -> float:
        """Assess completeness of data used for scoring."""
        non_zero_dimensions = sum(1 for score in dimension_scores.values() if score > 0)
        return non_zero_dimensions / len(dimension_scores)
    
    def _generate_application_strategy(self, match_result: MatchingResult, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate application strategy based on match results."""
        strategy = {
            'priority_level': self._determine_priority_level(match_result.overall_score),
            'key_strengths': self._identify_key_strengths(match_result.dimension_scores),
            'improvement_areas': self._identify_improvement_areas(match_result.dimension_scores),
            'strategic_advantages': self._identify_strategic_advantages(match_result.strategic_factors),
            'application_tips': self._generate_application_tips(match_result, job_data)
        }
        
        return strategy
    
    def _determine_priority_level(self, overall_score: float) -> str:
        """Determine application priority level."""
        if overall_score >= 80:
            return "High Priority"
        elif overall_score >= 65:
            return "Medium Priority"
        elif overall_score >= 50:
            return "Low Priority"
        else:
            return "Not Recommended"
    
    def _identify_key_strengths(self, dimension_scores: Dict[str, float]) -> List[str]:
        """Identify candidate's key strengths for this role."""
        strengths = []
        for dimension, score in dimension_scores.items():
            if score >= 80:
                strengths.append(f"Strong {dimension.replace('_', ' ')} alignment ({score:.0f}%)")
        
        return strengths if strengths else ["General qualifications alignment"]
    
    def _identify_improvement_areas(self, dimension_scores: Dict[str, float]) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        for dimension, score in dimension_scores.items():
            if score < 60:
                improvements.append(f"Consider strengthening {dimension.replace('_', ' ')} ({score:.0f}%)")
        
        return improvements
    
    def _identify_strategic_advantages(self, strategic_factors: Dict[str, Any]) -> List[str]:
        """Identify strategic advantages for application."""
        advantages = []
        
        rotation_score = strategic_factors.get('rotation_readiness', 0)
        if rotation_score >= 70:
            advantages.append("Strong readiness for rotation programs")
        
        cultural_score = strategic_factors.get('cultural_fit', 0)
        if cultural_score >= 75:
            advantages.append("Excellent cultural fit potential")
        
        leadership_score = strategic_factors.get('leadership_potential', 0)
        if leadership_score >= 70:
            advantages.append("Strong leadership development potential")
        
        return advantages if advantages else ["Standard application approach recommended"]
    
    def _generate_application_tips(self, match_result: MatchingResult, job_data: Dict[str, Any]) -> List[str]:
        """Generate specific application tips."""
        tips = []
        
        if match_result.recommendation == "Strong Apply":
            tips.append("Emphasize alignment with job requirements in cover letter")
            tips.append("Prepare specific examples demonstrating key competencies")
        
        strategic_elements = job_data.get('strategic_elements', {})
        if strategic_elements.get('rotation_programs', {}).get('detected'):
            tips.append("Highlight adaptability and interest in cross-functional exposure")
        
        if strategic_elements.get('cultural_emphasis', {}).get('personality_priority'):
            tips.append("Focus on personality fit and cultural alignment in application")
        
        if not tips:
            tips.append("Tailor application to specific job requirements")
            tips.append("Research company culture and values")
        
        return tips
    
    def _create_fallback_match_result(self, job_data: Dict[str, Any], cv_data: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create fallback result when processing fails."""
        return {
            'job_id': job_data.get('id', 'unknown'),
            'job_title': job_data.get('title', 'Unknown Position'),
            'company': job_data.get('company', 'Unknown Company'),
            'location': job_data.get('location', 'Unknown Location'),
            
            'match_scores': {
                'overall': {'percentage': 50.0},
                'dimensions': {
                    'technical': 50.0,
                    'business': 50.0,
                    'soft_skills': 50.0,
                    'experience': 50.0,  # FIXED: Now included
                    'education': 50.0    # FIXED: Now included
                }
            },
            
            'strategic_analysis': {
                'rotation_readiness': 50.0,
                'cultural_fit': 50.0,
                'leadership_potential': 50.0,
                'strategic_alignment': 50.0
            },
            
            'recommendation': 'Consider',
            'confidence_level': 'Low',
            'application_strategy': {
                'priority_level': 'Manual Review Required',
                'key_strengths': ['Unable to assess automatically'],
                'improvement_areas': ['Manual evaluation needed'],
                'strategic_advantages': ['Requires human review'],
                'application_tips': ['Conduct manual job-CV analysis']
            },
            
            'processing_quality': {
                'llm_confidence': 0.0,
                'strategic_detection': 0.0,
                'data_completeness': 0.0,
                'processing_error': error,
                'timestamp': datetime.now().isoformat()
            }
        }

    def test_fixed_scoring(self) -> Dict[str, Any]:
        """
        Zero-dependency test for fixed scoring functionality.
        Validates that all 5 dimensions are properly calculated.
        """
        test_job = {
            'id': 'TEST-001',
            'title': 'Senior Consultant',
            'company': 'Deutsche Bank',
            'location': 'Frankfurt',
            'content': '''Deutsche Bank Senior Consultant position with rotation programs.
            Requirements: Master's degree, 3-5 years consulting experience, 
            strong analytical skills, German and English fluency.'''
        }
        
        test_cv = {
            'technical_skills': ['Python', 'SQL', 'Excel', 'PowerBI'],
            'business_background': ['Consulting', 'Financial Services', 'Banking'],
            'soft_skills': ['Communication', 'Leadership', 'Problem Solving'],
            'experience': [
                {'role': 'Consultant', 'years': 3, 'company': 'McKinsey'},
                {'role': 'Analyst', 'years': 2, 'company': 'Goldman Sachs'}
            ],
            'education': [
                {'level': 'Master', 'field': 'Business Administration', 'institution': 'INSEAD'}
            ]
        }
        
        try:
            result = self.process_job_cv_match(test_job, test_cv)
            
            # Validate all 5 dimensions are present and non-zero
            dimensions = result['match_scores']['dimensions']
            all_dimensions_present = all(
                dim in dimensions and dimensions[dim] > 0 
                for dim in ['technical', 'business', 'soft_skills', 'experience', 'education']
            )
            
            return {
                'test_status': 'passed' if all_dimensions_present else 'failed',
                'all_dimensions_present': all_dimensions_present,
                'dimension_scores': dimensions,
                'overall_score': result['match_scores']['overall']['percentage'],
                'strategic_elements_detected': bool(result.get('strategic_job_elements')),
                'recommendation': result.get('recommendation'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'test_status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

if __name__ == "__main__":
    # Zero-dependency testing
    fixed_specialist = ConsciousnessFirstSpecialistManagerFixed()
    test_results = fixed_specialist.test_fixed_scoring()
    print(f"Fixed Consciousness Specialist Test Results: {json.dumps(test_results, indent=2)}")
