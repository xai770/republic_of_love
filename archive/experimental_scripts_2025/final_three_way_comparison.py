#!/usr/bin/env python3
"""
COMPLETE Three-Way Strawberry Test Comparison
Manual vs CPU vs GPU Results Analysis
"""

import json
import pandas as pd
from collections import defaultdict, Counter

def main():
    print('🔍 COMPLETE THREE-WAY STRAWBERRY TEST COMPARISON')
    print('='*100)
    print()

    # Load your manual results
    manual_results = {
        'gpt-oss:latest': '3', 'mistral-nemo:12b': '3', 'granite3.1-moe:3b': '6',
        'qwen2.5:7b': '3', 'llama3.2:latest': '3', 'gemma3:4b': '3',
        'phi3:3.8b': '3', 'phi4-mini-reasoning:latest': '3', 'qwen3:latest': '3',
        'deepseek-r1:8b': '3', 'gemma3:1b': '2', 'qwen3:0.6b': '2',
        'qwen3:4b': '3', 'qwen3:1.7b': '3', 'mistral:latest': '3',
        'dolphin3:8b': '5', 'olmo2:latest': '4', 'codegemma:latest': '5',
        'qwen2.5vl:latest': 'non-bracket', 'gemma3n:latest': '3',
        'llama3.2:1b': '7', 'phi4-mini:latest': '3', 'gemma2:latest': '3',
        'gemma3n:e2b': '3'
    }

    # Load CPU run
    with open('strawberry_test_output/strawberry_results_20250919_081556.json', 'r') as f:
        cpu_data = json.load(f)

    # Load GPU run (now complete!)
    with open('strawberry_test_output/strawberry_results_20250919_094312.json', 'r') as f:
        gpu_data = json.load(f)

    # Process results - original prompt only for comparison
    def process_results(data):
        results = defaultdict(list)
        latencies = defaultdict(list)
        
        for test in data:
            if test and test.get('prompt_type') == 'original':
                model = test['model']
                answer = test['extracted_answer']
                latency = test['latency']
                
                results[model].append(str(answer) if answer is not None else 'TIMEOUT')
                latencies[model].append(latency)
        
        return results, latencies

    cpu_results, cpu_latencies = process_results(cpu_data)
    gpu_results, gpu_latencies = process_results(gpu_data)

    print('📊 COMPLETE Model-by-Model Comparison (Original Prompt)')
    print('-'*110)
    header_cols = ['Model', 'Manual', 'CPU Mode', 'GPU Mode', 'CPU Acc', 'GPU Acc', 'CPU Lat', 'GPU Lat']
    header = f"{header_cols[0]:<24} {header_cols[1]:<8} {header_cols[2]:<8} {header_cols[3]:<8} {header_cols[4]:<8} {header_cols[5]:<8} {header_cols[6]:<8} {header_cols[7]:<8}"
    print(header)
    print('-'*110)

    total_models = 0
    manual_correct = 0
    cpu_any_correct = 0
    gpu_any_correct = 0

    for model in sorted(set(list(manual_results.keys()) + list(cpu_results.keys()) + list(gpu_results.keys()))):
        if model == 'bge-m3:567m':  # Skip unsupported
            continue
        
        total_models += 1
        
        # Manual result
        manual_ans = manual_results.get(model, 'N/A')
        manual_is_correct = manual_ans == '3'
        if manual_is_correct:
            manual_correct += 1
        
        # CPU results
        cpu_mode = 'N/A'
        cpu_acc = 'N/A'
        cpu_lat = 'N/A'
        if model in cpu_results and cpu_results[model]:
            cpu_answers = [str(ans) for ans in cpu_results[model] if ans != 'TIMEOUT']
            if cpu_answers:
                cpu_mode = Counter(cpu_answers).most_common(1)[0][0]
                correct_count = sum(1 for ans in cpu_answers if ans == '3')
                cpu_acc = f'{correct_count}/5'
                cpu_lat = f'{sum(cpu_latencies[model])/len(cpu_latencies[model]):.1f}s'
                if correct_count > 0:
                    cpu_any_correct += 1
            else:
                cpu_mode = 'TIMEOUT'
        
        # GPU results
        gpu_mode = 'N/A'
        gpu_acc = 'N/A'
        gpu_lat = 'N/A'
        if model in gpu_results and gpu_results[model]:
            gpu_answers = [str(ans) for ans in gpu_results[model] if ans != 'TIMEOUT']
            if gpu_answers:
                gpu_mode = Counter(gpu_answers).most_common(1)[0][0]
                correct_count = sum(1 for ans in gpu_answers if ans == '3')
                gpu_acc = f'{correct_count}/5'
                gpu_lat = f'{sum(gpu_latencies[model])/len(gpu_latencies[model]):.1f}s'
                if correct_count > 0:
                    gpu_any_correct += 1
        
        model_short = model[:23]
        row = f'{model_short:<24} {manual_ans:<8} {cpu_mode:<8} {gpu_mode:<8} {cpu_acc:<8} {gpu_acc:<8} {cpu_lat:<8} {gpu_lat:<8}'
        print(row)

    print('-'*110)
    print(f'📈 FINAL ACCURACY COMPARISON:')
    print(f'Manual Run (Single):     {manual_correct}/{total_models} models correct ({manual_correct/total_models*100:.1f}%)')
    print(f'CPU Run (5x each):       {cpu_any_correct}/{total_models} models with ≥1 correct ({cpu_any_correct/total_models*100:.1f}%)')
    print(f'GPU Run (5x each):       {gpu_any_correct}/{total_models} models with ≥1 correct ({gpu_any_correct/total_models*100:.1f}%)')

    print()
    print('🎯 KEY INSIGHTS:')
    print('-'*50)

    # Compare CPU vs GPU performance
    cpu_gpu_agreement = 0
    comparable_models = 0

    for model in cpu_results:
        if model in gpu_results and cpu_results[model] and gpu_results[model]:
            comparable_models += 1
            cpu_answers = [str(ans) for ans in cpu_results[model] if ans != 'TIMEOUT']
            gpu_answers = [str(ans) for ans in gpu_results[model] if ans != 'TIMEOUT']
            
            if cpu_answers and gpu_answers:
                cpu_mode = Counter(cpu_answers).most_common(1)[0][0]
                gpu_mode = Counter(gpu_answers).most_common(1)[0][0]
                
                if cpu_mode == gpu_mode:
                    cpu_gpu_agreement += 1

    print(f'• CPU vs GPU Agreement: {cpu_gpu_agreement}/{comparable_models} models ({cpu_gpu_agreement/comparable_models*100:.1f}%)')

    # Hardware impact analysis
    cpu_total_correct = sum(sum(1 for ans in cpu_results[m] if str(ans) == '3') for m in cpu_results if cpu_results[m])
    cpu_total_tests = sum(len([ans for ans in cpu_results[m] if ans != 'TIMEOUT']) for m in cpu_results)

    gpu_total_correct = sum(sum(1 for ans in gpu_results[m] if str(ans) == '3') for m in gpu_results if gpu_results[m])
    gpu_total_tests = sum(len([ans for ans in gpu_results[m] if ans != 'TIMEOUT']) for m in gpu_results)

    print(f'• CPU Overall Accuracy: {cpu_total_correct}/{cpu_total_tests} ({cpu_total_correct/cpu_total_tests*100:.1f}%)')
    print(f'• GPU Overall Accuracy: {gpu_total_correct}/{gpu_total_tests} ({gpu_total_correct/gpu_total_tests*100:.1f}%)')

    # Latency comparison (exclude extreme outliers/timeouts)
    cpu_lats = [lat for model_lats in cpu_latencies.values() for lat in model_lats if lat < 300]
    gpu_lats = [lat for model_lats in gpu_latencies.values() for lat in model_lats if lat < 300]
    
    cpu_avg_latency = sum(cpu_lats) / len(cpu_lats)
    gpu_avg_latency = sum(gpu_lats) / len(gpu_lats)

    print(f'• Average Latency - CPU: {cpu_avg_latency:.1f}s, GPU: {gpu_avg_latency:.1f}s')
    print(f'• GPU Speed Improvement: {cpu_avg_latency/gpu_avg_latency:.1f}x faster')

    # Top differences between manual and both systematic runs
    print()
    print('🔄 BIGGEST DIFFERENCES FROM MANUAL:')
    print('-'*40)
    
    differences = []
    for model in manual_results:
        if model in cpu_results and model in gpu_results:
            manual_ans = manual_results[model]
            
            cpu_answers = [str(ans) for ans in cpu_results[model] if ans != 'TIMEOUT']
            gpu_answers = [str(ans) for ans in gpu_results[model] if ans != 'TIMEOUT']
            
            if cpu_answers and gpu_answers:
                cpu_mode = Counter(cpu_answers).most_common(1)[0][0]
                gpu_mode = Counter(gpu_answers).most_common(1)[0][0]
                
                # Check if manual differs from both systematic runs
                if str(manual_ans) != cpu_mode or str(manual_ans) != gpu_mode:
                    differences.append({
                        'model': model,
                        'manual': manual_ans,
                        'cpu': cpu_mode,
                        'gpu': gpu_mode,
                        'cpu_all': cpu_answers,
                        'gpu_all': gpu_answers
                    })

    for i, diff in enumerate(differences[:5]):
        model = diff['model'][:20]
        print(f'{i+1:2d}. {model:<20} Manual: {diff["manual"]:<3} CPU: {diff["cpu"]:<3} GPU: {diff["gpu"]:<3}')
        print(f'      CPU results: {diff["cpu_all"]}')
        print(f'      GPU results: {diff["gpu_all"]}')

    print()
    print('🏆 FINAL CONCLUSIONS:')
    print('-'*30)
    
    hardware_winner = 'GPU' if gpu_total_correct/gpu_total_tests > cpu_total_correct/cpu_total_tests else 'CPU'
    consistency_score = cpu_gpu_agreement/comparable_models if comparable_models > 0 else 0
    
    print(f'• Accuracy Winner: {hardware_winner} ({max(cpu_total_correct/cpu_total_tests, gpu_total_correct/gpu_total_tests)*100:.1f}%)')
    print(f'• Speed Winner: GPU ({cpu_avg_latency/gpu_avg_latency:.1f}x faster)')
    print(f'• CPU-GPU Consistency: {consistency_score*100:.1f}% agreement')
    print(f'• Manual vs Systematic: High variability suggests models are sensitive to context/iteration')
    
    # Save summary to file
    with open('strawberry_test_output/final_three_way_summary.txt', 'w') as f:
        f.write(f'Three-Way Strawberry Test Summary\\n')
        f.write(f'================================\\n\\n')
        f.write(f'Manual Run: {manual_correct}/{total_models} correct ({manual_correct/total_models*100:.1f}%)\\n')
        f.write(f'CPU Run: {cpu_any_correct}/{total_models} with correct answers ({cpu_any_correct/total_models*100:.1f}%)\\n')
        f.write(f'GPU Run: {gpu_any_correct}/{total_models} with correct answers ({gpu_any_correct/total_models*100:.1f}%)\\n')
        f.write(f'\\nHardware Impact: GPU {cpu_avg_latency/gpu_avg_latency:.1f}x faster\\n')
        f.write(f'CPU-GPU Agreement: {consistency_score*100:.1f}%\\n')

    print()
    print('📄 Summary saved to: strawberry_test_output/final_three_way_summary.txt')

if __name__ == '__main__':
    main()