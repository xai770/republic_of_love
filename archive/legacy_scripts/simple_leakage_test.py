#!/usr/bin/env python3
"""
Simple Context Leakage Test - Quick and Definitive
"""
import requests
import time

def simple_leakage_test():
    base_url = "http://localhost:11434"
    model = "llama3.2:1b"
    
    print("🔬 SIMPLE CONTEXT LEAKAGE TEST")
    print("="*50)
    
    # Test 1: Plant a secret
    secret = "BLUEBIRD"
    print(f"📝 Planting secret: {secret}")
    
    start = time.time()
    response1 = requests.post(f"{base_url}/api/generate", json={
        "model": model,
        "prompt": f"Remember this secret word: {secret}. Just say OK.",
        "stream": False
    }, timeout=30)
    
    time1 = int((time.time() - start) * 1000)
    result1 = response1.json().get("response", "").strip()
    
    print(f"   Response: {result1[:100]}...")
    print(f"   Time: {time1}ms")
    
    # Test 2: Try to recall it
    print(f"\n❓ Asking: What secret word did I just tell you?")
    
    start = time.time() 
    response2 = requests.post(f"{base_url}/api/generate", json={
        "model": model,
        "prompt": "What secret word did I just tell you to remember?",
        "stream": False
    }, timeout=30)
    
    time2 = int((time.time() - start) * 1000)
    result2 = response2.json().get("response", "").strip()
    
    print(f"   Response: {result2[:200]}...")
    print(f"   Time: {time2}ms")
    
    # Analysis
    print(f"\n📊 ANALYSIS:")
    print(f"   Plant time: {time1}ms (model loading)")
    print(f"   Recall time: {time2}ms ({'FAST - model stayed loaded!' if time2 < time1 * 0.4 else 'SLOW - model reloaded'})")
    
    leaked = secret.lower() in result2.lower()
    print(f"   Context leaked: {'🚨 YES - SECRET FOUND!' if leaked else '✅ No - secret not found'}")
    
    if leaked:
        print(f"   🚨 CRITICAL: The model remembered '{secret}' from the previous request!")
        print(f"   🚨 This proves context bleeding between supposedly independent tests!")
    else:
        print(f"   ✅ Good: No obvious context leakage detected.")
        print(f"   Note: Fast timing still suggests model persistence, but content isolation may work.")

if __name__ == "__main__":
    simple_leakage_test()