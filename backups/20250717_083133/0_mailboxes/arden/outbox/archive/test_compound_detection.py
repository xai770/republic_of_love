#!/usr/bin/env python3
"""
Quick test for compound word detection in domain signals.
"""

import re

def test_compound_detection():
    """Test if transformation is detected in Transformationsprojekten"""
    
    content = "Du arbeitest an strategischen Transformationsprojekten und übernimmst Verantwortung"
    signal = "transformation"
    
    print(f"Content: {content}")
    print(f"Signal: {signal}")
    print()
    
    # Test exact match
    if signal.lower() in content.lower():
        print("✅ Exact match found")
    else:
        print("❌ No exact match")
    
    # Test compound pattern
    pattern = re.compile(r'\b\w*' + re.escape(signal.lower()) + r'\w*\b', re.IGNORECASE)
    matches = pattern.findall(content)
    
    if matches:
        print(f"✅ Compound matches found: {matches}")
    else:
        print("❌ No compound matches")
    
    # Test pattern search
    match = pattern.search(content)
    if match:
        print(f"✅ Pattern search found: {match.group()}")
    else:
        print("❌ Pattern search failed")

if __name__ == "__main__":
    test_compound_detection()
