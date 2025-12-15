-- Migration 032: Add multi-actor dialogue and parallel execution support
-- Purpose: Enable conversations with multiple AI actors discussing, and parallel workflow execution
-- Date: 2025-11-01
-- Author: Arden (AI) + User

BEGIN;

-- ============================================================================
-- PART 1: Multi-Actor Dialogue Support
-- ============================================================================

-- Add conversation_type to conversations table
ALTER TABLE conversations ADD COLUMN conversation_type TEXT DEFAULT 'single_actor';

ALTER TABLE conversations ADD CONSTRAINT conversations_conversation_type_check 
    CHECK (conversation_type = ANY (ARRAY[
        'single_actor',           -- One AI, one or more instructions (current default)
        'multi_turn',             -- One AI, multiple back-and-forth instructions
        'multi_actor_sequential', -- Multiple AIs, each does their part in sequence
        'multi_actor_dialogue'    -- Multiple AIs discussing/debating (NEW capability)
    ]));

COMMENT ON COLUMN conversations.conversation_type IS 
'Type of conversation execution:
- single_actor: One AI executes all instructions (most common)
- multi_turn: One AI, multiple instructions in sequence (current behavior with multiple instructions)
- multi_actor_sequential: Multiple AIs, each assigned to specific instructions
- multi_actor_dialogue: Multiple AIs engaging in structured dialogue/debate';

-- Create new table for orchestrating multi-actor dialogues
CREATE TABLE conversation_dialogue (
    dialogue_step_id SERIAL PRIMARY KEY,
    dialogue_step_name TEXT NOT NULL UNIQUE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    actor_role TEXT NOT NULL, -- 'generator', 'critic', 'reviewer', 'moderator', 'validator', etc.
    execution_order INTEGER NOT NULL,
    reads_from_step_id INTEGER REFERENCES conversation_dialogue(dialogue_step_id), -- Which previous step to read output from
    prompt_template TEXT NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,
    max_dialogue_rounds INTEGER DEFAULT 1, -- How many times this actor can speak in the dialogue
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(conversation_id, execution_order)
);

CREATE INDEX idx_conversation_dialogue_conversation ON conversation_dialogue(conversation_id) WHERE enabled = true;
CREATE INDEX idx_conversation_dialogue_actor ON conversation_dialogue(actor_id);
CREATE INDEX idx_conversation_dialogue_order ON conversation_dialogue(conversation_id, execution_order);
CREATE INDEX idx_conversation_dialogue_reads_from ON conversation_dialogue(reads_from_step_id) WHERE reads_from_step_id IS NOT NULL;

COMMENT ON TABLE conversation_dialogue IS 
'Orchestrates multi-actor dialogues within a conversation. Each row defines one actor''s 
contribution to the dialogue, what they read, and when they speak. Enables AI-to-AI 
discussions, debates, and collaborative refinement.';

COMMENT ON COLUMN conversation_dialogue.actor_role IS 
'Semantic role of this actor in the dialogue: generator, critic, reviewer, moderator, validator, etc.';

COMMENT ON COLUMN conversation_dialogue.reads_from_step_id IS 
'Which previous dialogue step this actor reads output from. NULL = reads from conversation input.';

COMMENT ON COLUMN conversation_dialogue.max_dialogue_rounds IS 
'Maximum times this actor can contribute in multi-round dialogues. 1 = speaks once.';

-- ============================================================================
-- PART 2: Parallel Execution Support
-- ============================================================================

-- Add parallel execution capabilities to workflow_conversations
ALTER TABLE workflow_conversations ADD COLUMN parallel_group INTEGER;
ALTER TABLE workflow_conversations ADD COLUMN wait_for_group BOOLEAN DEFAULT false;

CREATE INDEX idx_workflow_conversations_parallel ON workflow_conversations(workflow_id, parallel_group) 
    WHERE parallel_group IS NOT NULL;

COMMENT ON COLUMN workflow_conversations.parallel_group IS 
'Conversations with the same parallel_group number execute concurrently within the workflow.
NULL = execute serially (default behavior).
Example: parallel_group=1 for steps 2,3,4 means they run simultaneously.';

COMMENT ON COLUMN workflow_conversations.wait_for_group IS 
'If true, workflow waits for ALL conversations in this parallel_group to complete before continuing.
Used as synchronization barrier for parallel execution.';

-- Add parallel execution tracking to workflow_runs
ALTER TABLE workflow_runs ADD COLUMN parallel_groups_active INTEGER DEFAULT 0;
ALTER TABLE workflow_runs ADD COLUMN parallel_groups_completed INTEGER DEFAULT 0;

COMMENT ON COLUMN workflow_runs.parallel_groups_active IS 
'Number of parallel conversation groups currently executing in this workflow run.';

COMMENT ON COLUMN workflow_runs.parallel_groups_completed IS 
'Number of parallel conversation groups that have completed in this workflow run.';

-- ============================================================================
-- PART 3: Add execution metadata for multi-actor tracking
-- ============================================================================

-- Add dialogue tracking to conversation_runs
ALTER TABLE conversation_runs ADD COLUMN dialogue_round INTEGER DEFAULT 1;
ALTER TABLE conversation_runs ADD COLUMN active_actor_id INTEGER REFERENCES actors(actor_id);

COMMENT ON COLUMN conversation_runs.dialogue_round IS 
'For multi-actor dialogues: which round of discussion is this (1, 2, 3...).';

COMMENT ON COLUMN conversation_runs.active_actor_id IS 
'For multi-actor dialogues: which actor is currently speaking in this conversation run.';

-- ============================================================================
-- PART 4: Create history/archive table for conversation_dialogue
-- ============================================================================

CREATE TABLE conversation_dialogue_history (
    history_id SERIAL PRIMARY KEY,
    dialogue_step_id INTEGER NOT NULL,
    dialogue_step_name TEXT NOT NULL,
    conversation_id INTEGER NOT NULL,
    actor_id INTEGER NOT NULL,
    actor_role TEXT NOT NULL,
    execution_order INTEGER NOT NULL,
    reads_from_step_id INTEGER,
    prompt_template TEXT NOT NULL,
    timeout_seconds INTEGER,
    max_dialogue_rounds INTEGER,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_type TEXT DEFAULT 'UPDATE'
);

CREATE INDEX idx_conversation_dialogue_history_dialogue_step ON conversation_dialogue_history(dialogue_step_id);
CREATE INDEX idx_conversation_dialogue_history_archived ON conversation_dialogue_history(archived_at);

-- Create trigger function for archiving conversation_dialogue changes
CREATE OR REPLACE FUNCTION archive_conversation_dialogue()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO conversation_dialogue_history (
        dialogue_step_id, dialogue_step_name, conversation_id, actor_id, 
        actor_role, execution_order, reads_from_step_id, prompt_template,
        timeout_seconds, max_dialogue_rounds, enabled, created_at, updated_at,
        change_type
    )
    VALUES (
        OLD.dialogue_step_id, OLD.dialogue_step_name, OLD.conversation_id, OLD.actor_id,
        OLD.actor_role, OLD.execution_order, OLD.reads_from_step_id, OLD.prompt_template,
        OLD.timeout_seconds, OLD.max_dialogue_rounds, OLD.enabled, OLD.created_at, OLD.updated_at,
        TG_OP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to conversation_dialogue table
CREATE TRIGGER conversation_dialogue_history_trigger
    BEFORE UPDATE ON conversation_dialogue
    FOR EACH ROW
    EXECUTE FUNCTION archive_conversation_dialogue();

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check new columns added
SELECT 
    'conversations.conversation_type' as new_column,
    COUNT(*) as rows_with_default
FROM conversations 
WHERE conversation_type = 'single_actor';

SELECT 
    'workflow_conversations.parallel_group' as new_column,
    COUNT(*) as rows_with_null
FROM workflow_conversations 
WHERE parallel_group IS NULL;

SELECT 
    'conversation_dialogue table' as new_table,
    COUNT(*) as initial_rows
FROM conversation_dialogue;

-- Summary
SELECT 
    '✅ Multi-actor dialogue support added' as status,
    '✅ Parallel execution framework added' as parallel_status,
    '✅ Ready for multi-AI conversations' as capability;
