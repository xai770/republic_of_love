#!/usr/bin/env python3
"""
Actor: postings__berufenet_U
Updates postings with Berufenet classification (profession ID, KLDB code, qualification level)

Pipeline:
1. Clean job title (strip noise)
2. Apply OWL synonyms (colloquial → formal)
3. Embed with BGE-M3
4. Match to Berufenet (3,562 professions)
5. Route by score:
   - ≥0.85 → Accept (berufenet_verified = 'auto')
   - 0.70-0.85 → LLM verify → YES/NO/UNCERTAIN
   - <0.70 → NULL (don't guess)

Usage:
    python actors/postings__berufenet_U.py --batch 1000
    python actors/postings__berufenet_U.py --batch 100 --with-llm  # Enable LLM verification
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection_raw
from lib.berufenet_matching import (
    clean_job_title,
    apply_owl_synonyms,
    llm_verify_match,
    THRESHOLD_AUTO_ACCEPT,
    THRESHOLD_LLM_VERIFY,
)

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "bge-m3:567m"


def get_embedding(text: str) -> np.ndarray | None:
    """Get embedding from Ollama."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            return np.array(resp.json()['embedding'])
    except Exception as e:
        print(f"  ⚠️ Embedding error: {e}")
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity."""
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def load_berufenet():
    """Load Berufenet data and embeddings."""
    data_dir = Path(__file__).parent.parent / 'data'
    
    df = pd.read_parquet(data_dir / 'berufenet_full.parquet')
    embeddings = np.load(data_dir / 'berufenet_full_embeddings.npy')
    
    return df, embeddings


def match_to_berufenet(
    normalized_title: str,
    beruf_df: pd.DataFrame,
    beruf_embeddings: np.ndarray
) -> dict | None:
    """Match a normalized title to Berufenet."""
    emb = get_embedding(normalized_title)
    if emb is None:
        return None
    
    # Compute similarities
    similarities = [cosine_similarity(emb, be) for be in beruf_embeddings]
    best_idx = np.argmax(similarities)
    score = similarities[best_idx]
    
    row = beruf_df.iloc[best_idx]
    return {
        'berufenet_id': int(row['berufenet_id']),
        'berufenet_name': row['name'],
        'berufenet_kldb': row['kldb'],
        'qualification_level': int(row['qualification_level']) if pd.notna(row['qualification_level']) else None,
        'score': score,
    }


def process_batch(batch_size: int, with_llm: bool = False, pending_only: bool = False):
    """Process a batch of postings."""
    print(f"\n{'='*60}")
    print(f"Berufenet Classification Actor")
    print(f"{'='*60}")
    print(f"Batch size: {batch_size}")
    print(f"Mode: {'PENDING LLM ONLY' if pending_only else 'Full processing'}")
    print(f"LLM verification: {'enabled' if with_llm else 'disabled'}")
    print(f"Thresholds: auto-accept ≥{THRESHOLD_AUTO_ACCEPT}, LLM {THRESHOLD_LLM_VERIFY}-{THRESHOLD_AUTO_ACCEPT}, NULL <{THRESHOLD_LLM_VERIFY}")
    
    # Load Berufenet
    print("\nLoading Berufenet data...")
    beruf_df, beruf_embeddings = load_berufenet()
    print(f"  Loaded {len(beruf_df)} professions")
    
    conn = get_connection_raw()
    cur = conn.cursor()
    
    if pending_only:
        # Phase 2: Only get pending_llm titles that need LLM verification
        cur.execute("""
            SELECT job_title, COUNT(*) as cnt
            FROM postings 
            WHERE berufenet_verified = 'pending_llm'
            GROUP BY job_title
            ORDER BY cnt DESC
            LIMIT %s
        """, (batch_size,))
    else:
        # Phase 1: Get distinct titles that haven't been processed
        cur.execute("""
            SELECT job_title, COUNT(*) as cnt
            FROM postings 
            WHERE job_title IS NOT NULL 
              AND berufenet_id IS NULL
              AND berufenet_verified IS NULL
            GROUP BY job_title
            ORDER BY cnt DESC
            LIMIT %s
        """, (batch_size,))
    
    titles = cur.fetchall()
    if not titles:
        if pending_only:
            print("\n✅ No pending LLM titles remaining!")
        else:
            print("\n✅ No unprocessed titles remaining!")
        return
    
    print(f"\nProcessing {len(titles)} unique titles...")
    
    stats = {'auto': 0, 'llm_yes': 0, 'llm_no': 0, 'llm_uncertain': 0, 'null': 0, 'error': 0}
    start_time = time.time()
    
    for i, row in enumerate(titles):
        title = row['job_title']
        posting_count = row['cnt']
        
        # Pipeline: clean → OWL → match
        cleaned = clean_job_title(title)
        normalized = apply_owl_synonyms(cleaned)
        
        match = match_to_berufenet(normalized, beruf_df, beruf_embeddings)
        
        if match is None:
            stats['error'] += 1
            # Mark as processed but failed
            cur.execute("""
                UPDATE postings 
                SET berufenet_verified = 'error'
                WHERE job_title = %s AND berufenet_id IS NULL
            """, (title,))
            continue
        
        score = match['score']
        
        # Route by confidence
        if score >= THRESHOLD_AUTO_ACCEPT:
            # Auto-accept
            verified = 'auto'
            stats['auto'] += 1
            accept = True
        elif score >= THRESHOLD_LLM_VERIFY:
            if with_llm:
                # LLM verification
                llm_result = llm_verify_match(normalized, match['berufenet_name'])
                if llm_result == 'YES':
                    verified = 'llm_yes'
                    stats['llm_yes'] += 1
                    accept = True
                elif llm_result == 'NO':
                    verified = 'llm_no'
                    stats['llm_no'] += 1
                    accept = False
                else:
                    verified = 'llm_uncertain'
                    stats['llm_uncertain'] += 1
                    accept = False
            else:
                # Skip LLM, mark as pending
                verified = 'pending_llm'
                stats['llm_uncertain'] += 1
                accept = False
        else:
            # Below threshold - NULL
            verified = 'null'
            stats['null'] += 1
            accept = False
        
        # Update database
        if accept:
            if pending_only:
                # Phase 2: Update pending_llm titles
                cur.execute("""
                    UPDATE postings 
                    SET berufenet_id = %s,
                        berufenet_name = %s,
                        berufenet_kldb = %s,
                        qualification_level = %s,
                        berufenet_score = %s,
                        berufenet_verified = %s
                    WHERE job_title = %s AND berufenet_verified = 'pending_llm'
                """, (
                    match['berufenet_id'],
                    match['berufenet_name'],
                    match['berufenet_kldb'],
                    match['qualification_level'],
                    score,
                    verified,
                    title,
                ))
            else:
                cur.execute("""
                    UPDATE postings 
                    SET berufenet_id = %s,
                        berufenet_name = %s,
                        berufenet_kldb = %s,
                        qualification_level = %s,
                        berufenet_score = %s,
                        berufenet_verified = %s
                    WHERE job_title = %s AND berufenet_id IS NULL
                """, (
                    match['berufenet_id'],
                    match['berufenet_name'],
                    match['berufenet_kldb'],
                    match['qualification_level'],
                    score,
                    verified,
                    title,
                ))
        else:
            if pending_only:
                # Phase 2: Update rejected/uncertain pending_llm titles
                cur.execute("""
                    UPDATE postings 
                    SET berufenet_score = %s,
                        berufenet_verified = %s
                    WHERE job_title = %s AND berufenet_verified = 'pending_llm'
                """, (score, verified, title))
            else:
                cur.execute("""
                    UPDATE postings 
                    SET berufenet_score = %s,
                        berufenet_verified = %s
                    WHERE job_title = %s AND berufenet_id IS NULL
                """, (score, verified, title))
        
        # Progress
        if (i + 1) % 50 == 0:
            conn.commit()
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{len(titles)} ({rate:.1f}/s) - auto:{stats['auto']} llm_yes:{stats['llm_yes']} null:{stats['null']}")
    
    conn.commit()
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"COMPLETED in {elapsed:.1f}s ({len(titles)/elapsed:.1f} titles/s)")
    print(f"{'='*60}")
    print(f"  ✅ Auto-accept:    {stats['auto']}")
    print(f"  🤖 LLM YES:        {stats['llm_yes']}")
    print(f"  🤖 LLM NO:         {stats['llm_no']}")
    print(f"  🤷 LLM Uncertain:  {stats['llm_uncertain']}")
    print(f"  ❌ NULL:           {stats['null']}")
    print(f"  ⚠️  Errors:        {stats['error']}")
    
    # Show remaining
    cur.execute("""
        SELECT COUNT(DISTINCT job_title) 
        FROM postings 
        WHERE job_title IS NOT NULL AND berufenet_verified IS NULL
    """)
    remaining = cur.fetchone()['count']
    print(f"\n📊 Remaining unprocessed titles: {remaining:,}")


def show_stats():
    """Show current classification statistics."""
    conn = get_connection_raw()
    cur = conn.cursor()
    
    print("\n📊 BERUFENET CLASSIFICATION STATUS\n")
    
    cur.execute("""
        SELECT 
            berufenet_verified,
            COUNT(DISTINCT job_title) as titles,
            COUNT(*) as postings
        FROM postings
        WHERE job_title IS NOT NULL
        GROUP BY berufenet_verified
        ORDER BY postings DESC
    """)
    
    for row in cur:
        status = row['berufenet_verified'] or 'unprocessed'
        print(f"  {status:15} : {row['titles']:6,} titles, {row['postings']:6,} postings")
    
    # Qualification level distribution
    cur.execute("""
        SELECT 
            qualification_level,
            COUNT(*) as cnt
        FROM postings
        WHERE qualification_level IS NOT NULL
        GROUP BY qualification_level
        ORDER BY qualification_level
    """)
    
    print("\n📈 QUALIFICATION LEVEL DISTRIBUTION:")
    level_names = {1: 'Helfer', 2: 'Fachkraft', 3: 'Spezialist', 4: 'Experte'}
    for row in cur:
        level = row['qualification_level']
        name = level_names.get(level, '?')
        print(f"  Level {level} ({name:10}): {row['cnt']:,} postings")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Classify postings with Berufenet')
    parser.add_argument('--batch', type=int, default=100, help='Batch size (unique titles)')
    parser.add_argument('--with-llm', action='store_true', help='Enable LLM verification for medium confidence')
    parser.add_argument('--pending-only', action='store_true', help='Only process pending_llm titles (for Phase 2)')
    parser.add_argument('--stats', action='store_true', help='Show classification statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    else:
        process_batch(args.batch, args.with_llm, args.pending_only)
