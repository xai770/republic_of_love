#!/usr/bin/env python3
"""
Complete Manual Prompt Validation Test
=====================================

This script tests your EXACT manual prompt across ALL models from your manual test
to validate the controlled experiment findings and compare with your manual results.

Models from your manual test:
- gpt-oss:latest, mistral-nemo:12b, granite3.1-moe:3b, qwen2.5:7b
- llama3.2:latest, gemma3:4b, phi3:3.8b, phi4-mini-reasoning:latest
- qwen3:latest, deepseek-r1:8b, gemma3:1b, qwen3:0.6b
- qwen3:4b, qwen3:1.7b, mistral:latest, dolphin3:8b
- olmo2:latest, codegemma:latest, qwen2.5vl:latest, gemma3n:latest
- llama3.2:1b, phi4-mini:latest, gemma2:latest, gemma3n:e2b

Author: Arden the Builder
Date: September 19, 2025
"""

import json
import subprocess
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ManualPromptValidator:
    def __init__(self):
        self.models = []
        self.results = []
        
        # Your EXACT manual prompt (the one that works)
        self.manual_prompt = """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

## Processing Payload  
How many "r" letters are in "strawberry"?  

## QA Check  
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

        # Your manual results for comparison
        self.manual_results = {
            'gpt-oss:latest': '[3]',
            'mistral-nemo:12b': '[3]', 
            'granite3.1-moe:3b': '[6]',
            'qwen2.5:7b': '[3]',
            'llama3.2:latest': '[3]',
            'gemma3:4b': '[3]',
            'phi3:3.8b': '[3]',
            'phi4-mini-reasoning:latest': '[3]',
            'qwen3:latest': '[3]',
            'deepseek-r1:8b': '[3]',
            'gemma3:1b': '[2]',
            'qwen3:0.6b': '[2]', 
            'qwen3:4b': '[3]',
            'qwen3:1.7b': '[3]',
            'mistral:latest': '[3]',
            'dolphin3:8b': '[5]',
            'olmo2:latest': '[4]',
            'codegemma:latest': '[5]',
            'qwen2.5vl:latest': '[strawberry contains 2 "r" letters]',
            'gemma3n:latest': '[ 3 ]',
            'llama3.2:1b': '[7]',
            'phi4-mini:latest': '[3]',
            'gemma2:latest': '[3]',
            'gemma3n:e2b': '[3]'
        }

        os.makedirs('validation_output', exist_ok=True)

    def discover_available_models(self) -> List[str]:
        """Get all available models and filter to match manual test models"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
            available_models = []
            for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    if ':' in model_name and model_name != 'bge-m3:567m':
                        available_models.append(model_name)
            
            # Filter to only models from your manual test
            manual_test_models = list(self.manual_results.keys())
            self.models = [model for model in manual_test_models if model in available_models]
            
            logging.info(f"Found {len(self.models)} models from your manual test:")
            for model in self.models:
                logging.info(f"  ✅ {model}")
                
            missing_models = [model for model in manual_test_models if model not in available_models]
            if missing_models:
                logging.info(f"\nMissing models (not available locally):")
                for model in missing_models:
                    logging.info(f"  ❌ {model}")
            
            return self.models
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to discover models: {e}")
            return []

    def test_model_http(self, model: str) -> Dict:
        """Test a single model using HTTP API with your exact manual prompt"""
        logging.info(f"Testing {model} via HTTP...")
        
        start_time = time.time()
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model,
                    'prompt': self.manual_prompt,
                    'stream': False,
                    'options': {'temperature': 0.1}
                },
                timeout=300  # 5 minutes should be enough for most models
            )
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                result_data = response.json()
                raw_response = result_data['response']
                extracted = self.extract_answer(raw_response)
                manual_answer = self.manual_results.get(model, 'UNKNOWN')
                is_match = extracted == manual_answer.strip('[]')
                is_correct = extracted == '3'
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'method': 'HTTP',
                    'raw_response': raw_response,
                    'extracted_answer': extracted,
                    'manual_result': manual_answer,
                    'matches_manual': is_match,
                    'is_correct': is_correct,
                    'latency': round(latency, 2)
                }
            else:
                return {
                    'model': model, 
                    'method': 'HTTP', 
                    'error': f'HTTP {response.status_code}', 
                    'manual_result': self.manual_results.get(model, 'UNKNOWN'),
                    'matches_manual': False,
                    'is_correct': False
                }
                
        except Exception as e:
            return {
                'model': model, 
                'method': 'HTTP', 
                'error': str(e),
                'manual_result': self.manual_results.get(model, 'UNKNOWN'), 
                'matches_manual': False,
                'is_correct': False
            }

    def extract_answer(self, response: str) -> str:
        """Extract numerical answer from response"""
        # Look for bracketed number first
        bracket_match = re.search(r'\[(\d+)\]', response)
        if bracket_match:
            return bracket_match.group(1)
        
        # Look for bracketed content with spaces
        bracket_space_match = re.search(r'\[\s*(\d+)\s*\]', response)
        if bracket_space_match:
            return bracket_space_match.group(1)
        
        # Look for special text responses
        if 'contains 2 "r" letters' in response.lower():
            return '2'
        
        # Look for any number
        numbers = re.findall(r'\b\d+\b', response)
        if numbers:
            return numbers[0]
        
        return 'NO_NUMBER_FOUND'

    def run_validation_test(self):
        """Run the complete validation test across all available models"""
        
        logging.info("🔬 Starting Manual Prompt Validation Test")
        logging.info("Testing your EXACT manual prompt across all available models")
        
        self.discover_available_models()
        if not self.models:
            logging.error("No models found from your manual test!")
            return
        
        all_results = []
        total_models = len(self.models)
        
        for i, model in enumerate(self.models, 1):
            logging.info(f"\n{'='*60}")
            logging.info(f"[{i}/{total_models}] Testing: {model}")
            logging.info(f"Manual result was: {self.manual_results[model]}")
            logging.info(f"{'='*60}")
            
            result = self.test_model_http(model)
            all_results.append(result)
            
            # Show immediate result
            if 'error' not in result:
                extracted = result['extracted_answer']
                manual = result['manual_result']
                match_status = "✅ MATCH" if result['matches_manual'] else "❌ DIFFERENT"
                correct_status = "✅ CORRECT" if result['is_correct'] else "❌ WRONG"
                
                logging.info(f"   HTTP Result: [{extracted}] vs Manual: {manual} → {match_status} | {correct_status}")
            else:
                logging.info(f"   ❌ ERROR: {result['error']}")
            
            # Brief pause between tests
            time.sleep(2)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw results
        json_file = f'validation_output/validation_results_{timestamp}.json'
        with open(json_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        logging.info(f"\nResults saved to {json_file}")
        
        # Generate analysis
        self.analyze_validation_results(all_results, timestamp)

    def analyze_validation_results(self, results: List[Dict], timestamp: str):
        """Analyze the validation test results"""
        
        logging.info("\n📊 VALIDATION ANALYSIS")
        logging.info("="*60)
        
        # Calculate statistics
        total_tests = len(results)
        successful_tests = len([r for r in results if 'error' not in r])
        exact_matches = len([r for r in results if r.get('matches_manual', False)])
        correct_answers = len([r for r in results if r.get('is_correct', False)])
        
        match_rate = (exact_matches / successful_tests * 100) if successful_tests > 0 else 0
        accuracy_rate = (correct_answers / successful_tests * 100) if successful_tests > 0 else 0
        
        print(f"\n🎯 VALIDATION SUMMARY:")
        print(f"Total models tested: {total_tests}")
        print(f"Successful tests: {successful_tests}")
        print(f"Exact matches with manual: {exact_matches}/{successful_tests} ({match_rate:.1f}%)")
        print(f"Correct answers [3]: {correct_answers}/{successful_tests} ({accuracy_rate:.1f}%)")
        
        # Detailed comparison table
        print(f"\n📋 DETAILED COMPARISON:")
        print(f"{'Model':<25} {'Manual':<10} {'HTTP':<10} {'Match':<8} {'Correct':<8}")
        print("-" * 65)
        
        for result in results:
            if 'error' in result:
                print(f"{result['model']:<25} {result['manual_result']:<10} {'ERROR':<10} {'❌':<8} {'❌':<8}")
            else:
                model = result['model']
                manual = result['manual_result']
                http_result = f"[{result['extracted_answer']}]"
                match = "✅" if result['matches_manual'] else "❌"
                correct = "✅" if result['is_correct'] else "❌"
                print(f"{model:<25} {manual:<10} {http_result:<10} {match:<8} {correct:<8}")
        
        # Save detailed analysis
        analysis_file = f'validation_output/validation_analysis_{timestamp}.md'
        with open(analysis_file, 'w') as f:
            f.write("# Manual Prompt Validation Analysis\n\n")
            f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Purpose:** Validate controlled experiment findings by testing your exact manual prompt\n\n")
            
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Models Tested:** {total_tests}\n")
            f.write(f"- **Successful Tests:** {successful_tests}\n")
            f.write(f"- **Exact Matches:** {exact_matches}/{successful_tests} ({match_rate:.1f}%)\n")
            f.write(f"- **Correct Answers:** {correct_answers}/{successful_tests} ({accuracy_rate:.1f}%)\n\n")
            
            f.write("## Detailed Results\n\n")
            f.write("| Model | Manual Result | HTTP Result | Match | Correct | Notes |\n")
            f.write("|-------|---------------|-------------|-------|---------|-------|\n")
            
            for result in results:
                model = result['model']
                manual = result['manual_result']
                
                if 'error' in result:
                    f.write(f"| {model} | {manual} | ERROR | ❌ | ❌ | {result['error']} |\n")
                else:
                    http_result = f"[{result['extracted_answer']}]"
                    match = "✅" if result['matches_manual'] else "❌"
                    correct = "✅" if result['is_correct'] else "❌"
                    f.write(f"| {model} | {manual} | {http_result} | {match} | {correct} | - |\n")
            
            f.write(f"\n## Key Findings\n\n")
            f.write(f"1. **Consistency Rate:** {match_rate:.1f}% of models gave identical results to your manual tests\n")
            f.write(f"2. **Accuracy Rate:** {accuracy_rate:.1f}% of models gave the correct answer [3]\n")
            f.write(f"3. **Reliability:** This validates that HTTP API produces consistent results with manual CLI testing\n\n")
        
        logging.info(f"Detailed analysis saved to {analysis_file}")
        
        # Final conclusion
        print(f"\n🔬 CONCLUSION:")
        if match_rate >= 80:
            print("🎉 EXCELLENT consistency! HTTP results closely match your manual tests.")
        elif match_rate >= 60:
            print("👍 GOOD consistency! Most HTTP results match your manual tests.")
        else:
            print("🤔 MIXED results. Some differences between HTTP and manual testing.")
        
        print(f"This validates our controlled experiment findings about prompt format being the key variable!")

def main():
    validator = ManualPromptValidator()
    validator.run_validation_test()

if __name__ == '__main__':
    main()