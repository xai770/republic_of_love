-- ── 064 Create city_snapshot table ────────────────────────────────────────────
-- City-level aggregates for the search redesign.
-- Provides (state × city × domain_code) counts with average coordinates,
-- enabling the Bundesland→City hierarchy panel and city map markers.
-- Populated by scripts/compute_city_snapshot.py alongside the demand_snapshot.
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

CREATE TABLE IF NOT EXISTS city_snapshot (
    city_id         SERIAL PRIMARY KEY,
    location_state  TEXT NOT NULL,
    location_city   TEXT NOT NULL,
    domain_code     TEXT,                          -- NULL = state×city total row
    total_postings  INTEGER NOT NULL DEFAULT 0,
    fresh_14d       INTEGER NOT NULL DEFAULT 0,
    fresh_7d        INTEGER NOT NULL DEFAULT 0,
    avg_lat         NUMERIC(9,6),
    avg_lon         NUMERIC(9,6),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (location_state, location_city, domain_code)
);

CREATE INDEX IF NOT EXISTS idx_city_snapshot_state     ON city_snapshot(location_state);
CREATE INDEX IF NOT EXISTS idx_city_snapshot_city      ON city_snapshot(location_city);
CREATE INDEX IF NOT EXISTS idx_city_snapshot_domain    ON city_snapshot(domain_code) WHERE domain_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_city_snapshot_total     ON city_snapshot(total_postings DESC);

COMMENT ON TABLE city_snapshot IS 'City-level posting aggregates for the search hierarchy panel. Refreshed nightly by compute_city_snapshot.py.';

COMMIT;
