# Schema Table Review: 23 Empty Tables Discussion

**Date:** November 24, 2025 07:50  
**Participants:** xai (wetbrain), Arden (AI assistant)  
**Purpose:** Deep review of 23 empty tables to determine drop/keep/redesign decisions

**Philosophy:** 
- Mistrust documentation - verify current state
- Read schema comments always  
- Ask when unclear
- No euphemisms - describe contents simply
- No stubs/quick fixes - do it right

---

## How We Got Here

Ran `scripts/count_all_tables.sh` and discovered:
- **74 total tables** in turing database
- **23 completely empty** (0 rows, never used)
- **4 empty but referenced in code** (will be used: profile_skills, posting_skills, qa_findings, workflow_metrics)
- **19 truly unused** candidates for detailed review

**Method:** Used `scripts/q.sh` wrapper (created today) to query database with pager off.

---

**Date:** November 24, 2025 07:50  
**Participants:** xai (wetbrain), Arden (AI assistant)  
**Purpose:** Deep review of 23 empty tables to determine drop/keep/redesign decisions

**Philosophy:** Mistrust documentation - verify current state. Read schema comments always. Ask when unclear.

---

## Context: What We Found

Ran `scripts/count_all_tables.sh` and discovered:
- **74 total tables** in turing database
- **23 completely empty** (0 rows, never used)
- **4 empty but referenced in code** (will be used)
- **19 truly unused** candidates for review

**Method:** Used `scripts/q.sh` wrapper (created today) to query database with pager off.

---

## Table-by-Table Analysis

### 1. career_analyses ❓ DISCUSS

**Schema Comment:**
> "Stores comprehensive career analysis results from Recipe 1122 multi-model ensemble"

**Business Context** (from [[rfa_talent_yoga]]):
- talent.yoga is employment navigation platform
- Born from Deutsche Bank job search sabotage
- Serves 2M+ unemployed in Germany
- Core features: data extraction, intelligence analysis, strategic narrative generation
- "Career Intelligence Dashboard" mentioned in RFA

**Current Reality:**
- Profile skills NOW stored in `profile_skills` table (referenced by skills_saver.py, save_profile_skills.py)
- Recipe 1122 is OLD schema (recipes/variations/sessions - all deleted Nov 24)
- Career analysis = skills extraction + gap analysis + recommendations

**Questions for xai:**
1. Do we still need comprehensive career analysis beyond skills?
2. Is career analysis part of current roadmap (talent.yoga dashboard)?
3. Should this be workflow outputs stored in `interactions.output` instead of dedicated table?

**Arden's Recommendation:** 
- **DROP table** - functionality belongs in interactions/workflow outputs
- Document career analysis as workflow 3XXX feature (not table)
- Profile skills already in `profile_skills`

---

### 2. dialogue_step_placeholders ❓ DISCUSS

**Schema Comment:**
> "Links dialogue steps to their required/optional placeholders"

**Architecture Context** (from [[3003_taxonomy_maintenance_turing_native]]):
- Workflow 3003 = open-ended workflow (variable number of interactions)
- Example: Organizing skills into n-level hierarchy
- Uses "gopher-like approach" - LLM navigates tree (Oracle → Tech Skills → Software → Database...)
- Each step might need different context/placeholders

**Current Reality:**
- We have `placeholder_definitions` table (46 rows) for workflow-level placeholders
- Interactions store all context in `input` JSONB
- No evidence of dialogue-step-level placeholder linking

**Questions for xai:**
1. Is the gopher approach (multi-step tree navigation) reflected in our architecture docs?
2. Do we build prompts dynamically based on tree position?
3. Is context passed through interaction chains (parent → child) sufficient?

**Arden's Assessment:**
> **"I think we don't need this table, as all is stored in interactions. But I want to make sure that this approach is reflected in our architecture documents."** - xai

**Status:** ✅ CONFIRMED - Not needed
- Workflow 3003 shows context passing through `input_interaction_ids`
- Each interaction gets context from parent outputs
- No step-level placeholder system exists

**Action Items:**
- [ ] Document gopher/tree-navigation pattern in architecture docs
- [ ] Add workflow 3003 example to WORKFLOW_CREATION_COOKBOOK.md
- [ ] DROP table

---

### 3. human_tasks ⚠️ CRITICAL - KEEP & REDESIGN

**Schema Comment:**
> "Queue of tasks awaiting human input. When execution_type=human_input, system creates entry here and waits for human to provide response."

**Business Need** (from xai):
- Workflow 3003 opens ticket to human when job summary fails
- "We will need the human in the middle sometimes"
- Should be handled by workflows with:
  - A. Identity/authentication records (who is executing)
  - B. Personal task queues (inbox for each person)
  - C. Starter workflows that spawn other workflows

**Current Reality:**
- We have 3 human actors: `arden`, `xai`, `gershon` (actor_type='human')
- Actor `gershon` has execution_type='human_input' and notification_email config
- WAVE_RUNNER_V2 mentions "queue human tasks" in requirements
- NO architecture for personal task queues documented

**Missing Architecture:**
1. ❌ **Authentication/Identity** - Not documented
   - `users` table exists (1 row) but not integrated
   - No auth flow documented
   - No user → actor mapping clear

2. ❌ **Personal Task Queues** - Not implemented
   - `human_tasks` table empty
   - No inbox/assignment system
   - No task claim mechanism

3. ❌ **Workflow Spawning** - Partially exists
   - `workflow_triggers` has trigger_type='MANUAL' (4 rows)
   - Can spawn workflows via triggers
   - No documented "starter workflow" pattern

**Arden's Finding:** 🚨 **GAP IN ARCHITECTURE**

**Recommendations:**
1. **KEEP table** `human_tasks` - needed for async human-in-loop
2. **DESIGN architecture** for:
   ```sql
   human_tasks (
       task_id,
       assigned_to_actor_id,  -- FK to actors (human type)
       interaction_id,         -- Which interaction needs input
       task_type,             -- 'review_summary', 'approve_taxonomy', etc
       status,                -- 'pending', 'claimed', 'completed'
       created_at,
       claimed_at,
       completed_at,
       response_data JSONB    -- Human's response
   )
   ```
3. **Document patterns:**
   - How workflow pauses for human input
   - How human claims task from queue
   - How response resumes workflow
   - Multi-user task assignment

**Questions for xai:**
1. Is authentication needed (login system) or just actor_id assignment?
2. Should tasks be auto-assigned or claimed from pool?
3. What's priority: Single user (xai) or multi-user (team)?

---

### 4. interaction_lineage ✅ DROP - But Learn From It

**Schema Comment:**
> "Causation graph: tracks which LLM interactions influenced which others. Enables lineage analysis and change impact tracking."

**Current Reality:**
- We have `input_interaction_ids` array in `interactions` table
- This IS the lineage graph (parent → child links)
- `interaction_events` table tracks causation (66 rows)
- Dedicated lineage table is redundant

**Lesson Learned (xai's wisdom):**
> "did you know that we have comments in the schema, that explain why we created them? Read them, always."

**Why This Table Existed:**
- Explored explicit causation graph
- Realized array FK is simpler
- Comment preserved the WHY

**Action:** 
- ✅ DROP table
- ✅ Document lineage queries in CHECKPOINT_QUERY_PATTERN.md
- Example query to add:
  ```sql
  -- Get all ancestors of interaction
  WITH RECURSIVE lineage AS (
      SELECT interaction_id, input_interaction_ids, 1 as depth
      FROM interactions 
      WHERE interaction_id = 123
      UNION ALL
      SELECT i.interaction_id, i.input_interaction_ids, l.depth + 1
      FROM interactions i
      JOIN lineage l ON i.interaction_id = ANY(l.input_interaction_ids)
  )
  SELECT * FROM lineage ORDER BY depth;
  ```

---

### 5. job_skills_staging ✅ DROP

**Schema Comment:**
> "Staging area for job skill extractor output - validated before promotion to job_requirements"

**Status:** Simple drop - no validation flow exists, skills go directly to tables.

---

### 6. organizations ⚠️ CRITICAL - ACTOR HIERARCHY DISCUSSION

**Schema Comment:**
> "Optional organization membership for recruiting firms, employers, etc."

**Context from Sandy's Log (Yesterday):**

Sandy discovered **actor hierarchy permissions**:
```python
def is_actor_allowed(actor_id, allowed_actor_id):
    """
    Sandy (4) can execute if instruction allows:
    - Sandy (4) - exact match
    - Copilots (3) - parent group
    - AI (2) - grandparent group  
    - actors (1) - root group
    """
    ancestors = get_ancestor_chain(actor_id)
    return allowed_actor_id in ancestors
```

**Current Actor Hierarchy** (from actors table):
```
actors (1) - ROOT
├─ AI (2)
│  └─ Copilots (3)
│     ├─ Sandy (4)
│     └─ Arden (5)
└─ Human (?)
   └─ xai, gershon, etc
```

**xai's Quote:**
> "Unfortunately, we didn't really do with it anything yet. So lets catch that ball and decide what to do with it."

**Discussion Points:**

1. **Is `parent_actor_id` sufficient for permissions?**
   - YES for hierarchy-based access
   - Sandy's code is elegant - tree traversal
   
2. **Do we need `organizations` table?**
   - MAYBE for multi-tenant scenarios
   - Example: Multiple recruiting firms using same Turing instance
   - Each org gets own actor subtree

3. **Current Need:**
   - Single organization (talent.yoga)
   - No multi-tenancy yet
   - Actor hierarchy works for team permissions

**Arden's Recommendation:**
- **DROP table** `organizations` - not needed yet
- **DOCUMENT** actor hierarchy permissions:
  - Add to WAVE_RUNNER_V2_DESIGN_DECISIONS.md
  - Show `get_ancestor_chain()` pattern
  - Example: "Copilots" group can execute any instruction allowing "AI"
- **FUTURE:** If we add multi-tenancy, add `organization_id` to actors table

**Questions for xai:**
1. Do we need additional permissions beyond hierarchy?
   - Example: "Sandy can access experimental workflows, Arden cannot"
2. Is multi-tenancy on roadmap?
3. Should we formalize actor groups (create actual group records)?

---

### 7. posting_field_mappings ⚠️ CRITICAL - DYNAMIC SOURCE ADAPTATION

**Schema Comment:**
> "Qwen-generated field mappings for dynamic source adaptation"

**xai's Explanation:**
> - We will have multiple job sites we fetch
> - These will have different fields
> - We want to normalize them into postings
> - We ask Qwen to create a mapping
> - We store that mapping in interactions (goes without saying)
> - Then we need to use that mapping to parse the JSON in the interactions into postings

**Current Reality:**
- We have `posting_sources` table (1 row) - defines sources
- We have `postings_staging` table (10 rows) - raw data before normalization
- We have `postings` table (2104 rows) - normalized data
- NO mapping generation workflow exists yet

**The Problem:**
Different job sites have different JSON structures:
```json
// Deutsche Bank
{"title": "...", "description": "...", "location": "..."}

// Indeed
{"jobTitle": "...", "jobDescription": "...", "formattedLocation": "..."}

// LinkedIn
{"position": "...", "details": "...", "workLocation": "..."}
```

**The Solution (xai's vision):**
1. Fetch raw JSON → `postings_staging`
2. LLM analyzes structure → generates field mapping
3. Mapping stored → where?
4. Normalization script uses mapping → creates `postings` record

**Architecture Decision Needed:**

**Option A: Store mapping in `posting_field_mappings` table**
```sql
posting_field_mappings (
    mapping_id,
    source_id,              -- FK to posting_sources
    field_mappings JSONB,   -- {"title": "jobTitle", ...}
    generated_by_interaction_id,
    created_at,
    active BOOLEAN
)
```
Pros: Fast lookup, reusable across postings from same source
Cons: Another table to maintain

**Option B: Store mapping in `interactions.output`**
```sql
-- Interaction output contains mapping
{
  "field_mappings": {
    "title": "jobTitle",
    "description": "jobDescription"
  }
}
```
Pros: Audit trail, follows "interactions is source of truth"
Cons: Must query interactions to get mapping, slower

**Option C: Hybrid - Generate in interactions, cache in table**
- LLM generates mapping → stored in interaction
- First successful use → copied to `posting_field_mappings`
- Subsequent posts from same source → use cached mapping
- Mapping drift detected → regenerate

**Arden's Recommendation:** **Option C - Hybrid Approach**

Reasoning:
- Follows "interactions is source of truth" principle
- Caches for performance (don't re-map every posting)
- Audit trail preserved (which interaction generated this?)
- Can detect source schema changes

**Implementation:**
1. **KEEP table** `posting_field_mappings` - redesign schema
2. **CREATE workflow** 3XXX for source adaptation:
   - Conversation 1: Analyze source JSON structure
   - Conversation 2: Generate field mapping
   - Conversation 3: Validate mapping (test on sample)
   - Script: Cache mapping to table
   - Script: Apply mapping to normalize posting
3. **DOCUMENT** in WORKFLOW_CREATION_COOKBOOK.md

**Questions for xai:**
1. Should mapping be per-source or per-posting?
2. How do we detect source schema changes?
3. What validation do we need before trusting a mapping?

---

### 8. production_runs ✅ DROP

**Schema Comment:**
> "Production execution of recipes using real job postings (not synthetic test variations). Same recipes tested in recipe_runs, deployed here with real data!"

**Status:** Recipe system deleted. Workflows replace this. Drop table.

---

### 9. profile_job_matches ⚠️ CRITICAL - MATCHING INFRASTRUCTURE

**xai's Question:**
> "Look, we match postings against profiles. Shouldnt we store the results? Think of hundreds of users and dozens of job sites, thousands of jobs. Lets discuss."

**Schema Comment:**
> "Match scores between profiles and job postings"

**Business Context** (from [[rfa_talent_yoga]]):
- Core feature: "Skills gap analysis against personal profile"
- "Application success probability calculation"
- 2M+ unemployed users (scale consideration)
- Real-time match updates as new jobs arrive

**Current Reality:**
- `profiles` table: 4 rows
- `postings` table: 2104 rows
- NO matching results stored
- Match calculation happens... where?

**The Scale Problem:**
```
100 users × 10,000 postings = 1M potential matches
1000 users × 10,000 postings = 10M potential matches

Calculate on-demand? Too slow for dashboard.
Pre-calculate all? 10M rows, storage explosion.
```

**Architecture Decision Needed:**

**Option A: Full Match Matrix (all combinations)**
```sql
profile_job_matches (
    match_id,
    profile_id,
    posting_id,
    match_score DECIMAL,      -- 0.0 to 1.0
    calculated_at TIMESTAMP,
    match_details JSONB       -- Skills matched, gaps, etc
)
```
Pros: Fast lookup, pre-computed
Cons: 10M+ rows, massive storage

**Option B: Sparse Matrix (only good matches)**
```sql
profile_job_matches (
    ...
    match_score DECIMAL CHECK (match_score >= 0.6)  -- Only store decent matches
)
```
Pros: 90% smaller (most matches are poor)
Cons: Can't show "why did this job NOT match?"

**Option C: On-Demand with Cache**
```sql
profile_job_matches (
    ...
    calculated_at TIMESTAMP,
    expires_at TIMESTAMP      -- Re-calculate after 7 days
)
-- Only calculate when user requests
-- Cache result for performance
-- Expire old matches
```
Pros: Storage efficient, always fresh
Cons: First load slow

**Option D: Event-Driven Match Queue**
```sql
-- When new posting arrives:
-- 1. Insert to match_queue for ALL profiles
-- 2. Worker processes queue (batch scoring)
-- 3. Only store matches > threshold
-- 4. Notify users of good matches

match_queue (
    queue_id,
    profile_id,
    posting_id,
    status,       -- 'pending', 'scored', 'notified'
    priority
)
```
Pros: Scalable, async, can prioritize
Cons: Complex, needs worker infrastructure

**Arden's Recommendation:** **Option D - Event-Driven with Sparse Storage**

Reasoning:
- Scales to millions of users
- New posting → queue match jobs for all profiles
- Worker scores in background
- Store only matches > 60% (IHL <= 60% per workflow 1124)
- User gets notifications of good matches

**Implementation:**
1. **KEEP & REDESIGN** `profile_job_matches` table:
   ```sql
   profile_job_matches (
       match_id BIGSERIAL PRIMARY KEY,
       profile_id INT REFERENCES profiles,
       posting_id BIGINT REFERENCES postings,
       match_score DECIMAL(5,4) CHECK (match_score >= 0.60),
       skills_matched TEXT[],
       skills_missing TEXT[],
       calculated_at TIMESTAMP,
       calculated_by_interaction_id BIGINT REFERENCES interactions,
       user_decision TEXT,  -- 'interested', 'applied', 'skipped'
       UNIQUE(profile_id, posting_id)
   )
   ```

2. **CREATE workflow** 3XXX for matching:
   - Input: profile_id + posting_id
   - Conversation 1: Extract required skills from posting
   - Conversation 2: Compare with profile skills
   - Conversation 3: Calculate match score
   - Output: Match record + notification

3. **CREATE batch processor:**
   - Triggered when new posting arrives
   - Creates interactions for all active profiles
   - Wave Runner processes queue
   - Results stored in profile_job_matches

**Questions for xai:**
1. What's the match score threshold for notifications?
2. Should we prioritize certain users (paid tier)?
3. Do we re-calculate matches when profile updates?
4. Storage budget for match results?

---

### 10. profile_skills_staging ✅ DROP

**Schema Comment:**
> "Staging area for skill extractor output - validated before promotion to profile_skills"

**Status:** No validation flow exists. Drop table. Skills go directly to `profile_skills`.

---

### 11. script_executions ✅ DROP

**Status:** We track script execution in `interactions` now. Drop table.

---

### 12. skill_aliases_staging ❓ DISCUSS - TAXONOMY MAINTENANCE

**Schema Comment:**
> "Staging area for skill mapper output - validated before promotion to skill_aliases"

**Context from [[3003_taxonomy_maintenance_turing_native]]:**
- Workflow for maintaining n-level skill hierarchy
- Gopher approach: LLM navigates tree
- Skills need to be mapped/aliased
- Quality control before promoting to taxonomy

**Current Reality:**
- `skill_aliases` table: 973 rows (active taxonomy)
- `skills_pending_taxonomy` table: 1090 rows (unprocessed)
- Workflow 3003 exists for taxonomy maintenance
- NO staging table being used

**xai's Question:**
> "read [[3003_taxonomy_maintenance_turing_native]]. This we need. And more of it. Do we need this table? You decide."

**Arden's Analysis:**

Workflow 3003 conversations:
1. `w3003_query_skills_from_db` - Get all skills
2. `w3003_analyze_taxonomy_structure` - Propose organization
3. `w3003_organize_skills_semantically` - Organize (loop until done)
4. `w3003_check_organization_threshold` - Check if MAX_ITERATIONS or COMPLETE
5. `w3003_write_skills_to_filesystem` - Save to `/home/xai/Documents/ty_learn/skills_taxonomy`
6. `w3003_generate_hierarchical_index` - Create index

**Missing:** Promotion flow from staging → taxonomy

**Recommendation:**
- **DROP table** `skill_aliases_staging` - not used by workflow 3003
- **ALTERNATIVE:** Use `skills_pending_taxonomy` (already has 1090 rows)
- **WORKFLOW:** Add conversation to 3003:
  - w3003_validate_aliases (review proposed aliases)
  - w3003_promote_to_taxonomy (move to skill_aliases)

**Questions for xai:**
1. Is human review needed before promoting skills?
2. Should alias generation be separate workflow from organization?
3. What's the quality bar for taxonomy promotion?

---

### 13. test_cases_history ⚠️ CRITICAL - TESTING STRATEGY

**Schema Comment:**
> "Audit trail of all changes to variations table. Tracks test data evolution, helps identify when variations were modified that might affect test reproducibility."

**xai's Guidance:**
> "Okay, test cases. How do we test? Well, look at /home/xai/Documents/ty_learn/data/llmcore.db if you want to see how we did it."
> 
> - variations are test data
> - actors are in actors
> - batches define how often we run
> - ...then we run these interactions
> - we consider every model that performs all batches successfully
> - we select the best models as champions and runner-ups
> 
> "Lets talk about how we would do that in our schema. As an example: in workflow 3001, we use gemma2:latest as a grader. That model is too large for our GPU. Would be nice to run the same prompt against other, smaller models. How would we design that?"

**Current Reality:**
- `test_cases` table: 2684 rows (active test cases!)
- `test_cases_history` table: 0 rows (audit trail)
- `batches` table: 10 rows (test groupings)
- `llmcore.db`: 32MB SQLite with old recipe/variation/session schema

**The Testing Vision:**

1. **Test Data:** Variations (old schema) or... what in new schema?
2. **Test Actors:** Different models to evaluate
3. **Test Batches:** Run X times to verify consistency
4. **Success Criteria:** All batches pass = champion model
5. **Model Selection:** Best performer wins, runner-up as backup

**Current Gap:** No formalized A/B testing for models

**Workflow 3001 Example:**
- Conversation 3336: Uses `gemma2:latest` for grading
- Problem: Too large for GPU
- Need: Test `gemma2:9b`, `qwen2.5:7b`, `phi3:medium` on same prompts
- Select: Best performing smaller model

**Architecture Decision Needed:**

**Option A: Test Cases Define Model Variants**
```sql
test_cases (
    test_case_id,
    test_case_name,
    workflow_id,
    conversation_id,
    test_input JSONB,           -- The prompt/data to test
    expected_output JSONB,      -- What we expect
    model_variants TEXT[]       -- ['gemma2:9b', 'qwen2.5:7b', 'phi3:medium']
)

-- Run each test case with each model variant
-- Compare results
-- Select champion
```

**Option B: Batch Runs with Model Swapping**
```sql
batches (
    batch_id,
    batch_name,
    workflow_id,
    conversation_id,
    model_to_test TEXT,         -- Which model to evaluate
    baseline_model TEXT,        -- Current champion
    test_run_count INT          -- Run N times for consistency
)

-- Run workflow N times with test model
-- Compare with baseline
-- Promote if better
```

**Option C: Model Testing Workflow**
```
Workflow 3XXX: Model Evaluation
1. Input: conversation_id + test_prompts[] + candidate_models[]
2. For each model:
   - Run all prompts
   - Collect outputs
3. LLM grades outputs (quality, accuracy, consistency)
4. Statistical comparison
5. Output: Champion model + confidence score
```

**Arden's Recommendation:** **Combination of B + C**

1. **KEEP table** `test_cases` (2684 rows - active tests!)
2. **KEEP table** `test_cases_history` (for audit trail)
3. **ADD columns** to `batches` for model testing
4. **CREATE workflow** 3XXX for model evaluation:
   ```
   Workflow 3XXX: Model Benchmarking
   Input: {
       conversation_id: 3336,
       current_model: "gemma2:latest",
       candidate_models: ["gemma2:9b", "qwen2.5:7b", "phi3:medium"],
       test_cases: [123, 456, 789]
   }
   
   For each candidate model:
       - Run test_cases with this model
       - Store results in interactions
       - Grade output quality
   
   Compare all results:
       - Accuracy
       - Speed
       - GPU usage
       - Consistency (run 3 times)
   
   Output: Champion recommendation
   ```

**Implementation:**
```sql
-- Extend batches table
ALTER TABLE batches ADD COLUMN model_variant TEXT;
ALTER TABLE batches ADD COLUMN baseline_model TEXT;
ALTER TABLE batches ADD COLUMN test_purpose TEXT; -- 'model_eval', 'regression', 'stress'

-- Track model performance
CREATE TABLE model_performance (
    performance_id BIGSERIAL PRIMARY KEY,
    model_name TEXT,
    conversation_id INT,
    test_case_id BIGINT,
    batch_id INT,
    execution_time_ms INT,
    quality_score DECIMAL,
    gpu_memory_mb INT,
    tested_at TIMESTAMP,
    interaction_id BIGINT REFERENCES interactions
);
```

**Questions for xai:**
1. Should model evaluation be automated or manual?
2. What metrics matter most? (Speed vs quality vs GPU usage)
3. How many test runs to confirm consistency?
4. Auto-promote champion or require human approval?

---

### 14. trigger_executions ✅ CONFIRM & DROP

**xai's Question:**
> "Yup. That can go. Now, when a trigger fires, we get an interaction, right? Right?"

**Arden's Answer:** **Let me check...**

<function_calls>
<invoke name="run_in_terminal">
<parameter name="command">cd /home/xai/Documents/ty_learn && ./scripts/q.sh "SELECT * FROM workflow_triggers WHERE trigger_id = 2;"