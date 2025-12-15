#!/usr/bin/env python3
"""
QUICK CANONICAL TEST - DEBUG VERSION
===================================
Test a few gradient parameters using proper canonical instructions
"""

import sqlite3
import requests
import json

def test_canonical_gradient():
    """Test a few gradient parameters with proper canonical instructions"""
    
    print("🔍 Testing canonical instruction substitution...")
    
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    # Get one parameter from each canonical type
    test_cases = [
        ('mr_literal_recall', 'gemma3:4b'),
        ('kv_calendar_facts', 'gemma3:4b'), 
        ('rd_youngest_chain', 'gemma3:4b'),
        ('of_translate_fr_basic', 'gemma3:4b')
    ]
    
    for canonical_code, model_name in test_cases:
        print(f"\n🧪 Testing {canonical_code} with {model_name}")
        
        # Get canonical instructions
        cursor.execute("""
            SELECT processing_instructions FROM canonicals 
            WHERE canonical_code = ?
        """, (canonical_code,))
        
        canonical_instructions = cursor.fetchone()[0]
        
        # Get a test parameter
        cursor.execute("""
            SELECT tp.test_word, tp.expected_response, tp.prompt_template, tp.difficulty_level
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            WHERE t.canonical_code = ? AND t.processing_model_name = ?
            LIMIT 1
        """, (canonical_code, model_name))
        
        param = cursor.fetchone()
        if not param:
            print(f"   ❌ No parameters found for {canonical_code}")
            continue
            
        test_word, expected_response, prompt_template, difficulty_level = param
        
        print(f"   📝 Test: {test_word} → {expected_response} (Level {difficulty_level})")
        
        # Create the proper prompt
        if canonical_code == 'mr_literal_recall':
            # Substitute target word in canonical payload
            final_prompt = canonical_instructions.replace(
                'Remember this word: orchid', 
                f'Remember this word: {expected_response}'
            )
        elif canonical_code == 'kv_calendar_facts':
            # Use the prompt_template which contains the specific question
            final_prompt = canonical_instructions.replace(
                'What day of the week follows Tuesday?',
                prompt_template
            )
        elif canonical_code == 'rd_youngest_chain':
            # Use the prompt_template which contains the specific chain
            final_prompt = canonical_instructions.replace(
                'A is older than B, B is older than C, C is older than D. Who is the youngest?',
                prompt_template  
            )
        elif canonical_code == 'of_translate_fr_basic':
            # Use the prompt_template which contains the specific translation request
            final_prompt = canonical_instructions.replace(
                'Translate "I am happy" into French. Use the male form.',
                prompt_template
            )
        else:
            final_prompt = canonical_instructions
        
        print(f"   🎯 Final prompt:")
        print(f"      {final_prompt[:200]}...")
        
        # Execute the test (optional - comment out if models are slow)
        # try:
        #     response = requests.post(
        #         "http://localhost:11434/api/generate",
        #         json={
        #             "model": model_name,
        #             "prompt": final_prompt,
        #             "stream": False,
        #             "options": {"temperature": 0.1}
        #         },
        #         timeout=30
        #     )
        #     
        #     if response.status_code == 200:
        #         result = response.json()
        #         model_response = result.get('response', '').strip()
        #         print(f"   🤖 Model response: {model_response}")
        #         
        #         # Check for bracket format
        #         import re
        #         bracket_match = re.search(r'\[([^\]]+)\]', model_response)
        #         if bracket_match:
        #             extracted = bracket_match.group(1)
        #             correct = extracted == expected_response
        #             print(f"   ✅ Extracted: '{extracted}' | Expected: '{expected_response}' | Correct: {correct}")
        #         else:
        #             print(f"   ❌ No bracket format found in response")
        #     else:
        #         print(f"   💥 Request failed: {response.status_code}")
        # 
        # except Exception as e:
        #     print(f"   💥 Error: {e}")
    
    conn.close()
    print(f"\n💕 Canonical instruction test complete!")

if __name__ == "__main__":
    test_canonical_gradient()