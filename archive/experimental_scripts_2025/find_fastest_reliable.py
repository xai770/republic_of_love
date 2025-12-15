#!/usr/bin/env python3
"""
Find the fastest reliable strawberry test performers
"""

import csv
import json

def analyze_speed_reliability():
    """Find models that are both fast and accurate"""
    
    print("🚀 Finding Fastest Reliable Strawberry Test Performers")
    print("=" * 55)
    
    performers = []
    
    # Read the CSV file
    with open('/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            model = row['Model']
            
            # Parse accuracies
            cpu_accuracy = float(row['CPU_Accuracy'].replace('%', '')) if row['CPU_Accuracy'] != 'N/A' else 0
            gpu_accuracy = float(row['GPU_Accuracy'].replace('%', '')) if row['GPU_Accuracy'] != 'N/A' else 0
            
            # Parse latencies (remove 's' suffix)
            cpu_latency = float(row['CPU_Avg_Latency'].replace('s', '')) if row['CPU_Avg_Latency'] != 'N/A' else float('inf')
            gpu_latency = float(row['GPU_Avg_Latency'].replace('s', '')) if row['GPU_Avg_Latency'] != 'N/A' else float('inf')
            
            # Parse prompt-specific accuracies
            cpu_original = float(row['CPU_Original_Prompt'].replace('%', '')) if row['CPU_Original_Prompt'] != 'N/A' else 0
            cpu_simplified = float(row['CPU_Simplified_Prompt'].replace('%', '')) if row['CPU_Simplified_Prompt'] != 'N/A' else 0
            gpu_original = float(row['GPU_Original_Prompt'].replace('%', '')) if row['GPU_Original_Prompt'] != 'N/A' else 0
            gpu_simplified = float(row['GPU_Simplified_Prompt'].replace('%', '')) if row['GPU_Simplified_Prompt'] != 'N/A' else 0
            
            manual_correct = row['Manual_Correct'] == 'Yes'
            
            # Calculate best configuration for each hardware
            cpu_configs = [
                {'hardware': 'CPU', 'prompt': 'original', 'accuracy': cpu_original, 'latency': cpu_latency},
                {'hardware': 'CPU', 'prompt': 'simplified', 'accuracy': cpu_simplified, 'latency': cpu_latency}
            ]
            
            gpu_configs = [
                {'hardware': 'GPU', 'prompt': 'original', 'accuracy': gpu_original, 'latency': gpu_latency},
                {'hardware': 'GPU', 'prompt': 'simplified', 'accuracy': gpu_simplified, 'latency': gpu_latency}
            ]
            
            all_configs = cpu_configs + gpu_configs
            
            for config in all_configs:
                if config['accuracy'] >= 80 and config['latency'] < float('inf'):  # 80%+ accuracy threshold
                    performers.append({
                        'model': model,
                        'hardware': config['hardware'],
                        'prompt': config['prompt'],
                        'accuracy': config['accuracy'],
                        'latency': config['latency'],
                        'manual_match': manual_correct,
                        'speed_score': config['accuracy'] / config['latency']  # Accuracy per second
                    })
    
    # Sort by speed score (accuracy per second) descending
    performers.sort(key=lambda x: x['speed_score'], reverse=True)
    
    print("\n🏆 **Top Performers (≥80% accuracy, sorted by speed score):**\n")
    
    if not performers:
        print("❌ No models achieved ≥80% accuracy threshold!")
        
        # Show best available performers
        print("\n📊 **Best Available Performers (≥50% accuracy):**\n")
        relaxed_performers = []
        
        # Re-read with relaxed criteria
        with open('/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv', 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                model = row['Model']
                cpu_accuracy = float(row['CPU_Accuracy'].replace('%', '')) if row['CPU_Accuracy'] != 'N/A' else 0
                gpu_accuracy = float(row['GPU_Accuracy'].replace('%', '')) if row['GPU_Accuracy'] != 'N/A' else 0
                cpu_latency = float(row['CPU_Avg_Latency'].replace('s', '')) if row['CPU_Avg_Latency'] != 'N/A' else float('inf')
                gpu_latency = float(row['GPU_Avg_Latency'].replace('s', '')) if row['GPU_Avg_Latency'] != 'N/A' else float('inf')
                
                # Take best overall accuracy
                best_accuracy = max(cpu_accuracy, gpu_accuracy)
                best_hardware = 'CPU' if cpu_accuracy >= gpu_accuracy else 'GPU'
                best_latency = cpu_latency if best_hardware == 'CPU' else gpu_latency
                
                if best_accuracy >= 50 and best_latency < float('inf'):
                    relaxed_performers.append({
                        'model': model,
                        'hardware': best_hardware,
                        'accuracy': best_accuracy,
                        'latency': best_latency,
                        'speed_score': best_accuracy / best_latency
                    })
        
        relaxed_performers.sort(key=lambda x: x['speed_score'], reverse=True)
        
        for i, p in enumerate(relaxed_performers[:10], 1):
            print(f"{i:2d}. **{p['model']}** ({p['hardware']})")
            print(f"     Accuracy: {p['accuracy']:.1f}% | Latency: {p['latency']:.1f}s | Score: {p['speed_score']:.2f}")
            print()
        
    else:
        for i, p in enumerate(performers, 1):
            print(f"{i:2d}. **{p['model']}** ({p['hardware']} + {p['prompt']} prompt)")
            print(f"     Accuracy: {p['accuracy']:.1f}% | Latency: {p['latency']:.1f}s | Score: {p['speed_score']:.2f}")
            if p['manual_match']:
                print(f"     ✅ Matches manual test result")
            else:
                print(f"     ⚠️  Disagrees with manual test")
            print()
    
    # Find absolute fastest reliable model
    print("\n⚡ **Speed Champions:**\n")
    
    all_reliable = []
    with open('/home/xai/Documents/ty_learn/comprehensive_strawberry_comparison_20250919.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            model = row['Model']
            cpu_accuracy = float(row['CPU_Accuracy'].replace('%', '')) if row['CPU_Accuracy'] != 'N/A' else 0
            gpu_accuracy = float(row['GPU_Accuracy'].replace('%', '')) if row['GPU_Accuracy'] != 'N/A' else 0
            cpu_latency = float(row['CPU_Avg_Latency'].replace('s', '')) if row['CPU_Avg_Latency'] != 'N/A' else float('inf')
            gpu_latency = float(row['GPU_Avg_Latency'].replace('s', '')) if row['GPU_Avg_Latency'] != 'N/A' else float('inf')
            
            if cpu_accuracy >= 80:
                all_reliable.append({'model': model, 'hardware': 'CPU', 'accuracy': cpu_accuracy, 'latency': cpu_latency})
            if gpu_accuracy >= 80:
                all_reliable.append({'model': model, 'hardware': 'GPU', 'accuracy': gpu_accuracy, 'latency': gpu_latency})
    
    # Sort by latency (fastest first)
    all_reliable.sort(key=lambda x: x['latency'])
    
    print("**Fastest ≥80% accurate models:**")
    for i, p in enumerate(all_reliable[:5], 1):
        print(f"{i}. {p['model']} ({p['hardware']}): {p['latency']:.1f}s @ {p['accuracy']:.1f}%")
    
    # Overall recommendation
    print(f"\n🎯 **RECOMMENDATION:**")
    if performers:
        top = performers[0]
        print(f"   **{top['model']}** with **{top['prompt']} prompt** on **{top['hardware']}**")
        print(f"   → {top['accuracy']:.1f}% accuracy in {top['latency']:.1f}s (score: {top['speed_score']:.2f})")
    elif relaxed_performers:
        top = relaxed_performers[0]
        print(f"   **{top['model']}** on **{top['hardware']}** (best available)")
        print(f"   → {top['accuracy']:.1f}% accuracy in {top['latency']:.1f}s (score: {top['speed_score']:.2f})")
    else:
        print("   No reliable performers found in dataset!")

if __name__ == "__main__":
    analyze_speed_reliability()