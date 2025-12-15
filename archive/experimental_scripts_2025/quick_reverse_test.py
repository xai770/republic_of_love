#!/usr/bin/env python3
"""
Quick Reverse String Gradient Test
=================================
Test a few fast models on the reverse string gradient to validate the system.
"""

import json
import csv
import sqlite3
import subprocess
import time
import logging
import os
from datetime import datetime
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_reverse_test():
    """Run a quick test on select fast models"""
    
    # Select fast, reliable models for testing
    test_models = [
        'dolphin3:latest',
        'gemma2:latest', 
        'gemma3:1b',
        'phi3:latest'
    ]
    
    # Load some test parameters
    conn = sqlite3.connect('data/llmcore.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT content, length, target_letter
        FROM word_banks
        WHERE category = 'reverse_string_gradient'
        AND length IN (2, 5, 10, 15, 20)
        ORDER BY length, content
        LIMIT 10
    """)
    
    parameters = []
    for row in cursor.fetchall():
        word = row[0]
        difficulty = row[1]
        reversed_word = row[2]
        expected = f"[{reversed_word}]"
        
        parameters.append({
            'word': word,
            'reversed': reversed_word,
            'expected': expected,
            'difficulty': difficulty
        })
    
    conn.close()
    
    results = []
    
    print(f"🔄 QUICK REVERSE STRING GRADIENT TEST")
    print(f"📊 Models: {len(test_models)}")
    print(f"📊 Test words: {len(parameters)}")
    print("="*50)
    
    for model in test_models:
        print(f"\n🤖 Testing: {model}")
        model_correct = 0
        
        for param in parameters:
            prompt = f"""## Processing Instructions
Format your response as [string]. Make sure to include the brackets in the output.

## Processing Payload
Write "{param['word']}" backwards.

## QA Check
Submit ONLY the required response. Do not add spaces. Do not include quotation marks, apostrophes, or any other punctuation inside the brackets."""
            
            start_time = time.time()
            
            try:
                result = subprocess.run([
                    'ollama', 'run', model, prompt
                ], capture_output=True, text=True, timeout=30)
                
                latency = time.time() - start_time
                
                if result.returncode == 0:
                    response = result.stdout.strip()
                    is_correct = response == param['expected']
                    
                    if is_correct:
                        status = "✅"
                        model_correct += 1
                    else:
                        status = "❌"
                    
                    print(f"   {param['word']:15s} ({param['difficulty']:2d}) -> {param['expected']:20s} | {response:20s} {status} ({latency:.1f}s)")
                    
                else:
                    print(f"   {param['word']:15s} ({param['difficulty']:2d}) -> ERROR: {result.stderr.strip()[:30]}")
            
            except Exception as e:
                print(f"   {param['word']:15s} ({param['difficulty']:2d}) -> ERROR: {str(e)[:30]}")
        
        accuracy = (model_correct / len(parameters)) * 100
        print(f"   📊 {model}: {model_correct}/{len(parameters)} ({accuracy:.1f}%)")

if __name__ == "__main__":
    quick_reverse_test()