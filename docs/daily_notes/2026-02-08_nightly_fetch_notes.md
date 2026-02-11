# 2026-02-08: Nightly Fetch Pipeline Overhaul

*Session with Arden (ℵ)*

---

## Summary

Rewrote the nightly_fetch.sh pipeline from 6 manual steps down to 3 steps by absorbing all enrichment logic into the pull_daemon. Ran the full pipeline live to validate. Found and fixed an infinite-loop bug on permanently-failing embeddings. Cleaned up 3 legacy IHL actors with broken work_queries.

---

## What Changed

### 1. nightly_fetch.sh: 6 Steps → 3 Steps

**Before (6 steps):**
1. AA fetch (Arbeitsagentur, 16 states)
2. DB fetch (Deutsche Bank)
3. job_description backfill (direct script call)
4. extracted_summary (direct script call)
5. Embeddings x3 (direct script call)
6. domain_gate classifier (direct script call)

**After (3 steps):**
1. `[1/3]` AA fetch (Arbeitsagentur, 16 states, metadata only)
2. `[2/3]` DB fetch (Deutsche Bank)
3. `[3/3]` `python3 core/pull_daemon.py --run-once --limit 50000`

Steps 3–6 are now handled entirely by pull_daemon, which auto-discovers work via each actor's `work_query` and processes them in priority order.

### 2. Domain Gate Promoted to Actor

`tools/populate_domain_gate.py` was being called as a standalone script in step 6. We added a `DomainGateClassifier` wrapper class and registered it as actor **1303** (prio 20, scale_limit 10, no model). Now it's just another cog in the pull_daemon machine.

### 3. Registered Enrichment Actors

| ID   | Name                      | Script                                    | Prio | Scale | Model      |
|------|---------------------------|-------------------------------------------|------|-------|------------|
| 1299 | job_description_backfill  | actors/postings__job_description_U.py     | 60   | 1     | -          |
| 1301 | external_partner_scrape   | actors/postings__external_partners_U.py   | 55   | 1     | -          |
| 1300 | extracted_summary         | actors/postings__extracted_summary_U.py   | 40   | 1     | -          |
| 1302 | embedding_generator       | actors/postings__embedding_U.py           | 30   | 3     | bge-m3:567m |
| 1303 | domain_gate_classifier    | tools/populate_domain_gate.py             | 20   | 10    | -          |

All actors have wrapper classes with `__init__(self, db_conn=None)`, `self.input_data`, and `process() -> dict`.

### 4. Pull Daemon Bug Fix: Failed Ticket Exclusion

**Problem:** 4 postings (139791, 130049, 66328, 106290) with very short match_text (106–141 chars) caused Ollama bge-m3 to return HTTP 500 (`"json: unsupported value: NaN"`). These postings got `failed` tickets, but `_find_work()` only excluded `pending`, `running`, `completed` — not `failed`. Result: infinite loop rediscovering the same 4 subjects every 2 seconds.

**Fix:** Added `'failed'` to the exclusion `IN` clause in both `_find_work()` (line ~444) and `_find_locked_subjects()` (line ~478):
```sql
AND i.status IN ('pending', 'running', 'completed', 'failed')
```

### 5. Legacy IHL Actors Cleaned Up

Three legacy actors had broken work_queries referencing non-existent columns/tables:
- `hybrid_posting_competencies_extraction_tt9121` → referenced `p.skill_keywords`
- `ihl_analyst_find_red_flags_tt9161` → referenced `posting_competencies` table
- `requirements_extract_tt9384` → referenced `extracted_requirements` column

All 3 were already `enabled=false`. Belt-and-suspenders: SET `work_query = NULL` on all 3 via MCP.

**Note:** `extracted_summary` (actor 1300) stays active — "the job_description is full of verbal fluff, which creates artificial similarity in the embeddings."

---

## Pipeline Run Results

Launched: `./scripts/nightly_fetch.sh 1 25000 force`

- AA fetch: 2,460 jobs across 16 states, 75+ new postings
- DB fetch: ran successfully
- Pull daemon: processed all enrichment (descriptions, summaries, embeddings, domain_gate)
- Embedding run: ~890 embeddings processed cleanly after the failed-ticket fix
- 4 postings permanently excluded (NaN from Ollama on short text)

---

## Schema Notes

- `task_types` is a **VIEW** on the `actors` table, filtered by `actor_type IN ('thick', 'script')`
- Has an INSTEAD OF UPDATE trigger for `last_poll_at` write-through
- Pull daemon queries: `WHERE c.enabled = TRUE AND c.work_query IS NOT NULL`

---

## Known Issues (carried forward)

1. **4 NaN-embedding postings** — too short for bge-m3, excluded via failed tickets
2. **job_description_backfill** — Playwright sync API inside asyncio loop error; posting 101053 "failed 3+ times"
3. **scripts/enrichment_daemon.py** — superseded by pull_daemon, should be removed
4. **owl actors** (1289, 1291) — still enabled with owl_pending work_queries, status unknown

---

## Files Modified

- `scripts/nightly_fetch.sh` — 6→3 steps, updated flowchart, updated pre-flight imports
- `core/pull_daemon.py` — added `'failed'` to ticket exclusion in `_find_work()` and `_find_locked_subjects()`
- `tools/populate_domain_gate.py` — added `DomainGateClassifier` wrapper class
- `actors/postings__embedding_U.py` — had `PostingsEmbeddingU` wrapper (from prior session)
- `actors/postings__external_partners_U.py` — had `PostingsExternalPartnersU` wrapper (from prior session)
- DB: 3 legacy IHL actors' `work_query` set to NULL
- DB: actor 1303 (domain_gate_classifier) registered

---

*ℵ*
