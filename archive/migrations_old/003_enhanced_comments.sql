-- Migration 003: Enhanced Schema Documentation
-- Date: 2025-10-30
-- Purpose: Improve schema comments for helper/delegate pattern and naming conventions

BEGIN;

-- ============================================================================
-- 1. Enhanced Actor Delegation Comments
-- ============================================================================

COMMENT ON COLUMN instructions.delegate_actor_id IS 
'Optional: Override session primary actor for THIS INSTRUCTION ONLY.

🎯 Use Cases:
- Query skill_gopher for taxonomy navigation
- Execute SQL scripts for data operations  
- Run validators for quality checks
- Call Python scripts for transformations

⚙️ Execution Logic:
  IF delegate_actor_id IS NOT NULL:
      Execute with delegated actor
  ELSE:
      Execute with session.actor_id (primary)

📋 Context Inheritance:
- Delegated helper receives same session context
- Helper output added to session_outputs
- Primary actor can reference helper output in next instruction
- Example: {session_2_output} works whether session 2 used helper or not

💡 Example:
  session.actor_id = "qwen2.5:7b"            (primary actor)
  instruction.delegate_actor_id = "skill_gopher" (helper for one instruction)
  
  → Instruction executed by skill_gopher
  → Output stored in session_outputs  
  → Next instruction (primary actor) can use: {session_2_output}

🔄 Pattern:
  Instruction 1: Primary actor extracts data
  Instruction 2: Helper actor (delegate) processes/validates  ← Uses delegate_actor_id
  Instruction 3: Primary actor formats result (has access to both outputs)';

-- ============================================================================
-- 2. Session Actor Comments
-- ============================================================================

COMMENT ON COLUMN sessions.actor_id IS 
'Primary actor for all instructions in this session (unless overridden by delegate_actor_id).

This actor maintains session context and has access to all previous instruction outputs.
Individual instructions can delegate to helpers via instructions.delegate_actor_id,
but control returns to primary actor for subsequent instructions.

See instructions.delegate_actor_id for helper/delegate pattern details.';

-- ============================================================================
-- 3. Session Outputs Context
-- ============================================================================

COMMENT ON TABLE session_runs IS 
'Execution instances of sessions. Tracks which sessions ran in which order.

Session Context:
- Each session_run maintains output history for all its instructions
- Primary actor has access to ALL previous instruction outputs
- Helpers (via delegate_actor_id) also receive session context
- Enables multi-step reasoning chains and data transformation pipelines

Execution Flow:
  recipe_run → session_runs (ordered) → instruction_runs (sequential)
  
Run Type:
- run_type=''testing'': Uses recipe_runs (synthetic test data)
- run_type=''production'': Uses production_runs (real job postings)';

-- ============================================================================
-- 4. Prompt Template Placeholders Documentation
-- ============================================================================

COMMENT ON COLUMN instructions.prompt_template IS 
'Prompt template with dynamic variable substitution.

Supported Placeholders:
  {variations_param_1}   - Input data from test variations
  {job_description}      - For production: posting.raw_job_description  
  {profile_text}         - For production: profiles.profile_raw_text
  {session_N_output}     - Output from session N (e.g., {session_1_output})
  {taxonomy}             - Dynamic taxonomy from skill_hierarchy table
  
Fallback Syntax:
  {session_4_output?session_1_output} - Use session 4 if available, else session 1
  
Context Availability:
- Session outputs accumulate across instructions
- Both primary and delegated actors receive same context
- Enables chaining: extract → validate → improve → format

Example:
  Session 1, Instruction 1: "Extract skills from {job_description}"
    → Output: ["Python", "SQL"]
  
  Session 1, Instruction 2: "Map these to taxonomy: {session_1_output}"
    → Receives: ["Python", "SQL"]
    → Output: ["PYTHON", "SQL"]';

-- ============================================================================
-- 5. Naming Convention Documentation
-- ============================================================================

COMMENT ON COLUMN session_runs.completed_at IS 
'Timestamp when session execution finished (success or failure).

⚠️ Naming Convention: Always use ''completed_at'' (not ''ended_at'')
This is the standard across all execution tracking tables:
- recipe_runs.completed_at
- production_runs.completed_at
- session_runs.completed_at';

COMMENT ON COLUMN session_runs.error_details IS 
'Error message if session failed. NULL if successful.

⚠️ Naming Convention: Always use ''error_details'' (not ''error_message'')
This is the standard across all execution tracking tables:
- recipe_runs.error_details
- production_runs.error_details  
- session_runs.error_details
- instruction_runs.error_details';

COMMENT ON COLUMN session_runs.execution_order IS 
'Sequence number matching recipe_sessions.execution_order.
Indicates which position this session occupies in recipe execution flow.

⚠️ Naming Convention: Always use ''execution_order'' consistently
- recipe_sessions.execution_order (definition)
- session_runs.execution_order (tracking)

This replaced the old ''session_number'' column for semantic clarity.';

-- ============================================================================
-- 6. Run Unification Documentation
-- ============================================================================

COMMENT ON COLUMN session_runs.run_id IS 
'Unified run identifier. Replaces old recipe_run_id/production_run_id split.

References:
- recipe_runs.recipe_run_id (when run_type=''testing'')
- production_runs.production_run_id (when run_type=''production'')

Migration Note: This column consolidates what were previously two mutually
exclusive foreign keys into a single, cleaner design.';

COMMENT ON COLUMN session_runs.run_type IS 
'Execution mode: ''testing'' or ''production''.

- testing: Uses synthetic test variations (recipe_runs)
- production: Uses real job postings (production_runs)

Determines which parent table run_id references.';

-- ============================================================================
-- 7. Skill Taxonomy Dynamic Reference
-- ============================================================================

COMMENT ON TABLE skill_hierarchy IS 
'Hierarchical skill taxonomy with parent-child relationships.

Used by {taxonomy} placeholder in prompt templates to inject current
taxonomy dynamically. See core/taxonomy_helper.py for implementation.

Structure:
- skill: Child skill (leaf or intermediate node)
- parent_skill: Parent category
- strength: Relationship confidence (0.0-1.0)

Dynamic Injection:
When prompt template contains {taxonomy}, the prompt_renderer calls
get_taxonomy_string() which queries this table and formats as:

**DOMAIN_1:** skill1, skill2, skill3
**DOMAIN_2:** skill4, skill5

This ensures prompts always use current taxonomy without hardcoding.';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

-- View all enhanced comments
-- SELECT 
--     c.table_name,
--     c.column_name,
--     pgd.description
-- FROM pg_catalog.pg_statio_all_tables st
-- JOIN pg_catalog.pg_description pgd ON (pgd.objoid = st.relid)
-- JOIN information_schema.columns c ON (
--     pgd.objsubid = c.ordinal_position AND
--     c.table_schema = st.schemaname AND
--     c.table_name = st.relname
-- )
-- WHERE c.table_name IN ('session_runs', 'instructions', 'sessions')
-- ORDER BY c.table_name, c.ordinal_position;
