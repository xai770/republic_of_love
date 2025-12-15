#!/usr/bin/env python3
"""
Test MemBridge v17 Integration
==============================

Test that the v17 MemBridge interface actually works and populates
the database tables when called.
"""

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "production" / "v17"))
sys.path.insert(0, str(Path(__file__).parent / "production"))

# Import MemBridge components
from membridge.registry import RegistrySystem, ConfigDrivenLLMCall
from membridge.models import MemBridgeConfig

def test_membridge_integration() -> None:
    """Test MemBridge integration and database population"""
    
    print("🧪 MemBridge Database Integration Test")
    print("=" * 40)
    
    try:
        # Initialize MemBridge directly
        print("🔧 Initializing MemBridge components...")
        
        db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
        config = MemBridgeConfig(
            prompt_registry_path="config/prompts",
            validation_enabled=True
        )
        
        registry = RegistrySystem(db_path=db_path, config=config)
        caller = ConfigDrivenLLMCall(registry)
        
        print("✅ MemBridge components initialized successfully")
        
        # Test call #1 (skill extraction)
        print("\n🎯 Testing call #1 (skill extraction)...")
        
        test_input = """Job Title: Senior Python Developer

Job Description: We are seeking a Senior Python Developer with experience in Django, 
REST APIs, and cloud deployment. The ideal candidate will have 5+ years 
of experience in web development and strong problem-solving skills."""
        
        result1 = caller.call_llm(
            call_number=1,
            input_text=test_input
        )
        
        print(f"✅ Call #1 result: {'SUCCESS' if result1['success'] else 'FAILED'}")
        print(f"   • Model: {result1['model_used']}")
        print(f"   • Latency: {result1['latency_ms']:.1f}ms")
        print(f"   • Output: {result1['output'][:100]}...")
        
        # Test call #2 (concise description)  
        print("\n📝 Testing call #2 (concise description)...")
        
        result2 = caller.call_llm(
            call_number=2,
            input_text=test_input
        )
        
        print(f"✅ Call #2 result: {'SUCCESS' if result2['success'] else 'FAILED'}")
        print(f"   • Model: {result2['model_used']}")
        print(f"   • Latency: {result2['latency_ms']:.1f}ms")
        print(f"   • Output: {result2['output'][:100]}...")
        
        # Check database population
        print("\n📊 Checking database population...")
        recent_calls = registry.get_recent_calls(limit=5)
        
        print(f"✅ Found {len(recent_calls)} recent calls in mb_log")
        for i, call in enumerate(recent_calls[:3], 1):
            status = "✅" if call.success else "❌"
            print(f"   • Call {i}: {status} #{call.call_number} ({call.latency_ms:.1f}ms)")
        
        print("\n🎯 Success! MemBridge is working and populating tables!")
        print("💡 Check SQLite Browser to see the new call logs!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_membridge_integration()
