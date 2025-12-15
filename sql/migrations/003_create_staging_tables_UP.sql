-- Migration: 003_create_staging_tables_UP.sql
-- Description: Create staging tables (safety net for script actors)
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 2 (Complete Workflow)
-- Reference: docs/STAGING_TABLE_DESIGN.md

-- Postings Staging (fetcher output)
CREATE TABLE IF NOT EXISTS postings_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT NOT NULL REFERENCES interactions(interaction_id) ON DELETE CASCADE,
    
    -- Raw data from fetcher
    raw_data JSONB NOT NULL,
    
    -- Extracted fields (parsed from raw_data)
    source_website TEXT,
    job_title TEXT,
    company_name TEXT,
    location TEXT,
    job_description TEXT,
    posting_url TEXT UNIQUE,
    salary_range TEXT,
    posted_date DATE,
    
    -- Validation status
    validation_status TEXT DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'passed', 'failed', 'promoted')),
    validation_errors JSONB,
    validated_at TIMESTAMPTZ,
    validated_by_actor_id INT REFERENCES actors(actor_id),
    
    -- Promotion tracking
    promoted_to_posting_id INT REFERENCES postings(posting_id),
    promoted_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_postings_staging_interaction ON postings_staging(interaction_id);
CREATE INDEX idx_postings_staging_status ON postings_staging(validation_status);
CREATE INDEX idx_postings_staging_url ON postings_staging(posting_url);

COMMENT ON TABLE postings_staging IS 'Staging area for fetcher output - validated before promotion to postings table';

-- Profile Skills Staging (skill extractor output)
CREATE TABLE IF NOT EXISTS profile_skills_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT NOT NULL REFERENCES interactions(interaction_id) ON DELETE CASCADE,
    
    -- Raw data from AI model
    raw_data JSONB NOT NULL,
    
    -- Extracted fields
    profile_id INT,
    skill_name TEXT,
    proficiency_level TEXT,
    years_experience INT,
    context TEXT,
    
    -- Validation status
    validation_status TEXT DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'passed', 'failed', 'promoted')),
    validation_errors JSONB,
    validated_at TIMESTAMPTZ,
    validated_by_actor_id INT REFERENCES actors(actor_id),
    
    -- Promotion tracking
    promoted_to_skill_id INT,
    promoted_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profile_skills_staging_interaction ON profile_skills_staging(interaction_id);
CREATE INDEX idx_profile_skills_staging_status ON profile_skills_staging(validation_status);
CREATE INDEX idx_profile_skills_staging_profile ON profile_skills_staging(profile_id);

COMMENT ON TABLE profile_skills_staging IS 'Staging area for skill extractor output - validated before promotion to profile_skills';

-- Job Skills Staging (job skill extractor output)
CREATE TABLE IF NOT EXISTS job_skills_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT NOT NULL REFERENCES interactions(interaction_id) ON DELETE CASCADE,
    
    -- Raw data from AI model
    raw_data JSONB NOT NULL,
    
    -- Extracted fields
    posting_id INT,
    skill_name TEXT,
    skill_category TEXT,
    required_or_preferred TEXT CHECK (required_or_preferred IN ('required', 'preferred', 'nice_to_have')),
    importance_score DECIMAL(3,2),
    context TEXT,
    
    -- Validation status
    validation_status TEXT DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'passed', 'failed', 'promoted')),
    validation_errors JSONB,
    validated_at TIMESTAMPTZ,
    validated_by_actor_id INT REFERENCES actors(actor_id),
    
    -- Promotion tracking
    promoted_to_requirement_id INT,
    promoted_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_job_skills_staging_interaction ON job_skills_staging(interaction_id);
CREATE INDEX idx_job_skills_staging_status ON job_skills_staging(validation_status);
CREATE INDEX idx_job_skills_staging_posting ON job_skills_staging(posting_id);

COMMENT ON TABLE job_skills_staging IS 'Staging area for job skill extractor output - validated before promotion to job_requirements';

-- Skill Aliases Staging (skill mapper output)
CREATE TABLE IF NOT EXISTS skill_aliases_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT NOT NULL REFERENCES interactions(interaction_id) ON DELETE CASCADE,
    
    -- Raw data from AI model
    raw_data JSONB NOT NULL,
    
    -- Extracted fields
    skill_name TEXT,
    canonical_skill_name TEXT,
    confidence_score DECIMAL(3,2),
    reasoning TEXT,
    
    -- Validation status
    validation_status TEXT DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'passed', 'failed', 'promoted')),
    validation_errors JSONB,
    validated_at TIMESTAMPTZ,
    validated_by_actor_id INT REFERENCES actors(actor_id),
    
    -- Promotion tracking
    promoted_to_alias_id INT,
    promoted_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skill_aliases_staging_interaction ON skill_aliases_staging(interaction_id);
CREATE INDEX idx_skill_aliases_staging_status ON skill_aliases_staging(validation_status);
CREATE INDEX idx_skill_aliases_staging_skill ON skill_aliases_staging(skill_name);

COMMENT ON TABLE skill_aliases_staging IS 'Staging area for skill mapper output - validated before promotion to skill_aliases';

-- Updated_at triggers for all staging tables
CREATE OR REPLACE FUNCTION update_staging_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER postings_staging_updated_at_trigger
    BEFORE UPDATE ON postings_staging
    FOR EACH ROW
    EXECUTE FUNCTION update_staging_updated_at();

CREATE TRIGGER profile_skills_staging_updated_at_trigger
    BEFORE UPDATE ON profile_skills_staging
    FOR EACH ROW
    EXECUTE FUNCTION update_staging_updated_at();

CREATE TRIGGER job_skills_staging_updated_at_trigger
    BEFORE UPDATE ON job_skills_staging
    FOR EACH ROW
    EXECUTE FUNCTION update_staging_updated_at();

CREATE TRIGGER skill_aliases_staging_updated_at_trigger
    BEFORE UPDATE ON skill_aliases_staging
    FOR EACH ROW
    EXECUTE FUNCTION update_staging_updated_at();
