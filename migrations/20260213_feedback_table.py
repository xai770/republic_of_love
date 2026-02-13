#!/usr/bin/env python3
"""
Migration: Create feedback table for in-app issue reporting.

Yogis click "Fehler melden" in the header, annotate the screen, and submit.
Creates a feedback table to store reports with screenshots and context.

Run: python3 migrations/20260213_feedback_table.py
Idempotent: safe to re-run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.database import get_connection


def run():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id   SERIAL PRIMARY KEY,
                    user_id       INTEGER REFERENCES users(user_id),
                    url           TEXT NOT NULL,
                    description   TEXT NOT NULL,
                    category      TEXT NOT NULL DEFAULT 'bug',
                    screenshot    TEXT,              -- base64 data URI (png)
                    annotation    JSONB,             -- {x, y, width, height} of highlighted region
                    viewport      JSONB,             -- {width, height, devicePixelRatio}
                    user_agent    TEXT,
                    status        TEXT NOT NULL DEFAULT 'open',
                    admin_notes   TEXT,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at   TIMESTAMPTZ
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_user
                    ON feedback(user_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_status
                    ON feedback(status);
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                    ON feedback(created_at DESC);
            """)
            conn.commit()

            cur.execute("SELECT COUNT(*) AS n FROM feedback")
            n = cur.fetchone()["n"]
            print(f"✓ feedback table ready ({n} existing rows)")


if __name__ == "__main__":
    run()
