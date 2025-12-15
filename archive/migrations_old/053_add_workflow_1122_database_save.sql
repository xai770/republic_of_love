-- Migration 053: Add Database Save Step to Workflow 1122
-- ==========================================================
-- Purpose: Add 4th conversation to save extracted skills to database
-- Flow: Summary → Extract → Map → **SAVE TO DATABASE**

BEGIN;

-- Step 1: Create conversation for database save
INSERT INTO conversations (
    conversation_name,
    conversation_description,
    actor_id,
    enabled
)
VALUES (
    'r2_save_skills_to_database',
    'Save taxonomy-mapped skills to profile_skills table',
    49,  -- skill_saver script actor (actor_id=49)
    TRUE
)
RETURNING conversation_id;

-- Get the conversation_id (will be around 3356+)
-- For this migration, we'll use a variable approach

DO $$
DECLARE
    new_conv_id INTEGER;
    new_inst_id INTEGER;
BEGIN
    -- Get the new conversation_id
    SELECT conversation_id INTO new_conv_id
    FROM conversations
    WHERE conversation_name = 'r2_save_skills_to_database';
    
    -- Step 2: Add conversation to workflow
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        enabled
    )
    VALUES (
        1122,
        new_conv_id,
        4,  -- After taxonomy mapping
        TRUE
    );
    
    -- Step 3: Create instruction for this conversation
    INSERT INTO instructions (
        instruction_name,
        conversation_id,
        step_number,
        step_description,
        prompt_template,
        timeout_seconds,
        is_terminal,
        delegate_actor_id,
        enabled
    )
    VALUES (
        'r2_save_skills_instruction',
        new_conv_id,
        1,
        'Save taxonomy-mapped skills to profile_skills table',
        '{
  "profile_id": {variations_profile_id},
  "taxonomy_skills": {session_3_output},
  "raw_skills": {session_2_output}
}',
        30,  -- 30 second timeout (database write is fast)
        TRUE,  -- This is the terminal instruction
        NULL,  -- Will use conversation actor (profile_importer)
        TRUE
    )
    RETURNING instruction_id INTO new_inst_id;
    
    -- Step 4: Update instruction 3351 (r2_map_to_taxonomy) to route to this new conversation
    -- First, remove its terminal flag
    UPDATE instructions
    SET is_terminal = FALSE
    WHERE instruction_id = 3351;
    
    -- Add routing from taxonomy mapping → database save
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        branch_condition,
        next_conversation_id,
        branch_priority,
        branch_description,
        enabled
    )
    VALUES (
        'w1122_taxonomy_to_save',
        3351,  -- From: r2_map_to_taxonomy
        'DEFAULT',
        new_conv_id,  -- To: r2_save_skills_to_database
        10,
        'After taxonomy mapping, save skills to database',
        TRUE
    );
    
    RAISE NOTICE 'Created conversation_id: %, instruction_id: %', new_conv_id, new_inst_id;
END $$;

-- Verification
SELECT 'Migration 053 applied successfully!' as status;

-- Show the complete workflow flow
SELECT 
    wc.execution_order,
    c.conversation_name,
    c.actor_id,
    a.actor_name as actor,
    i.instruction_id,
    i.is_terminal,
    istep.branch_condition,
    istep.next_conversation_id,
    nc.conversation_name as next_conversation
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN instructions i ON i.conversation_id = c.conversation_id
LEFT JOIN instruction_steps istep ON i.instruction_id = istep.instruction_id
LEFT JOIN conversations nc ON istep.next_conversation_id = nc.conversation_id
WHERE wc.workflow_id = 1122
ORDER BY wc.execution_order, i.step_number;

COMMIT;
