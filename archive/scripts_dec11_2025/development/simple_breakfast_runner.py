#!/usr/bin/env python3
"""
SIMPLE BREAKFAST TEST RUNNER ☕
===============================
Run tests on existing clean data - no setup needed!
"""

import sqlite3
import json
import requests
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleBreakfastRunner:
    """Simple test runner for existing clean data"""
    
    def __init__(self, db_path: str = 'data/llmcore.db', ollama_url: str = 'http://localhost:11434'):
        self.db_path = db_path
        self.ollama_url = ollama_url
        
    def execute_strawberry_tests(self, limit: int = 5):
        """Execute strawberry counting tests"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing ce_char_extract test parameters
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.expected_response,
                tp.prompt_template,
                t.processing_model_name
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = 'ce_char_extract'
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        
        test_params = cursor.fetchall()
        
        logger.info(f"🍓 Running {len(test_params)} strawberry counting tests...")
        
        results = []
        for param_id, test_word, expected, prompt_template, model in test_params:
            
            # Format prompt for strawberry counting
            formatted_prompt = f'How many times does the letter "r" appear in the word "{test_word}"?'
            
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": formatted_prompt,
                        "stream": False
                    },
                    timeout=30
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    actual_response = response_data.get('response', '').strip()
                    
                    # Extract number from response
                    import re
                    numbers = re.findall(r'\d+', actual_response)
                    actual_number = numbers[0] if numbers else actual_response
                    
                    result_pass = 1 if actual_number == expected else 0
                    
                    # Store result
                    cursor.execute("""
                        INSERT INTO test_results (
                            param_id, processing_payload_actual, processing_response_actual,
                            processing_latency_ms, result_pass, confidence_score,
                            qa_validation_pass
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        param_id,
                        formatted_prompt,
                        actual_response,
                        latency_ms,
                        result_pass,
                        1.0 if result_pass else 0.0,
                        result_pass
                    ))
                    
                    status = "✅ PASS" if result_pass else "❌ FAIL"
                    logger.info(f"   {model}: '{test_word}' → {actual_number} (expected {expected}) {status}")
                    
                    results.append({
                        'param_id': param_id,
                        'model': model,
                        'word': test_word,
                        'expected': expected,
                        'actual': actual_number,
                        'pass': result_pass,
                        'latency_ms': latency_ms
                    })
                    
                else:
                    logger.error(f"   {model}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"   {model}: Error - {e}")
        
        conn.commit()
        conn.close()
        
        return results
    
    def show_results_dashboard(self):
        """Show breakfast results dashboard"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest results summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_results,
                SUM(result_pass) as passes,
                ROUND(AVG(processing_latency_ms), 1) as avg_latency,
                COUNT(DISTINCT tp.param_id) as unique_tests
            FROM test_results tr
            JOIN test_parameters tp ON tr.param_id = tp.param_id
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = 'ce_char_extract'
            AND tr.test_run_timestamp >= datetime('now', '-1 hour')
        """)
        
        summary = cursor.fetchone()
        
        # Get model breakdown
        cursor.execute("""
            SELECT 
                t.processing_model_name,
                COUNT(*) as tests,
                SUM(tr.result_pass) as passes,
                ROUND(AVG(tr.processing_latency_ms), 1) as avg_latency
            FROM test_results tr
            JOIN test_parameters tp ON tr.param_id = tp.param_id
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = 'ce_char_extract'
            AND tr.test_run_timestamp >= datetime('now', '-1 hour')
            GROUP BY t.processing_model_name
            ORDER BY SUM(tr.result_pass) DESC, AVG(tr.processing_latency_ms) ASC
        """)
        
        model_results = cursor.fetchall()
        
        print("\n" + "☕" + "="*58 + "☕")
        print("   🍓 BREAKFAST STRAWBERRY TEST RESULTS")
        print("☕" + "="*58 + "☕")
        
        if summary[0] > 0:
            total, passes, avg_latency, unique = summary
            pass_rate = (passes / total * 100) if total > 0 else 0
            
            print(f"\n📊 OVERALL SUMMARY:")
            print(f"   🎯 Results: {total} total, {passes} passed ({pass_rate:.1f}%)")
            print(f"   ⚡ Avg Latency: {avg_latency}ms")
            print(f"   🧪 Unique Tests: {unique}")
            
            print(f"\n🤖 MODEL PERFORMANCE:")
            print(f"{'Model':<25} {'Tests':<7} {'Passes':<7} {'Rate':<8} {'Latency':<8}")
            print("-" * 60)
            
            for model, tests, passes, latency in model_results:
                rate = (passes / tests * 100) if tests > 0 else 0
                model_short = model[:24]
                print(f"{model_short:<25} {tests:<7} {passes:<7} {rate:<7.1f}% {latency:<8}ms")
        else:
            print("\n📭 No recent results found - run some tests first!")
        
        conn.close()

def main():
    """Execute simple breakfast test run"""
    
    print("☀️" + "="*40 + "☀️")
    print("   SIMPLE BREAKFAST TESTING")
    print("☀️" + "="*40 + "☀️")
    print("Fresh strawberry counting tests! 🍓☕")
    print()
    
    runner = SimpleBreakfastRunner()
    
    # Run strawberry tests
    results = runner.execute_strawberry_tests(limit=8)
    
    # Show dashboard
    runner.show_results_dashboard()
    
    print(f"\n✅ Breakfast testing complete! {len(results)} tests executed")
    print("🧹 Database is clean and production-ready! 🎯")

if __name__ == "__main__":
    main()