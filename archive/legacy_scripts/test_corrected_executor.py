#!/usr/bin/env python3
"""
Test corrected LLMCore executor with streaming API
Validate that streaming fix achieves both speed and accuracy
"""

import sys
import os
sys.path.append('/home/xai/Documents/ty_learn/llmcore')

from llmcore_executor_v2 import LLMCoreExecutor

def test_corrected_executor():
    """Test corrected executor with streaming API"""
    print("🧪 Testing CORRECTED LLMCore executor (streaming API)...")
    
    executor = LLMCoreExecutor()
    
    # Test the fixed call_ollama method directly
    prompt = """## Processing Instructions
Format your response as [NUMBER]. Make sure to to include the brackets in the output.
Example: [X] where X is your calculated answer.

## Processing Payload
How many "r" letters are in "strawberry"? 

## QA Check
Submit ONLY the required response. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""

    print(f"Model: phi3:latest")
    print(f"Expected: [3]")
    
    response, latency, error = executor.call_ollama('phi3:latest', prompt)
    
    print(f"Response: {repr(response)}")
    print(f"Latency: {latency:.2f}s")
    print(f"Error: {error}")
    
    if error:
        print("❌ FAILED: Error occurred")
        return False
    elif response.strip() == '[3]':
        print("✅ SUCCESS: Correct answer with streaming API!")
        return True
    elif '[3]' in response:
        print("⚠️  PARTIAL: Contains [3] but has extra content")
        print(f"   Full response: {response}")
        return True
    else:
        print("❌ FAILED: Wrong answer")
        return False

if __name__ == "__main__":
    success = test_corrected_executor()
    print(f"\n📊 Corrected Executor Test: {'PASSED' if success else 'FAILED'}")