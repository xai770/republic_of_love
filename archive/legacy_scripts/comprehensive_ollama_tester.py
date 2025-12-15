#!/usr/bin/env python3
"""
Comprehensive Ollama Access Path Testing - All Models, Multiple Runs
Per xai's requirements - test ALL models from manual test table with multiple runs

Features:
- Tests all models from manual test output table
- Multiple access methods (CLI, HTTP streaming, HTTP non-streaming)
- 5 runs per model per access method (as requested)
- Single comprehensive CSV output with all data
"""

import subprocess
import requests
import json
import time
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sys

# Test configuration - EXACT prompt from RFA spec
TEST_PROMPT = """## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"? 

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

# All models from manual test output table
ALL_MODELS = [
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
    "dolphin3:latest",
    "olmo2:latest",
    "codegemma:latest",
    "qwen2.5vl:latest",
    "gemma3n:latest",
    "llama3.2:1b",
    "phi4-mini:latest",
    "gemma2:latest",
    "gemma3n:e2b"
]

EXPECTED_RESPONSE = "[3]"
NUM_RUNS = 5  # 5 runs as requested (columns D-L in your spec)

class ComprehensiveOllamaTest:
    def __init__(self, timeout: int = 45):
        self.timeout = timeout
        self.results = []
        
    def test_cli_method(self, model: str) -> List[Dict[str, Any]]:
        """Test CLI method with 5 runs"""
        print(f"  🖥️  CLI method...")
        runs = []
        
        for run_num in range(1, NUM_RUNS + 1):
            print(f"    Run {run_num}/5...", end="")
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    ["ollama", "run", model, TEST_PROMPT],
                    capture_output=True, 
                    text=True,
                    timeout=self.timeout
                )
                
                total_time = time.time() - start_time
                
                if result.returncode == 0:
                    response = result.stdout.strip()
                    error = None
                    print(f" ✅ {total_time:.1f}s")
                else:
                    response = ""
                    error = result.stderr.strip()
                    print(f" ❌ Error")
                    
            except subprocess.TimeoutExpired:
                total_time = time.time() - start_time
                response = ""
                error = f"Timeout after {self.timeout}s"
                print(f" ⏰ Timeout")
            except Exception as e:
                total_time = time.time() - start_time
                response = ""
                error = str(e)
                print(f" ❌ Exception")
                
            runs.append({
                'run': run_num,
                'latency_ms': int(total_time * 1000),
                'response': response,
                'error': error
            })
            
            # Brief pause between runs to avoid overwhelming model
            time.sleep(2)
            
        return runs
    
    def test_http_streaming_method(self, model: str) -> List[Dict[str, Any]]:
        """Test HTTP streaming method with 5 runs"""
        print(f"  🌐 HTTP Streaming method...")
        runs = []
        
        for run_num in range(1, NUM_RUNS + 1):
            print(f"    Run {run_num}/5...", end="")
            start_time = time.time()
            response_text = ""
            error = None
            
            try:
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": TEST_PROMPT,
                        "stream": True
                    },
                    stream=True,
                    timeout=self.timeout
                )
                
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "response" in data and data["response"]:
                                response_text += data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                error = str(e)
                
            total_time = time.time() - start_time
            
            if error:
                print(f" ❌ Error")
            else:
                print(f" ✅ {total_time:.1f}s")
                
            runs.append({
                'run': run_num,
                'latency_ms': int(total_time * 1000),
                'response': response_text.strip(),
                'error': error
            })
            
            # Brief pause between runs
            time.sleep(1)
            
        return runs
    
    def test_http_non_streaming_method(self, model: str) -> List[Dict[str, Any]]:
        """Test HTTP non-streaming method with 5 runs"""
        print(f"  🌐 HTTP Non-streaming method...")
        runs = []
        
        for run_num in range(1, NUM_RUNS + 1):
            print(f"    Run {run_num}/5...", end="")
            start_time = time.time()
            
            try:
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "prompt": TEST_PROMPT,
                        "stream": False,
                        "options": {"temperature": 0}
                    },
                    timeout=self.timeout
                )
                
                total_time = time.time() - start_time
                
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "").strip()
                    error = None
                    print(f" ✅ {total_time:.1f}s")
                else:
                    response_text = ""
                    error = f"HTTP {resp.status_code}: {resp.text}"
                    print(f" ❌ HTTP Error")
                    
            except Exception as e:
                total_time = time.time() - start_time
                response_text = ""
                error = str(e)
                print(f" ❌ Exception")
                
            runs.append({
                'run': run_num,
                'latency_ms': int(total_time * 1000),
                'response': response_text,
                'error': error
            })
            
            # Brief pause between runs
            time.sleep(1)
            
        return runs
    
    def test_cli_single_run(self, model: str) -> Dict[str, Any]:
        """Test CLI method with single run"""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["ollama", "run", model, TEST_PROMPT],
                capture_output=True, 
                text=True,
                timeout=self.timeout
            )
            
            total_time = time.time() - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                error = None
            else:
                response = ""
                error = result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            total_time = time.time() - start_time
            response = ""
            error = f"Timeout after {self.timeout}s"
        except Exception as e:
            total_time = time.time() - start_time
            response = ""
            error = str(e)
            
        return {
            'latency_ms': int(total_time * 1000),
            'response': response,
            'error': error
        }
    
    def test_http_streaming_single_run(self, model: str) -> Dict[str, Any]:
        """Test HTTP streaming method with single run"""
        start_time = time.time()
        response_text = ""
        error = None
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": TEST_PROMPT,
                    "stream": True
                },
                stream=True,
                timeout=self.timeout
            )
            
            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        if "response" in data and data["response"]:
                            response_text += data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            error = str(e)
            
        total_time = time.time() - start_time
        
        return {
            'latency_ms': int(total_time * 1000),
            'response': response_text.strip(),
            'error': error
        }
    
    def test_http_non_streaming_single_run(self, model: str) -> Dict[str, Any]:
        """Test HTTP non-streaming method with single run"""
        start_time = time.time()
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": TEST_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0}
                },
                timeout=self.timeout
            )
            
            total_time = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "").strip()
                error = None
            else:
                response_text = ""
                error = f"HTTP {resp.status_code}: {resp.text}"
                
        except Exception as e:
            total_time = time.time() - start_time
            response_text = ""
            error = str(e)
            
        return {
            'latency_ms': int(total_time * 1000),
            'response': response_text,
            'error': error
        }
    
    def test_single_model(self, model: str) -> List[Dict[str, Any]]:
        """Test one model with all access methods"""
        print(f"\n🤖 Testing model: {model}")
        print("-" * 50)
        
        model_results = []
        
        # Test all access methods
        access_methods = [
            ("CLI", self.test_cli_method),
            ("HTTP_Streaming", self.test_http_streaming_method),
            ("HTTP_Non_Streaming", self.test_http_non_streaming_method)
        ]
        
        for access_name, test_method in access_methods:
            try:
                runs = test_method(model)
                
                # Create result record
                result_row = {
                    'prompt': TEST_PROMPT,
                    'model': model,
                    'access_method': access_name,
                }
                
                # Add latency and response for each run (columns D through L)
                for i, run_data in enumerate(runs, 1):
                    result_row[f'latency_run_{i}'] = run_data['latency_ms'] if not run_data['error'] else None
                    result_row[f'response_run_{i}'] = run_data['response'] if not run_data['error'] else run_data['error']
                
                model_results.append(result_row)
                
            except Exception as e:
                print(f"  ❌ Failed {access_name}: {e}")
                
            # Pause between access methods
            time.sleep(3)
        
        return model_results
    
    def run_comprehensive_test(self, models_to_test: List[str] = None) -> List[Dict[str, Any]]:
        """Run comprehensive test - 5 COMPLETE ROUNDS through ALL models"""
        if models_to_test is None:
            models_to_test = ALL_MODELS
            
        print("🧪 COMPREHENSIVE OLLAMA ACCESS PATH TESTING")
        print("=" * 60)
        print(f"📝 Models to test: {len(models_to_test)}")
        print(f"🔧 Access methods: CLI, HTTP Streaming, HTTP Non-streaming")  
        print(f"🔄 Rounds: {NUM_RUNS} complete rounds through ALL models")
        print(f"🎯 Expected response: {EXPECTED_RESPONSE}")
        print(f"⏱️  Timeout per test: {self.timeout}s")
        print("=" * 60)
        
        # Initialize results structure - one row per model per access method
        all_results = []
        
        # Create base result rows for each model and access method combination
        access_methods = ["CLI", "HTTP_Streaming", "HTTP_Non_Streaming"]
        
        for model in models_to_test:
            for access_method in access_methods:
                result_row = {
                    'prompt': TEST_PROMPT,
                    'model': model,
                    'access_method': access_method,
                    'latency_run_1': None, 'response_run_1': None,
                    'latency_run_2': None, 'response_run_2': None,
                    'latency_run_3': None, 'response_run_3': None,
                    'latency_run_4': None, 'response_run_4': None,
                    'latency_run_5': None, 'response_run_5': None,
                }
                all_results.append(result_row)
        
        # Now run 5 complete rounds through all models
        for round_num in range(1, NUM_RUNS + 1):
            print(f"\n� ROUND {round_num}/{NUM_RUNS} - Testing ALL models")
            print("=" * 50)
            
            for model_idx, model in enumerate(models_to_test, 1):
                print(f"\n📊 Round {round_num} - Model {model_idx}/{len(models_to_test)}: {model}")
                
                try:
                    # Test all access methods for this model in this round
                    model_round_results = self.test_single_model_single_round(model)
                    
                    # Update the corresponding result rows with this round's data
                    for access_method, run_data in model_round_results.items():
                        # Find the matching result row
                        for result_row in all_results:
                            if result_row['model'] == model and result_row['access_method'] == access_method:
                                result_row[f'latency_run_{round_num}'] = run_data['latency_ms'] if not run_data['error'] else None
                                result_row[f'response_run_{round_num}'] = run_data['response'] if not run_data['error'] else run_data['error']
                                break
                    
                except KeyboardInterrupt:
                    print(f"\n⚠️  Test interrupted by user")
                    self.results = all_results
                    return all_results
                except Exception as e:
                    print(f"❌ Model {model} failed in round {round_num}: {e}")
                    continue
            
            print(f"\n✅ Round {round_num} complete!")
            # Brief pause between rounds
            time.sleep(5)
        
        self.results = all_results
        return all_results
    
    def test_single_model_single_round(self, model: str) -> Dict[str, Dict[str, Any]]:
        """Test one model with all access methods for ONE round only"""
        print(f"  Testing {model}...", end="")
        
        round_results = {}
        
        # Test all access methods for this model
        access_methods = [
            ("CLI", self.test_cli_single_run),
            ("HTTP_Streaming", self.test_http_streaming_single_run),
            ("HTTP_Non_Streaming", self.test_http_non_streaming_single_run)
        ]
        
        method_times = []
        
        for access_name, test_method in access_methods:
            try:
                run_data = test_method(model)
                round_results[access_name] = run_data
                
                if not run_data['error']:
                    method_times.append(f"{access_name[:4]}:{run_data['latency_ms']}ms")
                
            except Exception as e:
                round_results[access_name] = {
                    'latency_ms': None,
                    'response': str(e),
                    'error': str(e)
                }
        
        # Print summary for this model
        print(f" [{', '.join(method_times)}]")
        
        return round_results
    
    def save_comprehensive_csv(self, filename: str = None):
        """Save results to CSV with xai's requested column structure"""
        if not self.results:
            print("❌ No results to save")
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/comprehensive_ollama_access_test_{timestamp}.csv"
        
        # Column headers as requested by xai
        fieldnames = [
            'prompt',                    # Column A
            'model',                     # Column B  
            'access_method',             # Column C
            'latency_run_1',            # Column D
            'response_run_1',           # Column E
            'latency_run_2',            # Column F
            'response_run_2',           # Column G
            'latency_run_3',            # Column H
            'response_run_3',           # Column I
            'latency_run_4',            # Column J
            'response_run_4',           # Column K
            'latency_run_5',            # Column L
            'response_run_5',           # Column M
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"💾 Comprehensive results saved to: {filename}")
        print(f"📊 Total records: {len(self.results)}")
        
        return filename
    
    def print_summary(self):
        """Print summary statistics"""
        if not self.results:
            return
            
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        # Count by access method
        by_access = {}
        successful_tests = 0
        
        for result in self.results:
            access = result['access_method']
            if access not in by_access:
                by_access[access] = {'total': 0, 'successful': 0}
            
            by_access[access]['total'] += 1
            
            # Check if any run was successful (has non-None latency)
            has_success = any(result.get(f'latency_run_{i}') is not None for i in range(1, NUM_RUNS + 1))
            if has_success:
                by_access[access]['successful'] += 1
                successful_tests += 1
        
        print(f"📈 Total test combinations: {len(self.results)}")
        print(f"✅ Successful combinations: {successful_tests}")
        
        print(f"\n📋 Results by access method:")
        for access, stats in by_access.items():
            success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {access}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Find models with response variations
        print(f"\n🔍 Response consistency analysis coming in CSV...")


def main():
    """Main execution"""
    # Allow testing subset of models for quick validation
    test_models = ALL_MODELS
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # Quick test with just a few models
            test_models = ["gemma3n:e2b", "phi3:latest", "qwen3:4b"]
            print("🚀 Quick test mode - testing 3 models only")
        elif sys.argv[1] == "single":
            # Single model test
            test_models = [sys.argv[2]] if len(sys.argv) > 2 else ["gemma3n:e2b"]
            print(f"🎯 Single model test: {test_models[0]}")
    
    # Run comprehensive test
    tester = ComprehensiveOllamaTest()
    
    try:
        results = tester.run_comprehensive_test(test_models)
        
        # Save results
        csv_filename = tester.save_comprehensive_csv()
        
        # Print summary
        tester.print_summary()
        
        print(f"\n🎉 COMPREHENSIVE TESTING COMPLETE!")
        print(f"📁 Results file: {csv_filename}")
        print(f"📊 Ready for analysis!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test stopped by user")
        if tester.results:
            csv_filename = tester.save_comprehensive_csv()
            print(f"💾 Partial results saved: {csv_filename}")


if __name__ == "__main__":
    main()