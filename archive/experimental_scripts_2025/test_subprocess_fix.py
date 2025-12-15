#!/usr/bin/env python3
"""
Test the subprocess fix for reverse string gradient
"""

import subprocess
import time

def test_subprocess_fix():
    """Test if the subprocess stdin fix works"""
    
    model = "gemma2:latest"
    word = "cat"
    expected = "[tac]"
    
    prompt = f"""## Processing Instructions
Format your response as [string]. Make sure to include the brackets in the output.

## Processing Payload
Write "{word}" backwards.

## QA Check
Submit ONLY the required response. Do not add spaces. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
    
    print(f"🔄 Testing subprocess fix with {model}")
    print(f"📝 Word: {word} -> Expected: {expected}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            'ollama', 'run', model, prompt
        ], capture_output=True, text=True, timeout=30, input="")
        
        latency = time.time() - start_time
        
        if result.returncode == 0:
            response = result.stdout.strip()
            is_correct = response == expected
            
            print(f"✅ Success!")
            print(f"📤 Response: '{response}'")
            print(f"🎯 Expected: '{expected}'")
            print(f"✓ Correct: {is_correct}")
            print(f"⏱️  Latency: {latency:.1f}s")
            
            return True
        else:
            print(f"❌ Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    test_subprocess_fix()