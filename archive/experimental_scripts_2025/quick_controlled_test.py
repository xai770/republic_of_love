#!/usr/bin/env python3
"""
Quick Controlled Variable Test - Prompt vs Interface
"""

import json
import subprocess
import time
import requests
from datetime import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def discover_test_models():
    """Get first 3 models for quick test"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        models = []
        for line in result.stdout.strip().split('\n')[1:]:
            if line.strip():
                model_name = line.split()[0]
                if ':' in model_name and model_name != 'bge-m3:567m':
                    models.append(model_name)
        return sorted(models)[:3]  # Just first 3 for quick test
    except:
        return []

def extract_answer(response):
    """Extract answer from response"""
    bracket_match = re.search(r'\[(\d+)\]', response)
    if bracket_match:
        return bracket_match.group(1)
    
    numbers = re.findall(r'\b\d+\b', response)
    return numbers[0] if numbers else 'NO_NUMBER_FOUND'

def test_http(model, prompt, test_name):
    """Test via HTTP API"""
    try:
        start_time = time.time()
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': model, 'prompt': prompt, 'stream': False},
            timeout=30
        )
        latency = time.time() - start_time
        
        if response.status_code == 200:
            raw = response.json()['response']
            answer = extract_answer(raw)
            return {
                'model': model, 'method': 'HTTP', 'test': test_name,
                'answer': answer, 'correct': answer == '3', 'latency': latency
            }
    except Exception as e:
        return {'model': model, 'method': 'HTTP', 'test': test_name, 'error': str(e), 'correct': False}

def test_cli(model, prompt, test_name):
    """Test via CLI"""
    try:
        start_time = time.time()
        result = subprocess.run(['ollama', 'run', model], input=prompt, capture_output=True, text=True, timeout=30)
        latency = time.time() - start_time
        
        if result.returncode == 0:
            raw = result.stdout.strip()
            answer = extract_answer(raw)
            return {
                'model': model, 'method': 'CLI', 'test': test_name,
                'answer': answer, 'correct': answer == '3', 'latency': latency
            }
    except Exception as e:
        return {'model': model, 'method': 'CLI', 'test': test_name, 'error': str(e), 'correct': False}

def main():
    # Your exact manual prompt
    manual_prompt = """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

## Processing Payload  
How many "r" letters are in "strawberry"?  

## QA Check  
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

    # Our original prompt
    our_prompt = """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

```
How many times does the letter 'r' appear in the word "strawberry"?  
```"""

    print("🧪 CONTROLLED VARIABLE EXPERIMENT")
    print("=" * 40)
    
    models = discover_test_models()
    print(f"Testing with models: {models}")
    
    if not models:
        print("No models found!")
        return
    
    all_results = []
    
    # Test matrix: 2 prompts × 2 methods × N models
    tests = [
        (manual_prompt, 'Manual_HTTP', test_http),
        (manual_prompt, 'Manual_CLI', test_cli),
        (our_prompt, 'Our_HTTP', test_http),
        (our_prompt, 'Our_CLI', test_cli)
    ]
    
    for prompt, test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        for model in models:
            print(f"Testing {model}...")
            result = test_func(model, prompt, test_name)
            all_results.append(result)
            
            if result.get('correct'):
                print(f"  ✓ {result.get('answer', 'ERROR')}")
            else:
                print(f"  ✗ {result.get('answer', 'ERROR')}")
    
    # Analysis
    print("\n📊 RESULTS SUMMARY:")
    print("-" * 30)
    
    by_test = {}
    for r in all_results:
        test = r['test']
        if test not in by_test:
            by_test[test] = {'correct': 0, 'total': 0}
        by_test[test]['total'] += 1
        if r.get('correct'):
            by_test[test]['correct'] += 1
    
    for test, stats in by_test.items():
        accuracy = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"{test:<12}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%)")
    
    # Key comparisons
    manual_http = by_test.get('Manual_HTTP', {'correct': 0, 'total': 1})
    our_http = by_test.get('Our_HTTP', {'correct': 0, 'total': 1})
    manual_cli = by_test.get('Manual_CLI', {'correct': 0, 'total': 1})
    
    mh_acc = manual_http['correct'] / manual_http['total'] * 100
    oh_acc = our_http['correct'] / our_http['total'] * 100
    mc_acc = manual_cli['correct'] / manual_cli['total'] * 100
    
    print(f"\n🔍 KEY FINDINGS:")
    prompt_effect = abs(mh_acc - oh_acc)
    interface_effect = abs(mh_acc - mc_acc)
    
    print(f"Prompt Effect:    {prompt_effect:.1f} percentage points")
    print(f"Interface Effect: {interface_effect:.1f} percentage points")
    
    if prompt_effect > interface_effect:
        print("🎯 CONCLUSION: PROMPT FORMAT matters more!")
    elif interface_effect > prompt_effect:
        print("🎯 CONCLUSION: INTERFACE METHOD matters more!")
    else:
        print("🎯 CONCLUSION: Both factors have similar impact")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'controlled_test_{timestamp}.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to controlled_test_{timestamp}.json")

if __name__ == '__main__':
    main()