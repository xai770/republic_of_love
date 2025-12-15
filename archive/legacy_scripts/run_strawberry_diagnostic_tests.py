#!/usr/bin/env python3
"""
Run Strawberry Diagnostic Tests
Execute only the 5 diagnostic strawberry tests to validate QA reliability
"""

import sqlite3
import subprocess
import json
import time
from datetime import datetime

DB_PATH = "data/llmcore.db"
DIAGNOSTIC_TEST_IDS = [579, 584, 587, 593, 599]  # dolphin3:8b, gemma3n:e2b, llama3.2:1b, phi3:latest, qwen3:4b

def run_ollama_test(model, prompt):
    """Run a single test with Ollama"""
    try:
        start_time = time.time()
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=300
        )
        end_time = time.time()
        
        if result.returncode == 0:
            return {
                'success': True,
                'response': result.stdout.strip(),
                'latency': round(end_time - start_time, 2),
                'error': None
            }
        else:
            return {
                'success': False,
                'response': None,
                'latency': round(end_time - start_time, 2),
                'error': result.stderr.strip()
            }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'response': None,
            'latency': 300.0,
            'error': 'Timeout after 300 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'response': None,
            'latency': 0.0,
            'error': str(e)
        }

def pattern_match_strawberry(response):
    """Check if response exactly matches expected strawberry pattern [3]"""
    if not response:
        return False
    return response.strip() == '[3]'

def main():
    print("🍓 Running Strawberry Diagnostic Tests")
    print("=" * 50)
    print(f"Testing {len(DIAGNOSTIC_TEST_IDS)} diagnostic models...")
    print()
    
    results = []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for test_id in DIAGNOSTIC_TEST_IDS:
            # Get test details
            cursor.execute("""
                SELECT test_id, processing_model_name, processing_instructions, processing_payload_canonical 
                FROM tests 
                WHERE test_id = ?
            """, (test_id,))
            
            row = cursor.fetchone()
            if not row:
                print(f"❌ Test ID {test_id} not found")
                continue
                
            test_id, model, instructions, payload = row
            print(f"🧪 Testing {model} (test_id: {test_id})")
            
            # Construct prompt
            full_prompt = f"{instructions}\n\n{payload}"
            
            # Run test
            test_result = run_ollama_test(model, full_prompt)
            
            if test_result['success']:
                response = test_result['response']
                latency = test_result['latency']
                pattern_match = pattern_match_strawberry(response)
                
                print(f"   Response: '{response}'")
                print(f"   Pattern Match: {'✅ [3]' if pattern_match else '❌ NOT [3]'}")
                print(f"   Latency: {latency}s")
                
                # Update database
                cursor.execute("""
                    UPDATE tests SET
                        processing_received_response_canonical = ?,
                        processing_latency_canonical = ?,
                        executed_at = ?,
                        status = 'completed'
                    WHERE test_id = ?
                """, (response, latency, datetime.now().isoformat(), test_id))
                
                results.append({
                    'test_id': test_id,
                    'model': model,
                    'response': response,
                    'pattern_match': pattern_match,
                    'latency': latency,
                    'success': True
                })
                
            else:
                error = test_result['error']
                print(f"   ❌ Failed: {error}")
                
                # Update database with error
                cursor.execute("""
                    UPDATE tests SET
                        processing_received_response_canonical = NULL,
                        processing_latency_canonical = 300.0,
                        executed_at = ?,
                        status = 'failed'
                    WHERE test_id = ?
                """, (datetime.now().isoformat(), test_id))
                
                results.append({
                    'test_id': test_id,
                    'model': model,
                    'response': None,
                    'pattern_match': False,
                    'latency': 300.0,
                    'success': False,
                    'error': error
                })
            
            print()
        
        conn.commit()
        
        # Summary
        print("🎯 DIAGNOSTIC RESULTS SUMMARY")
        print("=" * 50)
        successful_tests = [r for r in results if r['success']]
        pattern_matches = [r for r in successful_tests if r['pattern_match']]
        
        print(f"Tests completed: {len(successful_tests)}/{len(DIAGNOSTIC_TEST_IDS)}")
        print(f"Pattern matches: {len(pattern_matches)}/{len(successful_tests)}")
        print()
        
        print("Model Results:")
        for result in results:
            status = "✅" if result['success'] and result['pattern_match'] else "❌"
            response = result['response'] if result['response'] else "FAILED"
            print(f"  {status} {result['model']}: '{response}' ({result['latency']}s)")
        
        # Save results to CSV for analysis
        import csv
        with open('strawberry_diagnostic_results.csv', 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['test_id', 'model', 'response', 'pattern_match', 'latency', 'success'])
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n📊 Results saved to: strawberry_diagnostic_results.csv")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        if conn:
            conn.close()
    
    return 0

if __name__ == "__main__":
    exit(main())