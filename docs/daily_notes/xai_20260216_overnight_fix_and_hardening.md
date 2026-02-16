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

### 6. Extracted summary failures + Deutsche Bank cleanup (`4b77f92`)

17–18 LLM summary failures per run — all Deutsche Bank postings. Root
cause: word-overlap QA validator designed for same-language extraction, but
DB postings are German while summaries are English. Legitimate translations
flagged as "hallucinations" (0% overlap).

**Fix:** Dropped word-overlap validation, kept bad-data-pattern and length
checks. Also fixed `external_url` — was storing `/apply` URLs instead of
description URLs (`regexp_replace` on 1,857 rows + actor fix). Reprocessed:
18/18 success, 0 missing summaries for Deutsche Bank.

### 7. Lazy posting verification + search safety (`1a8af0b`)

Search was showing disabled and invalidated postings (no filter at all!).
Implemented Google-style lazy verification: postings checked on-demand when
they appear in search results and haven't been verified in 24 hours.
Background thread checks AA search API, max 5 per search, 0.3s rate limit.

- `lib/posting_verifier.py` — verification logic + background thread
- `api/routers/search.py` — added `enabled=true AND invalidated=false` filter

### 8. Unique active external_id index (`91d69ab`)

Investigated 99 duplicate external_id pairs — all were one
invalidated + one active (re-fetched after invalidation). Zero
active-active duplicates. Added partial unique index as belt-and-suspenders.

### 9. API test coverage expansion (`bc403a6`)

89 new tests across 19 test classes. Total now: 404 passing. Covers auth
flow, messages API, feedback API, search endpoints, profile operations.

### 10. Domain filter fix + UI batch (`1dc6603`, `1bfbf15`, `59a405e`)

- Guard interaction endpoints against non-existent posting IDs
- Fix domain filter breaking search results (feedback #22)
- Alpha-sort domains, stats below map, zen feedback button (#20 #23 #25)

### 11. Opportunity Landscape — Market Intelligence (`64f5e2a`)

Nate's daily note: move from "job search" to "labour navigation." Built:

- `demand_snapshot` table (10,358 rows) — daily batch aggregation of
  posting counts by state × domain × profession
- `profession_similarity` table (8,461 pairs) — embedding cosine similarity
  between professions for "related opportunities" suggestions
- `compute_demand_snapshot.py` + `compute_profession_similarity.py` batch scripts
- Intelligence API router with 4 endpoints (regional, related, activity, overview)
- Landscape UI page at `/landscape`
- Heatmap tuning: 90th percentile normalization, 7-stop gradient
- Pipeline hooks in `turing_fetch.sh`
- Migration: `025_demand_snapshot.sql`

### 12. Search intelligence panel (`c03ff89`, `dd78821`, `24caa3f`)

Gershon's feedback: intelligence should be ON the search page, not a
separate page. Built into the right panel:

- Compact QL bars (matching domain bar density)
- 30-day sparkline showing daily posting activity
- Two side-by-side ranked lists: top states + top professions
- Works for all postings or filtered by domain
- Dark mode support

### 13. Restart script (`591e7e8`)

`tools/turing_restart.sh` — kills uvicorn, restarts with --reload, logs to
`logs/uvicorn.log`. Quick way to bounce the server during development.

### 14. Frustrationsabbau — Arcade Game (`e0285ce`, `8e2f709`)

Mysti's idea: retro arcade game for frustrated job seekers. Built:

- HTML5 Canvas Space Invaders variant at `/arcade`
- Player: pixel yogi in lotus pose with cyan glow
- Monsters (👾👹💀🐛🦇🕷️🐍👻🧟🤖😈🦂) fall from top — shoot for +10
- Fruits (🍎🍊🍋🍇🍉🍓🍌🫐🥝🍑) fall too — collect for +50
- Rare ⭐ star worth 100 pts
- Friendly fire penalty: -25 for shooting fruits
- Monsters escaping = lose a life (3 lives)
- Levels increase speed. CRT scanline overlay. Particle effects.
- Sidebar link: 👾 Frustabbau

### 15. Arcade full rebuild — bosses, weapons, leaderboard (`440a51b`–`f0a6c10`)

Mysti loved the arcade. Extensive overhaul across 6 commits:

- **Boss fights** every 5 levels with health bars and unique attack patterns
- **Weapon system**: spreadshot, laser beam, homing missiles — collected via power-ups
- **Combo/multiplier** system for consecutive hits
- **Leaderboard** — top 10 scores in DB, classic 3-char name entry screen
- **80s neon overhaul** — pure saturated colors, multi-glow halos, neon grid floor, glowing particles
- **Physics tuning** — slower start pace, momentum-based movement, spectacular weapon visuals
- **Bug fixes**: RealDictCursor dict access (not tuples), space bar not triggering feedback widget, gender-neutral leaderboard text ("Yogis" not "Guys")

### 16. Signal pipeline alerting (`a1c8205`)

`lib/signal_notify.py` existed but didn't load `.env` — SIGNAL_SENDER was
always None. Added `from dotenv import load_dotenv` call. Tested all 3
message types: `send_alert()`, `send_pipeline_summary()`, `send_error()` —
all delivered to phone via signal-cli.

`scripts/turing_fetch.sh` was already wired with `notify()` helper calling
both ntfy.sh and signal_notify.py on failure and completion.

### 17. Search map zoom fix — feedback #61 (`442c25b`)

**Issue:** Grey Leaflet tiles when zooming browser (viewport DPR 0.895).

**Root cause:** `ResizeObserver` on `#search-map` alone doesn't detect
browser zoom changes — the element doesn't resize, the viewport does.

**Fix:** Added `window.addEventListener('resize', ...)` with debounced
`map.invalidateSize()`, observed `.search-panels` container for grid
reflow, and called `invalidateSize()` after each `doSearch()` render.

### 18. CSS consolidation (`5f72d82`)

Moved 23 inline dark-mode declarations from `landscape.html` and
`documents_old_grid.html` into `frontend/static/css/style.css`. Admin
pages (`admin/*.html`) keep inline CSS — they use `admin/base.html` which
doesn't load `style.css`. Bumped cache version to `v=20260216e`.

### 19. Profile builder — upsert for new users (`de163a8`)

Profile builder UI already existed (form, CV upload, work history CRUD,
preferences, notifications) but **new users couldn't use it** — all
endpoints returned 404 when no profile row existed.

**Fix:** Added `_ensure_profile(user, conn)` helper that auto-creates a
`profiles` row on first interaction. All 5 profile endpoints now use it.
Also converted basic info form from broken htmx `hx-put` (form-encoded to
JSON endpoint) to proper `fetch()` with JSON body.

---

## Commits today

| Hash | Description |
|------|-------------|
| `7dfaf01` | fix: cursor scope bug in description retry |
| `dbe72d4` | fix: /bi redirect instead of iframe |
| `18bfb13` | add: start_bi.sh + @reboot cron for BI auto-start |
| `6184d61` | fix: messages sidebar removal + logon/logoff event rendering |
| `22fa6d8` | hardening: systemd services, ROADMAP refresh, API tests |
| `896ab98` | CSS consolidation + backup unification |
| `1a8af0b` | feat: lazy posting verification + search safety filters |
| `91d69ab` | unique partial index on external_id |
| `4b77f92` | fix: extracted_summary failures + Deutsche Bank URL cleanup |
| `bc403a6` | test: 89 new tests across 19 classes |
| `1dc6603` | fix: guard interaction endpoints |
| `1bfbf15` | fix: domain filter breaking search |
| `59a405e` | ui: feedback #20 #23 #25 |
| `64f5e2a` | feat: opportunity landscape — market intelligence |
| `c03ff89` | feat: search intelligence panel |
| `dd78821` | fix: intelligence for all postings |
| `24caa3f` | feat: 30-day sparkline |
| `591e7e8` | add: turing_restart.sh |
| `e0285ce` | feat: Frustrationsabbau arcade game |
| `8e2f709` | refactor(arcade): monsters & fruits |
| `1be695c` | docs: update daily notes with afternoon session |
| `0c13bab` | fix: rename 'System' to 'Arden' in messages |
| `440a51b` | feat(arcade): full rebuild — bosses, weapons, power-ups, combos, leaderboard |
| `e5261ee` | feat(arcade): slower pace, momentum physics, spectacular weapons |
| `f43be05` | feat(arcade): 80s neon overhaul — pure colors, multi-glow, neon grid |
| `ff6016a` | fix(arcade): leaderboard KeyError — RealDictCursor dicts not tuples |
| `8e10a19` | fix(arcade): score submission KeyError |
| `509db8e` | fix(arcade): space bar in inputs, gender-neutral leaderboard text |
| `f0a6c10` | feat(arcade): classic name entry for leaderboard |
| `a1c8205` | feat: Signal pipeline alerting — live and tested |
| `442c25b` | fix: search map grey tiles on browser zoom (#61) |
| `5f72d82` | feat: CSS consolidation — inline dark-mode → style.css |
| `de163a8` | feat: profile builder — auto-create profile for new users (upsert) |

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
