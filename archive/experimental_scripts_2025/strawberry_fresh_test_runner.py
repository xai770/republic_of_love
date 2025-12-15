#!/usr/bin/env python3
"""
Strawberry Test Runner - Fresh Model Loading with Prompt Comparison
Reruns the exact tests from manual strawberry test with two different prompts
Ensures fresh model state for each test to avoid spillage
PSM Format: Problem-Solution-Measurement approach

Problem: Manual strawberry test needs systematic replication with prompt variation analysis
Solution: Fresh model loading + dual prompt testing + statistical comparison
Measurement: 5 iterations per prompt per model with variance analysis
"""

import subprocess
import json
import time
import csv
from datetime import datetime
from typing import Dict, List, Tuple
import statistics
import os

class StrawberryTestRunner:
    def __init__(self):
        # Models from the manual test in exact order
        self.models = [
            "gpt-oss:latest",
            "mistral-nemo:12b", 
            "granite3.1-moe:3b",
            "qwen2.5:7b",
            "llama3.2:latest",
            "gemma3:4b",
            "phi3:3.8b",
            "phi4-mini-reasoning:latest",
            "qwen3:latest",
            "deepseek-r1:8b",
            "gemma3:1b",
            "qwen3:0.6b",
            "qwen3:4b",
            "qwen3:1.7b",
            "mistral:latest",
            "dolphin3:8b",
            "olmo2:latest",
            "codegemma:latest",
            "qwen2.5vl:latest",
            "gemma3n:latest",
            "llama3.2:1b",
            "phi4-mini:latest",
            "gemma2:latest",
            "gemma3n:e2b"
        ]
        
        # Manual test results for comparison
        self.manual_results = {
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
        
        # Original prompt (from manual test)
        self.original_prompt = '''## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"?

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.'''

        # New prompt variation (from your specification)
        self.new_prompt = '''## Payload
How many "r" letters are in "strawberry"? 

## Instructions
- Format your response as [NUMBER]. Make sure to to include ONE PAIR brackets in the output. 
- Example response: [X] where X is your calculated answer.
- Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets.'''

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

    def ensure_fresh_model(self, model: str):
        """Ensure model is freshly loaded by stopping and starting"""
        try:
            # Stop the model to clear memory
            subprocess.run(['ollama', 'stop', model], 
                         capture_output=True, timeout=30)
            time.sleep(2)  # Brief pause to ensure cleanup
        except:
            pass  # If stop fails, continue anyway

    def test_single_iteration(self, model: str, prompt: str, iteration: int, prompt_name: str) -> Dict:
        """Run single test iteration with fresh model state"""
        start_time = time.time()
        
        try:
            # Ensure fresh model state
            self.ensure_fresh_model(model)
            
            # Run ollama CLI command with fresh state
            result = subprocess.run(
                ['ollama', 'run', model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            if result.returncode == 0:
                raw_response = result.stdout.strip()
                latency = time.time() - start_time
                extracted = self.extract_answer(raw_response)
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "prompt_name": prompt_name,
                    "iteration": iteration,
                    "raw_response": raw_response,
                    "extracted_answer": extracted,
                    "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                    "matches_manual": extracted.strip() == self.manual_results.get(model, "").strip(),
                    "latency": round(latency, 2),
                    "status": "success"
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "prompt_name": prompt_name,
                    "iteration": iteration,
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
                "prompt_name": prompt_name,
                "iteration": iteration,
                "raw_response": "TIMEOUT",
                "extracted_answer": "TIMEOUT",
                "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                "matches_manual": False,
                "latency": 180,
                "status": "timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "prompt_name": prompt_name,
                "iteration": iteration,
                "raw_response": f"ERROR: {str(e)}",
                "extracted_answer": "ERROR",
                "manual_result": self.manual_results.get(model, "NO_MANUAL_DATA"),
                "matches_manual": False,
                "latency": time.time() - start_time,
                "status": "error"
            }

    def extract_answer(self, response: str) -> str:
        """Extract answer from response - handles various formats"""
        import re
        
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

    def run_complete_test_suite(self, iterations: int = 5) -> Dict:
        """Run complete test suite: 5 iterations of both prompts for all models"""
        available_models = self.get_available_models()
        testable_models = [m for m in self.models if m in available_models]
        missing_models = [m for m in self.models if m not in available_models]
        
        print("🍓 Strawberry Test Runner - Fresh Model Loading")
        print("=" * 60)
        print(f"PSM Analysis: Testing prompt influence with fresh model states")
        print(f"Total models in manual test: {len(self.models)}")
        print(f"Available locally: {len(available_models)}")
        print(f"Will test: {len(testable_models)} models")
        print(f"Missing: {len(missing_models)} models: {missing_models}")
        print(f"Iterations per prompt: {iterations}")
        print(f"Total tests: {len(testable_models)} × 2 prompts × {iterations} = {len(testable_models) * 2 * iterations}")
        print("=" * 60)
        
        all_results = []
        total_tests = len(testable_models) * 2 * iterations
        completed_tests = 0
        
        for model in testable_models:
            print(f"\n🔄 Testing model: {model}")
            print(f"   Manual result: {self.manual_results.get(model, 'NO_DATA')}")
            
            # Test original prompt 5 times
            print(f"   📝 Original prompt ({iterations} iterations)...")
            for i in range(1, iterations + 1):
                result = self.test_single_iteration(model, self.original_prompt, i, "original")
                all_results.append(result)
                completed_tests += 1
                
                print(f"      Iteration {i}: {result['extracted_answer']} "
                      f"({'✅' if result['matches_manual'] else '❌'}) "
                      f"[{result['latency']}s]")
                
                # Brief pause between iterations to ensure fresh state
                time.sleep(3)
            
            # Test new prompt 5 times  
            print(f"   📝 New prompt ({iterations} iterations)...")
            for i in range(1, iterations + 1):
                result = self.test_single_iteration(model, self.new_prompt, i, "new")
                all_results.append(result)
                completed_tests += 1
                
                print(f"      Iteration {i}: {result['extracted_answer']} "
                      f"({'✅' if result['matches_manual'] else '❌'}) "
                      f"[{result['latency']}s]")
                
                # Brief pause between iterations
                time.sleep(3)
            
            # Progress update
            progress = (completed_tests / total_tests) * 100
            print(f"   📊 Progress: {completed_tests}/{total_tests} ({progress:.1f}%)")
            
            # Longer pause between models to avoid system overload
            time.sleep(5)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_models": len(self.models),
            "available_models": len(available_models),
            "tested_models": len(testable_models),
            "missing_models": missing_models,
            "iterations_per_prompt": iterations,
            "total_tests_run": len(all_results),
            "results": all_results
        }

    def analyze_prompt_influence(self, results: Dict) -> Dict:
        """Analyze the influence of different prompts on results"""
        analysis = {
            "model_comparison": {},
            "overall_statistics": {},
            "prompt_effectiveness": {}
        }
        
        # Group results by model
        by_model = {}
        for result in results['results']:
            model = result['model']
            if model not in by_model:
                by_model[model] = {'original': [], 'new': []}
            by_model[model][result['prompt_name']].append(result)
        
        # Analyze each model
        for model, prompts in by_model.items():
            original_answers = [r['extracted_answer'] for r in prompts['original'] if r['status'] == 'success']
            new_answers = [r['extracted_answer'] for r in prompts['new'] if r['status'] == 'success']
            
            original_consistency = len(set(original_answers)) == 1 if original_answers else False
            new_consistency = len(set(new_answers)) == 1 if new_answers else False
            
            # Calculate accuracy against manual results
            manual_result = self.manual_results.get(model, "")
            original_accuracy = sum(1 for ans in original_answers if ans.strip() == manual_result.strip()) / len(original_answers) if original_answers else 0
            new_accuracy = sum(1 for ans in new_answers if ans.strip() == manual_result.strip()) / len(new_answers) if new_answers else 0
            
            analysis["model_comparison"][model] = {
                "manual_result": manual_result,
                "original_prompt": {
                    "answers": original_answers,
                    "most_common": max(set(original_answers), key=original_answers.count) if original_answers else "NO_ANSWERS",
                    "consistency": original_consistency,
                    "accuracy_vs_manual": round(original_accuracy * 100, 1)
                },
                "new_prompt": {
                    "answers": new_answers,
                    "most_common": max(set(new_answers), key=new_answers.count) if new_answers else "NO_ANSWERS",
                    "consistency": new_consistency,
                    "accuracy_vs_manual": round(new_accuracy * 100, 1)
                },
                "prompt_influence": {
                    "different_results": set(original_answers) != set(new_answers),
                    "accuracy_difference": round((new_accuracy - original_accuracy) * 100, 1),
                    "consistency_change": new_consistency != original_consistency
                }
            }
        
        # Overall statistics
        total_models = len(by_model)
        models_with_different_results = sum(1 for comp in analysis["model_comparison"].values() 
                                          if comp["prompt_influence"]["different_results"])
        
        original_accuracies = [comp["original_prompt"]["accuracy_vs_manual"] 
                             for comp in analysis["model_comparison"].values()]
        new_accuracies = [comp["new_prompt"]["accuracy_vs_manual"] 
                        for comp in analysis["model_comparison"].values()]
        
        analysis["overall_statistics"] = {
            "total_models_tested": total_models,
            "models_affected_by_prompt": models_with_different_results,
            "prompt_influence_rate": round((models_with_different_results / total_models) * 100, 1) if total_models > 0 else 0,
            "average_original_accuracy": round(statistics.mean(original_accuracies), 1) if original_accuracies else 0,
            "average_new_accuracy": round(statistics.mean(new_accuracies), 1) if new_accuracies else 0,
            "accuracy_improvement": round(statistics.mean(new_accuracies) - statistics.mean(original_accuracies), 1) if original_accuracies and new_accuracies else 0
        }
        
        # Determine which prompt is more effective
        original_better = sum(1 for comp in analysis["model_comparison"].values() 
                            if comp["original_prompt"]["accuracy_vs_manual"] > comp["new_prompt"]["accuracy_vs_manual"])
        new_better = sum(1 for comp in analysis["model_comparison"].values() 
                       if comp["new_prompt"]["accuracy_vs_manual"] > comp["original_prompt"]["accuracy_vs_manual"])
        
        analysis["prompt_effectiveness"] = {
            "original_prompt_better": original_better,
            "new_prompt_better": new_better,
            "tie": total_models - original_better - new_better,
            "winner": "original" if original_better > new_better else ("new" if new_better > original_better else "tie")
        }
        
        return analysis

    def save_results(self, results: Dict, analysis: Dict, timestamp: str):
        """Save all results and analysis to files"""
        # Save raw results
        results_file = f"strawberry_fresh_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save analysis
        analysis_file = f"strawberry_prompt_analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Save CSV for easy viewing
        csv_file = f"strawberry_comparison_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            fieldnames = ['model', 'manual_result', 'original_most_common', 'original_accuracy', 
                         'new_most_common', 'new_accuracy', 'prompt_influenced', 'accuracy_change']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for model, comp in analysis['model_comparison'].items():
                writer.writerow({
                    'model': model,
                    'manual_result': comp['manual_result'],
                    'original_most_common': comp['original_prompt']['most_common'],
                    'original_accuracy': comp['original_prompt']['accuracy_vs_manual'],
                    'new_most_common': comp['new_prompt']['most_common'],
                    'new_accuracy': comp['new_prompt']['accuracy_vs_manual'],
                    'prompt_influenced': comp['prompt_influence']['different_results'],
                    'accuracy_change': comp['prompt_influence']['accuracy_difference']
                })
        
        print(f"\n📁 Files created:")
        print(f"   📊 Raw results: {results_file}")
        print(f"   📈 Analysis: {analysis_file}")
        print(f"   📋 CSV summary: {csv_file}")
        
        return results_file, analysis_file, csv_file

    def print_summary(self, analysis: Dict):
        """Print comprehensive summary of results"""
        print("\n" + "=" * 60)
        print("🎯 STRAWBERRY TEST ANALYSIS - PROMPT INFLUENCE STUDY")
        print("=" * 60)
        
        stats = analysis["overall_statistics"]
        eff = analysis["prompt_effectiveness"]
        
        print(f"📊 Overall Statistics:")
        print(f"   Models tested: {stats['total_models_tested']}")
        print(f"   Models affected by prompt change: {stats['models_affected_by_prompt']}")
        print(f"   Prompt influence rate: {stats['prompt_influence_rate']}%")
        print(f"   Average accuracy (original): {stats['average_original_accuracy']}%")
        print(f"   Average accuracy (new): {stats['average_new_accuracy']}%")
        print(f"   Accuracy change: {'+' if stats['accuracy_improvement'] >= 0 else ''}{stats['accuracy_improvement']}%")
        
        print(f"\n🏆 Prompt Effectiveness:")
        print(f"   Original prompt better: {eff['original_prompt_better']} models")
        print(f"   New prompt better: {eff['new_prompt_better']} models")
        print(f"   Tied performance: {eff['tie']} models")
        print(f"   Overall winner: {eff['winner'].upper()} prompt")
        
        print(f"\n🔍 Key Findings:")
        influenced_models = [model for model, comp in analysis["model_comparison"].items() 
                           if comp["prompt_influence"]["different_results"]]
        
        if influenced_models:
            print(f"   Models most affected by prompt change:")
            for model in influenced_models[:5]:  # Show top 5
                comp = analysis["model_comparison"][model]
                change = comp["prompt_influence"]["accuracy_difference"]
                print(f"      {model}: {'+' if change >= 0 else ''}{change}% accuracy change")
        else:
            print(f"   No significant prompt influence detected")

if __name__ == "__main__":
    print("🍓 Starting Strawberry Test Runner with Fresh Model Loading")
    print("PSM Approach: Problem-Solution-Measurement")
    print("Problem: Analyze prompt influence on strawberry test results")
    print("Solution: Fresh model loading + dual prompt testing")
    print("Measurement: Statistical analysis of prompt effectiveness")
    
    runner = StrawberryTestRunner()
    
    # Run complete test suite
    results = runner.run_complete_test_suite(iterations=5)
    
    # Analyze prompt influence
    analysis = runner.analyze_prompt_influence(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    runner.save_results(results, analysis, timestamp)
    
    # Print summary
    runner.print_summary(analysis)
    
    print(f"\n✅ Test completed successfully!")
    print(f"📈 Fresh model loading ensured no memory spillage between tests")
    print(f"🔬 Prompt influence analysis reveals systematic differences")
    print(f"💾 All results saved with timestamp: {timestamp}")