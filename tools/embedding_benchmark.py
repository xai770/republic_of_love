#!/usr/bin/env python3
"""
Embedding Model Benchmark
=========================

Compare embedding models for skill matching quality and speed.

Tests:
1. Semantic similarity accuracy (do similar skills have high scores?)
2. Dissimilar rejection (do unrelated skills have low scores?)
3. Speed (embeddings/second)
4. Dimension count

Models tested:
- bge-m3:567m (current production - 1024 dims)
- mxbai-embed-large (top MTEB performer - 1024 dims)
- nomic-embed-text (lightweight, good quality - 768 dims)
- snowflake-arctic-embed (enterprise focused - 1024 dims)
- all-minilm (tiny, fast - 384 dims)

Usage:
    python3 tools/embedding_benchmark.py
    python3 tools/embedding_benchmark.py --quick   # fewer samples
"""

import sys
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test cases: (skill_a, skill_b, expected_relation)
# "similar" = should have high similarity (>0.7)
# "related" = moderate similarity (0.4-0.7)
# "unrelated" = low similarity (<0.4)

SKILL_PAIRS = [
    # Similar pairs (should score >0.7)
    ("Python programming", "Python development", "similar"),
    ("Machine learning", "ML engineering", "similar"),
    ("Data analysis", "Data analytics", "similar"),
    ("Project management", "Program management", "similar"),
    ("JavaScript", "JS development", "similar"),
    ("SQL database", "SQL queries", "similar"),
    ("Cloud computing", "Cloud infrastructure", "similar"),
    ("DevOps", "DevOps engineering", "similar"),
    ("UI design", "User interface design", "similar"),
    ("API development", "REST API design", "similar"),
    
    # Related pairs (should score 0.4-0.7)
    ("Python", "Data science", "related"),
    ("JavaScript", "React", "related"),
    ("Cloud computing", "AWS", "related"),
    ("Machine learning", "Statistics", "related"),
    ("Project management", "Agile methodology", "related"),
    ("SQL", "Database administration", "related"),
    ("DevOps", "Kubernetes", "related"),
    ("Data analysis", "Excel", "related"),
    ("Software engineering", "Code review", "related"),
    ("UI design", "Figma", "related"),
    
    # Unrelated pairs (should score <0.4)
    ("Python programming", "Plumbing", "unrelated"),
    ("Machine learning", "Carpentry", "unrelated"),
    ("Cloud computing", "Cooking", "unrelated"),
    ("JavaScript", "Nursing", "unrelated"),
    ("Data analysis", "Landscaping", "unrelated"),
    ("Project management", "Welding", "unrelated"),
    ("DevOps", "Hair styling", "unrelated"),
    ("SQL", "Painting", "unrelated"),
    ("API development", "Gardening", "unrelated"),
    ("UI design", "Electrical work", "unrelated"),
]

# Edge cases that trip up naive embeddings
EDGE_CASES = [
    # Abbreviations
    ("ML", "Machine Learning", "similar"),
    ("AI", "Artificial Intelligence", "similar"),
    ("NLP", "Natural Language Processing", "similar"),
    ("CI/CD", "Continuous Integration", "related"),
    
    # Case variations
    ("PYTHON", "python", "similar"),
    ("JavaScript", "JAVASCRIPT", "similar"),
    
    # Compound skills
    ("Full-stack development", "Frontend and backend", "similar"),
    ("Data engineering", "ETL pipelines", "related"),
    
    # Domain-specific
    ("HIPAA compliance", "Healthcare data privacy", "similar"),
    ("SOC 2", "Security compliance", "related"),
    ("PCI DSS", "Payment card security", "similar"),
]

# =============================================================================
# MULTILINGUAL TEST CASES (German ↔ English)
# =============================================================================
# Critical for German job market - skills appear in both languages

MULTILINGUAL_PAIRS = [
    # German ↔ English SAME SKILL (should score >0.7)
    ("Projektmanagement", "Project management", "similar"),
    ("Softwareentwicklung", "Software development", "similar"),
    ("Datenanalyse", "Data analysis", "similar"),
    ("Maschinelles Lernen", "Machine learning", "similar"),
    ("Künstliche Intelligenz", "Artificial Intelligence", "similar"),
    ("Qualitätssicherung", "Quality assurance", "similar"),
    ("Buchhaltung", "Accounting", "similar"),
    ("Personalwesen", "Human Resources", "similar"),
    ("Vertrieb", "Sales", "similar"),
    ("Kundenbetreuung", "Customer service", "similar"),
    
    # German technical terms ↔ English equivalents
    ("Datenbankentwicklung", "Database development", "similar"),
    ("Webentwicklung", "Web development", "similar"),
    ("Cloud-Architektur", "Cloud architecture", "similar"),
    ("Systemadministration", "System administration", "similar"),
    ("Netzwerksicherheit", "Network security", "similar"),
    
    # German ↔ English RELATED (should score 0.4-0.7)
    ("Python", "Datenverarbeitung", "related"),  # Python ↔ Data processing
    ("SAP", "Unternehmensressourcenplanung", "related"),  # SAP ↔ ERP
    ("Excel", "Tabellenkalkulation", "related"),  # Excel ↔ Spreadsheet
    ("Agile", "Scrum-Methodik", "related"),  # Agile ↔ Scrum methodology
    ("DevOps", "Automatisierung", "related"),  # DevOps ↔ Automation
    
    # German ↔ English UNRELATED (should score <0.4)
    ("Softwareentwicklung", "Kochen", "unrelated"),  # Software dev ↔ Cooking
    ("Maschinelles Lernen", "Gärtnerei", "unrelated"),  # ML ↔ Gardening
    ("Projektmanagement", "Klempnerei", "unrelated"),  # PM ↔ Plumbing
    ("Datenanalyse", "Malerei", "unrelated"),  # Data analysis ↔ Painting
    ("Cloud-Architektur", "Friseurhandwerk", "unrelated"),  # Cloud ↔ Hairdressing
    
    # Mixed language job postings (common in German tech)
    ("Senior Software Engineer", "Erfahrener Softwareentwickler", "similar"),
    ("Full Stack Developer", "Full-Stack-Entwickler", "similar"),
    ("Data Scientist", "Datenwissenschaftler", "similar"),
    ("Product Owner", "Produktverantwortlicher", "similar"),
    ("Scrum Master", "Scrum-Master", "similar"),
    
    # German compound words (notoriously long!)
    ("Softwarequalitätssicherungsingenieur", "Software QA Engineer", "similar"),
    ("Datenbankadministrator", "Database Administrator", "similar"),
    ("Anwendungsentwickler", "Application Developer", "similar"),
]


def get_embedding(text: str, model: str) -> List[float]:
    """Get embedding from Ollama."""
    response = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": model, "input": text}
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def evaluate_model(model: str, pairs: List[Tuple], quick: bool = False) -> Dict:
    """Evaluate a model on skill pairs."""
    results = {
        "model": model,
        "dimensions": 0,
        "total_pairs": 0,
        "correct": 0,
        "similar_accuracy": 0,
        "related_accuracy": 0,
        "unrelated_accuracy": 0,
        "avg_time_ms": 0,
        "embeddings_per_sec": 0,
        "scores": {"similar": [], "related": [], "unrelated": []},
        "failures": [],
    }
    
    if quick:
        pairs = pairs[:15]  # Just 5 of each type
    
    times = []
    similar_correct = 0
    similar_total = 0
    related_correct = 0
    related_total = 0
    unrelated_correct = 0
    unrelated_total = 0
    
    for skill_a, skill_b, expected in pairs:
        try:
            start = time.time()
            emb_a = get_embedding(skill_a, model)
            emb_b = get_embedding(skill_b, model)
            elapsed = time.time() - start
            times.append(elapsed)
            
            if results["dimensions"] == 0:
                results["dimensions"] = len(emb_a)
            
            similarity = cosine_similarity(emb_a, emb_b)
            results["scores"][expected].append(similarity)
            
            # Check if prediction matches expectation
            if expected == "similar":
                similar_total += 1
                if similarity >= 0.65:  # Slightly relaxed threshold
                    similar_correct += 1
                else:
                    results["failures"].append(
                        f"SIMILAR failed: '{skill_a}' vs '{skill_b}' = {similarity:.3f}"
                    )
            elif expected == "related":
                related_total += 1
                if 0.35 <= similarity <= 0.80:
                    related_correct += 1
                else:
                    results["failures"].append(
                        f"RELATED failed: '{skill_a}' vs '{skill_b}' = {similarity:.3f}"
                    )
            else:  # unrelated
                unrelated_total += 1
                if similarity < 0.45:
                    unrelated_correct += 1
                else:
                    results["failures"].append(
                        f"UNRELATED failed: '{skill_a}' vs '{skill_b}' = {similarity:.3f}"
                    )
                    
        except Exception as e:
            results["failures"].append(f"ERROR: {skill_a} vs {skill_b}: {e}")
    
    # Calculate metrics
    results["total_pairs"] = len(pairs)
    results["correct"] = similar_correct + related_correct + unrelated_correct
    
    if similar_total > 0:
        results["similar_accuracy"] = similar_correct / similar_total
    if related_total > 0:
        results["related_accuracy"] = related_correct / related_total
    if unrelated_total > 0:
        results["unrelated_accuracy"] = unrelated_correct / unrelated_total
    
    if times:
        results["avg_time_ms"] = (sum(times) / len(times)) * 1000 / 2  # per embedding
        results["embeddings_per_sec"] = 1000 / results["avg_time_ms"] if results["avg_time_ms"] > 0 else 0
    
    # Calculate average scores for each category
    for cat in ["similar", "related", "unrelated"]:
        if results["scores"][cat]:
            avg = sum(results["scores"][cat]) / len(results["scores"][cat])
            results[f"avg_{cat}_score"] = avg
    
    return results


def print_report(all_results: List[Dict]):
    """Print comparison report."""
    print("\n" + "=" * 80)
    print("EMBEDDING MODEL BENCHMARK RESULTS")
    print("=" * 80)
    
    # Summary table
    print(f"\n{'Model':<25} {'Dims':>6} {'Accuracy':>10} {'Similar':>8} {'Related':>8} {'Unrelated':>10} {'Speed':>12}")
    print("-" * 80)
    
    for r in sorted(all_results, key=lambda x: x["correct"] / max(x["total_pairs"], 1), reverse=True):
        acc = r["correct"] / r["total_pairs"] if r["total_pairs"] > 0 else 0
        print(f"{r['model']:<25} {r['dimensions']:>6} {acc:>9.1%} "
              f"{r['similar_accuracy']:>7.1%} {r['related_accuracy']:>7.1%} "
              f"{r['unrelated_accuracy']:>9.1%} {r['embeddings_per_sec']:>8.1f}/sec")
    
    # Average scores
    print(f"\n{'Model':<25} {'Avg Similar':>12} {'Avg Related':>12} {'Avg Unrelated':>14}")
    print("-" * 65)
    for r in all_results:
        print(f"{r['model']:<25} "
              f"{r.get('avg_similar_score', 0):>11.3f} "
              f"{r.get('avg_related_score', 0):>11.3f} "
              f"{r.get('avg_unrelated_score', 0):>13.3f}")
    
    # Best model recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    # Find best by different criteria
    by_accuracy = max(all_results, key=lambda x: x["correct"] / max(x["total_pairs"], 1))
    by_speed = max(all_results, key=lambda x: x["embeddings_per_sec"])
    by_separation = max(all_results, key=lambda x: x.get("avg_similar_score", 0) - x.get("avg_unrelated_score", 0))
    
    print(f"\n🏆 Best Accuracy: {by_accuracy['model']} ({by_accuracy['correct']}/{by_accuracy['total_pairs']} correct)")
    print(f"⚡ Fastest: {by_speed['model']} ({by_speed['embeddings_per_sec']:.1f} embeddings/sec)")
    print(f"📊 Best Separation: {by_separation['model']} (similar-unrelated gap: {by_separation.get('avg_similar_score', 0) - by_separation.get('avg_unrelated_score', 0):.3f})")
    
    # Failures summary
    print("\n" + "-" * 80)
    print("NOTABLE FAILURES")
    print("-" * 80)
    for r in all_results:
        if r["failures"]:
            print(f"\n{r['model']}:")
            for f in r["failures"][:5]:  # First 5 failures
                print(f"  • {f}")
            if len(r["failures"]) > 5:
                print(f"  ... and {len(r['failures']) - 5} more")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark embedding models")
    parser.add_argument("--quick", action="store_true", help="Quick test with fewer samples")
    parser.add_argument("--models", nargs="+", help="Specific models to test")
    parser.add_argument("--multilingual", action="store_true", help="Include German/English tests")
    parser.add_argument("--multilingual-only", action="store_true", help="Only German/English tests")
    args = parser.parse_args()
    
    # Models to test
    if args.models:
        models = args.models
    else:
        models = [
            "bge-m3:567m",
            "mxbai-embed-large",
            "nomic-embed-text",
            "snowflake-arctic-embed",
            "all-minilm",
        ]
    
    # Combine test pairs
    if args.multilingual_only:
        all_pairs = MULTILINGUAL_PAIRS
        print("🇩🇪🇬🇧 MULTILINGUAL MODE (German ↔ English only)")
    elif args.multilingual:
        all_pairs = SKILL_PAIRS + EDGE_CASES + MULTILINGUAL_PAIRS
        print("🌍 FULL MODE (English + German/English)")
    else:
        all_pairs = SKILL_PAIRS + EDGE_CASES
    
    print(f"Testing {len(models)} models on {len(all_pairs)} skill pairs...")
    if args.quick:
        print("(Quick mode - reduced sample size)")
    
    all_results = []
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"Testing: {model}")
        print("=" * 60)
        
        try:
            results = evaluate_model(model, all_pairs, quick=args.quick)
            all_results.append(results)
            
            acc = results["correct"] / results["total_pairs"]
            print(f"  Accuracy: {acc:.1%} ({results['correct']}/{results['total_pairs']})")
            print(f"  Dimensions: {results['dimensions']}")
            print(f"  Speed: {results['embeddings_per_sec']:.1f} embeddings/sec")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results.append({"model": model, "error": str(e), "correct": 0, "total_pairs": 1,
                              "similar_accuracy": 0, "related_accuracy": 0, "unrelated_accuracy": 0,
                              "dimensions": 0, "embeddings_per_sec": 0, "failures": [], "scores": {}})
    
    # Print comparison report
    print_report(all_results)
    
    # Save detailed results
    output_path = PROJECT_ROOT / "output" / "embedding_benchmark.json"
    with open(output_path, "w") as f:
        # Convert numpy types for JSON
        for r in all_results:
            r["scores"] = {k: [float(v) for v in vals] for k, vals in r.get("scores", {}).items()}
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
