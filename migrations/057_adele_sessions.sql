-- Migration 057: Adele Interview Sessions
-- Tracks conversational profile building state
--
-- Adele is the Interview Coach persona. She builds yogi profiles
-- through conversation instead of CV upload. This table tracks
-- where we are in the interview flow and what data has been collected.
--
-- Author: Arden
-- Date: 2026-02-17

BEGIN;

-- ═══════════════════════════════════════════════════════════════
-- ADELE_SESSIONS — Conversational profile building state
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS adele_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Current phase of the interview
    -- intro → current_role → work_history → skills → education → preferences → summary → complete
    phase VARCHAR(30) NOT NULL DEFAULT 'intro',

    -- Structured data collected so far (progressive build)
    collected JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Example shape:
    -- {
    --   "current_title": "Senior Risk Analyst",
    --   "career_level": "senior",
    --   "work_history": [
    --     {"employer_description": "a large international bank", "role": "Senior Risk Analyst",
    --      "duration_years": 3, "industry": "banking", "key_responsibilities": ["credit risk", "stress tests"]}
    --   ],
    --   "skills": ["Python", "SQL", "Tableau"],
    --   "languages": ["German", "English"],
    --   "certifications": ["FRM"],
    --   "education": [{"level": "masters", "field": "Financial Mathematics"}],
    --   "preferences": {
    --     "desired_roles": ["Head of Risk"],
    --     "desired_locations": ["Frankfurt"],
    --     "salary_min": 90000,
    --     "salary_max": 120000
    --   },
    --   "profile_summary": "Experienced risk analyst..."
    -- }

    -- How many work history entries collected (for the loop)
    work_history_count INTEGER DEFAULT 0,

    -- Conversation turn count
    turn_count INTEGER DEFAULT 0,

    -- Lifecycle
    started_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Only one active session per user (completed sessions don't count)
    started_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_adele_one_active_session
    ON adele_sessions(user_id) WHERE completed_at IS NULL;

COMMENT ON TABLE adele_sessions IS
'Tracks Adele''s conversational profile building sessions.
Each yogi has at most one active session. As Adele asks questions,
collected data accumulates in the JSONB column until the profile
is confirmed and saved.';

COMMIT;
