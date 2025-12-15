#!/usr/bin/env python3
"""
Reverse String Gradient Test Runner
==================================
Comprehensive testing of string reversal capabilities across all models
using graduated word complexity from 2 to 45 letters.

Similar to the strawberry test but for string manipulation capabilities.
"""

import json
import csv
import sqlite3
import subprocess
import time
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReverseStringGradientTester:
    """Comprehensive reverse string gradient testing framework"""
    
    def __init__(self, output_dir: str = "reverse_test_output"):
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.models = []
        self.test_parameters = []
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Setup database connection
        self.db_path = 'data/llmcore.db'
        
    def load_active_models(self) -> List[str]:
        """Load active models from database"""
        
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
        
        logger.info(f"📋 Loaded {len(models)} active models")
        return models
    
    def load_test_parameters(self) -> List[Dict]:
        """Load all reverse string gradient test parameters from word_banks"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT content, length, target_letter
            FROM word_banks
            WHERE category = 'reverse_string_gradient'
            ORDER BY length, content
        """)
        
        parameters = []
        param_id = 1
        for row in cursor.fetchall():
            word = row[0]
            difficulty = row[1]
            reversed_word = row[2]  # Stored in target_letter field
            formatted_response = f"[{reversed_word}]"
            
            parameters.append({
                'parameter_id': param_id,
                'word': word,
                'reversed': reversed_word,
                'formatted': formatted_response,
                'difficulty': difficulty,
                'expected': formatted_response
            })
            param_id += 1
        
        conn.close()
        
        logger.info(f"📋 Loaded {len(parameters)} test parameters")
        return parameters
    
    def test_model_on_word(self, model: str, word: str, expected: str, difficulty: int) -> Dict:
        """Test a single model on a single word reversal"""
        
        prompt = f"""## Processing Instructions
Format your response as [string]. Make sure to include the brackets in the output.

## Processing Payload
Write "{word}" backwards.

## QA Check
Submit ONLY the required response. Do not add spaces. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
        
        start_time = time.time()
        
        try:
            # Execute ollama with timeout and proper stdin handling
            result = subprocess.run([
                'ollama', 'run', model, prompt
            ], capture_output=True, text=True, timeout=120, input="")
            
            end_time = time.time()
            latency = end_time - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Check for exact match
                is_correct = response == expected
                
                return {
                    'model': model,
                    'word': word,
                    'expected': expected,
                    'response': response,
                    'correct': is_correct,
                    'latency': latency,
                    'difficulty': difficulty,
                    'error': None,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'model': model,
                    'word': word,
                    'expected': expected,
                    'response': '',
                    'correct': False,
                    'latency': time.time() - start_time,
                    'difficulty': difficulty,
                    'error': f"Ollama error: {result.stderr.strip()}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except subprocess.TimeoutExpired:
            return {
                'model': model,
                'word': word,
                'expected': expected,
                'response': '',
                'correct': False,
                'latency': 120.0,
                'difficulty': difficulty,
                'error': "Timeout (120s)",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'model': model,
                'word': word,
                'expected': expected,
                'response': '',
                'correct': False,
                'latency': 0.0,
                'difficulty': difficulty,
                'error': f"Exception: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def run_comprehensive_test(self, iterations: int = 1) -> None:
        """Run comprehensive reverse string gradient test across all models"""
        
        # Load models and parameters
        self.models = self.load_active_models()
        self.test_parameters = self.load_test_parameters()
        
        total_tests = len(self.models) * len(self.test_parameters) * iterations
        completed_tests = 0
        
        print(f"\n🔄 STARTING COMPREHENSIVE REVERSE STRING GRADIENT TEST")
        print(f"📊 Models: {len(self.models)}")
        print(f"📊 Parameters: {len(self.test_parameters)} (difficulty 2-45 letters)")
        print(f"📊 Iterations: {iterations}")
        print(f"📊 Total tests: {total_tests}")
        print(f"⏱️  Estimated duration: {total_tests * 5 / 60:.1f} minutes")
        print("="*70)
        
        start_time = datetime.now()
        
        for iteration in range(iterations):
            logger.info(f"🔄 Starting iteration {iteration + 1}/{iterations}")
            
            for i, model in enumerate(self.models):
                logger.info(f"🤖 Testing model {i+1}/{len(self.models)}: {model}")
                
                model_correct = 0
                model_total = 0
                
                for j, param in enumerate(self.test_parameters):
                    result = self.test_model_on_word(
                        model=model,
                        word=param['word'],
                        expected=param['expected'],
                        difficulty=param['difficulty']
                    )
                    
                    result['iteration'] = iteration + 1
                    self.results.append(result)
                    
                    if result['correct']:
                        model_correct += 1
                    model_total += 1
                    
                    completed_tests += 1
                    
                    # Progress update every 10 tests
                    if completed_tests % 10 == 0:
                        progress = (completed_tests / total_tests) * 100
                        elapsed = (datetime.now() - start_time).total_seconds() / 60
                        remaining = (elapsed / (completed_tests / total_tests)) - elapsed
                        
                        print(f"⚡ Progress: {completed_tests}/{total_tests} ({progress:.1f}%) | "
                              f"Elapsed: {elapsed:.1f}m | Remaining: {remaining:.1f}m")
                
                # Model summary
                model_accuracy = (model_correct / model_total) * 100
                logger.info(f"✅ {model}: {model_correct}/{model_total} ({model_accuracy:.1f}%)")
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() / 60
        
        print(f"\n🎉 TEST COMPLETED!")
        print(f"⏱️  Total duration: {total_duration:.1f} minutes")
        print(f"📊 Total tests executed: {len(self.results)}")
        
        # Save results
        self.save_results()
        self.generate_analysis()
    
    def save_results(self) -> None:
        """Save results to CSV and JSON files"""
        
        # CSV file
        csv_filename = f"{self.output_dir}/reverse_results_{self.timestamp}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['model', 'word', 'expected', 'response', 'correct', 'latency', 
                         'difficulty', 'error', 'iteration', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        # JSON file
        json_filename = f"{self.output_dir}/reverse_results_{self.timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.results, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Results saved to {csv_filename} and {json_filename}")
    
    def generate_analysis(self) -> None:
        """Generate comprehensive analysis and summary"""
        
        # Calculate model performance
        model_stats = {}
        for result in self.results:
            model = result['model']
            if model not in model_stats:
                model_stats[model] = {
                    'total': 0,
                    'correct': 0,
                    'total_latency': 0,
                    'errors': 0,
                    'by_difficulty': {}
                }
            
            stats = model_stats[model]
            stats['total'] += 1
            if result['correct']:
                stats['correct'] += 1
            stats['total_latency'] += result['latency']
            if result['error']:
                stats['errors'] += 1
            
            # Track by difficulty
            diff = result['difficulty']
            if diff not in stats['by_difficulty']:
                stats['by_difficulty'][diff] = {'total': 0, 'correct': 0}
            stats['by_difficulty'][diff]['total'] += 1
            if result['correct']:
                stats['by_difficulty'][diff]['correct'] += 1
        
        # Generate markdown analysis
        analysis_filename = f"{self.output_dir}/reverse_analysis_{self.timestamp}.md"
        
        with open(analysis_filename, 'w', encoding='utf-8') as f:
            f.write("# 🔄 Reverse String Gradient Test Analysis\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall statistics
            total_tests = len(self.results)
            total_correct = sum(1 for r in self.results if r['correct'])
            overall_accuracy = (total_correct / total_tests) * 100 if total_tests > 0 else 0
            
            f.write("## 📊 Overall Statistics\n\n")
            f.write(f"- **Total Tests:** {total_tests:,}\n")
            f.write(f"- **Models Tested:** {len(model_stats)}\n")
            f.write(f"- **Overall Accuracy:** {overall_accuracy:.1f}% ({total_correct:,}/{total_tests:,})\n")
            f.write(f"- **Test Parameters:** {len(self.test_parameters)}\n")
            f.write(f"- **Difficulty Range:** 2-45 letters\n\n")
            
            # Model rankings
            f.write("## 🏆 Model Performance Rankings\n\n")
            
            # Sort models by accuracy, then by speed
            ranked_models = []
            for model, stats in model_stats.items():
                accuracy = (stats['correct'] / stats['total']) * 100
                avg_latency = stats['total_latency'] / stats['total']
                ranked_models.append({
                    'model': model,
                    'accuracy': accuracy,
                    'correct': stats['correct'],
                    'total': stats['total'],
                    'avg_latency': avg_latency,
                    'errors': stats['errors']
                })
            
            ranked_models.sort(key=lambda x: (-x['accuracy'], x['avg_latency']))
            
            f.write("| Rank | Model | Accuracy | Speed | Errors |\n")
            f.write("|------|-------|----------|-------|--------|\n")
            
            for i, model_data in enumerate(ranked_models):
                f.write(f"| {i+1:2d} | `{model_data['model']}` | "
                       f"{model_data['accuracy']:5.1f}% ({model_data['correct']}/{model_data['total']}) | "
                       f"{model_data['avg_latency']:5.1f}s | {model_data['errors']} |\n")
            
            # Difficulty analysis
            f.write("\n## 📈 Difficulty Analysis\n\n")
            
            # Calculate accuracy by difficulty level
            difficulty_stats = {}
            for result in self.results:
                diff = result['difficulty']
                if diff not in difficulty_stats:
                    difficulty_stats[diff] = {'total': 0, 'correct': 0}
                difficulty_stats[diff]['total'] += 1
                if result['correct']:
                    difficulty_stats[diff]['correct'] += 1
            
            f.write("| Letters | Tests | Accuracy | Words |\n")
            f.write("|---------|-------|----------|---------|\n")
            
            for diff in sorted(difficulty_stats.keys()):
                stats = difficulty_stats[diff]
                accuracy = (stats['correct'] / stats['total']) * 100
                
                # Get sample words for this difficulty
                sample_words = [p['word'] for p in self.test_parameters if p['difficulty'] == diff]
                words_str = ', '.join(sample_words[:3])
                if len(sample_words) > 3:
                    words_str += f", ... ({len(sample_words)} total)"
                
                f.write(f"| {diff:2d} | {stats['total']:3d} | {accuracy:5.1f}% | {words_str} |\n")
        
        logger.info(f"📊 Analysis saved to {analysis_filename}")

def main():
    """Main function"""
    
    tester = ReverseStringGradientTester()
    
    try:
        # Run the comprehensive test
        tester.run_comprehensive_test(iterations=1)
        
        print(f"\n✅ Reverse String Gradient Test completed!")
        print(f"📁 Results saved in: {tester.output_dir}/")
        
    except KeyboardInterrupt:
        logger.info("❌ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()