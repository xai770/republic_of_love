-- Migration: 026_arcade_scores.sql
-- Created: 2026-02-16
-- Purpose: Leaderboard for Frustrationsabbau arcade game

CREATE TABLE IF NOT EXISTS arcade_scores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    score INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    monsters_killed INTEGER NOT NULL DEFAULT 0,
    fruits_collected INTEGER NOT NULL DEFAULT 0,
    friendly_fire INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_arcade_scores_top ON arcade_scores (score DESC);
CREATE INDEX IF NOT EXISTS idx_arcade_scores_user ON arcade_scores (user_id, score DESC);
