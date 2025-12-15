#!/usr/bin/env python3
"""
Context Leakage Detection Test
Tests whether Ollama requests maintain context between supposedly independent calls
"""
import requests
import time
import random

class ContextLeakageTest:
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        # Generate random secret words to avoid any training data contamination
        self.secret_words = ["ZEPHYR", "QUASAR", "NIMBUS", "VORTEX", "PRISM"]
    
    def make_request(self, model_name: str, prompt: str, headers: dict = None) -> tuple:
        """Make a single request to Ollama and return response + timing"""
        start_time = time.time()
        
        request_headers = headers or {}
        
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1  # Low temperature for consistent responses
                }
            },
            headers=request_headers,
            timeout=30
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip(), latency_ms, True
        else:
            return f"ERROR: {response.status_code}", latency_ms, False
    
    def test_baseline_method(self, model_name: str) -> dict:
        """Test current method (suspected leakage)"""
        secret_word = random.choice(self.secret_words)
        
        print(f"🧪 Testing BASELINE method with {model_name}")
        print(f"🔹 Secret word: {secret_word}")
        
        # Step 1: Plant the secret word
        plant_prompt = f"Please remember this secret word: {secret_word}. Respond only with 'OK'."
        plant_response, plant_time, plant_success = self.make_request(model_name, plant_prompt)
        
        print(f"   Plant request: {plant_time}ms - {plant_response[:50]}...")
        
        # Step 2: Try to recall it
        recall_prompt = "What secret word did I just ask you to remember? If you don't remember any secret word, say 'NO MEMORY'."
        recall_response, recall_time, recall_success = self.make_request(model_name, recall_prompt)
        
        print(f"   Recall request: {recall_time}ms - {recall_response[:100]}...")
        
        # Check if secret word appears in recall response
        leaked = secret_word.lower() in recall_response.lower()
        
        return {
            "method": "baseline",
            "model": model_name,
            "secret_word": secret_word,
            "plant_response": plant_response,
            "recall_response": recall_response,
            "leaked": leaked,
            "plant_time": plant_time,
            "recall_time": recall_time
        }
    
    def test_isolated_method(self, model_name: str) -> dict:
        """Test with connection isolation headers"""
        secret_word = random.choice(self.secret_words)
        
        print(f"🧪 Testing ISOLATED method with {model_name}")
        print(f"🔹 Secret word: {secret_word}")
        
        isolation_headers = {
            'Connection': 'close',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # Step 1: Plant the secret word
        plant_prompt = f"Please remember this secret word: {secret_word}. Respond only with 'OK'."
        plant_response, plant_time, plant_success = self.make_request(model_name, plant_prompt, isolation_headers)
        
        print(f"   Plant request: {plant_time}ms - {plant_response[:50]}...")
        
        # Step 2: Try to recall it (with fresh connection)
        recall_prompt = "What secret word did I just ask you to remember? If you don't remember any secret word, say 'NO MEMORY'."
        recall_response, recall_time, recall_success = self.make_request(model_name, recall_prompt, isolation_headers)
        
        print(f"   Recall request: {recall_time}ms - {recall_response[:100]}...")
        
        # Check if secret word appears in recall response
        leaked = secret_word.lower() in recall_response.lower()
        
        return {
            "method": "isolated_headers",
            "model": model_name,
            "secret_word": secret_word,
            "plant_response": plant_response,
            "recall_response": recall_response,
            "leaked": leaked,
            "plant_time": plant_time,
            "recall_time": recall_time
        }
    
    def test_model_unload_method(self, model_name: str) -> dict:
        """Test with explicit model unloading between requests"""
        secret_word = random.choice(self.secret_words)
        
        print(f"🧪 Testing MODEL_UNLOAD method with {model_name}")
        print(f"🔹 Secret word: {secret_word}")
        
        # Step 1: Plant the secret word
        plant_prompt = f"Please remember this secret word: {secret_word}. Respond only with 'OK'."
        plant_response, plant_time, plant_success = self.make_request(model_name, plant_prompt)
        
        print(f"   Plant request: {plant_time}ms - {plant_response[:50]}...")
        
        # Step 1.5: Explicitly unload model
        print("   🔄 Unloading model from memory...")
        unload_response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": model_name,
                "prompt": "",
                "keep_alive": 0  # Immediately unload
            }
        )
        print(f"   Unload status: {unload_response.status_code}")
        
        # Wait a moment for unload to complete
        time.sleep(2)
        
        # Step 2: Try to recall it (model should be cold-loaded again)
        recall_prompt = "What secret word did I just ask you to remember? If you don't remember any secret word, say 'NO MEMORY'."
        recall_response, recall_time, recall_success = self.make_request(model_name, recall_prompt)
        
        print(f"   Recall request: {recall_time}ms - {recall_response[:100]}...")
        
        # Check if secret word appears in recall response
        leaked = secret_word.lower() in recall_response.lower()
        
        return {
            "method": "model_unload",
            "model": model_name,
            "secret_word": secret_word,
            "plant_response": plant_response,
            "recall_response": recall_response,
            "leaked": leaked,
            "plant_time": plant_time,
            "recall_time": recall_time
        }

def main():
    tester = ContextLeakageTest()
    
    # Test with a fast, small model for quick results
    test_model = "llama3.2:1b"
    
    print("=" * 80)
    print("🔬 CONTEXT LEAKAGE DETECTION EXPERIMENT")
    print("=" * 80)
    print(f"Testing model: {test_model}")
    print()
    
    results = []
    
    # Run all three methods
    results.append(tester.test_baseline_method(test_model))
    print()
    results.append(tester.test_isolated_method(test_model))
    print()
    results.append(tester.test_model_unload_method(test_model))
    
    print("\n" + "=" * 80)
    print("🧪 EXPERIMENTAL RESULTS")
    print("=" * 80)
    
    for result in results:
        method = result['method']
        leaked = result['leaked']
        plant_time = result['plant_time']
        recall_time = result['recall_time']
        
        status = "🚨 LEAKAGE DETECTED" if leaked else "✅ NO LEAKAGE"
        timing_pattern = "⚡ Fast recall" if recall_time < plant_time * 0.3 else "🐌 Full reload"
        
        print(f"{method.upper()}: {status} | {timing_pattern}")
        print(f"  Plant: {plant_time}ms | Recall: {recall_time}ms")
        print(f"  Secret: {result['secret_word']}")
        print(f"  Recall response: {result['recall_response'][:100]}...")
        print()
    
    # Summary
    leakage_count = sum(1 for r in results if r['leaked'])
    print(f"📊 SUMMARY: {leakage_count}/{len(results)} methods showed context leakage")
    
    if leakage_count > 0:
        print("🚨 CRITICAL: Context leakage detected! Test results may be contaminated!")
    else:
        print("✅ GOOD: No context leakage detected across methods.")

if __name__ == "__main__":
    main()