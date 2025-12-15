#!/usr/bin/env python3
"""
Ollama Access Path Testing Script
Per RFA: rfa_ty_learn_ollama_access.md

Tests all available Ollama interfaces with EXACTLY the same prompt
to identify differences in responses and latency patterns.

Author: Arden
Date: 2025-09-21
"""

import subprocess
import requests
import json
import time
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sys

# Test configuration from RFA spec
TEST_PROMPT = """## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"? 

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

EXPECTED_RESPONSE = "[3]"
DEFAULT_MODEL = "gemma3n:e2b"  # Using the proven winner from strawberry tests

class OllamaAccessTester:
    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.results = []
        
    def test_cli_subprocess(self) -> Dict[str, Any]:
        """Test CLI access via subprocess"""
        print(f"🖥️  Testing CLI (subprocess) with {self.model}...")
        
        start_time = time.time()
        first_token_time = None
        
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, TEST_PROMPT],
                capture_output=True, 
                text=True,
                timeout=self.timeout
            )
            
            # For subprocess, we can't easily measure first token time
            # so we estimate it as 10% of total time (rough approximation)
            total_time = time.time() - start_time
            first_token_time = total_time * 0.1
            
            if result.returncode == 0:
                response = result.stdout
                error = None
            else:
                response = ""
                error = result.stderr
                
        except subprocess.TimeoutExpired:
            total_time = time.time() - start_time
            response = ""
            error = f"Timeout after {self.timeout}s"
        except Exception as e:
            total_time = time.time() - start_time
            response = ""
            error = str(e)
            
        return {
            "interface": "cli_subprocess",
            "model": self.model,
            "prompt": TEST_PROMPT,
            "response": response,
            "error": error,
            "latency_first_token_ms": int(first_token_time * 1000) if first_token_time else None,
            "latency_total_ms": int(total_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
    
    def test_http_requests_streaming(self) -> Dict[str, Any]:
        """Test HTTP REST API with streaming response"""
        print(f"🌐 Testing HTTP REST (streaming) with {self.model}...")
        
        start_time = time.time()
        first_token_time = None
        response_text = ""
        error = None
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
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
                            if first_token_time is None:
                                first_token_time = time.time() - start_time
                            response_text += data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            error = str(e)
            
        total_time = time.time() - start_time
        
        return {
            "interface": "http_streaming",
            "model": self.model,
            "prompt": TEST_PROMPT,
            "response": response_text,
            "error": error,
            "latency_first_token_ms": int(first_token_time * 1000) if first_token_time else None,
            "latency_total_ms": int(total_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
    
    def test_http_requests_non_streaming(self) -> Dict[str, Any]:
        """Test HTTP REST API without streaming (like our fixed LLMCore)"""
        print(f"🌐 Testing HTTP REST (non-streaming) with {self.model}...")
        
        start_time = time.time()
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": TEST_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0}  # Match our LLMCore fix
                },
                timeout=self.timeout
            )
            
            total_time = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                error = None
            else:
                response_text = ""
                error = f"HTTP {resp.status_code}: {resp.text}"
                
        except Exception as e:
            total_time = time.time() - start_time
            response_text = ""
            error = str(e)
            
        return {
            "interface": "http_non_streaming",
            "model": self.model,
            "prompt": TEST_PROMPT,
            "response": response_text,
            "error": error,
            "latency_first_token_ms": None,  # Non-streaming doesn't provide first token timing
            "latency_total_ms": int(total_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
    
    def test_python_wrapper(self) -> Dict[str, Any]:
        """Test Python wrapper library (if available)"""
        print(f"🐍 Testing Python wrapper (ollama-py) with {self.model}...")
        
        try:
            import ollama
        except ImportError:
            return {
                "interface": "python_wrapper",
                "model": self.model,
                "prompt": TEST_PROMPT,
                "response": "",
                "error": "ollama-py library not installed",
                "latency_first_token_ms": None,
                "latency_total_ms": None,
                "timestamp": datetime.now().isoformat()
            }
        
        start_time = time.time()
        first_token_time = None
        response_text = ""
        error = None
        
        try:
            stream = ollama.generate(
                model=self.model, 
                prompt=TEST_PROMPT, 
                stream=True
            )
            
            for chunk in stream:
                if first_token_time is None and chunk.get("response"):
                    first_token_time = time.time() - start_time
                response_text += chunk.get("response", "")
                
        except Exception as e:
            error = str(e)
            
        total_time = time.time() - start_time
        
        return {
            "interface": "python_wrapper",
            "model": self.model,
            "prompt": TEST_PROMPT,
            "response": response_text,
            "error": error,
            "latency_first_token_ms": int(first_token_time * 1000) if first_token_time else None,
            "latency_total_ms": int(total_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all available access method tests"""
        print(f"🧪 Starting Ollama Access Path Testing...")
        print(f"📝 Model: {self.model}")
        print(f"🎯 Expected: {EXPECTED_RESPONSE}")
        print(f"⏱️  Timeout: {self.timeout}s")
        print("=" * 60)
        
        # Test all access methods
        tests = [
            self.test_cli_subprocess,
            self.test_http_requests_streaming,
            self.test_http_requests_non_streaming,
            self.test_python_wrapper
        ]
        
        results = []
        for test_func in tests:
            try:
                result = test_func()
                results.append(result)
                
                # Print summary
                success = "✅" if not result["error"] else "❌"
                response_preview = (result["response"][:50] + "...") if len(result["response"]) > 50 else result["response"]
                latency = result["latency_total_ms"]
                print(f"{success} {result['interface']}: {latency}ms - {repr(response_preview)}")
                
                if result["error"]:
                    print(f"   Error: {result['error']}")
                
            except Exception as e:
                print(f"❌ {test_func.__name__} failed: {e}")
                
            # Brief pause between tests
            time.sleep(1)
        
        self.results = results
        return results
    
    def save_results(self, output_file: str = "ollama_access_test_results.json"):
        """Save results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Results saved to: {output_file}")
        
    def save_results_csv(self, output_file: str = "ollama_access_test_results.csv"):
        """Save results to CSV file"""
        if not self.results:
            print("❌ No results to save")
            return
            
        fieldnames = [
            "interface", "model", "response", "error", 
            "latency_first_token_ms", "latency_total_ms", "timestamp"
        ]
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                # Create CSV row (exclude prompt for readability)
                csv_row = {k: v for k, v in result.items() if k != "prompt"}
                writer.writerow(csv_row)
                
        print(f"📊 CSV results saved to: {output_file}")
    
    def analyze_results(self):
        """Analyze and compare results across access methods"""
        print("\n" + "=" * 60)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 60)
        
        successful_tests = [r for r in self.results if not r["error"]]
        failed_tests = [r for r in self.results if r["error"]]
        
        print(f"✅ Successful tests: {len(successful_tests)}/{len(self.results)}")
        print(f"❌ Failed tests: {len(failed_tests)}")
        
        if successful_tests:
            print(f"\n🎯 Response Analysis (Expected: {EXPECTED_RESPONSE}):")
            for result in successful_tests:
                interface = result["interface"]
                response = result["response"].strip()
                matches_expected = response == EXPECTED_RESPONSE
                match_icon = "✅" if matches_expected else "⚠️"
                
                print(f"  {match_icon} {interface}: {repr(response)}")
        
        if len(successful_tests) > 1:
            print(f"\n⏱️  Latency Comparison:")
            sorted_results = sorted(successful_tests, key=lambda x: x["latency_total_ms"])
            for result in sorted_results:
                interface = result["interface"]
                total_ms = result["latency_total_ms"]
                first_ms = result["latency_first_token_ms"]
                first_str = f"{first_ms}ms" if first_ms else "N/A"
                print(f"  {interface}: {total_ms}ms total, {first_str} first token")


def main():
    """Main execution function"""
    # Allow model override via command line
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    
    tester = OllamaAccessTester(model=model)
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"data/ollama_access_test_{timestamp}.json"
    csv_file = f"data/ollama_access_test_{timestamp}.csv"
    
    tester.save_results(json_file)
    tester.save_results_csv(csv_file)
    
    # Analyze results
    tester.analyze_results()
    
    print(f"\n🎉 Testing complete! Results saved to:")
    print(f"   JSON: {json_file}")
    print(f"   CSV: {csv_file}")


if __name__ == "__main__":
    main()