#!/usr/bin/env python3
"""
Quick Model Benchmark for Skill Classification

Tests models on classification task to find fastest accurate model.

Usage:
    python3 tools/benchmark_classify.py

Author: Sandy
Date: December 2025
"""

import json
import time
import subprocess
from typing import Dict, List, Tuple
from datetime import datetime
import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Domain mapping for reference
DOMAINS = {
    "8452": "technology",
    "8453": "data_and_analytics",
    "8454": "business_operations",
    "8455": "people_and_communication",
    "8456": "compliance_and_risk",
    "8457": "project_and_product",
    "8458": "corporate_culture",
    "8459": "specialized_knowledge"
}

# Test cases: (skill_name, expected_domain_id)
TEST_CASES = [
    ("Python programming", "8452"),           # tech
    ("Kubernetes orchestration", "8452"),     # tech
    ("SQL query optimization", "8453"),       # data
    ("Machine learning", "8453"),             # data
    ("Budgeting and forecasting", "8454"),    # biz ops
    ("Supply chain management", "8454"),      # biz ops
    ("Stakeholder communication", "8455"),    # people
    ("Executive presentations", "8455"),      # people
    ("Internal audit procedures", "8456"),    # compliance
    ("GDPR compliance", "8456"),              # compliance
    ("Agile methodology", "8457"),            # project
    ("Product roadmap", "8457"),              # project
    ("Diversity initiatives", "8458"),        # culture
    ("Remote work practices", "8458"),        # culture
    ("Medical terminology", "8459"),          # specialized
    ("Basel III regulations", "8459"),        # specialized
]

PROMPT_TEMPLATE = """Classify this skill into ONE domain.

SKILL: {skill}

DOMAINS:
8452 = technology (programming, infrastructure, software)
8453 = data_and_analytics (data science, ML, BI)
8454 = business_operations (finance, HR, legal, supply chain)
8455 = people_and_communication (leadership, communication)
8456 = compliance_and_risk (audit, regulatory, risk)
8457 = project_and_product (agile, scrum, product management)
8458 = corporate_culture (DEI, remote work, engagement)
8459 = specialized_knowledge (industry-specific, medical, banking)

Output ONLY the domain ID number (e.g., 8452):"""

# Models to test
MODELS = [
    "qwen2.5:7b",
    "qwen2.5:3b",
    "gemma3:4b",
    "gemma2:latest",
    "mistral:latest",
    "llama3.2:3b",
    "phi3:latest",
]


def test_model(model_name: str) -> Tuple[int, int, float]:
    """
    Test a model on all test cases.
    
    Returns: (correct_count, total_count, avg_latency_ms)
    """
    correct = 0
    total_latency = 0
    
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print('='*60)
    
    for skill, expected in TEST_CASES:
        prompt = PROMPT_TEMPLATE.format(skill=skill)
        
        start = time.time()
        
        try:
            result = subprocess.run(
                ['ollama', 'run', model_name],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            latency = (time.time() - start) * 1000  # ms
            total_latency += latency
            
            response = result.stdout.strip()
            
            # Extract domain ID from response
            # Look for 4-digit number starting with 84
            actual = None
            for word in response.split():
                word = word.strip('.,;:()[]')
                if word.startswith('84') and len(word) == 4 and word.isdigit():
                    actual = word
                    break
            
            is_correct = (actual == expected)
            if is_correct:
                correct += 1
                symbol = "✅"
            else:
                symbol = "❌"
            
            print(f"  {symbol} {skill[:30]:<30} expected:{expected} got:{actual or '???'} ({latency:.0f}ms)")
            
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {skill[:30]:<30} TIMEOUT")
        except Exception as e:
            print(f"  💥 {skill[:30]:<30} ERROR: {e}")
    
    avg_latency = total_latency / len(TEST_CASES)
    accuracy = (correct / len(TEST_CASES)) * 100
    
    print(f"\n  📊 Results: {correct}/{len(TEST_CASES)} ({accuracy:.1f}%)")
    print(f"  ⏱️  Avg: {avg_latency:.0f}ms")
    
    return correct, len(TEST_CASES), avg_latency


def main():
    print("\n" + "="*60)
    print("🏁 SKILL CLASSIFICATION MODEL BENCHMARK")
    print("="*60)
    print(f"Test cases: {len(TEST_CASES)}")
    print(f"Models: {len(MODELS)}")
    
    results = []
    
    for model in MODELS:
        try:
            correct, total, avg_latency = test_model(model)
            results.append({
                'model': model,
                'correct': correct,
                'total': total,
                'accuracy': (correct / total) * 100,
                'avg_latency_ms': avg_latency,
                'qualified': correct == total  # 100% required
            })
        except Exception as e:
            print(f"  💥 Model {model} failed: {e}")
            results.append({
                'model': model,
                'correct': 0,
                'total': len(TEST_CASES),
                'accuracy': 0,
                'avg_latency_ms': 999999,
                'qualified': False
            })
    
    # Sort by: qualified first, then by speed
    results.sort(key=lambda x: (-x['qualified'], x['avg_latency_ms']))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 FINAL RANKINGS")
    print("="*60)
    print(f"\n{'Rank':<5} {'Model':<20} {'Accuracy':<12} {'Avg Latency':<12} {'Status'}")
    print("-"*60)
    
    for i, r in enumerate(results, 1):
        status = "✅ QUALIFIED" if r['qualified'] else "❌ DISQUALIFIED"
        print(f"{i:<5} {r['model']:<20} {r['accuracy']:>5.1f}%      {r['avg_latency_ms']:>6.0f}ms     {status}")
    
    # Champion
    qualified = [r for r in results if r['qualified']]
    if qualified:
        champion = qualified[0]
        print(f"\n🏆 CHAMPION: {champion['model']} ({champion['avg_latency_ms']:.0f}ms avg)")
    else:
        print("\n⚠️  No model achieved 100% accuracy")
        best = max(results, key=lambda x: x['accuracy'])
        print(f"  Best: {best['model']} ({best['accuracy']:.1f}%)")
    
    # Save report
    report_file = f"reports/benchmark_classify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("reports").mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_cases_count': len(TEST_CASES),
            'results': results
        }, f, indent=2)
    print(f"\n📄 Report saved: {report_file}")


if __name__ == "__main__":
    main()
