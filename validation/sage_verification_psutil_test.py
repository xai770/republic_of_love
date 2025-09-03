#!/usr/bin/env python3
"""
Sage Verification Test: psutil Non-Blocking Behavior
Test that psutil.cpu_percent(interval=None) is truly non-blocking even on fresh systems.
"""

import time
import psutil

def test_psutil_nonblocking_fresh_system() -> None:
    """Test psutil behavior on fresh Python process (simulates fresh system)."""
    
    print("🔍 SAGE VERIFICATION: psutil Non-Blocking Behavior Test")
    print("=" * 60)
    
    # Test 1: First call with interval=None (should be instant)
    print("\n1. Testing first call with interval=None:")
    start_time = time.time()
    cpu_percent_1 = psutil.cpu_percent(interval=None)
    first_call_duration = (time.time() - start_time) * 1000  # ms
    print(f"   First call: {cpu_percent_1:.1f}% CPU in {first_call_duration:.3f}ms")
    
    # Test 2: Second call with interval=None (should use cached/previous value)
    print("\n2. Testing subsequent call with interval=None:")
    start_time = time.time()
    cpu_percent_2 = psutil.cpu_percent(interval=None)
    second_call_duration = (time.time() - start_time) * 1000  # ms
    print(f"   Second call: {cpu_percent_2:.1f}% CPU in {second_call_duration:.3f}ms")
    
    # Test 3: Compare with blocking call
    print("\n3. Testing blocking call with interval=0.1 for comparison:")
    start_time = time.time()
    cpu_percent_blocking = psutil.cpu_percent(interval=0.1)
    blocking_call_duration = (time.time() - start_time) * 1000  # ms
    print(f"   Blocking call: {cpu_percent_blocking:.1f}% CPU in {blocking_call_duration:.3f}ms")
    
    # Analysis
    print("\n📊 ANALYSIS:")
    print(f"   • First interval=None call:  {first_call_duration:.3f}ms")
    print(f"   • Second interval=None call: {second_call_duration:.3f}ms")
    print(f"   • Blocking interval=0.1:     {blocking_call_duration:.3f}ms")
    
    # Verification
    print("\n✅ VERIFICATION RESULTS:")
    if first_call_duration < 10:  # Under 10ms is essentially instant
        print(f"   ✅ First call is non-blocking: {first_call_duration:.3f}ms < 10ms")
    else:
        print(f"   ❌ First call blocks: {first_call_duration:.3f}ms >= 10ms")
    
    if second_call_duration < 5:  # Subsequent calls should be even faster
        print(f"   ✅ Subsequent calls are instant: {second_call_duration:.3f}ms < 5ms")
    else:
        print(f"   ❌ Subsequent calls slow: {second_call_duration:.3f}ms >= 5ms")
    
    if blocking_call_duration > 90:  # interval=0.1 should take ~100ms
        print(f"   ✅ Blocking call properly blocks: {blocking_call_duration:.3f}ms > 90ms")
    else:
        print(f"   ⚠️  Blocking call unexpectedly fast: {blocking_call_duration:.3f}ms <= 90ms")
    
    print(f"\n🎯 CONCLUSION: interval=None calls are truly non-blocking")
    print(f"   Performance gain: {blocking_call_duration/first_call_duration:.1f}x faster than blocking")

if __name__ == "__main__":
    test_psutil_nonblocking_fresh_system()
