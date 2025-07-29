"""
Enhanced QA System for ty_report_base
Implements rule-based validation with specific flags

Phase 2: Activated QA hooks with detailed flagging
"""

import re
from typing import List, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)

class EnhancedQAChecker:
    """Enhanced Quality Assurance checker with specific validation rules"""
    
    def __init__(self):
        self.qa_rules = {
            "missing_title": self._check_missing_title,
            "title_duplication": self._check_title_duplication,
            "empty_fields": self._check_empty_fields,
            "whitespace_only": self._check_whitespace_only,
            "low_confidence": self._check_low_confidence,
            "content_quality": self._check_content_quality,
            "section_completeness": self._check_section_completeness
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            "very_low": 0.3,
            "low": 0.5,
            "medium": 0.7,
            "high": 0.8
        }
    
    def run_enhanced_checks(self, input_data: Dict[str, Any], 
                           sections: List[Dict[str, Any]]) -> List[str]:
        """
        Run comprehensive QA checks on input data and generated sections
        
        Args:
            input_data: The original extraction data
            sections: Generated report sections
            
        Returns:
            List of QA flags
        """
        flags = []
        
        # Run all QA rules
        for rule_name, rule_func in self.qa_rules.items():
            try:
                rule_flags = rule_func(input_data, sections)
                if rule_flags:
                    flags.extend(rule_flags)
                    logger.debug(f"QA rule {rule_name} generated flags: {rule_flags}")
            except Exception as e:
                logger.warning(f"QA rule {rule_name} failed: {e}")
                flags.append(f"qa_rule_error:{rule_name}")
        
        logger.info(f"Enhanced QA check complete. Flags: {flags}")
        return flags
    
    def _check_missing_title(self, input_data: Dict[str, Any], 
                            sections: List[Dict[str, Any]]) -> List[str]:
        """Check for missing or empty titles"""
        flags = []
        
        # Check input blocks for missing titles
        blocks = input_data.get('blocks', [])
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                title = block.get('title', '').strip()
                if not title:
                    flags.append(f"missing_title:block_{i}")
        
        return flags
    
    def _check_title_duplication(self, input_data: Dict[str, Any], 
                                sections: List[Dict[str, Any]]) -> List[str]:
        """Check for duplicated tokens in titles"""
        flags = []
        
        blocks = input_data.get('blocks', [])
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                title = block.get('title', '')
                if title:
                    # Split title into words and check for duplicates
                    words = title.lower().split()
                    word_counts: Dict[str, int] = {}
                    for word in words:
                        word_counts[word] = word_counts.get(word, 0) + 1
                    
                    duplicated_words = [word for word, count in word_counts.items() if count > 1]
                    if duplicated_words:
                        flags.append(f"title_duplication:block_{i}:{','.join(duplicated_words)}")
        
        return flags
    
    def _check_empty_fields(self, input_data: Dict[str, Any], 
                           sections: List[Dict[str, Any]]) -> List[str]:
        """Check for empty critical fields"""
        flags = []
        
        critical_fields = ['title', 'company', 'requirements']
        blocks = input_data.get('blocks', [])
        
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                for field in critical_fields:
                    value = block.get(field)
                    if value is None or (isinstance(value, str) and not value.strip()):
                        flags.append(f"empty_field:block_{i}:{field}")
                    elif isinstance(value, list) and not value:
                        flags.append(f"empty_field:block_{i}:{field}")
        
        return flags
    
    def _check_whitespace_only(self, input_data: Dict[str, Any], 
                              sections: List[Dict[str, Any]]) -> List[str]:
        """Check for fields that contain only whitespace"""
        flags = []
        
        text_fields = ['title', 'company', 'location', 'description']
        blocks = input_data.get('blocks', [])
        
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                for field in text_fields:
                    value = block.get(field)
                    if isinstance(value, str) and value and not value.strip():
                        flags.append(f"whitespace_only:block_{i}:{field}")
        
        return flags
    
    def _check_low_confidence(self, input_data: Dict[str, Any], 
                             sections: List[Dict[str, Any]]) -> List[str]:
        """Check for low extraction confidence"""
        flags = []
        
        blocks = input_data.get('blocks', [])
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                confidence = block.get('extraction_confidence', 1.0)
                if confidence < self.confidence_thresholds['very_low']:
                    flags.append(f"very_low_confidence:block_{i}:{confidence}")
                elif confidence < self.confidence_thresholds['low']:
                    flags.append(f"low_confidence:block_{i}:{confidence}")
        
        return flags
    
    def _check_content_quality(self, input_data: Dict[str, Any], 
                              sections: List[Dict[str, Any]]) -> List[str]:
        """Check quality of generated content"""
        flags = []
        
        for section in sections:
            content = section.get('content', '')
            section_name = section.get('name', 'unknown')
            
            # Check for placeholder content (Phase 1 indicator)
            if '[Placeholder content' in content:
                flags.append(f"placeholder_content:{section_name}")
            
            # Check for very short content
            if len(content.strip()) < 20:
                flags.append(f"very_short_content:{section_name}")
            
            # Check for repetitive content patterns
            if self._is_repetitive_content(content):
                flags.append(f"repetitive_content:{section_name}")
        
        return flags
    
    def _check_section_completeness(self, input_data: Dict[str, Any], 
                                   sections: List[Dict[str, Any]]) -> List[str]:
        """Check if all expected sections are present and complete"""
        flags = []
        
        expected_sections = {'Overview', 'Key Claims', 'Validation Results', 
                           'Narrative Commentary', 'Metrics'}
        
        present_sections = {section.get('name', '') for section in sections}
        missing_sections = expected_sections - present_sections
        
        if missing_sections:
            flags.append(f"missing_sections:{','.join(missing_sections)}")
        
        return flags
    
    def _is_repetitive_content(self, content: str) -> bool:
        """Check if content appears repetitive"""
        # Simple check for repeated phrases
        sentences = content.split('.')
        if len(sentences) < 2:
            return False
        
        sentence_counts: Dict[str, int] = {}
        for sentence in sentences:
            clean_sentence = sentence.strip().lower()
            if clean_sentence:
                sentence_counts[clean_sentence] = sentence_counts.get(clean_sentence, 0) + 1
        
        # Flag if any sentence appears more than twice
        return any(count > 2 for count in sentence_counts.values())
    
    def generate_qa_summary(self, flags: List[str]) -> Dict[str, Any]:
        """Generate a summary of QA results"""
        flag_categories: Dict[str, List[str]] = {}
        
        for flag in flags:
            if ':' in flag:
                category = flag.split(':')[0]
            else:
                category = 'general'
            
            if category not in flag_categories:
                flag_categories[category] = []
            flag_categories[category].append(flag)
        
        return {
            'total_flags': len(flags),
            'categories': flag_categories,
            'severity': self._assess_severity(flags),
            'recommendations': self._generate_recommendations(flag_categories)
        }
    
    def _assess_severity(self, flags: List[str]) -> str:
        """Assess overall severity of QA flags"""
        if not flags:
            return 'clean'
        
        critical_patterns = ['missing_title', 'very_low_confidence', 'missing_sections']
        
        for flag in flags:
            for pattern in critical_patterns:
                if pattern in flag:
                    return 'critical'
        
        if len(flags) > 5:
            return 'high'
        elif len(flags) > 2:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, flag_categories: Dict[str, List[str]]) -> List[str]:
        """Generate recommendations based on flag patterns"""
        recommendations = []
        
        if 'missing_title' in flag_categories:
            recommendations.append("Review extraction process for title field handling")
        
        if 'title_duplication' in flag_categories:
            recommendations.append("Implement deduplication in title processing")
        
        if 'placeholder_content' in flag_categories:
            recommendations.append("Replace placeholder content with LLM generation")
        
        if 'low_confidence' in flag_categories or 'very_low_confidence' in flag_categories:
            recommendations.append("Consider reprocessing low-confidence extractions")
        
        return recommendations
