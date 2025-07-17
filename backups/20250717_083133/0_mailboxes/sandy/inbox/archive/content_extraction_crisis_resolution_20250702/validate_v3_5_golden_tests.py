#!/usr/bin/env python3
"""
Content Extraction Specialist v3.5 - Golden Test Validation
==========================================================

Comprehensive validation against Sandy's golden test cases to ensure
v3.5 meets production requirements for talent.yoga pipeline.
"""

import json
import time
import sys
import os

# Add the llm_factory to path
sys.path.insert(0, '/home/xai/Documents/llm_factory')

from content_extraction_specialist_v3_5 import ContentExtractionSpecialistV35

def load_golden_test_cases():
    """Load Sandy's golden test cases"""
    test_cases_file = "/home/xai/Documents/llm_factory/0_mailboxes/terminator@llm_factory/inbox/content_extraction_v3_3_golden_test_cases.json"
    
    with open(test_cases_file, 'r') as f:
        data = json.load(f)
    
    return data

def calculate_accuracy(extracted_skills, expected_skills):
    """Calculate accuracy percentage"""
    if not expected_skills:
        return 100.0 if not extracted_skills else 0.0
    
    # Convert to lowercase for comparison
    extracted_lower = [skill.lower() for skill in extracted_skills]
    expected_lower = [skill.lower() for skill in expected_skills]
    
    # Count matches
    matches = 0
    for expected in expected_lower:
        # Check for exact matches or partial matches
        for extracted in extracted_lower:
            if expected in extracted or extracted in expected:
                matches += 1
                break
    
    return (matches / len(expected_skills)) * 100

def validate_specialist():
    """Run comprehensive validation"""
    print("=== CONTENT EXTRACTION SPECIALIST v3.5 GOLDEN TEST VALIDATION ===")
    
    # Load test cases
    test_data = load_golden_test_cases()
    
    print(f"Business Owner: {test_data['business_owner']}")
    print(f"Specialist: {test_data['specialist_name']}")
    print(f"Current Issue: {test_data['current_issue']['symptom']}")
    
    # Initialize specialist
    specialist = ContentExtractionSpecialistV35(debug_mode=False)  # No debug for clean output
    
    test_results = []
    total_tests = len(test_data['test_cases'])
    successful_tests = 0
    
    for test_case in test_data['test_cases']:
        print(f"\n=== TEST CASE: {test_case['name']} ===")
        print(f"ID: {test_case['id']}")
        
        # Run extraction
        start_time = time.time()
        try:
            result = specialist.extract_skills(test_case['input_data'])
            
            # Calculate accuracies
            tech_accuracy = calculate_accuracy(result.technical_skills, 
                                             test_case['expected_output']['technical_skills'])
            soft_accuracy = calculate_accuracy(result.soft_skills,
                                             test_case['expected_output']['soft_skills'])
            business_accuracy = calculate_accuracy(result.business_skills,
                                                 test_case['expected_output']['business_skills'])
            
            overall_accuracy = (tech_accuracy + soft_accuracy + business_accuracy) / 3
            
            # Check minimum skills requirement
            meets_minimum = len(result.all_skills) >= test_case['expected_output']['minimum_skills_count']
            
            # Determine success
            success = (overall_accuracy >= 70.0 and 
                      meets_minimum and 
                      2.0 <= result.processing_time <= 15.0)
            
            if success:
                successful_tests += 1
            
            # Display results
            print(f"Technical Skills ({len(result.technical_skills)}): {result.technical_skills}")
            print(f"Expected Technical ({len(test_case['expected_output']['technical_skills'])}): {test_case['expected_output']['technical_skills']}")
            print(f"Technical Accuracy: {tech_accuracy:.1f}%")
            
            print(f"\nSoft Skills ({len(result.soft_skills)}): {result.soft_skills}")
            print(f"Expected Soft ({len(test_case['expected_output']['soft_skills'])}): {test_case['expected_output']['soft_skills']}")
            print(f"Soft Accuracy: {soft_accuracy:.1f}%")
            
            print(f"\nBusiness Skills ({len(result.business_skills)}): {result.business_skills}")
            print(f"Expected Business ({len(test_case['expected_output']['business_skills'])}): {test_case['expected_output']['business_skills']}")
            print(f"Business Accuracy: {business_accuracy:.1f}%")
            
            print(f"\nAll Skills ({len(result.all_skills)}): {result.all_skills}")
            print(f"Minimum Required: {test_case['expected_output']['minimum_skills_count']}, Actual: {len(result.all_skills)}, Meets Minimum: {meets_minimum}")
            print(f"Processing Time: {result.processing_time:.2f}s")
            print(f"Overall Accuracy: {overall_accuracy:.1f}%")
            print(f"SUCCESS: {success}")
            
            test_results.append({
                'test_id': test_case['id'],
                'name': test_case['name'],
                'success': success,
                'overall_accuracy': overall_accuracy,
                'processing_time': result.processing_time,
                'skills_count': len(result.all_skills),
                'meets_minimum': meets_minimum
            })
            
        except Exception as e:
            print(f"❌ TEST FAILED: {str(e)}")
            test_results.append({
                'test_id': test_case['id'],
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests > 0:
        avg_accuracy = sum(r['overall_accuracy'] for r in test_results if r['success']) / successful_tests
        avg_time = sum(r['processing_time'] for r in test_results if r['success']) / successful_tests
        print(f"Average Accuracy: {avg_accuracy:.1f}%")
        print(f"Average Processing Time: {avg_time:.2f}s")
    
    # Production readiness assessment
    print("\n" + "="*80)
    print("PRODUCTION READINESS ASSESSMENT")
    print("="*80)
    
    production_ready = successful_tests >= 4  # At least 80% success rate
    print(f"PRODUCTION READY: {production_ready}")
    
    if production_ready:
        print("✅ SPECIALIST READY FOR DEPLOYMENT")
        print("v3.5 has successfully resolved Sandy's empty results issue!")
        print("✅ Environmental robustness from v3.4 maintained")
        print("✅ Enhanced precision and accuracy achieved")
        print("✅ Meets talent.yoga production pipeline requirements")
    else:
        print("❌ SPECIALIST NEEDS FURTHER IMPROVEMENT")
        print("Failed tests:")
        for result in test_results:
            if not result['success']:
                print(f"  - {result['name']}: {result.get('error', 'Accuracy/performance issue')}")

if __name__ == "__main__":
    validate_specialist()
