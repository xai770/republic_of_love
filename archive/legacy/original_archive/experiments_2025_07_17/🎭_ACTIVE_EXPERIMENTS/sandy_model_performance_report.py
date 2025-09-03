#!/usr/bin/env python3
"""
Sandy Model Performance Report Generator
========================================

Simple script to capture model performance data for sharing with team.
Outputs: Model name, response quality, processing time.
"""

import re
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

def extract_dialogue_data(log_file: Path) -> Dict[str, Any]:
    """Extract clean data from dialogue log"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract model name
        model_match = re.search(r'Model: ([^\n]+)', content)
        model_name = model_match.group(1) if model_match else "unknown"
        
        # Extract processing time
        time_match = re.search(r'Processing Time: ([\d.]+) seconds', content)
        processing_time = float(time_match.group(1)) if time_match else 0.0
        
        # Extract response
        response_match = re.search(r'### Raw Response from Model:\s*```\s*(.*?)\s*```', content, re.DOTALL)
        response_text = response_match.group(1).strip() if response_match else ""
        
        # Determine test type
        if "Your Tasks" in content and "Your Profile" in content:
            test_type = "Concise Job Description Extraction"
        elif "I only need the requirements" in content:
            test_type = "Requirements Focus Extraction"
        elif "=== TECHNICAL REQUIREMENTS ===" in content:
            test_type = "Structured Technical Analysis"
        elif "=== SOFT SKILLS ===" in content:
            test_type = "Skills Categorization"
        else:
            test_type = "Unknown"
        
        return {
            "model_name": model_name,
            "test_type": test_type,
            "processing_time": processing_time,
            "response_length": len(response_text),
            "response_text": response_text,
            "success": len(response_text) > 50
        }
        
    except Exception as e:
        print(f"Error processing {log_file}: {e}")
        return {
            "model_name": "error",
            "test_type": "error",
            "processing_time": 0.0,
            "response_length": 0,
            "response_text": "",
            "success": False
        }

def assess_quality(response_text: str, test_type: str) -> Dict[str, Any]:
    """Simple quality assessment"""
    text_lower = response_text.lower()
    
    # Basic quality checks
    has_structure = False
    contains_keywords = False
    follows_format = False
    
    if "Concise Job Description" in test_type:
        has_structure = any(marker in text_lower for marker in [
            "your tasks", "your profile", "tasks:", "profile:", "responsibilities"
        ])
        contains_keywords = any(word in text_lower for word in [
            "experience", "skills", "knowledge", "degree", "management"
        ])
    
    elif "Requirements Focus" in test_type:
        contains_keywords = any(word in text_lower for word in [
            "requirement", "skill", "experience", "degree", "education"
        ])
        has_structure = not any(phrase in text_lower for phrase in [
            "we offer", "company benefits", "kultur"
        ])
    
    elif "Structured Technical" in test_type:
        follows_format = ("=== TECHNICAL REQUIREMENTS ===" in response_text and 
                         "=== BUSINESS REQUIREMENTS ===" in response_text)
        has_structure = response_text.count("===") >= 2
        contains_keywords = any(word in text_lower for word in [
            "technical", "business", "requirement", "critical"
        ])
    
    elif "Skills Categorization" in test_type:
        follows_format = "=== SOFT SKILLS ===" in response_text
        has_structure = response_text.count("===") >= 2
        contains_keywords = any(word in text_lower for word in [
            "communication", "leadership", "teamwork", "management"
        ])
    
    # Calculate simple quality score
    quality_factors = [
        100 < len(response_text) < 5000,  # Appropriate length
        has_structure,
        contains_keywords,
        follows_format
    ]
    
    quality_score = sum(quality_factors) / len(quality_factors)
    
    return {
        "quality_score": quality_score,
        "has_structure": has_structure,
        "contains_keywords": contains_keywords,
        "follows_format": follows_format,
        "response_appropriate_length": 100 < len(response_text) < 5000
    }

def generate_performance_report():
    """Generate clean performance report for team sharing"""
    
    dialogue_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
    sandy_logs = list(dialogue_dir.glob("20250716_190808_dialogue_*_sandy_test_*.md"))
    
    print("🎯 Sandy Model Performance Report")
    print("=" * 60)
    print(f"📊 Analyzing {len(sandy_logs)} test results\n")
    
    # Model size reference
    model_sizes = {
        "gemma3n:latest": 7.5, "gemma3n:e2b": 5.6, "gemma3:4b": 3.3, "gemma3:1b": 0.8,
        "qwen3:latest": 5.2, "qwen3:4b": 2.6, "qwen3:1.7b": 1.4, "qwen3:0.6b": 0.5,
        "qwen2.5vl:latest": 6.0, "deepseek-r1:8b": 4.9, "olmo2:latest": 4.5,
        "phi3:latest": 2.2, "phi3:3.8b": 2.2, "phi4-mini-reasoning:latest": 3.2,
        "mistral:latest": 4.1, "dolphin3:8b": 4.9, "dolphin3:latest": 4.9,
        "llama3.2:latest": 2.0, "codegemma:latest": 5.0, "codegemma:2b": 1.6,
    }
    
    # Process logs
    model_data = defaultdict(lambda: {
        "tests": [],
        "total_time": 0,
        "total_quality": 0,
        "successes": 0
    })
    
    for log_file in sandy_logs:
        result = extract_dialogue_data(log_file)
        if result:
            model_name = result["model_name"]
            quality = assess_quality(result["response_text"], result["test_type"])
            
            test_result = {
                "test_type": result["test_type"],
                "processing_time": result["processing_time"],
                "response_length": result["response_length"],
                "quality_score": quality["quality_score"],
                "success": result["success"] and quality["quality_score"] > 0.5,
                "actual_response": result["response_text"][:1000] + "..." if len(result["response_text"]) > 1000 else result["response_text"]
            }
            
            model_data[model_name]["tests"].append(test_result)
            model_data[model_name]["total_time"] += result["processing_time"]
            model_data[model_name]["total_quality"] += quality["quality_score"]
            
            if test_result["success"]:
                model_data[model_name]["successes"] += 1
    
    # Calculate summary stats
    model_summary = {}
    for model_name, data in model_data.items():
        num_tests = len(data["tests"])
        if num_tests == 0:
            continue
            
        model_summary[model_name] = {
            "success_rate": data["successes"] / num_tests,
            "avg_processing_time": data["total_time"] / num_tests,
            "avg_quality_score": data["total_quality"] / num_tests,
            "model_size_gb": model_sizes.get(model_name, 0),
            "tests_completed": num_tests,
            "sample_responses": data["tests"][:2]  # Include first 2 responses as examples
        }
    
    # Sort by success rate, then by quality
    sorted_models = sorted(
        model_summary.items(), 
        key=lambda x: (x[1]["success_rate"], x[1]["avg_quality_score"]), 
        reverse=True
    )
    
    # Display results
    print("📋 MODEL PERFORMANCE SUMMARY")
    print("-" * 60)
    print(f"{'Model':<25} {'Success':<8} {'Quality':<8} {'Time':<7} {'Size':<6}")
    print("-" * 60)
    
    for model_name, stats in sorted_models:
        print(f"{model_name:<25} {stats['success_rate']:6.1%}   {stats['avg_quality_score']:6.3f}   {stats['avg_processing_time']:5.1f}s  {stats['model_size_gb']:4.1f}GB")
    
    # Top recommendations
    print("\n🏆 TOP PERFORMERS")
    print("-" * 40)
    
    # Best overall (100% success)
    perfect_models = [(name, stats) for name, stats in sorted_models if stats["success_rate"] == 1.0]
    
    if perfect_models:
        print("✅ Perfect Success Rate (100%):")
        for i, (model_name, stats) in enumerate(perfect_models[:5], 1):
            print(f"  {i}. {model_name} - Quality: {stats['avg_quality_score']:.3f}, Size: {stats['model_size_gb']:.1f}GB")
    
    # Most efficient (best performance per GB)
    print("\n⚡ Most Efficient (Performance per GB):")
    efficient_models = [
        (name, stats, stats['success_rate'] * stats['avg_quality_score'] / max(stats['model_size_gb'], 0.1))
        for name, stats in sorted_models if stats['model_size_gb'] > 0
    ]
    efficient_models.sort(key=lambda x: x[2], reverse=True)
    
    for i, (model_name, stats, efficiency) in enumerate(efficient_models[:5], 1):
        print(f"  {i}. {model_name} - Efficiency: {efficiency:.3f}, Size: {stats['model_size_gb']:.1f}GB")
    
    # Generate JSON export for programmatic use
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_models_tested": len(model_summary),
        "total_tests_run": sum(stats["tests_completed"] for stats in model_summary.values()),
        "model_results": {
            name: {
                "success_rate_percent": round(stats["success_rate"] * 100, 1),
                "avg_quality_score": round(stats["avg_quality_score"], 3),
                "avg_processing_time_seconds": round(stats["avg_processing_time"], 2),
                "model_size_gb": stats["model_size_gb"],
                "tests_completed": stats["tests_completed"],
                "sample_responses": [
                    {
                        "test_type": resp["test_type"],
                        "quality_score": round(resp["quality_score"], 3),
                        "success": resp["success"],
                        "response_length": resp["response_length"],
                        "actual_output": resp["actual_response"]
                    }
                    for resp in stats["sample_responses"]
                ]
            }
            for name, stats in model_summary.items()
        }
    }
    
    # Save JSON report
    report_file = Path("sandy_model_performance_report.json")
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    print("\n🎯 READY TO SHARE WITH TEAM")
    print("=" * 60)
    
    return report_data

if __name__ == "__main__":
    generate_performance_report()
