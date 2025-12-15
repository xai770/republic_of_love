#!/usr/bin/env python3
"""
Format Standardization Model Benchmark

Tests which AI model best performs format standardization for job summaries.
Evaluates based on:
1. Correctness (has required sections, no forbidden content)
2. Speed (latency per request)

Usage:
    python3 tools/benchmark_format.py

Author: Sandy
Date: November 30, 2025
"""

import subprocess
import time
import json
import re
from typing import Dict, List, Any, Tuple
from datetime import datetime


# Models to test (from your actors table)
MODELS_TO_TEST = [
    "gemma2:latest",      # Current baseline
    "qwen2.5:7b",         # Strong performer
    "olmo2:7b",           # Promising - passed hard test!
    "olmo2:latest",       # Latest olmo
]

# The prompt template from the actual conversation
FORMAT_PROMPT = """Clean this job posting summary by following these rules EXACTLY:

INPUT:
{summary}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else."""

# Test cases
TEST_CASES = [
    {
        "id": "tc1_messy_markdown",
        "summary": "```json\n**Role:** Data Engineer\n**Company:** Deutsche Bank\n**Location:** Frankfurt, Germany\n**Type:** Full-time\n\n**Key Responsibilities:**\n* Build data pipelines\n* Maintain ETL processes\n* Work with big data technologies\n\n**Skills and Experience:**\n- 5+ years Python\n- SQL expertise\n- Cloud platforms\n\n**Benefits:**\n- Competitive salary\n- Health insurance\n```",
        "must_have": ["**Role:**", "**Company:**", "**Location:**", "**Key Responsibilities:**", "**Requirements:**"],
        "must_not_have": ["```", "Type:", "Skills and Experience:", "Benefits:"]
    },
    {
        "id": "tc2_asterisk_bullets",
        "summary": "**Role:** Software Developer\n**Company:** DWS Group\n**Location:** London, UK\n**Job ID:** SW-2024-001\n\n**Key Responsibilities:**\n* Design software solutions\n* Code review\n* Mentor junior developers\n\n**Requirements:**\n* Java or Python\n* Agile experience\n* Communication skills",
        "must_have": ["**Role:**", "**Company:**", "**Location:**", "**Key Responsibilities:**", "**Requirements:**"],
        "must_not_have": ["```"]
    },
    {
        "id": "tc3_extra_sections",
        "summary": "**Role:** Risk Analyst\n**Company:** Deutsche Bank AG\n**Location:** Singapore\n\n**Type:** Permanent\n\n**Key Responsibilities:**\n- Assess operational risks\n- Prepare risk reports\n\n**Skills and Experience:**\n- Risk management background\n- Financial services experience\n\n**Benefits:**\n- Annual bonus\n- Flexible hours\n\n**Requirements:**\n- Bachelor's degree",
        "must_have": ["**Role:**", "**Company:**", "**Location:**", "**Key Responsibilities:**", "**Requirements:**"],
        "must_not_have": ["Type:", "Skills and Experience:", "Benefits:"]
    },
    {
        "id": "tc4_clean_input",
        "summary": "**Role:** KYC Analyst\n**Company:** Deutsche Bank Group\n**Location:** Budapest, Hungary\n**Job ID:** KYC-2024-HU\n**Key Responsibilities:**\n- Client onboarding\n- Document verification\n**Requirements:**\n- English proficiency\n- MS Office skills\n**Details:**\nHybrid working.",
        "must_have": ["**Role:**", "**Company:**", "**Location:**", "**Key Responsibilities:**", "**Requirements:**"],
        "must_not_have": ["```"]
    },
    {
        "id": "tc5_code_block_wrapper",
        "summary": "```\n**Role:** Compliance Officer\n**Company:** Deutsche Bank\n**Location:** New York\n\n**Key Responsibilities:**\n- Monitor regulations\n- Ensure compliance\n- Train staff\n\n**Requirements:**\n- Law degree\n- 5+ years experience\n```",
        "must_have": ["**Role:**", "**Company:**", "**Location:**", "**Key Responsibilities:**", "**Requirements:**"],
        "must_not_have": ["```"]
    }
]


def run_model(model_name: str, prompt: str, timeout: int = 60) -> Tuple[str, float, str]:
    """
    Run a model with the given prompt.
    
    Returns: (response, latency_seconds, error_or_none)
    """
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            ['ollama', 'run', model_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=prompt, timeout=timeout)
        latency = time.time() - start_time
        
        if process.returncode != 0:
            return "", latency, f"Error: {stderr}"
        
        return stdout.strip(), latency, None
        
    except subprocess.TimeoutExpired:
        process.kill()
        return "", timeout, "Timeout"
    except Exception as e:
        return "", time.time() - start_time, str(e)


def evaluate_response(response: str, test_case: Dict) -> Tuple[bool, List[str]]:
    """
    Evaluate if response meets requirements.
    
    Returns: (passed, list_of_failures)
    """
    failures = []
    
    # Check must_have sections
    for section in test_case.get("must_have", []):
        if section not in response:
            failures.append(f"Missing: {section}")
    
    # Check must_not_have content
    for forbidden in test_case.get("must_not_have", []):
        if forbidden in response:
            failures.append(f"Contains forbidden: {forbidden}")
    
    return len(failures) == 0, failures


def run_benchmark():
    """Run the full benchmark."""
    print("=" * 70)
    print("🏁 FORMAT STANDARDIZATION MODEL BENCHMARK")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nTesting {len(MODELS_TO_TEST)} models on {len(TEST_CASES)} test cases\n")
    
    results = {}
    
    for model in MODELS_TO_TEST:
        print(f"\n📊 Testing: {model}")
        print("-" * 50)
        
        model_results = {
            "passed": 0,
            "failed": 0,
            "total_latency": 0,
            "errors": [],
            "test_results": []
        }
        
        for tc in TEST_CASES:
            print(f"  {tc['id']}... ", end="", flush=True)
            
            prompt = FORMAT_PROMPT.format(summary=tc["summary"])
            response, latency, error = run_model(model, prompt)
            
            if error:
                print(f"❌ ERROR ({error})")
                model_results["failed"] += 1
                model_results["errors"].append(f"{tc['id']}: {error}")
                model_results["test_results"].append({
                    "id": tc["id"],
                    "passed": False,
                    "latency": latency,
                    "error": error
                })
            else:
                passed, failures = evaluate_response(response, tc)
                model_results["total_latency"] += latency
                
                if passed:
                    print(f"✅ PASS ({latency:.1f}s)")
                    model_results["passed"] += 1
                else:
                    print(f"❌ FAIL ({', '.join(failures)})")
                    model_results["failed"] += 1
                    model_results["errors"].append(f"{tc['id']}: {', '.join(failures)}")
                
                model_results["test_results"].append({
                    "id": tc["id"],
                    "passed": passed,
                    "latency": latency,
                    "failures": failures if not passed else []
                })
        
        total_tests = model_results["passed"] + model_results["failed"]
        avg_latency = model_results["total_latency"] / max(model_results["passed"], 1)
        correctness = (model_results["passed"] / total_tests) * 100 if total_tests > 0 else 0
        
        model_results["correctness_pct"] = correctness
        model_results["avg_latency"] = avg_latency
        model_results["qualified"] = correctness == 100.0
        
        results[model] = model_results
        
        print(f"\n  📈 Result: {model_results['passed']}/{total_tests} ({correctness:.0f}%)")
        print(f"  ⏱️  Avg latency: {avg_latency:.2f}s")
        print(f"  {'✅ QUALIFIED' if model_results['qualified'] else '❌ DISQUALIFIED'}")
    
    # Generate summary
    print("\n" + "=" * 70)
    print("🏆 BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    
    # Sort by qualified first, then by speed
    qualified = [(m, r) for m, r in results.items() if r["qualified"]]
    disqualified = [(m, r) for m, r in results.items() if not r["qualified"]]
    
    qualified.sort(key=lambda x: x[1]["avg_latency"])
    
    print("\n✅ QUALIFIED MODELS (100% correct, sorted by speed):")
    print("-" * 50)
    if qualified:
        for rank, (model, r) in enumerate(qualified, 1):
            marker = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "
            print(f"{marker} {rank}. {model:25} {r['avg_latency']:.2f}s avg")
    else:
        print("   No models qualified!")
    
    print("\n❌ DISQUALIFIED MODELS:")
    print("-" * 50)
    if disqualified:
        for model, r in disqualified:
            print(f"   {model:25} {r['correctness_pct']:.0f}% correct")
    else:
        print("   None!")
    
    # Champion announcement
    if qualified:
        champion = qualified[0]
        print("\n" + "=" * 70)
        print(f"🏆 CHAMPION: {champion[0]}")
        print(f"   Average latency: {champion[1]['avg_latency']:.2f}s")
        print(f"   Correctness: 100%")
        print("=" * 70)
        
        # Compare to current baseline (gemma2:latest)
        baseline_result = results.get("gemma2:latest")
        if baseline_result and champion[0] != "gemma2:latest":
            if baseline_result["qualified"]:
                speedup = baseline_result["avg_latency"] / champion[1]["avg_latency"]
                print(f"\n📊 vs gemma2:latest baseline:")
                print(f"   {speedup:.1f}x {'faster' if speedup > 1 else 'slower'}")
            else:
                print(f"\n📊 vs gemma2:latest baseline:")
                print(f"   Baseline failed ({baseline_result['correctness_pct']:.0f}% correct)")
    
    return results


if __name__ == "__main__":
    results = run_benchmark()
