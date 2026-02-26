#!/usr/bin/env python3
"""
postings__profession_translate_U.py - Translate new Berufenet profession names DE→EN

PURPOSE:
After each fetch run, new postings arrive with German berufenet_name values.
This actor translates newly-seen names into English using a local Ollama LLM
and saves them to config/profession_translations_en.json, which the search API
hot-reloads on every request.

Runs incrementally: already-translated names are skipped, so each run only
processes names that arrived since the last run.

Input:  postings.berufenet_name (DISTINCT values not yet in translations JSON)
Output: config/profession_translations_en.json  (appended / updated in-place)

PIPELINE POSITION:
    fetch → berufenet → **profession_translate** → domain_gate → geo_state → enrichment

Usage:
    # In pipeline (translate up to 200 new names, ~5 min):
    python3 actors/postings__profession_translate_U.py --limit 200

    # Translate everything still missing (background / one-time backfill):
    python3 actors/postings__profession_translate_U.py

    # Dry run — show stats, don't translate:
    python3 actors/postings__profession_translate_U.py --dry-run

    # Use a faster/smaller model:
    python3 actors/postings__profession_translate_U.py --model qwen2.5:3b --limit 200

Author: Arden
Date: 2026-02-26
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import psycopg2
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.logging_config import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
OUTPUT_FILE  = ROOT / 'config' / 'profession_translations_en.json'

OLLAMA_URL    = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
DEFAULT_MODEL = os.getenv('TRANSLATION_MODEL', 'llama3.1:8b')

# Default limit per pipeline run — keeps the step to ~5 minutes.
# Pass --limit 0 to translate everything (background backfill mode).
DEFAULT_LIMIT = 200
BATCH_SIZE    = 40   # names per LLM call

DB_HOST = 'localhost'
DB_USER = 'base_admin'
DB_PASS = 'A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38'
DB_NAME = 'turing'


# ─────────────────────────────────────────────────────────────────────────────
# DB + FILE I/O
# ─────────────────────────────────────────────────────────────────────────────
def get_all_names() -> list[str]:
    """Return all distinct berufenet_name values from postings, sorted."""
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT berufenet_name FROM postings "
                "WHERE berufenet_name IS NOT NULL ORDER BY 1"
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def load_existing() -> dict:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save(translations: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2, sort_keys=True)


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────
def translate_batch(names: list[str], model: str) -> dict[str, str]:
    """Call Ollama to translate a batch of German job titles to English."""
    names_str = '\n'.join(f'- {n}' for n in names)
    prompt = (
        'Translate the following German job titles to English. '
        'Return ONLY a valid JSON object mapping each German title to its English equivalent. '
        'No explanation, no markdown, just raw JSON.\n\n'
        f'German job titles:\n{names_str}\n\nJSON:'
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.05, 'num_predict': 2048},
            },
            timeout=180,
        )
        if not r.ok:
            logger.warning(f'Ollama HTTP {r.status_code}')
            return {}

        text = r.json().get('response', '').strip()
        start = text.find('{')
        end   = text.rfind('}')
        if start == -1 or end == -1:
            logger.warning(f'No JSON in Ollama response: {text[:200]}')
            return {}

        raw = json.loads(text[start:end + 1])
        return {str(k).strip(): str(v).strip() for k, v in raw.items() if k and v}

    except json.JSONDecodeError as e:
        logger.warning(f'JSON parse error: {e}')
        return {}
    except Exception as e:
        logger.warning(f'Translation error: {e}')
        return {}


def find_match(name: str, result: dict) -> str | None:
    """Case-insensitive lookup in translation result."""
    if name in result:
        return result[name]
    name_lower = name.lower()
    for k, v in result.items():
        if k.lower() == name_lower:
            return v
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Translate new Berufenet profession names DE→EN (incremental)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show stats and exit without translating'
    )
    parser.add_argument(
        '--limit', type=int, default=DEFAULT_LIMIT,
        help=f'Max new names to translate this run (0=all, default={DEFAULT_LIMIT})'
    )
    parser.add_argument(
        '--model', default=DEFAULT_MODEL,
        help=f'Ollama model to use (default: {DEFAULT_MODEL})'
    )
    parser.add_argument(
        '--batch', type=int, default=BATCH_SIZE,
        help=f'Names per LLM call (default: {BATCH_SIZE})'
    )
    args = parser.parse_args()

    logger.info('Loading names from DB…')
    all_names = get_all_names()
    existing  = load_existing()
    to_do     = [n for n in all_names if n not in existing]

    total_in_db = len(all_names)
    already_done = len(existing)
    remaining = len(to_do)

    if args.limit and args.limit > 0:
        to_do = to_do[:args.limit]

    total_batches = (len(to_do) + args.batch - 1) // args.batch if to_do else 0

    logger.info(
        f'Profession translations — DB: {total_in_db}, '
        f'done: {already_done}, remaining: {remaining}, '
        f'this run: {len(to_do)} (model: {args.model})'
    )

    if args.dry_run:
        print(f'DB total:     {total_in_db:>6}')
        print(f'Already done: {already_done:>6}')
        print(f'Remaining:    {remaining:>6}')
        print(f'This run:     {len(to_do):>6}  (--limit {args.limit})')
        print(f'Model:        {args.model}')
        print('\nDry-run — exiting.')
        return

    if not to_do:
        logger.info('Profession translations: nothing new to translate.')
        return

    translations  = dict(existing)
    matched_total = 0

    for i in range(0, len(to_do), args.batch):
        batch    = to_do[i:i + args.batch]
        batch_no = i // args.batch + 1

        logger.info(f'Translating batch {batch_no}/{total_batches} ({len(batch)} names)…')

        result  = translate_batch(batch, args.model)
        matched = 0
        for name in batch:
            en = find_match(name, result)
            if en:
                translations[name] = en
                matched += 1

        matched_total += matched
        logger.info(f'  Batch {batch_no}: {matched}/{len(batch)} matched')

        # Save after every batch — progress is never lost on crash/timeout
        save(translations)

        time.sleep(0.2)

    new_total = len(translations)
    logger.info(
        f'Profession translation run complete: {matched_total} new, '
        f'{new_total}/{total_in_db} total in {OUTPUT_FILE}'
    )

    if remaining > len(to_do):
        still_left = remaining - len(to_do)
        logger.info(
            f'  {still_left} names still untranslated — '
            f'will be picked up in the next pipeline run.'
        )


if __name__ == '__main__':
    main()
