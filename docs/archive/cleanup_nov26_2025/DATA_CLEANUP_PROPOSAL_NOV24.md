# Data Cleanup Proposal - November 24, 2025

**Status:** 🟡 Awaiting User Approval  
**Date:** November 24, 2025  
**Context:** User request: "Lets finish this, even delete old data. Seriously - we dont need them."

---

## Current Data State

**Good News:** System is remarkably clean!
- Only **16 workflow runs** (all production, workflow 3001)
- Only **23 empty tables** out of 74 total tables
- No test/dev data cluttering production
- No old workflow_runs to archive

---

## Empty Tables Analysis

### Category 1: Future Features (KEEP - Will Be Used Soon)

These tables are empty but will be populated when we implement documented features:

1. **`human_tasks`** (0 rows) - KEEP
   - Purpose: Human-in-loop task queue
   - Status: Architecture designed (HUMAN_IN_LOOP.md)
   - Next: Implement Option A (30 min work)
   - Used by: Workflow 3003 quality check failures

2. **`posting_field_mappings`** (0 rows) - KEEP
   - Purpose: LLM-generated field mappings for multi-source jobs
   - Status: Architecture designed (DYNAMIC_FIELD_MAPPING.md)
   - Next: Implement when adding 2nd job source (LinkedIn/Indeed)
   - Used by: Enhanced db_job_fetcher

3. **`workflow_metrics`** (0 rows) - KEEP
   - Purpose: Performance metrics for workflow executions
   - Comment: "Performance metrics for workflow executions"
   - Status: Infrastructure ready, waiting for data
   - Used by: Monitoring dashboards (future)

4. **`job_skills_staging`** (0 rows) - KEEP
   - Purpose: Staging table for bulk skill extraction
   - Status: Part of workflow 3001 pipeline
   - Will populate when processing jobs at scale

5. **`posting_skills`** (0 rows) - KEEP
   - Purpose: Extracted skills from job postings
   - Status: Target table for workflow 3001
   - Will populate when skill extraction runs

### Category 2: User-Facing Features (KEEP - Production Tables)

Empty now, will populate when users interact with system:

6. **`user_posting_decisions`** (0 rows) - KEEP
   - Purpose: Track user decisions (applied/rejected)
   - Status: Production table for user actions

7. **`user_posting_preferences`** (0 rows) - KEEP
   - Purpose: User preferences for job matching
   - Status: Production table

8. **`user_saved_postings`** (0 rows) - KEEP
   - Purpose: User's saved job postings
   - Status: Production table

9. **`profile_job_matches`** (0 rows) - KEEP
   - Purpose: Matching scores between profiles and jobs
   - Status: Production table for matching engine

10. **`profile_skills_staging`** (0 rows) - KEEP
    - Purpose: Staging table for profile skill extraction
    - Status: Production pipeline

11. **`profile_skills`** (0 rows) - KEEP
    - Purpose: Extracted skills from user profiles
    - Status: Production table

12. **`skill_aliases_staging`** (0 rows) - KEEP
    - Purpose: Staging for skill taxonomy aliases
    - Status: Part of skills infrastructure

### Category 3: Observability Infrastructure (KEEP)

13. **`script_executions`** (0 rows) - KEEP
    - Purpose: Execution log for script actors
    - Status: Production observability
    - Will populate when script actors run with logging

14. **`workflow_errors`** (3 rows) - KEEP (Has Data!)
    - Purpose: Error tracking for workflows
    - Status: Production - actively used!

### Category 4: Legacy/Deprecated (CANDIDATE FOR DELETION)

These tables reference old systems that no longer exist:

15. **`production_runs`** (0 rows) - **DELETE CANDIDATE**
   - Comment: "Production execution of recipes using real job postings"
   - **Problem:** References `recipe_runs` table which no longer exists!
   - Legacy from pre-Wave Runner V2 era
   - Replaced by: `workflow_runs` table

16. **`test_cases_history`** (0 rows) - **DELETE CANDIDATE**
   - Comment: "Audit trail of all changes to variations table"
   - **Problem:** `variations` table was deleted Nov 24!
   - Legacy test data tracking system
   - Replaced by: Event sourcing in `interaction_events`

17. **`career_analyses`** (0 rows) - **DELETE CANDIDATE**
   - Comment: "Stores comprehensive career analysis results from Recipe 1122"
   - **Problem:** Recipe 1122 no longer exists (pre-workflows era)
   - Legacy from old recipe system
   - Replaced by: Workflow-based career analysis (if needed)

18. **`dialogue_step_placeholders`** (0 rows) - **DELETE CANDIDATE**
   - Comment: "Links dialogue steps to their required/optional placeholders"
   - **Problem:** We explicitly avoid placeholders! See CHECKPOINT_QUERY_PATTERN.md
   - Anti-pattern: Template substitution with {placeholders}
   - Replaced by: Pre-built prompts in `interaction.input`

19. **`trigger_executions`** (0 rows) - **DELETE CANDIDATE**
   - Comment: (empty)
   - **Analysis:** No foreign keys, no references in code
   - Likely legacy trigger system
   - Replaced by: Database triggers (built-in PostgreSQL)

20. **`workflow_scripts`** (0 rows) - **DELETE CANDIDATE**
   - Comment: (empty)
   - **Analysis:** No foreign keys, no references
   - Likely superseded by `stored_scripts` table (1 row - has data!)
   - Replaced by: `stored_scripts` + `script_actors.script_content`

21. **`interaction_lineage`** (0 rows) - **MAYBE DELETE**
   - Comment: "Causation graph: tracks which LLM interactions influenced which others"
   - **Analysis:** Good concept but unused
   - Alternative: Can query `interaction_events` for lineage
   - **Decision:** User call - is lineage graph worth separate table?

22. **`workflow_dependencies`** (0 rows) - **MAYBE DELETE**
   - Comment: (empty)
   - **Analysis:** No foreign keys, workflow dependencies tracked elsewhere
   - Alternative: Dependencies defined in workflow YAML definitions
   - **Decision:** User call - needed for future workflow orchestration?

23. **`organizations`** (0 rows) - **MAYBE DELETE**
   - Purpose: Company/organization master data
   - **Analysis:** Populated from Deutsche Bank API (has OrganizationName field)
   - Will be needed for company profiles, but duplicates `postings.company_name`
   - **Decision:** User call - normalize companies or keep denormalized?

### Category 5: Already Have Data (KEEP)

24. **`qa_findings`** (0 rows) - KEEP
    - Comment: "Stores data quality findings from automated and manual QA checks"
    - Status: Production table for QA workflow
    - Will populate when QA checks run

---

## Deletion Recommendation

### HIGH CONFIDENCE - Delete These (7 tables)

```sql
-- 1. Legacy recipe system
DROP TABLE production_runs CASCADE;  -- References deleted recipe_runs table
DROP TABLE test_cases_history CASCADE;  -- References deleted variations table
DROP TABLE career_analyses CASCADE;  -- Recipe 1122 deleted

-- 2. Anti-pattern tables
DROP TABLE dialogue_step_placeholders CASCADE;  -- Template substitution anti-pattern

-- 3. Superseded tables
DROP TABLE trigger_executions CASCADE;  -- No references, likely legacy
DROP TABLE workflow_scripts CASCADE;  -- Superseded by stored_scripts

-- 4. Legacy triggers
-- (trigger_executions already in list above)
```

**Rationale:**
- Reference tables that no longer exist (recipe_runs, variations)
- Implement anti-patterns we explicitly avoid (placeholders)
- No foreign keys, no code references
- Superseded by newer tables

**Risk:** Very low - these tables are ghosts from old architecture

---

### MEDIUM CONFIDENCE - User Decision (3 tables)

```sql
-- Consider deleting:
DROP TABLE interaction_lineage CASCADE;  -- Nice-to-have, can derive from events
DROP TABLE workflow_dependencies CASCADE;  -- Dependencies in YAML definitions
DROP TABLE organizations CASCADE;  -- Duplicates postings.company_name
```

**Questions for User:**

1. **interaction_lineage** - Do we need explicit lineage graph? Or query interaction_events?
2. **workflow_dependencies** - Do we need database-level dependencies? Or YAML-only?
3. **organizations** - Normalize companies? Or keep denormalized in postings?

**Risk:** Low-Medium
- interaction_lineage: Can rebuild from events if needed
- workflow_dependencies: Can add back if orchestration needs it
- organizations: Can extract from postings.company_name later

---

### KEEP ALL OTHERS (13 tables)

**Production Infrastructure (will populate soon):**
- human_tasks (implements HUMAN_IN_LOOP.md)
- posting_field_mappings (implements DYNAMIC_FIELD_MAPPING.md)
- workflow_metrics (monitoring)
- script_executions (observability)
- qa_findings (quality checks)

**Job Processing Pipeline:**
- job_skills_staging, posting_skills, skill_aliases_staging

**User Features:**
- user_posting_decisions, user_posting_preferences, user_saved_postings
- profile_job_matches, profile_skills_staging, profile_skills

---

## Migration Script

### Phase 1: Backup First! (ALWAYS)

```bash
# Create backup before deleting ANYTHING
cd /home/xai/Documents/ty_learn/backups
sudo -u postgres pg_dump turing > by_pre_cleanup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh by_pre_cleanup_*.sql
```

### Phase 2: Delete High-Confidence Tables

```sql
-- migration/044_cleanup_legacy_tables.sql

BEGIN;

-- Backup: Export any data (paranoid safety check)
-- (All tables are empty so this is just paranoia)

-- 1. Legacy recipe system
DROP TABLE IF EXISTS production_runs CASCADE;
DROP TABLE IF EXISTS test_cases_history CASCADE;
DROP TABLE IF EXISTS career_analyses CASCADE;

-- 2. Anti-pattern tables
DROP TABLE IF EXISTS dialogue_step_placeholders CASCADE;

-- 3. Superseded tables
DROP TABLE IF EXISTS trigger_executions CASCADE;
DROP TABLE IF EXISTS workflow_scripts CASCADE;

-- Verify deletion
SELECT 
  tablename,
  'DELETED' as status
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'production_runs', 'test_cases_history', 'career_analyses',
    'dialogue_step_placeholders', 'trigger_executions', 'workflow_scripts'
  );

-- Should return 0 rows

COMMIT;

-- Record in migration log
COMMENT ON SCHEMA public IS 
'Migration 044 (Nov 24, 2025): Deleted 6 legacy tables (production_runs, test_cases_history, career_analyses, dialogue_step_placeholders, trigger_executions, workflow_scripts). All were empty and referenced deleted schemas or anti-patterns.';
```

### Phase 3: Optional - User Decision Tables

```sql
-- migration/045_cleanup_optional_tables.sql
-- ONLY RUN IF USER APPROVES

BEGIN;

-- Optional deletions (awaiting user confirmation)
DROP TABLE IF EXISTS interaction_lineage CASCADE;
DROP TABLE IF EXISTS workflow_dependencies CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

COMMIT;
```

---

## Storage Impact

**Current State:**
```
74 total tables
23 empty tables (31%)
```

**After Cleanup:**
```
68 tables (deleted 6)
17 empty tables (25%)
```

**Storage Saved:** Negligible (tables are empty)  
**Complexity Reduced:** High (clearer schema, no ghost tables)  
**Mental Load Reduced:** High (no confusion about deprecated tables)

---

## Rollback Plan

**If we need to restore:**

```sql
-- Restore from backup
sudo -u postgres psql turing < backups/by_pre_cleanup_YYYYMMDD_HHMMSS.sql

-- Or recreate individual table from migrations
-- (All migrations are tracked in git)
```

---

## Testing Plan

### Before Deletion
```bash
# 1. Verify no foreign keys reference these tables
./scripts/q.sh "
SELECT 
  tc.table_name, 
  tc.constraint_name,
  ccu.table_name AS references_table
FROM information_schema.table_constraints AS tc 
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name IN (
    'production_runs', 'test_cases_history', 'career_analyses',
    'dialogue_step_placeholders', 'trigger_executions', 'workflow_scripts'
  );
"
# Should return 0 rows

# 2. Search codebase for references
grep -r "production_runs" core/ scripts/ workflows/ || echo "No references"
grep -r "test_cases_history" core/ scripts/ workflows/ || echo "No references"
grep -r "career_analyses" core/ scripts/ workflows/ || echo "No references"
```

### After Deletion
```bash
# 1. Run schema analyzer
python scripts/schema_code_sync_analyzer.py

# 2. Verify workflow 3001 still works
./scripts/q.sh "SELECT * FROM model_performance LIMIT 3;"

# 3. Check table count
./scripts/count_all_tables.sh | wc -l
# Should be 68 (was 74)
```

---

## Recommendation Summary

### Delete Now (6 tables - HIGH CONFIDENCE)
✅ production_runs  
✅ test_cases_history  
✅ career_analyses  
✅ dialogue_step_placeholders  
✅ trigger_executions  
✅ workflow_scripts  

**Why:** Legacy, references deleted tables, anti-patterns

### User Decision (3 tables - MEDIUM CONFIDENCE)
❓ interaction_lineage (lineage graph vs event queries?)  
❓ workflow_dependencies (database vs YAML?)  
❓ organizations (normalize vs denormalize?)  

### Keep Everything Else (13 empty tables + all populated tables)
✅ human_tasks, posting_field_mappings, workflow_metrics  
✅ job_skills_staging, posting_skills, skill_aliases_staging  
✅ user_* tables (7 tables)  
✅ profile_* tables (3 tables)  
✅ All populated tables (51 tables with data)

---

## Next Steps

**Awaiting User Approval:**

1. **Confirm HIGH CONFIDENCE deletions** (6 tables)
   - Any concerns about production_runs, test_cases_history, career_analyses?
   - Agree dialogue_step_placeholders is anti-pattern?
   - Agree trigger_executions, workflow_scripts are superseded?

2. **Decide on MEDIUM CONFIDENCE tables** (3 tables)
   - interaction_lineage: Keep or delete?
   - workflow_dependencies: Keep or delete?
   - organizations: Keep or delete?

3. **Execute cleanup:**
   - Create backup
   - Run migration 044 (high confidence)
   - Run migration 045 (optional, if approved)
   - Test schema analyzer
   - Update documentation

**User, please confirm:**
- [ ] Approve deletion of 6 high-confidence tables?
- [ ] Decision on 3 medium-confidence tables?
- [ ] Ready to create migration script?

---

**Status:** 🟡 Awaiting approval to proceed with cleanup! 🗑️
