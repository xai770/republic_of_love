#!/usr/bin/env python3
"""
Create comprehensive CSV comparing manual results with automated test results
"""

import json
import csv
import os
from collections import defaultdict
from pathlib import Path

def extract_manual_results():
    """Extract manual results from the RFA spec"""
    manual_results = {
        'gpt-oss:latest': '[3]',
        'mistral-nemo:12b': '[3]', 
        'granite3.1-moe:3b': '[6]',
        'qwen2.5:7b': '[3]',
        'llama3.2:latest': '[3]',
        'gemma3:4b': '[3]',
        'phi3:3.8b': '[3]',
        'phi4-mini-reasoning:latest': '[3]',
        'qwen3:latest': '[3]',
        'deepseek-r1:8b': '[3]',
        'gemma3:1b': '[2]',
        'qwen3:0.6b': '[2]',
        'qwen3:4b': '[3]',
        'qwen3:1.7b': '[3]',
        'mistral:latest': '[3]',
        'dolphin3:8b': '[5]',
        'olmo2:latest': '[4]',
        'codegemma:latest': '[5]',
        'qwen2.5vl:latest': '[strawberry contains 2 "r" letters]',  # Non-compliant format
        'gemma3n:latest': '[ 3 ]',  # Has spaces
        'llama3.2:1b': '[7]',
        'phi4-mini:latest': '[3]',
        'gemma2:latest': '[3]',
        'gemma3n:e2b': '[3]'
    }
    return manual_results

def load_test_results(file_path):
    """Load and process automated test results from JSON"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        results = defaultdict(lambda: {
            'total_tests': 0,
            'correct': 0,
            'original_correct': 0,
            'original_total': 0,
            'simplified_correct': 0,
            'simplified_total': 0,
            'avg_latency': 0,
            'responses': []
        })
        
        for entry in data:
            if entry.get('status') != 'completed':
                continue
                
            model = entry['model']
            is_correct = entry.get('is_correct', False)
            latency = entry.get('latency', 0)
            prompt_type = entry.get('prompt_type', 'unknown')
            response = entry.get('response', '')
            extracted = entry.get('extracted_answer', '')
            
            results[model]['total_tests'] += 1
            results[model]['avg_latency'] += latency
            results[model]['responses'].append(f"[{extracted}]" if extracted else response[:20])
            
            if is_correct:
                results[model]['correct'] += 1
                
            if prompt_type == 'original':
                results[model]['original_total'] += 1
                if is_correct:
                    results[model]['original_correct'] += 1
            elif prompt_type == 'simplified':
                results[model]['simplified_total'] += 1
                if is_correct:
                    results[model]['simplified_correct'] += 1
        
        # Calculate averages
        for model in results:
            if results[model]['total_tests'] > 0:
                results[model]['avg_latency'] /= results[model]['total_tests']
        
        return dict(results)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def calculate_accuracy_percentage(correct, total):
    """Calculate accuracy as percentage"""
    return f"{(correct/total*100):.1f}%" if total > 0 else "0.0%"

def main():
    """Create comprehensive comparison CSV"""
    print("Creating comprehensive strawberry test comparison...")
    
    # Extract manual results
    manual_results = extract_manual_results()
    
    # Load automated test results
    cpu_results = load_test_results('/home/xai/Documents/ty_learn/strawberry_test_output/strawberry_results_20250919_081556.json')
    gpu_results = load_test_results('/home/xai/Documents/ty_learn/strawberry_test_output/strawberry_results_20250919_094312.json')
    
    # Get all models (union of all datasets)
    all_models = set(manual_results.keys()) | set(cpu_results.keys()) | set(gpu_results.keys())
    
    # Create CSV data
    csv_data = []
    headers = [
        'Model',
        'Manual_Result',
        'Manual_Correct',
        'CPU_Accuracy',
        'CPU_Original_Prompt', 
        'CPU_Simplified_Prompt',
        'CPU_Avg_Latency',
        'GPU_Accuracy',
        'GPU_Original_Prompt',
        'GPU_Simplified_Prompt', 
        'GPU_Avg_Latency',
        'Hardware_Speedup',
        'CPU_Sample_Responses',
        'GPU_Sample_Responses'
    ]
    
    for model in sorted(all_models):
        manual_result = manual_results.get(model, 'N/A')
        manual_correct = 'Yes' if manual_result in ['[3]', '[ 3 ]'] else 'No'
        
        # CPU results
        cpu_data = cpu_results.get(model, {})
        cpu_accuracy = calculate_accuracy_percentage(cpu_data.get('correct', 0), cpu_data.get('total_tests', 0))
        cpu_original = calculate_accuracy_percentage(cpu_data.get('original_correct', 0), cpu_data.get('original_total', 0))
        cpu_simplified = calculate_accuracy_percentage(cpu_data.get('simplified_correct', 0), cpu_data.get('simplified_total', 0))
        cpu_latency = f"{cpu_data.get('avg_latency', 0):.1f}s"
        cpu_responses = ' | '.join(cpu_data.get('responses', [])[:3])  # First 3 responses
        
        # GPU results  
        gpu_data = gpu_results.get(model, {})
        gpu_accuracy = calculate_accuracy_percentage(gpu_data.get('correct', 0), gpu_data.get('total_tests', 0))
        gpu_original = calculate_accuracy_percentage(gpu_data.get('original_correct', 0), gpu_data.get('original_total', 0))
        gpu_simplified = calculate_accuracy_percentage(gpu_data.get('simplified_correct', 0), gpu_data.get('simplified_total', 0))
        gpu_latency = f"{gpu_data.get('avg_latency', 0):.1f}s"
        gpu_responses = ' | '.join(gpu_data.get('responses', [])[:3])  # First 3 responses
        
        # Hardware speedup
        cpu_lat = cpu_data.get('avg_latency', 0)
        gpu_lat = gpu_data.get('avg_latency', 0)
        speedup = f"{cpu_lat/gpu_lat:.1f}x" if gpu_lat > 0 and cpu_lat > 0 else 'N/A'
        
        csv_data.append([
            model,
            manual_result,
            manual_correct,
            cpu_accuracy,
            cpu_original,
            cpu_simplified, 
            cpu_latency,
            gpu_accuracy,
            gpu_original,
            gpu_simplified,
            gpu_latency,
            speedup,
            cpu_responses,
            gpu_responses
        ])
    
    # Write CSV
    output_file = '/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(csv_data)
    
    print(f"✅ Comprehensive comparison saved to: {output_file}")
    print(f"📊 Analyzed {len(all_models)} models across manual + automated tests")
    
    # Summary statistics
    total_manual = len([r for r in manual_results.values() if r != 'N/A'])
    correct_manual = len([r for r in manual_results.values() if r in ['[3]', '[ 3 ]']])
    
    print(f"\n📈 Quick Summary:")
    print(f"   Manual tests: {correct_manual}/{total_manual} correct ({correct_manual/total_manual*100:.1f}%)")
    print(f"   CPU tests: {len(cpu_results)} models tested")
    print(f"   GPU tests: {len(gpu_results)} models tested")

if __name__ == "__main__":
    main()