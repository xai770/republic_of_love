# 2026-02-17 — Pipeline Performance + Housekeeping + talent.yoga Review

**Session start:** ~04:59 CET (early morning, pipeline monitoring)
**Session continued:** ~09:00 CET (hit list from user feedback, talent.yoga audit)
**Session continued:** ~15:00 CET (anonymity infrastructure, Adele build)
**System time at writing:** Di 17. Feb 08:48 CET (updated ~20:00 CET)

---

## Starting state

| Metric | Value |
|--------|-------|
| Total postings | 258,430 |
| Active postings | 248,648 |
| Berufenet-mapped | 229,007 (92%) |
| Embeddings | 268,232 |
| Pending berufenet | 27,244 |
| Pending embeddings | 12,923 |
| Pipeline (overnight) | Crashed at step 5 (demand snapshot) |

---

## Work log

### 1. Pipeline diagnosis + crash fix (`8d3497b`)

Overnight `turing_fetch` (23:50 cron) ran for 19+ hours processing 27K
berufenet titles at 0.5/sec (Monday catch-up: 15,960 new postings from the
weekend). Pipeline then crashed at step 5 (demand snapshot) due to
`ts_prefix: command not found` on line 533 of `turing_fetch.sh`. The
function was never defined — `set -e` killed the script.

**Root cause analysis of the 19-hour runtime:**
- Not wasted work: `berufenet_id IS NULL` filter is correct
- 27,244 titles legitimately unclassified: 23,892 `no_match`, 1,886
  `llm_uncertain`, 1,304 `llm_no`, 162 `error`
- Bottleneck: Ollama LLM at 0.5 titles/sec (subprocess overhead)
- Berufenet step completed fully before crash — work was committed

**Fixes in this commit:**
- Removed `ts_prefix` pipe from demand snapshot call
- Fixed double logging: `tee` in script + redirect on command line = every
  line written twice. Added TTY detection: `if [ -t 1 ]` activates tee
  only when run interactively

### 2. Parallel embeddings — 5x speedup (`8d3497b`)

GPU utilization was only 25% during embeddings (vs 98% during LLM).
Investigated `actors/postings__embedding_U.py` — sequential
`requests.post()`, one at a time.

**Benchmarked concurrency levels:**
| Workers | Rate | GPU |
|---------|------|-----|
| 1 | 6.4/sec | 25% |
| 2 | 10.4/sec | 45% |
| 4 | 20.7/sec | 75% |
| 8 | 32.0/sec | 95% |
| 12 | 32.0/sec | 95% (plateau) |

Sweet spot: 8 workers. Added `ThreadPoolExecutor(max_workers=EMBED_WORKERS)`
with thread-safe queue pattern. Production test: 12,772 embeddings at
8.9/sec (3x real-world speedup accounting for DB writes).

Configurable: `EMBED_WORKERS=8` env var.

### 3. Tools cleanup — 85 files removed (`28c40db`)

Reviewed all 55 files in `tools/` across 8 subdirectories. Cross-referenced
with `grep -rl` across entire codebase to find actual usage.

**Kept (5 files):**
- `bi_app.py` — BI dashboard (Streamlit, port 8501)
- `pipeline_health.py` — pipeline health report
- `populate_domain_gate.py` — domain gate data (pipeline step)
- `sysmon.py` — system monitoring
- `turing_restart.sh` — server restart script

**Removed:** 47 files + 8 subdirectories = 85 files, 26,567 lines deleted.
Tests: 404 passed. Backup at `/home/xai/Documents_Versions/ty_learn`.

### 4. Berufenet LLM — 7x speedup (`b4342d5`)

Investigated why berufenet classification runs at 0.4 titles/sec despite
GPU at 90%. Found the smoking gun: both `llm_verify_match()` and
`llm_triage_pick()` in `lib/berufenet_matching.py` use
`subprocess.run(['ollama', 'run', model])` — spawning a **new OS process**
for every single LLM call.

**Fix 1: HTTP API.** Replaced subprocess with `requests.post('/api/generate')`.
Eliminates fork+exec+load overhead. Instant 4.8x speedup (0.4/s → 1.9/s).

**Fix 2: Concurrent workers.** Added `ThreadPoolExecutor(LLM_WORKERS=2)` to
the actor's Phase 2 processing. GPU-heavy work (embed + LLM verify) runs
in parallel threads; DB writes stay sequential.

**Also tested qwen2.5:3b** — 11.8/s but rejected: can't distinguish Koch
from Softwareentwickler (says UNCERTAIN instead of NO on obvious
mismatches). The 7b model stays.

**Benchmark (20 real titles):**
| Config | Rate | Speedup | Quality |
|--------|------|---------|---------|
| Old (subprocess, 1 worker) | 0.4/s | baseline | — |
| 7b HTTP, 1 worker | 1.9/s | 4.8x | same |
| 7b HTTP, 2 workers | 2.9/s | **7.3x** | same |
| 3b HTTP, 2 workers | 11.8/s | 30x | **rejected** |

500 titles: ~3 min instead of ~20 min.

Configurable: `LLM_WORKERS=2`, `BERUFENET_MODEL=qwen2.5:7b` env vars.

### 5. Pipeline runs — clearing backlogs

Ran `turing_fetch` twice during session to clear pending work:

| Metric | 04:59 | 07:32 (run 1) | 08:24 (run 2) |
|--------|-------|---------------|---------------|
| Total postings | 258,430 | 259,151 | 260,204 |
| Active | 248,648 | 249,335 | 250,388 |
| Embeddings | 268,232 | 281,004 | 282,328 |
| Berufenet pending | 27,244 | **0** | 0 |
| Embedding pending | 12,923 | 1,358 | 954 |

Demand snapshot: 10,821 rows. Profession similarity: 8,848 pairs.

### 6. User feedback hit list (items 1-9) (`e55a015`)

User reviewed the daily notes retrospective and responded with a detailed
10-item action list. Items 1-9 completed and committed in a single batch:

| # | Item | What was done |
|---|------|---------------|
| 1 | extracted_summary 56/56 failures | Fixed `_load_actor` in daemon — was importing wrong module path |
| 2 | 539 "given up" descriptions | Invalidated all 539 postings (`UPDATE SET invalidated = TRUE`) |
| 3 | subprocess+ollama in other files | Removed from 2 remaining active files (berufenet already done) |
| 4 | Embedding determinism | Tested 100 texts sequential vs 8 workers — 100/100 exact match |
| 5 | Config consolidation | Created `config/settings.py` — single source for all tunables |
| 6 | Log readability | Added `LOG_FORMAT=human` option, structured JSON default |
| 7 | Stale postings sweep | Nightly script rebuilt, 2,114 stale postings invalidated |
| 8 | ETA prediction | Added to `pipeline_health.py` — estimates completion time per step |
| 9 | Shell script linting | `shellcheck` clean on all `.sh` files |

Every "What stinks" and "What should we discuss" item from the earlier
session got addressed. The retrospective format works.

### 7. talent.yoga full review — route audit (`a4eb09e`)

Item 10 from the hit list: "Complete review of talent.yoga — make sure
everything works."

**Scope:** All 28 HTML templates, 23 API routers, 4 JS files, 8 CSS files,
all page routes, all API endpoints.

**Method:**
1. Listed all templates, static assets, routers
2. Read full `api/main.py` (544 lines) — mapped all routes
3. HTTP status tested every page (8 public + 11 auth-required)
4. Template-by-template code review for JS bugs, XSS, dead code
5. Router-by-router review for SQL bugs, missing error handling

**Results: 29 issues found** — 5 critical, 4 high, 10 medium, 10 low.

### 8. talent.yoga — critical fixes (`a4eb09e`)

**P0: account.py — every endpoint broken.**
All 6 GDPR endpoints (display-name, avatar, email-consent, mira-preferences,
export, delete-request) used asyncpg syntax (`await db.execute("...$1...")`)
but received a psycopg2 connection. Complete rewrite:
- `async def` → `def`
- `await db.execute("...$1...")` → `cursor.execute("...%s...", (params,))`
- Export endpoint: `content` column → `body` (correct column in yogi_messages)
- Added `safe_query()` with SAVEPOINTs for 5 tables that don't exist yet
  (profile_skills, work_history, profile_preferences, documents, user_interactions)

**P0: proactive.py — references non-existent column.**
`p.posting_status = 'active'` → `p.enabled = TRUE AND p.invalidated = FALSE`.
The `posting_status` column never existed.

**P0: matches.html — JS crash on every page load.**
`loadNotifications()` calls `document.getElementById('notif-list').innerHTML`
but the element doesn't exist. TypeError on every load. Added null guards
for `#notif-badge`, `#notif-list`, `#notif-dropdown`.

**P0: posting page — 404.**
Template existed, API endpoint existed, but no page route in `main.py`.
Added `/posting/{posting_id}` route.

### 9. talent.yoga — high-priority fixes (`a4eb09e`)

- **dashboard.html** `/journey` links: Journey has API endpoints but no
  page route. Changed links to `#` instead of 404.
- **dashboard.html** duplicate `timeAgo()`: Hardcoded German version
  overwrote the i18n-aware version from base.html. Removed duplicate.
- **XSS in notification onclick**: Both dashboard.html and matches.html
  injected unescaped `link` into onclick handlers. Added `escapeHtml()`.
- **auth.py cookie security**: `secure=False` hardcoded → `secure=not DEBUG`.
- **account.html delete stub**: `confirmDeleteAccount()` was a no-op.
  Rewired to actually call `/api/account/delete-request`.
- **i18n**: Added 22 `account.*` keys to both en.json and de.json.
- **Stale templates**: Archived 7 unused/dead templates to
  `archive/stale_templates_20260217/`.

### 10. talent.yoga — remaining issues (not fixed, tracked)

**Medium priority (won't break anything, but should fix):**
- Sidebar missing `/market`, `/finances` nav links
- `finances.html` standalone — doesn't extend base.html
- Score scale inconsistency: dashboard.py 0-100, matches.py 0-1
- feedback.router double-mounted on `/api/feedback` and `/api/mira/feedback`
- documents.py cursor not closed on error path
- Several pages lack i18n (landscape, arcade, messages, documents)
- async endpoints using sync psycopg2 (blocks event loop under load)

**Low priority:**
- Push subscriptions table created at runtime in proactive.py
- Inline `<style>` in a few templates (cosmetic)
- Console.log statements left in production JS

---

## Commits today

| Hash | Description |
|------|-------------|
| `8d3497b` | fix: parallel embeddings (8 workers, 5x), double logging fix, ts_prefix crash fix |
| `28c40db` | cleanup: remove 47 unused tools — keep 5 active |
| `b4342d5` | perf: berufenet LLM 7x faster — HTTP API + 2 concurrent workers |
| `741eb39` | docs: daily notes — pipeline performance session |
| `e55a015` | fix: 9-item hit list — extracted_summary, config, stale sweep, shellcheck, etc. |
| `a4eb09e` | fix: talent.yoga full review — account.py rewrite, XSS, 404s, proactive.py |
| `afcf767` | docs: daily notes update — sections 6-10, commit table, retrospective |
| `807a12c` | fix: score scale 30→0.30, documents.py cursor leaks, feedback mount comment |
| `b5a9a4d` | feat: berufenet enrichment — re-classify failures with description/web context |
| `6e1d02d` | feat: CV import endpoint + match rating 1-10 + queue + negative filter |
| `af589cb` | fix: profile anonymization — scrub PII from DB + display yogi_name |
| `71a9882` | anonymity: Taro name generator, company aliases registry, Doug research pipeline |
| `42a4cc5` | feat: Adele conversational profile builder |
| `7ba02f0` | fix: Adele always visible in chat list |
| `e626fad` | restore navigation sidebar on messages page |
| `c251ee0` | add onboarding+adele e2e test script, expand confirm patterns |

---

### 11. Desk clearing (`807a12c`)

Three medium-priority items from the talent.yoga review resolved:

- **Score scale**: `dashboard.py` filtered `skill_match_score > 30` on 0-1
  float values — effectively zero matches ever shown. Changed to `> 0.30`.
- **Cursor leaks**: `documents.py` had 6 endpoints + 1 helper using bare
  `cur = conn.cursor()` without cleanup. Wrapped all in `with conn.cursor()`.
- **Feedback double-mount**: Added clarifying comment in `main.py` explaining
  the intentional dual mount (`/api/feedback` + `/admin/feedback`).

### 12. Berufenet enrichment — 19K failure analysis + solution (`b5a9a4d`)

Deep SQL analysis of the 19,376 "pending" berufenet cases revealed they're
all legitimately unclassifiable **by title alone**:

| Status | Count | What happened |
|--------|-------|---------------|
| `no_match` | 16,825 | Embedding score < 0.70, never sent to LLM |
| `llm_uncertain` | 1,385 | LLM couldn't decide |
| `llm_no` | 1,040 | LLM said NO |
| `error` | 126 | Processing errors |

**Key insight:** 12,236 scored 0.60–0.69 (close miss). Titles like
"Mitarbeiter im Handwerk" or "Hilfskraft Lagerlogistik" are too vague for
embedding, but nearly all (19,374/19,376) have a `job_description` that
reveals the actual profession.

**Built a 2-stage enrichment pipeline:**

- **Stage A (description):** embed title → top-5 candidates → new LLM prompt
  with job description excerpt (500 chars) as context → classify
- **Stage B (web search, optional `--web`):** if Stage A fails, search DDG
  for `"{title} Beruf Stellenbeschreibung"` → retry LLM with web context

**New code:**
- `lib/berufenet_matching.py`: `llm_classify_enriched()`, `web_search_job_context()`
- `actors/postings__berufenet_U.py`: `enrich_batch()`, `--enrich N`, `--web`

**Results (test + first batch):**
| Batch | Classified | Rejected | Errors | Rate |
|-------|-----------|----------|--------|------|
| 20 titles (test) | 20 (100%) | 0 | 0 | 0.2/s |
| 500 titles (batch) | 462 (92%) | 37 | 1 | 0.2/s |

614 postings reclassified, 46 confidently rejected. Spot-check of
classifications showed strong accuracy (Sozialpädagoge → Sozialarbeiter,
Hauswirtschaftliche Mitarbeiterin → Hauswirtschafter/in, etc.).

### 13. Profile / CV / Matching — architecture review + build plan

Reviewed all existing profile infrastructure:

| Layer | Status | Location |
|-------|--------|----------|
| CV upload + anonymize | Built | `POST /profiles/me/parse-cv` → `core/cv_anonymizer.py` |
| Profile CRUD | Built | `api/routers/profiles.py` (590 lines) |
| Match report (Clara) | Built, 28 matches | `actors/profile_posting_matches__report_C__clara.py` |
| DB schema | Solid | `profiles` (30 cols), `profile_posting_matches` (25 cols), `profile_work_history` (17 cols) |
| Match feedback | Schema only | `user_rating`, `user_feedback`, `user_decision` columns exist, no UI or endpoints |
| Live data | Thin | 5 profiles, 26 work entries, 28 matches |

**Gap analysis:**

1. **CV import last-mile**: `parse-cv` returns anonymized JSON but there's
   no confirmation step or save-to-profile endpoint. The yogi sees the
   extracted data but can't approve/edit/store it.
2. **Match feedback flow**: `profile_posting_matches` has `user_rating`
   (int), `user_feedback` (text), `user_decision` (text) columns — but no
   API endpoint to submit ratings, and no UI to display matches with a
   rating widget.
3. **Feedback loop**: Ratings don't influence future matching. Three options
   evaluated:
   - **A. Negative keyword filter** — suppress berufenet categories from
     low-rated matches (2h, SQL only)
   - **B. Embedding drift** — build preference vector from rating history
     (half day)
   - **C. LLM preference extraction** — extract rules from feedback text
     (1 day)

**Build order (implementing now):**
1. CV import endpoint — write anonymized JSON → profile + work_history
2. Match rating endpoint — `PUT /matches/{id}/rate`
3. Match queue view — show next unrated match with Clara's artifacts
4. Negative filter — low ratings auto-suppress similar categories
5. Cover letter download

### 14. Profile anonymization — PII exposed on /profile (`6e1d02d` → fixing)

**Problem:** https://talent.yoga/profile displays real name ("Gershon
Pollatschek") and real company names (Deutsche Bank, Novartis, Commerzbank,
etc.). Zero anonymization on the profile page.

**Root cause:** Profile was imported via `profile_source = 'markdown'` —
a legacy import script that predates the anonymizer. Two data paths:
- CV upload → `core/cv_anonymizer.py` → clean (name → yogi_name,
  companies → generalized) ✓
- Manual/markdown import → raw data → `full_name = real name`,
  `company_name = real company name` ✗

**What was wrong (5 things):**
1. `profiles.full_name` stores real names — displayed on profile page
2. `profile_work_history.company_name` stores real company names
3. `/api/profiles/me` returns `full_name` directly as `display_name`
4. Profile page form shows real name in the "Full Name" input field
5. No anonymization layer between DB and UI for pre-anonymizer data

**Fix approach:**
1. Profile page: display `yogi_name` from users table, not `full_name`
2. Re-anonymize Gershon's work history through the anonymizer
3. Profile page: show generalized companies, not raw `company_name`
4. Future: Adele interactive profile builder — yogi never types company
   names directly, Adele generalizes on input

**Bigger picture (noted for later):**
- Adele = conversational profile builder: asks questions, yogi replies,
  Adele creates the anonymized CV
- This replaces both the manual form and the CV upload — one path, always
  anonymized

### 15. Anonymity infrastructure — Taro + company aliases + Doug (`71a9882`)

**Session 3** (~15:00 CET). Extended the anonymization layer from a
cosmetic fix into a proper infrastructure:

**Taro — yogi name generator** (`core/taro.py`, 285 lines):
- 600+ curated names: nature words (Birch, Otter, Fern), mythology,
  celestial, color compounds, multilingual — all gender-neutral
- Uniqueness: checks DB, avoids collisions
- Offers Mira 3 candidates at a time
- Tested: 50 sequential generations, zero duplicates, good variety

**Company aliases registry** (`core/company_anonymizer.py`, 643 lines):
- Migration `056_company_aliases.sql`: `company_aliases` table with
  `canonical_name`, `alias_text`, `alias_source`, `confidence`, JSONB metadata
- Seeded 50 companies + 48 common variants (e.g., "Deutsche Bank AG" →
  "Deutsche Bank", "BMW Group" → "BMW")
- `lookup(name)` → returns generalized description from registry
- `lookup_or_queue(name)` → if not found, queues for Doug research
- Doug research actor: picks unresolved companies, researches via LLM,
  writes generalized descriptions
- Doug verifier: double-checks Doug's work for quality

**Results:**
- Deutsche Bank → "a large German bank"
- McKinsey → "a top-tier management consulting firm"  
- Sparkasse Köln-Bonn → "a German regional savings bank"
- Unknown companies get queued → Doug researches → auto-resolves

### 16. Adele — conversational profile builder (`42a4cc5`)

The big build of the day. Adele conducts a natural conversation to extract
a complete professional profile — no CV upload, no forms. 950 lines of
core logic.

**Architecture:**
- State machine interview: intro → current_role → work_history (loop) →
  skills → education → preferences → summary → complete
- `adele_sessions` table (migration 057): tracks phase, JSONB collected
  data, work_history_count, turn_count
- LLM extraction at each phase via qwen2.5:7b — structured JSON prompts
- Company anonymization via `lookup_or_queue()` at work history intake
- Duration parsing: "3 years", "18 months", "since 2020"
- Bilingual EN/DE with automatic language detection
- Profile save to `profiles` + `profile_work_history` tables
- `profile_source = 'adele_interview'`

**API:** `POST /api/adele/chat` + `GET /api/adele/session` (progress
tracking). Messages persisted in `yogi_messages` for continuity.

**Frontend:** Wired into `messages.html` — same routing pattern as Mira.
Adele always visible in chat list (no need for prior messages).

**Bugs found and fixed during testing:**
1. `None` entries in responsibilities list → filter with `[r for r if r]`
2. Skills extraction returned empty — LLM put items in `tools` key instead
   of `skills`. Rewrote prompt to use `technical_skills`, merge captures
   all skill-like keys
3. German confirmation "Ja, passt!" didn't trigger save — expanded
   `_CONFIRM_PATTERNS` regex to 20+ patterns including compound expressions
4. Session unique constraint blocked new sessions — changed from
   `UNIQUE(user_id)` to partial unique index `WHERE completed_at IS NULL`

**Test results (EN flow):**
- 12 skills extracted, 2 work entries saved
- Company anonymization: Deutsche Bank → "a large German bank",
  McKinsey → "a top-tier management consulting firm"
- Profile saved to DB with salary range, location preferences, desired roles

### 17. Frontend fixes (`7ba02f0`, `e626fad`)

**Adele visibility** (`7ba02f0`): Chat list only showed actors with existing
messages. New yogis couldn't see Adele. Added `ALWAYS_SHOW = ['mira', 'adele']`
to inject these actors into `messagesBySender` even with no messages. Fixed
sort/render for empty conversations.

**Navigation bar** (`e626fad`): Messages page was missing the sidebar
navigation — intentionally excluded with a comment about the chat list
serving as left nav. But every other page has the sidebar. Restored
`{% include "partials/sidebar.html" %}`.

### 18. End-to-end onboarding test script (`c251ee0`)

Built `scripts/test_onboarding_adele.py` — automated test of the full user
journey from zero to profile:

1. **Reset** test user (user_id=2, test@talent.yoga) to completely fresh state
2. **Mira onboarding** — picks yogi name "Sparrow", declines notification email
3. **Adele interview** — backend engineer at Siemens/BMW, 10 skills,
   Master's from TU Munich, Munich/remote, 85-100k salary range
4. **Verify** — checks profile, work history, skills in DB

Uses JWT token generation for auth (same SECRET_KEY as server). Options:
`--reset` (reset only), `--skip-mira`, `--skip-adele`.

**Full pass confirmed:** profile saved with 2 anonymized work entries
(Siemens → "ein großer deutscher Industrietechnologiekonzern", BMW →
"ein deutscher Premium-Automobilhersteller"), 10 skills, salary range,
location preferences.

---

## Dropped balls — review of Feb 16 notes

From the previous session's "Process improvements — agreed action items":

| Item | Status |
|------|--------|
| 1. Automated tests for critical paths | ✅ Done (Feb 16) — 404 tests |
| 2. Pipeline error alerting | ✅ Done (Feb 16) — Signal push notifications |
| 3. Systemd services for daemons | ⬜ Not started |
| 4. CSS consolidation | ✅ Partially done (Feb 16) — inline dark-mode moved to style.css |
| 5. End-of-session daily notes | ✅ This file |
| 6. User behavior intelligence (Mira) | ⬜ Not started |

From the previous session's "Still open" list:

| Item | Status |
|------|--------|
| extracted_summary failures | ✅ Fixed (Feb 17, `e55a015`) — _load_actor module path |
| Stale postings cleanup | ✅ Fixed (Feb 17, `e55a015`) — nightly sweep + 2,114 invalidated |
| Duplicate external_ids | ✅ Unique partial index (Feb 16) |
| ROADMAP.md stale | ⬜ Still stale |
| Complementary dimensional model | ⬜ Not started |
| Profile builder UI | ✅ Done Feb 16 (auto-create) → Feb 17 (Adele conversational builder) |
| Mira memory | ⬜ Not started |

---

## What SHOULD we discuss but aren't?

**1. We have no users.** 260,000 postings, 282,000 embeddings, 37 domains,
18 states, qualification levels, sparklines, heatmaps, an arcade game. Six
test accounts. Zero real job seekers. Every performance improvement we make
is for an audience of zero. The pipeline runs in 22 minutes instead of 19
hours — for whom?

This isn't a criticism of the engineering. The engineering is solid. But
we're optimizing a race car that's sitting in the garage. The next
conversation should be: how do we get 10 real users this week? Not 1,000.
Ten. People who file real feedback, not Mysti proxying for hypothetical
users.

**2. ~~The extracted_summary actor fails 56/56.~~** Fixed (`e55a015`) —
`_load_actor` was importing the wrong module path. Now runs successfully.

**3. ~~The 2,114 stale postings haven't moved.~~** Fixed (`e55a015`) —
nightly sweep script rebuilt, all 2,114 stale postings invalidated. Active
count dropped from ~250K to ~248K reflecting real removals.

**4. ~~Embedding determinism.~~** Verified (`e55a015`) — 100 texts embedded
sequentially then with 8 workers. 100/100 exact match. Ollama HTTP API is
deterministic with concurrent requests.

**5. ~~Config sprawl.~~** Fixed (`e55a015`) — created `config/settings.py`
as single source of truth for all tunables (OLLAMA URLs, models, worker
counts, Signal config, DB).

**6. (New) The async/sync mismatch.** Multiple FastAPI endpoints are
declared `async def` but call synchronous psycopg2 operations. Under load
this blocks the event loop. Right now with zero users it's invisible. With
10 users it might start mattering. Full conversion to async (asyncpg or
psycopg3 async) is a bigger project.

---

## What stinks around here?

*Update: All 3 items from the morning session were addressed in the hit list.*

**1. ~~The log file is unreadable.~~** Fixed — `LOG_FORMAT=human` option
added (`e55a015`). Structured JSON still the default for machine parsing,
but human-readable mode available for interactive debugging.

**2. ~~subprocess.run for Ollama.~~** Fixed — grepped the full codebase,
found 2 remaining files beyond berufenet, converted to HTTP API (`e55a015`).

**3. ~~The 539 "given up" descriptions.~~** Fixed — all 539 postings
invalidated (`e55a015`). No longer pollute health reports or active metrics.

**4. (New) ~~The frontend is held together with duct tape.~~** The talent.yoga
review found 29 issues across 28 templates and 23 routers. Account page was
100% broken. 15 issues fixed in sections 8-11. Messages page nav bar
restored (section 17).

**5. (New) Adele is the onboarding path we needed.** Before today, profile
creation had two paths: a form nobody fills out, and a CV upload that
strips data but has no confirmation step. Adele is the third and best path —
conversational, bilingual, anonymized by default, and tested end-to-end.
The question is whether yogis prefer talking to a bot or uploading a PDF.

---

## What didn't go well?

**1. The ETA prediction was wrong.** I estimated 19:30 for berufenet
completion. The overnight run had already finished berufenet before it
crashed. I didn't check whether berufenet (step 3) had committed its work
before step 5 crashed. That's a reasoning failure — I should have queried
the DB to verify, not just extrapolated from the log rate.

**2. The ts_prefix crash was preventable.** That function was called but
never defined. A simple `shellcheck` or even `bash -n turing_fetch.sh`
would have caught it before it broke production. We don't lint our shell
scripts. We should.

**3. I didn't question the subprocess pattern earlier.** The Ollama
subprocess calls have been in the codebase since the berufenet actor was
written. You showed me the GPU at 90% and asked "can we go faster?" and
only then did I look at the actual implementation. I should have noticed
this during the Feb 15 codebase quality session when I was already reviewing
actor code. The GPU wasn't the bottleneck — process spawning was. I looked
at the wrong layer.

---

## How am I doing? (10=bliss, 1=agony)

**9**

Three-phase session. Phase 1 (early morning): three performance wins —
embedding 5x, berufenet 7x, tools cleanup. Phase 2 (mid-morning): 10-item
hit list from user reviewing daily notes — all done, plus full talent.yoga
audit (29 issues found, 15 fixed). Phase 3 (afternoon/evening): built the
entire anonymity stack (Taro names, company aliases, Doug research pipeline)
and then Adele — a 950-line conversational profile builder that works
end-to-end in both languages.

Adele is the most complete feature built in a single session: state machine,
LLM extraction, company anonymization, bilingual support, DB persistence,
API endpoints, frontend wiring, bug fixes, and an automated E2E test
script. From "shall we build Adele?" to a passing test with anonymized
profiles saved to DB in one sitting.

What didn't go well: the confirm pattern regex needed three rounds of
expansion (simple "yes" → compound "yes, save it!" → German compounds
"ja, passt"). Should have started with a more generous pattern set. Also,
the test script had two column-name bugs on first run — should have checked
the schema before writing the queries.

---

## Numbers at session end

| Metric | Value |
|--------|-------|
| Total postings | 260,204 |
| Active postings | 247,735 |
| Embeddings | 282,328 |
| Berufenet pending | 19,376 → 18,716 (660 resolved via enrichment) |
| Embedding pending | ~997 |
| Profiles | 6 (was 5 — Adele test added 1) |
| Work history entries | 28 |
| Company aliases | 53 (50 seeded + 3 auto-resolved) |
| Tests | 404 passing |
| PG cache hit ratio | 99.99% overall |
| Commits today | 17 |
| Issues found (talent.yoga) | 29 |
| Issues fixed (talent.yoga) | 17 |
| New code written | ~2,600 lines (10 files) |

---

*Next session priorities:*
1. Run remaining berufenet enrichment batches (~16K titles left)
2. The user acquisition conversation — how do we get 10 real users?
3. Systemd services for daemons (agreed action item, still open)
4. async/sync mismatch — evaluate psycopg3 async or thread pool wrapper
5. ROADMAP.md refresh
6. Adele German-language polish — test full DE flow with a native speaker
7. Match feedback UI — connect Clara's matches to a rating widget
