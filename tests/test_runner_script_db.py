#!/usr/bin/env python3
"""
Quick test to verify by_recipe_runner.py can execute script actors from DB
"""

import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn/scripts')

from by_recipe_runner import BYRecipeRunner

def test_script_actor():
    """Test executing a script actor from database"""
    runner = BYRecipeRunner()
    
    # Test with dictionary_lookup_script (actor_id=6)
    print("Testing script execution from database...")
    print("=" * 60)
    
    test_prompt = "test"  # Simple test input
    
    try:
        result = runner.execute_instruction(
            actor_id=6,  # dictionary_lookup_script
            prompt=test_prompt,
            timeout=10
        )
        
        print(f"✅ Script executed successfully!")
        print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_model():
    """Test executing an AI model actor"""
    runner = BYRecipeRunner()
    
    print("\nTesting AI model execution...")
    print("=" * 60)
    
    test_prompt = "Say hello in one word"
    
    try:
        result = runner.execute_instruction(
            actor_id=3,  # codegemma:2b
            prompt=test_prompt,
            timeout=30
        )
        
        print(f"✅ AI model executed successfully!")
        print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ AI model execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("BY Recipe Runner - DB-Stored Script Test")
    print("=" * 60)
    
    script_ok = test_script_actor()
    ai_ok = test_ai_model()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Script Actor: {'✅ PASS' if script_ok else '❌ FAIL'}")
    print(f"  AI Model:     {'✅ PASS' if ai_ok else '❌ FAIL'}")
    print("=" * 60)
    
    sys.exit(0 if (script_ok and ai_ok) else 1)
