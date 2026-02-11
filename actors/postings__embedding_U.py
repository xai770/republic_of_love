#!/usr/bin/env python3
"""
postings__embedding_U.py - Compute embeddings for posting summaries

PURPOSE:
Compute bge-m3 embeddings for job posting text (extracted_summary or job_description).
Embeddings are stored in the content-addressed `embeddings` table, keyed by text_hash.
This enables semantic similarity search across postings.

Input:  postings_for_matching.match_text (via CLI batch mode)
Output: embeddings table (text_hash, text, embedding, model)

Design:
- Content-addressed: same text = same hash = computed once
- Parallel-safe: multiple workers can run simultaneously
- Uses postings_for_matching view (same as domain_gate)

Usage:
    # Batch mode (for nightly pipeline):
    python3 actors/postings__embedding_U.py --batch 1000
    
    # Single posting:
    python3 actors/postings__embedding_U.py 12345

Author: Arden
Date: 2026-01-28
"""

import json
import hashlib
import time
import argparse
from typing import Optional, List, Dict, Any

import requests
import psycopg2.extras

# ============================================================================
# SETUP
# ============================================================================

import os
from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings'
MODEL = "bge-m3:567m"
BATCH_SIZE = 100  # Commit every N embeddings


def compute_text_hash(text: str) -> str:
    """Compute text hash for content-addressed storage."""
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:32]


def get_embedding(text: str, model: str = MODEL) -> Optional[List[float]]:
    """Get embedding vector from Ollama."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={'model': model, 'prompt': text},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()['embedding']
    except Exception as e:
        logger.error("Embedding error: %s", e)
    return None


def save_embedding(conn, text: str, embedding: List[float], model: str):
    """Save embedding to database (content-addressed)."""
    # Strip and lowercase text to match hash computation and work_query
    text = text.strip().lower()
    text_hash = compute_text_hash(text)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO embeddings (text_hash, text, embedding, model)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (text_hash) DO NOTHING
    """, (text_hash, text, json.dumps(embedding), model))


def get_postings_needing_embeddings(conn, limit: int) -> List[Dict[str, Any]]:
    """
    Find postings whose match_text doesn't have an embedding yet.
    Uses the postings_for_matching view (same source as domain_gate).
    Content-addressed: we check if the exact text exists in embeddings.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.posting_id, p.match_text
        FROM postings_for_matching p
        WHERE NOT EXISTS (
            SELECT 1 FROM embeddings e
            WHERE e.text = p.match_text
        )
        ORDER BY p.posting_id
        LIMIT %s
    """, (limit,))
    
    return [dict(row) for row in cur.fetchall()]


def process_batch(limit: int = 1000):
    """Process a batch of postings that need embeddings."""
    conn = get_connection_raw()
    
    try:
        postings = get_postings_needing_embeddings(conn, limit)
        
        if not postings:
            logger.info("No postings need embeddings")
            return
        
        logger.info("Found %s postings needing embeddings", len(postings))
        
        start_time = time.time()
        success = 0
        failed = 0
        
        for i, p in enumerate(postings):
            posting_id = p['posting_id']
            text = p['match_text']
            
            # Skip if text too short
            if not text or len(text) < 50:
                continue
            
            embedding = get_embedding(text)
            
            if embedding:
                save_embedding(conn, text, embedding, MODEL)
                success += 1
                
                # Commit in batches
                if success % BATCH_SIZE == 0:
                    conn.commit()
                    elapsed = time.time() - start_time
                    rate = success / elapsed
                    logger.info("%s/%s saved (%.1f/sec)", success, len(postings), rate)
            else:
                failed += 1
        
        # Final commit
        conn.commit()
        
        elapsed = time.time() - start_time
        rate = success / elapsed if elapsed > 0 else 0
        logger.info("Done: %s embeddings in%.1fs (%.1f/sec)", success, elapsed, rate)
        if failed:
            logger.warning("%s failed", failed)
            
    finally:
        return_connection(conn)


def process_single(posting_id: int):
    """Process a single posting."""
    conn = get_connection_raw()
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT match_text FROM postings_for_matching WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        
        if not row:
            logger.error("Posting %s not found in postings_for_matching", posting_id)
            return
        
        text = row[0]
        if not text:
            logger.error("Posting %s has no match_text", posting_id)
            return
        
        embedding = get_embedding(text)
        if embedding:
            save_embedding(conn, text, embedding, MODEL)
            conn.commit()
            logger.info("Embedding saved for posting %s (%s dims)", posting_id, len(embedding))
        else:
            logger.error("Failed to compute embedding for posting %s", posting_id)
            
    finally:
        return_connection(conn)


# ============================================================================
# PULL DAEMON ACTOR CLASS
# ============================================================================
# Wrapper class so core/pull_daemon.py can import and call process() per subject.

class PostingsEmbeddingU:
    """Pull daemon-compatible wrapper for single-posting embedding."""

    def __init__(self, db_conn=None):
        self.conn = db_conn
        self.input_data = {}

    def process(self) -> Dict[str, Any]:
        posting_id = self.input_data.get('subject_id') or self.input_data.get('posting_id')
        if not posting_id:
            return {'success': False, 'error': 'No posting_id/subject_id'}

        conn = self.conn
        own_conn = False
        if conn is None:
            conn = get_connection_raw()
            own_conn = True

        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT match_text FROM postings_for_matching WHERE posting_id = %s
            """, (posting_id,))
            row = cur.fetchone()

            if not row or not row['match_text']:
                return {'success': False, 'skip_reason': 'no_match_text'}

            text = row['match_text']
            # bge-m3 returns NaN for texts under ~150 chars - skip these
            if len(text) < 150:
                return {'success': False, 'skip_reason': 'text_too_short'}

            # bge-m3 context window is ~8K tokens. HTML-bloated postings exceed this.
            # Mark them invalid - they're usually staffing agency boilerplate anyway.
            MAX_TEXT_LENGTH = 6000  # chars (conservative, smallest failure was 6464)
            if len(text) > MAX_TEXT_LENGTH:
                cur.execute("""
                    UPDATE postings SET posting_status = 'invalid', updated_at = NOW()
                    WHERE posting_id = %s
                """, (posting_id,))
                conn.commit()
                return {'success': False, 'skip_reason': 'text_too_long_invalidated'}

            embedding = get_embedding(text)
            if not embedding:
                return {'success': False, 'error': 'Embedding computation failed'}

            save_embedding(conn, text, embedding, MODEL)
            conn.commit()

            return {
                'success': True,
                'posting_id': posting_id,
                'dims': len(embedding),
            }
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            if own_conn and conn:
                return_connection(conn)


def main():
    parser = argparse.ArgumentParser(description="Compute embeddings for posting summaries")
    parser.add_argument('posting_id', nargs='?', type=int, help='Single posting ID')
    parser.add_argument('--batch', '-b', type=int, default=0, help='Batch size (0 = single mode)')
    
    args = parser.parse_args()
    
    if args.batch > 0:
        process_batch(args.batch)
    elif args.posting_id:
        process_single(args.posting_id)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
