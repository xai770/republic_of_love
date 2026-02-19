# 2026-02-19 — Morning Review + Pipeline Health

**Session start:** ~05:06 CET
**System time at writing:** Do 19. Feb ~05:06 CET

---

## Starting state

| Metric | Value | Δ from yesterday |
|--------|-------|-----------------|
| Total postings | 287,596 | +15,784 |
| Active postings | 274,564 | +16,424 |
| Embeddings | 291,972 | +8,623 |
| With summary | 7,567 | +2,836 |
| No berufenet | 19,018 | +325 |
| No description | 1,112 | +219 |
| Profiles | 6 | — |
| Matches | 2 | +2 (Clara test runs) |
| OWL entries | 126,103 | +9,726 |

---

## Overnight pipeline analysis (23:50→04:43, 293 min)

All 5 stages green. No crashes. Logging captured properly.

| Stage | Result | Duration | Notes |
|-------|--------|----------|-------|
| AA fetch | ✅ 15,784 new | 3.4 min | Clean |
| DB fetch | ✅ 4,249 jobs | 12.5 min | Clean |
| Berufenet classification | ✅ | 211.6 min | Bulk of runtime |
| Domain cascade | ✅ | 17.0 min | |
| Qualification backfill | ✅ | <1s | |
| Enrichment daemon | ✅ | 46.5 min | |
| job_description_backfill | ✅ 15,434 ok / 1,167 fail | 24.3 min | **74 VPN rotations**, 7% fail rate |
| extracted_summary | ✅ 74/74 | 12.7 min | LLM @ 0.1/sec (local Ollama) |
| external_partner_scrape | ✅ 0/12 | 11.6s | 12 skipped (no work found) |
| domain_gate_classifier | ✅ 283/283 | 0.4s | |
| Description retry | ✅ 70/187 resolved (37%) | 1.8 min | |
| Demand snapshot | ✅ 11,385 rows | 1.0s | |
| Profession similarity | ✅ 9,255 pairs | 6.7s | 644/929 professions with embeddings |
| Health report | ✅ Sent to 3 users | — | |

### What went well
- **Pipeline reliability:** 4th consecutive clean nightly run. No crashes, no hangs.
- **Logging:** `turing_fetch.log` captured everything (fix from Feb 18 working).
- **VPN rotation:** 74 rotations during description backfill, streak never exceeded 3/5. Resilient.
- **Summary extraction:** 74/74 @ 100% success — LLM pipeline is solid.
- **Description retry:** 37% resolve rate on second pass — the retry strategy is paying off.

### What needs attention
- **13,214 embeddings pending:** That's 30 min of work per the health report ETA. This backlog is growing (was ~8K yesterday). The embedding actor runs at ~0.14s/ea but there's no catch-up mechanism — new postings arrive faster than embeddings complete.
- **1,167 description failures (7%):** These are AA postings where the Arbeitsagentur detail API returned errors. Should we retry these separately, or accept the ~7% fail rate?
- **968 missing descriptions (retryable):** The retry stage only resolved 70/187. 117 stubbornly fail. We need to decide: retry harder, or mark them as permanently unavailable.
- **5 duplicate external_ids:** Data quality issue. Low priority but indicates the dedup logic has edge cases.
- **Berufenet classification: 211 minutes.** This is >70% of pipeline runtime. It's the bottleneck. Could we batch-classify or cache more aggressively?
- **extracted_summary at 0.1/sec:** Only 74 summaries generated overnight. At this rate, clearing the backlog of ~280K unsummarized postings would take... 32 days of continuous LLM. This is fine as incremental enrichment but won't scale to full coverage.

---

## Carried over from Feb 18

### Open dropped balls
- **Systemd services:** Units validated, NOT installed. Needs `sudo bash config/systemd/install.sh`. FastAPI + BI currently run via @reboot cron — one crash = manual restart.
- **Async/sync mismatch:** 4 files use sync `psycopg2` in async FastAPI routes. Blocks the event loop under load. Tech debt.
- **i18n gaps:** 4 pages not fully translated (landscape, arcade, messages, documents). Cosmetic.
- **Inline styles:** 6 templates use inline styles instead of CSS. Cosmetic.
- **Adele→profile sync:** Profile page doesn't live-update as Adele extracts data. Needs websocket or polling design.
- **E2E browser test:** Upload → parse → import → markdown view with dates + tech badges. Not yet verified in browser.

### ROADMAP blockers for Mysti test
| Step | Status | What's needed |
|------|--------|---------------|
| 3. Profile (CV upload) | 🔧 Partial | Upload works, no confirm/edit/save step |
| 4. Search | 🔧 Partial | UI exists, needs refinement |
| 6. Match review | ⬜ Missing | No UI to browse matches + rate them |
| 7. Apply action | ⬜ Missing | No "apply" or "save" action on postings |

---

## Work log

### 1. Embedding backlog root cause + fix
**Problem:** 13,214 embeddings pending and growing nightly. Embedding actor ran *before* description backfill, so newly fetched descriptions never got embedded until the next night.

**Root cause:** `task_types.priority` ordering: embedding_generator (30) ran first, job_description_backfill (0) ran last. Daemon executes `ORDER BY priority DESC`.

**Fix:** SQL priority swap:
```sql
UPDATE task_types SET priority = 60 WHERE task_type_name = 'job_description_backfill';
UPDATE task_types SET priority = 50 WHERE task_type_name = 'extracted_summary';
```

New order: descriptions (60) → summaries (50) → embeddings (30). Ran catch-up `turing_fetch.sh` to verify.

**Result:** 13,214 → **2** pending embeddings. 13,827 processed, 0 failed, 811.6s.

### 2. Description failure analysis
1,167 failures from overnight job_description_backfill:
- 403 rate limited: **434** (37%) — transient, VPN rotation handles
- Request timeout: **407** (35%) — transient
- No description in page: **156** (13%) — transient (verified: page has content when fetched again)
- Job removed 404: **67** (6%) — legitimate removals
- Connection errors: **103** (9%) — transient

**Verdict:** 94% retryable, 6% legitimate. The 7% fail rate is expected given 74 VPN rotations. Step 5 retry recovers ~37%. No action needed.

### 3. Berufenet parallelization analysis
211 min total (70% of pipeline):
- Phase 1 (OWL lookup): 18 min — sequential DB queries, 2,676/12,196 classified
- Phase 2 (embed+LLM): **160 min** — bottleneck, `LLM_WORKERS=2`, ~1 title/sec
- Phase 3 (auto-triage): 33 min — LLM re-evaluation

**Three levers identified:** (a) `LLM_WORKERS=4` → halve Phase 2, (b) increase Phase 2 batch 500→2000, (c) batch OWL lookup SQL. Combined: 211→~100 min.

**Implemented** (commit `9ded8f5`):
- `config/settings.py`: LLM_WORKERS default 2→4
- `scripts/turing_fetch.sh`: PHASE2_BATCH 500→2000
- `actors/postings__berufenet_U.py`: new `owl_lookup_batch()` (single SQL round-trip via `ANY(%s)` array), extracted `_resolve_owl_rows()`, Phase 1 loop rewritten to pre-clean all titles and call `owl_lookup_batch()` once

### 4. Extracted summary scope verified
Work query correctly targets `WHERE source = 'deutsche_bank'` only. 3,318 legacy AA summaries exist (from Feb 13 before scope was narrowed) — harmless, no action needed.

### 5. Fixed broken test (white elephant A)
`tests/test_onboarding.py` imported `_validate_and_normalize` which was removed in the Feb 18 two-pass CV rewrite. Removed the import and `TestValidateAndNormalize` class (5 tests). Validation logic is now inline in `extract_and_anonymize`.

**Tests:** 438 passed, 0 errors (was 388 collected + 1 error).

### 6. Cheat sheet updated
Added to `docs/DEVELOPMENT_CHEAT_SHEET.md`:
- "Pipeline Change Verification Pattern" — always run catch-up after config changes
- "Daemon Actor Execution Order" — current priority table with data dependency chain

### 7. wave_runner removal (commit `9ded8f5`)
Removed the 67-file ghost ship:
- `core/wave_runner/` (61 files, 672K) → `archive/dead_wave_runner_20260219/`
- 7 dead scripts → same archive (wave_runner_daemon, wf3006_runner, old turing_daemon, run_workflow_{3001,3002,3004,1125})
- `core/queue_worker.py` and `core/workflow_guard.py` — dead, moved to archive
- Updated `core/__init__.py` and `scripts/health_check.py` to remove wave_runner refs
- Verified: zero live wave_runner references (grep confirms)

### 8. Pydantic V2 audit
Already on v2.11.5. Searched for V1 patterns (`class Config:`, `orm_mode`, `@validator`, `.dict()`) — none found. Nothing to do.

### 9. systemd install
Service files validated and ready in `config/systemd/`. Needs `sudo bash config/systemd/install.sh`. Deferred — requires interactive sudo password.

---

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `84415eb` | embedding backlog fix + broken test fix + cheat sheet |
| 2 | `9ded8f5` | berufenet parallelization + wave_runner removal |
| 3 | `cb318a3` | daily note update |
| 4 | `50f8acc` | profile builder: form with work/education/projects, i18n, full-pane layout |
| 5 | `34a1a19` | taro: layered yogi name protection (A+B+C+D) |

---

## Afternoon work

### 10. Profile builder overhaul (feedback #166 + #167)
User submitted feedback requesting: (1) form for projects & studies (not just work), (2) i18n not working, (3) form needs full left pane.

**DB:** Added `entry_type` column to `profile_work_history` (work/education/project) with index.

**API:** `entry_type` in all work-history endpoints (GET/POST/PUT/DELETE). Markdown render refactored with `_render_entries()` helper — now renders 3 sections (Berufserfahrung, Ausbildung, Projekte). Completeness rebalanced (work 20%, education 10%, projects 10%).

**Form:** Dynamic entry cards with add/remove for Work Experience, Education, and Projects. Each card has company/title, date range, current checkbox, description.

**i18n:** ~50 new `profile.*` keys in both `de.json` and `en.json`. All hardcoded German in template replaced with `{{ t('...') }}` calls.

**Layout:** Form tab hides log and fills entire left pane (`flex: 1`, removed 45vh cap).

### 11. Taro yogi name protection (A+B+C+D)
Collaborated with Nate (ChatGPT) on design. Built layered protection system:

**A) UX nudge:** Label now says "Pseudonym, nicht dein echter Name". Hint explains privacy. Placeholder shows example pseudonyms from Taro's pools.

**B) Pattern detection** (`core/taro.py`): ~150 common first names (DE/EN/TR), title prefixes (Dr/Prof/Herr/Frau), name particles (von/van/de/al/bin), two-capitalized-words heuristic. All soft warnings — user can confirm.

**C) Pseudonym generator:** `GET /api/profiles/me/yogi-name/suggest` returns 6 fresh unique names from Taro's 5 curated word pools (~130 words). Frontend shows clickable suggestion chips via "🎲 Suggest names" button.

**D) Hard-block:** Email (`@`), phone (5+ digits), address (Straße+number, PLZ patterns). Immediate rejection with red error box.

**Real-name guard:** Transient comparison against Google OAuth display_name + email + profile full_name. Names are read in-memory only — **never stored, logged, or returned**. EU-compliant.

**API flow:** `PUT /me/yogi-name` now returns `{status:'warning', warning:...}` for soft detections. Frontend shows yellow box with "Trotzdem verwenden" / "Ändern" buttons. Errors return 400.

**Refactored:** Inline 60-line real-name check in `profiles.py` → `core.taro.validate_yogi_name()`.

---

## End-of-day checklist

- [x] Pipeline overnight reviewed
- [x] Tests pass (438 passed, 0 errors)
- [x] Committed and pushed (5 commits)
- [x] Daily note updated
- [x] Profile form overhaul (feedback #166 + #167)
- [x] Yogi name protection (A+B+C+D via Taro)
- [ ] systemd install (needs sudo)
- [ ] Browser verification of profile page
