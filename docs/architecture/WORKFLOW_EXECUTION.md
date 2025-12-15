# Turing Workflow Execution

**Version:** 1.5  
**Last Updated:** December 11, 2025  
**Purpose:** Complete guide to workflow execution, wave processing, and branching logic

**Recent Updates:**
- **Dec 11: Added `extracted_summary` to posting data variables (skills extraction bug fix)**
- Dec 7: Dynamic template variable extraction (no more hardcoded conversation IDs)
- Dec 5: Parallel convergence pattern (`wait_for_group`) design finalized
- Dec 4: WF3001 completed 100% (1,689 postings processed)
- Nov 25: Traceability system - actual substituted prompts stored in interactions

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Execution Flow Overview

```
1. Wave Batch Processor starts
     ↓
2. Load workflow definition (conversations, instructions, branching)
     ↓
3. Fetch postings to process (WHERE extracted_summary IS NULL)
     ↓
4. Initialize PostingState for each posting
     ↓
5. GROUP postings by current execution_order (WAVE)
     ↓
6. Load actor/model for that conversation (ONCE)
     ↓
7. FOR EACH posting in wave:
     - Execute instruction (LLM or script actor)
     - Evaluate branch conditions
     - Update PostingState.next_conversation_id
     ↓
8. REGROUP postings by next_conversation_id
     ↓
9. REPEAT steps 5-8 until all postings reach TERMINAL
     ↓
10. Save results to database
```

**Critical:** Wave processor handles **both LLM and script actors** uniformly. This is the core value of Turing - multi-actor workflows where any actor type can be used at any step.

---

## Multi-Actor Processing (Nov 21, 2025)

### The Big Idea: Unified Actor Execution

Turing's wave processor executes **all actor types** in waves:
- **LLM actors** (gemma3, qwen2.5, phi3, etc.) - AI model inference
- **Script actors** (db_job_fetcher, summary_saver, sql_query_executor) - Python scripts

### Why This Matters

Traditional workflow systems separate:
- "AI tasks" go to LLM orchestrator
- "Script tasks" go to script runner
- Complex handoffs, dual infrastructure, coordination problems

**Turing's approach:** One execution engine, all actor types!

```python
# Wave 3: LLM actor
execute_wave(conversation_id=3335, actor='gemma3:1b', postings=[...])
# → Calls actor_router.execute_instruction(44, prompt) → ollama API

# Wave 10: Script actor  
execute_wave(conversation_id=9168, actor='summary_saver', postings=[...])
# → Calls actor_router.execute_instruction(77, input) → python script

# Same execution path! Same wave logic! Same branching!
```

### Historical Bug (Fixed Nov 21, 2025)

**The Problem:**
- Someone added a guard in `wave_executor.py` (lines 247-256) that **skipped script actors**
- When wave processor encountered a script actor, it would:
  1. Log warning: "Script actors should not be processed by wave_processor"
  2. Return 0 (no postings processed)
  3. Reload same postings next iteration
  4. Hit infinite loop (Wave 97, 98, 99, 100...)
  5. Exceed max_waves limit, workflow fails

**The Fix:**
- Removed the skip check (commit: Nov 21, 2025)
- Wave processor now handles script actors natively
- Script actors execute via `actor_router.execute_instruction()` (same as LLMs)
- Branching, checkpointing, metrics all work identically

**Impact:**
- Multi-actor workflows (LLM + script) now work seamlessly
- No more infinite loops on script actors
- Unified monitoring (all actors in same wave metrics)

### Implementation Details

From `core/wave_processor/wave_executor.py` lines 240-260:

```python
# Get prompt template (for LLM actors) or prepare for script execution
actor_type = conv.get('actor_type', 'llm')  # Default to llm if not specified
prompt_template = conv.get('prompt_template')

# Only LLM actors require prompt templates
# Script actors execute without templates (they get instructions via actor_router)
if actor_type == 'llm' and not prompt_template:
    logger.error("no_prompt_template", extra={
        'conversation_id': conversation_id,
        'conversation_name': conv['canonical_name']
    })
    return 0

# Prepare input for actor
# LLM actors: render prompt template with posting data
# Script actors: use template as-is (it contains JSON/structured input)
if actor_type == 'llm' and prompt_template:
    prompt = render_prompt(prompt_template, posting)
elif actor_type == 'script' and prompt_template:
    # Script actors may have structured input in template
    prompt = render_prompt(prompt_template, posting)
else:
    # No template (shouldn't happen after earlier check)
    prompt = f'{{"posting_id": {posting.posting_id}}}'
```

Then execution (same for both types):

```python
# Execute actor (unified for LLM and script)
execution_result = execute_instruction(actor_id, prompt, timeout=300)

# Process result (identical for both)
if execution_result['status'] == 'SUCCESS':
    circuit_breaker.record_success(actor_id)
    output = execution_result['response']
else:
    circuit_breaker.record_failure(actor_id)
    output = f"[{execution_result['status']}]"

# Evaluate branches (identical for both)
next_conv_id = evaluate_branch_conditions(output, branches, ...)

# Write event (type differs)
event_type = 'conversation_completed' if actor_type == 'llm' else 'script_execution_completed'
```

### Benefits of Unified Execution

✅ **Simplicity**: One code path for all actors, easier to maintain
✅ **Flexibility**: Mix LLM and script actors freely in any workflow
✅ **Consistency**: Branching, metrics, monitoring work identically
✅ **Efficiency**: Script actors benefit from wave batching (execute once per batch)
✅ **Debugging**: Same logging, error handling, circuit breakers for all

### Example Multi-Actor Workflow (3001)

```
Step 1: db_job_fetcher (SCRIPT)     → Fetch jobs from API
Step 2: sql_query_executor (SCRIPT) → Check if summary exists
Step 3: gemma3:1b (LLM)             → Extract job summary
Step 4: gemma2:latest (LLM)         → Grade extraction
Step 5: qwen2.5:7b (LLM)            → Second opinion grade
Step 9: phi3:latest (LLM)           → Format standardization
Step 10: summary_saver (SCRIPT)     → Save to database
Step 11: sql_query_executor (SCRIPT) → Check if skills exist
Step 12: qwen2.5:7b (LLM)           → Extract skills
```

All executed in waves, unified execution engine, seamless transitions between actor types!

---

## Parallel Execution Patterns (Dec 2025)

### Fan-Out: One Parent → Many Children

Used when a single interaction spawns multiple parallel tasks.

**Example: WF1125 Multi-Agent Profile Analysis**
```
[Profile Text]
       ↓
    ┌──┴──┬──────┬──────┬──────┐
    ↓     ↓      ↓      ↓      ↓
[Tech] [Domain] [Lead] [Creat] [Biz]   ← parallel_group=1
    └──┬──┴──────┴──────┴──────┘
       ↓
[Synthesizer]  ← wait_for_group=true
       ↓
[Skill Saver]
```

**Schema:**
```sql
-- All 5 experts in parallel_group=1
UPDATE workflow_conversations SET parallel_group = 1
WHERE workflow_id = 1125 AND conversation_id IN (9208, 9210, 9211, 9212, 9213);

-- Synthesizer waits for all to complete
UPDATE workflow_conversations SET wait_for_group = true 
WHERE workflow_id = 1125 AND conversation_id = 9214;
```

### Fan-In: Many Parents → One Child (wait_for_group)

The `wait_for_group` flag on a conversation means:
> "Don't create my child interaction until ALL siblings in my parallel_group have completed."

**Implementation in `interaction_creator.py`:**
1. When parent completes, check if target conversation has `wait_for_group=true`
2. If yes, check if ALL conversations in the same `parallel_group` have completed
3. If not all done, skip child creation (another sibling will trigger it)
4. If all done, create ONE child with ALL sibling outputs as parents

**Key fields:**
- `workflow_conversations.parallel_group` - Groups concurrent steps
- `workflow_conversations.wait_for_group` - Sync barrier before next step
- `interactions.parent_interaction_id` - Single parent (legacy)
- `interactions.input_interaction_ids` - All parent IDs (for fan-in)

### Production Workflows Using Parallel Patterns

| Workflow | Pattern | Description |
|----------|---------|-------------|
| WF1125 | Fan-out + Fan-in | 5 expert agents → synthesizer → saver |
| WF3001 | Sequential | Linear job processing pipeline |
| WF3004 | Batch iteration | Fetch orphans → classify → repeat |

---

## Wave Processing

### What is a Wave?

A wave is **all postings at the same execution_order**. Instead of loading the model N times (once per posting), we load it ONCE and process all postings in that wave.

### Example Wave Execution

```
Wave 1 (execution_order 1): fetch_db_jobs
  - Postings: [3, 4, 5, 7, 8, ...]
  - Actor: fetch_db_jobs (script)
  - Output: Job descriptions loaded into memory

Wave 2 (execution_order 2): check_summary_exists
  - Postings: [3, 4, 5, 7, 8, ...]
  - Actor: idempotency_check (script)
  - Output: [SKIP] or [RUN] for each posting
  - Branching: 
    - [SKIP] → save_summary_check_ihl (execution_order 10)
    - [RUN] → gemma3_extract (execution_order 3)
  - After wave: postings split into two groups!

Wave 3 (execution_order 3): gemma3_extract
  - Postings: [3, 4, 5, ...] (only [RUN] postings)
  - Actor: gemma3:4b (LLM)
  - Model loaded ONCE, processes all postings
  - Output: Extracted summaries

Wave 10 (execution_order 10): save_summary_check_ihl
  - Postings: [2, 169, 858] ([SKIP] postings from wave 2) + [3, 4, 5, ...] (completed postings from wave 9)
  - Actor: save_summary (script)
  - Saves results to postings.extracted_summary
```

**Key Insight**: Each posting follows its own path, but postings at the same execution_order are processed together for efficiency.

---

## Execution Order Grouping (Nov 17, 2025)

### Critical Optimization

Wave processor groups postings by **execution_order first**, then conversation_id second.

### Problem (Old Pattern)

```python
# Grouped only by conversation_id
Wave 1: check_summary_exists (12 postings), gemma3_extract (8 postings), llama3_extract (3 postings)
# Result: Load gemma3 → unload → load llama3 → unload → load gemma3 again (inefficient!)
```

### Solution (New Pattern)

```python
# Grouped by execution_order → conversation_id (two-level)
Wave 1 - execution_order 2:
  check_summary_exists (67 postings)  # All step 2 postings first!

Wave 2 - execution_order 3:
  gemma3_extract (36 postings)        # All step 3 postings together!

Wave 3 - execution_order 4:
  gemma2_grade (20 postings)          # All step 4 postings together!
```

### Implementation

From `core/wave_batch_processor.py` lines 1200-1240:

```python
# Group postings by execution_order first
exec_order_groups = {}
for posting in postings:
    conv_id = posting.current_conversation_id
    exec_order = workflow_definition['conversations'][conv_id]['execution_order']
    if exec_order not in exec_order_groups:
        exec_order_groups[exec_order] = []
    exec_order_groups[exec_order].append(posting)

# Process execution orders sequentially (lowest first)
for exec_order in sorted(exec_order_groups.keys()):
    order_postings = exec_order_groups[exec_order]
    
    # Further group by conversation_id within this execution_order
    conv_groups = {}
    for posting in order_postings:
        conv_id = posting.current_conversation_id
        if conv_id not in conv_groups:
            conv_groups[conv_id] = []
        conv_groups[conv_id].append(posting)
    
    # Log wave start with execution_order
    logger.info("wave_batch_started", extra={
        'wave_number': wave_num,
        'execution_order': exec_order,
        'conversation_count': len(conv_groups),
        'active_postings': len(order_postings)
    })
    
    # Process each conversation group at this execution_order
    for conv_id, group_postings in conv_groups.items():
        self._process_wave(conv_id, group_postings)
```

### Benefits

- ✅ **Model loaded once per step** for all postings (not per posting)
- ✅ **Dramatically reduces load/unload cycles** when postings branch
- ✅ **Sequential step completion**: ALL step 3 completes before ANY step 4 starts
- ✅ **Efficient GPU utilization**: Fewer context switches

### Monitoring Impact

**Before** (conversation_id grouping):
```
RECENT ACTIVITY (last 5 minutes):
  Step  3: 12 postings
  Step  2: 8 postings   ← jumps back
  Step 10: 3 postings   ← jumps forward
  Step  3: 5 postings   ← jumps back again (model reload!)
```

**After** (execution_order → conversation_id grouping):
```
RECENT ACTIVITY (last 5 minutes):
  Step  2: 67 postings   ← ALL step 2 first
  Step  3: 36 postings   ← THEN ALL step 3
  Step  4: 20 postings   ← THEN ALL step 4
```

---

## Branching Logic

### How Branching Works

1. Actor executes instruction, produces output
2. System reads all `instruction_steps` for that instruction (ordered by `branch_priority`)
3. For each step, check if `branch_condition` appears in output
4. First match wins → route to `next_conversation_id` or `next_instruction_id`
5. If no match, posting terminates (workflow ends for that posting)

### Branch Condition Matching

Simple substring match. If output contains `[SKIP]`, the `[SKIP]` branch is taken.

**Example Output**:
```json
{
  "should_skip": true,
  "branch": "[SKIP]",
  "reason": "extracted_summary already exists (1234 chars)"
}
```

The system sees `[SKIP]` in the output → routes to the `[SKIP]` branch.

### Common Branch Patterns

| Branch | Use Case | Example |
|--------|----------|---------|
| `[SKIP]` | Idempotency checks | Work already done, skip ahead |
| `[RUN]` | Proceed with work | Work needed, continue processing |
| `[RATE_LIMITED]` | API rate limits | Pause processing, wait before retry |
| `[ERROR]` | Error handling | Route to error recovery conversation |
| `[DEFAULT]` | Catch-all | If no other condition matches |

### Branch Priority

Lower priority number = evaluated first. Use this for specific conditions before general ones.

```sql
-- Example: Specific before general
INSERT INTO instruction_steps (branch_condition, next_conversation_id, branch_priority)
VALUES 
  ('[ERROR]', error_handler_id, 1),      -- Check errors first
  ('[SKIP]', next_step_id, 2),           -- Then idempotency
  ('[RUN]', current_step_id, 3),         -- Then proceed
  ('[DEFAULT]', fallback_id, 99);        -- Catch-all last
```

### ⚠️ Known Issue: Branching Doesn't Stop After First Match

**Problem (Nov 25, 2025):** Current implementation evaluates ALL matching conditions at ALL priority levels, creating multiple children when only one expected.

**Example bug:**
```sql
-- Conversation 3337 branching rules:
Priority 10: [PASS] → Format (3341)    -- Matches
Priority 0:  *      → Ticket (3340)    -- Also matches (wildcard)

-- Result: Creates BOTH children (wrong!)
```

**Expected behavior:** Stop after first match at highest priority.

**Workaround:** Avoid wildcard catch-all rules (`*`) when higher priority rules exist.

**Proper fix:** Update `runner.py` branching logic to stop after first match:

```python
# Fixed logic (not yet implemented)
for priority in sorted(priorities, reverse=True):  # High to low
    matched = False
    for rule in rules_at_priority:
        if rule.condition_matches(output):
            children.append(create_child(rule.next_conversation))
            matched = True
            break  # Stop checking this priority
    if matched:
        break  # Stop checking lower priorities
```

**Status:** Known bug, workaround in place (delete wildcard rules). Proper fix pending.

---

## Data Flow: Database vs In-Memory

### Database Storage (persistent)

- `postings.job_description`: Input data
- `postings.extracted_summary`: Final output (saved at wave 10)
- `postings.taxonomy_skills`: Final output (saved at wave 15)
- `postings.ihl_score`: Final output (saved at wave 19)

### In-Memory Storage (temporary, during workflow execution)

- `PostingState.outputs`: Intermediate results from each conversation
- `PostingState.conversation_outputs`: Conversation outputs for multi-turn workflows (conversation_1_output, conversation_2_output, etc.)
- Actor output strings passed between conversations

### Why In-Memory?

Efficiency! Intermediate results (grades, improvements, formatting) don't need database writes. Only final results are persisted.

### Example Flow

```
Wave 3: gemma3_extract
  → Output: "Summary: Software Engineer..." (2000 chars)
  → Stored in PostingState.outputs[3335] (in-memory)

Wave 4: gemma2_grade
  → Input: PostingState.outputs[3335] (from memory)
  → Output: "Grade: 8/10" (9 chars)
  → Stored in PostingState.outputs[3336] (in-memory)

Wave 5: gemma3_improve
  → Input: PostingState.outputs[3335] + PostingState.outputs[3336] (from memory)
  → Output: "Improved summary..." (2200 chars)
  → Stored in PostingState.outputs[3337] (in-memory)

...

Wave 10: save_summary_check_ihl
  → Input: PostingState.outputs[3339] (final formatted summary)
  → Action: UPDATE postings SET extracted_summary = ... WHERE posting_id = ...
  → Stored in database (persistent)
```

---

## Execution Order and Idempotency

### Execution Order Strategy

- **Order 1**: Fetch data (always first)
- **Order 2, 11, 16**: Idempotency checks (before expensive operations)
- **Order 3-9**: Extraction pipeline (extract → grade → improve → format)
- **Order 10**: Save extraction results, check IHL needs
- **Order 12-15**: Skills extraction pipeline
- **Order 17-19**: IHL scoring pipeline

### Idempotency Pattern

```
Check Conversation (order N)
  ↓
  If work done: [SKIP] → Jump ahead (order N+X)
  If work needed: [RUN] → Proceed (order N+1)
```

### Example: Workflow 3001 Idempotency Checks

**1. check_summary_exists** (order 2):
- Check: `postings.extracted_summary IS NOT NULL AND LENGTH(...) > 50`
- [SKIP] → save_summary_check_ihl (order 10) - skip extraction
- [RUN] → gemma3_extract (order 3) - do extraction

**2. check_skills_exist** (order 11):
- Check: `postings.taxonomy_skills IS NOT NULL`
- [SKIP] → check_ihl_exists (order 16) - skip skills extraction
- [RUN] → taxonomy_skill_extraction (order 12) - do skills extraction

**3. check_ihl_exists** (order 16):
- Check: `postings.ihl_score IS NOT NULL`
- [SKIP] → TERMINAL (NULL) - workflow complete
- [RUN] → w1124_c1_analyst (order 19) - do IHL scoring

### Benefits

- **Crash recovery**: Restart workflow, already-completed work is skipped
- **Efficiency**: No wasted LLM calls on completed work
- **Flexibility**: Can re-run workflows for specific stages

---

## Wave Chunking Strategy

### Critical Optimization (Nov 13, 2025)

Large waves (1,900+ postings) must be processed in **chunks** to prevent connection pool exhaustion.

### Implementation

```python
def _process_wave(self, conversation_id: int, postings: List[PostingState]):
    """Process wave in CHUNKS to avoid overwhelming connection pool"""
    
    chunk_size = 35  # Process 35 postings at a time
    
    for chunk_start in range(0, len(postings), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(postings))
        chunk_postings = postings[chunk_start:chunk_end]
        
        # Create workflow_runs for chunk in ONE transaction
        with db_transaction() as cursor:
            for posting in chunk_postings:
                cursor.execute("INSERT INTO workflow_runs ...")
                posting.workflow_run_id = cursor.fetchone()['workflow_run_id']
        
        # Process each posting in chunk sequentially
        for posting in chunk_postings:
            # Each posting makes 3-4 DB calls (connections are POOLED/REUSED)
            ...
```

### Why Chunking?

⚠️ **COMMON MISCONCEPTION:** "35 postings × 4 operations = 140 connections needed"

✅ **REALITY:** Connections are **POOLED and REUSED**, not held concurrently!

### How Connection Pooling Actually Works

```python
# Posting 1 processing:
conn1 = pool.get_connection()     # Checkout from pool
create_workflow_run(conn1)
pool.return_connection(conn1)     # Return to pool

conn2 = pool.get_connection()     # Gets SAME connection back!
log_llm_interaction(conn2)
pool.return_connection(conn2)

# Posting 2 processing:
conn3 = pool.get_connection()     # Gets SAME connection again!
create_workflow_run(conn3)
pool.return_connection(conn3)

# Result: Only 1-2 connections used total!
```

### So Why chunk_size = 35?

Not to prevent exhaustion (connections reused), but to prevent **QUEUE BUILDUP**:

**The Math**:
- Processing time: ~3-5 seconds per posting (LLM model inference)
- Chunk of 35 postings: 105-175 seconds total processing time
- Connection pool queue has no explicit timeout, but large batches create backpressure
- If 1,900 postings all request connections simultaneously, even with reuse the pool can't serve them instantly → queue builds up → slowdown

**With chunking (35 postings at a time)**:
- Chunk 1: 35 postings request connections → pool serves them → they complete → return connections
- Chunk 2: Next 35 proceed with reused connections
- Smooth flow, no queue buildup, steady throughput

**Why 35 specifically?**
- Small enough: Completes quickly (2-3 minutes), provides visible progress updates
- Large enough: Not too chatty (54 chunks for 1,900 postings vs 1,900 individual units)
- Empirically tested: Balances throughput vs responsiveness

**Could it be different?** Yes! 20-50 would also work. We chose 35 as a sweet spot.

### Chunk Size Calculation

```python
chunk_size = 35  # Chosen empirically:
  # - Small enough: No queue timeout (35 postings process in ~2-3 seconds)
  # - Large enough: Progress monitoring makes sense (35 is visible unit)
  # - Sweet spot: Balances throughput vs responsiveness
```

**Real Bottleneck:** Processing time per posting (~3-5s), not connection count!

### Benefits

- **Prevents queue timeout:** 35 postings complete before pool queue fills
- **Better monitoring:** Clear progress per chunk (35/1900, 70/1900...)
- **Graceful degradation:** If one posting fails, only affects that chunk
- **Smooth GPU utilization:** Steady flow prevents starvation/saturation

### Performance Impact

- Chunk of 35 processes in ~2-5 seconds (depending on model)
- Total throughput: ~700 postings/minute (same as without chunking!)
- Peak connections used: ~5-10 (far below pool max of 50)

---

## PostingState Entity

### Purpose

Tracks a posting's journey through the workflow.

### Structure

```python
class PostingState:
    posting_id: int
    job_description: str
    current_conversation_id: Optional[int]
    outputs: Dict[int, str]  # conversation_id → output
    conversation_outputs: Dict[str, str]  # conversation_1_output, etc.
    execution_sequence: List[int]  # path taken
    is_terminal: bool
    workflow_run_id: Optional[int]
    conversation_run_ids: Dict[Tuple[int, int], int]  # (posting_id, conv_id) → run_id
    
    def to_dict(self) -> Dict:
        """Serialize for checkpointing"""
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PostingState':
        """Deserialize from checkpoint"""
```

### Key Fields

- **outputs**: Stores intermediate conversation results (in-memory)
- **execution_sequence**: Records path taken through workflow (for debugging)
- **is_terminal**: True if workflow complete for this posting
- **conversation_run_ids**: Maps (posting, conversation) to conversation_run_id

---

## Progress Tracking

### Real-time Monitoring

Wave processor logs progress with ETA estimation:

```json
{
  "message": "wave_progress",
  "processed": 100,
  "total": 1926,
  "percent": 5.2,
  "avg_time_sec": 3.45,
  "eta": "1:45:23",
  "elapsed_sec": 345.0
}
```

### Monitoring Tools

```bash
# Live updating dashboard (every 3 seconds)
./tools/live_workflow_monitor.sh

# One-time snapshot
./tools/watch_workflow.sh

# Step metrics for completed workflow
python3 tools/show_workflow_metrics.py --workflow-id 3001
```

---

## Common Patterns

### Pattern 1: Multi-Stage Pipelines

**Problem**: Complex workflow with distinct stages (extraction, skills, IHL)

**Solution**: Structure as ordered stages with idempotency checks between

```
Stage 1: Job Description Extraction (orders 2-10)
Stage 2: Skills Extraction (orders 11-15)
Stage 3: IHL Scoring (orders 16-19)
```

### Pattern 2: Dynamic Branching

**Problem**: Workflows that adapt based on data (e.g., different models for different jobs)

**Solution**: Use branching logic to select model/actor at runtime

```sql
-- Branch by job family
INSERT INTO instruction_steps (branch_condition, next_conversation_id, branch_priority)
VALUES 
  ('"job_family": "engineering"', extract_engineering_id, 1),
  ('"job_family": "sales"', extract_sales_id, 1),
  ('"job_family": "marketing"', extract_marketing_id, 1),
  ('[DEFAULT]', extract_generic_id, 99);  -- Catch-all
```

### Pattern 3: Halting Problem Prevention

**Problem**: Workflows with loops (e.g., "improve until grade > 9") could run infinitely

**Solution**: Multi-layer budget system

**Implementation**:

1. **Workflow-level budget**: `max_total_session_runs` per workflow
   - Example: Workflow 3001 has budget of 50 conversations
   - Once exhausted, workflow terminates gracefully

2. **Conversation-level budget**: `max_instructions` per conversation
   - Example: Improvement conversation limited to 5 iterations
   - Prevents infinite improve-grade-improve loops

3. **Time-based timeout**: `max_execution_time` (future)
   - Abort if single conversation exceeds threshold

**Result**: System is bounded-time Turing-complete (can compute any function within budget constraints)

---

## See Also

**Related Architecture Docs**:
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - workflows, conversations, postings tables
- [ACTOR_SYSTEM.md](ACTOR_SYSTEM.md) - How actors execute within waves
- [CHECKPOINT_SYSTEM.md](CHECKPOINT_SYSTEM.md) - Wave crash recovery and state queries
- [CONNECTION_POOLING.md](CONNECTION_POOLING.md) - Why wave chunking (35) doesn't exhaust pool
- [CODE_DEPLOYMENT.md](CODE_DEPLOYMENT.md) - Actor code sync before workflow runs

---

## Workflow State Management (Nov 25, 2025)

### Overview

Workflow state provides persistent, queryable state using event-sourcing with semantic keys.

**Key features:**
- ✅ **Semantic keys** - Use `{current_summary}` instead of `{session_7_output}`
- ✅ **Cross-conversation data flow** - Access data without parent/child relationships
- ✅ **Idempotency** - State-based skip checks (`state ? 'extract_summary'`)
- ✅ **Audit trail** - Complete history in JSONB column

---

## Dynamic Template Variable Extraction (Dec 7, 2025)

### The Problem Solved

**Before Dec 7:** Template variables were hardcoded in Python:

```python
# ❌ BAD - hardcoded conversation IDs (53 mappings!)
variables = {
    'session_1_output': parents.get(3335, {}).get('response', ''),
    'session_2_output': parents.get(3336, {}).get('response', ''),
    'orphan_skills': parents.get(9229, {}).get('orphan_skills', ''),
    # ... 50 more lines of hardcoded mappings
}
```

**Problems:**
- Every new workflow required Python code changes
- New conversation IDs required editing `interaction_creator.py`
- Template substitution failures when IDs weren't mapped

### The Solution: Dynamic Extraction

```python
# ✅ GOOD - dynamic extraction (works for ANY workflow)
for conv_id, parent_output in parents.items():
    if isinstance(parent_output, dict):
        # Generate conversation_XXXX_output automatically
        variables[f'conversation_{conv_id}_output'] = parent_output.get('response', '')
        
        # Extract ALL keys from script outputs
        for key, value in parent_output.items():
            if key not in ('response', 'model', 'latency_ms'):
                variables[key] = str(value)

# Generate session_X_output for legacy templates
for idx, (conv_id, output) in enumerate(parents.items(), start=1):
    variables[f'session_{idx}_output'] = output.get('response', '')
```

### How Template Variables Work Now

**Available automatically:**

| Pattern | Source | Example |
|---------|--------|---------|
| `{conversation_XXXX_output}` | Parent AI response | `{conversation_3335_output}` |
| `{session_N_output}` | Nth parent in order | `{session_1_output}` |
| `{any_key}` | Script JSON output | `{orphan_skills}`, `{jobs_fetched}` |
| `{current_summary}` | workflow_state | Semantic key |
| `{job_description}` | posting data | From database |
| `{extracted_summary}` | posting data | Saved summary from Pipeline 2 |
| `{posting_id}` | posting data | Primary key |

**Order of precedence:**
1. Workflow state (semantic keys) - highest priority
2. Dynamic parent outputs
3. Posting data - lowest priority

### Where This Lives

- `core/wave_runner/interaction_creator.py` - lines 130-165
- `core/wave_runner/executors.py` - lines 100-140

**See also:** `docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md`

### Quick Example

```python
# Save state after extraction
db.update_workflow_state(workflow_run_id, {
    'extract_summary': output,
    'current_summary': output
})

# Later: Format conversation reads state
state = db.get_workflow_state(workflow_run_id)
summary = state.get('current_summary', '')
```

### Variable Substitution Precedence

1. **Workflow state** (highest) - `{current_summary}`, `{extracted_skills}`
2. **Parent outputs** - `{conversation_3335_output}`
3. **Posting data** (lowest) - `{posting_id}`, `{variations_param_1}`

**Complete documentation:** See [WORKFLOW_STATE_ARCHITECTURE.md](WORKFLOW_STATE_ARCHITECTURE.md)

---

## Traceability System (Nov 25, 2025)

### The Problem We Solved

**Before Nov 25:**
- `interactions.input` stored template prompts with placeholders (e.g., `{variations_param_1}`)
- Actual substituted prompts sent to AI were **not stored** anywhere
- Debugging "why did AI produce this output?" was impossible
- No audit trail of what data was actually sent to models

**After Nov 25:**
- Template prompt created during interaction creation (with placeholders)
- **Actual substituted prompt** stored before AI execution
- Full traceability: template → substituted prompt → AI response
- Complete audit compliance

### How It Works

**1. Interaction Creation** (workflow_starter.py, interaction_creator.py):
```python
# Create interaction with template
interaction = {
    'input': {
        'prompt': 'Extract skills from: {variations_param_1}',  # Template
        'system_prompt': 'You are a skill extractor'
    }
}
# Stored in database with placeholders
```

**2. Prompt Building** (executors.py):
```python
# When executing, build actual prompt
def _build_ai_prompt(interaction):
    prompt_template = get_instruction_prompt(conv_id)
    posting = get_posting_data(posting_id)
    
    variables = {
        'variations_param_1': posting.get('job_description', ''),
        'posting_id': str(posting_id),
        # ... more variables
    }
    
    # Substitute placeholders
    prompt = prompt_template
    for var_name, var_value in variables.items():
        prompt = prompt.replace('{' + var_name + '}', str(var_value))
    
    return prompt  # 3,771 chars with actual job description
```

**3. Store Actual Prompt** (runner.py):
```python
def _execute_ai_model(interaction):
    # Build substituted prompt
    prompt = self.ai_executor._build_ai_prompt(interaction)
    
    # Store actual prompt for traceability
    self.db.update_interaction_prompt(
        interaction['interaction_id'],
        prompt,  # Actual 3,771-char prompt
        system_prompt
    )
    
    # Execute with actual prompt
    return self.ai_executor.execute(model_name, prompt, system_prompt)
```

**4. Database Update** (database.py):
```python
def update_interaction_prompt(self, interaction_id, prompt, system_prompt):
    # Get current input
    cursor.execute("SELECT input FROM interactions WHERE interaction_id = %s", 
                   (interaction_id,))
    input_data = cursor.fetchone()['input'] or {}
    
    # Update with actual prompts
    input_data['prompt'] = prompt  # Replace template with actual
    input_data['prompt_length'] = len(prompt)
    if system_prompt:
        input_data['system_prompt'] = system_prompt
    
    # Store back
    cursor.execute("""
        UPDATE interactions
        SET input = %s, updated_at = NOW()
        WHERE interaction_id = %s
    """, (Json(input_data), interaction_id))
```

### What Gets Stored

**Template (initial):**
```
Create summary for: {variations_param_1}
Length: 520 chars
```

**Actual prompt (after substitution):**
```
Create summary for: Job Description: Job Title: CA Intern Location: Mumbai... [3,771 chars]
Length: 4,200 chars
```

**Result:**
- **Template preserved** in version history (git)
- **Actual prompt** in database (what AI saw)
- **AI response** in database (what AI produced)
- **Complete audit trail** template → prompt → response

### Benefits

1. **Debugging**: "Why did AI fail?" → Look at exact prompt sent
2. **QA**: Compare template vs actual to find variable mapping bugs
3. **Audit**: Prove exactly what data was sent to AI models
4. **Compliance**: GDPR/regulatory requirements for AI transparency
5. **Reproducibility**: Can replay exact prompt if needed

### Trace Reports

Trace reports (in `/reports/trace_*.md`) now show:

```markdown
### Prompt Template
Create summary: {variations_param_1}

### Actual Input (Substituted)
Create summary: Job Description: CA Intern... [full 3,771 chars]

### Actual Output
**Role:** CA Intern
**Company:** Deutsche Bank
... [actual AI response]
```

**Critical for debugging:**
- Variable mapping errors (wrong placeholder names)
- Missing data (empty substitutions)
- Data flow issues (parent outputs not passing through)

### Code Files

- `core/wave_runner/runner.py` - Calls `update_interaction_prompt()`
- `core/wave_runner/database.py` - Stores actual prompts
- `core/wave_runner/executors.py` - Builds substituted prompts

**Related Docs:**
- [WORKFLOW_DEBUGGING_COOKBOOK.md](WORKFLOW_DEBUGGING_COOKBOOK.md) - Trace report analysis
- [../CHECKPOINT_QUERY_PATTERN.md](../CHECKPOINT_QUERY_PATTERN.md) - Variable mapping patterns

---

**Key Code Files**:
- `core/wave_batch_processor.py` - Main wave processing loop (1314 lines)
- `core/posting_state.py` - PostingState class and methods
- `workflows/` - Workflow JSON definitions

**Monitoring**:
- `tools/monitor_workflow.py` - Live workflow progress
- `tools/watch_workflow.sh` - Auto-refreshing dashboard

**Main Reference**:
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Comprehensive system overview

---

## Wave Runner Best Practices (Nov 27, 2025)

### Production Execution Rules

**NEVER in production:**
- ❌ `max_iterations` parameter (causes incomplete runs)
- ❌ Per-posting execution loops (defeats batching)
- ❌ Manual Python commands (no audit trail)
- ❌ `workflow_run_id` scoping for batch processing (sequential execution)

**ALWAYS in production:**
- ✅ `global_batch=True` for batch processing (6-12x speedup)
- ✅ No iteration limits (run until complete)
- ✅ Standard wrapper scripts (logged execution)
- ✅ GPU monitoring during execution

### Global Batch Mode (Critical for Performance)

**The Problem (Nov 27 Discovery):**

When processing multiple postings, creating one workflow_run per posting defeats wave batching:

```python
# WRONG - Sequential execution (4.5 hours for 181 jobs)
for posting_id in posting_ids:
    result = start_workflow(conn, workflow_id=3001, posting_id=posting_id)
    runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
    runner.run()  # ← Processes ONE posting at a time
```

**Why this is slow:**
- Each posting: gemma3 → mistral → gemma2 → qwen (90 seconds)
- GPU loads/unloads models 181 times
- Sawtooth GPU pattern (not sustained utilization)
- Sequential: 181 × 90s = ~4.5 hours

**The Solution - Global Batch Mode:**

```python
# CORRECT - Wave batching (15 minutes for 181 jobs)
# Step 1: Start ALL workflows (creates pending interactions)
for posting_id in posting_ids:
    start_workflow(conn, workflow_id=3001, posting_id=posting_id)

# Step 2: Run ONE WaveRunner in global batch mode
runner = WaveRunner(conn, global_batch=True)
runner.run()  # ← Processes ALL postings simultaneously per model
```

**Why this is fast:**
- All gemma3 calls together (3 minutes for 181 postings)
- All mistral calls together (2 minutes)
- All gemma2 calls together (4 minutes)
- All qwen calls together (6 minutes)
- GPU loads models once per model (sustained 95% utilization)
- Total: ~15 minutes (18x faster)

**Performance Impact:**
- Model loading overhead: 2.7 hours → 60 seconds (saved 2.6 hours)
- Combined with mistral optimization: **28-55x total improvement**
- GPU utilization: Sawtooth 22% → Sustained 95%

**When to use each mode:**

| Mode | Use Case | Filter | Batch Size | Duration |
|------|----------|--------|------------|----------|
| Single posting | Debugging | `posting_id=X` | 3-4 interactions | 90 seconds |
| Single workflow | Resume failed | `workflow_run_id=X` | 3-4 interactions | 90 seconds |
| **Global batch** | **Production** | `global_batch=True` | 100s-1000s | Minutes |

### Iteration Limits - The Nov 27 Bug

**What happened:**
- Ran WaveRunner with `max_iterations=50` → stopped after 53 minutes (incomplete)
- Increased to `max_iterations=200` → stopped again (incomplete)
- Finally removed limit → ran to completion

**The problem:**
- No way to know the right limit in advance
- Too low → incomplete processing, manual restart needed
- Restart creates duplicate workflow_runs
- No audit trail of settings used

**The solution:**
```python
# Production: NO iteration limit
runner = WaveRunner(conn, global_batch=True)
runner.run()  # Runs until ALL interactions complete

# Debugging: Can use limit for safety
runner = WaveRunner(conn, posting_id=4920)
runner.run(max_iterations=20)  # Safe for single posting (4 actors)
```

**Rule:** For batch processing, NEVER use `max_iterations`. Let it run to completion.

### Standard Execution Pattern

**Create wrapper script: `scripts/run_workflow_batch.sh`**

```bash
#!/usr/bin/env bash
# Usage: ./scripts/run_workflow_batch.sh [workflow_id]
# Runs workflow in global batch mode with logging

WORKFLOW_ID=${1:-3001}
LOG_FILE="logs/wave_runner_$(date +%Y%m%d_%H%M%S).log"

python3 -c "
from core.database import get_connection
from core.wave_runner.runner import WaveRunner

conn = get_connection()
runner = WaveRunner(db_conn=conn, global_batch=True)

print(f'Running workflow ${WORKFLOW_ID} in global batch mode...')
print('No iteration limit - will run until complete.')
print()

result = runner.run()

print()
print('='*60)
print(f\"Status: {result.get('status')}\")
print(f\"Completed: {result.get('interactions_completed', 0)}\")
print(f\"Failed: {result.get('interactions_failed', 0)}\")
print(f\"Duration: {result.get('duration_ms', 0)/1000:.1f}s\")
print('='*60)
" 2>&1 | tee "$LOG_FILE"

echo
echo "Log saved to: $LOG_FILE"
```

**Usage:**
```bash
# Run workflow 3001 in batch mode
./scripts/run_workflow_batch.sh 3001

# Monitor progress in another terminal
watch -n 5 './scripts/q.sh "SELECT COUNT(*) FROM interactions WHERE created_at > NOW() - interval '\''1 hour'\''"'

# Check GPU utilization (should see sustained 95%, not spikes)
watch -n 2 nvidia-smi
```

### Monitoring During Execution

**GPU Pattern (Validation):**
```bash
watch -n 2 nvidia-smi

# Expected: Sustained 95% utilization during model waves
# Bad: Sawtooth pattern (spikes then drops) = sequential execution
```

**Database Progress:**
```sql
-- Check completion rate (should see tight clusters per model)
SELECT 
    a.actor_name,
    COUNT(*) as completed,
    MIN(i.updated_at)::time as wave_start,
    MAX(i.updated_at)::time as wave_end
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE i.status = 'completed'
  AND i.updated_at > NOW() - interval '1 hour'
GROUP BY a.actor_name
ORDER BY MIN(i.updated_at);

-- Expected: 3-6 minute windows per model (wave batching)
-- Bad: 90+ second spreads (sequential)
```

**Running interactions (real-time):**
```sql
-- Should see 5-20 interactions per model simultaneously
SELECT 
    a.actor_name,
    COUNT(*) as running_now
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE i.status = 'running'
GROUP BY a.actor_name;
```

### Cleanup After Execution

**Check for duplicates:**
```sql
-- Should see ONE workflow_run per posting
SELECT posting_id, COUNT(*) as runs
FROM workflow_runs
WHERE workflow_id = 3001
GROUP BY posting_id
HAVING COUNT(*) > 1;

-- If duplicates found, mark old ones as cancelled
UPDATE workflow_runs
SET status = 'cancelled'
WHERE workflow_run_id IN (
    SELECT workflow_run_id
    FROM workflow_runs
    WHERE posting_id = 4920
    ORDER BY created_at
    LIMIT 1  -- Keep latest, cancel old
);
```

### Key Takeaways

1. **Global batch mode is mandatory** for multi-posting production processing
2. **Never use iteration limits** in production (causes incomplete runs)
3. **Monitor GPU utilization** to validate wave batching (sustained vs sawtooth)
4. **Use wrapper scripts** for logging and audit trail
5. **Clean up duplicates** from failed attempts before running

**See also:**
- [decisions/008_global_batch_mode.md](decisions/008_global_batch_mode.md) - Full architectural decision record
- [WORKFLOW_ORCHESTRATION.md](WORKFLOW_ORCHESTRATION.md) - Future database-driven execution
