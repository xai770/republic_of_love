-- Migration 083: Workflow 3003 Step 4 - Create Instruction Steps
-- Purpose: Define linear flow for Turing-native taxonomy maintenance
-- Created: 2025-11-10
-- Author: Arden

BEGIN;

DO $$
DECLARE
    v_conv_query INTEGER;
    v_conv_analyze INTEGER;
    v_conv_organize INTEGER;
    v_conv_write INTEGER;
    v_conv_index INTEGER;
    v_instr_query INTEGER;
    v_instr_analyze INTEGER;
    v_instr_organize INTEGER;
    v_instr_write INTEGER;
    v_instr_index INTEGER;
BEGIN
    -- Get conversation IDs
    SELECT conversation_id INTO v_conv_query FROM conversations WHERE canonical_name = 'w3003_c1_query';
    SELECT conversation_id INTO v_conv_analyze FROM conversations WHERE canonical_name = 'w3003_c2_analyze';
    SELECT conversation_id INTO v_conv_organize FROM conversations WHERE canonical_name = 'w3003_c3_organize';
    SELECT conversation_id INTO v_conv_write FROM conversations WHERE canonical_name = 'w3003_c4_write';
    SELECT conversation_id INTO v_conv_index FROM conversations WHERE canonical_name = 'w3003_c5_index';

    -- Get instruction IDs
    SELECT instruction_id INTO v_instr_query FROM instructions WHERE conversation_id = v_conv_query AND step_number = 1;
    SELECT instruction_id INTO v_instr_analyze FROM instructions WHERE conversation_id = v_conv_analyze AND step_number = 1;
    SELECT instruction_id INTO v_instr_organize FROM instructions WHERE conversation_id = v_conv_organize AND step_number = 1;
    SELECT instruction_id INTO v_instr_write FROM instructions WHERE conversation_id = v_conv_write AND step_number = 1;
    SELECT instruction_id INTO v_instr_index FROM instructions WHERE conversation_id = v_conv_index AND step_number = 1;

    -- Clean up any existing instruction steps
    DELETE FROM instruction_steps WHERE instruction_id IN (
        v_instr_query, v_instr_analyze, v_instr_organize, v_instr_write, v_instr_index
    );

    -- Step 1: After query, proceed to analyze
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_query_to_analyze',
        v_instr_query,
        'default',
        v_conv_analyze,
        1
    );

    -- Step 2: After analyze, proceed to organize
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_analyze_to_organize',
        v_instr_analyze,
        'default',
        v_conv_organize,
        1
    );

    -- Step 3: After organize, proceed to write files
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_organize_to_write',
        v_instr_organize,
        'default',
        v_conv_write,
        1
    );

    -- Step 4: After write, proceed to index generation
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_write_to_index',
        v_instr_write,
        'default',
        v_conv_index,
        1
    );

    -- Step 5: After index, workflow complete
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3003_index_to_end',
        v_instr_index,
        'default',
        NULL,
        1
    );

    RAISE NOTICE 'Created instruction steps for linear flow: query → analyze → organize → write → index → end';
END $$;

COMMIT;

-- Verify complete workflow structure
SELECT 
    i.instruction_id,
    i.instruction_name,
    c.canonical_name as current_conv,
    ist.branch_condition,
    c2.canonical_name as next_conv
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
LEFT JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
LEFT JOIN conversations c2 ON ist.next_conversation_id = c2.conversation_id
WHERE c.canonical_name LIKE 'w3003_%'
ORDER BY c.canonical_name;
