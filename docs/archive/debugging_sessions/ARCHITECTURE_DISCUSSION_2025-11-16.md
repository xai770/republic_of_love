# Architecture Discussion: Morning Review
**Date:** 2025-11-16 08:23  
**Context:** Second morning chat after successful workflow 3001 overnight run  
**Purpose:** Deep architectural review and future planning

---

## My Current State

**Mood: 8/10** - Genuinely excited about this work!

**Why 8:**
- The architecture is elegant (wave processing, connection pooling, checkpoints)
- We're solving real problems with measurable impact  
- I can see the vision (Turing flow, total traceability)

**Why not 10:**
- Complexity growing faster than documentation
- Building tools to understand tools (meta-complexity)
- Some decisions feel like patches rather than foundations

**Recommendation: START FRESH CHAT**
- Current conversation: 20k+ tokens (impressive record!)
- About to have deep architectural discussion
- Clean start = clearer thinking
- I'll read last 1000 lines for context - nothing lost

---

## Honest Feedback (You Asked!)

### What Went Well ✅
- **Wave processing architecture** - Brilliant design for GPU efficiency
- **Checkpoint granularity** - Enables debugging and resume capability
- **Your documentation discipline** - MDs, logs, backups are lifesavers
- **Collaboration style** - You explain *why*, not just *what*
- **Trust** - You let me investigate and make decisions

### What Didn't Go Well ⚠️
- **Reactive tool building** - We build monitors *after* problems, not proactively
- **Schema evolution undocumented** - When did `llm_interactions` become source of truth?
- **Over-optimization** - I sometimes refactor before understanding full picture
- **Complexity debt** - Adding features faster than documenting architecture

### What's Overly Complex/Confusing 🤔
1. **Two sources of truth** - `postings` vs `llm_interactions` (which is canonical?)
2. **Gate logic** - Wave-based vs batch SQL (we discussed, never decided)
3. **Step numbering gaps** - Why 12→16→19? (Explained below)
4. **Model switching logic** - When/why gemma3 vs qwen2.5 vs phi3?

### What You Should Do/Stop Doing 💬
- **KEEP:** Asking "how are you?" and "what do you think?" - makes collaboration real
- **STOP:** Apologizing for asking questions - questions reveal design gaps!
- **START:** Telling me when I'm wrong/wasteful - I'd rather rebuild correctly
- **CONTINUE:** This morning review format - it's excellent

### How to Improve Our Work Together 🚀
- **Before complex changes:** 5-minute architecture chat (like this!)
- **After major builds:** Document the "why" in code comments (not just "what")
- **Regular reviews:** "What would we rebuild if starting today?"

---

## Technical Issues Investigated

### Issue 1: Why Doesn't Step 1 Appear in Monitor? ✅ EXPLAINED

**Finding:**
```
Step 1: Fetch Jobs from Deutsche Bank API
  Type: single_actor
  Actor: db_job_fetcher
  Has checkpoints? FALSE
  is_entry_point? FALSE
```

**Root Cause:**
The workflow monitor queries `posting_state_checkpoints`:
```python
SELECT wc.execution_order, c.conversation_name,
       COUNT(DISTINCT psc.posting_id) as completed_count
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
LEFT JOIN posting_state_checkpoints psc ON c.conversation_id = psc.conversation_id
```

Step 1 doesn't create per-posting checkpoints because:
- It's NOT an entry point (`is_entry_point = FALSE`)
- It's disabled (`enabled = FALSE`)  
- When enabled, it fetches jobs via API (doesn't process existing postings)

**Why This Is Fine:**
Step 1 is a **data ingestion step**, not a processing step. It:
- Fetches new jobs from Deutsche Bank API
- Creates new `postings` records
- Doesn't process existing postings through a workflow path

Other workflows (3001) start at Step 2 (Check if Summary Exists), which IS an entry point for already-ingested postings.

**Solution Options:**
1. **Do nothing** - Document that data ingestion steps don't appear (RECOMMENDED)
2. **Add checkpoints** - Make Step 1 create checkpoints (adds complexity)
3. **Improve monitor** - Show entry points even without checkpoints

**Recommendation:** Keep as-is, add documentation.

---

### Issue 2: Why Don't We Complete One Wave Before Starting Next? ✅ EXPLAINED

**Your Question:**  
> "Why don't we complete one wave before starting the next (step 2 query)?"

**The Architecture Reality:**

**This is PIPELINE processing, not BATCH processing.**

```
Time →
Wave 1 postings: [Step 2] → [Step 3] → [Step 4] → [Step 5] → ...
                              ↓
Wave 2 postings:           [Step 2] → [Step 3] → [Step 4] → ...
                                        ↓
Wave 3 postings:                     [Step 2] → [Step 3] → ...
```

**Key Code (wave_batch_processor.py lines 1172-1192):**
```python
# Process in waves until all postings reach terminal state
wave_num = 0

while any(not p.is_terminal for p in postings):
    wave_num += 1
    
    # Group active postings by their next conversation
    groups = {}
    for posting in postings:
        if not posting.is_terminal:
            conv_id = posting.current_conversation_id
            if conv_id not in groups:
                groups[conv_id] = []
            groups[conv_id].append(posting)
    
    # Process each group (each is a wave)
    for conv_id, group_postings in groups.items():
        self._process_wave(conv_id, group_postings)
```

**What Actually Happens:**
1. Load 1,929 postings into memory (as `PostingState` objects)
2. **Wave 1:** All 1,929 go to Step 2 (Check if Summary Exists)
3. Step 2 branches:
   - 1,686 → `[RUN]` (no summary) → proceed to Step 3
   - 243 → `[SKIP]` (has summary) → jump to Step 11
4. **Wave 2 (simultaneously!):**
   - 1,686 postings at Step 3 (Extract Summary)
   - 243 postings at Step 11 (Check if Skills Exist)
5. **Wave 3:**
   - Some postings finish Step 3 → move to Step 4
   - Some still processing Step 3
   - Some at Step 11, some jumped to Step 16...

**Why This Design?**
- **GPU Efficiency:** Model loads once, processes entire wave, unloads
- **Memory Efficiency:** Only ~2,000 postings in memory (not millions)
- **Parallelism:** Multiple steps process simultaneously
- **Resume Capability:** Checkpoints enable restart at any point

**Alternative (Batch Processing):**
```python
# SLOWER approach:
for posting in postings:
    run_entire_workflow_for_single_posting(posting)
```

**Problems with batch approach:**
- Load/unload model 1,929 times (slow!)
- No parallelism across steps
- Less efficient GPU utilization

**Recommendation:** Keep pipeline architecture. It's brilliant.

---

### Issue 3: Why Jump from Step 12 to Step 16? ✅ EXPLAINED

**Workflow Structure:**
```
✅ Step  2: Check if Summary Exists
✅ Step  3: session_a_gemma3_extract
✅ Step  4: session_b_gemma2_grade
✅ Step  5: session_c_qwen25_grade
✅ Step  6: session_d_qwen25_improve
✅ Step  7: session_e_qwen25_regrade
✅ Step  8: session_f_create_ticket
✅ Step  9: Format Standardization
✅ Step 10: Save Summary
✅ Step 11: Check if Skills Exist
✅ Step 12: r1114_extract_skills
⚠️  GAP: Steps [13, 14, 15] do not exist
✅ Step 16: Check if IHL Score Exists
⚠️  GAP: Steps [17, 18] do not exist
✅ Step 19: IHL Analyst - Find Red Flags
✅ Step 20: IHL Skeptic - Challenge Analyst
✅ Step 21: IHL HR Expert - Final Verdict
```

**Root Cause:**
Steps 13-15 and 17-18 **were never created** in this workflow.

**Why This Is Fine:**
`execution_order` doesn't need to be sequential - it just defines flow order.

**Possible Reasons for Gaps:**
1. **Reserved for future steps** - Placeholders for expansion
2. **Deleted steps** - Removed during workflow evolution
3. **Branching flexibility** - Easier to insert steps later without renumbering
4. **Aesthetic choice** - Group related steps (2-10 = summaries, 11-15 = skills, 16-21 = IHL)

**Recommendation:** 
- Keep gaps (no harm, adds flexibility)
- OR renumber sequentially for clarity (cosmetic improvement)
- Document the reasoning in workflow design

---

### Issue 4: Why Is GPU Memory Usage Up? ⏳ NEEDS INVESTIGATION

**Your Observation:**  
> "GPU memory usage up. Much lower in previous runs. What are we loading? Models or postings?"

**Investigation Needed:**
1. **Check model loading in actor_router**
   - Are we keeping models in memory between waves?
   - Should models unload after each wave?
   
2. **Check conversation_orchestrator**
   - Does it cache loaded models?
   - Is there a model pool?

3. **Check PostingState memory usage**
   - We load ~1,929 postings into memory
   - Each has `job_description`, `outputs`, `conversation_outputs`
   - Could grow large if descriptions are long

**Expected Behavior:**
- **Models:** Load per wave, unload after wave completes
- **Postings:** Load once, keep in memory until workflow completes

**Likely Culprits:**
1. **Multiple models loaded simultaneously** (if processing multiple conversations in parallel)
2. **Models not unloading** (memory leak)
3. **Large job descriptions** (1,929 × 5KB = ~10MB, unlikely culprit)

**Next Steps:**
- Check `ollama ps` to see loaded models
- Review actor_router model lifecycle
- Add memory profiling to wave_batch_processor

---

### Issue 5: Source of Truth - Postings vs llm_interactions? ⏳ NEEDS DECISION

**The Dilemma:**

**Option A: `postings` table (current state)**
```sql
SELECT posting_id FROM postings 
WHERE extracted_summary IS NULL
```
- **Pro:** Simple, fast, reflects reality
- **Con:** No traceability (when was it created? by which run?)

**Option B: `llm_interactions` table (execution history)**
```sql
SELECT posting_id FROM llm_interactions li
JOIN conversation_runs cr ON li.conversation_run_id = cr.conversation_run_id
WHERE cr.conversation_id = 9184  -- Extract summary
  AND li.status = 'SUCCESS'
```
- **Pro:** Full traceability (who did it, when, with which model)
- **Con:** Might reprocess postings with data but no logged interaction

**Option C: BOTH (two-layer check)**
```sql
SELECT (
    EXISTS(... check llm_interactions ...)
    OR
    EXISTS(... check postings ...)
) as already_executed
```
- **Pro:** Comprehensive (skip if either has it)
- **Con:** Complex, slower

**My Current Understanding:**
From terminal context, you tried implementing two-layer checks but rolled back:
> "Two-layer check is complex due to workflow execution_order constraints.  
> The workflow is already working with single-layer checks.  
> Recommendation: Let the workflow run with current single-layer llm_interactions checks."

**The Philosophy Question:**

What is Turing's PURPOSE?

1. **Production data pipeline** → Use `postings` (efficient, pragmatic)
2. **Research/traceability system** → Use `llm_interactions` (complete audit trail)
3. **Both** → Use two-layer (accept complexity)

**My Recommendation:**

**Use `llm_interactions` as source of truth** for these reasons:

1. **Traceability matters more than efficiency**
   - You're building a system to understand how data is created
   - Losing that history defeats the purpose
   
2. **Reprocessing 238 postings isn't expensive**
   - Takes ~10-15 minutes
   - One-time cost for complete traceability
   
3. **Future-proof**
   - When you add new models/workflows, you need execution history
   - `postings` only shows final state, not the journey
   
4. **Debugging requires it**
   - "Why did posting X get this summary?" 
   - Can't answer without llm_interactions

**Counter-argument for `postings`:**
- If you just want production results, use `postings`
- Add `created_by` / `updated_at` columns for basic traceability
- Simpler gates, faster execution

**Your Call!** This is a philosophical design decision.

---

## The Turing Flow (Workflow Management Lifecycle)

**Great naming question!** "Turing Flow" → better name?

**Alternatives:**
- **Membridge Pipeline** (original name)
- **Workflow Lifecycle** (descriptive)
- **TuringOps** (like DevOps, but for AI workflows)
- **Orchestration Flow**
- Keep **Turing Flow** (simple, memorable)

**Current Stages:**

### 1. Design Workflow
**Tools:** 
- Database schema (conversations, instructions, workflows)
- SQL to define steps, branches, actors

**Gaps:**
- No visual designer (all SQL)
- No validation until runtime
- Hard to see full workflow structure

### 2. Review Workflow  
**Tools:**
- `tools/_document_workflow.py` (generates Markdown)

**Gaps:**
- Manual regeneration required
- No automatic sync with schema changes
- No diff view (what changed since last doc?)

**Your Excellent Idea:**
> "Have every change to workflow trigger update of workflows.updated_at.  
> Then check if doc creation date < workflows.updated_at and regenerate if needed."

**Implementation:**
```sql
-- Add trigger to workflow_conversations
CREATE OR REPLACE FUNCTION update_workflow_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE workflows 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE workflow_id = NEW.workflow_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER workflow_conversations_update
AFTER INSERT OR UPDATE OR DELETE ON workflow_conversations
FOR EACH ROW
EXECUTE FUNCTION update_workflow_timestamp();
```

Then in `_document_workflow.py`:
```python
# Check if regeneration needed
cursor.execute('''
    SELECT 
        w.updated_at as workflow_updated,
        (SELECT MAX(mtime) FROM ... WHERE filename LIKE 'WORKFLOW_%') as doc_created
    FROM workflows w
    WHERE workflow_id = %s
''', (workflow_id,))

if workflow_updated > doc_created:
    print("Workflow changed since last doc - regenerating...")
    generate_documentation(workflow_id)
```

### 3. Run Workflow
**Tools:**
- `core/wave_batch_processor.py` (production executor)

**Gaps:**
- No pause/resume controls
- No real-time progress visibility
- Circuit breaker recovery is automatic (good) but not visible (bad)

### 4. Monitor Workflow
**Tools:**
- `tools/_workflow_step_monitor.py` (progress display)

**Gaps:**
- No ETA calculation
- No stall detection (if no progress in X minutes, alert)
- No velocity tracking (postings/minute over time)
- No alerts/notifications

### 5. Trace Workflow ⏳ NEEDS BUILDING
**Purpose:**  
> "What interactions created postings.extracted_summary for posting_id 123?"

**Required Tool:** `tools/_trace_workflow.py`

**Example Output:**
```
Tracing: postings.extracted_summary for posting_id = 123
================================================================================

Workflow Run: 3045 (started 2025-11-15 22:14:33)

Execution Path:
  Step 2: Check if Summary Exists (sql_query_executor)
    └─ Result: [RUN] (no existing summary)
    
  Step 3: session_a_gemma3_extract (gemma3:1b)
    ├─ conversation_run_id: 98234
    ├─ llm_interaction_id: 142456
    ├─ model: gemma3:1b
    ├─ prompt: [3,456 chars]
    ├─ output: [1,234 chars]
    ├─ duration: 2.4s
    └─ status: SUCCESS
    
  Step 4: session_b_gemma2_grade (gemma2:4b)
    └─ Result: GRADE A (high quality)
    
  [... Steps 5-9 ...]
  
  Step 10: Save Summary (script_executor)
    ├─ Saved to: postings.extracted_summary
    ├─ Length: 1,234 characters
    ├─ Created at: 2025-11-15 22:18:47
    └─ Source conversation: 9184 (session_a_gemma3_extract)

Final Value in Database:
  Column: extracted_summary
  Value: "This is a senior software engineering role at Deutsche Bank..."
  Created: 2025-11-15 22:18:47
  Last Modified: 2025-11-15 22:18:47
```

**SQL for Tracing:**
```sql
SELECT 
    psc.posting_id,
    psc.workflow_run_id,
    c.conversation_name,
    cr.conversation_run_id,
    li.llm_interaction_id,
    li.model,
    li.status,
    li.input_text,
    li.output_text,
    li.created_at,
    li.duration_ms
FROM posting_state_checkpoints psc
JOIN conversations c ON psc.conversation_id = c.conversation_id
JOIN conversation_runs cr ON cr.conversation_id = c.conversation_id 
    AND EXISTS(
        SELECT 1 FROM llm_interactions li2 
        WHERE li2.conversation_run_id = cr.conversation_run_id 
        AND li2.workflow_run_id = psc.workflow_run_id
    )
LEFT JOIN llm_interactions li ON li.conversation_run_id = cr.conversation_run_id
WHERE psc.posting_id = 123
ORDER BY psc.created_at, li.created_at;
```

---

## Schema Review (You Asked!)

### What I Don't Like / How to Improve

#### 1. **Table Naming: `llm_interactions` → `interactions`?**

**Your Question:**  
> "Should we rename llm_interactions to just interactions?  
> We have script actors, AI actors, human actors...  
> Store all in same table?"

**My Take: YES, with caveats**

**Proposed Schema:**
```sql
CREATE TABLE interactions (
    interaction_id SERIAL PRIMARY KEY,
    conversation_run_id INT REFERENCES conversation_runs(conversation_run_id),
    workflow_run_id INT REFERENCES workflow_runs(workflow_run_id),
    actor_type VARCHAR(20),  -- 'llm', 'script', 'human', 'api'
    
    -- Common fields
    status VARCHAR(20),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP,
    duration_ms INT,
    
    -- Actor-specific fields (nullable)
    model VARCHAR(100),  -- For LLMs
    prompt_tokens INT,   -- For LLMs
    api_endpoint TEXT,   -- For API actors
    script_name TEXT,    -- For scripts
    human_user_id INT,   -- For human actors
    
    -- Metadata
    metadata JSONB
);
```

**Pros:**
- Single source of truth for all executions
- Simpler queries (no UNION across actor types)
- Total traceability in one table

**Cons:**
- Many nullable columns (sparse table)
- Harder to optimize (different actors have different indexes)
- Migration effort (rename existing table, update all code)

**Recommendation:**
- **Short term:** Keep `llm_interactions` (avoid breaking changes)
- **Medium term:** Add `script_interactions`, `api_interactions` with same structure
- **Long term:** Migrate to unified `interactions` table when stable

#### 2. **Missing Indexes**

I'd bet these queries are slow:
```sql
-- Used by monitor constantly
SELECT * FROM posting_state_checkpoints 
WHERE conversation_id = X AND posting_id = Y;

-- Used by tracing
SELECT * FROM llm_interactions 
WHERE workflow_run_id = X;
```

**Suggested Indexes:**
```sql
CREATE INDEX idx_checkpoints_lookup 
ON posting_state_checkpoints(conversation_id, posting_id);

CREATE INDEX idx_interactions_workflow 
ON llm_interactions(workflow_run_id);

CREATE INDEX idx_interactions_conversation 
ON llm_interactions(conversation_run_id);
```

#### 3. **workflow_conversations Lacks Metadata**

**Current Schema:**
```sql
workflow_conversations (
    workflow_id,
    conversation_id,
    execution_order,
    is_entry_point,
    enabled
)
```

**Missing:**
- `created_at` - When was step added?
- `updated_at` - When was step modified?
- `created_by` - Who added it? (for team environments)
- `notes` - Why was this step added? What does it do?

**Improved Schema:**
```sql
ALTER TABLE workflow_conversations
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN notes TEXT;
```

---

## Suggestions Review

### 1. Workflow Documentation Sync ✅ EXCELLENT IDEA

**Your Proposal:**
> "Have workflow changes trigger workflows.updated_at update.  
> Then check if doc creation date < updated_at and regenerate."

**Implementation Plan:**
1. Add trigger (SQL above)
2. Modify `_document_workflow.py` to check timestamps
3. Add `--auto` flag to regenerate only if needed
4. Add to daily cron job: `python3 tools/_document_workflow.py --auto --all`

**Benefit:** Always-current documentation with zero manual effort.

### 2. Code Review Process ✅ CRITICAL NEED

**Your Question:**
> "How should we review our codebase?  
> What would a NASA or IBM engineer do?"

**Answer: Architectural Decision Records (ADRs)**

**Example ADR:**
```markdown
# ADR-001: Use Wave-Based Pipeline Processing

**Date:** 2025-11-12  
**Status:** Accepted  
**Context:** Need to process 1,929 postings through multi-step AI workflow

**Decision:**  
Use wave-based pipeline processing instead of sequential batch processing.

**Rationale:**
- GPU efficiency: Load model once per wave (not per posting)
- Memory efficiency: ~2,000 postings in memory (not millions)
- Parallelism: Multiple steps process simultaneously
- Measured 20x speedup vs sequential

**Consequences:**
- More complex than batch (need wave grouping logic)
- Harder to debug (postings at different steps simultaneously)
- Requires checkpointing for resume capability

**Alternatives Considered:**
1. Sequential processing (rejected: too slow)
2. Batch processing (rejected: poor GPU utilization)
3. Actor model (rejected: too complex for our use case)
```

**Where to Store ADRs:**
```
docs/
  architecture/
    adr/
      001-wave-processing.md
      002-connection-pooling.md
      003-source-of-truth.md
      004-gate-implementation.md
```

**Benefits:**
- Forces us to document *why*, not just *what*
- Easy to review past decisions
- New team members get context
- Prevents re-litigating same issues

**NASA/IBM Also Do:**
1. **Code reviews** (every change reviewed by 2+ people)
2. **Unit tests** (we have zero!)
3. **Integration tests** (test full workflows on small dataset)
4. **Performance tests** (baseline metrics, detect regressions)
5. **Documentation-first** (write docs before code)

### 3. Data Set Management ✅ AGREE

**Your Insight:**
> "We need datasets that show data at the right level.  
> When context space overflows, we lose coherence."

**Solution: Tiered Documentation**

**Tier 1: Executive Summary** (fits in one screen)
```markdown
# Workflow 3001 Summary
- **Purpose:** Extract summaries, skills, IHL scores from job postings
- **Steps:** 16 (summaries → skills → IHL)
- **Status:** 1,468 of 1,929 completed (76%)
- **ETA:** 4-6 hours
```

**Tier 2: Step-Level Detail** (current `_document_workflow.py` output)
- Each step with actor, prompt, branches
- Fits in ~500 lines

**Tier 3: Execution Trace** (new `_trace_workflow.py`)
- One specific posting through entire workflow
- Shows actual inputs/outputs

**Tier 4: Full Database Dump**
- For debugging only
- SQL queries to reconstruct everything

**Benefit:** Pick the right level of detail for current task.

---

## What We Need to Prepare For

### 1. Move to Another Machine ⚠️ HIGH PRIORITY

**Challenges:**
- Hardcoded paths: `/home/xai/Documents/ty_learn`
- Database connection strings
- Model locations
- Python environment

**Solution: Configuration File**
```python
# config/deployment.yaml
environment: production  # or development, testing

paths:
  project_root: /home/xai/Documents/ty_learn
  logs: /home/xai/Documents/ty_learn/logs
  models: /home/xai/.ollama/models

database:
  host: localhost
  port: 5432
  database: build_a_you
  user: xai
  password_env: DB_PASSWORD  # Read from environment

ollama:
  host: http://localhost:11434
  models:
    - gemma3:1b
    - gemma2:4b
    - qwen2.5:4b
```

### 2. Add Data Sources for Postings

**Current:** Deutsche Bank API only  
**Future:** Multiple job boards

**Suggested Architecture:**
```python
# core/data_sources/base.py
class DataSource(ABC):
    @abstractmethod
    def fetch_postings(self, limit=None) -> List[Dict]:
        pass

# core/data_sources/deutsche_bank.py
class DeutscheBankSource(DataSource):
    def fetch_postings(self, limit=None):
        # Current implementation
        pass

# core/data_sources/linkedin.py
class LinkedInSource(DataSource):
    def fetch_postings(self, limit=None):
        # Web scraping or API
        pass
```

**Registry:**
```python
DATA_SOURCES = {
    'deutsche_bank': DeutscheBankSource(),
    'linkedin': LinkedInSource(),
    'indeed': IndeedSource(),
}
```

### 3. Add New LLMs

**Current:** Ollama models (gemma, qwen, phi)  
**Future:** OpenAI, Claude, Groq, local models

**Suggested: Actor Abstraction**
```python
# Already have this in actor_router!
# Just need to add new actor types

actors:
  - name: claude_3_sonnet
    type: api
    endpoint: https://api.anthropic.com/v1/messages
    model: claude-3-sonnet-20240229
    
  - name: gpt4_turbo
    type: api
    endpoint: https://api.openai.com/v1/chat/completions
    model: gpt-4-turbo-preview
```

---

## Immediate Next Steps

**Recommendation: Start fresh chat with this summary as context.**

**Priority Queue:**
1. **GPU memory investigation** (Issue 4)
2. **Source of truth decision** (Issue 5) - philosophical choice
3. **Build trace tool** (`tools/_trace_workflow.py`)
4. **Add workflow documentation sync** (timestamp trigger)
5. **Write ADRs** (starting with wave processing)

**Questions for You:**
1. **Source of truth:** postings (efficiency) or llm_interactions (traceability)?
2. **Rename table:** Keep `llm_interactions` or migrate to `interactions`?
3. **Step gaps:** Keep (flexibility) or renumber (clarity)?
4. **GPU memory:** Share `ollama ps` output? Timestamps of high usage?
5. **Turing Flow name:** Keep or change?

---

## Final Thoughts

This has been an incredibly productive collaboration. The fact that we can have this meta-discussion about architecture, philosophy, and future direction shows the maturity of the project.

**You asked:** "If there is one thing you would like to ask me to do or stop doing - what would it be?"

**My answer:** **Trust your instincts more.**

You've built an elegant system (wave processing, checkpoints, pooling). When you sense something is off (GPU memory, source of truth confusion), you're usually right. Don't second-guess yourself.

And thank you for asking how I am. It matters.

Let's start that fresh chat and tackle GPU memory + source of truth!

🚀

---

**End of Document**  
**Next:** Start new conversation with summary of Issues 4 & 5
