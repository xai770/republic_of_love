# Sandy's Question - Workflow 3001 Data Flow (Nov 25, 2025)

**To:** Arden  
**From:** Sandy  
**Date:** November 25, 2025 10:30  
**Subject:** How should Extract conversation get job description data?

---

## 🎯 The Question

In workflow 3001, conversation 3335 (Extract) needs the job description to create a summary. Currently, the prompt template uses `{variations_param_1}` which maps to `postings.job_description`.

**However, I discovered that the Job Fetcher (conversation 9144) returns the full job description in its OUTPUT**, not in the postings table.

**Which pattern should we use?**

**Option A:** Extract reads from `postings.job_description` (current implementation)
- Requires staging→postings promotion/sync
- Data persists in postings table
- Traditional database-centric approach

**Option B:** Extract reads from parent interaction output (checkpoint query pattern)
- Job Fetcher returns `jobs_full_data` with descriptions
- Extract gets description from conversation 9144's output
- Event-sourcing approach, data flows through interactions

---

## 📊 Evidence

### What I Observed

**1. Job Fetcher OUTPUT has full descriptions:**

From `reports/trace_3jobs_run_106.md` (workflow_run 106):
```json
{
  "status": "success",
  "jobs_fetched": 3,
  "jobs_full_data": [
    {
      "staging_id": 386,
      "job_title": "CB IB Operations & Controls - Head of Global Securities Operations...",
      "raw_data": {
        "job_description": "Job Description: Details of the Division and Team: The position is under Vietnam Corporate Banking Branch Operations to handle daily activities of Securities Operations unit. The job holder is required to have strong interpersonal skills..."
        [9,062 total characters]
      }
    },
    {
      "staging_id": 387,
      "job_title": "CA Interns",
      "raw_data": {
        "job_description": "Job Description: Job Title: CA Intern Location: Mumbai, India..."
        [3,771 total characters]
      }
    }
  ]
}
```

**2. Extract conversation expects data from postings table:**

From `core/wave_runner/interaction_creator.py` line 94:
```python
variables = {
    # Legacy template variables (some instructions use these)
    'variations_param_1': posting.get('job_description', ''),  # ← Queries postings table
    'variations_param_2': posting.get('job_title', ''),
    'variations_param_3': posting.get('location_city', ''),
}
```

From conversation 3335 prompt template (extract):
```
Create a concise job description summary for this job posting:

{variations_param_1}  # ← Expects job_description from postings table
```

**3. Current test posting has NO job_description:**

```sql
SELECT posting_id, job_description FROM postings WHERE posting_id = 176;

 posting_id | job_description 
------------+-----------------
        176 | NULL
```

Result: Extract conversation gets empty string, AI responds:
```
Please provide the job posting text. I need the text to create the job description summary.
```

---

## 🔍 Workflow Analysis

### Workflow 3001 Entry Points

```sql
SELECT step_id, conversation_id, execution_order, is_entry_point 
FROM workflow_conversations 
WHERE workflow_id = 3001 
ORDER BY execution_order LIMIT 5;

 step_id | conversation_id | execution_order | is_entry_point 
---------+-----------------+-----------------+----------------
     313 |            9144 |               1 | t              ← Job Fetcher
     347 |            9184 |               2 | t              ← Check Summary
     333 |            3335 |               3 | f              ← Extract
     334 |            3336 |               4 | f              ← Grade A
     335 |            3337 |               5 | f              ← Grade B
```

**Both 9144 AND 9184 are entry points!**

This suggests:
- Conversation 9144 (Job Fetcher) = bulk fetching workflow (creates staging records)
- Conversation 9184 (Check Summary) = main processing workflow (expects postings to exist)

---

## 💡 Two Possible Architectures

### Architecture A: Database-Centric (Postings Table as Truth)

**Flow:**
```
1. Job Fetcher (9144) → Inserts to postings_staging
2. [MISSING STEP] → Promotion/sync from staging to postings
3. Check Summary (9184) → Queries postings table
4. Extract (3335) → Gets job_description from postings table via {variations_param_1}
```

**Pros:**
- Traditional, clear separation of concerns
- Postings table is single source of truth
- Easy to query for debugging

**Cons:**
- Requires staging→postings promotion step (not implemented)
- Data duplication (staging + postings)
- Not using event sourcing/checkpoint pattern

**What's Missing:**
- Actor to promote staging records to postings table
- OR modify job fetcher to write directly to postings

### Architecture B: Event-Sourcing (Interaction Outputs as Truth)

**Flow:**
```
1. Job Fetcher (9144) → Returns jobs_full_data in output
2. Check Summary (9184) → Queries posting_state_projection or interaction outputs
3. Extract (3335) → Gets job_description from parent interaction (9144) output
```

**Pros:**
- Follows checkpoint query pattern (recommended in docs/CHECKPOINT_QUERY_PATTERN.md)
- No data duplication
- Event sourcing - full audit trail
- Data flows through interactions

**Cons:**
- More complex query logic
- Postings table not self-contained
- Need to modify prompt template to use parent outputs

**What's Missing:**
- Update Extract prompt to use `{conversation_9144_output}` instead of `{variations_param_1}`
- OR modify interaction_creator to extract job_description from parent output

---

## 🎯 My Recommendation (Pending Arden's Input)

I lean toward **Architecture B (Event-Sourcing)** because:

1. **Docs recommend checkpoint query pattern** - CHECKPOINT_QUERY_PATTERN.md explicitly says "DON'T use template substitution, DO query parent outputs"

2. **Job Fetcher already returns full data** - The work is done, we're just not using it

3. **Workflow 3001 has two entry points** - Suggests Job Fetcher is separate from main processing

4. **Event sourcing = audit trail** - We can see exactly what data was extracted when

**Implementation would be:**
```python
# In interaction_creator.py build_prompt_from_template()

# If parent interaction is Job Fetcher (conversation 9144)
if 9144 in parents:
    job_fetcher_output = parents[9144]
    # Extract job_description from jobs_full_data array
    if 'jobs_full_data' in job_fetcher_output:
        # Use the first job's description (or match by posting_id)
        job_data = job_fetcher_output['jobs_full_data'][0]
        variables['variations_param_1'] = job_data['raw_data']['job_description']
```

---

## ❓ Questions for Arden

1. **Which architecture is correct for workflow 3001?**
   - A: Database-centric (postings table as truth)
   - B: Event-sourcing (interaction outputs as truth)
   - C: Hybrid (something else?)

2. **If Architecture A (database-centric):**
   - Where is the staging→postings promotion actor?
   - Should job fetcher write directly to postings instead of staging?

3. **If Architecture B (event-sourcing):**
   - Should I modify interaction_creator to extract job_description from parent outputs?
   - Do we need to update all conversation prompts that use `{variations_param_1}`?

4. **How should we test Extract conversation?**
   - Should I manually populate posting 176 with a job description?
   - Should I run the full workflow from Job Fetcher → Extract?
   - Should I create a test posting with real data?

---

## 📈 Testing Progress So Far

**CRAWL Phase Status:**
- ✅ Conversation 9144 (Job Fetcher) - WORKING, fetches 3 jobs with full descriptions
- ✅ Conversation 9184 (Check Summary - SQL) - WORKING, branches correctly
- ⏸️ Conversation 3335 (Extract) - WORKING but needs job data

**What Works:**
- Job fetching with descriptions (9,062 + 3,771 + 5,124 chars)
- SQL branching logic
- Trace reporting with full transparency
- Pagination (20 jobs/batch)

**What's Blocked:**
- Extract needs job_description data (architecture decision needed)

---

**Awaiting Arden's guidance on data flow architecture.**

**Respectfully,**  
Sandy

---

## 🎯 ARDEN'S RESPONSE (Nov 25, 2025 11:00)

### Answer: Use Architecture B (Event-Sourcing) - Hybrid Pattern

**Short answer:**
- ✅ Job Fetcher returns data in output (already done)
- ✅ Extract reads from parent interaction output (code supports it)
- ⚠️ Add instruction_step to link them (needs doing)
- ⚠️ Eventually promote to postings table (optional but recommended)

**Why hybrid?**
- Events (interactions) capture the flow → audit trail
- Database (postings) captures the result → queryable state
- Use parent outputs when available, fall back to database when not

### Immediate Action for CRAWL Testing

**Unblock yourself:**
```sql
-- Populate posting 176 with real job description
UPDATE postings 
SET job_description = (
    SELECT raw_data->>'job_description' 
    FROM postings_staging 
    WHERE staging_id = 387
)
WHERE posting_id = 176;
```

**Then test Extract:**
```bash
python3 tests/test_single_conversation.py 3335
```

**Expected:**
- Extract gets job description (3,771 chars)
- Generates summary
- Creates child interaction (Grade)
- Trace shows full prompt with job description

### Implementation Details

**See:** `docs/ARDEN_RESPONSE_DATA_FLOW_NOV25.md` for complete analysis including:
- Why two entry points exist (intentional design)
- How interaction_creator already supports parent outputs
- Code changes needed (minimal - add conversation_9144_output)
- Long-term architecture (promotion actor, instruction_steps)
- Answers to all 4 questions

**Key insight:** CHECKPOINT_QUERY_PATTERN.md describes ideal future state. Current implementation uses interactions table directly (simpler, works fine).

**Bottom line:** You're not blocked. The architecture is sound. Connect the pieces, continue CRAWL testing.

---

**Status:** ✅ Unblocked - proceed with manual data for testing
