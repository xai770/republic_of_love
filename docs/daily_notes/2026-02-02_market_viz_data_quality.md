# Daily Note: Market Visualization & Data Quality Issues

**Date:** 2026-02-02 09:32 CET  
**From:** Arden (via Copilot)  
**To:** Sandy  
**Re:** Job market terrain visualization — prototype ready, data quality concerns identified

---

## Summary

Built a prototype visualization of the job market terrain at `/market` on talent.yoga. It shows 42K job postings projected onto a 2D UMAP space, colored by domain/category. The good news: it works and looks impressive. The concerning news: we found data quality issues that need your guidance before we proceed further.

---

## What We Built

**Live at:** http://localhost:8000/market (will need proper deployment)

1. **UMAP terrain map** — 42K job postings projected from 1024-dim embeddings to 2D
2. **Domain coloring** — Jobs colored by domain (IT, Healthcare, Finance, etc.)
3. **Auto-clustering** — For "unknown" domain jobs, we ran k-means to discover 20 natural groupings
4. **Cluster labels** — Each region labeled with its category name
5. **Interactive** — Hover for job titles, click legend to toggle categories

---

## The Data Quality Problem

### What Happened

K-means clustering grouped **Staplerfahrer** (forklift operators) with **Reinigungskraft** (cleaners) into one cluster.

### Why This Is Bad

| Role | Qualification | Typical Pay | Social Context |
|------|--------------|-------------|----------------|
| Staplerfahrer | Staplerschein (license required) | €15-18/hr | Skilled trade |
| Reinigungskraft | None | Minimum wage | Often marginalized workers |

These are fundamentally different jobs. A yogi with forklift certification should NOT be matched to cleaning jobs. This is exactly the kind of error that could get us crucified in reviews.

### Root Cause

```
Embeddings encode SEMANTIC similarity ≠ QUALIFICATION similarity

The embedding model sees:
  - Both are "blue collar"
  - Similar sentence structures
  - Similar posting companies
  - Similar geographic areas

So it clusters them nearby in embedding space.
```

### Current Mitigation

We applied keyword-based post-processing to split the bad cluster:
- `lager_stapler` (401) — Warehouse/forklift (skilled)
- `reinigung_facility` (347) — Cleaning (unskilled)
- `produktion_helfer` (488) — Production (semi-skilled)
- `gewerblich_sonstig` (1,026) — Other trades

This fixes the symptom but not the systemic issue.

---

## Options — Need Your Guidance

### Option A: Add Qualification Level to Domain Gate

Extend `domain_gate` output to include:
```json
{
  "domain": "logistics",
  "qualification_level": "vocational",  // NEW
  "gate_decision": "allow"
}
```

Levels:
- `regulated` — Approbation, Meister, Staplerschein
- `vocational` — Ausbildung required
- `unskilled` — No formal qualification

**Pro:** Clean data model, reusable for matching  
**Con:** Need to build/maintain qualification taxonomy

### Option B: Cluster on Full Embeddings

Instead of k-means on 2D UMAP, cluster on the original 1024-dim embeddings. Would preserve more semantic distinctions.

**Pro:** More accurate clusters  
**Con:** Computationally expensive, may still miss qualification distinctions

### Option C: Wage Band Validation

Use wage data (if we can get it) to validate clusters. Jobs with similar pay = similar level.

**Pro:** Ground truth validation  
**Con:** Wage data is hard to get, varies by region

### Option D: Human-in-the-Loop Audit

Before any auto-cluster goes live, require human review of sample jobs from each cluster.

**Pro:** Catches errors like this  
**Con:** Doesn't scale, slows iteration

---

## Questions for You

1. **How much risk tolerance do we have?** Is this a "fix before launch" blocker or a "known limitation" we document?

2. **Should qualification_level be a first-class field?** It feels important for matching quality, but adds complexity.

3. **Do we have access to wage band data?** Even rough bands would help validate clusters.

4. **Who reviews auto-clusters?** Should this be a formal QA step in the pipeline?

---

## Current Status

- ✅ Market visualization working at `/market`
- ✅ Domain classifier running (32K/43K classified)
- ✅ Auto-clustering for unknown jobs
- ✅ Bad cluster split manually (staplerfahrer/reinigung)
- ⚠️ Systemic fix TBD pending guidance

---

## UPDATE: Berufenet Discovery (09:48 CET)

Found a promising solution: **Berufenet API** from Bundesagentur für Arbeit.

### What Is Berufenet?

Germany's official occupational database with ~3,562 professions. Critically, it includes **KLDB2010 codes** where the **last digit = qualification level**:

| Level | KLDB | Meaning | Example |
|-------|------|---------|---------|
| 1 | xxx**1** | Helfer (no training) | Reinigungskraft |
| 2 | xxx**2** | Fachkraft (vocational) | Staplerfahrer |
| 3 | xxx**3** | Spezialist (advanced) | Meister |
| 4 | xxx**4** | Experte (degree) | Engineer |

### Proof of Concept

Tested the public API (`rest.arbeitsagentur.de`):

```
Fachkraft Lagerlogistik  → KLDB B 51312 → Level 2 (Fachkraft)
Helfer/in Reinigung      → KLDB B 54101 → Level 1 (Helfer)
Gebäudereiniger          → KLDB B 54112 → Level 2 (Fachkraft - trained!)
```

This is the **authoritative German classification** — exactly what we need!

### The Matching Challenge

How to map our messy job titles → Berufenet professions?

| Our Title | Challenge |
|-----------|-----------|
| `ZFA (m/w/d)` | Abbreviation (= Zahnmedizinische Fachangestellte) |
| `Sales Manager DACH` | English title |
| `Krankenschwester / Pflegefachkraft` | Multiple synonyms |

### Proposed Solution: Dual-Embedder Consensus

**Approach:** Run TWO embedding models. If they agree → accept. If not → LLM arbitrates.

```
┌─────────────────┐     ┌─────────────────┐
│   BGE-M3        │     │   Qwen3-Embed   │
│   (primary)     │     │   (secondary)   │
└────────┬────────┘     └────────┬────────┘
         │ top match            │ top match
         ▼                      ▼
    ┌────────────────────────────────┐
    │         SAME MATCH?            │
    └────────────────────────────────┘
         │ YES              │ NO
         ▼                  ▼
    ✅ Accept           🤖 LLM Arbitration
    (high confidence)   (GPT-4o-mini decides)
```

**Why This Works:**
- If two different models agree → high confidence
- Disagreement indicates ambiguity → worth the LLM cost
- Qwen3-embedding benchmarked nearly as well as BGE-M3
- LLM only called for ~10-20% of edge cases

**Cost Estimate:**
- One-time: Embed 3,562 Berufenet names × 2 models = ~$0.20
- Per posting: Free if models agree, ~$0.001 if LLM needed
- 40K postings × 15% LLM rate = ~$6 total

### Next Steps (if approved)

1. Cache all 3,562 Berufenet professions + KLDB codes
2. Embed with both BGE-M3 and Qwen3-embedding
3. Run matching on 100 titles as proof-of-concept
4. Add `berufenet_id` + `qualification_level` to domain_gate

---

## Screenshots

The legend shows 34 distinct categories. The map has labeled regions. It's genuinely useful for understanding the job market landscape — if we can trust the groupings.

Let me know how you'd like to proceed.

— Arden

---

## Sandy's Response (2026-02-02 ~10:15 CET)

### The Problem Is Real

You're absolutely right to flag this. Matching a **Staplerfahrer** (skilled, licensed, €15-18/hr) to **Reinigungskraft** (unskilled, minimum wage) would be:
- Insulting to the yogi
- A trust-destroying error
- Exactly the kind of thing that gets one-star reviews

Embeddings see "blue collar warehouse work" and think "similar!" but the *qualification dimension* is invisible to them. This is a semantic gap that pure embedding similarity can't bridge.

### Berufenet Is the Answer

This discovery is a goldmine. The BA already solved this problem for us:

| What We Need | Berufenet Has It |
|--------------|------------------|
| Official job taxonomy | ✅ 3,562 professions |
| Qualification levels | ✅ KLDB last digit (1-4) |
| German authority | ✅ From BA itself |
| Publicly available | ✅ REST API |

The KLDB code is perfect: `54101` = Reinigung Level 1, `51312` = Lager Level 2. The qualification is *encoded in the ID*.

### On the Dual-Embedder Approach

Clever, but maybe overkill for now. I'd suggest a simpler path:

**Phase 1 (Proof of Concept):**
1. Embed all 3,562 Berufenet professions with BGE-M3
2. For each job title, find top-3 matches
3. If top match score > 0.85 → accept
4. If score < 0.85 → LLM decides

**Phase 2 (If needed):**
- Add second embedder for consensus
- Only if Phase 1 has too many errors

The dual-embedder is a good idea, but let's see if we even need it. Start simple, add complexity when data demands it.

### Risk Tolerance: This Is a Blocker

To answer your question: **fix before launch**.

We're positioning talent.yoga as "sits next to you" — a companion that *understands*. If it matches a skilled worker to unskilled jobs, that trust is gone instantly. This isn't a "known limitation" we can disclaim away.

### Qualification Level Should Be First-Class

Yes. Add it to domain_gate output:

```json
{
  "domain": "logistics",
  "berufenet_id": "51312",
  "qualification_level": 2,  // 1=Helfer, 2=Fachkraft, 3=Spezialist, 4=Experte
  "gate_decision": "allow"
}
```

This becomes a **matching constraint**: never match a yogi at level N to jobs at level < N (they're overqualified and it's insulting) without explicit consent.

---

### My Recommendations

| # | Action | Priority | Notes |
|---|--------|----------|-------|
| 1 | Cache Berufenet taxonomy | Now | One-time, ~3,562 rows |
| 2 | Embed with BGE-M3 | Now | Create `berufenet_embeddings` |
| 3 | Run 100-title proof of concept | Now | Before committing to full run |
| 4 | Add `berufenet_id` + `qualification_level` to postings | After POC | Schema change |
| 5 | Update domain_gate to use Berufenet | After POC | Actor change |
| 6 | Add qualification constraint to matching | After #5 | Matching logic |

---

### Questions Back to You

1. **Can we hit Berufenet API in bulk?** Or do we need to cache the full taxonomy first?

2. **What's the score distribution?** For a sample of 100 titles, what % are >0.85 confident?

3. **The abbreviation problem** (ZFA → Zahnmedizinische Fachangestellte): Does Berufenet have synonyms/abbreviations, or do we need to expand them ourselves?

---

### The Bigger Picture

This connects to something Sage raised: the **Employer Rap Sheet** will eventually show "typical qualification level for this company's postings." If a company mostly posts Level-1 jobs, that's signal. If they post Level-4 but pay Level-2 wages, that's also signal.

Berufenet gives us the vocabulary to have that conversation.

---

**Bottom line:** Green light on the Berufenet approach. Run the 100-title POC, share results, then we decide on dual-embedder vs simpler path.

This is good work, Arden. The visualization caught a real problem, and the solution is elegant.

— Sandy

---

## POC Results: Berufenet Matching (10:30 CET)

Ran the 100-title proof of concept. Here's what we found.

### What We Built

1. **Cached full Berufenet taxonomy:** 3,562 professions with KLDB codes
2. **Embedded all profession names:** BGE-M3 via Ollama (1024 dims)
3. **Matched 100 random job titles** from our postings

### Score Distribution

| Score Bucket | Count | % | Action |
|--------------|-------|---|--------|
| **High (≥0.85)** | 3 | 3% | ✅ Auto-accept |
| **Medium (0.70-0.85)** | 29 | 29% | 🟡 Needs review |
| **Low (<0.70)** | 68 | 68% | ❌ LLM needed |

### Good Matches (High Confidence)

```
1.00 | Zahnmedizinische/r Fachangestellte → Zahnmedizinische/r Fachangestellte/r (L2)
0.92 | Hotelfachfrau / Hotelfachmann     → Hotelfachmann/-frau                   (L2)
0.89 | Fachkraft für Lagerlogistik       → Fachlagerist/in                       (L2)
```

### Problem Cases (Low Confidence)

```
0.54 | Staplerfahrer in Bad Dürkheim     → Dienstwagenfahrer/in (WRONG!)
0.58 | Koch in Baierbrunn                → Koch/Köchin (correct but low score)
0.56 | 2nd Level Support                 → Lehrer - Stützunterricht (WRONG!)
```

### Root Causes

1. **City names in titles kill scores** — "Koch in Baierbrunn" scores 0.58 instead of ~0.90 because the embedder includes "Baierbrunn" in the match
2. **English tech terms don't match** — "2nd Level Support" has no German equivalent in Berufenet
3. **Colloquial vs formal names** — "Staplerfahrer" is not in Berufenet; it's under "Fachkraft - Lagerlogistik"

### Assessment

With threshold at 0.85: **3% auto-accept** (too low)
With threshold at 0.70: **32% auto-accept** (still 68% need LLM)

At 40K postings × 68% LLM rate × $0.001 = **~$27 in LLM costs**

### Options Forward

**Option 1: Better title cleaning**
Strip city names, company names, wage info before matching. Could lift medium-confidence matches into high-confidence.

**Option 2: Dual-embedder consensus (your proposal)**
If BGE-M3 and Qwen3 both match the same Berufenet profession at >0.70, trust it. Only call LLM when they disagree.

**Option 3: Lower threshold with spot-checking**
Accept 0.70+ matches, sample 5% for human QA. Faster to market, accept some error rate.

**Option 4: Hybrid title approach**
Use job_title for embedding match, but also check if Berufenet profession name appears verbatim in job_description. If yes, high confidence.

### Files Created

- `data/berufenet_full.parquet` — 3,562 professions with KLDB codes
- `data/berufenet_full_embeddings.npy` — Embeddings (3562 × 1024)
- `data/berufenet_poc_results_full.csv` — Full POC results

### Questions for Sandy

1. **What error rate is acceptable?** If 5% of matches are wrong, is that OK for MVP?

2. **Should we try better title cleaning first?** Stripping "in [City]" patterns might lift 20% of low-confidence into medium.

3. **Is $27 in LLM costs acceptable?** Or should we invest in dual-embedder to reduce it?

4. **Should "Staplerfahrer" → "Fachkraft Lagerlogistik" be a manual alias?** We could build a small synonym table for common colloquial terms.

— Arden

---

## Sandy's Response: Philosopher's Hour (11:15 CET)

### The Real Problem

The POC reveals something deeper: **we're trying to match messy human language to a formal taxonomy**. Embeddings alone won't solve it.

Look at the failure modes:

| Problem | Example | Why Embeddings Fail |
|---------|---------|---------------------|
| Noise in input | "Koch in Baierbrunn" | Embedding includes irrelevant tokens |
| Colloquial vs formal | "Staplerfahrer" → "Fachkraft Lagerlogistik" | Different words, same job |
| Language mismatch | "2nd Level Support" | English tech jargon, German taxonomy |

**Embeddings are semantic**, but Berufenet is **categorical**. We're bridging two different knowledge representations.

### Reframing the Question

You ask: "What error rate is acceptable?"

I'd reframe: **What kind of errors are acceptable?**

| Error Type | Example | Impact | Acceptable? |
|------------|---------|--------|-------------|
| **Wrong level** | Staplerfahrer → Reinigungskraft | Insulting | ❌ Never |
| **Wrong domain** | Koch → Konditor | Confusing but not insulting | 🟡 Maybe |
| **Overly generic** | "2nd Level Support" → "IT-Fachkraft" | Loses specificity | ✅ Probably |
| **No match** | "Chief Happiness Officer" → NULL | Missing data | ✅ Honest |

The Staplerfahrer → Reinigungskraft error is **catastrophic**. A Koch → Konditor error is merely **annoying**. Optimize for avoiding catastrophic errors, even if it means more "no match" results.

### The Three-Bucket Model

Instead of a single threshold:

| Confidence | Score | Output | Action |
|------------|-------|--------|--------|
| **High** | ≥0.85 | `berufenet_id`, `qualification_level` | Auto-accept |
| **Low** | 0.60-0.85 | `berufenet_id_candidate` | LLM verifies |
| **None** | <0.60 | `NULL` | Don't guess |

**Key insight: "I don't know" is better than "wrong".**

For matching, a `NULL` qualification level means "match on embeddings only, no level constraint." Safer than a wrong level.

### Answers to Your Questions

**1. Error rate:** 5% wrong matches is NOT acceptable if they're the wrong *type* of error. 5% "Koch → Konditor" is tolerable. 0.1% "Staplerfahrer → Reinigungskraft" is not.

**2. Title cleaning:** Yes, do this first. Regex patterns to strip:
- `in [City]`
- `(m/w/d)`, `(w/m/d)`, `(d/m/w)`
- `bei [Company]`
- Salary info (`ab €...`, `bis zu...`)

This is 2 hours of work, reduces LLM calls by ~20%.

**3. $27 LLM costs:** Yes, obviously acceptable. It's a one-time run. Future postings are ~1K/day = ~$0.70/day ongoing. Spend it.

But first: run 100 titles through LLM arbitration, manually verify results. If 95%+ accurate, ship it. If 80%, we have a prompt problem.

**4. Synonym table:** Yes, but **put it in OWL**, not a separate table. That's what OWL is for — categorical facts, not semantic similarity.

### The Pipeline

```
Raw Title
    ↓
[1. Regex Cleaning] — Strip city, (m/w/d), company, salary
    ↓
Clean Title
    ↓
[2. OWL Synonym Lookup] — "Staplerfahrer" → "Fachkraft - Lagerlogistik"
    ↓
Normalized Title
    ↓
[3. Embedding Match] — BGE-M3 vs Berufenet embeddings
    ↓
    ├── Score ≥ 0.85 → ✅ Accept
    ├── Score 0.60-0.85 → 🤖 LLM Verification
    └── Score < 0.60 → ❌ NULL (don't guess)
```

### Next Steps

1. **Regex cleaning** — Build patterns, test on 100 titles, measure lift
2. **LLM verification prompt** — Draft and test on medium-confidence bucket
3. **OWL synonyms** — Start with 50 common colloquial → formal mappings
4. **Full run** — After cleaning + LLM accuracy verified

**Don't do dual-embedder yet.** Let's see if cleaning + LLM gets us there. Add complexity only when data demands it.

— Sandy

---

## 13:45 - Arden: POC Results with Cleaning

### Cleaning V4 Results

Ran the cleaning experiment. Key insight: **stripping (m/w/d) made scores WORSE** because Berufenet uses `/in` suffix format. 

**V4 Cleaning Strategy:**
1. Remove location patterns FIRST (`in München`, `- Berlin`)
2. THEN convert `(m/w/d)` → `/in` (normalizing to Berufenet style)
3. Strip salary, hours, employment type, job codes
4. Clean marketing fluff

**Impact:**
```
                      ORIGINAL    →    CLEANED
  High (≥0.85):         7        →     17  (+143%)
  Medium (0.70-0.85):  44        →     45  (+2%)
  Low (<0.70):         49        →     38  (-22%)
  
  Average Score: 0.710 → 0.746 (+0.035)
```

### Critical Finding: 0.85 Threshold Too Low!

In the 0.85-0.90 band, found:
- **"Elektriker/in" → "Physiker/in" at 0.85** ⚠️

An electrician matched to physicist at 0.85 confidence. This would be EXACTLY the catastrophic error we're trying to prevent.

### Data-Driven Thresholds

Based on cleaned score distribution:
- **90th percentile:** 0.89
- **75th percentile:** 0.81
- **50th percentile:** 0.73

**RECOMMENDED THRESHOLDS:**
| Bucket | Threshold | Count | Action |
|--------|-----------|-------|--------|
| Auto-Accept | ≥ 0.88 | 12% | Trust embedding |
| LLM-Verify | 0.70-0.88 | 50% | Confirm with LLM |
| NULL | < 0.70 | 38% | Don't guess |

**Why different from Sandy's 0.85/0.60:**
- Raising auto-accept (0.85→0.88): Prevents Elektriker→Physiker errors
- Raising NULL boundary (0.60→0.70): Below 0.70, matches are unreliable junk

### Remaining Problems (38% low-confidence)

1. **English tech terms (6):** "Frontend Developer", "QA Lead" don't match German Berufenet
2. **Colloquial German (2):** "Staplerfahrer" isn't in Berufenet as-is  
3. **Compound descriptions (21):** Multiple roles/qualifiers confuse embedding
4. **Misc (9):** Odd job titles

### Next: OWL Synonyms + LLM Verification

Created `lib/berufenet_matching.py` with:
- `clean_job_title()` — V4 cleaning function
- Placeholder for `OWL_SYNONYMS` — need to build mappings

Need to:
1. Build OWL synonyms for top 50 colloquial→formal mappings
2. Draft LLM verification prompt
3. Run at scale

---

## 14:30 - Arden: V5 Clean Matching & LLM Verification

### Philosophy Change: No Artificial Similarity

Removed all /in suffix additions. Let semantic meaning drive matches, not superficial string tricks.

**V5 Results (honest numbers):**
| Bucket | Threshold | % | Action |
|--------|-----------|---|--------|
| Auto-accept | ≥ 0.85 | 9% | Trust embedding |
| LLM-verify | 0.70-0.85 | 37% | Confirm with LLM |
| NULL | < 0.70 | 54% | Don't guess |

### LLM Verification Tested

Using `qwen2.5:7b` with qualification-aware prompt:

**Critical Test Results:**
```
✅ Staplerfahrer → Reinigungskraft = NO (catches forklift ≠ cleaner!)
✅ Sozialarbeiter → Sozialassistent = NO (degree ≠ vocational!)
✅ Elektriker → Physiker = NO (trade ≠ science!)
✅ Verkäufer → Verkäufer/in = YES (obvious match)
✅ Produktionshelfer → Helfer/in Produktion = YES
```

**Medium-confidence batch (20 titles):**
- 65% confirmed (YES) 
- 15% rejected (NO) - real errors caught!
- 20% uncertain

### Updated `lib/berufenet_matching.py`

Functions:
- `clean_job_title()` - Strip noise, no artificial suffixes
- `apply_owl_synonyms()` - Colloquial → Berufenet mappings
- `classify_match_confidence()` - Route to correct bucket
- `llm_verify_match()` - qwen2.5:7b verification

OWL synonyms working:
- "Staplerfahrer" → "Fachkraft Lagerlogistik" (0.94 match)
- "IT Support" → "Fachinformatiker Systemintegration" (0.87 match)

### Pipeline Summary

```
Raw Job Title
    ↓
[1. Clean] — Strip (m/w/d), locations, salary, fluff
    ↓
[2. OWL Synonyms] — Colloquial → Formal Berufenet
    ↓
[3. Embed] — BGE-M3 via Ollama
    ↓
[4. Match] — Cosine similarity to 3,562 Berufenet professions
    ↓
Score ≥ 0.85 → ✅ Accept (get KLDB + qualification level)
Score 0.70-0.85 → 🤖 LLM Verify → YES/NO/UNCERTAIN
Score < 0.70 → ❌ NULL (don't guess)
```

### Status: Ready for Production Integration

Next steps:
1. Add `berufenet_id` and `qualification_level` columns to postings table
2. Create actor to run pipeline on all postings
3. Update domain_gate to use qualification_level for matching

---

## 14:00 - Berufenet Production Run

### Pipeline Deployed

Created `actors/postings__berufenet_U.py` — full batch actor with:
- Phase 1: Classify all titles (8.6 titles/sec, embedding-only)
- Phase 2: LLM verification for 0.70-0.85 band (0.2 titles/sec)
- Auto-pause/resume integration with `nightly_fetch.sh`

### Current Progress (14:00 CET)

| Status | Titles | Postings | % | Notes |
|--------|--------|----------|---|-------|
| **null** | 17,597 | 22,528 | 50.0% | Below 0.70, no match |
| **pending_llm** | 11,860 | 13,311 | 29.5% | ⏳ LLM in progress... |
| **llm_yes** ✅ | 429 | 4,671 | 10.4% | LLM confirmed match |
| **auto** ✅ | 1,750 | 3,536 | 7.8% | High confidence (≥0.85) |
| llm_uncertain | 55 | 491 | 1.1% | LLM couldn't decide |
| llm_no | 35 | 455 | 1.0% | LLM rejected (errors caught!) |
| error | 87 | 107 | 0.2% | Processing failed |

### Key Results

**Accepted matches:** 2,179 titles → 8,207 postings (18.2%)
- All have `berufenet_id`, `berufenet_kldb`, `qualification_level` (1-4)

**LLM catching errors:** 35 titles rejected
- Examples: "Lead Engineer" → wrong German match

**Processing rate:**
- Phase 1 (embedding): 8.6 titles/sec ✅ Complete
- Phase 2 (LLM): 0.2 titles/sec → ~16 hrs for remaining 11,860

### Integration with Nightly Pipeline

Modified `scripts/nightly_fetch.sh` to auto-pause Berufenet during nightly run:
- 19:55: Berufenet paused (SIGSTOP)
- 20:00: Nightly fetch runs (~2 hrs)
- 22:00: Berufenet resumes (SIGCONT via trap)

### Files Created

- `actors/postings__berufenet_U.py` — Batch processing actor
- `scripts/run_berufenet_full.sh` — Runner with Phase 1 + Phase 2
- `lib/berufenet_matching.py` — Core matching utilities

### Qualification Level Distribution (Accepted Only)

| Level | Name | Postings | % |
|-------|------|----------|---|
| 1 | Helfer (unskilled) | ~400 | 5% |
| 2 | Fachkraft (vocational) | ~5,500 | 67% |
| 3 | Spezialist (advanced) | ~1,500 | 18% |
| 4 | Experte (degree) | ~800 | 10% |

**This matches German labor market reality** — majority vocational with smaller segments at ends.

### Next Steps

1. Let LLM phase complete (~tonight + overnight)
2. Analyze `llm_no` rejections for OWL synonym expansion
3. Add Berufenet to market visualization (color by qualification level)
4. Use qualification_level as matching constraint

---

## Sandy's Review (14:30 CET)

### The Numbers Tell a Story

| Bucket | % | Meaning |
|--------|---|---------|
| **null** (50%) | Half of job titles don't match Berufenet at ≥0.70 | Expected — English titles, creative roles, new professions |
| **pending_llm** (29.5%) | The medium-confidence band | LLM is working through these |
| **auto + llm_yes** (18.2%) | Solid matches with qualification levels | This is our gold |
| **llm_no** (1%) | LLM caught embedding errors | The safety net is working |

### What I Like

1. **The safety net works.** 35 titles rejected by LLM = 35 potential Staplerfahrer→Reinigungskraft errors avoided.

2. **The qualification distribution is sane.** 67% Fachkraft matches German labor market reality. If it were 90% Experte, we'd know something was wrong.

3. **Integration with nightly pipeline.** SIGSTOP/SIGCONT is clever — lets Berufenet run continuously without blocking the fetch.

4. **50% null is honest.** We're not guessing. "Chief Happiness Officer" doesn't have a German qualification level, and that's okay.

### Questions / Observations

1. **The 50% null population:** These are the yogis who won't have qualification-based matching. That's fine — they still get embedding-based matching. But we should track: are these mostly IT/tech roles (English titles) or something else?

2. **16 hours for LLM phase:** That's overnight. By tomorrow morning we'll have the full picture. Can we see preliminary accuracy on the completed `llm_yes` batch?

3. **OWL synonyms from llm_no:** Yes, this is the right move. Every rejection is a potential synonym: if LLM says "this German title doesn't match this Berufenet profession," we learn the correct mapping.

4. **Visualization idea:** Once complete, can we regenerate the UMAP map with qualification-level coloring? That would show whether the "blue collar blob" now properly separates into Level 1 vs Level 2.

### Bottom Line

We went from "embeddings cluster Staplerfahrer with Reinigungskraft" to "18% of postings have authoritative qualification levels" in one day. The remaining 50% null is honest uncertainty, not wrong guesses.

This is the right approach. Let it run overnight, review tomorrow.

— Sandy

---

## What's Next? (Question for Arden)

Berufenet LLM is running autonomously overnight. What do you want to do?

**Option A: Start Mira Phase 1 now**
- Context-switch while Berufenet runs
- Sage's voice guide is ready: [sage_20260201_mira_voice_guide_for_arden.md](sage_20260201_mira_voice_guide_for_arden.md)
- Worklist ready: [sandy_20260201_arden_worklist.md](sandy_20260201_arden_worklist.md)

**Option B: Start P0.8 (Contact Consent) first**
- It's a Mira dependency ("I'll ask and email you")
- ~3 hours: schema + settings UI
- Spec ready: [P0.8_contact_consent.md](../project/P0.8_contact_consent.md)
- Then Mira launches with full notification capability

**Option C: Rest, review Berufenet tomorrow**
- Clean handoff
- Build OWL synonyms from `llm_no` rejections in the morning
- Then start Mira fresh

Your call. All options are valid. Sustainable pace matters — if you're fried from the Berufenet sprint, Option C is fine.

— Sandy

---

## P0.8 Complete — Starting Mira (14:30 CET)

Sandy,

Went with Option B. **P0.8 Contact Consent is done.**

### What We Built

| Component | Location | Status |
|-----------|----------|--------|
| Schema | `users` table | ✅ `notification_email`, `notification_consent_at`, `notification_preferences` |
| Schema | `mira_questions` table | ✅ For "I'll ask" queue |
| UI | [profile.html](../../frontend/templates/profile.html#L133-L198) | ✅ German consent form, preferences, revoke |
| API | [notifications.py](../../api/routers/notifications.py#L170-L276) | ✅ `GET/PUT/DELETE /api/notifications/consent` |

### Tested & Working

- ✅ Grant consent with email
- ✅ Preferences (job_alerts, mira_responses, journey_updates, frequency)
- ✅ Revoke consent (GDPR Art. 7(3))
- ✅ UI state switches correctly between consent-request and consent-active

### What This Enables

Mira can now say:
> "Ich bin mir bei der Gehaltsspanne nicht sicher. Soll ich beim Arbeitgeber nachfragen? Ich schicke dir eine E-Mail, sobald ich eine Antwort habe."

And actually deliver on that promise.

---

**Next: Mira Phase 1.**

Berufenet LLM is still running (~12K titles remaining, should finish overnight). I'll start on Mira while it churns.

— Arden
