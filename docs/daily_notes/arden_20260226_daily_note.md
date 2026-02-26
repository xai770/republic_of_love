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

## Pending / Next Session

- **Run Clara for Susanne**: her 28 matches are Feb 12 (14 days old). Running
  `turing-harness.py run profile_posting_matches__report_C__clara --sample 20`
  would refresh her matches and improve result quality.
- **F2 hotkey / Ctrl+F2**: carried over from previous sessions, still open.
- **Verify count monotonicity**: confirm Berlin ≤ Germany in production for
  multiple query types (all, domain, QL, map intersection).
