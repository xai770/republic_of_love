#!/usr/bin/env python3
"""
Validation Script for Content Extraction Specialist v2.1 - APPROACH A
=====================================================================

Testing our Dual-Purpose Prompt Redesign approach against Sandy's golden test cases.

APPROACH A STRATEGY:
- Phase 1: Extract ALL technical terms explicitly (no summarization)
- Phase 2: Clean content while protecting extracted skills
- Target: 90%+ skill extraction accuracy

Date: June 26, 2025
"""

import json
import sys
import time
from typing import List, Dict, Any
from pathlib import Path

# Import our new v2.1 specialist
from content_extraction_specialist_v2_1_approach_a import ContentExtractionSpecialistV21

def load_golden_test_cases() -> Dict[str, Any]:
    """Load Sandy's golden test cases."""
    try:
        with open('golden_test_cases_content_extraction_v2.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Golden test cases file not found!")
        sys.exit(1)

def calculate_skill_accuracy(expected_skills: List[str], extracted_content: str) -> tuple:
    """
    Calculate skill extraction accuracy using simple text matching.
    
    Returns:
        (accuracy_percentage, matched_skills, missed_skills, extra_skills)
    """
    if not expected_skills:
        return 100.0, [], [], []
    
    # Convert to lowercase for case-insensitive matching
    content_lower = extracted_content.lower()
    
    matched_skills = []
    missed_skills = []
    
    for skill in expected_skills:
        skill_lower = skill.lower()
        # Check if the skill appears in the extracted content
        if skill_lower in content_lower:
            matched_skills.append(skill)
        else:
            missed_skills.append(skill)
    
    accuracy = (len(matched_skills) / len(expected_skills)) * 100 if expected_skills else 0
    
    # Extract potential extra skills (basic heuristic)
    # Look for bullet points in Required Skills section
    import re
    skills_section = re.search(r'\*\*Required Skills:\*\*(.*?)(?:\*\*|$)', extracted_content, re.DOTALL)
    extra_skills = []
    if skills_section:
        skill_bullets = re.findall(r'^\s*[-•]\s*(.+)', skills_section.group(1), re.MULTILINE)
        # Find skills that aren't in expected list
        for bullet in skill_bullets:
            bullet_clean = bullet.strip().lower()
            if not any(expected.lower() in bullet_clean for expected in expected_skills):
                extra_skills.append(bullet.strip())
    
    return accuracy, matched_skills, missed_skills, extra_skills

def check_location_match(expected_location: str, extracted_content: str) -> bool:
    """Check if location is correctly extracted."""
    if not expected_location:
        return True
    
    # Simple location matching
    expected_lower = expected_location.lower()
    content_lower = extracted_content.lower()
    
    # Check for exact match or key location terms
    if expected_lower in content_lower:
        return True
    
    # Check for key location components
    location_parts = expected_lower.replace(',', ' ').split()
    for part in location_parts:
        if len(part) > 2 and part in content_lower:
            return True
    
    return False

def run_validation():
    """Run validation of APPROACH A against golden test cases."""
    print("🔥 Starting APPROACH A Validation - Dual-Purpose Prompt Redesign")
    print("=" * 80)
    print("🎯 TESTING: Skill-First Extraction with Protected Terms")
    print("📋 Business Owner: Sandy")
    print("🔧 Specialist: Content Extraction Specialist v2.1 - APPROACH A")
    print(f"📅 Test Date: {time.strftime('%Y-%m-%d')}")
    print("🏆 Success Criteria: 90%+ skill extraction accuracy")
    print()
    
    # Load test cases
    test_data = load_golden_test_cases()
    test_cases = test_data.get('test_cases', [])
    
    if not test_cases:
        print("❌ No test cases found!")
        return
    
    # Initialize specialist
    specialist = ContentExtractionSpecialistV21()
    
    # Track overall results
    total_tests = len(test_cases)
    successful_tests = 0
    total_skill_accuracy = 0.0
    total_location_matches = 0
    total_processing_time = 0.0
    total_content_reduction = 0.0
    
    detailed_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        test_id = test_case.get('id', f'test_{i}')
        test_name = test_case.get('name', 'Unknown Test')
        job_description = test_case.get('job_description', '')
        expected_skills = test_case.get('expected_skills', [])
        expected_location = test_case.get('expected_location', '')
        
        print(f"🧪 Testing {test_id}: {test_name}")
        print(f"📍 Expected location: {expected_location}")
        print(f"🎯 Expected skills ({len(expected_skills)}): {', '.join(expected_skills[:5])}{'...' if len(expected_skills) > 5 else ''}")
        
        # Process with our APPROACH A specialist
        try:
            result = specialist.extract_core_content(job_description, test_id)
            
            # Calculate metrics
            skill_accuracy, matched_skills, missed_skills, extra_skills = calculate_skill_accuracy(
                expected_skills, result.extracted_content
            )
            location_match = check_location_match(expected_location, result.extracted_content)
            
            # Update totals
            total_skill_accuracy += skill_accuracy
            total_processing_time += result.llm_processing_time
            total_content_reduction += result.reduction_percentage
            if location_match:
                total_location_matches += 1
            
            # Print results
            print(f"⏱️  Processing time: {result.llm_processing_time:.2f}s")
            print(f"📊 Content reduction: {result.reduction_percentage:.1f}%")
            print(f"🎯 Skill accuracy: {skill_accuracy:.1f}% ({len(matched_skills)}/{len(expected_skills)} matched)")
            print(f"📍 Location match: {'✅' if location_match else '❌'} ({expected_location})")
            
            if missed_skills:
                print(f"❌ Missed skills: {', '.join(missed_skills[:3])}{'...' if len(missed_skills) > 3 else ''}")
            if extra_skills:
                print(f"➕ Extra skills: {', '.join(extra_skills[:3])}{'...' if len(extra_skills) > 3 else ''}")
            
            # Store detailed results
            detailed_results.append({
                'test_id': test_id,
                'test_name': test_name,
                'skill_accuracy': skill_accuracy,
                'matched_skills': matched_skills,
                'missed_skills': missed_skills,
                'extra_skills': extra_skills,
                'location_match': location_match,
                'processing_time': result.llm_processing_time,
                'content_reduction': result.reduction_percentage,
                'extracted_content': result.extracted_content,
                'approach': 'A - Dual-Purpose Prompt Redesign'
            })
            
            successful_tests += 1
            
        except Exception as e:
            print(f"❌ Test {test_id} failed: {str(e)}")
            detailed_results.append({
                'test_id': test_id,
                'test_name': test_name,
                'error': str(e),
                'approach': 'A - Dual-Purpose Prompt Redesign'
            })
        
        print()
    
    # Calculate overall metrics
    avg_skill_accuracy = total_skill_accuracy / total_tests if total_tests > 0 else 0
    location_accuracy = (total_location_matches / total_tests) * 100 if total_tests > 0 else 0
    avg_processing_time = total_processing_time / total_tests if total_tests > 0 else 0
    avg_content_reduction = total_content_reduction / total_tests if total_tests > 0 else 0
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # Print summary
    print("=" * 80)
    print("📊 APPROACH A VALIDATION SUMMARY REPORT")
    print("=" * 80)
    print(f"📅 Validation Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🧪 Total Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {total_tests - successful_tests}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    print()
    print("🎯 PERFORMANCE METRICS:")
    print(f"   Skill Accuracy: {avg_skill_accuracy:.1f}%")
    print(f"   Location Accuracy: {location_accuracy:.1f}%")
    print(f"   Avg Processing Time: {avg_processing_time:.2f}s")
    print(f"   Avg Content Reduction: {avg_content_reduction:.1f}%")
    print()
    
    # Determine if we meet success criteria
    meets_criteria = avg_skill_accuracy >= 90.0
    print(f"🏆 MEETS SUCCESS CRITERIA: {'✅ YES' if meets_criteria else '❌ NO'}")
    print(f"   Required: 90%+ skill accuracy")
    print(f"   Achieved: {avg_skill_accuracy:.1f}%")
    print()
    
    if meets_criteria:
        print("🎉 APPROACH A SUCCESS! Ready for production optimization!")
    else:
        improvement_needed = 90.0 - avg_skill_accuracy
        print(f"📈 IMPROVEMENT NEEDED: +{improvement_needed:.1f} percentage points")
        print("🔄 Consider moving to APPROACH B or C")
    
    # Save detailed results
    results_file = f"validation_results_approach_a_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'validation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'approach': 'A - Dual-Purpose Prompt Redesign',
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'avg_skill_accuracy': avg_skill_accuracy,
                'location_accuracy': location_accuracy,
                'avg_processing_time': avg_processing_time,
                'avg_content_reduction': avg_content_reduction,
                'meets_criteria': meets_criteria
            },
            'detailed_results': detailed_results
        }, indent=2)
    
    print(f"💾 Detailed results saved to: {results_file}")
    
    # Exit with appropriate code
    sys.exit(0 if meets_criteria else 1)

if __name__ == "__main__":
    run_validation()
