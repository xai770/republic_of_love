# Failure Management Cookbook

**Author:** Sandy (GitHub Copilot)  
**Date:** December 4, 2025  
**Status:** Active

## Overview

At scale (2,000+ job sites, 500K+ interactions/week), failure management is critical infrastructure. This document describes how Turing handles failures intelligently.

## Core Principle

> **Failures are classified at the moment they occur, not later.**

The runner has full context when an exception is caught: the exception type, the error message, the actor type, the retry count. We use this context immediately to make intelligent retry decisions.

## Failure Taxonomy

```
Failure Types:
├── Transient (retry will likely succeed)
│   ├── timeout      - Model/script took too long
│   ├── interrupted  - Runner was killed (SIGTERM)
│   ├── rate_limit   - API rate limit hit
│   └── connection   - Network/database blip
│
├── Deterministic (retry will fail the same way)
│   ├── invalid_input    - Bad data provided
│   ├── invalid_output   - LLM gave unparseable response (retry once)
│   ├── script_error     - Script bug (non-zero exit)
│   └── not_found        - Resource doesn't exist
│
└── Resource (needs intervention)
    ├── oom          - Out of memory
    └── disk_full    - Storage exhausted
```

## Schema

```sql
-- interactions table
failure_type    TEXT    -- Classification: timeout, interrupted, rate_limit, etc.
retry_count     INTEGER DEFAULT 0   -- How many times we've retried
max_retries     INTEGER DEFAULT 3   -- Maximum retry attempts
error_message   TEXT    -- Full error details
```

## Retry Logic

```python
# In runner.py exception handler:
failure_type, is_retriable = classify_failure(exception, error_message)
will_retry = is_retriable AND retry_count < max_retries

if will_retry:
    status = 'pending'      # Will be picked up again
    retry_count += 1
else:
    status = 'failed'       # Permanent failure
```

### What Gets Retried Automatically

| Failure Type | Retriable | Rationale |
|--------------|-----------|-----------|
| `timeout` | ✅ Yes | Model was busy, try again |
| `interrupted` | ✅ Yes | Not our fault, runner was killed |
| `rate_limit` | ✅ Yes | Wait and retry |
| `connection` | ✅ Yes | Network blip |
| `invalid_output` | ✅ Yes (1x) | LLM is non-deterministic |
| `invalid_input` | ❌ No | Data won't magically fix itself |
| `script_error` | ❌ No | Bug needs code fix |
| `not_found` | ❌ No | Resource doesn't exist |
| `oom` | ❌ No | Needs intervention |
| `disk_full` | ❌ No | Needs intervention |
| `unknown` | ✅ Yes (1x) | Give it a chance |

## Querying Failures

```bash
# All failures by type
./scripts/q.sh "SELECT failure_type, COUNT(*) FROM interactions 
                WHERE status = 'failed' 
                GROUP BY failure_type ORDER BY 2 DESC"

# Recent failures with context
./scripts/q.sh "SELECT i.interaction_id, c.conversation_name, 
                       i.failure_type, i.retry_count, 
                       LEFT(i.error_message, 80)
                FROM interactions i 
                JOIN conversations c USING(conversation_id)
                WHERE i.status = 'failed' 
                  AND i.updated_at > NOW() - INTERVAL '24 hours'
                ORDER BY i.updated_at DESC"

# Stuck interactions (running too long)
./scripts/q.sh "SELECT interaction_id, conversation_id, started_at
                FROM interactions 
                WHERE status = 'running' 
                  AND started_at < NOW() - INTERVAL '30 minutes'"
```

## Recovery Patterns

### Pattern 1: Timeout Burst (Model Overload)

**Symptom:** Many `timeout` failures in short period

**Diagnosis:**
```bash
./scripts/q.sh "SELECT DATE_TRUNC('hour', updated_at) as hour, 
                       COUNT(*) as timeouts
                FROM interactions 
                WHERE failure_type = 'timeout'
                GROUP BY 1 ORDER BY 1 DESC LIMIT 10"
```

**Action:** These retry automatically. If persistent, check Ollama load or increase timeout.

### Pattern 2: Interrupted Workflow

**Symptom:** Workflow status = 'interrupted', interactions stuck as 'failed' with no error_message

**Diagnosis:**
```bash
./scripts/q.sh "SELECT i.interaction_id, i.status, i.failure_type, i.error_message
                FROM interactions i
                JOIN workflow_runs wr USING(workflow_run_id)
                WHERE wr.status = 'interrupted'
                  AND i.status IN ('running', 'failed')
                LIMIT 20"
```

**Action:** Reset interrupted interactions to pending:
```bash
./scripts/q.sh "UPDATE interactions 
                SET status = 'pending', 
                    failure_type = 'interrupted',
                    retry_count = retry_count + 1
                WHERE workflow_run_id = <WF_RUN_ID>
                  AND status IN ('running', 'failed')
                  AND (error_message IS NULL OR error_message = '')
                  AND retry_count < max_retries"
```

### Pattern 3: Script Bug

**Symptom:** Same script failing repeatedly with `script_error`

**Diagnosis:**
```bash
./scripts/q.sh "SELECT c.conversation_name, i.error_message, COUNT(*)
                FROM interactions i
                JOIN conversations c USING(conversation_id)
                WHERE i.failure_type = 'script_error'
                GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10"
```

**Action:** Fix the script, then reset:
```bash
./scripts/q.sh "UPDATE interactions 
                SET status = 'pending', 
                    retry_count = 0,
                    failure_type = NULL,
                    error_message = NULL
                WHERE conversation_id = <CONV_ID>
                  AND status = 'failed'"
```

### Pattern 4: LLM Garbage Output

**Symptom:** `invalid_output` failures from LLM not returning valid JSON

**Diagnosis:**
```bash
./scripts/q.sh "SELECT c.conversation_name, COUNT(*) as failures
                FROM interactions i
                JOIN conversations c USING(conversation_id)
                WHERE i.failure_type = 'invalid_output'
                GROUP BY 1 ORDER BY 2 DESC"
```

**Action:** 
1. Check the prompt template for clarity
2. These get one auto-retry (LLM is non-deterministic)
3. If still failing, prompt needs work

## Monitoring at Scale

### Daily Health Check

```bash
# Overall failure rate
./scripts/q.sh "SELECT 
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'failed') / 
          NULLIF(COUNT(*), 0), 2) as failure_rate_pct
FROM interactions 
WHERE updated_at > NOW() - INTERVAL '24 hours'"

# Failure rate by conversation (spot problem prompts)
./scripts/q.sh "SELECT c.conversation_name,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE i.status = 'failed') / 
          NULLIF(COUNT(*), 0), 1) as fail_pct
FROM interactions i
JOIN conversations c USING(conversation_id)
WHERE i.updated_at > NOW() - INTERVAL '24 hours'
GROUP BY 1
HAVING COUNT(*) > 10
ORDER BY 4 DESC"
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Failure rate (24h) | >2% | >5% | Investigate top failures |
| Timeout rate | >5% | >10% | Check model load |
| OOM count | >0 | >3 | Scale resources |
| Stuck interactions | >10 | >50 | Check runner health |

## Implementation Details

### Files Modified

- `core/wave_runner/failure_types.py` - Classification logic
- `core/wave_runner/database.py` - `update_interaction_failed()` stores `failure_type`
- `core/wave_runner/runner.py` - Classifies at catch time

### Future: Retry Workflow (WF3010)

For edge cases that need manual/scheduled retry:

1. Interrupted interactions from killed runners
2. Batch recovery after infrastructure issues
3. Re-processing after bug fixes

This is a **cleanup workflow**, not the primary retry mechanism. Primary retry happens inline.

## Summary

1. **Classify at failure time** - Don't lose context
2. **Retry transient, fail deterministic** - Be smart about what will work
3. **Store classification** - Enable analysis and recovery
4. **Monitor daily** - Catch problems before they snowball
5. **Document recovery patterns** - Make ops repeatable

---

*The database is truth. Query it.*
