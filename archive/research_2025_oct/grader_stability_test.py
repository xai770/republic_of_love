#!/usr/bin/env python3
"""
Grader Stability Validation
==========================
Test phi3:latest stability across multiple runs
"""

from test_improved_rubric import ImprovedRubricTester
import time
import json

def run_stability_test(runs=5):
    """Run calibration test multiple times to check stability"""
    print(f"🔬 GRADER STABILITY TEST - {runs} RUNS")
    print("=" * 50)
    
    tester = ImprovedRubricTester()
    all_results = []
    
    for run_num in range(1, runs + 1):
        print(f"\n📊 RUN {run_num}/{runs}")
        print("-" * 30)
        
        results, accuracy = tester.test_improved_rubric('phi3:latest')
        all_results.append({
            'run': run_num,
            'accuracy': accuracy,
            'results': results
        })
        
        print(f"Run {run_num} Accuracy: {accuracy:.1f}%")
        
        if run_num < runs:
            print("⏳ Cooling down 10s...")
            time.sleep(10)  # Cool down between runs
    
    # Analyze stability
    print("\n📈 STABILITY ANALYSIS")
    print("=" * 50)
    
    accuracies = [r['accuracy'] for r in all_results]
    avg_accuracy = sum(accuracies) / len(accuracies)
    min_accuracy = min(accuracies)
    max_accuracy = max(accuracies)
    variance = max_accuracy - min_accuracy
    
    print(f"Accuracies: {accuracies}")
    print(f"Average: {avg_accuracy:.1f}%")
    print(f"Range: {min_accuracy:.1f}% - {max_accuracy:.1f}%")
    print(f"Variance: ±{variance/2:.1f}%")
    
    # Stability assessment
    if variance <= 10:
        stability = "🏆 EXCELLENT (±5% or less)"
        recommendation = "✅ STABLE - Ready for production"
    elif variance <= 20:
        stability = "✅ GOOD (±10% or less)"  
        recommendation = "⚠️ ACCEPTABLE - Monitor in production"
    else:
        stability = "❌ POOR (>±10%)"
        recommendation = "🚨 UNSTABLE - Do not deploy"
    
    print(f"Stability: {stability}")
    print(f"Recommendation: {recommendation}")
    
    # Check for systematic patterns
    print(f"\n🔍 PATTERN ANALYSIS")
    print("-" * 30)
    
    # Track which test cases are consistently problematic
    test_case_failures = {}
    for result_set in all_results:
        for test_result in result_set['results']:
            case = test_result['strategy']
            if case not in test_case_failures:
                test_case_failures[case] = 0
            if not test_result['correct']:
                test_case_failures[case] += 1
    
    print("Failure rates by test case:")
    for case, failures in test_case_failures.items():
        failure_rate = failures / runs * 100
        status = "🚨" if failure_rate > 60 else "⚠️" if failure_rate > 20 else "✅"
        print(f"  {status} {case}: {failures}/{runs} failures ({failure_rate:.0f}%)")
    
    return all_results, avg_accuracy, variance

if __name__ == "__main__":
    results, avg_acc, variance = run_stability_test(3)  # Start with 3 runs for speed
    
    print(f"\n🎯 FINAL ASSESSMENT:")
    if avg_acc >= 60 and variance <= 20:
        print("✅ phi3:latest is STABLE and READY for production grading")
        print("🚀 Proceeding with improved rubric deployment")
    else:
        print("❌ phi3:latest stability issues detected")
        print("🔧 Need to debug or find alternative grader")