# turing_fetch QA Report — Feb 12/13 Nightly Run
**Date:** 2026-02-13, 05:30  
**Analyst:** Copilot  
**Run window:** 2026-02-12 20:00 → 2026-02-13 02:41 (6h41m)

---

## Executive Summary

**Verdict: Solid run. The fetch itself is clean. Three issues found.**

The pipeline fetched 33,165 API results, inserted 17,514 new postings (17,457 AA + 57 DB),
ran domain classification (98% coverage), berufenet matching (55%), and then **crashed**
at step 3c (qualification level backfill) due to a SQL alias typo. This crash also killed
step 4 (enrichment / job description backfill), leaving 2 days of descriptions unfilled.

---

## What Worked Well

| Metric | Value | Assessment |
|--------|-------|------------|
| AA jobs fetched | 33,165 API → 17,457 new | Normal dedup ratio (~52%) |
| Deutsche Bank | 57 new inserts | Healthy |
| All URLs valid | 17,514 / 17,514 `http*` | Perfect |
| Zero encoding issues | 0 garbled UTF-8 | Clean |
| Unique ext IDs | 17,514 / 17,514 | Dedup working |
| Unique companies | 5,049 today | Realistic |
| All `posting_status` | 17,514 = `active` | Correct |
| Domain classification | 17,173 / 17,514 (98%) | Excellent |
| Berufenet matching | 9,606 / 17,514 (55%) | Good for auto |
| Berufenet scores | avg 0.87, min 0.70, max 1.00 | High quality, zero low-confidence |
| Berufenet errors | 5 / 17,514 (0.03%) | Trivial |
| Domain cascade | 88% via keyword (3,196) + LLM (835) + 548 unclassified | Log matches DB |
| State distribution | 14 states proportional | NRW > Bayern > BaWü — correct |
| Timestamps | 0 rows `last_seen < first_seen` | Sane |
| Soft duplicates | Max 9x (TEDi Teamleiter Hamburg) | Legit multi-posting, not a bug |

---

## Issue 1: Step 3c CRASH — SQL alias typo (BLOCKER)

**Severity: HIGH** — kills step 3c AND step 4.

```
[2026-02-13 02:41:46] [3c/4] Qualification level backfill...
psycopg2.errors.UndefinedColumn: column o.berufenet_id does not exist
LINE 11: JOIN berufenet b ON b.berufenet_id = o.berufenet_id
HINT: Perhaps you meant to reference the column "p.berufenet_id"
```

The SQL references alias `o` (probably from a previous version that had an `owl_*` table).
Should be `p` (postings).

**Impact:**
- `qualification_level` only populated for 9,606 rows (those already matched in step 3a)
- Step [4/4] enrichment (including `job_description_backfill`) **never ran**
- Same crash happened on Feb 11 too → 2 days of data affected

**Fix:** Change `o.berufenet_id` → `p.berufenet_id` in the step 3c script.

---

## Issue 2: Zero job descriptions for Feb 11 + Feb 12 (32,940 rows)

**Severity: HIGH for search quality.**

| Batch | Total | Has description | % |
|-------|-------|----------------|---|
| Feb 12 | 17,457 | 0 | 0% |
| Feb 11 | 15,583 | 0 | 0% |
| Feb 10 | 13,831 | 13,779 | 99.6% |
| Feb 09 | 26,733 | 17,865 | 66.8% |
| Feb 08 | 2,356 | 2,281 | 96.8% |

The fetch runs with `Fetch descriptions: No (metadata only)`. Descriptions are
populated by step [4/4] (`job_description_backfill`), which never ran because
step 3c crashed on both nights.

**Fix:** Fix step 3c, then re-run steps 3c + 4 for the affected rows.

---

## Issue 3: 41,541 rows (19%) have NULL `location_state`

**Severity: MEDIUM** — affects state-based filtering.

This is NOT a fetch bug. The Arbeitsagentur API doesn't return `arbeitsort.region`
for many jobs, especially from major cities.

Key finding: **Hessen and Sachsen data EXISTS** — it's just all stored with NULL state:

| City | Rows | Actual State |
|------|------|-------------|
| Berlin | 2,870 | Berlin (city-state) |
| München | 2,524 | Bayern |
| Hamburg | 1,874 | Hamburg (city-state) |
| Frankfurt am Main | 1,843 | **Hessen** |
| Köln | 1,833 | NRW |
| Dresden | 1,086 | **Sachsen** |
| Leipzig | 1,016 | **Sachsen** |
| Wiesbaden | 548 | **Hessen** |

**Subtotals:** 41,541 rows with null state, 41,336 of those DO have a city name.
Only 3 have postal codes. Zero have geo coordinates.

**Fix:** City-to-Bundesland lookup table backfill. Most of the 41K can be resolved
from city name alone.

---

## Minor Observations (Not Blockers)

- **50 rows with no title** — all AA. They have `beruf` and `posting_name`. Low impact.
- **114 rows with no city** — have state and company. Remote/undisclosed jobs.
- **No salary data** — AA generally doesn't include salary. `salary_raw/min/max` all null.
- **No `ihl_score`** — appears to be populated by a separate process.
- **`no_match` berufenet** — 7,089 rows. Top: Helfer/in-Verkauf (21), Gebäudereiniger (12).
  Valid occupations without berufenet mapping yet.
- **KLDB codes** — all prefixed `B ` — format correct and consistent.
- **5 berufenet errors** — all LLM classification failures on edge-case titles.
  Veterinärmedizinisch-technische Assistenz, ZFA with creative title, etc.

---

## Recommended Fix Order

1. **Fix step 3c SQL** — `o.berufenet_id` → `p.berufenet_id`
2. **Re-run steps 3c + 4** for Feb 11 + Feb 12 data
3. **Build city→Bundesland lookup** and backfill null `location_state`
4. **Verify tonight's cron** picks up the fix

---

## Raw Numbers

```
Total postings:     222,568
  Valid:            213,859
  Invalidated:       8,709
  Arbeitsagentur:  218,564
  Deutsche Bank:     4,004

Today's inserts:     17,514
  With domain_gate:  17,173 (98%)
  With berufenet_id:  9,606 (55%)
  With qual_level:    9,606
  With description:       0 ← Issue 2
  With location_city: 17,400
  With location_state: 17,343 (today only; 41,541 null globally)
```
