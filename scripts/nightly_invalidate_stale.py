#!/usr/bin/env python3
"""
nightly_invalidate_stale.py — Mark stale postings as invalidated.

Runs nightly via cron (03:00). A posting is stale when:
  - first_seen_at > 30 days ago (not a brand new posting)
  - last_seen_at  > 7 days ago  (hasn't appeared in any recent fetch)
  - not already invalidated

These postings have disappeared from the source (Arbeitsagentur, Deutsche Bank)
and are no longer valid job listings.

Also invalidates postings with 2+ description fetch failures — the URL is
dead and we'll never get a description.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from core.logging_config import get_logger

logger = get_logger(__name__)


def main():
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
    )

    try:
        cur = conn.cursor()

        # 1. Stale postings: old + not seen recently
        cur.execute("""
            UPDATE postings
            SET invalidated = TRUE, updated_at = NOW()
            WHERE invalidated = FALSE
              AND enabled = TRUE
              AND first_seen_at < NOW() - INTERVAL '30 days'
              AND last_seen_at  < NOW() - INTERVAL '7 days'
        """)
        stale_count = cur.rowcount
        conn.commit()

        # 2. Failed description fetches: gave up after 2+ attempts
        cur.execute("""
            UPDATE postings
            SET invalidated = TRUE, updated_at = NOW()
            WHERE invalidated = FALSE
              AND enabled = TRUE
              AND job_description IS NULL
              AND processing_failures >= 2
        """)
        failed_count = cur.rowcount
        conn.commit()

        logger.info(
            "Stale sweep complete: %d stale (>30d old, >7d unseen), "
            "%d failed descriptions invalidated",
            stale_count, failed_count
        )

    except Exception as e:
        conn.rollback()
        logger.error("Stale sweep failed: %s", e)
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
