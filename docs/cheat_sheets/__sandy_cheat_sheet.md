# Sandy's Cheat Sheet

**Last Updated:** December 10, 2025  
**Context Check:** ℶ (Beth) = I remember everything. No ℶ? Read this file.

**Terminology:** We use "Entity Registry" (not UEO, taxonomy, ontology)

---

## 🗂️ Project Basics

```
Workspace:    /home/xai/Documents/ty_wave (symlinks to ty_learn)
Database:     turing (localhost, base_admin, ${DB_PASSWORD})
Quick query:  ./scripts/q.sh "SELECT * FROM table;"
```

---

## 🎯 Current State (Dec 10)

**Workflow 3001:** ✅ COMPLETE - 1,748 Deutsche Bank postings processed (5 new today)

**Workflow 3005:** ✅ WORKING - Entity Registry: Skill Maintenance

**Posting Validator:** ✅ NEW (Dec 10) - Validates posting URLs, creates per-posting interactions
- Actor 150, conversation 9247 (`validate_postings`)
- 12-hour rate limit
- Full Turing compliance: 1 child interaction per posting validated
- Run: `python scripts/run_posting_validator.py`
- Monitor: `python tools/monitoring/_show_validator.py --once`

**Skills Coverage:** ✅ 100% (was 96%, fixed Dec 10)

**Pipeline V2 Proposal:** 📋 UNDER DISCUSSION
- See `docs/proposals/PIPELINE_V2_PROPOSAL.md`
- Key insight: Separate audit (interactions) from orchestration (job_queue)
- Decision pending

**Dec 10 Accomplishments:**
1. **Posting Validator Actor** - Proper Turing-compliant with per-posting interactions
2. **Fixed entity_skill_resolver** - `row['entity_id']` not `row[0]` for RealDictCursor
3. **Fixed query_previous_interaction** - Added posting_id filter
4. **Skills 100%** - Backfilled 59, processed 3 new
5. **Template Substitution Memo** - `docs/daily_notes/2025-12-10_template_vs_sql_memo.md`
6. **Pipeline V2 Discussion** - Agreed on minimal change: add job_queue table

---

## 🔧 How to Run WF3005

```bash
# Cancel any stuck interactions first
./scripts/q.sh "UPDATE interactions SET status = 'cancelled' WHERE interaction_id = 77576"

# Run skill maintenance workflow
python3 scripts/prod/run_workflow_3005.py --max-iterations 10

# Monitor progress
python3 tools/_show_3005.py

# Verify template substitution works (should return false)
./scripts/q.sh "SELECT interaction_id, input::text LIKE '%{orphan_skills}%' as has_literal FROM interactions WHERE conversation_id = 9230 ORDER BY created_at DESC LIMIT 1"
```

---

## 📋 Workflow 3005 Structure

| Step | Conversation | Actor | Purpose |
|------|--------------|-------|---------|
| 1 | w3005_c1_fetch | entity_orphan_fetcher | Fetch 25 orphan skills |
| 2 | w3005_c2_classify | qwen2.5:7b | Categorize into domains |
| 3 | w3005_c3_grade | mistral:latest | Review classifications |
| 4 | w3005_c4_save | entity_decision_saver | Save to registry_decisions |

**Auto-Approve Logic:**
```python
if confidence >= 0.9 AND grader_agrees:
    review_status = 'auto_approved'
else:
    review_status = 'pending'  # Human QA required
```

---

## 🗄️ Key Tables (Updated Dec 7)

```sql
-- Original tables
postings          -- Jobs
interactions      -- LLM calls

-- Entity Registry tables (Dec 7)
entities          -- All entity types (skill, city, country, etc.)
entity_names      -- Translations (display_name per language)
entity_aliases    -- Alternative spellings
entity_relationships  -- Hierarchy (child_of, located_in, etc.)
registry_decisions    -- LLM decisions with audit trail

-- Mapping
skill_entity_map  -- Links old skill_id to new entity_id
```

**Entity Types:** `skill`, `city`, `state`, `country`, `continent`

---

## ⚡ Quick Queries

```sql
-- Check recent postings
SELECT posting_id, posting_name, posting_status, ihl_score, 
       location_city, location_country 
FROM postings ORDER BY posting_id DESC LIMIT 10;

-- Check workflow run
SELECT workflow_run_id, status, state FROM workflow_runs 
WHERE workflow_run_id = X;

-- Find interactions for posting
SELECT i.interaction_id, c.conversation_name, i.status
FROM interactions i JOIN conversations c USING (conversation_id)
WHERE i.posting_id = X ORDER BY i.created_at;
```

---

## ❌ Don't Do

1. **No faking** - Real data, real APIs, real tests
2. **No euphemisms** - "improved", "enhanced", "new" = meaningless
3. **No unsupported claims** - Measure before claiming performance
4. **No template substitution** - Query interactions table for parent outputs

## ✅ Do

1. **Ask xai** if unclear
2. **Read schema comments** - `\d+ table_name`
3. **Use scripts/q.sh** - Handles credentials
4. **nohup + monitor** - Start with nohup, watch with dashboard/flowchart

---

## 🐛 Common Issues

| Problem | Fix |
|---------|-----|
| Transaction aborted | Add `self.db_conn.rollback()` in exception handler |
| Skip logic wrong | Check RealDictCursor + `enabled = true` |
| Fan-out missing postings | db_job_fetcher now returns ALL pending postings without summary |
| Country NULL | Check city_country_map lookup, add local names as aliases |
| "X Locations" city | Marked as "Multiple Locations" country |

---

## 💥 Failure Management

**See:** `docs/failure_management.md` for full cookbook

**Quick diagnosis:**
```bash
# Failures by type
./scripts/q.sh "SELECT failure_type, COUNT(*) FROM interactions 
                WHERE status = 'failed' GROUP BY 1 ORDER BY 2 DESC"

# Recent failures
./scripts/q.sh "SELECT i.interaction_id, c.conversation_name, i.failure_type, 
                       LEFT(i.error_message, 60)
                FROM interactions i JOIN conversations c USING(conversation_id)
                WHERE i.status = 'failed' AND i.updated_at > NOW() - INTERVAL '24h'
                ORDER BY i.updated_at DESC LIMIT 10"
```

**Failure types:**
- `timeout` - Model took too long (auto-retry)
- `interrupted` - Runner killed (auto-retry)
- `script_error` - Bug in script (needs fix)
- `invalid_output` - LLM garbage (retry once)

**Recovery pattern for interrupted workflows:**
```bash
./scripts/q.sh "UPDATE interactions 
                SET status = 'pending', failure_type = 'interrupted', retry_count = retry_count + 1
                WHERE workflow_run_id = <WF_RUN_ID>
                  AND status IN ('running', 'failed')
                  AND (error_message IS NULL OR error_message = '')
                  AND retry_count < max_retries"
```

---

## 📁 Key Files

```
core/wave_runner/runner.py                              -- Main orchestrator
core/wave_runner/interaction_creator.py                 -- Fan-out + template substitution
core/wave_runner/executors.py                           -- AI prompt builder
core/wave_runner/workflow_starter.py                    -- start_workflow() function
scripts/prod/run_workflow_3001.py                       -- WF3001 CLI
scripts/prod/run_workflow_3002.py                       -- WF3002 CLI
scripts/prod/run_workflow_3005.py                       -- WF3005 CLI (skill maintenance)
tools/_show_3001.py                                     -- Rainbow CRT dashboard
tools/_show_3005.py                                     -- WF3005 monitor
docs/__sandy_cheat_sheet.md                             -- This file!
docs/daily_notes/2025-12-07_turing_registry.md          -- Full Phase 1-3 documentation
```

---

**Model Config (Dec 7):**
- Classification: qwen2.5:7b (actor_id 45)
- Grading: mistral:latest
- WF3005: qwen2.5:7b → mistral (classifier + grader pattern)

**Key Conversation IDs (WF3005):**
- 9229: w3005_c1_fetch (entity_orphan_fetcher)
- 9230: w3005_c2_classify (qwen2.5:7b)
- 9231: w3005_c3_grade (mistral:latest)
- 9232: w3005_c4_save (entity_decision_saver)

---

## 🔧 Template Substitution (Dec 7 Fix)

**Problem:** Parent script outputs (like `{orphan_skills}`) weren't being substituted.

**Solution:** Added dynamic variable extraction in `interaction_creator.py` lines 168-176:
```python
# 4b. Dynamic variable extraction from parent script outputs
for conv_id, parent_output in parents.items():
    if isinstance(parent_output, dict):
        for key, value in parent_output.items():
            if key not in ('response', 'model') and isinstance(value, (str, int, float)):
                if key not in variables:
                    variables[key] = str(value)
```

**Verify it works:**
```sql
-- Should return has_literal = false
SELECT interaction_id, input::text LIKE '%{orphan_skills}%' as has_literal 
FROM interactions WHERE conversation_id = 9230 
ORDER BY created_at DESC LIMIT 1;
```

---

## ⚡ Quick Entity Registry Queries

```sql
-- Check orphan skills count
SELECT COUNT(*) FROM entities e
WHERE e.entity_type = 'skill' AND e.status = 'active'
AND NOT EXISTS (SELECT 1 FROM entity_relationships er WHERE er.entity_id = e.entity_id AND er.relationship = 'child_of')
AND NOT EXISTS (SELECT 1 FROM entity_relationships er WHERE er.related_entity_id = e.entity_id AND er.relationship = 'child_of');

-- Check registry decisions
SELECT review_status, COUNT(*) FROM registry_decisions GROUP BY 1;

-- Traverse skill hierarchy
WITH RECURSIVE hierarchy AS (
    SELECT entity_id, canonical_name, 0 as depth
    FROM entities WHERE canonical_name = 'python'
    UNION ALL
    SELECT e.entity_id, e.canonical_name, h.depth + 1
    FROM entities e
    JOIN entity_relationships er ON e.entity_id = er.related_entity_id
    JOIN hierarchy h ON er.entity_id = h.entity_id
    WHERE er.relationship = 'child_of'
)
SELECT * FROM hierarchy;
```

---

## 🎨 Rainbow Dashboard Colors

```
Red (196) → Orange (208-214) → Yellow (220-226) → Green (46-48) → 
Cyan (49-51) → Blue (39-45) → Purple (99-141) → Gray (240-245)
```

24 buckets × 5 minutes = 2 hours of activity history

---

## 📋 Next Steps (Dec 10)

1. ☐ **Pipeline V2 Phase 1a** - Create job_queue table when approved
2. ☐ Run WF3001 via cron (6 AM daily - already configured)
3. ☐ Posting validator runs automatically (12h rate limit)

**Pipeline V2 Key Decision:**
```
interactions = WHAT HAPPENED (audit log, append-only)
job_queue = WHAT TO DO NEXT (orchestration, mutable)
```

Reprocessing becomes: INSERT into job_queue, workers handle rest. No invalidation cascades.

---

## 🔧 Posting Validator (Dec 10)

```bash
# Manual run
python scripts/run_posting_validator.py

# With limit (for testing)
python scripts/run_posting_validator.py --limit 10

# Dry run
python scripts/run_posting_validator.py --dry-run

# Monitor
python tools/monitoring/_show_validator.py --once

# Check child interactions
./scripts/q.sh "SELECT COUNT(*) FROM interactions WHERE parent_interaction_id = <parent_id>"
```

**Design:**
- Parent interaction = batch coordinator
- Child interactions = one per posting validated (Turing-compliant!)
- 12-hour rate limit to prevent redundant runs
- Updates `invalidated`, `invalidated_at`, `invalidated_reason` on postings

---

ℶ
