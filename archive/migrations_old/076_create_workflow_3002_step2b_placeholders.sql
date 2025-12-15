-- Migration 076: Workflow 3002 Step 2b - Register Placeholders
-- Purpose: Register all placeholder variables used in Workflow 3002
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

-- Input placeholder: Workflow trigger data
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'trigger_reason',
    'test_case_data',
    'Reason for triggering taxonomy maintenance (manual, scheduled, after_N_skills, etc.)'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 1: Export
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'export_result',
    'dialogue_output',
    'Result from taxonomy export: number of files created, any errors'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 2: Organize
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'organize_result',
    'dialogue_output',
    'Result from taxonomy organization: rounds completed, folder structure, any issues'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 3: Index generation
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'index_result',
    'dialogue_output',
    'Result from index generation: INDEX.md created, navigation structure'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

COMMIT;

-- Verify
SELECT placeholder_name, source_type, description
FROM placeholder_definitions
WHERE placeholder_name IN ('trigger_reason', 'export_result', 'organize_result', 'index_result')
ORDER BY placeholder_name;
