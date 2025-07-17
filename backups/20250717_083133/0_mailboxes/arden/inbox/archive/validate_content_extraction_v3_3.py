#!/usr/bin/env python3
"""
Content Extraction Specialist v3.3 PRODUCTION - Validation Script
================================================================

Validates the v3.3 PRODUCTION specialist against Sandy's golden test cases
Generates detailed JSON output for production readiness assessment

Usage: python validate_v3_3.py
Output: validation_results_v3_3.json

Date: June 27, 2025
For: Sandy@consciousness - Final Production Validation
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Import the v3.3 specialist
from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33

class ProductionValidator:
    """Final production validation for v3.3 specialist"""
    
    def __init__(self, test_file_path: str):
        self.test_file_path = test_file_path
        self.specialist = ContentExtractionSpecialistV33()
        self.validation_results = {
            "specialist_version": "Content Extraction Specialist v3.3 PRODUCTION",
            "test_date": datetime.now().strftime("%Y-%m-%d"),
            "overall_accuracy": "",
            "format_compliance": "",
            "test_results": [],
            "summary": {}
        }
        
    def load_golden_test_cases(self) -> Dict[str, Any]:
        """Load Sandy's golden test cases"""
        try:
            with open(self.test_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading test file {self.test_file_path}: {e}")
            sys.exit(1)
    
    def calculate_accuracy(self, extracted_skills: List[str], expected_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate precision-focused accuracy"""
        extracted_lower = [skill.lower().strip() for skill in extracted_skills]
        expected_lower = [skill.lower().strip() for skill in expected_skills]
        
        # Find matches with fuzzy matching for similar skills
        matched_skills = []
        missing_skills = []
        extra_skills = list(extracted_skills)  # Start with all extracted
        
        for expected in expected_skills:
            expected_lower_item = expected.lower().strip()
            best_match = None
            
            # Exact match first
            for extracted in extracted_skills:
                if extracted.lower().strip() == expected_lower_item:
                    best_match = extracted
                    break
            
            # Fuzzy match for similar skills
            if not best_match:
                for extracted in extracted_skills:
                    extracted_lower_item = extracted.lower().strip()
                    # Check for substring matches or common variations
                    if (expected_lower_item in extracted_lower_item or 
                        extracted_lower_item in expected_lower_item or
                        self._are_similar_skills(expected_lower_item, extracted_lower_item)):
                        best_match = extracted
                        break
            
            if best_match:
                matched_skills.append(expected)
                if best_match in extra_skills:
                    extra_skills.remove(best_match)
            else:
                missing_skills.append(expected)
        
        accuracy = len(matched_skills) / len(expected_skills) * 100 if expected_skills else 0
        return accuracy, missing_skills, extra_skills
    
    def _are_similar_skills(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are similar (e.g., 'simcorp dimension' vs 'sim corp dimension')"""
        # Handle common variations
        skill1_clean = skill1.replace(' ', '').replace('-', '').replace('_', '')
        skill2_clean = skill2.replace(' ', '').replace('-', '').replace('_', '')
        
        return skill1_clean == skill2_clean
    
    def check_format_compliance(self, extracted_skills: List[str]) -> Tuple[bool, List[str]]:
        """Check if output format meets Sandy's requirements"""
        format_issues = []
        
        for skill in extracted_skills:
            # Check for numbered lists
            if any(skill.strip().startswith(f"{i}.") for i in range(1, 20)):
                format_issues.append(f"Numbered list detected: '{skill}'")
            
            # Check for verbose descriptions
            if len(skill.split()) > 5:
                format_issues.append(f"Verbose description: '{skill}'")
            
            # Check for parenthetical explanations
            if '(' in skill and ')' in skill:
                format_issues.append(f"Parenthetical explanation: '{skill}'")
            
            # Check for skill suffix issues
            if any(suffix in skill.lower() for suffix in [' skills', ' abilities', ' knowledge']):
                format_issues.append(f"Verbose skill name: '{skill}'")
        
        is_compliant = len(format_issues) == 0
        return is_compliant, format_issues
    
    def validate_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single test case"""
        print(f"Testing: {test_case['name']}")
        
        start_time = time.time()
        
        try:
            # Extract skills using v3.3 specialist
            result = self.specialist.extract_skills(test_case['job_description'])
            extracted_skills = result.all_skills
            processing_time = time.time() - start_time
            
            # Calculate accuracy
            accuracy, missing_skills, extra_skills = self.calculate_accuracy(
                extracted_skills, test_case['expected_skills']
            )
            
            # Check format compliance
            format_compliant, format_issues = self.check_format_compliance(extracted_skills)
            
            test_result = {
                "test_id": test_case['id'],
                "test_name": test_case['name'],
                "accuracy_score": round(accuracy, 1),
                "format_compliant": format_compliant,
                "format_issues": format_issues,
                "processing_time": round(processing_time, 2),
                "extracted_skills": extracted_skills,
                "expected_skills": test_case['expected_skills'],
                "missing_skills": missing_skills,
                "extra_skills": extra_skills,
                "technical_skills": result.technical_skills,
                "soft_skills": result.soft_skills,
                "business_skills": result.business_skills
            }
            
            print(f"  Accuracy: {accuracy:.1f}% | Format: {'✓' if format_compliant else '✗'}")
            return test_result
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            return {
                "test_id": test_case['id'],
                "test_name": test_case['name'],
                "error": str(e),
                "accuracy_score": 0.0,
                "format_compliant": False
            }
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation against all test cases"""
        print("Content Extraction Specialist v3.3 PRODUCTION - Validation")
        print("=" * 60)
        
        # Load test cases
        test_data = self.load_golden_test_cases()
        test_cases = test_data.get('test_cases', [])
        
        print(f"Running {len(test_cases)} test cases...")
        
        # Validate each test case
        total_accuracy = 0
        total_format_compliant = 0
        
        for test_case in test_cases:
            result = self.validate_single_test(test_case)
            self.validation_results['test_results'].append(result)
            
            if 'accuracy_score' in result:
                total_accuracy += result['accuracy_score']
            if result.get('format_compliant', False):
                total_format_compliant += 1
        
        # Calculate overall metrics
        overall_accuracy = total_accuracy / len(test_cases) if test_cases else 0
        format_compliance_rate = (total_format_compliant / len(test_cases)) * 100 if test_cases else 0
        
        self.validation_results['overall_accuracy'] = f"{overall_accuracy:.1f}%"
        self.validation_results['format_compliance'] = f"{format_compliance_rate:.1f}%"
        
        # Summary
        self.validation_results['summary'] = {
            "total_tests": len(test_cases),
            "average_accuracy": f"{overall_accuracy:.1f}%",
            "format_compliance_rate": f"{format_compliance_rate:.1f}%",
            "production_ready": overall_accuracy >= 90.0 and format_compliance_rate >= 95.0,
            "recommendation": "APPROVED FOR PRODUCTION" if (overall_accuracy >= 90.0 and format_compliance_rate >= 95.0) else "REQUIRES FURTHER OPTIMIZATION"
        }
        
        print(f"\nValidation Complete:")
        print(f"Overall Accuracy: {overall_accuracy:.1f}%")
        print(f"Format Compliance: {format_compliance_rate:.1f}%")
        print(f"Production Ready: {'✓' if self.validation_results['summary']['production_ready'] else '✗'}")
        
        return self.validation_results
    
    def save_results(self, output_file: str):
        """Save validation results to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {output_file}")

def main():
    """Main validation execution"""
    test_file = "/home/xai/Documents/llm_factory/0_mailboxes/terminator@llm_factory/inbox/archive/golden_test_cases_content_extraction_v2.json"
    output_file = "validation_results_v3_3.json"
    
    validator = ProductionValidator(test_file)
    results = validator.run_validation()
    validator.save_results(output_file)
    
    return 0 if results['summary']['production_ready'] else 1

if __name__ == "__main__":
    sys.exit(main())
