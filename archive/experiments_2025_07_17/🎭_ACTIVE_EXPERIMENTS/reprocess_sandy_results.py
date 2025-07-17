#!/usr/bin/env python3
"""
Quick Results Reprocessor
========================

Re-analyze the saved results with improved quality assessment.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

def improved_quality_assessment(response_text: str, test_type: str) -> Dict[str, Any]:
    """Improved quality assessment of response"""
    
    quality = {
        "has_structure": False,
        "appropriate_length": False,
        "contains_keywords": False,
        "follows_format": False,
        "overall_score": 0.0
    }
    
    text_lower = response_text.lower()
    length = len(response_text)
    
    # Check appropriate length
    quality["appropriate_length"] = 100 < length < 5000
    
    # Test-type specific assessments
    if test_type == "concise_extraction":
        quality["has_structure"] = any(marker in text_lower for marker in [
            "your tasks", "your profile", "tasks:", "profile:", "responsibilities", 
            "requirements", "**your tasks**", "**your profile**", "## your", "# your"
        ])
        quality["contains_keywords"] = any(word in text_lower for word in [
            "experience", "skills", "knowledge", "ability", "degree", "coordination", 
            "management", "audit", "compliance"
        ])
        
    elif test_type == "requirements_focus":
        quality["contains_keywords"] = any(word in text_lower for word in [
            "requirement", "skill", "experience", "knowledge", "degree", "certification",
            "bachelor", "master", "education", "technical", "business"
        ])
        quality["has_structure"] = not any(phrase in text_lower for phrase in [
            "we offer", "company benefits", "kultur", "emotional ausgeglichen", 
            "körperlich fit", "finanziell abgesichert"
        ])
        
    elif test_type == "structured_analysis":
        quality["follows_format"] = ("=== TECHNICAL REQUIREMENTS ===" in response_text and 
                                   "=== BUSINESS REQUIREMENTS ===" in response_text)
        quality["has_structure"] = response_text.count("===") >= 2
        quality["contains_keywords"] = any(word in text_lower for word in [
            "critical", "important", "nice-to-have", "technical", "business", 
            "requirement", "skill", "knowledge"
        ])
        
    elif test_type == "skills_categorization":
        quality["follows_format"] = ("=== SOFT SKILLS ===" in response_text and
                                   ("=== EXPERIENCE REQUIRED ===" in response_text or
                                    "=== EDUCATION REQUIRED ===" in response_text))
        quality["has_structure"] = response_text.count("===") >= 2
        quality["contains_keywords"] = any(word in text_lower for word in [
            "communication", "leadership", "experience", "education", "degree",
            "teamwork", "collaboration", "management", "analytical"
        ])
    
    # Calculate overall score
    scores = []
    if quality["appropriate_length"]:
        scores.append(1.0)
    if quality["has_structure"]:
        scores.append(1.0)
    if quality["contains_keywords"]:
        scores.append(1.0)
    if quality["follows_format"]:
        scores.append(1.0)
    
    if quality["appropriate_length"] and quality["contains_keywords"]:
        scores.append(1.0)
    
    quality["overall_score"] = sum(scores) / max(len(scores), 1) if scores else 0.0
    
    return quality

def reprocess_results():
    """Reprocess the latest results file"""
    results_dir = Path("results/sandy_llm_comparison")
    
    # Find the latest results file
    results_files = list(results_dir.glob("sandy_llm_comparison_*.json"))
    if not results_files:
        print("No results files found!")
        return
    
    latest_file = max(results_files, key=lambda f: f.stat().st_mtime)
    print(f"📁 Processing: {latest_file}")
    
    # Load results
    with open(latest_file, 'r') as f:
        results = json.load(f)
    
    # Model size mapping
    model_sizes = {
        "gemma3n:latest": 7.5, "gemma3n:e2b": 5.6, "gemma3:4b": 3.3, "gemma3:1b": 0.8,
        "qwen3:latest": 5.2, "qwen3:4b": 2.6, "qwen3:1.7b": 1.4, "qwen3:0.6b": 0.5,
        "qwen2.5vl:latest": 6.0, "deepseek-r1:8b": 4.9, "olmo2:latest": 4.5,
        "phi3:latest": 2.2, "phi3:3.8b": 2.2, "phi4-mini-reasoning:latest": 3.2,
        "mistral:latest": 4.1, "dolphin3:8b": 4.9, "dolphin3:latest": 4.9,
        "llama3.2:latest": 2.0, "codegemma:latest": 5.0, "codegemma:2b": 1.6,
    }
    
    # Reprocess model results
    model_scores = {}
    
    for model_name, model_data in results["model_results"].items():
        if not model_data.get("available", False):
            continue
        
        prompt_results = model_data.get("prompt_results", {})
        
        # Re-assess each prompt result
        total_success = 0
        total_quality = 0
        total_time = 0
        total_length = 0
        
        for prompt_key, result in prompt_results.items():
            if result.get("response_text"):
                response_text = result["response_text"]
                test_type = result.get("test_type", "")
                
                # Re-assess quality
                new_quality = improved_quality_assessment(response_text, test_type)
                
                # Check success
                is_successful = (len(response_text) > 50 and 
                               new_quality.get("appropriate_length", False) and
                               new_quality.get("contains_keywords", False))
                
                if is_successful:
                    total_success += 1
                
                total_quality += new_quality.get("overall_score", 0)
                total_time += result.get("response_time", 0)
                total_length += result.get("response_length", 0)
        
        # Calculate metrics
        num_prompts = len(prompt_results)
        success_rate = total_success / num_prompts if num_prompts > 0 else 0
        avg_quality = total_quality / num_prompts if num_prompts > 0 else 0
        avg_time = total_time / num_prompts if num_prompts > 0 else 0
        avg_length = total_length / num_prompts if num_prompts > 0 else 0
        model_size = model_sizes.get(model_name, 0)
        
        efficiency_score = (success_rate * avg_quality) / max(model_size, 0.1) if model_size > 0 else 0
        composite_score = (success_rate * 0.4) + (avg_quality * 0.4) + (min(avg_time, 60) / 60 * 0.2)
        
        model_scores[model_name] = {
            "success_rate": success_rate,
            "avg_response_time": avg_time,
            "avg_quality": avg_quality,
            "avg_length": avg_length,
            "model_size": model_size,
            "efficiency_score": efficiency_score,
            "composite_score": composite_score
        }
    
    # Display results
    print("\n" + "=" * 80)
    print("🏆 REPROCESSED SANDY PIPELINE LLM COMPARISON RESULTS")
    print("=" * 80)
    
    # Sort by composite score
    sorted_models = sorted(model_scores.items(), key=lambda x: x[1]["composite_score"], reverse=True)
    
    print("\n🥇 OVERALL RANKING (by composite score):")
    print("-" * 80)
    print(f"{'Rank':<4} {'Model':<25} {'Score':<7} {'Success':<8} {'Quality':<8} {'Time':<7} {'Size(GB)':<9} {'Efficiency':<10}")
    print("-" * 80)
    for i, (model_name, scores) in enumerate(sorted_models, 1):
        print(f"{i:2d}. {model_name:<25} {scores['composite_score']:.3f}   {scores['success_rate']:5.1%}    {scores['avg_quality']:.3f}    {scores['avg_response_time']:5.1f}s  {scores['model_size']:5.1f}GB   {scores['efficiency_score']:.3f}")
    
    # Show efficiency ranking
    print("\n⚡ EFFICIENCY RANKING (Performance per GB):")
    print("-" * 80)
    efficiency_sorted = sorted(model_scores.items(), key=lambda x: x[1]["efficiency_score"], reverse=True)
    print(f"{'Rank':<4} {'Model':<25} {'Efficiency':<10} {'Size(GB)':<9} {'Quality':<8} {'Success':<8}")
    print("-" * 80)
    for i, (model_name, scores) in enumerate(efficiency_sorted[:10], 1):  # Top 10
        if scores['model_size'] > 0:
            print(f"{i:2d}. {model_name:<25} {scores['efficiency_score']:.3f}      {scores['model_size']:5.1f}GB   {scores['avg_quality']:.3f}    {scores['success_rate']:5.1%}")
    
    # Show best small models
    print("\n🏃 BEST SMALL MODELS (< 3GB):")
    print("-" * 60)
    small_models = [(name, scores) for name, scores in sorted_models if scores['model_size'] < 3.0 and scores['model_size'] > 0]
    for i, (model_name, scores) in enumerate(small_models[:5], 1):
        print(f"{i}. {model_name:<25} | Score: {scores['composite_score']:.3f} | Size: {scores['model_size']:.1f}GB | Success: {scores['success_rate']:5.1%}")
    
    # Recommendations
    print("\n🎯 SANDY PIPELINE RECOMMENDATIONS:")
    print("-" * 60)
    
    if sorted_models:
        best_model = sorted_models[0]
        current_model = "gemma3n:latest"
        
        current_score = model_scores.get(current_model, {}).get("composite_score", 0)
        
        if best_model[0] != current_model and best_model[1]["composite_score"] > current_score:
            improvement = ((best_model[1]["composite_score"] - current_score) / current_score * 100) if current_score > 0 else 0
            
            print(f"🚀 RECOMMENDED UPGRADE: {best_model[0]}")
            print(f"   Performance improvement: +{improvement:.1f}% over current {current_model}")
            print(f"   Better success rate: {best_model[1]['success_rate']:.1%} vs {model_scores.get(current_model, {}).get('success_rate', 0):.1%}")
            print(f"   Better quality: {best_model[1]['avg_quality']:.3f} vs {model_scores.get(current_model, {}).get('avg_quality', 0):.3f}")
            print(f"   Size: {best_model[1]['model_size']:.1f}GB vs {model_scores.get(current_model, {}).get('model_size', 0):.1f}GB")
        else:
            current_rank = next((i for i, (name, _) in enumerate(sorted_models, 1) if name == current_model), 0)
            print(f"✅ Current model {current_model} ranked #{current_rank}")
            print(f"   Success rate: {model_scores.get(current_model, {}).get('success_rate', 0):.1%}")
            print(f"   Quality score: {model_scores.get(current_model, {}).get('avg_quality', 0):.3f}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    reprocess_results()
