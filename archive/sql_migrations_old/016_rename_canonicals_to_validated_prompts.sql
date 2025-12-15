-- Migration 016: Rename canonicals to validated_prompts
-- Date: 2025-10-31
-- Purpose: Rename canonicals table to better reflect its purpose as a scrapbook 
--          of validated prompts from manual testing (OWUI/llm_chat.py)

BEGIN;

-- Rename the table
ALTER TABLE canonicals RENAME TO validated_prompts;

-- Rename the primary key sequence
ALTER SEQUENCE canonicals_canonical_id_seq RENAME TO validated_prompts_validated_prompt_id_seq;

-- Rename the primary key column
ALTER TABLE validated_prompts RENAME COLUMN canonical_id TO validated_prompt_id;

-- Rename the name column for consistency
ALTER TABLE validated_prompts RENAME COLUMN canonical_name TO validated_prompt_name;

-- Rename constraints
ALTER TABLE validated_prompts RENAME CONSTRAINT canonicals_pkey TO validated_prompts_pkey;
ALTER TABLE validated_prompts RENAME CONSTRAINT canonicals_canonical_name_unique TO validated_prompts_validated_prompt_name_unique;
ALTER TABLE validated_prompts RENAME CONSTRAINT canonicals_capability_id_fkey TO validated_prompts_capability_id_fkey;

-- Rename indexes
ALTER INDEX idx_canonicals_enabled RENAME TO idx_validated_prompts_enabled;
ALTER INDEX idx_canonicals_facet RENAME TO idx_validated_prompts_facet;

-- Rename history table
ALTER TABLE canonicals_history RENAME TO validated_prompts_history;

-- Rename history table columns (uses canonical_code not canonical_id)
ALTER TABLE validated_prompts_history RENAME COLUMN canonical_code TO validated_prompt_code;
ALTER TABLE validated_prompts_history RENAME COLUMN facet_id TO facet_name;

-- Rename the history trigger
DROP TRIGGER IF EXISTS canonicals_history_trigger ON validated_prompts;
CREATE TRIGGER validated_prompts_history_trigger
    BEFORE UPDATE ON validated_prompts
    FOR EACH ROW
    EXECUTE FUNCTION archive_canonicals();  -- Function name unchanged for now

-- Rename the archive function (remove parentheses)
ALTER FUNCTION archive_canonicals RENAME TO archive_validated_prompts;

-- Update the trigger to use new function name
DROP TRIGGER validated_prompts_history_trigger ON validated_prompts;
CREATE TRIGGER validated_prompts_history_trigger
    BEFORE UPDATE ON validated_prompts
    FOR EACH ROW
    EXECUTE FUNCTION archive_validated_prompts();

-- Update foreign key in sessions table
ALTER TABLE sessions RENAME COLUMN canonical_id TO validated_prompt_id;
ALTER TABLE sessions RENAME CONSTRAINT sessions_canonical_id_fkey TO sessions_validated_prompt_id_fkey;

-- Update table comment
COMMENT ON TABLE validated_prompts IS 
'Validated prompt-response pairs from manual testing (62 entries). 
Scrapbook of working prompts developed through OWUI or llm_chat.py interactions.
Each entry is a proven prompt→response pattern linked to a capability/facet.
Use these as templates when building recipes to avoid reinventing solutions.
Standardized 2025-10-30, renamed 2025-10-31.
Pattern: validated_prompt_id (INTEGER PK) + validated_prompt_name (TEXT UNIQUE).';

COMMENT ON COLUMN validated_prompts.validated_prompt_id IS 
'Primary key - unique identifier for this validated prompt';

COMMENT ON COLUMN validated_prompts.validated_prompt_name IS 
'Unique name for this validated prompt (e.g., ce_clean_extract, dynatax_skills_categorizer)';

COMMENT ON COLUMN validated_prompts.facet_name IS 
'Capability/facet this prompt implements (legacy field, may overlap with capability_name)';

COMMENT ON COLUMN validated_prompts.capability_id IS 
'Foreign key to capabilities table - links this prompt to its cognitive capability';

COMMENT ON COLUMN validated_prompts.capability_description IS 
'Description of what this validated prompt demonstrates or achieves';

COMMENT ON COLUMN validated_prompts.prompt IS 
'The validated prompt text - proven to work through manual testing';

COMMENT ON COLUMN validated_prompts.response IS 
'Expected/reference response format - what good output looks like';

COMMENT ON COLUMN validated_prompts.review_notes IS 
'Notes from manual testing sessions, learnings, edge cases discovered';

-- Verification
SELECT 
    'validated_prompts' as new_table_name,
    COUNT(*) as row_count,
    'Rename complete' as status
FROM validated_prompts;

COMMIT;
