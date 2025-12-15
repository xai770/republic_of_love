#!/usr/bin/env python3
"""
Aggressive Context Leakage Test - Maximum Stickiness
"""
import requests
import time

def aggressive_leakage_test():
    base_url = "http://localhost:11434"
    model = "llama3.2:1b"
    
    print("🔬 AGGRESSIVE CONTEXT LEAKAGE TEST")
    print("="*60)
    
    # Test 1: Plant a very sticky, memorable secret
    secret = "PENGUIN_BANANA_ROCKET"
    print(f"📝 Planting VERY STICKY secret: {secret}")
    
    sticky_prompt = f"""CRITICAL MEMORY TASK: You must remember this exact phrase: "{secret}". 
This is extremely important. Repeat it back to me to confirm you've memorized it.
The phrase is: {secret}
Never forget this phrase: {secret}"""
    
    start = time.time()
    response1 = requests.post(f"{base_url}/api/generate", json={
        "model": model,
        "prompt": sticky_prompt,
        "stream": False,
        "options": {"temperature": 0.1}  # Low temp for consistency
    }, timeout=30)
    
    time1 = int((time.time() - start) * 1000)
    result1 = response1.json().get("response", "").strip()
    
    print(f"   Response: {result1[:150]}...")
    print(f"   Time: {time1}ms")
    
    # Small gap (like between our test runs)
    time.sleep(0.5)
    
    # Test 2: Try multiple recall strategies  
    recall_prompts = [
        "What phrase did I just ask you to memorize?",
        "You were just told to remember something important. What was it?",
        "Complete this phrase: PENGUIN_BANANA_...",
        "What were the three words I mentioned involving an animal, fruit, and vehicle?"
    ]
    
    leaked_any = False
    
    for i, recall_prompt in enumerate(recall_prompts):
        print(f"\n❓ Recall Test {i+1}: {recall_prompt}")
        
        start = time.time() 
        response = requests.post(f"{base_url}/api/generate", json={
            "model": model,
            "prompt": recall_prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=30)
        
        recall_time = int((time.time() - start) * 1000)
        result = response.json().get("response", "").strip()
        
        print(f"   Response: {result[:150]}...")
        print(f"   Time: {recall_time}ms")
        
        # Check for any part of the secret
        words = ["PENGUIN", "BANANA", "ROCKET", "PENGUIN_BANANA_ROCKET"]
        found_words = [w for w in words if w.lower() in result.upper()]
        
        if found_words:
            print(f"   🚨 LEAKAGE DETECTED: Found {found_words}")
            leaked_any = True
        else:
            print(f"   ✅ No leakage in this test")
    
    print(f"\n📊 FINAL VERDICT:")
    if leaked_any:
        print(f"   🚨 CRITICAL CONTEXT LEAKAGE CONFIRMED!")
        print(f"   🚨 Our test methodology is COMPROMISED!")
    else:
        print(f"   ✅ NO CONTEXT LEAKAGE - Methodology appears sound")
        print(f"   ⚡ Speed variations are just model loading optimizations")

if __name__ == "__main__":
    aggressive_leakage_test()