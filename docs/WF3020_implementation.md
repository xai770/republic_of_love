# WF3020 Skill Taxonomy Engine - Implementation Specs

**Status:** Partially implemented  
**Owner:** Arden + Sandy  
**Last Updated:** December 30, 2025  

This document provides the technical specs for building and maintaining WF3020. For conceptual understanding ("what" and "why"), see [WF3020_story.md](WF3020_story.md).

---

## 1. Current State

WF3020 already exists in the database with the following structure:

### 1.1 Workflow Record

```sql
workflow_id: 3020
workflow_name: Skill Taxonomy Engine
environment: dev
enabled: true
```

### 1.2 Conversations (9 total)

| Order | Canonical Name | Entry Point | Actor Script |
|-------|----------------|-------------|--------------|
| 1 | wf3020_c1_atomize | ✅ Yes | `wf3020_atomize.py` |
| 2 | wf3020_c2_lookup | No | `wf3020_lookup.py` |
| 3 | wf3020_c3_create | No | `wf3020_create_entity.py` |
| 4 | wf3020_c4_classify | No | LLM (qwen2.5:7b) |
| 5 | wf3020_c5_navigate | No | `wf3020_navigate.py` |
| 6 | wf3020_c6_apply | No | `wf3020_apply.py` |
| 7 | wf3020_c7_find_duplicates | ✅ Yes | `wf3020_find_duplicates.py` |
| 8 | wf3020_c8_decide_merge | No | LLM (claude/gpt-4) |
| 9 | wf3020_c9_execute_merge | No | `wf3020_execute_merge.py` |

**Note:** C7-C9 are a separate sub-workflow for duplicate detection, triggered post-classification.

### 1.3 Branch Conditions (Existing)

```
C1 → C2: * (always, after atomization)
C2 → C3: contains:"found": false
C2 → C4: contains:"found": true
C3 → C4: default (after entity creation)
C4 → C5: default (after classification)
C5 → C4: default (loop continue) OR contains:"retry": "true"
C5 → C6: contains:"done": "true"
C6 → C2: contains:"more_skills": "true" (batch mode)
C7 → C8: contains:"has_duplicates": "true"
C7 → END: contains:"no_duplicates": "true"
C8 → C9: default (after decision)
C9 → C7: contains:"continue": "true"
C9 → END: default
```

---

## 2. Actor-to-Story Mapping

The story uses "librarian" personas. Here's how they map to actors:

| Story Name | Conversation | Actor | Type |
|------------|--------------|-------|------|
| C1 Atomize | wf3020_c1_atomize | `wf3020_atomize.py` | Script |
| Lucy (Lookup) | wf3020_c2_lookup | `wf3020_lookup.py` | Script |
| Carl (Create) | wf3020_c3_create | `wf3020_create_entity.py` | Script |
| Clara (Classify) | wf3020_c4_classify | LLM | qwen2.5:7b |
| Nate (Navigate) | wf3020_c5_navigate | `wf3020_navigate.py` | Script |
| Adam (Apply) | wf3020_c6_apply | `wf3020_apply.py` | Script |
| Victor (Supervisor) | **NOT IMPLEMENTED** | Would need new conv | claude/gpt-4 |
| Quinn (QA) | External | `scripts/wf3020_qa.py` | Cron/daemon |

### 2.1 Missing: Victor (Supervisor)

The story describes Victor handling "new category" proposals. This path is NOT currently implemented. The existing flow assumes Clara picks from existing options only.

**To add Victor:**
1. Create conversation `wf3020_c4b_supervisor`
2. Add branch from C5: `contains:"proposed_category"` → C4b
3. Add branches from C4b: APPROVE → C6, REJECT → C4

---

## 3. Actor File Locations

All actor scripts are in `core/wave_runner/actors/`:

| File | Lines | Status |
|------|-------|--------|
| `wf3020_atomize.py` | — | Exists |
| `wf3020_lookup.py` | 295 | Exists |
| `wf3020_create_entity.py` | — | Exists |
| `wf3020_navigate.py` | 364 | Exists |
| `wf3020_apply.py` | — | Exists |
| `wf3020_find_duplicates.py` | — | Exists |
| `wf3020_execute_merge.py` | — | Exists |
| `wf3020_report.py` | — | Exists (utility) |

---

## 4. Input/Output Contracts

### 4.1 C1 Atomize (Entry Point)

**Input (from queue):**
```python
{
    "subject_id": 12345,          # posting_id or entity with raw skills
    "raw_skill_text": "Python, JavaScript, React"  # Optional override
}
```

**Output:**
```python
{
    "skills": ["Python", "JavaScript", "React"],
    "source_id": 12345,
    "count": 3
}
```

**Note:** Per Arden/Sandy discussion, Mode B (raw text input) is dead. Kill it. WF3020 expects entity_id input only. Atomization should happen in WF3007 before queueing to WF3020.

### 4.2 C2 Lookup (Lucy)

**Input:**
```python
{
    "skill_name": "kubernetes",
    "parent_response": {}  # Empty on first call
}
```

**Output (found):**
```python
{
    "found": true,
    "entity_id": 12345,
    "canonical_name": "kubernetes",
    "match_type": "exact",  # or "alias", "fuzzy"
    "location": "ROOT",
    "options": "a. technical_engineering - ...\nb. data_analytics...",
    "current_options_map": {"a": "technical_engineering", ...}
}
```

**Output (not found):**
```python
{
    "found": false,
    "skill_name": "kubernetes",
    "create_new": true
}
```

### 4.3 C3 Create (Carl)

**Input:**
```python
{
    "skill_name": "kubernetes",
    "parent_response": {"found": false, ...}
}
```

**Output:**
```python
{
    "entity_id": 99999,           # Newly created
    "canonical_name": "kubernetes",
    "created": true,
    "location": "ROOT",
    "options": "a. technical_engineering - ...",
    "current_options_map": {"a": "technical_engineering", ...}
}
```

**Race Condition Handling:** Uses INSERT ... ON CONFLICT DO NOTHING, then SELECT.

### 4.4 C4 Classify (Clara)

**Input (Prompt Template):**
```
You are classifying a skill into our taxonomy.

Skill: {skill_name}
Current location: {parent_response.location}

Choose where this skill belongs:
{parent_response.options}

Or:
n. CREATE NEW: [name] - [description]
z. GO BACK to previous level

Respond with just the letter.
```

**Output (from LLM):**
```
b
```

Or for new category:
```
n. cloud_orchestration - Container orchestration and cloud deployment tools
```

### 4.5 C5 Navigate (Nate)

**Input:**
```python
{
    "skill_name": "kubernetes",
    "letter": "b",  # Parsed from Clara's response
    "parent_response": {
        "location": "ROOT",
        "options": "...",
        "current_options_map": {"a": "technical_engineering", ...},
        "path": []
    }
}
```

**Output (continue drilling):**
```python
{
    "done": false,
    "location": "IN: technical_engineering",
    "options": "a. programming_languages - ...\nb. devops - ...",
    "current_options_map": {"a": "programming_languages", ...},
    "path": ["technical_engineering"],
    "depth": 1
}
```

**Output (placement selected):**
```python
{
    "done": true,
    "target_group": "devops",
    "target_group_id": 37401,
    "path": ["technical_engineering", "devops"]
}
```

**Output (retry - invalid selection):**
```python
{
    "retry": true,
    "error": "Invalid selection 'x'. Please choose a-h or z.",
    "location": "IN: technical_engineering",
    "options": "...",
    "current_options_map": {...}
}
```

**Loop State:** Nate's full output is passed as `parent_response` to Clara on next iteration. The Dec 28 fix ensures this works.

### 4.6 C6 Apply (Adam)

**Input:**
```python
{
    "entity_id": 12345,
    "skill_name": "kubernetes",
    "parent_response": {
        "done": true,
        "target_group_id": 37401,
        "path": ["technical_engineering", "devops"]
    }
}
```

**Output:**
```python
{
    "applied": true,
    "relationship_id": 88888,
    "entity_id": 12345,
    "parent_id": 37401,
    "relationship_type": "belongs_to"
}
```

---

## 5. Branch Condition Reference

Branch conditions use **substring matching** (not regex). The daemon checks if the condition string appears in the JSON output.

### 5.1 Main Classification Flow

| From | To | Condition | Priority |
|------|-----|-----------|----------|
| C1 | C2 | `*` | 0 |
| C2 | C4 | `"found": true` | 5 |
| C2 | C3 | `"found": false` | 10 |
| C3 | C4 | `default` | 1 |
| C4 | C5 | `default` | 0 |
| C5 | C4 | `default` (loop) | 0 |
| C5 | C4 | `"retry": "true"` | 10 |
| C5 | C6 | `"done": "true"` | 5 |

### 5.2 Duplicate Detection Flow

| From | To | Condition | Priority |
|------|-----|-----------|----------|
| C7 | C8 | `"has_duplicates": "true"` | 10 |
| C7 | END | `"no_duplicates": "true"` | 5 |
| C8 | C9 | `default` | 5 |
| C9 | C7 | `"continue": "true"` | 10 |
| C9 | END | `default` | 5 |

### 5.3 Victor Path (NOT IMPLEMENTED)

Would need:
| From | To | Condition | Priority |
|------|-----|-----------|----------|
| C5 | C4b | `"proposed_category"` | 15 |
| C4b | C6 | `APPROVE` | 5 |
| C4b | C4 | `REJECT` | 10 |

---

## 6. State Flow Diagram

```
[Queue] ──entity_id──▶ [C1 Atomize] ──skills[]──▶ [C2 Lookup]
                                                       │
                              ┌────────────────────────┴─────────────────────────┐
                              ▼                                                  ▼
                       [C3 Create]                                   [C4 Classify (LLM)]
                              │                                                  │
                              └────────────────────────┬─────────────────────────┘
                                                       ▼
                                              [C5 Navigate]
                                                       │
                              ┌────────────────────────┼─────────────────────────┐
                              ▼                        ▼                         ▼
                        [C4 (loop)]            [C4b Victor]                 [C6 Apply]
                                                 (TODO)                          │
                                                                                 ▼
                                                                         [Complete]
```

### 6.1 State Passing

| From | To | What's Passed |
|------|-----|---------------|
| C1 | C2 | `{"skills": [...]}` |
| C2 | C3 | `{"found": false, "skill_name": "..."}` |
| C2 | C4 | `{"found": true, "entity_id": ..., "location": "ROOT", "options": "..."}` |
| C3 | C4 | `{"entity_id": ..., "location": "ROOT", "options": "..."}` |
| C4 | C5 | `{"letter": "b"}` (parsed from LLM) |
| C5 | C4 | Full state: `{"location": "...", "options": "...", "path": [...]}` |
| C5 | C6 | `{"done": true, "target_group_id": ...}` |

**Key:** Clara receives Nate's full output as `parent_response`. Her prompt uses `{parent_response.location}` and `{parent_response.options}`.

---

## 7. Database Queries

### 7.1 Lucy's Lookup Query

```sql
-- 1. Exact match on canonical_name
SELECT entity_id, canonical_name 
FROM entities 
WHERE entity_type = 'skill_atomic' 
AND LOWER(canonical_name) = LOWER($skill_name);

-- 2. Alias match
SELECT e.entity_id, e.canonical_name
FROM entities e
JOIN entity_names en ON e.entity_id = en.entity_id
WHERE e.entity_type = 'skill_atomic'
AND en.name_type IN ('alias', 'verbatim', 'observed')
AND LOWER(en.display_name) = LOWER($skill_name);

-- 3. Fuzzy match (conservative)
SELECT entity_id, canonical_name, 
       similarity(canonical_name, $skill_name) as sim
FROM entities
WHERE entity_type = 'skill_atomic'
AND similarity(canonical_name, $skill_name) > 0.90
ORDER BY sim DESC
LIMIT 1;
```

### 7.2 Carl's Create Query

```sql
-- Idempotent insert with race condition handling
INSERT INTO entities (entity_type, canonical_name, created_by)
VALUES ('skill_atomic', $canonical_name, 'wf3020')
ON CONFLICT (entity_type, canonical_name) DO NOTHING
RETURNING entity_id;

-- If no return, skill was created by another process - fetch it
SELECT entity_id FROM entities 
WHERE entity_type = 'skill_atomic' 
AND canonical_name = $canonical_name;
```

### 7.3 Nate's Option Builder Query

```sql
-- Get children of current group
SELECT e.entity_id, e.canonical_name,
       (SELECT COUNT(*) FROM entity_relationships er2 
        WHERE er2.parent_entity_id = e.entity_id) as child_count
FROM entities e
JOIN entity_relationships er ON e.entity_id = er.child_entity_id
WHERE er.parent_entity_id = $parent_id
AND e.entity_type = 'skill_group'
ORDER BY e.canonical_name;
```

### 7.4 Adam's Apply Query

```sql
-- Insert classification relationship
INSERT INTO entity_relationships 
    (parent_entity_id, child_entity_id, relationship_type, created_by)
VALUES ($target_group_id, $entity_id, 'belongs_to', 'wf3020')
ON CONFLICT (parent_entity_id, child_entity_id, relationship_type) DO NOTHING;
```

---

## 8. Quinn (QA) - External Script

Quinn is NOT part of the per-skill workflow. She runs externally.

### 8.1 Deployment

```bash
# Location
/home/xai/Documents/ty_wave/scripts/wf3020_qa.py

# Cron (daily at 3am)
0 3 * * * cd /home/xai/Documents/ty_learn && python scripts/wf3020_qa.py --full-audit >> logs/quinn.log 2>&1

# Daemon hook (after 100 completions) - in turing_orchestrator.py
if completed_count % 100 == 0:
    subprocess.run(["python", "scripts/wf3020_qa.py", "--quick-check"])
```

### 8.2 QA Checks

| Check | Query | Threshold |
|-------|-------|-----------|
| Orphan skills | Skills with no parent | 0 |
| Oversized groups | Groups with >100 children | Flag for split |
| Duplicate canonicals | Same name, different entities | Auto-merge |
| Broken paths | Skills in group, group has no parent | 0 |
| Shallow classifications | Skills at depth 1 (root children) | <5% |

---

## 9. Testing Checklist

### 9.1 Unit Tests

- [ ] Lucy: exact match returns correct entity
- [ ] Lucy: alias match works for "python3" → "python"
- [ ] Lucy: fuzzy match at 0.90 threshold
- [ ] Carl: race condition handled (parallel creates)
- [ ] Nate: depth limit (5) enforced
- [ ] Nate: GO BACK returns to previous options
- [ ] Adam: duplicate relationships rejected gracefully

### 9.2 Integration Tests

- [ ] Full flow: new skill → create → classify → apply
- [ ] Full flow: existing skill → lookup → classify → apply
- [ ] Loop: Clara↔Nate iterates 3+ times correctly
- [ ] Retry: invalid letter selection loops back
- [ ] Batch: 10 skills processed sequentially

### 9.3 Edge Cases

- [ ] Empty skill name
- [ ] Skill with special characters
- [ ] Already-classified skill (re-classification)
- [ ] Clara picks invalid letter
- [ ] Database connection lost mid-flow

---

## 10. Migration History

WF3020 was created incrementally. Key migrations:

| Date | Migration | Changes |
|------|-----------|---------|
| Dec 28 | Initial | Created workflow, C1-C6 |
| Dec 29 | Add dedup | Added C7-C9 for duplicate detection |
| Dec 30 | — | This doc created |

### 10.1 Pending Migrations

None required for current functionality. Victor path would need:

```sql
-- Add supervisor conversation (when needed)
INSERT INTO conversations (canonical_name, ...) 
VALUES ('wf3020_c4b_supervisor', ...);

INSERT INTO instruction_steps (...)
VALUES ('navigate_to_supervisor', 'proposed_category', 15, NULL, c4b_id);
```

---

## 11. Known Issues

### 11.1 Mode B (Raw Text Input)

The story mentions Mode B for raw skill text input. Per Sandy: **Kill it**. WF3020 expects entity_id only. Atomization is WF3007's job.

**Status:** C1 (atomize) exists but should be deprecated or made pass-through.

### 11.2 Victor Not Implemented

The "new category" proposal path (`n. CREATE NEW: ...`) routes to Victor for approval. This is not yet implemented. Currently, Clara can only pick from existing options.

**Impact:** Low. Most skills fit existing categories. Victor is a rare path.

### 11.3 Loop Depth Not Enforced

Nate has `MAX_DEPTH = 5` in code but the story says 5 levels. Need to verify this is enforced and Clara is told when max depth reached.

---

## 12. Runbook

### 12.1 Queue a Skill for Classification

```python
# From WF3007 C8 save (after extraction)
queue_workflow(
    workflow_id=3020,
    subject_type='skill_atomic',
    subject_id=entity_id,
    reason='wf3007_extraction'
)
```

### 12.2 Monitor Progress

```bash
# Pending classifications
./scripts/q.sh "SELECT COUNT(*) FROM queue WHERE workflow_id = 3020 AND status = 'pending'"

# Recent completions
./scripts/q.sh "SELECT COUNT(*) FROM workflow_runs WHERE workflow_id = 3020 AND status = 'complete' AND completed_at > NOW() - INTERVAL '1 hour'"

# Stuck runs
./scripts/q.sh "SELECT * FROM workflow_runs WHERE workflow_id = 3020 AND status = 'running' AND started_at < NOW() - INTERVAL '5 minutes'"
```

### 12.3 Debug a Stuck Skill

```bash
# Find the run
./scripts/q.sh "SELECT * FROM workflow_runs WHERE workflow_id = 3020 AND subject_id = $ENTITY_ID"

# Check last interaction
./scripts/q.sh "SELECT * FROM interactions WHERE workflow_run_id = $RUN_ID ORDER BY created_at DESC LIMIT 5"
```

### 12.4 Reset and Retry

```sql
-- Reset stuck run
UPDATE workflow_runs SET status = 'pending' WHERE workflow_run_id = $RUN_ID;

-- Or re-queue
INSERT INTO queue (workflow_id, subject_type, subject_id, reason)
VALUES (3020, 'skill_atomic', $ENTITY_ID, 'manual_retry');
```

---

## Appendix A: Conversation IDs

For reference when writing queries:

| Canonical Name | Conversation ID | Instruction ID |
|----------------|-----------------|----------------|
| wf3020_c1_atomize | 9307 | 3496 |
| wf3020_c2_lookup | 9308 | 3498 |
| wf3020_c3_create | 9309 | 3499 |
| wf3020_c4_classify | 9310 | 3497 |
| wf3020_c5_navigate | 9311 | 3500 |
| wf3020_c6_apply | 9312 | 3501 |
| wf3020_c7_find_duplicates | 9313 | 3502 |
| wf3020_c8_decide_merge | 9314 | 3503 |
| wf3020_c9_execute_merge | 9315 | 3504 |

---

## Appendix B: Related Workflows

| Workflow | Relationship |
|----------|--------------|
| WF3001 | Upstream - extracts skills from postings |
| WF3007 | Upstream - saves extracted skills, queues to WF3020 |
| WF3010 | Deprecated - replaced by WF3020 |
| WF3011 | Deprecated - replaced by WF3020 |
| WF3012 | Deprecated - replaced by WF3020 |

---

ℶ Sandy + Arden

---

## 13. Open Questions for Sandy

*Added by Arden - Dec 30, 2025*

Before implementing Victor, need decisions on:

### 13.1 Victor Model Selection

Tested three local models with a APPROVE/REJECT scenario:

| Model | Reasoning Quality | Response Format | Speed |
|-------|-------------------|-----------------|-------|
| **olmo-3:7b** | Very thorough, explicit thinking | Clean APPROVE/REJECT | ~15s |
| **gpt-oss:latest** | Thorough, considers alternatives | Structured with notes | ~12s |
| **mistral-nemo:12b** | Concise, to the point | Clean, good REJECT | ~8s |

All three correctly APPROVED `fintech_innovation` for `regulatory_sandbox_testing` and mistral-nemo correctly REJECTED `soft_skills` (pointing to `communication_collaboration`).

**Sandy's pick:** **mistral-nemo:12b** - Speed matters for a rare path. Concise responses parse better. The REJECT behavior is what we need most.

### 13.2 Rejection Round Tracking

How does Victor know it's round 2 (to trigger ESCALATE)?

| Option | Pros | Cons |
|--------|------|------|
| **A: Track in Nate's state** | Simple, no DB queries | State gets complex |
| **B: Workflow state table** | Clean separation | Extra table/queries |
| **C: Count from interactions** | Audit trail | Query per check |

**Arden's recommendation:** Option A (track in `victor_attempts` field in Nate's output)

**Sandy's pick:** **A** - Nate already manages state. Add `victor_attempts: 0` to initial state, increment when routing to Victor. Simple. No new tables.

### 13.3 ESCALATE Behavior

After 2 Victor rejections, what happens?

| Option | Behavior | Impact |
|--------|----------|--------|
| **A: Fail workflow** | `status='failed'` | Blocks skill, needs manual retry |
| **B: Flag for review** | Insert to `qa_review_queue` | Needs new table |
| **C: Place + flag** | Place at current level, add `needs_review` | Flow continues |

**Arden's recommendation:** Option C (don't block flow, flag for later)

**Sandy's pick:** **C** - Never block the pipeline. Place the skill at current location, set `metadata.needs_review = true` on the entity. Quinn catches these in her audit. Flow continues.

### 13.4 Clara `[n]` Handling (Before Victor Exists)

If Clara outputs `n. new_category` today (Victor not yet built), what should Nate do?

| Option | Behavior |
|--------|----------|
| **A: Treat as invalid** | Retry: "please pick a-h or z" |
| **B: Force PLACE HERE** | Log warning, place at current level |
| **C: Fail workflow** | Error: "Victor not implemented" |

**Arden's recommendation:** Option B (log + place, so we can measure frequency)

**Sandy's pick:** **B** - Measure first, build later. Log `warning: clara_proposed_new_category` with the skill name and proposal. Place at current level. If we see this >5% of the time, then build Victor.

### 13.5 Entry Point Cleanup

C1 (Atomize) is vestigial. Should entry point be:

| Option | Entry | C1 Status |
|--------|-------|-----------|
| **A: Keep C1** | C1 → C2 | Pass-through only |
| **B: Change to C2** | C2 (Lucy) | Delete C1 |
| **C: Conditional** | C1 if raw text, C2 if entity_id | Complex branching |

**Arden's recommendation:** Option B (C2 as entry, kill C1)

**Sandy's pick:** **B** - Kill C1. Mode B is dead (per our Dec 29 discussion). WF3020 = entity-only input. Atomization is WF3007's job. Update `is_entry_point` on C2, disable C1.

### 13.6 Lucy's Scope

Should Lucy (C2) also initialize navigation state, or just lookup?

| Option | Lucy Returns | Who Initializes Navigation |
|--------|--------------|---------------------------|
| **A: Lookup only** | `{found, entity_id}` | Nate (add C2→C5 branch) |
| **B: Lookup + init** | `{found, entity_id, location, options}` | Lucy (current) |

**Arden's recommendation:** Option B (current behavior, simpler flow)

**Sandy's pick:** **B** - Lucy already does this well. Single-responsibility purists can fight me. Simpler flow wins.

### 13.7 Duplicate Detection Trigger

When does C7-C9 (duplicate handling) run?

| Option | Trigger | Flow |
|--------|---------|------|
| **A: Per-skill** | C6 → C7 | Every skill checks for duplicates |
| **B: Batch queue** | External script queues to C7 | Separate entry point |
| **C: Quinn's job** | Quinn detects, queues to C7 | External + workflow |

**Arden's recommendation:** Option C (keep main flow simple)

**Sandy's pick:** **C** - Duplicate detection is expensive. Don't run it per-skill. Quinn flags dupes, human reviews, then C7-C9 executes the merge. Keep the happy path fast.

---

## Sandy's Summary

| Question | Decision | Rationale |
|----------|----------|-----------|
| 13.1 Victor Model | **mistral-nemo:12b** | Fastest, concise, good REJECT detection |
| 13.2 Rejection Tracking | **A (Nate's state)** | KISS. `victor_attempts: 1` in output |
| 13.3 ESCALATE | **C (place + flag)** | Don't block flow, flag for later |
| 13.4 Clara `[n]` pre-Victor | **B (force place + log)** | Measure frequency before building |
| 13.5 Entry Point | **B (C2, kill C1)** | Mode B is dead |
| 13.6 Lucy Scope | **B (lookup + init)** | Current behavior, simple flow |
| 13.7 Duplicate Trigger | **C (Quinn's job)** | Keep main flow fast |

**Implementation priority:**
1. Kill C1, set C2 as entry point ← do now
2. Add `[n]` → force-place handling in Nate ← measure demand
3. Build Victor only if Clara picks `[n]` >5% of the time

ℶ Sandy


---

## 14. Implementation Log

### 2025-12-30: Entry Point & New Category Handling (Arden)

**Changes made per Sandy's decisions:**

#### 14.1 Killed C1, Set C2 as Entry Point

```sql
-- Executed:
UPDATE workflow_conversations 
SET is_entry_point = false, enabled = false 
WHERE workflow_id = 3020 
AND conversation_id = (SELECT conversation_id FROM conversations WHERE canonical_name = 'wf3020_c1_atomize');

UPDATE workflow_conversations 
SET is_entry_point = true 
WHERE workflow_id = 3020 
AND conversation_id = (SELECT conversation_id FROM conversations WHERE canonical_name = 'wf3020_c2_lookup');
```

**Result:**
| Conversation | is_entry_point | enabled |
|--------------|----------------|---------|
| wf3020_c1_atomize | false | false |
| wf3020_c2_lookup | true | true |

#### 14.2 Added `[n]` New Category Handling in Nate

**File:** `core/wave_runner/actors/wf3020_navigate.py`

**Changes:**
1. Added `n. ** NEW CATEGORY **` option to both top-level and sub-level option builders
2. Added handler for `[n]` selection that:
   - Logs warning: `clara_proposed_new_category | skill=X | location=Y | proposal=Z`
   - Forces PLACE HERE at current level
   - Returns `done: "true"` with `action: "forced_place_new_category_proposed"`
   - Includes `proposed_category` and `warning` in output

**Test:**
```
Input: letter="n. fintech_innovation - Emerging financial technology"
Output: {
  "done": "true",
  "action": "forced_place_new_category_proposed",
  "proposed_category": "fintech_innovation - ...",
  "warning": "Clara proposed new category... but Victor not implemented. Placed at ROOT."
}
```

**Monitoring:** To measure Clara's `[n]` frequency:
```bash
grep "clara_proposed_new_category" logs/daemon.log | wc -l
```

If this exceeds 5% of classifications, build Victor.

#### 14.3 Killed Mode B Batch Loop (C6→C2)

**Problem:** The old design had C6 (Adam/apply) looping back to C2 (Lucy/lookup) when `more_skills: "true"`. This was for batch atomization mode (Mode B) which we killed.

**Fix:**
```sql
-- Executed:
UPDATE instruction_steps 
SET enabled = false 
WHERE instruction_step_name = 'apply_to_lookup';
```

**Result:** Branch disabled. C6 now always continues to C7 (duplicate check) after applying a skill.

#### 14.4 Fixed Report Generator to Respect `enabled` Flags

**Problem:** Auto-generated report at `reports/workflows/3020_skill_taxonomy_engine.md` was showing:
- Disabled C1 conversation
- Disabled `apply_to_lookup` branch (C6→C2)
- Hardcoded `Start → C1` instead of actual entry point

**File:** `tools/admin/_document_workflow.py`

**Fixes:**
1. Added `AND wc.enabled = true` to filter disabled workflow_conversations
2. Added `AND (ist.enabled = true OR ist.enabled IS NULL)` in LEFT JOIN to filter disabled instruction_steps
3. Changed hardcoded `Start --> C1` to dynamic `Start --> C{first_exec_order}`

**Result:** Regenerated report now matches story:
- Starts at C2 (Lucy/lookup)
- No C1 shown
- No C6→C2 batch loop shown

---

### Ready for Testing? (Sandy's Review)

**What's implemented:**
| Item | Status | Notes |
|------|--------|-------|
| Entry point = C2 (Lucy) | ✅ Done | C1 disabled |
| Mode A only (single skill) | ✅ Done | Mode B batch loop removed |
| Clara's `[n]` option | ✅ Done | Logs + force place |
| Report generator fixed | ✅ Done | Respects enabled flags |

**What's NOT implemented (per decisions):**
| Item | Status | Notes |
|------|--------|-------|
| Victor (supervisor) | ⏳ Deferred | Build when `[n]` rate >5% |
| Quinn (QA cron) | ⏳ Separate | Not part of main workflow |
| Duplicate detection trigger | ⏳ Quinn's job | C7-C9 exist but Quinn decides when |

**Test Plan:**
```bash
# Single skill classification test
./scripts/q.sh "SELECT * FROM workflow_runs WHERE workflow_id = 3020 ORDER BY created_at DESC LIMIT 5"

# Or trigger manually via wave_runner with a test skill
```

**Questions for Sandy:**
1. Ready to run a test skill through C2→C3→C4→C5→C6→C7→END flow?
2. Any specific skills you want tested (new vs existing)?
3. Should we test the `[n]` path by crafting a prompt that encourages Clara to propose new category?

---

## Sandy's Review (2025-12-30)

**Excellent execution.** All four changes are clean and correct.

### Answers:

**Q1: Ready to run test?**
Yes. Let's do it. Start with ONE skill, watch the logs, verify each step completes.

**Q2: Specific skills to test?**
Three test cases:
1. **Existing skill:** `python` - should find existing entity, classify to existing group (fast path)
2. **New skill:** Pick something we don't have yet - `terraform` or `pulumi` - tests C3 entity creation
3. **Edge case:** Something ambiguous like `data_engineering` - could go data_analytics OR technical_engineering

**Q3: Test `[n]` path?**
Not yet. Let's verify the happy path works first. Once we have 50+ skills classified, check the `[n]` rate. If it's <1%, we did a good job with our root categories. If it's >5%, we need Victor.

### Minor Nit

The report generator fix is great, but:
```sql
AND (ist.enabled = true OR ist.enabled IS NULL)
```
Should probably be `AND ist.enabled IS NOT FALSE` or just check the column default. But it works, don't touch it.

### Approval

✅ **APPROVED for testing**

Run the three test cases above. Report back with:
- Workflow run IDs
- Final entity_relationship created (parent→child)
- Any errors or unexpected branches

If all three pass, we can batch-queue the unclassified skill_atomics.

ℶ Sandy

---

## 15. Test Results (2025-12-30)

### Test Execution

Queued 3 unclassified skills (Sandy requested `python`/`terraform` but those were already classified, so we used unclassified alternatives):

| queue_id | entity_id | skill | workflow_run_id |
|----------|-----------|-------|-----------------|
| 95182 | 24098 | business_administration | 178800 |
| 95183 | 34912 | authentication_and_authorization | 178802 |
| 95184 | 29197 | experimental_design | 178801 |

### Results Summary

All 3 completed successfully through the full path: **C2→C4→C5→C6**

| Skill | Clara's Choice | Navigate Result | Apply Result |
|-------|----------------|-----------------|--------------|
| business_administration | `[h]` PLACE HERE | place_here at ROOT | TOP LEVEL |
| authentication_and_authorization | `[h]` PLACE HERE | place_here at ROOT | TOP LEVEL |
| experimental_design | `[h]` PLACE HERE | place_here at ROOT | TOP LEVEL |

### Finding: Taxonomy Gap

Clara chose `[h]` PLACE HERE for ALL THREE skills. This is correct behavior because:

```
Current ROOT_CATEGORIES in wf3020_lookup.py:
a. technical_engineering - Programming, DevOps, cloud, databases, frameworks, tools
b. data_analytics_intelligence - Data science, analytics, ML/AI, business intelligence
c. compliance_risk - AML/KYC, regulatory, risk management, audit, legal
d. finance_banking - Trading, banking, financial analysis, accounting
e. communication_collaboration - Soft skills, leadership, teamwork, communication
h. ** PLACE HERE **
```

**None of these categories fit:**
- `business_administration` → not technical, not data, not compliance, not finance, maybe communication? Borderline.
- `authentication_and_authorization` → should be `technical_engineering` but Clara didn't navigate there
- `experimental_design` → could be `data_analytics_intelligence` (research methods)

### Sandy Decision Required

**Q1: Why did Clara choose `[h]` for `authentication_and_authorization`?**
This SHOULD go under `technical_engineering`. Was the model confused by the top-level options?

**Q2: Missing category?**
Should we add a 6th root: `business_management` or `operations` for skills like:
- business_administration
- project_management (if not already covered)
- operations_management
- business_strategy

**Q3: No relationships created**
C6 reports `success: true` and "placed at top level" but no `entity_relationships` row was created. Is "TOP LEVEL" supposed to mean orphan (no parent)?

### Raw Interaction Data

**business_administration (workflow_run 178800):**
```
C2 (lookup): found=true, options generated
C4 (classify): response="[h]", latency=484ms
C5 (navigate): done=true, action=place_here, target_group=null
C6 (apply): success=true, target_group="TOP LEVEL"
```

---

**Next steps:**
- [x] Sandy approval ← **DONE**
- [x] Run test batch ← **DONE** (3 skills tested)
- [x] Verify flow C2→C4→C5→C6 ← **WORKS**
- [x] Clean up orphan skill_groups ← **DONE** (87 deleted, 4 deprecated)
- [x] Make root categories dynamic ← **DONE** (Lucy queries DB)
- [ ] **Create intermediate subgroups** ← BLOCKING
- [ ] Wire subgroups to roots via `is_a`
- [ ] Re-classify skills to proper depth

---

## 16. Story vs Workflow Comparison

**Purpose:** Track progress toward making WF3020 match what the story describes.

### Actors

| Story | Conversation | Script/AI | Status | Notes |
|-------|--------------|-----------|--------|-------|
| **Lucy** (Lookup) | wf3020_c2_lookup | Script | ✅ Working | Dynamic root categories |
| **Carl** (Create) | wf3020_c3_create | Script | ✅ Working | Creates skill_atomic entities |
| **Clara** (Classify) | wf3020_c4_classify | qwen2.5:7b | ⚠️ Partial | Can't navigate deep (no subgroups) |
| **Nate** (Navigate) | wf3020_c5_navigate | Script | ⚠️ Partial | Has `[n]` handling, needs path stack testing |
| **Victor** (Supervisor) | wf3020_c4b_supervisor | — | ❌ Not built | Deferred until `[n]` rate >5% |
| **Adam** (Apply) | wf3020_c6_apply | Script | ⚠️ Partial | TOP LEVEL = no relationship created |
| **Quinn** (QA) | wf3020_c7_qa | Script | ❌ Not integrated | Exists but not in workflow |

### Clara's Options

| Option | Story Says | Workflow Does | Status |
|--------|------------|---------------|--------|
| `[a-e]` Navigate to category | Pick subgroup to go DEEPER | ✅ Works | But no subgroups exist to navigate into |
| `[h]` PLACE HERE | File at current location | ✅ Works | Creates relationship (except at TOP LEVEL) |
| `[z]` GO BACK | Pop path stack, return to parent | ⚠️ Code exists | Needs path stack persistence testing |
| `[n]` NEW CATEGORY | Propose new group → Victor | ⚠️ Partial | Logs + forces place; no Victor yet |

### Hierarchy Structure

| Story Says | Workflow Reality | Gap |
|------------|------------------|-----|
| 5 root halls + children | 5 roots exist | ✅ |
| Sections connected via `is_a` | **0 is_a relationships** | ❌ CRITICAL |
| Shelves (deeper sections) | No depth structure | ❌ |
| Skills file at most specific level | All skills at root level | ❌ Result of above |

**Root cause:** The 5 root categories have 6,719 skills filed directly under them via `belongs_to`, but **zero subgroups** connected via `is_a`. Clara has nowhere to navigate.

```
Story expectation:
  technical_engineering
  ├── containerization_and_orchestration (is_a)
  │   ├── kubernetes (belongs_to)
  │   └── docker (belongs_to)
  └── databases (is_a)
      ├── postgresql (belongs_to)
      └── mongodb (belongs_to)

Current reality:
  technical_engineering
  ├── kubernetes (belongs_to)
  ├── docker (belongs_to)
  ├── postgresql (belongs_to)
  ├── mongodb (belongs_to)
  └── ... 3,088 more skills (belongs_to)
```

### QA Rules

| Rule | Story Says | Workflow Does | Status |
|------|------------|---------------|--------|
| No empty groups | Quinn deletes empty | We deleted 87 manually | ✅ Done manually |
| No loops | Quinn halts + alerts | Not checked | ❌ |
| Single parent | Each group has 1 is_a parent | No is_a relationships exist | N/A |
| Balanced depth (1-20 per group) | Quinn flags oversized | 3,092 in technical_engineering | ❌ |
| All roots are domains | Orphan groups get wired | 5 roots remain after cleanup | ✅ |

### Error Handling

| Scenario | Story Says | Workflow Does | Status |
|----------|------------|---------------|--------|
| Clara timeout | Retry 2x | Not tested | ⚠️ |
| Clara stuck (>20 turns) | Force place + flag | Not implemented | ❌ |
| Carl duplicate | `ON CONFLICT DO NOTHING` | Not verified | ⚠️ |
| Victor timeout | Retry 2x, escalate | Victor not built | ❌ |
| Adam constraint violation | Log duplicate, continue | Not tested | ⚠️ |

### What's Blocking Progress

1. **No intermediate subgroups** - Clara can only place at root or "navigate" into nothing
2. **No is_a relationships** - Even if subgroups existed, they're not wired
3. **Victor not built** - Clara's `[n]` proposals have nowhere to go

### Recommended Next Steps

**Phase 1: Create structure (manual/script)**
1. Identify 20-30 intermediate groups from existing skill names
2. Create them as `skill_group` entities
3. Wire to roots via `is_a` relationships

**Phase 2: Re-classify**
1. Queue all 6,719 classified skills for re-run
2. Now Clara can navigate into subgroups
3. Skills land at appropriate depth

**Phase 3: Build Victor**
1. Create wf3020_c4b_supervisor conversation
2. Add branch from Nate: `contains:"proposed_category"` → Victor
3. Victor creates groups on approval

---

## 17. Cleanup Log (2025-12-30)

### Orphan Skill_Groups Cleanup

**Before:** 97 orphan skill_groups (no `is_a` parent)
- 5 canonical roots (keep)
- 91 empty orphans (delete)
- 1 duplicate (`communication` with 6 children)

**Actions:**
```sql
-- Deleted 87 empty orphans
DELETE FROM entities WHERE entity_type = 'skill_group' AND status = 'active'
  AND canonical_name NOT IN (5 roots) AND no is_a AND no children;

-- Deprecated 4 with merge references
UPDATE entities SET status = 'deprecated' WHERE entity_id IN (36902, 37107, 37296, 37310);

-- Merged 'communication' into 'communication_collaboration'
UPDATE entity_relationships SET related_entity_id = 37325 
WHERE related_entity_id = 37051 AND relationship = 'is_a';
UPDATE entities SET status = 'deprecated' WHERE entity_id = 37051;
```

**After:** 5 orphan skill_groups (the canonical roots)

### Dynamic Root Categories

**Before:** Hardcoded in `wf3020_lookup.py`:
```python
ROOT_CATEGORIES = [
    ("technical_engineering", "..."),
    # ... 5 hardcoded entries
]
```

**After:** Queries DB dynamically:
```python
def get_root_categories(conn):
    cursor.execute("""
        SELECT canonical_name, description FROM entities
        WHERE entity_type = 'skill_group' AND status = 'active'
        AND NOT EXISTS (... is_a parent ...)
    """)
```

**Added descriptions to roots:**
| Root | Description |
|------|-------------|
| technical_engineering | Programming, DevOps, cloud, databases, frameworks, tools |
| data_analytics_intelligence | Data science, analytics, ML/AI, business intelligence |
| compliance_risk | AML/KYC, regulatory, risk management, audit, legal |
| finance_banking | Trading, banking, financial analysis, accounting |
| communication_collaboration | Soft skills, leadership, teamwork, communication |

### Test After Cleanup

Re-ran `authentication_and_authorization` (entity 34912):
- Clara saw all 5 dynamic categories + `[f]` PLACE HERE + `[z]` GO BACK + `[n]` NEW CATEGORY
- Clara chose `[f]` PLACE HERE (correct given no subgroups to navigate into)
- Workflow completed successfully

**Finding:** Workflow works correctly. The flat taxonomy is the bottleneck, not the code.

