#!/usr/bin/env python3
"""
LLMCore Exhaustive Test Runner
==============================
Tests every variation × instruction × model × batch combination.
No adaptive logic - just systematic exhaustive testing.
"""

import sqlite3
import subprocess
import time
from datetime import datetime
from typing import Optional, Dict, Any

class ExhaustiveTestRunner:
    def __init__(self, db_path: str = "/home/xai/Documents/ty_learn/data/llmcore.db"):
        self.db_path = db_path
        self.ollama_timeout = 300  # 5 minutes per test
        self.tests_run = 0
        self.start_time = None
        
    def get_next_untested_combo(self) -> Optional[Dict[str, Any]]:
        """Get next variation+instruction+model+batch that hasn't been tested yet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    v.variation_id,
                    v.test_input,
                    v.expected_response,
                    v.difficulty_level,
                    i.instruction_id,
                    i.prompt_template,
                    m.model_name,
                    b.batch_id,
                    v.recipe_id,
                    r.canonical_code
                FROM variations v
                CROSS JOIN instructions i  
                CROSS JOIN models m
                CROSS JOIN batches b
                JOIN recipes r ON v.recipe_id = r.recipe_id
                WHERE v.enabled = 1 
                  AND i.enabled = 1
                  AND m.enabled = 1
                  AND v.recipe_id = i.recipe_id
                  AND NOT EXISTS (
                      SELECT 1 FROM dishes d
                      WHERE d.variation_id = v.variation_id
                        AND d.instruction_id = i.instruction_id  
                        AND d.model_name = m.model_name
                        AND d.batch_id = b.batch_id
                  )
                ORDER BY v.variation_id, i.instruction_id, m.model_name, b.batch_id
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'variation_id': result[0],
                    'test_input': result[1],
                    'expected_response': result[2],
                    'difficulty_level': result[3],
                    'instruction_id': result[4],
                    'prompt_template': result[5],
                    'model_name': result[6],
                    'batch_id': result[7],
                    'recipe_id': result[8],
                    'canonical_code': result[9]
                }
            return None
            
        except Exception as e:
            print(f"Error getting next combo: {e}")
            return None
    
    def render_prompt(self, template: str, test_input: str) -> str:
        """Replace placeholders in prompt template with test input"""
        # Handle simple payload replacements
        rendered = template.replace('{{payload}}', test_input)
        rendered = rendered.replace('{payload}', test_input)
        
        # Hardcode specific values for character extraction
        rendered = rendered.replace('{target_letter}', 'r')
        rendered = rendered.replace('{word}', test_input)
        
        # For any other single placeholders, replace with test_input
        import re
        placeholders = re.findall(r'\{([^}]+)\}', rendered)
        for placeholder in placeholders:
            rendered = rendered.replace(f'{{{placeholder}}}', test_input)
            
        return rendered
    
    def run_ollama_test(self, model: str, prompt: str) -> Dict[str, Any]:
        """Execute test with Ollama and return results"""
        try:
            start = time.time()
            
            result = subprocess.run(
                ['ollama', 'run', model, prompt],
                capture_output=True,
                text=True,
                timeout=self.ollama_timeout
            )
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                return {
                    'success': True,
                    'response': response,
                    'latency_ms': elapsed_ms,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'response': None,
                    'latency_ms': elapsed_ms,
                    'error': result.stderr.strip()
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'response': None,
                'latency_ms': self.ollama_timeout * 1000,
                'error': f'Timeout after {self.ollama_timeout}s'
            }
        except Exception as e:
            return {
                'success': False,
                'response': None,
                'latency_ms': 0,
                'error': str(e)
            }
    
    def save_result(self, combo: Dict[str, Any], result: Dict[str, Any], 
                    rendered_prompt: str) -> bool:
        """Save test result to dishes table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create a cooking session for this test
            cursor.execute("""
                INSERT INTO cooking_sessions (recipe_id, started_at, session_name) 
                VALUES (?, ?, ?)
            """, (combo['recipe_id'], datetime.now().isoformat(), 'Exhaustive Testing'))
            
            session_id = cursor.lastrowid
            
            # Save the dish
            cursor.execute("""
                INSERT INTO dishes (
                    variation_id,
                    instruction_id,
                    batch_id,
                    model_name,
                    prompt_rendered,
                    processing_received_response_dish,
                    processing_latency_dish,
                    error_details,
                    session_id,
                    enabled,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                combo['variation_id'],
                combo['instruction_id'],
                combo['batch_id'],
                combo['model_name'],
                rendered_prompt,
                result['response'],
                result['latency_ms'],
                result['error'],
                session_id,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                print("  Warning: Duplicate combination, skipping")
                return False
            print(f"  Database error: {e}")
            return False
        except Exception as e:
            print(f"  Error saving result: {e}")
            return False
    
    def run_tests(self, max_tests: int = None):
        """Run exhaustive tests until all combos are tested or max reached"""
        print("LLMCore Exhaustive Test Runner")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.db_path}")
        print()
        
        self.start_time = time.time()
        self.tests_run = 0
        
        while True:
            # Check if we've hit max tests
            if max_tests and self.tests_run >= max_tests:
                print(f"\nReached maximum of {max_tests} tests")
                break
            
            # Get next untested combo
            combo = self.get_next_untested_combo()
            if not combo:
                print("\nAll combinations tested!")
                break
            
            # Display progress
            print(f"Test {self.tests_run + 1}")
            print(f"  Recipe: {combo['canonical_code']}")
            print(f"  Input: {combo['test_input'][:50]}...")
            print(f"  Difficulty: {combo['difficulty_level']}")
            print(f"  Model: {combo['model_name']}")
            print(f"  Batch: {combo['batch_id']}")
            
            # Render prompt
            prompt = self.render_prompt(combo['prompt_template'], combo['test_input'])
            
            # Run test
            print(f"  Running...", end=" ", flush=True)
            result = self.run_ollama_test(combo['model_name'], prompt)
            
            if result['success']:
                print(f"OK ({result['latency_ms']}ms)")
                print(f"  Response: {result['response'][:80]}...")
            else:
                print(f"FAILED")
                print(f"  Error: {result['error']}")
            
            # Save result
            if self.save_result(combo, result, prompt):
                self.tests_run += 1
            
            print()
            time.sleep(0.5)  # Brief pause between tests
        
        # Summary
        elapsed = time.time() - self.start_time
        print("=" * 70)
        print(f"Tests completed: {self.tests_run}")
        print(f"Total time: {int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m {int(elapsed % 60)}s")
        print(f"Average: {elapsed / self.tests_run:.1f}s per test" if self.tests_run > 0 else "")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run exhaustive LLM tests')
    parser.add_argument('--max-tests', type=int, default=None,
                       help='Maximum number of tests to run (default: unlimited)')
    parser.add_argument('--db', type=str, 
                       default='/home/xai/Documents/ty_learn/data/llmcore.db',
                       help='Path to database')
    
    args = parser.parse_args()
    
    runner = ExhaustiveTestRunner(db_path=args.db)
    runner.run_tests(max_tests=args.max_tests)