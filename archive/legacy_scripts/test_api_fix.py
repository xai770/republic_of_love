#!/usr/bin/env python3
"""
Test Max's API fix for LLMCore execution context
Simple implementation per Max's guidance - no ceremony
"""

import requests
import time

def execute_ollama_test(model, prompt):
    """Max's direct API approach"""
    response = requests.post('http://localhost:11434/api/generate', 
        json={
            'model': model,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0}
        }
    )
    return response.json()['response'].strip()

def test_strawberry_api():
    """Test if API approach fixes execution context issue"""
    model = 'gemma3n:e2b'
    prompt = """## Payload
How many "r" letters are in "strawberry"? 
## Instructions
- Format your response as [NUMBER]. Make sure to to include ONE PAIR brackets in the output. 
- Example response: [X] where X is your calculated answer.
- Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

    print("🧪 Testing API fix for execution context...")
    print(f"Model: {model}")
    print(f"Expected: [3]")
    
    start_time = time.time()
    try:
        result = execute_ollama_test(model, prompt)
        latency = time.time() - start_time
        
        print(f"Result: {repr(result)}")
        print(f"Latency: {latency:.2f}s")
        
        # Check if it matches CLI expectation
        if result == '[3]':
            print("✅ SUCCESS: Perfect CLI alignment!")
            return True
        elif '[3]' in result:
            print("⚠️  PARTIAL: Contains [3] but has extra content")
            print(f"   Extra content: {result}")
            return False
        else:
            print("❌ FAILED: Different answer")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_strawberry_api()
    print(f"\n📊 API Fix Test: {'PASSED' if success else 'FAILED'}")