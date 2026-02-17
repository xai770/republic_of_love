#!/usr/bin/env python3
"""
berufenet_description_retry.py — Second-pass berufenet matching with job descriptions.

PURPOSE:
Re-attempts berufenet classification for rejected owl_pending items, this time
including the job description as context for the LLM. The original Phase 2 only
sees the job title — this pass feeds the LLM the full description, which often
contains enough clues to resolve ambiguous or generic titles.

FLOW:
    1. Find owl_pending items where status='rejected' AND matching postings
       now have a job_description populated
    2. For each, construct an enriched LLM prompt with title + description excerpt
    3. LLM picks from the existing candidates (already in source_context)
    4. If matched: resolve owl_pending, update postings, add OWL synonym
    5. If still no match: leave as rejected (no change)

PIPELINE POSITION:
    This runs AFTER step 4 (description backfill), either:
    - As a nightly second pass in turing_fetch.sh
    - Or as a periodic cleanup script

EXPECTED YIELD:
    ~20-30% of rejected items should resolve with description context.
    Pattern A (LLM too conservative) and Pattern B (wrong candidate) benefit most.
    Pattern C (berufenet gap) won't benefit — that's expected.

Usage:
    python3 scripts/berufenet_description_retry.py              # Process all eligible
    python3 scripts/berufenet_description_retry.py --limit 100  # Process first 100
    python3 scripts/berufenet_description_retry.py --dry-run    # Show what would happen
    python3 scripts/berufenet_description_retry.py --stats      # Show statistics only

Author: Arden
Date: 2026-02-14
"""
import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from core.logging_config import get_logger

logger = get_logger(__name__)

DB_PARAMS = {
    'dbname': os.getenv('DB_NAME', 'turing'),
    'user': os.getenv('DB_USER', 'base_admin'),
    'password': os.getenv('DB_PASSWORD', ''),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
}

BATCH_SIZE = 50
LLM_MODEL = "qwen2.5:7b"

# ============================================================================
# LLM prompt — enhanced version that includes job description context
# ============================================================================

LLM_TRIAGE_WITH_DESCRIPTION_PROMPT = """You are a German job classification expert. Given a job posting title AND its description, pick which Berufenet professions it matches.

RULES:
- Pick ALL candidates that genuinely match the job (can be 1, 2, or all)
- Use the description to understand what the job ACTUALLY involves
- A match means: same profession, or this Berufenet entry covers this type of work
- Qualification level matters: Helfer ≠ Fachkraft ≠ Spezialist ≠ Experte
- If NONE of the candidates match the actual job described, say NONE
- Answer with ONLY the numbers (e.g. "1" or "1,3" or "NONE")

Job title: "{job_title}"

Job description (excerpt):
{description_excerpt}

Candidates:
{candidates_text}

Answer (numbers only):"""


def _truncate_description(desc: str, max_chars: int = 800) -> str:
    """
    Truncate description to fit in LLM context window.
    Keep beginning (usually has the core job info).
    """
    if not desc:
        return "(no description available)"
    desc = desc.strip()
    if len(desc) <= max_chars:
        return desc
    # Cut at word boundary
    truncated = desc[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."


from config.settings import OLLAMA_GENERATE_URL


def _llm_triage_with_description(job_title: str, description: str, candidates: list[dict]) -> list[int]:
    """
    Ask LLM to pick matches using title + description context.
    Returns list of 0-based indices, or empty list if NONE.
    """
    cands_text = "\n".join(
        f"  {i+1}. {c.get('name', '?')} (score: {c.get('score', 0):.3f})"
        for i, c in enumerate(candidates)
    )

    prompt = LLM_TRIAGE_WITH_DESCRIPTION_PROMPT.format(
        job_title=job_title,
        description_excerpt=_truncate_description(description),
        candidates_text=cands_text,
    )

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={'model': LLM_MODEL, 'prompt': prompt, 'stream': False,
                  'options': {'temperature': 0, 'seed': 42}},
            timeout=90,
        )
        resp.raise_for_status()
        answer = resp.json().get('response', '').strip().upper()

        if 'NONE' in answer:
            return []

        picked = []
        for token in answer.replace(',', ' ').split():
            token = token.strip('.')
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(candidates):
                    picked.append(idx)
        return picked
    except Exception as e:
        logger.error("LLM error: %s", e)
        return []


def get_eligible_items(conn, limit: int = 0) -> list[dict]:
    """
    Find rejected owl_pending items where matching postings now have descriptions.

    Returns items enriched with a representative job_description from postings.
    """
    query = """
        SELECT DISTINCT ON (op.pending_id)
            op.pending_id,
            op.raw_value,
            op.source_context,
            p.job_description,
            p.posting_id
        FROM owl_pending op
        JOIN postings p
            ON LOWER(p.job_title) = LOWER(op.raw_value)
            AND p.job_description IS NOT NULL
            AND LENGTH(p.job_description) > 50
            AND COALESCE(p.invalidated, false) = false
        WHERE op.owl_type = 'berufenet'
          AND op.status = 'rejected'
          AND op.raw_value IS NOT NULL
          AND op.raw_value != ''
          AND COALESCE(op.processed_by, '') != 'description_retry_rejected'
        ORDER BY op.pending_id, LENGTH(p.job_description) DESC
    """
    if limit > 0:
        query += f"\n        LIMIT {limit}"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        return cur.fetchall()


def show_stats(conn):
    """Show statistics about eligible items for retry."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Total rejected
        cur.execute("SELECT COUNT(*) as cnt FROM owl_pending WHERE status = 'rejected'")
        total_rejected = cur.fetchone()['cnt']

        # Rejected with descriptions available
        cur.execute("""
            SELECT COUNT(DISTINCT op.pending_id) as cnt
            FROM owl_pending op
            JOIN postings p
                ON LOWER(p.job_title) = LOWER(op.raw_value)
                AND p.job_description IS NOT NULL
                AND LENGTH(p.job_description) > 50
                AND COALESCE(p.invalidated, false) = false
            WHERE op.owl_type = 'berufenet'
              AND op.status = 'rejected'
              AND COALESCE(op.processed_by, '') != 'description_retry_rejected'
              AND op.raw_value IS NOT NULL
              AND op.raw_value != ''
        """)
        with_desc = cur.fetchone()['cnt']

        # Already retried (check resolution_notes)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM owl_pending
            WHERE status = 'resolved'
              AND processed_by = 'llm_description_retry'
        """)
        previously_resolved = cur.fetchone()['cnt']

        print(f"\n📊 Berufenet Description Retry — Statistics")
        print(f"{'─' * 50}")
        print(f"  Total rejected owl_pending:         {total_rejected:,}")
        print(f"  Have job description available:      {with_desc:,} ({with_desc/max(total_rejected,1)*100:.0f}%)")
        print(f"  Without description (can't retry):   {total_rejected - with_desc:,}")
        print(f"  Previously resolved by retry:        {previously_resolved:,}")
        print(f"  Eligible for retry now:              {with_desc:,}")


def process(limit: int = 0, dry_run: bool = False):
    """Main processing loop."""
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        items = get_eligible_items(conn, limit)
        if not items:
            print("No eligible items for description retry.")
            return {'resolved': 0, 'still_rejected': 0, 'errors': 0}

        print(f"Found {len(items):,} rejected items with descriptions available.")
        if dry_run:
            print("DRY RUN — showing first 10:")
            for item in items[:10]:
                desc_len = len(item['job_description']) if item['job_description'] else 0
                ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
                cands = ctx.get('candidates', [])
                cand_names = [c.get('name', '?') for c in cands[:3]]
                print(f"  [{item['pending_id']}] '{item['raw_value']}' → desc {desc_len} chars, candidates: {cand_names}")
            return {'dry_run': True, 'eligible': len(items)}

        resolved = 0
        still_rejected = 0
        errors = 0
        t0 = time.time()

        for i, item in enumerate(items):
            try:
                ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
                candidates = ctx.get('candidates', [])
                if not candidates:
                    still_rejected += 1
                    continue

                picked_indices = _llm_triage_with_description(
                    item['raw_value'],
                    item['job_description'],
                    candidates,
                )

                if picked_indices:
                    picked = [candidates[j] for j in picked_indices if j < len(candidates)]
                    if not picked:
                        still_rejected += 1
                        continue

                    primary = picked[0]
                    with conn.cursor() as cur:
                        # Update ALL matching postings
                        cur.execute("""
                            UPDATE postings
                            SET berufenet_id = %s,
                                berufenet_verified = 'llm_description_retry',
                                berufenet_score = %s
                            WHERE (berufenet_verified = 'pending_owl' OR berufenet_verified = 'no_match')
                              AND berufenet_id IS NULL
                              AND LOWER(job_title) = LOWER(%s)
                        """, (primary['berufenet_id'], primary.get('score', 0), item['raw_value']))
                        updated = cur.rowcount

                        # Add OWL synonym
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
                                            'llm_description_retry', 'llm_confirmed')
                                    ON CONFLICT (owl_id, language, display_name) DO NOTHING
                                """, (owl_row[0], item['raw_value']))

                        # Mark resolved
                        cur.execute("""
                            UPDATE owl_pending
                            SET status = 'resolved',
                                resolved_owl_id = (
                                    SELECT owl_id FROM owl
                                    WHERE owl_type = 'berufenet'
                                      AND metadata->>'berufenet_id' = %s
                                    LIMIT 1
                                ),
                                resolution_notes = %s,
                                processed_at = NOW(),
                                processed_by = 'llm_description_retry'
                            WHERE pending_id = %s
                        """, (
                            str(primary['berufenet_id']),
                            f"Description retry: {[c['name'] for c in picked]} ({updated} postings updated)",
                            item['pending_id'],
                        ))
                    conn.commit()
                    resolved += 1
                else:
                    # Mark as tried so we don't retry every night
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE owl_pending
                            SET processed_by = 'description_retry_rejected',
                                processed_at = NOW()
                            WHERE pending_id = %s
                        """, (item['pending_id'],))
                    conn.commit()
                    still_rejected += 1

            except Exception as e:
                conn.rollback()
                logger.error("Error processing pending_id=%s: %s", item['pending_id'], e)
                errors += 1

            # Progress reporting
            if (i + 1) % BATCH_SIZE == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"  [{i+1}/{len(items)}] {resolved}R/{still_rejected}J/{errors}E "
                      f"({rate:.1f}/s, {elapsed:.0f}s)")

        elapsed = time.time() - t0
        resolve_rate = resolved / max(resolved + still_rejected, 1) * 100

        print(f"\n{'=' * 60}")
        print(f"Description retry complete in {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"{'=' * 60}")
        print(f"  ✅ Newly resolved:    {resolved:,} ({resolve_rate:.0f}%)")
        print(f"  ❌ Still rejected:    {still_rejected:,}")
        print(f"  ⚠️  Errors:           {errors:,}")

        return {'resolved': resolved, 'still_rejected': still_rejected, 'errors': errors}

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Re-attempt berufenet matching with job descriptions")
    parser.add_argument('--limit', type=int, default=0, help='Max items to process (0 = all)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    args = parser.parse_args()

    if args.stats:
        conn = psycopg2.connect(**DB_PARAMS)
        try:
            show_stats(conn)
        finally:
            conn.close()
        return

    process(limit=args.limit, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
