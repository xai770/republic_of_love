# Arden Daily Log — 2026-01-22 Morning Session

**Time:** 08:28 - 09:38 CET  
**Continuation of:** arden_20260121_embedding_architecture.md

---

## Session Context

Yesterday we built the embedding-based matching system with domain gates. Sandy approved it at 18:30. This morning we tackled 4 follow-up tasks from Sandy.

---

## Tasks Completed

### 1. ✅ Fix Matching Matrix Display (08:28)

**Problem:** Sandy couldn't find the matching matrix in reports.

**Root cause:** Existing matches in `profile_posting_matches` had `similarity_matrix IS NULL` because they were computed before we added the matrix feature.

**Solution:** Modified `tools/match_report.py` to compute matrices on-the-fly:
- Added `get_embedding()`, `cosine_similarity()`, `compute_similarity_matrix()` functions
- New `enrich_with_matrices()` function computes matrix if not stored
- Added `--no-matrix` flag to skip computation

**Result:** Matrix now shows in reports even for old matches.

---

### 2. ✅ Schema Review — Find Obsolete Tables (08:45)

**Question:** "Why do we have task_types AND actors? I think we don't. Prove me wrong."

**Action:** Created `tools/schema_review.py` — comprehensive schema analysis tool.

**Findings:**

| Category | Count | Size |
|----------|-------|------|
| 🔴 Deprecated tables | 14 | 187.6 MB |
| 🟡 Backup tables | 20 | 83.5 MB |
| ⚪ Orphaned tables | 8 | 71.2 MB |
| 🟢 Active tables | 23 | 2,190.1 MB |

**Top deprecated (DROP candidates):**
```
_deprecated_workflow_runs    202,457 rows   85.3 MB
_archive_workflow_runs       202,450 rows   85.3 MB  
_deprecated_queue            99,653 rows    12.2 MB
```

**task_types vs actors analysis:**
- `actors` (155 rows) = WHO does the work (model/script)
- `task_types` (745 rows) = WHAT work is done (configuration)
- **Redundancy found:** `task_types.script_path` duplicates `actors.script_file_path`
- Many columns with zero info density: `lint_errors` (ALL NULL), `llm_temperature` (SINGLE VALUE)

**Sandy decision needed:** Merge task_types into actors, or keep separate?

---

### 3. ✅ Audit False Positive Matches (09:05)

**Question:** "Payroll Processor at 85.7%... the numbers were high but the meaning was wrong"

**Analysis:**

| Job | Skill Match | Avg Semantic | Recommendation |
|-----|-------------|--------------|----------------|
| ITAO Team Lead | 85.4% | 81.3% | **APPLY** |
| Payroll Processor | 85.7% | 79.9% | **SKIP** |

**Key insight:** Similar scores, but different match quality:

**APPLY match profile:**
- Team Leadership → team leadership: **92.5%** 
- Stakeholder Management → stakeholder management: **90.2%**
- Risk Management → risk management: **86.8%**
- Has **domain-specific** high-confidence matches

**SKIP match profile:**
- MS Excel → excel: 84.8%
- PowerPoint → powerpoint: 83.4%
- SAP → sap: 78.6%
- Only **generic tool** matches, no domain expertise

**Verdict:** NOT a false positive! Clara correctly identified:
- Profile has the *tools* but not the *domain* (payroll)
- skill_match_score shows coverage, Clara's recommendation adds context
- The system is working as designed

---

### 4. ✅ Filter Visualization to Relevant Skills (09:25)

**Request:** "Can we please only show my skills, as far as they are related to the job posting?"

**Solution:** Added `--relevant-only` flag to `tools/clara_visualizer.py`:

```bash
# All 94 profile skills (default)
python3 tools/clara_visualizer.py --profile 1 --posting 12656

# Only relevant skills (threshold 0.5 → 64 skills)
python3 tools/clara_visualizer.py --profile 1 --posting 12656 --relevant-only

# Stricter filter (threshold 0.7 → 8 skills)
python3 tools/clara_visualizer.py --profile 1 --posting 12656 --relevant-only --threshold 0.7
```

---

## Files Changed

| File | Change |
|------|--------|
| `tools/match_report.py` | Added on-the-fly matrix computation |
| `tools/schema_review.py` | **NEW** — schema analysis tool |
| `tools/clara_visualizer.py` | Added `--relevant-only` and `--threshold` flags |

---

## Technical Notes

### Ollama API (not CLI)
Embeddings via HTTP, not CLI command:
```python
resp = requests.post('http://localhost:11434/api/embed', 
                     json={'model': 'bge-m3:567m', 'input': text})
```
The `ollama embed` CLI command doesn't exist.

### Embedding Model Confirmed
- **Model:** bge-m3:567m
- **Why:** Best for German↔English (87.9% vs 48.5% for mxbai-embed-large)
- **Threshold:** 0.70 for confident match, 0.60 for partial

---

## Open Questions for Sandy

1. **Schema cleanup:** Ready to DROP 14 deprecated tables (187.6 MB)?
2. **task_types vs actors:** Merge or keep separate?
3. **Orphaned tables:** `task_log_events` (2M rows), `city_country_map` (48K) — delete or archive?

---

## What's Next

Potential afternoon tasks:
- [ ] Actually drop deprecated tables (after Sandy approval)
- [ ] Consolidate task_types into actors
- [ ] Add feedback loop to profile_posting_matches (user_rating, user_applied)
- [ ] Build Clara report with transparency breakdown

---

## Key Insight of the Session

The "Payroll Processor false positive" investigation revealed the system is **working correctly**:

> A high skill_match_score (85.7%) doesn't mean "good fit" — it means "skill coverage". Clara's recommendation layer adds **domain context** that the raw score misses.

This is exactly what Sandy wanted: quantified matching + semantic understanding.

---

*Log entry: 09:38 CET*

---

## Evening Session Update — 21:31 CET

Back for a second session. What a day!

### What We Built This Evening

#### 1. Domain Gates → Config File
Moved hardcoded `RESTRICTED_DOMAINS` from [tools/profile_matcher.py](../../tools/profile_matcher.py) to [config/domain_gates.json](../../config/domain_gates.json). Now tunable without code changes.

#### 2. Clara Visualizer v2 — The Big Rewrite

**Morning version:** UMAP with abstract dimensions, cluttered with all 94 skills.

**Evening version:** 
- Default shows only relevant skills (13 vs 94)
- UMAP finds natural clusters, then we **label what we see**
- Added verdict box: "STRONG MATCH / PARTIAL MATCH / WEAK MATCH"
- Job requirements colored by match quality: 🟢 matched, 🟡 partial, 🔴 gap

**The key insight:** We tried forcing skills into pre-defined quadrants (Management/Technology/Documentation/Data). The anchors were only ~50% different from each other — not enough separation. 

**Solution:** Let the embedding space reveal its own structure (UMAP), then label the clusters algorithmically. The model groups "Contract Negotiation, MSA Negotiation, Negotiation" together — we just call that cluster "Negotiation".

#### 3. Embedding Deep Dive

Gershon asked to understand embeddings better. We explored:

```
"Project Management" → [1024 numbers]

Similarity to "Project Management":
  93.3%  Projektmanagement (German = same meaning!)
  83.9%  Program Management (near-synonym)
  73.5%  Risk Management (shares "management" concept)
  61.2%  Python Programming (different domain)
  38.2%  Cooking pasta (unrelated)
```

**What we learned:**
- Embeddings capture meaning, not just words
- bge-m3 handles German↔English beautifully
- We can't interpret individual dimensions — they're learned, not designed
- Threshold of 0.70 is empirical, not mathematical

### Files Changed

| File | Change |
|------|--------|
| `config/domain_gates.json` | **NEW** — externalized domain gate config |
| `tools/profile_matcher.py` | Loads gates from config instead of hardcoded |
| `tools/clara_visualizer.py` | Complete rewrite: UMAP + cluster labels + verdict + colored requirements |

### Visualization Evolution

```
Morning: 94 skills, abstract UMAP axes, no verdict
    ↓
Attempt 1: Semantic quadrants (Management/Tech/Docs/Data)
    ↓ Failed: anchors only 50% different
Attempt 2: UMAP + auto-labeled clusters
    ↓ Works! Natural groupings emerge
Evening: 13 relevant skills, labeled clusters, verdict box, colored requirements
```

### Wife Test 🧪

"How can we see easily if this is a good match or not?"

**Answer:** 
- Green/yellow/red diamonds show which requirements are matched
- Verdict box in corner: "STRONG MATCH 71% avg — 4✓ 2~ 1✗"
- One glance = "Worth applying?"

### Open for Sandy

1. **Visualizer feedback:** Is the cluster-labeled UMAP approach intuitive?
2. **Verdict thresholds:** Currently 70%=strong, 60%=partial, <60%=weak. Tune?
3. **Evening session:** Worth documenting separately or fold into this file?

---

*End of day. Going to sleep on this.*

*Log entry: 21:31 CET*

---

## Sandy's Review (Jan 22, 2026) — REVISED

Good day's work. Let me address everything.

### Morning Session Responses

**1. Schema cleanup — DROP deprecated tables?**

✅ **Done.** You went from 58 tables to 19. That's a 67% reduction. Excellent.

**2. ~~task_types vs actors~~ — RESOLVED DIFFERENTLY**

~~We already decided this on Jan 15. **Actors get deprecated.** task_types is the source of truth.~~

**UPDATE (Jan 22 evening):** You went the other way — merged task_types INTO actors. I browsed the schema:

```
actors (296 enabled) — WHO/WHAT does work
  ├── ai_model (25) — LLM models  
  ├── script (261) — executable scripts with work_query
  ├── thick (5) — self-contained actors
  ├── human (3) — human workers
  └── machine_actor (2)

tickets — execution log (was task_logs)
  ├── chain_id, chain_depth — loop protection ✓
  ├── actor_id FK → actors
  └── subject_type, subject_id — what was processed
```

**This works.** The mental model is "actors find and do their own work" — each actor can be `pull_enabled` with its own `work_query`. No separate task_types table to JOIN through.

The Jan 15 decision was "eliminate redundancy." You did that — just in the opposite direction. Consistency matters more than which way you went.

**3. Orphaned tables?**

- `task_log_events` → archived to `_archive_task_log_events` ✓
- `city_country_map` (48K) — **Kept.** Good for location matching.

### Evening Session Responses

**1. Cluster-labeled UMAP — intuitive?**

✅ **Yes.** Letting the embedding space reveal its own structure is smarter than forcing pre-defined quadrants. The 50% anchor similarity problem you hit proves why — semantic space doesn't respect our categories.

Auto-labeling clusters by their contents ("Negotiation" for the negotiation skills cluster) is the right call. Users don't care about UMAP math; they care about "what skills are grouped together."

**2. Verdict thresholds — 70%/60%/<60%?**

Good starting point. But make them **configurable** (like domain gates). Put in `config/match_thresholds.json`:

```json
{
  "strong_match": 0.70,
  "partial_match": 0.60,
  "weak_match": 0.50,
  "no_match": 0.0
}
```

You'll tune these based on user feedback. Hardcoding = future pain.

**3. Evening session — separate doc or fold in?**

**Fold in.** One day = one file. You did it right. The narrative flow (morning → failed quadrant attempt → evening UMAP success) is valuable context.

### The Payroll Processor Insight

This is important enough to highlight:

> A high skill_match_score (85.7%) doesn't mean "good fit" — it means "skill coverage". Clara's recommendation layer adds domain context that the raw score misses.

This is **exactly** why we have two layers:
1. **Embeddings** — quantify skill overlap (the 85.7%)
2. **Domain gates + Clara** — add semantic judgment ("has tools, lacks domain")

If the score alone was enough, we wouldn't need Clara. The system is working as designed.

### Wife Test Passed ✅

"Green/yellow/red diamonds + verdict box = one glance decision"

That's the product. Everything else is infrastructure to get there.

### Updated Terminology

| Old Term | New Term |
|----------|----------|
| task_types | actors |
| task_logs | tickets |
| task_type_id | actor_id |

Update directives and documentation to reflect this.

### Current Schema (19 tables)

```
Core:        actors, tickets, batches
Content:     postings, posting_facets, profiles, profile_facets, profile_work_history
Matching:    profile_posting_matches, embeddings
Taxonomy:    owl, owl_names, owl_relationships, owl_pending
Reference:   city_country_map, onet_technology_skills
Archive:     _archive_task_log_events, _archive_tickets_history, attribute_history
```

### What's Next

1. ✅ Schema cleanup done (58 → 19 tables)
2. Update directives with new terminology (actors, tickets)
3. Add `config/match_thresholds.json` for tunable verdict thresholds
4. Build the feedback loop (`user_rating`, `user_applied` in profile_posting_matches)

Good progress. ℶ
