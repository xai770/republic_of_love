#!/usr/bin/env python3
"""
Three-Way Strawberry Test Comparison
Compares Manual, CPU-only, and GPU results
"""

import json
import pandas as pd
from collections import defaultdict, Counter

def main():
    print('🔍 THREE-WAY STRAWBERRY TEST COMPARISON')
    print('='*100)

    # Load your manual results from the RFA doc
    manual_results = {
        'gpt-oss:latest': '3',
        'mistral-nemo:12b': '3', 
        'granite3.1-moe:3b': '6',
        'qwen2.5:7b': '3',
        'llama3.2:latest': '3',
        'gemma3:4b': '3',
        'phi3:3.8b': '3',
        'phi4-mini-reasoning:latest': '3',
        'qwen3:latest': '3',
        'deepseek-r1:8b': '3',
        'gemma3:1b': '2',
        'qwen3:0.6b': '2',
        'qwen3:4b': '3',
        'qwen3:1.7b': '3',
        'mistral:latest': '3',
        'dolphin3:8b': '5',
        'olmo2:latest': '4',
        'codegemma:latest': '5',
        'qwen2.5vl:latest': 'non-bracket',
        'gemma3n:latest': '3',
        'llama3.2:1b': '7',
        'phi4-mini:latest': '3',
        'gemma2:latest': '3',
        'gemma3n:e2b': '3'
    }

    # Load our first systematic run (CPU)
    with open('strawberry_test_output/strawberry_results_20250919_081556.json', 'r') as f:
        our_cpu_data = json.load(f)

    # Process our CPU data - focus on original prompt only for comparison
    cpu_results = defaultdict(list)
    cpu_latencies = defaultdict(list)

    for test in our_cpu_data:
        if test['prompt_type'] == 'original':
            model = test['model']
            answer = test['extracted_answer']
            latency = test['latency']
            
            cpu_results[model].append(answer)
            cpu_latencies[model].append(latency)

    # Create comparison table
    print()
    print('📊 Model-by-Model Comparison (Original Prompt)')
    print('-'*100)
    print(f"{'Model':<26} {'Manual':<12} {'CPU Mode':<10} {'CPU Acc':<8} {'Latency':<8} {'All CPU Results'}")
    print('-'*100)

    total_models = 0
    manual_correct = 0
    cpu_any_correct = 0

    for model in sorted(set(list(manual_results.keys()) + list(cpu_results.keys()))):
        if model == 'bge-m3:567m':  # Skip unsupported model
            continue
            
        total_models += 1
        
        # Your manual result
        manual_ans = manual_results.get(model, 'N/A')
        manual_is_correct = manual_ans == '3'
        if manual_is_correct:
            manual_correct += 1
        
        # Our CPU results
        if model in cpu_results and cpu_results[model]:
            cpu_answers = [str(ans) for ans in cpu_results[model] if ans is not None]
            if cpu_answers:
                # Most common answer
                most_common = Counter(cpu_answers).most_common(1)[0][0]
                correct_count = sum(1 for ans in cpu_answers if ans == '3')
                accuracy = f'{correct_count}/5'
                avg_latency = f'{sum(cpu_latencies[model])/len(cpu_latencies[model]):.1f}s'
                
                if correct_count > 0:
                    cpu_any_correct += 1
                
                # Clean display of all results
                results_clean = [ans.replace(' (no brackets)', '').replace(' (✓)', '').replace(' (✗)', '') for ans in cpu_answers]
                results_display = str(results_clean[:5])
                
            else:
                most_common = 'TIMEOUT'
                accuracy = '0/5'
                avg_latency = 'TIMEOUT'
                results_display = '[TIMEOUTS]'
        else:
            most_common = 'N/A'
            accuracy = 'N/A'
            avg_latency = 'N/A'
            results_display = 'N/A'
        
        model_short = model[:25]
        print(f'{model_short:<26} {manual_ans:<12} {most_common:<10} {accuracy:<8} {avg_latency:<8} {results_display}')

    print('-'*100)
    print(f'📈 OVERALL ACCURACY SUMMARY:')
    print(f'Your Manual Run:  {manual_correct}/{total_models} models correct ({manual_correct/total_models*100:.1f}%)')
    print(f'Our CPU Run:      {cpu_any_correct}/{total_models} models with ≥1 correct ({cpu_any_correct/total_models*100:.1f}%)')

    print()
    print('🎯 KEY DIFFERENCES:')
    print('-'*50)

    # Find major differences
    major_differences = []
    for model in manual_results:
        if model in cpu_results and cpu_results[model] and model != 'bge-m3:567m':
            manual_ans = manual_results[model]
            cpu_answers = [str(ans) for ans in cpu_results[model] if ans is not None]
            
            if cpu_answers:
                cpu_most_common = Counter(cpu_answers).most_common(1)[0][0]
                cpu_correct_rate = sum(1 for ans in cpu_answers if ans == '3') / len(cpu_answers)
                
                # Check for significant differences
                if str(manual_ans) != cpu_most_common or (manual_ans == '3' and cpu_correct_rate < 0.6):
                    major_differences.append({
                        'model': model,
                        'manual': manual_ans,
                        'cpu_mode': cpu_most_common,
                        'cpu_correct_rate': cpu_correct_rate,
                        'cpu_all': cpu_answers
                    })

    for i, diff in enumerate(major_differences[:8]):
        model = diff['model']
        manual = diff['manual']
        cpu_mode = diff['cpu_mode']
        cpu_rate = diff['cpu_correct_rate']
        cpu_all = diff['cpu_all']
        
        print(f'{i+1:2d}. {model[:23]:<23} Manual: {manual:<12} CPU: {cpu_mode} ({cpu_rate:.0%} correct)')
        print(f'     CPU Results: {cpu_all}')

    print()
    print('📊 STATISTICAL INSIGHTS:')
    print('-'*30)

    # Calculate consistency metrics
    total_cpu_tests = sum(len([ans for ans in cpu_results[m] if ans is not None]) for m in cpu_results)
    total_cpu_correct = sum(sum(1 for ans in cpu_results[m] if str(ans) == '3') for m in cpu_results if cpu_results[m])

    print(f'• CPU Overall Accuracy: {total_cpu_correct}/{total_cpu_tests} ({total_cpu_correct/total_cpu_tests*100:.1f}%)')

    # Agreement calculation
    agreement_count = 0
    comparable_models = 0
    for m in manual_results:
        if m in cpu_results and cpu_results[m] and m != 'bge-m3:567m':
            cpu_answers = [str(ans) for ans in cpu_results[m] if ans is not None]
            if cpu_answers:
                comparable_models += 1
                cpu_mode = Counter(cpu_answers).most_common(1)[0][0]
                if str(manual_results[m]) == cpu_mode:
                    agreement_count += 1

    print(f'• Manual vs CPU Agreement: {agreement_count}/{comparable_models} models ({agreement_count/comparable_models*100:.1f}%)')

    # Latency analysis
    all_latencies = [lat for model_lats in cpu_latencies.values() for lat in model_lats if lat < 300]  # Exclude timeouts
    print(f'• Average Latency: {sum(all_latencies)/len(all_latencies):.1f}s (range: {min(all_latencies):.1f}s - {max(all_latencies):.1f}s)')

    print()
    print('🚀 GPU run in progress - will add third comparison when complete!')
    
    return {
        'manual_results': manual_results,
        'cpu_results': cpu_results,
        'stats': {
            'manual_accuracy': manual_correct/total_models,
            'cpu_any_correct': cpu_any_correct/total_models,
            'agreement_rate': agreement_count/comparable_models if comparable_models > 0 else 0
        }
    }

if __name__ == '__main__':
    main()