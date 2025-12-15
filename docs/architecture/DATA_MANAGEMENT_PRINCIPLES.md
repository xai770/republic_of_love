# Data Management Principles (Our "Damn Book")

**Version:** 1.0  
**Date:** November 27, 2025  
**Status:** Living Document

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Core Principles (From User)

### 1. Single Entry Point for All Activity
**Principle:** There is but one table as an entry point into Turing and that's `interactions`. Humans, AI, scripts - all record their doings in that table.

**Rationale:**
- Single source of truth for "what happened"
- Auditable trail of all system activity
- Enables trace analysis and debugging
- Supports workflow orchestration

**Implementation:**
- Every actor (AI, script, human) MUST create an interaction before executing
- Interaction captures: input, output, status, timing, parent/child relationships
- No "shadow" operations outside interactions table

### 2. Efficiency Through Caching/Reuse
**Principle:** Before we do something, we check if it has already been done inside its freshness period (for postings a day, for AI actors forever) in interactions. If it has been done, we reuse that data.

**Freshness Periods:**
- **AI model outputs:** Forever (deterministic at temp=0)
- **Summaries/extractions:** Forever (input doesn't change)
- **Job postings data:** 24 hours (external data may update)
- **IHL scores:** Forever (analysis on snapshot)
- **Skills taxonomy:** Until taxonomy version changes

**Implementation:**
- Check-if-exists conversations (e.g., "Check if Summary Exists")
- Query pattern: `SELECT output FROM interactions WHERE conversation_id=X AND posting_id=Y AND status='completed' ORDER BY created_at DESC LIMIT 1`
- Reuse if found, execute if not

### 3. Test-Driven Workflow Development
**Principle:** For any workflow step we add or test, we create:
1. **Workflow documentation** (e.g., `3001_complete_job_processing_pipeline.md`)
2. **Trace reports** (e.g., `trace_scenario_2_run_191.md`)
3. **Expected vs actual analysis**
4. **Root cause fixes** (no band-aids)

**Quality Standard:**
- Review expected results vs real results
- Investigate ANY errors (even 1% failure rate)
- Iterate until 100% works as expected
- Fix root causes: schema changes, rewrites, plan changes - whatever it takes
- **Or give up and go home** (no half-measures)

---

## Additional Principles (Arden's Contributions)

### 4. Schema is Source of Truth
**Principle:** The database schema defines reality. Code adapts to schema, not vice versa.

**Rationale:**
- Database outlives code (migrations are permanent)
- Schema constraints prevent bugs (NULL checks, foreign keys)
- Generated docs from schema are always accurate
- Easier to reason about data model

**Implementation:**
- Schema changes via migrations (never manual ALTER)
- Migrations documented with WHY (ADRs)
- Code queries schema at runtime (no hardcoded assumptions)
- Weekly schema documentation regeneration

**Example:**
```python
# WRONG: Assume column exists
result['skill_keywords']

# RIGHT: Query schema, adapt
columns = get_table_columns('postings')
if 'skill_keywords' in columns:
    result['skill_keywords']
```

### 5. Data Completeness is Binary
**Principle:** A record is either COMPLETE (all required fields populated) or INCOMPLETE (discard/reprocess). No partial records in production tables.

**Required Fields by Table:**

**`postings`:**
- MUST have: posting_id, job_title, job_description, external_url
- SHOULD have: extracted_summary, skill_keywords, ihl_score, ihl_category
- MAY have: location_*, posted_date, salary_range

**`interactions`:**
- MUST have: interaction_id, conversation_id, status, created_at
- MUST have IF completed: started_at, completed_at, output
- MUST have IF failed: error_message

**Validation:**
- Check completeness BEFORE promoting staging → production
- Flag incomplete records (invalidated=TRUE)
- Report completeness metrics daily

**Example Check:**
```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE job_title IS NOT NULL 
                      AND job_description IS NOT NULL 
                      AND external_url IS NOT NULL) as complete,
    COUNT(*) FILTER (WHERE external_url IS NULL) as missing_url
FROM postings
WHERE invalidated = FALSE;
-- Alert if missing_url > 0
```

### 6. Fail Fast, Fix Once
**Principle:** Detect failures at the earliest boundary. When found, fix root cause immediately. Never band-aid.

**Boundaries (in order):**
1. **API response validation** (before staging insert)
2. **Staging validation** (before promotion)
3. **Workflow validation** (before processing)
4. **Output validation** (before save)

**Implementation:**
- Defense-in-depth validation (multiple layers)
- Each boundary has explicit validation step
- Failures logged to interactions with error details
- Weekly review of failure patterns → root cause fixes

**Example from Nov 26:**
- Found: NULL job_description processed through 13 interactions (60s wasted)
- Root cause: No validation at ANY boundary
- Fix: Added validation at boundary 1 (job fetcher) AND boundary 3 (validation conversation)
- Result: Invalid postings stopped in 0.3s instead of 60s

### 7. Workflow Steps Are Idempotent
**Principle:** Running the same workflow step twice on the same input produces the same output. No side effects.

**Requirements:**
- Check-if-exists before execution
- Reuse existing output if valid
- If re-run needed, mark old interaction as superseded
- Never delete interactions (audit trail)

**Implementation Pattern:**
```python
# 1. Check if already done
existing = query_interaction(conversation_id, posting_id, status='completed')
if existing and not force_rerun:
    return existing.output

# 2. Execute
output = execute_actor(input_data)

# 3. Save new interaction
save_interaction(conversation_id, posting_id, output)

# 4. If superseding old interaction
if existing and force_rerun:
    mark_superseded(existing.interaction_id)
```

### 8. Metrics Drive Decisions
**Principle:** Measure everything. Decide based on data, not intuition.

**Key Metrics:**

**Performance:**
- Seconds per interaction (by conversation)
- Seconds per posting (end-to-end)
- Throughput (postings/hour)
- Batch efficiency (wave batching speedup)

**Quality:**
- Completion rate (by conversation)
- Error rate (by conversation)
- Data completeness (by table)
- Reuse rate (cache hit ratio)

**Cost:**
- LLM tokens per posting
- Database queries per posting
- Storage growth rate
- Compute time per $

**Daily Reporting:**
```sql
-- Example daily metrics query
SELECT 
    DATE(created_at) as date,
    c.conversation_name,
    COUNT(*) as executions,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds,
    COUNT(*) FILTER (WHERE status='completed') * 100.0 / COUNT(*) as success_rate
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at), c.conversation_name
ORDER BY date DESC, avg_seconds DESC;
```

### 9. Documentation is Executable
**Principle:** Documentation that can't be auto-generated or tested is unreliable. Prefer executable specs.

**Hierarchy:**
1. **Schema** (executable, enforced by DB)
2. **Tests** (executable, enforced by CI)
3. **Trace reports** (generated from actual runs)
4. **Workflow diagrams** (generated from conversation/instruction tables)
5. **ADRs** (explain WHY, never HOW - that's in code)

**Anti-pattern:**
- Manual documentation of table structure (schema describes itself)
- Step-by-step guides that go stale (automate the steps)
- "Current state" docs (generate from DB queries)

**Good pattern:**
```bash
# Generate workflow diagram
python3 tools/_document_workflow.py 3001 > docs/workflows/3001_generated.md

# Generate schema docs
python3 tools/generate_schema_docs.py > docs/schema/CURRENT.md

# Generate trace report
python3 core/wave_runner/trace_reporter.py --run-id 195 > reports/trace_195.md
```

### 10. Version Everything
**Principle:** Every change is versioned. Every version is reproducible.

**What to Version:**

**Schema:** Migrations numbered sequentially
- `001_initial_schema.sql`
- `046_fix_skills_and_ihl_routing.sql`

**Actors:** Code history in `actor_code_history` table
- Auto-tracked when script_sync detects drift
- Can revert to any previous version

**Prompts:** Versioned in `instructions` table
- Every prompt change creates new instruction row
- Can A/B test prompt versions

**Models:** Tracked in `conversations.model_used`
- Can see which model was used for any interaction
- Can benchmark model A vs B on same inputs

**Data:** Snapshots at key milestones
- Daily backups: `by_full_20251127_030001.backup`
- Pre-migration backups: `by_pre_migration_046_*.sql`

**Reproducibility Test:**
Given:
- `workflow_run_id` = 195
- `created_at` = 2025-11-26 17:22:17

Can we reconstruct EXACTLY what happened?
- ✅ Which actors executed (from `interactions.actor_id`)
- ✅ Which prompts used (from `instructions` via `conversation_id`)
- ✅ Which models used (from `conversations.model_used`)
- ✅ What inputs/outputs (from `interactions.input/output`)
- ✅ What schema version (from migration history)

---

## Enforcement Mechanisms

### Automated Checks (Daily Cron)

```bash
# Check 1: Data completeness
./scripts/check_data_completeness.sh

# Check 2: Orphaned records
./scripts/check_referential_integrity.sh

# Check 3: Schema drift
./scripts/check_schema_vs_migrations.sh

# Check 4: Performance regression
./scripts/check_performance_metrics.sh

# Check 5: Workflow health
./scripts/check_workflow_health.sh
```

### Code Review Checklist

Before merging ANY change:
- [ ] Does it add to interactions table? (Principle 1)
- [ ] Does it check for existing results? (Principle 2)
- [ ] Does it have a test scenario? (Principle 3)
- [ ] Is schema updated via migration? (Principle 4)
- [ ] Are required fields validated? (Principle 5)
- [ ] Does it fail fast with clear errors? (Principle 6)
- [ ] Is it idempotent? (Principle 7)
- [ ] Are metrics captured? (Principle 8)
- [ ] Is documentation auto-generated? (Principle 9)
- [ ] Are versions tracked? (Principle 10)

### Weekly Audit

Every Monday morning:
1. Review last week's workflow runs (completion rate)
2. Review data completeness metrics (any gaps?)
3. Review error patterns (any recurring issues?)
4. Review performance trends (any regressions?)
5. Document findings in weekly notes
6. Plan fixes for upcoming week

---

## Application to Current Situation

### Problem: 57 Postings Missing Skills/IHL/URLs

**Principle violations:**
- ❌ **Principle 5 (Completeness):** Partial records in production
- ❌ **Principle 6 (Fail Fast):** URL loss not caught at staging boundary
- ❌ **Principle 8 (Metrics):** Didn't measure completeness before 500-job run

**Fixes applied:**
- ✅ Backfill URLs from staging (restore completeness)
- ✅ Migration 046 (fix routing at root cause)
- ✅ Updated validation queries (measure completeness)
- ✅ Defense-in-depth for future (prevent recurrence)

**Lesson learned:**
Always validate PRODUCT TABLE (postings), not just PIPELINE TABLE (interactions).

---

## Open Questions / Discussion Points

1. **Should we enforce completeness with DB constraints?**
   - e.g., `ALTER TABLE postings ADD CONSTRAINT require_url CHECK (external_url IS NOT NULL OR invalidated = TRUE);`
   - Pro: Impossible to save incomplete records
   - Con: Breaks two-phase commit (insert bare → update fields)

2. **Should we version the postings table?**
   - e.g., `postings_history` table with trigger on UPDATE
   - Pro: Can see how posting evolved (summary v1 → v2 → v3)
   - Con: Storage cost

3. **Should we auto-archive old interactions?**
   - e.g., Move interactions >90 days to `interactions_archive`
   - Pro: Keeps main table fast
   - Con: Loses audit trail accessibility

4. **Should we add data quality scores?**
   - e.g., `postings.quality_score` (0-100) based on completeness/freshness
   - Pro: Can filter/sort by quality
   - Con: Another field to maintain

---

## Next Steps

1. **Finalize this document** (get user approval on principles)
2. **Create enforcement scripts** (automated checks)
3. **Add to code review checklist** (in `.github/PULL_REQUEST_TEMPLATE.md`)
4. **Weekly audit process** (first one: next Monday)
5. **Continuous improvement** (add principles as we learn)

---

**This is a living document.** As we encounter new challenges, we add principles. As principles prove ineffective, we revise them. The goal: Build institutional memory that survives beyond any individual contributor.

**The "Damn Book" is never finished. It evolves with us.**
