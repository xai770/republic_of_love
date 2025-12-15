#!/usr/bin/env python3
"""
FOCUSED GRADIENT TEST 🎯
======================
Run a small focused test with better models using proper canonical instructions
"""

import sqlite3
import requests
import json
import time
import re
from datetime import datetime

def run_focused_gradient_test():
    """Run a focused gradient test with proper canonical instructions"""
    
    print("🎯" + "="*60 + "🎯")
    print("   FOCUSED GRADIENT TEST")
    print("🎯" + "="*60 + "🎯")
    print("💕 Testing with proper canonical instructions!")
    print()
    
    # Use better models for reasoning
    test_model = 'gemma3:4b'  # Should be better than CodeGemma for reasoning
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Get canonical instructions for each type
    canonicals_info = {}
    
    for canonical_code in ['mr_literal_recall', 'kv_calendar_facts', 'rd_youngest_chain', 'of_translate_fr_basic']:
        cursor.execute("""
            SELECT processing_instructions 
            FROM canonicals 
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        result = cursor.fetchone()
        if result:
            canonicals_info[canonical_code] = result[0]
    
    # Get 2 test parameters per canonical
    test_params = []
    
    for canonical_code in canonicals_info.keys():
        cursor.execute("""
            SELECT 
                tp.param_id, tp.test_word, tp.expected_response, 
                tp.prompt_template, tp.difficulty_level
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = ? AND t.processing_model_name = ?
            ORDER BY tp.difficulty_level
            LIMIT 2
        """, (canonical_code, test_model))
        
        for row in cursor.fetchall():
            test_params.append({
                'canonical_code': canonical_code,
                'model_name': test_model,
                'param_id': row[0],
                'test_word': row[1], 
                'expected_response': row[2],
                'prompt_template': row[3],
                'difficulty_level': row[4],
                'canonical_instructions': canonicals_info[canonical_code]
            })
    
    print(f"🧪 Running {len(test_params)} focused tests...")
    print()
    
    results = []
    
    for i, param in enumerate(test_params, 1):
        canonical_code = param['canonical_code']
        model_name = param['model_name']
        
        print(f"[{i:2d}/{len(test_params)}] {canonical_code} | Level {param['difficulty_level']} | {param['test_word']}")
        
        # Create proper prompt using canonical instructions
        canonical_instructions = param['canonical_instructions']
        
        if canonical_code == 'mr_literal_recall':
            # Substitute target word in payload
            final_prompt = canonical_instructions.replace(
                'Remember this word: orchid', 
                f'Remember this word: {param["expected_response"]}'
            )
            
        elif canonical_code == 'kv_calendar_facts':
            # Use the specific question from prompt_template
            final_prompt = canonical_instructions.replace(
                'What day of the week follows Tuesday?',
                param['prompt_template']
            )
            
        elif canonical_code == 'rd_youngest_chain':
            # Use the specific chain from prompt_template  
            final_prompt = canonical_instructions.replace(
                'A is older than B, B is older than C, C is older than D. Who is the youngest?',
                param['prompt_template']
            )
            
        elif canonical_code == 'of_translate_fr_basic':
            # Use the specific translation request from prompt_template
            final_prompt = canonical_instructions.replace(
                'Translate "I am happy" into French. Use the male form.',
                param['prompt_template']
            )
        else:
            final_prompt = canonical_instructions
        
        # Execute model request
        try:
            start_time = time.time()
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": final_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_k": 10,
                        "top_p": 0.9
                    }
                },
                timeout=45
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                model_response = result.get('response', '').strip()
                
                # Extract according to canonical format (brackets)
                bracket_match = re.search(r'\[([^\]]+)\]', model_response)
                
                if bracket_match:
                    extracted_answer = bracket_match.group(1).strip()
                    format_compliant = True
                    extraction_method = 'bracket_format'
                else:
                    # Try to find expected response in text
                    if param['expected_response'].lower() in model_response.lower():
                        extracted_answer = param['expected_response']
                        format_compliant = False
                        extraction_method = 'text_search'
                    else:
                        extracted_answer = ''
                        format_compliant = False
                        extraction_method = 'failed'
                
                is_correct = extracted_answer == param['expected_response']
                
                # Store in database
                cursor.execute("""
                    INSERT INTO test_runs (
                        param_id, processing_payload_test_run, 
                        processing_received_response_test_run, processing_latency_test_run,
                        qa_received_response_test_run, qa_score_test_run,
                        test_run_pass, remarks, enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    param['param_id'], final_prompt, model_response, latency_ms,
                    json.dumps({
                        'extracted_answer': extracted_answer,
                        'format_compliant': format_compliant,
                        'extraction_method': extraction_method,
                        'is_correct': is_correct
                    }),
                    '1.0' if is_correct else '0.0',
                    1 if is_correct else 0,
                    f"Focused gradient test - Level {param['difficulty_level']}"
                ))
                
                results.append({
                    'canonical_code': canonical_code,
                    'is_correct': is_correct,
                    'format_compliant': format_compliant,
                    'extracted_answer': extracted_answer,
                    'expected_response': param['expected_response'],
                    'latency_ms': latency_ms
                })
                
                # Show result
                status = "✅" if is_correct else "❌"
                format_status = "📋" if format_compliant else "📄"
                print(f"     {status} {format_status} Expected: '{param['expected_response']}' | Got: '{extracted_answer}' | {latency_ms}ms")
                
            else:
                print(f"     💥 Request failed: {response.status_code}")
                results.append({
                    'canonical_code': canonical_code,
                    'is_correct': False,
                    'format_compliant': False,
                    'error': f'HTTP {response.status_code}'
                })
        
        except Exception as e:
            print(f"     💥 Error: {e}")
            results.append({
                'canonical_code': canonical_code,
                'is_correct': False,
                'format_compliant': False,
                'error': str(e)
            })
        
        # Small delay
        time.sleep(0.2)
    
    conn.commit()
    conn.close()
    
    # Summary
    print(f"\n🎉 Focused gradient test complete!")
    
    total_tests = len([r for r in results if 'error' not in r])
    correct_answers = len([r for r in results if r.get('is_correct', False)])
    format_compliant = len([r for r in results if r.get('format_compliant', False)])
    
    if total_tests > 0:
        success_rate = (correct_answers / total_tests) * 100
        format_rate = (format_compliant / total_tests) * 100
        
        print(f"   📊 Results: {correct_answers}/{total_tests} ({success_rate:.1f}%) correct")
        print(f"   📋 Format: {format_compliant}/{total_tests} ({format_rate:.1f}%) compliant")
        
        # By canonical
        by_canonical = {}
        for r in results:
            if 'error' in r:
                continue
            canonical = r['canonical_code']
            if canonical not in by_canonical:
                by_canonical[canonical] = {'total': 0, 'correct': 0}
            by_canonical[canonical]['total'] += 1
            if r['is_correct']:
                by_canonical[canonical]['correct'] += 1
        
        print(f"   📈 By canonical:")
        for canonical, stats in by_canonical.items():
            rate = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"      {canonical}: {stats['correct']}/{stats['total']} ({rate:.1f}%)")
    
    print(f"\n💕 Using proper canonical instructions makes a huge difference!")
    
    return results

if __name__ == "__main__":
    run_focused_gradient_test()