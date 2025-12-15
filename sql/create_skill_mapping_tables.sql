-- ============================================================================
-- Skill Mapping Infrastructure
-- ============================================================================
-- Purpose: Support hybrid skill extraction approach
--   1. Extract raw skills from job summaries
--   2. Map to taxonomy using synonyms
--   3. Track new skills for taxonomy expansion
--
-- Created: 2025-10-29
-- ============================================================================

-- ============================================================================
-- Table 1: skill_synonyms
-- Maps alternative names/spellings to canonical taxonomy skills
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_synonyms (
    synonym TEXT PRIMARY KEY,
    canonical_skill TEXT NOT NULL REFERENCES skill_aliases(skill),
    confidence FLOAT DEFAULT 1.0,
    source TEXT DEFAULT 'manual',  -- 'manual', 'llm', 'fuzzy_match'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_skill_synonyms_canonical 
    ON skill_synonyms(canonical_skill);

COMMENT ON TABLE skill_synonyms IS 
    'Maps alternative skill names to canonical taxonomy entries. Used for normalizing raw skill extractions.';

-- ============================================================================
-- Table 2: skills_pending_taxonomy
-- Tracks new skills found in job postings that need taxonomy classification
-- ============================================================================

CREATE TABLE IF NOT EXISTS skills_pending_taxonomy (
    raw_skill TEXT PRIMARY KEY,
    occurrences INT DEFAULT 1,
    suggested_domain TEXT,
    suggested_canonical TEXT,
    suggested_confidence FLOAT,
    review_status TEXT DEFAULT 'pending' 
        CHECK (review_status IN ('pending', 'approved', 'rejected', 'duplicate')),
    found_in_jobs TEXT[],
    llm_reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_skills_pending_status 
    ON skills_pending_taxonomy(review_status);

CREATE INDEX IF NOT EXISTS idx_skills_pending_occurrences 
    ON skills_pending_taxonomy(occurrences DESC);

COMMENT ON TABLE skills_pending_taxonomy IS 
    'Queue of new skills discovered in job postings that need human review for taxonomy inclusion.';

-- ============================================================================
-- Table 3: skill_extraction_log
-- Audit trail of skill extraction attempts
-- ============================================================================

CREATE TABLE IF NOT EXISTS skill_extraction_log (
    log_id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    extraction_attempt INT DEFAULT 1,
    raw_skills_found TEXT[],
    mapped_skills TEXT[],
    unmapped_skills TEXT[],
    extraction_method TEXT,  -- 'llm_qwen', 'llm_llama', 'hybrid'
    llm_model TEXT,
    processing_time_seconds FLOAT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_skill_extraction_job 
    ON skill_extraction_log(job_id);

CREATE INDEX IF NOT EXISTS idx_skill_extraction_created 
    ON skill_extraction_log(created_at DESC);

COMMENT ON TABLE skill_extraction_log IS 
    'Audit trail of all skill extraction attempts for debugging and improvement.';

-- ============================================================================
-- Seed Data: Common Synonyms
-- ============================================================================

-- Programming Languages
INSERT INTO skill_synonyms (synonym, canonical_skill, source, notes) VALUES
    ('python', 'Python', 'manual', 'Lowercase variant'),
    ('java', 'Java', 'manual', 'Lowercase variant'),
    ('javascript', 'JavaScript', 'manual', 'Lowercase variant'),
    ('js', 'JavaScript', 'manual', 'Common abbreviation'),
    ('typescript', 'TypeScript', 'manual', 'Lowercase variant'),
    ('ts', 'TypeScript', 'manual', 'Common abbreviation')
ON CONFLICT (synonym) DO NOTHING;

-- Data & Analytics
INSERT INTO skill_synonyms (synonym, canonical_skill, source, notes) VALUES
    ('sql', 'SQL', 'manual', 'Lowercase variant'),
    ('excel', 'Excel', 'manual', 'Lowercase variant'),
    ('powerbi', 'Power BI', 'manual', 'No space variant'),
    ('power_bi', 'Power BI', 'manual', 'Underscore variant'),
    ('tableau', 'Tableau', 'manual', 'Lowercase variant')
ON CONFLICT (synonym) DO NOTHING;

-- Cloud Platforms
INSERT INTO skill_synonyms (synonym, canonical_skill, source, notes) VALUES
    ('aws', 'AWS', 'manual', 'Lowercase variant'),
    ('amazon_web_services', 'AWS', 'manual', 'Full name'),
    ('azure', 'Azure', 'manual', 'Lowercase variant'),
    ('microsoft_azure', 'Azure', 'manual', 'Full name'),
    ('gcp', 'Google Cloud', 'manual', 'Common abbreviation'),
    ('google_cloud_platform', 'Google Cloud', 'manual', 'Full name')
ON CONFLICT (synonym) DO NOTHING;

-- Soft Skills
INSERT INTO skill_synonyms (synonym, canonical_skill, source, notes) VALUES
    ('leadership', 'Leadership', 'manual', 'Lowercase variant'),
    ('communication', 'Communication', 'manual', 'Lowercase variant'),
    ('teamwork', 'Teamwork', 'manual', 'Lowercase variant'),
    ('team_work', 'Teamwork', 'manual', 'Underscore variant')
ON CONFLICT (synonym) DO NOTHING;

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 
    'skill_synonyms' as table_name,
    COUNT(*) as record_count
FROM skill_synonyms
UNION ALL
SELECT 
    'skills_pending_taxonomy' as table_name,
    COUNT(*) as record_count
FROM skills_pending_taxonomy
UNION ALL
SELECT 
    'skill_extraction_log' as table_name,
    COUNT(*) as record_count
FROM skill_extraction_log;

SELECT 
    'Synonym examples:' as info,
    STRING_AGG(synonym || ' → ' || canonical_skill, ', ' ORDER BY synonym) as examples
FROM (
    SELECT synonym, canonical_skill 
    FROM skill_synonyms 
    LIMIT 5
) sample;
