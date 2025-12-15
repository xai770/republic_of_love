-- Migration 033: Simplify conversation_dialogue for deterministic scripted turns
-- Purpose: MVP multi-actor support - actors speak in predetermined order
-- Date: 2025-11-02
-- Author: Arden (AI) + User

BEGIN;

-- Drop the existing conversation_dialogue table (we just created it, but let's redesign)
DROP TABLE IF EXISTS conversation_dialogue_history CASCADE;
DROP TRIGGER IF EXISTS conversation_dialogue_history_trigger ON conversation_dialogue CASCADE;
DROP FUNCTION IF EXISTS archive_conversation_dialogue() CASCADE;
DROP TABLE IF EXISTS conversation_dialogue CASCADE;

-- Create simplified conversation_dialogue for scripted turns
CREATE TABLE conversation_dialogue (
    dialogue_step_id SERIAL PRIMARY KEY,
    dialogue_step_name TEXT NOT NULL UNIQUE,
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    
    -- WHO speaks at this step
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    actor_role TEXT NOT NULL, -- Semantic role: 'generator', 'critic', 'validator', 'synthesizer', etc.
    
    -- WHEN they speak (deterministic order)
    execution_order INTEGER NOT NULL,
    
    -- WHAT they see (context from previous steps)
    reads_from_step_ids INTEGER[], -- Array of dialogue_step_ids this actor reads from
    
    -- WHAT they say (prompt template with placeholders)
    prompt_template TEXT NOT NULL,
    
    -- Execution settings
    timeout_seconds INTEGER DEFAULT 300,
    enabled BOOLEAN DEFAULT true,
    
    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(conversation_id, execution_order),
    CHECK(execution_order > 0)
);

-- Indexes
CREATE INDEX idx_conversation_dialogue_conversation ON conversation_dialogue(conversation_id) 
    WHERE enabled = true;
CREATE INDEX idx_conversation_dialogue_actor ON conversation_dialogue(actor_id);
CREATE INDEX idx_conversation_dialogue_order ON conversation_dialogue(conversation_id, execution_order);

-- Comments
COMMENT ON TABLE conversation_dialogue IS 
'Orchestrates multi-actor dialogues with scripted, deterministic turn-taking.
Each row defines one actor''s turn: who speaks, when, what they see, what they say.
Actors speak in execution_order sequence. No chaos, no snowballing - controlled dialogue.

Example: CV Review
  Step 1: career_coach reads CV → suggests improvements
  Step 2: industry_expert reads CV + step_1 → validates suggestions  
  Step 3: writing_expert reads all → polishes language
  Step 4: synthesizer reads all → generates final output

Example: Novel Scene (Mysti''s use case)
  Step 1: history_expert analyzes scene historically
  Step 2: magic_specialist reads step_1 → adds magic system constraints
  Step 3: psychologist reads step_1,2 → analyzes character psychology
  Step 4: synthesizer reads all → creates coherent scene';

COMMENT ON COLUMN conversation_dialogue.actor_role IS 
'Semantic role of this actor in the dialogue: generator, critic, reviewer, validator, 
synthesizer, historian, psychologist, etc. Helps humans understand dialogue structure.';

COMMENT ON COLUMN conversation_dialogue.execution_order IS 
'Deterministic turn order. Actor at order=1 speaks first, order=2 second, etc.
No moderator needed - just follow the script.';

COMMENT ON COLUMN conversation_dialogue.reads_from_step_ids IS 
'Array of dialogue_step_ids this actor can see/read from. NULL = reads only conversation input.
Example: ARRAY[1,2] means this actor sees outputs from steps 1 and 2.
Use in prompt_template as {dialogue_step_1_output}, {dialogue_step_2_output}, etc.';

COMMENT ON COLUMN conversation_dialogue.prompt_template IS 
'Prompt template with placeholders:
- {dialogue_step_N_output} - Output from dialogue step N
- {test_case_data.param_1} - Input from test case
- Standard placeholders work too
Example: "Review this code: {dialogue_step_1_output}. Context: {test_case_data.param_1}"';

-- Add tracking table for dialogue step executions
CREATE TABLE dialogue_step_runs (
    dialogue_step_run_id SERIAL PRIMARY KEY,
    conversation_run_id INTEGER NOT NULL REFERENCES conversation_runs(conversation_run_id) ON DELETE CASCADE,
    dialogue_step_id INTEGER NOT NULL REFERENCES conversation_dialogue(dialogue_step_id) ON DELETE CASCADE,
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    execution_order INTEGER NOT NULL,
    
    -- Execution details
    prompt_rendered TEXT NOT NULL,
    response_received TEXT,
    latency_ms INTEGER,
    status TEXT DEFAULT 'PENDING',
    error_details TEXT,
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT dialogue_step_runs_status_check 
        CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT'))
);

CREATE INDEX idx_dialogue_step_runs_conversation ON dialogue_step_runs(conversation_run_id);
CREATE INDEX idx_dialogue_step_runs_step ON dialogue_step_runs(dialogue_step_id);
CREATE INDEX idx_dialogue_step_runs_status ON dialogue_step_runs(status);

COMMENT ON TABLE dialogue_step_runs IS 
'Tracks execution of each dialogue step within a conversation run.
Records what each actor said, when, and how long it took.
Provides audit trail for multi-actor conversations.';

COMMIT;

-- Verification
SELECT 
    'conversation_dialogue' as table_created,
    COUNT(*) as initial_rows
FROM conversation_dialogue;

SELECT 
    'dialogue_step_runs' as tracking_table,
    COUNT(*) as initial_runs  
FROM dialogue_step_runs;

-- Show we're ready
SELECT 
    '✅ MVP multi-actor dialogue support ready' as status,
    '✅ Deterministic scripted turns' as execution_mode,
    '✅ Moderator can be added later' as future_capability;
