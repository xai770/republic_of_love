#!/usr/bin/env python3
"""
Compute city snapshot — nightly batch job for search hierarchy panel.

Populates `city_snapshot` with (state × city) and (state × city × domain_code)
aggregates, plus average lat/lon for map markers.

Run after the pipeline completes (called from turing_fetch.sh):
    python3 scripts/compute_city_snapshot.py

Designed to be idempotent — full refresh (DELETE + INSERT).
Typical runtime: < 3 seconds for 293K postings.
"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("city_snapshot")


def compute_snapshot():
    """
    Two-pass computation:
      Pass 1: City totals (state × city, domain_code=NULL)
      Pass 2: City × domain (state × city × domain_code)
    """
    t0 = time.time()

    with get_connection() as conn:
        cur = conn.cursor()

        # Clear old data (full refresh)
        cur.execute("DELETE FROM city_snapshot")
        log.info("Cleared old city snapshot data")

        # ── Pass 1: City totals (state × city, no domain) ────────────────
        cur.execute("""
            INSERT INTO city_snapshot (location_state, location_city, domain_code,
                                       total_postings, fresh_14d, fresh_7d,
                                       avg_lat, avg_lon, computed_at)
            SELECT
                p.location_state,
                p.location_city,
                NULL,
                COUNT(*),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '14 days'),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '7 days'),
                AVG(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS NUMERIC))
                    FILTER (WHERE p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL),
                AVG(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS NUMERIC))
                    FILTER (WHERE p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' IS NOT NULL),
                NOW()
            FROM postings p
            WHERE p.enabled = true AND p.invalidated = false
              AND p.location_state IS NOT NULL
              AND p.location_city IS NOT NULL
            GROUP BY p.location_state, p.location_city
            ON CONFLICT (location_state, location_city, domain_code)
            DO UPDATE SET
                total_postings = EXCLUDED.total_postings,
                fresh_14d = EXCLUDED.fresh_14d,
                fresh_7d = EXCLUDED.fresh_7d,
                avg_lat = EXCLUDED.avg_lat,
                avg_lon = EXCLUDED.avg_lon,
                computed_at = EXCLUDED.computed_at
        """)
        city_rows = cur.rowcount
        log.info(f"Pass 1: {city_rows} city-total rows (state × city)")

        # ── Pass 2: City × domain ────────────────────────────────────────
        cur.execute("""
            INSERT INTO city_snapshot (location_state, location_city, domain_code,
                                       total_postings, fresh_14d, fresh_7d,
                                       avg_lat, avg_lon, computed_at)
            SELECT
                p.location_state,
                p.location_city,
                SUBSTRING(b.kldb FROM 3 FOR 2) AS domain_code,
                COUNT(*),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '14 days'),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '7 days'),
                AVG(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' AS NUMERIC))
                    FILTER (WHERE p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lat' IS NOT NULL),
                AVG(CAST(p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' AS NUMERIC))
                    FILTER (WHERE p.source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'->>'lon' IS NOT NULL),
                NOW()
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE p.enabled = true AND p.invalidated = false
              AND p.location_state IS NOT NULL
              AND p.location_city IS NOT NULL
              AND b.kldb IS NOT NULL
            GROUP BY p.location_state, p.location_city, SUBSTRING(b.kldb FROM 3 FOR 2)
            ON CONFLICT (location_state, location_city, domain_code)
            DO UPDATE SET
                total_postings = EXCLUDED.total_postings,
                fresh_14d = EXCLUDED.fresh_14d,
                fresh_7d = EXCLUDED.fresh_7d,
                avg_lat = EXCLUDED.avg_lat,
                avg_lon = EXCLUDED.avg_lon,
                computed_at = EXCLUDED.computed_at
        """)
        domain_rows = cur.rowcount
        log.info(f"Pass 2: {domain_rows} city×domain rows")

        conn.commit()

        # ── Summary ──────────────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) AS total FROM city_snapshot")
        total = cur.fetchone()['total']
        cur.execute("SELECT COUNT(DISTINCT location_state) AS states FROM city_snapshot")
        states = cur.fetchone()['states']
        cur.execute("SELECT COUNT(DISTINCT location_city) AS cities FROM city_snapshot")
        cities = cur.fetchone()['cities']

        elapsed = time.time() - t0
        log.info(
            f"Done in {elapsed:.1f}s — {total} rows total "
            f"({city_rows} city-totals, {domain_rows} city×domain) "
            f"across {states} states, {cities} cities"
        )

        return {
            "total_rows": total,
            "city_totals": city_rows,
            "city_domain": domain_rows,
            "states": states,
            "cities": cities,
            "elapsed_seconds": round(elapsed, 1),
        }


if __name__ == "__main__":
    result = compute_snapshot()
    print(f"\n✅ City snapshot computed: {result['total_rows']} rows in {result['elapsed_seconds']}s")
