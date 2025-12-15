-- WF3005 Enhancement: Add Pending Skills Processing Step
-- Date: December 8, 2025
-- Author: Sandy
--
-- This migration adds Step 0 to WF3005 that processes entities_pending
-- before the orphan skills classification loop.

BEGIN;

-- ============================================================================
-- 1. CREATE ACTORS
-- ============================================================================

INSERT INTO actors (actor_id, actor_name, actor_type, url, execution_type, execution_path, script_file_path, enabled)
VALUES 
    (143, 'pending_skills_fetcher', 'script', 'local://script', 'python_script', 
     'core/wave_runner/actors/pending_skills_fetcher.py',
     'core/wave_runner/actors/pending_skills_fetcher.py', true),
    (144, 'pending_skills_applier', 'script', 'local://script', 'python_script',
     'core/wave_runner/actors/pending_skills_applier.py',
     'core/wave_runner/actors/pending_skills_applier.py', true);

-- ============================================================================
-- 2. CREATE CONVERSATIONS
-- ============================================================================

INSERT INTO conversations (conversation_id, conversation_name, canonical_name)
VALUES
    (9242, 'w3005_fetch_pending_skills', 'w3005_c0a_fetch_pending'),
    (9243, 'w3005_triage_pending_skills', 'w3005_c0b_triage_pending'),
    (9244, 'w3005_apply_pending_decisions', 'w3005_c0c_apply_pending');

-- ============================================================================
-- 3. CREATE INSTRUCTIONS
-- ============================================================================

-- Step 0a: Fetch pending skills (script actor)
INSERT INTO instructions (instruction_id, instruction_name, conversation_id, step_number, 
                          prompt_template, delegate_actor_id, is_terminal, enabled)
VALUES (3447, 'w3005_fetch_pending', 9242, 1, 
        'Fetch pending skills batch', 143, true, true);

-- Step 0b: Triage pending skills (LLM)
INSERT INTO instructions (instruction_id, instruction_name, conversation_id, step_number,
                          prompt_template, is_terminal, enabled)
VALUES (3448, 'w3005_triage_pending', 9243, 1, 
'You are a skill registry curator. For each pending skill, decide its fate.

**Pending skills to triage (format: pending_id|raw_value):**
{pending_skills}

**Existing skills in registry (format: entity_id|canonical_name):**
{existing_skills}

**Decision options:**
1. **NEW** - This is a genuinely new skill. Create a new entity.
2. **ALIAS** - This matches an existing skill. Map it as an alias.
3. **SKIP** - This is NOT a skill (e.g., years experience, job title, language level).

For EACH pending skill, output ONE JSON object per line:

For NEW:
{"pending_id": 123, "decision": "NEW", "canonical_name": "Machine Learning", "confidence": 0.9, "reasoning": "Genuine skill not in registry"}

For ALIAS:
{"pending_id": 123, "decision": "ALIAS", "target_entity_id": 456, "confidence": 0.95, "reasoning": "Same as existing Python"}

For SKIP:
{"pending_id": 123, "decision": "SKIP", "confidence": 0.85, "reasoning": "Not a skill - experience requirement"}

**IMPORTANT:**
- For ALIAS, use the entity_id from existing skills list
- For NEW, suggest a clean canonical_name (no parenthetical variants like "Python (programming)")
- Group similar pending skills under ONE canonical entity
- Output ONLY JSON objects, one per line. No other text.',
true, true);

-- Step 0c: Apply pending decisions (script actor)
INSERT INTO instructions (instruction_id, instruction_name, conversation_id, step_number,
                          prompt_template, delegate_actor_id, is_terminal, enabled)
VALUES (3449, 'w3005_apply_pending', 9244, 1,
        'Apply pending skill decisions', 144, true, true);

-- ============================================================================
-- 4. SHIFT EXISTING WORKFLOW STEPS (make room for new steps at beginning)
-- ============================================================================

-- First, temporarily remove unique constraint by shifting to high values
UPDATE workflow_conversations 
SET execution_order = execution_order + 100
WHERE workflow_id = 3005;

-- Now shift back down with +3 offset (to make room for 3 new steps)
UPDATE workflow_conversations 
SET execution_order = execution_order - 100 + 3
WHERE workflow_id = 3005;

-- ============================================================================
-- 5. INSERT NEW WORKFLOW STEPS
-- ============================================================================

-- Step 0a: Fetch pending (new entry point)
INSERT INTO workflow_conversations 
    (step_id, workflow_id, conversation_id, execution_order, 
     is_entry_point, execute_condition, on_success_action, enabled)
VALUES 
    (398, 3005, 9242, 1, true, 'always', 'continue', true);

-- Step 0b: Triage pending (depends on fetch)
INSERT INTO workflow_conversations 
    (step_id, workflow_id, conversation_id, execution_order,
     depends_on_step_id, is_entry_point, execute_condition, on_success_action, enabled)
VALUES 
    (399, 3005, 9243, 2, 398, false, 'always', 'continue', true);

-- Step 0c: Apply pending (depends on triage)
INSERT INTO workflow_conversations 
    (step_id, workflow_id, conversation_id, execution_order,
     depends_on_step_id, is_entry_point, execute_condition, on_success_action, enabled)
VALUES 
    (400, 3005, 9244, 3, 399, false, 'always', 'continue', true);

-- ============================================================================
-- 6. UPDATE OLD ENTRY POINT
-- ============================================================================

-- The old entry point (c1_fetch) should now depend on c0c_apply
UPDATE workflow_conversations
SET is_entry_point = false,
    depends_on_step_id = 400
WHERE step_id = 386;  -- w3005_c1_fetch

-- ============================================================================
-- 7. VERIFY
-- ============================================================================

-- Show the new workflow order
SELECT wc.step_id, wc.execution_order, c.canonical_name, 
       wc.depends_on_step_id, wc.is_entry_point
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE wc.workflow_id = 3005
ORDER BY wc.execution_order;

COMMIT;
