#!/usr/bin/env python3
import os

"""
Berufenet Auto-Matcher — 3-Tier Cascade for Profession Classification

Matches AA's non-standard profession names (beruf) to canonical berufenet entries.

TIER 1: Pattern Matching (instant, SQL)
   - Strip specialization suffixes: "Schweißer/in - Konstruktionstechnik" → "Schweißer/in"
   - Strip parentheticals: "Tiefbaufacharbeiter/in (ohne Angabe...)" → "Tiefbaufacharbeiter/in"
   - Handle word order variations
   
TIER 2: Embedding Search (fast, GPU)
   - BGE-M3 semantic similarity
   - Threshold: 0.88 for auto-match, 0.80-0.88 for review queue

TIER 3: LLM Suggestion (slow, manual review)
   - qwen2.5:7b suggests best match
   - Outputs to review queue for human approval

Usage:
    python3 tools/berufenet_auto_matcher.py                    # Full cascade
    python3 tools/berufenet_auto_matcher.py --tier 1           # Pattern only
    python3 tools/berufenet_auto_matcher.py --tier 2           # Embedding only  
    python3 tools/berufenet_auto_matcher.py --tier 3 --limit 50  # LLM suggestions
    python3 tools/berufenet_auto_matcher.py --dry-run          # Preview matches
    python3 tools/berufenet_auto_matcher.py --report           # Show unmatched stats
"""

import argparse
import re
import json
import sys
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.database import get_connection


def tlog(msg: str):
    """Print timestamped message to stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


@dataclass
class MatchResult:
    """Result of a matching attempt."""
    aa_beruf: str
    berufenet_id: Optional[str]
    berufenet_name: Optional[str]
    tier: int  # 1=pattern, 2=embedding, 3=llm
    confidence: float  # 1.0 for exact, 0.0-1.0 for similarity
    method: str  # e.g., "strip_suffix", "embedding_0.92", "llm_suggestion"
    posting_count: int


# =============================================================================
# TIER 1: Pattern Matching
# =============================================================================

def normalize_beruf(beruf: str) -> str:
    """Normalize a profession name for matching."""
    if not beruf:
        return ""
    
    # Lowercase and strip whitespace
    s = beruf.strip()
    
    # Remove common suffixes after " - "
    # "Schweißer/in - Konstruktionstechnik" → "Schweißer/in"
    if ' - ' in s:
        s = s.split(' - ')[0].strip()
    
    # Remove parenthetical qualifiers
    # "Tiefbaufacharbeiter/in (ohne Angabe des Schwerpunkts)" → "Tiefbaufacharbeiter/in"
    s = re.sub(r'\s*\([^)]+\)\s*$', '', s).strip()
    
    # Remove trailing qualifiers like "(m/w/d)"
    s = re.sub(r'\s*\(m/w/d\)\s*$', '', s, flags=re.IGNORECASE).strip()
    
    return s


def get_pattern_variations(beruf: str) -> List[str]:
    """Generate pattern variations of a profession name."""
    variations = set()
    
    # Original
    variations.add(beruf)
    
    # Normalized (strip suffix, parentheticals)
    normalized = normalize_beruf(beruf)
    variations.add(normalized)
    
    # Try removing leading qualifiers like "Medizinisch-technische/r"
    # "Medizinisch-technische/r Laboratoriumsassistent/in" → might match something
    if '/' in beruf:
        # Try last part only
        parts = beruf.split()
        if len(parts) > 1:
            variations.add(parts[-1])  # Last word
    
    # Remove gender suffixes and try
    # "Schweißer/in" → "Schweißer"
    degender = re.sub(r'/in\b', '', beruf)
    variations.add(degender)
    variations.add(normalize_beruf(degender))
    
    # Handle "Technische/r X" → "Technischer X" or "Technische X"
    if '/r ' in beruf:
        variations.add(beruf.replace('/r ', 'r '))
        variations.add(beruf.replace('/r ', ' '))
    
    # Handle compound professions - try base form
    # "CNC-Schleifer/in" → "Schleifer/in"
    if '-' in beruf:
        base = beruf.split('-')[-1].strip()
        if len(base) > 5:  # Avoid too-short bases
            variations.add(base)
    
    return [v for v in variations if v and len(v) > 3]


def tier1_pattern_match(dry_run: bool = False) -> Dict[str, int]:
    """
    Tier 1: Pattern-based matching via SQL.
    
    Matches unmatched berufe to berufenet entries by:
    1. Stripping specialization suffixes
    2. Stripping parenthetical qualifiers
    3. Case-insensitive comparison
    
    Returns dict with match counts by method.
    """
    stats = {'strip_suffix': 0, 'strip_parens': 0, 'base_form': 0}
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get all unmatched berufe with their posting counts
        cur.execute('''
            SELECT beruf, COUNT(*) as cnt
            FROM postings 
            WHERE beruf IS NOT NULL 
              AND berufenet_id IS NULL
              AND source = 'arbeitsagentur'
            GROUP BY beruf
            ORDER BY cnt DESC
        ''')
        unmatched = cur.fetchall()
        
        if not unmatched:
            print("  No unmatched professions found!")
            return stats
        
        # Load berufenet lookup (name → id, kldb)
        cur.execute('SELECT berufenet_id, name, kldb FROM berufenet')
        berufenet_lookup = {}
        for row in cur.fetchall():
            # Store both original and lowercase
            berufenet_lookup[row['name'].lower()] = row
        
        # Process each unmatched beruf
        matches_to_insert = []
        
        for row in unmatched:
            beruf = row['beruf']
            cnt = row['cnt']
            
            # Try pattern variations
            for variation in get_pattern_variations(beruf):
                lookup_key = variation.lower()
                if lookup_key in berufenet_lookup:
                    match = berufenet_lookup[lookup_key]
                    matches_to_insert.append({
                        'aa_beruf': beruf,
                        'berufenet_id': match['berufenet_id'],
                        'berufenet_name': match['name'],
                        'method': 'pattern',
                        'posting_count': cnt
                    })
                    
                    # Determine which pattern worked
                    if variation != beruf:
                        if ' - ' in beruf and ' - ' not in variation:
                            stats['strip_suffix'] += cnt
                        elif '(' in beruf and '(' not in variation:
                            stats['strip_parens'] += cnt
                        else:
                            stats['base_form'] += cnt
                    break
        
        if dry_run:
            print(f"\n  DRY RUN - Would add {len(matches_to_insert)} synonyms:")
            for m in matches_to_insert[:20]:
                print(f"    {m['aa_beruf'][:50]:50s} → {m['berufenet_name'][:40]} ({m['posting_count']} postings)")
            if len(matches_to_insert) > 20:
                print(f"    ... and {len(matches_to_insert) - 20} more")
        else:
            # Insert new synonyms (with separate commits to avoid cascade failures)
            inserted = 0
            for m in matches_to_insert:
                try:
                    cur.execute('''
                        INSERT INTO berufenet_synonyms (aa_beruf, berufenet_id, source, created_at)
                        VALUES (%s, %s, 'auto_pattern', NOW())
                        ON CONFLICT (aa_beruf) DO NOTHING
                    ''', (m['aa_beruf'], m['berufenet_id']))
                    inserted += cur.rowcount
                    conn.commit()  # Commit each insert to avoid cascade failures
                except Exception as e:
                    conn.rollback()  # Rollback failed transaction
                    print(f"    Warning: Could not insert synonym for {m['aa_beruf']}: {e}")
            
            conn.commit()
            
            # Now run the classification to apply new synonyms
            cur.execute('''
                UPDATE postings p
                SET 
                    berufenet_id = bn.berufenet_id,
                    berufenet_name = bn.name,
                    berufenet_kldb = bn.kldb,
                    berufenet_verified = 'auto_pattern'
                FROM berufenet_synonyms s
                JOIN berufenet bn ON s.berufenet_id = bn.berufenet_id
                WHERE p.beruf = s.aa_beruf
                  AND p.beruf IS NOT NULL
                  AND p.berufenet_id IS NULL
            ''')
            classified = cur.rowcount
            conn.commit()
            
            print(f"  Added {len(matches_to_insert)} new synonyms")
            print(f"  Classified {classified} postings")
    
    return stats


# =============================================================================
# TIER 2: Embedding Search
# =============================================================================

def get_berufenet_embeddings(conn) -> Dict[str, Tuple[str, str, List[float]]]:
    """Load berufenet profession embeddings."""
    cur = conn.cursor()
    
    # Check if we have berufenet embeddings (join on text)
    cur.execute('''
        SELECT e.text, e.embedding, b.berufenet_id, b.name, b.kldb
        FROM embeddings e
        JOIN berufenet b ON e.text = b.name
        LIMIT 1
    ''')
    
    if not cur.fetchone():
        # Need to generate berufenet embeddings first
        return None
    
    cur.execute('''
        SELECT e.text, e.embedding, b.berufenet_id, b.name, b.kldb
        FROM embeddings e
        JOIN berufenet b ON e.text = b.name
    ''')
    
    result = {}
    for row in cur.fetchall():
        result[row['berufenet_id']] = (row['name'], row['kldb'], row['embedding'])
    
    return result


def generate_berufenet_embeddings():
    """Generate embeddings for all berufenet profession names."""
    import requests
    import hashlib
    import json as json_module
    
    print("  Generating berufenet profession embeddings...")
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Get all berufenet entries without embeddings
        # Embeddings table is content-addressed by text_hash
        cur.execute('''
            SELECT b.berufenet_id, b.name
            FROM berufenet b
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e 
                WHERE e.text = b.name
            )
        ''')
        missing = cur.fetchall()
        
        if not missing:
            print("    All berufenet entries already have embeddings")
            return
        
        print(f"    Generating {len(missing)} embeddings...")
        
        for i, row in enumerate(missing):
            name = row['name']
            text_hash = hashlib.sha256(name.encode()).hexdigest()
            
            # Call Ollama for embedding
            try:
                resp = requests.post(
                    os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings',
                    json={'model': 'bge-m3:567m', 'prompt': name},
                    timeout=30
                )
                resp.raise_for_status()
                embedding = resp.json()['embedding']
                
                # Store embedding (content-addressed)
                cur.execute('''
                    INSERT INTO embeddings (text_hash, text, embedding, model, created_at)
                    VALUES (%s, %s, %s, 'bge-m3:567m', NOW())
                    ON CONFLICT (text_hash) DO UPDATE SET
                        embedding = EXCLUDED.embedding
                ''', (text_hash, name, json_module.dumps(embedding)))
                
                if (i + 1) % 100 == 0:
                    conn.commit()
                    print(f"    {i + 1}/{len(missing)} embeddings generated")
                    
            except Exception as e:
                print(f"    Warning: Failed to embed '{name}': {e}")
        
        conn.commit()
        print(f"    Done! Generated {len(missing)} berufenet embeddings")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors using numpy."""
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def tier2_embedding_match(
    threshold_auto: float = 0.88,
    threshold_review: float = 0.80,
    limit: int = 100,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Tier 2: Embedding-based matching.
    
    For each unmatched beruf:
    1. Generate embedding via BGE-M3
    2. Find most similar berufenet entry
    3. If similarity >= threshold_auto: auto-match
    4. If similarity >= threshold_review: add to review queue
    
    Returns dict with match counts.
    """
    import requests
    
    stats = {'auto_matched': 0, 'review_queue': 0, 'no_match': 0}
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # First, ensure berufenet embeddings exist
        # Join with berufenet to check how many profession names have embeddings
        cur.execute('''
            SELECT COUNT(*) as cnt FROM berufenet b
            WHERE EXISTS (SELECT 1 FROM embeddings e WHERE e.text = b.name)
        ''')
        berufenet_embed_count = cur.fetchone()['cnt']
        
        if berufenet_embed_count < 100:
            print("  Need to generate berufenet embeddings first...")
            generate_berufenet_embeddings()
        
        # Load all berufenet embeddings
        cur.execute('''
            SELECT b.berufenet_id, b.name, b.kldb, e.embedding
            FROM berufenet b
            JOIN embeddings e ON e.text = b.name
        ''')
        berufenet_data = cur.fetchall()
        
        if not berufenet_data:
            print("  No berufenet embeddings found!")
            return stats
        
        print(f"  Loaded {len(berufenet_data)} berufenet embeddings")
        
        # Get unmatched berufe (limit for efficiency)
        cur.execute('''
            SELECT beruf, COUNT(*) as cnt
            FROM postings 
            WHERE beruf IS NOT NULL 
              AND berufenet_id IS NULL
              AND source = 'arbeitsagentur'
            GROUP BY beruf
            ORDER BY cnt DESC
            LIMIT %s
        ''', (limit,))
        unmatched = cur.fetchall()
        
        if not unmatched:
            print("  No unmatched professions!")
            return stats
        
        print(f"  Processing {len(unmatched)} unmatched professions...")
        
        auto_matches = []
        review_queue = []
        
        for i, row in enumerate(unmatched):
            beruf = row['beruf']
            cnt = row['cnt']
            
            # Generate embedding for this beruf
            try:
                resp = requests.post(
                    os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings',
                    json={'model': 'bge-m3:567m', 'prompt': beruf},
                    timeout=30
                )
                resp.raise_for_status()
                beruf_embedding = resp.json()['embedding']
            except Exception as e:
                print(f"    Warning: Failed to embed '{beruf}': {e}")
                continue
            
            # Find best match
            best_match = None
            best_similarity = 0.0
            
            for brow in berufenet_data:
                sim = cosine_similarity(beruf_embedding, brow['embedding'])
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = brow
            
            if best_similarity >= threshold_auto:
                auto_matches.append({
                    'aa_beruf': beruf,
                    'berufenet_id': best_match['berufenet_id'],
                    'berufenet_name': best_match['name'],
                    'similarity': best_similarity,
                    'posting_count': cnt
                })
                stats['auto_matched'] += cnt
            elif best_similarity >= threshold_review:
                review_queue.append({
                    'aa_beruf': beruf,
                    'berufenet_id': best_match['berufenet_id'],
                    'berufenet_name': best_match['name'],
                    'similarity': best_similarity,
                    'posting_count': cnt
                })
                stats['review_queue'] += cnt
            else:
                stats['no_match'] += cnt
            
            if (i + 1) % 20 == 0:
                print(f"    {i + 1}/{len(unmatched)} processed...")
        
        # Report results
        print(f"\n  Results:")
        print(f"    Auto-match (>={threshold_auto}): {len(auto_matches)} professions")
        print(f"    Review queue ({threshold_review}-{threshold_auto}): {len(review_queue)} professions")
        
        if dry_run:
            print(f"\n  DRY RUN - Auto matches:")
            for m in auto_matches[:15]:
                print(f"    {m['aa_beruf'][:45]:45s} → {m['berufenet_name'][:35]:35s} ({m['similarity']:.3f}, {m['posting_count']} posts)")
            
            print(f"\n  DRY RUN - Review queue:")
            for m in review_queue[:15]:
                print(f"    {m['aa_beruf'][:45]:45s} → {m['berufenet_name'][:35]:35s} ({m['similarity']:.3f}, {m['posting_count']} posts)")
        else:
            # Insert auto-matches as synonyms
            inserted = 0
            for m in auto_matches:
                try:
                    cur.execute('''
                        INSERT INTO berufenet_synonyms (aa_beruf, berufenet_id, source, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (aa_beruf) DO NOTHING
                    ''', (m['aa_beruf'], m['berufenet_id'], f"auto_embed_{m['similarity']:.2f}"))
                    inserted += cur.rowcount
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    print(f"    Warning: {e}")
            
            # Apply new synonyms to postings
            cur.execute('''
                UPDATE postings p
                SET 
                    berufenet_id = bn.berufenet_id,
                    berufenet_name = bn.name,
                    berufenet_kldb = bn.kldb,
                    berufenet_verified = 'auto_embed'
                FROM berufenet_synonyms s
                JOIN berufenet bn ON s.berufenet_id = bn.berufenet_id
                WHERE p.beruf = s.aa_beruf
                  AND p.beruf IS NOT NULL
                  AND p.berufenet_id IS NULL
            ''')
            classified = cur.rowcount
            conn.commit()
            
            print(f"\n  Added {len(auto_matches)} synonyms, classified {classified} postings")
            
            # Save review queue to file for manual review
            if review_queue:
                review_file = f'/home/xai/Documents/ty_learn/output/berufenet_review_queue_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(review_file, 'w') as f:
                    json.dump(review_queue, f, indent=2, ensure_ascii=False)
                print(f"  Review queue saved to: {review_file}")
    
    return stats


# =============================================================================
# TIER 3: LLM Suggestion
# =============================================================================

def tier3_llm_suggest(limit: int = 20, dry_run: bool = False) -> Dict[str, int]:
    """
    Tier 3: LLM-based suggestion for manual review.
    
    For remaining unmatched berufe:
    1. Ask LLM to suggest best berufenet match
    2. Output suggestions for human approval
    
    Returns dict with suggestion counts.
    """
    import requests
    
    stats = {'suggestions': 0, 'no_match': 0}
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Load berufenet names for context
        cur.execute('SELECT berufenet_id, name, kldb FROM berufenet ORDER BY name')
        berufenet_all = cur.fetchall()
        
        # Create a compact list for LLM context
        berufenet_names = [f"{r['berufenet_id']}: {r['name']}" for r in berufenet_all]
        
        # Get top unmatched berufe
        cur.execute('''
            SELECT beruf, COUNT(*) as cnt
            FROM postings 
            WHERE beruf IS NOT NULL 
              AND berufenet_id IS NULL
              AND source = 'arbeitsagentur'
            GROUP BY beruf
            ORDER BY cnt DESC
            LIMIT %s
        ''', (limit,))
        unmatched = cur.fetchall()
        
        if not unmatched:
            print("  No unmatched professions!")
            return stats
        
        print(f"  Asking LLM to suggest matches for {len(unmatched)} professions...")
        
        suggestions = []
        
        # Process in batches of 5 for efficiency
        for i in range(0, len(unmatched), 5):
            batch = unmatched[i:i+5]
            batch_berufe = [r['beruf'] for r in batch]
            batch_counts = {r['beruf']: r['cnt'] for r in batch}
            
            prompt = f"""Du bist ein Experte für deutsche Berufsklassifikation.

Hier ist eine Liste von Berufsbezeichnungen aus Stellenanzeigen, die keinem Berufenet-Eintrag zugeordnet werden konnten:

{chr(10).join(f'- {b}' for b in batch_berufe)}

Hier ist ein Auszug der verfügbaren Berufenet-Einträge (Format: "ID: Name"):

{chr(10).join(berufenet_names[:500])}

[... {len(berufenet_names) - 500} weitere Einträge ...]

Für jede unzugeordnete Berufsbezeichnung:
1. Finde den BESTEN passenden Berufenet-Eintrag (oder "NONE" wenn kein guter Match)
2. Gib die Übereinstimmung auf einer Skala von 1-10 an

Antworte NUR im folgenden JSON-Format:
[
  {{"beruf": "...", "berufenet_id": "...", "berufenet_name": "...", "confidence": 8, "reason": "..."}},
  ...
]"""

            try:
                resp = requests.post(
                    os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate',
                    json={
                        'model': 'qwen2.5:7b',
                        'prompt': prompt,
                        'stream': False,
                        'options': {'temperature': 0.1}
                    },
                    timeout=120
                )
                resp.raise_for_status()
                response_text = resp.json()['response']
                
                # Parse JSON from response
                # Find JSON array in response
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    llm_suggestions = json.loads(json_match.group())
                    
                    for s in llm_suggestions:
                        if s.get('berufenet_id') and s['berufenet_id'] != 'NONE':
                            s['posting_count'] = batch_counts.get(s['beruf'], 0)
                            suggestions.append(s)
                            stats['suggestions'] += s['posting_count']
                        else:
                            stats['no_match'] += batch_counts.get(s.get('beruf', ''), 0)
                
            except Exception as e:
                print(f"    Warning: LLM request failed: {e}")
            
            print(f"    {min(i+5, len(unmatched))}/{len(unmatched)} processed...")
        
        # Output suggestions
        print(f"\n  LLM Suggestions ({len(suggestions)} matches):")
        for s in suggestions:
            conf = s.get('confidence', '?')
            print(f"    [{conf}/10] {s['beruf'][:40]:40s} → {s.get('berufenet_name', '?')[:35]} ({s.get('posting_count', 0)} posts)")
            if s.get('reason'):
                print(f"           Reason: {s['reason'][:60]}")
        
        # Save suggestions for review
        if suggestions:
            review_file = f'/home/xai/Documents/ty_learn/output/berufenet_llm_suggestions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(review_file, 'w') as f:
                json.dump(suggestions, f, indent=2, ensure_ascii=False)
            print(f"\n  Suggestions saved to: {review_file}")
            print("  Review and run: python3 tools/berufenet_auto_matcher.py --apply <file>")
    
    return stats


def apply_suggestions(filepath: str) -> int:
    """Apply LLM suggestions from a review file."""
    with open(filepath) as f:
        suggestions = json.load(f)
    
    applied = 0
    with get_connection() as conn:
        cur = conn.cursor()
        
        for s in suggestions:
            if s.get('berufenet_id') and s.get('beruf'):
                try:
                    cur.execute('''
                        INSERT INTO berufenet_synonyms (aa_beruf, berufenet_id, source, created_at)
                        VALUES (%s, %s, 'llm_reviewed', NOW())
                        ON CONFLICT (aa_beruf) DO NOTHING
                    ''', (s['beruf'], s['berufenet_id']))
                    if cur.rowcount > 0:
                        applied += 1
                except Exception as e:
                    print(f"  Warning: {e}")
        
        conn.commit()
        
        # Apply to postings
        cur.execute('''
            UPDATE postings p
            SET 
                berufenet_id = bn.berufenet_id,
                berufenet_name = bn.name,
                berufenet_kldb = bn.kldb,
                berufenet_verified = 'llm_reviewed'
            FROM berufenet_synonyms s
            JOIN berufenet bn ON s.berufenet_id = bn.berufenet_id
            WHERE p.beruf = s.aa_beruf
              AND p.beruf IS NOT NULL
              AND p.berufenet_id IS NULL
        ''')
        classified = cur.rowcount
        conn.commit()
    
    print(f"Applied {applied} synonyms, classified {classified} postings")
    return applied


# =============================================================================
# Reporting
# =============================================================================

def report_unmatched():
    """Show statistics on unmatched professions."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Overall stats
        cur.execute('SELECT COUNT(*) as cnt FROM postings WHERE source = %s', ('arbeitsagentur',))
        total_aa = cur.fetchone()['cnt']
        
        cur.execute('''
            SELECT COUNT(*) as cnt FROM postings 
            WHERE source = 'arbeitsagentur' AND berufenet_id IS NOT NULL
        ''')
        matched = cur.fetchone()['cnt']
        
        cur.execute('''
            SELECT COUNT(DISTINCT beruf) as cnt FROM postings 
            WHERE source = 'arbeitsagentur' AND beruf IS NOT NULL AND berufenet_id IS NULL
        ''')
        unique_unmatched = cur.fetchone()['cnt']
        
        pct = 100 * matched / total_aa if total_aa > 0 else 0
        
        print(f"\n📊 BERUFENET MATCHING STATUS")
        print(f"{'='*50}")
        print(f"  Total AA postings:     {total_aa:,}")
        print(f"  Matched:               {matched:,} ({pct:.1f}%)")
        print(f"  Unmatched:             {total_aa - matched:,} ({100-pct:.1f}%)")
        print(f"  Unique unmatched:      {unique_unmatched:,} profession names")
        
        # Top unmatched
        cur.execute('''
            SELECT beruf, COUNT(*) as cnt
            FROM postings 
            WHERE beruf IS NOT NULL 
              AND berufenet_id IS NULL
              AND source = 'arbeitsagentur'
            GROUP BY beruf
            ORDER BY cnt DESC
            LIMIT 20
        ''')
        top_unmatched = cur.fetchall()
        
        print(f"\n  Top 20 Unmatched Professions:")
        print(f"  {'-'*46}")
        for r in top_unmatched:
            print(f"  {r['cnt']:5d}  {r['beruf'][:50]}")
        
        # Synonym sources
        cur.execute('''
            SELECT source, COUNT(*) as cnt
            FROM berufenet_synonyms
            GROUP BY source
            ORDER BY cnt DESC
        ''')
        sources = cur.fetchall()
        
        print(f"\n  Synonym Sources:")
        print(f"  {'-'*30}")
        for r in sources:
            print(f"  {r['cnt']:5d}  {r['source']}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Berufenet Auto-Matcher')
    parser.add_argument('--tier', type=int, choices=[1, 2, 3], help='Run specific tier only')
    parser.add_argument('--dry-run', action='store_true', help='Preview matches without applying')
    parser.add_argument('--report', action='store_true', help='Show unmatched statistics')
    parser.add_argument('--limit', type=int, default=100, help='Max professions to process')
    parser.add_argument('--apply', type=str, help='Apply suggestions from JSON file')
    parser.add_argument('--embed-threshold', type=float, default=0.88, help='Auto-match threshold for embeddings')
    args = parser.parse_args()
    
    if args.apply:
        apply_suggestions(args.apply)
        return
    
    if args.report:
        report_unmatched()
        return
    
    tlog("🎯 BERUFENET AUTO-MATCHER")
    print("="*50)
    
    total_stats = {}
    
    # Tier 1: Pattern matching
    if args.tier is None or args.tier == 1:
        tlog("📐 TIER 1: Pattern Matching")
        print("-"*50)
        stats = tier1_pattern_match(dry_run=args.dry_run)
        total_stats['tier1'] = stats
        print(f"  Strip suffix: {stats['strip_suffix']}, Strip parens: {stats['strip_parens']}, Base form: {stats['base_form']}")
    
    # Tier 2: Embedding search
    if args.tier is None or args.tier == 2:
        tlog("🧮 TIER 2: Embedding Search")
        print("-"*50)
        stats = tier2_embedding_match(
            threshold_auto=args.embed_threshold,
            limit=args.limit,
            dry_run=args.dry_run
        )
        total_stats['tier2'] = stats
    
    # Tier 3: LLM suggestions
    if args.tier == 3:
        tlog("🤖 TIER 3: LLM Suggestions")
        print("-"*50)
        stats = tier3_llm_suggest(limit=args.limit, dry_run=args.dry_run)
        total_stats['tier3'] = stats
    
    # Final report
    if not args.dry_run:
        report_unmatched()


if __name__ == '__main__':
    main()
