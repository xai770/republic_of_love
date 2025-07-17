#!/usr/bin/env python3
"""
Job 50571 Content Extraction Test - THE SMOKING GUN VALIDATION
==============================================================

Testing our Content Extraction Specialist against the actual problematic case
that's misclassified as 'investment_management' instead of 'management_consulting'
"""

import json
import sys
sys.path.append('/home/xai/Documents/republic_of_love/🌸_TEAM_COLLABORATION/arden@republic-of-love/outbox')

from content_extraction_specialist import ContentExtractionSpecialist

def main():
    # Load the problematic Job 50571 data
    with open('/home/xai/Documents/republic_of_love/🌸_TEAM_COLLABORATION/arden@republic-of-love/inbox/job50571_reprocessed_llm.json', 'r') as f:
        job_data = json.load(f)
    
    # Extract the raw bloated description
    raw_description = job_data['description']
    
    print("🚨 JOB 50571 CONTENT EXTRACTION VALIDATION")
    print("=" * 60)
    print(f"📊 CURRENT MISCLASSIFICATION: {job_data['domain_classification']['result']['primary_domain_classification']}")
    print(f"📊 CURRENT CONFIDENCE: {job_data['domain_classification']['result']['analysis_details']['domain_confidence']}")
    print(f"📊 CURRENT REASONING: {job_data['domain_classification']['result']['analysis_details']['domain_reasoning']}")
    print()
    
    print(f"📝 RAW CONTENT LENGTH: {len(raw_description)} characters")
    print()
    
    # Run our Content Extraction Specialist
    specialist = ContentExtractionSpecialist()
    result = specialist.extract_core_content(raw_description, "50571")
    
    print("🎯 CONTENT EXTRACTION RESULTS:")
    print("=" * 60)
    print(f"📉 CONTENT REDUCTION: {result.reduction_percentage:.1f}%")
    print(f"📊 ORIGINAL LENGTH: {result.original_length} chars")
    print(f"📊 EXTRACTED LENGTH: {result.extracted_length} chars")
    print(f"🎯 DOMAIN SIGNALS: {result.domain_signals}")
    print()
    
    print("✅ REMOVED SECTIONS:")
    for section in result.removed_sections[:5]:  # Show first 5
        print(f"   - {section}")
    if len(result.removed_sections) > 5:
        print(f"   ... and {len(result.removed_sections) - 5} more sections")
    print()
    
    print("🔍 CLEAN EXTRACTED CONTENT:")
    print("=" * 60)
    print(result.extracted_content)
    print()
    
    print("🚀 EXPECTED OUTCOME:")
    print("=" * 60)
    print("❌ BEFORE: investment_management (WRONG)")
    print("✅ AFTER:  management_consulting (CORRECT)")
    print("💡 REASONING: Clean content shows DBMC = Deutsche Bank Management Consulting")
    print("🎯 EVIDENCE: 'strategic projects', 'transformation', 'consulting', 'DBMC'")

if __name__ == "__main__":
    main()
