# Multi-Actor Dialogue - Usage Examples

## Overview
The runner now supports **deterministic scripted multi-actor dialogues**. Actors speak in predetermined order, each seeing outputs from specified previous speakers.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│ Conversation Type: multi_actor_dialogue                 │
├─────────────────────────────────────────────────────────┤
│ Turn 1: Actor A speaks                                  │
│         Sees: input data                                │
│         Outputs: response_1                             │
├─────────────────────────────────────────────────────────┤
│ Turn 2: Actor B speaks                                  │
│         Sees: input + response_1                        │
│         Outputs: response_2                             │
├─────────────────────────────────────────────────────────┤
│ Turn 3: Actor C speaks                                  │
│         Sees: input + response_1 + response_2           │
│         Outputs: response_3 (final)                     │
└─────────────────────────────────────────────────────────┘
```

## Example 1: CV Review (3 Actors)

```sql
-- Step 1: Create multi-actor conversation
INSERT INTO conversations (conversation_name, conversation_type, actor_id)
VALUES ('AI CV Review Team', 'multi_actor_dialogue', NULL);
-- Note: actor_id is NULL for multi-actor (defined in dialogue steps)

-- Step 2: Define dialogue steps
INSERT INTO conversation_dialogue 
    (dialogue_step_name, conversation_id, actor_id, actor_role, execution_order, 
     reads_from_step_ids, prompt_template)
VALUES
    -- Turn 1: Career coach analyzes CV
    ('cv_review_coach', <conv_id>, <career_coach_actor_id>, 'career_coach', 1, 
     NULL,  -- First speaker, reads only input
     'Analyze this CV and suggest improvements: {param_1}'),
    
    -- Turn 2: Industry expert validates suggestions
    ('cv_review_expert', <conv_id>, <industry_expert_actor_id>, 'industry_expert', 2,
     ARRAY[1],  -- Reads turn 1
     'Review these CV improvement suggestions from a career coach: {dialogue_step_1_output}. 
      Original CV: {param_1}. Are these suggestions valid for the industry?'),
    
    -- Turn 3: Writing expert polishes language
    ('cv_review_writer', <conv_id>, <writing_expert_actor_id>, 'writing_expert', 3,
     ARRAY[1, 2],  -- Reads turns 1 and 2
     'Based on career advice: {dialogue_step_1_output} and industry validation: {dialogue_step_2_output}, 
      create an improved CV with professional language: {param_1}');
```

**Output:** Actor 3's response becomes the conversation output.

## Example 2: Novel Scene (Mysti's Use Case - 4 Actors)

```sql
-- Step 1: Create conversation
INSERT INTO conversations (conversation_name, conversation_type, actor_id)
VALUES ('Novel Scene Development Team', 'multi_actor_dialogue', NULL);

-- Step 2: Define dialogue (4 experts collaborate)
INSERT INTO conversation_dialogue 
    (dialogue_step_name, conversation_id, actor_id, actor_role, execution_order, 
     reads_from_step_ids, prompt_template)
VALUES
    -- Turn 1: History expert sets context
    ('scene_history', <conv_id>, <history_expert_id>, 'historian', 1,
     NULL,
     'Historical context for this medieval scene: {param_1}'),
    
    -- Turn 2: Magic specialist adds constraints
    ('scene_magic', <conv_id>, <magic_expert_id>, 'magic_specialist', 2,
     ARRAY[1],
     'Given historical context: {dialogue_step_1_output}, 
      what magic system rules apply to this scene: {param_1}?'),
    
    -- Turn 3: Psychologist analyzes character
    ('scene_psychology', <conv_id>, <psychologist_id>, 'psychologist', 3,
     ARRAY[1, 2],
     'Scene: {param_1}. Historical context: {dialogue_step_1_output}. 
      Magic constraints: {dialogue_step_2_output}. 
      Analyze the character''s psychological state and motivations.'),
    
    -- Turn 4: Synthesizer creates final scene
    ('scene_synthesis', <conv_id>, <synthesizer_id>, 'synthesizer', 4,
     ARRAY[1, 2, 3],
     'Create a cohesive scene incorporating:
      - History: {dialogue_step_1_output}
      - Magic: {dialogue_step_2_output}
      - Psychology: {dialogue_step_3_output}
      - Original concept: {param_1}');
```

## Example 3: Code Review with Debate (2 Actors, Multiple Rounds)

```sql
-- 2 actors debating back and forth
INSERT INTO conversation_dialogue 
    (dialogue_step_name, conversation_id, actor_id, actor_role, execution_order, 
     reads_from_step_ids, prompt_template)
VALUES
    -- Round 1
    ('code_generate', <conv_id>, <claude_id>, 'generator', 1, NULL,
     'Generate Python code for: {param_1}'),
    
    ('code_review', <conv_id>, <qwen_id>, 'critic', 2, ARRAY[1],
     'Review and critique this code: {dialogue_step_1_output}'),
    
    -- Round 2  
    ('code_defend', <conv_id>, <claude_id>, 'responder', 3, ARRAY[1, 2],
     'Original code: {dialogue_step_1_output}. 
      Criticism: {dialogue_step_2_output}. 
      Defend your approach or revise the code.'),
    
    ('code_final_review', <conv_id>, <qwen_id>, 'validator', 4, ARRAY[1, 2, 3],
     'Final validation. Original: {dialogue_step_1_output}. 
      Initial review: {dialogue_step_2_output}. 
      Revision: {dialogue_step_3_output}. 
      Is this acceptable?');
```

## Running Multi-Actor Dialogues

```python
# No code changes needed! Runner automatically detects conversation_type

runner = BYRecipeRunner()
success = runner.execute_recipe(
    workflow_id=<your_workflow>,
    test_data="Your input here...",
    execution_mode='testing'
)
```

**Console output:**
```
📍 Session 1: AI CV Review Team (actor: None)
─────────────────────────────────────────────────────────
  🎭 Multi-actor dialogue: 3 actors will speak

  🎤 Turn 1: career_coach (actor 45)
     Reads from: none (first speaker)
     ✅ career_coach responded (15234ms)
     💬 The CV needs stronger action verbs...

  🎤 Turn 2: industry_expert (actor 46)
     Reads from: [1]
     ✅ industry_expert responded (12890ms)
     💬 These suggestions align with industry standards...

  🎤 Turn 3: writing_expert (actor 47)
     Reads from: [1, 2]
     ✅ writing_expert responded (18456ms)
     💬 [IMPROVED CV TEXT]...

  ✅ Multi-actor dialogue completed - 3 turns
```

## Placeholder Reference

**In prompt_template, you can use:**

1. **Input data:**
   - `{param_1}` - Test case input (most common)
   - `{test_case_data.param_1}` - Explicit form
   - `{test_case_data.job_id}` - If test case has job_id

2. **Previous dialogue outputs:**
   - `{dialogue_step_1_output}` - Output from turn 1
   - `{dialogue_step_2_output}` - Output from turn 2
   - etc.

3. **Reads from array:**
   - `reads_from_step_ids = ARRAY[1, 3]` means this actor sees outputs from turns 1 and 3
   - Use `{dialogue_step_1_output}` and `{dialogue_step_3_output}` in prompt

## Database Tables

**conversation_dialogue** - Defines who speaks when:
- `dialogue_step_id` - Primary key
- `conversation_id` - Which conversation
- `actor_id` - Which AI speaks
- `actor_role` - Semantic role (historian, critic, etc.)
- `execution_order` - When they speak (1, 2, 3...)
- `reads_from_step_ids` - Array of step IDs they read
- `prompt_template` - What they say/ask

**dialogue_step_runs** - Tracks execution:
- `dialogue_step_run_id` - Primary key
- `conversation_run_id` - Which execution
- `dialogue_step_id` - Which step
- `prompt_rendered` - Actual prompt sent
- `response_received` - Actor's response
- `latency_ms` - How long it took
- `status` - SUCCESS/FAILED

## Future Enhancements (Not Yet Implemented)

- ⏸️ **AI Moderator** - Dynamically choose next speaker
- ⏸️ **Conditional branching** - Route based on dialogue content
- ⏸️ **Max rounds** - Actors can speak multiple times
- ⏸️ **Parallel actors** - Multiple actors respond simultaneously

## Testing

```sql
-- Check if conversation is multi-actor
SELECT conversation_name, conversation_type 
FROM conversations 
WHERE conversation_type = 'multi_actor_dialogue';

-- See dialogue structure
SELECT 
    d.execution_order,
    d.actor_role,
    a.actor_name,
    d.reads_from_step_ids,
    LEFT(d.prompt_template, 60) as prompt_preview
FROM conversation_dialogue d
JOIN actors a ON d.actor_id = a.actor_id
WHERE d.conversation_id = <your_conv_id>
ORDER BY d.execution_order;

-- View execution results
SELECT 
    dsr.execution_order,
    a.actor_name,
    dsr.status,
    dsr.latency_ms,
    LEFT(dsr.response_received, 100) as response_preview
FROM dialogue_step_runs dsr
JOIN actors a ON dsr.actor_id = a.actor_id
WHERE dsr.conversation_run_id = <your_run_id>
ORDER BY dsr.execution_order;
```

---

**Status:** ✅ MVP Ready - Deterministic scripted turns working  
**Next:** Add AI moderator for dynamic turn control (when needed)
