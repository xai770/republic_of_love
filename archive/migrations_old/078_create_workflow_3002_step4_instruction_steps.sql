-- Migration 078: Workflow 3002 Step 4 - Create Instruction Steps
-- Purpose: Create simple linear flow for taxonomy maintenance (no complex branching)
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

    -- Get instruction IDs
    SELECT instruction_id INTO v_instr_export 
    FROM instructions WHERE conversation_id = v_conv_export AND step_number = 1;
    
    SELECT instruction_id INTO v_instr_organize 
    FROM instructions WHERE conversation_id = v_conv_organize AND step_number = 1;
    
    SELECT instruction_id INTO v_instr_index 
    FROM instructions WHERE conversation_id = v_conv_index AND step_number = 1;

    -- Clean up any existing instruction steps
    DELETE FROM instruction_steps WHERE instruction_id IN (v_instr_export, v_instr_organize, v_instr_index);

    -- Step 1: After export, proceed to organize
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3002_export_to_organize',
        v_instr_export,
        'default',
        v_conv_organize,
        1
    );

    -- Step 2: After organize, proceed to index generation
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3002_organize_to_index',
        v_instr_organize,
        'default',
        v_conv_index,
        1
    );

    -- Step 3: After index generation, workflow complete
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority
    ) VALUES (
        'w3002_index_to_end',
        v_instr_index,
        'default',
        NULL,
        1
    );

    RAISE NOTICE 'Created instruction steps for linear flow: export -> organize -> index -> end';
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
WHERE c.canonical_name LIKE 'w3002_%'
ORDER BY c.canonical_name;
