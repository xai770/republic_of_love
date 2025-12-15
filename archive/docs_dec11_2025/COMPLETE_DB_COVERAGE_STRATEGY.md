# Complete Coverage Strategy: All DB Jobs Through Workflow 3001

**Date:** November 27, 2025  
**Goal:** Process ALL Deutsche Bank jobs with 100% data completeness  
**Status:** Planning Phase

---

## Current State Assessment

### What We Have
- **50 test postings** processed (incomplete: missing skills/IHL/URLs)
- **Workflow 3001** validated (13 interactions, 16 conversations total)
- **Performance measured:** 148s per posting (2.5 min avg)
- **Bugs identified:** 3 critical (URLs, skills routing, IHL routing)
- **Fixes ready:** Migration 046 + URL backfill

### What's in the Database

```sql
-- Check current DB jobs inventory
SELECT 
    COUNT(*) as total_in_staging,
    COUNT(*) FILTER (WHERE promoted_to_posting_id IS NOT NULL) as already_promoted,
    COUNT(*) FILTER (WHERE promoted_to_posting_id IS NULL) as available_to_process
FROM postings_staging
WHERE source_website = 'deutsche_bank';
```

**Expected:** 500-2000 jobs in staging (based on your 500-job test plan)

### What We Need

**Complete postings table with:**
- ✅ job_title
- ✅ job_description  
- ✅ external_url (link to apply)
- ✅ extracted_summary (our value-add)
- ✅ skill_keywords (our value-add)
- ✅ ihl_score + ihl_category (our value-add)
- ✅ location_city, location_country
- ✅ posted_date, salary_range (if available)

---

## Strategy: Crawl → Walk → Run

### Phase 1: CRAWL (Fix Foundation) ⏱️ 1 hour

**Goal:** Fix all known bugs, validate with small batch

**Steps:**
1. ✅ Backfill URLs for existing 57 postings
2. ✅ Run Migration 046 (fix skills + IHL routing)
3. ✅ Fix workflow status update (already done in runner.py)
4. ✅ Test with 5 fresh postings
5. ✅ Verify 100% data completeness

**Success Criteria:**
- 5/5 postings complete with ALL fields
- 5/5 workflows marked 'completed'
- 0 errors in logs
- Average time: <180s per posting

**Output:** Validated, bug-free pipeline ready for scale

---

### Phase 2: WALK (Medium Batch) ⏱️ 5-6 hours

**Goal:** Process 500 jobs with monitoring and optimization

**Steps:**

#### 2.1: Pre-flight Checks (15 min)
```bash
# Database backup
./scripts/backup_database.sh

# Check staging inventory
./scripts/q.sh "
SELECT 
    COUNT(*) as available,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM postings_staging 
WHERE promoted_to_posting_id IS NULL
  AND source_website = 'deutsche_bank';
"

# Verify watchdog active
crontab -l | grep watchdog

# Clear disk space (logs, old backups)
df -h
```

#### 2.2: Execute Batch (4-5 hours)
```bash
# Dry run first
python3 scripts/batch_process_500_jobs.py --max-jobs 500 --dry-run

# Execute with monitoring
python3 scripts/batch_process_500_jobs.py --max-jobs 500 --workers 5 \
  | tee logs/batch_500_$(date +%Y%m%d_%H%M%S).log
```

#### 2.3: Monitor Progress (every hour)
```sql
-- Completeness check
SELECT 
    COUNT(*) as processed,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as with_skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as with_ihl,
    COUNT(*) FILTER (WHERE external_url IS NOT NULL) as with_url
FROM postings
WHERE created_at >= CURRENT_DATE;

-- Error check
SELECT 
    c.conversation_name,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failures,
    i.output->'data'->>'error' as error_message
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.created_at >= CURRENT_DATE
  AND i.status = 'failed'
GROUP BY c.conversation_name, error_message
ORDER BY failures DESC;
```

#### 2.4: Post-batch Validation (30 min)
```bash
# Generate comprehensive report
python3 tools/generate_batch_report.py --run-date $(date +%Y-%m-%d) \
  > reports/BATCH_500_RESULTS_$(date +%Y%m%d).md

# Verify data completeness
./scripts/q.sh "
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE 
        job_title IS NOT NULL AND
        job_description IS NOT NULL AND
        external_url IS NOT NULL AND
        extracted_summary IS NOT NULL AND
        skill_keywords IS NOT NULL AND
        ihl_score IS NOT NULL
    ) * 100.0 / COUNT(*) as completeness_percent
FROM postings
WHERE created_at >= CURRENT_DATE;
"
# Target: >95% completeness
```

**Success Criteria:**
- 500/500 postings processed
- >475 (95%) complete workflows
- >95% data completeness
- <5 hours total runtime
- <10 manual interventions

**Output:** 500 production-quality job postings ready for matching

---

### Phase 3: RUN (Full Database) ⏱️ 12-24 hours

**Goal:** Process ALL remaining DB jobs in staging

**Steps:**

#### 3.1: Inventory Check
```sql
-- How many jobs left?
SELECT 
    COUNT(*) as total_remaining,
    COUNT(*) FILTER (WHERE validation_status = 'valid') as valid_to_process,
    COUNT(*) FILTER (WHERE validation_status IS NULL) as needs_validation
FROM postings_staging
WHERE promoted_to_posting_id IS NULL
  AND source_website = 'deutsche_bank';
```

**Scenarios:**

**A) <1000 jobs remaining:**
- Run single batch: `--max-jobs 1000 --workers 5`
- Expected time: ~8 hours
- Monitor hourly

**B) 1000-2000 jobs remaining:**
- Run two batches: 1000 + remainder
- Expected time: 16 hours (overnight + morning)
- Schedule overnight, check morning

**C) >2000 jobs remaining:**
- Run in 1000-job chunks
- Expected time: 24+ hours (multi-day)
- Consider increasing workers to 8-10

#### 3.2: Optimization (Optional)
If Phase 2 showed bottlenecks:

**Format Standardization slow?**
```sql
UPDATE conversations
SET model_used = 'qwen2.5:7b',  -- Faster model
    temperature = 0.0
WHERE conversation_name = 'Format Standardization';
```

**Extract slow?**
```sql
UPDATE conversations
SET model_used = 'gemma3:1b',  -- Lighter model
    temperature = 0.0
WHERE conversation_name = 'session_a_gemma3_extract';
```

**Database contention?**
- Increase connection pool
- Add read replicas
- Batch insertions

#### 3.3: Execute Full Run
```bash
# For <1000 jobs
python3 scripts/batch_process_500_jobs.py --max-jobs 1000 --workers 5

# For >1000 jobs (overnight)
nohup python3 scripts/batch_process_500_jobs.py --max-jobs 2000 --workers 8 \
  > logs/batch_full_$(date +%Y%m%d).log 2>&1 &

# Monitor with
tail -f logs/batch_full_*.log | grep -E "Processing|ERROR|✅"
```

#### 3.4: Final Validation
```sql
-- Complete inventory
SELECT 
    'postings_staging' as table_name,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE promoted_to_posting_id IS NOT NULL) as promoted
FROM postings_staging
WHERE source_website = 'deutsche_bank'
UNION ALL
SELECT 
    'postings' as table_name,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE source = 'deutsche_bank') as deutsche_bank_jobs
FROM postings;

-- Data quality audit
SELECT 
    'Complete records' as metric,
    COUNT(*) as count,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM postings WHERE source = 'deutsche_bank') as percent
FROM postings
WHERE source = 'deutsche_bank'
  AND job_title IS NOT NULL
  AND job_description IS NOT NULL
  AND external_url IS NOT NULL
  AND extracted_summary IS NOT NULL
  AND skill_keywords IS NOT NULL
  AND ihl_score IS NOT NULL
UNION ALL
SELECT 
    'Missing URLs' as metric,
    COUNT(*) as count,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM postings WHERE source = 'deutsche_bank') as percent
FROM postings
WHERE source = 'deutsche_bank'
  AND external_url IS NULL
-- ... repeat for each critical field
ORDER BY percent DESC;
```

**Success Criteria:**
- 100% of staging jobs processed (or invalidated with reason)
- >95% data completeness across all postings
- Complete trace reports for debugging
- Performance metrics documented

**Output:** Complete Deutsche Bank job catalog ready for production use

---

## Risk Management

### Known Risks

**1. Rate Limiting (API)**
- **Risk:** DB might throttle if we fetch too fast
- **Mitigation:** Already rate-limited in job fetcher (158 jobs cap)
- **Monitoring:** Watch for HTTP 429 errors in logs

**2. Model Availability (Ollama)**
- **Risk:** Local models might crash during long runs
- **Mitigation:** Watchdog detects stuck interactions, auto-fails after 15min
- **Monitoring:** Check `ollama ps` periodically

**3. Database Connection Pool Exhaustion**
- **Risk:** 5+ workers competing for connections
- **Mitigation:** Connection pooling in wave_runner
- **Monitoring:** Check `SELECT count(*) FROM pg_stat_activity`

**4. Disk Space**
- **Risk:** Large batch generates huge logs
- **Mitigation:** Rotate logs, compress old ones
- **Monitoring:** `df -h` before/during batch

**5. Workflow Divergence**
- **Risk:** Schema/routing changes mid-batch
- **Mitigation:** Lock migrations during batch runs
- **Monitoring:** Git status before batch

### Rollback Plan

**If Phase 2 fails catastrophically:**

```sql
-- Option A: Mark all today's postings invalid
UPDATE postings
SET invalidated = TRUE,
    invalidated_reason = 'batch_500_failed_validation',
    invalidated_at = NOW()
WHERE created_at >= CURRENT_DATE;

-- Option B: Delete today's postings (nuclear option)
DELETE FROM postings
WHERE created_at >= CURRENT_DATE;

-- Option C: Revert migration 046
-- (SQL in migration file has DOWN section)
```

**Then:**
1. Fix root cause
2. Test with 5 postings again
3. Retry batch when confident

---

## Continuous Processing Strategy (Post-Initial Load)

### Daily Updates

Once initial load complete, process NEW jobs daily:

```bash
# Cron job (every morning at 6am)
0 6 * * * cd /home/xai/Documents/ty_learn && \
  python3 scripts/batch_process_500_jobs.py --max-jobs 100 --workers 3 \
  >> logs/daily_update.log 2>&1
```

**Workflow:**
1. Job fetcher checks DB website (runs every hour via cron)
2. New jobs → postings_staging
3. Daily batch processes new jobs
4. Updated jobs invalidate old postings, create new ones

### Monitoring Dashboard

**Daily metrics to track:**
- New jobs fetched (per day)
- Jobs processed (per day)
- Completion rate (% successful)
- Average processing time (trend over time)
- Data completeness (% with all fields)
- Error rate by conversation (identify degradation)

**Implementation:**
```bash
# Generate daily report
python3 tools/generate_daily_metrics.py --date $(date +%Y-%m-%d) \
  > reports/daily/metrics_$(date +%Y%m%d).md

# Email summary (optional)
cat reports/daily/metrics_$(date +%Y%m%d).md | mail -s "Daily Workflow Report" user@example.com
```

---

## Quality Assurance Checklist

### Before ANY batch run:

- [ ] Database backup current (<24 hours old)
- [ ] Migration 046 applied successfully
- [ ] URL backfill completed (all postings have external_url)
- [ ] 5-posting validation passed 100%
- [ ] Watchdog active in crontab
- [ ] Sufficient disk space (>10GB free)
- [ ] Ollama models running (`ollama list`)
- [ ] No pending schema changes
- [ ] Monitoring scripts ready

### During batch run:

- [ ] Monitor logs every hour
- [ ] Check error rate (<5%)
- [ ] Check data completeness (sample 10 postings every 100)
- [ ] Verify workflow status updates working
- [ ] Watch disk space
- [ ] Watch database connections

### After batch run:

- [ ] Generate comprehensive report
- [ ] Validate data completeness (>95%)
- [ ] Review error patterns
- [ ] Document lessons learned
- [ ] Update this strategy doc with findings
- [ ] Backup final database state

---

## Success Metrics

### Phase 1 (Crawl) - MUST ACHIEVE:
- ✅ 5/5 postings 100% complete
- ✅ 0 errors
- ✅ <180s per posting

### Phase 2 (Walk) - TARGETS:
- 🎯 500/500 postings processed
- 🎯 >95% data completeness
- 🎯 <5 hours total time
- 🎯 <2% error rate

### Phase 3 (Run) - TARGETS:
- 🎯 100% of available jobs processed
- 🎯 >95% data completeness
- 🎯 <10% error rate (some jobs may be genuinely bad)
- 🎯 Complete audit trail (every job traced)

---

## Next Actions

**Immediate (Sandy):**
1. Execute Phase 0 (URL backfill)
2. Execute Phase 1 (Migration 046 + 5-posting test)
3. Report results

**Short-term (This week):**
1. Execute Phase 2 (500-job batch)
2. Analyze results
3. Optimize bottlenecks

**Medium-term (Next week):**
1. Execute Phase 3 (full database)
2. Set up daily processing
3. Build monitoring dashboard

**Long-term (This month):**
1. Expand to other job sources (LinkedIn, Indeed, etc.)
2. Build candidate matching pipeline
3. Production deployment

---

## Open Questions

1. **How many DB jobs are actually in staging?**
   - Need to run inventory query
   - Determines Phase 3 timeline

2. **Should we process incrementally or all-at-once?**
   - Incremental: Safer, easier to debug
   - All-at-once: Faster, more efficient
   - Recommendation: Depends on total count

3. **What's our target for "done"?**
   - Option A: All jobs with valid job_description processed
   - Option B: All jobs in staging (even invalid ones)
   - Recommendation: Option A (quality over quantity)

4. **Should we parallelize across multiple machines?**
   - Current: 1 machine, 5 workers
   - Alternative: 3 machines, 5 workers each = 15 parallel
   - Recommendation: Only if >5000 jobs remaining

---

**Bottom Line:** We have a working pipeline. Now we scale it. Crawl (5 jobs) → Walk (500 jobs) → Run (all jobs). Each phase validates the next. No shortcuts.

**Timeline estimate:**
- Phase 1: 1 hour
- Phase 2: 5 hours  
- Phase 3: 8-24 hours (depending on job count)
- **Total: 14-30 hours to complete coverage**

**Let's execute!** 🚀
