-- Migration 087: Restructure Workflow 1124 as 3 Separate Conversations
-- Date: 2025-11-10
-- Purpose: Split single multi_actor_dialogue into 3 conversations for compiler compatibility
-- Before: 1 conversation with 3 instructions
-- After: 3 conversations with 1 instruction each (Analyst → Skeptic → HR Expert)

BEGIN;

DO $$
DECLARE
    v_actor_qwen INTEGER;
    v_actor_gemma INTEGER;
    v_conv_analyst INTEGER;
    v_conv_skeptic INTEGER;
    v_conv_expert INTEGER;
    v_inst_analyst INTEGER;
    v_inst_skeptic INTEGER;
    v_inst_expert INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b';
    SELECT actor_id INTO v_actor_gemma FROM actors WHERE actor_name = 'gemma2:latest';
    
    -- Create Conversation 1: Analyst
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'IHL Analyst - Find Red Flags',
        'w1124_c1_analyst',
        'Actor 1: Analyze job posting to identify suspicious patterns and red flags',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    ) RETURNING conversation_id INTO v_conv_analyst;
    
    -- Create Conversation 2: Skeptic
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'IHL Skeptic - Challenge Analyst',
        'w1124_c2_skeptic',
        'Actor 2: Challenge the Analyst findings, argue job is legitimate',
        v_actor_gemma,
        'single_actor',
        'inherit_previous',
        true
    ) RETURNING conversation_id INTO v_conv_skeptic;
    
    -- Create Conversation 3: HR Expert
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'IHL HR Expert - Final Verdict',
        'w1124_c3_expert',
        'Actor 3: Review both arguments and make balanced final decision',
        v_actor_qwen,
        'single_actor',
        'inherit_previous',
        true
    ) RETURNING conversation_id INTO v_conv_expert;
    
    -- Move instructions to new conversations
    -- Analyst (instruction_id 3387)
    UPDATE instructions 
    SET conversation_id = v_conv_analyst
    WHERE instruction_id = 3387;
    
    -- Skeptic (instruction_id 3388)
    UPDATE instructions 
    SET conversation_id = v_conv_skeptic
    WHERE instruction_id = 3388;
    
    -- HR Expert (instruction_id 3389)
    UPDATE instructions 
    SET conversation_id = v_conv_expert
    WHERE instruction_id = 3389;
    
    -- Update workflow_conversations
    -- First delete conversation_runs that reference the old step_id
    DELETE FROM conversation_runs 
    WHERE workflow_step_id IN (
        SELECT step_id FROM workflow_conversations WHERE workflow_id = 1124
    );
    
    DELETE FROM workflow_conversations WHERE workflow_id = 1124;
    
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,
        on_success_action,
        on_failure_action,
        max_retry_attempts
    ) VALUES 
        (1124, v_conv_analyst, 1, 'always', 'continue', 'stop', 1),
        (1124, v_conv_skeptic, 2, 'always', 'continue', 'stop', 1),
        (1124, v_conv_expert, 3, 'always', 'continue', 'stop', 1);
    
    -- Disable old conversation
    UPDATE conversations SET enabled = false WHERE conversation_id = 9125;
    
    RAISE NOTICE 'Created 3 conversations: analyst=%, skeptic=%, expert=%', v_conv_analyst, v_conv_skeptic, v_conv_expert;
END $$;

COMMIT;

-- Verify
SELECT 
    wc.execution_order,
    c.conversation_id,
    c.canonical_name,
    c.conversation_description,
    a.actor_name,
    i.instruction_name
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN instructions i ON c.conversation_id = i.conversation_id AND i.enabled = true
WHERE wc.workflow_id = 1124
ORDER BY wc.execution_order;
