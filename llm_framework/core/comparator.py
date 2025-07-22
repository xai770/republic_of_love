#!/usr/bin/env python3
"""
Baseline Comparator Module
==========================

Compare LLM responses against a baseline model to assess similarity and quality.
Provides detailed similarity metrics and upgrade recommendations.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from ..utils.dialogue_parser import DialogueEntry


@dataclass
class SimilarityScore:
    """Comprehensive similarity scoring between responses"""
    overall_similarity: float
    length_ratio: float
    structure_similarity: float
    key_term_coverage: float
    format_consistency: float
    verdict: str
    verdict_emoji: str
    detailed_breakdown: Dict[str, float]


@dataclass
class BaselineComparison:
    """Complete comparison result against baseline"""
    similarity_score: SimilarityScore
    performance_delta: Dict[str, float]
    upgrade_recommendation: str
    confidence_level: float
    risk_assessment: str


class BaselineComparator:
    """Compare LLM responses against a designated baseline model"""
    
    def __init__(self, baseline_model: str, similarity_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize baseline comparator
        
        Args:
            baseline_model: Name of the baseline model
            similarity_thresholds: Custom thresholds for similarity assessment
        """
        self.baseline_model = baseline_model
        self.thresholds = similarity_thresholds or {
            "excellent": 0.9,
            "good": 0.7,
            "fair": 0.5,
            "poor": 0.3
        }
        self.baseline_responses: Dict[str, str] = {}
        self.key_terms_cache: Dict[str, List[str]] = {}
    
    def set_baseline_responses(self, baseline_entries: List[DialogueEntry]):
        """
        Set baseline responses for comparison
        
        Args:
            baseline_entries: List of DialogueEntry objects from baseline model
        """
        self.baseline_responses = {
            entry.test_id: entry.response_text 
            for entry in baseline_entries
        }
        print(f"📊 Set baseline responses for {len(self.baseline_responses)} test types")
    
    def compare_to_baseline(self, model_response: str, baseline_response: str, 
                           test_id: str) -> SimilarityScore:
        """
        Compare a model response to the baseline response
        
        Args:
            model_response: The model's response to compare
            baseline_response: The baseline model's response
            test_id: Type of test being compared
            
        Returns:
            SimilarityScore object with detailed comparison
        """
        # Length comparison
        length_ratio = self._calculate_length_ratio(model_response, baseline_response)
        
        # Structure similarity
        structure_similarity = self._calculate_structure_similarity(
            model_response, baseline_response, test_id
        )
        
        # Key terms overlap
        key_term_coverage = self._calculate_key_term_coverage(
            model_response, baseline_response, test_id
        )
        
        # Format consistency
        format_consistency = self._calculate_format_consistency(
            model_response, baseline_response, test_id
        )
        
        # Calculate weighted overall similarity
        weights = self._get_similarity_weights(test_id)
        overall_similarity = (
            length_ratio * weights["length"] +
            structure_similarity * weights["structure"] +
            key_term_coverage * weights["content"] +
            format_consistency * weights["format"]
        )
        overall_similarity = min(overall_similarity, 1.0)
        
        # Determine verdict
        verdict, verdict_emoji = self._determine_verdict(overall_similarity)
        
        # Detailed breakdown
        breakdown = {
            "length_ratio": length_ratio,
            "structure_similarity": structure_similarity,
            "key_term_coverage": key_term_coverage,
            "format_consistency": format_consistency,
            "weights_applied": weights["length"]  # Just store first weight as float for type safety
        }
        
        return SimilarityScore(
            overall_similarity=overall_similarity,
            length_ratio=length_ratio,
            structure_similarity=structure_similarity,
            key_term_coverage=key_term_coverage,
            format_consistency=format_consistency,
            verdict=verdict,
            verdict_emoji=verdict_emoji,
            detailed_breakdown=breakdown
        )
    
    def compare_entry_to_baseline(self, entry: DialogueEntry) -> Optional[BaselineComparison]:
        """
        Compare a dialogue entry to the corresponding baseline
        
        Args:
            entry: DialogueEntry to compare against baseline
            
        Returns:
            BaselineComparison object or None if no baseline available
        """
        if entry.test_id not in self.baseline_responses:
            return None
        
        baseline_response = self.baseline_responses[entry.test_id]
        similarity = self.compare_to_baseline(
            entry.response_text, baseline_response, entry.test_id
        )
        
        # Calculate performance delta (would need baseline performance metrics)
        performance_delta = self._calculate_performance_delta(entry)
        
        # Generate upgrade recommendation
        upgrade_rec = self._generate_upgrade_recommendation(similarity, entry)
        
        # Assess confidence and risk
        confidence = self._assess_confidence(similarity)
        risk = self._assess_risk(similarity, entry)
        
        return BaselineComparison(
            similarity_score=similarity,
            performance_delta=performance_delta,
            upgrade_recommendation=upgrade_rec,
            confidence_level=confidence,
            risk_assessment=risk
        )
    
    def _calculate_length_ratio(self, response: str, baseline: str) -> float:
        """Calculate normalized length ratio between responses"""
        response_len = len(response)
        baseline_len = max(len(baseline), 1)  # Avoid division by zero
        
        ratio = response_len / baseline_len
        
        # Normalize to 0-1 scale where 1.0 = perfect match
        if ratio <= 1.0:
            return ratio
        else:
            # Penalize responses that are too long
            return max(0.1, 2.0 - ratio)
    
    def _calculate_structure_similarity(self, response: str, baseline: str, test_id: str) -> float:
        """Calculate structural similarity between responses"""
        # Count structural elements
        response_sections = self._count_structural_elements(response, test_id)
        baseline_sections = self._count_structural_elements(baseline, test_id)
        
        if max(response_sections, baseline_sections) == 0:
            return 1.0  # Both have no structure
        
        similarity = min(response_sections, baseline_sections) / max(response_sections, baseline_sections)
        return similarity
    
    def _count_structural_elements(self, text: str, test_id: str) -> int:
        """Count structural elements in text based on test type"""
        if test_id in ["structured_analysis", "skills_categorization"]:
            return text.count("===")
        elif test_id == "concise_extraction":
            sections = 0
            if "your tasks" in text.lower():
                sections += 1
            if "your profile" in text.lower():
                sections += 1
            return sections
        else:
            # General structure counting
            return text.count("**") + text.count("###") + text.count("##")
    
    def _calculate_key_term_coverage(self, response: str, baseline: str, test_id: str) -> float:
        """Calculate overlap of key terms between responses"""
        # Get key terms for this test type
        key_terms = self._get_key_terms(test_id)
        
        response_words = set(response.lower().split())
        baseline_words = set(baseline.lower().split())
        
        # Count key terms in each response
        response_key_count = sum(1 for term in key_terms if term in response_words)
        baseline_key_count = sum(1 for term in key_terms if term in baseline_words)
        
        if baseline_key_count == 0:
            return 1.0 if response_key_count == 0 else 0.5
        
        coverage = response_key_count / baseline_key_count
        return min(coverage, 1.0)
    
    def _get_key_terms(self, test_id: str) -> List[str]:
        """Get key terms for a specific test type"""
        if test_id in self.key_terms_cache:
            cached_terms = self.key_terms_cache[test_id]
            return cached_terms
        
        key_terms = {
            "concise_extraction": [
                "audit", "security", "management", "experience", "skills", 
                "coordination", "validation", "compliance", "regulatory"
            ],
            "requirements_focus": [
                "requirement", "skill", "experience", "degree", "education",
                "certification", "bachelor", "master", "knowledge"
            ],
            "structured_analysis": [
                "technical", "business", "critical", "important", "requirement",
                "endpoint", "security", "audit", "compliance"
            ],
            "skills_categorization": [
                "communication", "leadership", "teamwork", "experience", 
                "education", "management", "analytical", "skills"
            ]
        }
        
        terms = key_terms.get(test_id, [])
        self.key_terms_cache[test_id] = terms
        return terms
    
    def _calculate_format_consistency(self, response: str, baseline: str, test_id: str) -> float:
        """Calculate format consistency between responses"""
        response_format = self._extract_format_features(response, test_id)
        baseline_format = self._extract_format_features(baseline, test_id)
        
        # Compare format features
        matches = sum(1 for key in baseline_format if response_format.get(key) == baseline_format[key])
        total_features = len(baseline_format)
        
        return matches / max(total_features, 1)
    
    def _extract_format_features(self, text: str, test_id: str) -> Dict[str, bool]:
        """Extract format features from text"""
        features = {}
        
        if test_id == "structured_analysis":
            features["has_tech_section"] = "=== TECHNICAL REQUIREMENTS ===" in text
            features["has_business_section"] = "=== BUSINESS REQUIREMENTS ===" in text
            features["has_priority_markers"] = bool(re.search(r'\(Critical\)|\(Important\)', text))
            
        elif test_id == "skills_categorization":
            features["has_soft_skills"] = "=== SOFT SKILLS ===" in text
            features["has_experience"] = "=== EXPERIENCE REQUIRED ===" in text
            features["has_education"] = "=== EDUCATION REQUIRED ===" in text
            
        elif test_id == "concise_extraction":
            features["has_tasks_section"] = "your tasks" in text.lower()
            features["has_profile_section"] = "your profile" in text.lower()
            features["has_bullet_points"] = "*" in text or "-" in text
            
        else:
            features["has_structure"] = bool(re.search(r'###|##|\*\*|===', text))
            features["has_bullets"] = bool(re.search(r'^\s*[-*•]', text, re.MULTILINE))
        
        return features
    
    def _get_similarity_weights(self, test_id: str) -> Dict[str, float]:
        """Get similarity calculation weights for specific test type"""
        default_weights = {
            "length": 0.2,
            "structure": 0.3,
            "content": 0.3,
            "format": 0.2
        }
        
        # Test-specific weight adjustments
        test_weights = {
            "structured_analysis": {"format": 0.4, "structure": 0.3, "content": 0.2, "length": 0.1},
            "skills_categorization": {"format": 0.4, "structure": 0.3, "content": 0.2, "length": 0.1},
            "concise_extraction": {"structure": 0.4, "content": 0.3, "format": 0.2, "length": 0.1}
        }
        
        return test_weights.get(test_id, default_weights)
    
    def _determine_verdict(self, similarity: float) -> Tuple[str, str]:
        """Determine verdict and emoji based on similarity score"""
        if similarity >= self.thresholds["excellent"]:
            return "Excellent match", "🟢"
        elif similarity >= self.thresholds["good"]:
            return "Good match", "🟡"
        elif similarity >= self.thresholds["fair"]:
            return "Fair match", "🟠"
        else:
            return "Poor match", "🔴"
    
    def _calculate_performance_delta(self, entry: DialogueEntry) -> Dict[str, float]:
        """Calculate performance differences from baseline"""
        # This would require baseline performance data
        # For now, return placeholder values
        return {
            "success_rate_delta": 0.0,
            "quality_score_delta": 0.0,
            "processing_time_delta": 0.0
        }
    
    def _generate_upgrade_recommendation(self, similarity: SimilarityScore, 
                                       entry: DialogueEntry) -> str:
        """Generate upgrade recommendation based on similarity"""
        if similarity.overall_similarity >= self.thresholds["excellent"]:
            return f"✅ RECOMMENDED: {entry.model_name} matches baseline quality"
        elif similarity.overall_similarity >= self.thresholds["good"]:
            return f"⚠️ CONSIDER: {entry.model_name} is a viable alternative"
        elif similarity.overall_similarity >= self.thresholds["fair"]:
            return f"🔍 EVALUATE: {entry.model_name} needs further testing"
        else:
            return f"❌ NOT RECOMMENDED: {entry.model_name} differs significantly from baseline"
    
    def _assess_confidence(self, similarity: SimilarityScore) -> float:
        """Assess confidence level in the comparison"""
        # Higher confidence for consistent scores across dimensions
        scores = [
            similarity.length_ratio,
            similarity.structure_similarity,
            similarity.key_term_coverage,
            similarity.format_consistency
        ]
        
        avg_score = sum(scores) / len(scores)
        variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
        consistency = 1.0 - min(variance, 1.0)
        
        # Combine overall score with consistency
        confidence = (similarity.overall_similarity * 0.7 + consistency * 0.3)
        return confidence
    
    def _assess_risk(self, similarity: SimilarityScore, entry: DialogueEntry) -> str:
        """Assess risk of using this model as baseline replacement"""
        if similarity.overall_similarity >= self.thresholds["excellent"]:
            return "🟢 LOW RISK: High similarity to baseline"
        elif similarity.overall_similarity >= self.thresholds["good"]:
            return "🟡 MEDIUM RISK: Good similarity, monitor closely"
        elif similarity.overall_similarity >= self.thresholds["fair"]:
            return "🟠 HIGH RISK: Significant differences from baseline"
        else:
            return "🔴 VERY HIGH RISK: Major deviations from baseline"


class BatchBaselineComparator:
    """Compare multiple models against baseline in batch operations"""
    
    def __init__(self, baseline_model: str):
        self.comparator = BaselineComparator(baseline_model)
        self.results: Dict[str, List[BaselineComparison]] = {}
    
    def compare_all_models(self, all_entries: Dict[str, List[DialogueEntry]]) -> Dict[str, List[BaselineComparison]]:
        """Compare all models against baseline"""
        baseline_entries = all_entries.get(self.comparator.baseline_model, [])
        if not baseline_entries:
            raise ValueError(f"No baseline entries found for {self.comparator.baseline_model}")
        
        self.comparator.set_baseline_responses(baseline_entries)
        
        results = {}
        for model_name, entries in all_entries.items():
            if model_name == self.comparator.baseline_model:
                continue  # Skip baseline model
            
            model_comparisons = []
            for entry in entries:
                comparison = self.comparator.compare_entry_to_baseline(entry)
                if comparison:
                    model_comparisons.append(comparison)
            
            results[model_name] = model_comparisons
        
        self.results = results
        return results
    
    def get_ranking(self) -> List[Tuple[str, float]]:
        """Get models ranked by average baseline similarity"""
        rankings = []
        
        for model_name, comparisons in self.results.items():
            if comparisons:
                avg_similarity = sum(comp.similarity_score.overall_similarity for comp in comparisons) / len(comparisons)
                rankings.append((model_name, avg_similarity))
        
        return sorted(rankings, key=lambda x: x[1], reverse=True)
