# 2026-02-16 — Overnight Fix + Infrastructure Hardening

**Session start:** ~01:00 (overnight pipeline monitoring)

---

## Starting state

| Metric | Value |
|--------|-------|
| Total postings | 242,444 |
| Active postings | 232,669 |
| Berufenet-mapped | 219,942 (91%) |
| Embeddings | 268,232 |
| Users | 6 |
| Open feedback | 1 (#16) |
| Pipeline (overnight) | Completed with 1,254 errors |

---

## Work log

### 1. Pipeline cursor bug fix (`7dfaf01`)

Overnight `turing_fetch` (23:50 cron) completed but step 5 (description
retry) logged **1,254 `cursor already closed` errors**. Every item that
should have been marked as rejected was silently skipped.

**Root cause:** Yesterday's fix (`10fd880`) added a "mark as rejected"
`else` branch in `berufenet_description_retry.py`, but placed
`cur.execute()` outside the `with conn.cursor() as cur:` block. The cursor
from the `if picked_indices:` branch was either undefined (first NONE
result) or already closed (after a successful match).

**Fix:** Wrapped the else branch in its own `with conn.cursor() as cur:`
context manager. Zero errors on re-run.

### 2. Pipeline re-run (clearing backlog)

After the cursor fix, re-ran `turing_fetch` to clear pending work:

| Metric | Before | After |
|--------|--------|-------|
| Pending embeddings | 1,657 | 84 |
| Description retry errors | 1,254 | 0 |
| New embeddings generated | — | 44,216 |
| Total embeddings | 266,599 | 268,232 |

All 8 pipeline steps green. Duration: 14.1 minutes.

### 3. `/bi` page fix (`dbe72d4`)

`/bi` embedded `bi.talent.yoga` in an iframe, but the Streamlit server
sends `X-Frame-Options` headers blocking iframe embedding. Firefox showed
"Firefox Can't Open This Page."

**Fix:** Changed `/bi` from rendering `bi.html` (iframe) to a direct 302
redirect to `https://bi.talent.yoga`.

### 4. BI dashboard auto-start (`18bfb13`)

The Streamlit BI app on port 8501 was not running — `bi.talent.yoga`
returned 502 Bad Gateway. Started manually, then created infrastructure:

- `scripts/start_bi.sh` — idempotent startup script with `--daemon` mode
  (checks if already running, backgrounds with nohup)
- `@reboot` cron entry for automatic restart after server reboot

### 5. Feedback #16 — Messages page (`6184d61`)

**Issue:** "Lets remove this grey empty area on the left."

The messages page had the 70px icon sidebar alongside the chat
conversations list — wasted horizontal space.

**Fix:**
- Removed sidebar from messages page entirely (chat-list serves as left nav)
- Set `margin-left: 0` on `.main-content` for messages page
- Added system-event rendering for logon/logoff messages — shows as subtle
  inline green/red dot notices (WhatsApp-style)

---

## Commits today

| Hash | Description |
|------|-------------|
| `7dfaf01` | fix: cursor scope bug in description retry |
| `dbe72d4` | fix: /bi redirect instead of iframe |
| `18bfb13` | add: start_bi.sh + @reboot cron for BI auto-start |
| `6184d61` | fix: messages sidebar removal + logon/logoff event rendering |

---

## Dropped balls — review of Feb 11–15 notes

Reviewed daily notes from Feb 11–15 and ROADMAP.md. Identified items that
were discussed/planned but not yet implemented:

### Still open (from previous notes)

1. **extracted_summary failures** (Feb 15 codebase quality note): 17–18
   LLM summary failures per run. All Deutsche Bank postings. QA correctly
   rejects hallucinated output from qwen2.5:7b. Not urgent — these are
   edge cases for the 7b model. Consider: dedicated prompt for DB postings,
   or skip QA for high-quality descriptions.
   
   **→ RESOLVED:** Root cause: word-overlap QA validator was designed for
   same-language extraction, but DB postings are German while summaries are
   English. Legitimate translations flagged as "hallucinations" (0% overlap).
   Fix: dropped word-overlap validation, kept bad-data-pattern and length
   checks. Also fixed `external_url` — was storing `/apply` URLs instead of
   description URLs (`regexp_replace` on 1,857 existing rows + actor fix).
   Reprocessed all 18: 18/18 success, 0 missing summaries for Deutsche Bank.

2. **Stale postings cleanup** (pipeline health): 2,114 stale postings
   (first seen >30d, last seen >7d, not invalidated). The
   `nightly_invalidate_stale.py` cron runs at 03:00 but these survive it.
   Need to check: is the threshold too conservative, or are these genuinely
   still appearing in AA results?
   
   **→ RESOLVED:** Implemented lazy verification (Google-style). Instead of
   bulk nightly invalidation, postings are verified on-demand when they
   appear in search results and haven't been checked in 24 hours. Background
   thread checks AA search API (or HEAD/GET for non-AA), updates
   `last_validated_at` on success, sets `invalidated=true` on 404/gone.
   Max 5 per search, 0.3s rate limit. New files:
   - `lib/posting_verifier.py` — verification logic + background thread
   - `api/routers/search.py` — added `enabled=true AND invalidated=false`
     filter (was missing!), wired lazy verification after results return.
   Also found: search was showing disabled and invalidated postings to users
   (no filter at all). Fixed.

3. **5 duplicate external_ids** (pipeline health): Persistent across runs.
   Likely legitimate — same job posted under slightly different metadata.
   Should investigate and either dedupe or accept.
   
   **→ RESOLVED:** Investigated — 99 duplicate pairs found, but ALL have
   pattern: one invalidated + one active (job re-fetched after invalidation).
   Zero active-active duplicates. A unique index on `external_job_id`
   already prevents duplicates during upsert. Added second partial unique
   index on `external_id` for belt-and-suspenders:
   `CREATE UNIQUE INDEX idx_postings_external_id_active ON postings (external_id)
   WHERE external_id IS NOT NULL AND invalidated = false AND enabled = true`
   Migration: `migrations/unique_active_external_id_20260216.sql`

4. **ROADMAP.md is stale** (last updated Feb 11): Metrics, cron time
   (still says 22:00, actually 23:50), test count (says 192, likely
   higher), and "Next Up" items are outdated. Several items from "Next Up"
   are partially done (search/filter UI exists, match notifications exist).

5. **Test coverage** (ROADMAP tech debt): Test count was 192 on Feb 11, 304
   on Feb 12. No new tests written since. Zero coverage on: auth flow,
   messages API, feedback API, Mira chat, pipeline scripts. Any regression
   in these areas is invisible until a user reports it.

6. **Complementary dimensional model** (Feb 13 QA note architecture
   proposal): hours/contract-type, "works mostly with," salary extraction.
   Discussed as next step for matching quality but not started.

7. **Profile builder UI** (ROADMAP high priority): Users can only create
   profiles via admin/API. No in-app UI for yogis to build their profile.

8. **Mira memory** (ROADMAP high priority): Chat context doesn't persist
   across sessions. Each page load resets the conversation.

---

## Process improvements — agreed action items

Based on discussion with Gershon. All six agreed for implementation:

### 1. Automated tests for critical paths
Start with pytest coverage for: auth flow, messages API, feedback API.
Current coverage: zero on these endpoints. Goal: catch regressions before
they reach production.

### 2. Pipeline error alerting
Pipeline health report goes to `yogi_messages` (in-app), but errors aren't
surfaced proactively. Add: a check after `turing_fetch` that sends a
Telegram/email/push alert if error count > 0. "Step 5 had 1,254 errors"
should wake someone up, not wait until morning.

### 3. Systemd services for all daemons
Currently using `@reboot` cron for BI app and backfill watchdog. Neither
the main FastAPI app nor Ollama have auto-restart. Migrate to systemd
services with `Restart=always` for: FastAPI (port 8000), Streamlit BI
(port 8501), Ollama.

### 4. CSS consolidation
Page-specific CSS is inline in templates (messages.html has ~400 lines of
`<style>`). Consolidate into separate per-page CSS files that are linked
from `base.html` or loaded conditionally. Easier to maintain, easier to
debug visual issues.

### 5. End-of-session daily notes discipline
Write daily notes at end of every session (not just when remembered).
Include: commits made, what to test tomorrow, known issues, dropped balls
from previous notes.

### 6. User behavior intelligence (Mira proactive support)
Logon/logoff events are now recorded in `yogi_messages`. Next step: build
intelligence layer where Mira detects patterns (repeated short sessions,
long inactivity, frustrated browsing) and offers contextual help. Requires:
user health scoring, session pattern detection, and system prompt
integration. Deserves its own design session.

---

## Implementation plan (today)

Priority order for the process improvements:

1. **Systemd services** — most impactful for reliability, prevents the
   BI-down-and-nobody-knows scenario
2. **ROADMAP.md refresh** — quick win, prevents stale docs confusion
3. **Automated tests** — start with API endpoint tests
4. **Pipeline alerting** — next session (needs Telegram/webhook setup)

*CSS consolidation and Mira intelligence deferred to separate sessions.*
