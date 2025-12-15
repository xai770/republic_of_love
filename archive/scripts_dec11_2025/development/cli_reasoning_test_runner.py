#!/usr/bin/env python3
"""
CLI-based Comprehensive LLM Reasoning Test Runner
Uses ollama CLI commands instead of HTTP API to match manual testing conditions
"""

import subprocess
import json
import time
import csv
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
import re
import os

class CLIReasoningTestRunner:
    def __init__(self):
        self.test_definitions = self._load_test_definitions()
        
    def _load_test_definitions(self) -> Dict:
        """Load all 17 test definitions from the manual test matrix"""
        return {
            "strawberry": {
                "prompt": '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"? 

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[3]"
            },
            "accommodation": {
                "prompt": '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [your calculated answer].

## Processing Payload
How many double letters are in "accommodation"?

## QA Check
 Format your response as the number only in square brackets. Do not include quotation marks, spaces, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[2]"
            },
            "analysis": {
                "prompt": '''## Processing Instructions
Read the processing payload. Reply [Yes] or [No]. Make sure to to include the brackets in the output.

## Processing Payload
Is the plural of "analysis" "analyses"?

## QA Check
Submit ONLY the required response.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[Yes]"
            },
            "grammar": {
                "prompt": '''## Processing Instructions
Read the processing payload. Make sure to to include the brackets in the output.

## Processing Payload
Is the sentence "He don't know the answer" grammatically correct? Reply [Yes] or [No]. 

## QA Check
Submit ONLY the required response.''',
                "expected": "[No]"
            },
            "percent": {
                "prompt": '''## Processing Instructions
DO NOT RETURN COMMENTARY, EXPLANATIONS OR OTHER ADDITIONS!
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
What is 15% of 200? Reply ONLY the correct number.

## QA Check
Submit ONLY the required response.''',
                "expected": "[30]"
            },
            "arithmetic": {
                "prompt": '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
Calculate 12 divided by 3 plus 4 times 2. 

## QA Check
Submit ONLY the required response.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[12]"
            },
            "translate": {
                "prompt": '''## Processing Instructions
DO NOT RETURN COMMENTARY, EXPLANATIONS OR OTHER ADDITIONS!
Format your response as [translation].Make sure to to include the brackets in the output.
Example: [Merci]
Example: [Bonne nuitt]

Translate "I am happy" into French. Use the male form.

## QA Check
Submit ONLY the required response in square brackets].  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[Je suis heureux]"
            },
            "memory": {
                "prompt": '''## Processing Instructions
Format your response as [string]. 
Example: [example]

## Processing Payload
Remember this word: orchid. Now respond with exactly that word.

## QA Check
Submit ONLY the required response in brackets. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[orchid]"
            }
        }

    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama CLI"""
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = []
                for line in lines:
                    if line.strip():
                        model_name = line.split()[0]  # First column is model name
                        models.append(model_name)
                return models
            else:
                print(f"Error getting models: {result.stderr}")
                return []
        except Exception as e:
            print(f"Error getting models: {e}")
            return []

    def test_model_single_cli(self, model: str, test_name: str, prompt: str, timeout: int = 120) -> Dict:
        """Test single model with single prompt via CLI"""
        start_time = time.time()
        
        try:
            # Create temporary file for the prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(prompt)
                prompt_file = f.name
            
            # Run ollama CLI command
            cmd = ['ollama', 'run', model]
            
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Clean up temp file
            os.unlink(prompt_file)
            
            if result.returncode == 0:
                raw_response = result.stdout.strip()
                latency = time.time() - start_time
                extracted = self.extract_answer(raw_response)
                expected = self.test_definitions[test_name]["expected"]
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "test_name": test_name,
                    "raw_response": raw_response,
                    "extracted_answer": extracted,
                    "expected_answer": expected,
                    "is_correct": self.is_correct_answer(raw_response, expected),
                    "latency": round(latency, 2),
                    "status": "success"
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "test_name": test_name,
                    "raw_response": f"CLI Error: {result.stderr}",
                    "extracted_answer": "ERROR",
                    "expected_answer": self.test_definitions[test_name]["expected"],
                    "is_correct": False,
                    "latency": time.time() - start_time,
                    "status": "cli_error"
                }
                
        except subprocess.TimeoutExpired:
            if 'prompt_file' in locals():
                os.unlink(prompt_file)
            return {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "test_name": test_name,
                "raw_response": "TIMEOUT",
                "extracted_answer": "TIMEOUT",
                "expected_answer": self.test_definitions[test_name]["expected"],
                "is_correct": False,
                "latency": timeout,
                "status": "timeout"
            }
        except Exception as e:
            if 'prompt_file' in locals():
                os.unlink(prompt_file)
            return {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "test_name": test_name,
                "raw_response": f"ERROR: {str(e)}",
                "extracted_answer": "ERROR",
                "expected_answer": self.test_definitions[test_name]["expected"],
                "is_correct": False,
                "latency": time.time() - start_time,
                "status": "error"
            }

    def extract_answer(self, response: str) -> str:
        """Extract bracketed answer from response - improved for reasoning models"""
        # First, look for the last occurrence of [content] pattern
        bracket_matches = re.findall(r'\[([^\[\]]*)\]', response)
        if bracket_matches:
            # Return the last bracketed content (most likely the final answer)
            return f"[{bracket_matches[-1]}]"
        
        # If no brackets, look for common answer patterns at the end
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('<think>') and not line.startswith('</think>'):
                # Check if this line contains a likely answer
                if re.match(r'^[A-Za-z0-9\s]+$', line) and len(line) < 50:
                    return line
        
        # Fallback: return first 50 chars of response
        return response[:50] if len(response) <= 50 else response[:50] + "..."

    def is_correct_answer(self, response: str, expected: str) -> bool:
        """Check if response matches expected answer"""
        extracted = self.extract_answer(response)
        return extracted.lower().strip() == expected.lower().strip()

    def run_cli_comparison_test(self, selected_models: Optional[List[str]] = None) -> Dict:
        """Run CLI tests for comparison with manual and HTTP results"""
        available_models = self.get_available_models()
        
        if selected_models:
            models_to_test = [m for m in selected_models if m in available_models]
        else:
            # Focus on the key models we want to compare
            priority_models = ["deepseek-r1:8b", "qwen3:latest", "codegemma:latest", "gpt-oss:latest"]
            models_to_test = [m for m in priority_models if m in available_models]
            
        print(f"Testing {len(models_to_test)} models via CLI across {len(self.test_definitions)} reasoning tasks...")
        print(f"Models: {models_to_test}")
        
        all_results = []
        
        for model in models_to_test:
            print(f"\nTesting model: {model}")
            
            # Test only a subset first to see how it compares
            for test_name, test_def in list(self.test_definitions.items())[:8]:  # Test first 8 tasks
                print(f"  Running {test_name}...")
                
                result = self.test_model_single_cli(
                    model=model,
                    test_name=test_name,
                    prompt=test_def["prompt"],
                    timeout=180  # Longer timeout for reasoning models
                )
                
                all_results.append(result)
                print(f"    Expected: {result['expected_answer']}")
                print(f"    Got: {result['extracted_answer']}")
                print(f"    Correct: {result['is_correct']}")
                
                # Brief pause between tests
                time.sleep(2)
                
            # Longer pause between models
            time.sleep(5)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "models_tested": len(models_to_test),
            "test_types": len(self.test_definitions),
            "interface": "CLI",
            "results": all_results
        }

    def save_results(self, results: Dict, filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"CLI results saved to {filename}")

    def create_three_way_comparison(self, cli_results: Dict, manual_csv_path: str, http_json_path: str, output_csv_path: str):
        """Create three-way comparison: Manual vs HTTP vs CLI"""
        
        # Load manual results
        manual_results = {}
        with open(manual_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Test name'] and row['Test name'].strip():
                    test_name = row['Test name'].strip().lower().replace(' ', '_')
                    manual_results[test_name] = row

        # Load HTTP results
        http_results = {}
        try:
            with open(http_json_path, 'r') as f:
                http_data = json.load(f)
                for result in http_data['results']:
                    key = f"{result['model']}_{result['test_name']}"
                    http_results[key] = result
        except FileNotFoundError:
            print(f"HTTP results file not found: {http_json_path}")
            http_results = {}

        # Create comparison CSV
        with open(output_csv_path, 'w', newline='') as f:
            fieldnames = ['test_name', 'model', 'manual_result', 'http_result', 'cli_result', 
                         'manual_correct', 'http_correct', 'cli_correct', 'all_match', 'cli_vs_manual_match']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in cli_results['results']:
                test_name = result['test_name']
                model = result['model']
                
                # Find corresponding results
                manual_data = manual_results.get(test_name, {})
                manual_answer = manual_data.get(model, 'NO_MANUAL_DATA')
                
                http_key = f"{model}_{test_name}"
                http_result = http_results.get(http_key, {})
                http_answer = http_result.get('extracted_answer', 'NO_HTTP_DATA')
                
                # Determine correctness
                expected = result['expected_answer']
                manual_correct = self.is_correct_answer(manual_answer, expected) if manual_answer != 'NO_MANUAL_DATA' else None
                http_correct = http_result.get('is_correct', None) if http_answer != 'NO_HTTP_DATA' else None
                cli_correct = result['is_correct']
                
                # Check matches
                all_match = (manual_answer == http_answer == result['extracted_answer']) if manual_answer != 'NO_MANUAL_DATA' and http_answer != 'NO_HTTP_DATA' else False
                cli_vs_manual = (manual_answer == result['extracted_answer']) if manual_answer != 'NO_MANUAL_DATA' else False
                
                writer.writerow({
                    'test_name': test_name,
                    'model': model,
                    'manual_result': manual_answer,
                    'http_result': http_answer,
                    'cli_result': result['extracted_answer'],
                    'manual_correct': manual_correct,
                    'http_correct': http_correct,
                    'cli_correct': cli_correct,
                    'all_match': all_match,
                    'cli_vs_manual_match': cli_vs_manual
                })
        
        print(f"Three-way comparison saved to {output_csv_path}")

if __name__ == "__main__":
    runner = CLIReasoningTestRunner()
    
    # Get available models
    available_models = runner.get_available_models()
    print(f"Available models: {available_models}")
    
    # Run CLI comparison test
    results = runner.run_cli_comparison_test()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"cli_reasoning_results_{timestamp}.json"
    runner.save_results(results, results_file)
    
    # Create three-way comparison
    comparison_file = f"three_way_comparison_{timestamp}.csv"
    runner.create_three_way_comparison(
        results, 
        "llm_manual_test_matrix.csv",
        "comprehensive_reasoning_results_20250919_123203.json",
        comparison_file
    )
    
    print(f"\nCompleted CLI reasoning test!")
    print(f"Results: {results_file}")
    print(f"Three-way comparison: {comparison_file}")