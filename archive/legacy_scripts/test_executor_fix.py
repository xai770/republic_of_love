#!/usr/bin/env python3
"""
Test fixed LLMCore executor with strawberry test
Validate that API fix achieves CLI alignment
"""

import sys
import os
sys.path.append('/home/xai/Documents/ty_learn/llmcore')

from llmcore_executor_v2 import LLMCoreExecutor

def test_strawberry_with_fixed_executor():
    """Test strawberry canonical with API-fixed executor"""
    print("🧪 Testing fixed LLMCore executor with strawberry...")
    
    executor = LLMCoreExecutor()
    
    # Test gemma3n:e2b with strawberry canonical
    result = executor.execute_single_test('rr_reason_recognize_basic', 'gemma3n:e2b')
    
    print(f"📊 Test Result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Latency: {result.get('processing_latency', 0):.2f}s")
    print(f"  QA Score: {result.get('qa_score', 'N/A')}")
    
    if result.get('success'):
        print("✅ EXECUTOR FIX SUCCESSFUL!")
        return True
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    success = test_strawberry_with_fixed_executor()
    print(f"\n📊 Executor Fix Test: {'PASSED' if success else 'FAILED'}")