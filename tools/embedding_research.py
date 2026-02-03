#!/usr/bin/env python3
"""
Embedding Research: What does bge-m3 know?

Tests embedding space separation for various dimensions yogis might filter by.
Run: python3 tools/embedding_research.py

Author: Sandy
Date: 2026-01-28
"""

import requests
import numpy as np
from typing import List, Tuple, Dict
import json

OLLAMA_URL = 'http://localhost:11434/api/embeddings'
MODEL = 'bge-m3:567m'

def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Ollama."""
    response = requests.post(OLLAMA_URL, json={
        'model': MODEL,
        'prompt': text
    })
    return np.array(response.json()['embedding'])

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_pairs(category: str, pairs: List[Tuple[str, str]], expect_similar: bool = True):
    """Test similarity between pairs of concepts."""
    print(f"\n{'='*60}")
    print(f"📊 {category}")
    print(f"   Expectation: {'SIMILAR (>0.7)' if expect_similar else 'DIFFERENT (<0.5)'}")
    print(f"{'='*60}")
    
    results = []
    for a, b in pairs:
        emb_a = get_embedding(a)
        emb_b = get_embedding(b)
        sim = cosine_similarity(emb_a, emb_b)
        
        # Determine if it matches expectation
        if expect_similar:
            status = "✅" if sim >= 0.7 else "⚠️" if sim >= 0.5 else "❌"
        else:
            status = "✅" if sim < 0.5 else "⚠️" if sim < 0.7 else "❌"
        
        print(f"   {status} {sim:.3f}  '{a}' ↔ '{b}'")
        results.append((a, b, sim))
    
    avg = np.mean([r[2] for r in results])
    print(f"   ────────────────────────────────────────────────")
    print(f"   Average: {avg:.3f}")
    return results

def test_clusters(category: str, clusters: Dict[str, List[str]]):
    """Test if items within clusters are similar and between clusters are different."""
    print(f"\n{'='*60}")
    print(f"📊 {category} - Cluster Analysis")
    print(f"   Within-cluster: want HIGH (>0.7)")
    print(f"   Between-cluster: want LOW (<0.5)")
    print(f"{'='*60}")
    
    # Get all embeddings
    embeddings = {}
    for cluster_name, items in clusters.items():
        for item in items:
            embeddings[item] = get_embedding(item)
    
    # Within-cluster similarities
    print(f"\n   Within-cluster similarities:")
    within_sims = []
    for cluster_name, items in clusters.items():
        cluster_sims = []
        for i, a in enumerate(items):
            for b in items[i+1:]:
                sim = cosine_similarity(embeddings[a], embeddings[b])
                cluster_sims.append(sim)
        if cluster_sims:
            avg = np.mean(cluster_sims)
            status = "✅" if avg >= 0.7 else "⚠️" if avg >= 0.5 else "❌"
            print(f"      {status} {cluster_name}: {avg:.3f}")
            within_sims.extend(cluster_sims)
    
    # Between-cluster similarities
    print(f"\n   Between-cluster similarities:")
    between_sims = []
    cluster_names = list(clusters.keys())
    for i, name_a in enumerate(cluster_names):
        for name_b in cluster_names[i+1:]:
            pair_sims = []
            for item_a in clusters[name_a]:
                for item_b in clusters[name_b]:
                    sim = cosine_similarity(embeddings[item_a], embeddings[item_b])
                    pair_sims.append(sim)
            avg = np.mean(pair_sims)
            status = "✅" if avg < 0.5 else "⚠️" if avg < 0.7 else "❌"
            print(f"      {status} {name_a} ↔ {name_b}: {avg:.3f}")
            between_sims.extend(pair_sims)
    
    print(f"\n   Summary:")
    print(f"      Within-cluster avg:  {np.mean(within_sims):.3f}")
    print(f"      Between-cluster avg: {np.mean(between_sims):.3f}")
    print(f"      Separation gap:      {np.mean(within_sims) - np.mean(between_sims):.3f}")

def main():
    print("🔬 Embedding Research: What does bge-m3 know?")
    print("   Model: bge-m3:567m (1024 dims, multilingual)")
    
    # =========================================================================
    # 1. GEOGRAPHY: City → State/Region
    # =========================================================================
    test_pairs("Geography: City-State Relationships", [
        ("München", "Bayern"),
        ("München, Bavaria", "Bayern, Germany"),
        ("Pune", "Maharashtra"),
        ("Pune, India", "Maharashtra, India"),
        ("Frankfurt", "Hessen"),
        ("Berlin", "Berlin"),  # City-state
        ("Hamburg", "Hamburg"),  # City-state
    ], expect_similar=True)
    
    # Cross-check: cities in DIFFERENT states should be less similar
    test_pairs("Geography: Cross-State (should be DIFFERENT)", [
        ("München", "Nordrhein-Westfalen"),
        ("Pune", "Karnataka"),
        ("Frankfurt", "Bayern"),
    ], expect_similar=False)
    
    # =========================================================================
    # 2. REMOTE WORK
    # =========================================================================
    test_clusters("Remote Work", {
        "remote": [
            "work from home",
            "remote work",
            "home office",
            "fully remote",
            "remote position",
            "Homeoffice möglich",
        ],
        "onsite": [
            "on-site work",
            "office based",
            "in-office required",
            "Präsenz im Büro",
            "no remote",
        ],
        "hybrid": [
            "hybrid work",
            "flexible work arrangement",
            "2 days office 3 days home",
            "teilweise Homeoffice",
        ]
    })
    
    # =========================================================================
    # 3. SENIORITY (verify current findings)
    # =========================================================================
    test_clusters("Seniority Levels", {
        "junior": [
            "junior developer",
            "entry level",
            "graduate position",
            "0-2 years experience",
            "Berufseinsteiger",
        ],
        "mid": [
            "mid-level developer",
            "3-5 years experience",
            "experienced professional",
        ],
        "senior": [
            "senior developer",
            "senior engineer",
            "5+ years experience",
            "tech lead",
            "Senior Entwickler",
        ],
        "executive": [
            "VP Engineering",
            "CTO",
            "Director of Engineering",
            "Head of Technology",
            "Geschäftsführer",
        ]
    })
    
    # =========================================================================
    # 4. DOMAINS (the big question)
    # =========================================================================
    test_clusters("Professional Domains", {
        "legal": [
            "legal counsel",
            "attorney",
            "lawyer",
            "Rechtsanwalt",
            "contract law",
            "litigation",
        ],
        "medical": [
            "physician",
            "doctor",
            "surgeon",
            "registered nurse",
            "clinical practice",
            "Arzt",
        ],
        "tech": [
            "software engineer",
            "developer",
            "programmer",
            "Softwareentwickler",
            "backend engineer",
            "full stack developer",
        ],
        "finance": [
            "financial analyst",
            "accountant",
            "investment banker",
            "Finanzberater",
            "portfolio manager",
        ],
        "marketing": [
            "marketing manager",
            "brand manager",
            "digital marketing",
            "content strategist",
            "SEO specialist",
        ]
    })
    
    # =========================================================================
    # 5. EDUCATION LEVEL
    # =========================================================================
    test_clusters("Education Level", {
        "vocational": [
            "Ausbildung",
            "vocational training",
            "apprenticeship",
            "trade school",
        ],
        "bachelors": [
            "Bachelor's degree",
            "undergraduate degree",
            "BS in Computer Science",
            "BA required",
        ],
        "masters": [
            "Master's degree",
            "MBA",
            "MS in Engineering",
            "graduate degree",
        ],
        "phd": [
            "PhD",
            "doctorate",
            "Dr. rer. nat.",
            "postdoctoral",
        ]
    })
    
    # =========================================================================
    # 6. SALARY RANGES (tricky - embeddings might not capture numbers well)
    # =========================================================================
    test_pairs("Salary: Can embeddings distinguish ranges?", [
        ("€50,000 annual salary", "€55,000 annual salary"),  # Should be similar
        ("€50,000 annual salary", "€150,000 annual salary"), # Should be different?
        ("entry level salary", "executive compensation"),    # Semantic
        ("minimum wage", "six figure salary"),               # Semantic
    ], expect_similar=True)  # Testing hypothesis
    
    # =========================================================================
    # 7. EXPERIENCE YEARS
    # =========================================================================
    test_pairs("Experience Years", [
        ("1 year experience", "2 years experience"),
        ("5 years experience", "10 years experience"),
        ("fresh graduate", "seasoned professional"),
        ("Berufserfahrung 3 Jahre", "3 years work experience"),  # Cross-lingual
    ], expect_similar=True)
    
    # =========================================================================
    # 8. CROSS-LINGUAL (German ↔ English)
    # =========================================================================
    test_pairs("Cross-Lingual: German ↔ English", [
        ("Software Developer", "Softwareentwickler"),
        ("Project Manager", "Projektleiter"),
        ("Data Scientist", "Datenwissenschaftler"),
        ("Machine Learning Engineer", "Machine Learning Ingenieur"),
        ("Senior Developer", "Senior Entwickler"),
        ("Work from home", "Homeoffice"),
    ], expect_similar=True)
    
    print("\n" + "="*60)
    print("🏁 Research complete!")
    print("="*60)

if __name__ == '__main__':
    main()
