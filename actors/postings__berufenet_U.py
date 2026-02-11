#!/usr/bin/env python3
"""
Actor: postings__berufenet_U
Updates postings with Berufenet classification (profession ID, KLDB code, qualification level)

Architecture (2026-02-11 OWL integration):

  Phase 1: OWL lookup — instant, database-only
    job_title → clean() → lookup in owl_names WHERE owl_type='berufenet'
    → HIT: done. berufenet_verified = 'owl'

  Phase 2: Embedding discovery — GPU, ~14/sec
    cleaned title → embed → top-5 berufenet candidates → LLM picks best
    → Confident: accept + ADD AS OWL SYNONYM (system learns!)
    → Uncertain: → owl_pending (human review)

  Phase 3: Human resolves owl_pending via /admin/owl-triage
    → Creates owl_names entry → Phase 1 catches it next time

Key insight: Embeddings are the DISCOVERY mechanism for new synonyms,
not the production classifier. OWL handles the steady state.

Usage:
    python actors/postings__berufenet_U.py --batch 1000
    python actors/postings__berufenet_U.py --batch 1000 --phase2    # Enable embedding+LLM
    python actors/postings__berufenet_U.py --stats                  # Show status
"""

import argparse
import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

import os

from core.database import get_connection_raw
from lib.berufenet_matching import clean_job_title, llm_verify_match

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings'
EMBED_MODEL = "bge-m3:567m"

THRESHOLD_AUTO_ACCEPT = 0.85
THRESHOLD_LLM_VERIFY = 0.70


# =============================================================================
# Phase 1: OWL Lookup (instant, no GPU)
# =============================================================================

def owl_lookup(cleaned_title: str, cur) -> Optional[dict]:
    """
    Look up a cleaned job title in OWL berufenet names.

    Only trusts entries with confidence_source IN ('human', 'import', 'llm_confirmed').
    REJECTS ambiguous names that map to multiple different owl entities
    (e.g. "Helfer" → 48 different specializations = ambiguous).
    Returns dict with berufenet metadata if found unambiguously, None otherwise.
    """
    cur.execute("""
        SELECT
            o.owl_id,
            o.canonical_name,
            o.metadata->>'berufenet_id' AS berufenet_id,
            o.metadata->>'kldb' AS kldb,
            (o.metadata->>'qualification_level')::int AS qualification_level
        FROM owl_names n
        JOIN owl o ON n.owl_id = o.owl_id
        WHERE o.owl_type = 'berufenet'
          AND n.language = 'de'
          AND lower(n.display_name) = lower(%s)
          AND n.confidence_source IN ('human', 'import', 'llm_confirmed')
    """, (cleaned_title,))
    rows = cur.fetchall()

    if not rows:
        return None

    # Check for ambiguity: do all rows point to the same owl entity?
    unique_owl_ids = set(r['owl_id'] for r in rows)
    if len(unique_owl_ids) > 1:
        # Ambiguous — "Helfer" maps to 48 specializations, refuse to guess
        return None

    row = rows[0]
    return {
        'owl_id': row['owl_id'],
        'berufenet_id': int(row['berufenet_id']) if row['berufenet_id'] else None,
        'berufenet_name': row['canonical_name'],
        'berufenet_kldb': row['kldb'],
        'qualification_level': row['qualification_level'],
    }


# =============================================================================
# Phase 2: Embedding Discovery (GPU required)
# =============================================================================

def get_embedding(text: str) -> Optional[np.ndarray]:
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
        print(f"  ⚠️ Embedding error: {e}")
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity."""
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def load_berufenet():
    """Load Berufenet data and pre-computed embeddings."""
    data_dir = Path(__file__).parent.parent / 'data'
    df = pd.read_parquet(data_dir / 'berufenet_full.parquet')
    embeddings = np.load(data_dir / 'berufenet_full_embeddings.npy')
    return df, embeddings


def embedding_top5(cleaned_title: str, beruf_df: pd.DataFrame, beruf_embeddings: np.ndarray) -> list[dict]:
    """Get top 5 berufenet matches by embedding similarity."""
    emb = get_embedding(cleaned_title)
    if emb is None:
        return []

    similarities = np.array([cosine_similarity(emb, be) for be in beruf_embeddings])
    top_indices = np.argsort(similarities)[-5:][::-1]

    candidates = []
    for idx in top_indices:
        row = beruf_df.iloc[idx]
        candidates.append({
            'berufenet_id': int(row['berufenet_id']),
            'berufenet_name': row['name'],
            'berufenet_kldb': row['kldb'],
            'qualification_level': int(row['qualification_level']) if pd.notna(row['qualification_level']) else None,
            'score': float(similarities[idx]),
        })
    return candidates


def llm_pick_best(cleaned_title: str, candidates: list[dict]) -> dict:
    """
    Route top candidates through threshold + LLM verification.
    Returns dict with 'confident' bool and match details.
    """
    if not candidates:
        return {'confident': False, 'reason': 'no_candidates'}

    best = candidates[0]

    # High confidence — auto-accept
    if best['score'] >= THRESHOLD_AUTO_ACCEPT:
        return {'confident': True, 'match': best, 'method': 'embedding_high'}

    # Medium confidence — LLM verification
    if best['score'] >= THRESHOLD_LLM_VERIFY:
        llm_result = llm_verify_match(cleaned_title, best['berufenet_name'])
        if llm_result == 'YES':
            return {'confident': True, 'match': best, 'method': 'llm_yes'}
        elif llm_result == 'NO':
            # Try second candidate
            if len(candidates) > 1 and candidates[1]['score'] >= THRESHOLD_LLM_VERIFY:
                llm2 = llm_verify_match(cleaned_title, candidates[1]['berufenet_name'])
                if llm2 == 'YES':
                    return {'confident': True, 'match': candidates[1], 'method': 'llm_yes_2nd'}
            return {'confident': False, 'reason': 'llm_no', 'best': best}
        else:
            return {'confident': False, 'reason': 'llm_uncertain', 'best': best}

    # Below threshold
    return {'confident': False, 'reason': 'low_score', 'best': best}


def add_owl_synonym(owl_id: int, display_name: str, cur, conn):
    """Add a new synonym to OWL as llm_single (probationary).
    Second observation auto-promotes to llm_confirmed."""
    cur.execute("""
        INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type,
                               created_by, confidence, confidence_source, observation_count,
                               provenance)
        VALUES (%s, 'de', %s, false, 'alias', 'berufenet_actor', 0.8, 'llm_single', 1,
                '{"source": "phase2_embedding_llm"}'::jsonb)
        ON CONFLICT (owl_id, language, display_name) DO UPDATE
        SET observation_count = owl_names.observation_count + 1,
            confidence_source = CASE
                WHEN owl_names.observation_count + 1 >= 2 THEN 'llm_confirmed'
                ELSE owl_names.confidence_source
            END
    """, (owl_id, display_name))
    conn.commit()


def escalate_to_owl_pending(cleaned_title: str, candidates: list[dict], cur, conn):
    """Escalate an unresolvable title to owl_pending for human triage."""
    context = json.dumps({
        'candidates': [
            {'name': c['berufenet_name'], 'score': round(c['score'], 3), 'berufenet_id': c['berufenet_id']}
            for c in candidates[:3]
        ]
    })
    cur.execute("""
        INSERT INTO owl_pending (owl_type, raw_value, source_language, source_context, status)
        VALUES ('berufenet', %s, 'de', %s, 'pending')
        ON CONFLICT DO NOTHING
    """, (cleaned_title, context))
    conn.commit()


# =============================================================================
# Main Processing
# =============================================================================

def process_batch(batch_size: int, phase2: bool = False):
    """Process a batch of unclassified posting titles."""
    print(f"\n{'='*60}")
    print(f"Berufenet Classification Actor (OWL-first)")
    print(f"{'='*60}")
    print(f"Batch size: {batch_size}")
    print(f"Phase 2 (embedding+LLM): {'enabled' if phase2 else 'disabled — OWL only'}")

    conn = get_connection_raw()
    cur = conn.cursor()

    # Get distinct unclassified titles (most frequent first)
    # Includes: NULL/null (never processed), pending_llm (old actor scored 0.70-0.85 but never set berufenet_id),
    #           pending_owl (Phase 1 ran, no OWL match found — needs Phase 2 embedding+LLM)
    cur.execute("""
        SELECT job_title, COUNT(*) as cnt
        FROM postings
        WHERE job_title IS NOT NULL
          AND berufenet_id IS NULL
          AND (berufenet_verified IS NULL OR berufenet_verified IN ('null', 'pending_llm', 'pending_owl'))
        GROUP BY job_title
        ORDER BY cnt DESC
        LIMIT %s
    """, (batch_size,))

    titles = cur.fetchall()
    if not titles:
        print("\n✅ No unclassified titles remaining!")
        return

    print(f"Processing {len(titles)} unique titles...")

    # Load Phase 2 resources only if needed
    beruf_df, beruf_embeddings = None, None
    if phase2:
        print("Loading Berufenet embeddings for Phase 2...")
        beruf_df, beruf_embeddings = load_berufenet()
        print(f"  Loaded {len(beruf_df)} professions")

    stats = {'owl_hit': 0, 'embed_auto': 0, 'llm_yes': 0, 'escalated': 0, 'null': 0, 'error': 0}
    start_time = time.time()

    for i, row in enumerate(titles):
        title = row['job_title']

        # Clean the title
        cleaned = clean_job_title(title)

        # === Phase 1: OWL Lookup ===
        match = owl_lookup(cleaned, cur)

        if match:
            # Direct OWL hit — instant, reliable
            cur.execute("""
                UPDATE postings
                SET berufenet_id = %s,
                    berufenet_name = %s,
                    berufenet_kldb = %s,
                    qualification_level = %s,
                    berufenet_score = 1.0,
                    berufenet_verified = 'owl'
                WHERE job_title = %s
                  AND berufenet_id IS NULL
            """, (
                match['berufenet_id'],
                match['berufenet_name'],
                match['berufenet_kldb'],
                match['qualification_level'],
                title,
            ))
            stats['owl_hit'] += 1
            conn.commit()
            continue

        # === Phase 2: Embedding + LLM (optional) ===
        if phase2 and beruf_df is not None:
            candidates = embedding_top5(cleaned, beruf_df, beruf_embeddings)

            if not candidates:
                stats['error'] += 1
                cur.execute("""
                    UPDATE postings
                    SET berufenet_verified = 'error'
                    WHERE job_title = %s AND berufenet_id IS NULL
                """, (title,))
                conn.commit()
                continue

            result = llm_pick_best(cleaned, candidates)

            if result['confident']:
                m = result['match']

                # Find the OWL entity for this berufenet profession
                cur.execute("""
                    SELECT owl_id FROM owl
                    WHERE owl_type = 'berufenet'
                      AND metadata->>'berufenet_id' = %s
                """, (str(m['berufenet_id']),))
                owl_row = cur.fetchone()

                # Add as OWL synonym (probationary → confirmed after 2nd observation)
                if owl_row:
                    add_owl_synonym(owl_row['owl_id'], cleaned, cur, conn)

                # Update the posting
                verified = result['method']
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
                    m['berufenet_id'],
                    m['berufenet_name'],
                    m['berufenet_kldb'],
                    m['qualification_level'],
                    m['score'],
                    verified,
                    title,
                ))
                conn.commit()

                if 'llm' in verified:
                    stats['llm_yes'] += 1
                else:
                    stats['embed_auto'] += 1
            else:
                # Not confident — escalate to owl_pending
                escalate_to_owl_pending(cleaned, candidates, cur, conn)
                stats['escalated'] += 1

                cur.execute("""
                    UPDATE postings
                    SET berufenet_score = %s,
                        berufenet_verified = 'pending_owl'
                    WHERE job_title = %s AND berufenet_id IS NULL
                """, (candidates[0]['score'] if candidates else 0, title))
                conn.commit()
        else:
            # Phase 2 disabled — mark as unresolved for now
            stats['null'] += 1

        # Progress
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{len(titles)} ({rate:.1f}/s) — owl:{stats['owl_hit']} embed:{stats['embed_auto']} llm:{stats['llm_yes']} esc:{stats['escalated']} null:{stats['null']}")

    elapsed = time.time() - start_time

    total_classified = stats['owl_hit'] + stats['embed_auto'] + stats['llm_yes']
    print(f"\n{'='*60}")
    print(f"COMPLETED in {elapsed:.1f}s ({len(titles)/max(elapsed,0.1):.1f} titles/s)")
    print(f"{'='*60}")
    print(f"  🦉 OWL hit (Phase 1):   {stats['owl_hit']}")
    print(f"  📐 Embed auto (≥0.85):  {stats['embed_auto']}")
    print(f"  🤖 LLM confirmed:       {stats['llm_yes']}")
    print(f"  📋 Escalated to triage:  {stats['escalated']}")
    print(f"  ❌ NULL (Phase 2 off):   {stats['null']}")
    print(f"  ⚠️  Errors:              {stats['error']}")
    print(f"  ─────────────────────────")
    print(f"  ✅ Total classified:     {total_classified}")


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

    total_titles = 0
    total_postings = 0
    for row in cur:
        status = row['berufenet_verified'] or 'unprocessed'
        print(f"  {status:15} : {row['titles']:>6,} titles, {row['postings']:>7,} postings")
        total_titles += row['titles']
        total_postings += row['postings']

    print(f"  {'─'*50}")
    print(f"  {'TOTAL':15} : {total_titles:>6,} titles, {total_postings:>7,} postings")

    # OWL coverage
    cur.execute("""
        SELECT COUNT(DISTINCT n.display_name)
        FROM owl_names n
        JOIN owl o ON n.owl_id = o.owl_id
        WHERE o.owl_type = 'berufenet'
    """)
    owl_names_count = cur.fetchone()['count']
    print(f"\n  OWL berufenet names: {owl_names_count:,}")

    # Qualification level distribution
    cur.execute("""
        SELECT qualification_level, COUNT(*) as cnt
        FROM postings
        WHERE qualification_level IS NOT NULL
        GROUP BY qualification_level
        ORDER BY qualification_level
    """)

    level_names = {1: 'Helfer', 2: 'Fachkraft', 3: 'Spezialist', 4: 'Experte'}
    print("\n📈 QUALIFICATION LEVEL DISTRIBUTION:")
    for row in cur:
        level = row['qualification_level']
        name = level_names.get(level, '?')
        print(f"  Level {level} ({name:10}): {row['cnt']:>7,} postings")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Classify postings with Berufenet (OWL-first)')
    parser.add_argument('--batch', type=int, default=1000, help='Batch size (unique titles)')
    parser.add_argument('--phase2', action='store_true', help='Enable Phase 2: embedding + LLM for OWL misses')
    parser.add_argument('--stats', action='store_true', help='Show classification statistics')

    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        process_batch(args.batch, args.phase2)
