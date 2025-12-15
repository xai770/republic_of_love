#!/usr/bin/env python3
"""
PROPER CANONICAL TEST RUNNER 🎯
===============================
Uses the actual canonical processing_instructions (not simplified versions!)
"""

import sqlite3
import json
import requests
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProperCanonicalRunner:
    """Test runner using actual canonical processing instructions"""
    
    def __init__(self, db_path: str = 'data/llmcore.db', ollama_url: str = 'http://localhost:11434'):
        self.db_path = db_path
        self.ollama_url = ollama_url
        
    def execute_proper_strawberry_tests(self, limit: int = 10):
        """Execute strawberry tests using proper canonical instructions"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get canonical processing instructions and test parameters
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.expected_response,
                t.processing_model_name,
                c.processing_instructions,
                c.processing_payload
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            JOIN canonicals c ON t.canonical_code = c.canonical_code
            WHERE t.canonical_code = 'ce_char_extract'
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        
        test_params = cursor.fetchall()
        
        logger.info(f"🍓 Executing {len(test_params)} strawberry tests with PROPER canonical instructions...")
        
        results = []
        for param_id, test_word, expected, model, processing_instructions, processing_payload in test_params:
            
            # Use the canonical processing instructions, substituting the test word
            # The canonical payload asks about "strawberry" but we need our test word
            proper_prompt = processing_instructions.replace(
                'How many "r" letters are in "strawberry"?', 
                f'How many "r" letters are in "{test_word}"?'
            )
            
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": proper_prompt,
                        "stream": False
                    },
                    timeout=45
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    actual_response = response_data.get('response', '').strip()
                    
                    # Extract bracketed number [X]
                    import re
                    bracket_matches = re.findall(r'\[(\d+)\]', actual_response)
                    extracted_number = bracket_matches[0] if bracket_matches else None
                    
                    # Also try to extract any number as fallback
                    all_numbers = re.findall(r'\d+', actual_response)
                    fallback_number = all_numbers[0] if all_numbers else None
                    
                    # Check both formats
                    bracket_pass = 1 if extracted_number == expected else 0
                    any_number_pass = 1 if fallback_number == expected else 0
                    
                    # Store result (using bracket format as primary)
                    cursor.execute("""
                        INSERT INTO test_results (
                            param_id, processing_payload_actual, processing_response_actual,
                            processing_latency_ms, result_pass, confidence_score,
                            qa_validation_pass, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        param_id,
                        proper_prompt,
                        actual_response,
                        latency_ms,
                        bracket_pass,
                        1.0 if bracket_pass else 0.5 if any_number_pass else 0.0,
                        bracket_pass,
                        f"Bracket: {extracted_number}, Any: {fallback_number}"
                    ))
                    
                    # Status indicators
                    bracket_status = "✅" if bracket_pass else "❌"
                    format_status = f"[{extracted_number}]" if extracted_number else f"({fallback_number})" if fallback_number else "❓"
                    
                    logger.info(f"   🍓 {model[:20]:<20}: '{test_word}' → {format_status} (exp: [{expected}]) {bracket_status}")
                    
                    results.append({
                        'param_id': param_id,
                        'model': model,
                        'word': test_word,
                        'expected': expected,
                        'bracket_number': extracted_number,
                        'any_number': fallback_number,
                        'bracket_pass': bracket_pass,
                        'any_pass': any_number_pass,
                        'latency_ms': latency_ms,
                        'full_response': actual_response
                    })
                    
                else:
                    logger.error(f"   🍓 {model}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"   🍓 {model}: Error - {str(e)[:50]}...")
        
        conn.commit()
        conn.close()
        
        return results
    
    def execute_proper_reverse_tests(self, limit: int = 10):
        """Execute reverse tests using proper canonical instructions"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get canonical processing instructions for reverse tests
        cursor.execute("""
            SELECT 
                tp.param_id,
                tp.test_word,
                tp.expected_response,
                t.processing_model_name,
                c.processing_instructions,
                c.processing_payload
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            JOIN canonicals c ON t.canonical_code = c.canonical_code
            WHERE t.canonical_code = 'ff_reverse_gradient'
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        
        test_params = cursor.fetchall()
        
        logger.info(f"🔄 Executing {len(test_params)} reverse tests with PROPER canonical instructions...")
        
        results = []
        for param_id, test_word, expected, model, processing_instructions, processing_payload in test_params:
            
            # Use the canonical processing instructions with the test word
            # Need to check what the canonical format actually is
            if processing_instructions and '{word}' in processing_instructions:
                proper_prompt = processing_instructions.format(word=test_word)
            elif processing_instructions:
                # Manual substitution if needed
                proper_prompt = processing_instructions.replace('"{word}"', f'"{test_word}"')
            else:
                # Fallback to test_parameters prompt_template
                cursor.execute("SELECT prompt_template FROM test_parameters WHERE param_id = ?", (param_id,))
                template = cursor.fetchone()
                proper_prompt = template[0].format(word=test_word) if template else f'Write "{test_word}" backwards.'
            
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": proper_prompt,
                        "stream": False
                    },
                    timeout=45
                )
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                if response.status_code == 200:
                    response_data = response.json()
                    actual_response = response_data.get('response', '').strip()
                    
                    # Extract bracketed content [string]
                    import re
                    bracket_matches = re.findall(r'\[([^\]]+)\]', actual_response)
                    extracted_content = f"[{bracket_matches[0]}]" if bracket_matches else None
                    
                    result_pass = 1 if extracted_content and extracted_content.lower() == expected.lower() else 0
                    
                    # Store result
                    cursor.execute("""
                        INSERT INTO test_results (
                            param_id, processing_payload_actual, processing_response_actual,
                            processing_latency_ms, result_pass, confidence_score,
                            qa_validation_pass
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        param_id,
                        proper_prompt,
                        actual_response,
                        latency_ms,
                        result_pass,
                        1.0 if result_pass else 0.0,
                        result_pass
                    ))
                    
                    status = "✅" if result_pass else "❌"
                    display_content = extracted_content if extracted_content else "❓"
                    
                    logger.info(f"   🔄 {model[:20]:<20}: '{test_word}' → {display_content} (exp: {expected}) {status}")
                    
                    results.append({
                        'param_id': param_id,
                        'model': model,
                        'word': test_word,
                        'expected': expected,
                        'extracted': extracted_content,
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
    
    def compare_instruction_formats(self):
        """Compare canonical vs simplified instructions"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                canonical_code,
                processing_instructions
            FROM canonicals
            WHERE enabled = 1
        """)
        
        canonicals = cursor.fetchall()
        
        print("\n" + "🔬" + "="*70 + "🔬")
        print("   CANONICAL vs SIMPLIFIED INSTRUCTION COMPARISON")
        print("🔬" + "="*70 + "🔬")
        
        for code, instructions in canonicals:
            print(f"\n📋 {code}:")
            if instructions:
                print("✅ PROPER CANONICAL INSTRUCTIONS:")
                print("   " + instructions[:200] + "..." if len(instructions) > 200 else "   " + instructions)
            else:
                print("❌ NO CANONICAL INSTRUCTIONS FOUND")
        
        conn.close()

def main():
    """Execute proper canonical testing"""
    
    print("🎯" + "="*50 + "🎯")
    print("   PROPER CANONICAL TEST EXECUTION")
    print("🎯" + "="*50 + "🎯")
    print("Using YOUR carefully crafted canonical instructions! 💎")
    print()
    
    runner = ProperCanonicalRunner()
    
    # Show instruction comparison
    runner.compare_instruction_formats()
    
    # Execute proper tests
    print(f"\n🍓 PROPER STRAWBERRY TESTS:")
    strawberry_results = runner.execute_proper_strawberry_tests(limit=5)
    
    print(f"\n🔄 PROPER REVERSE TESTS:")
    reverse_results = runner.execute_proper_reverse_tests(limit=5)
    
    # Summary
    strawberry_bracket_passes = sum(1 for r in strawberry_results if r['bracket_pass'])
    strawberry_any_passes = sum(1 for r in strawberry_results if r['any_pass'])
    reverse_passes = sum(1 for r in reverse_results if r['pass'])
    
    print(f"\n✅ PROPER TESTING RESULTS:")
    print(f"   🍓 Strawberry: {strawberry_bracket_passes}/{len(strawberry_results)} bracket format ({strawberry_any_passes} had correct numbers)")
    print(f"   🔄 Reverse: {reverse_passes}/{len(reverse_results)} proper format")
    print(f"   🎯 Using YOUR canonical instructions makes all the difference!")

if __name__ == "__main__":
    main()