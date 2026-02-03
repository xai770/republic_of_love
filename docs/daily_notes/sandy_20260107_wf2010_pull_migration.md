# WF2010 Pull Architecture Migration

*Sandy Handoff — January 7, 2026*

---

## Executive Summary

**WF2010 (Skill Taxonomy)** has been successfully ported from push to pull architecture. The `pull_daemon.py` now serves as the **single entry point** for both:

- **Thick actors** (WF2020 SECT Decompose) — self-contained Python scripts
- **Conversational workflows** (WF2010 Skill Taxonomy) — multi-turn LLM conversations

This is a significant architectural milestone. One daemon rules them all.

---

## What Changed

### 1. Pull Daemon Now Runs WaveRunner Automatically

Previously, the daemon only created `pending` interactions. WaveRunner had to be run separately.

**Now:** When pull_daemon picks up a conversational subject:
1. Creates the interaction with status `pending`
2. Automatically runs `WaveRunner.run(max_iterations=100)` 
3. WaveRunner processes the full conversation chain
4. Logs completion: `✅ Skill Taxonomy completed for skill:12587`

Key code in `_execute_conversational()`:
```python
runner = WaveRunner(
    interaction_id=interaction_id,
    db_conn=self.conn
)
result = runner.run(max_iterations=100)
```

### 2. Work Query Wrap Excludes Completed

The daemon wraps the conversation's `work_query` to prevent reprocessing:

```sql
WITH candidates AS ({work_query})
SELECT * FROM candidates c
WHERE NOT EXISTS (
    SELECT 1 FROM interactions i
    WHERE i.conversation_id = {conv_id}
      AND i.subject_id = c.subject_id
      AND i.subject_type = c.subject_type
      AND i.status IN ('pending', 'running', 'completed')  -- Added 'completed'!
)
```

**Bug fixed:** Without `completed` in the exclusion list, the daemon kept picking up the same skill repeatedly (13 times in a row before we caught it!).

### 3. Conversation Configuration

Skill Taxonomy (conversation 9351) now has:

| Setting | Value |
|---------|-------|
| `pull_enabled` | `true` |
| `scale_limit` | `1` |
| `batch_size` | `10` |
| `work_query` | Queries `entities_pending WHERE status='pending'` |

The `work_query`:
```sql
SELECT pending_id as subject_id, 'skill' as subject_type, raw_value as skill_name 
FROM entities_pending 
WHERE entity_type = 'skill' AND status = 'pending' 
ORDER BY created_at 
LIMIT :batch_size
```

### 4. Disabled Old Actors

These WF2020/2021 actors were causing "drift detected" spam because their script files don't exist:

| actor_id | actor_name | Action |
|----------|------------|--------|
| 260 | wf2020_fetch_pending | Disabled |
| 261 | wf2020_save_sect | Disabled |
| 266 | wf2020_sect_simple | Disabled |
| 268 | wf2021_skill_extract | Disabled |

They were relics from before the thick actor consolidation.

---

## Testing Results

### Full Chain Execution ✅

After resolving initial timeout issues, WF2010 works fully through pull_daemon:

```
12:09:41 [INFO] 📋 Skill Taxonomy: found 1 subjects (capacity: 1/1)
12:11:08 [INFO]   ✅ Skill Taxonomy completed for skill:18609
```

**Time per skill: ~60-90 seconds** (includes 2 LLM classification calls)

The full chain executes:
1. `Skill Taxonomy` (9351) - lookup existing skill
2. `wf2010_c2_create` (9352) - entity creation  
3. `wf2010_c3a_classify_a_v2` (9364) - Classifier A (mistral-nemo:12b)
4. `wf2010_c3b_classify_b_v2` (9365) - Classifier B (qwen2.5:7b)
5. `wf2010_c6_compare` (9356) - compare results, route to apply or arbitrate

### QA Monitor Results

```
[2026-01-07 12:14:55] WF2010: Rate:2/hr | Oversized:9 | NR:1

Classifier Agreement (last 24h):
  Agreed: 3 | Arbitrated: 3 | Rate: 50%

New folder created via pull:
  • data_security_principles_and_practices
```

### Bugs Fixed During Testing

1. **Over-fetch for exclusion wrap** — Inner query LIMIT ran before exclusion
   - Fix: Use `max(limit * 10, 100)` for inner query, final LIMIT after

2. **Input nesting** — Passed `{subject: {...}}` but actor expected root
   - Fix: Pass `subject` dict directly as input

3. **Status divergence** — Thick used `running`, conversational used `pending`
   - Fix: Both use `pending`, thick actors call `_claim_interaction()` first

4. **Timeout misunderstanding** — 30s conv timeout seemed like bug
   - Reality: ~60-90s per skill is normal with dual-grader LLM calls

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      pull_daemon.py                         │
│                    (Single Entry Point)                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   Thick Actors      │         │  Conversational     │
│   (actor_type=      │         │  (actor_type=       │
│    'thick')         │         │   'script')         │
├─────────────────────┤         ├─────────────────────┤
│ sect_decompose.py   │         │ WaveRunner          │
│ (runs directly)     │         │ (max_iterations=100)│
└─────────────────────┘         └─────────────────────┘
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     interactions table                       │
│              (status: pending → running → completed)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Remaining Work

### For Sandy (Next Session)

1. **RAQ Test Ready?** — For SECT Decompose (30 postings x 3 runs):
   - ✅ SECT Decompose is pull-enabled (conv 9379)
   - ✅ Thick actor works via pull_daemon
   - ⚠️ Need: batch_reason tracking for RAQ runs
   - ⚠️ Need: way to re-run same 30 postings 3 times

2. **Conversation Timeouts** — Some conversations may need longer timeouts
   - Current: 30s default
   - LLM calls can take 30-60s each
   - Check reaper isn't killing valid work

3. **QA Monitor** — Already working! Shows:
   - Rate: 2/hr (from recent pull runs)
   - Classifier agreement: 50%
   - New folders being created

---

## RAQ Test Readiness Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Pull daemon works | ✅ | Tested today |
| SECT thick actor | ✅ | Processes postings |
| WF2010 conversational | ✅ | Full chain works |
| Batch tracking | ⚠️ | `--batch-reason` exists but needs RAQ mode |
| Re-run same subjects | ❌ | Work query excludes completed |
| Output comparison | ❌ | Need RAQ analysis script |

**Verdict:** Need small modifications for RAQ mode:
1. Flag to bypass "already completed" exclusion
2. Batch tagging for run1/run2/run3
3. Output comparison tooling

### Questions for Ty

1. **RAQ mode** — Should we add `--raq-mode` flag that allows re-processing?
2. **Posting selection** — Pick 30 random or specific postings?

---

## Files Modified

| File | Changes |
|------|---------|
| `core/pull_daemon.py` | Added `completed` to wrap exclusion; `_execute_conversational` runs WaveRunner |
| DB: `actors` | Disabled 4 defunct actors (260, 261, 266, 268) |
| DB: `conversations` | Renamed conv 9351 to "Skill Taxonomy", enabled pull mode |

---

## Command Reference

```bash
# Run daemon for Skill Taxonomy only
python3 core/pull_daemon.py --conversation 9351

# Run daemon for all pull-enabled conversations  
python3 core/pull_daemon.py

# Check pending work
./scripts/q.sh "SELECT COUNT(*) FROM entities_pending WHERE entity_type='skill' AND status='pending'"
```

---

## Bottom Line

**Pull architecture now works for conversational workflows.** The daemon finds work, creates interactions, runs WaveRunner, and completes — all automatically. No more separate "queue" and "process" steps.

WF2010 is ready for production scale testing.

🎯 **One daemon to rule them all.**
