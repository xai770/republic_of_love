#!/usr/bin/env python3
"""
pipeline_report.py — Per-source posting pipeline summary

Answers: How did the fetch go?

Columns per data provider:
  total        — all postings ever fetched (incl. invalidated)
  active        — not invalidated AND posting_status not in ('invalid')
  has_desc      — job_description present and > 150 chars
  has_summary   — extracted_summary present (LLM-extracted)
  has_embedding — match_text exists in the embeddings table

Usage:
    python3 scripts/pipeline_report.py
    python3 scripts/pipeline_report.py --json
"""

import argparse
import json
import sys
import os

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import psycopg2.extras

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', 'A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38'),
    )


QUERY = """
WITH embedded AS (
    -- postings whose CURRENT match_text has a fresh embedding
    -- match on text_hash (indexed) not text — same hash as embedding actor:
    -- Python: sha256(normalize_text_python(text).encode()).hexdigest()[:32]
    -- normalize_text_python strips unicode whitespace; LOWER(TRIM()) does not.
    SELECT pfm.posting_id
    FROM postings_for_matching pfm
    WHERE EXISTS (
        SELECT 1 FROM embeddings e
        WHERE e.text_hash = LEFT(ENCODE(SHA256(CONVERT_TO(normalize_text_python(pfm.match_text), 'UTF8')), 'hex'), 32)
    )
)
SELECT
    COALESCE(p.source, '(unknown)') AS source,
    COUNT(*)                                                                 AS total,
    COUNT(*) FILTER (
        WHERE NOT p.invalidated
          AND p.posting_status NOT IN ('invalid')
    )                                                                        AS active,
    COUNT(*) FILTER (
        WHERE p.job_description IS NOT NULL
          AND length(p.job_description) > 150
    )                                                                        AS has_desc,
    COUNT(*) FILTER (
        WHERE p.extracted_summary IS NOT NULL
    )                                                                        AS has_summary,
    COUNT(emb.posting_id)                                                    AS has_embedding
FROM postings p
LEFT JOIN embedded emb ON emb.posting_id = p.posting_id
GROUP BY p.source
ORDER BY total DESC
"""

TOTALS_QUERY = """
WITH embedded AS (
    SELECT pfm.posting_id
    FROM postings_for_matching pfm
    WHERE EXISTS (
        SELECT 1 FROM embeddings e
        WHERE e.text_hash = LEFT(ENCODE(SHA256(CONVERT_TO(normalize_text_python(pfm.match_text), 'UTF8')), 'hex'), 32)
    )
)
SELECT
    'TOTAL'                                                                  AS source,
    COUNT(*)                                                                 AS total,
    COUNT(*) FILTER (
        WHERE NOT p.invalidated
          AND p.posting_status NOT IN ('invalid')
    )                                                                        AS active,
    COUNT(*) FILTER (
        WHERE p.job_description IS NOT NULL
          AND length(p.job_description) > 150
    )                                                                        AS has_desc,
    COUNT(*) FILTER (
        WHERE p.extracted_summary IS NOT NULL
    )                                                                        AS has_summary,
    COUNT(emb.posting_id)                                                    AS has_embedding,
    -- Active sub-counts (for %-of-active breakdown)
    COUNT(*) FILTER (
        WHERE NOT p.invalidated
          AND p.posting_status NOT IN ('invalid')
          AND p.job_description IS NOT NULL
          AND length(p.job_description) > 150
    )                                                                        AS active_has_desc,
    COUNT(*) FILTER (
        WHERE NOT p.invalidated
          AND p.posting_status NOT IN ('invalid')
          AND p.extracted_summary IS NOT NULL
    )                                                                        AS active_has_summary,
    (SELECT COUNT(*) FROM embeddings)                                        AS total_embeddings_table
FROM postings p
LEFT JOIN embedded emb ON emb.posting_id = p.posting_id
"""


def pct(num, denom):
    if not denom:
        return '  —  '
    return f'{num / denom * 100:5.1f}%'


def run(as_json=False):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(QUERY)
    rows = [dict(r) for r in cur.fetchall()]

    cur.execute(TOTALS_QUERY)
    total_row = dict(cur.fetchone())
    rows.append(total_row)

    conn.close()

    if as_json:
        print(json.dumps(rows, indent=2))
        return

    # Pretty table
    cols = ['source', 'total', 'active', 'has_desc', 'has_summary', 'has_embedding']
    headers = {
        'source':        'Source',
        'total':         'Total fetched',
        'active':        'Active',
        'has_desc':      'Has description',
        'has_summary':   'Has summary',
        'has_embedding': 'Embedding (current)',
    }

    # Compute column widths
    widths = {c: len(headers[c]) for c in cols}
    for row in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(row[c])))

    sep = '+-' + '-+-'.join('-' * widths[c] for c in cols) + '-+'
    hdr = '| ' + ' | '.join(headers[c].ljust(widths[c]) for c in cols) + ' |'

    print()
    print(f'  Pipeline report — postings by source')
    print()
    print(sep)
    print(hdr)
    print(sep)

    for i, row in enumerate(rows):
        is_total = row['source'] == 'TOTAL'
        if is_total:
            print(sep)

        line_parts = []
        for c in cols:
            val = str(row[c])
            if c == 'source':
                line_parts.append(val.ljust(widths[c]))
            else:
                line_parts.append(val.rjust(widths[c]))
        print('| ' + ' | '.join(line_parts) + ' |')

    print(sep)

    # Percentage breakdown for the totals row
    t = total_row
    emb_table = t.get('total_embeddings_table', '?')
    print()
    print('  Coverage (of all fetched):')
    print(f'    Active          {pct(t["active"],        t["total"])}  ({t["active"]:,} / {t["total"]:,})')
    print(f'    Has description {pct(t["has_desc"],      t["total"])}  ({t["has_desc"]:,} / {t["total"]:,})')
    print(f'    Has summary     {pct(t["has_summary"],   t["total"])}  ({t["has_summary"]:,} / {t["total"]:,})')
    print()
    print('  Coverage (of active postings only):')
    print(f'    Has description   {pct(t["active_has_desc"],    t["active"])}  ({t["active_has_desc"]:,} / {t["active"]:,})')
    print(f'    Has summary       {pct(t["active_has_summary"], t["active"])}  ({t["active_has_summary"]:,} / {t["active"]:,})')
    print(f'    Embedding current {pct(t["has_embedding"],      t["active"])}  ({t["has_embedding"]:,} / {t["active"]:,})')
    emb_need_rerun = t["active"] - t["has_embedding"]
    orphaned = emb_table - t["has_embedding"]
    print()
    print(f'  embeddings table total rows : {emb_table:,}')
    print(f'  current (match_text matched): {t["has_embedding"]:,}')
    print(f'  active postings to re-embed : {emb_need_rerun:,}')
    print()
    print('  Source-specific pipeline rules (why stale embeddings happen):')
    print('    arbeitsagentur : embed job_description directly — no LLM summary')
    print('                     stale when: description backfill updates job_description')
    print('    deutsche_bank  : LLM extracts summary → embed extracted_summary')
    print('                     stale when: extracted_summary written after embedding')
    print('    Fix: always run the embedding actor LAST, after all text-modifying stages.')
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline report: postings by source')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of table')
    args = parser.parse_args()
    run(as_json=args.json)
