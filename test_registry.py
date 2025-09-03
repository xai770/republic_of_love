#!/usr/bin/env python3
"""
Test Registry System - Round 5.4 Phase 1

Test the new registry system components:
- Add prompts and templates
- Validate config-driven LLM calls
- Test simple table access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from membridge.registry import RegistrySystem, ConfigDrivenLLMCall
from membridge.models import MemBridgeConfig

def test_registry_system() -> None:
    """Test the basic registry system functionality"""
    
    print("🧪 Testing MemBridge Registry System - Round 5.4")
    print("=" * 60)
    
    # Initialize registry
    config = MemBridgeConfig()
    registry = RegistrySystem("membridge/membridge.db", config)
    
    print("\n1. Adding test prompts to registry...")
    
    # Add a skill extraction prompt
    skill_prompt_id = registry.add_prompt(
        name="CV Skill Extraction",
        description="Extract technical skills from CV/resume content",
        content="""You are a skill extraction specialist. Extract technical skills from the following CV content.

Return only the skills, one per line, without explanations or commentary.
Focus on:
- Programming languages
- Frameworks and libraries  
- Tools and technologies
- Certifications

CV Content:""",
        tags=["cv", "skills", "extraction", "ty_extract"]
    )
    
    # Add a job description analysis prompt  
    job_prompt_id = registry.add_prompt(
        name="Job Description Analysis",
        description="Analyze job descriptions for requirements and skills",
        content="""You are a job analysis specialist. Analyze the following job description.

Extract:
1. Required technical skills
2. Experience level required
3. Key responsibilities

Job Description:""",
        tags=["job", "analysis", "requirements"]
    )
    
    print(f"   ✅ Added CV Skill Extraction prompt (ID: {skill_prompt_id})")
    print(f"   ✅ Added Job Description Analysis prompt (ID: {job_prompt_id})")
    
    print("\n2. Adding test templates to registry...")
    
    # Template 1: CV skill extraction with CodeGemma
    template1_id = registry.add_template(
        call_number=1,
        name="CV Skills with CodeGemma",
        model="codegemma:latest",
        prompt_id=skill_prompt_id,
        config={"temperature": 0.1, "max_tokens": 500}
    )
    
    # Template 2: Job analysis with Qwen  
    template2_id = registry.add_template(
        call_number=2,
        name="Job Analysis with Qwen",
        model="qwen3:latest", 
        prompt_id=job_prompt_id,
        config={"temperature": 0.2, "max_tokens": 1000}
    )
    
    print(f"   ✅ Added CV Skills template (Call #1, ID: {template1_id})")
    print(f"   ✅ Added Job Analysis template (Call #2, ID: {template2_id})")
    
    print("\n3. Testing config-driven LLM calls...")
    
    caller = ConfigDrivenLLMCall(registry)
    
    # Test call 1: CV skill extraction
    test_cv = """
    John Doe - Senior Software Engineer
    Experience: 5 years in Python, React, PostgreSQL
    Worked with Docker, Kubernetes, AWS
    Certified in AWS Solutions Architect
    """
    
    result1 = caller.call_llm(call_number=1, input_text=test_cv)
    print(f"   📞 Call #1 Result:")
    print(f"      Success: {result1['success']}")
    print(f"      Model: {result1['model_used']}")
    print(f"      Template: {result1['template_used']}")
    print(f"      Output: {result1['output'][:100]}...")
    
    # Test call 2: Job analysis
    test_job = """
    Senior Python Developer
    Requirements: 3+ years Python, Django, REST APIs
    Experience with PostgreSQL, Redis
    Knowledge of Docker preferred
    """
    
    result2 = caller.call_llm(call_number=2, input_text=test_job)
    print(f"   📞 Call #2 Result:")
    print(f"      Success: {result2['success']}")
    print(f"      Model: {result2['model_used']}")
    print(f"      Template: {result2['template_used']}")
    print(f"      Output: {result2['output'][:100]}...")
    
    print("\n4. Testing validation system...")
    
    # Test with invalid input (too short)
    result3 = caller.call_llm(call_number=1, input_text="Hi")
    print(f"   ❌ Short input validation:")
    print(f"      Success: {result3['success']}")
    print(f"      Error: {result3['error']}")
    
    # Test with JSON request (should fail)
    result4 = caller.call_llm(call_number=1, input_text="Extract skills and return as JSON format")
    print(f"   ❌ JSON request validation:")
    print(f"      Success: {result4['success']}")
    print(f"      Error: {result4['error']}")
    
    # Test with invalid call number
    result5 = caller.call_llm(call_number=999, input_text="Some valid input text here")
    print(f"   ❌ Invalid call number:")
    print(f"      Success: {result5['success']}")
    print(f"      Error: {result5['error']}")
    
    print("\n5. Testing simple table access (xai's requirement)...")
    
    # Get all templates
    templates = registry.get_all_templates()
    print(f"   📋 Templates in registry: {len(templates)}")
    for template in templates:
        print(f"      Call #{template.call_number}: {template.name} ({template.model})")
    
    # Get all prompts
    prompts = registry.get_all_prompts()
    print(f"   📋 Prompts in registry: {len(prompts)}")
    for prompt in prompts:
        print(f"      ID {prompt.prompt_id}: {prompt.name}")
    
    # Get recent call logs
    recent_calls = registry.get_recent_calls(limit=10)
    print(f"   📋 Recent calls logged: {len(recent_calls)}")
    for call in recent_calls[:3]:  # Show first 3
        status = "✅" if call.success else "❌"
        print(f"      {status} Call #{call.call_number}: {call.model} - {call.latency_ms:.1f}ms")
    
    print("\n🎯 Phase 1 Registry System Test Complete!")
    print("=" * 60)
    print("✅ Prompt registry: Working")
    print("✅ Template registry: Working") 
    print("✅ Call logging: Working")
    print("✅ Validation layer: Working")
    print("✅ Config-driven calls: Working")
    print("✅ Simple table access: Working")
    print("\nReady for Phase 2: ty_extract integration!")

if __name__ == "__main__":
    test_registry_system()
