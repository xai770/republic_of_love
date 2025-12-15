#!/usr/bin/env python3
"""
Manual vs Automated Test Correlation Analysis
Compares manual test matrix results with Prime MIV performance
"""

import pandas as pd
import sqlite3

# Manual test results analysis
def analyze_manual_results():
    # Read manual test matrix
    df = pd.read_csv('/home/xai/Documents/ty_learn/data/llm_manual_test_matrix.csv')
    
    # Models that appear in both manual and automated testing
    overlapping_models = [
        'mistral-nemo:12b', 'granite3.1-moe:3b', 'qwen2.5:7b', 'llama3.2:latest',
        'gemma3:4b', 'phi3:3.8b', 'phi4-mini-reasoning:latest', 'qwen3:latest',
        'gemma3:1b', 'qwen3:0.6b', 'qwen3:4b', 'qwen3:1.7b', 'mistral:latest',
        'dolphin3:latest', 'olmo2:latest', 'codegemma:latest', 'codegemma:2b',
        'phi3:latest', 'qwen2.5vl:latest', 'gemma3n:latest', 'llama3.2:1b',
        'gemma2:latest', 'gemma3n:e2b'
    ]
    
    # Calculate success rates for each model
    results = {}
    
    for model in overlapping_models:
        if model in df.columns:
            model_col = df[model]
            expected_col = df['Expected']
            
            # Count correct responses (ignoring empty/error responses)
            correct_count = 0
            total_valid = 0
            
            for i, (expected, actual) in enumerate(zip(expected_col, model_col)):
                if pd.notna(actual) and str(actual).strip() != '' and 'error' not in str(actual).lower():
                    total_valid += 1
                    if str(expected).strip() == str(actual).strip():
                        correct_count += 1
            
            if total_valid > 0:
                success_rate = (correct_count / total_valid) * 100
                results[model] = {
                    'manual_success_rate': success_rate,
                    'correct_responses': correct_count,
                    'total_valid_responses': total_valid
                }
    
    return results

# Get Prime MIV counts from automated testing
def get_prime_miv_data():
    conn = sqlite3.connect('/home/xai/Documents/ty_learn/data/llmcore.db')
    
    query = """
    WITH PrimeMIVCombos AS (
      SELECT
        d.instruction_id,
        d.variation_id, 
        d.model_name,
        AVG(d.processing_latency_dish) as avg_latency
      FROM dishes d
      INNER JOIN variations v ON d.variation_id = v.variation_id
      GROUP BY d.instruction_id, d.variation_id, d.model_name
      HAVING SUM(d.processing_received_response_dish = v.expected_response) = 5
    ),
    PrimeMIVs AS (
      SELECT
        model_name,
        COUNT(*) as prime_miv_count,
        AVG(avg_latency) as avg_latency
      FROM PrimeMIVCombos
      GROUP BY model_name
    ),
    ModelStats AS (
      SELECT 
        model_name,
        COUNT(DISTINCT instruction_id) as instructions_tested,
        COUNT(DISTINCT variation_id) as variations_tested
      FROM dishes
      GROUP BY model_name
    )
    SELECT 
      p.model_name,
      COALESCE(p.prime_miv_count, 0) as prime_miv_count,
      COALESCE(p.avg_latency, 0) as avg_latency_ms,
      s.instructions_tested,
      s.variations_tested
    FROM ModelStats s
    LEFT JOIN PrimeMIVs p ON s.model_name = p.model_name
    ORDER BY prime_miv_count DESC;
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df.set_index('model_name').to_dict('index')

# Main analysis
def main():
    print("🔍 Manual vs Automated Test Correlation Analysis")
    print("=" * 60)
    
    # Get manual results
    manual_results = analyze_manual_results()
    print(f"\n📊 Manual Test Results ({len(manual_results)} models):")
    
    # Get automated results  
    automated_results = get_prime_miv_data()
    print(f"\n🤖 Automated Prime MIV Results ({len(automated_results)} models):")
    
    # Correlation analysis
    print(f"\n🔄 Correlation Analysis:")
    print("Model Name | Manual Success % | Prime MIVs | Avg Latency | Correlation")
    print("-" * 80)
    
    correlations = []
    
    for model in manual_results:
        if model in automated_results:
            manual_rate = manual_results[model]['manual_success_rate']
            prime_mivs = automated_results[model]['prime_miv_count']
            avg_latency = automated_results[model]['avg_latency_ms']
            
            # Simple correlation indicator
            if manual_rate > 70 and prime_mivs > 10:
                correlation = "✅ HIGH-HIGH"
            elif manual_rate < 30 and prime_mivs < 5:
                correlation = "🔴 LOW-LOW"  
            elif manual_rate > 70 and prime_mivs < 5:
                correlation = "⚠️ HIGH-LOW"
            elif manual_rate < 30 and prime_mivs > 10:
                correlation = "🤔 LOW-HIGH"
            else:
                correlation = "🟡 MIXED"
                
            correlations.append({
                'model': model,
                'manual_rate': manual_rate,
                'prime_mivs': prime_mivs,
                'correlation': correlation
            })
            
            print(f"{model:<20} | {manual_rate:>8.1f}% | {prime_mivs:>8} | {avg_latency:>8.0f}ms | {correlation}")
    
    # Summary statistics
    print(f"\n📈 Summary:")
    high_high = len([c for c in correlations if c['correlation'] == "✅ HIGH-HIGH"])
    low_low = len([c for c in correlations if c['correlation'] == "🔴 LOW-LOW"])
    total = len(correlations)
    
    print(f"High Manual + High Prime MIVs: {high_high}/{total} models")
    print(f"Low Manual + Low Prime MIVs: {low_low}/{total} models")
    print(f"Consistent correlation: {(high_high + low_low)}/{total} = {((high_high + low_low)/total)*100:.1f}%")

if __name__ == "__main__":
    main()