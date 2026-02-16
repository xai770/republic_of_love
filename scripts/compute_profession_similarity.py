#!/usr/bin/env python3
"""
Compute profession similarity — hybrid KLDB structure + embedding cosine similarity.

Populates `profession_similarity` with top-N related professions per Berufenet profession.

KLDB scoring:
  - Same 5-digit group (e.g., 11102): kldb_score = 1.0
  - Same 3-digit group (e.g., 111):   kldb_score = 0.7
  - Same 2-digit domain (e.g., 11):   kldb_score = 0.3
  - Different domain:                 kldb_score = 0.0

Embedding scoring:
  - Cosine similarity between Berufenet profession name embeddings.
  - Only computed for professions that have pre-existing embeddings.

Combined score:
  - combined = 0.4 * kldb_score + 0.6 * embedding_score (when both available)
  - combined = kldb_score (when no embedding available)
  - Minimum threshold: combined >= 0.15 to keep

Usage:
    python3 scripts/compute_profession_similarity.py [--top-n 10]

Idempotent — full refresh each run. Typical runtime: 30-60s.
"""
import sys
import os
import time
import json
import argparse
import logging
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("profession_similarity")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def compute_kldb_score(kldb_a: str, kldb_b: str) -> float:
    """
    KLDB structural similarity: compare codes like 'B 11102'.
    Extract the 5-digit numeric part after 'B '.
    """
    # Extract numeric part: "B 11102" → "11102"
    num_a = kldb_a.replace("B ", "").replace(" ", "")
    num_b = kldb_b.replace("B ", "").replace(" ", "")

    if len(num_a) < 5 or len(num_b) < 5:
        return 0.0

    # Same 5-digit group
    if num_a == num_b:
        return 1.0
    # Same 3-digit group (first 3 digits)
    if num_a[:3] == num_b[:3]:
        return 0.7
    # Same 2-digit domain
    if num_a[:2] == num_b[:2]:
        return 0.3
    return 0.0


def compute_similarity(top_n: int = 10):
    """
    Full computation of profession similarity.

    Strategy: For each profession with >= 20 postings, find top-N similar
    professions using KLDB structure + embedding cosine similarity.
    """
    t0 = time.time()

    with get_connection() as conn:
        cur = conn.cursor()

        # ── Load professions with >= 20 postings ────────────────────────
        cur.execute("""
            SELECT b.berufenet_id, b.name, b.kldb
            FROM berufenet b
            JOIN (
                SELECT berufenet_id, COUNT(*) AS cnt
                FROM postings
                WHERE enabled = true AND invalidated = false AND berufenet_id IS NOT NULL
                GROUP BY berufenet_id
                HAVING COUNT(*) >= 20
            ) pc ON pc.berufenet_id = b.berufenet_id
            WHERE b.kldb IS NOT NULL
            ORDER BY b.berufenet_id
        """)
        professions = cur.fetchall()
        prof_by_id = {p['berufenet_id']: p for p in professions}
        log.info(f"Loaded {len(professions)} professions with >= 20 postings")

        # ── Load embeddings for these professions ────────────────────────
        # Join on LOWER(text) = LOWER(name)
        berufenet_ids = [p['berufenet_id'] for p in professions]
        cur.execute("""
            SELECT b.berufenet_id, e.embedding
            FROM berufenet b
            JOIN embeddings e ON LOWER(e.text) = LOWER(b.name)
            WHERE b.berufenet_id = ANY(%s)
        """, [berufenet_ids])

        embeddings = {}
        for row in cur.fetchall():
            vec = row['embedding']
            if isinstance(vec, str):
                vec = json.loads(vec)
            if isinstance(vec, list):
                embeddings[row['berufenet_id']] = np.array(vec, dtype=np.float32)
        log.info(f"Loaded embeddings for {len(embeddings)}/{len(professions)} professions")

        # ── Group by 2-digit domain for KLDB comparison ──────────────────
        # Only compare within same domain + adjacent domains to limit compute
        domain_groups = defaultdict(list)
        for p in professions:
            num = p['kldb'].replace("B ", "").replace(" ", "")
            if len(num) >= 2:
                domain_groups[num[:2]].append(p['berufenet_id'])

        # ── Compute pairwise similarities ────────────────────────────────
        log.info("Computing pairwise similarities...")
        # For each profession, collect (other_id, kldb_score, embedding_score, combined)
        results = []
        computed = 0

        for prof in professions:
            pid = prof['berufenet_id']
            kldb_a = prof['kldb']
            num_a = kldb_a.replace("B ", "").replace(" ", "")
            domain_a = num_a[:2] if len(num_a) >= 2 else ""

            # Candidates: same domain + adjacent domains
            candidate_ids = set()
            for d_code, members in domain_groups.items():
                kldb_test = compute_kldb_score(
                    f"B {domain_a}000",
                    f"B {d_code}000"
                )
                if kldb_test > 0 or d_code == domain_a:
                    candidate_ids.update(members)

            # Also include embedding neighbors from other domains if we have vectors
            emb_a = embeddings.get(pid)

            scored = []
            for cid in candidate_ids:
                if cid == pid:
                    continue
                other = prof_by_id.get(cid)
                if not other:
                    continue

                ks = compute_kldb_score(kldb_a, other['kldb'])
                es = None
                if emb_a is not None and cid in embeddings:
                    es = cosine_similarity(emb_a, embeddings[cid])

                if es is not None:
                    combined = 0.4 * ks + 0.6 * es
                else:
                    combined = ks

                if combined >= 0.15:
                    scored.append((cid, ks, es, combined))

            # If we have embeddings, also check top embedding matches globally
            # (cross-domain discoveries)
            if emb_a is not None:
                for other_id, emb_b in embeddings.items():
                    if other_id == pid or other_id in candidate_ids:
                        continue
                    es = cosine_similarity(emb_a, emb_b)
                    if es >= 0.5:  # Only high-confidence cross-domain
                        ks = 0.0
                        if other_id in prof_by_id:
                            ks = compute_kldb_score(kldb_a, prof_by_id[other_id]['kldb'])
                        combined = 0.4 * ks + 0.6 * es
                        if combined >= 0.15:
                            scored.append((other_id, ks, es, combined))

            # Take top-N
            scored.sort(key=lambda x: -x[3])
            for rank, (cid, ks, es, combined) in enumerate(scored[:top_n], 1):
                results.append((pid, cid, ks, es, combined, rank))

            computed += 1
            if computed % 100 == 0:
                log.info(f"  Processed {computed}/{len(professions)} professions...")

        log.info(f"Computed {len(results)} similarity pairs")

        # ── Write results ────────────────────────────────────────────────
        cur.execute("DELETE FROM profession_similarity")

        if results:
            from psycopg2.extras import execute_batch
            execute_batch(
                cur,
                """
                INSERT INTO profession_similarity
                    (berufenet_id_a, berufenet_id_b, kldb_score, embedding_score,
                     combined_score, rank_for_a, computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                [(r[0], r[1], float(r[2]), float(r[3]) if r[3] is not None else None,
                  float(r[4]), r[5]) for r in results],
                page_size=500
            )

        conn.commit()

        elapsed = time.time() - t0
        log.info(
            f"Done in {elapsed:.1f}s — {len(results)} pairs for {len(professions)} professions"
        )

        return {
            "professions": len(professions),
            "pairs": len(results),
            "with_embeddings": len(embeddings),
            "elapsed_seconds": round(elapsed, 1),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute profession similarity")
    parser.add_argument("--top-n", type=int, default=10, help="Top-N similar professions per profession")
    args = parser.parse_args()

    result = compute_similarity(top_n=args.top_n)
    print(f"\n✅ Profession similarity: {result['pairs']} pairs for {result['professions']} professions in {result['elapsed_seconds']}s")
    print(f"   Embeddings used: {result['with_embeddings']}/{result['professions']}")
