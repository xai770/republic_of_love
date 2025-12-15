-- Migration: Wire entity_decision_saver and entity_decision_applier into WF3005
-- Date: 2025-12-14
-- Author: Sandy
--
-- Problem: The orphan classification pipeline (w3005) goes through:
--   triage -> classify -> grade -> debate panel -> validate -> "save" -> export
-- But the "save" step is an LLM that doesn't actually write to registry_decisions!
-- The entity_decision_saver and entity_decision_applier actors exist but are disconnected.
--
-- Solution:
--   1. Update w3005_save_instruction to use entity_decision_saver actor
--   2. Create new instruction in w3005_c9_apply for entity_decision_applier
--   3. Chain: validate -> save (decision_saver) -> apply (decision_applier) -> export

BEGIN;

-- Step 1: Update w3005_save_instruction to use entity_decision_saver actor (ID 140)
UPDATE instructions 
SET delegate_actor_id = 140,  -- entity_decision_saver
    prompt_template = NULL,   -- Clear LLM prompt since actor handles it
    updated_at = NOW()
WHERE instruction_id = 3441;  -- w3005_save_instruction

-- Step 2: Create instruction for entity_decision_applier in w3005_c9_apply
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    delegate_actor_id,
    timeout_seconds,
    is_terminal,
    enabled,
    created_at,
    updated_at
) VALUES (
    'w3005_apply_decisions',
    9237,  -- w3005_c9_apply
    1,
    'Apply approved registry decisions to entity_relationships',
    142,   -- entity_decision_applier
    60,    -- 60 second timeout
    false, -- Not terminal - chains to export
    true,
    NOW(),
    NOW()
) RETURNING instruction_id;

-- Step 3: Update w3005_save_instruction to chain to w3005_c9_apply instead of export
UPDATE instruction_steps
SET next_conversation_id = 9237  -- w3005_c9_apply
WHERE instruction_step_id = 129;  -- w3005_save_instruction step

-- Step 4: Create instruction_step for w3005_apply_decisions to chain to export
-- First get the new instruction_id (we'll use a variable approach)
DO $$
DECLARE
    new_instruction_id INTEGER;
BEGIN
    SELECT instruction_id INTO new_instruction_id
    FROM instructions 
    WHERE instruction_name = 'w3005_apply_decisions' 
    ORDER BY created_at DESC 
    LIMIT 1;
    
    INSERT INTO instruction_steps (
        instruction_step_name,
        instruction_id,
        next_conversation_id,
        enabled,
        created_at,
        updated_at
    ) VALUES (
        'apply_to_export',
        new_instruction_id,
        9246,  -- w3005_export_registry
        true,
        NOW(),
        NOW()
    );
END $$;

COMMIT;

-- Verification queries
SELECT '=== Migration Complete ===' as status;

SELECT 'w3005_save_instruction now uses actor:' as check, 
       i.instruction_name, a.actor_name
FROM instructions i
LEFT JOIN actors a ON i.delegate_actor_id = a.actor_id
WHERE i.instruction_id = 3441;

SELECT 'New w3005_apply_decisions instruction:' as check,
       i.instruction_name, a.actor_name, c.canonical_name as conversation
FROM instructions i
LEFT JOIN actors a ON i.delegate_actor_id = a.actor_id
LEFT JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.instruction_name = 'w3005_apply_decisions';

SELECT 'Updated chain flow:' as check;
SELECT i.instruction_name, ist.instruction_step_name, c.canonical_name as next_conv
FROM instructions i
JOIN instruction_steps ist ON i.instruction_id = ist.instruction_id
LEFT JOIN conversations c ON ist.next_conversation_id = c.conversation_id
WHERE i.instruction_name IN ('Validate parent categories', 'w3005_save_instruction', 'w3005_apply_decisions')
ORDER BY i.instruction_name;
