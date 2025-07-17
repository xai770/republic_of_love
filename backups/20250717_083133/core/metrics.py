#!/usr/bin/env python3
"""
Performance Metrics Module
==========================

Comprehensive performance metrics calculation and analysis for LLM optimization.
Provides standardized metrics across different evaluation dimensions.
"""

import re
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MetricCategory(Enum):
    """Categories of performance metrics"""
    QUALITY = "quality"
    PERFORMANCE = "performance"
    CONSISTENCY = "consistency"
    EFFICIENCY = "efficiency"
    RELIABILITY = "reliability"


@dataclass
class MetricResult:
    """Individual metric calculation result"""
    name: str
    category: MetricCategory
    value: float
    max_value: float
    unit: str
    interpretation: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelMetrics:
    """Complete metrics for a single model"""
    model_name: str
    overall_score: float
    category_scores: Dict[MetricCategory, float]
    individual_metrics: List[MetricResult]
    benchmark_rank: Optional[int] = None
    performance_tier: str = ""
    recommendations: List[str] = field(default_factory=list)


class PerformanceMetrics:
    """Calculate comprehensive performance metrics for LLM models"""
    
    def __init__(self, custom_weights: Optional[Dict[MetricCategory, float]] = None):
        """
        Initialize performance metrics calculator
        
        Args:
            custom_weights: Custom category weights for overall scoring
        """
        self.weights = custom_weights or {
            MetricCategory.QUALITY: 0.4,
            MetricCategory.PERFORMANCE: 0.25,
            MetricCategory.CONSISTENCY: 0.2,
            MetricCategory.EFFICIENCY: 0.1,
            MetricCategory.RELIABILITY: 0.05
        }
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v/total_weight for k, v in self.weights.items()}
    
    def calculate_model_metrics(self, model_entries: List[Any], 
                              model_name: str) -> ModelMetrics:
        """
        Calculate comprehensive metrics for a single model
        
        Args:
            model_entries: List of dialogue entries for the model
            model_name: Name of the model
            
        Returns:
            ModelMetrics object with complete analysis
        """
        metrics = []
        
        # Quality metrics
        metrics.extend(self._calculate_quality_metrics(model_entries))
        
        # Performance metrics
        metrics.extend(self._calculate_performance_metrics(model_entries))
        
        # Consistency metrics
        metrics.extend(self._calculate_consistency_metrics(model_entries))
        
        # Efficiency metrics
        metrics.extend(self._calculate_efficiency_metrics(model_entries))
        
        # Reliability metrics
        metrics.extend(self._calculate_reliability_metrics(model_entries))
        
        # Calculate category scores
        category_scores = self._calculate_category_scores(metrics)
        
        # Calculate overall score
        overall_score = sum(
            category_scores[category] * weight 
            for category, weight in self.weights.items()
        )
        
        # Generate performance tier and recommendations
        tier = self._determine_performance_tier(overall_score)
        recommendations = self._generate_recommendations(metrics, category_scores)
        
        return ModelMetrics(
            model_name=model_name,
            overall_score=overall_score,
            category_scores=category_scores,
            individual_metrics=metrics,
            performance_tier=tier,
            recommendations=recommendations
        )
    
    def _calculate_quality_metrics(self, entries: List[Any]) -> List[MetricResult]:
        """Calculate quality-related metrics"""
        metrics: List[MetricResult] = []
        
        if not entries:
            return metrics
        
        # Response completeness
        completeness_scores = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                score = self._assess_response_completeness(entry.response_text, entry.test_id)
                completeness_scores.append(score)
        
        if completeness_scores:
            avg_completeness = statistics.mean(completeness_scores)
            metrics.append(MetricResult(
                name="Response Completeness",
                category=MetricCategory.QUALITY,
                value=avg_completeness,
                max_value=1.0,
                unit="score",
                interpretation=self._interpret_completeness(avg_completeness),
                confidence=0.9,
                details={"individual_scores": completeness_scores}
            ))
        
        # Structure quality
        structure_scores = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                score = self._assess_structure_quality(entry.response_text, entry.test_id)
                structure_scores.append(score)
        
        if structure_scores:
            avg_structure = statistics.mean(structure_scores)
            metrics.append(MetricResult(
                name="Structure Quality",
                category=MetricCategory.QUALITY,
                value=avg_structure,
                max_value=1.0,
                unit="score",
                interpretation=self._interpret_structure(avg_structure),
                confidence=0.85,
                details={"individual_scores": structure_scores}
            ))
        
        # Content relevance
        relevance_scores = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                score = self._assess_content_relevance(entry.response_text, entry.test_id)
                relevance_scores.append(score)
        
        if relevance_scores:
            avg_relevance = statistics.mean(relevance_scores)
            metrics.append(MetricResult(
                name="Content Relevance",
                category=MetricCategory.QUALITY,
                value=avg_relevance,
                max_value=1.0,
                unit="score",
                interpretation=self._interpret_relevance(avg_relevance),
                confidence=0.8,
                details={"individual_scores": relevance_scores}
            ))
        
        return metrics
    
    def _calculate_performance_metrics(self, entries: List[Any]) -> List[MetricResult]:
        """Calculate performance-related metrics"""
        metrics: List[MetricResult] = []
        
        if not entries:
            return metrics
        
        # Response length appropriateness
        length_scores = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                score = self._assess_response_length_appropriateness(entry.response_text, entry.test_id)
                length_scores.append(score)
        
        if length_scores:
            avg_length_score = statistics.mean(length_scores)
            metrics.append(MetricResult(
                name="Response Length Appropriateness",
                category=MetricCategory.PERFORMANCE,
                value=avg_length_score,
                max_value=1.0,
                unit="score",
                interpretation=self._interpret_length_appropriateness(avg_length_score),
                confidence=0.75,
                details={"individual_scores": length_scores}
            ))
        
        # Task completion rate
        completion_rate = self._calculate_task_completion_rate(entries)
        metrics.append(MetricResult(
            name="Task Completion Rate",
            category=MetricCategory.PERFORMANCE,
            value=completion_rate,
            max_value=1.0,
            unit="rate",
            interpretation=self._interpret_completion_rate(completion_rate),
            confidence=0.95,
            details={"total_tasks": len(entries)}
        ))
        
        return metrics
    
    def _calculate_consistency_metrics(self, entries: List[Any]) -> List[MetricResult]:
        """Calculate consistency-related metrics"""
        metrics: List[MetricResult] = []
        
        if len(entries) < 2:
            return metrics
        
        # Format consistency across responses
        format_consistency = self._calculate_format_consistency(entries)
        metrics.append(MetricResult(
            name="Format Consistency",
            category=MetricCategory.CONSISTENCY,
            value=format_consistency,
            max_value=1.0,
            unit="score",
            interpretation=self._interpret_consistency(format_consistency),
            confidence=0.8,
            details={"entry_count": len(entries)}
        ))
        
        # Response quality variance
        quality_variance = self._calculate_quality_variance(entries)
        consistency_score = max(0, 1.0 - quality_variance)
        metrics.append(MetricResult(
            name="Quality Consistency",
            category=MetricCategory.CONSISTENCY,
            value=consistency_score,
            max_value=1.0,
            unit="score",
            interpretation=self._interpret_quality_variance(quality_variance),
            confidence=0.85,
            details={"variance": quality_variance}
        ))
        
        return metrics
    
    def _calculate_efficiency_metrics(self, entries: List[Any]) -> List[MetricResult]:
        """Calculate efficiency-related metrics"""
        metrics: List[MetricResult] = []
        
        if not entries:
            return metrics
        
        # Average response length as efficiency proxy
        response_lengths = [len(entry.response_text) for entry in entries if hasattr(entry, 'response_text')]
        if response_lengths:
            avg_length = statistics.mean(response_lengths)
            # Normalize to 0-1 scale (shorter responses generally more efficient)
            efficiency_score = max(0, min(1.0, 1.0 - (avg_length - 500) / 2000))
            
            metrics.append(MetricResult(
                name="Response Efficiency",
                category=MetricCategory.EFFICIENCY,
                value=efficiency_score,
                max_value=1.0,
                unit="score",
                interpretation=self._interpret_efficiency(efficiency_score),
                confidence=0.6,
                details={"avg_length": avg_length, "length_range": (min(response_lengths), max(response_lengths))}
            ))
        
        return metrics
    
    def _calculate_reliability_metrics(self, entries: List[Any]) -> List[MetricResult]:
        """Calculate reliability-related metrics"""
        metrics: List[MetricResult] = []
        
        if not entries:
            return metrics
        
        # Error rate (responses that seem incomplete or malformed)
        error_count = sum(1 for entry in entries if self._is_response_error(entry))
        reliability_score = 1.0 - (error_count / len(entries))
        
        metrics.append(MetricResult(
            name="Response Reliability",
            category=MetricCategory.RELIABILITY,
            value=reliability_score,
            max_value=1.0,
            unit="rate",
            interpretation=self._interpret_reliability(reliability_score),
            confidence=0.9,
            details={"error_count": error_count, "total_responses": len(entries)}
        ))
        
        return metrics
    
    def _assess_response_completeness(self, response: str, test_id: str) -> float:
        """Assess how complete a response is for its test type"""
        if test_id == "structured_analysis":
            has_tech = "technical requirements" in response.lower()
            has_business = "business requirements" in response.lower()
            has_structure = "===" in response
            return (has_tech + has_business + has_structure) / 3.0
        
        elif test_id == "skills_categorization":
            has_soft = "soft skills" in response.lower()
            has_experience = "experience" in response.lower()
            has_education = "education" in response.lower()
            return (has_soft + has_experience + has_education) / 3.0
        
        elif test_id == "concise_extraction":
            has_tasks = "tasks" in response.lower()
            has_profile = "profile" in response.lower()
            return (has_tasks + has_profile) / 2.0
        
        else:
            # General completeness check
            return min(1.0, len(response) / 200)  # Assume 200 chars is baseline complete
    
    def _assess_structure_quality(self, response: str, test_id: str) -> float:
        """Assess the structural quality of a response"""
        structure_elements = response.count("===") + response.count("**") + response.count("###")
        
        if test_id in ["structured_analysis", "skills_categorization"]:
            # These should have clear section headers
            expected_sections = 3
            return min(1.0, structure_elements / expected_sections)
        else:
            # General structure check
            return min(1.0, structure_elements / 2)
    
    def _assess_content_relevance(self, response: str, test_id: str) -> float:
        """Assess how relevant the content is to the test type"""
        response_lower = response.lower()
        
        relevance_keywords = {
            "concise_extraction": ["audit", "security", "management", "experience"],
            "requirements_focus": ["requirement", "skill", "degree", "certification"],
            "structured_analysis": ["technical", "business", "requirement", "critical"],
            "skills_categorization": ["communication", "leadership", "experience", "education"]
        }
        
        keywords = relevance_keywords.get(test_id, ["job", "skill", "requirement"])
        relevance_count = sum(1 for keyword in keywords if keyword in response_lower)
        
        return min(1.0, relevance_count / len(keywords))
    
    def _assess_response_length_appropriateness(self, response: str, test_id: str) -> float:
        """Assess if response length is appropriate for the test type"""
        length = len(response)
        
        # Expected length ranges for different test types
        length_expectations = {
            "concise_extraction": (200, 600),
            "requirements_focus": (300, 800),
            "structured_analysis": (400, 1200),
            "skills_categorization": (300, 900)
        }
        
        expected_min, expected_max = length_expectations.get(test_id, (200, 800))
        
        if expected_min <= length <= expected_max:
            return 1.0
        elif length < expected_min:
            return length / expected_min
        else:
            # Penalize overly long responses
            return max(0.1, expected_max / length)
    
    def _calculate_task_completion_rate(self, entries: List[Any]) -> float:
        """Calculate the rate of successfully completed tasks"""
        if not entries:
            return 0.0
        
        completed_tasks = sum(1 for entry in entries if self._is_task_completed(entry))
        return completed_tasks / len(entries)
    
    def _is_task_completed(self, entry: Any) -> bool:
        """Check if a task was completed successfully"""
        if not hasattr(entry, 'response_text'):
            return False
        
        response = entry.response_text
        
        # Basic completion checks
        if len(response) < 50:  # Too short to be complete
            return False
        
        if "error" in response.lower() or "cannot" in response.lower():
            return False
        
        return True
    
    def _calculate_format_consistency(self, entries: List[Any]) -> float:
        """Calculate how consistent the formatting is across responses"""
        if len(entries) < 2:
            return 1.0
        
        format_features = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                features = {
                    'has_sections': '===' in entry.response_text,
                    'has_bullets': '*' in entry.response_text or '-' in entry.response_text,
                    'has_headers': '**' in entry.response_text or '###' in entry.response_text
                }
                format_features.append(features)
        
        if not format_features:
            return 1.0
        
        # Calculate consistency across features
        consistency_scores = []
        for feature in ['has_sections', 'has_bullets', 'has_headers']:
            feature_values = [features[feature] for features in format_features]
            if len(set(feature_values)) == 1:  # All same
                consistency_scores.append(1.0)
            else:
                # Calculate ratio of most common value
                most_common_count = max(feature_values.count(True), feature_values.count(False))
                consistency_scores.append(most_common_count / len(feature_values))
        
        return statistics.mean(consistency_scores)
    
    def _calculate_quality_variance(self, entries: List[Any]) -> float:
        """Calculate variance in response quality"""
        quality_scores = []
        for entry in entries:
            if hasattr(entry, 'response_text'):
                # Simple quality proxy based on length and structure
                length_score = min(1.0, len(entry.response_text) / 300)
                structure_score = self._assess_structure_quality(entry.response_text, entry.test_id)
                quality_scores.append((length_score + structure_score) / 2)
        
        if len(quality_scores) < 2:
            return 0.0
        
        return statistics.variance(quality_scores)
    
    def _is_response_error(self, entry: Any) -> bool:
        """Check if a response appears to be an error"""
        if not hasattr(entry, 'response_text'):
            return True
        
        response = entry.response_text.lower()
        
        # Check for error indicators
        error_indicators = [
            "error", "failed", "cannot process", "unable to", 
            "invalid", "timeout", "exception"
        ]
        
        return any(indicator in response for indicator in error_indicators)
    
    def _calculate_category_scores(self, metrics: List[MetricResult]) -> Dict[MetricCategory, float]:
        """Calculate average scores for each category"""
        category_scores = {}
        
        for category in MetricCategory:
            category_metrics = [m for m in metrics if m.category == category]
            if category_metrics:
                # Weight by confidence
                weighted_sum = sum(m.value * m.confidence for m in category_metrics)
                confidence_sum = sum(m.confidence for m in category_metrics)
                category_scores[category] = weighted_sum / confidence_sum if confidence_sum > 0 else 0
            else:
                category_scores[category] = 0.0
        
        return category_scores
    
    def _determine_performance_tier(self, overall_score: float) -> str:
        """Determine performance tier based on overall score"""
        if overall_score >= 0.9:
            return "🥇 EXCELLENT"
        elif overall_score >= 0.8:
            return "🥈 VERY GOOD"
        elif overall_score >= 0.7:
            return "🥉 GOOD"
        elif overall_score >= 0.6:
            return "⚡ ACCEPTABLE"
        elif overall_score >= 0.5:
            return "⚠️ NEEDS IMPROVEMENT"
        else:
            return "❌ POOR"
    
    def _generate_recommendations(self, metrics: List[MetricResult], 
                                category_scores: Dict[MetricCategory, float]) -> List[str]:
        """Generate improvement recommendations based on metrics"""
        recommendations = []
        
        # Check each category for improvement opportunities
        for category, score in category_scores.items():
            if score < 0.7:
                if category == MetricCategory.QUALITY:
                    recommendations.append(f"🎯 Improve response quality (current: {score:.2f})")
                elif category == MetricCategory.PERFORMANCE:
                    recommendations.append(f"⚡ Optimize task performance (current: {score:.2f})")
                elif category == MetricCategory.CONSISTENCY:
                    recommendations.append(f"🔄 Enhance response consistency (current: {score:.2f})")
                elif category == MetricCategory.EFFICIENCY:
                    recommendations.append(f"🚀 Improve response efficiency (current: {score:.2f})")
                elif category == MetricCategory.RELIABILITY:
                    recommendations.append(f"🛡️ Increase response reliability (current: {score:.2f})")
        
        # Specific metric recommendations
        low_metrics = [m for m in metrics if m.value < 0.6]
        for metric in low_metrics:
            recommendations.append(f"📊 Focus on {metric.name.lower()} (current: {metric.value:.2f})")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    # Interpretation methods
    def _interpret_completeness(self, score: float) -> str:
        if score >= 0.9: return "Excellent completeness"
        elif score >= 0.7: return "Good completeness"
        elif score >= 0.5: return "Adequate completeness"
        else: return "Poor completeness"
    
    def _interpret_structure(self, score: float) -> str:
        if score >= 0.9: return "Excellent structure"
        elif score >= 0.7: return "Good structure"
        elif score >= 0.5: return "Basic structure"
        else: return "Poor structure"
    
    def _interpret_relevance(self, score: float) -> str:
        if score >= 0.9: return "Highly relevant"
        elif score >= 0.7: return "Good relevance"
        elif score >= 0.5: return "Adequate relevance"
        else: return "Poor relevance"
    
    def _interpret_length_appropriateness(self, score: float) -> str:
        if score >= 0.9: return "Optimal length"
        elif score >= 0.7: return "Good length"
        elif score >= 0.5: return "Acceptable length"
        else: return "Poor length"
    
    def _interpret_completion_rate(self, rate: float) -> str:
        if rate >= 0.95: return "Excellent completion"
        elif rate >= 0.85: return "Good completion"
        elif rate >= 0.7: return "Acceptable completion"
        else: return "Poor completion"
    
    def _interpret_consistency(self, score: float) -> str:
        if score >= 0.9: return "Highly consistent"
        elif score >= 0.7: return "Good consistency"
        elif score >= 0.5: return "Moderate consistency"
        else: return "Poor consistency"
    
    def _interpret_quality_variance(self, variance: float) -> str:
        if variance <= 0.05: return "Very stable quality"
        elif variance <= 0.1: return "Stable quality"
        elif variance <= 0.2: return "Moderate variance"
        else: return "High variance"
    
    def _interpret_efficiency(self, score: float) -> str:
        if score >= 0.8: return "Highly efficient"
        elif score >= 0.6: return "Good efficiency"
        elif score >= 0.4: return "Moderate efficiency"
        else: return "Low efficiency"
    
    def _interpret_reliability(self, score: float) -> str:
        if score >= 0.95: return "Highly reliable"
        elif score >= 0.85: return "Good reliability"
        elif score >= 0.7: return "Acceptable reliability"
        else: return "Poor reliability"


class MetricsBenchmarker:
    """Compare metrics across multiple models and generate rankings"""
    
    def __init__(self):
        self.model_metrics: Dict[str, ModelMetrics] = {}
    
    def add_model_metrics(self, metrics: ModelMetrics):
        """Add metrics for a model"""
        self.model_metrics[metrics.model_name] = metrics
    
    def generate_rankings(self) -> Dict[str, List[Tuple[str, float]]]:
        """Generate rankings for different aspects"""
        rankings = {}
        
        # Overall ranking
        overall_ranking = sorted(
            [(name, metrics.overall_score) for name, metrics in self.model_metrics.items()],
            key=lambda x: x[1], reverse=True
        )
        rankings["overall"] = overall_ranking
        
        # Category rankings
        for category in MetricCategory:
            category_ranking = sorted(
                [(name, metrics.category_scores.get(category, 0.0)) 
                 for name, metrics in self.model_metrics.items()],
                key=lambda x: x[1], reverse=True
            )
            rankings[category.value] = category_ranking
        
        # Update benchmark ranks
        for i, (model_name, _) in enumerate(overall_ranking):
            self.model_metrics[model_name].benchmark_rank = i + 1
        
        return rankings
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.model_metrics:
            return {}
        
        rankings = self.generate_rankings()
        
        # Calculate category averages
        category_averages = {}
        for category in MetricCategory:
            scores = [metrics.category_scores.get(category, 0.0) 
                     for metrics in self.model_metrics.values()]
            category_averages[category.value] = {
                "average": statistics.mean(scores),
                "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
                "min": min(scores),
                "max": max(scores)
            }
        
        return {
            "model_count": len(self.model_metrics),
            "rankings": rankings,
            "category_averages": category_averages,
            "top_performer": rankings["overall"][0] if rankings["overall"] else None,
            "performance_spread": max(m.overall_score for m in self.model_metrics.values()) - 
                                min(m.overall_score for m in self.model_metrics.values())
        }
