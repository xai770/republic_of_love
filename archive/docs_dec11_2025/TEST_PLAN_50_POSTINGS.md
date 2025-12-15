# Test Plan: 50 Postings Batch Processing

**Date:** November 26, 2025  
**Test ID:** BATCH-50-001  
**Author:** Sandy  
**Status:** Ready to Execute

---

## Test Objective

**Primary Goal:**
Validate complete Workflow 3001 pipeline with parallel execution improvements on 50 real job postings from Deutsche Bank Workday API.

**What we're testing:**
1. ✅ Parallel execution fix (Grade A + B simultaneously)
2. ✅ Wave batching with model caching
3. ✅ System stability under load (watchdog protection active)
4. ✅ End-to-end pipeline: Fetch → Summary → Skills → IHL Quality → Grades
5. ✅ Performance metrics for realistic workload

**What we're NOT testing:**
- ❌ Error handling edge cases (separate test)
- ❌ Maximum throughput (500-job test later)
- ❌ Multiple worker processes (single runner for now)

---

## Test Data

### Source
- **API:** Deutsche Bank Workday API
- **Method:** Job Fetcher (conversation 9144)
- **Batch size:** 50 jobs minimum
- **Search criteria:** All available jobs (no filters)

### Data Requirements
Each posting must have:
- ✅ Job title
- ✅ Full job description (from detail page, not summary)
- ✅ Location information
- ✅ External job ID (for tracking)

### Data Flow
```
1. Fetcher (9144) → postings_staging (raw jobs)
2. Check Summary (9184) → Promote to postings table
3. Workflow 3001 → Process 50 postings through complete pipeline
```

---

## Expected Performance

### Based on Measured Data

**Per Posting Metrics (from Run 195):**
- Total interactions: 13 per posting
- Average duration: 22.5s per interaction
- Total time per posting: ~292s (4.9 minutes)

**Parallel Execution Improvement:**
- **Before fix:** Grade A + B sequential = 92.1s
- **After fix:** Grade A + B parallel = 60.3s
- **Savings:** 31.8s per posting

**50 Posting Estimates:**

| Metric | Without Parallel Fix | With Parallel Fix | Improvement |
|--------|---------------------|-------------------|-------------|
| **Time per posting** | 292s (4.9 min) | 260s (4.3 min) | -11% |
| **Total sequential** | 14,600s (4.1 hrs) | 13,000s (3.6 hrs) | -26 minutes |
| **With 5 workers** | 2,920s (49 min) | 2,600s (43 min) | -6 minutes |
| **Total interactions** | 650 interactions | 650 interactions | Same |

**Conservative Estimate (single runner):**
- **Expected duration:** 3.6 - 4.1 hours
- **Acceptable range:** 3.0 - 5.0 hours
- **Red flag if:** >6 hours (indicates stuck interactions)

---

## Test Environment

### System Configuration
- **Hardware:** GPU-enabled system (check `nvidia-smi`)
- **Database:** PostgreSQL (turing database)
- **LLM Service:** Ollama (local models)
- **Models:** qwen2.5:7b, gemma2:latest, llama3.2:latest

### Software State
- ✅ Parallel execution fix deployed (ThreadPoolExecutor in runner.py)
- ✅ Watchdog active (auto-fails interactions >15 minutes)
- ✅ Monitoring script available (`scripts/monitor_system.sh`)
- ✅ Wave batching enabled (model cache active)

### Pre-Test Checklist
```bash
# 1. Check GPU available
nvidia-smi

# 2. Check Ollama running
ps aux | grep ollama

# 3. Check database connected
./scripts/q.sh "SELECT 1;"

# 4. Verify no stuck interactions
./scripts/monitor_system.sh

# 5. Check disk space
df -h

# 6. Verify watchdog in crontab
crontab -l | grep watchdog
```

---

## Test Execution Plan

### Phase 1: Fetch Test Data (10-15 minutes)

**Command:**
```bash
python3 scripts/fetch_all_db_jobs.py
```

**Expected Output:**
- Jobs fetched: 50-100+ (depends on API)
- All jobs stored in `postings_staging`
- Full descriptions extracted (not just summaries)

**Validation:**
```sql
-- Verify fetched jobs
SELECT 
    COUNT(*) as jobs_fetched,
    AVG(LENGTH(raw_data->>'job_description')) as avg_desc_length
FROM postings_staging
WHERE created_at > NOW() - interval '30 minutes';

-- Should return:
--   jobs_fetched: 50+
--   avg_desc_length: 2000+ chars
```

### Phase 2: Promote to Postings (1 minute)

**Command:**
```bash
python3 -c "
from core.database import get_connection
conn = get_connection()
cursor = conn.cursor()

# Promote first 50 staging records to postings
cursor.execute('''
    INSERT INTO postings (
        posting_name,
        job_title,
        location_city,
        location_country,
        job_description,
        source_id,
        external_job_id,
        source,
        external_id,
        raw_data,
        created_by_staging_id,
        posting_status
    )
    SELECT 
        job_title || ' - ' || location as posting_name,
        job_title,
        SPLIT_PART(location, ',', 1) as location_city,
        SPLIT_PART(location, ',', -1) as location_country,
        raw_data->>'job_description' as job_description,
        1 as source_id,  -- Deutsche Bank
        raw_data->>'external_id' as external_job_id,
        'deutsche_bank' as source,
        raw_data->>'external_id' as external_id,
        raw_data,
        staging_id,
        'active' as posting_status
    FROM postings_staging
    WHERE source_website = 'deutsche_bank'
      AND created_at > NOW() - interval '30 minutes'
    ORDER BY staging_id
    LIMIT 50
    RETURNING posting_id;
''')

posting_ids = [row[0] for row in cursor.fetchall()]
conn.commit()
print(f'Created {len(posting_ids)} postings')
print(f'IDs: {posting_ids[:10]}...')
conn.close()
"
```

**Validation:**
```sql
-- Verify postings created
SELECT COUNT(*) FROM postings 
WHERE created_at > NOW() - interval '5 minutes';

-- Should return: 50
```

### Phase 3: Execute Batch Processing (3.6 - 4.1 hours)

**Command:**
```bash
# Get posting IDs from Phase 2
POSTING_IDS=$(./scripts/q.sh "
    SELECT array_agg(posting_id) 
    FROM postings 
    WHERE created_at > NOW() - interval '10 minutes'
    ORDER BY posting_id
    LIMIT 50;
" -t)

# Run batch processor
nohup python3 scripts/batch_process_optimized.py \
    --posting-ids "$POSTING_IDS" \
    --workers 1 \
    > logs/batch_50_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

echo "Batch processing started - PID: $!"
echo "Monitor with: tail -f logs/batch_50_test_*.log"
```

**Alternative (if batch_process_optimized not ready):**
```bash
# Process postings one at a time through workflow
for posting_id in $(./scripts/q.sh "
    SELECT posting_id FROM postings 
    WHERE created_at > NOW() - interval '10 minutes' 
    ORDER BY posting_id LIMIT 50" -t); do
    
    echo "Processing posting $posting_id..."
    python3 -c "
from core.database import get_connection
from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner

conn = get_connection()
result = start_workflow(conn, workflow_id=3001, posting_id=$posting_id)
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner.run(max_iterations=100)
conn.close()
    "
done
```

### Phase 4: Monitoring (during test)

**Monitor every 5 minutes:**
```bash
watch -n 300 './scripts/monitor_system.sh'
```

**What to watch for:**
- ✅ GPU utilization (should be >50% during LLM calls)
- ✅ Ollama models loaded (model caching working)
- ✅ Database connections (shouldn't grow indefinitely)
- ✅ Running interactions (should be 1-3 at a time)
- ⚠️ Stuck interactions (watchdog will clean >15 min)

**Progress check:**
```sql
-- Check completion progress
SELECT 
    COUNT(*) as total_runs,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    ROUND(100.0 * COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*), 1) as pct_complete
FROM workflow_runs
WHERE workflow_id = 3001
  AND started_at > NOW() - interval '6 hours';
```

---

## Success Criteria

### Must Pass (Critical)
1. ✅ **All 50 postings processed** - `status = 'completed'`
2. ✅ **No stuck interactions** - Watchdog cleans any >15 min
3. ✅ **All data populated:**
   - `extracted_summary` IS NOT NULL
   - `skill_keywords` IS NOT NULL  
   - `ihl_score` IS NOT NULL
   - `ihl_category` IS NOT NULL
4. ✅ **Parallel execution working** - Both grades created simultaneously
5. ✅ **No database errors** - Check `workflow_errors` table

### Should Pass (Important)
1. ✅ **Performance within range** - 3.0 to 5.0 hours total
2. ✅ **Average <5 min per posting** - Within acceptable bounds
3. ✅ **Model caching visible** - Same model reused across batches
4. ✅ **<5% failure rate** - Max 2-3 failures acceptable

### Nice to Have (Optional)
1. 🎯 **Performance improvement** - Faster than 4.9 min average (Run 195)
2. 🎯 **Zero watchdog interventions** - No stuck interactions
3. 🎯 **High quality scores** - Good distribution of IHL scores

---

## Data Collection

### Metrics to Capture

**1. Overall Performance:**
```sql
SELECT 
    COUNT(*) as total_runs,
    MIN(started_at) as test_start,
    MAX(completed_at) as test_end,
    EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(started_at))) as total_seconds,
    ROUND(EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(started_at))) / COUNT(*), 1) as avg_seconds_per_posting
FROM workflow_runs
WHERE workflow_id = 3001
  AND started_at > NOW() - interval '6 hours'
  AND status = 'completed';
```

**2. Interaction Performance:**
```sql
SELECT 
    c.conversation_name,
    a.actor_name,
    COUNT(*) as total_interactions,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 1) as avg_seconds,
    MIN(EXTRACT(EPOCH FROM (completed_at - started_at))) as min_seconds,
    MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_seconds
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.created_at > NOW() - interval '6 hours'
  AND i.status = 'completed'
GROUP BY c.conversation_name, a.actor_name
ORDER BY avg_seconds DESC;
```

**3. Parallel Execution Validation:**
```sql
-- Check Grade A and B created simultaneously
SELECT 
    wr.workflow_run_id,
    wr.posting_id,
    ga.interaction_id as grade_a_id,
    gb.interaction_id as grade_b_id,
    ga.created_at as grade_a_created,
    gb.created_at as grade_b_created,
    EXTRACT(EPOCH FROM (gb.created_at - ga.created_at)) as time_diff_ms
FROM workflow_runs wr
JOIN interactions ga ON ga.workflow_run_id = wr.workflow_run_id 
    AND ga.conversation_id = 3336  -- Grade A
JOIN interactions gb ON gb.workflow_run_id = wr.workflow_run_id 
    AND gb.conversation_id = 3337  -- Grade B
WHERE wr.started_at > NOW() - interval '6 hours'
ORDER BY wr.workflow_run_id
LIMIT 10;

-- time_diff_ms should be <100ms if parallel execution working
```

**4. Data Quality:**
```sql
SELECT 
    COUNT(*) as total_postings,
    COUNT(extracted_summary) as with_summary,
    COUNT(skill_keywords) as with_skills,
    COUNT(ihl_score) as with_ihl_score,
    COUNT(ihl_category) as with_category,
    ROUND(AVG(ihl_score), 1) as avg_ihl_score,
    ROUND(100.0 * COUNT(extracted_summary) / COUNT(*), 1) as pct_complete
FROM postings
WHERE created_at > NOW() - interval '6 hours';
```

**5. Watchdog Activity:**
```sql
SELECT 
    COUNT(*) as watchdog_interventions,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_stuck_seconds
FROM interactions
WHERE status = 'failed'
  AND output->>'error' LIKE '%watchdog%'
  AND created_at > NOW() - interval '6 hours';
```

---

## Expected Results

### Performance Targets

| Metric | Target | Acceptable Range | Red Flag |
|--------|--------|------------------|----------|
| **Total duration** | 3.6 hours | 3.0 - 5.0 hours | >6 hours |
| **Avg per posting** | 260s (4.3 min) | 180s - 300s | >360s (6 min) |
| **Completion rate** | 100% | >95% | <90% |
| **Parallel execution** | <100ms gap | <500ms | >1000ms |
| **Watchdog interventions** | 0 | <5 | >10 |

### Data Completeness Targets

| Field | Target | Acceptable | Red Flag |
|-------|--------|------------|----------|
| **Summary** | 100% | >98% | <95% |
| **Skills** | 100% | >98% | <95% |
| **IHL Score** | 100% | >98% | <95% |
| **IHL Category** | 100% | >98% | <95% |

---

## Troubleshooting

### Common Issues

**1. Test stalls/hangs:**
```bash
# Check for stuck interactions
./scripts/monitor_system.sh

# Watchdog will auto-fail after 15 minutes
# If urgent, manual cleanup:
./scripts/q.sh "
UPDATE interactions SET status='failed', completed_at=NOW()
WHERE status='running' AND started_at < NOW() - interval '10 minutes';
"
```

**2. Out of memory:**
```bash
# Check memory
free -h

# Check GPU memory
nvidia-smi

# If needed, restart Ollama
sudo systemctl restart ollama
```

**3. Slow performance (>6 hours):**
- Check GPU utilization (should be high during LLM calls)
- Check model caching working (same model reused)
- Check database connections (shouldn't pile up)
- Consider adding more workers (Phase 2 test)

**4. High failure rate (>10%):**
```sql
-- Investigate failures
SELECT 
    c.conversation_name,
    a.actor_name,
    COUNT(*) as failures,
    output->>'error' as error_message
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE status = 'failed'
  AND created_at > NOW() - interval '6 hours'
GROUP BY c.conversation_name, a.actor_name, output->>'error'
ORDER BY failures DESC;
```

---

## Post-Test Analysis

### Analysis Queries

**1. Performance Summary:**
```bash
# Generate comprehensive report
./scripts/q.sh "
SELECT 
    'PERFORMANCE SUMMARY' as metric,
    NULL as value
UNION ALL
SELECT 'Total postings processed', COUNT(*)::text
FROM workflow_runs WHERE workflow_id=3001 AND started_at > NOW() - interval '6 hours'
UNION ALL
SELECT 'Total duration (hours)', 
    ROUND(EXTRACT(EPOCH FROM (MAX(completed_at) - MIN(started_at)))/3600, 2)::text
FROM workflow_runs WHERE workflow_id=3001 AND started_at > NOW() - interval '6 hours'
UNION ALL
SELECT 'Avg time per posting (minutes)',
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))/60, 1)::text
FROM workflow_runs WHERE workflow_id=3001 AND started_at > NOW() - interval '6 hours';
"
```

**2. Compare to Run 195:**
```sql
-- Performance comparison
WITH test_run AS (
    SELECT 
        AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration,
        COUNT(*) as runs
    FROM workflow_runs
    WHERE workflow_id = 3001
      AND started_at > NOW() - interval '6 hours'
),
baseline AS (
    SELECT 
        291.9 as avg_duration,  -- Run 195
        1 as runs
)
SELECT 
    'Test (50 postings)' as run_type,
    test_run.avg_duration as avg_seconds,
    test_run.avg_duration / 60 as avg_minutes,
    test_run.runs
FROM test_run
UNION ALL
SELECT 
    'Baseline (Run 195)',
    baseline.avg_duration,
    baseline.avg_duration / 60,
    baseline.runs
FROM baseline;
```

**3. Identify Bottlenecks:**
```sql
-- Top 10 slowest interactions
SELECT 
    c.conversation_name,
    a.actor_name,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds,
    ROUND(EXTRACT(EPOCH FROM (completed_at - started_at)) / 60, 1) as duration_minutes
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN actors a ON i.actor_id = a.actor_id
WHERE created_at > NOW() - interval '6 hours'
  AND status = 'completed'
ORDER BY duration_seconds DESC
LIMIT 10;
```

### Decision Matrix

**If test passes all criteria:**
→ Proceed with 500-job batch test
→ Consider adding multiple workers (5 workers = 5x throughput)

**If performance good but some failures:**
→ Investigate failure patterns
→ Fix specific issues
→ Re-test with 50 postings
→ Then proceed to 500

**If performance poor (>6 hours):**
→ Profile to find bottleneck (likely gemma2:latest is slow)
→ Consider alternative models
→ Optimize slowest interactions
→ Re-test before scaling up

**If data quality issues:**
→ Investigate which step failing
→ Check LLM prompt quality
→ Review extraction logic
→ Fix and re-test

---

## Success Declaration

**Test is SUCCESSFUL if:**
1. ✅ 47+ postings completed (>94%)
2. ✅ All completed postings have summary, skills, IHL score
3. ✅ Total duration <5 hours
4. ✅ Parallel execution confirmed (<100ms grade creation gap)
5. ✅ <5 watchdog interventions

**Next step:** Document results and proceed with 500-job test

---

**Test Plan Status:** ✅ Ready to Execute  
**Prerequisites:** All completed  
**Estimated Duration:** 4-6 hours (including fetch and promotion)  
**Risk Level:** LOW (watchdog protection active, single posting tested successfully)
