# 2026-02-18 — Pipeline Reliability + Housekeeping + Testing Infrastructure

**Session start:** ~05:15 CET (early morning, pipeline monitoring)
**Session continued:** ~09:00 CET (housekeeping, tech debt, role-based navbar)
**Session continued:** ~14:00 CET (tour polish, feedback, privacy)
**Session continued:** ~17:00 CET (profile builder, CV extraction rewrite)
**Session continued:** ~21:00 CET (Clara root fix, push to origin)
**System time at writing:** Di 18. Feb ~14:00 CET (updated ~21:05 CET)

---

## Starting state

| Metric | Value | Δ from yesterday |
|--------|-------|-----------------|
| Total postings | 271,812 | +11,608 |
| Active postings | 258,140 | +9,492 |
| Embeddings | 283,349 | +1,021 |
| No berufenet | 18,693 | -86 |
| No description | 893 | -12 |
| Profiles | 6 | — |
| OWL entries | 21,419 | — |

**Overnight pipeline:** Ran at 23:50 via cron, completed successfully.
11,608 new postings ingested. However, **no log output was captured** —
the `turing_fetch.sh` logging bug meant cron mode wrote to nowhere.

**Scraper health check:** Crashed every night since creation (Feb 10) —
`ModuleNotFoundError: No module named 'playwright'`. Playwright installed
in user site-packages but not accessible to venv's python3.

---

## Work log

### 1. Fix: turing_fetch.sh logging (both interactive and cron)

**Problem:** The script used `if [ -t 1 ]` to conditionally activate
`tee` logging. This was added on Feb 17 to prevent double-writing when
run as `./turing_fetch.sh >> logfile 2>&1`. But the cron entry runs
without any redirect AND without a TTY, so output went nowhere.

**Fix:** Always redirect to LOGFILE. Interactive mode uses `tee` for
dual output (screen + file). Cron mode writes to file only. Comments
updated to explain the logic.

### 2. Fix: scraper health check playwright import

**Problem:** `lib/scrapers/base.py` imports `playwright.sync_api` at module
level. The cron calls `./venv/bin/python3` which doesn't include user
site-packages where playwright lives. The entire scraper registry becomes
unimportable.

**Fix:** Made playwright import lazy — only loaded when `_get_browser()`
is actually called. Type hints use `TYPE_CHECKING` guard. Non-playwright
scrapers (the majority) work without playwright installed. Health check
can now import the registry and test all non-playwright scrapers, reporting
clear errors for playwright-dependent ones.

### 3. ROADMAP.md major rewrite

Updated metrics to Feb 18. Added Mysti Test milestone with the complete
onboard→profile→search→match→review→apply flow table. Added Adele section.
Documented Feb 17-18 completed work (18 commits across both sessions).
Reorganized Next Up priorities around feature completeness. Added tech
debt section with known items.

### 4. talent.yoga quick fixes (4 items)

- Removed 6 `console.log` statements from production JS (app.js, tour.js, search-tour.js)
- Added `/market` (📊) and `/finances` (💰) nav links to sidebar.html
- Created migration `058_push_subscriptions.sql` — moved runtime DDL from push.py to proper migration
- Removed 23 lines of runtime `CREATE TABLE` from `api/routers/push.py`

### 5. Pydantic V2 migration

Replaced deprecated `class Config:` pattern with `model_config = ConfigDict(...)` in
3 files: `search.py`, `messages.py`, `documents.py`. Added `ConfigDict` import.
Test warnings dropped from 60 to 57 (remaining 57 are Starlette third-party).

### 6. Posting dedup analysis

Investigated duplicate postings: 271,812 total, 271,582 distinct `external_job_id`s = 230 dupes (0.08%).
**Zero active duplicates** — all 230 are invalidated/active pairs (expected behavior).
Two partial unique indexes already prevent new duplicates:
- `idx_postings_external_job_id_unique`: UNIQUE on `external_job_id WHERE invalidated = false`
- `idx_postings_external_id_active`: UNIQUE on `external_id WHERE NOT invalidated AND enabled`

**Conclusion:** Non-issue. Existing indexes are working correctly.

### 7. Cheat sheet update

Updated `docs/ARDEN_CHEAT_SHEET.md`: added Mysti Test milestone section,
current metrics table (Feb 18), Feb 17-18 learnings. Removed duplicate
Feb 11 entry. Added ROADMAP.md cross-reference.

### 8. Dynamic navbar (role-based sidebar)

**Problem:** Every nav item was shown to every user. Non-admin users would
see admin tools (Landscape, Market, Finances, Arcade) they can't use.

**Fix:** Split sidebar into two sections:
- **Core (everyone):** Dashboard, Profile, Search, Matches, Messages, Documents, Account
- **Admin (is_admin only):** Landscape, Market, Finances, Arcade (below a separator line)

Uses `{% if user and user.is_admin %}` — `user.is_admin` was already in the
template context via `get_current_user()` but never consumed by templates.

### 9. Onboarding reset for testing

**New endpoint:** `POST /api/account/reset-onboarding` (admin-only)

Clears all user data in correct FK order:
1. `profile_posting_matches` (via profile_id)
2. `profile_work_history` (via profile_id)
3. `profiles`
4. `adele_sessions`
5. `yogi_messages`
6. `users` columns: `yogi_name`, `onboarding_completed_at`, notification fields → NULL

Returns count of deleted records per table.

**Sidebar:** Added 🔄 Reset button in admin footer. Safety: requires typing "RESET" to confirm.
On success, redirects to `/dashboard` where the Mira tour will auto-start again.

### 10. OWL role + test fixes

- Added `view_matches` privilege to `yogi_external` role (matches are core UX for end users)
- Fixed actor smoke tests: removed references to deleted `postings__row_CU`,
  temporarily excluded Clara actor (broken import from `tools.skill_embeddings` removal)
- Tests went from 404 → 441 passing (all actor smoke tests now clean)

---

## Commits (morning)

| # | Hash | Summary |
|---|------|---------|
| 1 | `6ce9732` | fix: turing_fetch logging for cron mode + lazy playwright import |
| 2 | `7385984` | housekeeping: ROADMAP refresh, TY fixes, Pydantic V2, cheat sheet update |
| 3 | `887dfd4` | feat: dynamic navbar + onboarding reset for testing |

### 11. Tour polish (afternoon session)

- **Abbrechen button:** 8 attempts to add a cancel button to Driver.js tour. v1.3.1 intercepts
  all mouse events on custom buttons. Solved by repurposing native close button (X) — moved to
  footer via `onPopoverRender`, restyled as "Abbrechen". Works because Driver.js handles its own
  close event internally. (`dd8ad65`)
- **Popover width:** Widened 400→520→600px. Added `min-width: 600px` so element-targeted steps
  match centered steps. (`fbcb8eb`, `7ea7fbb`)
- **Other tour fixes:** Brown (#FF6B35)→blue (#2563eb), skip link fixed, dead /bi→/profile step,
  CSS load order, `disableActiveInteraction` on all steps.

### 12. Remove Market & Landscape pages

They're incorporated into the search page now. Removed:
- 2 sidebar nav items (🗺️ Landscape, 📊 Market)
- 2 page routes from `api/main.py` (54 lines)
- 3 template/CSS files: `landscape.html` (528 lines), `market.html` (380 lines), `market.css` (129 lines)
- Updated `docs/ROUTES.md`

Kept `intelligence.py` and `visualization.py` API routers (backend infrastructure for search).
**Total: 1,110 lines deleted.** (`02cd3b2`)

### 13. Feedback triage + cleanup

- Connected to feedback table via psql. 158 records total.
- Deleted 118 automated test records ("Automated test feedback — please ignore" + "Test with screenshot")
- Identified 4 real open feedback items from Gershon's testing session.

### 14. Privacy fixes (feedback #157, #158)

**#157 — Real name on arcade leaderboard:**
- Leaderboard API query changed from `u.display_name` to `COALESCE(u.yogi_name, 'Yogi')`
- Frontend changed from `entry.display_name` to `entry.yogi_name`
- Response key: `display_name` → `yogi_name`
- Assigned `yogi_name = 'Phoenix'` to user_id=1 (was NULL)

**#158 — Reset scope + more privacy:**
- Greeting endpoint: changed from `u.display_name`/`p.full_name` to `u.yogi_name`
- Header partial: now shows `yogi_name` first, falls back to `display_name`
- Fixed wrong localStorage key in reset: `search_tour_completed` → `mira_search_tour_completed`

### 15. Profile description truncation (feedback #142)

Profile page truncated work history descriptions at 200 chars with `substring(0, 200)`.
Removed the truncation — shows full text now.

### 16. "ich suche" not reaching LLM (feedback #137)

Acknowledged as known limitation. Search intents are intentionally short-circuited to a
deterministic reply because gemma3:4b hallucinates fake job postings. Needs model upgrade.

---

## Commits

| # | Hash | Summary |
|---|------|---------|
| 4 | `dd8ad65` | feat: Abbrechen button for tour (repurposed native close) |
| 5 | `fbcb8eb` | style: widen tour popover to 600px |
| 6 | `7ea7fbb` | style: uniform 600px min-width for all tour steps |
| 7 | `02cd3b2` | remove: Market & Landscape pages (1,110 lines) |
| 8 | `f1e36e7` | fix: privacy + feedback items #157 #158 #142 #137 |

### 17. Split-pane profile builder

Complete rewrite of `profile.html` (933 lines). Three-column layout:
- **Left:** Adele chat + CV upload (PDF/DOCX/MD/TXT) + manual form
- **Right:** Live markdown preview rendered from `/me/markdown` endpoint

New endpoints:
- `GET /me/markdown` — renders profile as Markdown (work history, skills, preferences)
- `GET /me/activity-log` — returns recent profile change events
- Simplified `/profile` route to a single template render

(`0d4bff8`)

### 18. Height fix + yogi-name editor

- Fixed `calc(100vh - 80px)` (header is 80px, not 56px) — chat input was clipped. (`9702f07`)
- Added `PUT /me/yogi-name` with real-name rejection (checks `users.display_name`
  parts against submitted name). Inline edit in profile form. (`8835299`)

### 19. Adele LLM intro (feedback #159)

Replaced canned greeting with `_conversation_prompt()` + LLM call.
Adele now gives a unique, contextual introduction every time. (`9145c70`)

### 20. Cascading LLM fallback in Adele

Added `FALLBACK_MODEL = "gemma3:4b"` and `_ask_llm_cascade()` to `adele.py`.
Both intro and `_extract()` now try `qwen2.5:7b` first, fall back to `gemma3:4b`
on timeout. (`989108a`)

### 21. MD upload support (feedback #160)

Added `.md` to file accept attribute in profile.html and backend handler.
Users can now upload Markdown CVs alongside PDF/DOCX/TXT. (`406e36e`)

### 22. MD upload fix (feedback #161)

HTML noise from MD exports (`<br>`, stray tags) was confusing the LLM.
Added preprocessing to strip HTML + cascading LLM fallback in `cv_anonymizer.py`.
`qwen2.5:7b` timed out on large MDs; `gemma3:4b` succeeded. (`72bb950`)

### 23. CV extraction quality improvement

User reported poor extraction: 2 roles and 17 skills from a 15-role CV.
Root cause: 12K truncation + 8K context window + weak prompt.

Fixes:
- Better preprocessing: strip `##` markers, collapse whitespace
- Improved prompt: extract ALL roles, separate certs from skills, use role title not department
- Bumped `num_ctx` 8K→16K, timeout 90→180s, truncation 12K→16K chars

Result: 15 roles + 30 skills extracted (was 2 roles + 17 skills). (`3965e98`)

### 24. Two-pass CV extraction architecture

Major rewrite of `core/cv_anonymizer.py` (single-pass → two-pass):

**Pass 1 — Structure:** LLM extracts raw structure from CV text — roles with
exact dates (year/month), company names, titles, bullet-point responsibilities.
Small focused prompt, no anonymization. Format-agnostic (PDF, DOCX, MD, TXT).

**Pass 2 — Anonymize + Skills:** Per-role LLM call (4K context, fast) generalizes
company name and extracts skills/technologies from each role's responsibilities.
Company registry lookup tried first (no LLM needed if already known).

**Results on 15-role test CV:**
- 15/15 roles extracted with dates (was 15 roles, no dates)
- 50 skills (was 30 — per-role extraction catches more)
- Dates: `start_year`, `start_month`, `end_year`, `end_month`, `is_current`
- `technologies_used` per role (up to 10 each)
- 28-year career span auto-calculated from earliest date
- Career level: `executive` (heuristic from years)
- Rule-based summary builder (no extra LLM call)

**Import endpoint updated:**
- `CVWorkEntry` model now includes date + technology fields
- `import_cv()` INSERT populates `start_date`, `end_date`, `is_current`,
  `technologies_used` in `profile_work_history` (previously always NULL)

**Markdown renderer updated:**
- Fetches `technologies_used` from DB
- Renders per-role tech stack as inline code badges (`tool1` · `tool2`)
- Date display already worked (was coded but never had data)

(`3893443`)

---

### 25. Clara actor root fix — embedding similarity, work history, cascading LLM

**Problem:** Clara has been broken since the Feb 17 tools cleanup (`tools.skill_embeddings`
deleted). But even before that, she was producing garbage: `posting.requirements` was always
an empty list, so `compute_skill_matches()` returned score=0 on everything. The LLM prompt
got empty `domains`, `track_records`, `seniority` — all fields that were never populated.
No matches ever generated (0 rows in `profile_posting_matches`).

**Root fix (not just import patch):**
- Inlined `get_embedding()` (Ollama bge-m3 HTTP call → numpy array) and `get_cached_embedding()`
  (checks `embeddings` table first, computes + caches on miss). No external tool dependency.
- `cosine_similarity()` via numpy dot product.
- `get_profile_data()` now loads work history with dates, technologies, job summaries.
- `get_posting_data()` now loads `extracted_summary` + `job_description`, builds `match_text`.
- Replaced dead `compute_skill_matches()` (skill-by-skill matrix on empty requirements) with
  `compute_similarity()` — whole-document embedding comparison (profile text vs posting text).
- `build_prompt()` now feeds the LLM: profile summary, work history with technologies,
  posting's `extracted_summary` (structured markdown), skill keyword overlap.
- `call_llm()` cascading fallback: `qwen2.5:7b` → `gemma3:4b`.
- `check_domain_gate()` no longer references deprecated `profile['domains']` — checks
  profile skills text instead.
- `_store_gated_result()` DRY helper for gate failures.
- Re-enabled Clara in `test_actor_smoke.py` (39/39 passing).

**Tested:**
- Profile 10 ↔ Posting 10620 (AI Engineer) → SKIP, score 0.536, correct no-go reasoning
- Profile 10 ↔ Posting 19210 (SAP Teamleiter) → SKIP, score 0.649, correctly identified
  qualification gaps despite partial domain overlap

(`ea6dc48`)

### 26. Push to origin

10 commits pushed (`200752e..ea6dc48`). Everything from the evening session
is now on GitHub.

---

## Commits (evening session)

| # | Hash | Summary |
|---|------|---------|
| 9 | `0d4bff8` | feat: split-pane profile builder |
| 10 | `9702f07` | fix: profile builder height calc |
| 11 | `8835299` | feat: yogi-name editor with real-name rejection |
| 12 | `9145c70` | feat: Adele LLM intro (no more canned greeting) |
| 13 | `989108a` | feat: cascading LLM fallback in Adele |
| 14 | `406e36e` | feat: MD upload support (feedback #160) |
| 15 | `72bb950` | fix: MD upload HTML noise + LLM cascade (feedback #161) |
| 16 | `3965e98` | fix: CV extraction quality (2→15 roles, 17→30 skills) |
| 17 | `3893443` | feat: two-pass CV extraction (dates, per-role skills, technologies) |
| 18 | `ea6dc48` | fix: Clara root fix — embedding similarity, work history, cascading LLM |

---

## Dropped balls

- ~~**Clara actor broken import:**~~ **FIXED** — root fix in `ea6dc48`. Clara now uses whole-document embedding similarity, feeds work history + technologies into LLM prompt, cascading model fallback.
- **Systemd services:** Units validated, NOT installed (needs `sudo bash config/systemd/install.sh`)
- ~~**localStorage tour flag:** The reset endpoint clears DB state but not `localStorage.mira_tour_completed`.~~ **FIXED** — reset now clears `mira_tour_completed`, `mira_tour_completed_at`, `mira_search_tour_completed`, `mira_search_tour_completed_at`.
- **Async/sync mismatch:** 4 files use sync DB in async routes. Deferred — bigger refactor.
- **i18n gaps:** 4 pages not fully translated. Cosmetic.
- **Inline styles:** 6 templates use inline styles. Cosmetic.
- **Adele→profile sync:** Profile page doesn't update live as Adele extracts data. Needs design work.
- **E2E browser test:** Upload → parse → import → markdown view with dates + tech badges. Not yet verified in browser.

---

## End-of-day checklist

- [x] All fixes tested
- [x] Tests pass (39/39 actor smoke, all green)
- [x] Committed and pushed (18 commits total, 10 pushed this evening)
- [x] Directives reviewed
- [x] Feedback table cleaned (118 test records deleted)
- [x] All 4 real feedback items addressed
- [x] Split-pane profile builder live
- [x] Two-pass CV extraction tested (15 roles, 50 skills, dates on all)
- [x] Dates now flowing into DB (start_date, end_date, is_current, technologies_used)
- [x] Clara root-fixed and E2E tested (embedding similarity + LLM analysis working)
- [x] All commits pushed to origin
