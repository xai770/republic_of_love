-- Migration 077: Workflow 3002 Step 3 - Create Instructions
-- Purpose: Create instruction prompts for taxonomy maintenance conversations
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_conv_export INTEGER;
    v_conv_organize INTEGER;
    v_conv_index INTEGER;
    v_instr_export INTEGER;
    v_instr_organize INTEGER;
    v_instr_index INTEGER;
BEGIN
    -- Get conversation IDs
    SELECT conversation_id INTO v_conv_export 
    FROM conversations WHERE canonical_name = 'w3002_c1_export';
    
    SELECT conversation_id INTO v_conv_organize 
    FROM conversations WHERE canonical_name = 'w3002_c2_organize';
    
    SELECT conversation_id INTO v_conv_index 
    FROM conversations WHERE canonical_name = 'w3002_c3_index';

    -- Instruction 1: Export skills from database
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_export,
        'Export Skills to Filesystem',
        1,
        'Execute tools/rebuild_skills_taxonomy.py to export all skills from skill_hierarchy table to skills_taxonomy/ directory.

This script will:
1. Connect to the database
2. Query all skills from skill_hierarchy table
3. Create .md files in skills_taxonomy/ directory
4. Preserve skill metadata and relationships

Output the result: number of skills exported, files created, any errors encountered.',
        600,
        true
    )
    RETURNING instruction_id INTO v_instr_export;

    -- Instruction 2: Organize taxonomy with infinite-depth AI
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_organize,
        'Organize Taxonomy with AI',
        1,
        'Execute tools/multi_round_organize.py to organize the skills_taxonomy/ directory using infinite-depth AI-driven organization.

This script will:
1. Run recursive_organize_infinite.py in multiple rounds
2. Use AI to analyze skill relationships and create semantic hierarchy
3. Organize into content-driven folder depth (no arbitrary limits)
4. Handle large taxonomies that exceed AI context windows

Output the result: number of rounds completed, final folder structure depth, skills organized, any issues.',
        1800,
        true
    )
    RETURNING instruction_id INTO v_instr_organize;

    -- Instruction 3: Generate navigation index
    INSERT INTO instructions (
        conversation_id,
        instruction_name,
        step_number,
        prompt_template,
        timeout_seconds,
        enabled
    ) VALUES (
        v_conv_index,
        'Generate Navigation Index',
        1,
        'Execute tools/generate_taxonomy_index.py to create INDEX.md with hierarchical navigation for skills_taxonomy/.

This script will:
1. Traverse the entire skills_taxonomy/ directory structure
2. Build hierarchical table of contents with proper indentation
3. Create markdown links to all skill files
4. Generate INDEX.md at the root of skills_taxonomy/

Output the result: INDEX.md created, total folders/files indexed, navigation structure depth.',
        300,
        true
    )
    RETURNING instruction_id INTO v_instr_index;

    RAISE NOTICE 'Created instructions: export=%, organize=%, index=%', 
        v_instr_export, v_instr_organize, v_instr_index;
END $$;

COMMIT;

-- Verify
SELECT 
    i.instruction_id,
    i.instruction_name,
    c.canonical_name,
    a.actor_name,
    LEFT(i.prompt_template, 80) as prompt_preview
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE c.canonical_name LIKE 'w3002_%'
ORDER BY c.canonical_name;
