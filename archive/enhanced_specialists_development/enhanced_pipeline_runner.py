#!/usr/bin/env python3
"""
Enhanced Pipeline Runner - New Version with Enhanced Specialists
===============================================================

A new pipeline runner that integrates the enhanced specialists without
modifying Sandy's existing code. This follows the Golden Rules:
- No direct changes to Sandy
- Only new versions and new specialists
- Modular, testable design

Author: Republic of Love Enhancement Team
Version: 1.0 (Enhanced Specialists Integration)
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

# Add Sandy to path for importing (read-only)
sys.path.append('/home/xai/Documents/republic_of_love/sandy')

# Import enhanced specialists (new versions created outside Sandy)
from consciousness_first_specialists_fixed import ConsciousnessFirstSpecialistManagerFixed
from strategic_requirements_specialist import StrategicRequirementsSpecialist

# Import Sandy's original components (read-only)
from daily_report_pipeline.specialists import (
    ContentExtractionSpecialist,
    LocationValidationSpecialist, 
    TextSummarizationSpecialist,
    RequirementsDisplaySpecialist
)
from daily_report_pipeline.specialists.monitoring import (
    PerformanceMonitoringSpecialist,
    LLMPerformanceSpecialist
)
from daily_report_pipeline.reporting.generators.markdown_generator import MarkdownReportGenerator
from daily_report_pipeline.reporting.generators.excel_generator import ExcelReportGenerator
from core.enhanced_job_fetcher import EnhancedJobFetcher

class EnhancedPipelineRunner:
    """
    Enhanced pipeline runner that uses the improved specialists
    without modifying Sandy's original code.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize enhanced pipeline components."""
        self.start_time = datetime.now()
        self.setup_logging()
        
        # Load configuration
        config_file = config_path or Path('/home/xai/Documents/republic_of_love/sandy/config/pipeline_config.json')
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # Initialize enhanced specialists (new versions)
        self.consciousness_manager = ConsciousnessFirstSpecialistManagerFixed()
        self.strategic_requirements_specialist = StrategicRequirementsSpecialist()
        
        # Initialize Sandy's original specialists (read-only)
        self.content_extraction = ContentExtractionSpecialist()
        self.location_validator = LocationValidationSpecialist()
        self.text_summarizer = TextSummarizationSpecialist()
        self.requirements_display = RequirementsDisplaySpecialist()
        
        # Initialize monitoring
        self.performance_monitor = PerformanceMonitoringSpecialist()
        self.llm_monitor = LLMPerformanceSpecialist()
        
        # Initialize reporting
        self.markdown_generator = MarkdownReportGenerator()
        self.excel_generator = ExcelReportGenerator()
        
        # Initialize job fetcher
        self.job_fetcher = EnhancedJobFetcher()
        
        self.logger.info("Enhanced pipeline runner initialized")

    def setup_logging(self):
        """Configure logging for the enhanced pipeline."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('EnhancedPipeline')

    def _get_specific_rationale_or_partial(self, recommendations: Dict, job_analysis: Dict, job_description: str) -> str:
        """
        Enhanced fallback logic that produces job-specific content
        instead of generic template responses.
        """
        try:
            # Try enhanced consciousness-first rationale
            if hasattr(self.consciousness_manager, '_calculate_match_scores_llm_enhanced'):
                enhanced_scores = self.consciousness_manager._calculate_match_scores_llm_enhanced(
                    job_description, job_analysis
                )
                if enhanced_scores and any(score > 0 for score in enhanced_scores.values()):
                    return f"Enhanced analysis reveals key strengths: {', '.join(enhanced_scores.keys())}. Detailed scoring: {enhanced_scores}"
        except Exception as e:
            self.logger.warning(f"Enhanced rationale generation failed: {e}")
        
        # Try strategic requirements as fallback
        try:
            strategic_reqs = self.strategic_requirements_specialist.extract_strategic_requirements(job_description)
            if strategic_reqs.get('strategic_elements'):
                elements = strategic_reqs['strategic_elements']
                return f"Strategic fit analysis: Key requirements identified in {', '.join(elements.keys())}. Consider highlighting relevant experience in these areas."
        except Exception as e:
            self.logger.warning(f"Strategic requirements fallback failed: {e}")
        
        # Extract key terms from job description as last resort
        key_terms = self._extract_key_terms(job_description)
        if key_terms:
            return f"Job-specific guidance: Focus on experience with {', '.join(key_terms[:3])}. Tailor application to emphasize relevant background."
        
        return "Decision analysis required - review job requirements and candidate profile for optimal matching strategy."

    def _get_specific_narrative_or_partial(self, recommendations: Dict, job_analysis: Dict, job_description: str) -> str:
        """
        Enhanced narrative generation with job-specific content.
        """
        try:
            # Use strategic specialist for narrative context
            strategic_reqs = self.strategic_requirements_specialist.extract_strategic_requirements(job_description)
            
            if strategic_reqs.get('context_analysis'):
                context = strategic_reqs['context_analysis']
                return f"Professional narrative: {context}. Consider emphasizing alignment with organizational goals."
        except Exception as e:
            self.logger.warning(f"Enhanced narrative generation failed: {e}")
        
        # Fallback to key terms narrative
        key_terms = self._extract_key_terms(job_description)
        if key_terms:
            return f"Narrative focus: Demonstrate expertise in {key_terms[0]} and related technologies. Highlight problem-solving approach."
        
        return "Comprehensive profile analysis recommended for optimal narrative development."

    def _extract_key_terms(self, job_description: str) -> List[str]:
        """Extract key technical and professional terms from job description."""
        import re
        
        # Common patterns for important terms
        patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Technical terms like "Machine Learning"
            r'\b[A-Z]{2,}\b',  # Acronyms like "API", "SQL"
            r'\b\w+(?:ing|tion|ment|ness)\b',  # Process words
        ]
        
        terms = set()
        for pattern in patterns:
            matches = re.findall(pattern, job_description)
            terms.update(matches)
        
        # Filter common words
        stop_words = {'the', 'and', 'for', 'with', 'you', 'are', 'this', 'that', 'will', 'have'}
        filtered_terms = [term for term in terms if term.lower() not in stop_words and len(term) > 2]
        
        return filtered_terms[:10]  # Return top 10 terms

    def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single job using enhanced specialists.
        """
        try:
            job_description = job_data.get('description', '')
            
            # Step 1: Content extraction (using Sandy's original)
            extraction_result = self.content_extraction.extract_requirements(job_description)
            
            # Step 2: Enhanced consciousness-first analysis
            consciousness_analysis = self.consciousness_manager._calculate_match_scores_llm_enhanced(
                job_description, extraction_result
            )
            
            # Step 3: Strategic requirements analysis
            strategic_analysis = self.strategic_requirements_specialist.extract_strategic_requirements(
                job_description
            )
            
            # Step 4: Generate enhanced recommendations
            recommendations = {
                'consciousness_scores': consciousness_analysis,
                'strategic_elements': strategic_analysis,
                'job_specific_rationale': self._get_specific_rationale_or_partial(
                    {}, extraction_result, job_description
                ),
                'professional_narrative': self._get_specific_narrative_or_partial(
                    {}, extraction_result, job_description
                )
            }
            
            return {
                'job_id': job_data.get('id'),
                'extraction': extraction_result,
                'enhanced_analysis': recommendations,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing job: {e}")
            return {
                'job_id': job_data.get('id'),
                'error': str(e),
                'processing_timestamp': datetime.now().isoformat()
            }

    def run_test(self, job_count: int = 1) -> bool:
        """
        Run a test of the enhanced pipeline with limited jobs.
        """
        try:
            self.logger.info(f"Starting enhanced pipeline test with {job_count} jobs")
            
            # Fetch test jobs
            jobs = self.job_fetcher.fetch_jobs(limit=job_count)
            
            if not jobs:
                self.logger.warning("No jobs fetched for testing")
                return False
            
            # Process jobs with enhanced specialists
            results = []
            for job in jobs[:job_count]:
                result = self.process_job(job)
                results.append(result)
                
                # Log progress
                if result.get('enhanced_analysis'):
                    self.logger.info(f"✅ Job {job.get('id')} processed with enhanced analysis")
                else:
                    self.logger.warning(f"⚠️ Job {job.get('id')} processed with basic analysis")
            
            # Generate test report
            self._generate_test_report(results)
            
            self.logger.info("Enhanced pipeline test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Enhanced pipeline test failed: {e}")
            return False

    def _generate_test_report(self, results: List[Dict]) -> None:
        """Generate a test report for the enhanced pipeline results."""
        report_path = Path('/home/xai/Documents/republic_of_love/enhanced_pipeline_test_report.md')
        
        with open(report_path, 'w') as f:
            f.write("# Enhanced Pipeline Test Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Jobs Processed: {len(results)}\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"## Job {i}: {result.get('job_id', 'Unknown')}\n\n")
                
                if 'error' in result:
                    f.write(f"❌ **Error**: {result['error']}\n\n")
                    continue
                
                enhanced = result.get('enhanced_analysis', {})
                
                f.write(f"**Consciousness Scores**: {enhanced.get('consciousness_scores', 'Not available')}\n\n")
                f.write(f"**Strategic Elements**: {enhanced.get('strategic_elements', 'Not available')}\n\n")
                f.write(f"**Job-Specific Rationale**: {enhanced.get('job_specific_rationale', 'Not available')}\n\n")
                f.write(f"**Professional Narrative**: {enhanced.get('professional_narrative', 'Not available')}\n\n")
                f.write("---\n\n")
        
        self.logger.info(f"Test report saved to: {report_path}")

def main():
    """Main entry point for the enhanced pipeline."""
    runner = EnhancedPipelineRunner()
    
    # Run test by default
    success = runner.run_test(job_count=1)
    
    if success:
        print("🎉 Enhanced pipeline test completed successfully!")
        print("📊 Check enhanced_pipeline_test_report.md for results")
    else:
        print("❌ Enhanced pipeline test failed - check logs")

if __name__ == "__main__":
    main()
