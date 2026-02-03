# talent.yoga Scaling Analysis

**Date:** 2026-01-25 (Sunday)  
**Author:** Arden  
**Purpose:** Understand processing times for capacity planning

---

## Executive Summary

| Operation | Time | Can be Offline? |
|-----------|------|-----------------|
| **Process 1 posting** | ~25-30s | ✅ Yes (batch) |
| **Process 1 profile** | ~10-15s | ✅ Yes (batch) |
| **Show matches to new user** | **~2s** | ❌ Online (instant!) |
| **Analyze 1 match (1st user)** | ~8s | ❌ Online (on-demand) |
| **Analyze same match (2nd user)** | **~0.1-2s** | ❌ Online (cached!) |

**Key Insights:**
1. Two-tier architecture - embeddings for screening (instant), LLM for analysis (on-demand)
2. Cross-user caching - posting analysis is universal, only personalization varies
3. 100 users analyzing same posting: 800s → 11s (**98.6% savings**)

**Hardware:** Intel NUC with NVIDIA GPU (local Ollama)

---

## 1. Posting Pipeline

```
job_description → extracted_summary → extracted_requirements → posting_facets
    (5,415 chars)     (1,073 chars)        (~700 chars)        (7.4 facets)
```

### Actors & Timing

| Step | Actor | Model | Estimated Time |
|------|-------|-------|----------------|
| 1. Fetch posting | `postings__row_CU.py` | - | ~1s (API call) |
| 2. Extract summary | `postings__extracted_summary_U.py` | qwen2.5-coder:7b | ~7-10s |
| 3. Extract requirements | `postings__extracted_requirements_U.py` | qwen2.5-coder:7b | ~7-10s |
| 4. Create facets | `posting_facets__row_C.py` | qwen2.5-coder:7b + qwen2.5:7b | ~10-15s (with retry) |
| **Total per posting** | | | **~25-35s** |

### Current Stats
- 2,202 postings with summaries
- 2,009 postings with facets
- 14,896 total posting_facets (avg 7.4 per posting)
- 5,303 unique requirement terms

### Scaling Notes
- **GPU bound:** Each step loads model, processes, unloads
- **Optimization:** Model-first batching (directive #7) - load model once, exhaust all work
- **Offline OK:** Deutsche Bank API checked daily; batch processing overnight works fine

---

## 2. Profile Pipeline

```
profile_work_history → Clara extract → Diego enrich → profile_facets
    (17 jobs × 186 chars)                              (315 facets)
```

### Actors & Timing

| Step | Actor | Model | Estimated Time |
|------|-------|-------|----------------|
| 1. Extract facets | `profile_facets__extract_C__clara.py` | qwen2.5:7b | ~5-8s per job |
| 2. Add enablers | `profile_facets__enrich_U__diego.py` | None (rules) | ~0.1s |
| **Total per profile (17 jobs)** | | | **~85-140s** |

### Current Stats
- 1 profile fully processed (profile_id=1)
- 17 work history entries
- 315 profile_facets (94 unique skills)
- Diego adds implied skills based on domain/seniority/role

### Scaling Notes
- **Per-job processing:** Each job in work history processed separately
- **Offline OK:** Profile import is manual; batch overnight
- **Typical profile:** 5-15 jobs → 25-120s total processing

---

## 3. Matching: Profile ↔ Posting

```
profile_facets (94 skills) × posting_facets (5 requirements)
                    ↓
         embedding similarity matrix
                    ↓
         LLM analysis → recommendation
```

### Components & Timing

| Component | Before DB Cache | After DB Cache | Notes |
|-----------|-----------------|----------------|-------|
| Load profile/posting data | 0.01s | 0.01s | DB query |
| Compute embedding matrix | ~10s | **~1.8s** | 5,334 embeddings cached |
| LLM analysis (qwen2.5:7b) | ~8-14s | ~5-10s | Warm model |
| **Total per match** | ~18-24s | **~7-12s** | |

### Test Results (with cache)
```
posting 11143: 10.0s - skip
posting 12656: 11.5s - apply
posting 13800: 5.6s - skip
posting 13960: 5.3s - skip
```

### Current Stats
- 26 matches computed for profile_id=1
- 5,334 embeddings in `embeddings` table
- Single embedding lookup: ~0.1s (computed) or ~0.001s (cached)

### Embedding Strategy
Embeddings are stored **per unique text**, not per profile or posting:
- "Python" appears in 100 profiles? Still 1 row in `embeddings`
- This is why 5,334 rows cover all 5,303 posting requirements + 94 profile skills
- New skills get computed once, then cached forever

---

## 4. Scaling Scenarios

### Scenario A: 100 new postings/day
| Step | Time | When |
|------|------|------|
| Fetch 100 postings | ~2 min | Morning |
| Process summaries | ~15 min | Overnight batch |
| Process requirements | ~15 min | Overnight batch |
| Create facets | ~25 min | Overnight batch |
| **Total** | **~1 hour** | **Offline, overnight** |

### Scenario B: New user signs up
| Step | Time | When |
|------|------|------|
| Import profile (manual) | ~1 min | Online |
| Extract facets (10 jobs) | ~1-2 min | Can wait |
| Match against 2,000 postings | ~4-7 hours | **Problem!** |

### Scenario C: Match on demand (user clicks "Find Matches")
- With warm cache + warm LLM: **~5-10s per match**
- User wants top 50? That's **4-8 minutes wait** ❌

---

## 5. The Key Insight: Embeddings vs LLM

### What Does the LLM Actually Do?

Analyzed 28 matches for profile_id=1:

| Embedding Score | LLM Says | Agreement? |
|-----------------|----------|------------|
| 0.91 | **SKIP** | ✗ Disagree |
| 0.86 | **SKIP** | ✗ Disagree |
| 0.85 | apply | ✓ |
| 0.84 | apply | ✓ |
| ... | ... | ... |
| 0.50 | **APPLY** | ✗ Disagree |

**Result: 75% agreement, 25% disagreement**

### Why the Disagreement?

**Case Study: Match 8 (embedding=0.91, LLM=SKIP)**
- Job: Finance Business Advisor
- Embedding matched "Budgeting" ↔ "Financial Analysis" (high similarity)
- LLM caught the nuance: *"Gershon lacks critical financial analysis expertise... His budgeting experience is in contract compliance context, not banking finance"*

**The fundamental difference:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  EMBEDDINGS answer: "How similar are these skill WORDS?"            │
│                                                                     │
│  LLM answers:       "Given this PERSON and this JOB, should they    │
│                      actually apply?"                               │
└─────────────────────────────────────────────────────────────────────┘
```

### What the LLM Produces

1. **Decision override** - Catches nuance embeddings miss (25% of cases)
2. **Reasoning** - go_reasons / nogo_reasons (explainability)
3. **Actionable content** - Cover letter OR nogo narrative

---

## 6. The Two-Tier Architecture (Recommended)

### The Problem
- New user signs up → match against 2,000 postings → **4-7 hours wait** ❌

### The Solution: On-Demand LLM

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1: Embedding Screening (INSTANT)                              │
│    - Compute embedding matrix for all postings                      │
│    - Show user "Potential Matches" ranked by embedding score        │
│    - Time: ~2 seconds total (with cache)                            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                    User clicks "View Details"
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 2: LLM Analysis (ON-DEMAND, 5-10s)                            │
│    - Call LLM for THIS specific match                               │
│    - Generate: recommendation, go/nogo reasons, cover letter        │
│    - Cache result for future views                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### User Experience

| Step | What User Sees | Time |
|------|----------------|------|
| 1. Sign up | Welcome screen | - |
| 2. Import profile | "Processing your profile..." | ~1-2 min |
| 3. View matches | **50 potential matches instantly!** | **~2s** |
| 4. Click on match | "Analyzing this opportunity..." | ~8s |
| 5. See details | Cover letter + go/nogo reasons | cached |

### Why This Works

1. **New user onboarding is instant** - They see matches in seconds
2. **LLM time is user-driven** - Only burn GPU when user actually cares
3. **Cover letters are just-in-time** - Generated when needed
4. **Results are cached** - Click twice? Instant second time

### Storage Impact

| Approach | Matches Stored | LLM Calls |
|----------|----------------|-----------|
| **Old: Batch all** | 2,000 × full analysis | 2,000 |
| **New: On-demand** | 2,000 × embedding score | ~50 (user clicks) |

---

## 7. Cross-User Caching: The Multiplier Effect

### The Insight

User A and User B both have similar skills (Python, SQL, AWS). When they analyze the same posting... **why run the LLM twice?**

Current reality:
```
User A clicks "Analyze" on Posting X → 8s LLM → analysis
User B clicks "Analyze" on Posting X → 8s LLM → almost identical analysis!
```

### Decomposing the LLM Work

| Component | Per-Posting? | Per-User? | Cacheable? |
|-----------|--------------|-----------|------------|
| **Posting requirements analysis** | ✓ | ✗ | ✅ Cache per posting |
| **"Ideal candidate" description** | ✓ | ✗ | ✅ Cache per posting |
| **Skill gap reasoning** | ✓ | ~partial | ✅ Cache per pattern |
| **Go/NoGo decision** | ✓ | ✓ | Compute from above |
| **Cover letter with name** | ✓ | ✓ | Generate on-demand |

### Three-Tier Caching Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1: Embeddings (already done)                                  │
│    Key: skill_text                                                  │
│    Value: 1024-dim vector                                           │
│    Reuse: Forever, all users                                        │
│    → 5,334 cached in `embeddings` table                             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  TIER 2: Posting Analysis (NEW - cache per posting)                 │
│    Key: posting_id                                                  │
│    Value: {                                                         │
│      "ideal_candidate": "Someone with X, Y, Z...",                  │
│      "critical_skills": ["Python", "SQL"],                          │
│      "nice_to_have": ["AWS"],                                       │
│      "domain_gates": ["fintech"],                                   │
│      "skill_gap_templates": {                                       │
│        "Python": "Essential for backend development...",            │
│        "SQL": "Required for data analysis..."                       │
│      }                                                              │
│    }                                                                │
│    Reuse: ALL users analyzing this posting                          │
│    Time: ~3s LLM call, ONCE per posting                             │
│    → Store in postings.llm_analysis (JSONB)                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  TIER 3: Personalization (on-demand, fast)                          │
│    Input: posting_analysis (cached) + user_name + track_records     │
│    Process:                                                         │
│      1. Compare user skills to requirements (instant, no LLM)       │
│      2. Select relevant gap templates (instant)                     │
│      3. Fill cover letter template with name + track records        │
│      4. Light LLM polish (~1-2s) OR pure template (0s)              │
│    Output: Personalized cover letter + go/nogo                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Impact: The Math

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| 1 user, 1 posting | 8s | 8s | - |
| 1 user, same posting again | 8s | 0s (cached) | 100% |
| 2nd user, same posting | 8s | **1-2s** | **75-88%** |
| 100 users, same posting | 800s | **~11s** (8 + 99×0.03) | **98.6%** |

### Why This Works

1. **Posting analysis is universal** - "This job needs Python" is true for ALL candidates
2. **Gap templates are reusable** - "Missing Python is critical because..." applies to anyone missing Python
3. **Only names and track records vary** - That's simple template substitution

### Implementation Path

**Phase 1: Posting Pre-Analysis (batch, offline)**
```sql
ALTER TABLE postings ADD COLUMN llm_analysis JSONB;
```
- Run LLM on each posting ONCE during nightly batch
- Store ideal candidate, critical skills, gap templates

**Phase 2: Fast Personalization (online)**
- User clicks "Analyze" → Load cached posting analysis
- Compare skills → Select applicable templates
- Insert name + track records → Return in ~0.1s
- OR: Light LLM polish → Return in ~1-2s

---

## 8. Optimizations Already Done

✅ Embedding cache in PostgreSQL (`embeddings` table)  
✅ Cache loaded at startup (5,334 embeddings in memory)  
✅ New embeddings auto-persisted  

---

## 9. Implementation Roadmap

### Phase 1: Two-Tier MVP
1. Store embedding scores in `profile_posting_matches` (no LLM)
2. Dashboard shows matches ranked by embedding score
3. "Analyze" button triggers LLM on-demand
4. Cache LLM results in same table

### Phase 2: Cross-User Caching
1. Add `llm_analysis` JSONB column to postings
2. Pre-analyze postings during nightly batch (~3s each)
3. On user click: load cached analysis + personalize (~0.1-2s)

### Phase 3: Background Processing
1. For top 50 matches, pre-compute LLM analysis overnight
2. User sees instant cover letters for best matches
3. On-demand for the rest

### Phase 3: Feedback Loop
1. User rates matches (already have `user_rating`)
2. Train threshold: "User liked this at embedding=0.72, disliked at 0.68"
3. Personalized cutoffs per user

---

## 10. Hardware Implications

### Current Setup
- Intel NUC with NVIDIA GPU
- Single Ollama instance (GPU)
- PostgreSQL on same machine

### For 100 users (with Two-Tier)
| Component | Load | Status |
|-----------|------|--------|
| Embedding computation | ~2s per new user | ✅ OK |
| LLM matching | ~50 clicks/user × 8s = 400s | ✅ OK (spread over time) |
| Database | Embedding cache + match scores | ✅ OK |

**Key insight:** Two-tier architecture means LLM load is **user-paced**, not batch-paced.

### Recommendation
1. **Phase 1 (MVP):** Two-tier on current hardware
2. **Phase 2 (10+ users):** Add job queue for LLM requests
3. **Phase 3 (100+ users):** Consider cloud GPU burst for peaks

---

## 11. Online vs Offline Decision Matrix (Updated)

| Operation | Online | Offline | Notes |
|-----------|--------|---------|-------|
| User login/auth | ✅ | | Instant |
| **Show potential matches** | **✅** | | **Instant (embedding scores)** |
| **Analyze single match** | **✅** | | **8s on click (LLM)** |
| Fetch new postings | | ✅ | Daily cron |
| Process postings | | ✅ | Overnight |
| Import profile | ⚠️ | | Fast but can queue |
| Process profile facets | | ✅ | Queue, 1-2 min |
| ~~Compute all matches~~ | | ~~✅~~ | **No longer needed!** |
| Rate a match | ✅ | | Instant (DB write) |
| Mark applied | ✅ | | Instant (DB write) |
| View skill matrix | ✅ | | Pre-computed or on-demand |

---

## Appendix: Raw Timing Data

### LLM Response Times
```
qwen2.5-coder:7b: 7.4s (64 tokens)
qwen2.5:7b: 3.6s (44 tokens)
```

### Embedding Times
```
Cached lookup: ~0.001s
New computation: ~0.1s per term
Matrix (94×5): ~1.8s with cache, ~10s without
```

### Match Process Breakdown
```
Load DB cache: one-time at startup
Load profile data: 0.01s
Load posting data: 0.01s
Compute embeddings: 1.8s (with cache)
LLM analysis: 5-10s
DB write: 0.01s
Total: 7-12s per match
```
