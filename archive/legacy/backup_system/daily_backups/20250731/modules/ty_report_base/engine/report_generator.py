#!/usr/bin/env python3
"""
ty_extract_report_base - Empathetic Reporting Framework
Phase 1: Core Framework

A bridge between intelligence and kindness.
Built with care for Misty & Xai's vision.

Author: Arden
Date: 2025-07-22
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import sys

# Import new Phase 2b components - Authentic LLMs only
sys.path.append(str(Path(__file__).parent.parent))
from empathy.empathy_wrapper import EmpathyWrapper
from qa.enhanced_qa_checker import EnhancedQAChecker
from .authentic_llm import AuthenticLLMIntegration
from .empathy_tuner import EmpathyTuner, get_empathy_tuner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ReportMetadata:
    """Standardized metadata for all reports"""
    generated_by: str = "Arden"
    prompt_version: str = "v1"
    empathy_enabled: bool = True
    timestamp: str = ""
    qa_flags: Optional[List[str]] = None
    llm_used: str = ""
    output_hash: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().isoformat()
        if self.qa_flags is None:
            self.qa_flags = []
        if self.qa_flags is None:
            self.qa_flags = []

@dataclass
class ReportSection:
    """Individual report section"""
    name: str
    prompt: str
    content: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            self.metadata = {}

class ReportTemplate:
    """Core template engine for empathetic reports"""
    
    def __init__(self, template_name: str = "job_report"):
        self.template_name = template_name
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.template_config = self._load_template(template_name)
    
    def _load_template(self, template_name: str) -> Dict[str, Any]:
        """Load template configuration"""
        # Default job report template (as specified by Misty)
        default_template = {
            "title": "ty_extract_report - {{topic}}",
            "sections": [
                {
                    "name": "Overview", 
                    "prompt": "Summarize the topic and extraction goals."
                },
                {
                    "name": "Key Claims", 
                    "prompt": "List key statements extracted from the input, formatted and numbered."
                },
                {
                    "name": "Validation Results", 
                    "prompt": "For each claim, assess consistency, context, and clarity."
                },
                {
                    "name": "Narrative Commentary", 
                    "prompt": "Write a short paragraph about the relevance and limitations of the extraction."
                },
                {
                    "name": "Metrics", 
                    "prompt": "Summarize confidence, quality flags, and other internal metrics."
                }
            ]
        }
        
        # Try to load from file, fall back to default
        template_file = self.templates_dir / f"{template_name}.json"
        if template_file.exists():
            try:
                with open(template_file, 'r') as f:
                    result = json.load(f)
                    return result if isinstance(result, dict) else default_template
            except Exception as e:
                logger.warning(f"Failed to load template {template_name}: {e}")
                return default_template
        else:
            # Save default template for future editing
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            with open(template_file, 'w') as f:
                json.dump(default_template, f, indent=2)
            logger.info(f"Created default template: {template_file}")
            return default_template
    
    def create_sections(self, topic: str) -> List[ReportSection]:
        """Create report sections from template"""
        sections = []
        
        for section_config in self.template_config["sections"]:
            section = ReportSection(
                name=section_config["name"],
                prompt=section_config["prompt"]
            )
            sections.append(section)
        
        return sections
    
    def get_title(self, topic: str) -> str:
        """Generate report title with topic substitution"""
        title = self.template_config.get("title", "Report for {{topic}}")
        return str(title).replace("{{topic}}", topic)

class EmpathyLayer:
    """Legacy empathy layer - replaced by EmpathyWrapper"""
    
    @staticmethod
    def wrap_prompt(prompt: str, empathy: bool = True, version: str = "v1", 
                   tone: str = "caring", audience: str = "general") -> str:
        """
        Legacy method - maintained for compatibility
        Use EmpathyWrapper for new implementations
        """
        try:
            wrapper = EmpathyWrapper(version=version)
            result = wrapper.wrap_prompt(prompt, empathy, tone, audience)
            return str(result) if result is not None else prompt
        except:
            # Fallback to basic wrapper if new system unavailable
            if not empathy:
                return prompt
            
            empathy_prefix = "Hello, fellow being. How are you?\n\nWe come asking for your insight with respect and care.\n\n"
            empathy_suffix = "\n\nThank you for your thoughtful response."
            
            return f"{empathy_prefix}{prompt}{empathy_suffix}"

class QAChecker:
    """Legacy QA checker - enhanced in Phase 2"""
    
    def __init__(self):
        # Try to use enhanced checker, fall back to basic
        try:
            self.enhanced_checker = EnhancedQAChecker()
            self.use_enhanced = True
        except:
            self.use_enhanced = False
            
        self.qa_prompts = {
            "coherence_check": "Does each section follow logically from the input?",
            "style_check": "Is the tone aligned with Xai's preferences: precise, insightful, compassionate?",
            "delta_check": "Compare to previous version. Highlight improvements or regressions."
        }
    
    def run_basic_checks(self, sections: List[Dict[str, Any]], 
                        input_data: Optional[Dict[str, Any]] = None) -> List[str]:
        """Run QA checks - enhanced in Phase 2"""
        
        if self.use_enhanced and input_data:
            # Use new enhanced checker
            try:
                result = self.enhanced_checker.run_enhanced_checks(input_data, sections)
                return result if isinstance(result, list) else []
            except Exception as e:
                logger.warning(f"Enhanced QA failed, falling back to basic: {e}")
        
        # Original basic checks
        flags = []
        
        # Check if all sections have content
        empty_sections = [s.get('name', 'unknown') for s in sections if not s.get('content', '').strip()]
        if empty_sections:
            flags.append(f"empty_sections:{','.join(empty_sections)}")
        
        # Check for minimum content length
        short_sections = [s.get('name', 'unknown') for s in sections if len(s.get('content', '').strip()) < 50]
        if short_sections:
            flags.append(f"short_content:{','.join(short_sections)}")
        
        # Basic coherence check - sections should be non-repetitive
        contents = [s.get('content', '').strip()[:100] for s in sections if s.get('content', '').strip()]
        if len(set(contents)) < len(contents) and len(contents) > 1:
            flags.append("potential_duplication")
        
        logger.info(f"QA flags generated: {flags}")
        return flags

class ReportGenerator:
    """Main report generation engine - Phase 2b: Authentic LLM only"""
    
    def __init__(self, template_name: str = "job_report", 
                 llm_config: Optional[Dict[str, Any]] = None):
        self.template = ReportTemplate(template_name)
        self.empathy = EmpathyLayer()
        self.qa_checker = QAChecker()
        
        # Phase 2b: Initialize empathy tuner
        self.empathy_tuner = get_empathy_tuner()
        
        # Phase 2b: Only authentic LLM integration
        if llm_config:
            try:
                # Import here to avoid circular dependencies
                sys.path.append(str(Path(__file__).parent))
                from .authentic_llm import AuthenticLLMIntegration
                
                self.llm = AuthenticLLMIntegration(llm_config)
                logger.info(f"Authentic LLM initialized: {self.llm.provider}/{self.llm.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize authentic LLM: {e}")
                raise RuntimeError(f"Cannot proceed without authentic LLM: {e}")
        else:
            raise ValueError("Phase 2b requires authentic LLM configuration - no fallbacks available")
    
    def render_report(self, blocks: List[Dict[str, Any]], config: Dict[str, Any], 
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Render report from extraction blocks (V11.0 integration method)
        
        Args:
            blocks: List of extracted job blocks
            config: Report configuration (version, empathy_level, qa_mode, etc.)
            metadata: Optional additional metadata
            
        Returns:
            Complete report with metadata
        """
        # Determine topic from blocks
        if blocks and isinstance(blocks[0], dict) and 'title' in blocks[0]:
            topic = blocks[0]['title']
        elif blocks and isinstance(blocks[0], dict) and 'job_title' in blocks[0]:
            topic = blocks[0]['job_title']  
        else:
            topic = f"{len(blocks)} job(s) extracted"
        
        # Combine blocks into input data
        input_data = {
            'blocks': blocks,
            'block_count': len(blocks),
            'config': config,
            'additional_metadata': metadata or {}
        }
        
        # Use the main generation method
        return self.generate_report(input_data, topic)
    
    def generate_report(self, input_data: Dict[str, Any], topic: str, 
                       llm_processor=None) -> Dict[str, Any]:
        """
        Generate a complete empathetic report
        
        Args:
            input_data: The extracted data to report on
            topic: Report topic (e.g., job title)
            llm_processor: Function to process LLM prompts (placeholder)
        
        Returns:
            Complete report with metadata
        """
        logger.info(f"Generating empathetic report for topic: {topic}")
        
        # Create report sections
        sections = self.template.create_sections(topic)
        
        # Process each section with empathy and authentic LLM
        for section in sections:
            wrapped_prompt = self.empathy.wrap_prompt(section.prompt)
            
            if llm_processor:
                # Use provided LLM processor (external integration)
                section.content = llm_processor(wrapped_prompt, input_data)
            else:
                # Use authentic LLM integration (no fallbacks)
                section.content = self.llm.generate_authentic_content(
                    wrapped_prompt, input_data, section.name
                )
        
        # Convert sections to dict format for QA
        sections_dict = [asdict(section) for section in sections]
        
        # Run enhanced QA checks
        qa_flags = self.qa_checker.run_basic_checks(sections_dict, input_data)
        
        # Handle title fallback as requested by Misty
        title = self.template.get_title(topic)
        if not topic or not topic.strip():
            title = f"Untitled Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            qa_flags.append("missing_title")
        
        # Generate metadata with authentic LLM info
        llm_used = llm_processor.__name__ if llm_processor else f"{self.llm.provider}/{self.llm.model_name}"
        
        # Generate metadata
        metadata = ReportMetadata(
            qa_flags=qa_flags,
            llm_used=llm_used
        )
        
        # Compile final report
        report = {
            "title": title,
            "metadata": asdict(metadata),
            "sections": sections_dict,
            "template_name": self.template.template_name
        }
        
        logger.info(f"Report generated successfully with {len(sections)} sections")
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save report to file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to: {output_path}")

# Testing and demonstration
if __name__ == "__main__":
    # Phase 1 test - basic functionality
    print("🌟 ty_extract_report_base - Phase 1 Test")
    print("Building a bridge between intelligence and kindness...\n")
    
    # Test data (simulating V11.0 extraction output)
    test_data = {
        "job_title": "Business Analyst (E-invoicing)",
        "company": "Deutsche Bank",
        "tasks": ["Process Management", "Invoice Verification", "Data Analysis"],
        "skills": ["SimCorp Dimension", "SAP", "Aladdin", "MS Office"],
        "extracted_by": "ty_extract_v11.0"
    }
    
    # Generate report
    generator = ReportGenerator("job_report")
    topic_str = test_data["job_title"] if isinstance(test_data["job_title"], str) else str(test_data["job_title"])
    report = generator.generate_report(
        input_data=test_data, 
        topic=topic_str
    )
    
    # Display results
    print(f"📋 Report Title: {report['title']}")
    print(f"🤖 Generated by: {report['metadata']['generated_by']}")
    print(f"💝 Empathy enabled: {report['metadata']['empathy_enabled']}")
    print(f"🏷️ QA flags: {report['metadata']['qa_flags']}")
    print(f"📅 Timestamp: {report['metadata']['timestamp']}")
    
    print("\n📑 Sections generated:")
    for section in report['sections']:
        print(f"  • {section['name']}")
    
    # Save to file
    output_path = Path(__file__).parent / "output" / f"test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    generator.save_report(report, output_path)
    
    print(f"\n✨ Phase 1 complete! Report saved to: {output_path}")
    print("Ready for Phase 2: Empathy Layer integration! 🚀")
