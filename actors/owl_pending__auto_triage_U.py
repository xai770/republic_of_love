#!/usr/bin/env python3
"""
Actor: owl_pending__auto_triage_U
LLM auto-triage for owl_pending berufenet items.

Runs as a turing_daemon actor. For each pending item, asks the LLM to pick
the best berufenet candidate(s). Resolved items become OWL synonyms,
rejected items get marked no_match.

work_query returns pending_id AS subject_id.
process() handles one item at a time.

Registered as actor_id 1306 in the actors table.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import psycopg2.extras
from core.database import get_connection_raw
from lib.berufenet_matching import llm_triage_pick


class OwlPendingAutoTriageU:
    """Pull daemon-compatible actor for LLM auto-triage of owl_pending items."""

    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}

    def process(self) -> Dict[str, Any]:
        pending_id = self.input_data.get('subject_id') or self.input_data.get('pending_id')
        if not pending_id:
            return {'success': False, 'error': 'No pending_id/subject_id'}

        conn = self.conn
        own_conn = False
        if conn is None:
            conn = get_connection_raw()
            own_conn = True

        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Fetch the pending item
            cur.execute("""
                SELECT pending_id, raw_value, source_context
                FROM owl_pending
                WHERE pending_id = %s
                  AND status = 'pending'
            """, (pending_id,))
            item = cur.fetchone()

            if not item:
                return {'success': False, 'skip_reason': 'not_pending'}

            if not item['raw_value']:
                return {'success': False, 'skip_reason': 'empty_raw_value'}

            # Parse candidates from source_context
            candidates = []
            if item['source_context']:
                ctx = item['source_context'] if isinstance(item['source_context'], dict) else json.loads(item['source_context'])
                candidates = ctx.get('candidates', [])

            if not candidates:
                return {'success': False, 'skip_reason': 'no_candidates'}

            # Ask LLM to pick
            picked_indices = llm_triage_pick(item['raw_value'], candidates)

            if not picked_indices:
                # LLM says no match
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
                """, (pending_id,))
                conn.commit()
                return {'success': True, 'status': 'rejected'}

            # LLM picked candidates
            picked = [candidates[i] for i in picked_indices if i < len(candidates)]
            if not picked:
                return {'success': False, 'skip_reason': 'invalid_indices'}

            primary = picked[0]

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

            # Add OWL synonyms
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
                    """, (owl_row['owl_id'], item['raw_value']))

            # Mark resolved
            cur.execute("""
                UPDATE owl_pending
                SET status = 'resolved',
                    resolution_notes = %s,
                    processed_at = NOW(),
                    processed_by = 'llm_triage'
                WHERE pending_id = %s
            """, (f"LLM picked: {[c['name'] for c in picked]}", pending_id))

            conn.commit()
            return {'success': True, 'status': 'resolved', 'picked': len(picked)}

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            return {'success': False, 'error': str(e)[:500]}
        finally:
            if own_conn and conn:
                conn.close()


# CLI mode for manual testing
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pending-id', type=int, help='Process single pending_id')
    parser.add_argument('--stats', action='store_true', help='Show owl_pending stats')
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(str(Path(__file__).parent.parent / '.env'))

    conn = get_connection_raw()

    if args.stats:
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as cnt FROM owl_pending
            WHERE owl_type = 'berufenet'
            GROUP BY status ORDER BY cnt DESC
        """)
        for row in cur.fetchall():
            s, c = (row['status'], row['cnt']) if isinstance(row, dict) else (row[0], row[1])
            print(f"  {s}: {c}")
        conn.close()
        sys.exit(0)

    if args.pending_id:
        actor = OwlPendingAutoTriageU(db_conn=conn)
        actor.input_data = {'subject_id': args.pending_id}
        result = actor.process()
        print(json.dumps(result, indent=2))
        conn.close()
