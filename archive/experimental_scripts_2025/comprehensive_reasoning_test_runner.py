#!/usr/bin/env python3
"""
Comprehensive LLM Reasoning Test Runner
Systematically tests all 17 reasoning tasks from the manual test matrix
Compares manual vs scripted results to identify performance differences
"""

import requests
import json
import time
import csv
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

class ReasoningTestRunner:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
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
            "falling_balls": {
                "prompt": '''## Processing Instructions
Reply [Yes] or [No]. 

## Processing Payload
If you drop a red ball and a blue ball at the same time, will the red ball hit the ground first?

## QA Check
Submit ONLY the required response in brackets.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[No]"
            },
            "elephant_fridge": {
                "prompt": '''## Processing Instructions
Format your response as [Yes] or [No]. Make sure to to include the brackets in the output.
Example: [Yes]
Example: [No]

## Processing Payload
Can an elephant fit into a standard fridge?

## QA Check
Submit ONLY the required response in square brackets.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[No]"
            },
            "tallest_person": {
                "prompt": '''## Processing Instructions
Format your response as [ ]. Make sure to to include the brackets in the output.
Example: [Jack]
Example: [Mary]

## Processing Payload
John is taller than Dave, Dave is taller than Alex. Who is the tallest?

## QA Check
Submit ONLY the required response.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[John]"
            },
            "coin_puzzle": {
                "prompt": '''## Processing Instructions
DO NOT RETURN COMMENTARY!
Format your response as [NUMBER] where NUMBER is a single digit.

## Processing Payload
Two coins total 30 cents, and one is not a nickel. How many nickels are there?

## QA Check
Submit ONLY the required response. Do not include any explanatory text.''',
                "expected": "[1]"
            },
            "word_type": {
                "prompt": '''## Processing Instructions
DO NOT RETURN COMMENTARY!
Format your response as [Yes] or [No]. Make sure to to include the brackets in the output.
Example: [Yes]
Example: [No]

## Processing Payload
Is "set" a noun? Reply ONLY Yes or No. 

## QA Check
Submit ONLY the required response.''',
                "expected": "[Yes]"
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
            "train_distance": {
                "prompt": '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.
Example: [X] where X is your calculated answer.

## Processing Payload
A train travels 60 mph for 2 hours. How many miles does it travel?

## QA Check
Submit ONLY the required response.''',
                "expected": "[120]"
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
            "backward_phrase": {
                "prompt": '''## Processing Instructions
Format your response as [string]. Make sure to to include the brackets in the output.

## Processing Payload
Write "capitalization" backwards. 

## QA Check
Submit ONLY the required response. Do not add spaces.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[noitazilatipac]"
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
            "youngest": {
                "prompt": '''## Processing Instructions
Format your response as [ ]. Make sure to to include the brackets in the output.

## Processing Payload
A is older than B, B is older than C, C is older than D. Who is the youngest?

## QA Check
Submit ONLY the required response in bracket!  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[D]"
            },
            "days": {
                "prompt": '''## Processing Instructions
Format your response as [day of week]. Make sure to to include the brackets in the output.

## Processing Payload
What day of the week follows Tuesday?

## QA Check
Submit ONLY the required response.
 Reply ONLY the correct response string. Enclose your reply in square brackets.  Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.''',
                "expected": "[Wednesday]"
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
        """Get list of available models from Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data["models"]]
        except Exception as e:
            print(f"Error getting models: {e}")
            return []

    def test_model_single(self, model: str, test_name: str, prompt: str, timeout: int = 60) -> Dict:
        """Test single model with single prompt via HTTP API"""
        start_time = time.time()
        
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 100
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result["message"]["content"].strip()
                latency = time.time() - start_time
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "test_name": test_name,
                    "raw_response": raw_response,
                    "extracted_answer": self.extract_answer(raw_response),
                    "expected_answer": self.test_definitions[test_name]["expected"],
                    "is_correct": self.is_correct_answer(raw_response, self.test_definitions[test_name]["expected"]),
                    "latency": round(latency, 2),
                    "status": "success"
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "test_name": test_name,
                    "raw_response": f"HTTP {response.status_code}: {response.text}",
                    "extracted_answer": "ERROR",
                    "expected_answer": self.test_definitions[test_name]["expected"],
                    "is_correct": False,
                    "latency": time.time() - start_time,
                    "status": "http_error"
                }
                
        except requests.exceptions.Timeout:
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
        """Extract bracketed answer from response"""
        # Look for [content] pattern
        bracket_match = re.search(r'\[([^\[\]]*)\]', response)
        if bracket_match:
            return f"[{bracket_match.group(1)}]"
        
        # Fallback: return first 50 chars of response
        return response[:50] if len(response) <= 50 else response[:50] + "..."

    def is_correct_answer(self, response: str, expected: str) -> bool:
        """Check if response matches expected answer"""
        extracted = self.extract_answer(response)
        return extracted.lower() == expected.lower()

    def run_comprehensive_test(self, selected_models: Optional[List[str]] = None) -> Dict:
        """Run all tests across all models"""
        available_models = self.get_available_models()
        
        if selected_models:
            models_to_test = [m for m in selected_models if m in available_models]
        else:
            models_to_test = available_models
            
        print(f"Testing {len(models_to_test)} models across {len(self.test_definitions)} reasoning tasks...")
        
        all_results = []
        
        for model in models_to_test:
            print(f"\nTesting model: {model}")
            
            for test_name, test_def in self.test_definitions.items():
                print(f"  Running {test_name}...")
                
                result = self.test_model_single(
                    model=model,
                    test_name=test_name,
                    prompt=test_def["prompt"],
                    timeout=120
                )
                
                all_results.append(result)
                
                # Brief pause between tests
                time.sleep(1)
                
            # Longer pause between models to avoid overloading
            time.sleep(3)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "models_tested": len(models_to_test),
            "test_types": len(self.test_definitions),
            "results": all_results
        }

    def save_results(self, results: Dict, filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {filename}")

    def create_comparison_matrix(self, results: Dict, manual_csv_path: str, output_csv_path: str):
        """Create comparison matrix between manual and scripted results"""
        # Load manual results
        manual_results = {}
        with open(manual_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Test name']:  # Skip empty rows
                    manual_results[row['Test name'].lower()] = row
        
        # Create comparison CSV
        with open(output_csv_path, 'w', newline='') as f:
            fieldnames = ['test_name', 'model', 'manual_result', 'scripted_result', 'manual_correct', 'scripted_correct', 'match']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results['results']:
                test_name = result['test_name']
                model = result['model']
                
                # Find corresponding manual result
                manual_data = manual_results.get(test_name.lower(), {})
                manual_answer = manual_data.get(model, 'NO_MANUAL_DATA')
                
                # Determine if manual answer was correct
                expected = result['expected_answer']
                manual_correct = self.is_correct_answer(manual_answer, expected) if manual_answer != 'NO_MANUAL_DATA' else None
                
                writer.writerow({
                    'test_name': test_name,
                    'model': model,
                    'manual_result': manual_answer,
                    'scripted_result': result['extracted_answer'],
                    'manual_correct': manual_correct,
                    'scripted_correct': result['is_correct'],
                    'match': manual_answer == result['extracted_answer'] if manual_answer != 'NO_MANUAL_DATA' else False
                })
        
        print(f"Comparison matrix saved to {output_csv_path}")

if __name__ == "__main__":
    runner = ReasoningTestRunner()
    
    # Get available models
    available_models = runner.get_available_models()
    print(f"Available models: {available_models[:5]}...")  # Show first 5
    
    # For initial test, let's focus on the models we know work well
    priority_models = ["deepseek-r1:8b", "qwen3:latest", "codegemma:latest", "gpt-oss:latest"]
    test_models = [m for m in priority_models if m in available_models]
    
    print(f"Testing priority models: {test_models}")
    
    # Run comprehensive test
    results = runner.run_comprehensive_test(selected_models=test_models)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"comprehensive_reasoning_results_{timestamp}.json"
    runner.save_results(results, results_file)
    
    # Create comparison matrix
    comparison_file = f"manual_vs_scripted_comparison_{timestamp}.csv"
    runner.create_comparison_matrix(results, "llm_manual_test_matrix.csv", comparison_file)
    
    print(f"\nCompleted comprehensive reasoning test!")
    print(f"Results: {results_file}")
    print(f"Comparison: {comparison_file}")