#!/usr/bin/env python3
"""
Strawberry Test Runner - Systematic LLM Letter Counting Validation
================================================================

This script systematically tests multiple LLM models on the "strawberry" letter counting task
to evaluate their ability to perform basic character analysis. Key features:

1. Fresh model loading for each test (no memory spillage)
2. Two prompt format variations tested
3. 5 iterations per prompt per model for statistical reliability
4. Comprehensive result logging and analysis
5. Automatic model discovery via ollama

Author: Arden the Builder
Date: September 19, 2025
"""

import json
import subprocess
import time
import csv
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import os
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('strawberry_test_results.log'),
        logging.StreamHandler()
    ]
)

class StrawberryTestRunner:
    def __init__(self):
        self.models = []
        self.results = []
        self.correct_answer = "3"  # Correct number of 'r' letters in "strawberry"
        
        # Define prompt variations
        self.prompt_original = {
            "name": "original",
            "content": """## Processing Instructions  
Format your response as [NUMBER]. Make sure to to include the brackets in the output.  
Example: [X] where X is your calculated answer.  

## Processing Payload  
How many "r" letters are in "strawberry"?  

## QA Check  
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
        }
        
        self.prompt_simplified = {
            "name": "simplified", 
            "content": """## Payload
How many "r" letters are in "strawberry"? 

## Instructions
- Format your response as [NUMBER]. Make sure to to include ONE PAIR brackets in the output. 
- Example response: [X] where X is your calculated answer.
- Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
        }
        
        self.prompts = [self.prompt_original, self.prompt_simplified]
        
        # Create output directory
        self.output_dir = "strawberry_test_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def discover_models(self) -> List[str]:
        """Discover available ollama models"""
        logging.info("Discovering available ollama models...")
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
            models = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    if model_name != "NAME":  # Skip if somehow header got through
                        models.append(model_name)
            
            logging.info(f"Discovered {len(models)} models: {', '.join(models)}")
            return models
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to discover models: {e}")
            return []
    
    def ensure_fresh_model(self, model_name: str) -> bool:
        """Ensure model is freshly loaded by stopping and starting ollama service"""
        logging.info(f"Ensuring fresh model state for {model_name}...")
        try:
            # Stop ollama to clear memory
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True)
            time.sleep(2)  # Wait for cleanup
            
            # Start ollama service
            subprocess.run(['ollama', 'serve'], capture_output=True, timeout=5)
            time.sleep(3)  # Wait for service to be ready
            
            # Load the specific model fresh
            subprocess.run(['ollama', 'run', model_name, '--'], input="test", 
                         capture_output=True, text=True, timeout=300)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logging.warning(f"Model refresh failed for {model_name}: {e}")
            return False
    
    def run_single_test(self, model_name: str, prompt: Dict[str, str], iteration: int) -> Dict:
        """Run a single strawberry test"""
        logging.info(f"Running {prompt['name']} test iteration {iteration} on {model_name}")
        
        start_time = time.time()
        
        try:
            # Run the test
            cmd = ['ollama', 'run', model_name]
            result = subprocess.run(
                cmd, 
                input=prompt['content'], 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Extract answer and check correctness
                is_correct, extracted_answer = self.evaluate_response(response)
                
                test_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt['name'],
                    'iteration': iteration,
                    'response': response,
                    'extracted_answer': extracted_answer,
                    'is_correct': is_correct,
                    'latency': round(latency, 2),
                    'status': 'completed'
                }
                
                logging.info(f"✓ {model_name} {prompt['name']} #{iteration}: {extracted_answer} ({'✓' if is_correct else '✗'}) - {latency:.2f}s")
                
                # Save result immediately
                self.save_incremental_result(test_result)
                return test_result
                
            else:
                error_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt['name'],
                    'iteration': iteration,
                    'response': result.stderr.strip(),
                    'extracted_answer': None,
                    'is_correct': False,
                    'latency': round(time.time() - start_time, 2),
                    'status': 'error'
                }
                logging.error(f"✗ {model_name} {prompt['name']} #{iteration}: ERROR - {result.stderr.strip()}")
                
                # Save error result immediately  
                self.save_incremental_result(error_result)
                return error_result
                
        except subprocess.TimeoutExpired:
            timeout_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt['name'],
                'iteration': iteration,
                'response': 'TIMEOUT',
                'extracted_answer': None,
                'is_correct': False,
                'latency': 300.0,
                'status': 'timeout'
            }
            logging.error(f"⏰ {model_name} {prompt['name']} #{iteration}: TIMEOUT")
            
            # Save timeout result immediately
            self.save_incremental_result(timeout_result)
            return timeout_result
            
        except Exception as e:
            exception_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt['name'],
                'iteration': iteration,
                'response': str(e),
                'extracted_answer': None,
                'is_correct': False,
                'latency': round(time.time() - start_time, 2),
                'status': 'exception'
            }
            logging.error(f"💥 {model_name} {prompt['name']} #{iteration}: EXCEPTION - {str(e)}")
            
            # Save exception result immediately
            self.save_incremental_result(exception_result)
            return exception_result
    
    def run_single_test_no_refresh(self, model_name: str, prompt: Dict[str, str], iteration: int) -> Dict:
        """Run a single strawberry test without model refresh (using model cycling)"""
        
        start_time = time.time()
        
        try:
            # Run the test directly - model cycling ensures fresh state
            cmd = ['ollama', 'run', model_name]
            result = subprocess.run(
                cmd, 
                input=prompt['content'], 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                
                # Extract answer and check correctness
                is_correct, extracted_answer = self.evaluate_response(response)
                
                test_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt['name'],
                    'iteration': iteration,
                    'response': response,
                    'extracted_answer': extracted_answer,
                    'is_correct': is_correct,
                    'latency': round(latency, 2),
                    'status': 'completed'
                }
                
                logging.info(f"✓ {model_name} {prompt['name']} #{iteration}: {extracted_answer} ({'✓' if is_correct else '✗'}) - {latency:.2f}s")
                
                # Save result immediately
                self.save_incremental_result(test_result)
                return test_result
                
            else:
                error_result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model_name,
                    'prompt_type': prompt['name'],
                    'iteration': iteration,
                    'response': result.stderr.strip(),
                    'extracted_answer': None,
                    'is_correct': False,
                    'latency': round(time.time() - start_time, 2),
                    'status': 'error'
                }
                logging.error(f"✗ {model_name} {prompt['name']} #{iteration}: ERROR - {result.stderr.strip()}")
                
                # Save error result immediately  
                self.save_incremental_result(error_result)
                return error_result
                
        except subprocess.TimeoutExpired:
            timeout_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt['name'],
                'iteration': iteration,
                'response': 'TIMEOUT',
                'extracted_answer': None,
                'is_correct': False,
                'latency': 300.0,
                'status': 'timeout'
            }
            logging.error(f"⏰ {model_name} {prompt['name']} #{iteration}: TIMEOUT")
            
            # Save timeout result immediately
            self.save_incremental_result(timeout_result)
            return timeout_result
            
        except Exception as e:
            exception_result = {
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'prompt_type': prompt['name'],
                'iteration': iteration,
                'response': str(e),
                'extracted_answer': None,
                'is_correct': False,
                'latency': round(time.time() - start_time, 2),
                'status': 'exception'
            }
            logging.error(f"💥 {model_name} {prompt['name']} #{iteration}: EXCEPTION - {str(e)}")
            
            # Save exception result immediately
            self.save_incremental_result(exception_result)
            return exception_result
    
    def evaluate_response(self, response: str) -> Tuple[bool, Optional[str]]:
        """Extract and evaluate the answer from model response"""
        import re
        
        # Try to extract number in brackets
        bracket_match = re.search(r'\[(\d+)\]', response)
        if bracket_match:
            extracted_answer = bracket_match.group(1)
            is_correct = extracted_answer == self.correct_answer
            return is_correct, extracted_answer
        
        # Try to extract standalone number
        number_match = re.search(r'\b(\d+)\b', response)
        if number_match:
            extracted_answer = number_match.group(1)
            is_correct = extracted_answer == self.correct_answer
            return is_correct, f"{extracted_answer} (no brackets)"
        
        # No number found
        return False, "NO_NUMBER_FOUND"
    
    def save_incremental_result(self, result):
        """Save individual result immediately to incremental files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to incremental JSON file (append mode)
        incremental_json = f"{self.output_dir}/strawberry_results_incremental.json"
        
        # Read existing results if file exists
        existing_results = []
        try:
            if os.path.exists(incremental_json):
                with open(incremental_json, 'r') as f:
                    existing_results = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_results = []
        
        # Add new result
        existing_results.append(result)
        
        # Write back all results
        with open(incremental_json, 'w') as f:
            json.dump(existing_results, f, indent=2)
        
        # Also append to CSV (create header if new file)
        incremental_csv = f"{self.output_dir}/strawberry_results_incremental.csv" 
        
        file_exists = os.path.exists(incremental_csv)
        with open(incremental_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=result.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(result)
    
    def run_model_tests(self, model_name: str, iterations: int = 5):
        """Run all test variations for a single model"""
        logging.info(f"\n🚀 Starting tests for {model_name} ({iterations} iterations per prompt)")
        
        model_results = []
        
        for prompt in self.prompts:
            logging.info(f"\n📝 Testing {prompt['name']} prompt format...")
            
            for iteration in range(1, iterations + 1):
                # Ensure fresh model state
                if not self.ensure_fresh_model(model_name):
                    logging.warning(f"Could not refresh model {model_name}, continuing anyway...")
                
                # Run the test
                result = self.run_single_test(model_name, prompt, iteration)
                model_results.append(result)
                self.results.append(result)
                
                # Brief pause between tests
                time.sleep(1)
        
        return model_results
    
    def generate_model_summary(self, model_name: str) -> Dict:
        """Generate summary statistics for a model"""
        model_results = [r for r in self.results if r['model'] == model_name]
        
        if not model_results:
            return {}
        
        summary = {
            'model': model_name,
            'total_tests': len(model_results),
            'completed_tests': len([r for r in model_results if r['status'] == 'completed']),
            'correct_answers': len([r for r in model_results if r['is_correct']]),
            'success_rate': 0,
            'avg_latency': 0,
            'prompt_performance': {}
        }
        
        if summary['total_tests'] > 0:
            summary['success_rate'] = round((summary['correct_answers'] / summary['total_tests']) * 100, 1)
        
        completed_results = [r for r in model_results if r['status'] == 'completed']
        if completed_results:
            summary['avg_latency'] = round(statistics.mean([r['latency'] for r in completed_results]), 2)
        
        # Per-prompt analysis
        for prompt in self.prompts:
            prompt_results = [r for r in model_results if r['prompt_type'] == prompt['name']]
            if prompt_results:
                correct_count = len([r for r in prompt_results if r['is_correct']])
                summary['prompt_performance'][prompt['name']] = {
                    'total': len(prompt_results),
                    'correct': correct_count,
                    'success_rate': round((correct_count / len(prompt_results)) * 100, 1)
                }
        
        return summary
    
    def save_results(self):
        """Save all results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw results as JSON
        json_file = f"{self.output_dir}/strawberry_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logging.info(f"Raw results saved to {json_file}")
        
        # Save results as CSV
        csv_file = f"{self.output_dir}/strawberry_results_{timestamp}.csv"
        if self.results:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
            logging.info(f"CSV results saved to {csv_file}")
        
        # Generate summary report
        self.generate_summary_report(timestamp)
    
    def generate_summary_report(self, timestamp: str):
        """Generate a comprehensive summary report"""
        report_file = f"{self.output_dir}/strawberry_summary_{timestamp}.md"
        
        # Calculate overall statistics
        total_tests = len(self.results)
        completed_tests = len([r for r in self.results if r['status'] == 'completed'])
        correct_answers = len([r for r in self.results if r['is_correct']])
        
        with open(report_file, 'w') as f:
            f.write(f"# Strawberry Test Results Summary\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Overall Statistics\n")
            f.write(f"- **Total Tests:** {total_tests}\n")
            f.write(f"- **Completed Tests:** {completed_tests}\n")
            f.write(f"- **Correct Answers:** {correct_answers}\n")
            f.write(f"- **Overall Success Rate:** {round((correct_answers/total_tests)*100, 1) if total_tests > 0 else 0}%\n\n")
            
            f.write(f"## Model Performance Summary\n\n")
            f.write(f"| Model | Total Tests | Correct | Success Rate | Avg Latency | Original Prompt | Simplified Prompt |\n")
            f.write(f"|-------|-------------|---------|--------------|-------------|-----------------|-------------------|\n")
            
            # Generate model summaries
            tested_models = list(set([r['model'] for r in self.results]))
            for model in sorted(tested_models):
                summary = self.generate_model_summary(model)
                if summary:
                    orig_perf = summary['prompt_performance'].get('original', {})
                    simp_perf = summary['prompt_performance'].get('simplified', {})
                    
                    f.write(f"| {model} | {summary['total_tests']} | {summary['correct_answers']} | {summary['success_rate']}% | {summary['avg_latency']}s | {orig_perf.get('success_rate', 0)}% | {simp_perf.get('success_rate', 0)}% |\n")
            
            f.write(f"\n## Prompt Format Comparison\n\n")
            
            # Analyze prompt performance
            for prompt in self.prompts:
                prompt_results = [r for r in self.results if r['prompt_type'] == prompt['name']]
                if prompt_results:
                    correct = len([r for r in prompt_results if r['is_correct']])
                    total = len(prompt_results)
                    success_rate = round((correct/total)*100, 1)
                    
                    f.write(f"### {prompt['name'].title()} Prompt\n")
                    f.write(f"- **Tests:** {total}\n")
                    f.write(f"- **Correct:** {correct}\n") 
                    f.write(f"- **Success Rate:** {success_rate}%\n\n")
        
        logging.info(f"Summary report saved to {report_file}")
    
    def run_comprehensive_test(self, iterations: int = 5):
        """Run the complete test suite with model cycling approach"""
        logging.info("🍓 Starting Strawberry Test Runner - Comprehensive LLM Validation")
        logging.info(f"Testing {iterations} iterations per prompt per model")
        
        # Discover models
        self.models = self.discover_models()
        
        if not self.models:
            logging.error("No models found! Exiting.")
            return
        
        logging.info(f"Will test {len(self.models)} models with {len(self.prompts)} prompt variations")
        logging.info(f"Total expected tests: {len(self.models)} × {len(self.prompts)} × {iterations} = {len(self.models) * len(self.prompts) * iterations}")
        logging.info("🔄 Using model cycling approach - no model refresh needed!")
        
        start_time = time.time()
        
        # Cycle through all combinations efficiently
        for prompt in self.prompts:
            logging.info(f"\n{'='*60}")
            logging.info(f"Testing {prompt['name'].upper()} prompt across all models")
            logging.info(f"{'='*60}")
            
            for iteration in range(1, iterations + 1):
                logging.info(f"\n📝 {prompt['name'].title()} Prompt - Iteration {iteration}/{iterations}")
                
                for model_idx, model in enumerate(self.models, 1):
                    logging.info(f"Testing {model} ({model_idx}/{len(self.models)}) - {prompt['name']} #{iteration}")
                    
                    try:
                        result = self.run_single_test_no_refresh(model, prompt, iteration)
                        self.results.append(result)
                    except Exception as e:
                        logging.error(f"❌ Failed to test {model}: {str(e)}")
                        continue
        
        end_time = time.time()
        total_time = round(end_time - start_time, 2)
        
        logging.info(f"\n🎉 Strawberry Test Runner Complete!")
        logging.info(f"Total execution time: {total_time} seconds")
        logging.info(f"Total tests executed: {len(self.results)}")
        
        # Save final results
        self.save_results()
        
        return self.results

def main():
    """Main execution function"""
    runner = StrawberryTestRunner()
    
    try:
        results = runner.run_comprehensive_test(iterations=5)
        print(f"\n✅ Strawberry testing complete! {len(results)} tests executed.")
        print(f"Check the '{runner.output_dir}' directory for detailed results.")
    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        if runner.results:
            runner.save_results()
            print(f"Partial results saved to '{runner.output_dir}' directory")
    except Exception as e:
        print(f"\n❌ Test run failed: {str(e)}")
        if runner.results:
            runner.save_results()
            print(f"Partial results saved to '{runner.output_dir}' directory")

if __name__ == "__main__":
    main()