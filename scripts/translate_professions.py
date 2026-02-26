#!/usr/bin/env python3
"""
Batch-translate German Berufenet profession names to English.
Uses the local Ollama LLM. Resumes from existing JSON on restart.

Output: config/profession_translations_en.json
        { "Koch": "Chef", "Kauffrau für Büromanagement": "Office Management Clerk", ... }

Usage:
    python scripts/translate_professions.py            # translate all missing
    python scripts/translate_professions.py --limit 50 # test first 50
    python scripts/translate_professions.py --dry-run  # show stats only
    python scripts/translate_professions.py --model qwen2.5:3b  # faster model
"""

import argparse
import json
import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(ROOT, 'config', 'profession_translations_en.json')

OLLAMA_URL   = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
DEFAULT_MODEL = os.getenv('TRANSLATION_MODEL', 'llama3.1:8b')

DB_HOST = 'localhost'
DB_USER = 'base_admin'
DB_PASS = 'A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38'
DB_NAME = 'turing'

BATCH_SIZE = 40   # names per LLM call (balances context size vs. round-trip count)


# ──────────────────────────────────────────────────────────────────────────────
# DB + FILE IO
# ──────────────────────────────────────────────────────────────────────────────
def get_all_names() -> list[str]:
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT berufenet_name FROM postings "
            "WHERE berufenet_name IS NOT NULL ORDER BY 1"
        )
        return [r[0] for r in cur.fetchall()]


def load_existing() -> dict:
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save(translations: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2, sort_keys=True)


# ──────────────────────────────────────────────────────────────────────────────
# TRANSLATION
# ──────────────────────────────────────────────────────────────────────────────
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
            print(f'  HTTP error {r.status_code}')
            return {}

        text = r.json().get('response', '').strip()

        # Extract the first complete JSON object from the response
        start = text.find('{')
        end   = text.rfind('}')
        if start == -1 or end == -1:
            print(f'  WARNING: no JSON in response (first 300 chars): {text[:300]}')
            return {}

        raw = json.loads(text[start:end + 1])
        return {
            str(k).strip(): str(v).strip()
            for k, v in raw.items()
            if k and v
        }

    except json.JSONDecodeError as e:
        print(f'  JSON parse error: {e}')
        return {}
    except Exception as e:
        print(f'  ERROR: {e}')
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


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description='Batch-translate profession names DE→EN')
    parser.add_argument('--dry-run', action='store_true', help='Show stats and exit')
    parser.add_argument('--limit', type=int, default=0, help='Max names to translate (0=all)')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='Ollama model name')
    parser.add_argument('--batch', type=int, default=BATCH_SIZE, help='Batch size')
    args = parser.parse_args()

    print('Loading names from DB…')
    all_names = get_all_names()
    existing  = load_existing()
    to_do     = [n for n in all_names if n not in existing]

    if args.limit:
        to_do = to_do[:args.limit]

    total_batches = (len(to_do) + args.batch - 1) // args.batch
    print(f'DB total:          {len(all_names):>6}')
    print(f'Already done:      {len(existing):>6}')
    print(f'Remaining:         {len(to_do):>6}')
    print(f'Batches (×{args.batch}):  {total_batches:>6}')
    print(f'Model:             {args.model}')

    if args.dry_run:
        print('\nDry-run — exiting.')
        return

    if not to_do:
        print('\nNothing to do.')
        return

    translations = dict(existing)
    matched_total = 0

    for i in range(0, len(to_do), args.batch):
        batch    = to_do[i:i + args.batch]
        batch_no = i // args.batch + 1
        print(f'\rBatch {batch_no}/{total_batches} ({len(batch)} names)…', end=' ', flush=True)

        result  = translate_batch(batch, args.model)
        matched = 0
        for name in batch:
            en = find_match(name, result)
            if en:
                translations[name] = en
                matched += 1

        matched_total += matched
        print(f'{matched}/{len(batch)} matched', end='  ')

        # Save after every batch so progress is never lost
        save(translations)

        # Tiny pause to avoid hammering Ollama
        time.sleep(0.3)

    print(f'\n\nDone! {len(translations)} total translations in {OUTPUT_FILE}')
    unmapped = [n for n in all_names if n not in translations]
    if unmapped:
        print(f'{len(unmapped)} names without translation (retry with --limit to re-run).')


if __name__ == '__main__':
    main()
