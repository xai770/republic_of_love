-- Migration 080: Workflow 3003 Step 2 - Create Conversations (Turing Native)
-- Purpose: Create conversations for Turing-native taxonomy maintenance
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_actor_qwen INTEGER;
    v_actor_gemma3_4b INTEGER;
    v_actor_file_writer INTEGER;
    v_conv_query_skills INTEGER;
    v_conv_analyze_structure INTEGER;
    v_conv_organize_skills INTEGER;
    v_conv_write_files INTEGER;
    v_conv_generate_index INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b';
    SELECT actor_id INTO v_actor_gemma3_4b FROM actors WHERE actor_name = 'gemma3:4b';
    
    -- Check if we have a file_writer script actor, if not we'll create it
    SELECT actor_id INTO v_actor_file_writer FROM actors WHERE actor_name = 'file_writer';
    
    IF v_actor_file_writer IS NULL THEN
        INSERT INTO actors (actor_name, actor_type, execution_type, url, enabled)
        VALUES ('file_writer', 'script', 'python_script', 'local', true)
        RETURNING actor_id INTO v_actor_file_writer;
    END IF;

    -- Conversation 1: Query skills from database
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_query_skills_from_db',
        'w3003_c1_query',
        'Query all skills from skill_hierarchy table. Output as structured JSON.',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_query_skills;

    -- Conversation 2: Analyze current taxonomy structure
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_analyze_taxonomy_structure',
        'w3003_c2_analyze',
        'Analyze skills and propose semantic organization structure.',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_analyze_structure;

    -- Conversation 3: Organize skills semantically
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_organize_skills_semantically',
        'w3003_c3_organize',
        'Group skills into semantic categories with folder structure. Output JSON mapping.',
        v_actor_gemma3_4b,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_organize_skills;

    -- Conversation 4: Write skills to file system
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_write_skills_to_filesystem',
        'w3003_c4_write',
        'Take skill data and folder structure, write .md files to skills_taxonomy/',
        v_actor_file_writer,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_write_files;

    -- Conversation 5: Generate hierarchical index
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3003_generate_hierarchical_index',
        'w3003_c5_index',
        'Generate INDEX.md with hierarchical navigation based on folder structure.',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_generate_index;

    -- Link conversations to workflow (defines execution order)
    DELETE FROM workflow_conversations WHERE workflow_id = 3003;
    
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        (3003, v_conv_query_skills, 1, 'always', 'continue', 'stop', 2),
        (3003, v_conv_analyze_structure, 2, 'always', 'continue', 'stop', 2),
        (3003, v_conv_organize_skills, 3, 'always', 'continue', 'stop', 2),
        (3003, v_conv_write_files, 4, 'always', 'continue', 'stop', 1),
        (3003, v_conv_generate_index, 5, 'always', 'continue', 'stop', 1);

    RAISE NOTICE 'Created conversations: query=%, analyze=%, organize=%, write=%, index=%', 
        v_conv_query_skills, v_conv_analyze_structure, v_conv_organize_skills, 
        v_conv_write_files, v_conv_generate_index;
END $$;

COMMIT;

-- Verify
SELECT 
    w.workflow_id,
    w.workflow_name,
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    c.canonical_name,
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 3003
ORDER BY wc.execution_order;
