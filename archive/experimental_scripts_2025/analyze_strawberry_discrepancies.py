#!/usr/bin/env python3
"""
Analyze discrepancies between manual and automated strawberry test results
"""

import csv
import json
from collections import defaultdict

def analyze_discrepancies():
    """Find cases where manual and automated results disagree"""
    
    print("🔍 Analyzing Manual vs Automated Strawberry Test Discrepancies")
    print("=" * 60)
    
    discrepancies = []
    
    # Read the CSV file
    with open('/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            model = row['Model']
            manual_result = row['Manual_Result']
            manual_correct = row['Manual_Correct'] == 'Yes'
            
            # Parse automated accuracies
            cpu_accuracy = float(row['CPU_Accuracy'].replace('%', '')) if row['CPU_Accuracy'] != 'N/A' else None
            gpu_accuracy = float(row['GPU_Accuracy'].replace('%', '')) if row['GPU_Accuracy'] != 'N/A' else None
            
            cpu_responses = row['CPU_Sample_Responses']
            gpu_responses = row['GPU_Sample_Responses']
            
            # Skip models not in manual test
            if manual_result == 'N/A':
                continue
                
            # Determine if automated tests were correct (>50% accuracy suggests mostly correct)
            cpu_mostly_correct = cpu_accuracy is not None and cpu_accuracy >= 50
            gpu_mostly_correct = gpu_accuracy is not None and gpu_accuracy >= 50
            
            # Check for discrepancies
            cpu_disagrees = (manual_correct != cpu_mostly_correct) if cpu_accuracy is not None else False
            gpu_disagrees = (manual_correct != gpu_mostly_correct) if gpu_accuracy is not None else False
            
            if cpu_disagrees or gpu_disagrees:
                discrepancy_type = []
                if cpu_disagrees:
                    discrepancy_type.append(f"CPU: {cpu_accuracy:.1f}%")
                if gpu_disagrees:
                    discrepancy_type.append(f"GPU: {gpu_accuracy:.1f}%")
                
                discrepancies.append({
                    'model': model,
                    'manual_result': manual_result,
                    'manual_correct': manual_correct,
                    'cpu_accuracy': cpu_accuracy,
                    'gpu_accuracy': gpu_accuracy,
                    'cpu_responses': cpu_responses,
                    'gpu_responses': gpu_responses,
                    'discrepancy_type': ' | '.join(discrepancy_type)
                })
    
    # Print discrepancies
    print(f"\n📊 Found {len(discrepancies)} models with manual vs automated discrepancies:")
    print()
    
    for i, disc in enumerate(discrepancies, 1):
        print(f"{i}. **{disc['model']}**")
        print(f"   Manual: {disc['manual_result']} ({'✅ Correct' if disc['manual_correct'] else '❌ Wrong'})")
        print(f"   Automated: {disc['discrepancy_type']}")
        print(f"   CPU samples: {disc['cpu_responses'][:80]}{'...' if len(disc['cpu_responses']) > 80 else ''}")
        print(f"   GPU samples: {disc['gpu_responses'][:80]}{'...' if len(disc['gpu_responses']) > 80 else ''}")
        print()
    
    # Category analysis
    print("\n🔍 **Discrepancy Categories:**")
    
    manual_correct_auto_wrong = [d for d in discrepancies if d['manual_correct']]
    manual_wrong_auto_correct = [d for d in discrepancies if not d['manual_correct']]
    
    print(f"\n**Manual Correct (✅) but Automated Wrong (❌):** {len(manual_correct_auto_wrong)} models")
    for d in manual_correct_auto_wrong:
        cpu_acc = f"{d['cpu_accuracy']:.1f}%" if d['cpu_accuracy'] is not None else "N/A"
        gpu_acc = f"{d['gpu_accuracy']:.1f}%" if d['gpu_accuracy'] is not None else "N/A" 
        print(f"   - {d['model']}: Manual {d['manual_result']} vs CPU {cpu_acc} / GPU {gpu_acc}")
    
    print(f"\n**Manual Wrong (❌) but Automated Correct (✅):** {len(manual_wrong_auto_correct)} models")
    for d in manual_wrong_auto_correct:
        cpu_acc = f"{d['cpu_accuracy']:.1f}%" if d['cpu_accuracy'] is not None else "N/A"
        gpu_acc = f"{d['gpu_accuracy']:.1f}%" if d['gpu_accuracy'] is not None else "N/A"
        print(f"   - {d['model']}: Manual {d['manual_result']} vs CPU {cpu_acc} / GPU {gpu_acc}")
    
    # Hardware consistency check
    print(f"\n🖥️ **Hardware Consistency Issues:**")
    hardware_issues = []
    
    with open('/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['CPU_Accuracy'] != 'N/A' and row['GPU_Accuracy'] != 'N/A':
                cpu_acc = float(row['CPU_Accuracy'].replace('%', ''))
                gpu_acc = float(row['GPU_Accuracy'].replace('%', ''))
                diff = abs(cpu_acc - gpu_acc)
                
                if diff >= 30:  # 30% or more difference
                    hardware_issues.append({
                        'model': row['Model'],
                        'cpu_acc': cpu_acc,
                        'gpu_acc': gpu_acc,
                        'diff': diff
                    })
    
    hardware_issues.sort(key=lambda x: x['diff'], reverse=True)
    
    print(f"Found {len(hardware_issues)} models with ≥30% CPU/GPU accuracy difference:")
    for issue in hardware_issues:
        print(f"   - {issue['model']}: CPU {issue['cpu_acc']:.1f}% vs GPU {issue['gpu_acc']:.1f}% (Δ{issue['diff']:.1f}%)")
    
    return discrepancies, hardware_issues

if __name__ == "__main__":
    discrepancies, hardware_issues = analyze_discrepancies()