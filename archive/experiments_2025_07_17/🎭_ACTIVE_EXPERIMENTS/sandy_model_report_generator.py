#!/usr/bin/env python3
"""
Sandy Model Performance Report Generator
========================================

Creates beautiful markdown reports with actual model outputs for team sharing.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Any
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

def generate_markdown_report():
    """Generate beautiful markdown report for team sharing"""
    
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
    
    # Process logs
    model_data = defaultdict(lambda: {
        "tests": [],
        "total_time": 0,
        "total_quality": 0,
        "successes": 0
    })
    
    all_responses = []
    
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
            
            model_data[model_name]["tests"].append(test_result)
            model_data[model_name]["total_time"] += result["processing_time"]
            model_data[model_name]["total_quality"] += quality["quality_score"]
            
            if test_result["success"]:
                model_data[model_name]["successes"] += 1
            
            all_responses.append({
                "model_name": model_name,
                **test_result
            })
    
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
            "tests": data["tests"]
        }
    
    # Sort by success rate, then by quality
    sorted_models = sorted(
        model_summary.items(), 
        key=lambda x: (x[1]["success_rate"], x[1]["avg_quality_score"]), 
        reverse=True
    )
    
    # Generate markdown report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_content = f"""# 🎯 Sandy Model Performance Report

**Generated:** {timestamp}  
**Total Models Tested:** {len(model_summary)}  
**Total Test Scenarios:** {sum(stats["tests_completed"] for stats in model_summary.values())}  
**Test Data:** Deutsche Bank Relationship Manager Position

---

## 📊 Executive Summary

### 🏆 Top Performing Models

| Rank | Model | Success Rate | Quality Score | Size (GB) | Efficiency |
|------|-------|--------------|---------------|-----------|------------|
"""
    
    # Add top 10 models to summary table
    for i, (model_name, stats) in enumerate(sorted_models[:10], 1):
        efficiency = (stats['success_rate'] * stats['avg_quality_score']) / max(stats['model_size_gb'], 0.1) if stats['model_size_gb'] > 0 else 0
        report_content += f"| {i} | `{model_name}` | {stats['success_rate']:.1%} | {stats['avg_quality_score']:.3f} | {stats['model_size_gb']:.1f} | {efficiency:.3f} |\n"
    
    # Key insights
    perfect_models = [name for name, stats in sorted_models if stats["success_rate"] == 1.0]
    efficient_models = sorted(
        [(name, stats, (stats['success_rate'] * stats['avg_quality_score']) / max(stats['model_size_gb'], 0.1))
         for name, stats in sorted_models if stats['model_size_gb'] > 0],
        key=lambda x: x[2], reverse=True
    )
    
    report_content += f"""

### 🎯 Key Insights

- **{len(perfect_models)} models achieved 100% success rate**
- **Most efficient model:** `{efficient_models[0][0]}` (efficiency: {efficient_models[0][2]:.3f})
- **Smallest working model:** `{min(sorted_models, key=lambda x: x[1]['model_size_gb'] if x[1]['success_rate'] > 0.5 else 999)[0]}`
- **Current model ranking:** `gemma3n:latest` ranked #{next((i for i, (name, _) in enumerate(sorted_models, 1) if name == 'gemma3n:latest'), 'N/A')}`

---

## 🧪 Test Scenarios

Sandy's pipeline was tested on 4 different specialist prompts:

1. **Concise Job Description Extraction** - Extract key tasks and profile requirements
2. **Requirements Focus Extraction** - Focus only on candidate requirements
3. **Structured Technical Analysis** - Categorize technical vs business requirements
4. **Skills Categorization** - Separate soft skills, experience, and education

---

## 📋 Detailed Model Results

"""
    
    # Add detailed results for each model
    for model_name, stats in sorted_models:
        status_emoji = "✅" if stats["success_rate"] == 1.0 else "⚠️" if stats["success_rate"] >= 0.75 else "❌"
        
        report_content += f"""### {status_emoji} {model_name}

**Performance Metrics:**
- Success Rate: **{stats['success_rate']:.1%}**
- Quality Score: **{stats['avg_quality_score']:.3f}**
- Model Size: **{stats['model_size_gb']:.1f}GB**
- Processing Time: **{stats['avg_processing_time']:.2f}s**

"""
        
        # Add sample outputs for each test type
        test_types = {}
        for test in stats["tests"]:
            if test["test_type"] not in test_types:
                test_types[test["test_type"]] = test
        
        for test_type, test_data in test_types.items():
            success_icon = "✅" if test_data["success"] else "❌"
            report_content += f"""**{test_type}** {success_icon}
- Quality: {test_data['quality_score']:.3f}
- Length: {test_data['response_length']} chars

<details>
<summary>View Model Output</summary>

```
{test_data['response_text'][:2000]}{'...' if len(test_data['response_text']) > 2000 else ''}
```

</details>

"""
        
        report_content += "---\n\n"
    
    # Add recommendations
    report_content += f"""## 🚀 Recommendations

### For Zara (Analysis & Strategy)
- **Best overall performers:** {', '.join([f'`{name}`' for name, _ in sorted_models[:3] if _['success_rate'] == 1.0])}
- **Most resource-efficient:** `{efficient_models[0][0]}` (only {efficient_models[0][1]['model_size_gb']:.1f}GB)
- **Quality consistency:** {len(perfect_models)} models achieve perfect reliability

### For Sandy (Implementation)
- **Recommended upgrade:** `{sorted_models[0][0]}` 
- **Current model performance:** {model_summary.get('gemma3n:latest', {}).get('success_rate', 0):.1%} success rate
- **Efficiency gain:** Switch to `{efficient_models[0][0]}` for {efficient_models[0][1]['model_size_gb']:.1f}GB vs {model_summary.get('gemma3n:latest', {}).get('model_size_gb', 7.5):.1f}GB

### Implementation Priority
1. **Immediate:** Test `{efficient_models[0][0]}` in Sandy's pipeline
2. **Validation:** Run production test with Deutsche Bank data
3. **Rollout:** Deploy if quality maintains at 100%

---

*Report generated by Sandy Model Performance Analyzer*  
*Data source: {len(sandy_logs)} dialogue logs from comprehensive model testing*
"""
    
    # Save markdown report
    report_file = Path("Sandy_Model_Performance_Report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("🎯 Sandy Model Performance Report Generated")
    print("=" * 60)
    print(f"📄 Report saved to: {report_file}")
    print(f"📊 Analyzed {len(sandy_logs)} test results")
    print(f"🏆 Top performer: {sorted_models[0][0]} ({sorted_models[0][1]['success_rate']:.1%} success)")
    print(f"⚡ Most efficient: {efficient_models[0][0]} ({efficient_models[0][2]:.3f} efficiency)")
    print("\n🎯 READY TO SHARE WITH TEAM")
    print("=" * 60)
    
    return report_file

if __name__ == "__main__":
    generate_markdown_report()
