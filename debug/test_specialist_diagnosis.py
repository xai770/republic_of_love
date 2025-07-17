#!/usr/bin/env python3
"""
Test the job fitness evaluator specialist with real Ollama integration
Following LLM Factory methodology exactly
"""

import sys
import os
from typing import TYPE_CHECKING

sys.path.append('/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE')

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
    from llm_factory.modules.quality_validation.specialists_versioned.job_fitness_evaluator.v2_0.src.job_fitness_evaluator_specialist import JobFitnessEvaluatorSpecialist
else:
    # Runtime imports
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
    from llm_factory.modules.quality_validation.specialists_versioned.job_fitness_evaluator.v2_0.src.job_fitness_evaluator_specialist import JobFitnessEvaluatorSpecialist

def test_current_specialist():
    """Test the current specialist to diagnose parsing issues"""
    print("🔧 Testing Current Job Fitness Evaluator with Real Ollama...")
    print("=" * 60)
    
    # Set up configuration
    config = SpecialistConfig()
    specialist = JobFitnessEvaluatorSpecialist(config)
    
    # Test case from Terminator's report - Deutsche Bank professional
    test_data = {
        'job_posting': {
            'title': 'IT Operations Specialist - E-invoicing',
            'requirements': 'Financial services operations experience, process improvement, regulatory compliance knowledge, database management',
            'company_culture': 'Deutsche Bank - structured environment with focus on compliance and operational excellence',
            'company_name': 'Deutsche Bank'
        },
        'candidate_profile': {
            'name': 'Gershon Pollatschek',
            'skills': ['IT sourcing', 'vendor management', 'contract management', 'compliance', 'Python', 'database design'],
            'experience': '15+ years financial services, Deutsche Bank (2005-2010, 2020-Present), Software Escrow Management Project Lead',
            'background': 'Senior IT sourcing/vendor management professional with extensive Deutsche Bank experience'
        }
    }
    
    try:
        print("📤 Processing job evaluation...")
        result = specialist.process(test_data)
        
        print("✅ SUCCESS! Specialist returned result")
        print(f"📊 Result type: {type(result)}")
        print(f"📋 Result data: {result}")
        
        # Check if this should be a good match
        if hasattr(result, 'data') and 'fitness_score' in result.data:
            score = result.data['fitness_score']
            print(f"🎯 Fitness Score: {score}")
            if score < 50:
                print("⚠️  WARNING: Low score for what should be a good match!")
                print("🔍 This validates Terminator's concerns about overly conservative evaluation")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"🔍 Error type: {type(e)}")
        
        # Let's try to get more diagnostic information
        if "No match levels could be extracted" in str(e):
            print("🎯 FOUND THE PARSING ISSUE!")
            print("This is exactly what Terminator reported - response parsing failure")
            
            # Let's test the LLM response directly
            try:
                print("\n🧪 Testing raw LLM response...")
                test_prompt = specialist._create_assessment_prompt(test_data)
                raw_response = config.ollama_client.generate(
                    model=config.model,
                    prompt=test_prompt
                )
                print(f"📝 Raw LLM Response:")
                print("-" * 40)
                print(raw_response)
                print("-" * 40)
                print("Now we can see exactly what the LLM is returning and fix the parsing!")
                
            except Exception as raw_error:
                print(f"❌ Raw LLM test failed: {raw_error}")

if __name__ == "__main__":
    test_current_specialist()
