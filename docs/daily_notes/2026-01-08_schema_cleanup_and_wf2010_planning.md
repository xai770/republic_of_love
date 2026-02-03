Well, # Daily Note: 2026-01-08

## Schema Cleanup & WF2010 Planning

**Session with:** GitHub Copilot (Claude Opus 4.5)  
**Context:** Continuing from pull architecture migration, preparing for WF2010 port

---

## Part 1: Schema Cleanup (Completed)

Made the schema more intuitive for future AI sessions:

### Changes Made

| Change | Reason |
|--------|--------|
| Dropped `posting_skills`, `profile_skills` views | Were aliases for `_competencies` tables. One name only. |
| `task_logs.posting_id` → `_deprecated_posting_id` | Use `subject_id` + `subject_type` (generic pattern) |
| `task_logs.workflow_run_id` → `_deprecated_workflow_run_id` | Pull architecture uses `parent_task_log_id` |
| `task_logs.run_id` → `_deprecated_run_id` | Use `batch_id` for RAQ grouping |
| Dropped `task_logs.trigger_task_log_id` | Zero usage |
| Dropped `task_types.validated_prompt_id` | Orphaned references |
| `task_routes.instruction_id` → `from_instruction_id` | Clearer: "the instruction this route branches FROM" |
| All `task_type_name` → snake_case | 115 converted from "Title Case" |
| Fixed stale comments on `owl`, `owl_relationships`, `task_routes` | Comments said `skill_*`, data says `competency_*` |
| Updated directive #11 | `ConversationNames` → `TaskTypeNames`, added `SECTType` |

### Deprecated Columns (Delete after 2026-02-08)
- `task_logs._deprecated_posting_id`
- `task_logs._deprecated_workflow_run_id`
- `task_logs._deprecated_run_id`

---

## Part 2: Architecture Context

### What Changed Since WF2010 Was Paused

1. **SECT decomposition** - Competencies now decompose into Skill/Experience/Certification/Track Record
2. **Pull architecture** - Task types find their own work via `work_query`, no workflow orchestration
3. **RAQ per task type** - Each task type has its own QA mechanism, not workflow-level

### Current Postings Pipeline (Pull-Based)
```
session_a_extract_summary → graders → format_standardization → save_summary
    → hybrid_competencies_extraction → save_posting_competencies
    → ihl_analyst → ihl_skeptic → ihl_hr_expert → save_ihl_score → complete_run
```

### WF2010 Purpose
Classify items from `owl_pending` into the OWL hierarchy. Not just skills - EVERYTHING needed for matching:
- Skills (S)
- Experience requirements (E)  
- Certifications (C)
- Track records (T)
- Locations (city/state/country)
- Salary ranges
- Work modes (remote/hybrid/onsite)
- Languages spoken
- Academic qualifications

---

## Part 3: OWL Type Rename (COMPLETED)

### Changes Made

1. **Merged 186 duplicate canonicals** between `competency` and `competency_atomic` types
2. **Renamed owl_types in database:**
   - `competency`, `competency_atomic` → `skill`
   - `competency_group` → `folder`
   - `competency_root` → `taxonomy_root`
3. **Created `copilot_lessons` table** - migrated 6 records from owl (didn't belong there)
4. **Updated `core/constants.py`** - new OwlTypes class with deprecated aliases
5. **Updated all Python files** in `core/wave_runner/actors/` to use new type names

### Current owl_type Values (After Rename)
```
skill          | 11,237  (leaf skills like "python")
folder         |     67  (category containers)
taxonomy_root  |      1  (tree root)
city/state/country/continent | 24 (geography)
```

### Merged Entities
186 duplicate `canonical_name` pairs were merged (kept lower owl_id, updated all references).
Merged records marked with `status='merged'` for audit trail.

### Problems Originally Identified
1. ~~`competency` vs `competency_atomic` - unclear distinction~~ → Merged to `skill`
2. ~~Naming doesn't reflect SECT types~~ → Will add as needed
3. ~~`competency_` prefix is redundant~~ → Removed
---

## Part 4: RAQ Per Task Type

Each task type now needs its own QA mechanism. Options:

1. **Script validation** - Pattern matching, but avoid overfitting
2. **Pupil-tutor** - Tutor grades, provides feedback, pupil improves (max 3 tries)
3. **Dual graders** - Two models grade, improvement loop if either fails
4. **Best-of-three** - Three models generate, picker chooses best

Key insight: *Think like a PM setting up a team.* We have access to:
- Local models (fast, free)
- Cloud models (expensive, high quality)
- Scripts (deterministic, no hallucination)

Goal: 100% RAQ for every task type.

---

## Key Insight: SECT is NOT owl_type

**SECT is the PROOF STACK, not a classification of competencies.**

A posting says "5 years Python experience required":
- SECT decomposition extracts: `{"sect_type": "E", "core_skill": "Python", "years": 5}`
- **"Python"** (core_skill) → goes to `owl_pending` → gets classified into OWL hierarchy
- **"E" + 5 years** → stays in `posting_competencies.sect_type` and `.years_required`

**Matching happens in OWL by competency node.** The SECT dimensions tell us HOW STRONG the match is:
- Posting wants E (experience) + 5 years
- Profile has T (track record: "built trading system in Python")
- T > E → Strong match! Track record proves more than just experience.

### owl_type Should Be WHAT the Thing Is

| owl_type | Examples | Matching Logic |
|----------|----------|----------------|
| `skill` | python, leadership, sql | Hierarchy distance |
| `folder` | technical, interpersonal | Container (not matched directly) |
| `certification` | AWS Solutions Architect, CPA | Exact or equivalent |
| `degree` | MBA, Bachelor CS | Level + field |
| `city` | Frankfurt, Munich | Containment (Frankfurt ⊂ Germany) |
| `country` | Germany, USA | Containment |
| `language` | English, German | Proficiency level |
| `work_mode` | remote, hybrid, onsite | Exact match |

### Simplification Plan ✅ DONE
- ~~`competency_root` → `taxonomy_root`~~ ✅
- ~~`competency_group` → `folder`~~ ✅
- ~~`competency` + `competency_atomic` → `skill`~~ ✅
- ~~`copilot_memory` → delete or move~~ ✅ Moved to `copilot_lessons` table

---

## Open Questions

1. ~~**Rename owl_types now or after WF2010?**~~ Done now, cleaner foundation
2. ~~**What to do with `copilot_memory`?**~~ Moved to `copilot_lessons` table
3. **The 8,985 pending** - These are `core_skill` values from SECT decomposition waiting for hierarchy classification?

---

## Next Steps

1. ~~Finalize owl_type naming decision~~ ✅ Done
2. Port WF2010 to pull architecture:
   - Entry point: `lucy_lookup` with `pull_enabled=true`
   - Chain: lucy → carl → clara_a → clara_b → compare → (arbitrate) → (victor) → adam
   - All via `task_routes`
3. Implement RAQ mechanism for each task type in the chain

---

*For Sandy: Schema is clean. owl_types renamed. Pull architecture works. Next is WF2010 port.*
