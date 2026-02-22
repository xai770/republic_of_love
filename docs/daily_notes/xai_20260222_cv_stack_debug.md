# Daily Notes — 2026-02-22 — CV Stack Debug & Partial Saves

## What We Shipped

### 1. Partial saves for CV extraction (`adb7bea`)

The CV job previously lost everything if it timed out mid-run. Now:

- `extract_and_anonymize` accepts an `on_partial` callback
- After each **Pass 1 chunk**: fires `{type: pass1_chunk, chunk, total_chunks, roles_found}`
- After each **Pass 2 role** anonymizes: fires `{type: pass2_role, partial_work_history: [...]}`
- `_run_cv_extraction` stores latest `partial_work_history` in the job dict as `partial_result`
- On `TimeoutError`: if `partial_result` has roles → saves as `status='partial'`; otherwise `status='failed'`
- Frontend pollers (profile + dashboard) handle `status='partial'`: imports what was found, shows "⚠ Partial import: N roles saved"

### 2. Progress messages improved

Chip now shows live messages:
- `🔍 Pass 1: 2/6 chunks — 11 roles so far…`
- `🔒 Anonymizing: 5/12 roles…`

---

## What Happened During Testing

Uploaded "Gershon Pollatschek Projects.md" (12,905 chars, 6 chunks):

| Time | Event |
|------|-------|
| 18:33:38 | Job started (new process after restart) |
| 18:35:39 | qwen2.5:7b FAILED chunk 1 (empty error) |
| 18:36:36 | gemma3:4b succeeded chunk 1: +6 roles |
| 18:38:36 | qwen2.5:7b FAILED chunk 2 |
| 18:39:32 | gemma3:4b succeeded chunk 2: +5 roles (11 total) |
| 18:41:32 | qwen2.5:7b FAILED chunk 3 |
| 18:42:15 | gemma3:4b succeeded chunk 3: +4 roles (15 total) |
| 18:44:00 | **Service restarted** (our commit) → job killed |

**Pattern**: qwen2.5:7b is failing every single chunk. gemma3:4b is reliably succeeding but each chunk takes ~3 min (2 min fail + 1 min fallback). 6 chunks × 3 min = ~18 min just for Pass 1.

---

## Root Cause Analysis

The code logic is correct. The problems are:

1. **qwen2.5:7b consistently fails** — empty error message (`"LLM call failed with qwen2.5:7b: "`) suggests timeout or OOM, not bad output. Possibly GPU memory pressure.

2. **Sequential Pass 1** — chunks run sequentially (by design, to avoid overwhelming Ollama). 6 chunks × ~3 min each = 18 min before Pass 2 even starts.

3. **Service restarts kill jobs** — in-memory jobs don't survive. Partial saves help for timeouts but not restarts.

---

## Open Question

Is qwen2.5:7b actually working at all? The `CALL_HARD_TIMEOUT = 240s` fires before we hear back from the model. `gemma3:4b` is smaller/faster and has been 100% reliable.

**Candidate fix**: Skip qwen2.5:7b entirely and use gemma3:4b as primary — halves the per-chunk time.

---

## Pending

- [ ] Run headless test script to confirm stack works without UI/HTTP noise
- [ ] Consider making gemma3:4b the primary model (or configurable per env)
- [ ] DB persistence for CV jobs (survive restarts) — lower priority given partial saves
