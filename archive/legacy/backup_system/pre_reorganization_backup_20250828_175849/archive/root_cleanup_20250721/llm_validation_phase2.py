#!/usr/bin/env python3
"""
LLM Validation Exercise - Phase 2: Multi-Job Testing
Tests top 3 models across 10 diverse job descriptions for consistency and scalability
"""

import json
import time
import subprocess
import os
from datetime import datetime
from pathlib import Path

# Phase 2 Configuration
TOP_3_MODELS = [
    "gemma3n:latest",   # 9.5/10 - Gold standard
    "qwen3:latest",     # 9.0/10 - Fast and excellent
    "dolphin3:8b"       # 8.0/10 - Fastest processing
]

# Selected diverse jobs for Phase 2 testing
PHASE_2_JOBS = [
    # Already tested in Phase 1 - baseline
    {"file": "job63144.json", "title": "DWS - Business Analyst (E-invoicing)", "category": "Business Analysis"},
    
    # Technical roles
    {"file": "job64640.json", "title": "Senior VMware Virtualization Engineer", "category": "Technology"},
    {"file": "job64976.json", "title": "Lead Engineer - Bare Metal as-a-Service", "category": "Technology"},
    {"file": "job63493.json", "title": "Senior Network Engineer - Zero Trust Networks", "category": "Technology"},
    
    # Finance & Risk roles
    {"file": "job56411.json", "title": "Senior Tax Analyst", "category": "Finance"},
    {"file": "job64841.json", "title": "Credit Analyst – CRM Leveraged Finance", "category": "Finance"},
    {"file": "job64981.json", "title": "Model Validation Senior Specialist", "category": "Risk"},
    
    # Leadership & Strategy roles
    {"file": "job64674.json", "title": "Fleet Operations Manager", "category": "Operations"},
    {"file": "job64726.json", "title": "Strategic Development Senior Analyst", "category": "Strategy"},
    
    # Security & Compliance
    {"file": "job59213.json", "title": "Information Security Specialist", "category": "Security"}
]

STRUCTURED_PROMPT_FILE = "/home/xai/Documents/republic_of_love/structured_job_extraction_prompt.md"
OUTPUT_DIR = "/home/xai/Documents/republic_of_love/llm_validation_results"
POSTINGS_DIR = "/home/xai/Documents/republic_of_love/data/postings"

def load_structured_prompt():
    """Load the structured extraction prompt"""
    with open(STRUCTURED_PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def load_job_description(job_file):
    """Load a specific job description"""
    file_path = os.path.join(POSTINGS_DIR, job_file)
    with open(file_path, 'r', encoding='utf-8') as f:
        job_data = json.load(f)
        return {
            "file": job_file,
            "title": job_data['job_content']['title'],
            "description": job_data['job_content']['description']
        }

def test_model_with_job(model_name, prompt, job_info):
    """Test a specific model with a job description"""
    print(f"  🔄 Testing {model_name} on {job_info['title'][:50]}...")
    
    # Combine prompt and job description
    full_prompt = f"{prompt}\n\n---\n\n**Job Description to Extract:**\n\n{job_info['description']}"
    
    start_time = time.time()
    
    try:
        # Run ollama with the model using stdin
        result = subprocess.run([
            "ollama", "run", model_name
        ], input=full_prompt, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result.returncode == 0:
            print(f"    ✅ Completed in {processing_time:.1f}s")
            return {
                "model": model_name,
                "job_file": job_info['file'],
                "job_title": job_info['title'],
                "success": True,
                "output": result.stdout,
                "processing_time": processing_time,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"    ❌ Failed: {result.stderr[:100]}...")
            return {
                "model": model_name,
                "job_file": job_info['file'],
                "job_title": job_info['title'],
                "success": False,
                "output": None,
                "processing_time": processing_time,
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        print(f"    ⏰ Timed out after 5 minutes")
        return {
            "model": model_name,
            "job_file": job_info['file'],
            "job_title": job_info['title'],
            "success": False,
            "output": None,
            "processing_time": 300,
            "error": "Timeout after 5 minutes",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"    💥 Error: {str(e)}")
        return {
            "model": model_name,
            "job_file": job_info['file'],
            "job_title": job_info['title'],
            "success": False,
            "output": None,
            "processing_time": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def analyze_phase2_results(results):
    """Analyze Phase 2 results for patterns and quality"""
    analysis = {
        "total_tests": len(results["test_results"]),
        "models": {},
        "jobs": {},
        "overall_stats": {}
    }
    
    # Analyze by model
    for model in TOP_3_MODELS:
        model_results = [r for r in results["test_results"] if r["model"] == model]
        successful = [r for r in model_results if r["success"]]
        
        analysis["models"][model] = {
            "total_jobs": len(model_results),
            "successful": len(successful),
            "failed": len(model_results) - len(successful),
            "success_rate": f"{len(successful)/len(model_results)*100:.1f}%" if model_results else "0%",
            "avg_processing_time": sum(r["processing_time"] for r in successful) / len(successful) if successful else 0,
            "min_time": min(r["processing_time"] for r in successful) if successful else 0,
            "max_time": max(r["processing_time"] for r in successful) if successful else 0
        }
    
    # Analyze by job category
    job_categories = {}
    for job in PHASE_2_JOBS:
        category = job["category"]
        if category not in job_categories:
            job_categories[category] = []
        
        job_results = [r for r in results["test_results"] if r["job_file"] == job["file"]]
        successful = [r for r in job_results if r["success"]]
        
        job_categories[category].append({
            "job_file": job["file"],
            "job_title": job["title"],
            "total_models": len(job_results),
            "successful_models": len(successful),
            "success_rate": f"{len(successful)/len(job_results)*100:.1f}%" if job_results else "0%"
        })
    
    analysis["job_categories"] = job_categories
    
    # Overall statistics
    all_successful = [r for r in results["test_results"] if r["success"]]
    analysis["overall_stats"] = {
        "total_tests": len(results["test_results"]),
        "successful_tests": len(all_successful),
        "overall_success_rate": f"{len(all_successful)/len(results['test_results'])*100:.1f}%",
        "avg_processing_time": sum(r["processing_time"] for r in all_successful) / len(all_successful) if all_successful else 0
    }
    
    return analysis

def save_phase2_results(results, analysis):
    """Save Phase 2 results and analysis"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw results
    results_file = f"{OUTPUT_DIR}/phase2_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Save analysis
    analysis_file = f"{OUTPUT_DIR}/phase2_analysis_{timestamp}.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    return results_file, analysis_file

def run_phase2_validation():
    """Run Phase 2: Multi-Job Validation"""
    print("🚀 Starting LLM Validation Exercise - Phase 2")
    print("=" * 60)
    
    # Load structured prompt
    prompt = load_structured_prompt()
    print(f"📝 Loaded structured prompt ({len(prompt)} chars)")
    print(f"🎯 Testing {len(TOP_3_MODELS)} models across {len(PHASE_2_JOBS)} diverse jobs")
    print(f"📊 Total tests: {len(TOP_3_MODELS) * len(PHASE_2_JOBS)}")
    
    results = {
        "phase": "Phase 2: Multi-Job Validation",
        "test_date": datetime.now().isoformat(),
        "models_tested": TOP_3_MODELS,
        "jobs_tested": PHASE_2_JOBS,
        "test_results": []
    }
    
    # Test each job with each model
    for i, job_config in enumerate(PHASE_2_JOBS, 1):
        print(f"\n📄 Job {i}/{len(PHASE_2_JOBS)}: {job_config['title']} ({job_config['category']})")
        
        # Load job description
        job_info = load_job_description(job_config['file'])
        
        # Test with each model
        for model in TOP_3_MODELS:
            result = test_model_with_job(model, prompt, job_info)
            results["test_results"].append(result)
    
    # Analyze results
    print(f"\n📊 Analyzing Phase 2 results...")
    analysis = analyze_phase2_results(results)
    
    # Save results
    results_file, analysis_file = save_phase2_results(results, analysis)
    
    # Display summary
    print(f"\n📈 PHASE 2 SUMMARY")
    print("=" * 40)
    print(f"✅ Total Tests: {analysis['overall_stats']['total_tests']}")
    print(f"✅ Successful: {analysis['overall_stats']['successful_tests']}")
    print(f"📈 Success Rate: {analysis['overall_stats']['overall_success_rate']}")
    print(f"⏱️  Avg Time: {analysis['overall_stats']['avg_processing_time']:.1f}s")
    
    print(f"\n🏆 MODEL PERFORMANCE:")
    for model, stats in analysis["models"].items():
        print(f"  {model}: {stats['success_rate']} ({stats['avg_processing_time']:.1f}s avg)")
    
    print(f"\n📁 Results saved:")
    print(f"  Raw data: {results_file}")
    print(f"  Analysis: {analysis_file}")
    
    print(f"\n🔍 Next Steps:")
    print(f"1. Review detailed results and model outputs")
    print(f"2. Assess quality consistency across job types")
    print(f"3. Select final model for ty_extract V10.0")
    
    return results, analysis

if __name__ == "__main__":
    results, analysis = run_phase2_validation()
