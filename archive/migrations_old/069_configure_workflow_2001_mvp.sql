-- Migration 069: Configure Workflow 2001 - TY Job Pipeline (Minimal MVP)
-- Creates conversations and links them to Workflow 2001
--
-- Design Philosophy: Start minimal, expand iteratively
-- Phase 1 MVP: Fetch → Skills → IHL → Save
--
-- Author: Arden (GitHub Copilot)
-- Date: 2025-11-09

BEGIN;

-- ============================================================================
-- STEP 1: Update Workflow Metadata
-- ============================================================================

UPDATE workflows
SET 
    workflow_name = 'TY Job Pipeline',
    workflow_description = 'Complete job ingestion and processing pipeline: Fetch jobs from API → Extract skills → Calculate IHL score → Map to taxonomy → Save to database',
    updated_at = CURRENT_TIMESTAMP
WHERE workflow_id = 2001;

-- ============================================================================
-- STEP 2: Create Conversations (if they don't exist)
-- ============================================================================

-- Conversation: Fetch Jobs from API
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id,
    conversation_description
)
SELECT 
    'Fetch Jobs from Deutsche Bank API',
    'fetch_db_jobs',
    56,
    'Fetches job postings from Deutsche Bank API, checks for duplicates, parses locations, stores in postings table'
WHERE NOT EXISTS (
    SELECT 1 FROM conversations WHERE canonical_name = 'fetch_db_jobs'
);

-- Conversation: Save Job Skills to Database
INSERT INTO conversations (
    conversation_name,
    canonical_name,
    actor_id,
    conversation_description
)
SELECT
    'Save Job Skills to Database',
    'save_job_skills',
    58,
    'Saves extracted skills to job_skills table with taxonomy linking'
WHERE NOT EXISTS (
    SELECT 1 FROM conversations WHERE canonical_name = 'save_job_skills'
);

-- ============================================================================
-- STEP 3: Create Instructions for New Conversations
-- ============================================================================

-- Instruction: Fetch Jobs
-- Input: JSON with user_id, max_jobs, source_id
-- Output: JSON with stats (fetched, new, duplicate, error)
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    prompt_template,
    timeout_seconds,
    is_terminal
) SELECT
    'Fetch Jobs from API',
    conversation_id,
    1,
    $PROMPT${
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1
}$PROMPT$,
    300,  -- 5 minutes for API fetching
    false  -- Not terminal, continue to skills extraction
FROM conversations WHERE canonical_name = 'fetch_db_jobs'
ON CONFLICT DO NOTHING;

-- Instruction: Save Job Skills
-- Input: posting_id + skills array from session_r10_output
-- Output: JSON with skill_ids saved
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    prompt_template,
    timeout_seconds,
    is_terminal
) SELECT
    'Save Job Skills to Database',
    conversation_id,
    1,
    $PROMPT${
  "posting_id": "{posting_id}",
  "skills": {session_r10_output},
  "taxonomy_mapping": {session_r30_output}
}$PROMPT$,
    60,  -- 1 minute for database operations
    true  -- Terminal step
FROM conversations WHERE canonical_name = 'save_job_skills'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 4: Link Conversations to Workflow 2001
-- ============================================================================

-- Current state: Steps 10, 20, 30 exist (skills, IHL, taxonomy)
-- Adding: Step 5 (fetch) and Step 40 (save)

-- Step 5: Fetch Jobs (BEFORE skills extraction)
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts
) SELECT
    2001,
    conversation_id,
    5,  -- BEFORE existing step 10
    'always',
    'continue',
    'stop',  -- If fetch fails, stop entire workflow
    1
FROM conversations WHERE canonical_name = 'fetch_db_jobs'
ON CONFLICT (workflow_id, execution_order) DO UPDATE SET
    conversation_id = EXCLUDED.conversation_id;

-- Step 40: Save Skills (AFTER taxonomy mapping)
INSERT INTO workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order,
    execute_condition,
    on_success_action,
    on_failure_action,
    max_retry_attempts
) SELECT
    2001,
    conversation_id,
    40,  -- AFTER taxonomy mapping (step 30)
    'always',
    'continue',
    'stop',  -- If save fails, stop
    1
FROM conversations WHERE canonical_name = 'save_job_skills'
ON CONFLICT (workflow_id, execution_order) DO UPDATE SET
    conversation_id = EXCLUDED.conversation_id;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

\echo ''
\echo '=== Workflow 2001: TY Job Pipeline (Complete Structure) ==='
SELECT 
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    a.actor_name,
    a.actor_type,
    i.instruction_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN instructions i ON c.conversation_id = i.conversation_id
WHERE wc.workflow_id = 2001
ORDER BY wc.execution_order;

\echo ''
\echo '=== Workflow Summary ==='
SELECT 
    workflow_id,
    workflow_name,
    workflow_description
FROM workflows
WHERE workflow_id = 2001;

