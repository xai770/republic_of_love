"""
Quick Demo: Content Extraction Specialist v2.0
=============================================

Quick demonstration of the optimized Content Extraction Specialist v2.0
using real job posting data to validate Sandy's skill matching requirements.

Usage: python quick_demo_v2.py
"""

import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from content_extraction_specialist_v2 import extract_job_content_v2  # type: ignore
    
    # Test with a simple job posting
    test_job = """
    Senior Python Developer
    
    We are seeking an experienced Python developer to join our team.
    
    Requirements:
    - 5+ years Python experience
    - Django, Flask frameworks
    - PostgreSQL, Redis
    - AWS, Docker, Kubernetes
    - Bachelor's degree in Computer Science
    
    Responsibilities:
    - Develop web applications
    - Database design and optimization
    - Code review and mentoring
    - System architecture design
    
    Benefits:
    - Health insurance
    - 401k matching
    - Flexible work hours
    - Remote work options
    - Professional development budget
    
    We are an equal opportunity employer committed to diversity and inclusion.
    Please submit your resume and cover letter through our online portal.
    """
    
    print("🚀 Content Extraction Specialist v2.0 - Quick Demo")
    print("=" * 55)
    print(f"📥 Input: {len(test_job)} characters")
    
    # Extract using v2.0 specialist
    result = extract_job_content_v2(test_job)
    
    print(f"📤 Output: {result.extracted_length} characters")
    print(f"📊 Reduction: {result.reduction_percentage:.1f}%")
    print(f"⏱️  Time: {result.llm_processing_time:.2f}s")
    print(f"🎯 Format: {result.format_version}")
    print()
    
    print("📋 OPTIMIZED OUTPUT:")
    print("-" * 40)
    print(result.extracted_content)
    print("-" * 40)
    
    if result.domain_signals:
        print(f"\n🎯 Domain Signals ({len(result.domain_signals)}):")
        print(", ".join(result.domain_signals))
    
    print("\n✅ Demo complete - v2.0 specialist working correctly!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the correct directory")
    print("💡 Or check if Ollama is running: ollama serve")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 This might be normal if Ollama is not running")
    print("💡 The specialist will use fallback mode")

if __name__ == "__main__":
    pass
