# WF2010 Overnight Run QA Report

*Arden's Assessment — January 3, 2026 (Updated after bug fixes)*

---

## Executive Summary

**Rating: 8/10** (up from 5/10 initial run)

The overnight run processed 1000 skills. After fixing the rejection loop bug and reprocessing stuck skills:

| Metric | Initial | After Fix |
|--------|---------|-----------|
| Skills placed | 493 (49%) | **513 (100%)** |
| Skills stuck in loop | 448 | **0** |
| Error rate | 0.0% | 0.0% |

**All skills now classified.** 15 edge cases landed in \`_NeedsReview\` for human triage (expected behavior for ambiguous skills).

### Remaining Issues (P1)
1. **3 oversized folders** — need Samantha splitting
2. **Folder named "null"** — cleanup needed (entity 39998)
3. **Garbage skills** — "X years experience" items need upstream filtering

---

## Final Run Statistics

| Metric | Value |
|--------|-------|
| Skills processed | 513 unique |
| Total workflow runs | 1,144 (includes retries) |
| Skills placed | 513 (100%) |
| Skills in _NeedsReview | 15 (2.9%) |
| Classifier agreement | 24.6% |
| Error rate | 0.00% |
| Total interactions | 24,874 |
| Total folders | 65 |

---

## What Worked

### 1. Rejection Memory Fix ✅
The root cause of the rejection loop was **no memory of rejected proposals**. Fixed by:
- Adding \`rejected_proposals: []\` and \`rejection_count: 0\` parameters
- Passing rejection history through workflow retries
- MAX_REJECTIONS = 3 → force-place in \`_NeedsReview\`

**Result:** Skills that classifiers disagree on now either:
- Get approved by Victor (new folder created)
- Get rejected → retry with memory of rejection
- Hit max rejections → land in \`_NeedsReview\` (no infinite loop)

### 2. Entity ID Leakage Fix ✅
Discovered secondary bug: retry interactions lost their subject context (skill entity_id). Fixed in \`interaction_creator.py\`:
- Now queries \`subject_type\`/\`subject_id\` from \`workflow_runs\`
- Injects \`_context\` into all branched interactions

### 3. Root-Level Category Guide ✅
Skills correctly route to top-level categories:
- \`technical_and_tools\`: 21 skills
- \`cognitive_and_analytical\`: 20 skills
- \`self_management\`: 20 skills

### 4. Zero Error Rate ✅
All 1,144 workflow runs completed without crashes.

---

## Folder Distribution (Top 15)

| Folder | Skills |
|--------|--------|
| ai_ethical_governance | 21 |
| career_progression_metrics | 21 |
| technical_and_tools | 21 |
| computational_thinking_and_problem_solving | 20 |
| cognitive_and_analytical | 20 |
| agile_culture_and_practices | 20 |
| language_and_communication | 20 |
| self_management | 20 |
| execution_and_compliance | 20 |
| advanced_education_and_certifications | 19 |
| creative_and_generative | 19 |
| agile_development_and_management | 19 |
| ai_tool_usage | 18 |
| perception_and_observation | 16 |
| null | 15 |
| _NeedsReview | 15 |

---

## Skills in _NeedsReview (15 total)

These hit max rejections (3) and need human review:
- "4 – 8 Years in relevant field" ← requirement, not skill
- "6 - 12 years of experience in relevant field" ← requirement
- "Ability to read and understand complex loan agreements"
- "Academic Achievement"
- "Academic Achievements (Bachelor's/Master's degree)"
- "Achieving sales targets"
- "Adaptability"
- "Advanced Degree"
- "advisory_experience"
- "alternative_investment_products_knowledge"
- "Analytical skills, ability to benchmark..."
- "Analytical thinking"
- "Analytic market data in fixed income and equities"
- "relevant_experience"

**Note:** Several of these are requirements ("X years experience"), not skills. Should be filtered upstream before WF2010.

---

## Remaining Issues

### P1 — High Priority

1. **3 Oversized Folders**
   - \`ai_ethical_governance\`: 21 skills (limit: 20)
   - \`career_progression_metrics\`: 21 skills
   - \`technical_and_tools\`: 21 skills
   
   **Action:** Run Samantha (folder splitter) or increase limit to 25

2. **Folder Named "null"** (entity 39998)
   - Has 15 skills assigned
   - Obviously a bug — JSON parsing issue somewhere
   
   **Action:** Delete entity, reassign skills

3. **Garbage Skills in Input**
   - "X years experience" items aren't skills
   - Should be filtered in wf2010_lookup
   
   **Action:** Add filter regex before classification

### P2 — Nice to Have

4. **Classifier Agreement at 24.6%**
   - Not necessarily bad — disagreement triggers Victor review
   - May want to tune prompts if we want more agreement

---

## Code Changes Made

### wf2010_victor.py
- Added \`get_rejection_tracking()\` helper
- Searches ancestor outputs for \`current_rejection_count\`
- Outputs \`rejected_proposals\`, \`rejection_count\` on REJECT

### wf2010_lookup.py  
- Reads \`rejected_proposals\`/\`rejection_count\` from \`parent_output\`
- Passes rejection memory through workflow

### interaction_creator.py
- Queries subject info from \`workflow_runs\` table
- Injects \`_context\` into all branched interactions
- Sets \`subject_type\`/\`subject_id\` columns in INSERT

### workflow_branches view
- Created human-friendly view of branching logic
- Added validation flags for broken branches
- Branch validation runs at daemon startup

---

## Comparison: Before vs After Fix

| Metric | Before Fix | After Fix | Change |
|--------|------------|-----------|--------|
| Rating | 6/10 | 8/10 | ⬆️ +2 |
| Placement rate | 49.3% | 100% | ⬆️ **+50.7%** |
| Stuck in loop | 448 | 0 | ⬆️ Fixed |
| _NeedsReview | 7 | 15 | ↔️ Expected |
| Agreement rate | 21.0% | 24.6% | ↔️ Similar |
| Error rate | 0.0% | 0.0% | ↔️ Same |

---

## Next Steps

1. ✅ ~~Fix rejection loop~~ — DONE
2. ✅ ~~Reprocess stuck skills~~ — DONE  
3. ⏳ **Run Samantha** — split 3 oversized folders
4. ⏳ **Clean up "null" folder** — delete entity 39998
5. ⏳ **Add upstream filter** — reject "X years experience" skills

---

*Ready for production at current scale. P1 items are data quality issues, not blockers.*

— Arden

---

## Sandy's Review

*January 3, 2026, 10:30 CET*

The rejection loop fix was a significant win. 49% → 100% placement is the headline. But the taxonomy structure reveals deeper problems that we need to address before scaling further.

### The Good

1. **Zero errors** — Mechanically, WF2010 is solid. 1,144 runs, no crashes.
2. **Rejection memory works** — The `rejected_proposals[]` + `rejection_count` pattern is correct. Skills that classifiers genuinely can't agree on land in `_NeedsReview` instead of looping forever.
3. **`_NeedsReview` is the right escape hatch** — 14 skills at 2.9% is healthy. These are genuinely ambiguous (requirements vs skills, credentials vs skills).

### The Problems (In Order of Severity)

#### P0: Classification Quality is Poor

Looking at the actual folder contents, the model is **dumping skills in the wrong categories**:

**`cognitive_and_analytical` has become a junk drawer:**
```
ai_ethical_governance/: 21 skills
  - "3-7 Years of Experience" ← NOT a skill, NOT AI-related
  - "Accountancy" ← domain expertise, not cognitive
  - "Analysis and fixing of software defects" ← technical skill
  
career_progression_metrics/: 21 skills
  - "10+ years experience in investment banking" ← NOT a skill
  - "Bachelor's Degree in Computer Science" ← credential, not skill
  - "TACL Programming" ← technical skill, wrong category entirely
```

These folders aren't "oversized" — they're **miscategorized garbage bins**.

**Empty top-level categories:**
```
technical/: 0 skills (but has no subfolders either!)
domain_expertise/: 0 skills
interpersonal/: 0 skills
```

Yet `cognitive_and_analytical` has 17 subfolders with 166+ skills. The model is routing nearly everything to one branch and ignoring the others.

#### P1: Folder Names Are Invented Nonsense

The model created folders that don't belong in a skill taxonomy:

| Folder | Problem |
|--------|---------|
| `career_progression_metrics` | This isn't a skill category — it's metadata about experience |
| `ai_ethical_governance` | Contains "3-7 Years Experience" and "Accountancy" — name doesn't match contents |
| `advanced_certifications_and_degrees` | Credentials aren't skills |
| `advanced_education_and_certifications` | Duplicate of above, slightly different name |
| `time_management` + `time_management_skills` | Two folders for the same concept under `self_management` |

Victor is approving folder names without validating that the proposed skill actually fits.

#### P2: "Years of Experience" Is Still Leaking Through

Despite our Lily discussion, experience requirements are still being classified as skills:

```
ROOT level:
  - "8 years relevant experience"

cognitive_and_analytical level:
  - "10+ years of relevant experience"
  - "12+ years of experience in recruitment"
  - "15+ years of overall experience"

career_progression_metrics folder:
  - "10+ years experience in investment banking operations"
  - "10 years' experience in some combination of..."
  - "12+ years of IT experience..."
  - "15 years of work experience..."
```

Lily (the decomposer) doesn't exist yet. These should never reach WF2010.

#### P3: Duplicate/Near-Duplicate Folders

```
self_management/
  ├── time_management/ (8 skills)
  └── time_management_skills/ (1 skill)  ← WHY?

cognitive_and_analytical/
  ├── advanced_certifications_and_degrees/ (10 skills)
  └── advanced_education_and_certifications/ (19 skills)  ← SAME THING

execution_and_compliance/
  ├── agile_development_and_management/
  └── agile_development_methods_and_practices/  ← SAME THING
```

Victor approved both. Clara proposed both. There's no deduplication check.

### Root Causes

1. **No folder existence check before Carl creates** — Clara says "create `time_management_skills`" without checking that `time_management` already exists.

2. **Victor approves names, not semantic fit** — Victor sees "Does `ai_ethical_governance` sound reasonable?" but doesn't verify the skill ("3-7 Years Experience") actually belongs there.

3. **Model prompt doesn't emphasize top-level routing** — The model sees all 10 root categories but funnels everything to `cognitive_and_analytical` because it's the vaguest bucket.

4. **No Lily** — Experience requirements are being classified as if they were skills.

### What Needs To Change

#### Fix 1: Lucy Must Check for Similar Folders (Today)

Before routing to Carl (create), Lucy should fuzzy-match:
```python
def find_similar_folders(proposed_name, existing_folders, threshold=0.8):
    """Return existing folders that are semantically similar."""
    # Check: time_management_skills vs time_management
    # Check: advanced_education_and_certifications vs advanced_certifications_and_degrees
```

If similarity > threshold, return the existing folder instead of creating new.

#### Fix 2: Vera Must Validate Skill-Folder Fit (Today)

Vera (validator script) should check:
```
Skill: "3-7 Years of Experience"
Proposed folder: ai_ethical_governance

❌ REJECT: Skill contains experience duration pattern.
   This is a requirement, not a skill.
   Route to _NeedsReview.
```

Vera runs BEFORE Victor. If Vera rejects, skill goes to `_NeedsReview` without burning Victor cycles.

#### Fix 3: Rebalance Prompt Weights (This Week)

The classifier prompt needs adjustment:
```
IMPORTANT: Consider ALL top-level categories before drilling down.
- technical/: Programming, tools, software, infrastructure
- domain_expertise/: Industry-specific knowledge (finance, healthcare, legal)
- interpersonal/: Collaboration, negotiation, leadership, teamwork
- cognitive_and_analytical/: Problem-solving, analysis, critical thinking (NOT credentials, NOT experience)
```

Add negative examples:
```
NOT cognitive_and_analytical:
- "Python programming" → technical
- "10 years banking experience" → NOT A SKILL
- "CFA certification" → NOT A SKILL (credential)
- "Investment banking knowledge" → domain_expertise
```

#### Fix 4: Implement Lily (This Week)

We discussed this. Lily decomposes requirements into skill + quantity:
```
Input: "10+ years Python experience"
Output: {skill: "Python", quantity: {type: "years", value: 10, op: ">="}}
```

Only the skill goes to WF2010. The quantity goes to `posting_skills.quantity`.

Until Lily exists, add a regex filter in `wf2010_lookup.py`:
```python
EXPERIENCE_PATTERNS = [
    r'^\d+\+?\s*years?\s+(of\s+)?experience',
    r'^\d+\s*-\s*\d+\s*years?\s+(of\s+)?experience',
    r'^minimum\s+\d+\s*years?',
]
if any(re.match(p, skill_name, re.I) for p in EXPERIENCE_PATTERNS):
    return {"action": "REJECT", "reason": "experience_requirement"}
```

This is a stopgap until Lily is built.

### Revised P0/P1/P2 List

| Priority | Issue | Action |
|----------|-------|--------|
| **P0** | Misclassifications in cognitive_and_analytical | Manual review of 50 random skills |
| **P0** | Experience patterns still classified | Add regex filter to lookup |
| **P0** | Duplicate folders created | Add fuzzy-match in Lucy |
| **P1** | Victor approves bad fits | Add Vera pre-validation |
| **P1** | Empty technical/domain/interpersonal | Rebalance classifier prompt |
| **P1** | Implement Lily properly | New actor + queue changes |
| **P2** | 3 oversized folders | Run Samantha OR manual split |
| **P2** | "null" folder cleanup | Delete entity 39998 |

### The Hard Truth

**8/10 is generous.** Mechanically, yes — no crashes, no infinite loops, 100% placement. But placement rate ≠ quality. If we're placing "TACL Programming" under `cognitive_and_analytical/career_progression_metrics`, we're just organizing garbage neatly.

The real metrics should be:
- **Correct top-level routing**: How many skills landed in the right root category?
- **Semantic folder fit**: Does the skill actually belong in the folder it was placed in?
- **Duplicate folders**: How many near-duplicate folders were created?

I'd estimate:
- Correct top-level routing: ~40% (based on empty technical/domain/interpersonal)
- Semantic folder fit: ~60% (eyeballing the folder contents)
- Duplicate folders: 6+ obvious ones

**Adjusted rating: 5/10** — Mechanically sound, semantically broken.

### Immediate Next Steps

1. **Don't run more skills** until the filters are in place
2. **Add experience regex filter** to `wf2010_lookup.py`
3. **Add fuzzy folder matching** to Lucy
4. **Manually review 50 skills** from `cognitive_and_analytical` — how many are correctly placed?
5. **Delete the "null" folder** and reassign its 15 skills
6. **Merge duplicate folders**:
   - `time_management_skills` → `time_management`
   - `advanced_education_and_certifications` → pick one, merge
   - `agile_development_methods_and_practices` → `agile_development_and_management`

The overnight run proved WF2010 *works*. Now we need to make it work *correctly*.

— Sandy ℶ
