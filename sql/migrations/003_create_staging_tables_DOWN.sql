-- Migration: 003_create_staging_tables_DOWN.sql
-- Description: Rollback staging tables creation
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 2 (Complete Workflow)

-- Drop triggers
DROP TRIGGER IF EXISTS skill_aliases_staging_updated_at_trigger ON skill_aliases_staging;
DROP TRIGGER IF EXISTS job_skills_staging_updated_at_trigger ON job_skills_staging;
DROP TRIGGER IF EXISTS profile_skills_staging_updated_at_trigger ON profile_skills_staging;
DROP TRIGGER IF EXISTS postings_staging_updated_at_trigger ON postings_staging;
DROP FUNCTION IF EXISTS update_staging_updated_at();

-- Drop skill_aliases_staging
DROP INDEX IF EXISTS idx_skill_aliases_staging_skill;
DROP INDEX IF EXISTS idx_skill_aliases_staging_status;
DROP INDEX IF EXISTS idx_skill_aliases_staging_interaction;
DROP TABLE IF EXISTS skill_aliases_staging CASCADE;

-- Drop job_skills_staging
DROP INDEX IF EXISTS idx_job_skills_staging_posting;
DROP INDEX IF EXISTS idx_job_skills_staging_status;
DROP INDEX IF EXISTS idx_job_skills_staging_interaction;
DROP TABLE IF EXISTS job_skills_staging CASCADE;

-- Drop profile_skills_staging
DROP INDEX IF EXISTS idx_profile_skills_staging_profile;
DROP INDEX IF EXISTS idx_profile_skills_staging_status;
DROP INDEX IF EXISTS idx_profile_skills_staging_interaction;
DROP TABLE IF EXISTS profile_skills_staging CASCADE;

-- Drop postings_staging
DROP INDEX IF EXISTS idx_postings_staging_url;
DROP INDEX IF EXISTS idx_postings_staging_status;
DROP INDEX IF EXISTS idx_postings_staging_interaction;
DROP TABLE IF EXISTS postings_staging CASCADE;
