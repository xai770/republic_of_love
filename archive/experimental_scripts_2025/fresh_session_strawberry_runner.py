#!/usr/bin/env python3
"""
Fresh Session Strawberry Test Runner - True Fresh Context Testing
================================================================

This enhanced version ensures COMPLETELY FRESH CONTEXT for each test by:
1. Using HTTP API with fresh requests (no session reuse)
2. Optional model reloading for true isolation
3. Equivalent to starting new conversation each time

Author: Arden the Builder  
Date: September 19, 2025
"""

import json
import subprocess
import time
import csv
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import os
import statistics
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strawberry_fresh_test_results.log'),
        logging.StreamHandler()
    ]
)

class FreshSessionStrawberryRunner:
    def __init__(self, force_model_reload=False):
        self.models = []
        self.results = []
        self.correct_answer = "3"
        self.force_model_reload = force_model_reload  # New option for true isolation
        
        # Define prompt variations - EXACT MATCH to manual testing
        self.prompts = {
            'original': """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

## Processing Payload  
How many "r" letters are in "strawberry"?  

## QA Check  
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.""",
            
            'alternative': """## Payload
How many "r" letters are in "strawberry"? 

## Instructions
- Format your response as [NUMBER]. Make sure to to include ONE PAIR brackets in the output. 
- Example response: [X] where X is your calculated answer.
- Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
        }
        
        # Ensure output directory exists
        os.makedirs('strawberry_test_output', exist_ok=True)

    def discover_models(self) -> List[str]:
        """Discover available ollama models"""
        logging.info("Discovering available ollama models...")
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
            models = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    if ':' in model_name:  # Only versioned models
                        models.append(model_name)
            
            # Filter out unsupported models
            models = [m for m in models if m != 'bge-m3:567m']
            
            self.models = sorted(models)
            logging.info(f"Discovered {len(self.models)} models: {', '.join(self.models[:3])}{'...' if len(self.models) > 3 else ''}")
            return self.models
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to discover models: {e}")
            return []

    def reload_model(self, model_name: str):
        """Force fresh model loading by unloading and reloading"""
        if not self.force_model_reload:
            return  # Skip if not enabled
            
        try:
            logging.info(f"🔄 Reloading {model_name} for fresh context...")
            
            # Unload the model
            requests.post('http://localhost:11434/api/generate',
                         json={
                             'model': model_name,
                             'keep_alive': 0  # Unload immediately
                         },
                         timeout=10)
            
            time.sleep(1)  # Brief pause
            
            # Preload model
            requests.post('http://localhost:11434/api/generate',
                         json={
                             'model': model_name,
                             'prompt': "",  # Empty prompt to just load
                             'stream': False,
                         },
                         timeout=30)
                         
        except Exception as e:
            logging.warning(f"⚠️  Model reload failed (continuing anyway): {e}")

    def run_single_test(self, model_name: str, prompt_type: str, iteration: int) -> Dict:
        """Run a single test with completely fresh context"""
        
        # Optionally reload model for true isolation
        self.reload_model(model_name)
        
        prompt_content = self.prompts[prompt_type]
        logging.info(f"Testing {model_name} ({prompt_type} #{iteration})")
        
        start_time = time.time()
        
        try:
            # Use HTTP API for fresh request (no session memory)
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model_name,
                    'prompt': prompt_content,
                    'stream': False,
                    'options': {
                        'temperature': 0.1,  # Low temperature for consistency
                    }
                },
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                raw_response = result_data['response']
                
                # Extract answer
                extracted_answer = self.extract_answer(raw_response)
                is_correct = extracted_answer == '3'
                
                test_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt_type,
                    'iteration': iteration,
                    'prompt': prompt_content,
                    'raw_response': raw_response,
                    'extracted_answer': extracted_answer,
                    'is_correct': is_correct,
                    'latency': round(latency, 2),
                    'status': 'completed'
                }
                
                status_icon = '✓' if is_correct else '✗'
                logging.info(f"{status_icon} {model_name} {prompt_type} #{iteration}: {extracted_answer} ({status_icon}) - {latency:.2f}s")
                
                return test_result
                
            else:
                error_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt_type,
                    'iteration': iteration,
                    'raw_response': f'HTTP {response.status_code}',
                    'extracted_answer': None,
                    'is_correct': False,
                    'latency': round(latency, 2),
                    'status': 'error'
                }
                logging.error(f"❌ {model_name} {prompt_type} #{iteration}: HTTP {response.status_code}")
                return error_result
                
        except requests.exceptions.Timeout:
            timeout_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt_type,
                'iteration': iteration,
                'raw_response': 'TIMEOUT',
                'extracted_answer': None,
                'is_correct': False,
                'latency': 300.0,
                'status': 'timeout'
            }
            logging.error(f"⏰ {model_name} {prompt_type} #{iteration}: TIMEOUT")
            return timeout_result
            
        except Exception as e:
            exception_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt_type,
                'iteration': iteration,
                'raw_response': str(e),
                'extracted_answer': None,
                'is_correct': False,
                'latency': round(time.time() - start_time, 2),
                'status': 'exception'
            }
            logging.error(f"💥 {model_name} {prompt_type} #{iteration}: EXCEPTION - {str(e)}")
            return exception_result

    def extract_answer(self, response: str) -> str:
        """Extract numerical answer from response"""
        
        # Remove common artifacts
        clean_response = response.replace('\\n', ' ').replace('\\t', ' ')
        
        # Look for bracketed number first
        bracket_match = re.search(r'\[(\d+)\]', clean_response)
        if bracket_match:
            return bracket_match.group(1)
        
        # Look for any number in the response
        numbers = re.findall(r'\b\d+\b', clean_response)
        if numbers:
            return numbers[0]
        
        # Special cases
        if 'three' in clean_response.lower():
            return '3'
        if 'two' in clean_response.lower():
            return '2'
        
        return 'NO_NUMBER_FOUND'

    def save_results(self, results: List[Dict], suffix: str = ""):
        """Save results to JSON, CSV, and markdown"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON results
        json_file = f'strawberry_test_output/fresh_session_results_{timestamp}{suffix}.json'
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Raw results saved to {json_file}")
        
        # CSV results  
        csv_file = f'strawberry_test_output/fresh_session_results_{timestamp}{suffix}.csv'
        with open(csv_file, 'w', newline='') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        logging.info(f"CSV results saved to {csv_file}")
        
        # Summary markdown
        md_file = f'strawberry_test_output/fresh_session_summary_{timestamp}{suffix}.md'
        self.create_summary_report(results, md_file)
        logging.info(f"Summary report saved to {md_file}")

    def create_summary_report(self, results: List[Dict], filename: str):
        """Create markdown summary report"""
        
        # Calculate statistics
        total_tests = len(results)
        correct_tests = sum(1 for r in results if r.get('is_correct', False))
        accuracy = (correct_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Group by model
        model_stats = {}
        for result in results:
            model = result['model']
            if model not in model_stats:
                model_stats[model] = {'total': 0, 'correct': 0, 'latencies': []}
            
            model_stats[model]['total'] += 1
            if result.get('is_correct', False):
                model_stats[model]['correct'] += 1
            model_stats[model]['latencies'].append(result.get('latency', 0))
        
        with open(filename, 'w') as f:
            f.write("# Fresh Session Strawberry Test Results\\n\\n")
            f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"**Total Tests:** {total_tests}\\n")
            f.write(f"**Overall Accuracy:** {correct_tests}/{total_tests} ({accuracy:.1f}%)\\n\\n")
            
            f.write("## Model Performance\\n\\n")
            f.write("| Model | Accuracy | Avg Latency |\\n")
            f.write("|-------|----------|-------------|\\n")
            
            for model in sorted(model_stats.keys()):
                stats = model_stats[model]
                model_accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
                avg_latency = statistics.mean(stats['latencies']) if stats['latencies'] else 0
                
                f.write(f"| {model} | {stats['correct']}/{stats['total']} ({model_accuracy:.1f}%) | {avg_latency:.1f}s |\\n")

    def run_fresh_test_suite(self, iterations_per_prompt: int = 5):
        """Run the complete test suite with fresh sessions"""
        
        logging.info("🍓 Starting Fresh Session Strawberry Test Runner")
        logging.info(f"Fresh model reload: {'ENABLED' if self.force_model_reload else 'DISABLED (HTTP only)'}")
        
        self.discover_models()
        
        if not self.models:
            logging.error("No models found!")
            return
            
        total_tests = len(self.models) * len(self.prompts) * iterations_per_prompt
        logging.info(f"Will run {total_tests} tests ({len(self.models)} models × {len(self.prompts)} prompts × {iterations_per_prompt} iterations)")
        
        all_results = []
        test_count = 0
        
        for prompt_type in self.prompts.keys():
            logging.info(f"\\n{'='*60}")
            logging.info(f"Testing {prompt_type.upper()} prompt")
            logging.info(f"{'='*60}")
            
            for iteration in range(1, iterations_per_prompt + 1):
                logging.info(f"\\n📝 {prompt_type.title()} Prompt - Iteration {iteration}/{iterations_per_prompt}")
                
                for i, model in enumerate(self.models, 1):
                    test_count += 1
                    logging.info(f"Testing {model} ({i}/{len(self.models)}) - {prompt_type} #{iteration} [{test_count}/{total_tests}]")
                    
                    result = self.run_single_test(model, prompt_type, iteration)
                    all_results.append(result)
                    
                    # Save incrementally every 10 tests
                    if test_count % 10 == 0:
                        self.save_results(all_results, "_incremental")
        
        # Final save
        self.save_results(all_results)
        
        # Summary statistics
        correct_count = sum(1 for r in all_results if r.get('is_correct', False))
        total_count = len(all_results)
        
        logging.info("\\n🎉 Fresh Session Test Complete!")
        logging.info(f"Final Results: {correct_count}/{total_count} correct ({correct_count/total_count*100:.1f}%)")
        logging.info(f"Files saved to 'strawberry_test_output' directory")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fresh Session Strawberry Test Runner')
    parser.add_argument('--force-reload', action='store_true', 
                       help='Force model reload for each test (slower but more isolated)')
    parser.add_argument('--iterations', type=int, default=5,
                       help='Iterations per prompt per model (default: 5)')
    
    args = parser.parse_args()
    
    runner = FreshSessionStrawberryRunner(force_model_reload=args.force_reload)
    runner.run_fresh_test_suite(iterations_per_prompt=args.iterations)

if __name__ == '__main__':
    main()