#!/usr/bin/env python3
"""
skill_embeddings.py - Semantic Skill Matching via Embeddings

PURPOSE:
Replace Alma's lexical word-overlap with true semantic similarity using
local embedding models (bge-m3). This enables matching like:
  - "procurement" ↔ "sourcing" ↔ "Einkauf" (German)
  - "Python programming" ↔ "software development"

While rejecting false positives like:
  - "staff management" ↔ "risk management" (lexical overlap but unrelated)

MODELS:
- bge-m3:567m (1.2GB) - Multilingual, good for EN/DE/FR
- nomic-embed-text (274MB) - English-focused, faster

USAGE:
    # Compute embeddings for all OWL skills (one-time)
    python3 tools/skill_embeddings.py build
    
    # Find matches for a skill
    python3 tools/skill_embeddings.py match "Python programming"
    
    # Batch match posting_facets skills
    python3 tools/skill_embeddings.py batch-match --limit 100

Author: Arden
Date: 2026-01-21
"""

import sys
import json
import time
import hashlib
import numpy as np
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os

from core.database import get_connection
import psycopg2.extras


# ============================================================================
# CONFIGURATION
# ============================================================================
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings'
DEFAULT_MODEL = "bge-m3:567m"
SIMILARITY_THRESHOLD_CONFIDENT = 0.70  # "Same concept"
SIMILARITY_THRESHOLD_RELATED = 0.60    # "Related concept"
BATCH_SIZE = 100


# ============================================================================
# EMBEDDING FUNCTIONS
# ============================================================================
# In-memory embedding cache (cleared per process)
_EMBEDDING_CACHE: Dict[str, np.ndarray] = {}
# Database cache loaded flag
_DB_CACHE_LOADED = False


def _compute_text_hash(text: str) -> str:
    """Compute text hash for embeddings table lookup."""
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:32]


def _load_db_cache():
    """Load all embeddings from database into memory cache."""
    global _DB_CACHE_LOADED
    if _DB_CACHE_LOADED:
        return
    
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT text, embedding, model FROM embeddings
                WHERE model = %s
            """, (DEFAULT_MODEL,))
            for row in cur.fetchall():
                cache_key = f"{row['model']}:{row['text'].lower().strip()}"
                emb_data = row['embedding']
                if isinstance(emb_data, list):
                    _EMBEDDING_CACHE[cache_key] = np.array(emb_data, dtype=np.float32)
                elif isinstance(emb_data, str):
                    _EMBEDDING_CACHE[cache_key] = np.array(json.loads(emb_data), dtype=np.float32)
            _DB_CACHE_LOADED = True
            if _EMBEDDING_CACHE:
                print(f"📦 Loaded {len(_EMBEDDING_CACHE)} cached embeddings from DB")
    except Exception as e:
        print(f"⚠️ Could not load embedding cache: {e}")


def _save_embedding_to_db(text: str, embedding: np.ndarray, model: str):
    """Persist a new embedding to the database."""
    try:
        text_hash = _compute_text_hash(text)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO embeddings (text_hash, text, embedding, model)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (text_hash) DO NOTHING
            """, (text_hash, text, json.dumps(embedding.tolist()), model))
            conn.commit()
    except Exception as e:
        # Non-fatal - embedding is still in memory cache
        pass


def get_embedding(text: str, model: str = DEFAULT_MODEL) -> Optional[np.ndarray]:
    """Get embedding vector. Checks memory cache, then DB, then Ollama."""
    # Load DB cache on first call
    _load_db_cache()
    
    cache_key = f"{model}:{text.lower().strip()}"
    
    # 1. Check memory cache
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]
    
    # 2. Compute via Ollama and persist
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={'model': model, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            emb = np.array(resp.json()['embedding'], dtype=np.float32)
            _EMBEDDING_CACHE[cache_key] = emb
            _save_embedding_to_db(text, emb, model)  # Persist for next time
            return emb
    except Exception as e:
        print(f"  ⚠️ Embedding error for '{text[:30]}...': {e}")
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def humanize(name: str) -> str:
    """Convert snake_case to Title Case for better embedding quality.
    
    Experiment showed 27.5% better separation between matches/non-matches
    when using humanized text vs raw snake_case.
    """
    return name.replace('_', ' ').title()


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    """Convert numpy array to bytes for database storage."""
    return embedding.tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    """Convert bytes back to numpy array."""
    return np.frombuffer(data, dtype=np.float32)


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================
def ensure_embedding_table(conn):
    """Create owl_embeddings table if not exists."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS owl_embeddings (
            owl_id INTEGER PRIMARY KEY REFERENCES owl(owl_id),
            model VARCHAR(50) NOT NULL,
            embedding BYTEA NOT NULL,
            dimension INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_owl_embeddings_model 
        ON owl_embeddings(model);
    """)
    conn.commit()
    print("✅ owl_embeddings table ready")


def get_owl_skills(conn) -> List[Dict]:
    """Get all OWL skill/competency nodes that need embeddings."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT owl_id, canonical_name
        FROM owl
        WHERE owl_type IN ('skill', 'competency')
          AND status = 'active'
        ORDER BY owl_id
    """)
    return [dict(row) for row in cur.fetchall()]


def get_existing_embeddings(conn, model: str) -> set:
    """Get owl_ids that already have embeddings for this model."""
    cur = conn.cursor()
    cur.execute("""
        SELECT owl_id FROM owl_embeddings WHERE model = %s
    """, (model,))
    return {row['owl_id'] for row in cur.fetchall()}


def save_embedding(conn, owl_id: int, model: str, embedding: np.ndarray):
    """Save embedding to database."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO owl_embeddings (owl_id, model, embedding, dimension)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (owl_id) DO UPDATE
        SET model = EXCLUDED.model,
            embedding = EXCLUDED.embedding,
            dimension = EXCLUDED.dimension,
            created_at = NOW()
    """, (owl_id, model, embedding_to_bytes(embedding), len(embedding)))
    conn.commit()


def load_all_embeddings(conn, model: str) -> Dict[int, np.ndarray]:
    """Load all embeddings for a model into memory."""
    cur = conn.cursor()
    cur.execute("""
        SELECT owl_id, embedding FROM owl_embeddings WHERE model = %s
    """, (model,))
    return {row['owl_id']: bytes_to_embedding(row['embedding']) for row in cur.fetchall()}


def get_owl_name(conn, owl_id: int) -> str:
    """Get canonical name for an owl_id."""
    cur = conn.cursor()
    cur.execute("SELECT canonical_name FROM owl WHERE owl_id = %s", (owl_id,))
    row = cur.fetchone()
    return row['canonical_name'] if row else f"owl_id={owl_id}"


# ============================================================================
# CORE MATCHING
# ============================================================================
def find_matches(
    text: str,
    embeddings: Dict[int, np.ndarray],
    model: str = DEFAULT_MODEL,
    top_k: int = 5
) -> List[Tuple[int, float]]:
    """
    Find top-K OWL skills most similar to input text.
    
    Returns: List of (owl_id, similarity_score) tuples, sorted by score desc.
    """
    query_embedding = get_embedding(text, model)
    if query_embedding is None:
        return []
    
    similarities = []
    for owl_id, emb in embeddings.items():
        sim = cosine_similarity(query_embedding, emb)
        similarities.append((owl_id, sim))
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


# ============================================================================
# BUILD EMBEDDINGS
# ============================================================================
def build_embeddings(model: str = DEFAULT_MODEL, force: bool = False):
    """Compute embeddings for all OWL skills."""
    print(f"🔨 Building embeddings with model: {model}")
    
    with get_connection() as conn:
        ensure_embedding_table(conn)
        
        skills = get_owl_skills(conn)
        print(f"   Found {len(skills)} OWL skills")
        
        if not force:
            existing = get_existing_embeddings(conn, model)
            skills = [s for s in skills if s['owl_id'] not in existing]
            print(f"   {len(skills)} need embeddings (others already computed)")
        
        if not skills:
            print("   ✅ All embeddings already computed!")
            return
        
        start = time.time()
        success = 0
        failed = 0
        
        for i, skill in enumerate(skills):
            owl_id = skill['owl_id']
            name = skill['canonical_name']
            display_name = humanize(name)  # "project_management" -> "Project Management"
            
            embedding = get_embedding(display_name, model)
            
            if embedding is not None:
                save_embedding(conn, owl_id, model, embedding)
                success += 1
            else:
                failed += 1
            
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                remaining = (len(skills) - i - 1) / rate
                print(f"   Progress: {i+1}/{len(skills)} ({rate:.1f}/sec, ~{remaining:.0f}s remaining)")
        
        elapsed = time.time() - start
        print(f"\n✅ Done! {success} embeddings computed in {elapsed:.1f}s")
        if failed:
            print(f"   ⚠️ {failed} failed")


# ============================================================================
# CLI COMMANDS
# ============================================================================
def cmd_build(args):
    """Build embeddings for all OWL skills."""
    model = args.model if hasattr(args, 'model') and args.model else DEFAULT_MODEL
    force = args.force if hasattr(args, 'force') else False
    build_embeddings(model, force)


def cmd_match(args):
    """Find matching OWL skills for input text."""
    text = args.text
    model = args.model if hasattr(args, 'model') and args.model else DEFAULT_MODEL
    top_k = args.top if hasattr(args, 'top') and args.top else 5
    
    print(f"🔍 Finding matches for: '{text}'")
    print(f"   Model: {model}")
    print()
    
    with get_connection() as conn:
        embeddings = load_all_embeddings(conn, model)
        
        if not embeddings:
            print("❌ No embeddings found! Run 'build' first.")
            return
        
        print(f"   Loaded {len(embeddings)} embeddings")
        
        matches = find_matches(text, embeddings, model, top_k)
        
        print(f"\nTop {len(matches)} matches:")
        print("="*60)
        for owl_id, score in matches:
            name = get_owl_name(conn, owl_id)
            indicator = "✓" if score >= SIMILARITY_THRESHOLD_CONFIDENT else \
                       "?" if score >= SIMILARITY_THRESHOLD_RELATED else "✗"
            print(f"  {indicator} {score:.3f}  {name} (owl_id={owl_id})")


def cmd_stats(args):
    """Show embedding statistics."""
    model = args.model if hasattr(args, 'model') and args.model else DEFAULT_MODEL
    
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Total OWL skills (same filter as build)
        cur.execute("""
            SELECT COUNT(*) as total FROM owl 
            WHERE owl_type IN ('skill', 'competency') AND status = 'active'
        """)
        total_skills = cur.fetchone()['total']
        
        # Embeddings by model
        cur.execute("""
            SELECT model, COUNT(*) as count, AVG(dimension) as avg_dim
            FROM owl_embeddings
            GROUP BY model
        """)
        models = cur.fetchall()
        
        print("📊 Embedding Statistics")
        print("="*60)
        print(f"Total OWL skills: {total_skills}")
        print()
        
        if models:
            print("Embeddings by model:")
            for m in models:
                coverage = (m['count'] / total_skills) * 100
                print(f"  {m['model']}: {m['count']} ({coverage:.1f}% coverage), dim={int(m['avg_dim'])}")
        else:
            print("No embeddings computed yet. Run 'build' first.")


def cmd_test(args):
    """Run semantic similarity tests."""
    model = args.model if hasattr(args, 'model') and args.model else DEFAULT_MODEL
    
    test_pairs = [
        # Should match (synonyms)
        ("procurement", "sourcing", True),
        ("procurement", "Einkauf", True),
        ("procurement", "purchasing", True),
        ("project management", "Projektmanagement", True),
        ("software engineer", "developer", True),
        ("data analysis", "data analytics", True),
        
        # Should NOT match
        ("procurement", "cooking", False),
        ("staff management", "risk management", False),
        ("Java", "coffee", False),
        ("Excel", "good performance", False),
        
        # Related but different
        ("frontend developer", "backend developer", None),  # Related
        ("SQL", "NoSQL", None),  # Related
        ("AWS", "Azure", None),  # Related
    ]
    
    print(f"🧪 Semantic Similarity Tests (model: {model})")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for s1, s2, expected in test_pairs:
        e1 = get_embedding(s1, model)
        e2 = get_embedding(s2, model)
        
        if e1 is None or e2 is None:
            print(f"⚠️ Could not embed: {s1} or {s2}")
            continue
        
        sim = cosine_similarity(e1, e2)
        
        if expected is True:
            # Should be high similarity
            ok = sim >= 0.65
            indicator = "✅" if ok else "❌"
            if ok:
                passed += 1
            else:
                failed += 1
        elif expected is False:
            # Should be low similarity
            ok = sim < 0.65
            indicator = "✅" if ok else "❌"
            if ok:
                passed += 1
            else:
                failed += 1
        else:
            # Just informational
            indicator = "ℹ️"
        
        print(f"{indicator} {s1:25} ↔ {s2:20} = {sim:.3f}")
    
    print()
    print(f"Results: {passed} passed, {failed} failed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Semantic skill matching via embeddings")
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL, help='Embedding model')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # build
    build_parser = subparsers.add_parser('build', help='Build embeddings for OWL skills')
    build_parser.add_argument('--force', '-f', action='store_true', help='Rebuild all')
    
    # match
    match_parser = subparsers.add_parser('match', help='Find matches for a skill')
    match_parser.add_argument('text', help='Skill text to match')
    match_parser.add_argument('--top', '-t', type=int, default=5, help='Top K results')
    
    # stats
    subparsers.add_parser('stats', help='Show embedding statistics')
    
    # test
    subparsers.add_parser('test', help='Run similarity tests')
    
    args = parser.parse_args()
    
    if args.command == 'build':
        cmd_build(args)
    elif args.command == 'match':
        cmd_match(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'test':
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
