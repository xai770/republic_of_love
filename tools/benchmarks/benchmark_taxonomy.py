#!/usr/bin/env python3
"""
Taxonomy Model Benchmark

Tests multiple LLM models on skill taxonomy classification task.
Finds the fastest model that achieves 100% correctness.

Usage:
    python3 tools/benchmark_taxonomy.py

Author: Sandy
Date: 2025-12-03
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Models to test (in order)
MODELS = [
    "qwen2.5:7b",
    "mistral:latest",
    "phi3:latest",
    "gemma3:4b",
    "llama3.2:latest",
]

# Load test cases
TEST_CASES_FILE = Path(__file__).parent.parent / "tests" / "taxonomy_test_cases.json"

def build_prompt(test_case: dict, existing_skills: list) -> str:
    """Build the taxonomy classification prompt"""
    
    # Format existing skills
    skills_text = "\n".join([
        f"- {s['skill_name']} (id: {s['skill_id']}, parent: {s['parent'] or 'root'})"
        for s in existing_skills
    ])
    
    return f"""You are a skill taxonomy curator. Classify this unmatched skill.

EXISTING CANONICAL SKILLS:
{skills_text}

UNMATCHED SKILL: "{test_case['raw_skill_name']}"

Decide:
- ALIAS: This is another name for an existing skill
- NEW: This is a new skill to add to taxonomy
- SPLIT: This is a compound skill that should become multiple skills
- SKIP: This is not a skill (experience requirement, benefit, etc.)

Respond with ONLY valid JSON:
{{
  "decision": "ALIAS" | "NEW" | "SPLIT" | "SKIP",
  "skill_id": <existing skill_id if ALIAS, null otherwise>,
  "reasoning": "<one sentence>"
}}"""


def run_model(model: str, prompt: str, timeout: int = 60) -> tuple:
    """Run a single model call, return (response, latency_ms, error)"""
    start = time.time()
    
    try:
        process = subprocess.Popen(
            ['ollama', 'run', model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=prompt, timeout=timeout)
        latency = (time.time() - start) * 1000
        
        if process.returncode != 0:
            return None, latency, f"Error: {stderr}"
        
        return stdout.strip(), latency, None
        
    except subprocess.TimeoutExpired:
        process.kill()
        return None, timeout * 1000, "TIMEOUT"
    except Exception as e:
        return None, (time.time() - start) * 1000, str(e)


def parse_response(response: str) -> dict:
    """Parse JSON from response (handle markdown code blocks)"""
    if not response:
        return None
    
    # Strip markdown code blocks
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in response
        import re
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return None


def check_correctness(result: dict, expected: dict) -> bool:
    """Check if the model's decision matches expected"""
    if not result:
        return False
    
    decision = result.get('decision', '').upper()
    expected_decision = expected['expected_decision'].upper()
    
    if decision != expected_decision:
        return False
    
    # For ALIAS, also check skill_id
    if decision == 'ALIAS':
        expected_id = expected.get('expected_skill_id')
        actual_id = result.get('skill_id')
        if expected_id and actual_id != expected_id:
            return False
    
    return True


def main():
    print("=" * 80)
    print("🏁 TAXONOMY MODEL BENCHMARK")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load test cases
    with open(TEST_CASES_FILE) as f:
        data = json.load(f)
    
    test_cases = data['test_cases']
    existing_skills = data['existing_skills']
    
    print(f"📋 Test Cases: {len(test_cases)}")
    print(f"🎯 Models to test: {', '.join(MODELS)}")
    print()
    
    # Results storage
    all_results = {}
    
    # Test each model
    for model in MODELS:
        print(f"\n{'=' * 60}")
        print(f"🤖 Testing: {model}")
        print('=' * 60)
        
        model_results = []
        
        for tc in test_cases:
            prompt = build_prompt(tc, existing_skills)
            
            print(f"  {tc['id']}: \"{tc['raw_skill_name']}\" ... ", end='', flush=True)
            
            response, latency, error = run_model(model, prompt)
            
            if error:
                print(f"❌ ERROR ({error})")
                model_results.append({
                    'id': tc['id'],
                    'correct': False,
                    'latency_ms': latency,
                    'error': error
                })
                continue
            
            parsed = parse_response(response)
            correct = check_correctness(parsed, tc)
            
            decision = parsed.get('decision', 'PARSE_ERROR') if parsed else 'PARSE_ERROR'
            
            if correct:
                print(f"✅ {decision} ({latency:.0f}ms)")
            else:
                print(f"❌ {decision} (expected {tc['expected_decision']}) ({latency:.0f}ms)")
            
            model_results.append({
                'id': tc['id'],
                'expected': tc['expected_decision'],
                'actual': decision,
                'correct': correct,
                'latency_ms': latency,
                'response': response[:200] if response else None
            })
        
        # Calculate metrics
        correct_count = sum(1 for r in model_results if r['correct'])
        total_count = len(model_results)
        accuracy = correct_count / total_count * 100
        avg_latency = sum(r['latency_ms'] for r in model_results) / total_count
        
        all_results[model] = {
            'correct': correct_count,
            'total': total_count,
            'accuracy': accuracy,
            'avg_latency_ms': avg_latency,
            'qualified': accuracy == 100.0,
            'details': model_results
        }
        
        print(f"\n  📊 Results: {correct_count}/{total_count} ({accuracy:.1f}%)")
        print(f"  ⏱️  Avg Latency: {avg_latency:.0f}ms")
        print(f"  {'✅ QUALIFIED' if accuracy == 100.0 else '❌ DISQUALIFIED'}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏆 FINAL RANKINGS")
    print("=" * 80)
    
    # Sort by qualified first, then by latency
    ranked = sorted(
        all_results.items(),
        key=lambda x: (-x[1]['qualified'], x[1]['avg_latency_ms'])
    )
    
    print(f"\n{'Rank':<6} {'Model':<20} {'Accuracy':<12} {'Avg Latency':<12} {'Status'}")
    print("-" * 60)
    
    for i, (model, data) in enumerate(ranked, 1):
        status = "✅ QUALIFIED" if data['qualified'] else "❌"
        print(f"{i:<6} {model:<20} {data['accuracy']:.1f}%{'':<6} {data['avg_latency_ms']:.0f}ms{'':<6} {status}")
    
    # Champion
    qualified = [(m, d) for m, d in ranked if d['qualified']]
    if qualified:
        champion, champ_data = qualified[0]
        print(f"\n🏆 CHAMPION: {champion}")
        print(f"   Accuracy: {champ_data['accuracy']:.1f}%")
        print(f"   Avg Latency: {champ_data['avg_latency_ms']:.0f}ms")
    else:
        print("\n❌ No model achieved 100% accuracy")
    
    # Save results
    output_file = Path(__file__).parent.parent / "reports" / f"taxonomy_benchmark_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_cases_count': len(test_cases),
            'models_tested': MODELS,
            'results': all_results
        }, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_file}")


if __name__ == '__main__':
    main()
