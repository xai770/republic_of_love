#!/usr/bin/env python3
"""
profiles__embedding_backfill_U.py — Backfill profile embeddings

PURPOSE:
Compute bge-m3 embeddings for yogis who already have skills in their profile
but no cached embedding in the embeddings table.

This is a one-shot backfill for yogis who uploaded a CV before the
/api/search/profile endpoint was wired up (before 2026-02-20). After that
date, new CV imports automatically trigger embedding computation via
_schedule_profile_embedding() in api/routers/profiles.py.

Flow:
  1. Query profiles with skill_keywords IS NOT NULL
  2. Build profile text (same convention as search.py / Clara):
       "current_title | skill1 skill2 ... | profile_summary | experience_level"
  3. sha256-hash the text (content-addressed key)
  4. Skip if already in embeddings table
  5. Call Ollama /api/embeddings → INSERT INTO embeddings

Usage:
    python3 actors/profiles__embedding_backfill_U.py [--dry-run] [--limit N]

Author: Arden
Date: 2026-02-20
"""

import argparse
import hashlib
import json
import time
import logging

import requests
import psycopg2.extras

from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger
from config.settings import OLLAMA_EMBED_URL, EMBED_MODEL

logger = get_logger(__name__)

# ============================================================================
# HELPERS
# ============================================================================

def build_profile_text(profile: dict) -> str:
    """Replicate the profile text convention used in search.py / Clara."""
    raw_skills = profile.get('skill_keywords') or []
    if isinstance(raw_skills, str):
        try:
            raw_skills = json.loads(raw_skills)
        except Exception:
            raw_skills = []
    if isinstance(raw_skills, dict):
        raw_skills = raw_skills.get('keywords', [])
    skills = [str(s) for s in raw_skills if s]

    parts = [
        profile.get('current_title') or '',
        ' '.join(skills),
        (profile.get('profile_summary') or '')[:500],
        profile.get('experience_level') or '',
    ]
    return ' | '.join(p for p in parts if p).strip()


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:32]


def get_embedding(text: str) -> list | None:
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={'model': EMBED_MODEL, 'prompt': text},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get('embedding')
    except Exception as e:
        logger.error("Ollama error: %s", e)
    return None


# ============================================================================
# MAIN LOGIC
# ============================================================================

def get_profiles_needing_embeddings(conn, limit: int) -> list:
    """Return profiles that have skills but no cached embedding."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                p.profile_id,
                p.user_id,
                p.skill_keywords,
                p.current_title,
                p.profile_summary,
                p.experience_level
            FROM profiles p
            WHERE p.skill_keywords IS NOT NULL
              AND jsonb_array_length(
                    CASE
                      WHEN jsonb_typeof(p.skill_keywords) = 'array' THEN p.skill_keywords
                      ELSE '[]'::jsonb
                    END
                  ) > 0
            ORDER BY p.updated_at DESC NULLS LAST
            LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def run_backfill(dry_run: bool = False, limit: int = 500):
    conn = get_connection_raw()
    try:
        profiles = get_profiles_needing_embeddings(conn, limit)
        logger.info("Found %d profiles with skills", len(profiles))

        skipped = 0
        computed = 0
        failed = 0

        for p in profiles:
            text = build_profile_text(p)
            if not text or len(text) < 5:
                logger.debug("Profile %d: empty text, skipping", p['profile_id'])
                skipped += 1
                continue

            text_hash = compute_hash(text)

            # Already cached?
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM embeddings WHERE text_hash = %s", (text_hash,))
                if cur.fetchone():
                    logger.debug("Profile %d: already cached", p['profile_id'])
                    skipped += 1
                    continue

            if dry_run:
                logger.info("[DRY RUN] Would embed profile %d | %s", p['profile_id'], text[:60])
                computed += 1
                continue

            logger.info("Computing embedding for profile %d…", p['profile_id'])
            embedding = get_embedding(text.lower().strip())
            if not embedding:
                logger.warning("Profile %d: embedding failed", p['profile_id'])
                failed += 1
                continue

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO embeddings (text_hash, text, embedding, model)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (text_hash) DO NOTHING
                """, (text_hash, text.lower().strip(), json.dumps(embedding), EMBED_MODEL))
            conn.commit()
            computed += 1

            # Respect Ollama GPU — tiny pause between requests
            time.sleep(0.05)

        logger.info(
            "Backfill done: %d computed, %d skipped (already cached / no text), %d failed",
            computed, skipped, failed,
        )

    finally:
        return_connection(conn)


# ============================================================================
# CLI
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description='Backfill profile embeddings')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without writing to DB')
    parser.add_argument('--limit', type=int, default=500,
                        help='Max profiles to process (default 500)')
    args = parser.parse_args()

    run_backfill(dry_run=args.dry_run, limit=args.limit)
