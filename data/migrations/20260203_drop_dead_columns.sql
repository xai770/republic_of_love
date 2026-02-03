-- Migration: Drop Dead Columns
-- Date: 2026-02-03
-- Author: Schema audit cleanup
-- Status: EXECUTED 2026-02-03
-- 
-- This migration drops columns identified as dead by the schema audit:
-- - Fill rate < 5% AND not used in current pipeline
-- - Referenced only by archived/dead actors
--
-- PRESERVED: ihl_score (2,019 rows, historical value for DB postings)

-- =============================================================================
-- DROP DEPENDENT VIEWS
-- =============================================================================
-- These views referenced dead columns and must be dropped first

DROP VIEW IF EXISTS postings_for_matching CASCADE;
DROP VIEW IF EXISTS posting_pipeline_status CASCADE;

-- =============================================================================
-- POSTINGS TABLE - Drop 9 dead columns
-- =============================================================================

-- competency_keywords: Old LLM skill extraction, replaced by embeddings
ALTER TABLE postings DROP COLUMN IF EXISTS competency_keywords;

-- extracted_requirements: CPS (Competency Proof Stack), expensive LLM extraction
ALTER TABLE postings DROP COLUMN IF EXISTS extracted_requirements;

-- job_description_en: Translation for LLM processing, not needed with multilingual bge-m3
ALTER TABLE postings DROP COLUMN IF EXISTS job_description_en;

-- source_id: Foreign key to dead sources table
ALTER TABLE postings DROP COLUMN IF EXISTS source_id;

-- sect_decomposed_at: Timestamp for dead workflow step
ALTER TABLE postings DROP COLUMN IF EXISTS sect_decomposed_at;

-- employment_career_level: Never populated in current pipeline
ALTER TABLE postings DROP COLUMN IF EXISTS employment_career_level;

-- created_by_task_log_id: Unused task tracking
ALTER TABLE postings DROP COLUMN IF EXISTS created_by_task_log_id;

-- updated_by_task_log_id: Unused task tracking
ALTER TABLE postings DROP COLUMN IF EXISTS updated_by_task_log_id;

-- processing_notes: Debug field, never used
ALTER TABLE postings DROP COLUMN IF EXISTS processing_notes;

-- =============================================================================
-- PROFILES TABLE - Drop 1 dead column
-- =============================================================================

-- last_activity_date: Never populated
ALTER TABLE profiles DROP COLUMN IF EXISTS last_activity_date;

-- =============================================================================
-- RECREATE USEFUL VIEW (simplified)
-- =============================================================================

CREATE VIEW postings_for_matching AS
SELECT 
    posting_id,
    posting_name,
    enabled,
    job_description,
    job_title,
    location_city,
    location_country,
    ihl_score,
    external_job_id,
    external_url,
    posting_status,
    first_seen_at,
    last_seen_at,
    source_metadata,
    updated_at,
    extracted_summary,
    source,
    external_id,
    invalidated,
    processing_failures,
    source_language,
    domain_gate,
    COALESCE(extracted_summary, job_description) AS match_text
FROM postings
WHERE job_description IS NOT NULL 
  AND LENGTH(job_description) > 100
  AND invalidated = FALSE;

-- =============================================================================
-- Summary (EXECUTED)
-- =============================================================================
-- Dropped 2 views: postings_for_matching, posting_pipeline_status
-- Dropped 9 columns from postings
-- Dropped 1 column from profiles
-- Recreated 1 view: postings_for_matching (simplified)
-- Total: 10 columns removed
-- Schema: postings reduced from 42 to 33 columns
