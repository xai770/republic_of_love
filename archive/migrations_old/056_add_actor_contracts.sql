-- Migration 056: Add Actor Contract Columns
-- Purpose: Document input/output formats for actors to enable validation and tool chaining
-- Date: 2025-11-05
-- Related: Task #5 - Document actor input/output contracts

BEGIN;

-- Add contract columns to actors table
ALTER TABLE actors
ADD COLUMN IF NOT EXISTS input_format TEXT,
ADD COLUMN IF NOT EXISTS output_format TEXT,
ADD COLUMN IF NOT EXISTS example_call TEXT,
ADD COLUMN IF NOT EXISTS error_handling TEXT;

COMMENT ON COLUMN actors.input_format IS 'Expected input format: json_array, json_object, text, etc.';
COMMENT ON COLUMN actors.output_format IS 'Output format: json_array, json_object, text, etc.';
COMMENT ON COLUMN actors.example_call IS 'Example input for this actor (quick reference)';
COMMENT ON COLUMN actors.error_handling IS 'How this actor handles errors (returns error in JSON, raises exception, etc.)';

-- Populate contracts for existing delegate actors

-- 1. simple_skill_mapper
UPDATE actors
SET 
    input_format = 'json_array',
    output_format = 'json_array',
    example_call = '["Java", "Python", "Machine Learning", "data analysis"]',
    error_handling = 'Returns empty array [] if no matches found. Returns error object on JSON parse failure.'
WHERE actor_name = 'simple_skill_mapper';

-- 2. skill_saver
UPDATE actors
SET 
    input_format = 'json_object',
    output_format = 'json_object',
    example_call = '{"profile_id": 1, "skills": ["java", "python", "sql"]}',
    error_handling = 'Returns {"status": "error", "error": "message"} on failure'
WHERE actor_name = 'skill_saver';

-- 3. taxonomy_expander (if registered as actor in future)
UPDATE actors
SET 
    input_format = 'json_array',
    output_format = 'json_object',
    example_call = '["Spring Framework", "Docker", "CI/CD"]',
    error_handling = 'Returns object with per-skill status: {"skill": {"added": bool, "skill_id": int, "error": str}}'
WHERE actor_name = 'taxonomy_expander';

-- 4. AI model actors (LLM format)
UPDATE actors
SET 
    input_format = 'text',
    output_format = 'text',
    example_call = 'Prompt text with {placeholders} substituted',
    error_handling = 'Timeout returns partial response. Parse errors logged to stderr.'
WHERE actor_type = 'ai_model' AND input_format IS NULL;

-- 5. Script actors (various formats)
UPDATE actors
SET 
    input_format = 'varies',
    output_format = 'varies',
    example_call = 'See script documentation',
    error_handling = 'Script-specific error handling'
WHERE actor_type = 'script' AND input_format IS NULL;

COMMIT;

-- Verify changes
SELECT 
    actor_id,
    actor_name,
    actor_type,
    input_format,
    output_format,
    SUBSTRING(example_call, 1, 50) as example_snippet
FROM actors
WHERE input_format IS NOT NULL
ORDER BY 
    CASE actor_type
        WHEN 'script' THEN 1
        WHEN 'ai_model' THEN 2
        ELSE 3
    END,
    actor_name;
