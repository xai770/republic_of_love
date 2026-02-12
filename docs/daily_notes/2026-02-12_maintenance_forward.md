# 2026-02-12 — Maintenance & Forward Progress

**Session start:** 05:09  
**Previous session:** [2026-02-11](2026-02-11_berufenet_owl_integration.md) (20 items, 16 commits, 19/19 stinks)

---

## Starting state

| Metric | Value |
|--------|-------|
| Active postings | 205,054 |
| Berufenet-mapped | 165,956 (81%) |
| OWL synonym names | 31,355 |
| Profiles | 5 |
| Matches | 28 |
| PG cache hit | 100.00% |
| Test suite | 192 green |
| Nightly fetch | running (PID 2808530, started Feb 11 21:48) |

**Overnight fetch health:** Clean. One transient Ollama timeout at 03:39 (embedding batch, read timeout=30s). Pipeline recovered automatically. Zero warnings. Berufenet phase 2 cycling normally.

---

## Work log

### 1. Fix log-level bug in summary stats
**Commit:** `ff3fdec`

`berufenet_U.py` and `aa_backfill_U.py` logged summary counters like "Errors: 0" and "NULL (Phase 2 off): 0" at ERROR level, polluting grep results. Fixed: now INFO when count=0, ERROR/WARNING only when count > 0.

### 2. Fix Phase 1 recycling loop (berufenet)
**Commit:** `467ee99`

Root cause: `pending_owl` titles re-selected every Phase 1 batch — pipeline stuck processing same 500 titles forever. Fix: (a) exclude `pending_owl` when Phase 2 is off, (b) mark Phase-1-misses as `pending_owl` immediately instead of leaving them NULL.

### 3. Fix Phase 2 recycling loop + migrate terminal states
**Commit:** `6d0fc83`

Same recycling bug in Phase 2: escalated titles set back to `pending_owl`, re-queried every batch. Fix: map rejection reasons to terminal states (`no_match`, `llm_no`, `llm_uncertain`). Migrated 14,430 already-escalated rows in DB. Phase 2 queue draining correctly — ETA ~10:18 for 23,722 remaining titles.

---

## Design: Accepting Ambiguous OWL Matches

### The problem

`owl_lookup()` rejects any cleaned title that maps to 2+ OWL entities. This affects 5,427 unique names (31.2% of all 17,381 berufenet OWL names).

```
owl_lookup("Techniker")  →  101 owl entities  →  return None  →  falls to Phase 2
owl_lookup("Helfer")     →   48 owl entities  →  return None  →  falls to Phase 2
owl_lookup("Erzieher")   →    2 owl entities  →  return None  →  falls to Phase 2
```

Phase 2 (embedding + LLM) is 300x slower and currently failing on most titles anyway.

### Why the original rejection was wrong

We were thinking like bureaucrats: "which exact KLDB code?" But the yogi doesn't need the exact KLDB code. The yogi needs:

1. **Domain** — to filter by job field (KLDB digits 1-2)
2. **Qualification level** — hard constraint, set by yogi (KLDB digit 5: 1-4)
3. **Confidence ranking** — best matches first, like Google

And critically: **we'd rather show a few mismatches than miss a good posting.**

### What the data says

Of the 5,427 ambiguous names:

| Category | Names | % |
|---|---|---|
| Same QL + same domain | 2,489 | 45.9% |
| Diff QL + same domain | 2,938 | 54.1% |
| Diff domain | 0 | 0% |

**100% of ambiguous names share the same KLDB domain.** That's striking. "Techniker" always maps to the same domain prefix, regardless of specialization. What differs is the qualification level (for ~54%) and the sub-specialization.

The big hitters are all single-QL:

| Name | Variants | QL | Action |
|---|---|---|---|
| Techniker | 101 | {3} | Accept — all Spezialist |
| Ingenieur | 70 | {4} | Accept — all Experte |
| Facharzt | 53 | {4} | Accept — all Experte |
| Helfer | 48 | {1} | Accept — all Helfer |
| Fachwirt | 47 | {3} | Accept — all Spezialist |
| Beamter | 69 | {2,3,4} | Accept — pick by description |
| Fachkraft | 41 | {2,3} | Accept — pick by description |

### The design: three-tier acceptance

Modify `owl_lookup()` to accept ambiguous names using a confidence tier:

**Tier 1 — Unanimous (same QL, same domain):** Accept. Pick any candidate (all equivalent for matching). Set `berufenet_verified = 'owl'`, `berufenet_score = 1.0`.

**Tier 2 — Same domain, mixed QL:** Accept. Use the posting's job description to disambiguate via embedding similarity against the candidates. Pick the best. Set `berufenet_verified = 'owl_fuzzy'`, `berufenet_score` = embedding similarity to chosen candidate. If no description available, pick the most common QL among candidates.

**Tier 3 — True ambiguity (different domains):** The data says this bucket is empty (0%), but we guard for it anyway. Reject — fall through to Phase 2 as today.

### What changes

**`owl_lookup()` signature changes:**

```python
def owl_lookup(cleaned_title: str, cur, job_description: str = None) -> Optional[dict]:
```

Current code at the ambiguity check:

```python
unique_owl_ids = set(r['owl_id'] for r in rows)
if len(unique_owl_ids) > 1:
    return None  # ← today: reject
```

New code:

```python
unique_owl_ids = set(r['owl_id'] for r in rows)
if len(unique_owl_ids) > 1:
    # Group by qualification level and KLDB domain
    ql_set = set(r['qualification_level'] for r in rows if r['qualification_level'])
    domain_set = set(r['kldb'][:2] for r in rows if r['kldb'])

    if len(domain_set) > 1:
        return None  # Tier 3: different domains — genuinely ambiguous

    if len(ql_set) == 1:
        # Tier 1: same QL, same domain — pick any, they're equivalent
        row = rows[0]
        return {**build_result(row), 'confidence': 'owl_unanimous'}

    # Tier 2: same domain, mixed QL — disambiguate via description
    if job_description:
        best = disambiguate_by_description(rows, job_description)
        return {**build_result(best), 'confidence': 'owl_fuzzy'}
    else:
        # No description — pick most common QL
        best = pick_most_common_ql(rows)
        return {**build_result(best), 'confidence': 'owl_majority'}
```

**`process_batch()` needs the job description:**

Currently, the batch loop fetches `job_title` and passes the cleaned title to `owl_lookup()`. We need to also fetch `job_description` (or `extracted_summary`) and pass it for Tier 2 disambiguation.

```python
cur.execute("""
    SELECT job_title, extracted_summary, COUNT(*) as cnt
    FROM postings
    WHERE ...
    GROUP BY job_title, extracted_summary
    ORDER BY cnt DESC
    LIMIT %s
""", (batch_size,))
```

**`disambiguate_by_description()` — new function:**

For Tier 2, we need to score each candidate against the job description. Options:

- **A. Embedding similarity:** Embed the description, compare against each candidate's canonical name embedding. Requires Ollama call — adds latency.
- **B. Keyword match:** Check if the description contains any distinguishing keywords from candidate names. "Druckerei" in description → Drucktechniker. Free, instant, but brittle.
- **C. Majority vote:** Skip disambiguation, pick the QL that appears most among candidates. Free, instant, statistically reasonable.

**Recommendation:** Start with C (majority vote) for the initial implementation. The QL difference is usually 2 vs 3 (adjacent). If the yogi reports bad matches, add A later. YAGNI.

### What about `berufenet_verified` values?

New values:
- `owl_unanimous` — Tier 1, all candidates agree
- `owl_fuzzy` — Tier 2, disambiguated by description
- `owl_majority` — Tier 2 fallback, picked most common QL

These are all "classified" — berufenet_id gets set. The confidence tier tells us how much we trust the choice.

### Impact estimate

Currently at 81.4% classified (167,007 / 205,054). The ambiguous name fix affects Phase 1 throughput:
- 5,427 ambiguous names are currently rejected at Phase 1 → fall to Phase 2 (slow, mostly failing)
- After fix: these names get accepted at Phase 1 (instant)
- Exact row impact depends on how many unclassified titles match ambiguous OWL names after cleaning — need to measure

### What we're NOT doing

- **Picking the "correct" sub-specialization.** If "Techniker" maps to Drucktechniker vs Elektrotechniker, we don't care which `berufenet_id` is stored — they share the same QL and domain. The yogi sees postings filtered correctly.
- **Building the description-disambiguation pipeline yet.** Majority vote is good enough for v1. The yogi's feedback loop will catch errors.
- **Changing Phase 2.** Phase 2 (embedding + LLM) stays as fallback for titles with zero OWL matches. We're just shrinking its workload.

### Files to change

| File | Change |
|------|--------|
| `actors/postings__berufenet_U.py` | Modify `owl_lookup()`, add disambiguation helpers, update `process_batch()` query |
| `tests/test_berufenet_matching.py` | Add tests for Tier 1/2/3 paths |

### Reprocessing

After the code change, titles currently stuck as `no_match` or `pending_owl` that match ambiguous names should be reprocessed. One-time DB migration:

```sql
UPDATE postings
SET berufenet_verified = NULL
WHERE berufenet_id IS NULL
  AND berufenet_verified = 'no_match'
  AND job_title IS NOT NULL;
```

This puts them back in the Phase 1 queue, where the new `owl_lookup()` will now accept them. Script saved in `sql/reprocess_no_match_2026_02_12.sql`. Run after current fetch batch finishes.

Scope: **15,651 rows** reset to NULL. The `llm_no`/`llm_uncertain` rows (3,208) are left alone — those were rejected by the LLM after embedding, not affected by regex bugs.

---

## Session totals

| # | Task | Commit |
|---|------|--------|
| 1 | Fix log-level bug in summary stats | `ff3fdec` |
| 2 | Fix Phase 1 recycling loop | `467ee99` |
| 3 | Fix Phase 2 recycling loop + migrate | `6d0fc83` |
| 4 | MCP PostgreSQL connection fixed | — (config) |
| 5 | Three-tier owl_lookup (unanimous/majority/reject) | `685677e` |
| 6 | clean_job_title — 10 regex bugs fixed | `9b7e6dc` |
| 7 | Reprocessing SQL executed (15,651 rows reset) | `sql/reprocess_no_match_2026_02_12.sql` |
| 8 | Notification bell + dropdown in header | `25437cf` |
| 9 | Dead cron jobs removed (reaper + watchdog) | — (crontab) |
| 10 | CURRENT.md updated (was 11 days stale) | — (docs) |
| 11 | Search/Suche page — full design agreed | — (see below) |
| 12 | Smart FAB + minimize fix + architecture doc | `31526af`, `d7725a6`, `f9ad8bb` |
| 13 | Enriched build_yogi_context | `05aefd7` |
| 14 | Tier 2 on-demand context | `67f33ea` |
| 15 | Search intent → filter actions + hallucination fix | `905d8e5` |
| 16 | Map grey tiles fix + i18n + tour | `e442286`, `1ed543a`, `e39b133` |
| 17 | Pipeline kldb_code fix | `750963c` |
| 18 | Yogi events + interleaved timeline | `7fa9aae` |
| 19 | Onboarding: yogi_name + CV anonymizer + PII safety net | `38f7d68` |
| 20 | Notification email wired + CV anonymizer refinements | `510c4d2` |

**18 commits pushed. 304 tests green (was 192).**

### Fixes A/B/C final status

| Fix | Problem | Status |
|-----|---------|--------|
| A — Recycling loops | Phase 1+2 re-selecting same titles | ✅ commits 2+3 |
| B — OWL ambiguity | 31% of names rejected | ✅ commit 5 (three-tier) |
| C — Regex bugs | *in, separators, salary, dates | ✅ commit 6 (10 patterns) |

---

## Design: Search/Suche Page (v1)

### Concept

Rename "Dashboard" to **Suche** (Search). Three-panel interactive layout. Yogis define their search visually, not through dropdowns. Cross-filtering: change any panel → single API call → all three panels update live.

**Core philosophy:** "Profile embeddings help us to pick the best matches from within the buckets the yogi defined."

### Three-panel layout

```
┌─────────────────┬──────────────────────────┬─────────────────┐
│  Berufsfeld     │        Karte             │  Qualifikation  │
│  (Domain)       │   Leaflet + OSM          │  (QL 1-4)       │
│                 │   Leaflet.heat heatmap   │                 │
│  ▓▓▓▓▓▓ 42k IT  │                          │  ■ Helfer    12k│
│  ▓▓▓▓░░ 31k Med │     ○ radius circle      │  ■ Fachkraft 28k│
│  ▓▓▓░░░ 18k Bau │     (10/25/50/100km)     │  ■ Spezialist 8k│
│  ▓▓░░░░ 12k ...  │                          │  ■ Experte    3k│
│  (tappable bars) │   [Stadtsuche 🔍]        │  (tappable)     │
└─────────────────┴──────────────────────────┴─────────────────┘
│              [ Suche speichern ]                              │
├───────────────────────────────────────────────────────────────┤
│  Preview cards: 3-5 best matches, updated live               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                        │
│  │ Job 1   │ │ Job 2   │ │ Job 3   │  312 neu diese Woche   │
│  └─────────┘ └─────────┘ └─────────┘                        │
└───────────────────────────────────────────────────────────────┘
```

### Panels

**Left — Domain (Berufsfeld):** Horizontal bar chart. KLDB digits 1-2 → domain name. Tappable, multi-select. Shows posting counts that update with other filters.

**Center — Map:** Leaflet + OpenStreetMap tiles + Leaflet.heat heatmap. Fixed-radius circle (dropdown: 10/25/50/100km). City search box (geocoder). Data: 159K postings with coordinates (79% of AA), compressed to ~20,509 grid cells at 2-decimal lat/lon (~1km precision) → ~60KB payload.

**Right — Qualification Level:** 4 levels (Helfer/Fachkraft/Spezialist/Experte). Buttons or bars with counts. Tappable, multi-select.

### Cross-filter API

```
POST /api/search/preview
{
  "domains": ["71", "81"],     // KLDB domain codes, optional
  "ql": [2, 3],                  // qualification levels, optional
  "lat": 48.14, "lon": 11.58,   // center point, optional
  "radius_km": 50               // radius, optional
}
→ {
  "total": 12847,
  "by_domain": [{"code": "71", "name": "IT", "count": 8234}, ...],
  "by_ql": [{"level": 2, "count": 5100}, ...],
  "heatmap": [[48.14, 11.58, 42], ...]  // [lat, lon, weight]
}
```

Single endpoint, all filters optional. Frontend sends current state, gets everything back.

### Five enhancements (all agreed for v1)

**1. City search box on map**
Don't make yogis drag-hunt. Leaflet geocoder plugin → type city name → map pans + circle appears. Low effort, high usability.

**2. Auto-seed from profile**
When yogi opens Search, pre-populate from their profile: berufenet classification → domain + QL pre-selected, city → map centered. They see their world immediately, then adjust.

**3. Preview cards below panels**
3-5 best-matching postings shown below the three panels, updated live on every filter change. Uses existing `profile_posting_matches` embeddings to rank within the filtered bucket. Yogis see real results instantly — makes the page feel alive, not just a filter wall.

**4. Freshness badge**
"312 neu diese Woche" — counts postings added in last 7 days within current filters. Shows the market is active. Updated on every filter change alongside the other counts.

**5. Natural language input (Ollama)**
Text box: "Ich suche Pflegejobs in München" → Ollama decomposes into structured filters → panels auto-populate. Later enhancement but included in v1 design. Uses existing Ollama (qwen2.5) on localhost. Intent extraction prompt: classify domain, QL, and city from free text.

### Data availability

| Data | Available? | Source |
|------|-----------|--------|
| Domain (Berufsfeld) | ✅ | `berufenet.kldb` digits 1-2 via `berufenet_id` |
| Qualification level | ✅ | `berufenet.kldb` digit 5 via `berufenet_id` |
| Coordinates (lat/lon) | ✅ 79% | `source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'` |
| Employment type | ❌ | Not in AA API data — skip for v1 |
| City name | ✅ | `source_metadata->'raw_api_response'->'arbeitsort'->'ort'` |
| Published date | ✅ | `source_metadata->'published_date'` or `raw_api_response->'aktuelleVeroeffentlichungsdatum'` |

### Tech stack

- **Map:** Leaflet.js + OpenStreetMap tiles + Leaflet.heat plugin
- **Charts:** Plain HTML/CSS bars (no charting library needed)
- **API:** FastAPI endpoint in `api/routers/search.py`
- **Template:** `frontend/templates/search.html` (new)
- **Nav:** Add "Suche" to `partials/sidebar.html`

### Files to create/modify

| File | Action |
|------|--------|
| `api/routers/search.py` | New — search preview endpoint |
| `frontend/templates/search.html` | New — three-panel layout |
| `frontend/templates/partials/sidebar.html` | Add Suche nav item |
| `api/main.py` | Register search router |
| `frontend/static/css/style.css` | Search page styles |

### What we're NOT doing in v1

- **Employment type filter** — AA API doesn't provide arbeitszeit/befristung/homeoffice in search results. Could later re-fetch from detail endpoint `/jobdetails/{refnr}` or extract from description text.
- **Save multiple searches** — v1 has one active search per yogi, saved via "Suche speichern".
- **Pagination of results** — preview cards show top 3-5 only. Full results list is a separate page later.

---

## Mira Context Architecture — "Give Her Eyes"

**Time:** 14:56  
**Inspiration:** Clarke, Bradbury, Dick

### The problem

`build_yogi_context()` in `core/mira_llm.py` only loads `skill_keywords` and `match_count`. Mira doesn't know the yogi's name, title, location, experience, desired roles, salary expectations, tier, or login history. She calls everyone "Yogi A". She can't help with the search because she has no mechanism to return structured actions (set filters, trigger queries). She has no awareness of what the yogi has been doing on the platform.

### Architecture: Two-Tier Context

```
┌─────────────────────────────────────────┐
│  TIER 1: ALWAYS IN CONTEXT (~1500 tok)  │
│                                         │
│  • Time & date                          │
│  • FAQ top 10 (already in prompt)       │
│  • Yogi card (name, skills, matches)    │
│  • Last 10 messages + last 5 events     │
│  • Current search state (if on /search) │
│                                         │
│  → Loaded by build_yogi_context()       │
│  → Every single chat call               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  TIER 2: ON-DEMAND TOOLS (~0-2000 tok)  │
│                                         │
│  • search_postings(domain, city, ql)    │
│  • get_profile_detail(section)          │
│  • get_doug_reports(topic)              │
│  • get_staff_messages(recent=5)         │
│  • request_doug_research(topic)         │
│                                         │
│  → Triggered by intent detection        │
│  → Results injected as assistant note   │
│  → gemma3:4b handles ~4K context well   │
└─────────────────────────────────────────┘
```

### Token budget (gemma3:4b = 8K context)

| Component | Tokens | Notes |
|-----------|--------|-------|
| System prompt (voice + rules) | ~600 | Already exists |
| FAQ knowledge | ~600 | Already exists |
| Yogi card | ~150 | NEW — name, title, skills, matches |
| Timeline (10 msgs + 5 events) | ~500 | Partially exists (msgs only) |
| Search state | ~100 | NEW — current filters on /search |
| Tier 2 results (on demand) | 0–2000 | NEW — only when triggered |
| **Subtotal** | ~1950–3950 | Leaves 4K for generation |

### Implementation plan

#### Task 1: Enrich `build_yogi_context` (30 min)
**File:** `core/mira_llm.py`

Load from DB and inject into system prompt:
- `users.display_name`, `users.tier`, `users.created_at`, `users.last_login_at`
- `profiles.full_name`, `profiles.current_title`, `profiles.desired_roles`, `profiles.desired_locations`
- `profiles.experience_level`, `profiles.years_of_experience`, `profiles.expected_salary_min/max`
- `profiles.profile_summary`
- Current datetime

Format as structured yogi card:
```
## This Yogi
Name: Gershon | Member since: Oct 2025 | Tier: Sustainer
Title: Senior Software Engineer | 8 yrs experience
Looking for: Backend Dev, Platform Engineer | Locations: Frankfurt, Remote
Skills: Python, PostgreSQL, FastAPI, Docker, K8s
Salary: €65K–80K | Level: Senior
Summary: "Experienced backend engineer transitioning from..."
Matches: 47 found, best: Backend Dev at Deutsche Bank (87%)
Last seen: 10 min ago
```

#### Task 2: Create `yogi_events` table + tracking (1 hr)
**Files:** `migrations/`, `api/deps.py` or middleware, `frontend/static/js/app.js`

```sql
CREATE TABLE yogi_events (
    event_id    SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(user_id),
    event_type  TEXT NOT NULL,
    event_data  JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_yogi_events_user ON yogi_events(user_id, created_at DESC);
```

Five events that matter:

| Event | Trigger | Data |
|-------|---------|------|
| `login` | Auth success | `{page: referrer}` |
| `page_view` | Route hit | `{page: '/search'}` |
| `posting_view` | Posting detail | `{posting_id, title, dwell_s}` |
| `search_filter` | Filter change | `{domains, ql, city, radius}` |
| `match_action` | Save/dismiss | `{match_id, action: 'save'\|'dismiss'}` |

**NOT tracking:** scroll depth, mouse hovers, exact timing (noisy, creepy).

#### Task 3: Interleaved timeline in context (30 min)
**File:** `core/mira_llm.py`

Merge `yogi_messages` + `yogi_events` chronologically, format for LLM:
```
[14:30] Yogi logged in
[14:31] Yogi viewed /search, set filters: Berlin + IT
[14:32] Yogi: "Hey, ich suche was in der Pflege in Frankfurt"
[14:32] Mira: "Meinst du Gesundheit/Pflege? ..."
[14:35] Yogi viewed posting #4521 (Backend Dev, Deutsche Bank) for 45s
```

#### Task 4: Search intent → filter action (1 hr)
**Files:** `core/mira_llm.py`, `api/routers/mira/chat.py`, `api/routers/mira/models.py`, `frontend/templates/search.html`

When user says "Pflegejobs in München":
1. After LLM reply, extract structured intent via regex + KLDB domain map
2. Return `actions: {set_filters: {domains: ["81","82"], city: "München", lat: 48.14, lon: 11.58}}`
3. Frontend applies filters to search state and triggers `doSearch()`

#### Task 5: Tier 2 on-demand tools (2 hrs)
**Files:** `core/mira_llm.py`, `api/routers/mira/chat.py`

Intent detection → DB query → inject result → re-prompt:
- "Was weißt du über Deutsche Bank?" → query Doug reports for that company
- "Zeig mir mein Profil" → load full `profile_raw_text`
- "Was hat Doug geschrieben?" → load latest `yogi_messages WHERE sender_type='doug'`

### Decision: Don't pollute `yogi_messages` with events

Login/logout markers are NOT chat messages. Inserting "Yogi logged on" as a `yogi_messages` row breaks the clean `sender_type` contract and pollutes the conversation. Instead: separate `yogi_events` table, interleaved at query time.

---

## Parked: Yogi Name Onboarding

**Status:** Parked — pick up when onboarding flow is built.

**Problem:** Mira currently uses `display_name` / `full_name` from the database. But yogis don't go by their real name on the platform — they choose a **yogi name** (e.g. "xai", not their legal name). Mira must address them by their yogi name, not their real one.

**What's needed:**
1. **Schema:** Add `yogi_name` column to `users` table (or `profiles`). This is the name Mira uses. `display_name` stays as-is for internal/admin use.
2. **Onboarding flow:** When a yogi first signs up (or first opens Mira), prompt them to choose a yogi name. This becomes part of the onboarding conversation — Mira asks, yogi answers, it's stored.
3. **Mira context:** `build_yogi_context()` should prefer `yogi_name` over `display_name` / `full_name`. If no yogi name is set yet, Mira should ask for one (first-conversation trigger).
4. **Uniqueness:** Yogi names should probably be unique (like a handle). Consider case-insensitive uniqueness check.
5. **Display:** The yogi name should appear in the UI header, chat greeting, and anywhere the platform addresses the user.

**Design questions to resolve later:**
- Where does yogi_name live? `users.yogi_name` feels right (it's identity, not profile).
- Can yogis change their name? Probably yes, but rate-limited.
- Should Mira's first-ever message be "Hi! What should I call you?" — yes, this is the ideal onboarding hook.

---

## Onboarding + Privacy-First Profile Ingestion

**Status:** Building — Feb 12, 2026 evening session

**The vision:** A yogi signs in, chooses a name, uploads a CV, and gets matched — 
without us ever storing their real name, email, address, or employer names.

**Legal basis:** EU anti-discrimination law + GDPR data minimization.
- CVs contain PII we must not store: real names, company names, addresses, dates
- Real name → replaced with yogi_name
- Company names → generalized ("Deutsche Bank" → "a large German bank")
- School names → stripped ("INSEAD MBA" → "MBA")
- Dates → converted to durations ("2018-2022" → "4 years")
- Notification email → yogi-provided (any address they choose), never from OAuth

**The flow:**
```
Google Sign-In (only sub claim stored, no email/name)
    ↓
Mira: "Wie soll ich dich nennen?" → yogi_name stored
    ↓
Upload CV (PDF/Word) → RAM only, never on disk
    ↓
LLM extracts structured data (skills, roles, companies, education)
    ↓
LLM anonymizes: yogi_name replaces real name, companies generalized
    ↓
PII safety net: regex + company corpus check — rejects if leaks detected
    ↓
Store ONLY the anonymized profile → delete original from memory
    ↓
Mira confirms: "Das habe ich verstanden: 12 Jahre Erfahrung, Python, Cloud..."
    ↓
Mira: "Sollen wir dich kontaktieren wenn wir deinen Traumjob finden?"
    → optional notification_email (any address, unsubscribe link in every email)
    ↓
Matching starts automatically
```

### Task breakdown

#### Task O1: Schema migration — yogi_name + PII cleanup (20 min)
**File:** `migrations/055_yogi_name_and_pii_cleanup.sql`

- Add `users.yogi_name` (TEXT, UNIQUE, case-insensitive via LOWER index)
- Add `users.onboarding_completed_at` (TIMESTAMPTZ)
- Drop PII columns from `users`: don't drop email/display_name yet (existing code uses them),
  but add `users.notification_email` migration note
- Note: `profiles.full_name`, `profile_raw_text` etc. will be addressed when
  the anonymized profile flow replaces the old import

#### Task O2: Mira onboarding — yogi_name conversation (30 min)
**File:** `core/mira_llm.py`

- Detect first-conversation state: no `yogi_name` → trigger onboarding
- Mira asks "Wie soll ich dich nennen?" / "What should I call you?"
- Extract yogi_name from response, validate (unique, 2-20 chars, no slurs)
- Store in `users.yogi_name`
- Use yogi_name in all subsequent context/greetings

#### Task O3: CV anonymization core (45 min)
**File:** `core/cv_anonymizer.py` (NEW)

- `extract_and_anonymize(text: str, yogi_name: str) -> dict`
- LLM prompt: extract skills, roles, education, work history WITH company names
- Second pass or same prompt: replace real name → yogi_name, companies → generalized
- Company generalization via LLM: "Deutsche Bank" → "a large German bank"
- Return structured JSON: skills, anonymized_work_history, education, years_experience

#### Task O4: PII safety net (20 min)
**File:** `core/pii_detector.py` (NEW)

- Regex patterns: email, phone, dates (DD.MM.YYYY, YYYY), LinkedIn URLs
- Company name corpus: load 36K names from `postings.posting_name`
- `check(text: str) -> list[str]` returns violations
- Used as post-LLM validation — if anything leaks, reject and re-try

#### Task O5: Wire into parse-cv endpoint (20 min)
**File:** `api/routers/profiles.py`

- Modify `parse_cv()` to use anonymizer instead of raw extraction
- RAM-only: file bytes → text → LLM → anonymized JSON → response
- No disk writes, no raw text stored
- Return anonymized work history for yogi confirmation

#### Task O6: Notification email consent (15 min)
**Files:** `api/routers/profiles.py`, `core/mira_llm.py`

- Mira asks after profile is set up (or separately in chat)
- "Was machen wir, wenn wir deinen Traumjob finden? Sollen wir dich kontaktieren?"
- Yogi can provide any email — stored in `users.notification_email`
- Clear privacy statement: only for match notifications, one-click unsubscribe
- If yogi says no: "Kein Problem! Du siehst neue Matches wenn du dich einloggst."

#### Task O7: Tests (20 min)
**File:** `tests/test_onboarding.py` (NEW)

- Test yogi_name validation (length, uniqueness, forbidden chars)
- Test PII detector (emails, phones, company names, clean text)
- Test anonymization output format
- Test onboarding state detection (no yogi_name → first convo)

### What we already have
- CV text extraction: `profiles.py:parse_cv()` — PDF/DOCX/TXT → text ✅
- LLM integration: Ollama with gemma3:4b (chat) and qwen2.5:7b (extraction) ✅
- 36K company names in `postings.posting_name` for PII corpus ✅
- Privacy architecture doc: full design from Arden, Nov 2025 ✅
- Workflow 1126 archive: 4-step extraction pipeline (reference) ✅

### Implementation results — commit `38f7d68`

| Task | Status | Notes |
|------|--------|-------|
| O1 | ✅ Done | `migrations/055_yogi_name_onboarding.sql` — yogi_name + onboarding_completed_at |
| O2 | ✅ Done | Mira onboarding in `core/mira_llm.py` — greeting filter, name extraction, validation |
| O3 | ✅ Done | `core/cv_anonymizer.py` — single-pass LLM extraction + anonymization (qwen2.5:7b) |
| O4 | ✅ Done | `core/pii_detector.py` — regex + 36K company corpus, catches email/phone/LinkedIn/companies |
| O5 | ✅ Done | `api/routers/profiles.py` — parse_cv wired to anonymizer, requires yogi_name |
| O6 | ✅ Done | Notification email wired into chat — ask after name, accept/decline, consent stored |
| O7 | ✅ Done | `tests/test_onboarding.py` — 55 tests, 304 total passing |

**E2E verified with 3 test users** (via `GET /auth/test-login/{id}`):

| User | Yogi name | Email path | DB state |
|------|-----------|------------|----------|
| Luna (4) | "Nenn mich Luna" | Provided: luna.star@proton.me | ✅ name + email + consent + onboarding done |
| Kai (5) | "Ich bin Kai" | Declined: "Nein danke" | ✅ name + no email + onboarding done |
| Rio (6) | "Call me Rio" | Provided: rio@proton.me | ✅ name + email + consent + onboarding done |

Full flow per user:
1. Greeting ("Hey!") → Mira asks "wie soll ich dich nennen?"
2. Name → Mira saves, asks about notification email
3. Email or decline → Mira saves (or skips), onboarding complete
4. Normal chat → Mira addresses by yogi_name, no more onboarding intercept

**CV anonymization E2E** (Luna, test CV with real PII):
- Input: Maria Schmidt, Deutsche Bank, SAP SE, Siemens, BMW, Accenture, TU München, phone, email, LinkedIn
- Output: yogi_name=Luna, "a large German bank", "a leading enterprise software company"
- Skills preserved: SAP S/4HANA, PMP, Scrum Master (company names allowed in skills/certs)
- PII scrubbed: no email, phone, address, LinkedIn leaked

**Bugs found & fixed during implementation:**
- Greeting treated as name ("Hallo!"/"Hi there!" → yogi_name) — expanded greeting filter
- SAP 3-char company detection — `len > 3` skipped "sap", changed to `>= 3`
- German phone regex too strict — rewrote to flexible pattern
- Compound name splitting — "Gershon Pollatschek" now checks each part separately
- PII scrubber over-redacting skills — split check: companies only in employer fields, not skills/certs

**Commits:** `38f7d68` (core), `510c4d2` (email wiring + refinements)

---

*Pretty amazing. From a blank search page to this. — ℵ*
