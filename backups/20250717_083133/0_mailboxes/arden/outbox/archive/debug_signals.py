#!/usr/bin/env python3
"""
Debug signal detection for Job 50571
"""

from content_extraction_specialist import ContentExtractionSpecialist
import json

def debug_signals():
    """Debug why transformation signal isn't being detected"""
    
    # Load Job 50571 data
    with open('../inbox/job50571_reprocessed_llm.json', 'r', encoding='utf-8') as f:
        job_data = json.load(f)
    
    raw_content = job_data['description']
    specialist = ContentExtractionSpecialist()
    
    print("🔍 DEBUGGING SIGNAL DETECTION")
    print("=" * 50)
    
    # Check if transformation-related text exists
    print(f"Raw content length: {len(raw_content)}")
    print(f"Contains 'transformation': {'transformation' in raw_content.lower()}")
    print(f"Contains 'Transformation': {'Transformation' in raw_content}")
    print(f"Contains 'transformations': {'transformations' in raw_content.lower()}")
    
    # Find all transformation-related words
    import re
    transform_pattern = re.compile(r'\b\w*transform\w*\b', re.IGNORECASE)
    transform_matches = transform_pattern.findall(raw_content)
    print(f"Transform-related words found: {transform_matches}")
    
    # Test extraction
    result = specialist.extract_core_content(raw_content, "50571")
    
    print(f"\nExtracted content length: {len(result.extracted_content)}")
    print(f"Domain signals found: {result.domain_signals}")
    
    # Check extracted content for transformation words
    extracted_transform_matches = transform_pattern.findall(result.extracted_content)
    print(f"Transform words in extracted content: {extracted_transform_matches}")
    
    # Test signal detection on extracted content
    signals = specialist._identify_domain_signals(result.extracted_content)
    print(f"Signals from extracted content: {signals}")
    
    # Test signal detection on raw content
    raw_signals = specialist._identify_domain_signals(raw_content)
    print(f"Signals from raw content: {raw_signals}")

if __name__ == "__main__":
    debug_signals()
