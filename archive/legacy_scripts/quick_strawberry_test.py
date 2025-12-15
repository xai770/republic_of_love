#!/usr/bin/env python3
"""
Quick Strawberry Test - Fast Reliable Models Only
=================================================
Tests a curated list of fast, reliable models for quick results.
"""

import json
import requests
import time
from datetime import datetime
import csv
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuickStrawberryTest:
    def __init__(self):
        # Fast, reliable models (excluding problematic ones like deepseek-r1, bge-m3)
        self.fast_models = [
            "gemma3:1b", "gemma3:4b", "gemma2:latest", "gemma3n:latest", "gemma3n:e2b",
            "llama3.2:1b", "llama3.2:latest", 
            "qwen3:0.6b", "qwen3:1.7b", "qwen3:4b", "qwen2.5:7b",
            "phi3:latest", "phi3:3.8b", "phi4-mini:latest",
            "mistral:latest", "mistral-nemo:12b",
            "granite3.1-moe:3b",
            "dolphin3:latest", "dolphin3:8b",
            "codegemma:2b", "codegemma:latest",
            "olmo2:latest"
        ]
        
        self.prompt = """How many "r" letters are in "strawberry"?

Format your response as [NUMBER]. Make sure to include the brackets.
Example: [3]"""
        
        self.results = []
        self.correct_answer = "3"

    def test_model(self, model: str, timeout: int = 15) -> dict:
        """Test a single model with timeout"""
        start_time = time.time()
        
        try:
            response = requests.post('http://localhost:11434/api/generate', 
                json={
                    'model': model,
                    'prompt': self.prompt,
                    'stream': False
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                model_response = data['response']
                latency = round(time.time() - start_time, 2)
                
                # Extract answer
                is_correct, extracted = self.evaluate_response(model_response)
                
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'model': model,
                    'response': model_response[:200] + "..." if len(model_response) > 200 else model_response,
                    'extracted_answer': extracted,
                    'is_correct': is_correct,
                    'latency': latency,
                    'status': 'completed'
                }
                
                status = "✓" if is_correct else "✗"
                logging.info(f"{status} {model}: {extracted} ({latency}s)")
                
                return result
            
        except requests.exceptions.Timeout:
            logging.warning(f"⏰ {model}: TIMEOUT ({timeout}s)")
            return {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'response': 'TIMEOUT',
                'extracted_answer': 'TIMEOUT',
                'is_correct': False,
                'latency': timeout,
                'status': 'timeout'
            }
        except Exception as e:
            logging.error(f"💥 {model}: ERROR - {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'response': f'ERROR: {str(e)}',
                'extracted_answer': 'ERROR',
                'is_correct': False,
                'latency': round(time.time() - start_time, 2),
                'status': 'error'
            }

    def evaluate_response(self, response: str) -> tuple:
        """Extract and evaluate the answer"""
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
        
        return False, "NO_NUMBER_FOUND"

    def run_all_tests(self):
        """Run tests on all fast models"""
        logging.info(f"🍓 Quick Strawberry Test - Testing {len(self.fast_models)} fast models")
        
        for i, model in enumerate(self.fast_models, 1):
            logging.info(f"Testing {model} ({i}/{len(self.fast_models)})")
            result = self.test_model(model)
            self.results.append(result)
            time.sleep(0.5)  # Brief pause
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        with open(f'quick_strawberry_{timestamp}.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save CSV
        if self.results:
            with open(f'quick_strawberry_{timestamp}.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
        
        # Generate summary
        self.generate_summary(timestamp)

    def generate_summary(self, timestamp: str):
        """Generate summary report"""
        total_tests = len(self.results)
        completed_tests = len([r for r in self.results if r['status'] == 'completed'])
        correct_answers = len([r for r in self.results if r['is_correct']])
        success_rate = (correct_answers / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average latency for completed tests
        completed_latencies = [r['latency'] for r in self.results if r['status'] == 'completed']
        avg_latency = sum(completed_latencies) / len(completed_latencies) if completed_latencies else 0
        
        summary = f"""# Quick Strawberry Test Results
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Statistics
- **Total Tests:** {total_tests}
- **Completed Tests:** {completed_tests}
- **Correct Answers:** {correct_answers}
- **Overall Success Rate:** {success_rate:.1f}%
- **Average Latency:** {avg_latency:.2f}s

## Individual Results

| Model | Answer | Correct | Latency | Status |
|-------|--------|---------|---------|--------|
"""
        
        for result in self.results:
            status_emoji = "✓" if result['is_correct'] else "✗"
            summary += f"| {result['model']} | {result['extracted_answer']} | {status_emoji} | {result['latency']}s | {result['status']} |\n"
        
        with open(f'quick_strawberry_summary_{timestamp}.md', 'w') as f:
            f.write(summary)
        
        print(summary)

if __name__ == "__main__":
    runner = QuickStrawberryTest()
    runner.run_all_tests()