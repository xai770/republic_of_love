#!/usr/bin/env python3
"""
Bulk auto-triage — run LLM on remaining owl_pending berufenet items.
Bypasses HTTP, hits DB directly. 2026-02-11.
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from lib.berufenet_matching import llm_triage_pick

DB_PARAMS = {
    'dbname': os.getenv('DB_NAME', 'turing'),
    'user': os.getenv('DB_USER', 'base_admin'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
}

BATCH_SIZE = 50

def run_batch(conn):
    """Process one batch of pending items. Returns (resolved, rejected, skipped)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT pending_id, raw_value, source_context
            FROM owl_pending
            WHERE owl_type = 'berufenet'
              AND status = 'pending'
              AND raw_value IS NOT NULL
              AND raw_value != ''
            ORDER BY created_at
            LIMIT %s
        """, (BATCH_SIZE,))
        items = cur.fetchall()

    if not items:
        return 0, 0, 0

    resolved = 0
    rejected = 0
    skipped = 0

    for item in items:
        candidates = []
        if item['source_context']:
            ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
            candidates = ctx.get('candidates', [])

        if not candidates:
            skipped += 1
            continue

        picked_indices = llm_triage_pick(item['raw_value'], candidates)

        try:
            if not picked_indices:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE postings
                        SET berufenet_verified = 'no_match'
                        WHERE berufenet_verified = 'pending_owl'
                          AND berufenet_id IS NULL
                          AND LOWER(job_title) = LOWER(%s)
                    """, (item['raw_value'],))
                    cur.execute("""
                        UPDATE owl_pending
                        SET status = 'rejected',
                            resolution_notes = 'LLM: no match',
                            processed_at = NOW(),
                            processed_by = 'llm_triage'
                        WHERE pending_id = %s
                    """, (item['pending_id'],))
                conn.commit()
                rejected += 1
            else:
                picked = [candidates[i] for i in picked_indices if i < len(candidates)]
                if not picked:
                    skipped += 1
                    continue

                primary = picked[0]
                with conn.cursor() as cur:
                    # Update postings with primary match
                    cur.execute("""
                        UPDATE postings
                        SET berufenet_id = %s,
                            berufenet_verified = 'llm_triage',
                            berufenet_score = %s
                        WHERE berufenet_verified = 'pending_owl'
                          AND berufenet_id IS NULL
                          AND LOWER(job_title) = LOWER(%s)
                    """, (primary['berufenet_id'], primary.get('score', 0), item['raw_value']))

                    # Add OWL synonyms — use VALUES form (not INSERT...SELECT)
                    # to avoid edge-case ON CONFLICT issues
                    for c in picked:
                        cur.execute("""
                            SELECT owl_id FROM owl
                            WHERE owl_type = 'berufenet'
                              AND metadata->>'berufenet_id' = %s
                            LIMIT 1
                        """, (str(c['berufenet_id']),))
                        owl_row = cur.fetchone()
                        if owl_row:
                            cur.execute("""
                                INSERT INTO owl_names (owl_id, language, display_name,
                                    is_primary, name_type, created_by, confidence_source)
                                VALUES (%s, 'de', %s, false, 'alias',
                                        'llm_triage', 'llm_confirmed')
                                ON CONFLICT (owl_id, language, display_name) DO NOTHING
                            """, (owl_row[0], item['raw_value']))

                    # Mark resolved
                    cur.execute("""
                        UPDATE owl_pending
                        SET status = 'resolved',
                            resolution_notes = %s,
                            processed_at = NOW(),
                            processed_by = 'llm_triage'
                        WHERE pending_id = %s
                    """, (f"LLM picked: {[c['name'] for c in picked]}", item['pending_id']))
                conn.commit()
                resolved += 1
        except Exception as e:
            conn.rollback()
            # Try to mark the item so we don't retry it forever
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE owl_pending
                        SET status = 'rejected',
                            resolution_notes = %s,
                            processed_at = NOW(),
                            processed_by = 'llm_triage'
                        WHERE pending_id = %s
                    """, (f"Error: {str(e)[:200]}", item['pending_id']))
                conn.commit()
            except Exception:
                conn.rollback()
            print(f"  [ERR] pending_id={item['pending_id']} raw={item['raw_value']!r}: {e}")
            skipped += 1

    return resolved, rejected, skipped


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    # Re-read password after dotenv
    DB_PARAMS['password'] = os.getenv('DB_PASSWORD', '')

    conn = psycopg2.connect(**DB_PARAMS)
    start = time.time()
    total_resolved = 0
    total_rejected = 0
    total_skipped = 0
    batch_num = 0

    print(f"=== Bulk auto-triage started ===")

    while True:
        batch_num += 1
        r, j, s = run_batch(conn)
        total_resolved += r
        total_rejected += j
        total_skipped += s

        if r == 0 and j == 0 and s == 0:
            print(f"=== All done at batch {batch_num} ===")
            break

        elapsed = time.time() - start
        print(f"  Batch {batch_num}: {r} resolved, {j} rejected, {s} skipped "
              f"(total: {total_resolved}R/{total_rejected}J/{total_skipped}S, {elapsed:.0f}s)")

    elapsed = time.time() - start
    print(f"\n=== Finished: {total_resolved} resolved, {total_rejected} rejected, "
          f"{total_skipped} skipped in {elapsed:.0f}s ({elapsed/60:.1f} min) ===")

    conn.close()


if __name__ == '__main__':
    main()
