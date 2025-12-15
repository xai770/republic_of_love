#!/usr/bin/env python3
"""
Direct test of fixed call_ollama method
"""

import sys
import os
sys.path.append('/home/xai/Documents/ty_learn/llmcore')

from llmcore_executor_v2 import LLMCoreExecutor

def test_direct_api_call():
    """Test the fixed call_ollama method directly"""
    print("🧪 Testing fixed call_ollama method directly...")
    
    executor = LLMCoreExecutor()
    
    prompt = """## Instructions
Format your response as [NUMBER]. Include brackets.
Example: [X] where X is your calculated answer.

How many "r" letters are in "strawberry"?"""

    print(f"Model: gemma3n:e2b")
    print(f"Expected: [3]")
    
    response, latency, error = executor.call_ollama('gemma3n:e2b', prompt)
    
    print(f"Response: {repr(response)}")
    print(f"Latency: {latency:.2f}s")
    print(f"Error: {error}")
    
    if response == '[3]':
        print("✅ PERFECT CLI ALIGNMENT!")
        return True
    elif '[3]' in response:
        print("⚠️  Contains [3] but has extra content")
        return False
    else:
        print("❌ Wrong answer")
        return False

if __name__ == "__main__":
    success = test_direct_api_call()
    print(f"\n📊 Direct API Fix Test: {'PASSED' if success else 'FAILED'}")