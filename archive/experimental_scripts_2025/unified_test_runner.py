#!/usr/bin/env python3
"""
Unified Test Execution System
============================
Consolidates all gradient tests into a single, repeatable SQL-driven framework.
Perfect for hourly production runs on your AI workstation.
"""

import sqlite3
import json
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnifiedTestRunner:
    """
    Unified test execution system for all gradient capability tests.
    Designed for hourly production runs with SQL-driven configuration.
    """
    
    def __init__(self, db_path: str = 'data/llmcore.db'):
        self.db_path = db_path
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def get_active_test_configurations(self) -> List[Dict]:
        """Load all active test configurations from unified test_parameters table"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all active test types from unified test_parameters
        cursor.execute("""
            SELECT DISTINCT 
                canonical_code,
                test_type,
                COUNT(*) as parameter_count,
                MIN(difficulty_level) as min_difficulty,
                MAX(difficulty_level) as max_difficulty
            FROM test_parameters 
            WHERE enabled = 1
            GROUP BY canonical_code, test_type
            ORDER BY canonical_code
        """)
        
        configurations = []
        for row in cursor.fetchall():
            configurations.append({
                'canonical_code': row[0],
                'test_type': row[1],
                'parameter_count': row[2],
                'min_difficulty': row[3],
                'max_difficulty': row[4],
                'enabled': True
            })
        
        conn.close()
        return configurations
        
    def get_active_models(self) -> List[str]:
        """Get all active models for testing"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_name 
            FROM models 
            WHERE enabled = 1 
            ORDER BY model_name
        """)
        
        models = [row[0] for row in cursor.fetchall()]
        conn.close()
        return models
        
    def load_test_parameters(self, canonical_code: str, category: str = None) -> List[Dict]:
        """Load parameters from the clean unified test_parameters table"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load directly from unified test_parameters table
        cursor.execute("""
            SELECT 
                test_type,
                test_word,
                difficulty_level,
                expected_response,
                prompt_template,
                response_format
            FROM test_parameters
            WHERE canonical_code = ? AND enabled = 1
            ORDER BY difficulty_level, test_word
        """, (canonical_code,))
        
        parameters = []
        for row in cursor.fetchall():
            parameters.append({
                'test_type': row[0],
                'word': row[1],
                'difficulty': row[2],
                'expected': row[3],
                'prompt_template': row[4],
                'expected_format': row[5]
            })
        
        conn.close()
        return parameters
        
    def execute_test(self, model: str, test_config: Dict) -> Dict:
        """Execute a single test on a model"""
        
        prompt = test_config['prompt_template'].format(word=test_config['word'])
        
        start_time = time.time()
        
        try:
            result = subprocess.run([
                'ollama', 'run', model, prompt
            ], capture_output=True, text=True, timeout=120, input="")
            
            latency = time.time() - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Check correctness based on format
                if test_config['expected_format'] == 'number':
                    is_correct = response == test_config['expected']
                elif test_config['expected_format'] == 'bracketed_string':
                    is_correct = response == test_config['expected']
                else:
                    is_correct = response == test_config['expected']
                
                return {
                    'model': model,
                    'test_type': test_config['test_type'],
                    'word': test_config['word'],
                    'difficulty': test_config['difficulty'],
                    'expected': test_config['expected'],
                    'response': response,
                    'correct': is_correct,
                    'latency': latency,
                    'error': None,
                    'timestamp': datetime.now().isoformat(),
                    'session_id': self.session_id
                }
            else:
                return {
                    'model': model,
                    'test_type': test_config['test_type'],
                    'word': test_config['word'],
                    'difficulty': test_config['difficulty'],
                    'expected': test_config['expected'],
                    'response': '',
                    'correct': False,
                    'latency': latency,
                    'error': f"Ollama error: {result.stderr.strip()}",
                    'timestamp': datetime.now().isoformat(),
                    'session_id': self.session_id
                }
                
        except Exception as e:
            return {
                'model': model,
                'test_type': test_config['test_type'],
                'word': test_config['word'],
                'difficulty': test_config['difficulty'],
                'expected': test_config['expected'],
                'response': '',
                'correct': False,
                'latency': time.time() - start_time,
                'error': f"Exception: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'session_id': self.session_id
            }
    
    def store_results(self, results: List[Dict]) -> None:
        """Store results in unified test_results table"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create unified results table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unified_test_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                test_type TEXT NOT NULL,
                test_word TEXT NOT NULL,
                difficulty_level INTEGER NOT NULL,
                expected_response TEXT NOT NULL,
                actual_response TEXT,
                is_correct INTEGER NOT NULL,
                latency_seconds REAL NOT NULL,
                error_message TEXT,
                executed_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert all results
        for result in results:
            cursor.execute("""
                INSERT INTO unified_test_results (
                    session_id, model_name, test_type, test_word, 
                    difficulty_level, expected_response, actual_response,
                    is_correct, latency_seconds, error_message, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result['session_id'],
                result['model'],
                result['test_type'],
                result['word'],
                result['difficulty'],
                result['expected'],
                result['response'],
                1 if result['correct'] else 0,
                result['latency'],
                result['error'],
                result['timestamp']
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Stored {len(results)} results in unified_test_results table")
    
    def run_hourly_test_suite(self) -> Dict:
        """Run the complete hourly test suite - designed for production cron"""
        
        logger.info(f"🚀 Starting Hourly Test Suite - Session {self.session_id}")
        
        # Get configurations and models
        test_configs = self.get_active_test_configurations()
        models = self.get_active_models()
        
        total_tests = sum(config['parameter_count'] for config in test_configs) * len(models)
        
        print(f"\n🎯 HOURLY UNIFIED TEST EXECUTION")
        print(f"📊 Test Types: {len(test_configs)}")
        print(f"📊 Models: {len(models)}")
        print(f"📊 Total Tests: {total_tests:,}")
        print(f"🆔 Session ID: {self.session_id}")
        print("="*60)
        
        all_results = []
        completed_tests = 0
        
        start_time = datetime.now()
        
        for test_config in test_configs:
            logger.info(f"🧪 Running {test_config['canonical_code']} ({test_config['test_type']}) tests")
            
            # Load parameters for this test type
            parameters = self.load_test_parameters(test_config['canonical_code'])
            
            for model in models:
                model_correct = 0
                
                for param in parameters:
                    result = self.execute_test(model, param)
                    all_results.append(result)
                    
                    if result['correct']:
                        model_correct += 1
                    
                    completed_tests += 1
                    
                    # Progress update every 50 tests
                    if completed_tests % 50 == 0:
                        progress = (completed_tests / total_tests) * 100
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        remaining = (elapsed / (completed_tests / total_tests)) - elapsed
                        
                        print(f"⚡ Progress: {completed_tests}/{total_tests} ({progress:.1f}%) | "
                              f"Elapsed: {elapsed:.1f}m | Remaining: {remaining:.1f}m")
                
                # Model summary
                accuracy = (model_correct / len(parameters)) * 100
                logger.info(f"✅ {model}: {model_correct}/{len(parameters)} ({accuracy:.1f}%)")
        
        # Store all results
        self.store_results(all_results)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        # Generate summary
        summary = {
            'session_id': self.session_id,
            'total_tests': len(all_results),
            'total_correct': sum(1 for r in all_results if r['correct']),
            'overall_accuracy': (sum(1 for r in all_results if r['correct']) / len(all_results)) * 100,
            'duration_minutes': duration,
            'models_tested': len(models),
            'test_types': len(test_configs),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        print(f"\n🎉 HOURLY TEST SUITE COMPLETED!")
        print(f"⏱️  Duration: {duration:.1f} minutes")
        print(f"📊 Overall Accuracy: {summary['overall_accuracy']:.1f}%")
        print(f"💾 Results stored in unified_test_results table")
        
        return summary

def main():
    """Main entry point for hourly test execution"""
    
    runner = UnifiedTestRunner()
    
    try:
        summary = runner.run_hourly_test_suite()
        
        # Save summary as JSON for monitoring
        with open(f'hourly_test_summary_{runner.session_id}.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📊 Summary saved: hourly_test_summary_{runner.session_id}.json")
        
    except Exception as e:
        logger.error(f"❌ Hourly test failed: {e}")
        raise

if __name__ == "__main__":
    main()