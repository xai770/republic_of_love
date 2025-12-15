#!/usr/bin/env python3
"""
COMPREHENSIVE MODEL TEST RUNNER 🚀
==================================
Run both strawberry counting and string reverse tests across ALL models
"""

import sqlite3
import json
import requests
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTestRunner:
    """Run tests across all models for both canonicals"""
    
    def __init__(self, db_path: str = 'data/llmcore.db', ollama_url: str = 'http://localhost:11434'):
        self.db_path = db_path
        self.ollama_url = ollama_url
        
    def get_available_models(self):
        """Get list of available models from Ollama"""
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                available_models = [model['name'] for model in data.get('models', [])]
                logger.info(f"📋 Found {len(available_models)} available models in Ollama")
                return available_models
            else:
                logger.warning("Could not fetch Ollama models, using database models")
                return []
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
            return []
    
    def setup_reverse_gradient_tests(self):
        """Set up reverse gradient tests for all models"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check existing reverse gradient tests
        cursor.execute("SELECT COUNT(*) FROM tests WHERE canonical_code = 'ff_reverse_gradient'")
        existing = cursor.fetchone()[0]
        
        if existing > 0:
            logger.info(f"✅ ff_reverse_gradient already has {existing} tests")
            conn.close()
            return existing
        
        logger.info("🔄 Setting up ff_reverse_gradient tests...")
        
        # Get all models from ce_char_extract tests
        cursor.execute("""
            SELECT DISTINCT processing_model_name 
            FROM tests 
            WHERE canonical_code = 'ce_char_extract'
            ORDER BY processing_model_name
        """)
        
        models = [row[0] for row in cursor.fetchall()]
        
        # Create simple reverse gradient tests - one per model
        test_words = [
            ('cat', 'tac'),
            ('dog', 'god'), 
            ('hello', 'olleh'),
            ('world', 'dlrow'),
            ('test', 'tset')
        ]
        
        created_count = 0
        for i, model in enumerate(models):
            # Cycle through test words
            word, reversed_word = test_words[i % len(test_words)]
            
            # Create test
            cursor.execute("""
                INSERT INTO tests (
                    canonical_code, processing_model_name,
                    created_at, status
                ) VALUES (?, ?, CURRENT_TIMESTAMP, 'ready')
            """, ('ff_reverse_gradient', model))
            
            test_id = cursor.lastrowid
            
            # Create test parameter
            cursor.execute("""
                INSERT INTO test_parameters (
                    test_id, test_word, difficulty_level, expected_response,
                    prompt_template, response_format, word_length, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                word,
                len(word),
                f"[{reversed_word}]",
                'Write "{word}" backwards. Format your response as [string].',
                'bracketed_string',
                len(word),
                len(word)
            ))
            
            created_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created {created_count} ff_reverse_gradient tests")
        return created_count
    
    def execute_strawberry_tests(self):
        """Execute all strawberry counting tests"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all strawberry test parameters
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.expected_response,
                t.processing_model_name
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = 'ce_char_extract'
            ORDER BY t.processing_model_name
        """)
        
        test_params = cursor.fetchall()
        
        logger.info(f"🍓 Executing {len(test_params)} strawberry counting tests...")
        
        results = []
        for param_id, test_word, expected, model in test_params:
            
            # Clean prompt for strawberry counting
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
                    timeout=45
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    actual_response = response_data.get('response', '').strip()
                    
                    # Extract first number from response
                    import re
                    numbers = re.findall(r'\d+', actual_response)
                    actual_number = numbers[0] if numbers else "0"
                    
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
                    
                    status = "✅" if result_pass else "❌"
                    logger.info(f"   🍓 {model[:20]:<20}: '{test_word}' → {actual_number} (exp: {expected}) {status}")
                    
                    results.append({
                        'canonical': 'ce_char_extract',
                        'model': model,
                        'word': test_word,
                        'expected': expected,
                        'actual': actual_number,
                        'pass': result_pass,
                        'latency_ms': latency_ms
                    })
                    
                else:
                    logger.error(f"   🍓 {model}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"   🍓 {model}: Error - {str(e)[:50]}...")
        
        conn.commit()
        conn.close()
        
        return results
    
    def execute_reverse_tests(self):
        """Execute all reverse string tests"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all reverse test parameters
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.expected_response,
                t.processing_model_name
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = 'ff_reverse_gradient'
            ORDER BY t.processing_model_name
        """)
        
        test_params = cursor.fetchall()
        
        logger.info(f"🔄 Executing {len(test_params)} reverse string tests...")
        
        results = []
        for param_id, test_word, expected, model in test_params:
            
            formatted_prompt = f'Write "{test_word}" backwards. Format your response as [string].'
            
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": formatted_prompt,
                        "stream": False
                    },
                    timeout=45
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    actual_response = response_data.get('response', '').strip()
                    
                    # Extract bracketed content
                    import re
                    brackets = re.findall(r'\[([^\]]+)\]', actual_response)
                    actual_content = f"[{brackets[0]}]" if brackets else actual_response
                    
                    result_pass = 1 if actual_content.lower() == expected.lower() else 0
                    
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
                    
                    status = "✅" if result_pass else "❌"
                    logger.info(f"   🔄 {model[:20]:<20}: '{test_word}' → {actual_content} (exp: {expected}) {status}")
                    
                    results.append({
                        'canonical': 'ff_reverse_gradient',
                        'model': model,
                        'word': test_word,
                        'expected': expected,
                        'actual': actual_content,
                        'pass': result_pass,
                        'latency_ms': latency_ms
                    })
                    
                else:
                    logger.error(f"   🔄 {model}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"   🔄 {model}: Error - {str(e)[:50]}...")
        
        conn.commit()
        conn.close()
        
        return results
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test results report"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get overall summary by canonical
        cursor.execute("""
            SELECT 
                t.canonical_code,
                COUNT(*) as total_tests,
                SUM(tr.result_pass) as passes,
                ROUND(AVG(tr.processing_latency_ms), 1) as avg_latency,
                COUNT(DISTINCT t.processing_model_name) as models_tested
            FROM test_results tr
            JOIN test_parameters tp ON tr.param_id = tp.param_id
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_gradient')
            AND tr.test_run_timestamp >= datetime('now', '-2 hours')
            GROUP BY t.canonical_code
            ORDER BY t.canonical_code
        """)
        
        canonical_summary = cursor.fetchall()
        
        # Get model performance across both canonicals
        cursor.execute("""
            SELECT 
                t.processing_model_name,
                t.canonical_code,
                COUNT(*) as tests,
                SUM(tr.result_pass) as passes,
                ROUND(AVG(tr.processing_latency_ms), 1) as avg_latency
            FROM test_results tr
            JOIN test_parameters tp ON tr.param_id = tp.param_id
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code IN ('ce_char_extract', 'ff_reverse_gradient')
            AND tr.test_run_timestamp >= datetime('now', '-2 hours')
            GROUP BY t.processing_model_name, t.canonical_code
            ORDER BY t.processing_model_name, t.canonical_code
        """)
        
        model_performance = cursor.fetchall()
        
        print("\n" + "🚀" + "="*78 + "🚀")
        print("   COMPREHENSIVE MODEL TEST RESULTS")
        print("🚀" + "="*78 + "🚀")
        
        # Canonical summary
        print("\n📊 OVERALL PERFORMANCE BY TEST TYPE:")
        print("-" * 60)
        for code, total, passes, avg_latency, models in canonical_summary:
            pass_rate = (passes / total * 100) if total > 0 else 0
            test_name = "🍓 Strawberry Count" if code == "ce_char_extract" else "🔄 String Reverse"
            
            print(f"{test_name}:")
            print(f"   📈 Success Rate: {passes}/{total} ({pass_rate:.1f}%)")
            print(f"   ⚡ Avg Latency:  {avg_latency}ms")
            print(f"   🤖 Models:       {models}")
            print()
        
        # Model comparison
        print("🤖 MODEL PERFORMANCE COMPARISON:")
        print(f"{'Model':<25} {'Strawberry':<12} {'Reverse':<12} {'Overall':<10}")
        print("-" * 65)
        
        # Group by model
        model_data = {}
        for model, canonical, tests, passes, latency in model_performance:
            if model not in model_data:
                model_data[model] = {}
            
            pass_rate = (passes / tests * 100) if tests > 0 else 0
            model_data[model][canonical] = {
                'rate': pass_rate,
                'tests': tests,
                'passes': passes,
                'latency': latency
            }
        
        for model in sorted(model_data.keys()):
            data = model_data[model]
            
            strawberry = data.get('ce_char_extract', {})
            reverse = data.get('ff_reverse_gradient', {})
            
            strawberry_str = f"{strawberry.get('rate', 0):.0f}%" if strawberry else "N/A"
            reverse_str = f"{reverse.get('rate', 0):.0f}%" if reverse else "N/A"
            
            # Calculate overall
            total_tests = strawberry.get('tests', 0) + reverse.get('tests', 0)
            total_passes = strawberry.get('passes', 0) + reverse.get('passes', 0)
            overall = f"{(total_passes/total_tests*100):.0f}%" if total_tests > 0 else "N/A"
            
            model_short = model[:24]
            print(f"{model_short:<25} {strawberry_str:<12} {reverse_str:<12} {overall:<10}")
        
        conn.close()
        
        print("\n🎯 Test execution complete! Check results above.")

def main():
    """Execute comprehensive test suite"""
    
    print("🚀" + "="*50 + "🚀")
    print("   COMPREHENSIVE MODEL TESTING")
    print("🚀" + "="*50 + "🚀")
    print("Running both canonicals across ALL models! 🎯")
    print()
    
    runner = ComprehensiveTestRunner()
    
    # Setup reverse tests if needed
    reverse_count = runner.setup_reverse_gradient_tests()
    
    # Execute both test suites
    print("\n🍓 EXECUTING STRAWBERRY COUNTING TESTS...")
    strawberry_results = runner.execute_strawberry_tests()
    
    print(f"\n🔄 EXECUTING STRING REVERSE TESTS...")
    reverse_results = runner.execute_reverse_tests()
    
    # Generate comprehensive report
    runner.generate_comprehensive_report()
    
    print(f"\n✅ COMPREHENSIVE TESTING COMPLETE!")
    print(f"   🍓 Strawberry tests: {len(strawberry_results)} executed")
    print(f"   🔄 Reverse tests: {len(reverse_results)} executed") 
    print(f"   📊 Total results: {len(strawberry_results) + len(reverse_results)}")

if __name__ == "__main__":
    main()