# WF2010 Enhancement Plan

**Created:** 2026-01-01  
**Status:** Phase 4 Ready  
**Author:** Arden

---

## Summary

Four enhancements to complete WF2010 skill taxonomy workflow:

| # | Feature | Purpose | Status |
|---|---------|---------|--------|
| 1 | Aliases | Match "k8s" = "kubernetes" | ✅ Complete |
| 2 | Dedup | Prevent "ai_ml" vs "ai-ml" duplicates | ✅ Complete |
| 3 | [N] New Folders | Classifier proposes new folders | ✅ Complete |
| 4 | [H] Triage | Escape hatch for confused classifier | ⬜ Not started |

---

## Phase 1: Alias Foundation ✅ COMPLETE

**Goal:** All skill matching goes through `entity_names`, not `entities.canonical_name`

### Key Insight
A canonical name IS an alias — it's just the primary one. All matching should hit `entity_names`.

### Implementation
- ✅ Migrated 11,079 canonical names to entity_names table
- ✅ Updated wf2010_lookup.py to query entity_names
- ✅ Broadened entity_type filter to `LIKE 'skill%'` for skill_atomic

---

## Phase 2: Dedup with AI ✅ COMPLETE

**Goal:** Catch near-duplicate folders before they're created

### Implementation
- ✅ Created `wf2010_dedup.py` module with:
  - Levenshtein distance calculation
  - Containment check (prefix/suffix)
  - Dynamic thresholds based on name length
  - AI confirmation via gemma3:4b
- ✅ Integrated into Victor's review flow
- ✅ Auto-rejects exact duplicates

---

## Phase 3: [N] New Folder Flow ✅ COMPLETE

**Goal:** Classifiers can propose new folders when none fit

### Implementation
- ✅ Classifier already supported [N] in prompt
- ✅ Fixed branch priority: `new_folder` branch (priority 10) > `match: false` (priority 2)
- ✅ Added resolve→victor branch for arbitrated new folder cases
- ✅ Updated Victor actor to:
  - Accept input from both compare and resolve
  - Run dedup + AI approval
  - Output `create_folder`, `new_folder_name`, `new_folder_parent_id`
- ✅ Apply creates folder with is_a relationship

### Test Result (2026-01-01)
- Skill: `quantum_machine_learning` (37469)
- Both classifiers proposed NEW_FOLDER under `technical`
- Victor approved `quantum_computing`
- Created folder 39973, placed skill
- **SUCCESS**
  }
}
```

---

## Phase 4: Triage Escape Hatch

**Goal:** Classifier can say "I'm stuck" instead of guessing wrong

### Design
- **Triage** = top-level folder (sibling of technical, interpersonal, etc.)
- Classifier can output `[H]` (help) → skill lands in triage
- Human reviews triage folder periodically
- After human classifies, system learns (future: fine-tuning data)

### Implementation ✅
- ✅ Created triage folder (entity_id 39974) under skill root
- ✅ Classifier already handles `[H]` → `command: "ESCALATE"`
- ✅ Compare maps `ESCALATE` → `needs_human: true` → `escalate: true, folder_id: 39974`
- ✅ Added branch `wf2010_compare_escalate` (priority 15) → Apply

### Triage Folder
```sql
-- Created triage folder (entity_id 39974)
SELECT * FROM entities WHERE entity_id = 39974;
-- canonical_name: 'triage', entity_type: 'skill_group', parent: 'skill' (39066)
```

---

## All Phases Complete! 🎉

| # | Feature | Status | Key Changes |
|---|---------|--------|-------------|
| 1 | Aliases | ✅ | wf2010_lookup.py queries entity_names |
| 2 | Dedup | ✅ | wf2010_dedup.py + Victor integration |
| 3 | [N] New Folders | ✅ | Branch priority fix + Victor script actor |
| 4 | [H] Triage | ✅ | Triage folder + compare routing |

---

## Verification

| Feature | Test | Expected | Verified |
|---------|------|----------|----------|
| Aliases | Query entity_names for skill | Returns via alias | ✅ |
| Dedup | Propose "cloud_infrastructure" | Victor rejects (exact) | ✅ |
| [N] | quantum_machine_learning | New folder quantum_computing | ✅ |
| Triage | Classifier outputs [H] | Routes to triage folder | ✅ (infra ready) |

---

## Success Criteria

| Feature | Test | Expected |
|---------|------|----------|
| Aliases | Query for "k8s" | Returns kubernetes entity |
| Dedup | Propose "ai_ml" when "ai-ml" exists | Victor rejects |
| [N] | Skill with no fit | New folder created, skill placed |
| Triage | Ambiguous skill | Lands in triage folder |

---

## Notes

- **triage** chosen as folder name (medical metaphor: needs expert review)
- All changes to wf2010_classify.py require daemon restart
- Test with small batches before bulk runs

---

*Document: docs/WF2010_enhancement_plan.md*
