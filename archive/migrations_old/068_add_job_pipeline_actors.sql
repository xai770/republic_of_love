-- Migration 068: Add Script Actors for Job Pipeline
-- Creates actors for job fetching, web search, and database operations
--
-- Author: Arden (GitHub Copilot)
-- Date: 2025-11-09

BEGIN;

-- ============================================================================
-- SCRIPT ACTORS FOR WORKFLOW 2001
-- ============================================================================

-- Actor 1: Job Fetcher (from Deutsche Bank API)
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    execution_config,
    url,
    enabled
) VALUES (
    'db_job_fetcher',
    'script',
    'python_script',
    'core/turing_job_fetcher.py',
    '{"mode": "stdin_json", "output_format": "json"}',
    'local',  -- Script actors run locally, not via URL
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    updated_at = CURRENT_TIMESTAMP;

-- Actor 2: Web Search for Missing Descriptions
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    execution_config,
    url,
    enabled
) VALUES (
    'web_description_search',
    'script',
    'python_script',
    'tools/fetch_missing_descriptions.py',
    '{"search_engine": "duckduckgo", "max_results": 3}',
    'local',
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    updated_at = CURRENT_TIMESTAMP;

-- Actor 3: Job Skills Saver (saves to job_skills table, not profile_skills)
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    execution_config,
    url,
    enabled
) VALUES (
    'job_skills_saver',
    'script',
    'python_script',
    'tools/save_job_skills.py',
    '{"target_table": "job_skills", "link_taxonomy": true}',
    'local',
    true
) ON CONFLICT (actor_name) DO UPDATE SET
    execution_type = EXCLUDED.execution_type,
    execution_path = EXCLUDED.execution_path,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Verification
\echo ''
\echo '=== Created Script Actors for Workflow 2001 ==='
SELECT 
    actor_id,
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    enabled
FROM actors
WHERE actor_name IN ('db_job_fetcher', 'web_description_search', 'job_skills_saver')
ORDER BY actor_id;

