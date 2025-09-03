#!/usr/bin/env python3
"""
Quality Assessor Module
======================

Comprehensive quality assessment for LLM responses across different test types.
Provides detailed metrics and scoring for response quality evaluation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class QualityDimension(Enum):
    """Different dimensions of quality assessment"""
    STRUCTURE = "structure"
    CONTENT = "content"
    FORMAT = "format"
    LENGTH = "length"
    COMPLETENESS = "completeness"


@dataclass
class QualityScore:
    """Comprehensive quality scoring result"""
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    has_structure: bool
    contains_keywords: bool
    follows_format: bool
    appropriate_length: bool
    completeness_score: float
    detailed_feedback: List[str]


class QualityAssessor:
    """Assess the quality of LLM responses across different test types"""
    
    def __init__(self, custom_criteria: Optional[Dict[str, Dict]] = None):
        """
        Initialize quality assessor with optional custom criteria
        
        Args:
            custom_criteria: Custom assessment criteria for specific test types
        """
        self.criteria = custom_criteria or {}
        self.default_weights = {
            QualityDimension.STRUCTURE: 0.25,
            QualityDimension.CONTENT: 0.30,
            QualityDimension.FORMAT: 0.20,
            QualityDimension.LENGTH: 0.15,
            QualityDimension.COMPLETENESS: 0.10
        }
    
    def assess_quality(self, response_text: str, test_id: str, 
                      custom_weights: Optional[Dict[QualityDimension, float]] = None) -> QualityScore:
        """
        Comprehensive quality assessment of a response
        
        Args:
            response_text: The model's response text
            test_id: Type of test (e.g., "concise_extraction")
            custom_weights: Optional custom weights for quality dimensions
            
        Returns:
            QualityScore object with detailed assessment
        """
        weights = custom_weights or self.default_weights
        
        # Assess each dimension
        structure_score = self._assess_structure(response_text, test_id)
        content_score = self._assess_content(response_text, test_id)
        format_score = self._assess_format(response_text, test_id)
        length_score = self._assess_length(response_text, test_id)
        completeness_score = self._assess_completeness(response_text, test_id)
        
        dimension_scores = {
            QualityDimension.STRUCTURE: structure_score,
            QualityDimension.CONTENT: content_score,
            QualityDimension.FORMAT: format_score,
            QualityDimension.LENGTH: length_score,
            QualityDimension.COMPLETENESS: completeness_score
        }
        
        # Calculate weighted overall score
        overall_score = sum(
            dimension_scores[dim] * weights.get(dim, 0.2)
            for dim in dimension_scores
        )
        
        # Boolean assessments
        has_structure = structure_score > 0.5
        contains_keywords = content_score > 0.5
        follows_format = format_score > 0.7
        appropriate_length = length_score > 0.5
        
        # Generate detailed feedback
        feedback = self._generate_feedback(response_text, test_id, dimension_scores)
        
        return QualityScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            has_structure=has_structure,
            contains_keywords=contains_keywords,
            follows_format=follows_format,
            appropriate_length=appropriate_length,
            completeness_score=completeness_score,
            detailed_feedback=feedback
        )
    
    def _assess_structure(self, response_text: str, test_id: str) -> float:
        """Assess structural quality of the response"""
        text_lower = response_text.lower()
        score = 0.0
        
        if test_id == "concise_extraction":
            # Look for clear section headers
            structure_markers = [
                "your tasks", "your profile", "tasks:", "profile:",
                "responsibilities", "requirements", "**your tasks**", 
                "**your profile**", "## your", "# your"
            ]
            marker_count = sum(1 for marker in structure_markers if marker in text_lower)
            score = min(marker_count / 2.0, 1.0)  # Expect at least 2 sections
            
        elif test_id == "requirements_focus":
            # Should avoid company benefits, focus on requirements
            negative_markers = [
                "we offer", "company benefits", "kultur", "emotional ausgeglichen",
                "körperlich fit", "finanziell abgesichert"
            ]
            positive_markers = ["requirements", "qualifications", "experience", "skills"]
            
            negative_count = sum(1 for marker in negative_markers if marker in text_lower)
            positive_count = sum(1 for marker in positive_markers if marker in text_lower)
            
            score = max(0, (positive_count - negative_count * 0.5) / 3.0)
            score = min(score, 1.0)
            
        elif test_id == "structured_analysis":
            # Check for proper section structure
            required_sections = ["=== TECHNICAL REQUIREMENTS ===", "=== BUSINESS REQUIREMENTS ==="]
            section_count = sum(1 for section in required_sections if section in response_text)
            
            total_sections = response_text.count("===")
            structure_score = section_count / len(required_sections)
            organization_score = min(total_sections / 4.0, 1.0)  # Expect some organization
            
            score = (structure_score * 0.7 + organization_score * 0.3)
            
        elif test_id == "skills_categorization":
            # Check for skill categorization structure
            required_sections = ["=== SOFT SKILLS ===", "=== EXPERIENCE REQUIRED ===", "=== EDUCATION REQUIRED ==="]
            section_count = sum(1 for section in required_sections if section in response_text)
            
            score = section_count / len(required_sections)
        
        return min(score, 1.0)
    
    def _assess_content(self, response_text: str, test_id: str) -> float:
        """Assess content quality and keyword coverage"""
        text_lower = response_text.lower()
        
        # Define key terms for each test type
        key_terms = {
            "concise_extraction": [
                "experience", "skills", "knowledge", "ability", "degree",
                "coordination", "management", "audit", "compliance", "security"
            ],
            "requirements_focus": [
                "requirement", "skill", "experience", "knowledge", "degree",
                "certification", "bachelor", "master", "education", "technical"
            ],
            "structured_analysis": [
                "critical", "important", "nice-to-have", "technical", "business",
                "requirement", "skill", "knowledge", "endpoint", "security"
            ],
            "skills_categorization": [
                "communication", "leadership", "experience", "education", "degree",
                "teamwork", "collaboration", "management", "analytical", "soft skills"
            ]
        }
        
        relevant_terms = key_terms.get(test_id, [])
        if not relevant_terms:
            return 0.5  # Default score for unknown test types
        
        found_terms = sum(1 for term in relevant_terms if term in text_lower)
        coverage_score = found_terms / len(relevant_terms)
        
        # Bonus for comprehensive coverage
        if coverage_score > 0.8:
            coverage_score = min(coverage_score * 1.1, 1.0)
        
        return coverage_score
    
    def _assess_format(self, response_text: str, test_id: str) -> float:
        """Assess format adherence"""
        if test_id == "structured_analysis":
            has_tech = "=== TECHNICAL REQUIREMENTS ===" in response_text
            has_business = "=== BUSINESS REQUIREMENTS ===" in response_text
            return 1.0 if (has_tech and has_business) else 0.3
            
        elif test_id == "skills_categorization":
            has_soft = "=== SOFT SKILLS ===" in response_text
            has_exp = "=== EXPERIENCE REQUIRED ===" in response_text or "=== EDUCATION REQUIRED ===" in response_text
            return 1.0 if (has_soft and has_exp) else 0.3
            
        elif test_id == "concise_extraction":
            has_tasks = "your tasks" in response_text.lower()
            has_profile = "your profile" in response_text.lower()
            return 1.0 if (has_tasks and has_profile) else 0.5
            
        else:
            # General format assessment
            has_structure = any(marker in response_text for marker in ["###", "**", "===", "##"])
            return 0.7 if has_structure else 0.3
    
    def _assess_length(self, response_text: str, test_id: str) -> float:
        """Assess response length appropriateness"""
        length = len(response_text)
        
        # Define optimal length ranges for each test type
        length_ranges = {
            "concise_extraction": (800, 3000),
            "requirements_focus": (400, 1500),
            "structured_analysis": (300, 1000),
            "skills_categorization": (500, 2000)
        }
        
        min_len, max_len = length_ranges.get(test_id, (100, 5000))
        
        if length < min_len:
            return length / min_len  # Linear penalty for too short
        elif length > max_len:
            return max(0.3, 1.0 - (length - max_len) / max_len)  # Penalty for too long
        else:
            return 1.0  # Perfect length
    
    def _assess_completeness(self, response_text: str, test_id: str) -> float:
        """Assess completeness of the response"""
        # Check for common completeness indicators
        text_lower = response_text.lower()
        
        # Penalize incomplete responses
        incomplete_indicators = ["...", "truncated", "continues", "etc.", "and more"]
        incomplete_count = sum(1 for indicator in incomplete_indicators if indicator in text_lower)
        
        # Reward comprehensive responses
        comprehensive_indicators = {
            "concise_extraction": ["tasks", "profile", "responsibilities", "requirements"],
            "requirements_focus": ["education", "experience", "skills", "qualifications"],
            "structured_analysis": ["technical", "business", "critical", "important"],
            "skills_categorization": ["soft skills", "experience", "education"]
        }
        
        expected_elements = comprehensive_indicators.get(test_id, [])
        found_elements = sum(1 for element in expected_elements if element in text_lower)
        
        completeness = found_elements / max(len(expected_elements), 1)
        completeness -= incomplete_count * 0.1  # Penalty for incomplete indicators
        
        return max(0.0, min(1.0, completeness))
    
    def _generate_feedback(self, response_text: str, test_id: str, 
                          dimension_scores: Dict[QualityDimension, float]) -> List[str]:
        """Generate detailed feedback for the response"""
        feedback = []
        
        # Structure feedback
        structure_score = dimension_scores[QualityDimension.STRUCTURE]
        if structure_score < 0.5:
            feedback.append(f"⚠️ Poor structure (score: {structure_score:.2f}) - Missing expected sections or organization")
        elif structure_score > 0.8:
            feedback.append(f"✅ Excellent structure (score: {structure_score:.2f})")
        
        # Content feedback
        content_score = dimension_scores[QualityDimension.CONTENT]
        if content_score < 0.5:
            feedback.append(f"⚠️ Insufficient key terms (score: {content_score:.2f}) - Missing important domain-specific content")
        elif content_score > 0.8:
            feedback.append(f"✅ Comprehensive content coverage (score: {content_score:.2f})")
        
        # Format feedback
        format_score = dimension_scores[QualityDimension.FORMAT]
        if format_score < 0.5:
            feedback.append(f"❌ Format issues (score: {format_score:.2f}) - Does not follow expected format")
        elif format_score > 0.8:
            feedback.append(f"✅ Perfect format adherence (score: {format_score:.2f})")
        
        # Length feedback
        length_score = dimension_scores[QualityDimension.LENGTH]
        length = len(response_text)
        if length_score < 0.5:
            feedback.append(f"⚠️ Length issues (score: {length_score:.2f}) - Response is {length} characters")
        
        return feedback


class AdvancedQualityAssessor(QualityAssessor):
    """Extended quality assessor with additional metrics"""
    
    def assess_with_context(self, response_text: str, test_id: str, 
                           context: Dict[str, Any]) -> QualityScore:
        """Assess quality with additional context information"""
        base_score = self.assess_quality(response_text, test_id)
        
        # Add context-specific adjustments
        if "domain" in context:
            base_score = self._adjust_for_domain(base_score, context["domain"])
        
        if "baseline_response" in context:
            base_score = self._adjust_for_baseline_similarity(
                base_score, response_text, context["baseline_response"]
            )
        
        return base_score
    
    def _adjust_for_domain(self, score: QualityScore, domain: str) -> QualityScore:
        """Adjust score based on domain-specific requirements"""
        # Domain-specific adjustments can be implemented here
        return score
    
    def _adjust_for_baseline_similarity(self, score: QualityScore, 
                                      response: str, baseline: str) -> QualityScore:
        """Adjust score based on similarity to baseline response"""
        # Baseline similarity adjustments can be implemented here
        return score
