#!/usr/bin/env python3
"""
Content Extraction Specialist v3.4 - Golden Test Validation
===========================================================

Validates v3.4 against Sandy's golden test cases to ensure production readiness.
Tests both accuracy and environmental robustness.

Date: July 2, 2025
"""

import json
import time
import sys
from typing import Dict, List, Any

# Import the v3.4 specialist
from content_extraction_specialist_v3_4 import ContentExtractionSpecialistV34

def load_golden_test_cases():
    """Load Sandy's golden test cases"""
    try:
        with open('/home/xai/Documents/llm_factory/0_mailboxes/terminator@llm_factory/inbox/content_extraction_v3_3_golden_test_cases.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading test cases: {e}")
        return None

def calculate_accuracy(expected: List[str], actual: List[str]) -> float:
    """Calculate accuracy as percentage of expected skills found"""
    if not expected:
        return 100.0 if not actual else 0.0
    
    expected_lower = [skill.lower() for skill in expected]
    actual_lower = [skill.lower() for skill in actual]
    
    found = 0
    for exp_skill in expected_lower:
        # Check for exact match or partial match
        if any(exp_skill in act_skill or act_skill in exp_skill for act_skill in actual_lower):
            found += 1
    
    return (found / len(expected)) * 100.0

def validate_test_case(specialist: ContentExtractionSpecialistV34, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single test case"""
    print(f"\n=== TEST CASE: {test_case['name']} ===")
    print(f"ID: {test_case['id']}")
    
    try:
        # Extract skills
        result = specialist.extract_skills(test_case['input_data'])
        
        # Calculate accuracies
        expected = test_case['expected_output']
        
        tech_accuracy = calculate_accuracy(expected.get('technical_skills', []), result.technical_skills)
        soft_accuracy = calculate_accuracy(expected.get('soft_skills', []), result.soft_skills)
        business_accuracy = calculate_accuracy(expected.get('business_skills', []), result.business_skills)
        overall_accuracy = (tech_accuracy + soft_accuracy + business_accuracy) / 3
        
        # Check minimum skills requirement
        min_required = expected.get('minimum_skills_count', 0)
        meets_minimum = len(result.all_skills) >= min_required
        
        # Determine success
        success = (
            overall_accuracy >= 70.0 and  # At least 70% accuracy
            meets_minimum and            # Meets minimum skill count
            result.processing_time <= 15.0 and  # Within time limit
            len(result.all_skills) > 0   # Not empty
        )
        
        # Print results
        print(f"Technical Skills ({len(result.technical_skills)}): {result.technical_skills[:5]}{'...' if len(result.technical_skills) > 5 else ''}")
        print(f"Expected Technical ({len(expected.get('technical_skills', []))}): {expected.get('technical_skills', [])}")
        print(f"Technical Accuracy: {tech_accuracy:.1f}%")
        
        print(f"\nSoft Skills ({len(result.soft_skills)}): {result.soft_skills[:5]}{'...' if len(result.soft_skills) > 5 else ''}")
        print(f"Expected Soft ({len(expected.get('soft_skills', []))}): {expected.get('soft_skills', [])}")
        print(f"Soft Accuracy: {soft_accuracy:.1f}%")
        
        print(f"\nBusiness Skills ({len(result.business_skills)}): {result.business_skills[:5]}{'...' if len(result.business_skills) > 5 else ''}")
        print(f"Expected Business ({len(expected.get('business_skills', []))}): {expected.get('business_skills', [])}")
        print(f"Business Accuracy: {business_accuracy:.1f}%")
        
        print(f"\nAll Skills ({len(result.all_skills)}): {result.all_skills[:8]}{'...' if len(result.all_skills) > 8 else ''}")
        print(f"Minimum Required: {min_required}, Actual: {len(result.all_skills)}, Meets Minimum: {meets_minimum}")
        print(f"Processing Time: {result.processing_time:.2f}s")
        print(f"Overall Accuracy: {overall_accuracy:.1f}%")
        print(f"SUCCESS: {success}")
        
        return {
            'test_id': test_case['id'],
            'name': test_case['name'],
            'success': success,
            'overall_accuracy': overall_accuracy,
            'tech_accuracy': tech_accuracy,
            'soft_accuracy': soft_accuracy,
            'business_accuracy': business_accuracy,
            'skills_count': len(result.all_skills),
            'processing_time': result.processing_time,
            'meets_minimum': meets_minimum,
            'debug_info': result.debug_info
        }
        
    except Exception as e:
        print(f"ERROR: Test case failed with exception: {e}")
        return {
            'test_id': test_case['id'],
            'name': test_case['name'],
            'success': False,
            'error': str(e),
            'overall_accuracy': 0.0,
            'skills_count': 0,
            'processing_time': 0.0
        }

def main():
    """Main validation function"""
    print("=== CONTENT EXTRACTION SPECIALIST v3.4 GOLDEN TEST VALIDATION ===")
    
    # Load test cases
    test_data = load_golden_test_cases()
    if not test_data:
        print("❌ Failed to load golden test cases")
        return
    
    print(f"Business Owner: {test_data['business_owner']}")
    print(f"Specialist: {test_data['specialist_name']}")
    print(f"Current Issue: {test_data['current_issue']['symptom']}")
    
    # Initialize specialist with debug mode for production debugging
    specialist = ContentExtractionSpecialistV34(
        debug_mode=True,
        strict_parsing=False  # Use relaxed parsing for production robustness
    )
    
    # Run all test cases
    results = []
    test_cases = test_data['test_cases']
    
    for test_case in test_cases:
        result = validate_test_case(specialist, test_case)
        results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (successful / total) * 100.0
    avg_accuracy = sum(r['overall_accuracy'] for r in results) / total
    avg_time = sum(r['processing_time'] for r in results) / total
    avg_skills = sum(r['skills_count'] for r in results) / total
    
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average Accuracy: {avg_accuracy:.1f}%")
    print(f"Average Processing Time: {avg_time:.2f}s")
    print(f"Average Skills Extracted: {avg_skills:.1f}")
    
    # Production readiness assessment
    print("\n" + "="*80)
    print("PRODUCTION READINESS ASSESSMENT")
    print("="*80)
    
    production_ready = (
        success_rate >= 80.0 and     # At least 80% success rate
        avg_accuracy >= 75.0 and     # At least 75% average accuracy
        avg_time <= 10.0 and         # Average time under 10s
        avg_skills >= 5.0             # At least 5 skills on average
    )
    
    print(f"PRODUCTION READY: {production_ready}")
    
    if production_ready:
        print("✅ SPECIALIST READY FOR DEPLOYMENT")
        print("Key improvements in v3.4:")
        print("  - Robust parsing handles environmental differences")
        print("  - Enhanced error handling and recovery")
        print("  - Comprehensive debugging for production troubleshooting")
        print("  - Backward compatibility with v3.3 interface")
        print("  - Multiple fallback mechanisms")
    else:
        print("❌ SPECIALIST NEEDS FURTHER IMPROVEMENT")
        failed_tests = [r for r in results if not r['success']]
        if failed_tests:
            print("Failed tests:")
            for failed in failed_tests:
                reason = failed.get('error', 'Accuracy/performance issue')
                print(f"  - {failed['name']}: {reason}")
    
    # Environmental robustness check
    print(f"\n=== ENVIRONMENTAL ROBUSTNESS ===")
    empty_results = sum(1 for r in results if r['skills_count'] == 0)
    if empty_results == 0:
        print("✅ NO EMPTY RESULTS - Environmental issue resolved!")
    else:
        print(f"❌ {empty_results} test cases still returning empty results")
    
    return production_ready

if __name__ == "__main__":
    try:
        production_ready = main()
        sys.exit(0 if production_ready else 1)
    except Exception as e:
        print(f"Validation failed with error: {e}")
        sys.exit(1)
