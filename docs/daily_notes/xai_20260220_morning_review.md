# 2026-02-20 — Morning Review + Pipeline Health

**Session start:** ~05:14 CET
**System time at writing:** Fr 20. Feb ~05:14 CET

---

## Starting state

| Metric | Value | Δ from yesterday |
|--------|-------|-----------------|
| Total postings | 301,732 | +14,136 |
| Active (not invalidated) | 196,868 | — |
| Active (status='active') | 297,926 | +23,362 |
| Invalidated | 104,864 | — |
| With description | 290,674 | — |
| Embeddings | 316,549 | +24,577 |
| With summary | 7,641 | +74 |
| No berufenet (active) | 21,203 | +2,185 |
| No description (active) | 11,046 | — |
| Profiles | 5 | −1 (was 6) |
| Matches | 0 | −2 (was 2) |
| OWL entries | 21,419 | — |

### Metric notes
- **Profiles: 5 → was 6.** Profile #9 (Sparrow) was the latest addition (Feb 17). Unknown which profile was removed — or was yesterday's count wrong? Remaining: Sparrow, Arden (ℵ), Zach (test), Gelinda (test), Ellie (test).
- **Matches: 0 → was 2.** Profile_posting_matches table is empty. Clara test matches were presumably cleaned up or expired.
- **OWL: 21,419** — yesterday's note said 126,103. Major discrepancy. Table is `owl` not `owl_entries`.  Likely yesterday used a different metric or sum of `owl` + `owl_names` + `owl_pending`. Needs investigation or calibration with yesterday's query.

---

## Overnight pipeline analysis (23:50→03:30, 220 min)

All 5 stages green. **No crashes, no errors in log.** 220 min total (down from 293 min yesterday — 25% faster).

| Stage | Result | Duration | Notes |
|-------|--------|----------|-------|
| [1/5] AA fetch | ✅ | 3.1 min | ~14,136 new postings |
| [2/5] DB fetch | ✅ | 9.9 min | 4,324 Deutsche Bank jobs |
| [3/5] Berufenet classification | ✅ | 145.9 min | OWL Phase 1 (17m) + Phase 2 embed+LLM (99m) + Phase 3 auto-triage (29m) |
| [3b/5] Domain cascade | ✅ | 16.3 min | KldB-based + keyword+LLM |
| [3c/5] Geo state | ✅ | <1s | City → Bundesland |
| [3d/5] Qualification backfill | ✅ | 1s | |
| [4/5] Enrichment daemon | ✅ | 43.0 min | See sub-tasks below |
| [5/5] Description retry | ✅ | 1.9 min | 56 resolved / 164 tried (34%) |
| Demand snapshot | ✅ | 0.9s | 9,338 rows (522 domain + 8,816 profession) |
| Profession similarity | ✅ | 6.5s | 8,188 pairs for 823 professions (563 with embeddings) |

### Enrichment daemon sub-tasks

| Sub-task | Success | Failed | Skipped | Duration | VPN rotations |
|----------|---------|--------|---------|----------|---------------|
| job_description_backfill | 13,292 | 768 | 1 | 19.1 min | 55 |
| extracted_summary | 74 | 1 | 0 | 12.7 min | 0 |
| embedding_generator | 11,236 | 0 | 120 | 11.0 min | 0 |
| domain_gate_classifier | 222 | 0 | 0 | 0.2s | 0 |
| owl_pending_auto_triage | — | — | — | — | No work |
| external_partner_scrape | — | — | — | — | No work |

### What went well
- **Pipeline 25% faster** than yesterday (220 vs 293 min). Berufenet classification drove the improvement.
- **Zero errors in log** — no crashes, no exceptions, no tracebacks.
- **Embedding throughput solid**: 11,236 embeddings at 17.2/sec — clean run, 0 failures.
- **Description retry**: 34% resolve rate on second pass — consistent with yesterday's 37%.
- **VPN rotation**: 55 rotations during description backfill at manageable streak levels.

### What needs attention ⚠️
1. **Health report says "Errors found: 6"** — confirmed legitimate. 4 are actor batch-error summaries (total 11 sub-task failures in enrichment/description steps) and 2 are Ollama read timeouts during embedding. All transient and retried next run. Health check logic is correct.
2. **230 duplicate external_ids** in active postings (e.g. `aa-11858-16036462-STA-S` appears 3×). Health report only flagged 5. The dedup logic or upsert is letting duplicates through. Low priority but should be tracked.
3. **job_description_backfill: 768 failures (5.5%)** — down from yesterday's 1,167 failures (7%). Improving, but still significant. All are VPN-related 403s from Arbeitsagentur rate limiting.
4. **Profession similarity: only 563/823 professions have embeddings** (68%). The remaining 260 professions with ≥20 postings lack embeddings — meaning their similarity scores can't be computed. Worth investigating whether these are new professions that haven't been embedded yet.
5. **764 retryable description failures** still pending — ETA 3 min per health report. These will be retried next run.

---

## Open feedback items (oldest-first)

| # | Category | Summary | Priority |
|---|----------|---------|----------|
| 137 | bug | Mira: "ich suche" input never made it to LLM | Medium — may need to live with it |
| 166 | suggestion | Profile form: needs projects/studies form, i18n, full-width left pane | High |
| 167 | bug | Profile form: should be for projects/studies, alternative to CV | High (same as 166) |
| 170 | suggestion | Nav bar should be transparent (like feedback bar) | Low |
| 171 | bug | CV-Fehler not English + yogi name creation dialog on profile page | High |
| 186 | bug | Mira shows "2 jobs for you" on fresh login (no profile/skills yet) | High — was reported as fixed in Arden #2, verify |

---

## Plan for today

### 🔴 Must-do

1. **Verify Mira premature match fix (#186)**
   - This was supposedly fixed in commit `8689879` yesterday (Arden #2). But feedback #186 is still open.
   - Need to log in as a fresh user and confirm Mira doesn't mention matches when no profile/skills exist.
   - Resolve if fixed, dig deeper if not.

2. **Profile experience form (#166, #167, #171)**
   - These three are really one item: replace the current profile form with a projects/studies/experience form.
   - #171 adds: CV error messages need i18n, and yogi name dialog should be inline (not "go talk to Mira").
   - This is the biggest UX gap right now — the profile page is the main user-facing tool after onboarding.
   - **Subtasks:**
     a. Audit current profile form and identify what's there vs what's needed.
     b. Design the experience/projects form (fields, validation, i18n).
     c. Add inline yogi name creation/edit widget to profile page.
     d. Fix CV error i18n.

3. **LLM Taro browser test**
   - Yesterday's LLM-powered name generation (keyword→Ollama) has not been browser-tested yet.
   - Need to walk through onboarding and confirm the flow works end-to-end.

### 🟡 Should-do

4. **Investigate "Errors found: 6" in health report**
   - The health check reports 6 errors but the log has none. Figure out what the health check is counting and fix the discrepancy so the report is trustworthy.

5. **Duplicate external_ids (230)**
   - Low data quality issue. The upsert/dedup logic in the AA fetch actor may have a race condition or the dedup key isn't matching correctly.
   - Audit `postings__aa_backfill_U.py` and the upsert query.

6. **Nav bar transparency (#170)**
   - Cosmetic suggestion. Quick CSS change if we have time.

7. **Mira "ich suche" passthrough (#137)**
   - User says intent was lost. May be a prompt engineering issue in Mira's context builder, or the input was filtered before reaching the LLM.
   - Investigate `interrogators/` or `mira/context.py` to see how user messages are passed.

### 🟢 Nice-to-have

8. **Profession embedding gap (260 professions)**
   - 260 professions with ≥20 postings lack embeddings for similarity computation. May need a backfill pass.

9. **Log rotation**
   - `turing_fetch.log` is 24,247 lines dating back to Feb 15. Should set up rotation or truncation.

10. **Daily notes consistency**
    - Yesterday's OWL count (126,103) doesn't match today's query (21,419). Need to align the metrics query so daily notes are comparable day over day.

### Evening commits from yesterday (for reference)

| # | Hash | Summary |
|---|------|---------|
| 16 | `8d74d1d` | LLM-powered Taro (keyword→Ollama names), privacy copy fix (#215, #216) |
| 17 | `2c191b1` | Name chips flexbox wrap — names fit in one row (#219) |

---

## Session progress (updated 20 Feb midday)

### Completed today

| # | Commit | Summary | Tickets |
|---|--------|---------|---------|
| 1 | `d4a5bf3` | Removed Taro from UI, logo juggle animation, back buttons steps 4+5 | #220, #221 |
| 2 | `b26df88` | Mira greeting: belt-and-suspenders guard on fallback template | #186 |
| 3 | `747bc23` | Stale sweep: set posting_status + metadata when invalidating | data quality |
| 4 | `d51ce90` | Translucent nav bar with backdrop blur | #170 |
| 5 | `4810748` | Mira search intent navigates to search page with URL params | #137 |
| 6 | `a4275ce` | CV upload + yogi name errors now bilingual (de+en) | #171 |

### Data fixes applied
- 102,102 zombie active+invalidated postings → `posting_status = 'invalid'`
- 1,044 reverse inconsistencies (invalid+not-invalidated) fixed
- 1,059 missing invalidation metadata backfilled
- 230 duplicate active external_ids → 0 remaining

### Investigations resolved
- Health report "6 errors" → confirmed legitimate (2 Ollama timeouts + 4 batch summaries)
- Mira prematch → original fix correct, added safety guard on fallback
- Duplicate external_ids → root cause: stale sweep didn't update posting_status, script fixed

### Still pending
- #166/#167: Profile form was already overhauled Feb 19; yogi name inline edit still open
- LLM Taro browser test (from onboarding)
- 260 profession embedding gap
- Log rotation
- Daily notes metrics consistency

---

## Services status

| Service | Status |
|---------|--------|
| talent-yoga (FastAPI) | ✅ active |
| talent-yoga-bi (Streamlit) | ✅ active |
| Tests | 437 pass, 56 Starlette deprecation warnings |
| Last commit | `a4275ce` — CV upload + yogi name i18n |

---

## Architecture brainstorm — 08:42 session

### "My Matches" is not a recommendation feed
It is a **job application pipeline tracker**. Postings enter it through yogi actions on the search page.
See `docs/daily_notes/ty_postings_yogi_status.graphml` for the full state machine.

Posting status flow:
- Search grid → click details → **viewed**
- Search grid → click external link → **interested**
- Anywhere → mark favorite → **favorites**
- Open cover letter → "Do you intend to apply?" → **apply** / **need_decision** / **no-go**
- Open no-go rationale → "Are you no longer interested?" → same three states

Clara's role: generate the cover letter ("I am especially qualified because of...") and the
no-go rationale when a yogi engages with a posting. Profile embeddings make these documents
personal. This requires a profile but does NOT require batch match generation.

### Multi-row search (next big UX feature)

Each row in the search builder is an independent query. All results are merged (union / OR)
into a single grid. Rows can be:

| Row type | Description | Status |
|----------|-------------|--------|
| Filter row | Domain(s) + QL + city/radius | Exists today |
| Profile row | Embedding similarity to yogi's full profile | **To build** |
| Saved search row | A named filter combo from a previous session | Partially (saved searches exist) |

**Within a row:** filters are AND'd (domain AND QL AND city).
**Between rows:** always OR (union). AND between rows = intersection, almost never useful, skip.

**Source tags:** Each result card shows which row surfaced it — e.g. `✦ passt zu deinem Profil`
or `▸ deine Suche: Berlin / Bildung`. Trivial to implement: tag each result with its source
row at query time. No LLM call, no extra cost.

### Profile embedding search — technical cost

Profile embedding already exists in DB. Search = `ORDER BY embedding <=> profile_embedding LIMIT 20`.
Same pgvector lookup as posting search. Very cheap. Only new requirement: ensure profile_embedding
is refreshed when profile changes (currently has a TODO at profiles.py:568).

### Profile is a living document, not a form

Profile = everything we know about the yogi:
- Work history + skills (from CV / Adele)
- Domain and location preferences (inferred from saved searches + click behaviour)
- Anti-preferences (postings marked no-go, with rationale text)
- Saved searches (explicitly named criteria sets, part of the profile)
- Feedback typed into Mira ("I don't like companies over 500 people")

Profile is never "done" — it grows with every interaction. Every saved search, every no-go,
every Mira conversation fragment can enrich the embedding.

**Quereinsteiger use case (career changers):** Stream A (explicit filter) shows what the yogi
*thinks* they want. Stream B (profile similarity) shows what talent.yoga thinks they *could* get.
A kindergarten teacher sees "Learning Experience Designer at edtech startup" in Stream B because
their embedding lands near it, even though they typed "Lehrer" in the search.

### Profile page vs Settings page

**Profile** = who the yogi IS and what they want (work history, skills, preferences, anti-preferences, saved searches).
**Settings** = how they use the app (language, notification email, privacy choices).

Currently fuzzy — the two are mixed on the profile page. Should be separated.
Settings page is mostly already there (language toggle in header, notification email in Mira onboarding).
Profile page should absorb saved searches and explicit preferences.

### Profile row auto-activation — confirmed (09:07)

**Fires automatically:** Yes. If `has_skills = true`, the profile row is included in every search
without the yogi needing to add it. It just appears. If the profile is empty, the row is greyed out.

**"Enough signal" = Adele's call:** The system does not ask the yogi to rate their own profile
completeness. Adele (the profile extraction actor) decides when there is enough signal and
notifies the yogi. No minimum threshold UI — Adele drives this silently.

### Open questions for next session

1. **Rating UI:** "a few sliders with a smiley that changes from happy to crying" — need to design
   the rating widget for the My Matches pipeline. What dimensions? (match quality? job appeal? salary?)
   The graphml shows ratings feed back into the profile. How exactly?
2. **Cover letter trigger:** Does clicking "I intend to apply" immediately start generating the
   cover letter, or is it on-demand from the My Matches page?
3. **Saved searches as profile rows:** When a saved search is added as a row, is it editable in
   the search builder, or locked (linked to the saved search object)?
4. **Profile page redesign:** Once we have multi-row search + profile-as-living-document settled,
   the profile page layout needs a rethink. What sections? What's editable vs. inferred?
