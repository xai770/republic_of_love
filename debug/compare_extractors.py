#!/usr/bin/env python3
"""
Compare Fixed Technical Extractor vs v3.3 vs Daily Report
=========================================================

Test all three systems side by side to identify the best approach
"""

import sys
import time

# Add path for v3.3
sys.path.append("/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_crisis_resolution_20250702")

from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33
from technical_requirements_extractor_fixed import TechnicalRequirementsExtractor

def compare_extractors():
    print("🔧 EXTRACTION COMPARISON TEST")
    print("=" * 80)
    
    # Job #2: Network Security (the one that failed)
    network_job = """Senior Engineer (f/m/x) – Network Security Deployment Job ID:R0385218 Fachliche Kenntnisse im Bereich Netzwerk (Layer2/3, Routing und Switching); Netzwerk Security (Firewall, Proxy); Cloud. Deployment von sämtlichen Technologien (Router, Switche, Firewall, Proxy, etc.) Zusammenarbeit in einem internationalen Team, das für alle sämtliche Security-Bereiche innerhalb des Netzwerkes zuständig ist"""
    
    print("🎯 TEST JOB: Network Security Engineer")
    print("📋 Expected Skills: Layer2/3, Routing, Switching, Firewall, Proxy, Cloud, Router, Switches")
    print()
    
    # Test v3.3
    print("🔄 Testing v3.3 Specialist...")
    v33_specialist = ContentExtractionSpecialistV33()
    v33_result = v33_specialist.extract_skills(network_job)
    
    print("v3.3 Technical Skills:")
    for skill in v33_result.technical_skills[:10]:  # Show first 10
        print(f"  • {skill}")
    if len(v33_result.technical_skills) > 10:
        print(f"  ... and {len(v33_result.technical_skills) - 10} more")
    print()
    
    # Test Fixed Extractor
    print("🔄 Testing Fixed Extractor...")
    fixed_extractor = TechnicalRequirementsExtractor()
    fixed_result = fixed_extractor.extract_all_skills(network_job)
    
    print("Fixed Extractor Technical Skills:")
    for skill in fixed_result.technical_skills:
        print(f"  • {skill}")
    print()
    
    # Compare accuracy
    expected_skills = ["Layer2/3", "Layer 2/3", "Routing", "Switching", "Firewall", "Proxy", "Cloud", "Router", "Switches"]
    
    def check_accuracy(skills, name):
        found = 0
        for expected in expected_skills:
            if any(expected.lower() in skill.lower() or skill.lower() in expected.lower() for skill in skills):
                found += 1
        accuracy = (found / len(expected_skills)) * 100
        print(f"📊 {name} Accuracy: {accuracy:.1f}% ({found}/{len(expected_skills)})")
        return accuracy
    
    print("🏆 ACCURACY COMPARISON:")
    v33_accuracy = check_accuracy(v33_result.technical_skills, "v3.3 Specialist")
    fixed_accuracy = check_accuracy(fixed_result.technical_skills, "Fixed Extractor")
    
    print(f"\n📈 WINNER: {'Fixed Extractor' if fixed_accuracy > v33_accuracy else 'v3.3 Specialist'}")
    
    print(f"\n⏱️ PERFORMANCE:")
    print(f"v3.3 Processing Time: {v33_result.processing_time:.2f}s")
    print(f"Fixed Extractor Time: {fixed_result.processing_time:.2f}s")
    
    return fixed_accuracy > v33_accuracy

if __name__ == "__main__":
    compare_extractors()
