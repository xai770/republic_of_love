-- Migration 013: Multi-User Architecture for talent.yoga
-- Date: October 31, 2025
-- Purpose: Add users, organizations, and multi-source posting support
-- Design: Single users table with role flags, global postings with user preferences

-- ============================================================================
-- PART 1: DROP OLD EMPTY TABLES
-- ============================================================================

DROP TABLE IF EXISTS job_skills CASCADE;
DROP TABLE IF EXISTS profile_skills CASCADE;
DROP TABLE IF EXISTS job_nodes CASCADE;
DROP TABLE IF EXISTS job_skill_edges CASCADE;
DROP TABLE IF EXISTS skill_relationships CASCADE;

-- ============================================================================
-- PART 2: CREATE CORE USER MANAGEMENT TABLES
-- ============================================================================

-- Organizations table (optional membership for users)
CREATE TABLE organizations (
    organization_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    organization_name TEXT UNIQUE NOT NULL,
    organization_type TEXT CHECK (organization_type IN ('recruiting_firm', 'outplacement', 'employer', 'other')),
    contact_email TEXT,
    contact_phone TEXT,
    website_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_organizations_name ON organizations(organization_name);

-- Users table (single table with role flags)
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    
    -- Role flags (users can have multiple roles)
    is_job_seeker BOOLEAN DEFAULT TRUE,
    is_recruiter BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    
    -- Optional organization membership
    organization_id INTEGER REFERENCES organizations(organization_id),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    email_verified_at TIMESTAMP,
    
    -- Flexible preferences storage
    preferences JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_status ON users(status);

-- ============================================================================
-- PART 3: MULTI-SOURCE POSTING INFRASTRUCTURE
-- ============================================================================

-- Posting sources (Deutsche Bank, Arbeitsagentur, etc.)
CREATE TABLE posting_sources (
    source_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source_name TEXT UNIQUE NOT NULL,
    base_url TEXT NOT NULL,
    scraper_config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posting_sources_active ON posting_sources(is_active);

-- Field mappings (Qwen-generated, source-specific)
CREATE TABLE posting_field_mappings (
    mapping_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source_id INTEGER NOT NULL REFERENCES posting_sources(source_id),
    source_field_name TEXT NOT NULL,
    target_field_name TEXT NOT NULL,
    transformation_rule TEXT,
    confidence NUMERIC DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT DEFAULT 'qwen_mapper',
    
    UNIQUE(source_id, source_field_name, target_field_name)
);

CREATE INDEX idx_field_mappings_source ON posting_field_mappings(source_id);

-- ============================================================================
-- PART 4: USER PREFERENCES & INTERACTIONS
-- ============================================================================

-- User posting preferences (opt-out filters)
CREATE TABLE user_posting_preferences (
    preference_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    preference_type TEXT NOT NULL CHECK (preference_type IN ('exclude_company', 'exclude_sector', 'exclude_location', 'exclude_source')),
    preference_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, preference_type, preference_value)
);

CREATE INDEX idx_user_prefs_user ON user_posting_preferences(user_id);

-- User saved postings (bookmarks with application tracking)
CREATE TABLE user_saved_postings (
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    posting_id INTEGER REFERENCES postings(posting_id) ON DELETE CASCADE,
    saved_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    application_status TEXT CHECK (application_status IN ('saved', 'applied', 'interviewing', 'rejected', 'accepted', 'withdrawn')),
    application_date DATE,
    
    PRIMARY KEY (user_id, posting_id)
);

CREATE INDEX idx_user_saved_postings_user ON user_saved_postings(user_id);
CREATE INDEX idx_user_saved_postings_status ON user_saved_postings(application_status);

-- ============================================================================
-- PART 5: ADD USER OWNERSHIP TO EXISTING TABLES
-- ============================================================================

-- Add user_id to profiles
ALTER TABLE profiles 
    ADD COLUMN user_id INTEGER REFERENCES users(user_id),
    ADD COLUMN profile_type TEXT DEFAULT 'self' CHECK (profile_type IN ('self', 'candidate'));

CREATE INDEX idx_profiles_user ON profiles(user_id);

-- Add source tracking to postings
ALTER TABLE postings
    ADD COLUMN source_id INTEGER REFERENCES posting_sources(source_id),
    ADD COLUMN posting_source_id TEXT;

CREATE INDEX IF NOT EXISTS idx_postings_source ON postings(source_id);
CREATE INDEX IF NOT EXISTS idx_postings_source_id ON postings(posting_source_id);

-- Add unique constraint for source + external ID
CREATE UNIQUE INDEX idx_postings_source_unique ON postings(source_id, posting_source_id) 
    WHERE source_id IS NOT NULL AND posting_source_id IS NOT NULL;

-- Add user_id to recipe_runs
ALTER TABLE recipe_runs
    ADD COLUMN user_id INTEGER REFERENCES users(user_id);

CREATE INDEX idx_recipe_runs_user ON recipe_runs(user_id);

-- Add user_id to profile_job_matches
ALTER TABLE profile_job_matches
    ADD COLUMN user_id INTEGER REFERENCES users(user_id);

CREATE INDEX idx_profile_job_matches_user ON profile_job_matches(user_id);

-- ============================================================================
-- PART 6: RECREATE SKILLS TABLES WITH JSONB-SYNC DESIGN
-- ============================================================================

-- Job skills (synced from postings.skill_keywords JSONB)
CREATE TABLE job_skills (
    job_skill_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    posting_id INTEGER NOT NULL REFERENCES postings(posting_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skill_aliases(skill_id),
    
    -- From hybrid JSONB format
    importance TEXT CHECK (importance IN ('essential', 'critical', 'important', 'preferred', 'bonus')),
    weight INTEGER CHECK (weight BETWEEN 10 AND 100),
    proficiency TEXT CHECK (proficiency IN ('expert', 'advanced', 'intermediate', 'beginner')),
    years_required INTEGER,
    reasoning TEXT,
    
    -- Extraction metadata
    extracted_by TEXT,
    recipe_run_id INTEGER REFERENCES recipe_runs(recipe_run_id),
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(posting_id, skill_id)
);

CREATE INDEX idx_job_skills_posting ON job_skills(posting_id);
CREATE INDEX idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX idx_job_skills_importance ON job_skills(importance);
CREATE INDEX idx_job_skills_weight ON job_skills(weight);

-- Profile skills (synced from profiles.skill_keywords JSONB)
CREATE TABLE profile_skills (
    profile_skill_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    profile_id INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skill_aliases(skill_id),
    
    -- From hybrid JSONB format
    years_experience NUMERIC,
    proficiency_level TEXT CHECK (proficiency_level IN ('expert', 'advanced', 'intermediate', 'beginner')),
    last_used_date DATE,
    is_implicit BOOLEAN DEFAULT FALSE,
    evidence_text TEXT,
    
    -- Extraction metadata
    extracted_by TEXT,
    recipe_run_id INTEGER REFERENCES recipe_runs(recipe_run_id),
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(profile_id, skill_id)
);

CREATE INDEX idx_profile_skills_profile ON profile_skills(profile_id);
CREATE INDEX idx_profile_skills_skill ON profile_skills(skill_id);
CREATE INDEX idx_profile_skills_proficiency ON profile_skills(proficiency_level);

-- ============================================================================
-- PART 7: SEED DATA
-- ============================================================================

-- Create demo user
INSERT INTO users (email, password_hash, full_name, is_job_seeker, is_admin, email_verified_at, preferences)
VALUES (
    'demo@talent.yoga',
    '$2b$12$demo.hash.placeholder',  -- Placeholder: needs bcrypt hash
    'Demo User',
    TRUE,
    TRUE,
    NOW(),
    '{"theme": "dark", "language": "en", "notifications": true}'::jsonb
);

-- Create Deutsche Bank posting source
INSERT INTO posting_sources (source_name, base_url, scraper_config, last_scraped_at)
VALUES (
    'Deutsche Bank Careers',
    'https://db.com/careers/students-and-graduates',
    '{"api_endpoint": "/api/job-req-service/jobReqSearch", "pagination": true, "max_results": 100}'::jsonb,
    NOW()
);

-- ============================================================================
-- PART 8: BACKFILL EXISTING DATA
-- ============================================================================

-- Assign all existing profiles to demo user
UPDATE profiles 
SET user_id = 1, 
    profile_type = 'self'
WHERE user_id IS NULL;

-- Assign all existing postings to Deutsche Bank source
UPDATE postings 
SET source_id = 1
WHERE source_id IS NULL;

-- Assign all existing recipe_runs to demo user
UPDATE recipe_runs 
SET user_id = 1
WHERE user_id IS NULL;

-- Assign all existing matches to demo user
UPDATE profile_job_matches 
SET user_id = 1
WHERE user_id IS NULL;

-- ============================================================================
-- PART 9: BACKFILL JOB_SKILLS FROM JSONB
-- ============================================================================

-- Parse skill_keywords JSONB and populate job_skills table
INSERT INTO job_skills (
    posting_id, 
    skill_id, 
    importance, 
    weight, 
    proficiency, 
    years_required, 
    reasoning, 
    extracted_by
)
SELECT 
    p.posting_id,
    sa.skill_id,
    (skill_obj->>'importance')::TEXT,
    (skill_obj->>'weight')::INTEGER,
    (skill_obj->>'proficiency')::TEXT,
    NULLIF(skill_obj->>'years_required', '')::INTEGER,
    skill_obj->>'reasoning',
    'recipe_1121'
FROM postings p
CROSS JOIN LATERAL jsonb_array_elements(p.skill_keywords) AS skill_obj
LEFT JOIN skill_aliases sa ON LOWER(skill_obj->>'skill') = LOWER(sa.skill_alias)
WHERE p.skill_keywords IS NOT NULL
  AND jsonb_array_length(p.skill_keywords) > 0
  AND sa.skill_id IS NOT NULL  -- Only insert if skill matched
ON CONFLICT (posting_id, skill_id) DO NOTHING;

-- ============================================================================
-- PART 10: ADD COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Single user table with role flags for multi-role support';
COMMENT ON TABLE organizations IS 'Optional organization membership for recruiting firms, employers, etc.';
COMMENT ON TABLE posting_sources IS 'Tracks job posting sources (Deutsche Bank, Arbeitsagentur, etc.)';
COMMENT ON TABLE posting_field_mappings IS 'Qwen-generated field mappings for dynamic source adaptation';
COMMENT ON TABLE user_posting_preferences IS 'User opt-out filters for companies, sectors, locations';
COMMENT ON TABLE user_saved_postings IS 'User bookmarks with application tracking';
COMMENT ON TABLE job_skills IS 'Normalized skills extracted from postings.skill_keywords JSONB';
COMMENT ON TABLE profile_skills IS 'Normalized skills extracted from profiles.skill_keywords JSONB';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verification queries:
-- SELECT COUNT(*) FROM users;  -- Should be 1 (demo user)
-- SELECT COUNT(*) FROM posting_sources;  -- Should be 1 (Deutsche Bank)
-- SELECT COUNT(*) FROM postings WHERE source_id = 1;  -- Should be 76
-- SELECT COUNT(*) FROM job_skills;  -- Should be ~710 (71 postings × ~10 skills each)
-- SELECT COUNT(*) FROM profiles WHERE user_id = 1;  -- Should be 4
-- SELECT COUNT(*) FROM recipe_runs WHERE user_id = 1;  -- Should be 569

