#!/usr/bin/env python3
"""
Test V17 MemBridge Templates
===========================

Test the MemBridge templates that V17 would use and see the call results.
"""

import sys
from pathlib import Path

# Add membridge to path
sys.path.insert(0, str(Path(__file__).parent))

from membridge.registry import RegistrySystem, ConfigDrivenLLMCall
from membridge.models import MemBridgeConfig

def test_v17_templates() -> None:
    """Test V17 MemBridge templates with realistic job data"""
    
    print("🧪 V17 MemBridge Template Test")
    print("=" * 50)
    
    # Initialize MemBridge
    db_path = "data/membridge.db"
    config = MemBridgeConfig()
    registry = RegistrySystem(db_path=db_path, config=config)
    caller = ConfigDrivenLLMCall(registry)
    
    # Show baseline
    baseline_calls = registry.get_recent_calls(limit=100)
    baseline_count = len(baseline_calls)
    print(f"📊 Baseline calls in database: {baseline_count}")
    
    # Show available templates
    templates = registry.get_all_templates()
    print(f"\n🎯 Available Templates for V17:")
    for template in templates:
        if template.enabled:
            print(f"   • Call #{template.call_number}: {template.name}")
            print(f"     Model: {template.model}")
            print(f"     Config: {template.config}")
    
    # Realistic job posting data
    job_data = """Job Title: Senior Full Stack Developer

Job Description: We are seeking an experienced Senior Full Stack Developer to join our dynamic team. The ideal candidate will have 5+ years of experience in web development with expertise in Python, Django, React, and cloud technologies.

Key Responsibilities:
- Develop and maintain web applications using Python/Django backend
- Build responsive user interfaces with React and modern CSS
- Design and implement RESTful APIs
- Deploy applications to AWS cloud infrastructure
- Collaborate with cross-functional teams in an Agile environment

Required Skills:
- 5+ years of Python development experience
- Strong knowledge of Django framework
- Proficiency in React, JavaScript, HTML/CSS
- Experience with PostgreSQL and database design
- Familiarity with AWS services (EC2, RDS, S3)
- Git version control and CI/CD pipelines
- Strong problem-solving and communication skills

Nice to Have:
- Experience with Docker and Kubernetes
- Knowledge of microservices architecture
- Previous startup experience
- Computer Science degree or equivalent"""
    
    print(f"\n🎯 Testing Call #1 (Skills Extraction)...")
    result1 = caller.call_llm(
        call_number=1,
        input_text=job_data
    )
    
    print(f"✅ Call #1: {'SUCCESS' if result1['success'] else 'FAILED'}")
    print(f"   • Template: {result1['template_used']}")
    print(f"   • Model: {result1['model_used']}")
    print(f"   • Latency: {result1['latency_ms']:.1f}ms")
    print(f"   • Output Preview: {result1['output'][:150]}...")
    
    print(f"\n📝 Testing Call #2 (Concise Description)...")
    result2 = caller.call_llm(
        call_number=2,
        input_text=job_data
    )
    
    print(f"✅ Call #2: {'SUCCESS' if result2['success'] else 'FAILED'}")
    print(f"   • Template: {result2['template_used']}")
    print(f"   • Model: {result2['model_used']}")
    print(f"   • Latency: {result2['latency_ms']:.1f}ms")
    print(f"   • Output Preview: {result2['output'][:150]}...")
    
    # Show database updates
    new_calls = registry.get_recent_calls(limit=100)
    new_count = len(new_calls)
    added_calls = new_count - baseline_count
    
    print(f"\n📊 MemBridge Database Updates:")
    print(f"   • New calls added: {added_calls}")
    print(f"   • Total calls now: {new_count}")
    
    if added_calls > 0:
        print(f"\n🎯 Latest call entries:")
        for i, call in enumerate(new_calls[:added_calls], 1):
            status = "✅" if call.success else "❌"
            print(f"   {i}. {status} Call #{call.call_number} - {call.latency_ms:.1f}ms")
            print(f"      Input: {call.input_text[:80]}...")
            print(f"      Output: {call.output_text[:80]}...")
    
    print(f"\n🎯 V17 Template Testing Complete!")
    print(f"💡 These are the exact calls V17 would make through MemBridge")
    print(f"📊 Check SQLite Browser mb_log table for full details")

if __name__ == "__main__":
    test_v17_templates()
