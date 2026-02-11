#!/usr/bin/env python3
"""
classify_domains_embeddings.py - Classify postings by domain using embeddings

Uses bge-m3 embeddings to classify postings that don't have berufenet data.
Compares job_title embeddings against domain reference vectors.

Tracks all changes in domain_gate with classification_method='embedding' so
we can audit and iterate later.

Usage:
    python3 tools/classify_domains_embeddings.py           # Preview
    python3 tools/classify_domains_embeddings.py --apply   # Apply changes
    python3 tools/classify_domains_embeddings.py --reset   # Remove embedding classifications

Author: Arden
Date: 2026-02-06
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection_raw, return_connection
from tools.skill_embeddings import get_embedding, cosine_similarity

# Domain reference phrases for embedding comparison
# More examples = better coverage of different job titles
DOMAIN_REFERENCES = {
    'IT & Technology': [
        'Software Developer', 'Programmer', 'IT Administrator',
        'Data Scientist', 'Web Developer', 'DevOps Engineer',
        'Informatiker', 'Softwareentwickler', 'System Administrator'
    ],
    'Technology & Engineering': [
        'Engineer', 'Technical', 'Mechatroniker', 'Elektroniker',
        'Electrical Engineer', 'Mechanical Engineer', 'Technician',
        'Ingenieur', 'Techniker', 'CAD Konstrukteur'
    ],
    'Manufacturing & Engineering': [
        'Production Worker', 'Machine Operator', 'Welder',
        'Produktionsmitarbeiter', 'Schweißer', 'CNC Operator',
        'Metallbauer', 'Industriemechaniker', 'Zerspanungsmechaniker'
    ],
    'Healthcare & Medicine': [
        'Nurse', 'Doctor', 'Medical Assistant', 'Pflegefachkraft',
        'Arzt', 'Krankenschwester', 'Altenpfleger', 'Physiotherapeut',
        'Dentalhygieniker', 'Medizinische Fachangestellte'
    ],
    'Transport & Logistics': [
        'Truck Driver', 'Warehouse Worker', 'Logistics',
        'LKW Fahrer', 'Lagerarbeiter', 'Speditionskaufmann',
        'Staplerfahrer', 'Kurier', 'Berufskraftfahrer'
    ],
    'Construction & Trades': [
        'Construction Worker', 'Carpenter', 'Electrician',
        'Bauarbeiter', 'Tischler', 'Elektriker', 'Maurer',
        'Dachdecker', 'Installateur', 'Fliesenleger'
    ],
    'Commerce & Retail': [
        'Sales Associate', 'Retail', 'Cashier', 'Verkäufer',
        'Einzelhandelskaufmann', 'Kassierer', 'Filialmitarbeiter',
        'Handelsvertreter', 'Einkäufer'
    ],
    'Business & Management': [
        'Manager', 'Business Analyst', 'Project Manager',
        'Sachbearbeiter', 'Bürokaufmann', 'Controller',
        'Teamleiter', 'Geschäftsführer', 'Personalreferent'
    ],
    'Hospitality & Food': [
        'Cook', 'Chef', 'Waiter', 'Hotel', 'Koch',
        'Kellner', 'Restaurantfachmann', 'Küchenhilfe',
        'Bäcker', 'Konditor', 'Barista'
    ],
    'Education & Social Work': [
        'Teacher', 'Social Worker', 'Educator', 'Lehrer',
        'Sozialarbeiter', 'Erzieher', 'Pädagoge', 'Trainer',
        'Sozialpädagoge', 'Dozent'
    ],
    'Finance & Banking': [
        'Accountant', 'Financial Analyst', 'Banker',
        'Buchhalter', 'Finanzberater', 'Bankkaufmann',
        'Steuerberater', 'Wirtschaftsprüfer', 'Kreditsachbearbeiter',
        'Investment Banking', 'Trader', 'FX Derivatives', 'Risk Analyst',
        'Tax Specialist', 'Quantitative Analyst', 'Portfolio Manager'
    ],
    'Government & Law': [
        'Lawyer', 'Legal', 'Government', 'Rechtsanwalt',
        'Jurist', 'Verwaltung', 'Beamter', 'Notar',
        'Sachbearbeiter Öffentlicher Dienst'
    ],
    'Science & Research': [
        'Researcher', 'Scientist', 'Laboratory', 'Forscher',
        'Wissenschaftler', 'Laborant', 'Chemiker', 'Biologe'
    ],
    'Culture & Media': [
        'Designer', 'Journalist', 'Media', 'Mediengestalter',
        'Grafiker', 'Redakteur', 'Fotograf', 'Marketing'
    ],
    'Security & Defense': [
        'Security Guard', 'Police', 'Military', 'Wachmann',
        'Sicherheitskraft', 'Polizist', 'Soldat'
    ],
    'Hospitality & Tourism': [
        'Tour Guide', 'Travel Agent', 'Hotel Reception',
        'Reiseverkehrskaufmann', 'Fremdenführer', 'Hotelfachmann'
    ],
    'Agriculture & Nature': [
        'Farmer', 'Gardener', 'Forester', 'Landwirt',
        'Gärtner', 'Forstwirt', 'Tierpfleger'
    ]
}

# Domain colors (match populate_domain_gate.py)
DOMAIN_COLORS = {
    'Security & Defense': '#8B0000',
    'Agriculture & Nature': '#228B22',
    'Manufacturing & Engineering': '#FF8C00',
    'Technology & Engineering': '#4169E1',
    'Construction & Trades': '#8B4513',
    'Science & Research': '#9400D3',
    'IT & Technology': '#00CED1',
    'Transport & Logistics': '#696969',
    'Commerce & Retail': '#FF69B4',
    'Business & Management': '#DAA520',
    'Hospitality & Food': '#DC143C',
    'Hospitality & Tourism': '#20B2AA',
    'Education & Social Work': '#32CD32',
    'Healthcare & Medicine': '#FF4500',
    'Finance & Banking': '#4B0082',
    'Government & Law': '#2F4F4F',
    'Culture & Media': '#FF1493'
}


def build_domain_centroids() -> dict:
    """Compute centroid embedding for each domain from reference phrases."""
    import numpy as np
    
    print("📊 Building domain reference embeddings...")
    centroids = {}
    
    for domain, phrases in DOMAIN_REFERENCES.items():
        embeddings = []
        for phrase in phrases:
            emb = get_embedding(phrase)
            if emb is not None:
                embeddings.append(emb)
        
        if embeddings:
            # Average all phrase embeddings to get domain centroid
            centroids[domain] = np.mean(embeddings, axis=0)
            print(f"  ✓ {domain}: {len(embeddings)} reference phrases")
        else:
            print(f"  ⚠️ {domain}: no embeddings!")
    
    return centroids


def classify_job_title(job_title: str, centroids: dict) -> tuple:
    """Classify a job title by finding closest domain centroid."""
    emb = get_embedding(job_title)
    if emb is None or len(emb) == 0:
        return None, 0.0
    
    best_domain = None
    best_sim = -1
    
    for domain, centroid in centroids.items():
        if len(centroid) != len(emb):
            continue  # Skip mismatched dimensions
        sim = cosine_similarity(emb, centroid)
        if sim > best_sim:
            best_sim = sim
            best_domain = domain
    
    return best_domain, best_sim


def get_unclassified_postings(conn, limit: int = None) -> list:
    """Get postings without domain_gate that have job_title."""
    cur = conn.cursor()
    
    query = """
        SELECT posting_id, job_title
        FROM postings
        WHERE (domain_gate IS NULL OR domain_gate->>'primary_domain' IS NULL)
          AND job_title IS NOT NULL
        ORDER BY posting_id
    """
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query)
    return cur.fetchall()


def preview_classification(conn, centroids: dict, sample_size: int = 50):
    """Preview classification on a sample."""
    print(f"\n🔍 PREVIEW: Classifying {sample_size} sample postings\n")
    
    postings = get_unclassified_postings(conn, limit=sample_size)
    
    domain_counts = defaultdict(int)
    results = []
    
    for row in postings:
        posting_id = row['posting_id']
        job_title = row['job_title']
        
        domain, similarity = classify_job_title(job_title, centroids)
        
        if domain:
            domain_counts[domain] += 1
            results.append({
                'posting_id': posting_id,
                'job_title': job_title[:50],
                'domain': domain,
                'similarity': similarity
            })
            print(f"  {job_title[:40]:<42} → {domain:<25} ({similarity:.2f})")
    
    print("\n📊 Domain distribution in sample:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(results)
        print(f"  {domain:<30} {count:>4} ({pct:>5.1f}%)")
    
    return results


def apply_classification(conn, centroids: dict, batch_size: int = 500):
    """Apply embedding-based classification to all unclassified postings."""
    cur = conn.cursor()
    
    postings = get_unclassified_postings(conn)
    total = len(postings)
    
    print(f"\n🔄 Classifying {total:,} postings using embeddings...")
    
    updated = 0
    domain_counts = defaultdict(int)
    low_confidence = 0
    
    for i, row in enumerate(postings):
        posting_id = row['posting_id']
        job_title = row['job_title']
        
        domain, similarity = classify_job_title(job_title, centroids)
        
        if domain and similarity >= 0.40:  # Minimum similarity threshold
            domain_gate = {
                'primary_domain': domain,
                'sub_domain': 'embedding_classified',
                'classification_method': 'embedding',
                'embedding_similarity': round(similarity, 3),
                'color': DOMAIN_COLORS.get(domain, '#999999')
            }
            
            cur.execute("""
                UPDATE postings
                SET domain_gate = %s
                WHERE posting_id = %s
            """, (json.dumps(domain_gate), posting_id))
            
            updated += 1
            domain_counts[domain] += 1
        else:
            low_confidence += 1
        
        # Progress
        if (i + 1) % batch_size == 0:
            conn.commit()
            print(f"  Processed {i+1:,}/{total:,} ({100*(i+1)/total:.1f}%)")
    
    conn.commit()
    
    print(f"\n✅ Classification complete!")
    print(f"   Updated: {updated:,}")
    print(f"   Low confidence (skipped): {low_confidence:,}")
    
    print("\n📊 Domain distribution:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / updated if updated > 0 else 0
        print(f"  {domain:<30} {count:>6,} ({pct:>5.1f}%)")
    
    return updated


def reset_embedding_classifications(conn):
    """Remove domain_gate for postings classified by embedding."""
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE postings
        SET domain_gate = NULL
        WHERE domain_gate->>'classification_method' = 'embedding'
    """)
    
    affected = cur.rowcount
    conn.commit()
    
    print(f"🔄 Reset {affected:,} embedding-classified postings")
    return affected


# =============================================================================
# DAEMON-COMPATIBLE CLASS (for turing_daemon)
# =============================================================================

# Cache for centroids (expensive to build, only do once)
_CENTROIDS_CACHE = None

def _get_centroids():
    """Get or build domain centroids (cached)."""
    global _CENTROIDS_CACHE
    if _CENTROIDS_CACHE is None:
        _CENTROIDS_CACHE = build_domain_centroids()
    return _CENTROIDS_CACHE


class DomainEmbeddingClassifier:
    """
    Daemon-compatible actor for classifying postings by domain using embeddings.
    
    Used for postings that don't have KLDB data (non-berufenet).
    The KLDB actor (1303) handles ~90% of postings; this handles the remainder.
    """
    
    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}
    
    def process(self) -> dict:
        """Process a single posting or batch."""
        posting_id = self.input_data.get('posting_id') or self.input_data.get('subject_id')
        
        if not posting_id:
            return {'success': False, 'error': 'No posting_id provided'}
        
        cur = self.conn.cursor()
        
        # Get job_title
        cur.execute("""
            SELECT posting_id, job_title
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        
        row = cur.fetchone()
        if not row:
            return {'success': False, 'error': f'Posting {posting_id} not found'}
        
        job_title = row['job_title']
        if not job_title:
            return {'success': False, 'error': 'No job_title', 'posting_id': posting_id}
        
        # Get centroids (cached)
        centroids = _get_centroids()
        
        # Classify
        domain, similarity = classify_job_title(job_title, centroids)
        
        if not domain or similarity < 0.40:
            # Low confidence - mark as unclassified but don't retry
            domain_gate = {
                'primary_domain': 'Unclassified',
                'sub_domain': 'low_confidence',
                'classification_method': 'embedding',
                'embedding_similarity': round(similarity, 3) if similarity else 0,
                'color': '#999999'
            }
            cur.execute("""
                UPDATE postings SET domain_gate = %s WHERE posting_id = %s
            """, (json.dumps(domain_gate), posting_id))
            self.conn.commit()
            return {
                'success': True,
                'posting_id': posting_id,
                'domain': 'Unclassified',
                'similarity': round(similarity, 3) if similarity else 0,
                'note': 'low_confidence'
            }
        
        # Good classification
        domain_gate = {
            'primary_domain': domain,
            'sub_domain': 'embedding_classified',
            'classification_method': 'embedding',
            'embedding_similarity': round(similarity, 3),
            'color': DOMAIN_COLORS.get(domain, '#999999')
        }
        
        cur.execute("""
            UPDATE postings SET domain_gate = %s WHERE posting_id = %s
        """, (json.dumps(domain_gate), posting_id))
        self.conn.commit()
        
        return {
            'success': True,
            'posting_id': posting_id,
            'domain': domain,
            'similarity': round(similarity, 3)
        }


def main():
    parser = argparse.ArgumentParser(description='Classify postings by domain using embeddings')
    parser.add_argument('--apply', action='store_true', help='Apply classification to database')
    parser.add_argument('--reset', action='store_true', help='Reset embedding classifications')
    parser.add_argument('--limit', type=int, help='Limit preview to N postings')
    args = parser.parse_args()
    
    conn = get_connection_raw()
    
    try:
        if args.reset:
            reset_embedding_classifications(conn)
            return
        
        # Build domain centroids
        centroids = build_domain_centroids()
        
        if args.apply:
            apply_classification(conn, centroids)
        else:
            # Preview mode
            preview_classification(conn, centroids, sample_size=args.limit or 30)
            
            # Count total unclassified
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) as cnt FROM postings 
                WHERE domain_gate IS NULL AND job_title IS NOT NULL
            """)
            total = cur.fetchone()['cnt']
            print(f"\n💡 Run with --apply to classify all {total:,} unclassified postings")
    
    finally:
        conn.close()


if __name__ == '__main__':
    main()
