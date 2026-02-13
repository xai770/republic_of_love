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

1. ~~**Fix step 3c SQL** — `o.berufenet_id` → `p.berufenet_id`~~ ✅ **DONE** (`ac8b95e`)
2. ~~**Re-run steps 3c + 4** for Feb 11 + Feb 12 data~~ ✅ **DONE** (ran manually after fix)
3. ~~**Build city→Bundesland lookup** and backfill null `location_state`~~ ✅ **DONE** — three-layer geo_state actor (`a1d8b00`, `ed8217d`): OWL lookup → GeoNames DE.txt fallback → self-learned cache
4. **Verify tonight's cron** picks up the fix — ⏳ pending (overnight run)

---

## Session Work Log — Feb 13, 2026

### Pipeline QA Fixes (morning)
- **Step 3c SQL fix** (`ac8b95e`): `o.berufenet_id` → `p.berufenet_id`, added synonym fallback via `owl_names` → `berufenet_synonyms`
- **Geo state resolution** (`ed8217d`, `a1d8b00`): Built `postings__geo_state_U.py` actor — 3-layer city→state lookup (OWL → DE.txt → self-learned). Backfilled 41K null states.
- **Re-ran steps 3c + 4** for Feb 11 + 12 affected rows

### OWL Browser (`052da32`, `f4448f1`, `aa7d8aa`)
- **Grid + detail view**: `/admin/owl-browser` — browse entities by type, search, drill into detail with relationships/metadata
- **Privilege system** (`f4448f1`): 11 OWL privileges (e.g. `can_view_matches`, `can_edit_profile`), role grants, recursive resolver in `user_has_owl_privilege()`
- **Tree view** (`aa7d8aa`): Collapsible folder tree with lazy-loading children via `/admin/owl-browser/children` endpoint

### OWL Geography Completion (`cd8529b`)
- **Fixed tree hierarchy**: Added missing Deutschland → geography `child_of` link (cities were in grid but not tree)
- **Loaded all GeoNames places**: 8,368 new villages from DE.txt → **13,183 total cities** in OWL
- **Added postal codes**: `postal_codes` array in metadata for all 13,182 cities (Berlin: 191 zips, München: 75)
- **Lat/lng**: Confirmed present for all 13,182 cities
- **475 ambiguous places** skipped (same name in multiple states)
- **Tree limit**: Raised from 500 → 5,000 children per node (largest: Rheinland-Pfalz at 2,093)

### Commits Today
| Hash | Summary |
|------|---------|
| `ac8b95e` | fix(pipeline): step 3c synonym fallback |
| `33d90b6` | docs: actor vs tool consequence explanation |
| `ed8217d` | feat: geo state resolution via OWL |
| `a1d8b00` | feat: three-layer city→state lookup |
| `052da32` | feat: OWL browser grid + detail |
| `f4448f1` | feat: OWL privilege system |
| `aa7d8aa` | feat: OWL browser tree view |
| `cd8529b` | feat: OWL geography completion (13K places + postal codes) |
| `27c5bd3` | feat: tree limit 500 → 5000 children |
| `417b057` | docs: daily notes update |
| `2e8f9f9` | feat: feedback widget ("Fehler melden") with screenshot + highlight |
| `99af5a8` | docs: privacy testing guide update |
| `9b4a2ba` | feat: add Phase 3 auto-triage to turing_fetch.sh |
| `248f7ed` | feat: owl-triage status tabs (rejected/pending/resolved/skipped) |

### Feedback Widget (`2e8f9f9`)
- **"Fehler melden" button**: Floating 🐛 overlay on all pages
- **Screenshot + highlight**: html2canvas captures page, user drags to highlight problem area
- **Admin dashboard**: `/admin/feedback` — status tabs, lightbox, resolve workflow
- **DB table**: `feedback` (id, user_id, page_url, screenshot_data, highlight_rect, description, status, created_at, resolved_at)

### OWL Triage Pipeline Fix (`9b4a2ba`)
- **Root cause**: 22,793 `owl_pending` items stuck at `status=pending` — all berufenet type
- **Why**: Phase 2 (embedding + LLM candidate generation) ran nightly, but Phase 3 (auto-triage via `bulk_auto_triage.py`) was never integrated into `turing_fetch.sh`
- **Fix**: Added Phase 3 auto-triage call to `turing_fetch.sh` after Phase 2
- **Bulk run result**: 22,664 items processed in 208.8 minutes
  - 16,061 resolved (70.9%)
  - 6,603 rejected (29.1%)
  - 0 skipped
- **DB state after**: 23,195 resolved, 9,776 rejected, **0 pending**

### OWL Triage UI Tabs (`248f7ed`)
- Added 4-tab status bar: Rejected | Pending | Resolved | Skipped (with counts)
- Default view: rejected items (since pending is now 0)
- Rejected items show candidates with "Override & Resolve" button
- Resolved/Skipped tabs are read-only
- All pagination and action redirect URLs carry `status` param

---

## Berufenet Classification: Hard Cases Analysis

**Context:** After clearing the 22K triage backlog, reviewed the 9,776 rejected items.
These are job titles where the LLM auto-triage couldn't find a confident berufenet match.
Sandy to review this section.

### The Numbers

| Metric | Value |
|--------|-------|
| Total postings | 222,568 |
| Have berufenet_id | 199,791 (89.8%) |
| No berufenet_id | 22,777 (10.2%) |
| owl_pending resolved | 23,195 |
| owl_pending rejected | 9,776 |
| owl_pending pending | 0 |

### Rejected Items by Embedding Score

| Score bucket | Count | Meaning |
|-------------|------:|---------|
| >0.65 (decent match, LLM said no) | 2,899 | Potentially fixable |
| 0.55–0.65 (mediocre match) | 5,739 | Grey zone |
| 0.45–0.55 (poor match) | 1,116 | Genuinely distant |
| <0.45 (garbage/noise) | 21 | Ad headlines, empty strings |
| No candidates | 1 | Empty title data bug (pending_id=2) |

### Three Failure Patterns in Rejected Items

**Pattern A — LLM too conservative (fixable, ~1,000–2,000 items)**
The embedding found a reasonable berufenet candidate, but the LLM rejected it.

| Raw title | Top candidate | Score | Assessment |
|-----------|--------------|-------|------------|
| Hausmeisterhelfer | Hausmeister/in | 0.785 | Should have matched — Helfer level of same occupation |
| Nachwuchsführungskraft Reinigung | Helfer/in - Reinigung | 0.710 | LLM rejected; `Gebäudereiniger/in` would be closer |
| Experte Rechnungswesen / Abrechnung | Assistent/in/Fachkraft - Rechnungswesen | 0.730 | Reasonable match, LLM was too strict |
| Elektriker:innen im Schichtdienst | Helfer/in - Elektro | 0.658 | `Elektroniker/in` exists and would fit better |

**Pattern B — Embedding missed the right candidate (fixable, ~1,000–2,000 items)**
Berufenet HAS a match, but the embedding surfaced the wrong one.

| Raw title | What embedding found | What actually exists |
|-----------|---------------------|---------------------|
| Maschinenbediener / Bestücker | Mechatroniker/in (0.671) | Maschinen- und Anlagenführer/in (132652–132656) |
| Helfer Kälte- und Klimatechnik | Helfer/in - Chemie- und Pharmatechnik (0.664) | Helfer/in - Klempnerei, Sanitär, Heizung, Klimatechnik |
| Kantinenmitarbeiter | (rejected) | Helfer/in - Küche (3751) |
| Network Deployment Engineer | DevOps Engineer (0.809) | Netzwerkadministrator/in or IT-Systemelektroniker/in |

**Pattern C — Berufenet fundamentally can't represent this (~5,000–6,000 items)**
These jobs don't map to the German vocational training taxonomy.

| Raw title | Why it fails | Category |
|-----------|-------------|----------|
| KYC Associate / KYC Role, NCT | Investment banking specialization, no berufenet equivalent | Too specialized |
| Clearing and Settlement Analyst, NCT | Post-trade finance niche | Too specialized |
| SAP Consultant / Principal Consultant | Berufenet has only generic "Data-Consultant" | Too specialized |
| Aushilfe auf geringfügiger Beschäftigungsbasis | Describes employment type, not occupation | Not an occupation |
| Teamassistenz | No entry for team/project assistant; Sekretär/in exists (15009) but is different | Gap in berufenet |
| Wohnbereichsleitung | Composite: management + social work + care | Composite role |
| Chief of Staff & Strategic Project Lead | C-suite adjacent composite | Composite role |
| Referendar (all genders) | Legal trainee stage (Beamtenlaufbahn), not an occupation | Status, not job |
| "Kaffee im Blut?" | Marketing headline, not a job title | Data noise |
| "Weil gutes Wohnen mit Zuhören beginnt" | Marketing headline | Data noise |
| Idstein / Gemeinde Enge-Sande | Place names stored as job titles | Data noise |
| CRO India Grads 2026 / ACO Junior Paris | Internal program names | Data noise |

### 8 Case Studies (reviewed by human)

1. **Maschinenbediener** — Berufenet has `Maschinen- und Anlagenführer/in` (IDs 132652–132656) with 5 specializations. Embedding should have found them. → **Pattern B, fixable**

2. **Empty title** — 1 item (pending_id=2), raw_value is empty string, all candidate scores 0.000. → **Data bug, clean up**

3. **KYC Associate** — Closest berufenet: Compliance-Manager/in (89949), Geldwäschebeauftragte/r (135002), Bankkaufmann/-frau (6755). None are KYC-specific. → **Pattern C, berufenet gap**

4. **Aushilfe auf geringfügiger Beschäftigungsbasis** — "Mini-job/€520 marginal employment." Berufenet has 30+ `Helfer/in - [domain]` entries but no generic Aushilfe. Title describes contract type, not occupation. → **Pattern C, not an occupation**

5. **Kantinenmitarbeiter** — Berufenet has `Helfer/in - Küche` (3751), `Helfer/in - Gastgewerbe` (10086), `Fachkraft - Küche` (136119). Should have matched. → **Pattern B, fixable**

6. **Wohnbereichsleitung** — Residential care team lead. Berufenet has `Pflegedienstleiter/in` (14589) which is close. Also `Sozialarbeiter/in` (58775). Neither is exact — it's a composite role. → **Pattern C, borderline — Pflegedienstleiter/in is 80% right**

7. **Teamassistenz** — No berufenet entry found. `Sekretär/in` (15009) exists but is a different role. `Managementassistent/in` (77908, 58991) exists but is a formal school-based training track. → **Pattern C, berufenet gap**

8. **Clearing and Settlement Analyst, NCT** — Post-trade finance. Closest: `Wertpapiersachbearbeiter/in` (6793), `Wertpapieranalyst/in` (6779). Loose fit. → **Pattern C, too specialized**

### Architectural Observation: Berufenet's Limits

Berufenet (based on KldB 2010) classifies occupations along two axes:
1. **Berufsfachlichkeit** (occupational field) — the 5-digit code, *what* you do
2. **Anforderungsniveau** (skill level) — 1=Helfer, 2=Fachkraft, 3=Spezialist, 4=Experte

But a *job posting* describes a *position*, not a *trained occupation*. A position has:
- **Occupation** (berufenet's domain — partially covered)
- **Level** (Helfer → Fachkraft → Spezialist → Experte — partially in berufenet)
- **Industry/Domain** (banking, automotive, public sector — NOT in berufenet)
- **Employment arrangement** (hours, contract type, mini-job — NOT in berufenet)
- **Compensation** (salary — NOT in berufenet)

Berufenet works for ~90% of German postings. The remaining ~10% are:
- **Too generic** — describe employment level, not occupation (Aushilfe, Maschinenbediener)
- **Too specialized** — company/industry-specific (KYC Associate, SAP Consultant)
- **Composite roles** — blend multiple domains (Wohnbereichsleitung, Chief of Staff)
- **Data noise** — marketing headlines, place names, program codes

### Proposed: Complementary Dimensional Model

Instead of forcing everything into berufenet, add orthogonal dimensions to postings:

| Dimension | Values | Source |
|-----------|--------|--------|
| Works mostly with | Humans, machines, animals, plants, raw materials, IT | Inferred from description (hardest) |
| Hours per week | Mini-job, part-time, full-time, shifts | Often explicit in posting text |
| Responsibility level | 0–n people managed | Extractable from titles (Leitung, Team Lead) |
| Salary in € | Range or single value | Sometimes in posting, usually not (AA doesn't include) |

**Key principle:** These dimensions live on the **posting**, not on the occupation. Berufenet remains ONE dimension (null when it doesn't fit), not THE dimension.

**Matching value:** "Looking for a Fachkraft-level role, primarily working with humans, full-time, €40–50K" matches both the Bankkaufmann WITH berufenet_id AND the KYC Associate WITHOUT one.

### Quick Wins (no architecture change needed)

1. **Fix Pattern A+B** (~2,000–3,000 items): Improve embedding search (more candidates, German synonym expansion) and tune LLM triage prompt to be less conservative
2. **Clean up data noise**: Filter out empty titles, marketing headlines, place names before they enter owl_pending
3. **Delete pending_id=2**: Empty title data bug

### Open Questions for Sandy

- Which dimension to tackle first? Hours/contract-type is lowest-hanging fruit (often explicit in text). "Works mostly with" is most interesting but hardest.
- Should Pattern C items get `berufenet_id = NULL` permanently (accepted gap), or do we want a fallback taxonomy?
- How important is berufenet classification for the matching algorithm vs. the new dimensions?
- Should we build a "closest approximate" mode — e.g. map KYC Associate → Bankkaufmann/-frau with a confidence flag?

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
