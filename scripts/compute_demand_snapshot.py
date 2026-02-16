#!/usr/bin/env python3
"""
Compute demand snapshot — nightly batch job for market intelligence.

Populates `demand_snapshot` with (state × domain) and (state × domain × berufenet_id)
aggregate counts, plus national averages and demand ratios.

Run after the pipeline completes:
    python3 scripts/compute_demand_snapshot.py

Designed to be idempotent — uses UPSERT (INSERT ... ON CONFLICT UPDATE).
Typical runtime: < 5 seconds for 232K postings.
"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("demand_snapshot")


def compute_snapshot():
    """
    Two-pass computation:
      Pass 1: Domain-level aggregates (state × domain_code, berufenet_id=NULL)
      Pass 2: Profession-level aggregates (state × domain_code × berufenet_id)

    After populating raw counts, compute national averages per domain/profession
    and demand ratios (this region vs national avg).
    """
    t0 = time.time()

    with get_connection() as conn:
        cur = conn.cursor()

        # Clear old data (full refresh is simpler and fast enough)
        cur.execute("DELETE FROM demand_snapshot")
        log.info("Cleared old snapshot data")

        # ── Pass 1: Domain-level (state × domain_code) ──────────────────
        cur.execute("""
            INSERT INTO demand_snapshot (location_state, domain_code, berufenet_id, berufenet_name,
                                         total_postings, fresh_14d, fresh_7d, computed_at)
            SELECT
                p.location_state,
                SUBSTRING(b.kldb FROM 3 FOR 2) AS domain_code,
                NULL,
                NULL,
                COUNT(*),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '14 days'),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '7 days'),
                NOW()
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            WHERE p.enabled = true AND p.invalidated = false
              AND p.location_state IS NOT NULL
              AND b.kldb IS NOT NULL
            GROUP BY p.location_state, SUBSTRING(b.kldb FROM 3 FOR 2)
            ON CONFLICT (location_state, domain_code, berufenet_id)
            DO UPDATE SET
                total_postings = EXCLUDED.total_postings,
                fresh_14d = EXCLUDED.fresh_14d,
                fresh_7d = EXCLUDED.fresh_7d,
                computed_at = EXCLUDED.computed_at
        """)
        domain_rows = cur.rowcount
        log.info(f"Pass 1: {domain_rows} domain-level rows (state × domain)")

        # ── Pass 2: Profession-level (state × domain × berufenet_id) ────
        # Only for professions with >= 20 postings nationally (suppress noise)
        cur.execute("""
            WITH national_counts AS (
                SELECT p.berufenet_id, COUNT(*) AS cnt
                FROM postings p
                WHERE p.enabled = true AND p.invalidated = false AND p.berufenet_id IS NOT NULL
                GROUP BY p.berufenet_id
                HAVING COUNT(*) >= 20
            )
            INSERT INTO demand_snapshot (location_state, domain_code, berufenet_id, berufenet_name,
                                         total_postings, fresh_14d, fresh_7d, computed_at)
            SELECT
                p.location_state,
                SUBSTRING(b.kldb FROM 3 FOR 2) AS domain_code,
                p.berufenet_id,
                b.name,
                COUNT(*),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '14 days'),
                COUNT(*) FILTER (WHERE p.first_seen_at > NOW() - INTERVAL '7 days'),
                NOW()
            FROM postings p
            JOIN berufenet b ON b.berufenet_id = p.berufenet_id
            JOIN national_counts nc ON nc.berufenet_id = p.berufenet_id
            WHERE p.enabled = true AND p.invalidated = false
              AND p.location_state IS NOT NULL
              AND b.kldb IS NOT NULL
            GROUP BY p.location_state, SUBSTRING(b.kldb FROM 3 FOR 2), p.berufenet_id, b.name
            ON CONFLICT (location_state, domain_code, berufenet_id)
            DO UPDATE SET
                berufenet_name = EXCLUDED.berufenet_name,
                total_postings = EXCLUDED.total_postings,
                fresh_14d = EXCLUDED.fresh_14d,
                fresh_7d = EXCLUDED.fresh_7d,
                computed_at = EXCLUDED.computed_at
        """)
        prof_rows = cur.rowcount
        log.info(f"Pass 2: {prof_rows} profession-level rows")

        # ── Compute national averages and demand ratios ──────────────────
        # For domain-level rows (berufenet_id IS NULL):
        #   national_avg = total postings for this domain / number of states with this domain
        #   demand_ratio = total_postings / national_avg
        cur.execute("""
            WITH national AS (
                SELECT domain_code,
                       AVG(total_postings) AS avg_postings
                FROM demand_snapshot
                WHERE berufenet_id IS NULL
                GROUP BY domain_code
            )
            UPDATE demand_snapshot ds
            SET national_avg = n.avg_postings,
                demand_ratio = CASE
                    WHEN n.avg_postings > 0 THEN ROUND(ds.total_postings / n.avg_postings, 4)
                    ELSE NULL
                END
            FROM national n
            WHERE ds.domain_code = n.domain_code
              AND ds.berufenet_id IS NULL
        """)
        log.info(f"Updated domain-level national averages and ratios")

        # For profession-level rows (berufenet_id IS NOT NULL):
        cur.execute("""
            WITH national AS (
                SELECT domain_code, berufenet_id,
                       AVG(total_postings) AS avg_postings
                FROM demand_snapshot
                WHERE berufenet_id IS NOT NULL
                GROUP BY domain_code, berufenet_id
            )
            UPDATE demand_snapshot ds
            SET national_avg = n.avg_postings,
                demand_ratio = CASE
                    WHEN n.avg_postings > 0 THEN ROUND(ds.total_postings / n.avg_postings, 4)
                    ELSE NULL
                END
            FROM national n
            WHERE ds.domain_code = n.domain_code
              AND ds.berufenet_id = n.berufenet_id
              AND ds.berufenet_id IS NOT NULL
        """)
        log.info(f"Updated profession-level national averages and ratios")

        conn.commit()

        # ── Summary stats ────────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) AS total FROM demand_snapshot")
        total = cur.fetchone()['total']
        cur.execute("SELECT COUNT(*) AS cnt FROM demand_snapshot WHERE berufenet_id IS NULL")
        domain_cnt = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(DISTINCT location_state) AS states FROM demand_snapshot")
        states = cur.fetchone()['states']
        cur.execute("SELECT COUNT(DISTINCT domain_code) AS domains FROM demand_snapshot")
        domains = cur.fetchone()['domains']

        elapsed = time.time() - t0
        log.info(
            f"Done in {elapsed:.1f}s — {total} rows total "
            f"({domain_cnt} domain-level, {total - domain_cnt} profession-level) "
            f"across {states} states, {domains} domains"
        )

        return {
            "total_rows": total,
            "domain_level": domain_cnt,
            "profession_level": total - domain_cnt,
            "states": states,
            "domains": domains,
            "elapsed_seconds": round(elapsed, 1),
        }


if __name__ == "__main__":
    result = compute_snapshot()
    print(f"\n✅ Demand snapshot computed: {result['total_rows']} rows in {result['elapsed_seconds']}s")
