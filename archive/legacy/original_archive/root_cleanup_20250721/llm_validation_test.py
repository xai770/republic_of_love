#!/usr/bin/env python3
"""
LLM Validation Exercise - Phase 1: Single Job Testing
Tests Orrin's recommended LLMs with structured job extraction prompt
"""

import json
import time
import subprocess
import os
from datetime import datetime
from pathlib import Path

# Test configuration
MODELS_TO_TEST = [
    "gemma3n:latest",  # Currently used in V7.1
    "qwen3:latest",
    "dolphin3:8b", 
    "olmo2:latest",
    "mistral:latest"
]

TEST_JOB_FILE = "/home/xai/Documents/republic_of_love/data/postings/job63144.json"
STRUCTURED_PROMPT_FILE = "/home/xai/Documents/republic_of_love/structured_job_extraction_prompt.md"
OUTPUT_DIR = "/home/xai/Documents/republic_of_love/llm_validation_results"

def load_structured_prompt():
    """Load the structured extraction prompt"""
    with open(STRUCTURED_PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def load_test_job():
    """Load the test job description"""
    with open(TEST_JOB_FILE, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
        return job_data['job_content']['description']

def test_model_with_prompt(model_name, prompt, job_description):
    """Test a specific model with the structured prompt"""
    print(f"\n🔄 Testing {model_name}...")
    
    # Combine prompt and job description
    full_prompt = f"{prompt}\n\n---\n\n**Job Description to Extract:**\n\n{job_description}"
    
    # Create temporary prompt file
    temp_file = f"/tmp/llm_test_prompt_{model_name.replace(':', '_')}.txt"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    start_time = time.time()
    
    try:
        # Run ollama with the model using stdin
        with open(temp_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        result = subprocess.run([
            "ollama", "run", model_name
        ], input=prompt_content, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ {model_name} completed in {processing_time:.1f}s")
            return {
                "model": model_name,
                "success": True,
                "output": result.stdout,
                "processing_time": processing_time,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ {model_name} failed: {result.stderr}")
            return {
                "model": model_name,
                "success": False,
                "output": None,
                "processing_time": processing_time,
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {model_name} timed out after 5 minutes")
        return {
            "model": model_name,
            "success": False,
            "output": None,
            "processing_time": 300,
            "error": "Timeout after 5 minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"💥 {model_name} error: {str(e)}")
        return {
            "model": model_name,
            "success": False,
            "output": None,
            "processing_time": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

def save_results(results):
    """Save test results to file"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"{OUTPUT_DIR}/phase1_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Results saved to: {results_file}")
    return results_file

def run_phase1_validation():
    """Run Phase 1: Single Job Validation"""
    print("🚀 Starting LLM Validation Exercise - Phase 1")
    print("=" * 60)
    
    # Load components
    prompt = load_structured_prompt()
    job_description = load_test_job()
    
    print(f"📝 Loaded structured prompt ({len(prompt)} chars)")
    print(f"📄 Loaded test job: DWS Business Analyst (E-invoicing)")
    print(f"🎯 Testing {len(MODELS_TO_TEST)} models")
    
    results = {
        "phase": "Phase 1: Single Job Validation",
        "test_job": "DWS Business Analyst (E-invoicing) - R0383278",
        "test_date": datetime.now().isoformat(),
        "models_tested": [],
        "summary": {}
    }
    
    # Test each model
    for model in MODELS_TO_TEST:
        result = test_model_with_prompt(model, prompt, job_description)
        results["models_tested"].append(result)
    
    # Generate summary
    successful_tests = [r for r in results["models_tested"] if r["success"]]
    failed_tests = [r for r in results["models_tested"] if not r["success"]]
    
    results["summary"] = {
        "total_models": len(MODELS_TO_TEST),
        "successful": len(successful_tests),
        "failed": len(failed_tests),
        "success_rate": f"{len(successful_tests)/len(MODELS_TO_TEST)*100:.1f}%",
        "avg_processing_time": sum(r["processing_time"] for r in successful_tests) / len(successful_tests) if successful_tests else 0
    }
    
    # Save and display results
    results_file = save_results(results)
    
    print("\n📊 PHASE 1 SUMMARY")
    print("=" * 30)
    print(f"✅ Successful: {results['summary']['successful']}/{results['summary']['total_models']}")
    print(f"❌ Failed: {results['summary']['failed']}/{results['summary']['total_models']}")
    print(f"📈 Success Rate: {results['summary']['success_rate']}")
    if successful_tests:
        print(f"⏱️  Avg Time: {results['summary']['avg_processing_time']:.1f}s")
    
    print(f"\n🔍 Next Steps:")
    print(f"1. Review results in: {results_file}")
    print(f"2. Analyze output quality for successful models")
    print(f"3. Compare against V7.1 gold standard")
    print(f"4. Select top performers for Phase 2")
    
    return results

if __name__ == "__main__":
    results = run_phase1_validation()
