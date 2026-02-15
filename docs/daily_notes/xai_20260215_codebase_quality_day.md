# 2026-02-15 — Codebase Quality Day

## Pipeline reliability (morning)

Overnight pipeline froze — diagnosed via `pg_stat_activity`. An orphaned
`berufenet_U.py --phase2` process held an `idle in transaction` lock for 7+
minutes, blocking the AA actor's `UPDATE postings SET last_seen_at`. Killed the
orphan (`kill -9`), pipeline resumed and caught up on 2,119 jobs.

Root cause: no timeout on idle transactions, no cleanup on actor crash.

**6 commits pushed:**

| Commit | Fix |
|--------|-----|
| `a82abcc` | Rate limit exhaustion stops only the current actor, not the whole daemon |
| `691a4ee` | VPN rotation redesigned: consecutive-failure counting instead of total |
| `979a5f5` | VPN skip for local actors via `requires_vpn` flag in `execution_config` |
| `589734b` | Daemon progress logging every 5 seconds |
| `040ef81` | Live streaming via `tee` in shell script |
| `34c14b8` | Berufenet progress logging every 5 seconds |

## "What stinks?" assessment + implementation (afternoon)

Asked Arden for an honest codebase assessment. Identified 8 systemic issues
and implemented all of them in a single commit (`62e7dfd`):

### 1. DB idle_in_transaction timeout
`ALTER DATABASE turing SET idle_in_transaction_session_timeout = '5min'`
— prevents any future orphan process from holding locks indefinitely.

### 2. Batch ON CONFLICT upserts
- **AA actor**: replaced row-by-row SELECT/UPDATE/INSERT (4,000+ queries for
  2,119 jobs) with `INSERT ... ON CONFLICT ... DO UPDATE` via
  `psycopg2.extras.execute_values()`. Batches of 500, uses
  `RETURNING (xmax = 0) AS was_inserted` to count new vs existing.
- **Deutsche Bank actor**: 3-phase approach — batch SELECT existing → batch
  UPDATE `last_seen_at` → per-new-job INSERT with ON CONFLICT DO NOTHING.

### 3. Actor base class (`core/base_actor.py`, ~600 lines)
Three classes:
- **`BaseActor`**: connection lifecycle (try/finally cleanup), signal handlers
  (SIGTERM/SIGINT), `subject_id` property, cursor/commit/rollback helpers,
  progress logging (5s intervals), LLM helpers (`call_llm`,
  `parse_json_response`, `is_bad_data_response`), shared `BAD_DATA_PATTERNS`.
- **`ProcessingActor(BaseActor)`**: 3-phase scaffold
  (preflight → work → QA with retry). Abstract hooks: `_preflight()`,
  `_do_work()`, `_qa_check()`, `_save_result()`.
- **`SourceActor(BaseActor)`**: for cron-driven batch fetchers, includes
  generic `batch_upsert()` method.

### 4. Proof-of-concept refactor
`postings__extracted_summary_U.py` refactored from standalone class to
`SummaryExtractActor(ProcessingActor)`. 431 → 310 lines. Removed `__del__`
antipattern, duplicate `BAD_DATA_PATTERNS`, duplicate `_call_llm` /
`_get_llm_settings` / `_save_summary`.

### 5. Transaction discipline
Baked into the base class — `cleanup()` always rollbacks before returning the
connection, signal handlers call `cleanup()`, `process()` wraps work in
try/except with rollback on failure.

### 6. task_types VIEW trigger fix
The `INSTEAD OF UPDATE` trigger on the `task_types` view was only propagating
8 of 16 columns. Updates to `priority`, `enabled`, `work_query`, `batch_size`,
`timeout_seconds`, `raq_config`, `script_code_hash`, `subject_type` were
silently dropped. Extended the trigger to handle all columns.

### 7. Pipeline tests (`tests/test_pipeline.py`)
24 tests across 8 test classes — all passing:
- `TestBaseActorLifecycle` (7): connection ownership, cleanup, subject_id, progress logging
- `TestProcessingActor` (4): 3-phase flow, preflight skip, no subject_id, work failure
- `TestAAUpsert` (2): ON CONFLICT new/existing counting, description update on longer
- `TestVPNRotationLogic` (1): consecutive failure counting
- `TestTaskTypesView` (2): priority and enabled update propagation
- `TestActorLoading` (2): daemon can load refactored actors
- `TestLLMHelpers` (5): JSON parsing, bad data detection
- `TestDBSettings` (1): `idle_in_transaction_session_timeout` is configured

### 8. Archive cleanup
Removed empty `archive/` directory (946 files previously cleaned to backups).

## Cron schedule change
Moved `turing_fetch` from 20:00 → **23:50** to catch late-posted jobs.
Scraper health check moved from 19:45 → **23:35** (still 15 min before fetch).

## Pipeline run verification
Launched fresh pipeline run after all changes. Completed in ~74 minutes,
all steps ran clean, 7 non-fatal errors (duplicates + stale warnings).

**DB stats at end of run:**
- Total postings: 239,465
- Active postings: 229,690
- Total embeddings: 265,844
- Pending embed: 51

## Commits today
| Hash | Description |
|------|-------------|
| `a82abcc` | fix: rate limit isolation |
| `691a4ee` | fix: VPN consecutive failure counting |
| `979a5f5` | fix: skip VPN for local actors |
| `589734b` | fix: daemon progress logging 5s |
| `040ef81` | fix: live streaming via tee |
| `34c14b8` | fix: berufenet progress logging 5s |
| `62e7dfd` | codebase quality: BaseActor, batch upserts, tests, DB safety |
