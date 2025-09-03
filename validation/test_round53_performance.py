#!/usr/bin/env python3
"""
Round 5.3 Performance and Stability Validation
Tests remaining success criteria: 80% stable rate and >70% cache hit rate
"""

import sys
import os
import tempfile
import time
import random
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


def failing_llm_call(error_message: str = "Mock failure") -> Callable[[], str]:
    """Mock failing LLM call for testing."""
    def call() -> str:
        time.sleep(0.1)
        raise Exception(error_message)
    return call


def test_80_percent_stable_achievement() -> bool:
    """Test that 80% of templates reach stable status within 100 calls"""
    print("🧪 Testing 80% Stable Achievement Rate...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        config = MemBridgeConfig(
            cache_duration_seconds=1,
            enable_environmental_context=True
        )
        bridge = ConvergedMemBridge(db_path, config)
        
        # Test 20 different templates with realistic success patterns
        template_results = []
        
        for template_id in range(20):
            template_name = f"Template {template_id}"
            
            # Simulate realistic patterns with some variation
            success_rate = random.uniform(0.75, 0.95)  # Most templates should be fairly reliable
            
            confidence_progression = []
            stage_progression = []
            
            for call_num in range(100):
                is_success = random.random() < success_rate
                
                if is_success:
                    result = bridge.get_or_compute(
                        template_name, "gemma3:1b",
                        mock_llm_call(f"Success {call_num}")
                    )
                else:
                    result = bridge.get_or_compute(
                        template_name, "gemma3:1b",
                        failing_llm_call(f"Failure {call_num}")
                    )
                
                confidence_progression.append(result['confidence']['score'])
                stage_progression.append(result['confidence']['stage'])
                
                time.sleep(1.1)  # Ensure cache expiry
            
            # Check final stage
            final_stage = stage_progression[-1]
            final_confidence = confidence_progression[-1]
            
            is_stable_or_higher = final_stage in ["stable", "trusted"]
            template_results.append({
                'template': template_name,
                'final_stage': final_stage,
                'final_confidence': final_confidence,
                'success_rate': success_rate,
                'achieved_stable': is_stable_or_higher
            })
            
            print(f"✅ {template_name}: {final_stage} (confidence: {final_confidence:.3f})")
        
        # Calculate percentage that reached stable or higher
        stable_count = sum(1 for r in template_results if r['achieved_stable'])
        stable_percentage = (stable_count / len(template_results)) * 100
        
        print(f"\n📊 Results: {stable_count}/{len(template_results)} templates reached stable+ ({stable_percentage:.1f}%)")
        
        # Success criteria: 80% reach stable or higher
        success = stable_percentage >= 80.0
        
        if success:
            print("🎉 80% Stable Achievement - PASSED!")
        else:
            print(f"❌ 80% Stable Achievement - FAILED (only {stable_percentage:.1f}%)")
        
        return success
        
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


def test_cache_hit_rate_maintenance() -> bool:
    """Test that system maintains >70% cache hit rate with adaptive sampling"""
    print("🧪 Testing Cache Hit Rate Maintenance...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        config = MemBridgeConfig(
            cache_duration_seconds=3600,  # Long cache duration to enable hits
            enable_environmental_context=True
        )
        bridge = ConvergedMemBridge(db_path, config)
        
        # Phase 1: Build up templates with different confidence levels
        templates = [
            "High confidence template",
            "Medium confidence template", 
            "Learning template",
            "Variable reliability template"
        ]
        
        # Build confidence for different templates
        for template in templates:
            # Give them different patterns
            if "High confidence" in template:
                # 15 successes to build high confidence
                for i in range(15):
                    bridge.get_or_compute(
                        template, "gemma3:1b",
                        mock_llm_call(f"Success {i}")
                    )
                    time.sleep(1.1)
            elif "Medium confidence" in template:
                # 10 successes to build medium confidence
                for i in range(10):
                    bridge.get_or_compute(
                        template, "gemma3:1b",
                        mock_llm_call(f"Success {i}")
                    )
                    time.sleep(1.1)
            elif "Learning" in template:
                # Just a few calls, still learning
                for i in range(3):
                    bridge.get_or_compute(
                        template, "gemma3:1b",
                        mock_llm_call(f"Learning {i}")
                    )
                    time.sleep(1.1)
            else:
                # Variable pattern with some failures
                for i in range(8):
                    if random.random() < 0.7:  # 70% success rate
                        bridge.get_or_compute(
                            template, "gemma3:1b",
                            mock_llm_call(f"Variable success {i}")
                        )
                    else:
                        bridge.get_or_compute(
                            template, "gemma3:1b",
                            failing_llm_call(f"Variable failure {i}")
                        )
                    time.sleep(1.1)
        
        # Phase 2: Run realistic workload and measure cache hit rate
        total_calls = 0
        cache_hits = 0
        
        # Simulate realistic usage patterns with repeated calls to same templates
        for workload_cycle in range(10):  # 10 cycles of varied usage
            for _ in range(20):  # 20 calls per cycle
                # 80% of calls use existing templates (more realistic)
                if random.random() < 0.8:
                    template = random.choice(templates)
                else:
                    template = f"New template {workload_cycle}_{random.randint(1, 5)}"
                
                result = bridge.get_or_compute(
                    template, "gemma3:1b",
                    mock_llm_call(f"Workload call {total_calls}")
                )
                
                total_calls += 1
                if result['cached']:
                    cache_hits += 1
        
        # Calculate cache hit rate
        cache_hit_rate = (cache_hits / total_calls) * 100 if total_calls > 0 else 0
        
        print(f"📊 Cache Performance: {cache_hits}/{total_calls} hits ({cache_hit_rate:.1f}%)")
        
        # Success criteria: >70% cache hit rate
        success = cache_hit_rate > 70.0
        
        if success:
            print("🎉 Cache Hit Rate Maintenance - PASSED!")
        else:
            print(f"❌ Cache Hit Rate Maintenance - FAILED ({cache_hit_rate:.1f}% < 70%)")
        
        return success
        
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
    """Run Round 5.3 performance validation tests"""
    print("🚀 Round 5.3 Performance & Stability Validation")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    print("Testing remaining success criteria for Round 5.3...")
    print()
    
    if test_80_percent_stable_achievement():
        success_count += 1
    
    print()
    
    if test_cache_hit_rate_maintenance():
        success_count += 1
    
    print("=" * 60)
    print(f"📊 Results: {success_count}/{total_tests} performance criteria met")
    
    if success_count == total_tests:
        print("🎉 Round 5.3 Performance Validation - SUCCESS!")
        print("All remaining success criteria achieved!")
        return True
    else:
        print("❌ Round 5.3 Performance Validation - PARTIAL SUCCESS")
        print(f"Met {success_count}/2 remaining criteria")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
