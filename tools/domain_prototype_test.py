#!/usr/bin/env python3
"""
Domain Prototype Test - Nate's "practical ladder step 1"

Create domain prototypes (curated exemplar postings), embed them,
classify new jobs by similarity. See if embedding space separates
domains before we train anything.

Usage:
    python3 tools/domain_prototype_test.py
"""

import json
import sys
from pathlib import Path
import numpy as np
import requests

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "snowflake-arctic-embed2:latest"  # bge-m3 has NaN issues with some German text

# ============================================================================
# DOMAIN PROTOTYPES - 5-10 synthetic exemplars per domain
# These are what "obviously belongs in this domain" looks like
# ============================================================================

DOMAIN_PROTOTYPES = {
    "healthcare": [
        "Arzt (m/w/d) für Innere Medizin gesucht. Approbation erforderlich. Krankenhaus der Maximalversorgung.",
        "Gesundheits- und Krankenpfleger (m/w/d) für Intensivstation. Examiniert, Schichtdienst.",
        "Physician needed for internal medicine department. Board certification required.",
        "Registered Nurse ICU position. State license required. 12-hour shifts.",
        "Physiotherapeut (m/w/d) für orthopädische Rehabilitation. Staatliche Anerkennung.",
        "Zahnarzt für Praxis in München. Approbation und Berufserfahrung.",
        "Psychotherapeut (m/w/d) mit Approbation für psychosomatische Klinik.",
    ],
    
    "legal": [
        "Rechtsanwalt (m/w/d) Arbeitsrecht. Volljurist mit zwei Staatsexamen.",
        "Notar gesucht. Zulassung erforderlich. Kanzlei in Frankfurt.",
        "Attorney at Law for corporate M&A. Bar admission required.",
        "Legal Counsel (m/w/d) für internationales Unternehmen. Volljurist.",
        "Patentanwalt für IP-Kanzlei. Zugelassen beim Deutschen Patent- und Markenamt.",
        "Syndikusrechtsanwalt (m/w/d) Compliance. Syndikuszulassung.",
    ],
    
    "education_teaching": [
        "Lehrer (m/w/d) für Mathematik und Physik. Gymnasium. Staatsexamen erforderlich.",
        "Grundschullehrer (m/w/d). Verbeamtung möglich. Referendariat abgeschlossen.",
        "Teacher for secondary school. State certification and QTS required.",
        "Berufsschullehrer (m/w/d) Elektrotechnik. Staatsexamen oder Quereinstieg.",
        "Studienrat für Deutsch und Geschichte an Realschule.",
    ],
    
    "childcare": [
        "Erzieher (m/w/d) für Kindertagesstätte. Staatlich anerkannt.",
        "Kinderpfleger/in für Krippe. Fachschulausbildung erforderlich.",
        "Nursery Teacher for early years setting. Level 3 childcare qualification.",
        "Sozialpädagoge (m/w/d) für Jugendhilfeeinrichtung. Staatliche Anerkennung.",
        "Heilerziehungspfleger (m/w/d) für integrative Kita.",
    ],
    
    "aviation": [
        "Pilot (m/w/d) für A320. ATPL, Type Rating, Medical Class 1.",
        "First Officer B737. CPL/IR, ATPL theory, min 500 hours.",
        "Flugkapitän für Langstrecke. ATPL, aktuelle Musterberechtigung.",
        "Airline Captain for European operations. Valid ATPL and type rating.",
    ],
    
    "it_software": [
        "Software Engineer Python/Django. 3+ years experience. Remote possible.",
        "DevOps Engineer für Cloud-Infrastruktur. AWS, Kubernetes, Terraform.",
        "Full Stack Developer React/Node.js. Agile team. Startup.",
        "Softwareentwickler (m/w/d) Java/Spring Boot. Backend-Fokus.",
        "Data Engineer für Big Data Plattform. Spark, Kafka, Python.",
        "Frontend Developer TypeScript/Vue.js. UI/UX affinity.",
    ],
    
    "construction_trades": [
        "Elektriker (m/w/d) für Industriemontage. Gesellenbrief erforderlich.",
        "Installateur und Heizungsbauer. Meisterbetrieb sucht Gesellen.",
        "Dachdecker (m/w/d) für Flachdachsanierung. Gesellenprüfung.",
        "Plumber for commercial projects. Journeyman certificate required.",
        "Maurer (m/w/d) für Hochbau. Erfahrung im Rohbau.",
        "Schornsteinfeger. Gesellenbrief, Führerschein Klasse B.",
    ],
    
    "finance_accounting": [
        "Steuerberater (m/w/d) für mittelständische Kanzlei. Berufsexamen.",
        "Wirtschaftsprüfer für Audit-Team. WP-Examen erforderlich.",
        "Accountant for international corporation. CPA preferred.",
        "Bilanzbuchhalter (m/w/d) für Konzernbuchhaltung. IHK-Abschluss.",
        "Financial Controller für Reporting. IFRS-Kenntnisse.",
        "Tax Manager for transfer pricing. Chartered accountant.",
    ],
    
    "security_guarding": [
        "Sicherheitsmitarbeiter (m/w/d) für Objektschutz. §34a Sachkunde.",
        "Security Officer for corporate headquarters. SIA license.",
        "Personenschutz für VIP-Begleitung. §34a, Führerschein.",
        "Doorman für Club in Berlin. Unterrichtung nach §34a.",
        "Werkschutzfachkraft für Industriegelände. IHK-Prüfung.",
    ],
    
    "logistics_warehouse": [
        "Lagerarbeiter (m/w/d) für Kommissionierung. Staplerschein.",
        "Warehouse Operative for distribution center. Forklift license.",
        "LKW-Fahrer (m/w/d) Fernverkehr. Führerschein CE, Fahrerkarte.",
        "Speditionskaufmann für Disposition. Ausbildung im Speditionswesen.",
        "Logistics Coordinator for supply chain. SAP experience.",
    ],
    
    "hospitality_gastro": [
        "Koch (m/w/d) für gehobene Küche. Ausbildung, Erfahrung à la carte.",
        "Restaurantfachmann/-frau für Service. Ausbildung oder Erfahrung.",
        "Hotel Receptionist for 4-star hotel. English and German fluent.",
        "Barkeeper für Cocktailbar. Erfahrung, kreativ.",
        "Hotelfachmann/-frau für Front Office. Schichtbereitschaft.",
    ],
    
    "retail_sales": [
        "Verkäufer (m/w/d) für Einzelhandel Mode. Kundenorientiert.",
        "Retail Sales Associate for electronics store. Commission-based.",
        "Filialleiter für Supermarkt. Führungserfahrung im LEH.",
        "Kaufmann im Einzelhandel (m/w/d). Ausbildungsplatz.",
        "Visual Merchandiser for flagship store. Creative, flexible.",
    ],
}


def get_embedding(text: str) -> np.ndarray:
    """Get embedding for a single text."""
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL, "input": text}, timeout=60)
        resp.raise_for_status()
        return np.array(resp.json()["embeddings"][0])
    except Exception as e:
        print(f"  ERROR embedding: {text[:50]}... → {e}")
        raise


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def build_domain_centroids(prototypes: dict) -> dict:
    """Build centroid embedding for each domain from its prototypes."""
    print("Building domain centroids from prototypes...")
    centroids = {}
    
    for domain, texts in prototypes.items():
        embeddings = []
        for text in texts:
            emb = get_embedding(text)
            embeddings.append(emb)
        
        # Centroid = mean of all prototype embeddings
        centroid = np.mean(embeddings, axis=0)
        # Normalize to unit vector for cosine similarity
        centroid = centroid / np.linalg.norm(centroid)
        centroids[domain] = centroid
        print(f"  {domain}: {len(texts)} prototypes → centroid")
    
    return centroids


def classify_by_prototype(text: str, centroids: dict, top_k: int = 3) -> list:
    """Classify text by similarity to domain centroids."""
    emb = get_embedding(text)
    
    scores = []
    for domain, centroid in centroids.items():
        sim = cosine_similarity(emb, centroid)
        scores.append((domain, sim))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def test_with_real_postings(centroids: dict, limit: int = 50):
    """Test classifier on real AA postings."""
    print(f"\n{'='*70}")
    print("Testing on real AA postings...")
    print(f"{'='*70}")
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get random sample of postings with enough text
        cur.execute("""
            SELECT posting_id, job_title, 
                   LEFT(job_description, 500) as description
            FROM postings 
            WHERE source = 'arbeitsagentur' 
              AND job_description IS NOT NULL
              AND LENGTH(job_description) > 200
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))
        
        rows = cur.fetchall()
    
    results = []
    
    for row in rows:
        posting_id = row['posting_id']
        title = row['job_title'] or ''
        description = row['description'] or ''
        text = f"{title}\n{description}"
        
        predictions = classify_by_prototype(text, centroids)
        top_domain, top_score = predictions[0]
        second_domain, second_score = predictions[1]
        
        gap = top_score - second_score
        
        results.append({
            'posting_id': posting_id,
            'title': (title or '')[:60],
            'top_domain': top_domain,
            'top_score': top_score,
            'gap': gap,
            'predictions': predictions,
        })
    
    # Analyze results
    print(f"\nClassified {len(results)} postings:")
    print()
    
    # Domain distribution
    domain_counts = {}
    for r in results:
        d = r['top_domain']
        domain_counts[d] = domain_counts.get(d, 0) + 1
    
    print("Domain distribution:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        pct = count / len(results) * 100
        bar = '█' * int(pct / 2)
        print(f"  {domain:25s} {count:3d} ({pct:5.1f}%) {bar}")
    
    # Confidence analysis
    high_conf = [r for r in results if r['gap'] > 0.05]
    medium_conf = [r for r in results if 0.02 < r['gap'] <= 0.05]
    low_conf = [r for r in results if r['gap'] <= 0.02]
    
    print(f"\nConfidence (gap to 2nd place):")
    print(f"  High (gap > 0.05):   {len(high_conf):3d} ({len(high_conf)/len(results)*100:.1f}%)")
    print(f"  Medium (0.02-0.05):  {len(medium_conf):3d} ({len(medium_conf)/len(results)*100:.1f}%)")
    print(f"  Low (gap ≤ 0.02):    {len(low_conf):3d} ({len(low_conf)/len(results)*100:.1f}%)")
    
    # Show examples
    print(f"\n{'='*70}")
    print("HIGH CONFIDENCE examples (gap > 0.05):")
    print(f"{'='*70}")
    for r in sorted(high_conf, key=lambda x: -x['gap'])[:10]:
        print(f"  [{r['top_domain']:20s}] {r['top_score']:.3f} (gap {r['gap']:.3f}) | {r['title']}")
    
    print(f"\n{'='*70}")
    print("LOW CONFIDENCE examples (gap ≤ 0.02) - ambiguous:")
    print(f"{'='*70}")
    for r in sorted(low_conf, key=lambda x: x['gap'])[:10]:
        preds = r['predictions']
        print(f"  {r['title'][:50]}")
        print(f"    → {preds[0][0]}: {preds[0][1]:.3f}")
        print(f"    → {preds[1][0]}: {preds[1][1]:.3f}")
        print(f"    → {preds[2][0]}: {preds[2][1]:.3f}")
        print()
    
    return results


def measure_domain_separation(centroids: dict):
    """Measure how well-separated the domain centroids are."""
    print(f"\n{'='*70}")
    print("Domain Centroid Separation Matrix")
    print(f"{'='*70}")
    
    domains = list(centroids.keys())
    n = len(domains)
    
    # Compute pairwise similarities
    matrix = np.zeros((n, n))
    for i, d1 in enumerate(domains):
        for j, d2 in enumerate(domains):
            matrix[i, j] = cosine_similarity(centroids[d1], centroids[d2])
    
    # Print matrix
    header = "            " + "".join(f"{d[:8]:>9s}" for d in domains)
    print(header)
    for i, d in enumerate(domains):
        row = f"{d[:12]:12s}"
        for j in range(n):
            if i == j:
                row += "    ---  "
            else:
                row += f"  {matrix[i, j]:.3f}  "
        print(row)
    
    # Find most similar pairs (excluding diagonal)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((domains[i], domains[j], matrix[i, j]))
    
    pairs.sort(key=lambda x: -x[2])
    
    print(f"\nMost similar domain pairs (potential confusion):")
    for d1, d2, sim in pairs[:5]:
        print(f"  {d1} ↔ {d2}: {sim:.3f}")
    
    print(f"\nMost distinct domain pairs:")
    for d1, d2, sim in pairs[-5:]:
        print(f"  {d1} ↔ {d2}: {sim:.3f}")
    
    # Overall separation
    off_diag = [matrix[i, j] for i in range(n) for j in range(n) if i != j]
    print(f"\nOverall separation:")
    print(f"  Mean inter-domain similarity: {np.mean(off_diag):.3f}")
    print(f"  Min inter-domain similarity:  {np.min(off_diag):.3f}")
    print(f"  Max inter-domain similarity:  {np.max(off_diag):.3f}")


def test_gated_domains(centroids: dict):
    """Test specifically on the gated domains - can we reliably detect them?"""
    print(f"\n{'='*70}")
    print("GATED DOMAIN DETECTION TEST")
    print("Can we reliably detect healthcare, legal, education, childcare, aviation?")
    print(f"{'='*70}")
    
    # Test cases - should clearly trigger their gate
    test_cases = [
        # Healthcare - should gate
        ("Facharzt für Kardiologie mit Approbation", "healthcare", True),
        ("Krankenschwester für Notaufnahme, examiniert", "healthcare", True),
        ("Psychotherapeut (m/w/d) mit Approbation", "healthcare", True),
        
        # Legal - should gate
        ("Rechtsanwalt Gesellschaftsrecht, zwei Staatsexamen", "legal", True),
        ("Notar für Immobilientransaktionen", "legal", True),
        
        # Education - should gate
        ("Gymnasiallehrer Mathematik, Staatsexamen", "education_teaching", True),
        ("Grundschullehrer mit abgeschlossenem Referendariat", "education_teaching", True),
        
        # Childcare - should gate
        ("Erzieher für Kita, staatlich anerkannt", "childcare", True),
        ("Kinderpfleger für Krippe", "childcare", True),
        
        # Aviation - should gate
        ("Pilot A320, ATPL, Medical Class 1", "aviation", True),
        
        # Should NOT gate (similar but different)
        ("Medical Device Sales Representative", "healthcare", False),  # Sales, not practice
        ("Legal Secretary for law firm", "legal", False),  # Admin, not lawyer
        ("Teaching Assistant for university", "education_teaching", False),  # Not state school teacher
        ("Babysitter for private family", "childcare", False),  # Not institutional
        ("Flight Attendant for Lufthansa", "aviation", False),  # Not pilot
        ("Healthcare IT Consultant", "it_software", False),  # IT, not healthcare
    ]
    
    print(f"\nTesting {len(test_cases)} cases...\n")
    
    correct = 0
    for text, expected_domain, should_gate in test_cases:
        predictions = classify_by_prototype(text, centroids)
        top_domain, top_score = predictions[0]
        second_domain, second_score = predictions[1]
        gap = top_score - second_score
        
        # For gated detection, we need:
        # 1. Correct domain prediction
        # 2. Sufficient confidence (gap > 0.03)
        predicted_gate = top_domain in ['healthcare', 'legal', 'education_teaching', 'childcare', 'aviation']
        confident = gap > 0.03
        
        is_correct = (top_domain == expected_domain) if should_gate else (not (predicted_gate and confident))
        
        status = "✓" if is_correct else "✗"
        correct += is_correct
        
        print(f"{status} [{top_domain:20s}] {top_score:.3f} (gap {gap:.3f})")
        print(f"  Text: {text[:60]}")
        print(f"  Expected: {expected_domain}, should_gate={should_gate}")
        if not is_correct:
            print(f"  ⚠️  WRONG - predicted {top_domain}, 2nd: {second_domain}")
        print()
    
    accuracy = correct / len(test_cases) * 100
    print(f"{'='*70}")
    print(f"Gate Detection Accuracy: {correct}/{len(test_cases)} ({accuracy:.1f}%)")
    print(f"{'='*70}")


def main():
    print("="*70)
    print("DOMAIN PROTOTYPE CLASSIFIER TEST")
    print("Nate's Step 1: Fixed embedder + prototype centroids")
    print("="*70)
    print()
    
    # Build centroids from prototypes
    centroids = build_domain_centroids(DOMAIN_PROTOTYPES)
    
    # Measure separation between domain centroids
    measure_domain_separation(centroids)
    
    # Test gated domain detection
    test_gated_domains(centroids)
    
    # Test on real postings
    test_with_real_postings(centroids, limit=100)


if __name__ == "__main__":
    main()
