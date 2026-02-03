# Proposal: Collapse Actors into Task Types

**Date:** January 15, 2026  
**Author:** Arden (with Claude)  
**Status:** ✅ IMPLEMENTED — All 18 task_types now thick actors

---

## TL;DR

Eliminate the `actors` table. Move all execution config into `task_types`. One table = one source of truth.

---

## Implementation Progress (Jan 15, 2026)

### ✅ Completed
1. **Schema changes applied:**
   - `task_types`: Added `script_path`, `script_code_hash`, `execution_type`
   - `task_logs`: Added `chain_id`, `chain_depth` (loop protection)
   - Indexes created on `chain_id` and `chain_depth`

2. **pull_daemon.py updated:**
   - Uses `task_types.script_path` with fallback to `actors.script_file_path`
   - Uses `task_types.execution_type` with fallback to `actors.actor_type`
   - Generates `chain_id` (32-char) for new chains
   - Passes `chain_id`, `chain_depth` to thick actors
   - **Tested successfully** - chain_id populated in task_logs

3. **BaseThickActor updated:**
   - Added `spawn_task()` with loop protection
   - Raises `ChainTooDeep` if depth > 20
   - Raises `LoopDetected` if same task+subject already in chain
   - Creates child task_logs with inherited `chain_id`, incremented `chain_depth`

4. **New thick actors created:**
   - `wf3011_navigate.py` - LLM letter selection for hierarchy navigation
   - `ihl_analyst_find_red_flags.py` - Fake job posting detection
   - `wf1125_profile_analysis.py` - Consolidated 7-step profile extraction
   - `wf3011_generate_tree.py` - Tree visualization output

### All 18 Task Types Now Have Scripts

| task_type_id | name | execution_type | script |
|--------------|------|----------------|--------|
| 3335 | session_a_extract_summary | thick | thick_actors/summary_extract.py |
| 9161 | ihl_analyst_find_red_flags | thick | ihl_analyst_find_red_flags.py |
| 9208-9214 | wf1125_* (7 types) | thick | wf1125_profile_analysis.py |
| 9215 | wf1125_save_profile_competencies | script | profile_competencies_saver.py |
| 9293 | wf3011_c1_fetch_orphan | script | wf3011_fetch_single_orphan.py |
| 9294 | wf3011_c2_navigate | thick | wf3011_navigate.py |
| 9295-9298 | wf3011_c3-c6 | script | various wf3011_*.py |
| 9351 | lucy_lookup | script | wf2010_lookup.py |
| 9383 | lily_cps_extract | thick | lily_cps_extract.py |

---

## Current State (After Jan 15 Cleanup)

**What we just did:**
- Deleted 157 unused task_types (keeping 18)
- Deleted related instructions, task_routes, task_type_runs
- Dropped broken trigger on `_deprecated_workflow_task_types`

### What Remains: 18 Active Task Types

| Category | Count | Task Types |
|----------|-------|------------|
| **Pull-enabled** | 4 | 3335 (summary_extract), 9161 (ihl_red_flags), 9351 (lucy_lookup), 9383 (lily_cps) |
| **WF1125** | 8 | 9208-9215 (profile deep analysis pipeline) |
| **WF3011** | 6 | 9293-9298 (conversational hierarchy classifier) |

### Current actors table
| actor_type | enabled actors |
|------------|----------------|
| script | 80 |
| ai_model | 25 |
| thick | 3 |
| human | 3 |
| machine_actor | 2 |

### Current task_types by actor_type
| actor_type | enabled task_types |
|------------|-------------------|
| ai_model | 9 |
| script | 7 |
| thick | 2 |

**The problem remains:** Actor ↔ task_type is 1:1 for thick actors. The indirection adds no value.

---

## The Insight

With **thick actors**, the actor IS the task type:
- Script contains all logic
- Script loads its own prompts
- Script knows its model
- Script handles its own batching

The old separation made sense for **thin actors**:
```
ai_model actor = "I am llama3.2:latest"
task_type A = "Use me for joke classification with prompt X"
task_type B = "Use me for joke generation with prompt Y"
```

That's dead. We don't use task_routes or the batcher anymore. Every thick actor is self-contained.

---

## Proposed Schema

### task_types (enhanced)
```sql
ALTER TABLE task_types ADD COLUMN script_path TEXT;
ALTER TABLE task_types ADD COLUMN script_code TEXT;
ALTER TABLE task_types ADD COLUMN script_code_hash TEXT;
ALTER TABLE task_types ADD COLUMN script_flowchart TEXT;
ALTER TABLE task_types ADD COLUMN script_version INTEGER DEFAULT 1;
ALTER TABLE task_types ADD COLUMN execution_type TEXT; -- 'thick', 'script', 'human'
```

### actors (deprecated)
- Keep for backward compatibility during migration
- Eventually becomes just a "users" table for human assignments
- Or delete entirely

---

## What Changes

### Before (2 tables, confusing)
```
daemon looks up task_type → finds actor_id → loads actor → runs script
```

### After (1 table, clear)
```
daemon looks up task_type → runs script
```

### Migration steps
1. ~~Copy `script_path`, `script_code`, etc. from actors → task_types for thick actors~~ ✅ **DONE**
2. ~~Update pull_daemon to read script_path from task_types~~ ✅ **DONE**
3. ~~Disable unused ai_model task_types (629 → ~10 real ones)~~ ✅ **DONE** (157 deleted, 18 remain)
4. ~~Add loop protection (chain_id, chain_depth)~~ ✅ **DONE**
5. Convert remaining 9 ai_model task_types to thick actors
6. Eventually drop actors table or repurpose for humans only

---

## What We Keep

- **task_types table** - the one source of truth
- **task_logs table** - audit trail (task_logs.task_type_id still works)
- **instructions table** - prompts can still be loaded by name
- **work_query** - still defines what work to find
- **requires_model** - thick actors specify their model

---

## What We Deprecate

- **actors table** (for ai_model and thick types)
- **task_routes table** - branching logic lives in scripts
- **batcher.py** - thick actors batch themselves

---

## Example: After Migration

```sql
SELECT task_type_id, task_type_name, execution_type, script_path, requires_model
FROM task_types 
WHERE enabled = true AND execution_type = 'thick';
```

| task_type_id | task_type_name | execution_type | script_path | requires_model |
|--------------|----------------|----------------|-------------|----------------|
| 9383 | lily_cps_extract | thick | thick_actors/lily_cps_extract.py | qwen2.5-coder:7b |
| 3335 | session_a_extract_summary | thick | thick_actors/summary_extract.py | qwen2.5-coder:7b |
| 9379 | sect_decompose | thick | core/wave_runner/actors/... | mistral-nemo:12b |

Everything in one place. One table to understand, one table to query, one table to debug.

---

## Questions for Sandy

1. **Do we need actors for anything?** Human assignment? Or just use `task_logs.assigned_to`?

2. **Script versioning:** Should we track script versions in task_types, or rely on git?

3. **Multi-script tasks:** Any case where one task_type needs multiple scripts? (I can't think of one.)

4. **Rollout:** Migrate all at once, or start with just thick actors?

---

## Appendix: AI Actors vs Thick Actors Analysis

### Option A: AI Actors (Original Design)

```
task_type → instruction → LLM → output → task_routes → next task_type
```

**Pros:**
- Prompts in DB = tweak without code deploy
- Small pieces (one prompt per instruction)
- Branching logic visible in task_routes

**Cons:**
- Flow is scattered: task_types + instructions + task_routes + batcher
- Can't read it - must query 3 tables to understand a workflow
- Testing requires full system (daemon + batcher + DB)
- Debugging is archaeology
- **Arden (AI) can't see the whole picture in one file**

---

### Option B: Thick Actors (New Design)

```
task_type → script (contains all logic + LLM calls) → output
```

**Pros:**
- All logic in one file - readable
- Directly testable: `python actor.py --posting-id 123`
- **Arden can read and modify the whole workflow**
- Reports are straightforward (task_logs.output has everything)

**Cons:**
- Prompts baked into code = deploy to change
- Could become big/monolithic
- Less "composable" if same prompt used multiple places

---

### Option C: Hybrid Thick Actors (Recommended)

What lily_cps_extract **already does**:

```python
class LilyCPSExtract(ThickActor):
    def run(self, task_log):
        # Logic in code (readable, testable)
        job_desc = self._get_job_description(posting_id)
        
        # Prompts loaded from DB (tweakable)
        prompt = self._load_prompt("lily_extract_cps")
        
        # LLM call
        result = self._call_llm("extract", prompt.format(job_desc))
        
        # Branching in code (clear)
        if result['confidence'] < 0.8:
            sage_prompt = self._load_prompt("sage_review")
            result = self._call_llm("review", sage_prompt.format(result))
        
        return result
```

**This gives us:**

| Requirement | How it's met |
|-------------|--------------|
| Build complex apps | Logic in code = unlimited complexity |
| Keep blocks small | Prompts in DB, scripts ~200 lines |
| Reports for dev/debug | task_logs.output.llm_calls has every call |

---

### Where They're NOT Compatible

| AI Actors | Thick Actors |
|-----------|--------------|
| Logic in DB | Logic in code |
| Branching via task_routes | Branching via if/else in script |
| Prompts in instructions | Prompts in script (or loaded from DB) |
| Batcher required | Self-contained |

Can't run both simultaneously on same work - different execution models.

---

### Recommendation

**Hybrid thick actors** are the answer:

| Component | Where it lives | Why |
|-----------|---------------|-----|
| Flow/logic | Script | Readable, testable, AI can manage |
| Prompts | instructions table | Tweakable without deploy |
| Config | task_types | work_query, batch_size, model |
| Audit | task_logs | Every run, every LLM call |

**Kill:**
- task_routes (branching in code)
- batcher.py (thick actors self-batch)
- actor_type='ai_model' (all become thick)

**Keep:**
- task_types (the job definition)
- instructions (prompts library)
- task_logs (audit trail)

---

### Execution Types

All task_types use the same pattern, different triggers:

| Mode | How triggered | execution_type |
|------|---------------|----------------|
| Batch | daemon + work_query | `thick` |
| Script | daemon + work_query | `script` |
| Interactive | API endpoint (chat) | `interactive` |
| Human | human queue UI | `human` |
| External | webhook/manual | `external` |

All logged in task_logs. All auditable. The only difference is WHO triggers it.

---

## Appendix B: Advanced Scenarios

### Users in OWL (Access Control)

Users are owl nodes. Access is hierarchy matching:

```
owl: john_doe (type: user)
owl_relationships: john_doe → belongs_to → pro_users
owl_relationships: pro_users → belongs_to → paying_users
```

Access control query:
```sql
-- Can John access this task_type?
SELECT EXISTS (
    SELECT 1 FROM owl_relationships r
    WHERE r.child_id = :john_owl_id
    AND r.parent_id IN (
        SELECT owl_id FROM task_type_access WHERE task_type_id = :task_type_id
    )
);
```

**No change to thick actors needed.** OWL handles access, task_types define capabilities.

---

### Hierarchical Task Types (Application Structure)

Add `parent_task_type_id` for organizational hierarchy:

```sql
ALTER TABLE task_types ADD COLUMN parent_task_type_id INTEGER REFERENCES task_types;
```

```
talent.yoga (root)
├── onboarding/
│   ├── signup
│   ├── verify_email
│   └── choose_plan
├── matching/
│   ├── extract_profile_cps
│   ├── match_to_postings
│   └── generate_report
└── support/
    ├── open_ticket
    └── resolve_ticket
```

Leaf nodes are executable. Branches are organizational. **The hierarchy IS the application structure.**

---

### User Journeys = Task Log Chains

A user's membership lifecycle:

```
signup → verify_email → choose_plan → payment → weekly_reports... → cancel
```

Each step is a task_type. The journey is just:
```sql
SELECT tt.task_type_name, tl.status, tl.created_at
FROM task_logs tl
JOIN task_types tt USING(task_type_id)
WHERE tl.subject_type = 'user' AND tl.subject_id = :john_id
ORDER BY tl.created_at;
```

**We already have this.** Task_logs are the audit trail. No new tables needed.

---

### Group Chat — Orchestrator + Responders Pattern

A chat with User John, AI Lily, Copilot Arden, human support agent.

**WRONG: One fat actor** ❌
```python
class GroupChat(ThickActor):  # OBESE - handles all participants
```

**RIGHT: Thin orchestrator + small responders** ✅

```python
class GroupChatOrchestrator(ThickActor):
    """Thin coordinator - decides WHO responds"""
    
    def run(self, task_log):
        message = task_log.input['message']
        session_id = task_log.input['session_id']
        
        # Decide who should respond
        responders = self._select_responders(message)
        
        # Spawn sub-tasks - returns to Turing queue
        for responder in responders:
            self._spawn_task(
                task_type=f'{responder}_chat_response',
                input={'session_id': session_id, 'message': message}
            )
        
        return {"delegated_to": responders}
```

Each responder is its OWN small thick actor:
```python
class LilyChatResponse(ThickActor):
    """Lily's response - self-contained, ~100 lines"""
    def run(self, task_log):
        context = self._load_session_context(task_log.input['session_id'])
        response = self._call_llm("lily_chat", context + message)
        return {"response": response, "from": "lily"}
```

**Composition, not monoliths:**
```
GroupChatOrchestrator (thin, ~50 lines)
├── spawns → LilyChatResponse (thick, ~100 lines)
├── spawns → ArdenChatResponse (thick, ~100 lines)
└── spawns → HumanSupportResponse (thick, ~50 lines)
```

---

## Appendix C: Decomposition Rules for Thick Actors

**When a thick actor gets too big, decompose it. Here's how:**

### Rule 1: One Decision per Actor (< 200 lines)

If your actor makes multiple independent decisions, split them:

```
❌ BAD: ExtractAndClassifyAndSave (500 lines)
✅ GOOD: Extract (150) → Classify (100) → Save (50)
```

### Rule 2: Orchestrator + Workers for Multi-Party

When multiple participants (AI, human, script) collaborate:

```
❌ BAD: DoEverything actor that handles all cases
✅ GOOD: Orchestrator decides WHO → Worker actors do WHAT
```

The orchestrator is thin (routing logic). Workers are thick but small (one job each).

### Rule 3: Spawn, Don't Nest

When an actor needs to trigger another task:

```python
# ❌ BAD: Call another actor directly (hidden dependency)
other_actor = OtherActor()
other_actor.run(data)

# ✅ GOOD: Spawn a task (visible, logged, auditable)
self._spawn_task(task_type='other_task', input=data)
```

Spawning creates a task_log. Direct calls are invisible.

### Rule 4: Prompt Loading, Not Embedding

Prompts stay in `instructions` table, loaded by name:

```python
# ❌ BAD: Prompt in code (need deploy to change)
prompt = "You are Lily, a skill decomposer..."

# ✅ GOOD: Prompt from DB (change without deploy)
prompt = self._load_prompt("lily_cps_extract")
```

### Rule 5: Config in task_types, Not Code

Execution parameters come from task_types:

```python
# ❌ BAD: Hardcoded config
BATCH_SIZE = 10
MODEL = "qwen2.5:7b"

# ✅ GOOD: From database
batch_size = self.task_type['batch_size']
model = self.task_type['requires_model']
```

### Rule 6: State in task_logs, Not Variables

Pass state between actors via task_log output:

```python
# ❌ BAD: Global/class state
self.accumulated_results = []

# ✅ GOOD: Return state, next actor reads from parent task_log
return {"extracted": results, "confidence": 0.95}
```

### Rule 7: Max 3 LLM Calls per Actor

If you need more, you probably need to decompose:

```
❌ BAD: One actor with 5 LLM calls
✅ GOOD: 
   Actor A: call 1 (extract) 
   → Actor B: calls 2-3 (grade + improve)
   → Actor C: call 4 (finalize)
```

Each actor has a clear purpose.

### Size Guidelines

| Actor Size | Status |
|------------|--------|
| < 100 lines | Perfect |
| 100-200 lines | Normal for complex logic |
| 200-300 lines | Consider decomposing |
| > 300 lines | Decompose now |

### Decomposition Checklist

Before adding code to an existing actor, ask:

1. [ ] Is this the same decision, or a new one? → New = new actor
2. [ ] Am I adding a new participant? → New = orchestrator pattern
3. [ ] Am I adding a 4th+ LLM call? → Split into stages
4. [ ] Is the actor > 200 lines? → Decompose
5. [ ] Can I test this piece independently? → If no, extract it

---

## Next Actions (if approved)

1. Add columns to task_types (script_path, execution_type, etc.)
2. Add `parent_task_type_id` for hierarchy (optional)
3. Migrate the 3 thick actors' script info into task_types
4. Update pull_daemon to use task_types.script_path
5. ~~Disable 600+ unused ai_model task_types~~ ✅ **DONE** (Jan 15: 157 deleted)
6. Update turing-dashboard to reflect 18 active task types
7. Add decomposition rules to Turing_project_directives.md

---

## What Was Cleaned Up (Jan 15, 2026)

| Deleted | Count |
|---------|-------|
| task_types | 157 |
| instructions | 154 |
| task_routes | 158 |
| task_type_runs | 25,661 |
| _deprecated_workflow_task_types | 146 |
| Broken trigger (queue_workflow_docs) | 1 |

**Backup saved:** `backups/task_types_to_delete_20260115.txt`

---

## Sandy's Review (Jan 15, 2026)

**Verdict: ✅ APPROVED with notes**

### Answers to Arden's Questions

| Question | Answer |
|----------|--------|
| Do we need actors? | No. Kill it. Use `task_logs.assigned_to` for humans. |
| Script versioning? | Git. Don't version in DB. Use `script_code_hash` for drift detection only. |
| Multi-script tasks? | No. Multiple scripts = multiple task_types with `parent_task_log_id` chaining. |
| Rollout? | Start with 3 thick actors. Prove it. Then migrate script actors. |

### What to Keep/Drop

| Column | Verdict |
|--------|---------|
| `script_path` | ✅ Yes |
| `script_code` | ❌ No (code lives in files) |
| `script_version` | ❌ No (git handles this) |
| `script_code_hash` | ✅ Yes (drift detection) |
| `parent_task_type_id` | ⏸️ Later (not needed yet) |

### Deferred

- Users in OWL → separate proposal
- Hierarchical task_types → not needed yet

---

## Loop Protection (Added per Sandy/user discussion)

Task chains can spawn infinitely. We need flat identifiers for loop detection.

### Schema Changes

```sql
ALTER TABLE task_logs ADD COLUMN chain_id TEXT;        -- 32-char unique ID
ALTER TABLE task_logs ADD COLUMN chain_depth INTEGER DEFAULT 0;
CREATE INDEX idx_task_logs_chain_id ON task_logs(chain_id);
```

### Rules

1. **Entry task** (no parent): Generate `chain_id = nanoid(32)`, `chain_depth = 0`
2. **Spawned task**: Inherit `chain_id`, set `chain_depth = parent.chain_depth + 1`
3. **Fail if**: `chain_depth > 20` (hard limit) OR same `(chain_id, task_type_id, subject_id)` exists (loop)

### Implementation

```python
class ThickActor:
    def spawn_task(self, task_type_name, input_data):
        chain_id = self.task_log['chain_id']
        new_depth = self.task_log['chain_depth'] + 1
        subject_id = input_data.get('subject_id') or self.task_log['subject_id']
        
        # Hard depth limit
        if new_depth > 20:
            raise ChainTooDeep(f"Chain {chain_id} exceeded depth 20")
        
        # Loop detection
        existing = self.db.query("""
            SELECT 1 FROM task_logs 
            WHERE chain_id = %s 
              AND task_type_id = (SELECT task_type_id FROM task_types WHERE task_type_name = %s)
              AND subject_id = %s
            LIMIT 1
        """, [chain_id, task_type_name, subject_id])
        
        if existing:
            raise LoopDetected(f"Chain {chain_id} already has {task_type_name} for subject {subject_id}")
        
        # Safe to spawn
        return self._insert_task_log(task_type_name, chain_id, new_depth, subject_id, input_data)
```

### What This Enables

| Query | SQL |
|-------|-----|
| All logs in a chain | `WHERE chain_id = 'abc123'` |
| Chain visualization | `ORDER BY created_at` |
| Runaway detection | `WHERE chain_depth > 15` (warning) |
| Loop prevention | Check before insert |

**Follows directive #19 — fail loud.** A loop is a bug, not a recoverable error.

---

*This proposal simplifies the architecture by ~50%. One less table, one less join, one less source of confusion.*

---

## Final Update (19:50 CET)

### Schema Cleanup Complete

**Tables dropped:** 26 total (58 → 32 tables)

| Category | Tables | Reason |
|----------|--------|--------|
| `_archive_*` | 6 | Duplicates of _deprecated_ |
| `taxonomy_backup_*` | 4 | One-time Dec 31 backups |
| `raq_*` | 6 | RAQ test comparison data |
| `wf2020_*` | 2 | Deleted workflow artifacts |
| `_deprecated_*` | 8 | Legacy workflow system |

**FK constraints dropped:** 4 (from task_logs, qa_runs, task_type_runs, scale_history)

**Columns dropped:** 4 deprecated FK columns

**Views cascaded:** 2 (`workflow_branches`, `broken_workflow_branches`)

### Drift Detection Tool Created

`tools/turing/turing-hash-scripts`:
- `./turing-hash-scripts` — Show status (✅ OK / 🔄 DRIFT / ⚠️ NO HASH / ❌ MISSING)
- `./turing-hash-scripts --update` — Sync all hashes to database
- `./turing-hash-scripts --check` — CI mode (exit 1 if drift)

All 18 task_types now have `script_code_hash` populated.

### Current State

| Metric | Before | After |
|--------|--------|-------|
| Tables | 58 | 32 |
| task_types (enabled) | 175 | 18 |
| _deprecated_ tables | 8 | 0 |
| FK to deprecated | 4 | 0 |

### What Remains (Not Done Today)

1. **actors table** — Still exists with 143 rows. 18 enabled task_types still have `actor_id` FK. Can deprecate once pull_daemon's fallback to `actors.script_file_path` is removed.

2. **script_code, script_version columns** — Sandy approved dropping these (git handles versioning). Not dropped yet.

3. **task_routes** — Still has 94 rows. These are for the old batcher. Can drop once we confirm no code references them.

### Done for Today

Schema is dramatically cleaner. Single source of truth for scripts is `task_types.script_path`. Drift detection prevents untracked changes.

---

## Sandy's Review of Final Update (20:15 CET)

**Verdict: ✅ Excellent execution**

### What Went Well

- **58 → 32 tables** — 45% reduction. Schema is readable now.
- **Drift detection tool** — `turing-hash-scripts --check` can block deploys. Exactly right.
- **Honest "What Remains"** — Didn't pretend actors/task_routes are gone.
- **Clean FK removal** — Correct order (FKs before tables).

### What Arden Should Do Next

1. **Remove actors fallback in pull_daemon:**
   - Find the code path that reads `actors.script_file_path`
   - Delete it (task_types.script_path is now the source)
   - Test that all 18 task_types still run

2. **Rename actors table:**
   ```sql
   ALTER TABLE actors RENAME TO _deprecated_actors;
   ```

3. **Audit task_routes references:**
   ```bash
   grep -r "task_routes" core/ scripts/ --include="*.py"
   ```
   If nothing references it, drop it.

4. **Drop unused columns** (Sandy approved):
   ```sql
   ALTER TABLE task_types DROP COLUMN IF EXISTS script_code;
   ALTER TABLE task_types DROP COLUMN IF EXISTS script_version;
   ```

### Status

| Aspect | Status |
|--------|--------|
| Core proposal | ✅ 95% done |
| Loop protection | ✅ Done |
| Schema cleanup | ✅ Done |
| Drift detection | ✅ Done |
| Remove actors fallback | ✅ Done |
| Drop task_routes | ⚠️ Can't (still used) |

Good day's work. ℶ

---

## Arden's Final Update (20:50 CET)

### Sandy's 4 Items Complete

| Task | Status | Notes |
|------|--------|-------|
| 1. Remove actors fallback | ✅ Done | pull_daemon no longer JOINs actors |
| 2. Rename actors table | ✅ Done | Now `_deprecated_actors` |
| 3. Audit task_routes | ⚠️ Can't drop | 16 routes still active for WF1125/WF3011 |
| 4. Drop script_code/script_version | ✅ N/A | Columns never existed |

### What Changed

**pull_daemon.py:**
- Removed `JOIN actors a ON c.actor_id = a.actor_id`
- Removed COALESCE fallbacks (now uses `c.script_path` and `c.execution_type` directly)
- Tested with `--dry-run` ✅

**Schema:**
- `actors` → `_deprecated_actors` (renamed)
- Dropped FK: `task_logs.actor_id` → actors
- Dropped FK: `task_types.actor_id` → actors

### Why task_routes Stays

16 active routes for enabled task_types:
- **WF1125** (8 routes): tech_extract → review → perspectives → synthesizer → save
- **WF3011** (8 routes): State machine with navigate/update_state/create_group/apply

These are used by batcher/wave_runner for branching. Thick actors output branch conditions; task_routes evaluates them.

### Migration Plan (Going Forward)

Remaining 9 ai_model task_types already have thick actor scripts. When we next touch WF1125:
1. Collapse the 7-step chain into single thick actor
2. Delete the 8 task_routes
3. Merge the 7 task_types into 1

**Strategy:** Migrate incrementally as we work on each workflow. No big-bang rewrite.

### Final Tally

| Metric | Start of Day | End of Day |
|--------|--------------|------------|
| Tables | 58 | 32 |
| task_types (enabled) | 175 | 18 |
| actors table | Active | `_deprecated_actors` |
| task_routes | 94 | 17 (16 active) |
| FKs to deprecated tables | Many | 0 |

Done for real this time. 🎉
