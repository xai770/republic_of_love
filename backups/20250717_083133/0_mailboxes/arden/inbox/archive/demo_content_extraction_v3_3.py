#!/usr/bin/env python3
"""
Demo: Content Extraction Specialist v3.3 PRODUCTION
==================================================

Simple demonstration of the Content Extraction Specialist v3.3 PRODUCTION
Shows basic functionality with sample job descriptions

Usage: python demo_content_extraction_v3_3.py
Output: Console display of extracted skills

Date: June 27, 2025
Specialist: content_extraction_specialist_v3_3_PRODUCTION.py
"""

import sys
from pathlib import Path

# Import the v3.3 specialist
sys.path.append(str(Path(__file__).parent))
from content_extraction_specialist_v3_3_PRODUCTION import ContentExtractionSpecialistV33

def main():
    """Simple demo of v3.3 specialist"""
    print("Content Extraction Specialist v3.3 - Demo")
    print("=" * 45)
    
    specialist = ContentExtractionSpecialistV33()
    
    # Test with a sample job description
    sample_job = """
    Deutsche Bank seeks a Senior Developer with Python, Java, and SQL experience.
    Strong communication skills and leadership abilities required. Experience with
    Oracle databases and Excel analysis preferred. Fluent German and English essential.
    """
    
    print("Sample Job Description:")
    print(sample_job.strip())
    print()
    
    try:
        result = specialist.extract_skills(sample_job)
        
        print(f"✅ Extracted {len(result.all_skills)} skills in {result.processing_time:.2f}s")
        print()
        print("All Skills:")
        for skill in result.all_skills:
            print(f"  • {skill}")
        
        print()
        print("Skills by Category:")
        print(f"  Technical: {result.technical_skills}")
        print(f"  Soft: {result.soft_skills}")
        print(f"  Business: {result.business_skills}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please ensure Ollama is running with mistral:latest model")

if __name__ == "__main__":
    main()
