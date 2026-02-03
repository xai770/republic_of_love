# Schema Cleanup: 10 Dead Columns Dropped
**Date:** 2026-02-03 09:07  
**Author:** Arden

## Summary

Schema audit identified 22 dead columns (<5% fill rate). After code review, dropped 10 columns and archived 5 dead actors.

## Analysis

Queried fill rates by source:
- **AA (74,546 postings):** 0 for all legacy columns  
- **DB (3,594 postings):** ~2,000 rows for legacy columns

Legacy columns were only used by the old Deutsche Bank LLM workflow (WF3001) which has been replaced by embeddings.

## Columns Dropped

### postings (9 columns, 42→33)

| Column | Fill | Reason |
|--------|------|--------|
| `competency_keywords` | 2.6% | Old LLM skill extraction, replaced by embeddings |
| `extracted_requirements` | 2.6% | CPS extraction, replaced by `extracted_summary` |
| `job_description_en` | 2.6% | Translation for LLM — **bge-m3 is multilingual** |
| `source_id` | 2.6% | Legacy FK, replaced by `source` text field |
| `sect_decomposed_at` | 2.6% | Never used timestamp |
| `employment_career_level` | 0% | Never populated |
| `created_by_task_log_id` | 2.6% | Legacy task tracking |
| `updated_by_task_log_id` | 2.6% | Legacy task tracking |
| `processing_notes` | 0% | Debug field |

### profiles (1 column, 30→29)

| Column | Fill | Reason |
|--------|------|--------|
| `last_activity_date` | 0% | Never populated |

### Preserved

**`ihl_score`** — Internal Hire Likeliness, 2,019 rows of historical data for DB postings. Detects "theater postings" (jobs posted externally when internal candidate already selected). Kept frozen.

## Views

- **`posting_pipeline_status`** — DROPPED. Tracked dead LLM workflow stages (translation → summary → requirements → competencies).
- **`postings_for_matching`** — Recreated without dead columns, added `match_text` computed field.

## Actors Archived

Moved to `archive/dead_actors_20260203/`:

1. `postings__extracted_requirements_U.py` — CPS extraction actor
2. `posting_facets__expand_C__ava.py` — Competency keyword expansion  
3. `posting_facets__row_C.py` — Posting facets row creation
4. `analyze_column_json_mapping.py` — QA tool for column analysis
5. `batch_extract_skills.py` — Batch skill extraction

## Code Updated

- `postings__extracted_summary_U.py` — Removed translation logic (bge-m3 is multilingual)
- `api/routers/matches.py` — Changed `extracted_requirements` → `extracted_summary`
- `contracts.py` — Removed `source_id` from WF3001 input
- `scripts/qa/qa_audit.py` — Removed `processing_notes` references
- `actors/TEMPLATE_actor.py` — Updated pipeline examples

## Key Insight

**bge-m3 is multilingual** (DE↔EN at 0.93 similarity). The old pipeline translated German job descriptions to English for LLM processing. This is completely unnecessary — we can embed German directly.

## Migration

`data/migrations/20260203_drop_dead_columns.sql` — executed and documented.

## Commits

- `23617ac` — chore: drop 10 dead columns from schema

---

## Part 2: Profile Facets Cleanup (09:15)

### Analysis

Checked `profile_facets` usage:
- **Last ran:** 2026-01-27 11:57:04
- **Data:** 336 rows for 4 profiles
- **Actors:** Clara extracts facets, Diego enriches them

**Finding:** The matching pipeline has fallback to `profiles.skill_keywords`. The CPS decomposition was experimental — embeddings handle skill matching directly.

### Deleted Files

**Actors:**
- `profile_facets__extract_C__clara.py` — extracts CPS facets from work history
- `profile_facets__enrich_U__diego.py` — adds implied skills

**Tools:**
- `run_pending_extractions.py` — ran Clara on pending work history
- `clara_visualizer.py` — visualized Clara's facet extraction

### Why Profile Facets Are Dead

1. **Skills** — `profiles.skill_keywords` stores them directly, embeddings match them
2. **Domains** — Berufenet KLDB codes for AA postings, embedding clusters for others
3. **Certificates** — Rarely in AA postings, not a hard constraint
4. **Experience years** — Embeddings handle seniority naturally

### Remaining Work (TODO)

Files still reference `profile_facets` but could use `profiles.skill_keywords`:
- `api/routers/profiles.py` — returns skills from facets
- `api/routers/dashboard.py` — skills list
- `tools/profile_matcher.py` — has fallback already
- `tools/batch_match_runner.py` — profile skills
- `tools/match_report.py` — profile skills

The `profile_facets` and `posting_facets` tables have legacy data (336 + some rows). Can be dropped after API refactoring.

### Directives Updated

- Marked Profile Pipeline section as deprecated
- Updated actor examples from deleted Clara to active actors
- Updated CPS storage note to show both tables deprecated
- Updated MVP roadmap to strikethrough CPS items
