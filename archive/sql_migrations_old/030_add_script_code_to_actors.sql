-- Migration 030: Add script_code column to actors table
-- Date: 2025-10-31
-- Purpose: Store script source code in database for script actors
--          Prevents workflow breakage from deleted/renamed script files

-- This migration adds script_code column because:
-- 1. Current design: actors.url points to file path (fragile!)
-- 2. Problem: Delete/rename script file → workflow breaks silently
-- 3. Solution: Store actual code in database (actors.script_code)
-- 4. Benefit: Version control via actors_history, audit trail, can't lose scripts
-- 5. Fallback: Keep execution_path for development convenience

-- Strategy:
-- - script_code = source of truth for production
-- - execution_path = optional fallback for development
-- - Runner checks script_code first, falls back to file if needed

BEGIN;

-- Step 1: Add script_code column (TEXT, nullable)
ALTER TABLE actors ADD COLUMN script_code TEXT;

-- Step 2: Add language column to track script language
ALTER TABLE actors ADD COLUMN script_language TEXT;

-- Step 3: Add script_version for tracking
ALTER TABLE actors ADD COLUMN script_version INTEGER DEFAULT 1;

-- Step 4: Update column comments
COMMENT ON COLUMN actors.script_code IS 'Source code for script actors (Python, Bash, etc.). When present, this is the authoritative code to execute. Prevents workflow breakage from deleted/renamed script files. NULL for AI/human actors.';

COMMENT ON COLUMN actors.script_language IS 'Programming language for script_code: python, bash, javascript, etc. NULL for AI/human actors.';

COMMENT ON COLUMN actors.script_version IS 'Version number of script_code. Incremented each time script is updated. Enables tracking which version ran in historical executions.';

COMMENT ON COLUMN actors.execution_path IS 'DEPRECATED: File path to script (e.g., scripts/my_script.py). Kept for development convenience but script_code is source of truth for production. Runner checks script_code first, falls back to this if script_code is NULL.';

COMMENT ON COLUMN actors.url IS 'DEPRECATED: Legacy URL/path field. Use script_code for scripts, execution_config for API endpoints.';

-- Step 5: Update table comment
COMMENT ON TABLE actors IS 'Computational units in the Turing execution engine (execution layer).
Actors are the "processors" that execute instructions in workflows - can be AI models, scripts, or humans.
Key to Turing completeness: heterogeneous computation mixing neural (AI), symbolic (scripts), and human judgment.

Actor Types:
- human (execution_type=human_input): Human actors who execute workflow steps
- ai_model (execution_type=ollama_api): AI/LLM models that process data
- script (execution_type=python_script/bash_script): Automated scripts
- machine_actor (execution_type=http_api): External API services

Script Execution (NEW - Migration 030):
- script_code: Source code stored in database (source of truth for production)
- script_language: python, bash, javascript, etc.
- script_version: Incremented on each update for audit trail
- execution_path: DEPRECATED - fallback for development only
- Runner priority: script_code → execution_path → ERROR

Actor vs User Distinction:
- actors table = EXECUTION LAYER: "Who executes this workflow step?"
- users table = APPLICATION LAYER: "Who owns this profile/job search?"
- Some actors ARE users (user_id FK): Job seekers responding to reports, providing feedback
- Not all actors are users: AI models and scripts will never authenticate
- Not all users are actors: Some platform users may never participate in workflow execution

Example: Job seeker Jane (user_id=42) receives a cover letter. When she replies, she acts as 
an actor (actor_id=123, user_id=42). The AI model that generated the cover letter (actor_id=5) 
has no user_id because it''s not an authenticated platform user.

Column order standardized 2025-10-31 (migration 015).
Pattern: actor_id (INTEGER PK) + actor_name (TEXT UNIQUE).
User linking added 2025-10-31 (migration 023).
Script code storage added 2025-10-31 (migration 030).';

COMMIT;

-- Next Steps (Manual):
-- 1. For each script actor, load script file and INSERT INTO actors.script_code
-- 2. Update by_recipe_runner.py to check script_code before execution_path
-- 3. Gradually migrate all scripts to database
-- 4. Eventually deprecate execution_path entirely

-- Example migration of a script:
-- UPDATE actors 
-- SET script_code = 'import sys\nprint("Hello from DB!")\n',
--     script_language = 'python',
--     script_version = 1
-- WHERE actor_name = 'example_script';

-- Verification:
-- SELECT actor_id, actor_name, script_language, script_version, 
--        LENGTH(script_code) as code_length 
-- FROM actors WHERE actor_type = 'script';
