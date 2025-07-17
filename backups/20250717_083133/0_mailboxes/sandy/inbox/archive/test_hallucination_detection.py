#!/usr/bin/env python3
"""
Zero-dependency advanced test script for Location Validation Specialist LLM
Validates edge cases and anti-hallucination compliance (see README)
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from location_validation_specialist_llm import LocationValidationSpecialistLLM
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_edge_cases():
    print("\U0001F50D ADVANCED LLM HALLUCINATION DETECTION TESTS")
    print("=" * 60)
    specialist = LocationValidationSpecialistLLM()
    test_cases = [
        {"name": "Test 1: Frankfurt→Pune (Original)", "metadata": "Frankfurt", "description": "Join our team at Deutsche Bank Technology Center in Pune, India. This position is based in our state-of-the-art Pune office...", "expected_conflict": True, "expected_location": "Pune, India"},
        {"name": "Test 2: Berlin→Berlin (Original)", "metadata": "Berlin, Germany", "description": "We are looking for a software engineer to join our Berlin team. Great opportunities in our German headquarters...", "expected_conflict": False, "expected_location": "Berlin, Germany"},
        {"name": "Test 3: Multiple Mentions", "metadata": "London", "description": "This role is based in our London office. You will work closely with teams in Frankfurt, Berlin, and our main London headquarters...", "expected_conflict": False, "expected_location": "London"},
        {"name": "Test 4: Ambiguous References", "metadata": "Frankfurt", "description": "Work with global teams. Travel to various offices including Frankfurt, London, Pune. Home base to be determined.", "expected_conflict": False, "expected_location": "Frankfurt"},
        {"name": "Test 5: Context Bleeding Test", "metadata": "New York", "description": "Join our New York trading floor. Experience the energy of Wall Street in our Manhattan office.", "expected_conflict": False, "expected_location": "New York"},
        {"name": "Test 6: Same City Different Country", "metadata": "London", "description": "This position is located in London, Ontario, Canada. Great opportunity in our Canadian operations.", "expected_conflict": True, "expected_location": "London, Ontario, Canada"}
    ]
    results = []
    for i, test in enumerate(test_cases):
        print(f"\n\U0001F9EA {test['name']}")
        print(f"\U0001F4CD Metadata: {test['metadata']}")
        print(f"\U0001F4DD Description: {test['description'][:100]}...")
        print(f"\U0001F3AF Expected: conflict={test['expected_conflict']}, location={test['expected_location']}")
        try:
            result = specialist.validate_location(test['metadata'], test['description'], f"edge_test_{i+1}")
            print(f"\U0001F916 LLM Result: conflict={result.conflict_detected}, location={result.authoritative_location}")
            print(f"\U0001F4CA Confidence: {result.confidence_score}%")
            print(f"\U0001F4AD Reasoning: {result.analysis_details.get('reasoning', 'N/A')}")
            conflict_correct = result.conflict_detected == test['expected_conflict']
            location_reasonable = test['expected_location'].lower() in result.authoritative_location.lower()
            if conflict_correct and (location_reasonable or not test['expected_conflict']):
                print("\u2705 CORRECT")
                results.append("PASS")
            else:
                print("\u274C INCORRECT - Potential hallucination detected!")
                results.append("FAIL")
        except Exception as e:
            print(f"\U0001F4A5 ERROR: {str(e)}")
            results.append("ERROR")
    print(f"\n" + "=" * 60)
    print(f"\U0001F3AF HALLUCINATION DETECTION SUMMARY")
    print(f"Total Tests: {len(test_cases)}")
    print(f"Passed: {results.count('PASS')}")
    print(f"Failed: {results.count('FAIL')}")
    print(f"Errors: {results.count('ERROR')}")
    if results.count('FAIL') == 0:
        print("\u2705 NO HALLUCINATIONS DETECTED - LLM appears to be working correctly!")
    else:
        print("\u26A0\uFE0F HALLUCINATIONS DETECTED - Need prompt engineering fixes")
    return results

if __name__ == "__main__":
    test_edge_cases()
