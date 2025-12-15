# Workflow Execution Trace

**Generated:** 2025-12-01 03:51:06

## Workflow Context

**Workflow ID:** 3001
**Workflow Name:** Complete Job Processing Pipeline
**Started:** 2025-12-01 03:49:46
**Completed:** 2025-12-01 03:51:06
**Duration:** 80.1 seconds
**Interactions:** 1 completed, 0 failed

---

## ✅ Interaction 1: Fetch Jobs from Deutsche Bank API

**Interaction ID:** 37139
**Duration:** 79.18s
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
{
  "max_jobs": 2000,
  "search_text": "",
  "skip_rate_limit": true
}
````

### Actual Output

````json
{
  "data": {
    "error": "current transaction is aborted, commands ignored until end of transaction block\n",
    "status": "[FAILED]",
    "traceback": "Traceback (most recent call last):\n  File \"/home/xai/Documents/ty_wave/core/wave_runner/actors/db_job_fetcher.py\", line 346, in process\n    cursor.execute(\"\"\"\n  File \"/home/xai/.local/lib/python3.10/site-packages/psycopg2/extras.py\", line 236, in execute\n    return super().execute(query, vars)\npsycopg2.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block\n\n",
    "jobs_fetched": 0
  },
  "status": "success"
}
````

---

## Summary

- **Total interactions:** 1
- **Completed:** 1
- **Failed:** 0
- **Total duration:** 80.1s
- **Avg per interaction:** 80.10s
