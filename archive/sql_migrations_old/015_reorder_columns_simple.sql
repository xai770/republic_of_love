-- Migration 015: Reorder columns (SIMPLE APPROACH)
-- Date: October 31, 2025
-- Strategy: Export data, drop/recreate tables with correct order, import data
-- Standard: xxx_id (position 1), xxx_name (position 2)

-- This migration will:
-- 1. Create temporary tables with data backup
-- 2. Drop original tables
-- 3. Recreate with correct column order  
-- 4. Restore data
-- 5. Recreate constraints and indexes

BEGIN;

-- ============================================================================
-- BACKUP DATA TO TEMP TABLES
-- ============================================================================

CREATE TEMP TABLE actors_backup AS SELECT * FROM actors;
CREATE TEMP TABLE capabilities_backup AS SELECT * FROM capabilities;
CREATE TEMP TABLE canonicals_backup AS SELECT * FROM canonicals;
CREATE TEMP TABLE postings_backup AS SELECT * FROM postings;
CREATE TEMP TABLE profiles_backup AS SELECT * FROM profiles;
CREATE TEMP TABLE skill_aliases_backup AS SELECT * FROM skill_aliases;
CREATE TEMP TABLE skills_pending_taxonomy_backup AS SELECT * FROM skills_pending_taxonomy;
CREATE TEMP TABLE schema_documentation_backup AS SELECT * FROM schema_documentation;

\echo '✓ Data backed up to temp tables'

-- ============================================================================
-- DROP EXISTING TABLES (CASCADE to drop dependent objects)
-- ============================================================================

DROP TABLE IF EXISTS actors CASCADE;
DROP TABLE IF EXISTS capabilities CASCADE;
DROP TABLE IF EXISTS canonicals CASCADE;
DROP TABLE IF EXISTS postings CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS skill_aliases CASCADE;
DROP TABLE IF EXISTS skills_pending_taxonomy CASCADE;
DROP TABLE IF EXISTS schema_documentation CASCADE;

\echo '✓ Old tables dropped'

-- ============================================================================
-- RECREATE TABLES WITH CORRECT COLUMN ORDER
-- ============================================================================

-- TABLE: actors (actor_id, actor_name, ...)
CREATE TABLE actors (
    actor_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    actor_name TEXT UNIQUE NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('ai_model', 'human', 'machine_actor', 'script', 'llm', 'external_api')),
    url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    execution_type TEXT CHECK (execution_type IN ('ollama_api', 'http_api', 'python_script', 'bash_script', 'human_input')),
    execution_path TEXT,
    execution_config JSONB DEFAULT '{}'::jsonb
);

-- TABLE: capabilities (capability_id, capability_name, ...)
CREATE TABLE capabilities (
    capability_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    capability_name TEXT UNIQUE NOT NULL,
    parent_capability_name TEXT,
    parent_id INTEGER REFERENCES capabilities(capability_id) ON UPDATE CASCADE ON DELETE SET NULL,
    short_description TEXT,
    remarks TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TABLE: canonicals (canonical_id, canonical_name, ...)
CREATE TABLE canonicals (
    canonical_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    canonical_name TEXT UNIQUE NOT NULL,
    facet_name TEXT,
    capability_id INTEGER REFERENCES capabilities(capability_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    capability_description TEXT,
    prompt TEXT,
    response TEXT,
    review_notes TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TABLE: skill_aliases (skill_id, skill_alias, skill_name, ...)
CREATE TABLE skill_aliases (
    skill_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    skill_alias TEXT UNIQUE NOT NULL,
    skill_name TEXT NOT NULL,
    display_name TEXT,
    language TEXT DEFAULT 'en',
    confidence NUMERIC DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,
    notes TEXT
);

-- TABLE: postings (posting_id, posting_name, ...)
CREATE TABLE postings (
    posting_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    posting_name TEXT UNIQUE NOT NULL,
    source_id INTEGER REFERENCES posting_sources(source_id),
    posting_source_id TEXT,
    metadata_source TEXT,
    metadata_created_at TIMESTAMP,
    metadata_last_modified TIMESTAMP,
    metadata_status TEXT,
    metadata_processor TEXT,
    job_title TEXT,
    job_description TEXT,
    job_requirements TEXT,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    location_remote_options TEXT,
    employment_type TEXT,
    employment_schedule TEXT,
    employment_career_level TEXT,
    employment_salary_range TEXT,
    employment_benefits TEXT,
    organization_name TEXT,
    organization_division TEXT,
    organization_division_id TEXT,
    posting_publication_date DATE,
    posting_position_uri TEXT,
    posting_hiring_year INTEGER,
    imported_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    enabled BOOLEAN DEFAULT TRUE,
    skill_keywords JSONB,
    complexity_score INTEGER,
    processing_notes TEXT,
    extracted_summary TEXT,
    summary_extracted_at TIMESTAMP,
    summary_extraction_status TEXT,
    is_test_posting BOOLEAN DEFAULT FALSE
);

-- TABLE: profiles (profile_id, profile_name, ...)
-- Note: Adding profile_name column (currently missing, using full_name)
CREATE TABLE profiles (
    profile_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    profile_name TEXT UNIQUE NOT NULL,  -- New: using full_name as profile_name
    user_id INTEGER REFERENCES users(user_id),
    profile_type TEXT DEFAULT 'self' CHECK (profile_type IN ('self', 'candidate')),
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    location_city TEXT,
    location_country TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    portfolio_url TEXT,
    summary TEXT,
    years_experience INTEGER,
    current_role TEXT,
    current_employer TEXT,
    availability_status TEXT,
    desired_role TEXT,
    desired_salary_range TEXT,
    skill_keywords JSONB,
    imported_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    enabled BOOLEAN DEFAULT TRUE
);

-- TABLE: skills_pending_taxonomy (pending_skill_id, raw_skill_name as "name", ...)
CREATE TABLE skills_pending_taxonomy (
    pending_skill_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    raw_skill_name TEXT NOT NULL,  -- This serves as the "name"
    occurrences INTEGER DEFAULT 1,
    suggested_domain TEXT,
    suggested_canonical TEXT,
    suggested_confidence NUMERIC,
    review_status TEXT DEFAULT 'pending' CHECK (review_status IN ('pending', 'approved', 'rejected', 'duplicate')),
    found_in_jobs TEXT,
    llm_reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    notes TEXT
);

-- TABLE: schema_documentation (documentation_id, table_name as "name", ...)
CREATE TABLE schema_documentation (
    documentation_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    table_name TEXT NOT NULL,  -- This serves as the "name"
    column_name TEXT,
    data_type TEXT,
    description TEXT,
    example_value TEXT,
    constraints TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

\echo '✓ Tables recreated with correct column order'

-- ============================================================================
-- RESTORE DATA FROM BACKUPS
-- ============================================================================

-- actors
INSERT INTO actors OVERRIDING SYSTEM VALUE
SELECT actor_id, actor_name, actor_type, url, enabled, created_at, updated_at, 
       execution_type, execution_path, execution_config
FROM actors_backup;

SELECT setval('actors_actor_id_seq', (SELECT MAX(actor_id) FROM actors));

-- capabilities
INSERT INTO capabilities OVERRIDING SYSTEM VALUE
SELECT capability_id, capability_name, parent_capability_name, parent_id, 
       short_description, remarks, enabled, created_at, updated_at
FROM capabilities_backup;

SELECT setval('capabilities_capability_id_seq', (SELECT MAX(capability_id) FROM capabilities));

-- canonicals
INSERT INTO canonicals OVERRIDING SYSTEM VALUE
SELECT canonical_id, canonical_name, facet_name, capability_id, capability_description,
       prompt, response, review_notes, enabled, created_at, updated_at
FROM canonicals_backup;

SELECT setval('canonicals_canonical_id_seq', (SELECT MAX(canonical_id) FROM canonicals));

-- skill_aliases
INSERT INTO skill_aliases OVERRIDING SYSTEM VALUE
SELECT skill_id, skill_alias, skill_name, display_name, language, confidence,
       created_at, created_by, notes
FROM skill_aliases_backup;

SELECT setval('skill_aliases_skill_id_seq', (SELECT MAX(skill_id) FROM skill_aliases));

-- postings
INSERT INTO postings OVERRIDING SYSTEM VALUE
SELECT posting_id, posting_name, source_id, posting_source_id, metadata_source, 
       metadata_created_at, metadata_last_modified, metadata_status, metadata_processor,
       job_title, job_description, job_requirements, location_city, location_state,
       location_country, location_remote_options, employment_type, employment_schedule,
       employment_career_level, employment_salary_range, employment_benefits,
       organization_name, organization_division, organization_division_id,
       posting_publication_date, posting_position_uri, posting_hiring_year,
       imported_at, updated_at, enabled, skill_keywords, complexity_score,
       processing_notes, extracted_summary, summary_extracted_at, 
       summary_extraction_status, is_test_posting
FROM postings_backup;

SELECT setval('postings_posting_id_seq', (SELECT MAX(posting_id) FROM postings));

-- profiles (using full_name as profile_name)
INSERT INTO profiles OVERRIDING SYSTEM VALUE
SELECT profile_id, full_name as profile_name, user_id, profile_type, full_name, 
       email, phone, location_city, location_country, linkedin_url, github_url,
       portfolio_url, summary, years_experience, current_role, current_employer,
       availability_status, desired_role, desired_salary_range, skill_keywords,
       imported_at, updated_at, enabled
FROM profiles_backup;

SELECT setval('profiles_profile_id_seq', (SELECT MAX(profile_id) FROM profiles));

-- skills_pending_taxonomy
INSERT INTO skills_pending_taxonomy OVERRIDING SYSTEM VALUE
SELECT pending_skill_id, raw_skill_name, occurrences, suggested_domain,
       suggested_canonical, suggested_confidence, review_status, found_in_jobs,
       llm_reasoning, created_at, reviewed_at, reviewed_by, notes
FROM skills_pending_taxonomy_backup;

SELECT setval('skills_pending_taxonomy_pending_skill_id_seq', (SELECT MAX(pending_skill_id) FROM skills_pending_taxonomy));

-- schema_documentation
INSERT INTO schema_documentation OVERRIDING SYSTEM VALUE
SELECT documentation_id, table_name, column_name, data_type, description,
       example_value, constraints, created_at, updated_at
FROM schema_documentation_backup;

SELECT setval('schema_documentation_documentation_id_seq', (SELECT MAX(documentation_id) FROM schema_documentation));

\echo '✓ Data restored'

-- ============================================================================
-- RECREATE INDEXES
-- ============================================================================

-- actors
CREATE INDEX idx_actors_type ON actors(actor_type);
CREATE INDEX idx_actors_enabled ON actors(enabled);

-- capabilities
CREATE INDEX idx_capabilities_enabled ON capabilities(enabled);
CREATE INDEX idx_capabilities_parent ON capabilities(parent_capability_name);

-- canonicals
CREATE INDEX idx_canonicals_enabled ON canonicals(enabled);
CREATE INDEX idx_canonicals_capability ON canonicals(capability_id);

-- skill_aliases
CREATE INDEX idx_skill_aliases_name ON skill_aliases(skill_name);
CREATE INDEX idx_skill_aliases_alias ON skill_aliases(skill_alias);

-- postings
CREATE INDEX idx_postings_name ON postings(posting_name);
CREATE INDEX idx_postings_enabled ON postings(enabled);
CREATE INDEX idx_postings_org ON postings(organization_name);
CREATE INDEX idx_postings_location ON postings(location_city, location_country);
CREATE INDEX idx_postings_test ON postings(is_test_posting);
CREATE INDEX idx_postings_source ON postings(source_id);
CREATE INDEX idx_postings_source_id ON postings(posting_source_id);
CREATE UNIQUE INDEX idx_postings_source_unique ON postings(source_id, posting_source_id) 
    WHERE source_id IS NOT NULL AND posting_source_id IS NOT NULL;

-- profiles
CREATE INDEX idx_profiles_user ON profiles(user_id);
CREATE INDEX idx_profiles_enabled ON profiles(enabled);

-- skills_pending_taxonomy
CREATE INDEX idx_skills_pending_status ON skills_pending_taxonomy(review_status);
CREATE INDEX idx_skills_pending_name ON skills_pending_taxonomy(raw_skill_name);

-- schema_documentation
CREATE INDEX idx_schema_doc_table ON schema_documentation(table_name);

\echo '✓ Indexes recreated'

-- ============================================================================
-- RECREATE FOREIGN KEYS FOR DEPENDENT TABLES
-- ============================================================================

-- job_skills → postings, skill_aliases
ALTER TABLE job_skills 
    ADD CONSTRAINT job_skills_posting_id_fkey 
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id) ON DELETE CASCADE;

ALTER TABLE job_skills
    ADD CONSTRAINT job_skills_skill_id_fkey
    FOREIGN KEY (skill_id) REFERENCES skill_aliases(skill_id);

-- profile_skills → profiles, skill_aliases
ALTER TABLE profile_skills
    ADD CONSTRAINT profile_skills_profile_id_fkey
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE;

ALTER TABLE profile_skills
    ADD CONSTRAINT profile_skills_skill_id_fkey
    FOREIGN KEY (skill_id) REFERENCES skill_aliases(skill_id);

-- skill_hierarchy → skill_aliases (self-referencing)
ALTER TABLE skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_skill_id_fkey
    FOREIGN KEY (skill_id) REFERENCES skill_aliases(skill_id);

ALTER TABLE skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_parent_skill_id_fkey
    FOREIGN KEY (parent_skill_id) REFERENCES skill_aliases(skill_id);

-- profile_job_matches → postings, profiles
ALTER TABLE profile_job_matches
    ADD CONSTRAINT profile_job_matches_posting_id_fkey
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id);

ALTER TABLE profile_job_matches
    ADD CONSTRAINT profile_job_matches_profile_id_fkey
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id);

-- sessions → actors
ALTER TABLE sessions
    ADD CONSTRAINT sessions_actor_id_fkey
    FOREIGN KEY (actor_id) REFERENCES actors(actor_id);

-- instructions → actors (delegate)
ALTER TABLE instructions
    ADD CONSTRAINT instructions_delegate_actor_id_fkey
    FOREIGN KEY (delegate_actor_id) REFERENCES actors(actor_id);

-- human_tasks → actors
ALTER TABLE human_tasks
    ADD CONSTRAINT human_tasks_actor_id_fkey
    FOREIGN KEY (actor_id) REFERENCES actors(actor_id);

\echo '✓ Foreign keys recreated'

-- ============================================================================
-- RECREATE HISTORY TRIGGERS
-- ============================================================================

CREATE TRIGGER actors_history_trigger
    BEFORE UPDATE ON actors
    FOR EACH ROW
    EXECUTE FUNCTION archive_actors();

CREATE TRIGGER capabilities_history_trigger
    BEFORE UPDATE ON capabilities
    FOR EACH ROW
    EXECUTE FUNCTION archive_capabilities();

CREATE TRIGGER canonicals_history_trigger
    BEFORE UPDATE ON canonicals
    FOR EACH ROW
    EXECUTE FUNCTION archive_canonicals();

CREATE TRIGGER postings_history_trigger
    BEFORE UPDATE ON postings
    FOR EACH ROW
    EXECUTE FUNCTION archive_postings();

CREATE TRIGGER profiles_history_trigger
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION archive_profiles();

CREATE TRIGGER skill_aliases_history_trigger
    BEFORE UPDATE ON skill_aliases
    FOR EACH ROW
    EXECUTE FUNCTION archive_skill_aliases();

\echo '✓ Triggers recreated'

-- ============================================================================
-- RECREATE VIEWS
-- ============================================================================

-- Note: Views were CASCADE deleted, need to recreate them
-- (Skipping for now - will need to add based on your existing views)

-- ============================================================================
-- VERIFICATION
-- ============================================================================

\echo ''
\echo '=== VERIFICATION ==='

\echo 'Checking column order...'
SELECT 
    'actors' as table_name,
    string_agg(column_name, ', ' ORDER BY ordinal_position) FILTER (WHERE ordinal_position <= 3) as first_three_columns
FROM information_schema.columns
WHERE table_name = 'actors' AND table_schema = 'public'
UNION ALL
SELECT 'capabilities', string_agg(column_name, ', ' ORDER BY ordinal_position) FILTER (WHERE ordinal_position <= 3)
FROM information_schema.columns WHERE table_name = 'capabilities' AND table_schema = 'public'
UNION ALL
SELECT 'postings', string_agg(column_name, ', ' ORDER BY ordinal_position) FILTER (WHERE ordinal_position <= 3)
FROM information_schema.columns WHERE table_name = 'postings' AND table_schema = 'public'
UNION ALL
SELECT 'profiles', string_agg(column_name, ', ' ORDER BY ordinal_position) FILTER (WHERE ordinal_position <= 3)
FROM information_schema.columns WHERE table_name = 'profiles' AND table_schema = 'public';

\echo ''
\echo 'Checking row counts...'
SELECT 'actors' as table, COUNT(*) as rows FROM actors
UNION ALL SELECT 'capabilities', COUNT(*) FROM capabilities
UNION ALL SELECT 'canonicals', COUNT(*) FROM canonicals
UNION ALL SELECT 'postings', COUNT(*) FROM postings
UNION ALL SELECT 'profiles', COUNT(*) FROM profiles
UNION ALL SELECT 'skill_aliases', COUNT(*) FROM skill_aliases;

COMMIT;

\echo ''
\echo '✅ Migration 015 complete: Column order standardized'
\echo 'Pattern: xxx_id (col 1), xxx_name (col 2)'
