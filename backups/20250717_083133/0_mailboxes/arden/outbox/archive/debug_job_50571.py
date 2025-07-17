#!/usr/bin/env python3
"""
Debug signal detection for Job 50571
"""

import json
from content_extraction_specialist import ContentExtractionSpecialist

def debug_job_50571():
    """Debug signal detection for management consulting job."""
    
    # Load the job data
    with open('../inbox/job50571_reprocessed_llm.json', 'r') as f:
        job_data = json.load(f)
    
    print("Keys in job data:", list(job_data.keys()))
    
    # Try different possible content keys
    content_key = None
    for key in ['content', 'description', 'job_description', 'text', 'raw_content']:
        if key in job_data:
            content_key = key
            break
    
    if not content_key:
        print("No content found in job data!")
        return
    
    raw_content = job_data[content_key]
    print(f"Found content under key: {content_key}")
    print(f"Content length: {len(raw_content)} chars")
    print(f"Content preview: {raw_content[:200]}...")
    
    # Test the specialist
    specialist = ContentExtractionSpecialist()
    result = specialist.extract_core_content(raw_content, "50571")
    
    print(f"\nExtraction Results:")
    print(f"Reduction: {result.reduction_percentage:.1f}%")
    print(f"Domain signals found: {result.domain_signals}")
    
    # Test specific signal detection
    content_lower = result.extracted_content.lower()
    expected_signals = ['transformation', 'DBMC', 'consulting', 'strategic']
    
    print(f"\nTesting specific signals in extracted content:")
    for signal in expected_signals:
        if signal.lower() in content_lower:
            print(f"✅ Found: {signal}")
        else:
            print(f"❌ Missing: {signal}")
    
    print(f"\nExtracted content preview:")
    print(result.extracted_content[:500] + "...")

if __name__ == "__main__":
    debug_job_50571()
