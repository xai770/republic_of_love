-- ============================================================
-- Profile: implied skills, skill weights, preferences
-- 2026-02-23
--
-- Three additions that form the adaptive matching layer:
--
-- 1. profiles.implied_skills   — Skills inferred by LLM from achievements,
--    not stated explicitly. Set once during CV processing (Pass 3).
--    Format: [{name, category, confidence, evidence}]
--    Used by matching as a secondary skill signal.
--
-- 2. profiles.skill_weights    — Per-skill multipliers updated from yogi
--    feedback (saves/dismissals on postings). Default 1.0 = neutral.
--    >1.0 = yogi wants more of this. <1.0 = deprioritise.
--    Format: [{skill, weight}]
--
-- 3. profile_preferences       — Normalised rows, one per preference signal.
--    Accumulates from explicit yogi input AND from yogi_posting_events
--    (auto-inferred: multiple dismissals in same domain → negative pref).
--    topic_type: skill | domain | employer_type | role_type | location
--    sentiment:  like | dislike | neutral
--    source:     explicit | inferred_from_events
--    strength:   1 (weak) – 3 (strong)
-- ============================================================


-- ── Step 1: Add columns to profiles ─────────────────────────

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS implied_skills   JSONB,
    ADD COLUMN IF NOT EXISTS skill_weights    JSONB;

COMMENT ON COLUMN profiles.implied_skills IS
    'LLM-inferred skills not explicitly stated in CV. '
    'Array of {name, category, confidence, evidence}. '
    'Set by cv_anonymizer Pass 3. Never overwritten — only set if null.';

COMMENT ON COLUMN profiles.skill_weights IS
    'Per-skill weight multipliers for matching, updated from yogi feedback. '
    'Array of {skill, weight} where weight defaults to 1.0. '
    'Updated incrementally by preference-learning pipeline.';


-- GIN index: fast containment queries like
--   WHERE implied_skills @> '[{"name": "SQL"}]'
CREATE INDEX IF NOT EXISTS idx_profiles_implied_skills
    ON profiles USING GIN (implied_skills jsonb_path_ops)
    WHERE implied_skills IS NOT NULL;


-- ── Step 2: profile_preferences table ───────────────────────

CREATE TABLE IF NOT EXISTS profile_preferences (
    preference_id   BIGSERIAL PRIMARY KEY,
    profile_id      INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,

    -- What the preference is about
    topic_type      TEXT NOT NULL CHECK (topic_type IN (
                        'skill',            -- e.g. "Python", "Contract Management"
                        'domain',           -- e.g. "Banking", "Software Procurement"
                        'employer_type',    -- e.g. "large German bank", "startup"
                        'role_type',        -- e.g. "team lead", "individual contributor"
                        'location'          -- e.g. "remote", "Frankfurt"
                    )),
    topic_value     TEXT NOT NULL,          -- the actual value

    -- How the yogi feels about it
    sentiment       TEXT NOT NULL CHECK (sentiment IN ('like', 'dislike', 'neutral')),
    strength        SMALLINT NOT NULL DEFAULT 1 CHECK (strength BETWEEN 1 AND 3),
    -- strength 1 = mild, 2 = clear, 3 = strong ("never again")

    -- Where this signal came from
    source          TEXT NOT NULL CHECK (source IN (
                        'explicit',              -- yogi typed/selected it directly
                        'inferred_from_events'   -- auto-derived from saved/dismissed events
                    )),
    source_event_id BIGINT REFERENCES yogi_posting_events(event_id) ON DELETE SET NULL,
    -- non-null when source = 'inferred_from_events' and traceable to one event

    -- Notes visible to yogi (shown in /profile preferences section)
    note            TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast lookup: all preferences for a profile (main query pattern)
CREATE INDEX IF NOT EXISTS idx_pp_profile_id
    ON profile_preferences (profile_id);

-- Upsert support: find existing preference by profile + topic
CREATE UNIQUE INDEX IF NOT EXISTS idx_pp_profile_topic_unique
    ON profile_preferences (profile_id, topic_type, topic_value);
-- This means: one row per (profile, topic_type, topic_value) pair.
-- When a second signal arrives for the same topic, we UPDATE strength/sentiment
-- rather than inserting a duplicate. Keeps the table clean.

-- Filter by sentiment (e.g. "all dislikes for this profile")
CREATE INDEX IF NOT EXISTS idx_pp_profile_sentiment
    ON profile_preferences (profile_id, sentiment);
