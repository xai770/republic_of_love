#!/usr/bin/env python3
"""
Sandy Model Performance Report Generator with Baseline Comparison
===============================================================

Creates beautiful markdown reports with actual model outputs and compares
all models against the gemma3n:latest baseline (Sandy's current gold standard).
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime

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
        
        # Extract prompt for context
        prompt_match = re.search(r'### Prompt Sent to Model:\s*```\s*(.*?)\s*```', content, re.DOTALL)
        prompt_text = prompt_match.group(1).strip() if prompt_match else ""
        
        # Determine test type
        if "Your Tasks" in content and "Your Profile" in content:
            test_type = "Concise Job Description Extraction"
            test_id = "concise_extraction"
        elif "I only need the requirements" in content:
            test_type = "Requirements Focus Extraction"
            test_id = "requirements_focus"
        elif "=== TECHNICAL REQUIREMENTS ===" in content:
            test_type = "Structured Technical Analysis"
            test_id = "structured_analysis"
        elif "=== SOFT SKILLS ===" in content:
            test_type = "Skills Categorization"
            test_id = "skills_categorization"
        else:
            test_type = "Unknown"
            test_id = "unknown"
        
        return {
            "model_name": model_name,
            "test_type": test_type,
            "test_id": test_id,
            "processing_time": processing_time,
            "response_length": len(response_text),
            "response_text": response_text,
            "prompt_text": prompt_text,
            "success": len(response_text) > 50
        }
        
    except Exception as e:
        print(f"Error processing {log_file}: {e}")
        return {
            "model_name": "error",
            "test_type": "error",
            "test_id": "error",
            "processing_time": 0.0,
            "response_length": 0,
            "response_text": "",
            "prompt_text": "",
            "success": False
        }

def assess_quality(response_text: str, test_id: str) -> Dict[str, Any]:
    """Simple quality assessment"""
    text_lower = response_text.lower()
    
    # Basic quality checks
    has_structure = False
    contains_keywords = False
    follows_format = False
    
    if test_id == "concise_extraction":
        has_structure = any(marker in text_lower for marker in [
            "your tasks", "your profile", "tasks:", "profile:", "responsibilities"
        ])
        contains_keywords = any(word in text_lower for word in [
            "experience", "skills", "knowledge", "degree", "management"
        ])
    
    elif test_id == "requirements_focus":
        contains_keywords = any(word in text_lower for word in [
            "requirement", "skill", "experience", "degree", "education"
        ])
        has_structure = not any(phrase in text_lower for phrase in [
            "we offer", "company benefits", "kultur"
        ])
    
    elif test_id == "structured_analysis":
        follows_format = ("=== TECHNICAL REQUIREMENTS ===" in response_text and 
                         "=== BUSINESS REQUIREMENTS ===" in response_text)
        has_structure = response_text.count("===") >= 2
        contains_keywords = any(word in text_lower for word in [
            "technical", "business", "requirement", "critical"
        ])
    
    elif test_id == "skills_categorization":
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

def compare_to_baseline(model_response: str, baseline_response: str, test_id: str) -> Dict[str, Any]:
    """Compare model response to gemma3n:latest baseline"""
    
    # Length comparison
    length_ratio = len(model_response) / max(len(baseline_response), 1)
    
    # Structure similarity
    model_sections = model_response.count("===") if "===" in model_response else model_response.count("**")
    baseline_sections = baseline_response.count("===") if "===" in baseline_response else baseline_response.count("**")
    structure_similarity = min(model_sections, baseline_sections) / max(model_sections, baseline_sections, 1)
    
    # Key terms overlap
    model_words = set(model_response.lower().split())
    baseline_words = set(baseline_response.lower().split())
    key_terms = ["audit", "security", "management", "experience", "degree", "skills", "requirements", "coordination"]
    
    model_key_count = sum(1 for term in key_terms if term in model_words)
    baseline_key_count = sum(1 for term in key_terms if term in baseline_words)
    key_term_coverage = model_key_count / max(baseline_key_count, 1)
    
    # Format consistency
    format_consistency = 1.0
    if test_id == "structured_analysis":
        model_has_format = "=== TECHNICAL REQUIREMENTS ===" in model_response and "=== BUSINESS REQUIREMENTS ===" in model_response
        baseline_has_format = "=== TECHNICAL REQUIREMENTS ===" in baseline_response and "=== BUSINESS REQUIREMENTS ===" in baseline_response
        format_consistency = 1.0 if model_has_format == baseline_has_format else 0.5
    elif test_id == "skills_categorization":
        model_has_format = "=== SOFT SKILLS ===" in model_response
        baseline_has_format = "=== SOFT SKILLS ===" in baseline_response
        format_consistency = 1.0 if model_has_format == baseline_has_format else 0.5
    elif test_id == "concise_extraction":
        model_has_format = "your tasks" in model_response.lower() and "your profile" in model_response.lower()
        baseline_has_format = "your tasks" in baseline_response.lower() and "your profile" in baseline_response.lower()
        format_consistency = 1.0 if model_has_format == baseline_has_format else 0.5
    
    # Overall similarity score
    similarity_score = (length_ratio * 0.2 + structure_similarity * 0.3 + key_term_coverage * 0.3 + format_consistency * 0.2)
    similarity_score = min(similarity_score, 1.0)  # Cap at 1.0
    
    # Determine comparison verdict
    if similarity_score >= 0.8:
        verdict = "Excellent match"
        verdict_emoji = "🟢"
    elif similarity_score >= 0.6:
        verdict = "Good match"
        verdict_emoji = "🟡"
    elif similarity_score >= 0.4:
        verdict = "Fair match"
        verdict_emoji = "🟠"
    else:
        verdict = "Poor match"
        verdict_emoji = "🔴"
    
    return {
        "similarity_score": similarity_score,
        "length_ratio": length_ratio,
        "structure_similarity": structure_similarity,
        "key_term_coverage": key_term_coverage,
        "format_consistency": format_consistency,
        "verdict": verdict,
        "verdict_emoji": verdict_emoji
    }

def generate_baseline_comparison_report():
    """Generate comprehensive report with baseline comparison"""
    
    dialogue_dir = Path("/home/xai/Documents/republic_of_love/llm_dialogues")
    sandy_logs = list(dialogue_dir.glob("20250716_190808_dialogue_*_sandy_test_*.md"))
    
    # Model size reference
    model_sizes = {
        "gemma3n:latest": 7.5, "gemma3n:e2b": 5.6, "gemma3:4b": 3.3, "gemma3:1b": 0.8,
        "qwen3:latest": 5.2, "qwen3:4b": 2.6, "qwen3:1.7b": 1.4, "qwen3:0.6b": 0.5,
        "qwen2.5vl:latest": 6.0, "deepseek-r1:8b": 4.9, "olmo2:latest": 4.5,
        "phi3:latest": 2.2, "phi3:3.8b": 2.2, "phi4-mini-reasoning:latest": 3.2,
        "mistral:latest": 4.1, "dolphin3:8b": 4.9, "dolphin3:latest": 4.9,
        "llama3.2:latest": 2.0, "codegemma:latest": 5.0, "codegemma:2b": 1.6,
    }
    
    BASELINE_MODEL = "gemma3n:latest"
    
    # Process logs
    model_data = defaultdict(lambda: {
        "tests": [],
        "total_time": 0,
        "total_quality": 0,
        "successes": 0,
        "baseline_comparisons": []
    })
    
    # Store baseline responses for comparison
    baseline_responses = {}
    
    for log_file in sandy_logs:
        result = extract_dialogue_data(log_file)
        if result and result["model_name"] != "error":
            model_name = result["model_name"]
            quality = assess_quality(result["response_text"], result["test_id"])
            
            test_result = {
                "test_type": result["test_type"],
                "test_id": result["test_id"],
                "processing_time": result["processing_time"],
                "response_length": result["response_length"],
                "quality_score": quality["quality_score"],
                "success": result["success"] and quality["quality_score"] > 0.5,
                "response_text": result["response_text"],
                "prompt_text": result["prompt_text"]
            }
            
            # Store baseline responses
            if model_name == BASELINE_MODEL:
                baseline_responses[result["test_id"]] = result["response_text"]
            
            model_data[model_name]["tests"].append(test_result)
            model_data[model_name]["total_time"] += result["processing_time"]
            model_data[model_name]["total_quality"] += quality["quality_score"]
            
            if test_result["success"]:
                model_data[model_name]["successes"] += 1
    
    # Now compare all models to baseline
    for model_name, data in model_data.items():
        if model_name == BASELINE_MODEL:
            continue
            
        for test in data["tests"]:
            test_id = test["test_id"]
            if test_id in baseline_responses:
                comparison = compare_to_baseline(
                    test["response_text"], 
                    baseline_responses[test_id], 
                    test_id
                )
                test["baseline_comparison"] = comparison
                data["baseline_comparisons"].append(comparison)
    
    # Calculate summary stats
    model_summary = {}
    for model_name, data in model_data.items():
        num_tests = len(data["tests"])
        if num_tests == 0:
            continue
            
        # Calculate baseline similarity average
        avg_similarity = 0.0
        if model_name != BASELINE_MODEL and data["baseline_comparisons"]:
            avg_similarity = sum(comp["similarity_score"] for comp in data["baseline_comparisons"]) / len(data["baseline_comparisons"])
        elif model_name == BASELINE_MODEL:
            avg_similarity = 1.0  # Baseline matches itself perfectly
            
        model_summary[model_name] = {
            "success_rate": data["successes"] / num_tests,
            "avg_processing_time": data["total_time"] / num_tests,
            "avg_quality_score": data["total_quality"] / num_tests,
            "model_size_gb": model_sizes.get(model_name, 0),
            "tests_completed": num_tests,
            "tests": data["tests"],
            "avg_baseline_similarity": avg_similarity,
            "is_baseline": model_name == BASELINE_MODEL
        }
    
    # Sort by baseline similarity, then by success rate
    sorted_models = sorted(
        model_summary.items(), 
        key=lambda x: (x[1]["avg_baseline_similarity"], x[1]["success_rate"]), 
        reverse=True
    )
    
    # Generate markdown report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_content = f"""# 🎯 Sandy Model Performance Report with Baseline Comparison

**Generated:** {timestamp}  
**Total Models Tested:** {len(model_summary)}  
**Total Test Scenarios:** {sum(stats["tests_completed"] for stats in model_summary.values())}  
**Test Data:** Deutsche Bank Relationship Manager Position  
**Baseline Model:** `{BASELINE_MODEL}` (Sandy's Current Gold Standard)

---

## 📊 Executive Summary

### 🏆 Top Performing Models (Compared to Baseline)

| Rank | Model | Baseline Similarity | Success Rate | Quality Score | Size (GB) | Status |
|------|-------|-------------------|--------------|---------------|-----------|--------|
"""
    
    # Add top 10 models to summary table
    for i, (model_name, stats) in enumerate(sorted_models[:10], 1):
        status = "🥇 BASELINE" if stats["is_baseline"] else "📈 ALTERNATIVE"
        report_content += f"| {i} | `{model_name}` | {stats['avg_baseline_similarity']:.3f} | {stats['success_rate']:.1%} | {stats['avg_quality_score']:.3f} | {stats['model_size_gb']:.1f} | {status} |\n"
    
    # Key insights
    perfect_similarity = [name for name, stats in sorted_models if stats["avg_baseline_similarity"] >= 0.9 and not stats["is_baseline"]]
    good_alternatives = [name for name, stats in sorted_models if 0.7 <= stats["avg_baseline_similarity"] < 0.9 and not stats["is_baseline"]]
    
    baseline_stats = model_summary[BASELINE_MODEL]
    
    report_content += f"""

### 🎯 Baseline Comparison Insights

- **Perfect Similarity (≥90%):** {len(perfect_similarity)} models match baseline quality
- **Good Alternatives (70-89%):** {len(good_alternatives)} models are viable replacements
- **Baseline Performance:** {baseline_stats['success_rate']:.1%} success, {baseline_stats['avg_quality_score']:.3f} quality, {baseline_stats['model_size_gb']:.1f}GB
- **Best Alternative:** `{sorted_models[1][0] if len(sorted_models) > 1 else 'None'}` ({sorted_models[1][1]['avg_baseline_similarity']:.3f} similarity)

### 🚀 Upgrade Recommendations

"""
    
    # Find best alternatives by category
    smaller_alternatives = [(name, stats) for name, stats in sorted_models 
                          if not stats["is_baseline"] and stats["model_size_gb"] < baseline_stats["model_size_gb"] 
                          and stats["avg_baseline_similarity"] >= 0.7]
    
    if smaller_alternatives:
        best_small = smaller_alternatives[0]
        size_reduction = ((baseline_stats["model_size_gb"] - best_small[1]["model_size_gb"]) / baseline_stats["model_size_gb"]) * 100
        report_content += f"""**🏃 Best Smaller Alternative:** `{best_small[0]}`
- **Size Reduction:** {size_reduction:.1f}% smaller ({best_small[1]['model_size_gb']:.1f}GB vs {baseline_stats['model_size_gb']:.1f}GB)
- **Baseline Similarity:** {best_small[1]['avg_baseline_similarity']:.3f}
- **Success Rate:** {best_small[1]['success_rate']:.1%}

"""
    
    # Best overall alternative
    if len(sorted_models) > 1 and not sorted_models[1][1]["is_baseline"]:
        best_alt = sorted_models[1]
        report_content += f"""**🏆 Best Overall Alternative:** `{best_alt[0]}`
- **Baseline Similarity:** {best_alt[1]['avg_baseline_similarity']:.3f}
- **Success Rate:** {best_alt[1]['success_rate']:.1%}
- **Quality Score:** {best_alt[1]['avg_quality_score']:.3f}

"""
    
    report_content += f"""---

## 🧪 Test Scenarios

Sandy's pipeline was tested on 4 different specialist prompts:

1. **Concise Job Description Extraction** - Extract key tasks and profile requirements
2. **Requirements Focus Extraction** - Focus only on candidate requirements
3. **Structured Technical Analysis** - Categorize technical vs business requirements
4. **Skills Categorization** - Separate soft skills, experience, and education

---

## 📋 Detailed Model Results with Baseline Comparison

"""
    
    # Add detailed results for each model
    for model_name, stats in sorted_models:
        if stats["is_baseline"]:
            status_emoji = "🥇"
            status_text = "BASELINE MODEL"
        elif stats["avg_baseline_similarity"] >= 0.9:
            status_emoji = "🟢"
            status_text = f"EXCELLENT MATCH ({stats['avg_baseline_similarity']:.3f})"
        elif stats["avg_baseline_similarity"] >= 0.7:
            status_emoji = "🟡"
            status_text = f"GOOD ALTERNATIVE ({stats['avg_baseline_similarity']:.3f})"
        elif stats["avg_baseline_similarity"] >= 0.5:
            status_emoji = "🟠"
            status_text = f"FAIR ALTERNATIVE ({stats['avg_baseline_similarity']:.3f})"
        else:
            status_emoji = "🔴"
            status_text = f"POOR MATCH ({stats['avg_baseline_similarity']:.3f})"
        
        report_content += f"""### {status_emoji} {model_name}

**Performance Metrics:**
- Success Rate: **{stats['success_rate']:.1%}**
- Quality Score: **{stats['avg_quality_score']:.3f}**
- Model Size: **{stats['model_size_gb']:.1f}GB**
- Processing Time: **{stats['avg_processing_time']:.2f}s**
- **Baseline Similarity: {status_text}**

"""
        
        # Add sample outputs for each test type with baseline comparison
        test_types = {}
        for test in stats["tests"]:
            if test["test_type"] not in test_types:
                test_types[test["test_type"]] = test
        
        for test_type, test_data in test_types.items():
            success_icon = "✅" if test_data["success"] else "❌"
            
            # Add baseline comparison if available
            comparison_text = ""
            if "baseline_comparison" in test_data:
                comp = test_data["baseline_comparison"]
                comparison_text = f" | Baseline Match: {comp['verdict_emoji']} {comp['verdict']} ({comp['similarity_score']:.3f})"
            
            report_content += f"""**{test_type}** {success_icon}
- Quality: {test_data['quality_score']:.3f} | Length: {test_data['response_length']} chars{comparison_text}

<details>
<summary>View Model Output</summary>

```
{test_data['response_text'][:2000]}{'...' if len(test_data['response_text']) > 2000 else ''}
```

</details>

"""
        
        report_content += "---\n\n"
    
    # Add final recommendations
    report_content += f"""## 🚀 Final Recommendations

### For Zara (Strategic Analysis)
- **Baseline Performance:** `{BASELINE_MODEL}` delivers {baseline_stats['success_rate']:.1%} success rate
- **Perfect Matches:** {len(perfect_similarity)} models achieve ≥90% baseline similarity
- **Efficient Alternatives:** {len(smaller_alternatives)} smaller models maintain quality

### For Sandy (Implementation Decision)
- **Current Model:** `{BASELINE_MODEL}` remains reliable but large ({baseline_stats['model_size_gb']:.1f}GB)
"""
    
    if smaller_alternatives:
        best_small = smaller_alternatives[0]
        size_reduction = ((baseline_stats["model_size_gb"] - best_small[1]["model_size_gb"]) / baseline_stats["model_size_gb"]) * 100
        report_content += f"""- **Recommended Upgrade:** `{best_small[0]}` 
  - {size_reduction:.1f}% size reduction ({best_small[1]['model_size_gb']:.1f}GB vs {baseline_stats['model_size_gb']:.1f}GB)
  - {best_small[1]['avg_baseline_similarity']:.3f} baseline similarity
  - {best_small[1]['success_rate']:.1%} success rate maintained
"""
    
    if len(sorted_models) > 1 and not sorted_models[1][1]["is_baseline"]:
        best_alt = sorted_models[1]
        report_content += f"""- **Best Quality Alternative:** `{best_alt[0]}`
  - {best_alt[1]['avg_baseline_similarity']:.3f} baseline similarity
  - {best_alt[1]['success_rate']:.1%} success rate
  - {best_alt[1]['model_size_gb']:.1f}GB model size
"""
    
    report_content += f"""
### Implementation Priority
1. **Test Phase:** Deploy `{smaller_alternatives[0][0] if smaller_alternatives else 'best alternative'}` in parallel
2. **Validation:** Compare outputs against `{BASELINE_MODEL}` on production data
3. **Rollout:** Replace if similarity ≥0.8 and performance maintained

---

*Report generated by Sandy Model Performance Analyzer with Baseline Comparison*  
*Baseline Model: `{BASELINE_MODEL}` | Data source: {len(sandy_logs)} dialogue logs*
"""
    
    # Save markdown report
    report_file = Path("Sandy_Model_Performance_Baseline_Report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("🎯 Sandy Baseline Comparison Report Generated")
    print("=" * 60)
    print(f"📄 Report saved to: {report_file}")
    print(f"📊 Analyzed {len(sandy_logs)} test results")
    print(f"🥇 Baseline: {BASELINE_MODEL} ({baseline_stats['avg_baseline_similarity']:.3f} self-similarity)")
    if len(sorted_models) > 1:
        best_alt = sorted_models[1]
        print(f"🏆 Best alternative: {best_alt[0]} ({best_alt[1]['avg_baseline_similarity']:.3f} similarity)")
    if smaller_alternatives:
        best_small = smaller_alternatives[0]
        size_reduction = ((baseline_stats["model_size_gb"] - best_small[1]["model_size_gb"]) / baseline_stats["model_size_gb"]) * 100
        print(f"🏃 Best smaller: {best_small[0]} ({size_reduction:.1f}% smaller, {best_small[1]['avg_baseline_similarity']:.3f} similarity)")
    print("\n🎯 READY TO SHARE WITH TEAM")
    print("=" * 60)
    
    return report_file

if __name__ == "__main__":
    generate_baseline_comparison_report()
