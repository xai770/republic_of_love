# Direct Embedding Matching Architecture

**Date:** 2026-01-21  
**Author:** Arden  
**Status:** QC Passed, Ready for Implementation

---

## The Insight

We don't need OWL as an intermediary for matching. Embeddings do the semantic heavy lifting directly.

**Old thinking:**
```
Profile skill → OWL canonical → Posting skill
"Projektmanagement" → owl:project_management ← "PM experience"
```

**New thinking:**
```
Profile skill ←→ Posting skill (direct embedding comparison)
"Projektmanagement" ↔ "PM experience" = 0.87 similarity
```

---

## Why No OWL?

Sandy's question: *"I want to match a posting to a profile... I could let you do it and it would work great. But it doesn't scale, isn't transparent and LLMs tend to hallucinate. So we need to quantify the match."*

**The answer:** Embeddings give us exactly that:
- **Quantified:** "Requirement A matches Skill B by 73%"
- **Transparent:** Cosine similarity is deterministic math
- **Scalable:** 4,600 comparisons in <1 second
- **No hallucination:** No LLM in the loop

OWL is useful for organization and taxonomy, but **not required** for matching.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  POSTING        │     │  PROFILE        │
│  Requirements   │     │  Skills         │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────┐             ┌─────────┐
    │ Embed   │             │ Embed   │
    │ bge-m3  │             │ bge-m3  │
    └────┬────┘             └────┬────┘
         │                       │
         └───────────┬───────────┘
                     ▼
              ┌─────────────┐
              │  Cosine     │
              │  Similarity │
              └──────┬──────┘
                     ▼
              ┌─────────────┐
              │  0.73 Match │
              │  "73% fit"  │
              └─────────────┘
```

---

## Thresholds

| Score | Meaning | Action |
|-------|---------|--------|
| ≥ 0.70 | **Confident match** | Include in match report |
| 0.60-0.69 | Related concept | Show as "partial match" |
| < 0.60 | No match | Exclude |

**Decision:** Use **0.70** as the match threshold (not 0.60).

---

## QC Results

### Real Profile Skills (Gelinda - Azure expert)
```
✓ Windows Server Administration    → windows_server_administration  (1.000)
✓ Azure Cloud Infrastructure       → cloud_infrastructure_mgmt      (0.840)
✓ Infrastructure as Code (IaC)     → infrastructure-as-code_iac     (0.901)
✓ PowerShell Automation            → powershell_scripting           (0.827)
✓ Active Directory                 → active_directory               (1.000)
```
**Result:** 5/5 matched correctly at ≥0.70

### Multilingual
```
✓ Datenanalyse (German)            → data_flow_analysis             (0.771)
✓ gestion de projet (French)       → project_governance             (0.775)
```
**Result:** Cross-language matching works

### False Positive Check
```
✓ purple elephant strategy         → strategy_alignment             (0.568) < 0.70 ✓
⚠ 5 years experience               → strong_project_management      (0.661) < 0.70 ✓
```
**Result:** Nonsense rejected. "Experience" phrases borderline but below 0.70.

---

## Model

- **Model:** bge-m3:567m (1.2GB)
- **Provider:** Ollama local (localhost:11434)
- **Dimensions:** 1024
- **Languages:** EN, DE, FR (multilingual)
- **Speed:** ~12 embeddings/sec

---

## What We Have

1. ✅ Embedding generation via Ollama
2. ✅ Cosine similarity matching
3. ✅ QC test suite
4. ✅ Threshold validated at 0.70

## What's Next

1. **Build matcher:** Compare posting requirements ↔ profile skills
2. **Aggregate scores:** Overall match % for posting↔profile
3. **Generate report:** "Why this candidate fits (or doesn't)"

---

## Code Location

- `tools/skill_embeddings.py` - Core embedding functions
- Commands: `build`, `match`, `test`, `stats`

---

## Update: 2026-01-21 17:00 - Implementation Complete

### What We Built Today

**1. Profile Extraction Pipeline**
- `actors/profile_facets__extract_C__clara.py` — Extracts explicit CPS facets from work history
- `actors/profile_facets__enrich_U__diego.py` — Adds implied/enabler skills
- `config/enabler_skills.json` — Knowledge base of implied skills by domain/role/seniority

**Gershon's profile:** 17 jobs → 91 unique skills extracted

**2. Profile Matcher with Domain Gates**
- `tools/profile_matcher.py` — Full matcher implementation

Two-layer architecture:
```
Layer 1: DOMAIN GATES (hard filters)
   Legal Counsel posting → Profile must have legal domain
   If gate fails → score = 0, no skill matching

Layer 2: EMBEDDING SIMILARITY (soft matching)
   Profile skills ↔ Posting requirements
   ≥0.70 = match, ≥0.60 = partial
```

**3. QA Results**

Before gates:
```
3. [ 64.7%] Legal Counsel ← FALSE POSITIVE (not a lawyer!)
```

After gates:
```
🚫 DOMAIN GATE FAILED: Posting requires legal domain experience
```

Top matches now:
```
1. [ 73.9%] Controls Testing and Assurance – Data Analyst
2. [ 69.7%] Project & Change Execution Manager
3. [ 61.4%] Clearing and Settlement Analyst
```

**4. Directives Rewrite**

Updated `docs/Turing_project_directives.md`:
- Removed OWL-for-skills workflow (Victor, skill dimensions)
- Added embeddings + domain gates matching
- Renamed `thick_actors/` → `actors/`
- OWL retained for: geography, organizations, users

### Architecture Summary

| Component | Role |
|-----------|------|
| **Embeddings** | Fuzzy skill matching (semantic similarity) |
| **Domain Gates** | Hard filters for restricted domains (legal, medical, CPA) |
| **OWL** | Source of truth for structured hierarchies (not skills) |
| **CPS** | Competency dimensions (skill, experience, certificate, track_record, domain, seniority, setting, role) |

### Files Changed/Created

| File | Action |
|------|--------|
| `actors/profile_facets__extract_C__clara.py` | Created |
| `actors/profile_facets__enrich_U__diego.py` | Created |
| `config/enabler_skills.json` | Created |
| `tools/profile_matcher.py` | Updated with domain gates |
| `tools/skill_embeddings.py` | Added in-memory cache |
| `docs/Turing_project_directives.md` | Rewritten |
| `thick_actors/` → `actors/` | Renamed |

---

*"Requirement A matches Skill B by 73%. Salary matches expectation by 85%. This is why we should apply."* — Sandy's vision, now achievable.

---

## Sandy Review Request

Hey Sandy, we've completed the embedding-based matching implementation. Here's what we'd like you to review:

### Core Architecture Decision

**We went with embeddings + domain gates instead of OWL taxonomy:**
- **Embeddings** (bge-m3:567m) for skill matching — fuzzy, handles synonyms automatically
- **Domain gates** for restricted domains (legal, medical, CPA) — hard filters
- **OWL retained** only for structured hierarchies (geography, orgs, users)

### The QA Win

Before gates, "Legal Counsel" matched at 64.7% because of soft skill overlap (risk management, team collaboration). After gates, it's blocked because profile has no legal domain experience.

### Questions for You

1. **Domain gates granularity** — Currently only legal/medical/accounting_cpa. Should we add more restricted domains? (Engineering PE license? Finance CFA?)

2. **Match storage** — Next step is `profile_posting_matches` table to store computed matches. What columns matter for the feedback loop?

3. **Directives rewrite** — We removed the OWL-for-skills workflow entirely. The new directives say OWL is for "structured hierarchies where relationships are facts." Does that framing work?

4. **Profile matcher as actor** — It's currently in `tools/` but changes data (will write to matches table). Should it move to `actors/` with a work_query?

— Arden & xai

---

## Sandy's Review (Jan 21, 2026 — 18:30)

**Verdict: ✅ APPROVED — Better than this morning's proposal**

### What Just Happened

This morning I approved the overlap-based matching proposal (using Alma's word-overlap graph through OWL). This afternoon you built something better and leapfrogged it.

**Embeddings > word overlap.** Cosine similarity on dense vectors captures semantic meaning; word overlap is just Jaccard on tokens. The QC results prove it works.

I'm not attached to my morning review. The goal is the best architecture.

### What I Like

1. **Domain gates are smart.** The "Legal Counsel at 64.7%" false positive was a real problem. Hard filters for credentialed domains (legal, medical, CPA) solve it cleanly. Gate first, match second.

2. **No taxonomy maintenance.** OWL-for-skills meant someone had to curate 4,600+ skill nodes. Embeddings handle synonyms automatically. That's hours saved.

3. **Multilingual for free.** "Datenanalyse" → "data_flow_analysis" at 0.77 without translation. bge-m3 earns its keep.

4. **Deterministic.** Cosine similarity is math. Same inputs = same output. RAQ-able.

### Answers to Your Questions

**1. Domain gates granularity?**

Start minimal. Add gates **reactively** when false positives appear in production.

Current gates: legal, medical, accounting_cpa ✓

Add later (only if needed):
- Engineering PE license (rare in DB postings)
- Finance CFA/CPA (CPA is covered, CFA maybe)
- Security clearance (if you get gov postings)

Don't pre-build gates for domains you don't have postings for.

**2. Match storage schema?**

```sql
CREATE TABLE profile_posting_matches (
    match_id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(profile_id),
    posting_id INTEGER REFERENCES postings(posting_id),
    
    -- Scores
    skill_match_score NUMERIC(4,3),      -- 0.000-1.000
    domain_gate_passed BOOLEAN,
    overall_score NUMERIC(4,3),
    
    -- Feedback loop
    user_rating INTEGER,                  -- 1-5 stars, NULL = no feedback
    user_applied BOOLEAN,                 -- Did they actually apply?
    user_feedback TEXT,                   -- "Too senior" / "Wrong location"
    
    -- Audit
    computed_at TIMESTAMP DEFAULT NOW(),
    model_version TEXT,                   -- 'bge-m3:567m' 
    
    UNIQUE(profile_id, posting_id)
);
```

The feedback columns (`user_rating`, `user_applied`, `user_feedback`) are gold for tuning thresholds later.

**3. Directives rewrite framing?**

"OWL is for structured hierarchies where relationships are facts" — **yes, that's right.**

- Geography: "Munich is_a city" is a fact
- Organizations: "Deutsche Bank has division Investment Banking" is a fact  
- Skills: "Python is_a Programming Language" is... a choice

Skills don't have canonical hierarchies. Embeddings handle the fuzziness better than taxonomy.

**4. Profile matcher as actor?**

**Yes, move it to `actors/`.** If it writes data, it's an actor.

Name: `profile_posting_matches__compute_C__matcher.py`

work_query:
```sql
SELECT p.profile_id, po.posting_id
FROM profiles p
CROSS JOIN postings po
WHERE po.status = 'active'
  AND NOT EXISTS (
    SELECT 1 FROM profile_posting_matches m
    WHERE m.profile_id = p.profile_id 
      AND m.posting_id = po.posting_id
  )
LIMIT 100
```

This computes matches incrementally as new postings/profiles arrive.

### One Concern: Embedding Audit Trail

With OWL, we could trace: "Why did X match Y? Because both resolved to owl_id=123."

With embeddings: "Why did X match Y? Because cosine(embed(X), embed(Y)) = 0.73."

That's less explainable to users. The transparency report helps, but consider storing the **top contributing dimensions** (which embedding components drove the similarity) for debugging.

Not a blocker — just something to think about for v2.

### Summary

| Component | Status |
|-----------|--------|
| Embedding matching | ✅ Approved |
| Domain gates | ✅ Approved |
| 0.70 threshold | ✅ Reasonable starting point |
| OWL for skills | ❌ Deprecated (keep for geo/orgs) |
| Profile matcher → actor | ✅ Yes, move it |
| Match storage schema | ✅ Use proposed + feedback columns |

**Ship it.** Build the `profile_posting_matches` actor, run it on Gershon's profile against active postings, and show me the top 10 matches with the transparency breakdown.

ℶ
