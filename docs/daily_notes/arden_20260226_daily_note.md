# Arden Session Notes — February 26, 2026

## Summary

Session with xai. Focus on search page correctness: fixed the Bavaria > Germany
count inversion, refactored the WHERE-builder, fixed the candidate pool bias,
and activated the Clara-first path for Susanne.

---

## 1. Bavaria > Germany Bug Fix ✅

### Problem
Searching for Bavaria returned **480 results**, Germany returned **478** —
a single state showing more postings than the entire country.

### Root Cause
The profile endpoint pre-filtered the candidate pool to **5,000 most-recent
active postings**. These happened to be from the last nightly AA fetch, which
was 62% NRW and 0% Bayern/Berlin/Baden-Württemberg. So "Germany" was
effectively "5,000 NRW postings" and "Bavaria" intersected with the wrong set.

### Fix (`0dab143`)
The profile endpoint no longer pre-filters candidates by location. It returns
nationwide top-N, and location filtering happens downstream in `search_results`.

**Invariant restored:** adding any location filter can only reduce counts, never
increase them.

---

## 2. `_build_posting_where()` Refactor ✅

### Problem
`api/routers/search.py` had the posting WHERE clause duplicated 5 times
across `search_preview` (4×) and `search_results` (1×). Bug in one copy
would silently diverge from the others.

### Fix (`fd91819`)
Extracted `_build_posting_where(*, domains, professions, profile_ids, ql,
states, geo_sql, geo_params)` — a single helper that returns `(where_str,
params_list)`. Three logical groups:

- **Subject** — domains OR professions OR profile_ids
- **QL** — qualification level filter
- **Location** — states OR geographic radius circles

Result: 184 lines deleted, 134 added. All five call sites now share one
implementation.

---

## 3. Stratified Candidate Pool ✅

### Problem
The 5,000-most-recent candidate pool for runtime profile matching was
geographically biased (62% NRW, 0% Bayern). Even after fixing the
pre-filter, the pool itself was skewed.

### Fix (`6b9c2ab`)
Switched to stratified sampling:

```sql
ROW_NUMBER() OVER (PARTITION BY location_state ORDER BY first_seen_at DESC) <= 350
```

~16 states × 350 = ~5,600 candidates, geographically representative.
Results in consistent counts across all states (Berlin, Bayern, BW
all visible now).

---

## 4. Clara-First Path Activation ✅

### Problem
The profile search has two modes:
1. **Clara mode** — use precomputed `profile_posting_matches` (nightly, all 173K postings, high quality)
2. **Runtime mode** — stratified cosine search at request time (fallback)

Clara mode had a 7-day freshness window. Susanne (profile_id=41) had
28 Clara matches — all of them between Nov 2025 and Feb 12, 2026 (14 days
ago). The 7-day window excluded them all, so she always fell through to
runtime mode.

### Fix (`6f01641`)
Extended the Clara-first window from `INTERVAL '7 days'` to `INTERVAL '30 days'`.

**DB confirmation:**
- Susanne = user_id=8, profile_id=41, Kauffrau für Büromanagement, mid-level
- 28 Clara matches, most recent 2026-02-12 (score=0.920, Rostock)
- Match locations: MV, SH, ST, BY, RP, BW, NRW, Berlin — geographically diverse

After the fix, Susanne's Clara-first path activates correctly.

---

## 5. Schema: `users.is_protected` ✅

Added `is_protected boolean DEFAULT false NOT NULL` to the `users` table with
a comment: "If true, reset/seed scripts refuse to touch this user. Set manually
on real personal accounts."

Purpose: protect real user accounts (e.g., Susanne's actual account) from being
wiped by dev reset scripts or seed runs.

---

## Commits This Session

| Hash | Description |
|---|---|
| `0dab143` | fix: profile endpoint always returns nationwide top-N |
| `fd91819` | refactor: `_build_posting_where()` — eliminate 5× duplicated WHERE-builder |
| `6b9c2ab` | fix: stratified candidate pool + Clara-first path |
| `6f01641` | fix: extend Clara-first window from 7 to 30 days |
| `bfe9a8d` | chore: fix stale comment (7 days → 30 days) |

---

## 5. GDPR: Stop Storing Google OAuth `display_name` ✅

### Problem
`api/routers/auth.py` called `google_user.get("name")` and stored the Google
real name into `users.display_name` on **every login** — automatic, silent,
without consent. xai discovered `display_name = "Gershon Pollatschek"` in
the DB while testing their own profile upload.

### Fix (`4a67808`)
6 files changed, 18 insertions, 49 deletions:

| File | Change |
|---|---|
| `auth.py` | Removed `display_name` variable; removed from INSERT and UPDATE |
| `deps.py` | Removed `display_name` from per-request SELECT |
| `y2y.py` | Both identity-reveal reads switched from `display_name` → `yogi_name` |
| `profiles.py` | Taro validator `real_name` no longer uses Google name; only CV text |
| `account.py` | `DisplayNameUpdate` model and `POST /account/display-name` endpoint deleted |
| `main.py` | Arcade `player_name → display_name` write removed |

DB: `UPDATE users SET display_name = NULL` cleared all 7 rows.

Comment added to `auth.py`:
```python
# display_name (Google real name) is intentionally NOT stored — GDPR.
```

**Status**: `users.display_name` column kept (nullable) but no code writes to
it. A future migration can `ALTER TABLE users DROP COLUMN display_name`.

---

## 6. Profession-First → Profile-Ranks Runtime Mode ✅

### Problem
`search_profile()` runtime mode (no Clara matches yet) built its candidate
pool from stratified geographic sampling:

```
350 most-recent postings × ~16 states = ~5,600 candidates
→ cosine-rank by profile embedding
```

**Flaw**: the 5,600 candidates are drawn from ALL 173K postings regardless of
domain. For an IT/CTO profile, ~95% of candidates are completely irrelevant
professions (nursing, logistics, trades). The embedding scorer then picks the
least-bad 500 from a mostly-wrong pool.

### Analysis
Domain 43 (Informatik/IT) alone has 6,848 active postings — more than the
entire stratified pool, and every single one is a priori relevant.
Domain 71 (Management/Consulting) has 13,453. Together: ~20K candidates that
are far more likely to match an IT executive profile than the stratified 5,600.

This is the standard **retrieve-then-rerank** pattern:
1. **Retrieve** — use structured metadata (domain/profession) to select a
   domain-relevant candidate pool
2. **Rerank** — use the profile embedding to sort that pool by semantic fit

### Implementation — Domain Inference
The profile has `current_title` (free text, English) and `desired_roles`
(ARRAY). `berufenet.name` is German. Rather than translation or LLM:

- Tokenise `current_title` + `desired_roles` (words ≥4 chars)
- Run `SELECT DISTINCT SUBSTRING(kldb FROM 3 FOR 2) FROM berufenet WHERE name ILIKE ANY(terms)`
- German berufenet names contain loanwords like "Software", "Manager",
  "Consultant", "Data", "Cloud", "IT" — enough tokens survive cross-language
  to return useful domain codes
- Fall back to the stratified pool when inference produces nothing

**Example for "Chief Technology Officer":**
Tokens: `Chief`, `Technology`, `Officer`
Berufenet matches on `Technology` → domain 43 (Informatik) → 6,848 candidates
(massively better pool than 5,600 mixed-domain postings)

### Implementation — Code Changes (`search_profile`)

1. `desired_roles` added to the profile SELECT in step 1
2. Step 4b replaced with:
   - Token-based berufenet domain inference
   - If domains found → `WHERE SUBSTRING(b.kldb FROM 3 FOR 2) = ANY(domains)` pool
   - If no domains → fall back to stratified 350/state pool (unchanged)
3. Docstring updated to describe both modes

### Scalability
- Domain pool ~10K–20K postings for IT profiles
- Embedding fetch via `WHERE text_hash = ANY(hashes)` — scales linearly
- Numpy cosine over 15K vectors: <100ms
- Stratified fallback preserved: no regression for non-IT profiles where
  inference fails

---

## Commits This Session

| Hash | Description |
|---|---|
| `0dab143` | fix: profile endpoint always returns nationwide top-N |
| `fd91819` | refactor: `_build_posting_where()` — eliminate 5× duplicated WHERE-builder |
| `6b9c2ab` | fix: stratified candidate pool + Clara-first path |
| `6f01641` | fix: extend Clara-first window from 7 to 30 days |
| `bfe9a8d` | chore: fix stale comment (7 days → 30 days) |
| `7d54c9e` | chore: daily note + schema users.is_protected |
| `4a67808` | fix(gdpr): stop storing Google OAuth display_name |
| `c24cd6e` | feat: profession-first candidate pool in runtime mode |

---

## 7. On-Demand Cover Letters via `POST /matches/{profile_id}/{posting_id}/enrich` ✅

### Problem
Clara runs the full LLM pipeline on every profile×posting pair. With 173K
active postings per profile, that's ~35K LLM calls × 3s = **~30 hours per
profile**. Running Clara nightly in batch is neither viable nor necessary —
most postings will never interest a given yogi.

### Architecture Decision
**Never pre-compute cover letters.** Instead:

```
Profile upload
  → cosine pre-filter (runtime mode, domain-inferred pool)
  → top 200 rows stored in profile_posting_matches (score only, no LLM)
  → search page shows all 200 instantly

Yogi clicks "Get cover letter" or "Why not?"
  → POST /api/matches/{profile_id}/{posting_id}/enrich
  → Background thread calls Clara.process_match() for that single pair
  → 5–30 s: gates → embedding → LLM
  → Result written to profile_posting_matches (upsert)
  → yogi_message delivered to inbox: "Cover letter ready: <title>"
```

**Benefits:**
- Zero wasted LLM calls (only yogis who click get an LLM call)
- Results in under 30 seconds per pair (not 30 hours overnight)
- Existing messages inbox surfaces the result — no new UI infrastructure
- Idempotent: repeat clicks return cached result immediately

### Implementation — `POST /matches/{profile_id}/{posting_id}/enrich`

New endpoint in `api/routers/matches.py`:

1. **Ownership check** — profile must belong to the requesting user (403 otherwise)
2. **Idempotent fast-path** — if `cover_letter` or `nogo_narrative` already
   present in `profile_posting_matches`, return them immediately with
   `{"status": "ready", ...}`
3. **Background task** — `threading.Thread(target=_run_clara_in_background)`
   is started; endpoint returns `{"status": "queued", "message": "Clara is
   analysing ..."}`
4. **Background thread** (`_run_clara_in_background`):
   - Opens its own DB connection
   - Calls `Clara.process_match(conn, profile_id, posting_id)` (full pipeline)
   - Composes a human-readable `yogi_message`:
     - APPLY → "Cover letter ready: {title}" + go_reasons + full cover letter
     - SKIP  → "Why not: {title}" + nogo_reasons + nogo narrative
     - GATED → "Match analysis: {title}" + gate explanation
     - ERROR → brief error message
   - Inserts into `yogi_messages` (`sender_type='arden'`,
     `message_type='match_enrichment'`, `posting_id` linked)
5. **Error safety** — background thread catches all exceptions, logs them,
   and sends a user-facing error message rather than silently failing

### Message format
```
Subject: "Cover letter ready: Senior Developer — Berlin"
Body:
  Great news! I analysed **Senior Developer** at Acme GmbH — Berlin
  (match score: 87%) and recommend you **apply**.

  **Why this fits:**
  - 8 years Python experience matches required 5+
  - Previous team lead role aligns with the management responsibility
  - Cloud/AWS stack is an exact match

  **Cover letter:**
  Dear Hiring Manager, ...
```

### What's still pending
- **UI buttons** — "Get cover letter" and "Why not?" buttons on the search
  page need to call `POST /api/matches/{profile_id}/{posting_id}/enrich`.
  Nothing blocks this; the backend is ready.
- **Inbox polling** — the messages inbox already exists; yogis can find the
  result there. A small UI indicator ("Clara is working…") would improve UX.
- **Cosine pre-filter on upload** — store top 200 scores on CV save so new
  users see results without waiting for a nightly run. Architecture agreed;
  not yet wired into `profiles.py`.

---

## Commits This Session (updated)

| Hash | Description |
|---|---|
| `0dab143` | fix: profile endpoint always returns nationwide top-N |
| `fd91819` | refactor: `_build_posting_where()` — eliminate 5× duplicated WHERE-builder |
| `6b9c2ab` | fix: stratified candidate pool + Clara-first path |
| `6f01641` | fix: extend Clara-first window from 7 to 30 days |
| `bfe9a8d` | chore: fix stale comment (7 days → 30 days) |
| `7d54c9e` | chore: daily note + schema users.is_protected |
| `4a67808` | fix(gdpr): stop storing Google OAuth display_name |
| `c24cd6e` | feat: profession-first candidate pool in runtime mode |
| `58efd8d` | chore: daily note — architecture sections |
| `3951a32` | feat: on-demand Clara enrichment endpoint |

---

## Pending / Next Session

- **UI buttons**: wire "Get cover letter" / "Why not?" on search page to
  `POST /api/matches/{profile_id}/{posting_id}/enrich`
- **Inbox UX**: show "Clara is working…" indicator while queued; auto-refresh
  or link to inbox when done
- **Cosine pre-filter on upload**: hook into `_schedule_profile_embedding()`
  in `profiles.py` — after embedding computed, run cosine vs all postings,
  store top 200 score-only rows in `profile_posting_matches`
- **F2 hotkey / Ctrl+F2**: carried over from previous sessions, still open
- **Drop `users.display_name` column**: all rows NULL, no code writes — safe
  to `ALTER TABLE users DROP COLUMN display_name` in a migration
