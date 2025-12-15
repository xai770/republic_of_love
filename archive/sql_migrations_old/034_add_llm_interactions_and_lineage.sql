-- Migration 034: Add comprehensive LLM interaction tracking and causation lineage
-- Purpose: Unified view of all LLM calls across workflow types + what influenced what
-- Author: Data Architect & User
-- Date: 2025-11-02

BEGIN;

-- =====================================================================
-- Table 1: llm_interactions
-- =====================================================================
-- Unified log of EVERY single LLM call, regardless of workflow type
-- One row per AI model invocation
-- Replaces fragmented tracking across conversation_runs, dialogue_step_runs

CREATE TABLE llm_interactions (
    interaction_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- Context: Where did this happen?
    workflow_run_id INTEGER NOT NULL REFERENCES workflow_runs(workflow_run_id) ON DELETE CASCADE,
    conversation_run_id INTEGER NOT NULL REFERENCES conversation_runs(conversation_run_id) ON DELETE CASCADE,
    dialogue_step_run_id INTEGER REFERENCES dialogue_step_runs(dialogue_step_run_id) ON DELETE CASCADE,
    -- dialogue_step_run_id is NULL for single-actor/multi-turn, populated for multi-actor dialogues
    
    -- What was executed?
    actor_id INTEGER NOT NULL REFERENCES actors(actor_id),
    instruction_id INTEGER REFERENCES instructions(instruction_id),
    -- instruction_id is NULL for multi-actor dialogues (prompt comes from conversation_dialogue.prompt_template)
    
    execution_order INTEGER NOT NULL,
    -- Order within the conversation (1, 2, 3, ...)
    
    -- The interaction itself
    prompt_sent TEXT NOT NULL,
    response_received TEXT,
    
    -- Performance metrics
    latency_ms INTEGER,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10, 6),
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'PENDING',
    -- PENDING, SUCCESS, TIMEOUT, ERROR, RATE_LIMITED, etc.
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    
    -- Constraints
    CHECK (status IN ('PENDING', 'SUCCESS', 'TIMEOUT', 'ERROR', 'RATE_LIMITED', 'QUOTA_EXCEEDED', 'INVALID_REQUEST')),
    CHECK (execution_order > 0),
    CHECK (latency_ms >= 0),
    CHECK (tokens_input >= 0),
    CHECK (tokens_output >= 0),
    CHECK (cost_usd >= 0)
);

-- Indexes for fast queries
CREATE INDEX idx_llm_workflow ON llm_interactions(workflow_run_id);
CREATE INDEX idx_llm_conversation ON llm_interactions(conversation_run_id);
CREATE INDEX idx_llm_dialogue_step ON llm_interactions(dialogue_step_run_id) WHERE dialogue_step_run_id IS NOT NULL;
CREATE INDEX idx_llm_actor ON llm_interactions(actor_id);
CREATE INDEX idx_llm_status ON llm_interactions(status);
CREATE INDEX idx_llm_timestamps ON llm_interactions(started_at, completed_at);
CREATE INDEX idx_llm_conversation_order ON llm_interactions(conversation_run_id, execution_order);

-- Full-text search on prompts and responses (for debugging)
CREATE INDEX idx_llm_prompt_fts ON llm_interactions USING gin(to_tsvector('english', prompt_sent));
CREATE INDEX idx_llm_response_fts ON llm_interactions USING gin(to_tsvector('english', COALESCE(response_received, '')));

COMMENT ON TABLE llm_interactions IS 'Unified log of every LLM invocation across all workflow types. One row per AI model call.';
COMMENT ON COLUMN llm_interactions.interaction_id IS 'Unique identifier for this LLM interaction';
COMMENT ON COLUMN llm_interactions.workflow_run_id IS 'Which workflow execution this belongs to';
COMMENT ON COLUMN llm_interactions.conversation_run_id IS 'Which conversation execution within the workflow';
COMMENT ON COLUMN llm_interactions.dialogue_step_run_id IS 'For multi-actor dialogues only: which dialogue step. NULL for single-actor/multi-turn.';
COMMENT ON COLUMN llm_interactions.instruction_id IS 'For single-actor/multi-turn: which instruction template was used. NULL for multi-actor dialogues.';
COMMENT ON COLUMN llm_interactions.execution_order IS 'Order of execution within the conversation (1-based)';
COMMENT ON COLUMN llm_interactions.prompt_sent IS 'The actual prompt sent to the LLM (after placeholder replacement)';
COMMENT ON COLUMN llm_interactions.response_received IS 'The response from the LLM';
COMMENT ON COLUMN llm_interactions.latency_ms IS 'Time taken for LLM to respond (milliseconds)';
COMMENT ON COLUMN llm_interactions.tokens_input IS 'Number of input tokens (if available from LLM API)';
COMMENT ON COLUMN llm_interactions.tokens_output IS 'Number of output tokens (if available from LLM API)';
COMMENT ON COLUMN llm_interactions.cost_usd IS 'Cost of this interaction in USD (if calculable)';
COMMENT ON COLUMN llm_interactions.status IS 'Execution status: SUCCESS, TIMEOUT, ERROR, etc.';

-- =====================================================================
-- Table 2: interaction_lineage
-- =====================================================================
-- Tracks causation: which interactions influenced which other interactions
-- Builds a directed acyclic graph (DAG) of dependencies

CREATE TABLE interaction_lineage (
    lineage_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    -- The causal relationship (directed edge in the graph)
    downstream_interaction_id INTEGER NOT NULL REFERENCES llm_interactions(interaction_id) ON DELETE CASCADE,
    upstream_interaction_id INTEGER NOT NULL REFERENCES llm_interactions(interaction_id) ON DELETE CASCADE,
    -- downstream reads/uses output from upstream
    
    -- How did upstream influence downstream?
    influence_type TEXT NOT NULL,
    -- 'direct_read' - explicitly read output via placeholder (e.g., {session_1_output})
    -- 'sequential' - previous step in same conversation (implicit context)
    -- 'parallel_sync' - waited for parallel group to complete
    -- 'conditional' - branching logic based on upstream output
    -- 'dialogue_context' - multi-actor dialogue reading previous turn(s)
    
    -- Optional: Which placeholder was used?
    placeholder_used TEXT,
    -- e.g., 'session_1_output', 'dialogue_step_2_output', 'param_1'
    
    -- Metadata
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (downstream_interaction_id != upstream_interaction_id),
    -- Prevent self-references
    
    CHECK (influence_type IN ('direct_read', 'sequential', 'parallel_sync', 'conditional', 'dialogue_context')),
    
    -- Prevent duplicate edges
    UNIQUE(downstream_interaction_id, upstream_interaction_id, influence_type)
);

-- Indexes for graph traversal (both directions)
CREATE INDEX idx_lineage_downstream ON interaction_lineage(downstream_interaction_id);
CREATE INDEX idx_lineage_upstream ON interaction_lineage(upstream_interaction_id);
CREATE INDEX idx_lineage_type ON interaction_lineage(influence_type);
CREATE INDEX idx_lineage_placeholder ON interaction_lineage(placeholder_used) WHERE placeholder_used IS NOT NULL;

COMMENT ON TABLE interaction_lineage IS 'Causation graph: tracks which LLM interactions influenced which others. Enables lineage analysis and change impact tracking.';
COMMENT ON COLUMN interaction_lineage.downstream_interaction_id IS 'The interaction that was influenced (reads/depends on upstream)';
COMMENT ON COLUMN interaction_lineage.upstream_interaction_id IS 'The interaction that provided influence (was read by downstream)';
COMMENT ON COLUMN interaction_lineage.influence_type IS 'How upstream influenced downstream: direct_read, sequential, parallel_sync, conditional, dialogue_context';
COMMENT ON COLUMN interaction_lineage.placeholder_used IS 'If direct_read: which placeholder was used (e.g., session_1_output, dialogue_step_2_output)';

-- =====================================================================
-- Backfill existing data
-- =====================================================================

-- Step 1: Backfill from dialogue_step_runs (multi-actor dialogues)
INSERT INTO llm_interactions (
    workflow_run_id,
    conversation_run_id,
    dialogue_step_run_id,
    actor_id,
    instruction_id,  -- NULL for dialogues
    execution_order,
    prompt_sent,
    response_received,
    latency_ms,
    status,
    started_at,
    completed_at
)
SELECT 
    cr.run_id,  -- This is the workflow_run_id
    dsr.conversation_run_id,
    dsr.dialogue_step_run_id,
    dsr.actor_id,
    NULL,  -- No instruction_id for multi-actor dialogues
    dsr.execution_order,
    dsr.prompt_rendered,
    dsr.response_received,
    dsr.latency_ms,
    dsr.status,
    dsr.completed_at - (dsr.latency_ms || ' milliseconds')::INTERVAL,  -- Approximate start time
    dsr.completed_at
FROM dialogue_step_runs dsr
JOIN conversation_runs cr ON dsr.conversation_run_id = cr.conversation_run_id
WHERE NOT EXISTS (
    SELECT 1 FROM llm_interactions li 
    WHERE li.dialogue_step_run_id = dsr.dialogue_step_run_id
);

-- Step 1b: Backfill from instruction_runs (single-actor and multi-turn conversations)
INSERT INTO llm_interactions (
    workflow_run_id,
    conversation_run_id,
    dialogue_step_run_id,
    actor_id,
    instruction_id,
    execution_order,
    prompt_sent,
    response_received,
    latency_ms,
    status,
    error_message,
    started_at,
    completed_at
)
SELECT 
    cr.run_id,  -- This is the workflow_run_id
    ir.session_run_id as conversation_run_id,
    NULL,  -- Not a dialogue
    c.actor_id,  -- Get actor from conversation
    ir.instruction_id,
    ir.step_number as execution_order,
    ir.prompt_rendered as prompt_sent,
    ir.response_received,
    ir.latency_ms,
    ir.status,
    ir.error_details as error_message,
    ir.created_at - (ir.latency_ms || ' milliseconds')::INTERVAL,  -- Approximate start time
    ir.created_at as completed_at
FROM instruction_runs ir
JOIN conversation_runs cr ON ir.session_run_id = cr.conversation_run_id
JOIN conversations c ON cr.conversation_id = c.conversation_id
WHERE NOT EXISTS (
    SELECT 1 FROM llm_interactions li 
    WHERE li.conversation_run_id = ir.session_run_id 
      AND li.instruction_id = ir.instruction_id
      AND li.execution_order = ir.step_number
);

-- Step 2: Backfill lineage for multi-actor dialogues
-- Each dialogue step reads from steps specified in conversation_dialogue.reads_from_step_ids
WITH dialogue_lineage AS (
    SELECT 
        li_downstream.interaction_id as downstream_id,
        li_upstream.interaction_id as upstream_id,
        cd.reads_from_step_ids,
        cd_upstream.execution_order as upstream_order
    FROM llm_interactions li_downstream
    JOIN dialogue_step_runs dsr_downstream ON li_downstream.dialogue_step_run_id = dsr_downstream.dialogue_step_run_id
    JOIN conversation_dialogue cd ON dsr_downstream.dialogue_step_id = cd.dialogue_step_id
    JOIN conversation_dialogue cd_upstream ON cd_upstream.conversation_id = cd.conversation_id
    JOIN dialogue_step_runs dsr_upstream ON dsr_upstream.dialogue_step_id = cd_upstream.dialogue_step_id 
        AND dsr_upstream.conversation_run_id = dsr_downstream.conversation_run_id
    JOIN llm_interactions li_upstream ON li_upstream.dialogue_step_run_id = dsr_upstream.dialogue_step_run_id
    WHERE cd.reads_from_step_ids IS NOT NULL
      AND cd_upstream.execution_order = ANY(cd.reads_from_step_ids)
)
INSERT INTO interaction_lineage (
    downstream_interaction_id,
    upstream_interaction_id,
    influence_type,
    placeholder_used
)
SELECT 
    downstream_id,
    upstream_id,
    'dialogue_context',
    'dialogue_step_' || upstream_order || '_output'
FROM dialogue_lineage
ON CONFLICT (downstream_interaction_id, upstream_interaction_id, influence_type) DO NOTHING;

COMMIT;

-- =====================================================================
-- Verification queries
-- =====================================================================

-- Check backfill results
SELECT 
    'Backfilled interactions' as metric,
    COUNT(*) as count,
    COUNT(DISTINCT workflow_run_id) as workflows,
    COUNT(DISTINCT conversation_run_id) as conversations
FROM llm_interactions;

SELECT 
    'Backfilled lineage' as metric,
    COUNT(*) as count,
    COUNT(DISTINCT downstream_interaction_id) as downstream_interactions,
    COUNT(DISTINCT upstream_interaction_id) as upstream_interactions
FROM interaction_lineage;

-- Show sample of what we captured
SELECT 
    i.interaction_id,
    i.execution_order,
    a.actor_name,
    i.latency_ms,
    i.status,
    LEFT(i.prompt_sent, 50) as prompt_preview,
    LEFT(i.response_received, 50) as response_preview
FROM llm_interactions i
JOIN actors a ON i.actor_id = a.actor_id
ORDER BY i.interaction_id DESC
LIMIT 10;
