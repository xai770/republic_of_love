#!/usr/bin/env python3
"""
Golden Test Case Validation for Content Extraction Specialist v2.0
================================================================

Validates the v2.0 specialist against Sandy's 5 real job descriptions
Generates comprehensive validation report with accuracy metrics
Tests against production requirements: 90%+ accuracy, clean formatting

Usage: python validate_golden_test_cases.py
Output: Validation report with results for all 5 test cases
"""

import json
import time
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any

# Try to import ollama, handle gracefully if not available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️  Warning: ollama not available, falling back to basic parsing")

# Add the specialist to Python path
sys.path.append(str(Path(__file__).parent / "../src"))

from content_extraction_specialist_v2 import ContentExtractionSpecialistV2

class GoldenTestValidator:
    """Validates specialist performance against Sandy's golden test cases"""
    
    def __init__(self, test_data_path: str):
        """Initialize validator with test data"""
        self.test_data_path = test_data_path
        self.specialist = ContentExtractionSpecialistV2()
        self.results = []
        
    def load_test_data(self) -> Dict[str, Any]:
        """Load Sandy's golden test cases"""
        try:
            with open(self.test_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load test data: {e}")
            sys.exit(1)
    
    def validate_single_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Validate specialist against a single test case"""
        test_id = test_case['id']
        test_name = test_case['name']
        job_description = test_case['job_description']
        expected_skills = set(test_case['expected_skills'])
        expected_location = test_case['expected_location']
        
        print(f"\n🧪 Testing {test_id}: {test_name}")
        print(f"📍 Expected location: {expected_location}")
        print(f"🎯 Expected skills ({len(expected_skills)}): {', '.join(list(expected_skills)[:5])}{'...' if len(expected_skills) > 5 else ''}")
        
        start_time = time.time()
        
        try:
            # Run the specialist
            result = self.specialist.extract_core_content(job_description, test_id)
            processing_time = time.time() - start_time
            
            # Use LLM to extract and compare skills (following Rule #1: Always use LLMs!)
            skill_comparison = self._extract_and_compare_skills_with_llm(
                result.extracted_content, 
                list(expected_skills), 
                test_id
            )
            
            # Extract location using LLM as well
            extracted_location = self._extract_location_with_llm(result.extracted_content, expected_location)
            location_match = expected_location.lower() in extracted_location.lower() if extracted_location else False
            
            test_result = {
                'test_id': test_id,
                'test_name': test_name,
                'processing_time': processing_time,
                'original_length': result.original_length,
                'extracted_length': result.extracted_length,
                'reduction_percentage': result.reduction_percentage,
                'expected_skills': list(expected_skills),
                'extracted_skills': skill_comparison['extracted_skills'],
                'skill_matches': skill_comparison['matched_skills'],
                'missed_skills': skill_comparison['missed_skills'],
                'extra_skills': skill_comparison['extra_skills'],
                'skill_accuracy_percent': skill_comparison['accuracy_percentage'],
                'expected_location': expected_location,
                'extracted_location': extracted_location,
                'location_match': location_match,
                'extracted_content': result.extracted_content,
                'processing_notes': result.processing_notes,
                'model_used': result.model_used,
                'llm_processing_time': result.llm_processing_time,
                'llm_analysis': skill_comparison['analysis']
            }
            
            # Print summary
            print(f"⏱️  Processing time: {processing_time:.2f}s")
            print(f"📊 Content reduction: {result.reduction_percentage:.1f}%")
            print(f"🎯 Skill accuracy: {skill_comparison['accuracy_percentage']:.1f}% ({len(skill_comparison['matched_skills'])}/{len(expected_skills)} matched)")
            print(f"📍 Location match: {'✅' if location_match else '❌'} ({extracted_location})")
            
            if skill_comparison['missed_skills']:
                missed_display = skill_comparison['missed_skills'][:3]
                print(f"❌ Missed skills: {', '.join(missed_display)}{'...' if len(skill_comparison['missed_skills']) > 3 else ''}")
            if skill_comparison['extra_skills']:
                extra_display = skill_comparison['extra_skills'][:3]
                print(f"➕ Extra skills: {', '.join(extra_display)}{'...' if len(skill_comparison['extra_skills']) > 3 else ''}")
                
            return test_result
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return {
                'test_id': test_id,
                'test_name': test_name,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'processing_time': time.time() - start_time
            }
    
    def _extract_and_compare_skills_with_llm(self, extracted_content: str, expected_skills: List[str], test_id: str) -> Dict[str, Any]:
        """Use LLM to extract skills and compare with expected results"""
        if not OLLAMA_AVAILABLE:
            print(f"❌ Cannot perform LLM skill comparison for {test_id} - ollama not available")
            return {
                'extracted_skills': [],
                'matched_skills': [],
                'missed_skills': expected_skills,
                'extra_skills': [],
                'accuracy_percentage': 0.0,
                'analysis': "LLM comparison unavailable - ollama not installed",
                'llm_response': ""
            }
        
        prompt = f"""You are a skill extraction and comparison specialist. Analyze the job content and compare extracted skills with expected skills.

JOB CONTENT EXTRACTED BY SPECIALIST:
{extracted_content}

EXPECTED SKILLS FROM BUSINESS OWNER:
{', '.join(expected_skills)}

TASK: Extract all skills from the job content and compare with expected skills.

RESPONSE FORMAT:
EXTRACTED_SKILLS: [List all skills you can identify from the job content]
MATCHED_SKILLS: [Skills that match the expected list]
MISSED_SKILLS: [Expected skills not found in job content]
EXTRA_SKILLS: [Skills found but not in expected list]
ACCURACY_PERCENTAGE: [Percentage of expected skills found]
ANALYSIS: [Brief explanation of the comparison]

Be precise with skill names and handle variations (e.g., "Python programming" matches "Python").
"""

        try:
            response = ollama.chat(
                model="llama3.2:latest",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}
            )
            
            response_text = response['message']['content']
            
            # Parse LLM response using template format
            extracted_skills = self._parse_llm_field(response_text, "EXTRACTED_SKILLS")
            matched_skills = self._parse_llm_field(response_text, "MATCHED_SKILLS")
            missed_skills = self._parse_llm_field(response_text, "MISSED_SKILLS")
            extra_skills = self._parse_llm_field(response_text, "EXTRA_SKILLS")
            accuracy_str = self._parse_llm_field(response_text, "ACCURACY_PERCENTAGE")
            analysis = self._parse_llm_field(response_text, "ANALYSIS")
            
            # Extract accuracy percentage
            accuracy = 0.0
            if accuracy_str:
                import re
                match = re.search(r'(\d+(?:\.\d+)?)', accuracy_str)
                if match:
                    accuracy = float(match.group(1))
            
            return {
                'extracted_skills': extracted_skills.split(', ') if extracted_skills else [],
                'matched_skills': matched_skills.split(', ') if matched_skills else [],
                'missed_skills': missed_skills.split(', ') if missed_skills else [],
                'extra_skills': extra_skills.split(', ') if extra_skills else [],
                'accuracy_percentage': accuracy,
                'analysis': analysis,
                'llm_response': response_text
            }
            
        except Exception as e:
            print(f"❌ LLM skill comparison failed for {test_id}: {e}")
            return {
                'extracted_skills': [],
                'matched_skills': [],
                'missed_skills': expected_skills,
                'extra_skills': [],
                'accuracy_percentage': 0.0,
                'analysis': f"LLM comparison failed: {e}",
                'llm_response': ""
            }
    
    def _parse_llm_field(self, text: str, field_name: str) -> str:
        """Parse a specific field from LLM template response"""
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith(f"{field_name}:"):
                return line.split(':', 1)[1].strip()
        return ""
    
    def _extract_location_with_llm(self, extracted_content: str, expected_location: str) -> str:
        """Use LLM to extract location from specialist output"""
        if not OLLAMA_AVAILABLE:
            # Fallback to simple parsing if LLM unavailable
            lines = extracted_content.split('\n')
            for line in lines:
                if 'position:' in line.lower() and ' - ' in line:
                    return line.split(' - ')[-1].strip()
            return "Not found"
        
        try:
            prompt = f"""Extract the job location from this content:

{extracted_content}

Expected location format: {expected_location}

RESPONSE FORMAT:
LOCATION: [The location mentioned in the job content]

Be precise and extract the exact location mentioned."""

            response = ollama.chat(
                model="llama3.2:latest",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}
            )
            
            location = self._parse_llm_field(response['message']['content'], "LOCATION")
            return location if location else "Not found"
            
        except Exception as e:
            # Fallback to simple parsing if LLM fails
            lines = extracted_content.split('\n')
            for line in lines:
                if 'position:' in line.lower() and ' - ' in line:
                    return line.split(' - ')[-1].strip()
            return "Not found"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run validation against all test cases"""
        print("🚀 Starting Golden Test Case Validation")
        print("=" * 60)
        
        test_data = self.load_test_data()
        
        print(f"📋 Business Owner: {test_data['business_owner']}")
        print(f"🔧 Specialist: {test_data['specialist_name']}")
        print(f"📅 Test Date: {test_data['date_requested']}")
        print(f"🎯 Success Criteria: {test_data['output_requirements']['success_criteria']}")
        
        # Run each test case
        for test_case in test_data['test_cases']:
            result = self.validate_single_test_case(test_case)
            self.results.append(result)
        
        # Generate summary report
        return self._generate_summary_report(test_data)
    
    def _generate_summary_report(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive validation summary"""
        successful_tests = [r for r in self.results if 'error' not in r]
        failed_tests = [r for r in self.results if 'error' in r]
        
        if successful_tests:
            avg_skill_accuracy = sum(r['skill_accuracy_percent'] for r in successful_tests) / len(successful_tests)
            avg_processing_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
            avg_reduction = sum(r['reduction_percentage'] for r in successful_tests) / len(successful_tests)
            location_matches = sum(1 for r in successful_tests if r['location_match'])
            location_accuracy = location_matches / len(successful_tests) * 100
        else:
            avg_skill_accuracy = avg_processing_time = avg_reduction = location_accuracy = 0
        
        summary = {
            'validation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_data_source': test_data,
            'total_tests': len(self.results),
            'successful_tests': len(successful_tests),
            'failed_tests': len(failed_tests),
            'overall_success_rate': len(successful_tests) / len(self.results) * 100,
            'average_skill_accuracy': avg_skill_accuracy,
            'average_processing_time': avg_processing_time,
            'average_content_reduction': avg_reduction,
            'location_accuracy': location_accuracy,
            'meets_success_criteria': avg_skill_accuracy >= 90.0,
            'detailed_results': self.results
        }
        
        self._print_summary_report(summary)
        return summary
    
    def _print_summary_report(self, summary: Dict[str, Any]):
        """Print formatted summary report"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY REPORT")
        print("=" * 60)
        
        print(f"📅 Validation Date: {summary['validation_date']}")
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"✅ Successful: {summary['successful_tests']}")
        print(f"❌ Failed: {summary['failed_tests']}")
        print(f"📈 Success Rate: {summary['overall_success_rate']:.1f}%")
        print()
        
        print("🎯 PERFORMANCE METRICS:")
        print(f"   Skill Accuracy: {summary['average_skill_accuracy']:.1f}%")
        print(f"   Location Accuracy: {summary['location_accuracy']:.1f}%")
        print(f"   Avg Processing Time: {summary['average_processing_time']:.2f}s")
        print(f"   Avg Content Reduction: {summary['average_content_reduction']:.1f}%")
        print()
        
        success_criteria = summary['meets_success_criteria']
        print(f"🏆 MEETS SUCCESS CRITERIA: {'✅ YES' if success_criteria else '❌ NO'}")
        print(f"   Required: 90%+ skill accuracy")
        print(f"   Achieved: {summary['average_skill_accuracy']:.1f}%")
        
        if summary['failed_tests'] > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in summary['detailed_results']:
                if 'error' in result:
                    print(f"   {result['test_id']}: {result.get('error', 'Unknown error')}")

def main():
    """Main execution function"""
    # Path to Sandy's test data
    test_data_path = "/home/xai/Documents/llm_factory/0_mailboxes/terminator@llm_factory/inbox/golden_test_cases_content_extraction_v2.json"
    
    # Run validation
    validator = GoldenTestValidator(test_data_path)
    summary = validator.run_all_tests()
    
    # Save results
    results_path = "validation_results.json"
    with open(results_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_path}")
    
    # Return appropriate exit code
    sys.exit(0 if summary['meets_success_criteria'] else 1)

if __name__ == "__main__":
    main()
