-- Migration: Create demand_snapshot and profession_similarity tables
-- for the Opportunity Landscape / market intelligence feature.
-- Run: psql -h localhost -U base_admin -d turing -f migrations/025_demand_snapshot.sql

BEGIN;

-- ── demand_snapshot ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS demand_snapshot (
    snapshot_id     SERIAL PRIMARY KEY,
    location_state  TEXT NOT NULL,
    domain_code     TEXT NOT NULL,
    berufenet_id    INTEGER,
    berufenet_name  TEXT,
    total_postings  INTEGER NOT NULL DEFAULT 0,
    fresh_14d       INTEGER NOT NULL DEFAULT 0,
    fresh_7d        INTEGER NOT NULL DEFAULT 0,
    national_avg    NUMERIC(10,4),
    demand_ratio    NUMERIC(10,4),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (location_state, domain_code, berufenet_id)
);

CREATE INDEX IF NOT EXISTS idx_demand_snapshot_state ON demand_snapshot(location_state);
CREATE INDEX IF NOT EXISTS idx_demand_snapshot_domain ON demand_snapshot(domain_code);
CREATE INDEX IF NOT EXISTS idx_demand_snapshot_berufenet ON demand_snapshot(berufenet_id) WHERE berufenet_id IS NOT NULL;

-- ── profession_similarity ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS profession_similarity (
    berufenet_id_a  INTEGER NOT NULL REFERENCES berufenet(berufenet_id),
    berufenet_id_b  INTEGER NOT NULL REFERENCES berufenet(berufenet_id),
    kldb_score      NUMERIC(5,4) NOT NULL DEFAULT 0,
    embedding_score NUMERIC(5,4),
    combined_score  NUMERIC(5,4) NOT NULL DEFAULT 0,
    rank_for_a      INTEGER,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (berufenet_id_a, berufenet_id_b)
);

CREATE INDEX IF NOT EXISTS idx_prof_sim_a ON profession_similarity(berufenet_id_a, combined_score DESC);
CREATE INDEX IF NOT EXISTS idx_prof_sim_b ON profession_similarity(berufenet_id_b);

COMMIT;
