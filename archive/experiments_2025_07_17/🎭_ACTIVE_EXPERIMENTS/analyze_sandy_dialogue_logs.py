#!/usr/bin/env python3
"""
Direct Dialogue Log Analysis
===========================

Analyze Sandy's LLM comparison results directly from dialogue logs.
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

def extract_response_from_log(log_file: Path) -> Dict[str, Any]:
    """Extract response data from a dialogue log file"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract model name
        model_match = re.search(r'Model: ([^\n]+)', content)
        model_name = model_match.group(1) if model_match else "unknown"
        
        # Extract processing time
        time_match = re.search(r'Processing Time: ([\d.]+) seconds', content)
        processing_time = float(time_match.group(1)) if time_match else 0.0
        
        # Extract the actual response
        response_match = re.search(r'### Raw Response from Model:\s*```\s*(.*?)\s*```', content, re.DOTALL)
        response_text = response_match.group(1).strip() if response_match else ""
        
        # Determine test type from prompt
        if "Your Tasks" in content and "Your Profile" in content:
            test_type = "concise_extraction"
        elif "I only need the requirements" in content:
            test_type = "requirements_focus"
        elif "=== TECHNICAL REQUIREMENTS ===" in content:
            test_type = "structured_analysis"
        elif "=== SOFT SKILLS ===" in content:
            test_type = "skills_categorization"
        else:
            test_type = "unknown"
        
        return {
            "model_name": model_name,
            "processing_time": processing_time,
            "response_text": response_text,
            "response_length": len(response_text),
            "test_type": test_type,
            "success": len(response_text) > 50
        }
        
    except Exception as e:
        print(f"Error processing {log_file}: {e}")
        return {
            "model_name": "unknown",
            "processing_time": 0.0,
            "response_length": 0,
            "response_text": "",
            "test_type": "unknown",
            "success": False
        }

def assess_response_quality(response_text: str, test_type: str) -> Dict[str, Any]:
    """Assess the quality of a response"""
    
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
        scores.append(1.0)  # Bonus for basic success
    
    quality["overall_score"] = sum(scores) / max(len(scores), 1) if scores else 0.0
    
    return quality

def analyze_dialogue_logs():
    """Analyze all Sandy test dialogue logs"""
    
    dialogue_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
    sandy_logs = list(dialogue_dir.glob("20250716_190808_dialogue_*_sandy_test_*.md"))
    
    print(f"📊 Found {len(sandy_logs)} Sandy test dialogue logs")
    
    # Group by model
    model_results = defaultdict(lambda: {
        "prompts": [],
        "total_time": 0,
        "total_quality": 0,
        "successes": 0,
        "total_length": 0
    })
    
    # Model size mapping
    model_sizes = {
        "gemma3n:latest": 7.5, "gemma3n:e2b": 5.6, "gemma3:4b": 3.3, "gemma3:1b": 0.8,
        "qwen3:latest": 5.2, "qwen3:4b": 2.6, "qwen3:1.7b": 1.4, "qwen3:0.6b": 0.5,
        "qwen2.5vl:latest": 6.0, "deepseek-r1:8b": 4.9, "olmo2:latest": 4.5,
        "phi3:latest": 2.2, "phi3:3.8b": 2.2, "phi4-mini-reasoning:latest": 3.2,
        "mistral:latest": 4.1, "dolphin3:8b": 4.9, "dolphin3:latest": 4.9,
        "llama3.2:latest": 2.0, "codegemma:latest": 5.0, "codegemma:2b": 1.6,
    }
    
    # Process each log
    for log_file in sandy_logs:
        result = extract_response_from_log(log_file)
        if result:
            model_name = result["model_name"]
            
            # Assess quality
            quality = assess_response_quality(result["response_text"], result["test_type"])
            
            # Update model results
            model_results[model_name]["prompts"].append({
                "test_type": result["test_type"],
                "success": result["success"] and quality["overall_score"] > 0.6,
                "quality": quality["overall_score"],
                "processing_time": result["processing_time"],
                "response_length": result["response_length"],
                "follows_format": quality["follows_format"]
            })
            
            model_results[model_name]["total_time"] += result["processing_time"]
            model_results[model_name]["total_quality"] += quality["overall_score"]
            model_results[model_name]["total_length"] += result["response_length"]
            
            if result["success"] and quality["overall_score"] > 0.6:
                model_results[model_name]["successes"] += 1
    
    # Calculate final scores
    model_scores = {}
    for model_name, data in model_results.items():
        num_prompts = len(data["prompts"])
        if num_prompts == 0:
            continue
            
        success_rate = data["successes"] / num_prompts
        avg_quality = data["total_quality"] / num_prompts
        avg_time = data["total_time"] / num_prompts
        avg_length = data["total_length"] / num_prompts
        model_size = model_sizes.get(model_name, 0)
        
        # Count perfect format followers
        perfect_format = sum(1 for p in data["prompts"] if p["follows_format"])
        
        efficiency_score = (success_rate * avg_quality) / max(model_size, 0.1) if model_size > 0 else 0
        composite_score = (success_rate * 0.4) + (avg_quality * 0.4) + (max(0, 1 - avg_time/60) * 0.2)
        
        model_scores[model_name] = {
            "success_rate": success_rate,
            "avg_response_time": avg_time,
            "avg_quality": avg_quality,
            "avg_length": avg_length,
            "model_size": model_size,
            "efficiency_score": efficiency_score,
            "composite_score": composite_score,
            "perfect_format_count": perfect_format,
            "total_prompts": num_prompts
        }
    
    # Display results
    print("\n" + "=" * 90)
    print("🏆 SANDY PIPELINE LLM COMPARISON - DIRECT LOG ANALYSIS")
    print("=" * 90)
    
    # Sort by composite score
    sorted_models = sorted(model_scores.items(), key=lambda x: x[1]["composite_score"], reverse=True)
    
    print("\n🥇 OVERALL RANKING (by composite score):")
    print("-" * 90)
    print(f"{'Rank':<4} {'Model':<25} {'Score':<7} {'Success':<8} {'Quality':<8} {'Time':<7} {'Size':<7} {'Format':<7}")
    print("-" * 90)
    for i, (model_name, scores) in enumerate(sorted_models, 1):
        print(f"{i:2d}. {model_name:<25} {scores['composite_score']:.3f}   {scores['success_rate']:5.1%}    {scores['avg_quality']:.3f}    {scores['avg_response_time']:5.1f}s  {scores['model_size']:4.1f}GB  {scores['perfect_format_count']}/{scores['total_prompts']}")
    
    # Show efficiency ranking
    print("\n⚡ EFFICIENCY RANKING (Performance per GB):")
    print("-" * 70)
    efficiency_sorted = sorted(model_scores.items(), key=lambda x: x[1]["efficiency_score"], reverse=True)
    print(f"{'Rank':<4} {'Model':<25} {'Efficiency':<10} {'Size':<7} {'Success':<8}")
    print("-" * 70)
    for i, (model_name, scores) in enumerate(efficiency_sorted[:10], 1):
        if scores['model_size'] > 0:
            print(f"{i:2d}. {model_name:<25} {scores['efficiency_score']:.3f}      {scores['model_size']:4.1f}GB  {scores['success_rate']:5.1%}")
    
    # Show best small models
    print("\n🏃 BEST SMALL MODELS (< 3GB):")
    print("-" * 70)
    small_models = [(name, scores) for name, scores in sorted_models if scores['model_size'] < 3.0 and scores['model_size'] > 0]
    for i, (model_name, scores) in enumerate(small_models[:5], 1):
        print(f"{i}. {model_name:<25} | Score: {scores['composite_score']:.3f} | Size: {scores['model_size']:.1f}GB | Success: {scores['success_rate']:5.1%}")
    
    # Show format adherence champions
    print("\n🎯 FORMAT ADHERENCE CHAMPIONS:")
    print("-" * 70)
    format_sorted = sorted(model_scores.items(), key=lambda x: x[1]["perfect_format_count"], reverse=True)
    for i, (model_name, scores) in enumerate(format_sorted[:5], 1):
        if scores['perfect_format_count'] > 0:
            print(f"{i}. {model_name:<25} | {scores['perfect_format_count']}/{scores['total_prompts']} perfect formats | Quality: {scores['avg_quality']:.3f}")
    
    # Recommendations
    print("\n🎯 SANDY PIPELINE RECOMMENDATIONS:")
    print("-" * 70)
    
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
    
    print("\n" + "=" * 90)

if __name__ == "__main__":
    analyze_dialogue_logs()
