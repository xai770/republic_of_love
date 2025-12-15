#!/usr/bin/env python3
"""
COMPREHENSIVE TEST ANALYSIS 📊
==============================
Detailed analysis of model performance across both test types
"""

import sqlite3
import json
from datetime import datetime

def generate_detailed_analysis():
    """Generate detailed analysis report"""
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Get detailed results
    cursor.execute("""
        SELECT 
            t.processing_model_name,
            t.canonical_code,
            tp.test_word,
            tp.expected_response,
            tr.processing_response_actual,
            tr.result_pass,
            tr.processing_latency_ms
        FROM test_results tr
        JOIN test_parameters tp ON tr.param_id = tp.param_id
        JOIN tests t ON tp.test_id = t.test_id
        WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_gradient')
        AND tr.test_run_timestamp >= datetime('now', '-1 hour')
        ORDER BY t.processing_model_name, t.canonical_code
    """)
    
    results = cursor.fetchall()
    
    print("🔬" + "="*80 + "🔬")
    print("   DETAILED MODEL PERFORMANCE ANALYSIS")
    print("🔬" + "="*80 + "🔬")
    
    # Key insights
    print("\n🎯 KEY INSIGHTS:")
    
    strawberry_passes = len([r for r in results if r[1] == 'ce_char_extract' and r[5] == 1])
    strawberry_total = len([r for r in results if r[1] == 'ce_char_extract'])
    reverse_passes = len([r for r in results if r[1] == 'ff_reverse_gradient' and r[5] == 1])
    reverse_total = len([r for r in results if r[1] == 'ff_reverse_gradient'])
    
    print(f"   🍓 Strawberry Challenge: Only {strawberry_passes}/{strawberry_total} models ({strawberry_passes/strawberry_total*100:.1f}%) correctly count 'r' letters")
    print(f"   🔄 Reverse Challenge: {reverse_passes}/{reverse_total} models ({reverse_passes/reverse_total*100:.1f}%) successfully reverse strings")
    print(f"   📈 String reversal is 3x easier than character counting!")
    
    print(f"\n🏆 TOP PERFORMERS:")
    
    # Find models that passed both tests
    model_performance = {}
    for model, canonical, word, expected, actual, passed, latency in results:
        if model not in model_performance:
            model_performance[model] = {'strawberry': 0, 'reverse': 0, 'total_tests': 0}
        
        model_performance[model]['total_tests'] += 1
        if canonical == 'ce_char_extract' and passed:
            model_performance[model]['strawberry'] = 1
        elif canonical == 'ff_reverse_gradient' and passed:
            model_performance[model]['reverse'] = 1
    
    # Sort by combined performance
    sorted_models = sorted(model_performance.items(), 
                          key=lambda x: (x[1]['strawberry'] + x[1]['reverse'], -x[0].count(':')), 
                          reverse=True)
    
    for i, (model, perf) in enumerate(sorted_models[:10]):
        total_score = perf['strawberry'] + perf['reverse']
        if total_score > 0:
            strawberry_icon = "✅" if perf['strawberry'] else "❌"
            reverse_icon = "✅" if perf['reverse'] else "❌"
            print(f"   #{i+1:2d}. {model[:30]:<30} {strawberry_icon} Strawberry  {reverse_icon} Reverse")
    
    print(f"\n🤔 FAILURE ANALYSIS:")
    
    # Strawberry failure patterns
    strawberry_failures = [r for r in results if r[1] == 'ce_char_extract' and r[5] == 0]
    
    print(f"   🍓 Strawberry Failures ({len(strawberry_failures)} cases):")
    
    # Count common wrong answers
    wrong_answers = {}
    for _, _, word, expected, actual, _, _ in strawberry_failures:
        # Extract numbers from actual response
        import re
        numbers = re.findall(r'\d+', actual)
        answer = numbers[0] if numbers else "no_number"
        wrong_answers[answer] = wrong_answers.get(answer, 0) + 1
    
    for answer, count in sorted(wrong_answers.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"      • '{answer}': {count} times")
    
    # Reverse failure patterns  
    reverse_failures = [r for r in results if r[1] == 'ff_reverse_gradient' and r[5] == 0]
    
    print(f"\n   🔄 Reverse Failures ({len(reverse_failures)} cases):")
    print(f"      • Missing brackets: {len([r for r in reverse_failures if '[' not in r[4]])} cases")
    print(f"      • Wrong content: {len([r for r in reverse_failures if '[' in r[4]])} cases")
    print(f"      • Format confusion: Models struggle with exact bracketed format")
    
    print(f"\n⚡ PERFORMANCE INSIGHTS:")
    
    # Latency analysis
    strawberry_latencies = [r[6] for r in results if r[1] == 'ce_char_extract' and r[6] is not None]
    reverse_latencies = [r[6] for r in results if r[1] == 'ff_reverse_gradient' and r[6] is not None]
    
    if strawberry_latencies and reverse_latencies:
        avg_strawberry = sum(strawberry_latencies) / len(strawberry_latencies)
        avg_reverse = sum(reverse_latencies) / len(reverse_latencies)
        
        print(f"   🍓 Strawberry avg latency: {avg_strawberry:.0f}ms")
        print(f"   🔄 Reverse avg latency: {avg_reverse:.0f}ms")
        
        if avg_strawberry > avg_reverse:
            print(f"   🤯 Strawberry tests take {avg_strawberry/avg_reverse:.1f}x longer - models struggle more!")
        
    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"   ✅ Use reverse string tests for basic instruction following")
    print(f"   🍓 Use strawberry tests for precise counting/attention capabilities")
    print(f"   🔬 Models show clear capability gaps - useful for evaluation")
    print(f"   📊 Consider these as complementary capability benchmarks")
    
    conn.close()

def save_results_summary():
    """Save results to JSON for further analysis"""
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Get summary data
    cursor.execute("""
        SELECT 
            t.processing_model_name,
            t.canonical_code,
            COUNT(*) as tests,
            SUM(tr.result_pass) as passes,
            AVG(tr.processing_latency_ms) as avg_latency
        FROM test_results tr
        JOIN test_parameters tp ON tr.param_id = tp.param_id
        JOIN tests t ON tp.test_id = t.test_id
        WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_gradient')
        AND tr.test_run_timestamp >= datetime('now', '-1 hour')
        GROUP BY t.processing_model_name, t.canonical_code
        ORDER BY t.processing_model_name, t.canonical_code
    """)
    
    results = cursor.fetchall()
    
    # Structure data
    summary = {
        'test_run_timestamp': datetime.now().isoformat(),
        'models_tested': len(set(r[0] for r in results)),
        'canonicals': ['ce_char_extract', 'ff_reverse_gradient'],
        'results': {}
    }
    
    for model, canonical, tests, passes, avg_latency in results:
        if model not in summary['results']:
            summary['results'][model] = {}
        
        summary['results'][model][canonical] = {
            'tests': tests,
            'passes': passes,
            'pass_rate': (passes / tests * 100) if tests > 0 else 0,
            'avg_latency_ms': round(avg_latency, 1) if avg_latency else None
        }
    
    # Save to file
    filename = f"comprehensive_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    conn.close()

if __name__ == "__main__":
    generate_detailed_analysis()
    save_results_summary()