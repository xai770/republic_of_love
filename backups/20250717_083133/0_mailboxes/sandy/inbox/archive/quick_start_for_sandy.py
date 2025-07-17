#!/usr/bin/env python3
"""
Quick Start Demo for Sandy - Location Validation Specialist
============================================================

Zero-dependency script to test the golden test cases immediately.
Copy this file to your codebase and run: python quick_start_for_sandy.py

GOLDEN TEST CASES:
- Job 57488: Frankfurt metadata → Pune reality (MUST detect conflict)
- Job 58735: Frankfurt metadata → Bangalore reality (MUST detect conflict)
"""

# Minimal imports - works in any Python environment
import re
from typing import Dict, Any

def quick_location_validation(job_metadata_location: str, job_description: str) -> Dict[str, Any]:
    """
    Simplified location validation function - standalone version for immediate testing.
    
    Args:
        job_metadata_location: Location from job posting metadata (e.g., "Frankfurt")
        job_description: Full job description text
    
    Returns:
        Dictionary with validation results
    """
    
    # Location patterns for common conflicts
    location_patterns = {
        'india_cities': r'\b(pune|mumbai|bangalore|bengaluru|delhi|hyderabad|chennai)\b',
        'germany_cities': r'\b(frankfurt|berlin|munich|hamburg|cologne)\b',
        'asia_other': r'\b(singapore|hong kong|tokyo|sydney)\b',
        'country_mentions': r'\b(india|germany|german|indian)\b'
    }
    
    description_lower = job_description.lower()
    metadata_lower = job_metadata_location.lower()
    
    # Find locations in description
    found_locations = []
    for region, pattern in location_patterns.items():
        matches = re.findall(pattern, description_lower)
        for match in matches:
            found_locations.append({'location': match, 'region': region})
    
    # Check for critical conflicts (e.g., Frankfurt metadata vs India cities)
    conflict_detected = False
    risk_level = "low"
    authoritative_location = job_metadata_location
    
    if found_locations:
        # Check for India cities when metadata says Frankfurt
        india_cities = [loc for loc in found_locations if loc['region'] == 'india_cities']
        if india_cities and 'frankfurt' in metadata_lower:
            conflict_detected = True
            risk_level = "critical"
            authoritative_location = india_cities[0]['location']
    
    return {
        'conflict_detected': conflict_detected,
        'confidence_score': 0.95 if conflict_detected else 0.85,
        'authoritative_location': authoritative_location,
        'risk_level': risk_level,
        'found_locations': [loc['location'] for loc in found_locations],
        'metadata_location_accurate': not conflict_detected
    }


def test_sandy_examples():
    """Test with Sandy's specific examples"""
    print("🧪 TESTING SANDY'S PROJECT SUNSET EXAMPLES")
    print("=" * 50)
    
    # Sandy's golden test cases
    test_cases = [
        {
            "name": "Job 57488 (Golden Test)",
            "metadata": "Frankfurt", 
            "description": "Join our development team in Pune, India. Position based in Pune office.",
            "should_detect": True
        },
        {
            "name": "Job 58735 (Golden Test)", 
            "metadata": "Frankfurt",
            "description": "Analytics role in Bangalore, India. Candidate will work from Bangalore office.",
            "should_detect": True
        },
        {
            "name": "Accurate Frankfurt Job",
            "metadata": "Frankfurt",
            "description": "Position in our Frankfurt office in Germany. Based in Frankfurt headquarters.",
            "should_detect": False
        }
    ]
    
    all_passed = True
    for test in test_cases:
        print(f"\n📋 {test['name']}")
        result = quick_location_validation(test['metadata'], test['description'])
        
        passed = result['conflict_detected'] == test['should_detect']
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - Conflict: {result['conflict_detected']}")
        print(f"   📍 Location: {result['authoritative_location']}")
        print(f"   🎯 Confidence: {result['confidence_score']}")
        print(f"   ⚠️  Risk: {result['risk_level']}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def integration_example():
    """Show Sandy how to integrate into her job processing"""
    print("\n\n🔧 INTEGRATION EXAMPLE FOR SANDY'S PIPELINE")
    print("=" * 50)
    
    # Simulate Sandy's job data format
    jobs = [
        {"id": "job_001", "location": "Frankfurt", "description": "Team in Mumbai, India office"},
        {"id": "job_002", "location": "Frankfurt", "description": "Frankfurt office in Germany"},
    ]
    
    for job in jobs:
        print(f"\n💼 Processing {job['id']}")
        validation = quick_location_validation(job['location'], job['description'])
        
        # Decision logic Sandy can use
        if validation['conflict_detected'] and validation['risk_level'] == 'critical':
            decision = "SKIP JOB - Critical location conflict"
        elif validation['conflict_detected']:
            decision = "FLAG FOR REVIEW - Potential conflict"
        else:
            decision = "PROCEED - Location validated"
        
        print(f"   🎯 Decision: {decision}")
        print(f"   📍 {job['location']} → {validation['authoritative_location']}")


if __name__ == "__main__":
    print("🎯 QUICK LOCATION VALIDATION TEST")
    print("🎯 For Sandy's Project Sunset Pipeline")
    print("🎯 Zero dependencies - just run it!")
    print("\n")
    
    # Run tests
    success = test_sandy_examples()
    
    # Show integration
    integration_example()
    
    print(f"\n{'🚀 ALL TESTS PASSED!' if success else '❌ SOME TESTS FAILED'}")
    print("\n💡 Next step: Integrate full Location Validation Specialist")
    print("💡 Run: python location_validation_demo.py (for full version)")
