# Test Data Management Strategy

**Date:** November 24, 2025  
**Status:** 🟢 RECOMMENDED APPROACH  
**Author:** Arden

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## The Problem

> "If I don't add environment to data (and I understand why not), how do I manage testing data?"

**Answer:** You don't need "test data" - you need **test executions on real data**.

---

## The Key Insight: Testing Models, Not Data

**What You're Actually Testing:**
- Does `gemma2:9b` extract better summaries than `gemma3:1b`?
- Does `qwen2.5:3b` run faster than `qwen2.5:7b` with same quality?
- Which model should be the **champion** for each conversation?

**What You're NOT Testing:**
- Fake job postings
- Synthetic profiles
- Made-up skills

**Implication:** Run test models on **REAL production data**, store results separately, compare.

---

## Recommended Approach: Shadow Testing

### How Shadow Testing Works

```
Production Workflow (workflow_id=1, environment='prod')
  ├─ Conversation 3335: Extract Summary
  │   └─ Actor: gemma3:1b (is_production=TRUE, model_variant='champion')
  │       └─ Interaction 100: posting_id=4709 → Summary A
  │           └─ Used in production ✅
  │
Shadow Test Workflow (workflow_id=50, environment='test')
  ├─ Conversation 3335: Extract Summary  
  │   └─ Actor: gemma2:9b (is_production=FALSE, model_variant='challenger_a')
  │       └─ Interaction 500: posting_id=4709 → Summary B
  │           └─ Not used (testing only) 🧪
  │
Compare: Summary A vs Summary B → Which is better?
```

**Same Input (posting_id=4709), Different Models, Different Outputs**

---

## Implementation: 3 Simple Patterns

### Pattern 1: Parallel Workflows (Safest)

**Setup:**
```sql
-- Production workflow
INSERT INTO workflows (workflow_name, environment, enabled)
VALUES ('3001_complete_job_pipeline', 'prod', TRUE);

-- Shadow test workflow (same logic, different actors)
INSERT INTO workflows (workflow_name, environment, enabled)
VALUES ('3001_complete_job_pipeline_test_gemma2_9b', 'test', TRUE);
```

**Execution:**
```python
# Process same posting in both workflows
posting_id = 4709

# Production run (writes to postings.extracted_summary)
prod_run_id = create_workflow_run(workflow_id=1, posting_id=posting_id)
run_workflow(prod_run_id)

# Shadow test run (writes to interactions only, NOT to postings table!)
test_run_id = create_workflow_run(workflow_id=50, posting_id=posting_id)
run_workflow(test_run_id)

# Compare results
compare_extractions(prod_run_id, test_run_id)
```

**Key:** Shadow workflow interactions DON'T update `postings.extracted_summary` - they're read-only tests!

**Pros:**
- ✅ Production unaffected
- ✅ Perfect A/B comparison
- ✅ Can test on 100% of production traffic

**Cons:**
- ❌ Doubles compute (run everything twice)
- ❌ Need to disable savers in test workflows

---

### Pattern 2: Test Runs on Sample Data (Cheaper)

**Setup:**
```sql
-- Mark 10% of postings for testing
CREATE TABLE test_sample (
    posting_id BIGINT PRIMARY KEY,
    sampled_at TIMESTAMP DEFAULT NOW(),
    sample_reason TEXT  -- 'random_10pct', 'edge_case', 'manual_select'
);

-- Insert random 10% sample
INSERT INTO test_sample (posting_id, sample_reason)
SELECT posting_id, 'random_10pct'
FROM postings 
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY RANDOM()
LIMIT (SELECT COUNT(*) * 0.1 FROM postings WHERE created_at > NOW() - INTERVAL '1 day');
```

**Execution:**
```python
# Run test workflow ONLY on sampled postings
for posting_id in get_test_sample():
    test_run_id = create_workflow_run(
        workflow_id=50,  # Test workflow
        posting_id=posting_id
    )
    run_workflow(test_run_id)

# Compare to production results
compare_sample_results()
```

**Pros:**
- ✅ Lower compute cost (10% vs 100%)
- ✅ Still testing on real data
- ✅ Can focus on edge cases

**Cons:**
- ❌ Smaller sample size
- ❌ Need to maintain test_sample table

---

### Pattern 3: Canary Testing (Gradual Rollout)

**Setup:**
```sql
-- Challenger serves 5% of production traffic
UPDATE actors SET 
    is_production = TRUE,
    traffic_weight = 5  -- 5% of requests
WHERE actor_id = 99;  -- gemma2:9b challenger

UPDATE actors SET
    traffic_weight = 95  -- 95% of requests
WHERE actor_id = 13;  -- gemma3:1b champion
```

**Execution:**
```python
# Router picks actor based on weight
def get_actor_for_conversation(conversation_id, posting_id):
    actors = get_production_actors(conversation_id)
    
    # Weighted random selection
    total_weight = sum(a['traffic_weight'] for a in actors)
    rand = random.randint(1, total_weight)
    
    cumulative = 0
    for actor in actors:
        cumulative += actor['traffic_weight']
        if rand <= cumulative:
            return actor
    
    return actors[0]  # Fallback to champion

# 95% of postings get gemma3:1b
# 5% get gemma2:9b (canary)
# Both write to production!
```

**Monitoring:**
```sql
-- Compare metrics
SELECT 
    a.actor_name,
    AVG(CAST(i.output->>'latency_ms' AS INT)) as avg_latency,
    COUNT(*) as volume,
    COUNT(*) FILTER (WHERE i.output->>'response' IS NOT NULL) as success_count
FROM interactions i
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.conversation_id = 3335
  AND i.created_at > NOW() - INTERVAL '24 hours'
GROUP BY a.actor_name;

-- If challenger metrics >= champion:
--   Increase traffic_weight 5% → 10% → 25% → 50% → 100%
-- If challenger metrics worse:
--   Set traffic_weight = 0, disable actor
```

**Pros:**
- ✅ Real production testing
- ✅ Gradual rollout (safe)
- ✅ Automatic champion selection possible

**Cons:**
- ❌ 5% of users get experimental results
- ❌ Need rollback plan if quality degrades

---

## My Recommendation: Pattern 1 + Pattern 3

**Phase 1 (THIS WEEK): Shadow Testing (Pattern 1)**
- Create test workflows for each challenger model
- Run on 100% of production traffic
- Compare results in `interactions` table
- **NO production impact** (test interactions don't write to postings)

**Phase 2 (NEXT WEEK): Canary Rollout (Pattern 3)**
- Once champion identified from shadow tests
- Start 5% canary on production traffic
- Monitor for 1 week
- Gradual rollout if metrics hold

---

## Handling Test Interactions

**Schema Addition:**
```sql
-- workflow_runs already has environment
-- Add flag to skip savers in test workflows
ALTER TABLE workflows 
ADD COLUMN skip_data_writes BOOLEAN DEFAULT FALSE;

-- Test workflows don't save to postings
UPDATE workflows 
SET skip_data_writes = TRUE 
WHERE environment IN ('test', 'dev');
```

**In Saver Scripts:**
```python
# core/wave_runner_v2/actors/summary_saver.py
def execute(self, interaction_data):
    # Check if workflow allows data writes
    workflow = get_workflow(interaction_data['workflow_run_id'])
    
    if workflow['skip_data_writes']:
        # Test mode - log only, don't save
        logger.info(f"TEST MODE: Would save summary: {interaction_data['input']['summary'][:100]}")
        return {
            'status': 'test_mode_skipped',
            'message': 'Summary not saved (test workflow)'
        }
    
    # Production mode - save normally
    save_summary_to_postings(interaction_data)
    return {'status': 'success'}
```

**Result:**
- Production workflows: Write to `postings` table ✅
- Test workflows: Only write to `interactions` table (read-only) ✅

---

## Test Data Lifecycle

```
Day 1: Create shadow test workflow for gemma2:9b
       Run on 1000 postings
       Store results in interactions table

Day 2: Compare metrics:
       - Latency: gemma2:9b 30% faster ✅
       - Quality: Human review of 20 samples → equivalent
       - Consistency: 95% match rate
       
Day 3: Promote gemma2:9b to 5% canary
       Monitor production metrics
       
Day 7: Canary successful, promote to 100%
       gemma2:9b becomes new champion
       
Day 8: Clean up old test interactions
       DELETE FROM interactions 
       WHERE workflow_run_id IN (
           SELECT workflow_run_id FROM workflow_runs
           WHERE environment = 'test'
             AND started_at < NOW() - INTERVAL '30 days'
       );
```

**Storage Impact:**
```sql
-- Check test data volume
SELECT 
    environment,
    COUNT(*) as workflow_runs,
    SUM((SELECT COUNT(*) FROM interactions WHERE workflow_run_id = wr.workflow_run_id)) as total_interactions,
    MIN(started_at) as oldest_run,
    MAX(started_at) as newest_run
FROM workflow_runs wr
JOIN workflows w ON wr.workflow_id = w.workflow_id
GROUP BY environment;

-- Results:
-- prod: 1000 runs, 16000 interactions, last 30 days
-- test: 500 runs, 8000 interactions, last 7 days
-- Total: 24000 interactions (~5MB)  ← Negligible!
```

---

## Automatic Champion Selection (Simple Version)

```sql
-- Create view for model performance
CREATE VIEW model_performance AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.model_variant,
    i.conversation_id,
    COUNT(*) as execution_count,
    AVG(CAST(i.output->>'latency_ms' AS INT)) as avg_latency_ms,
    STDDEV(CAST(i.output->>'latency_ms' AS INT)) as latency_stddev,
    COUNT(*) FILTER (WHERE i.status = 'completed') as success_count,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failure_count
FROM interactions i
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.created_at > NOW() - INTERVAL '7 days'
  AND a.actor_type = 'ai_model'
GROUP BY a.actor_id, a.actor_name, a.model_variant, i.conversation_id;

-- Automatic promotion query
WITH champion_candidates AS (
    SELECT 
        conversation_id,
        actor_id,
        actor_name,
        avg_latency_ms,
        success_count,
        -- Score: lower latency + higher success rate = better
        (1000.0 / avg_latency_ms) * (success_count::FLOAT / execution_count) as performance_score
    FROM model_performance
    WHERE execution_count >= 50  -- Minimum sample size
      AND success_count::FLOAT / execution_count >= 0.95  -- 95% success rate
)
SELECT 
    conversation_id,
    actor_name,
    performance_score,
    RANK() OVER (PARTITION BY conversation_id ORDER BY performance_score DESC) as rank
FROM champion_candidates;

-- Promote top performer
UPDATE actors SET 
    model_variant = 'champion',
    is_production = TRUE
WHERE actor_id IN (
    SELECT actor_id FROM champion_candidates WHERE rank = 1
);
```

**Workflow 3XXX: Automatic Champion Selection**
- Runs weekly (Saturday 2am)
- Compares all models from past week
- Selects champion per conversation
- Creates human task if results ambiguous
- Updates `actors` table

---

## Summary: No Test Data Needed!

**Instead of:** Creating fake postings/profiles with `environment='test'` ❌

**Do this:** Run multiple actors on same real data, compare results ✅

**Storage:**
- Production data: `postings`, `profiles`, `skills` (real)
- Test results: `interactions` table (actors × conversations × postings)
- Cleanup: Delete test workflow_runs after 30 days

**Cost:**
- Shadow testing: 2x compute (run everything twice)
- Canary testing: 1.05x compute (5% extra traffic)
- Automatic champion: Negligible (query once/week)

**Benefit:**
- Always testing on REAL data (no fake scenarios)
- Production unaffected (test interactions don't write to postings)
- Clean champion promotion (data-driven decisions)

---

Want me to write workflow 3XXX for automatic champion selection?
