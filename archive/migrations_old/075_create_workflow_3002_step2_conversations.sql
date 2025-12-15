-- Migration 075: Workflow 3002 Step 2 - Create Conversations
-- Purpose: Create conversations for taxonomy maintenance workflow
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_actor_exporter INTEGER;
    v_actor_organizer INTEGER;
    v_actor_indexer INTEGER;
    v_conv_export INTEGER;
    v_conv_organize INTEGER;
    v_conv_index INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_exporter FROM actors WHERE actor_name = 'taxonomy_exporter';
    SELECT actor_id INTO v_actor_organizer FROM actors WHERE actor_name = 'taxonomy_organizer';
    SELECT actor_id INTO v_actor_indexer FROM actors WHERE actor_name = 'taxonomy_indexer';

    -- Conversation 1: Export skills from database to file system
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3002_export_skills_to_filesystem',
        'w3002_c1_export',
        'Export all skills from skill_hierarchy table to skills_taxonomy/ as .md files',
        v_actor_exporter,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_export;

    -- Conversation 2: Organize taxonomy with infinite-depth AI
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3002_organize_taxonomy',
        'w3002_c2_organize',
        'Run multi-round infinite-depth taxonomy organization using recursive_organize_infinite.py',
        v_actor_organizer,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_organize;

    -- Conversation 3: Generate navigation index
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w3002_generate_index',
        'w3002_c3_index',
        'Generate INDEX.md with hierarchical navigation for skills_taxonomy/',
        v_actor_indexer,
        'single_actor',
        'isolated',
        true
    )
    RETURNING conversation_id INTO v_conv_index;

    -- Link conversations to workflow (defines execution order)
    DELETE FROM workflow_conversations WHERE workflow_id = 3002;
    
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        (3002, v_conv_export, 1, 'always', 'continue', 'stop', 1),
        (3002, v_conv_organize, 2, 'always', 'continue', 'stop', 1),
        (3002, v_conv_index, 3, 'always', 'continue', 'stop', 1);

    RAISE NOTICE 'Created conversations: export=%, organize=%, index=%', 
        v_conv_export, v_conv_organize, v_conv_index;
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
WHERE w.workflow_id = 3002
ORDER BY wc.execution_order;
