-- Migration 015: Reorder columns to put xxx_id first in all tables
-- Date: October 31, 2025
-- Purpose: Database design best practice - primary keys should be first column
-- Affected tables: 8 tables where PK is not in position 1
-- Risk level: HIGH - requires table recreation, but with careful data preservation

-- NOTE: This migration will:
-- 1. Create new table with correct column order
-- 2. Copy all data from old table
-- 3. Drop old table and rename new table
-- 4. Recreate all constraints, indexes, triggers
-- 5. Verify data integrity

BEGIN;

-- ============================================================================
-- TABLE 1: actors (actor_id from position 10 → 1)
-- ============================================================================

\echo 'Reordering actors table...'

-- Create new table with correct order
CREATE TABLE actors_new (
    actor_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    actor_name TEXT UNIQUE NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('ai_model', 'human', 'machine_actor', 'script', 'llm', 'external_api')),
    url TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    execution_type TEXT,
    execution_path TEXT,
    execution_config JSONB
);

-- Copy data
INSERT INTO actors_new OVERRIDING SYSTEM VALUE
SELECT actor_id, actor_name, actor_type, url, enabled, created_at, updated_at, execution_type, execution_path, execution_config
FROM actors;

-- Update sequence to continue from max value
SELECT setval('actors_new_actor_id_seq', (SELECT MAX(actor_id) FROM actors_new));

-- Drop old table and its sequence
DROP SEQUENCE IF EXISTS actors_actor_id_seq CASCADE;
DROP TABLE actors CASCADE;

-- Rename new table and sequence
ALTER TABLE actors_new RENAME TO actors;
ALTER SEQUENCE actors_new_actor_id_seq RENAME TO actors_actor_id_seq;

-- Recreate indexes
CREATE INDEX idx_actors_type ON actors(actor_type);
CREATE INDEX idx_actors_enabled ON actors(enabled);

-- Recreate history trigger if it exists
CREATE TRIGGER actors_history_trigger
    BEFORE UPDATE ON actors
    FOR EACH ROW
    EXECUTE FUNCTION archive_actors();

\echo 'actors ✓'

-- ============================================================================
-- TABLE 2: capabilities (capability_id from position 8 → 1)
-- ============================================================================

\echo 'Reordering capabilities table...'

CREATE TABLE capabilities_new (
    capability_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    capability_name TEXT UNIQUE NOT NULL,
    parent_capability_name TEXT,
    parent_id INTEGER REFERENCES capabilities_new(capability_id) ON UPDATE CASCADE ON DELETE SET NULL,
    short_description TEXT,
    remarks TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Copy data
INSERT INTO capabilities_new OVERRIDING SYSTEM VALUE
SELECT capability_id, capability_name, parent_capability_name, parent_id, short_description, remarks, enabled, created_at, updated_at
FROM capabilities;

-- Update sequence
SELECT setval('capabilities_new_capability_id_seq', (SELECT MAX(capability_id) FROM capabilities_new));

-- Drop old and rename
DROP TABLE capabilities CASCADE;
ALTER TABLE capabilities_new RENAME TO capabilities;
ALTER SEQUENCE capabilities_new_capability_id_seq RENAME TO capabilities_capability_id_seq;

-- Recreate indexes
CREATE INDEX idx_capabilities_enabled ON capabilities(enabled);
CREATE INDEX idx_capabilities_parent ON capabilities(parent_capability_name);

-- Recreate history trigger
CREATE TRIGGER capabilities_history_trigger
    BEFORE UPDATE ON capabilities
    FOR EACH ROW
    EXECUTE FUNCTION archive_capabilities();

-- Add comments (critical ones)
COMMENT ON TABLE capabilities IS 
'Hierarchical taxonomy of cognitive/computational capabilities (74 entries).
HISTORICAL NOTE: Previously named "facets" - see rfa_latest/rfa_facets.md for the conceptual foundation.
Column order standardized 2025-10-31 (migration 015).';

COMMENT ON COLUMN capabilities.capability_id IS 
'Surrogate key - stable integer identifier for foreign key joins.
Used by canonicals table to link test cases to capabilities.';

\echo 'capabilities ✓'

-- ============================================================================
-- TABLE 3: canonicals (canonical_id from position 10 → 1)
-- ============================================================================

\echo 'Reordering canonicals table...'

CREATE TABLE canonicals_new (
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

-- Copy data
INSERT INTO canonicals_new OVERRIDING SYSTEM VALUE
SELECT canonical_id, canonical_name, facet_name, capability_id, capability_description, prompt, response, review_notes, enabled, created_at, updated_at
FROM canonicals;

-- Update sequence
SELECT setval('canonicals_new_canonical_id_seq', (SELECT MAX(canonical_id) FROM canonicals_new));

-- Drop old and rename
DROP TABLE canonicals CASCADE;
ALTER TABLE canonicals_new RENAME TO canonicals;
ALTER SEQUENCE canonicals_new_canonical_id_seq RENAME TO canonicals_canonical_id_seq;

-- Recreate indexes
CREATE INDEX idx_canonicals_enabled ON canonicals(enabled);
CREATE INDEX idx_canonicals_capability ON canonicals(capability_id);

-- Recreate history trigger
CREATE TRIGGER canonicals_history_trigger
    BEFORE UPDATE ON canonicals
    FOR EACH ROW
    EXECUTE FUNCTION archive_canonicals();

\echo 'canonicals ✓'

-- ============================================================================
-- TABLE 4: skill_aliases (skill_id from position 9 → 1)
-- ============================================================================

\echo 'Reordering skill_aliases table...'

CREATE TABLE skill_aliases_new (
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

-- Copy data
INSERT INTO skill_aliases_new OVERRIDING SYSTEM VALUE
SELECT skill_id, skill_alias, skill_name, display_name, language, confidence, created_at, created_by, notes
FROM skill_aliases;

-- Update sequence
SELECT setval('skill_aliases_new_skill_id_seq', (SELECT MAX(skill_id) FROM skill_aliases_new));

-- Drop old and rename
DROP TABLE skill_aliases CASCADE;
ALTER TABLE skill_aliases_new RENAME TO skill_aliases;
ALTER SEQUENCE skill_aliases_new_skill_id_seq RENAME TO skill_aliases_skill_id_seq;

-- Recreate indexes
CREATE INDEX idx_skill_aliases_name ON skill_aliases(skill_name);
CREATE INDEX idx_skill_aliases_alias ON skill_aliases(skill_alias);

-- Recreate history trigger
CREATE TRIGGER skill_aliases_history_trigger
    BEFORE UPDATE ON skill_aliases
    FOR EACH ROW
    EXECUTE FUNCTION archive_skill_aliases();

\echo 'skill_aliases ✓'

-- ============================================================================
-- TABLE 5: skill_hierarchy (composite PK, skill_id from position 7 → 1)
-- ============================================================================

\echo 'Reordering skill_hierarchy table...'

CREATE TABLE skill_hierarchy_new (
    skill_id INTEGER NOT NULL REFERENCES skill_aliases(skill_id),
    parent_skill_id INTEGER NOT NULL REFERENCES skill_aliases(skill_id),
    strength NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by TEXT,
    notes TEXT,
    PRIMARY KEY (skill_id, parent_skill_id)
);

-- Copy data
INSERT INTO skill_hierarchy_new (skill_id, parent_skill_id, strength, created_at, created_by, notes)
SELECT skill_id, parent_skill_id, strength, created_at, created_by, notes
FROM skill_hierarchy;

-- Drop old and rename
DROP TABLE skill_hierarchy CASCADE;
ALTER TABLE skill_hierarchy_new RENAME TO skill_hierarchy;

-- Recreate indexes
CREATE INDEX idx_skill_hierarchy_parent ON skill_hierarchy(parent_skill_id);
CREATE INDEX idx_skill_hierarchy_strength ON skill_hierarchy(strength);

\echo 'skill_hierarchy ✓'

-- ============================================================================
-- TABLE 6: skills_pending_taxonomy (pending_skill_id from position 13 → 1)
-- ============================================================================

\echo 'Reordering skills_pending_taxonomy table...'

CREATE TABLE skills_pending_taxonomy_new (
    pending_skill_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    raw_skill_name TEXT NOT NULL,
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

-- Copy data
INSERT INTO skills_pending_taxonomy_new OVERRIDING SYSTEM VALUE
SELECT pending_skill_id, raw_skill_name, occurrences, suggested_domain, suggested_canonical, suggested_confidence, review_status, found_in_jobs, llm_reasoning, created_at, reviewed_at, reviewed_by, notes
FROM skills_pending_taxonomy;

-- Update sequence
SELECT setval('skills_pending_taxonomy_new_pending_skill_id_seq', (SELECT MAX(pending_skill_id) FROM skills_pending_taxonomy_new));

-- Drop old and rename
DROP TABLE skills_pending_taxonomy CASCADE;
ALTER TABLE skills_pending_taxonomy_new RENAME TO skills_pending_taxonomy;
ALTER SEQUENCE skills_pending_taxonomy_new_pending_skill_id_seq RENAME TO skills_pending_taxonomy_pending_skill_id_seq;

-- Recreate indexes
CREATE INDEX idx_skills_pending_status ON skills_pending_taxonomy(review_status);
CREATE INDEX idx_skills_pending_name ON skills_pending_taxonomy(raw_skill_name);

\echo 'skills_pending_taxonomy ✓'

-- ============================================================================
-- TABLE 7: schema_documentation (documentation_id from position 9 → 1)
-- ============================================================================

\echo 'Reordering schema_documentation table...'

CREATE TABLE schema_documentation_new (
    documentation_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    table_name TEXT NOT NULL,
    column_name TEXT,
    data_type TEXT,
    description TEXT,
    example_value TEXT,
    constraints TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Copy data
INSERT INTO schema_documentation_new OVERRIDING SYSTEM VALUE
SELECT documentation_id, table_name, column_name, data_type, description, example_value, constraints, created_at, updated_at
FROM schema_documentation;

-- Update sequence
SELECT setval('schema_documentation_new_documentation_id_seq', (SELECT MAX(documentation_id) FROM schema_documentation_new));

-- Drop old and rename
DROP TABLE schema_documentation CASCADE;
ALTER TABLE schema_documentation_new RENAME TO schema_documentation;
ALTER SEQUENCE schema_documentation_new_documentation_id_seq RENAME TO schema_documentation_documentation_id_seq;

-- Recreate indexes
CREATE INDEX idx_schema_doc_table ON schema_documentation(table_name);

\echo 'schema_documentation ✓'

-- ============================================================================
-- TABLE 8: postings (posting_id from position 35 → 1)
-- ============================================================================

\echo 'Reordering postings table (largest table, may take time)...'

CREATE TABLE postings_new (
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

-- Copy data (this may take a moment)
INSERT INTO postings_new OVERRIDING SYSTEM VALUE
SELECT posting_id, posting_name, source_id, posting_source_id, metadata_source, metadata_created_at, 
       metadata_last_modified, metadata_status, metadata_processor, job_title, job_description, 
       job_requirements, location_city, location_state, location_country, location_remote_options, 
       employment_type, employment_schedule, employment_career_level, employment_salary_range, 
       employment_benefits, organization_name, organization_division, organization_division_id, 
       posting_publication_date, posting_position_uri, posting_hiring_year, imported_at, updated_at, 
       enabled, skill_keywords, complexity_score, processing_notes, extracted_summary, 
       summary_extracted_at, summary_extraction_status, is_test_posting
FROM postings;

-- Update sequence
SELECT setval('postings_new_posting_id_seq', (SELECT MAX(posting_id) FROM postings_new));

-- Drop old and rename
DROP TABLE postings CASCADE;
ALTER TABLE postings_new RENAME TO postings;
ALTER SEQUENCE postings_new_posting_id_seq RENAME TO postings_posting_id_seq;

-- Recreate indexes
CREATE INDEX idx_postings_name ON postings(posting_name);
CREATE INDEX idx_postings_enabled ON postings(enabled);
CREATE INDEX idx_postings_org ON postings(organization_name);
CREATE INDEX idx_postings_location ON postings(location_city, location_country);
CREATE INDEX idx_postings_test ON postings(is_test_posting);
CREATE INDEX IF NOT EXISTS idx_postings_source ON postings(source_id);
CREATE INDEX IF NOT EXISTS idx_postings_source_id ON postings(posting_source_id);
CREATE UNIQUE INDEX idx_postings_source_unique ON postings(source_id, posting_source_id) 
    WHERE source_id IS NOT NULL AND posting_source_id IS NOT NULL;

-- Recreate history trigger
CREATE TRIGGER postings_history_trigger
    BEFORE UPDATE ON postings
    FOR EACH ROW
    EXECUTE FUNCTION archive_postings();

\echo 'postings ✓'

-- ============================================================================
-- RECREATE DEPENDENT TABLES (CASCADE deleted them)
-- ============================================================================

\echo 'Recreating dependent foreign keys...'

-- Recreate job_skills FK
ALTER TABLE job_skills 
    ADD CONSTRAINT job_skills_posting_id_fkey 
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id) ON DELETE CASCADE;

ALTER TABLE job_skills
    ADD CONSTRAINT job_skills_skill_id_fkey
    FOREIGN KEY (skill_id) REFERENCES skill_aliases(skill_id);

-- Recreate profile_job_matches FK
ALTER TABLE profile_job_matches
    ADD CONSTRAINT profile_job_matches_posting_id_fkey
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id);

-- Recreate instruction_runs posting references (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'instruction_runs' AND column_name = 'posting_id') THEN
        ALTER TABLE instruction_runs
            ADD CONSTRAINT instruction_runs_posting_id_fkey
            FOREIGN KEY (posting_id) REFERENCES postings(posting_id);
    END IF;
END $$;

-- Recreate instructions FK to actors
ALTER TABLE instructions
    ADD CONSTRAINT instructions_actor_id_fkey
    FOREIGN KEY (actor_id) REFERENCES actors(actor_id);

\echo 'Foreign keys recreated ✓'

-- ============================================================================
-- VERIFICATION
-- ============================================================================

\echo ''
\echo '=== VERIFICATION ==='

\echo 'Checking column order for all 8 tables...'
SELECT 
    table_name,
    string_agg(column_name, ', ' ORDER BY ordinal_position) FILTER (WHERE ordinal_position <= 3) as first_three_columns
FROM information_schema.columns
WHERE table_name IN ('actors', 'capabilities', 'canonicals', 'skill_aliases', 
                     'skill_hierarchy', 'skills_pending_taxonomy', 'schema_documentation', 'postings')
AND table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;

\echo ''
\echo 'Checking row counts preserved...'
SELECT 
    'actors' as table_name, COUNT(*) as rows FROM actors
UNION ALL SELECT 'capabilities', COUNT(*) FROM capabilities
UNION ALL SELECT 'canonicals', COUNT(*) FROM canonicals
UNION ALL SELECT 'skill_aliases', COUNT(*) FROM skill_aliases
UNION ALL SELECT 'skill_hierarchy', COUNT(*) FROM skill_hierarchy
UNION ALL SELECT 'skills_pending_taxonomy', COUNT(*) FROM skills_pending_taxonomy
UNION ALL SELECT 'schema_documentation', COUNT(*) FROM schema_documentation
UNION ALL SELECT 'postings', COUNT(*) FROM postings;

\echo ''
\echo 'Checking foreign keys working...'
SELECT COUNT(*) as job_skills_with_valid_fks FROM job_skills js
JOIN postings p ON js.posting_id = p.posting_id
JOIN skill_aliases sa ON js.skill_id = sa.skill_id;

COMMIT;

\echo ''
\echo '✅ Migration 015 complete: All 8 tables reordered with xxx_id as first column'
\echo 'Tables: actors, capabilities, canonicals, skill_aliases, skill_hierarchy,'
\echo '        skills_pending_taxonomy, schema_documentation, postings'
