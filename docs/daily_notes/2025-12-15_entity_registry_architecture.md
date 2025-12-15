# Entity Registry Architecture: A Scholarly Analysis
**Date:** December 15, 2025  
**Authors:** Arden & xai  
**For:** Sandy

---

## Executive Summary

We've been patching WF3005 to classify skills, but the underlying architecture has fundamental issues. This document analyzes the current state, identifies root causes, and proposes a cleaner solution.

**The Core Problem:** We have 5,847 skills. Only 153 (2.6%) have domain assignments. 5,694 are orphans. The workflow processed 8,208 "skills" but most of those were `entities_pending` records, not actual domain classifications.

---

## Part 1: Current State Analysis

### 1.1 The Numbers

| Table | What It Holds | Count |
|-------|--------------|-------|
| `entities` (skill) | Canonical skill records | 5,847 active |
| `entities` (skill_domain) | Domain categories (Technology, etc.) | 8 active |
| `entity_names` | Aliases (alternative names for entities) | 63 |
| `entity_relationships` (is_a) | Skill → Domain assignments | 181 |
| `entities_pending` | Incoming skills from job postings | 8,401 |
| `registry_decisions` | LLM classification decisions | 337 |

### 1.2 The Gap

```
Skills with domain assignment:     153  (2.6%)
Orphan skills (no domain):       5,694  (97.4%)
  - Never processed by LLM:      5,548  (94.9%)
  - Has decision, not applied:     146  (2.5%)
```

### 1.3 What WF3005 Actually Did

The dashboard showed "8,208 skills done" but this is misleading:

| What We Thought | What Actually Happened |
|-----------------|------------------------|
| Classified 8,208 skills into domains | Processed 8,208 `entities_pending` records |
| Assigned skills to Technology, etc. | Decided NEW/ALIAS/SKIP for pending skills |
| Built a skill taxonomy | Created 63 aliases and ~6,000 new entities |

**The workflow has TWO separate paths:**
1. **Pending Path** (`entities_pending` → triage → apply) - This ran to completion
2. **Orphan Path** (`entities` orphans → classify → assign domain) - This barely ran

---

## Part 2: The Terminology Confusion

### 2.1 "Skills" vs "Entities"

The codebase conflates several concepts:

| Term | In `entities_pending` | In `entities` | In `entity_relationships` |
|------|----------------------|---------------|---------------------------|
| "Skill" | A raw skill string from a job posting | A canonical skill entity | The subject of an is_a relationship |
| "Processing" | Triage (NEW/ALIAS/SKIP) | Classification (assign to domain) | Creating the is_a row |
| "Done" | Status = approved/merged/rejected | Has registry_decision | Has is_a relationship |

### 2.2 Why This Matters

When we say "process skills," we might mean:
1. **Deduplication**: Is "Python" the same as "Python Programming"? (handled by pending triage)
2. **Classification**: Does "Python" belong under Technology? (handled by orphan classifier)
3. **Hierarchy**: Should Technology have sub-domains like Languages, Databases? (not handled)

WF3005 conflates all three, with different paths for each.

---

## Part 3: Why Orphan Classification Doesn't Work

### 3.1 The Missing Loop

The orphan path works like this:

```
entity_orphan_fetcher → triage → classify → grade → debate → save → apply
```

But there's no **loop**. When we kick it off manually, it:
1. Fetches ONE batch of 25 orphans
2. Processes them through the pipeline
3. Stops

It doesn't automatically fetch the next batch. We have to manually create a new interaction to continue.

### 3.2 The Wiring Gaps (What We Fixed Yesterday)

| Component | Problem | Fix Applied |
|-----------|---------|-------------|
| `entity_orphan_fetcher` | Not wired to any instruction | Wired to `w3005_fetch_instruction` |
| `entity_decision_saver` | Not in workflow | Added to `w3005_c4_save` |
| `entity_decision_applier` | Not in workflow | Added to `w3005_c9_apply` |

Even after fixes, the workflow only runs ONE batch per trigger.

### 3.3 The Trigger Problem

WF3005 has **no triggers** in `workflow_triggers`. It relies on:
- Manual interaction creation
- Some external scheduler (doesn't exist)

Compare to a healthy workflow that would have:
```sql
INSERT INTO workflow_triggers (workflow_id, trigger_type, schedule_cron, ...)
VALUES (3005, 'schedule', '*/5 * * * *', ...);  -- Every 5 minutes
```

---

## Part 4: The Proposed Solution

### 4.1 What We Need

A workflow that:
1. **Runs continuously** until all orphans are processed
2. **Is self-sustaining** - fetches next batch automatically
3. **Handles all three tasks**: deduplication, classification, hierarchy management
4. **Is extensible** to other entity types (organizations, geography, etc.)

### 4.2 Option A: Fix WF3005 (Patch the Horse)

Add a trigger + modify the pipeline to loop:

```python
# In entity_orphan_fetcher, after returning results:
if has_more_orphans:
    create_next_batch_interaction()  # Self-perpetuating
```

**Pros:** Uses existing infrastructure  
**Cons:** Still complex, multiple code paths, hard to understand

### 4.3 Option B: New Workflow 3006 (Fresh Horse)

Create a clean, single-purpose workflow:

```
WF3006: Entity Classification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: FETCH
    - Query: SELECT * FROM entities WHERE is_orphan LIMIT batch_size
    - If empty → DONE
    - Else → Step 2

Step 2: CHECK_EXISTING
    - SQL: Does this skill exist in entity_names?
    - If yes → Step 2a (alias handling)
    - If no → Step 3

Step 2a: HANDLE_ALIAS
    - Record alias in entity_names
    - Link to existing entity
    - → Step 1 (next batch)

Step 3: CLASSIFY
    - LLM: Which domain does this skill belong to?
    - Confidence threshold: 0.8

Step 4: APPLY
    - SQL: INSERT INTO entity_relationships (entity_id, related_entity_id, relationship)
           VALUES (skill_id, domain_id, 'is_a')
    - → Step 1 (next batch)

Step 5: MONITOR_HIERARCHY
    - SQL: SELECT domain_id, COUNT(*) FROM entity_relationships GROUP BY domain_id
    - If any domain > 10 skills → Step 5a
    - Else → Step 1

Step 5a: SPLIT_DOMAIN
    - LLM: How should we split this domain?
    - Example: Technology → Software, Hardware, Infrastructure
    - Create sub-domains
    - Reassign skills
    - → Step 1
```

**Pros:** Clean, understandable, self-documenting  
**Cons:** New code to write, migration from WF3005

### 4.4 Option C: Simple Script (Skip the Workflow System)

For immediate results, a Python script that runs in a loop:

```python
# scripts/classify_orphans.py
while True:
    orphans = fetch_orphan_batch(25)
    if not orphans:
        print("All done!")
        break
    
    for skill in orphans:
        # Check alias
        if exists_in_entity_names(skill):
            record_alias(skill)
            continue
        
        # Classify
        domain = llm_classify(skill)
        
        # Apply
        create_is_a_relationship(skill, domain)
    
    # Hierarchy check
    check_and_split_large_domains()
```

**Pros:** Simple, immediate, easy to debug  
**Cons:** Doesn't use the Turing infrastructure, not "production"

---

## Part 5: Recommendation

### 5.1 Short Term (Today)

**Option C** - Write a simple script to classify the 5,548 orphans. Get results now, understand the problem better.

### 5.2 Medium Term (This Week)

**Option B** - Design WF3006 properly. Use lessons learned from the script. Make it self-sustaining and extensible.

### 5.3 Long Term (Architecture)

The entity registry will grow beyond skills:
- Organizations (companies, non-profits)
- Geography (cities, regions)
- Contractual provisions
- Literary analysis (as you mentioned)

Each entity type needs:
1. **Intake** - How do new entities enter?
2. **Deduplication** - Is this entity already known?
3. **Classification** - Where does it belong in the hierarchy?
4. **Hierarchy management** - When to split/merge categories?

A generic `EntityClassificationWorkflow` could handle all types with configuration:

```yaml
entity_type: skill
hierarchy_root: skill_domain
max_children_per_node: 10
classification_model: gemma3:4b
dedup_threshold: 0.85
```

---

## Part 6: Questions for Sandy

1. **Workflow complexity**: Is the conversation/instruction/step model worth the complexity? A simpler task queue might be easier.

2. **Self-perpetuating workflows**: Should workflows be able to spawn their own continuations? Or is external triggering better?

3. **Hierarchy depth**: How deep should the skill taxonomy go? Technology → Languages → Python → Libraries → Pandas?

4. **LLM reliability**: The debate panel (Challenge/Defend/Final) added latency but didn't improve accuracy much. Worth keeping?

5. **Real-time vs batch**: Should classification happen as skills arrive (real-time) or in batches overnight?

---

## Appendix: Current WF3005 Architecture

```
WF3005: Entity Registry - Skill Maintenance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATH A: Pending Skills (entities_pending → entities)
────────────────────────────────────────────────────
w3005_fetch_pending       → pending_skills_fetcher
w3005_triage_pending      → qwen2.5:7b (NEW/ALIAS/SKIP)
grade_triage_decisions    → qwen2.5:7b (verify)
w3005_apply_pending       → pending_skills_applier (create entities)

PATH B: Orphan Classification (entities → entity_relationships)
───────────────────────────────────────────────────────────────
w3005_fetch_instruction   → entity_orphan_fetcher
w3005_triage_orphans      → qwen2.5:7b (which domain?)
w3005_classify_orphans    → gemma3:4b (confirm)
w3005_grade_classifications → qwen2.5:7b (verify)
Challenge assignment      → qwen2.5:7b (debate)
Defend assignment         → gemma3:4b (debate)
Final decision            → gemma3:4b (resolve)
Validate parent categories → qwen2.5:7b (check hierarchy)
w3005_save_instruction    → entity_decision_saver
w3005_apply_decisions     → entity_decision_applier (create is_a)
w3005_export_registry     → entity_registry_exporter (generate tree)
```

**Actors:**
- `pending_skills_fetcher` - Queries entities_pending
- `pending_skills_applier` - Creates entities from decisions
- `entity_orphan_fetcher` - Queries unclassified entities
- `entity_decision_saver` - Saves to registry_decisions
- `entity_decision_applier` - Creates entity_relationships
- `entity_registry_exporter` - Generates folder tree

**Issues:**
- Path B doesn't loop
- No trigger for continuous processing
- 12+ LLM calls per skill (expensive, slow)

---

*"We got very far. But we might need to switch horses."* - xai

The horse (WF3005) got us here, but it's exhausted. Time for a fresh one.
