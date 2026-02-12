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

**6 commits pushed. 215 tests green (was 192).**

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

*— ℵ*
