-- Migration: profile language + non-destructive translation cache
-- Date: 2026-02-23
-- Rationale: Store the canonical language of each profile, and cache
--   translated versions separately (never overwrite the original).
--   This enables dual-embedding matching: DE profile ↔ DE jobs,
--   EN translation ↔ EN jobs — both active simultaneously.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Canonical language on profiles
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'de';

COMMENT ON COLUMN profiles.language IS
    'ISO-639-1 code of the language the profile was written in (e.g. ''de'', ''en'').
     Set automatically from CV text on upload; can only be ''de'' or ''en'' for now.';

-- 2. Cache table for translated profile summaries
CREATE TABLE IF NOT EXISTS profile_translations (
    translation_id  SERIAL PRIMARY KEY,
    profile_id      INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    language        VARCHAR(10) NOT NULL,          -- target language, e.g. 'en'
    profile_summary TEXT,
    translated_at   TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    model           TEXT DEFAULT 'gemma3:4b',
    CONSTRAINT profile_translations_unique UNIQUE (profile_id, language)
);

CREATE INDEX IF NOT EXISTS idx_profile_translations_profile
    ON profile_translations (profile_id);

COMMENT ON TABLE profile_translations IS
    'Non-destructive translation cache. Each row holds a translated profile_summary
     in a target language. The canonical profile.profile_summary is never overwritten.';

-- 3. Cache table for translated work-history descriptions
CREATE TABLE IF NOT EXISTS profile_work_history_translations (
    id               SERIAL PRIMARY KEY,
    work_history_id  INTEGER NOT NULL
        REFERENCES profile_work_history(work_history_id) ON DELETE CASCADE,
    language         VARCHAR(10) NOT NULL,
    job_description  TEXT,
    translated_at    TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    model            TEXT DEFAULT 'gemma3:4b',
    CONSTRAINT pwht_unique UNIQUE (work_history_id, language)
);

CREATE INDEX IF NOT EXISTS idx_pwht_work_history
    ON profile_work_history_translations (work_history_id);

COMMENT ON TABLE profile_work_history_translations IS
    'Non-destructive translation cache for work-history job descriptions.
     Canonical profile_work_history.job_description is never overwritten.';
