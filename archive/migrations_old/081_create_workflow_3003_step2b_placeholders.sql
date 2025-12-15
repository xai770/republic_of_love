-- Migration 081: Workflow 3003 Step 2b - Register Placeholders
-- Purpose: Register all placeholder variables for Turing-native taxonomy workflow
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

-- Output from Conversation 1: Skills query
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'skills_json',
    'dialogue_output',
    'JSON array of all skills from skill_hierarchy: [{skill_id, skill_name, parent_skill_id, description}]'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 2: Structure analysis
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'taxonomy_plan',
    'dialogue_output',
    'Proposed taxonomy structure: top-level categories and organization strategy'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 3: Organization mapping
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'folder_mapping',
    'dialogue_output',
    'JSON mapping of skills to folder paths: {skill_id: "folder/path/skill_name.md"}'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 4: File write results
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'write_result',
    'dialogue_output',
    'Results from writing files: number of files created, any errors'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Output from Conversation 5: Index generation
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'index_content',
    'dialogue_output',
    'Generated INDEX.md content with hierarchical navigation'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

-- Workflow trigger data
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    description
) VALUES (
    'taxonomy_trigger',
    'test_case_data',
    'Trigger reason for taxonomy maintenance (manual, scheduled, post-extraction, etc.)'
) ON CONFLICT (placeholder_name) DO UPDATE SET
    source_type = EXCLUDED.source_type,
    description = EXCLUDED.description;

COMMIT;

-- Verify
SELECT placeholder_name, source_type, LEFT(description, 60) as description_preview
FROM placeholder_definitions
WHERE placeholder_name IN (
    'skills_json', 'taxonomy_plan', 'folder_mapping', 
    'write_result', 'index_content', 'taxonomy_trigger'
)
ORDER BY placeholder_name;
