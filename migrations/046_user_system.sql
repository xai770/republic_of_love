-- Migration 046: User System Tables
-- Privacy-first user management schema
-- 
-- The ONLY entry point to Turing is via interactions.
-- Users exist because they interacted, not the other way around.
--
-- Author: Arden
-- Date: 2025-11-30

BEGIN;

-- ═══════════════════════════════════════════════════════════════
-- 1. USERS - Identity Stub (minimal, no PII)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS app_users (
    user_id SERIAL PRIMARY KEY,
    
    -- OAuth identity (hashed, not plaintext)
    oauth_provider VARCHAR(50) NOT NULL DEFAULT 'google',
    oauth_subject_hash VARCHAR(64) NOT NULL,  -- SHA256 of Google sub claim
    
    -- System metadata only
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- For GDPR deletion requests
    deleted_at TIMESTAMPTZ,
    deletion_reason VARCHAR(100),
    
    UNIQUE(oauth_provider, oauth_subject_hash)
);

COMMENT ON TABLE app_users IS 
'Minimal identity stub. Contains NO PII. 
OAuth subject is hashed - we cannot reverse it to get email/name.
We know a user EXISTS, not WHO they are.
Named app_users to avoid conflict with existing users table.';

COMMENT ON COLUMN app_users.oauth_subject_hash IS
'SHA256(provider + ":" + subject_id). One-way hash. 
Google cannot be asked "who is this hash" - it is irreversible.';

-- ═══════════════════════════════════════════════════════════════
-- 2. USER_PROFILES - Anonymized Career Data
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Anonymized career data (extracted by local LLM)
    years_experience INTEGER,
    career_level VARCHAR(50),  -- 'junior', 'mid', 'senior', 'executive'
    
    -- Skills as JSONB array (links to our skill taxonomy)
    skills JSONB DEFAULT '[]',
    -- Example: [{"skill_id": 123, "proficiency": "expert", "years": 5}]
    
    -- Work history (anonymized - industries, not companies)
    work_history JSONB DEFAULT '[]',
    -- Example: [{"industry": "banking", "role_type": "risk", "years": 3}]
    -- NOTE: Company associations stored in user_company_verifications, not here
    
    -- Education (anonymized)
    education JSONB DEFAULT '[]',
    -- Example: [{"level": "masters", "field": "finance"}]
    -- NOTE: No school names, no graduation years
    
    -- Desired next role
    target_roles JSONB DEFAULT '[]',
    target_locations JSONB DEFAULT '[]',
    target_industries JSONB DEFAULT '[]',
    
    -- Salary expectations (ranges only)
    salary_min INTEGER,  -- EUR annual
    salary_max INTEGER,
    
    -- Profile versioning
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Raw profile NEVER stored - only this anonymized extract
    anonymization_model VARCHAR(100),
    anonymization_timestamp TIMESTAMPTZ
);

COMMENT ON TABLE user_profiles IS
'Anonymized career profile. Extracted from user-provided resume/CV.
The original document is NEVER stored. Only this anonymized extract exists.
Contains NO: names, company names, school names, dates, contact info.';

CREATE INDEX idx_user_profiles_user ON user_profiles(user_id);

-- ═══════════════════════════════════════════════════════════════
-- 3. USER_PREFERENCES - Matching Rules
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Preference type
    preference_type VARCHAR(50) NOT NULL,
    -- Types: 'include_skill', 'exclude_skill', 'include_company', 
    --        'exclude_company', 'include_industry', 'exclude_industry',
    --        'min_salary', 'max_commute', 'remote_only', etc.
    
    -- The preference value (flexible)
    preference_key VARCHAR(100),
    preference_value VARCHAR(500),
    
    -- Strength of preference (-1.0 to 1.0)
    weight DECIMAL(3,2) DEFAULT 0.0,
    
    -- Source of preference
    source VARCHAR(50) DEFAULT 'user_explicit',
    source_interaction_id BIGINT REFERENCES interactions(interaction_id),
    
    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    -- Audit
    created_by VARCHAR(50),
    
    UNIQUE(user_id, preference_type, preference_key)
);

COMMENT ON TABLE user_preferences IS
'User matching preferences. Both explicit (user said "no tax jobs") 
and inferred (feedback processor detected pattern).
Weight indicates strength: -1=dealbreaker, +1=must-have.';

CREATE INDEX idx_user_preferences_active ON user_preferences(user_id, is_active) 
WHERE is_active = TRUE;

-- ═══════════════════════════════════════════════════════════════
-- 4. USER_FEEDBACK - Raw Feedback Log
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- What they're responding to
    report_id INTEGER,
    posting_id INTEGER REFERENCES postings(posting_id) ON DELETE SET NULL,
    
    -- The feedback itself
    feedback_type VARCHAR(50) NOT NULL,
    
    -- Raw feedback text (anonymized before storage)
    feedback_text TEXT,
    
    -- Structured feedback (extracted by local LLM)
    feedback_structured JSONB,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    preferences_updated JSONB,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    anonymization_model VARCHAR(100)
);

COMMENT ON TABLE user_feedback IS
'User feedback on recommendations. Raw text is anonymized before storage.
Local LLM extracts structured preferences from feedback.';

CREATE INDEX idx_user_feedback_user ON user_feedback(user_id);
CREATE INDEX idx_user_feedback_unprocessed ON user_feedback(processed) WHERE processed = FALSE;

-- ═══════════════════════════════════════════════════════════════
-- 5. USER_REPORTS - Weekly Recommendation Batches
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_reports (
    report_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Report metadata
    report_type VARCHAR(50) DEFAULT 'weekly',
    report_period_start DATE,
    report_period_end DATE,
    
    -- The recommendations
    postings JSONB NOT NULL,
    
    -- Delivery
    delivered_at TIMESTAMPTZ,
    
    -- Engagement
    opened_at TIMESTAMPTZ,
    feedback_received INTEGER DEFAULT 0,
    
    -- Generation metadata
    matching_algorithm_version VARCHAR(20),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_reports IS
'Weekly job recommendation reports sent to users.
Stores which postings were recommended and why.';

CREATE INDEX idx_user_reports_user ON user_reports(user_id);

-- ═══════════════════════════════════════════════════════════════
-- 6. USER_SESSIONS - Login History (Minimal)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Session metadata (no IP addresses, no device fingerprints)
    session_token_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    
    -- Minimal device info (for security, not tracking)
    device_type VARCHAR(20)
);

COMMENT ON TABLE user_sessions IS
'Minimal session tracking. No IP addresses, no detailed device info.
Just enough to manage authentication state.';

CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token_hash) WHERE revoked_at IS NULL;

-- ═══════════════════════════════════════════════════════════════
-- 7. COMPANIES - For ratings (separate from user profiles)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    
    -- Aggregated ratings
    avg_rating DECIMAL(3,2),
    rating_count INTEGER DEFAULT 0,
    
    -- Metadata
    industry VARCHAR(100),
    headquarters_location VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_name)
);

COMMENT ON TABLE companies IS
'Companies that can be rated. Seeded from job postings.
Ratings are aggregated here, individual ratings in company_ratings.';

CREATE INDEX idx_companies_name ON companies(company_name);

-- ═══════════════════════════════════════════════════════════════
-- 8. COMPANY_RATINGS - User ratings of companies
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS company_ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- The rating (1-5 stars)
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    
    -- Optional anonymous review (anonymized)
    review_text TEXT,
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verification_id INTEGER,  -- FK to user_verifications if verified
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One rating per user per company
    UNIQUE(user_id, company_id)
);

COMMENT ON TABLE company_ratings IS
'User ratings of companies. Note: Rating does NOT imply user worked there.
Verification is separate - a user can rate without proving employment.';

CREATE INDEX idx_company_ratings_company ON company_ratings(company_id);

-- Trigger to update company avg_rating
CREATE OR REPLACE FUNCTION update_company_avg_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE companies
    SET avg_rating = (
            SELECT AVG(rating)::DECIMAL(3,2)
            FROM company_ratings
            WHERE company_id = COALESCE(NEW.company_id, OLD.company_id)
        ),
        rating_count = (
            SELECT COUNT(*)
            FROM company_ratings
            WHERE company_id = COALESCE(NEW.company_id, OLD.company_id)
        ),
        updated_at = NOW()
    WHERE company_id = COALESCE(NEW.company_id, OLD.company_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_company_rating
AFTER INSERT OR UPDATE OR DELETE ON company_ratings
FOR EACH ROW EXECUTE FUNCTION update_company_avg_rating();

-- ═══════════════════════════════════════════════════════════════
-- 9. USER_VERIFICATIONS - "Verify then forget" results
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_verifications (
    verification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- What was verified
    verification_type VARCHAR(50) NOT NULL,
    -- Types: 'company_employment', 'certification', 'education', 'skill'
    
    -- The claim (anonymized reference)
    claimed_value VARCHAR(200),
    -- Example: 'company_id:47' or 'CFA' or 'skill_id:123'
    
    -- Verification result (we store ONLY this, not the evidence)
    is_verified BOOLEAN NOT NULL,
    confidence DECIMAL(3,2),  -- 0.00 to 1.00
    
    -- Metadata (no PII)
    verification_method VARCHAR(50),
    -- Methods: 'web_search', 'linkedin_public', 'document_check'
    
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Verifications can expire
    
    -- The search/evidence is NOT stored - only the boolean result
    UNIQUE(user_id, verification_type, claimed_value)
);

COMMENT ON TABLE user_verifications IS
'Verification results using "verify then forget" pattern.
We verify claims (e.g., "worked at Goldman") via web search,
but store ONLY the yes/no result, not the search data.
This protects privacy while enabling trust.';

CREATE INDEX idx_user_verifications_user ON user_verifications(user_id);

-- ═══════════════════════════════════════════════════════════════
-- DONE
-- ═══════════════════════════════════════════════════════════════

COMMIT;
