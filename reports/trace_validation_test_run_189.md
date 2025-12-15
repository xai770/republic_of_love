# Workflow Execution Trace

**Generated:** 2025-11-26 13:56:12

## Workflow Context

**Workflow ID:** 3001
**Workflow Name:** Complete Job Processing Pipeline
**Posting ID:** 4794
**Job Title:** Generic Role
**Started:** 2025-11-26 13:56:12
**Completed:** 2025-11-26 13:56:12
**Duration:** 0.4 seconds
**Interactions:** 2 completed, 0 failed

---

## ✅ Interaction 1: Fetch Jobs from Deutsche Bank API

**Interaction ID:** 614
**Duration:** 0.26s
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
- **Next:** Conversation 9193

**API failure - terminate** (Priority: 50)
- **Condition:** `[FAILED]`
- **Description:** Job fetcher API failed - cannot proceed, terminate workflow
- **Next:** END (terminal)

**Route to check summary (success path)** (Priority: 50)
- **Condition:** `success`
- **Description:** Jobs fetched successfully - proceed to check summary
- **Next:** Conversation 9193

**API timeout - terminate** (Priority: 49)
- **Condition:** `[TIMEOUT]`
- **Description:** Job fetcher timed out - cannot proceed, terminate workflow
- **Next:** END (terminal)

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{}
````

### Actual Output

````json
{
  "data": {
    "status": "[RATE_LIMITED]",
    "message": "Already fetched 5 jobs today",
    "jobs_fetched": 0
  },
  "status": "success"
}
````

### Child Interactions Created

- Interaction 615

---

## ✅ Interaction 2: Validate Job Description

**Interaction ID:** 615
**Duration:** 0.09s
**Status:** completed

### Conversation Configuration

**Conversation ID:** 9193
**Name:** Validate Job Description
**Description:** Validates job_description exists and meets minimum quality standards
**Type:** single_actor
**Context Strategy:** isolated

### Actor Configuration

**Actor ID:** 74
**Name:** sql_query_executor
**Type:** script
**Script:** core/wave_runner/actors/sql_query_executor.py

### Prompt Template

````
{
  "query": "SELECT CASE WHEN job_description IS NULL THEN '[NO_DESCRIPTION]' WHEN LENGTH(job_description) < 100 THEN '[TOO_SHORT]' ELSE '[VALID]' END as validation_result FROM postings WHERE posting_id = {posting_id}",
  "result_field": "validation_result"
}
````

### Branching Logic

After this interaction completes, the following branching rules apply:

**Valid description - continue to Check Summary** (Priority: 10)
- **Condition:** `[VALID]`
- **Next:** Conversation 9184

**No description - end workflow** (Priority: 10)
- **Condition:** `[NO_DESCRIPTION]`
- **Next:** END (terminal)

**Description too short - end workflow** (Priority: 10)
- **Condition:** `[TOO_SHORT]`
- **Next:** END (terminal)

### Parent Interactions

This interaction received data from:

- Interaction 614

### Actual Input (Substituted)

This is what was actually executed (all placeholders substituted):

````json
{
  "query": "SELECT CASE WHEN job_description IS NULL THEN '[NO_DESCRIPTION]' WHEN LENGTH(job_description) < 100 THEN '[TOO_SHORT]' ELSE '[VALID]' END as validation_result FROM postings WHERE posting_id = 4794",
  "result_field": "validation_result"
}
````

### Actual Output

````json
{
  "data": {
    "status": "[RUN]",
    "query_result": {
      "validation_result": "[TOO_SHORT]"
    },
    "result_value": "[TOO_SHORT]"
  },
  "status": "success"
}
````

---

## Summary

- **Total interactions:** 2
- **Completed:** 2
- **Failed:** 0
- **Total duration:** 0.4s
- **Avg per interaction:** 0.18s
