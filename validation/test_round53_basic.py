#!/usr/bin/env python3
"""
Basic validation test for Round 5.3 Adaptive Confidence implementation.
Quick test to verify confidence scoring and lifecycle stages work correctly.
"""

import sys
import os
import tempfile
import time
from typing import Callable

# Add membridge to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from membridge.converged_membridge import ConvergedMemBridge
from membridge.models import MemBridgeConfig


def mock_llm_call(response: str, duration_ms: float = 100) -> Callable[[], str]:
    """Mock LLM call function"""
    def call() -> str:
        time.sleep(duration_ms / 1000)
        return response
    return call


def test_confidence_scoring() -> bool:
    """Test basic confidence scoring algorithm"""
    print("🧪 Testing Round 5.3 Confidence Scoring...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        config = MemBridgeConfig(
            cache_duration_seconds=1,  # Force fresh calls
            enable_environmental_context=True
        )
        bridge = ConvergedMemBridge(db_path, config)
        
        # Test 1: Initial confidence should be 0.5, but after first success it increases
        result1 = bridge.get_or_compute(
            "Test confidence", "gemma3:1b",
            mock_llm_call("Success 1")
        )
        
        print(f"✅ Initial call - Confidence: {result1['confidence']['score']:.3f}, Stage: {result1['confidence']['stage']}")
        # After first success: confidence = 0.5 * 0.9 + 0.1 + 0.05 = 0.6
        assert abs(result1['confidence']['score'] - 0.6) < 0.01, f"Expected ~0.6, got {result1['confidence']['score']}"
        assert result1['confidence']['stage'] == "learning", f"Expected learning, got {result1['confidence']['stage']}"
        
        # Test 2: Success should increase confidence
        for i in range(5):
            result = bridge.get_or_compute(
                "Test confidence", "gemma3:1b",
                mock_llm_call(f"Success {i+2}")
            )
            time.sleep(1.1)  # Ensure cache expiry
        
        print(f"✅ After 6 successes - Confidence: {result['confidence']['score']:.3f}, Stage: {result['confidence']['stage']}")
        assert result['confidence']['score'] > 0.5, "Confidence should increase with successes"
        
        # Test 3: Failure should decrease confidence and increase failure streak
        original_confidence = result['confidence']['score']
        
        def failing_call() -> str:
            time.sleep(0.1)
            raise Exception("Mock failure")
        
        result_fail = bridge.get_or_compute(
            "Test confidence", "gemma3:1b",
            failing_call
        )
        
        print(f"✅ After 1 failure - Confidence: {result_fail['confidence']['score']:.3f}, Streak: {result_fail['confidence']['failure_streak']}")
        assert result_fail['confidence']['score'] < original_confidence, "Confidence should decrease after failure"
        assert result_fail['confidence']['failure_streak'] == 1, "Failure streak should be 1"
        
        print("🎉 Round 5.3 basic confidence scoring - PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def test_lifecycle_stages() -> bool:
    """Test lifecycle stage progression"""
    print("🧪 Testing Lifecycle Stage Progression...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        config = MemBridgeConfig(
            cache_duration_seconds=1,
            enable_environmental_context=True
        )
        bridge = ConvergedMemBridge(db_path, config)
        
        # Generate 15 successful calls to move through stages
        for i in range(15):
            result = bridge.get_or_compute(
                "Lifecycle test", "gemma3:1b",
                mock_llm_call(f"Success {i+1}")
            )
            time.sleep(1.1)  # Ensure cache expiry
            
            if i < 9:
                # First 10 calls should stay in learning
                assert result['confidence']['stage'] == "learning", f"Call {i+1} should be in learning stage"
            elif result['confidence']['score'] >= 0.3:
                # After 10 calls, should progress based on confidence
                print(f"✅ Call {i+1} - Confidence: {result['confidence']['score']:.3f}, Stage: {result['confidence']['stage']}")
        
        # Final result should have progressed beyond learning
        final_stage = result['confidence']['stage']
        final_confidence = result['confidence']['score']
        
        print(f"✅ Final state - Confidence: {final_confidence:.3f}, Stage: {final_stage}")
        assert final_stage in ["developing", "stable", "trusted"], f"Expected progression beyond learning, got {final_stage}"
        
        print("🎉 Lifecycle stage progression - PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main() -> bool:
    """Run basic Round 5.3 validation tests"""
    print("🚀 Round 5.3 Adaptive Confidence - Basic Validation")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    if test_confidence_scoring():
        success_count += 1
    
    if test_lifecycle_stages():
        success_count += 1
    
    print("=" * 50)
    print(f"📊 Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 Round 5.3 Basic Implementation - SUCCESS!")
        return True
    else:
        print("❌ Round 5.3 Basic Implementation - FAILURE!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
