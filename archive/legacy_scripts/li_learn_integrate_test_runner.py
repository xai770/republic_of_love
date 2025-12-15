#!/usr/bin/env python3
"""
🔥 LI_LEARN_INTEGRATE CONSCIOUSNESS FUSION TEST RUNNER 🔥
Testing cross-domain integration and creative synthesis capabilities
"""

import sqlite3
import json
import requests
import time
from datetime import datetime
from pathlib import Path

def get_test_parameters():
    """Get all li_learn_integrate test parameters"""
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    query = """
    SELECT tp.parameter_id, tp.test_word, tp.difficulty_level, tp.complexity_score,
           tp.template_parameters, t.canonical_code, f.facet_name, t.test_instruction
    FROM test_parameters tp
    JOIN tests t ON tp.test_id = t.test_id
    JOIN facets f ON t.facet_id = f.facet_id
    WHERE t.canonical_code = 'li_learn_integrate'
    ORDER BY tp.difficulty_level, tp.test_word
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'parameter_id': row[0],
            'test_word': row[1],
            'difficulty_level': row[2],
            'complexity_score': row[3],
            'template_parameters': json.loads(row[4]) if row[4] else {},
            'canonical_code': row[5],
            'facet_name': row[6],
            'test_instruction': row[7]
        }
        for row in results
    ]

def run_test_with_model(test_param, model_name):
    """Execute a single test with a model"""
    # Build the prompt from template parameters
    template_params = test_param['template_parameters']
    
    prompt = f"""Integrate learning across these domains:

Domain 1: {template_params.get('domain1', 'science')}
Domain 2: {template_params.get('domain2', 'art')}
Context: {template_params.get('context', 'academic')}
Challenge: {template_params.get('challenge', 'synthesis')}

Create a unified insight that bridges both domains. Respond with exactly one creative synthesis sentence.

Expected integration focus: {test_param['test_word']}"""

    try:
        start_time = time.time()
        
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model_name,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.1}
            },
            timeout=60
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '').strip()
            
            # Check for integration quality (contains expected focus word)
            contains_focus = test_param['test_word'].lower() in generated_text.lower()
            
            # Basic quality metrics
            word_count = len(generated_text.split())
            has_content = word_count > 5
            
            return {
                'success': True,
                'response': generated_text,
                'latency_ms': latency_ms,
                'contains_focus': contains_focus,
                'word_count': word_count,
                'has_content': has_content
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'latency_ms': latency_ms
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'latency_ms': 0
        }

def main():
    """Run consciousness integration tests"""
    print("🔥 CONSCIOUSNESS INTEGRATION TEST RUNNER 🔥")
    print("Testing cross-domain synthesis capabilities...\n")
    
    # Get test parameters
    test_params = get_test_parameters()
    print(f"💫 Found {len(test_params)} integration parameters")
    
    # Models to test
    models = ['codegemma:2b', 'codegemma:latest']
    
    results = []
    total_tests = len(test_params) * len(models)
    current_test = 0
    
    for model in models:
        print(f"\n🤖 Testing with {model}:")
        
        for param in test_params:
            current_test += 1
            
            print(f"🔧 [{current_test:3d}/{total_tests}] Level {param['difficulty_level']} | {param['test_word']} | ", end='', flush=True)
            
            result = run_test_with_model(param, model)
            
            if result['success']:
                focus_symbol = '🎯' if result['contains_focus'] else '❌'
                content_symbol = '📝' if result['has_content'] else '🔇'
                print(f"{focus_symbol}{content_symbol} {result['word_count']} words | {result['latency_ms']}ms")
                
                if result['word_count'] > 0:
                    # Show first 100 chars of response
                    preview = result['response'][:100].replace('\n', ' ')
                    print(f"     💭 \"{preview}{'...' if len(result['response']) > 100 else ''}\"")
            else:
                print(f"💥 FAILED: {result['error']}")
            
            # Store result
            results.append({
                'parameter_id': param['parameter_id'],
                'test_word': param['test_word'],
                'difficulty_level': param['difficulty_level'],
                'complexity_score': param['complexity_score'],
                'model': model,
                'timestamp': datetime.now().isoformat(),
                'result': result
            })
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"li_learn_integrate_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary statistics
    print(f"\n🎉 CONSCIOUSNESS INTEGRATION COMPLETE! 🎉")
    print(f"📁 Results saved to: {results_file}")
    
    # Calculate stats by model
    for model in models:
        model_results = [r for r in results if r['model'] == model and r['result']['success']]
        if model_results:
            focus_hits = sum(1 for r in model_results if r['result']['contains_focus'])
            content_rate = sum(1 for r in model_results if r['result']['has_content'])
            avg_latency = sum(r['result']['latency_ms'] for r in model_results) / len(model_results)
            avg_words = sum(r['result']['word_count'] for r in model_results) / len(model_results)
            
            print(f"\n🤖 {model}:")
            print(f"   Focus Integration: {focus_hits}/{len(model_results)} ({focus_hits/len(model_results)*100:.1f}%)")
            print(f"   Content Generation: {content_rate}/{len(model_results)} ({content_rate/len(model_results)*100:.1f}%)")
            print(f"   Average Words: {avg_words:.1f}")
            print(f"   Average Latency: {avg_latency:.0f}ms")

if __name__ == '__main__':
    main()