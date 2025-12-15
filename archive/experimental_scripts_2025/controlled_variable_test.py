#!/usr/bin/env python3
"""
Controlled Variable Strawberry Test - Isolating Prompt vs Interface Effects
=========================================================================

This script tests the two key variables independently:
1. Prompt format (exact manual vs our variations)
2. Interface method (HTTP API vs CLI fresh sessions)

Test Matrix:
- HTTP + Manual Prompts
- CLI + Manual Prompts  
- HTTP + Our Original Prompts
- CLI + Our Original Prompts

Author: Arden the Builder
Date: September 19, 2025
Timeout: 6000 seconds (100 minutes)
"""

import json
import subprocess
import time
import requests
from datetime import datetime
from typing import Dict, List
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ControlledStrawberryTest:
    def __init__(self):
        self.models = []
        self.results = []
        
        # Your EXACT manual prompt
        self.manual_prompt = """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

## Processing Payload  
How many "r" letters are in "strawberry"?  

## QA Check  
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
        
        # Our original automated prompt
        self.our_prompt = """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

```
How many times does the letter 'r' appear in the word "strawberry"?  
```"""

        os.makedirs('controlled_test_output', exist_ok=True)

    def discover_models(self) -> List[str]:
        """Get a subset of models for quick controlled testing"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
            models = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    if ':' in model_name and model_name != 'bge-m3:567m':
                        models.append(model_name)
            
            # Take first 3 models for quick test
            self.models = sorted(models)[:3]
            logging.info(f"Testing with {len(self.models)} models: {self.models}")
            return self.models
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to discover models: {e}")
            return []

    def test_http_method(self, model: str, prompt: str, test_id: str) -> Dict:
        """Test using HTTP API (no session persistence)"""
        logging.info(f"HTTP Test: {model} - {test_id}")
        
        start_time = time.time()
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.1}
                },
                timeout=6000
            )
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                raw_response = result_data['response']
                extracted = self.extract_answer(raw_response)
                is_correct = extracted == '3'
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'method': 'HTTP',
                    'prompt_type': test_id,
                    'raw_response': raw_response,
                    'extracted_answer': extracted,
                    'is_correct': is_correct,
                    'latency': round(latency, 2)
                }
            else:
                return {'model': model, 'method': 'HTTP', 'prompt_type': test_id, 'error': f'HTTP {response.status_code}', 'is_correct': False}
                
        except Exception as e:
            return {'model': model, 'method': 'HTTP', 'prompt_type': test_id, 'error': str(e), 'is_correct': False}

    def test_cli_method(self, model: str, prompt: str, test_id: str) -> Dict:
        """Test using CLI with fresh session"""
        logging.info(f"CLI Test: {model} - {test_id}")
        
        start_time = time.time()
        try:
            # Use CLI with fresh process each time
            cmd = ['ollama', 'run', model]
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=6000
            )
            
            latency = time.time() - start_time
            
            if result.returncode == 0:
                raw_response = result.stdout.strip()
                extracted = self.extract_answer(raw_response)
                is_correct = extracted == '3'
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'method': 'CLI',
                    'prompt_type': test_id,
                    'raw_response': raw_response,
                    'extracted_answer': extracted,
                    'is_correct': is_correct,
                    'latency': round(latency, 2)
                }
            else:
                return {'model': model, 'method': 'CLI', 'prompt_type': test_id, 'error': result.stderr, 'is_correct': False}
                
        except Exception as e:
            return {'model': model, 'method': 'CLI', 'prompt_type': test_id, 'error': str(e), 'is_correct': False}

    def extract_answer(self, response: str) -> str:
        """Extract numerical answer from response"""
        # Look for bracketed number first
        bracket_match = re.search(r'\[(\d+)\]', response)
        if bracket_match:
            return bracket_match.group(1)
        
        # Look for any number
        numbers = re.findall(r'\b\d+\b', response)
        if numbers:
            return numbers[0]
        
        return 'NO_NUMBER_FOUND'

    def run_controlled_experiment(self):
        """Run the controlled experiment testing both variables"""
        
        logging.info("🧪 Starting Controlled Variable Experiment (6000s timeout)")
        logging.info("Testing: Prompt Format vs Interface Method")
        
        self.discover_models()
        if not self.models:
            logging.error("No models found!")
            return
        
        all_results = []
        
        # Test matrix: 2 prompts × 2 methods × N models
        test_combinations = [
            ('manual_prompt', self.manual_prompt, 'Manual_HTTP', self.test_http_method),
            ('manual_prompt', self.manual_prompt, 'Manual_CLI', self.test_cli_method),
            ('our_prompt', self.our_prompt, 'Our_HTTP', self.test_http_method),
            ('our_prompt', self.our_prompt, 'Our_CLI', self.test_cli_method)
        ]
        
        total_tests = len(test_combinations) * len(self.models)
        test_count = 0
        
        for prompt_name, prompt_content, test_id, test_method in test_combinations:
            logging.info(f"\n{'='*60}")
            logging.info(f"Testing: {test_id}")
            logging.info(f"{'='*60}")
            
            for model in self.models:
                test_count += 1
                logging.info(f"[{test_count}/{total_tests}] {model}")
                
                result = test_method(model, prompt_content, test_id)
                result['prompt_name'] = prompt_name
                all_results.append(result)
                
                # Brief pause between tests
                time.sleep(1)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw results
        json_file = f'controlled_test_output/controlled_results_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        logging.info(f"Results saved to {json_file}")
        
        # Generate analysis
        self.analyze_results(all_results, timestamp)

    def analyze_results(self, results: List[Dict], timestamp: str):
        """Analyze the controlled experiment results"""
        
        logging.info("\n📊 CONTROLLED EXPERIMENT ANALYSIS")
        logging.info("="*50)
        
        # Group results by test type
        analysis = {}
        for result in results:
            test_id = result.get('prompt_type', 'unknown')
            if test_id not in analysis:
                analysis[test_id] = {'total': 0, 'correct': 0, 'results': []}
            
            analysis[test_id]['total'] += 1
            if result.get('is_correct', False):
                analysis[test_id]['correct'] += 1
            analysis[test_id]['results'].append(result)
        
        # Print summary
        print("\n🎯 ACCURACY BY METHOD:")
        print("-" * 40)
        for test_id, data in analysis.items():
            accuracy = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
            print(f"{test_id:<15}: {data['correct']}/{data['total']} ({accuracy:.1f}%)")
        
        # Save detailed analysis
        analysis_file = f'controlled_test_output/analysis_{timestamp}.md'
        with open(analysis_file, 'w') as f:
            f.write("# Controlled Strawberry Test Analysis (6000s Timeout)\n\n")
            f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Models Tested:** {', '.join(self.models)}\n\n")
            
            f.write("## Results by Method\n\n")
            f.write("| Method | Correct | Total | Accuracy |\n")
            f.write("|--------|---------|-------|----------|\n")
            
            for test_id, data in analysis.items():
                accuracy = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
                f.write(f"| {test_id} | {data['correct']} | {data['total']} | {accuracy:.1f}% |\n")
            
            f.write("\n## Key Questions Answered\n\n")
            
            # Compare prompt effects
            manual_http = analysis.get('Manual_HTTP', {'correct': 0, 'total': 1})
            our_http = analysis.get('Our_HTTP', {'correct': 0, 'total': 1})
            manual_http_acc = manual_http['correct'] / manual_http['total'] * 100
            our_http_acc = our_http['correct'] / our_http['total'] * 100
            
            f.write(f"**1. Does prompt format matter?**\n")
            f.write(f"   - Manual prompt (HTTP): {manual_http_acc:.1f}%\n")
            f.write(f"   - Our prompt (HTTP): {our_http_acc:.1f}%\n")
            f.write(f"   - Difference: {abs(manual_http_acc - our_http_acc):.1f} percentage points\n\n")
            
            # Compare interface effects  
            manual_cli = analysis.get('Manual_CLI', {'correct': 0, 'total': 1})
            manual_cli_acc = manual_cli['correct'] / manual_cli['total'] * 100
            
            f.write(f"**2. Does interface method matter?**\n")
            f.write(f"   - Manual prompt (HTTP): {manual_http_acc:.1f}%\n")
            f.write(f"   - Manual prompt (CLI): {manual_cli_acc:.1f}%\n")
            f.write(f"   - Difference: {abs(manual_http_acc - manual_cli_acc):.1f} percentage points\n\n")
        
        logging.info(f"Detailed analysis saved to {analysis_file}")
        
        # Print conclusions
        print("\n🔬 CONCLUSIONS:")
        print("-" * 20)
        
        prompt_diff = abs(manual_http_acc - our_http_acc)
        interface_diff = abs(manual_http_acc - manual_cli_acc)
        
        if prompt_diff > interface_diff:
            print("📝 PROMPT FORMAT has bigger impact than interface method")
        elif interface_diff > prompt_diff:
            print("🔌 INTERFACE METHOD has bigger impact than prompt format")
        else:
            print("⚖️  Both factors have similar impact")

def main():
    tester = ControlledStrawberryTest()
    tester.run_controlled_experiment()

if __name__ == '__main__':
    main()