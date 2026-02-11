#!/usr/bin/env python3
"""
populate_domain_gate.py - Classify postings by domain using berufenet KldB codes

Maps KldB (Klassifikation der Berufe) codes to user-friendly domain categories
and updates the domain_gate JSONB field in postings.

KldB Structure:
- First 2 digits = Berufshauptgruppe (major occupational group)
- We map these to ~12 domains useful for job seekers

Usage:
    python3 tools/populate_domain_gate.py           # Preview (dry run)
    python3 tools/populate_domain_gate.py --apply   # Apply changes

Author: Arden
Date: 2026-02-06
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection_raw, return_connection

# =============================================================================
# DOMAIN MAPPING FROM KLDB
# =============================================================================

# KldB Berufshauptgruppe (first 2 digits after 'B ') -> Domain
KLDB_TO_DOMAIN = {
    # Security & Defense
    '01': ('Security & Defense', 'military'),
    '02': ('Security & Defense', 'police'),
    '03': ('Security & Defense', 'security'),
    '53': ('Security & Defense', 'surveillance'),
    
    # Agriculture & Nature
    '11': ('Agriculture & Nature', 'agriculture'),
    '12': ('Agriculture & Nature', 'forestry'),
    '13': ('Agriculture & Nature', 'fishing'),
    '14': ('Agriculture & Nature', 'animal_care'),
    
    # Manufacturing & Production
    '21': ('Manufacturing & Engineering', 'raw_materials'),
    '22': ('Manufacturing & Engineering', 'ceramics_glass'),
    '23': ('Manufacturing & Engineering', 'paper_printing'),
    '24': ('Manufacturing & Engineering', 'metal_production'),
    '27': ('Manufacturing & Engineering', 'technical_dev'),
    '28': ('Manufacturing & Engineering', 'textiles'),
    '29': ('Hospitality & Food', 'food_production'),
    
    # Technology & Engineering
    '25': ('Technology & Engineering', 'machinery'),
    '26': ('Technology & Engineering', 'electrical'),
    
    # Construction & Trades
    '31': ('Construction & Trades', 'architecture'),
    '32': ('Construction & Trades', 'civil_engineering'),
    '33': ('Construction & Trades', 'interior_finishing'),
    '34': ('Construction & Trades', 'building_services'),
    '54': ('Construction & Trades', 'cleaning'),
    
    # Science & Research
    '41': ('Science & Research', 'natural_sciences'),
    '42': ('Science & Research', 'geography_environment'),
    
    # IT & Technology
    '43': ('IT & Technology', 'computer_science'),
    
    # Transport & Logistics
    '51': ('Transport & Logistics', 'logistics'),
    '52': ('Transport & Logistics', 'transport'),
    
    # Commerce & Retail
    '61': ('Commerce & Retail', 'purchasing'),
    '62': ('Commerce & Retail', 'sales'),
    '63': ('Hospitality & Tourism', 'tourism'),
    
    # Business & Finance
    '71': ('Business & Management', 'management'),
    '72': ('Finance & Banking', 'finance'),
    
    # Law & Government
    '73': ('Government & Law', 'law_admin'),
    
    # Healthcare
    '81': ('Healthcare & Medicine', 'medicine'),
    '82': ('Healthcare & Medicine', 'nursing'),
    
    # Education & Social
    '83': ('Education & Social Work', 'social_work'),
    '84': ('Education & Social Work', 'teaching'),
    
    # Culture & Media
    '91': ('Culture & Media', 'humanities'),
    '92': ('Culture & Media', 'media'),
    '93': ('Culture & Media', 'design'),
    '94': ('Culture & Media', 'arts'),
}

# Domain colors for visualization (match bi_app.py Set2 palette)
DOMAIN_COLORS = {
    'Healthcare & Medicine': '#66c2a5',
    'IT & Technology': '#fc8d62',
    'Manufacturing & Engineering': '#8da0cb',
    'Technology & Engineering': '#e78ac3',
    'Construction & Trades': '#a6d854',
    'Finance & Banking': '#ffd92f',
    'Commerce & Retail': '#e5c494',
    'Transport & Logistics': '#b3b3b3',
    'Education & Social Work': '#80b1d3',
    'Science & Research': '#fdb462',
    'Hospitality & Tourism': '#bc80bd',
    'Hospitality & Food': '#ccebc5',
    'Government & Law': '#ffed6f',
    'Business & Management': '#d9d9d9',
    'Agriculture & Nature': '#ffffb3',
    'Security & Defense': '#bebada',
    'Culture & Media': '#fb8072',
}

# =============================================================================
# PHASE 2A: KEYWORD PATTERN DOMAIN MATCHER
# =============================================================================
# For postings with no KldB code — match domain from job title keywords.
# Order matters: more specific patterns first.

KEYWORD_DOMAIN_RULES = [
    # Healthcare & Medicine (Pflege, Medizin, Klinik, Arzt, Therapeut, OTA, MFA)
    (r'pflege|pflegefach|pflegedienst|altenpflege|krankenpflege|gesundheits|klinik|'
     r'arzt|ärztin|ärzt|medizin|therapeut|therapie|krankenhaus|rettung|sanitä|'
     r'hebamme|physiother|ergother|logopä|radiolog|apothek|pharma|zahnmed|'
     r'zahnarzt|kieferorth|augenopt|hörakustik|ota\b|mfa\b|mta\b|mtla\b|'
     r'wohnbereich|einrichtungsleitung|hauswirtschaft|hygiene',
     'Healthcare & Medicine', 'healthcare'),

    # IT & Technology
    (r'software|developer|programm|devops|it[ -]|informatik|daten|data\b|cloud|'
     r'cyber|sap\b|system.?admin|netzwerk|frontend|backend|fullstack|full.?stack|'
     r'scrum|agile|kubernetes|linux|python|java\b|\.net|webentwick|app.?entwick|'
     r'ki\b|künstliche.?intelligenz|machine.?learn|artificial|deep.?learn',
     'IT & Technology', 'it'),

    # Manufacturing & Engineering (Produktion, Fertigung, Montage)
    (r'produktions|fertigungs|montage|monteur|maschinen|anlagen|schweiß|'
     r'schlosser|dreher|fräser|zerspanung|werkzeug|industriemech|'
     r'verfahrens|qualitätssicherung|cnc|galvanik|gießer|'
     r'produktionshelfer|produktionsmit|quereinsteiger.?produktion',
     'Manufacturing & Engineering', 'production'),

    # Technology & Engineering (Technik, Ingenieur, Elektro)
    (r'ingenieur|engineer|techniker|elektronik|elektro|elektrik|'
     r'mechatronik|automatisierung|steuerung|service.?technik|'
     r'mess.?technik|regelung|prüf|instandhalt|wartung',
     'Technology & Engineering', 'engineering'),

    # Construction & Trades (Bau, Handwerk)
    (r'maurer|zimmerer|dachdecker|maler|lackier|tischler|schreiner|'
     r'fliesenleger|estrich|beton|stuckateur|trockenbau|rohrleitungs|'
     r'klempner|sanitär|heizung|bauleiter|bauleit|polier|gerüst|'
     r'tiefbau|hochbau|straßenbau|gleisbau|baumasch',
     'Construction & Trades', 'construction'),

    # Transport & Logistics (Fahrer, Lager, Logistik, Post)
    (r'fahrer|berufskraftfahrer|lkw|spedition|logistik|lager|'
     r'kommission|versand|postbot|brief|paket|kurier|zustell|'
     r'gabelstapler|stapler|dispon|transport|bahn.?energie|lokführ',
     'Transport & Logistics', 'logistics'),

    # Commerce & Retail (Verkauf, Handel, Kasse)
    (r'verkäuf|einzelhandel|kassierer|kassier|filial|marktleiter|'
     r'handelsfach|drogist|vertrieb|außendienst|innendienst|'
     r'einkauf|beschaffung|key.?account|kundenberater|'
     r'kundenbetreuer',
     'Commerce & Retail', 'retail'),

    # Finance & Banking (Buchhaltung, Finanzen, Bank, Steuer)
    (r'buchhal|finanzbuch|bilanz|steuer|wirtschaftsprüf|'
     r'controller|controlling|revision|audit|kredit|bank|'
     r'versicherung|immobilien|zoll|debitor|kreditor',
     'Finance & Banking', 'finance'),

    # Business & Management
    (r'geschäftsführ|management|manager|personal|hr\b|'
     r'sachbearbeit|verwaltung|büro|sekretär|assistenz|'
     r'projektleiter|projektmanag|prozess|organisation',
     'Business & Management', 'management'),

    # Hospitality & Food
    (r'koch|köchin|küche|bäcker|konditor|metzger|fleischer|'
     r'barista|gastronom|restaurant|hotel|rezeption|housekeep|'
     r'catering|systemgastro|lebensmittel',
     'Hospitality & Food', 'food'),

    # Education & Social Work
    (r'erzieher|pädagog|sozialarbeit|sozialpäd|lehrer|lehrkraft|'
     r'dozent|trainer|ausbildung|kinderpflege|kindergarten|kita|'
     r'jugend|betreuung|schulbegleit|inklusionsass',
     'Education & Social Work', 'education'),

    # Science & Research
    (r'biolog|chemie|chemiela|labor|forschung|wissenschaft|'
     r'geolog|physik|umwelt|ökolog|analyst',
     'Science & Research', 'research'),

    # Agriculture & Nature
    (r'landwirt|gärtner|garten|forst|tier|veterinär|florist',
     'Agriculture & Nature', 'agriculture'),

    # Government & Law
    (r'rechtsanwalt|jurist|notar|anwalt|richter|staatsanwalt|'
     r'rechts|verwaltungsfach|beamt|öffentlich.?dienst',
     'Government & Law', 'law'),

    # Security & Defense
    (r'sicherheit|wachschutz|objektschutz|detektiv|feuerwehr|'
     r'werkschutz|schutz.?dienst|bewachung',
     'Security & Defense', 'security'),

    # Culture & Media
    (r'grafik|design|medien|redakteur|journalist|fotograf|'
     r'kamera|video|film|museum|bibliothek',
     'Culture & Media', 'media'),

    # Hospitality & Tourism
    (r'tourismus|reise|travel|touristik|fremdenverkehr',
     'Hospitality & Tourism', 'tourism'),
]

import re
# Compile patterns once
_COMPILED_RULES = [(re.compile(p, re.IGNORECASE), d, s) for p, d, s in KEYWORD_DOMAIN_RULES]


def keyword_domain_match(title: str) -> dict:
    """Match a job title to a domain using keyword patterns. Returns domain_gate dict or None."""
    if not title:
        return None
    for pattern, domain, subdomain in _COMPILED_RULES:
        if pattern.search(title):
            return {
                'primary_domain': domain,
                'sub_domain': subdomain,
                'source': 'keyword_pattern',
                'color': DOMAIN_COLORS.get(domain, '#999999')
            }
    return None


# =============================================================================
# PHASE 2B: DOMAIN CENTROID EMBEDDING
# =============================================================================
# Compare title embedding to pre-computed domain centroid embeddings.
# Centroids are the average embedding of all titles already classified
# in each domain.

import os
import numpy as np
import requests

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings'
EMBED_MODEL = "bge-m3:567m"

def get_title_embedding(text: str) -> 'Optional[np.ndarray]':
    """Get embedding from Ollama."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            emb = np.array(resp.json()['embedding'])
            if np.any(np.isnan(emb)):
                return None
            return emb
    except Exception as e:
        pass
    return None


def build_domain_centroids(conn) -> dict:
    """Build centroid embedding per domain from already-classified postings.
    
    Returns dict: domain_name -> np.ndarray (centroid vector)
    Samples up to 200 titles per domain for speed.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (p.job_title)
            p.job_title,
            p.domain_gate->>'primary_domain' as domain
        FROM postings p
        WHERE p.domain_gate IS NOT NULL
          AND p.domain_gate->>'primary_domain' IS NOT NULL
          AND p.job_title IS NOT NULL
        ORDER BY p.job_title
    """)
    rows = cur.fetchall()
    
    # Group titles by domain, sample up to 200 per domain
    from collections import defaultdict
    import random
    domain_titles = defaultdict(list)
    for row in rows:
        domain_titles[row['domain']].append(row['job_title'])
    
    centroids = {}
    for domain, titles in domain_titles.items():
        sample = random.sample(titles, min(200, len(titles)))
        embeddings = []
        for t in sample:
            emb = get_title_embedding(t)
            if emb is not None:
                embeddings.append(emb)
        if embeddings:
            centroids[domain] = np.mean(embeddings, axis=0)
            print(f"  Centroid for {domain}: {len(embeddings)} samples")
    
    return centroids


def embedding_domain_match(title: str, centroids: dict, threshold: float = 0.55) -> dict:
    """Match a title to a domain using embedding cosine similarity to centroids.
    
    Returns domain_gate dict or None.
    """
    emb = get_title_embedding(title)
    if emb is None:
        return None
    
    best_domain = None
    best_score = -1
    
    for domain, centroid in centroids.items():
        norm_e = np.linalg.norm(emb)
        norm_c = np.linalg.norm(centroid)
        if norm_e == 0 or norm_c == 0:
            continue
        score = float(np.dot(emb, centroid) / (norm_e * norm_c))
        if score > best_score:
            best_score = score
            best_domain = domain
    
    if best_domain and best_score >= threshold:
        return {
            'primary_domain': best_domain,
            'sub_domain': 'embedding',
            'source': 'domain_centroid',
            'confidence': round(best_score, 3),
            'color': DOMAIN_COLORS.get(best_domain, '#999999')
        }
    return None


# =============================================================================
# PHASE 2C: LLM DOMAIN CLASSIFICATION
# =============================================================================

DOMAIN_LIST = sorted(DOMAIN_COLORS.keys())

LLM_DOMAIN_PROMPT = """You classify German job titles into domains.

DOMAINS:
{domain_list}

RULES:
- Pick exactly ONE domain from the list above.
- Answer with ONLY the domain name, nothing else.
- If truly impossible to classify, answer: UNKNOWN

Job title: "{title}"
Domain:"""


def llm_domain_classify(title: str, model: str = "qwen2.5:7b") -> dict:
    """Use LLM to assign a domain to an unclassified job title.
    
    Returns domain_gate dict or None.
    """
    import subprocess
    
    domain_list = "\n".join(f"- {d}" for d in DOMAIN_LIST)
    prompt = LLM_DOMAIN_PROMPT.format(domain_list=domain_list, title=title)
    
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60
        )
        answer = result.stdout.strip()
        
        # Match answer to known domain (fuzzy — LLM might add punctuation)
        for domain in DOMAIN_LIST:
            if domain.lower() in answer.lower():
                return {
                    'primary_domain': domain,
                    'sub_domain': 'llm',
                    'source': 'llm_domain',
                    'color': DOMAIN_COLORS.get(domain, '#999999')
                }
    except Exception:
        pass
    return None


# =============================================================================
# PHASE 2 CASCADE: pattern → centroid → LLM
# =============================================================================

def classify_domain_cascade(title: str, centroids: dict = None) -> dict:
    """Three-layer cascade to assign a domain to a job title.
    
    Layer 1: Keyword pattern match (instant, deterministic)
    Layer 2: Embedding centroid similarity (fast, no LLM)
    Layer 3: LLM direct classification (slow, accurate)
    
    Returns (domain_gate_dict, method_used) or (None, None).
    """
    # Layer 1: Pattern
    result = keyword_domain_match(title)
    if result:
        return result, 'pattern'
    
    # Layer 2: Embedding centroid
    if centroids:
        result = embedding_domain_match(title, centroids)
        if result:
            return result, 'centroid'
    
    # Layer 3: LLM
    result = llm_domain_classify(title)
    if result:
        return result, 'llm'
    
    return None, None


def extract_hauptgruppe(kldb: str) -> str:
    """Extract the 2-digit Berufshauptgruppe from a KldB code like 'B 11104'."""
    if not kldb or len(kldb) < 4:
        return None
    # Format is "B XXXXX" where we want positions 2-3 (after "B ")
    return kldb[2:4] if kldb.startswith('B ') else kldb[:2]


def get_domain_info(kldb: str) -> dict:
    """Get domain information for a KldB code."""
    hauptgruppe = extract_hauptgruppe(kldb)
    if not hauptgruppe or hauptgruppe not in KLDB_TO_DOMAIN:
        return None
    
    domain, subdomain = KLDB_TO_DOMAIN[hauptgruppe]
    return {
        'primary_domain': domain,
        'sub_domain': subdomain,
        'kldb_hauptgruppe': hauptgruppe,
        'color': DOMAIN_COLORS.get(domain, '#999999')
    }


def get_postings_to_update(conn, limit: int = None) -> list:
    """Get postings with berufenet links that need domain classification.
    
    Uses UNION of:
    1. Direct berufenet_id link (preferred)
    2. Synonym lookup via berufenet_synonyms table
    """
    cur = conn.cursor()
    
    query = """
        -- Direct berufenet_id link (most postings have this)
        SELECT DISTINCT
            p.posting_id,
            b.kldb,
            b.name as berufenet_name
        FROM postings p
        JOIN berufenet b ON b.berufenet_id = p.berufenet_id
        WHERE (p.domain_gate IS NULL OR p.domain_gate->>'primary_domain' IS NULL)
          AND b.kldb IS NOT NULL
        
        UNION
        
        -- Synonym lookup for postings without direct berufenet_id
        SELECT DISTINCT
            p.posting_id,
            b.kldb,
            b.name as berufenet_name
        FROM postings p
        JOIN berufenet_synonyms bs ON LOWER(p.beruf) = LOWER(bs.aa_beruf)
        JOIN berufenet b ON bs.berufenet_id = b.berufenet_id
        WHERE (p.domain_gate IS NULL OR p.domain_gate->>'primary_domain' IS NULL)
          AND b.kldb IS NOT NULL
          AND p.berufenet_id IS NULL
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query)
    return cur.fetchall()


def preview_domain_distribution(conn):
    """Preview what the domain distribution would look like."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            SUBSTRING(b.kldb FROM 3 FOR 2) as hauptgruppe,
            COUNT(*) as postings
        FROM postings p
        JOIN berufenet_synonyms bs ON LOWER(p.beruf) = LOWER(bs.aa_beruf)
        JOIN berufenet b ON bs.berufenet_id = b.berufenet_id
        WHERE b.kldb IS NOT NULL
        GROUP BY SUBSTRING(b.kldb FROM 3 FOR 2)
        ORDER BY postings DESC
    """)
    
    rows = cur.fetchall()
    
    print("\n📊 DOMAIN DISTRIBUTION PREVIEW")
    print("=" * 60)
    
    domain_totals = {}
    for row in rows:
        hauptgruppe = row['hauptgruppe']
        count = row['postings']
        if hauptgruppe in KLDB_TO_DOMAIN:
            domain, _ = KLDB_TO_DOMAIN[hauptgruppe]
            domain_totals[domain] = domain_totals.get(domain, 0) + count
    
    # Sort by count
    sorted_domains = sorted(domain_totals.items(), key=lambda x: -x[1])
    
    total = sum(domain_totals.values())
    print(f"\nTotal classifiable postings: {total:,}\n")
    
    for domain, count in sorted_domains:
        pct = 100 * count / total
        bar = '█' * int(pct / 2)
        print(f"  {domain:<30} {count:>6,} ({pct:>5.1f}%) {bar}")
    
    print("\n" + "=" * 60)
    return domain_totals


def update_postings_batch(conn, postings: list, batch_size: int = 1000) -> int:
    """Update postings with domain_gate in batches."""
    cur = conn.cursor()
    updated = 0
    
    for i in range(0, len(postings), batch_size):
        batch = postings[i:i + batch_size]
        
        for row in batch:
            posting_id = row['posting_id']
            kldb = row['kldb']
            domain_info = get_domain_info(kldb)
            if domain_info:
                cur.execute("""
                    UPDATE postings 
                    SET domain_gate = %s
                    WHERE posting_id = %s
                """, (json.dumps(domain_info), posting_id))
                updated += 1
        
        conn.commit()
        print(f"  Updated {updated:,} postings...")
    
    return updated


# =============================================================================
# PULL DAEMON ACTOR CLASS
# =============================================================================

class DomainGateClassifier:
    """Pull daemon actor: classify a single posting's domain from KldB codes."""

    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}

    def process(self) -> dict:
        posting_id = self.input_data.get('subject_id')
        if not posting_id:
            return {'status': 'error', 'error': 'no subject_id'}

        cur = self.conn.cursor()

        # Try direct berufenet_id link first, then synonym fallback
        cur.execute("""
            SELECT b.kldb
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE p.posting_id = %s AND b.kldb IS NOT NULL
            UNION
            SELECT b.kldb
            FROM postings p
            JOIN berufenet_synonyms bs ON LOWER(p.beruf) = LOWER(bs.aa_beruf)
            JOIN berufenet b ON bs.berufenet_id = b.berufenet_id
            WHERE p.posting_id = %s AND b.kldb IS NOT NULL AND p.berufenet_id IS NULL
            LIMIT 1
        """, (posting_id, posting_id))

        row = cur.fetchone()
        if not row:
            return {'status': 'skip', 'reason': 'no_kldb_link'}

        domain_info = get_domain_info(row['kldb'])
        if not domain_info:
            return {'status': 'skip', 'reason': 'unmapped_hauptgruppe'}

        cur.execute(
            "UPDATE postings SET domain_gate = %s WHERE posting_id = %s",
            (json.dumps(domain_info), posting_id)
        )
        self.conn.commit()

        return {
            'status': 'success',
            'domain': domain_info['primary_domain'],
            'sub_domain': domain_info['sub_domain']
        }


def main():
    parser = argparse.ArgumentParser(description="Populate domain_gate from berufenet KldB codes")
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--limit', type=int, help='Limit number of postings to update')
    parser.add_argument('--cascade', action='store_true',
                        help='Run Phase 2 cascade (pattern→centroid→LLM) on postings with no domain_gate')
    
    args = parser.parse_args()
    
    conn = get_connection_raw()
    
    try:
        if args.cascade:
            # =================================================================
            # Phase 2 cascade: classify postings that have no KldB code
            # =================================================================
            import time
            cur = conn.cursor()
            
            cur.execute("""
                SELECT job_title, COUNT(*) as cnt
                FROM postings
                WHERE (domain_gate IS NULL OR domain_gate->>'primary_domain' IS NULL)
                  AND job_title IS NOT NULL
                  AND job_title != ''
                GROUP BY job_title
                ORDER BY cnt DESC
            """)
            titles = cur.fetchall()
            
            if not titles:
                print("✅ All postings have domain_gate — nothing to do!")
                return
            
            total = len(titles)
            print(f"\n{'='*60}")
            print(f"Domain Gate Cascade — {total} unique titles")
            print(f"{'='*60}")
            print(f"Layer 1: Keyword patterns (instant)")
            print(f"Layer 2: Embedding centroids (Ollama)")
            print(f"Layer 3: LLM classification (qwen2.5:7b)")
            print()
            
            # Quick scan: how many can pattern matching handle?
            pattern_hits = sum(1 for t in titles if keyword_domain_match(t['job_title']))
            print(f"Pattern pre-scan: {pattern_hits}/{total} titles matchable ({100*pattern_hits/total:.0f}%)")
            remaining = total - pattern_hits
            print(f"Will need LLM for: {remaining} titles")
            print()
            
            if not args.apply:
                print("⚠️  DRY RUN — run with --cascade --apply to execute")
                return
            
            # Skip centroid building — LLM is faster for ~2k titles
            # than building 17 centroids × 200 embeddings
            centroids = None
            
            stats = {'pattern': 0, 'centroid': 0, 'llm': 0, 'unclassified': 0, 'error': 0}
            start = time.time()
            
            for i, row in enumerate(titles):
                title = row['job_title']
                try:
                    gate, method = classify_domain_cascade(title, centroids)
                    
                    if gate:
                        cur.execute("""
                            UPDATE postings
                            SET domain_gate = %s
                            WHERE job_title = %s
                              AND (domain_gate IS NULL OR domain_gate->>'primary_domain' IS NULL)
                        """, (json.dumps(gate), title))
                        conn.commit()
                        stats[method] += 1
                    else:
                        stats['unclassified'] += 1
                except Exception as e:
                    stats['error'] += 1
                    conn.rollback()
                
                # Progress every 100
                if (i + 1) % 100 == 0:
                    elapsed = time.time() - start
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    print(f"  {i+1}/{total} ({rate:.1f}/s) — "
                          f"pattern:{stats['pattern']} centroid:{stats['centroid']} "
                          f"llm:{stats['llm']} none:{stats['unclassified']}")
            
            elapsed = time.time() - start
            print(f"\n{'='*60}")
            print(f"COMPLETED in {elapsed:.0f}s ({total/(elapsed or 1):.1f} titles/s)")
            print(f"{'='*60}")
            print(f"  🔤 Keyword pattern:    {stats['pattern']}")
            print(f"  📐 Embedding centroid:  {stats['centroid']}")
            print(f"  🤖 LLM classification: {stats['llm']}")
            print(f"  ❌ Unclassified:        {stats['unclassified']}")
            print(f"  ⚠️  Errors:             {stats['error']}")
            classified = stats['pattern'] + stats['centroid'] + stats['llm']
            print(f"  ─────────────────────")
            print(f"  ✅ Total classified:    {classified}/{total} ({100*classified/total:.0f}%)")
            return
        
        # Always show preview
        domain_totals = preview_domain_distribution(conn)
        
        if not args.apply:
            print("\n⚠️  DRY RUN - No changes made")
            print("   Run with --apply to update the database")
            return
        
        # Get postings to update
        print("\n🔄 Fetching postings to update...")
        postings = get_postings_to_update(conn, args.limit)
        print(f"   Found {len(postings):,} postings needing classification")
        
        if len(postings) == 0:
            print("   Nothing to update!")
            return
        
        # Update
        print("\n📝 Updating domain_gate...")
        updated = update_postings_batch(conn, postings)
        
        print(f"\n✅ Done! Updated {updated:,} postings with domain classification")
        
        # Verify
        cur = conn.cursor()
        cur.execute("""
            SELECT domain_gate->>'primary_domain' as domain, COUNT(*) as cnt
            FROM postings 
            WHERE domain_gate IS NOT NULL 
            GROUP BY 1 ORDER BY 2 DESC
        """)
        print("\n📊 Final domain distribution:")
        for row in cur.fetchall():
            print(f"   {row['domain']}: {row['cnt']:,}")
        
    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
