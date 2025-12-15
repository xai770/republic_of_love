# Workflow Execution Trace

**Generated:** 2025-11-26 10:43:19

## Workflow Context

**Workflow ID:** 3001
**Workflow Name:** Complete Job Processing Pipeline
**Posting ID:** 4794
**Job Title:** Generic Role
**Started:** 2025-11-26 10:42:05
**Completed:** 2025-11-26 10:43:19
**Duration:** 73.2 seconds
**Interactions:** 4 completed, 0 failed

---

## ✅ Interaction 1: Fetch Jobs from Deutsche Bank API

**Interaction ID:** 526
**Duration:** 56.37s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9144
**Name:** Fetch Jobs from Deutsche Bank API
**Description:** Fetches job postings from Deutsche Bank API, checks for duplicates, parses locations, stores in postings table
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 56
**Name:** db_job_fetcher
**Type:** script
**Script:** core/wave_runner/actors/db_job_fetcher.py

### Prompt Template

````
{
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1,
  "skip_rate_limit": true
}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**skip_if_rate_limited** (Priority: 100)
- **Condition:** `[RATE_LIMITED]`
- **Description:** Skip to extraction if fetcher is rate-limited (already ran today)
- **Next:** Conversation 9184

**API failure - terminate** (Priority: 50)
- **Condition:** `[FAILED]`
- **Description:** Job fetcher API failed - cannot proceed, terminate workflow
- **Next:** END (terminal)

**Route to check summary (success path)** (Priority: 50)
- **Condition:** `success`
- **Description:** Jobs fetched successfully - proceed to check summary
- **Next:** Conversation 9184

**API timeout - terminate** (Priority: 49)
- **Condition:** `[TIMEOUT]`
- **Description:** Job fetcher timed out - cannot proceed, terminate workflow
- **Next:** END (terminal)

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "user_id": 1,
  "max_jobs": 50,
  "source_id": 1,
  "skip_rate_limit": true
}
````

### Actual Output

````json
{
  "data": {
    "status": "success",
    "staging_ids": [],
    "jobs_fetched": 0,
    "jobs_full_data": [],
    "batches_fetched": 12,
    "total_available": 0
  },
  "status": "success"
}
````

### Child Interactions Created

- Interaction 527

---

## ✅ Interaction 2: Check if Summary Exists

**Interaction ID:** 527
**Duration:** 0.08s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9184
**Name:** Check if Summary Exists
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 74
**Name:** sql_query_executor
**Type:** script
**Script:** core/wave_runner/actors/sql_query_executor.py

### Prompt Template

````
{"query": "SELECT CASE WHEN state ? 'current_summary' OR state ? 'extract_summary' THEN true ELSE false END as summary_exists FROM workflow_runs WHERE workflow_run_id = {workflow_run_id}", "result_field": "summary_exists", "branch_map": {"true": "[SKIP]", "false": "[RUN]", "null": "[RUN]", "error": "[RUN]"}}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Skip extraction if summary exists** (Priority: 100)
- **Condition:** `[SKIP]`
- **Description:** Summary already exists, skip extraction and grading
- **Next:** Conversation 9185

**Run extraction if summary missing** (Priority: 90)
- **Condition:** `[RUN]`
- **Description:** Summary missing, proceed with extraction
- **Next:** Conversation 3335

**C2 check timeout - assume missing** (Priority: 39)
- **Condition:** `[TIMEOUT]`
- **Description:** Summary check timed out - assume missing
- **Next:** Conversation 3335

**check_summary_failed** (Priority: 10)
- **Condition:** `[FAILED]`
- **Description:** Check failed - assume not executed, run extraction
- **Next:** Conversation 3335

### Parent Interactions

This interaction received data from:

- Interaction 526

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "query": "SELECT CASE WHEN state ? 'current_summary' OR state ? 'extract_summary' THEN true ELSE false END as summary_exists FROM workflow_runs WHERE workflow_run_id = {workflow_run_id}",
  "branch_map": {
    "null": "[RUN]",
    "true": "[SKIP]",
    "error": "[RUN]",
    "false": "[RUN]"
  },
  "result_field": "summary_exists"
}
````

### Actual Output

````json
{
  "data": {
    "status": "[RUN]",
    "query_result": {
      "summary_exists": false
    },
    "result_value": "false"
  },
  "status": "success"
}
````

### Child Interactions Created

- Interaction 528

---

## ✅ Interaction 3: session_a_gemma3_extract

**Interaction ID:** 528
**Duration:** 2.74s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3335
**Name:** session_a_gemma3_extract
**Description:** Extract job summary
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 13
**Name:** gemma3:1b
**Type:** ai_model
**Model:** gemma3:1b

### Prompt Template

**Step Description:** Extract with gemma3:1b

````
Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Route to first grader** (Priority: 1)
- **Condition:** `*`
- **Description:** Extraction complete - send to first grader (gemma2) for QA review
- **Next:** Conversation 3336

**Route to second grader (parallel evaluation)** (Priority: 1)
- **Condition:** `*`
- **Description:** Second grader independently evaluates the same summary
- **Next:** Conversation 3337

### Parent Interactions

This interaction received data from:

- Interaction 527

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
Create a concise job description summary for this job posting:

We need someone to do stuff. Must have skills. Send resume to apply. Competitive salary.

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do not add information.
````

### Actual Output

````
Please provide the job posting text. I need the text to create the job description summary. 😊
````

**Metadata:** `{"model": "gemma3:1b", "latency_ms": 2719}`

### Child Interactions Created

- Interaction 529

---

## ✅ Interaction 4: session_b_gemma2_grade

**Interaction ID:** 529
**Duration:** 13.99s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 3336
**Name:** session_b_gemma2_grade
**Description:** Grade extraction with gemma2
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 12
**Name:** gemma2:latest
**Type:** ai_model
**Model:** gemma2:latest

### Prompt Template

**Step Description:** Grade with gemma2:latest

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
{conversation_3335_output}
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Parent Interactions

This interaction received data from:

- Interaction 528

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````
# Instructions: 
## 1. Read the following **raw posting**:

--- start raw posting ---
We need someone to do stuff. Must have skills. Send resume to apply. Competitive salary.
--- end raw posting ---

## 2. Read the following **summary** created by an AI:

--- start summary ---
Please provide the job posting text. I need the text to create the job description summary. 😊
--- end summary ---

## 3. Grade the summary

Compare the summary against the original posting. Check:
- **Accuracy**: Does the summary match the actual job posting? No hallucinated details?
- **Completeness**: Are key responsibilities and requirements included?
- **Formatting**: Does it follow the ===OUTPUT TEMPLATE=== format?

## 4. Provide your decision

**[PASS]** if the summary is accurate, complete, and well-formatted.
**[FAIL]** if the summary has errors, omissions, or hallucinations.

Start your response with [PASS] or [FAIL], then explain your reasoning.
````

### Actual Output

````
[FAIL] 

The AI's summary completely missed the point of the raw posting.  It requested the job posting text instead of summarizing it. There is no attempt to extract information about the needed skills, salary, or application process from the original posting.  


Let me know if you want me to try summarizing the raw posting!
````

**Metadata:** `{"model": "gemma2:latest", "latency_ms": 13964}`

---

## Summary

- **Total interactions:** 4
- **Completed:** 4
- **Failed:** 0
- **Total duration:** 73.2s
- **Avg per interaction:** 18.30s
