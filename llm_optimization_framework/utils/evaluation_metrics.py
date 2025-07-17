#!/usr/bin/env python3
"""
Evaluation Metrics Module
========================

Common evaluation metrics and scoring functions for LLM evaluation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    model: str
    task: str
    score: float
    details: Dict[str, Any]
    timestamp: str
    duration: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "model": self.model,
            "task": self.task,
            "score": self.score,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration": self.duration
        }


class EvaluationMetrics:
    """Common evaluation metrics for LLM tasks"""
    
    @staticmethod
    def calculate_completion_rate(responses: List[str]) -> float:
        """Calculate the rate of non-empty responses"""
        if not responses:
            return 0.0
            
        completed = sum(1 for r in responses if r and r.strip())
        return completed / len(responses)
    
    @staticmethod
    def calculate_average_length(responses: List[str]) -> float:
        """Calculate average response length"""
        if not responses:
            return 0.0
            
        lengths = [len(r) for r in responses if r]
        return sum(lengths) / len(lengths) if lengths else 0.0
    
    @staticmethod
    def calculate_consistency_score(scores: List[float]) -> float:
        """Calculate consistency based on score variance"""
        if len(scores) < 2:
            return 1.0
            
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Normalize to 0-1 scale (lower variance = higher consistency)
        # Assuming max reasonable std_dev is 3.0 for 0-10 scale
        consistency = max(0.0, 1.0 - (std_dev / 3.0))
        return consistency
    
    @staticmethod
    def calculate_speed_score(durations: List[float], target_duration: float = 30.0) -> float:
        """Calculate speed score based on response durations"""
        if not durations:
            return 0.0
            
        avg_duration = sum(durations) / len(durations)
        
        # Score based on how close to target duration
        if avg_duration <= target_duration:
            return 1.0
        elif avg_duration <= target_duration * 2:
            # Linear decrease from 1.0 to 0.5
            return 1.0 - (0.5 * (avg_duration - target_duration) / target_duration)
        else:
            # Further penalty for very slow responses
            return max(0.1, 0.5 - (avg_duration - target_duration * 2) / 100.0)
    
    @staticmethod
    def extract_numeric_score(text: str, scale: tuple = (0, 10)) -> Optional[float]:
        """Extract numeric score from text response"""
        if not text:
            return None
            
        # Look for patterns like "8/10", "7.5/10", "Score: 8", etc.
        patterns = [
            r'(\d+\.?\d*)\s*\/\s*10',
            r'(\d+\.?\d*)\s*\/\s*5',
            r'[Ss]core\s*:?\s*(\d+\.?\d*)',
            r'[Rr]ating\s*:?\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*out\s+of\s+10',
            r'(\d+\.?\d*)\s*points?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize to 0-10 scale if needed
                    if '/5' in pattern:
                        score = score * 2  # Convert 5-point to 10-point scale
                    return max(scale[0], min(scale[1], score))
                except ValueError:
                    continue
                    
        return None
    
    @staticmethod
    def count_keywords(text: str, keywords: List[str], case_sensitive: bool = False) -> Dict[str, int]:
        """Count occurrences of keywords in text"""
        if not text:
            return {keyword: 0 for keyword in keywords}
            
        search_text = text if case_sensitive else text.lower()
        search_keywords = keywords if case_sensitive else [k.lower() for k in keywords]
        
        counts = {}
        for original_keyword, search_keyword in zip(keywords, search_keywords):
            counts[original_keyword] = search_text.count(search_keyword)
            
        return counts
    
    @staticmethod
    def calculate_structured_response_score(text: str) -> float:
        """Calculate score based on response structure"""
        if not text:
            return 0.0
            
        structure_indicators = {
            'numbered_list': len(re.findall(r'\d+\.', text)),
            'bullet_points': len(re.findall(r'[•\-\*]\s', text)),
            'headers': len(re.findall(r'^#+\s', text, re.MULTILINE)),
            'sections': len(re.findall(r'\n\n', text)),
            'length': len(text.split())
        }
        
        # Score based on structure
        score = 0.0
        
        # Points for organization
        if structure_indicators['numbered_list'] > 0:
            score += 2.0
        if structure_indicators['bullet_points'] > 0:
            score += 1.5
        if structure_indicators['headers'] > 0:
            score += 1.0
        if structure_indicators['sections'] > 2:
            score += 1.0
            
        # Points for appropriate length
        word_count = structure_indicators['length']
        if 50 <= word_count <= 300:
            score += 3.0
        elif 20 <= word_count <= 500:
            score += 2.0
        elif word_count > 0:
            score += 1.0
            
        # Normalize to 0-10 scale
        return min(10.0, score)
    
    @staticmethod
    def calculate_relevance_score(response: str, expected_topics: List[str]) -> float:
        """Calculate relevance score based on topic coverage"""
        if not response or not expected_topics:
            return 0.0
            
        response_lower = response.lower()
        
        # Check for each expected topic
        topics_covered = 0
        for topic in expected_topics:
            topic_words = topic.lower().split()
            # Check if all words in topic are present
            if all(word in response_lower for word in topic_words):
                topics_covered += 1
                
        # Calculate coverage percentage
        coverage = topics_covered / len(expected_topics)
        
        # Convert to 0-10 scale
        return coverage * 10.0
    
    @staticmethod
    def aggregate_scores(scores: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
        """Aggregate multiple scores with optional weights"""
        if not scores:
            return 0.0
            
        if weights is None:
            # Equal weights
            return sum(scores.values()) / len(scores)
        else:
            # Weighted average
            total_weight = sum(weights.get(key, 1.0) for key in scores)
            weighted_sum = sum(scores[key] * weights.get(key, 1.0) for key in scores)
            return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def normalize_score(score: float, min_val: float, max_val: float, target_range: tuple = (0, 10)) -> float:
        """Normalize a score to target range"""
        if max_val == min_val:
            return target_range[0]
            
        # Normalize to 0-1
        normalized = (score - min_val) / (max_val - min_val)
        
        # Scale to target range
        target_min, target_max = target_range
        return target_min + normalized * (target_max - target_min)
