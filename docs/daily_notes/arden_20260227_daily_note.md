# Arden Session Notes — February 27, 2026

## Where we are

Yesterday landed two big backend pieces:

| Commit | What |
|--------|------|
| `c24cd6e` | **Domain-inferred candidate pool** — runtime profile search now picks postings from the right occupational domains (38K IT postings for a CTO, not 5.6K random ones) |
| `3951a32` | **On-demand Clara enrichment** — `POST /api/matches/{profile_id}/{posting_id}/enrich` fires Clara in a background thread and delivers the cover letter or no-go narrative to the yogi's inbox |

Both are committed and import-clean but **neither has been exercised
end-to-end through the UI yet**. The server is running yesterday's code.

---

## What needs doing — ranked

### 1. Wire the enrich button into the search page (highest impact)

The posting detail modal in `frontend/templates/search.html` has an interest
bar (👍/👎) and a "View on source" link, but no way to trigger Clara.

**Needed:**
- A "Get cover letter" button in `openPostingDetail()` that calls
  `POST /api/matches/{profile_id}/{posting_id}/enrich`
- When response is `{"status": "ready"}` → show the cover letter / no-go
  inline in the modal (it's already there)
- When response is `{"status": "queued"}` → show a spinner + "Clara is
  analysing this… check your inbox in ~15 seconds"
- Edge: the button should only appear when a profile is active (profile
  search mode). Preview/domain search has no profile_id to enrich against.

**Scope:** ~40 lines of JS in the modal, no backend changes.

### 2. Inbox polling / notification

`messages.html` loads once and never refreshes. When Clara finishes (5–30 s
after clicking "Get cover letter"), the yogi has to manually reload the inbox
to see the result.

**Options (increasing effort):**
- **a) `setInterval` poll** — every 10 s, `GET /api/messages/unread-counts`.
  If count increases, re-fetch. Dead simple, ~10 lines of JS.
- **b) SSE / WebSocket** — real-time push. Much heavier; probably overkill
  for a single user product.
- **c) Toast notification** — after the enrich call returns `queued`, start
  a short poll (every 3 s, 10 attempts) checking the match row's
  `cover_letter IS NOT NULL`. When it resolves, show a toast with a link
  to the inbox.

**(a) is the right call for now.** We can layer (c) on top later.

### 3. Cosine pre-filter on profile upload

Right now `search_profile()` computes the domain-inferred pool + cosine
ranking at **request time** (every page load). That's fine for ~20K vectors,
but we discussed storing the top 200 scores on profile save so results are
instant and persistent.

**Hook point:** `api/routers/profiles.py` line 1552 — right after
`_schedule_profile_embedding(user_id)`. The embedding thread itself
(`_compute_profile_embedding_bg`) could chain into a pre-filter step once the
embedding is cached.

**Concern:** the embedding thread is fire-and-forget (`daemon=True`). If we
chain cosine-rank inside it, failure in one step could silently kill the
other. Better to keep the embedding write as-is and add a second background
task that runs *after* the embedding is confirmed stored — or just poll for
it.

**Scope:** medium. Needs its own background function, SQL for the top-200
upsert, and a way to avoid re-running every time the profile is viewed (idempotent check).

### 4. Smaller items (low effort, high hygiene)

| Item | Effort | Notes |
|------|--------|-------|
| `ALTER TABLE users DROP COLUMN display_name` | migration file | All rows NULL, no code reads it |
| Push to origin | `git push` | 173 commits ahead of `origin/master` |
| `sql/schema.sql` uncommitted diff | inspect | Looks like a pg_dump artifact (`\restrict`/`\unrestrict`) — commit or revert |
| F2 / Ctrl+F2 hotkey | ? | Carried over, unspecified — needs scoping |

### 5. End-to-end test of enrichment

Before wiring the UI, we should test the enrichment endpoint manually:

```bash
curl -X POST http://localhost:8000/api/matches/41/SOME_POSTING_ID/enrich \
  -H "Authorization: Bearer ..."
```

This confirms Clara's `process_match()` actually works inside the API
process (Ollama reachable, model loaded, DB write succeeds, message delivered).

---

## Proposed order for today

1. **Manual test** of `/enrich` endpoint (prove the backend works end-to-end)
2. **Search page button** — "Get cover letter" in the posting modal
3. **Inbox polling** — `setInterval` in `messages.html`
4. **Housekeeping** — push, migration, schema.sql cleanup
5. **Cosine pre-filter** — if time permits; not blocking anything

---

## Open questions

- **Ollama availability**: is the server running? Which models are loaded?
  Clara needs `qwen2.5:7b` (fallback: `gemma3:4b`) and `bge-m3` for
  embeddings. If Ollama isn't up, enrichment will fail gracefully but we
  should verify before testing.
- **Auth token for manual test**: we need a valid JWT for user 8 (Susanne)
  to test against profile_id 41. Can use the `/auth/debug-token` endpoint
  if it exists, or generate one via Python.
- **Which posting to test with?** Pick one from domain 43 (IT) that has a
  `job_description` — so Clara has text to work with.

---

## Commits This Session

| Hash | Description |
|---|---|
| `2d8cb71` | **fix: reconnect on SSL drop in Deutsche Bank actor** — added `_reconnect()` and `_safe_rollback()` methods so overnight SSL drops don't crash the entire pipeline |
| `1a827ab` | **fix: use Workday REST API for DB job descriptions** — replaced flaky `og:description` scraper with Workday's JSON API (`/wday/cxs/db/DBWebsite/`), instant-skip Cornerstone URLs |
| `05f5e58` | **fix: parse Deutsche Bank location from Workday URL slug** — extracted city/state from URL paths like `/job/Frankfurt-Taunusanlage-12/...` via `_GERMAN_CITY_MAP`; backfilled all 1,559 active DB postings (zero `'Unknown'` remaining) |
| `b9e705a` | **fix: remove geonames contamination from owl_names + add guard trigger** — deleted 13,218 geonames rows, restored 155 corrupted Berufenet names, nulled 22,701 garbage classifications, added write-once trigger |
| `0170229` | **feat: drop berufenet gate, rank search by embedding similarity** — removed `berufenet_id IS NOT NULL` filter, LEFT JOIN everywhere, new `_score_ranked_results()` with global cosine pagination, sort indicator in frontend |

---

## Session Log

### Pipeline crash diagnosis

Overnight pipeline (`turing_fetch.sh`, Feb 26 23:50) crashed at step 2
(Deutsche Bank fetch) at job 820/852:

```
psycopg2.OperationalError: SSL connection has been closed unexpectedly
psycopg2.InterfaceError: connection already closed  (during rollback)
```

Steps 3–5 never ran. **Not related** to the profession translation code
we added yesterday — pure coincidence (SSL drop mid-run).

**Fix (`2d8cb71`):** Added `_reconnect()` (re-establish DB connection after
SSL drop), `_safe_rollback()` (rollback or reconnect on dead connection),
and separate `(InterfaceError, OperationalError)` exception handling in the
inner loop. Final commit wrapped in try/except too.

### Deutsche Bank description scraper — ~98% failure rate

After re-running the pipeline, step 2 showed 837 new candidates but
only ~20 got descriptions (338/340 skipped every 20-job batch). Investigated:

**Root cause:** Deutsche Bank uses **two** job platforms:
- **Workday** (`db.wd3.myworkdayjobs.com`) — ~20% of jobs — `og:description`
  was populated inconsistently (some pages had it, many didn't)
- **Cornerstone** (`emea3.recruitmentplatform.com`) — ~80% of jobs — JS-rendered
  application form, no useful description in static HTML at all

The old scraper only checked `og:description`, so it failed silently on
every Cornerstone URL (wasting ~10 seconds each on a doomed HTTP request)
and some Workday URLs too.

**Fix (`1a827ab`):**
- **Workday REST API** — discovered `/wday/cxs/db/DBWebsite/{path}` returns
  full HTML job descriptions as JSON (tenant = `db`). 5,000+ chars,
  100% reliable for EU-accessible jobs.
- **Cornerstone detection** — URLs containing `recruitmentplatform.com` are
  skipped instantly (no HTTP request). These are self-employed financial
  advisor postings that can't be scraped.
- **Fallback chain** — Workday REST API → `og:description` → `name=description`
- **Logging** — platform breakdown (Workday vs Cornerstone count) on each run,
  skip warnings every 100 jobs instead of 20.

**Before:** ~2% success rate, 12+ minutes wasted on doomed fetches
**After:** ~100% success on Workday URLs, Cornerstone skipped instantly

Note: a small number of geo-restricted US/APAC jobs return 403 from the
REST API — these are correctly handled as unfetchable (not relevant to
German job seekers anyway).

### Deutsche Bank location fix (`05f5e58`)

All 1,559 active Deutsche Bank postings had `location_city = 'Unknown'`.
The Beesite API `PositionLocation` array comes back empty — no `CityName`.
The real location is embedded in the Workday URL slug:
`/job/Frankfurt-Taunusanlage-12/...`

**Fix:** Added `_parse_location_from_url()` with two lookup maps:
- `_GERMAN_CITY_MAP` — 15 German cities → canonical name + Bundesland
- `_MULTIWORD_CITY_MAP` — international multi-word cities (New York, Hong
  Kong, Zürich, etc.)

INSERT persists `location_state` and `location_country`. The revalidation
loop also backfills existing `'Unknown'` rows when it re-sees them.

**Backfill result:** 50 in Frankfurt am Main, 38 in Berlin, 102 German
total. Zero `'Unknown'` remaining across all 1,559 rows.

### Geonames contamination fix (`b9e705a`)

While investigating why only 9/50 Frankfurt DB postings were classified,
discovered absurd Berufenet mappings:

| Job title | Assigned Berufenet | Should be |
|---|---|---|
| Client Service Analyst Wertpapiere | Zytologieassistent/in | Bankkaufmann/frau |
| Senior Legal Counsel M&A | Verkehrsbetriebswirtschaft | Jurist/in |

The top Berufenet ID across all DB postings (`28331`) was mapped in
`owl_names` to "Steingaden" — a Bavarian village. The real profession is
"Sales-Manager/in".

**Root cause:** A `geonames_import` run (2026-02-13) wrote 13,218 German
place names into `owl_names`. 155 of those collided with existing Berufenet
IDs and overwrote primary display names. The embedding classifier was
matching job titles against town names.

**Fix:**
1. Deleted all 13,218 geonames rows from `owl_names`
2. Restored 155 corrupted primary names from `berufenet.name`
3. NULLed `berufenet_id` + `berufenet_verified` for 22,701 affected postings
4. Added a write-once guard trigger on `owl_names` to prevent overwriting
   `is_primary = true` rows from a different `confidence_source`

### Berufenet gate removal + score-ranked search (`0170229`)

**The big one.** With geonames fixed, the Berufenet classifier is now clean
— but thousands of postings still have no classification yet. The search
page previously hard-filtered on `berufenet_id IS NOT NULL`, hiding 5,766
postings that haven't been classified.

User's exact ask: "All postings in Frankfurt for my qualification levels.
Rank them by embedding similarity. That's all I need."

#### Backend changes (`api/routers/search.py`)

**`_build_posting_where()` refactored:**
- Removed `p.berufenet_id IS NOT NULL` hard gate
- Added `require_berufenet: bool = False` parameter
- Domain/QL filters use `OR b.berufenet_id IS NULL` pass-through so
  unclassified postings appear regardless of which domain bars are selected

**All 7 preview sub-queries:**
- `JOIN berufenet` → `LEFT JOIN berufenet` everywhere
- Domain bars: new "Nicht klassifiziert" bucket for NULL berufenet_id
- QL bars: new level-0 bucket "Nicht klass." for unclassified postings

**New `_score_ranked_results()` function:**
- Loads profile embedding via SHA256 text hash lookup
- Fetches ALL matching postings (LEFT JOINs to berufenet, posting_interest,
  postings_for_matching, embeddings)
- Computes cosine similarity in Python (numpy dot product)
- Sorts globally by score DESC, paginates server-side
- Falls back to recency sort if no profile embedding exists

**Results endpoint split:**
- `score=true` → `_score_ranked_results()`, returns `"sort": "score"`
- Default → recency mode, returns `"sort": "recency"`

**Detail endpoint:** `JOIN` → `LEFT JOIN`, NULL-safe domain_name/ql_level.

**Constants:** `DOMAIN_COLORS['Nicht klassifiziert'] = '#999999'`,
`QL_LABELS[0] = 'Nicht klass.'`

#### Frontend changes

- **Score badge** moved to first position in tile header (before domain dot),
  🎯 emoji prefix, slightly larger (0.72rem)
- **Sort indicator** — new `<span class="results-sort-indicator">` shows
  "🎯 Ranked by relevance" or "🕐 Sorted by date" based on `data.sort`
- **I18N** — 4 new keys in `de.json` and `en.json`: `ql_nicht_klass`,
  `domain_nicht_klassifiziert`, `results_sort_score`, `results_sort_recency`
- **CSS** — `.results-sort-indicator` styling + dark mode variant

#### Bug fix during testing

First test returned 500: `psycopg2.errors.AmbiguousColumn: column reference
"source_metadata" is ambiguous`. The `postings_for_matching` view also has
a `source_metadata` column, so unqualified references blew up when JOINed.
Fixed by prefixing all `source_metadata` → `p.source_metadata` in the
haversine template, score query, and preview queries.

#### Result

Frankfurt, QL 3+4+0 (AI Engineering Partner profile): **322 postings**,
sorted by cosine similarity.

| Position | Title | Score |
|---|---|---|
| 1 | Ingenieur Qualität und Prozesssicherung | 51.8% |
| 5 | Administrator Windows Senior | 45.7% |

Position 5 is an **unclassified** posting — previously invisible, now surfaced
and ranked. Page 2 shows scores 41.3% → 37.4%, confirming global pagination
works correctly.

### What we didn't get to

The proposed order for today was: enrich button → inbox polling → cosine
pre-filter. Instead, the session went deep on data quality (geonames
contamination, DB locations) and the gate removal turned into a substantial
search architecture change. The enrich button, inbox polling, and cosine
pre-filter remain for a future session.

---

## Production Readiness Audit

Ahead of limited production (test users, slow ramp-up), here's what stinks,
what's iffy, and what would hurt if we don't fix it. Ordered by "likelihood
of ruining someone's day."

### RED — Fix before any real user touches this

#### 1. `DEBUG=true` is the default — and it enables a backdoor

`api/config.py` line 34: `DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'`

When DEBUG is true (the default):
- **`GET /auth/test-login/{user_id}`** is active — anyone who knows or guesses
  a user_id can impersonate that user with zero authentication
- `/docs` and `/redoc` expose the full API schema
- Session cookies have `secure=False` (sent over HTTP)
- CORS allows `localhost` origins

If we forget to set `DEBUG=false` in production, every user account is
compromised. The default should be `false`, period.

**Fix:** Flip the default to `false`. Developers set `DEBUG=true` in
their `.env`. Also: disable `/auth/test-login` entirely outside of
`pytest` — not just behind a boolean.

#### 2. No file size limit on CV upload — OOM denial-of-service

`api/routers/profiles.py` line ~1222: `content = await file.read()` reads
the full upload into memory. An attacker (or a confused user with a 2 GB
scan) crashes the server.

**Fix:** `if file.size > 10_000_000: raise HTTPException(413, "File too large")`
plus configure uvicorn's `--limit-max-request-size`. 5 lines.

#### 3. No rate limiting on any endpoint

No `slowapi`, no middleware, nothing. Every endpoint is unlimited. The most
dangerous targets:
- `/api/me/parse-cv` — triggers an Ollama LLM call (~5–60 seconds of GPU)
- `/api/matches/.../enrich` — another Ollama call per request
- `/auth/login` — brute-forceable
- `/auth/test-login/{user_id}` — (see #1)

Even with only test users, a buggy frontend loop or a curious curl session
could saturate Ollama and hang everything.

**Fix:** `slowapi` with sensible defaults (e.g., 30/min per IP globally,
5/min on LLM endpoints). ~20 lines.

#### 4. `/health` endpoint returns 200 even when unhealthy

`api/routers/health.py` returns `{"status": "unhealthy", ...}` with HTTP 200.
A load balancer or uptime monitor checking status codes will never detect
a problem. Also, it only checks postgres — not Ollama, not disk, not the
connection pool.

**Fix:** Return 503 on failure. Add an Ollama ping. Add pool utilization.

### ORANGE — Fix before ramping beyond a few test users

#### 5. GDPR user deletion is blocked by FK constraints

8 foreign keys on the `users` table lack `ON DELETE CASCADE`:
`arcade_scores`, `feedback`, `mira_questions`, `notifications`,
`push_subscriptions`, `yogi_messages`, `yogi_documents`, `posting_interest`.

If a user invokes their right to erasure (Art. 17), the DELETE will fail
with a FK violation. We'd have to manually cascade in application code.

**Fix:** Migration to add `ON DELETE CASCADE` (or `SET NULL` where
appropriate). Or a `delete_user()` function that cascades explicitly.

#### 6. Background threads — fire-and-forget with no monitoring

5 daemon threads (embedding, Clara enrichment, stale validation, etc.) run
with `daemon=True`. If they crash:
- No retry
- No dead-letter queue
- No health tracking
- User never learns their embedding or cover letter silently failed
  (exception: Clara does send an error message via `_deliver_error_message`)

On graceful shutdown (deploy restart), daemon threads are killed instantly —
any in-progress Ollama call or DB write is aborted mid-transaction.

**Fix (short-term):** Thread registry + simple status tracking so we can
at least see "thread X started at T, hasn't finished after 5 minutes."
**Fix (medium-term):** Replace fire-and-forget threads with a task queue
(even a simple DB-backed one) that retries on failure.

#### 7. No global exception handler in the API

Unhandled route exceptions hit uvicorn's stderr but aren't structured-logged
with request context (user_id, path, params). No alerting hook. FastAPI's
default doesn't leak stack traces, so it's not a security issue — it's an
observability blind spot.

**Fix:** `@app.exception_handler(Exception)` that logs the error with
request context and returns a clean 500.

#### 8. No migration tracking — double-apply risk

50+ migration files in `migrations/`, no migration runner, no
`schema_version` table. Most use `IF NOT EXISTS` guards, but not all.
Applying a migration twice could silently duplicate data or fail noisily
in production.

**Fix (simple):** A `schema_migrations` table with a single-file runner
script that records applied migrations. Doesn't need Alembic — a 50-line
bash script would do.

### YELLOW — Technical debt, not blocking but accumulating

#### 9. CORS allows localhost origins in production

`api/main.py` line 46: `allow_origins` includes `http://localhost:3000`
and `http://localhost:8000` unconditionally. In production, this lets
any localhost process make authenticated requests to the API. Low risk
for a single-server deployment but bad hygiene.

**Fix:** Gate dev origins behind `if DEBUG`.

#### 10. `job_description`, `job_title`, `source` are NULLable on postings

Postings can exist without a description, title, or source. Downstream
actors handle this gracefully (skip rows with no description), but the
DB doesn't enforce it. This means broken data *can* enter and sit there
forever.

**Fix:** `ALTER TABLE postings ALTER COLUMN source SET NOT NULL` (after a
data cleanup pass). Consider `job_title` too. `job_description` stays
nullable since it's populated asynchronously.

#### 11. health_check.py isn't scheduled

The comprehensive health check script (`scripts/health_check.py`) checks
Ollama, GPU, stuck interactions, disk space — but the crontab entry is
commented out as "DEAD". The only active monitoring is `scraper_health_check.py`
(runs at 23:35) and the minimal `/health` endpoint.

**Fix:** Re-enable in crontab: `*/5 * * * *` for the comprehensive check.

#### 12. No off-site backup

Daily pg_dump → USB rsync is solid for local failures. But if the machine
is stolen, catches fire, or the USB dies simultaneously, everything's gone.
173 commits have never been pushed to origin.

**Fix:** `git push` (the 173 commits). Set up a nightly `pg_dump | gpg | scp`
to a remote VPS or S3 bucket. Even a free-tier cloud storage would do.

#### 13. Two separate connection pools

The API pool (max 20, `api/deps.py`) and the core pool (max 50,
`core/database.py`) together allow 70 concurrent DB connections. PostgreSQL
default `max_connections` is 100. Under load (pipeline + web + background
threads), we could hit the ceiling.

**Fix:** Verify `postgresql.conf` max_connections. Consider a single shared
pool or at least a combined budget that stays under the DB limit.

### Summary

| Priority | Count | Theme |
|---|---|---|
| RED (fix now) | 4 | Auth backdoor, DoS vectors, health check lies |
| ORANGE (fix soon) | 4 | GDPR, observability, thread reliability |
| YELLOW (tech debt) | 5 | Hygiene, monitoring gaps, backup gaps |

The good news: parameterized SQL everywhere (no injection in the API layer),
solid backup scripting, proper log rotation, structured logging, good FK
coverage on most tables, well-designed actor/daemon signal handling.

The core architecture is sound. The problems are mostly "we built for dev
speed and haven't hardened for production yet" — which is normal and fixable.

---

## RED items — FIXED (`36e7ea8`)

All 4 RED items from the production readiness audit are committed:

| RED Fix | What landed |
|---|---|
| DEBUG default | Flipped to `false` in `api/config.py`; dev override via `DEBUG=true` in `.env` |
| CV upload limit | 10 MB cap in `api/routers/profiles.py` — returns 413 before slurping |
| Rate limiting | `slowapi` wired up: 60/min global, 5/min on `parse_cv` and `enrich_match` |
| Health endpoint | `api/routers/health.py` returns 503 when unhealthy, checks DB + Ollama |

Bonus: CORS dev origins and `/docs`/`/redoc` gated behind DEBUG.
New `api/limiter.py` avoids circular imports.

---

## Deutsche Bank location fix (`05f5e58`)

Deutsche Bank postings had `location_city = 'Unknown'` for all 1,559 active
rows. Root cause: the Beesite API `PositionLocation` array is always empty —
no `CityName` data is returned. The real location lives in the Workday URL
slug: `/job/Frankfurt-Taunusanlage-12/...`

**Fix:** Added `_parse_location_from_url()` that extracts city/state from
the URL slug via `_GERMAN_CITY_MAP` (15 German cities → canonical name +
Bundesland) and `_MULTIWORD_CITY_MAP` (international multi-word cities like
New York, Hong Kong, Zürich). INSERT now persists `location_state` and
`location_country`. Revalidation loop also backfills existing `'Unknown'`
rows when it re-sees them on the next fetch.

**Backfill:** All 1,559 active DB postings updated — 50 now in Frankfurt am
Main, 38 in Berlin, 102 German total. Zero `'Unknown'` remaining.

---

## CRITICAL — Geonames contamination of Berufenet classifier

### Discovery

While investigating why only 9/50 Frankfurt Deutsche Bank postings got
classified, found that the classified ones had **absurd** Berufenet mappings:

| Job title | Assigned Berufenet | Actual profession |
|---|---|---|
| Client Service Analyst Wertpapiere | Zytologieassistent/in (cytology lab assistant) | Bankkaufmann/frau |
| Senior Legal Counsel M&A | Verkehrsbetriebswirtschaft (traffic management) | Jurist/in |

The **top Berufenet category across all DB postings** was `28331` — which
`owl_names` reports as "Steingaden" (a Bavarian village). The `berufenet`
table says it's actually "Sales-Manager/in".

### Root cause

A `geonames_import` run (user: arden, 2026-02-13) wrote **13,218 German
place names** into `owl_names`. 155 of those entries accidentally collided
with existing Berufenet IDs and **overwrote their primary display name**
with town names. The embedding classifier builds its label space from
`owl_names` → it was matching job titles against "Steingaden", "Rhumspringe",
"Wildenbruch" instead of "Sales-Manager/in", "Vermessungsbeamter", etc.

### Impact

- **155 Berufenet professions** have corrupted primary names in `owl_names`
- **22,701 active postings** have a `berufenet_id` that was assigned by
  matching against town names → **all garbage classifications**
- The classifier's `no_match` / `escalated` rate was artificially high
  because real profession names were replaced by place names in the
  embedding space
- Matching quality for all users is degraded (wrong profession → wrong
  candidate pool)

### Fix plan

1. **DELETE** all 13,218 `geonames_import` rows from `owl_names`
2. **Restore** the 155 corrupted primary names from `berufenet.name`
3. **NULL out** `berufenet_id` + `berufenet_verified` for the 22,701
   affected postings (they need fresh classification)
4. **Re-run** the berufenet classifier on the now-clean ontology
5. **Add a guard** — `owl_names` INSERT should reject rows where `owl_id`
   matches a `berufenet_id` AND `confidence_source` is not a berufenet-aware
   pipeline

### Prevention

How do you prevent namespace contamination in a shared OWL table?

The fundamental issue is that `owl_names` is a single flat namespace where
`owl_id` is just an integer. Geonames IDs, Berufenet IDs, and any future
ontology all share the same `owl_id` column. A bulk import into the wrong
ID range silently overwrites unrelated entries.

**Options:**
- **Namespaced IDs** — prefix or range partition: Berufenet = 1–99999,
  Geonames = 100000+. Fragile, arbitrary ceilings.
- **Composite key** — `(owl_type, owl_id)` instead of just `owl_id`.
  Each import declares its type. A geonames row can't collide with a
  berufenet row even if the integer ID matches. This is the correct fix.
- **Pre-import validation** — before any bulk import, cross-check proposed
  IDs against all existing ontology tables. Reject if collisions found.
- **Write-once guard on primary names** — a trigger or CHECK constraint
  that prevents overwriting `is_primary = true` rows from a different
  `confidence_source`. The original importer's primary name is sacred.

The composite key is the structural fix; the write-once guard is the
immediate safety net.

---

## Clara threshold fix (`a397279`)

Susanne saw 2 jobs instead of hundreds. Root cause: Clara-first path in
`/search/profile` triggered with only 9 precomputed matches (incomplete
pipeline run), replacing the runtime cosine pool of 500+. After frontend
filtering by domain/QL/geo, only 2 survived.

**Fix:** `CLARA_MIN_MATCHES = 50` — Clara mode only activates when there
are enough matches to be useful. Runtime mode fills in otherwise.

---

## Search page redesign — profile-as-scorer (not filter)

### Problem

The current search architecture treats the yogi's profile as a **binary
filter**: profile ON → only show 500 pre-ranked posting IDs; profile OFF →
show everything. This is wrong:

- 500/2000 hard limit means most of the job market is hidden
- When Clara has only run partially, the limit drops to single digits
- The profile pill toggle is confusing — "am I hiding jobs?"
- Searching by profession bypasses the limit entirely, creating
  inconsistent behaviour

### New model

**Profile defines the starting view; it doesn't restrict it.**

1. **Scope from profile** — sector (domain), qualification level, and geo
   are inferred from the uploaded profile / form entry / Mira interaction.
   These pre-select the three search panels on page load. The yogi can
   adjust them freely.

2. **All postings in scope are visible** — no 500-posting ceiling. The
   domain/QL/geo filters determine the universe. Can be thousands.

3. **Match percentage as decoration** — the first N results get a cosine
   match score displayed alongside them. Beyond N, postings appear without
   a score. The profile *ranks* but doesn't *exclude*.

4. **Cover letter / no-go on demand** — the `/enrich` endpoint we built
   fires Clara in the background. Yogi gets a notification when ready.

### What dies

- `state.profileActive` / `state.profileResults` in search.html
- The profile toggle pill
- `profile_ids` parameter in `_build_posting_where()`
- `/search/profile` as a filter source (repurposed as a scoring endpoint)

### What's new

- `GET /api/search/profile-scope` — returns inferred `{domains, ql, geo}`
  from the yogi's profile. Called once on page load to pre-select panels.
- `/search/results` gains a `score` field per posting (null when unscored)
- Results sorted: scored postings first (by match %), then unscored
  (by `first_seen_at` DESC)

### Implementation plan

1. **New endpoint** `GET /search/profile-scope` — extracts domain codes,
   QL, and location from the profile. Lightweight (no embeddings).
2. **Modify `initProfileFilter()`** → `initProfileScope()` — calls the
   new endpoint, pre-selects domain bars + QL + geo. No profile toggle.
3. **Modify `/search/results`** — accept optional `profile_id`, score
   the first page of results by cosine similarity, return `score` field.
4. **Modify result tiles** — show match % badge when `score` is present.
5. **Remove profile filter plumbing** — delete `profileActive`,
   `profileResults`, `profile_ids` from preview, profile pill rendering.
