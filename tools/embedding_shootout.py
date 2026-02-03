#!/usr/bin/env python3
"""
Embedding Model Shootout: Domain Separation

Which model best separates professional domains?
- bge-m3:567m (current)
- snowflake-arctic-embed2 (Arctic Embed 2.0)
- nomic-embed-text (lightweight MoE)

Author: Sandy
Date: 2026-01-28
"""

import requests
import numpy as np
from typing import List, Dict
import time

OLLAMA_URL = 'http://localhost:11434/api/embeddings'

MODELS = [
    'bge-m3:567m',
    'snowflake-arctic-embed2',
    'nomic-embed-text',
]

# Domain clusters for testing
DOMAINS = {
    "legal": [
        "legal counsel",
        "attorney at law", 
        "corporate lawyer",
        "litigation specialist",
        "Rechtsanwalt",
    ],
    "medical": [
        "physician",
        "registered nurse",
        "surgeon",
        "clinical director",
        "Arzt",
    ],
    "tech": [
        "software engineer",
        "backend developer",
        "full stack programmer",
        "DevOps engineer",
        "Softwareentwickler",
    ],
    "finance": [
        "financial analyst",
        "investment banker",
        "portfolio manager",
        "accountant",
        "Finanzberater",
    ],
    "marketing": [
        "marketing manager",
        "brand strategist",
        "digital marketing specialist",
        "content manager",
        "SEO expert",
    ],
}

def get_embedding(text: str, model: str) -> np.ndarray:
    """Get embedding from Ollama."""
    response = requests.post(OLLAMA_URL, json={
        'model': model,
        'prompt': text
    })
    return np.array(response.json()['embedding'])

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_domain_separation(model: str) -> Dict:
    """Test domain separation for a model."""
    print(f"\n   Testing {model}...", end=" ", flush=True)
    start = time.time()
    
    # Get all embeddings
    embeddings = {}
    for domain, items in DOMAINS.items():
        for item in items:
            embeddings[(domain, item)] = get_embedding(item, model)
    
    elapsed = time.time() - start
    items_per_sec = len(embeddings) / elapsed
    
    # Calculate within-cluster similarities
    within_sims = []
    for domain, items in DOMAINS.items():
        for i, a in enumerate(items):
            for b in items[i+1:]:
                sim = cosine_similarity(embeddings[(domain, a)], embeddings[(domain, b)])
                within_sims.append(sim)
    
    # Calculate between-cluster similarities
    between_sims = []
    domain_names = list(DOMAINS.keys())
    for i, domain_a in enumerate(domain_names):
        for domain_b in domain_names[i+1:]:
            for item_a in DOMAINS[domain_a]:
                for item_b in DOMAINS[domain_b]:
                    sim = cosine_similarity(
                        embeddings[(domain_a, item_a)], 
                        embeddings[(domain_b, item_b)]
                    )
                    between_sims.append(sim)
    
    within_avg = np.mean(within_sims)
    between_avg = np.mean(between_sims)
    gap = within_avg - between_avg
    
    print(f"done ({elapsed:.1f}s, {items_per_sec:.1f}/sec)")
    
    return {
        'model': model,
        'within_avg': within_avg,
        'between_avg': between_avg,
        'gap': gap,
        'speed': items_per_sec,
        'dims': len(embeddings[(domain_names[0], DOMAINS[domain_names[0]][0])]),
    }

def test_critical_pairs(model: str) -> Dict:
    """Test specific pairs that matter for domain gates."""
    pairs = [
        ("software engineer", "legal counsel"),
        ("software engineer", "physician"),
        ("accountant", "financial analyst"),  # Should be similar
        ("nurse", "doctor"),  # Should be similar
        ("Softwareentwickler", "software engineer"),  # Cross-lingual, same domain
    ]
    
    results = []
    for a, b in pairs:
        emb_a = get_embedding(a, model)
        emb_b = get_embedding(b, model)
        sim = cosine_similarity(emb_a, emb_b)
        results.append((a, b, sim))
    
    return results

def main():
    print("="*70)
    print("🔬 EMBEDDING MODEL SHOOTOUT: Domain Separation")
    print("="*70)
    print("\nQuestion: Which model best separates professional domains?")
    print("Goal: HIGH within-cluster, LOW between-cluster, BIG gap")
    
    results = []
    for model in MODELS:
        result = test_domain_separation(model)
        results.append(result)
    
    # Print comparison table
    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)
    print(f"\n{'Model':<30} {'Within':>8} {'Between':>8} {'GAP':>8} {'Speed':>10} {'Dims':>6}")
    print("-"*70)
    
    # Sort by gap (best separation)
    results.sort(key=lambda x: x['gap'], reverse=True)
    
    for r in results:
        gap_indicator = "🥇" if r == results[0] else "  "
        print(f"{gap_indicator}{r['model']:<28} {r['within_avg']:>8.3f} {r['between_avg']:>8.3f} {r['gap']:>8.3f} {r['speed']:>8.1f}/s {r['dims']:>6}")
    
    print("\n" + "="*70)
    print("🎯 CRITICAL PAIR TESTS (winner only)")
    print("="*70)
    
    winner = results[0]['model']
    pairs = test_critical_pairs(winner)
    print(f"\nUsing {winner}:")
    for a, b, sim in pairs:
        status = "✅" if sim < 0.5 else "⚠️" if sim < 0.7 else "❌"
        print(f"   {status} {sim:.3f}  '{a}' ↔ '{b}'")
    
    print("\n" + "="*70)
    print("📋 VERDICT")
    print("="*70)
    
    best = results[0]
    current = next(r for r in results if r['model'] == 'bge-m3:567m')
    
    if best['model'] == 'bge-m3:567m':
        print(f"\n   BGE-M3 is still the best for domain separation!")
        print(f"   Gap: {best['gap']:.3f}")
    else:
        improvement = ((best['gap'] - current['gap']) / current['gap']) * 100
        print(f"\n   🏆 WINNER: {best['model']}")
        print(f"   Gap improvement over BGE-M3: {improvement:+.1f}%")
        print(f"   BGE-M3 gap: {current['gap']:.3f} → {best['model']} gap: {best['gap']:.3f}")
        
        if best['speed'] < current['speed'] * 0.5:
            print(f"\n   ⚠️  But it's {current['speed']/best['speed']:.1f}x slower")
        elif best['speed'] > current['speed']:
            print(f"\n   ✅ And it's {best['speed']/current['speed']:.1f}x faster!")

if __name__ == '__main__':
    main()
