"""
LLM Testing Stubs for ty_report_base
Simple mock functions to trace flow before real model integration

Phase 2: Testing empathy and QA flow
"""

import time
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class LLMStub:
    """Mock LLM for testing report generation flow"""
    
    def __init__(self, model_name: str = "test_stub_v1"):
        self.model_name = model_name
        self.response_templates = self._load_response_templates()
    
    def _load_response_templates(self) -> Dict[str, str]:
        """Load template responses for different section types"""
        return {
            "Overview": """Based on the extraction data provided, this appears to be a {job_type} position for {title} at {company}. 

The role involves {key_requirements} and represents a {confidence_level} confidence extraction. This overview synthesizes the key elements from the source data while maintaining empathy for the job seeker's perspective.""",
            
            "Key Claims": """The following key claims have been extracted from the source data:

1. Position Title: {title}
2. Company: {company}
3. Primary Requirements: {requirements_summary}
4. Confidence Level: {confidence}%
5. Data Quality: {data_quality}

Each claim reflects careful analysis of the source material with respect for accuracy and context.""",
            
            "Validation Results": """Assessment of extracted claims:

✓ Title consistency: {title_status}
✓ Company verification: {company_status}  
✓ Requirements clarity: {requirements_status}
✓ Overall data integrity: {integrity_status}

The validation process considered context, consistency, and clarity while maintaining empathetic awareness of the importance of accurate job information.""",
            
            "Narrative Commentary": """This extraction represents {narrative_summary}. The data quality suggests {quality_assessment}, which is important for job seekers relying on this information.

From a holistic perspective, this posting {relevance_note} and should be considered within the broader context of career exploration. The extraction process honored both precision and the human element of job searching.""",
            
            "Metrics": """Extraction Performance Summary:

• Confidence Score: {confidence}%
• Processing Quality: {quality_grade}
• Data Completeness: {completeness}%
• QA Flags: {qa_flag_count}
• Empathy Level: {empathy_setting}

These metrics provide transparency while maintaining focus on serving job seekers with reliable, compassionate information."""
        }
    
    def mock_generate(self, prompt: str, input_data: Dict[str, Any], 
                     section_name: str = "General") -> str:
        """
        Generate mock content based on section type and input data
        
        Args:
            prompt: The (possibly empathy-wrapped) prompt
            input_data: Extraction data to work with
            section_name: Which section we're generating for
            
        Returns:
            Generated content string
        """
        # Simulate processing time
        time.sleep(0.1 + random.uniform(0.05, 0.15))
        
        # Extract blocks for content generation
        blocks = input_data.get('blocks', [])
        first_block = blocks[0] if blocks else {}
        
        # Generate content based on section
        template = self.response_templates.get(section_name, 
                                             "Generated content for {section_name}: {summary}")
        
        # Fill template with extracted data
        content = self._fill_template(template, first_block, input_data, section_name)
        
        logger.info(f"Generated {len(content)} chars for {section_name} section")
        return content
    
    def _fill_template(self, template: str, block: Dict[str, Any], 
                      input_data: Dict[str, Any], section_name: str) -> str:
        """Fill content template with actual data"""
        # Extract data with safe defaults
        title = block.get('title', 'Untitled Position')
        company = block.get('company', 'Unknown Company')
        requirements = block.get('requirements', ['No requirements specified'])
        confidence = block.get('extraction_confidence', 0.0)
        
        # Build context-aware replacements
        replacements = {
            'job_type': self._infer_job_type(title),
            'title': title,
            'company': company,
            'key_requirements': ', '.join(requirements[:3]) if requirements else 'various skills',
            'confidence_level': self._confidence_to_text(confidence),
            'requirements_summary': ', '.join(requirements[:4]) if requirements else 'Not specified',
            'confidence': int(confidence * 100),
            'data_quality': self._assess_data_quality(block),
            'title_status': 'Present and clear' if title != 'Untitled Position' else 'Missing or unclear',
            'company_status': 'Verified' if company != 'Unknown Company' else 'Not specified',
            'requirements_status': 'Detailed' if len(requirements) > 2 else 'Limited',
            'integrity_status': 'High' if confidence > 0.8 else 'Moderate' if confidence > 0.5 else 'Low',
            'narrative_summary': self._generate_narrative_summary(block, confidence),
            'quality_assessment': self._quality_assessment(confidence),
            'relevance_note': self._relevance_assessment(block),
            'quality_grade': self._confidence_to_grade(confidence),
            'completeness': self._calculate_completeness(block),
            'qa_flag_count': len(input_data.get('qa_flags', [])),
            'empathy_setting': 'High' if input_data.get('config', {}).get('empathy_level') == 'high' else 'Standard',
            'section_name': section_name,
            'summary': f"Analysis of {title} position with {confidence:.1%} confidence"
        }
        
        # Replace placeholders in template
        try:
            return template.format(**replacements)
        except KeyError as e:
            logger.warning(f"Template placeholder {e} not found, using fallback")
            return f"Generated {section_name} content for {title} at {company} (confidence: {confidence:.1%})"
    
    def _infer_job_type(self, title: str) -> str:
        """Infer job type from title"""
        title_lower = title.lower()
        if 'senior' in title_lower or 'lead' in title_lower:
            return 'senior-level'
        elif 'junior' in title_lower or 'entry' in title_lower:
            return 'entry-level'
        elif 'manager' in title_lower or 'director' in title_lower:
            return 'management'
        else:
            return 'professional'
    
    def _confidence_to_text(self, confidence: float) -> str:
        """Convert confidence score to descriptive text"""
        if confidence > 0.9:
            return 'very high'
        elif confidence > 0.7:
            return 'high'
        elif confidence > 0.5:
            return 'moderate'
        else:
            return 'low'
    
    def _confidence_to_grade(self, confidence: float) -> str:
        """Convert confidence to letter grade"""
        if confidence > 0.9:
            return 'A'
        elif confidence > 0.8:
            return 'B+'
        elif confidence > 0.7:
            return 'B'
        elif confidence > 0.6:
            return 'C+'
        elif confidence > 0.5:
            return 'C'
        else:
            return 'D'
    
    def _assess_data_quality(self, block: Dict[str, Any]) -> str:
        """Assess overall data quality"""
        score = 0
        total = 0
        
        # Check presence of key fields
        key_fields = ['title', 'company', 'requirements', 'location']
        for field in key_fields:
            total += 1
            if block.get(field):
                score += 1
        
        percentage = score / total if total > 0 else 0
        
        if percentage > 0.8:
            return 'Excellent'
        elif percentage > 0.6:
            return 'Good'
        elif percentage > 0.4:
            return 'Fair'
        else:
            return 'Limited'
    
    def _calculate_completeness(self, block: Dict[str, Any]) -> int:
        """Calculate data completeness percentage"""
        expected_fields = ['title', 'company', 'requirements', 'location', 'description', 'salary_range']
        present_fields = sum(1 for field in expected_fields if block.get(field))
        return int((present_fields / len(expected_fields)) * 100)
    
    def _generate_narrative_summary(self, block: Dict[str, Any], confidence: float) -> str:
        """Generate narrative summary"""
        if confidence > 0.8:
            return "a well-structured job posting with clear requirements and comprehensive information"
        elif confidence > 0.6:
            return "a reasonably complete job posting with some areas for clarification"
        elif confidence > 0.4:
            return "a job posting with partial information that may require verification"
        else:
            return "a job posting with limited information that needs careful review"
    
    def _quality_assessment(self, confidence: float) -> str:
        """Generate quality assessment text"""
        if confidence > 0.8:
            return "high reliability and should serve job seekers well"
        elif confidence > 0.6:
            return "good reliability with minor gaps that don't significantly impact usefulness"
        elif confidence > 0.4:
            return "moderate reliability - job seekers should verify key details"
        else:
            return "limited reliability - additional research recommended before application"
    
    def _relevance_assessment(self, block: Dict[str, Any]) -> str:
        """Assess relevance and context"""
        title = block.get('title', '')
        if title:
            return f"offers valuable information for those seeking {title.lower()} roles"
        else:
            return "provides data that may be useful but requires careful interpretation"
