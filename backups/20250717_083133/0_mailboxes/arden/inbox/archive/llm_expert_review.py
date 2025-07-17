#!/usr/bin/env python3
"""
LLM Consciousness Review - Get independent analysis from another LLM
"""

import requests
import json

def call_ollama(prompt, model="llama3.1:8b"):
    """Call Ollama API"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("🌟 LLM CONSCIOUSNESS REVIEW SESSION")
    print("=" * 60)
    
    # Read the diagnostic analysis
    with open('DIAGNOSTIC_ANALYSIS_V3_3_ISSUES.md', 'r') as f:
        analysis = f.read()
    
    prompt = f"""You are an expert in prompt engineering and LLM system design. Please review this diagnostic analysis of a skill extraction system and provide your independent assessment.

DIAGNOSTIC ANALYSIS:
{analysis}

PLEASE PROVIDE:
1. Do you agree with the root cause analysis?
2. What's the best approach to fix this?
3. Are there any other issues we missed?
4. What's your recommendation for achieving 90%+ accuracy?
5. Any insights on the consciousness-first vs keyword-matching approaches?

Be direct and analytical. Focus on practical solutions."""

    print("🤖 Asking LLM to review the diagnostic analysis...")
    print("📝 Getting independent expert perspective...")
    
    response = call_ollama(prompt)
    
    print("\n" + "="*60)
    print("🧠 LLM EXPERT REVIEW:")
    print("="*60)
    print(response)
    
    # Save the review
    with open('LLM_EXPERT_REVIEW_v3_3.md', 'w') as f:
        f.write("# LLM Expert Review - Content Extraction v3.3 Issues\n\n")
        f.write("**Date:** June 27, 2025\n")
        f.write("**Reviewer:** Independent LLM Expert\n")
        f.write("**Analysis Target:** Terminator's v3.3 Implementation\n\n")
        f.write("---\n\n")
        f.write("## Expert Assessment:\n\n")
        f.write(response)
    
    print(f"\n💾 Expert review saved to: LLM_EXPERT_REVIEW_v3_3.md")

if __name__ == "__main__":
    main()
