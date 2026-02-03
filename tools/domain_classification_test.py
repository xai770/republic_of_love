#!/usr/bin/env python3
"""
Domain Classification Test: Can small LLMs reliably classify job domains?

Tests multiple models on a set of job postings with known domains.

Author: Sandy
Date: 2026-01-28
"""

import subprocess
import json
import time

MODELS = [
    'gemma3:1b',      # 815 MB - tiny
    'gemma3:4b',      # 3.3 GB - small  
    'phi4-mini',      # 2.5 GB - small
    'qwen2.5:7b',     # 4.7 GB - medium
]

# Nate's domains (with Legal added explicitly)
DOMAINS = """Banking, Insurance, FinTech, Real Estate, Healthcare, Pharma, Medical Devices, 
Public Sector, Defense, Law Enforcement, Education, Research, Energy, Utilities, Telecoms, 
Software/IT, Hardware, Manufacturing, Automotive, Transportation, Retail, Consumer Goods, 
Media, Travel, Agriculture, Construction, Legal/Consulting, Nonprofit, Environmental"""

# Test cases with expected answers
TEST_CASES = [
    ("Senior Software Engineer - Trading Systems", "Goldman Sachs", "Banking"),
    ("Registered Nurse - ICU", "Mayo Clinic", "Healthcare"),
    ("Corporate Lawyer - M&A", "Freshfields Bruckhaus Deringer", "Legal/Consulting"),
    ("Data Scientist", "Pfizer", "Pharma"),
    ("Police Officer", "NYPD", "Law Enforcement"),
    ("High School Teacher", "Lincoln High School", "Education"),
    ("Petroleum Engineer", "Shell", "Energy"),
    ("DevOps Engineer", "Netflix", "Software/IT"),
    ("Marketing Manager", "Procter & Gamble", "Consumer Goods"),
    ("Flight Attendant", "Lufthansa", "Travel"),
    ("Sustainability Analyst", "WWF", "Environmental"),
    ("Investment Analyst", "BlackRock", "FinTech"),  # or Banking?
    ("Lagerarbeiter", "Amazon Logistik", "Transportation"),  # German: warehouse worker
    ("Sachbearbeiter Versicherung", "Allianz", "Insurance"),  # German: insurance clerk
]

def test_model(model: str) -> dict:
    """Test a model on all cases."""
    results = {'correct': 0, 'wrong': 0, 'details': []}
    
    prompt_template = f"""Classify this job into exactly ONE domain.

DOMAINS: {DOMAINS}

JOB: {{title}} at {{company}}

Reply with ONLY the domain name, nothing else."""

    for title, company, expected in TEST_CASES:
        prompt = prompt_template.format(title=title, company=company)
        
        try:
            result = subprocess.run(
                ['ollama', 'run', model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            answer = result.stdout.strip().split('\n')[0]  # First line only
            
            # Fuzzy match (contains expected or vice versa)
            correct = (expected.lower() in answer.lower()) or (answer.lower() in expected.lower())
            
            if correct:
                results['correct'] += 1
                status = '✅'
            else:
                results['wrong'] += 1
                status = '❌'
            
            results['details'].append({
                'title': title,
                'expected': expected,
                'got': answer,
                'correct': correct
            })
            
            print(f"   {status} {title[:30]:<30} expected={expected:<20} got={answer}")
            
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            results['wrong'] += 1
    
    return results

def main():
    print("="*80)
    print("🔬 DOMAIN CLASSIFICATION TEST: Can small LLMs do this?")
    print("="*80)
    
    all_results = {}
    
    for model in MODELS:
        print(f"\n{'─'*80}")
        print(f"Testing {model}...")
        print(f"{'─'*80}")
        
        start = time.time()
        results = test_model(model)
        elapsed = time.time() - start
        
        accuracy = results['correct'] / len(TEST_CASES) * 100
        all_results[model] = {
            'accuracy': accuracy,
            'time': elapsed,
            'correct': results['correct'],
            'total': len(TEST_CASES)
        }
        
        print(f"\n   Accuracy: {results['correct']}/{len(TEST_CASES)} = {accuracy:.0f}%")
        print(f"   Time: {elapsed:.1f}s ({elapsed/len(TEST_CASES):.1f}s per case)")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"\n{'Model':<25} {'Accuracy':>10} {'Time':>10} {'Per case':>10}")
    print("-"*55)
    
    for model, r in sorted(all_results.items(), key=lambda x: -x[1]['accuracy']):
        print(f"{model:<25} {r['correct']}/{r['total']:>3} ({r['accuracy']:>3.0f}%) {r['time']:>8.1f}s {r['time']/r['total']:>8.1f}s")

if __name__ == '__main__':
    main()
