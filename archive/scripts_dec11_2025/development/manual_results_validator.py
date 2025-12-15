#!/usr/bin/env python3
"""
Complete Manual Results Validation Script
Tests all 25 models from the manual strawberry test to validate CLI scripted results match manual results
"""

import subprocess
import json
import time
import csv
from datetime import datetime
from typing import Dict, List, Optional
import re

class ManualResultsValidator:
    def __init__(self):
        self.manual_results = self._load_manual_results()
        self.test_prompt = self._get_test_prompt()
        
    def _load_manual_results(self) -> Dict[str, str]:
        """Load the exact manual results from the markdown file"""
        return {
            "gpt-oss:latest": "[3]",
            "mistral-nemo:12b": "[3]",
            "granite3.1-moe:3b": "[6]", 
            "qwen2.5:7b": "[3]",
            "llama3.2:latest": "[3]",
            "gemma3:4b": "[3]",
            "phi3:3.8b": "[3]",
            "phi4-mini-reasoning:latest": "[3]",
            "qwen3:latest": "[3]",
            "deepseek-r1:8b": "[3]",
            "gemma3:1b": "[2]",
            "qwen3:0.6b": "[2]",
            "qwen3:4b": "[3]",
            "qwen3:1.7b": "[3]",
            "mistral:latest": "[3]",
            "dolphin3:8b": "[5]",
            "olmo2:latest": "[4]",
            "codegemma:latest": "[5]",
            "qwen2.5vl:latest": '[strawberry contains 2 "r" letters]',
            "gemma3n:latest": "[ 3 ]",
            "llama3.2:1b": "[7]",
            "phi4-mini:latest": "[3]",
            "gemma2:latest": "[3]",
            "gemma3n:e2b": "[3]"
        }
    
    def _get_test_prompt(self) -> str:
        """The exact prompt from the manual test"""
        return '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"?

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.'''

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

    def test_single_model(self, model: str, timeout: int = 180) -> Dict:
        """Test single model via CLI with proper timeout for reasoning models"""
        start_time = time.time()
        
        try:
            # Run ollama CLI command
            result = subprocess.run(
                ['ollama', 'run', model],
                input=self.test_prompt,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                raw_response = result.stdout.strip()
                latency = time.time() - start_time
                extracted = self.extract_answer(raw_response)
                manual_expected = self.manual_results.get(model, "NO_MANUAL_DATA")
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "raw_response": raw_response,
                    "extracted_answer": extracted,
                    "manual_result": manual_expected,
                    "matches_manual": extracted.strip() == manual_expected.strip(),
                    "latency": round(latency, 2),
                    "status": "success"
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "raw_response": f"CLI Error: {result.stderr}",
                    "extracted_answer": "ERROR",
                    "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                    "matches_manual": False,
                    "latency": time.time() - start_time,
                    "status": "cli_error"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "raw_response": "TIMEOUT",
                "extracted_answer": "TIMEOUT",
                "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                "matches_manual": False,
                "latency": timeout,
                "status": "timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "raw_response": f"ERROR: {str(e)}",
                "extracted_answer": "ERROR",
                "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                "matches_manual": False,
                "latency": time.time() - start_time,
                "status": "error"
            }

    def extract_answer(self, response: str) -> str:
        """Extract answer from response - handles various formats"""
        # Look for [content] pattern - find the last one (most likely final answer)
        bracket_matches = re.findall(r'\[([^\[\]]*)\]', response)
        if bracket_matches:
            return f"[{bracket_matches[-1]}]"
        
        # Handle special cases like qwen2.5vl format
        if "strawberry contains" in response.lower():
            return response.strip()
            
        # Look for standalone numbers or words at the end of response
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('<think>') and not line.startswith('</think>'):
                # Check for simple answers
                if re.match(r'^[0-9]+$', line):
                    return f"[{line}]"
                elif len(line) < 100 and not line.startswith('##'):
                    return line
        
        # Fallback: return truncated response
        return response[:50] if len(response) <= 50 else response[:50] + "..."

    def run_complete_validation(self) -> Dict:
        """Run validation test across all models from manual results"""
        available_models = self.get_available_models()
        manual_models = list(self.manual_results.keys())
        
        # Find models that are both in manual results and available locally
        testable_models = [m for m in manual_models if m in available_models]
        missing_models = [m for m in manual_models if m not in available_models]
        
        print(f"Manual test had {len(manual_models)} models")
        print(f"Available locally: {len(available_models)} models")
        print(f"Can test: {len(testable_models)} models")
        print(f"Missing: {len(missing_models)} models: {missing_models}")
        print(f"\nTesting models: {testable_models}")
        
        all_results = []
        matches = 0
        total_tested = 0
        
        for model in testable_models:
            print(f"\nTesting {model}...")
            print(f"  Manual result: {self.manual_results[model]}")
            
            result = self.test_single_model(model, timeout=240)  # 4 minutes for reasoning models
            
            all_results.append(result)
            
            print(f"  CLI result: {result['extracted_answer']}")
            print(f"  Match: {'✅' if result['matches_manual'] else '❌'}")
            print(f"  Status: {result['status']}")
            print(f"  Latency: {result['latency']}s")
            
            if result['matches_manual']:
                matches += 1
            total_tested += 1
            
            # Brief pause between models to avoid system overload
            time.sleep(3)
        
        match_rate = (matches / total_tested * 100) if total_tested > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_manual_models": len(manual_models),
            "available_models": len(available_models),
            "testable_models": len(testable_models),
            "missing_models": missing_models,
            "total_tested": total_tested,
            "matches": matches,
            "match_rate_percent": round(match_rate, 1),
            "results": all_results
        }

    def save_results(self, results: Dict, filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {filename}")

    def create_comparison_report(self, results: Dict, output_file: str):
        """Create detailed comparison report CSV"""
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['model', 'manual_result', 'cli_result', 'matches', 'status', 'latency']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results['results']:
                writer.writerow({
                    'model': result['model'],
                    'manual_result': result['manual_result'],
                    'cli_result': result['extracted_answer'],
                    'matches': result['matches_manual'],
                    'status': result['status'],
                    'latency': result['latency']
                })
        
        print(f"Comparison report saved to {output_file}")

if __name__ == "__main__":
    validator = ManualResultsValidator()
    
    print("🎯 Manual Results Validation Script")
    print("Testing CLI scripted results against manual strawberry test results")
    print("=" * 60)
    
    # Run complete validation
    results = validator.run_complete_validation()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"manual_validation_results_{timestamp}.json"
    validator.save_results(results, results_file)
    
    # Create comparison report
    report_file = f"manual_vs_cli_comparison_{timestamp}.csv"
    validator.create_comparison_report(results, report_file)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total models in manual test: {results['total_manual_models']}")
    print(f"Models available locally: {results['available_models']}")
    print(f"Models tested: {results['total_tested']}")
    print(f"Exact matches: {results['matches']}")
    print(f"Match rate: {results['match_rate_percent']}%")
    print(f"\nMissing models: {results['missing_models']}")
    print(f"\nFiles created:")
    print(f"  - {results_file}")
    print(f"  - {report_file}")
    
    if results['match_rate_percent'] >= 80:
        print(f"\n✅ SUCCESS: {results['match_rate_percent']}% match rate - CLI testing successfully replicates manual results!")
    else:
        print(f"\n⚠️  PARTIAL: {results['match_rate_percent']}% match rate - Some differences found, needs investigation")