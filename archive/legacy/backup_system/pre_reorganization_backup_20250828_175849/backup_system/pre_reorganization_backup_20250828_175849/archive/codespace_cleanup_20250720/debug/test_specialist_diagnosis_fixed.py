#!/usr/bin/env python3
"""
Test script to diagnose job fitness evaluator specialist issues.
This will help us understand and fix the parsing/evaluation problems.
Following LLM Factory methodology exactly.
"""

import sys
import os
from typing import TYPE_CHECKING

# Add the LLM Factory to Python path
llm_factory_path = "/home/xai/Documents/republic_of_love/🏗️_LLM_INFRASTRUCTURE"
if llm_factory_path not in sys.path:
    sys.path.insert(0, llm_factory_path)

if TYPE_CHECKING:
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
    from llm_factory.modules.quality_validation.specialists_versioned.job_fitness_evaluator.v2_0.src.job_fitness_evaluator_specialist import JobFitnessEvaluatorSpecialist
else:
    # Runtime imports
    from llm_factory.core.ollama_client import OllamaClient
    from llm_factory.core.types import ModuleConfig
    from llm_factory.modules.quality_validation.specialists_versioned.job_fitness_evaluator.v2_0.src.job_fitness_evaluator_specialist import JobFitnessEvaluatorSpecialist

def test_job_fitness_evaluator():
    print("🔬 DIAGNOSING JOB FITNESS EVALUATOR SPECIALIST")
    print("=" * 60)
    
    # Initialize Ollama client
    try:
        client = OllamaClient()
        print("✅ Ollama client connected successfully")
        
        # Check available models
        models = client.available_models()
        print(f"📋 Available models: {models}")
        
        # Use llama3.2 if available, otherwise use first available model
        model_name = "llama3.2:latest" if "llama3.2:latest" in models else models[0]
        print(f"🤖 Using model: {model_name}")
        
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return
    
    # Create proper ModuleConfig as per LLM Factory pattern
    config = ModuleConfig(
        models=[model_name],
        conservative_bias=True,
        quality_threshold=8.0,
        ollama_client=client
    )
    
    # Create test data for German job market (Deutsche Bank background)
    test_data = {
        "candidate_profile": {
            "name": "xai",
            "background": "Deutsche Bank, 15+ years financial services",
            "skills": ["Python", "SQL", "Financial Analysis", "Risk Management", "German/English fluency"],
            "experience_level": "Senior",
            "location": "Germany",
            "preferences": {
                "industry": ["Finance", "Technology", "Consulting"],
                "company_size": ["Large Enterprise", "Mid-size"],
                "work_style": "Hybrid/Remote friendly"
            }
        },
        "job_posting": {
            "title": "Senior Data Analyst - Financial Services",
            "company": "European Investment Bank",
            "location": "Frankfurt, Germany",
            "description": "We seek a senior data analyst with banking experience to support risk analytics and regulatory reporting. Strong Python and SQL skills required. German language advantage.",
            "requirements": [
                "5+ years banking/financial services experience",
                "Advanced Python and SQL skills", 
                "Experience with risk management",
                "EU work authorization",
                "German language skills preferred"
            ],
            "benefits": ["Competitive salary", "Hybrid work", "Professional development"]
        },
        "use_adversarial": False  # Disable adversarial mode for cleaner diagnosis
    }
    
    print("\n📋 TEST DATA:")
    print(f"Candidate: {test_data['candidate_profile']['name']} (Deutsche Bank background)")
    print(f"Job: {test_data['job_posting']['title']} at {test_data['job_posting']['company']}")
    
    # Initialize and run the specialist
    try:
        specialist = JobFitnessEvaluatorSpecialist(config)
        print("\n✅ Specialist initialized successfully")
        
        print("\n🚀 Running job fitness evaluation...")
        result = specialist.process(test_data)
        
        print("\n📊 RESULTS:")
        print("=" * 40)
        print(f"Success: {result.get('success', 'Unknown')}")
        
        if 'data' in result:
            data = result['data']
            print(f"\nMatch Score: {data.get('match_score', 'Not found')}")
            print(f"Recommendation: {data.get('recommendation', 'Not found')}")
            print(f"Confidence: {data.get('confidence', 'Not found')}")
            
            if 'analysis' in data:
                analysis = data['analysis']
                print(f"\nSkill Match: {analysis.get('skill_match', 'Not found')}")
                print(f"Experience Match: {analysis.get('experience_match', 'Not found')}")
                print(f"Culture Fit: {analysis.get('culture_fit', 'Not found')}")
                
            if 'strengths' in data:
                print(f"\nStrengths: {data['strengths']}")
            if 'concerns' in data:
                print(f"Concerns: {data['concerns']}")
                
        if 'validation' in result:
            validation = result['validation']
            print(f"\nValidation Score: {validation.get('quality_score', 'Not found')}")
            print(f"Issues: {validation.get('issues', [])}")
            
        print(f"\nProcessing Time: {result.get('processing_time', 'Unknown')} seconds")
        
    except Exception as e:
        print(f"❌ Error running specialist: {e}")
        print(f"🔍 Error type: {type(e)}")
        
        # Let's try to get more diagnostic information
        print("\n🔍 DIAGNOSTIC MODE: Testing raw LLM response...")
        try:
            # Let's see if we can call methods directly to understand the parsing issue
            if hasattr(specialist, '_create_assessment_prompt'):
                test_prompt = specialist._create_assessment_prompt(test_data)
                print(f"📝 Generated prompt length: {len(test_prompt)} chars")
                
                # Try raw LLM call
                raw_response = client.generate(model=model_name, prompt=test_prompt)
                print(f"\n📤 Raw LLM Response:")
                print("-" * 40)
                print(raw_response[:500] + "..." if len(raw_response) > 500 else raw_response)
                print("-" * 40)
                
                # Try to understand what the parsing expects
                if hasattr(specialist, '_parse_assessment_response'):
                    print("\n🔧 Testing response parsing...")
                    try:
                        parsed = specialist._parse_assessment_response(raw_response)
                        print(f"✅ Parsing successful: {parsed}")
                    except Exception as parse_error:
                        print(f"❌ Parsing failed: {parse_error}")
                        print("This is likely the root cause of the issue!")
                        
        except Exception as diag_error:
            print(f"❌ Diagnostic test failed: {diag_error}")
            
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_job_fitness_evaluator()
