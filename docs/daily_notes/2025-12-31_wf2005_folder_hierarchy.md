# WF2005: Folder Hierarchy Classification
**Date:** 2025-12-31  
**Author:** Arden  
**Status:** Planning  

---

## Context: What We Have

### Working Workflows

| ID | Name | Subject | Relationship | Target |
|----|------|---------|--------------|--------|
| **WF2003** | Dual-Grader Skill Taxonomy | skill | `belongs_to` | skill_group |
| **WF2004** | Post-Batch Taxonomy QA | (batch) | finds issues | queues repairs |

### The Pattern (from WF3020_story.md)

The "Librarian" metaphor:
1. **Lucy** - Lookup (does entity exist?)
2. **Carl** - Create (make new entity if needed)
3. **Clara** - Classify (pick category from options)
4. **Nate** - Navigate (build next options, track path)
5. **Adam** - Apply (write the relationship)
6. **Victor** - Verify (approve new categories)
7. **Quinn** - QA (audit after batch)

WF2003 simplified this to a **dual-grader** approach:
- Two classifiers (A + B) must agree on a 2-letter code
- Arbitrator breaks ties
- No navigation loop needed (fixed 10 categories)

### The Problem

**17 orphan skill_groups** have no `is_a` parent:

```
accrual_processing          → should be under: domain_expertise or execution_and_compliance?
adobe_experience_platform   → technical
software_testing            → technical or execution_and_compliance?
interpersonal_skills        → interpersonal
education_&_qualifications  → domain_expertise?
]_project_management        → (malformed name - needs cleanup)
```

These were created by WF2003 as targets for skills, but they're floating - not connected to the 10 root categories.

### The Root Categories (created today)

| entity_id | canonical_name |
|-----------|----------------|
| 39051 | perception_and_observation |
| 39052 | language_and_communication |
| 39053 | cognitive_and_analytical |
| 39054 | creative_and_generative |
| 39055 | execution_and_compliance |
| 39056 | technical |
| 39057 | physical_and_manual |
| 39058 | domain_expertise |
| 39059 | interpersonal |
| 39060 | self_management |

---

## The Insight: Folders ARE Entities

There are no "folders" in the database. The folder structure visualized in `reports/hierarchy_wf3020/` is just a representation of `is_a` relationships:

```
technical (entity 39056)
    ↑ is_a
containerization (entity 12345)
    ↑ is_a  
kubernetes_ecosystem (entity 67890)
    ↑ belongs_to
kubernetes (skill)
```

**WF2005's job:** Take an orphan skill_group and classify it into a parent group via `is_a`.

This is **the same classification problem** as WF2003, just one level up:

| | WF2003 | WF2005 |
|---|--------|--------|
| Subject | skill | skill_group |
| Relationship | `belongs_to` | `is_a` |
| Target | skill_group | parent skill_group |
| Terminates at | any skill_group | root category |

---

## Design Decision: Simple or Navigating?

### Option A: Simple Dual-Grader (like WF2003)

Ask two LLMs: "Which root category does `software_testing` belong to?"
- Returns 2-letter code (TC, EC, etc.)
- Creates `is_a` relationship to root directly

**Pros:** Simple, fast, reuses WF2003 pattern
**Cons:** Everything ends up directly under root - no intermediate levels

### Option B: Navigating Classifier (like WF3020)

Ask LLM to navigate the existing hierarchy:
- "Here are technical's children. Does software_testing fit one, or place here?"
- Can create intermediate groups
- Builds deeper hierarchy

**Pros:** Better structure, allows growth
**Cons:** More complex, needs navigation loop

### Recommendation: Start with Option A

For the current 17 orphans, simple classification to root is fine:
- `software_testing` → `technical` or `execution_and_compliance`
- `interpersonal_skills` → `interpersonal`
- `education_&_qualifications` → `domain_expertise`

Once we have a clean single-level hierarchy, we can evolve to navigation if needed.

---

## WF2005 Architecture

### Flow

```
Queue: orphan skill_group
    ↓
C1: Lookup (verify it's a skill_group, get context)
    ↓
C2: Classify A (mistral-nemo) → [TC]
C3: Classify B (qwen2.5) → [TC]
    ↓
C4: Compare (script)
    ↓ agree
C5: Apply (create is_a relationship)
    ↓ disagree
C4b: Arbitrate (gemma3) → [TC]
    ↓
C5: Apply
```

### Conversations to Create

| Order | Conversation | Actor | Type | Purpose |
|-------|--------------|-------|------|---------|
| 1 | wf2005_c1_lookup | wf2005_lookup | script | Verify subject, get children count |
| 2 | wf2005_c2_classify_A | mistral-nemo:12b | ai | First classifier |
| 3 | wf2005_c3_classify_B | qwen2.5:7b | ai | Second classifier |
| 4 | wf2005_c4_compare | wf2005_compare | script | Check agreement |
| 5 | wf2005_c4b_arbitrate | gemma3:4b | ai | Break ties |
| 6 | wf2005_c5_apply | wf2005_apply | script | Write is_a relationship |

### Script Actors Needed

**wf2005_lookup.py:**
- Input: `{subject_id: 12345}`
- Query: Get canonical_name, count children (skills + sub-groups)
- Output: `{found: true, group_name: "software_testing", skill_count: 31, subgroup_count: 0}`

**wf2005_compare.py:**
- Input: `{classifier_a: "[TC]", classifier_b: "[TC]"}`
- Output: `{agreed: true, final_code: "TC"}` or `{agreed: false}`

**wf2005_apply.py:**
- Input: `{subject_id: 12345, parent_code: "TC"}`
- Lookup: Map "TC" → entity_id 39056 (technical)
- Insert: `entity_relationships(entity_id=12345, related_entity_id=39056, relationship='is_a')`
- Output: `{success: true, relationship: "software_testing is_a technical"}`

### Prompt Template (Classifiers)

```
## Task
Classify this skill GROUP into ONE of the 10 root categories.
This group contains related skills - pick the BEST category for the group as a whole.

## Categories
PO = perception_and_observation (Sensing, monitoring, detecting)
LC = language_and_communication (Speaking, writing, translating)
CA = cognitive_and_analytical (Logic, math, problem-solving)
CG = creative_and_generative (Design, art, innovation)
EC = execution_and_compliance (Procedures, compliance, QA, auditing)
TC = technical (Tools, platforms, programming, systems)
PM = physical_and_manual (Motor skills, craftsmanship)
DE = domain_expertise (Industry knowledge: healthcare, finance, legal)
IP = interpersonal (Leadership, negotiation, teamwork)
SM = self_management (Time management, adaptability)

## Group to Classify
Name: {group_name}
Contains: {skill_count} skills, {subgroup_count} subgroups

## Instructions
Return ONLY the 2-letter code in brackets: [XX]
```

---

## Trigger Chain

```
WF2003 (skill → folder) completes batch
    ↓ trigger
WF2004 (Quinn QA) runs
    ↓ finds orphans
    ↓ queues to WF2005
WF2005 (folder → root) processes orphans
    ↓ trigger
WF2004 (Quinn QA) runs again
    ↓ no more orphans
    ↓ HEALTHY ✓
```

**Triggers needed:**
1. `after_wf2003_batch` → WF2004 (EXISTS - ID 5)
2. `after_wf2005_batch` → WF2004 (NEW)

**Quinn update needed:**
- Change `queue_for_clara()` from `workflow_id=3021` to `workflow_id=2005`

---

## Data Issues to Handle

### Malformed Names

```
]_project_management_methodologies  ← invalid leading bracket
education_&_qualifications          ← ampersand in name
```

Should wf2005_lookup flag these for cleanup before classification?

### Duplicate Groups

```
interpersonal_skills (entity 39039)  ← vs root "interpersonal" (entity 39059)
```

These might be semantic duplicates. Options:
1. Classify as-is (interpersonal_skills is_a interpersonal)
2. Merge into root (delete 39039, remap relationships)

For now: classify as-is. Quinn can catch true duplicates later.

---

## Implementation Checklist

- [ ] Create workflow record (WF2005)
- [ ] Create script actors (wf2005_lookup, wf2005_compare, wf2005_apply)
- [ ] Create conversations (c1-c5, c4b)
- [ ] Create instructions with prompts
- [ ] Create instruction_steps with branching
- [ ] Create workflow_conversations with execution_order
- [ ] Update Quinn to queue to WF2005
- [ ] Add trigger: WF2005 → WF2004
- [ ] Test with one orphan
- [ ] Run full batch

---

## Questions for Sandy

1. **Simple vs Navigation:** Start simple (direct to root) and evolve?
2. **Malformed names:** Flag and skip, or fix inline?
3. **Near-duplicates:** (interpersonal_skills vs interpersonal) - merge or classify?

---

*Ready to implement when Sandy approves approach.*
