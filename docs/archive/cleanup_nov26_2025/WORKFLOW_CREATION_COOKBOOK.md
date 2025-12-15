# Workflow Creation Cookbook
**For Turing System - Complete Guide**

Author: Arden  
Date: 2025-11-04  
Status: Production Guide

---

## Overview

This cookbook documents the **correct** way to create workflows in Turing's schema. Follow this pattern every time to ensure consistency and avoid common pitfalls.

## Turing Architecture Hierarchy

```
workflows                      (Registry: What exists)
  ↓
workflow_conversations          (Sequence: What order)
  ↓
conversations                   (Units: Who does what)
  ↓
instructions                    (Prompts: What to say)
  ↓
instruction_steps              (Branching: What happens next)
```

## Key Principles

1. **Use canonical_name** for conversations - makes them reusable across workflows
2. **Let PostgreSQL auto-generate IDs** - Don't hardcode conversation_id or instruction_id
3. **Use RETURNING clauses** to capture generated IDs
4. **Test incrementally** - Verify each step before moving to the next
5. **Keep prompts in the schema** - No hardcoded Python scripts
6. **Let database sequences handle ID assignment** - Don't manually calculate IDs (see Database ID Management below)

---

## Pre-Flight Checklist for New Workflows

Use this checklist BEFORE starting any new workflow to avoid common mistakes and leverage existing tools.

### 🔍 Phase 0: Research & Planning (Before Writing Any Code)

**Check existing resources:**
- [ ] **Read TOOL_REGISTRY.md** - Does a tool already exist that does what you need?
  - Example: Don't write a new skill mapper if `simple_skill_mapper` exists
  - Example: Use `chunked_deepseek_analyzer` for large document processing
- [ ] **Search existing workflows** - Can you reuse conversations?
  ```sql
  -- Search by description
  SELECT workflow_id, workflow_name, workflow_description 
  FROM workflows 
  WHERE workflow_description ILIKE '%your_keyword%';
  
  -- Search by tags (PREFERRED - more accurate)
  SELECT * FROM v_conversation_discovery
  WHERE 'extract' = ANY(tags)  -- Find all extraction conversations
    AND app_scope = 'talent';  -- Optional: filter by app
  ```
- [ ] **Check existing actors** - Is there a delegate actor for your task?
  ```sql
  SELECT actor_id, actor_name, actor_type, url
  FROM actors
  WHERE actor_type = 'delegate_actor';
  ```

**Plan your workflow:**
- [ ] **Sketch data flow** - What are inputs? What are outputs? What transformations happen?
- [ ] **Identify conversations** - Break work into logical units (extract, validate, transform, save)
- [ ] **List all placeholders needed** - Document what data flows between conversations
- [ ] **Choose appropriate actors** - Match task complexity to model capability
  - Small/fast tasks → gemma2:2b, phi3:latest
  - Medium tasks → qwen2.5:7b, gemma2:latest
  - Complex reasoning → qwen2.5:32b, deepseek-r1
  - Specialized tasks → delegate actors (skill_mapper, taxonomy_expander, etc.)

**Test prompts interactively:**
- [ ] **Use llm_chat.py to prototype prompts** - Test with actual data BEFORE writing migrations
  ```bash
  python3 tools/llm_chat.py qwen2.5:7b send "Your test prompt here"
  ```
- [ ] **Verify output markers** - Test that LLM outputs [SUCCESS], [FAIL] markers if needed
- [ ] **Test edge cases** - What happens with malformed input? Empty data? Missing fields?
- [ ] **Document what worked** - Save successful prompts for migration

### 📝 Phase 1: Implementation (During Development)

**Migration hygiene:**
- [ ] **Use DO blocks with variables** - Don't hardcode IDs
- [ ] **Include RETURNING clauses** - Capture auto-generated IDs
- [ ] **Let PostgreSQL assign IDs** - Don't use MAX(id)+1 pattern (see Database ID Management)
- [ ] **Test each migration incrementally** - Run and verify before moving to next step
- [ ] **Set app_scope for workflow** - Always specify which application (talent/news/write/research/contract)
- [ ] **Tag all conversations** - Use tag_conversation() to apply action verb tags for discovery

**Placeholder management (CRITICAL):**
- [ ] **Register ALL placeholders in Step 2b** - Don't skip this step!
- [ ] **Use correct source_type**:
  - `test_case_data` for workflow inputs
  - `dialogue_output` for conversation outputs
  - `posting`/`profile`/`custom_query` for database data
- [ ] **Follow naming convention**: `session_r{N}_output` for conversation N's output
- [ ] **Verify placeholders match prompts**: 
  ```sql
  -- Get placeholders used in instruction
  SELECT 
    i.instruction_name,
    regexp_matches(i.instruction_text, '\{([^}]+)\}', 'g') as placeholders
  FROM instructions i;
  
  -- Check if registered
  SELECT placeholder_name FROM placeholder_definitions 
  WHERE placeholder_name = 'your_placeholder';
  ```

**Conversation design:**
- [ ] **Use canonical_name always** - Pattern: `w{workflow_id}_c{N}_{short_name}`
- [ ] **Set appropriate timeouts** - Consider model speed and task complexity
- [ ] **Mark terminal instructions** - Set `is_terminal = true` for final steps
- [ ] **Define branching logic** - Add instruction_steps for all possible outcomes

### ✅ Phase 2: Validation (After Implementation)

**End-to-end testing:**
- [ ] **Test with real data** - Not just happy path, test error conditions too
- [ ] **Verify all branches work** - Test [SUCCESS], [FAIL], [ERROR] paths
- [ ] **Check database writes** - Confirm data appears in target tables
- [ ] **Review LLM interaction logs** - Look for unexpected behaviors
  ```sql
  SELECT * FROM conversation_history 
  WHERE workflow_run_id = YOUR_RUN_ID
  ORDER BY created_at;
  ```

**Documentation:**
- [ ] **Update TOOL_REGISTRY.md** - If you created a delegate actor, document it
- [ ] **Add workflow to PROJECT_PLAN** - Note what problem it solves
- [ ] **Update this cookbook** - Document any new patterns or lessons learned

### 🚨 Common Gotchas to Avoid

❌ **Don't skip Step 2b (placeholder registration)** - You'll get validation errors later  
❌ **Don't hardcode conversation_id or skill_id values** - Use RETURNING clauses  
❌ **Don't calculate IDs manually** - Let PostgreSQL sequences handle it  
❌ **Don't forget to test prompts with llm_chat.py first** - Saves migration rewrites  
❌ **Don't assume tools don't exist** - Check TOOL_REGISTRY.md first  
❌ **Don't forget about chunked_deepseek_analyzer** - Use it for large documents  
❌ **Don't write output markers in prompts without testing** - Verify LLM actually outputs them

### ✨ Success Criteria

Your workflow is ready when:
- ✅ All migrations run without errors
- ✅ End-to-end test completes successfully
- ✅ Script actors use checkpoint queries (not deprecated placeholders)
- ✅ LLM prompts only reference workflow inputs (no {session_X_output})
- ✅ Workflow has app_scope set (talent/news/write/research/contract)
- ✅ All conversations are tagged with action verbs
- ✅ Discovery queries return your conversations correctly
- ✅ Branching logic handles all cases
- ✅ Documentation is updated
- ✅ You can explain the data flow to someone else

---

## Step-by-Step Process

### Step 1: Create the Workflow (Registry Entry)

**File:** `migrations/0XX_create_workflow_NNNN_name.sql`

```sql
BEGIN;

INSERT INTO workflows (
    workflow_id,                    -- Choose next available ID
    workflow_name,                  -- Short, descriptive name
    workflow_description,           -- What it does, inputs/outputs
    max_total_session_runs,         -- Total runs across all conversations
    enabled
) VALUES (
    1126,
    'Profile Document Import',
    'Parse documents → Extract data → Validate → Import to DB. Output: profile_id',
    100,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

COMMIT;

-- Verify
SELECT workflow_id, workflow_name, workflow_description 
FROM workflows WHERE workflow_id = 1126;
```

**Test:** `sudo -u postgres psql -d turing -f migrations/0XX_create_workflow_NNNN_name.sql`

---

### Step 2: Create Conversations (Units of Work)

**File:** Same migration or separate file

**Pattern:** Use DO block with RETURNING to capture IDs

```sql
BEGIN;

DO $$
DECLARE
    v_actor_qwen INTEGER;
    v_actor_gemma INTEGER;
    v_conv_extract INTEGER;
    v_conv_validate INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b';
    SELECT actor_id INTO v_actor_gemma FROM actors WHERE actor_name = 'gemma2:latest';

    -- Conversation 1: Extract
    INSERT INTO conversations (
        conversation_name,              -- Human-readable name
        canonical_name,                 -- IMPORTANT: Reusable identifier
        conversation_description,       -- What this conversation does
        actor_id,                       -- Who executes it
        conversation_type,              -- single_actor, multi_turn, multi_actor_dialogue
        context_strategy,               -- isolated, inherit_previous, shared_conversation
        enabled
    ) VALUES (
        'w1126_extract_profile_data',
        'w1126_c1_extract',             -- Pattern: wXXXX_cN_shortname
        'Parse document and extract structured profile data into JSON',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    ) ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        conversation_description = EXCLUDED.conversation_description,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_extract;

    -- Conversation 2: Validate
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w1126_validate_profile_data',
        'w1126_c2_validate',
        'Independent validation of extracted data',
        v_actor_gemma,
        'single_actor',
        'isolated',
        true
    ) ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_validate;

    -- Link conversations to workflow (defines execution order)
    DELETE FROM workflow_conversations WHERE workflow_id = 1126;
    
    INSERT INTO workflow_conversations (
        workflow_id,
        conversation_id,
        execution_order,
        execute_condition,              -- always, on_success, on_failure
        on_success_action,              -- continue, skip_to, stop
        on_failure_action,              -- stop, retry, skip_to
        max_retry_attempts
    ) VALUES 
        (1126, v_conv_extract, 1, 'always', 'continue', 'stop', 1),
        (1126, v_conv_validate, 2, 'always', 'continue', 'stop', 1);

    RAISE NOTICE 'Created conversations: extract=%, validate=%', v_conv_extract, v_conv_validate;
END $$;

COMMIT;

-- Verify
SELECT 
    w.workflow_id,
    w.workflow_name,
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    c.canonical_name,
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 1126
ORDER BY wc.execution_order;
```

**Test:** Should see all conversations linked to workflow in correct order.

---

### Step 2b: Accessing Prior Conversation Outputs

⚠️ **IMPORTANT:** Template substitution (`{session_X_output}` placeholders) is **DEPRECATED** due to critical bugs in checkpoint reload. Use checkpoint queries instead.

**Pattern: Script Actors Querying Previous Outputs**

For script actors (Python, Node.js) that need outputs from prior conversations:

```python
# Import the utility
from core.checkpoint_utils import get_conversation_output
import os

# Get posting_id from environment
posting_id = int(os.environ['POSTING_ID'])

# Query specific conversation outputs
summary = get_conversation_output(posting_id, '3341')  # conversation_id
requirements = get_conversation_output(posting_id, '3338')

# Use the outputs
formatted_data = {
    'summary': summary,
    'requirements': requirements,
    'posting_id': posting_id
}

# Save to database, transform, validate, etc.
```

**Pattern: LLM Prompts Referencing Workflow Inputs**

For LLM actors, prompts can ONLY reference workflow input data (not prior conversation outputs):

```sql
-- GOOD: Reference workflow input variations
INSERT INTO instructions (instruction_text, ...)
VALUES (
'Analyze this job posting:
{posting_variations_param_1}

Extract the key skills and requirements.',
...
);

-- BAD: Do NOT use session_X_output placeholders (deprecated!)
-- This pattern is unreliable and will break:
'Previous summary:
{session_9_output}  ← BROKEN! Don't use this!'
```

**Pattern: Multi-Step Workflows**

If conversation B needs output from conversation A:

1. **Conversation A (LLM)**: Extract data, output JSON/text
2. **Conversation B (Script)**: Query A's output via checkpoint, process it, save result
3. **Conversation C (LLM)**: Use workflow inputs only OR let script actor (B) prepare the data

**Why Checkpoint Queries?**

✅ **Reliable**: Direct access to source of truth (`posting_state_checkpoints` table)  
✅ **Traceable**: Every value change recorded with timestamp  
✅ **Flexible**: Can transform, validate, aggregate data in script  
✅ **No hidden bugs**: No dependency on in-memory state being correct  

See `docs/TEMPLATE_VS_QUERY_ARCHITECTURE.md` for full architectural decision.

**Test:** For script actors, verify checkpoint queries work with mock posting_id.

---

### Step 2c: Tag Conversations (For Discovery)

**Purpose:** Tag conversations with application scope and action verbs so they can be discovered and reused across workflows.

**File:** Same migration (add after Step 2b)

```sql
-- Set application scope for this workflow
UPDATE workflows 
SET app_scope = 'talent'  -- talent, news, write, research, contract
WHERE workflow_id = 1126;

-- Tag conversation 1: Extract
SELECT tag_conversation(
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'w1126_c1_extract'),
    ARRAY['extract', 'transform']  -- What this conversation DOES
);

-- Tag conversation 2: Validate
SELECT tag_conversation(
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'w1126_c2_validate'),
    ARRAY['validate', 'verify']
);

-- Tag conversation 3: Save (example)
SELECT tag_conversation(
    (SELECT conversation_id FROM conversations WHERE canonical_name = 'w1126_c3_save'),
    ARRAY['save', 'transform']
);

COMMIT;

-- Verify tags applied
SELECT 
    c.canonical_name,
    c.app_scope,
    array_agg(ct.tag ORDER BY ct.tag) as tags
FROM conversations c
JOIN conversation_tags ct ON c.conversation_id = ct.conversation_id
WHERE c.canonical_name LIKE 'w1126%'
GROUP BY c.canonical_name, c.app_scope
ORDER BY c.canonical_name;
```

**Available Tags (by category):**

**Data Operations:**
- `fetch` - Retrieve data from external source (API, web, database)
- `extract` - Extract structured information from unstructured content
- `validate` - Check data quality, completeness, format correctness
- `transform` - Convert data from one format/structure to another
- `save` - Persist data to database or storage

**Analysis Operations:**
- `classify` - Categorize or label data into predefined classes
- `score` - Assign numerical rating or confidence score
- `rank` - Order items by importance, relevance, or quality
- `match` - Find relationships or similarities between entities
- `compare` - Identify differences and similarities between items

**Generation Operations:**
- `summarize` - Create concise summary of longer content
- `generate` - Create new content from scratch or templates
- `translate` - Convert content between languages
- `format` - Apply styling, structure, or presentation rules
- `combine` - Merge multiple inputs into unified output

**Reasoning Operations:**
- `analyze` - Deep examination to understand patterns, causes, implications
- `recommend` - Provide actionable suggestions based on analysis
- `explain` - Clarify reasoning, provide justification for decisions
- `critique` - Evaluate quality, identify weaknesses, suggest improvements

**Quality Operations:**
- `review` - Human or AI examination for approval/rejection
- `verify` - Confirm correctness against known truth or rules
- `audit` - Systematic examination for compliance or errors
- `detect_errors` - Identify mistakes, inconsistencies, quality issues

**Tag Selection Guidelines:**
- Choose 1-3 tags that describe what the conversation DOES (not what it processes)
- Use action verbs, not nouns (e.g., `extract` not `extraction`)
- Tag based on function, not domain (e.g., `match` works for jobs, articles, chapters, etc.)
- When in doubt, check tag definitions:
  ```sql
  SELECT tag, category, description, examples
  FROM conversation_tag_definitions
  ORDER BY category, tag;
  ```

**Discovery Examples:**

```sql
-- Find all extraction conversations across all apps
SELECT * FROM v_conversation_discovery 
WHERE 'extract' = ANY(tags);

-- Find talent.yoga matching conversations
SELECT * FROM v_conversation_discovery
WHERE app_scope = 'talent' 
  AND 'match' = ANY(tags);

-- Find all generation work
SELECT * FROM v_conversation_discovery
WHERE tags && ARRAY['generate', 'summarize', 'translate', 'format', 'combine'];
```

**Test:** Verify tags applied and discovery queries return expected conversations.

---

### Step 3: Create Instructions (The Prompts)

**File:** `migrations/0XX_create_workflow_NNNN_step3_instructions.sql`

**Pattern:** One instruction per conversation step

**IMPORTANT:** 
1. **Test prompts first** using `tools/llm_chat.py` (see "Prompt Development" section)
2. Use placeholders registered in Step 2b
3. Reference them with curly braces: `{placeholder_name}`

```sql
BEGIN;

-- Instruction for Conversation 1: Extract
INSERT INTO instructions (
    instruction_name,
    conversation_id,                -- Link to conversation
    step_number,                    -- Sequential within conversation
    step_description,
    instruction_text,               -- RENAMED from prompt_template in newer schemas
    instruction_timeout_seconds,    -- RENAMED from timeout_seconds
    is_terminal,                    -- true = no automatic continuation
    enabled
)
SELECT
    'Extract Profile Data from Document',
    conversation_id,
    1,
    'Parse document and extract structured JSON with profile/work history/skills',
    $PROMPT$You are an expert at extracting structured career data from documents.

DOCUMENT:
{document_text}                     -- Placeholder registered in Step 2b

Extract ALL information into valid JSON format:

{
  "profile": {
    "full_name": "string (REQUIRED)",
    "email": "string or null",
    "current_title": "string or null",
    ...
  },
  "work_history": [...],
  "skills": [...],
  "languages": [...]
}

RULES:
1. Output ONLY valid JSON
2. If missing data, use null
3. Dates in YYYY-MM-DD format
...$PROMPT$,
    300,
    false,
    true
FROM conversations
WHERE canonical_name = 'w1126_c1_extract';

COMMIT;

-- Verify
SELECT 
    c.conversation_name,
    i.instruction_id,
    i.step_number,
    i.instruction_name,
    i.instruction_timeout_seconds,
    LENGTH(i.instruction_text) as prompt_length,
    -- Extract placeholders used
    (SELECT string_agg(match[1], ', ') 
     FROM regexp_matches(i.instruction_text, '\{([^}]+)\}', 'g') AS match
    ) as placeholders_used
FROM conversations c
JOIN instructions i ON c.conversation_id = i.conversation_id
WHERE c.canonical_name LIKE 'w1126_%'
ORDER BY c.conversation_id, i.step_number;
```

**Test:** 
- Verify instructions are linked to conversations
- Check that all `placeholders_used` were registered in Step 2b
- If any placeholders are missing, go back and add them to placeholder_definitions!

---

### Step 4: Create Instruction Steps (Branching Logic)

**File:** Same or separate migration

**Pattern:** Define what happens after each instruction based on output

```sql
BEGIN;

-- Step: If extraction succeeds, go to validation
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,                 -- Which instruction triggers this
    branch_condition,               -- [PASS], [FAIL], [SUCCESS], etc.
    next_conversation_id,           -- Jump to different conversation
    branch_priority,                -- Higher = evaluated first (DESC order)
    branch_description,
    enabled
)
SELECT
    'Extraction successful - validate data',
    i.instruction_id,
    '[SUCCESS]',
    c_next.conversation_id,
    10,
    'If extraction produced valid JSON, proceed to validation',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c2_validate'
WHERE c_from.canonical_name = 'w1126_c1_extract'
  AND i.step_number = 1;

-- Step: If extraction fails, go to error handling
INSERT INTO instruction_steps (
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
)
SELECT
    'Extraction failed - generate error report',
    i.instruction_id,
    '[FAIL]',
    c_next.conversation_id,
    5,
    'If extraction failed, generate human-readable error report',
    true
FROM instructions i
JOIN conversations c_from ON i.conversation_id = c_from.conversation_id
JOIN conversations c_next ON c_next.canonical_name = 'w1126_c4_error'
WHERE c_from.canonical_name = 'w1126_c1_extract'
  AND i.step_number = 1;

COMMIT;

-- Verify
SELECT 
    ist.instruction_step_id,
    ist.instruction_step_name,
    i.instruction_name as from_instruction,
    ist.branch_condition,
    c_next.conversation_name as next_conversation,
    ist.branch_priority
FROM instruction_steps ist
JOIN instructions i ON ist.instruction_id = i.instruction_id
JOIN conversations c ON i.conversation_id = c.conversation_id
LEFT JOIN conversations c_next ON ist.next_conversation_id = c_next.conversation_id
WHERE c.canonical_name LIKE 'w1126_%'
ORDER BY ist.branch_priority DESC;
```

**Test:** Should see branching logic defined.

---

## Common Patterns

### Context Strategy Options

- **`isolated`**: Each run is independent (most common)
- **`inherit_previous`**: Can access previous conversation outputs via `{session_rN_output}`
- **`shared_conversation`**: Has access to all previous conversations in workflow

### Conversation Types

- **`single_actor`**: One actor, one or more instructions
- **`multi_turn`**: One actor, multiple back-and-forth exchanges
- **`multi_actor_sequential`**: Multiple actors in sequence
- **`multi_actor_dialogue`**: Multiple actors in conversation

### Branch Conditions

- **`[PASS]`** / **`[FAIL]`**: Simple success/failure
- **`[SUCCESS]`** / **`[ERROR]`**: For database operations
- **`[SCORE > 80]`**: Conditional logic (requires parsing in runner)
- **`*`**: Catch-all (lowest priority)

### Placeholder Variables

Available in `prompt_template`:

- **`{document_text}`**: Input document content
- **`{session_r1_output}`**: Output from conversation 1
- **`{session_r2_output}`**: Output from conversation 2
- **`{profile_id}`**: Profile ID (if loaded from DB)
- Custom placeholders defined by runner

---

## Testing Checklist

After each step:

1. ✅ Run migration: `sudo -u postgres psql -d turing -f migrations/0XX_file.sql`
2. ✅ Verify structure with SELECT queries (provided in each step)
3. ✅ Check for errors in output
4. ✅ Test with actual runner (once instructions complete)

---

## Example: Complete Workflow

See Migration 044 for Workflow 1126 as reference implementation.

**Full Flow:**
1. Create workflow registry entry
2. Create 4 conversations (extract, validate, import, error)
3. Link conversations to workflow via workflow_conversations
4. Add instructions to each conversation
5. Add instruction_steps for branching
6. Create Python runner that executes the workflow

---

## Prompt Development with llm_chat.py

Before writing prompts in the schema, **develop and test them conversationally** using `tools/llm_chat.py`. This allows you to:
- Test prompt variations quickly
- Have multi-turn conversations with models to refine instructions
- See actual LLM responses before committing to the database
- Iterate on branch conditions based on observed outputs

### How to Use llm_chat.py

**Basic Commands:**

```bash
# Start a conversation and send first message
python3 tools/llm_chat.py qwen2.5:7b send "You are an expert at extracting structured career data. Extract JSON from this text: John Doe, Software Engineer at Google since 2020."

# Continue the conversation (maintains context)
python3 tools/llm_chat.py qwen2.5:7b send "Good! Now add [SUCCESS] at the end of your output."

# View full conversation history
python3 tools/llm_chat.py qwen2.5:7b show

# Start fresh conversation (clears history)
python3 tools/llm_chat.py qwen2.5:7b clear
```

**Conversation State:**
- Each model maintains separate conversation history in `temp/conversation_{model}.json`
- Context is preserved across multiple `send` commands
- Use `clear` to reset and start fresh
- Use `show` to review what the model remembers

**Typical Workflow:**

1. **Initial Prompt Test:**
   ```bash
   python3 tools/llm_chat.py qwen2.5:7b send "Extract profile data from this document: [paste test doc]"
   ```

2. **Refine Instructions:**
   ```bash
   python3 tools/llm_chat.py qwen2.5:7b send "Please output ONLY valid JSON, no extra text."
   python3 tools/llm_chat.py qwen2.5:7b send "Add [SUCCESS] at the end if extraction worked."
   ```

3. **Test Edge Cases:**
   ```bash
   python3 tools/llm_chat.py qwen2.5:7b send "What if the document has no dates?"
   python3 tools/llm_chat.py qwen2.5:7b send "Try this malformed document: [bad data]"
   ```

4. **Copy Final Prompt to Schema:**
   Once you've refined the prompt through conversation, copy the successful version to your migration:
   ```sql
   INSERT INTO instructions (prompt_template, ...) VALUES (
       'You are an expert at extracting structured career data.
       
       Output ONLY valid JSON with this structure: {...}
       
       Add [SUCCESS] at the end if extraction succeeded.',
       ...
   );
   ```

### Real Example: Testing Branch Markers

**Problem:** Workflow 1126 extraction always takes DEFAULT branch because qwen2.5 doesn't output `[SUCCESS]`.

**Solution:** Test prompt with llm_chat.py first:

```bash
# Clear previous conversation
python3 tools/llm_chat.py qwen2.5:7b clear

# Test without explicit instruction
python3 tools/llm_chat.py qwen2.5:7b send "Extract JSON from: John Doe, Software Engineer at Google since 2020."
# Result: Only outputs JSON, no marker ❌

# Test WITH explicit instruction
python3 tools/llm_chat.py qwen2.5:7b send "Extract JSON from: John Doe, Software Engineer at Google since 2020. Output the JSON, then on a new line output [SUCCESS]."
# Result: Outputs JSON followed by [SUCCESS] ✅
```

**Lesson Learned:** LLMs need explicit instruction to output branch markers. Update prompt in migration:

```sql
-- BEFORE (missing marker instruction)
'You are an expert at extracting data. Output JSON: {...}'

-- AFTER (includes marker instruction)
'You are an expert at extracting data.

Output JSON: {...}

IMPORTANT: After the JSON, output [SUCCESS] on a new line if extraction succeeded.'
```

### Tips for Prompt Development

- **Start simple**: Test core instruction first, add refinements iteratively
- **Test output markers**: Verify LLM actually outputs `[SUCCESS]`, `[FAIL]` etc. using llm_chat.py
- **Check JSON validity**: Ask model to output structured data, verify it parses
- **Use multiple models**: Test same prompt with different models (qwen2.5:7b, gemma2:latest, phi3:latest)
- **Document what worked**: Add comments in migration explaining prompt design choices
- **Iterate in conversation**: Use multi-turn dialogue to refine instructions before committing to schema

### Alternative: Shell Script (Archived)

The bash version `archive/llm_conversation.sh` provides similar functionality:
```bash
# Source the script
source archive/llm_conversation.sh qwen2.5:7b

# Start conversation
init_conversation

# Send messages
talk_to_llm "Your message here"

# View history
show_conversation
```

**Use Python version (`llm_chat.py`) for new work** - it's cleaner and easier to maintain.

---

## Anti-Patterns (Don't Do This)

❌ **Hardcoding conversation_id values** (11261, 11262, etc.)  
✅ **Use auto-increment with RETURNING**

❌ **Putting prompts in Python code**  
✅ **Store prompts in instructions.prompt_template**

❌ **Creating one giant migration**  
✅ **Break into testable steps**

❌ **Forgetting canonical_name**  
✅ **Always set canonical_name for reusability**

❌ **Not using instruction_steps**  
✅ **Define branching logic in schema**

❌ **Manually calculating IDs (MAX(id) + 1)**  
✅ **Let PostgreSQL sequences handle it (RETURNING id)**

---

## Database ID Management Best Practices

**Problem:** When inserting rows with SERIAL/auto-increment primary keys, there are two approaches:
1. Let the database sequence assign IDs automatically (RECOMMENDED)
2. Manually calculate next ID with `MAX(id) + 1` and insert explicitly

**Why Option 1 is better:**

### ✅ Option 1: Let PostgreSQL Handle It (RECOMMENDED)

```python
# Don't specify skill_id, let DEFAULT nextval() work
cursor.execute("""
    INSERT INTO skill_aliases (skill_name, skill_alias, language, confidence, created_by)
    VALUES (%s, %s, 'en', 1.0, 'taxonomy_expander')
    RETURNING skill_id
""", (skill_name, skill_name))

skill_id = cursor.fetchone()['skill_id']  # Get auto-generated ID
```

**Benefits:**
- ✅ No sequence sync issues
- ✅ No duplicate key conflicts
- ✅ Works correctly with concurrent inserts
- ✅ Standard PostgreSQL pattern
- ✅ Simpler code, less error-prone

### ❌ Option 2: Manual ID Calculation (AVOID)

```python
# Anti-pattern: Don't do this!
cursor.execute("SELECT COALESCE(MAX(skill_id), 0) + 1 FROM skill_aliases")
next_id = cursor.fetchone()[0]

cursor.execute("""
    INSERT INTO skill_aliases (skill_id, skill_name, ...)
    VALUES (%s, %s, ...)
""", (next_id, skill_name))
```

**Problems:**
- ❌ Sequence gets out of sync (MAX=835, sequence=901)
- ❌ Duplicate key errors when sequence advances
- ❌ Requires manual sequence resync: `SELECT setval('table_id_seq', MAX(id))`
- ❌ Race conditions with concurrent inserts
- ❌ More complex error handling

**When to use Option 2:**
- Never for new code
- Only if you need specific ID values for some reason (rare)
- If using, must keep sequence in sync with every insert

**Real Example - taxonomy_expander.py Bug:**

```python
# BEFORE (broken):
skill_id = self._get_next_skill_id()  # Calculates MAX + 1
cursor.execute("INSERT INTO skill_aliases (skill_id, ...) VALUES (%s, ...)", (skill_id,))
# Result: Duplicate key errors, sequence out of sync

# AFTER (fixed):
cursor.execute("INSERT INTO skill_aliases (...) VALUES (...) RETURNING skill_id")
skill_id = cursor.fetchone()['skill_id']  # Use auto-generated ID
# Result: Works perfectly, no conflicts
```

**Lesson:** If a table has a SERIAL primary key with an auto-increment sequence, USE IT! Don't fight the database.

---

## Workflow Creation Checklist

Use this checklist when creating a new workflow:

- [ ] **Step 1: Create workflow registry entry**
  - [ ] Choose next available workflow_id
  - [ ] Write clear workflow_description with inputs/outputs
  - [ ] Test: Verify workflow appears in `workflows` table

- [ ] **Step 2: Create conversations**
  - [ ] Define canonical_names (w{id}_c{n}_{name})
  - [ ] Choose appropriate actors for each conversation
  - [ ] Link to workflow via `workflow_conversations` with execution_order
  - [ ] Test: Verify conversations linked in correct order

- [ ] **Step 2b: Data access pattern** ⚠️ **CRITICAL**
  - [ ] Script actors: Import `from core.checkpoint_utils import get_conversation_output`
  - [ ] Script actors: Query checkpoints, don't use template substitution
  - [ ] LLM prompts: Only reference workflow inputs (`{posting_variations_param_1}`)
  - [ ] NO `{session_X_output}` placeholders (deprecated and broken!)
  - [ ] Test: Verify checkpoint queries return expected data

- [ ] **Step 2c: Tag conversations** ⚠️ **CRITICAL**
  - [ ] Set workflow app_scope (talent/news/write/research/contract)
  - [ ] Tag each conversation with 1-3 action verbs (extract, validate, match, etc.)
  - [ ] Use `tag_conversation(conv_id, ARRAY['tag1', 'tag2'])`
  - [ ] Test: Query `v_conversation_discovery` to verify tags applied

- [ ] **Step 3: Create instructions**
  - [ ] Write prompts using `{placeholder_name}` syntax for workflow inputs only
  - [ ] For script actors: Use checkpoint queries in code (not placeholders)
  - [ ] Set appropriate timeout_seconds (consider model speed)
  - [ ] Mark terminal instructions with `is_terminal = true`
  - [ ] Test: Verify prompts render correctly with sample data

- [ ] **Step 4: Create instruction_steps (branching)**
  - [ ] Define branch conditions ([SUCCESS], [FAIL], [PASS], etc.)
  - [ ] Route to next conversations or NULL (terminal)
  - [ ] Set branch_priority (higher = checked first)
  - [ ] Test: Verify branching logic is complete (no dead ends)

- [ ] **Step 5a: Register workflow trigger** (production architecture)
  - [ ] Create MANUAL trigger in workflow_triggers table
  - [ ] Set timeout_minutes and max_concurrent_runs
  - [ ] Define default_parameters structure
  - [ ] Note: Full scheduler/executor system to be built later
  - [ ] For now: Use CLI runner for testing

- [ ] **Step 5b: Create Python CLI runner** (for testing/development)
  - [ ] Import `WorkflowExecutor` from core.workflow_executor
  - [ ] Handle input loading (file, text, database)
  - [ ] Execute workflow with placeholder substitution
  - [ ] Parse final output (profile_id, skill_count, etc.)
  - [ ] Test: End-to-end workflow execution

- [ ] **Integration testing**
  - [ ] Test with real data
  - [ ] Verify all branches work (success, failure, edge cases)
  - [ ] Check LLM interaction logs
  - [ ] Validate database writes
  - [ ] Test chaining to downstream workflows

---

## Quick Reference: Table Relationships

```
workflows (1) ──< workflow_conversations (M) >── conversations (1)
      ↓                                                ↓
workflow_triggers (M)                            instructions (M)
      ↓                                                ↓
trigger_executions (M)                          instruction_steps (M)
      ↓
workflow_runs (M)
```

**Core Schema:**
- `workflow_conversations.workflow_id` → `workflows.workflow_id`
- `workflow_conversations.conversation_id` → `conversations.conversation_id`
- `instructions.conversation_id` → `conversations.conversation_id`
- `instruction_steps.instruction_id` → `instructions.instruction_id`
- `instruction_steps.next_conversation_id` → `conversations.conversation_id` (optional)

**Orchestration Schema (Production):**
- `workflow_triggers.workflow_id` → `workflows.workflow_id`
- `trigger_executions.trigger_id` → `workflow_triggers.trigger_id`
- `trigger_executions.workflow_run_id` → `workflow_runs.workflow_run_id`

---

## Production Architecture: Workflow Triggers

**Note:** Turing has a complete orchestration system through `workflow_triggers` table. This enables:
- **SCHEDULE** triggers (cron-based recurring execution)
- **EVENT** triggers (database event monitoring)
- **MANUAL** triggers (on-demand execution via API/UI)
- **DEPENDENCY** triggers (chain workflows together)

**Why we're not using it yet:**
The trigger system requires a scheduler/executor daemon that:
1. Monitors `workflow_triggers` table for ready-to-run triggers
2. Creates entries in `trigger_executions` when triggered
3. Spawns `workflow_runs` and tracks execution
4. Updates trigger statistics (success/failure counts, next_scheduled_run)

**Current approach (Step 5b - CLI runner):**
For development and testing, we use a direct CLI runner that:
- ✅ Validates workflow setup
- ✅ Executes workflow conversations in order
- ✅ Handles branching logic
- ✅ Returns results immediately
- ❌ Doesn't track in trigger_executions/workflow_runs
- ❌ No scheduling/monitoring/retry logic

**Migration path:**
1. **Now:** Use CLI runner for testing (validate workflow logic works)
2. **Soon:** Build trigger executor daemon (production orchestration)
3. **Later:** Add monitoring UI, retry policies, alerting, etc.

**Step 5a exists** to register the trigger definition now, so when we build the executor, Workflow 1126 is already configured and ready to go.

---

## Q&A: Workflow Design Decisions

### Q1: Why separate conversations instead of one big prompt?

**A:** [Answer from Gershon...]

### Q2: When should I use `delegate_actor_id` vs regular actor_id?

**A:** [Answer from Gershon...]

### Q3: How do I handle optional vs required placeholders?

**A:** [Answer from Gershon...]

### Q4: What's the difference between `is_terminal` in instructions vs NULL in instruction_steps.next_conversation_id?

**A:** [Answer from Gershon...]

### Q5: Should every workflow have an error handling conversation?

**A:** [Answer from Gershon...]

### Q6: How do I test workflows without committing data to production tables?

**A:** [Answer from Gershon...]

### Q7: What happens if an LLM times out or produces invalid output?

**A:** [Answer from Gershon...]

### Q8: Can workflows call other workflows?

**A:** [Answer from Gershon...]

---

## Next Steps

1. Follow this cookbook for Workflow 1126
2. Document any new patterns discovered
3. Update cookbook with lessons learned
4. Use as template for future workflows

---

**Questions? See:**
- Workflow 1122 (profile_skill_extraction) - Simple 3-conversation example
- Migration 044 (Workflow 1126) - Reference implementation of this cookbook
- `/docs/TURING_SCHEMA.md` - Full schema documentation
