# Multi-Actor Dialogue & Parallel Execution - Implementation Guide

**Date:** 2025-11-01  
**Migrations:** 031, 032  
**Status:** ✅ Schema Ready, Runner Compatible

## What Was Added

### 1. Table Rename: `conversation_steps` → `workflow_conversations`
**Purpose:** Clarify that this is a cross-reference table orchestrating which conversations belong to which workflows.

**Key insight:** This enables conversation reusability - the same conversation can be used in multiple workflows.

```
Workflow "Job Skills Extraction" ─┐
                                   ├─> Conversation "Hybrid Extraction" (reused!)
Workflow "Profile Skills"        ─┘
```

### 2. Multi-Actor Dialogue Support

#### New Column: `conversations.conversation_type`
- `single_actor` (default) - One AI, one or more instructions
- `multi_turn` - One AI, multiple back-and-forth instructions  
- `multi_actor_sequential` - Multiple AIs, each assigned to specific instructions
- `multi_actor_dialogue` - **NEW!** Multiple AIs discussing/debating

#### New Table: `conversation_dialogue`
Orchestrates multi-actor conversations with structured dialogue flows.

**Columns:**
- `dialogue_step_id` - Primary key
- `conversation_id` - Which conversation this dialogue belongs to
- `actor_id` - Which AI actor speaks at this step
- `actor_role` - Semantic role: 'generator', 'critic', 'reviewer', 'validator', etc.
- `execution_order` - When this actor speaks (1, 2, 3...)
- `reads_from_step_id` - Which previous dialogue step to read output from
- `prompt_template` - What this actor says/asks
- `max_dialogue_rounds` - How many times this actor can contribute
- `timeout_seconds` - Max time for this actor's response

#### Example Use Case: Code Review Dialogue
```sql
-- Create a conversation with type 'multi_actor_dialogue'
INSERT INTO conversations (conversation_name, conversation_type, actor_id)
VALUES ('AI Code Review Dialogue', 'multi_actor_dialogue', NULL);

-- Set up the dialogue flow
INSERT INTO conversation_dialogue 
    (conversation_id, actor_id, actor_role, execution_order, reads_from_step_id, prompt_template)
VALUES
    -- Step 1: Claude generates code
    (conv_id, claude_actor_id, 'generator', 1, NULL, 
     'Generate a Python function for: {task_description}'),
    
    -- Step 2: Qwen reviews the code  
    (conv_id, qwen_actor_id, 'critic', 2, 1,
     'Review this code and suggest improvements: {dialogue_step_1_output}'),
    
    -- Step 3: Claude responds to criticism
    (conv_id, claude_actor_id, 'responder', 3, 2,
     'Address these review comments: {dialogue_step_2_output}. Original code: {dialogue_step_1_output}'),
    
    -- Step 4: Qwen validates final version
    (conv_id, qwen_actor_id, 'validator', 4, 3,
     'Validate this improved code meets all requirements: {dialogue_step_3_output}');
```

### 3. Parallel Execution Framework

#### New Columns: `workflow_conversations.parallel_group` & `wait_for_group`

**Purpose:** Enable multiple conversations to execute simultaneously within a workflow.

**How it works:**
- Conversations with the same `parallel_group` number execute concurrently
- `wait_for_group=true` acts as a synchronization barrier
- NULL `parallel_group` = serial execution (default)

#### Example: Parallel Job Analysis
```sql
-- Workflow "Comprehensive Job Analysis"
INSERT INTO workflow_conversations 
    (workflow_id, conversation_id, execution_order, parallel_group, wait_for_group)
VALUES
    -- Step 1: Serial - Initial extraction
    (wf_id, conv_extract_id, 1, NULL, false),
    
    -- Steps 2-4: PARALLEL - Analyze different aspects simultaneously
    (wf_id, conv_skills_id, 2, 1, false),      -- Extract skills
    (wf_id, conv_culture_id, 3, 1, false),     -- Analyze culture
    (wf_id, conv_salary_id, 4, 1, true),       -- Estimate salary (barrier: wait for group 1)
    
    -- Step 5: Serial - Synthesize results after parallel work completes
    (wf_id, conv_synthesize_id, 5, NULL, false);
```

**Execution flow:**
```
Step 1: Extract (serial)
   ↓
Step 2,3,4: Skills + Culture + Salary (PARALLEL)
   ↓ (wait_for_group barrier)
Step 5: Synthesize (serial, has all parallel results)
```

#### New Tracking Columns: `workflow_runs`
- `parallel_groups_active` - How many parallel groups currently running
- `parallel_groups_completed` - How many parallel groups finished

### 4. Execution Metadata for Multi-Actor Tracking

#### New Columns: `conversation_runs`
- `dialogue_round` - Which round of multi-actor discussion (1, 2, 3...)
- `active_actor_id` - Which actor is currently speaking

## Implementation Roadmap

### ✅ Phase 1: Schema (COMPLETE)
- [x] Rename `conversation_steps` → `workflow_conversations`
- [x] Add `conversation_type` to conversations
- [x] Create `conversation_dialogue` table
- [x] Add parallel execution columns
- [x] Add tracking metadata

### 🔄 Phase 2: Runner Enhancement (TODO)

**For Multi-Actor Dialogue:**
1. Update `execute_recipe()` to check `conversation_type`
2. If `multi_actor_dialogue`, call new method `execute_multi_actor_dialogue()`
3. Implement dialogue orchestration:
   - Loop through `conversation_dialogue` steps in order
   - Each step: render prompt with previous outputs
   - Save each actor's contribution
   - Build context for next actor

**For Parallel Execution:**
1. Update `execute_recipe()` to detect `parallel_group` values
2. Group conversations by `parallel_group`
3. Use `threading` or `asyncio` to execute group concurrently
4. Wait for all in group before continuing (if `wait_for_group=true`)
5. Update `parallel_groups_active` and `parallel_groups_completed`

### 📝 Phase 3: Testing & Validation

**Test Cases Needed:**
- [ ] Simple multi-actor dialogue (2 actors, 4 turns)
- [ ] Multi-round dialogue (actors speak multiple times)
- [ ] Parallel execution (3 conversations simultaneously)
- [ ] Mixed workflow (serial → parallel → serial)
- [ ] Error handling in parallel groups

## Benefits

**Multi-Actor Dialogue:**
- ✅ AI-to-AI debate and refinement
- ✅ Structured peer review
- ✅ Collaborative problem-solving
- ✅ Multiple perspectives on same input

**Parallel Execution:**
- ✅ Faster workflow completion
- ✅ Independent tasks run simultaneously
- ✅ Better resource utilization
- ✅ Scalable architecture for complex workflows

## Next Steps

1. **Create test conversation** with 2-3 actors to validate schema
2. **Implement runner support** for multi-actor dialogue
3. **Implement parallel execution** in runner
4. **Build validated_prompts** for common multi-actor patterns
5. **Performance testing** with parallel workflows

## Notes

- Backward compatible: All existing workflows continue to work (serial, single-actor)
- Conversation reusability preserved via `workflow_conversations` junction table
- Schema supports future enhancements (e.g., conditional branches in dialogues)
- History tables track all changes for audit/rollback

---

**Architecture Decision:** Kept 3-layer structure (workflows → conversations → instructions) 
to preserve reusability while adding multi-actor and parallel capabilities where needed.
