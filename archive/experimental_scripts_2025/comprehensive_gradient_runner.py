#!/usr/bin/env python3
"""
COMPREHENSIVE GRADIENT TEST RUNNER 🌈
====================================
Execute systematic capability gradient tests across all models
Using proper canonical instructions with full parameter sets!
"""

import sqlite3
import json
import requests
import time
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class GradientTestRunner:
    """Execute gradient tests using canonical processing instructions"""
    
    def __init__(self, db_path: str = 'data/llmcore.db', ollama_url: str = 'http://localhost:11434'):
        self.db_path = db_path
        self.ollama_url = ollama_url
        
    def get_canonical_instructions(self, canonical_code: str) -> Optional[str]:
        """Get canonical processing instructions - NEVER simplify these!"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT processing_instructions 
            FROM canonicals 
            WHERE canonical_code = ? AND enabled = 1
        """, (canonical_code,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def substitute_canonical_parameters(self, canonical_instructions: str, 
                                     canonical_code: str, test_word: str, 
                                     expected_response: str) -> str:
        """Substitute test parameters into canonical instructions while preserving structure"""
        
        formatted_prompt = canonical_instructions
        
        # Handle different canonical substitution patterns
        if canonical_code == 'mr_literal_recall':
            # Memory recall: substitute the target word in the payload
            target_word = expected_response  # The word we expect back
            formatted_prompt = canonical_instructions.replace(
                'Remember this word: orchid', 
                f'Remember this word: {target_word}'
            )
            
        elif canonical_code == 'ce_char_extract':
            # Character extraction: substitute both the word and character
            formatted_prompt = canonical_instructions.replace(
                '"strawberry"', 
                f'"{expected_response}"'
            ).replace(
                '"r"',
                f'"{test_word}"'
            )
            
        elif canonical_code == 'ff_reverse_gradient':
            # String reversal: substitute the word to reverse
            formatted_prompt = canonical_instructions.replace(
                '"strawberry"', 
                f'"{expected_response}"'
            )
        
        # For other canonicals (kv_calendar_facts, rd_youngest_chain, of_translate_fr_basic)
        # we'll use the prompt_template directly since they have specific question formats
        
        return formatted_prompt
    
    def execute_model_request(self, model_name: str, prompt: str) -> Dict:
        """Execute request to Ollama API"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistency
                        "top_k": 10,
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'response': result.get('response', '').strip(),
                'total_duration': result.get('total_duration', 0),
                'load_duration': result.get('load_duration', 0),
                'prompt_eval_count': result.get('prompt_eval_count', 0),
                'eval_count': result.get('eval_count', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': '',
                'total_duration': 0
            }
    
    def extract_canonical_result(self, response: str, canonical_code: str, 
                               expected_response: str) -> Dict:
        """Extract result according to canonical format specifications"""
        
        if canonical_code in ['ce_char_extract', 'mr_literal_recall']:
            # Look for [NUMBER] or [string] format
            bracket_match = re.search(r'\[([^\]]+)\]', response)
            if bracket_match:
                extracted = bracket_match.group(1).strip()
                return {
                    'extracted_answer': extracted,
                    'format_compliant': True,
                    'is_correct': extracted == expected_response,
                    'extraction_method': 'bracket_format'
                }
            else:
                # Try to find the expected response in the text
                if expected_response.lower() in response.lower():
                    return {
                        'extracted_answer': expected_response,
                        'format_compliant': False,
                        'is_correct': True,
                        'extraction_method': 'text_search'
                    }
                else:
                    return {
                        'extracted_answer': '',
                        'format_compliant': False,
                        'is_correct': False,
                        'extraction_method': 'failed'
                    }
        
        elif canonical_code == 'ff_reverse_gradient':
            # Look for [string] format
            bracket_match = re.search(r'\[([^\]]+)\]', response)
            if bracket_match:
                extracted = bracket_match.group(1).strip()
                return {
                    'extracted_answer': extracted,
                    'format_compliant': True,
                    'is_correct': extracted == expected_response,
                    'extraction_method': 'bracket_format'
                }
            else:
                return {
                    'extracted_answer': '',
                    'format_compliant': False,
                    'is_correct': False,
                    'extraction_method': 'failed'
                }
        
        else:
            # Generic extraction for other canonicals
            response_lower = response.lower().strip()
            expected_lower = expected_response.lower().strip()
            
            return {
                'extracted_answer': response.strip(),
                'format_compliant': True,  # Assume compliant for non-bracket formats
                'is_correct': response_lower == expected_lower,
                'extraction_method': 'direct_comparison'
            }
    
    def get_gradient_test_parameters(self, canonical_codes: List[str] = None) -> List[Dict]:
        """Get all gradient test parameters ready for execution"""
        
        if canonical_codes is None:
            canonical_codes = ['mr_literal_recall', 'kv_calendar_facts', 
                             'rd_youngest_chain', 'of_translate_fr_basic']
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all test parameters for gradient canonicals
        placeholders = ','.join(['?' for _ in canonical_codes])
        
        cursor.execute(f"""
            SELECT 
                tp.param_id,
                tp.test_id,
                t.canonical_code,
                t.processing_model_name,
                tp.test_word,
                tp.difficulty_level,
                tp.expected_response,
                tp.prompt_template,
                tp.response_format,
                tp.complexity_score,
                c.processing_instructions
            FROM test_parameters tp
            JOIN tests t ON tp.test_id = t.test_id
            JOIN canonicals c ON t.canonical_code = c.canonical_code
            WHERE t.canonical_code IN ({placeholders})
              AND tp.enabled = 1
              AND c.enabled = 1
            ORDER BY t.canonical_code, t.processing_model_name, tp.difficulty_level, tp.param_id
        """, canonical_codes)
        
        parameters = []
        for row in cursor.fetchall():
            parameters.append({
                'param_id': row[0],
                'test_id': row[1],
                'canonical_code': row[2],
                'model_name': row[3],
                'test_word': row[4],
                'difficulty_level': row[5],
                'expected_response': row[6],
                'prompt_template': row[7],
                'response_format': row[8],
                'complexity_score': row[9],
                'canonical_instructions': row[10]
            })
        
        conn.close()
        return parameters
    
    def store_test_result(self, param_id: int, processing_payload: str, 
                         response_data: Dict, extraction_result: Dict,
                         latency_ms: int):
        """Store test result in test_runs table"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate pass/fail
        test_pass = 1 if extraction_result['is_correct'] else 0
        
        # Create QA analysis
        qa_analysis = {
            'format_compliant': extraction_result['format_compliant'],
            'extraction_method': extraction_result['extraction_method'],
            'extracted_answer': extraction_result['extracted_answer'],
            'is_correct': extraction_result['is_correct']
        }
        
        cursor.execute("""
            INSERT INTO test_runs (
                param_id,
                processing_payload_test_run,
                processing_received_response_test_run,
                processing_latency_test_run,
                qa_received_response_test_run,
                qa_score_test_run,
                test_run_pass,
                remarks,
                enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            param_id,
            processing_payload,
            response_data['response'],
            latency_ms,
            json.dumps(qa_analysis),
            '1.0' if extraction_result['is_correct'] else '0.0',
            test_pass,
            f"Gradient test - Difficulty {extraction_result.get('difficulty_level', 'N/A')}"
        ))
        
        conn.commit()
        conn.close()
    
    def run_gradient_tests(self, canonical_codes: List[str] = None, 
                          max_params_per_canonical: int = None) -> Dict:
        """Execute comprehensive gradient testing"""
        
        print("🌈" + "="*70 + "🌈")
        print("   COMPREHENSIVE GRADIENT TEST EXECUTION")
        print("🌈" + "="*70 + "🌈")
        print("💕 Running systematic capability gradient tests!")
        print()
        
        # Get all test parameters
        parameters = self.get_gradient_test_parameters(canonical_codes)
        
        if max_params_per_canonical:
            # Limit parameters for testing
            limited_params = []
            canonical_counts = {}
            
            for param in parameters:
                canonical = param['canonical_code']
                count = canonical_counts.get(canonical, 0)
                
                if count < max_params_per_canonical:
                    limited_params.append(param)
                    canonical_counts[canonical] = count + 1
            
            parameters = limited_params
        
        print(f"📊 Total parameters to test: {len(parameters)}")
        
        # Group by canonical for progress tracking
        by_canonical = {}
        for param in parameters:
            canonical = param['canonical_code']
            if canonical not in by_canonical:
                by_canonical[canonical] = []
            by_canonical[canonical].append(param)
        
        for canonical, count in [(k, len(v)) for k, v in by_canonical.items()]:
            print(f"   {canonical}: {count} parameters")
        
        print()
        
        # Execute tests - 5 iterations per parameter for statistical reliability
        total_executions = len(parameters) * 5  # 5 runs per parameter
        results = {
            'total_tests': total_executions,
            'successful_executions': 0,
            'failed_executions': 0,
            'correct_answers': 0,
            'format_compliant': 0,
            'by_canonical': {},
            'by_model': {},
            'execution_times': []
        }
        
        execution_count = 0
        for param_idx, param in enumerate(parameters, 1):
            for run_number in range(1, 6):  # 5 iterations per parameter
                execution_count += 1
                canonical_code = param['canonical_code']
                model_name = param['model_name']
                
                print(f"🔧 [{execution_count:4d}/{total_executions}] {canonical_code} | {model_name} | Level {param['difficulty_level']} | {param['test_word']} | Run {run_number}/5")
            
                # Get proper prompt using canonical instructions
                if param['prompt_template']:
                    # Use the specific prompt template if available
                    processing_payload = param['prompt_template']
                else:
                    # Substitute into canonical instructions
                    processing_payload = self.substitute_canonical_parameters(
                        param['canonical_instructions'],
                        canonical_code,
                        param['test_word'], 
                        param['expected_response']
                    )
                
                # Execute model request
                start_time = time.time()
                response_data = self.execute_model_request(model_name, processing_payload)
                end_time = time.time()
                
                latency_ms = int((end_time - start_time) * 1000)
                results['execution_times'].append(latency_ms)
            
                if response_data['success']:
                    results['successful_executions'] += 1
                    
                    # Extract result according to canonical format
                    extraction_result = self.extract_canonical_result(
                        response_data['response'],
                        canonical_code,
                        param['expected_response']
                    )
                    
                    extraction_result['difficulty_level'] = param['difficulty_level']
                    
                    # Update statistics
                    if extraction_result['is_correct']:
                        results['correct_answers'] += 1
                        
                    if extraction_result['format_compliant']:
                        results['format_compliant'] += 1
                    
                    # Store result
                    self.store_test_result(
                        param['param_id'],
                        processing_payload,
                        response_data,
                        extraction_result,
                        latency_ms
                    )
                
                    # Track by canonical
                    if canonical_code not in results['by_canonical']:
                        results['by_canonical'][canonical_code] = {
                            'total': 0, 'correct': 0, 'compliant': 0
                        }
                    results['by_canonical'][canonical_code]['total'] += 1
                    if extraction_result['is_correct']:
                        results['by_canonical'][canonical_code]['correct'] += 1
                    if extraction_result['format_compliant']:
                        results['by_canonical'][canonical_code]['compliant'] += 1
                    
                    # Track by model
                    if model_name not in results['by_model']:
                        results['by_model'][model_name] = {
                            'total': 0, 'correct': 0, 'compliant': 0
                        }
                    results['by_model'][model_name]['total'] += 1
                    if extraction_result['is_correct']:
                        results['by_model'][model_name]['correct'] += 1
                    if extraction_result['format_compliant']:
                        results['by_model'][model_name]['compliant'] += 1
                    
                    # Show result
                    status = "✅" if extraction_result['is_correct'] else "❌"
                    format_status = "📋" if extraction_result['format_compliant'] else "📄"
                    print(f"     {status} {format_status} Expected: '{param['expected_response']}' | Got: '{extraction_result['extracted_answer']}' | {latency_ms}ms")
                    
                else:
                    results['failed_executions'] += 1
                    print(f"     💥 FAILED: {response_data.get('error', 'Unknown error')}")
                
                # Small delay to be nice to the API
                time.sleep(0.1)
        
        # Generate summary report
        print("\n" + "🎉" + "="*70 + "🎉")
        print("   GRADIENT TEST EXECUTION COMPLETE!")
        print("🎉" + "="*70 + "🎉")
        
        success_rate = (results['correct_answers'] / results['total_tests']) * 100
        format_rate = (results['format_compliant'] / results['total_tests']) * 100
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {results['total_tests']}")
        print(f"   Successful Executions: {results['successful_executions']}")
        print(f"   Correct Answers: {results['correct_answers']} ({success_rate:.1f}%)")
        print(f"   Format Compliant: {results['format_compliant']} ({format_rate:.1f}%)")
        print(f"   Average Latency: {sum(results['execution_times']) / len(results['execution_times']):.0f}ms")
        
        print(f"\n📋 By Canonical:")
        for canonical, stats in results['by_canonical'].items():
            canonical_success = (stats['correct'] / stats['total']) * 100
            canonical_format = (stats['compliant'] / stats['total']) * 100
            print(f"   {canonical}: {stats['correct']}/{stats['total']} ({canonical_success:.1f}%) correct, {canonical_format:.1f}% compliant")
        
        print(f"\n🤖 By Model:")
        for model, stats in results['by_model'].items():
            model_success = (stats['correct'] / stats['total']) * 100
            model_format = (stats['compliant'] / stats['total']) * 100
            print(f"   {model}: {stats['correct']}/{stats['total']} ({model_success:.1f}%) correct, {model_format:.1f}% compliant")
        
        print(f"\n💕 Gradient capability mapping complete!")
        
        return results

def main():
    """Run comprehensive gradient tests"""
    
    runner = GradientTestRunner()
    
    # Start with a smaller test run to verify everything works
    print("🚀 Starting gradient test execution...")
    print("   (Running limited test set first)")
    
    results = runner.run_gradient_tests(
        canonical_codes=['mr_literal_recall', 'kv_calendar_facts', 'rd_youngest_chain', 'of_translate_fr_basic'],
        max_params_per_canonical=20  # 20 params per canonical for initial test
    )
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"gradient_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Results saved to: {results_file}")
    print("💕 Ready for full gradient analysis!")

if __name__ == "__main__":
    main()