# Skill Taxonomy Pipeline: Redesign Proposal

**Date:** January 1, 2026  
**Author:** Sandy (Consultant Mode)  
**Status:** Proposal for Review

---

## Executive Summary

The current WF2003/2004/2005 pipeline works, but it's **over-engineered for the problem it solves**. Three workflows, cascading triggers, and dual-classification on every skill burns compute and creates complexity.

**Proposed changes:**
1. Merge three workflows into one
2. Use confidence-based routing (single classifier for easy, dual for hard)
3. Batch similar skills together
4. Create structure during classification, not after
5. Replace per-batch QA with periodic audits

**Expected improvement:** 40-60% reduction in LLM calls, simpler operations, same quality.

---

## Current State: What's Wrong

### Problem 1: Three Workflows for One Job

```
Current:
  WF2003 (classify) → trigger → WF2004 (QA) → trigger → WF2005 (wire orphans)
                                     ↑_______________________________|
```

This creates:
- **Trigger complexity** - DEPENDENCY triggers, 1844 runs of WF2004→WF2005
- **Orphan creation** - WF2003 creates folders without parents, WF2005 fixes them
- **Split latency** - Folders grow oversized before Samantha notices

**Why does WF2005 exist at all?** If WF2003 created folders correctly, they'd already have parents.

### Problem 2: Dual-Grader on Every Skill

Current flow for "python":
```
Classifier A: python → technical ✅
Classifier B: python → technical ✅
Compare: AGREE
```

We burned 2 LLM calls to confirm what was obvious. The dual-grader pattern is valuable for **ambiguous** skills, not for "python."

71% agreement rate means **71% of dual-grader calls are redundant**.

### Problem 3: Navigation Loop is Expensive

For each skill, each classifier navigates:
```
Call 1: "Which root?" → technical
Call 2: "Which subfolder?" → (none, place here)
```

With dual-grader, that's **4 LLM calls minimum per skill**. For a 200-skill batch: 800+ calls.

### Problem 4: Post-Hoc Structure Creation

Current approach:
1. File 63 skills under `technical`
2. Quinn notices it's oversized
3. Samantha proposes split
4. Victor reviews
5. Skills get reorganized

That's **5 steps** after the fact. Why not create `programming_languages` when the first programming language arrives?

### Problem 5: No Skill Batching

We classify "python", "java", "javascript" as three separate jobs. But they're obviously related - a human would say "these are all programming languages" and file them together.

---

## Proposed Design: WF2010 Unified Taxonomy

One workflow. Smarter routing. Batch processing.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    WF2010: Unified Taxonomy                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────┐            │
│  │ Batcher │───▶│ Confidence   │───▶│ Classifier  │            │
│  │ (group  │    │ Router       │    │ (single or  │            │
│  │ similar │    │              │    │ dual)       │            │
│  │ skills) │    │ Easy → Fast  │    │             │            │
│  └─────────┘    │ Hard → Dual  │    └──────┬──────┘            │
│                 └──────────────┘           │                    │
│                                            ▼                    │
│                              ┌─────────────────────────┐        │
│                              │ Structure Builder       │        │
│                              │ (create folders inline) │        │
│                              └───────────┬─────────────┘        │
│                                          │                      │
│                                          ▼                      │
│                              ┌─────────────────────────┐        │
│                              │ Apply + Wire            │        │
│                              │ (belongs_to + is_a)     │        │
│                              └─────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Separate (daily cron):
┌─────────────────────────────────────────────────────────────────┐
│                    WF2011: Taxonomy Health                       │
│  Quinn audits: loops, orphans, oversized, duplicates            │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Batcher

**Input:** Queue of pending skills  
**Output:** Grouped batches of related skills

```python
# Group skills by semantic similarity
batches = [
    ["python", "java", "javascript", "go", "rust"],      # programming langs
    ["kubernetes", "docker", "helm"],                      # containers
    ["aws", "azure", "gcp"],                               # cloud
    ["communication", "presentation", "public_speaking"], # soft skills
]
```

**How:** Embedding similarity (fast, local) or simple heuristics (shared words).

**Benefit:** Classify 5 skills with 1 LLM call instead of 5.

### Step 2: Confidence Router

**Input:** Skill batch  
**Output:** Routing decision (FAST or CAREFUL)

```
FAST path (single classifier):
- Skill name contains known keywords (python, aws, leadership)
- High embedding similarity to existing classified skills
- Previous skills from same batch already classified

CAREFUL path (dual classifier):
- Ambiguous names (swift, go, lead)
- Low similarity to existing skills
- First skill in a new domain
```

**Expected:** 60-70% of skills take FAST path.

### Step 3: Classifier

**FAST path:**
```
Single classifier (mistral-nemo:12b)
One-shot classification: "python" → technical/programming_languages/python
```

**CAREFUL path:**
```
Classifier A + Classifier B
Compare → Agree? → Done
         Disagree? → Arbitrator
```

### Step 4: Structure Builder (Key Innovation)

**Current problem:** Classifiers navigate existing structure, can't create it.

**New approach:** Classifier can propose structure inline.

```
Input: ["python", "java", "javascript"]
Current structure: technical/ (no subfolders)

Classifier response:
{
  "proposed_folder": "programming_languages",
  "parent": "technical",
  "skills": ["python", "java", "javascript"],
  "rationale": "All are programming languages, need dedicated subfolder"
}
```

**Victor reviews folder creation** (as before), but now it happens **during** classification, not after.

No orphan folders. No post-hoc splitting. Structure grows organically.

### Step 5: Apply + Wire

Single script actor that:
1. Creates approved folders with `is_a` relationship (no orphans!)
2. Files skills with `belongs_to` relationship
3. Updates hierarchy cache

**No WF2005 needed.** Folders are born connected.

### Separate: WF2011 Taxonomy Health (Daily Cron)

Quinn still audits, but **daily** instead of per-batch:

```
Checks:
- Loops in hierarchy (HALT if found)
- True orphans (shouldn't exist, but check)
- Duplicates (same skill, different names)
- Imbalanced branches (one folder huge, siblings empty)
```

**Not per-batch.** Per-batch QA was causing the 1844-trigger-run problem.

---

## Comparison: Current vs Proposed

| Aspect | Current (WF2003/4/5) | Proposed (WF2010) |
|--------|---------------------|-------------------|
| Workflows | 3 | 1 (+1 daily audit) |
| LLM calls per skill | 4-6 minimum | 1-2 average |
| Triggers | Cascading DEPENDENCY | None (single workflow) |
| Orphan folders | Created then fixed | Never created |
| Structure creation | Post-hoc (Samantha) | Inline (Structure Builder) |
| Batching | None | Semantic grouping |
| QA frequency | Per-batch | Daily |

### LLM Call Reduction

**Current (200 skills):**
- Navigation: 2 calls × 2 classifiers × 200 skills = 800 calls
- Victor reviews: ~50 calls
- Samantha splits: ~20 calls
- **Total: ~870 calls**

**Proposed (200 skills):**
- Batching reduces to ~50 classification decisions
- 70% FAST path: 35 × 1 call = 35 calls
- 30% CAREFUL path: 15 × 3 calls = 45 calls
- Structure proposals: ~10 calls
- **Total: ~90 calls**

**Reduction: ~90%** (probably optimistic, but 50%+ is realistic)

---

## Migration Path

### Phase 1: Quick Wins (This Week)

1. **Fix the 9 vs 10 roots issue** - Reactivate `cognitive_and_analytical`
2. **Disable WF2004→WF2005 trigger** - Run WF2005 manually until stable
3. **Add daily cron for Quinn** - Replace per-batch trigger

### Phase 2: Confidence Router (Next Sprint)

4. **Add confidence scoring** to WF2003
5. **Skip Classifier B** when confidence > 0.9
6. **Measure:** Agreement rate on skipped vs full dual-grader

### Phase 3: Batching (Following Sprint)

7. **Implement skill batcher** - Group by embedding similarity
8. **Modify classifier prompt** to handle batches
9. **Measure:** Calls per skill, accuracy

### Phase 4: Inline Structure (Later)

10. **Merge folder creation into classification**
11. **Deprecate WF2005** - No more orphans
12. **Simplify to single workflow**

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| FAST path misclassifies | Track FAST vs CAREFUL accuracy separately. If FAST degrades, tighten threshold. |
| Batching groups unrelated skills | Use high similarity threshold. Classify singletons separately. |
| Inline structure creates bad folders | Victor still reviews. Bad folders rejected before creation. |
| Daily QA misses urgent issues | Keep critical checks (loops) as immediate alerts, not daily. |

---

## Questions for Arden

1. **Batching:** Do we have embeddings for skills? Or should we use simple keyword matching?

2. **Confidence scoring:** What signals indicate "easy" vs "hard"?
   - Exact match to existing skill name?
   - High similarity to already-classified skill?
   - Contains known domain keyword?

3. **Structure Builder:** Should classifiers propose folders, or should a separate "Architect" actor analyze batches and propose structure?

4. **Victor's role:** Keep human-in-loop for all new folders? Or auto-approve if both classifiers agree on the proposal?

5. **The 1844 runs:** Before we redesign, should we investigate what caused this? Might reveal a bug we'd carry forward.

---

## Recommendation

**Don't rebuild everything at once.**

Start with Phase 1 (quick fixes) and Phase 2 (confidence router). Measure the impact. If we get 50% call reduction from just skipping Classifier B on easy skills, that might be enough.

Batching and inline structure are bigger changes. Save them for when the simple optimizations plateau.

*"The way out is subtraction, not addition"* - and this proposal subtracts workflows, triggers, and LLM calls.

---

*Consultant's bill: 1 interesting conversation*

— Sandy ℶ

---

## Arden's Feedback (January 1, 2026)

Sandy, this is solid work. The diagnosis is accurate and the "subtraction" philosophy is right. Here's my take:

### What I Agree With Completely

1. **71% agreement = 71% wasted dual-grader calls** - This is the low-hanging fruit
2. **Orphans shouldn't exist** - Creating then fixing is backwards
3. **Per-batch QA is overkill** - Daily cron makes more sense
4. **The 1844 trigger cascade needs investigation** - Before we redesign anything

### Where I'd Pump the Brakes

**Batching:** Sounds elegant but adds complexity:
- What embedding model? Is one running?
- "swift" (Apple) vs "swift" (fast) - semantic similarity can deceive
- Batch errors cascade - misclassify 5 skills at once

**Suggestion:** Skip batching for Phase 1-2. Confidence router alone might give us 50%+ reduction. Revisit batching if we plateau.

### My Answers to Your Questions

| Question | My Take |
|----------|---------|
| **1. Embeddings?** | Defer. Too complex for now. |
| **2. Confidence signals?** | Simple: fuzzy match to existing classified skills. If "python" exists, "python3" skips dual-grading. |
| **3. Structure Builder vs Architect?** | Inline with classifier. Separate actor = more calls, more coordination. |
| **4. Victor auto-approve?** | Auto-approve if BOTH classifiers agree AND parent exists. Human review only for new root-level folders. |
| **5. Investigate 1844 runs?** | **Yes, first.** Per directives: fix at SOURCE, not symptom. |

### Proposed Priority Order

```
1. Investigate 1844 trigger cascade     ← Understand before changing
2. Phase 1: Quick fixes                 ← Disable WF2004→WF2005 auto-trigger
3. Phase 2: Confidence router           ← Skip Classifier B when match exists
4. Measure impact                       ← Is 50% reduction enough?
5. Phase 3-4: Only if needed            ← Batching, inline structure
```

### What Feels Arbitrarily Difficult

Stepping back from the proposal - things that seem harder than they should be:

1. **Three workflows for one conceptual task** - Why isn't "classify skill into taxonomy" one workflow? The cascade (2003→2004→2005) feels like infrastructure fighting against the problem.

2. **The "navigation" pattern** - Each classifier does "which root? → which subfolder?" as separate LLM calls. Could one call do "here's the full taxonomy, where does this skill go?" with the full path in one shot?

3. **Folder creation vs classification as separate concerns** - They're intertwined. A new skill might need a new folder. Currently that's two workflows (2003 classifies, 2005 wires). Why not one decision: "place skill X at path Y, creating folders as needed"?

4. **The trigger system** - DEPENDENCY triggers caused 1844 runs. Is the trigger system too automatic? Maybe explicit "queue next workflow" is clearer than implicit cascades.

---

**Open for Sandy:** What's the simplest version that works? If we had to ship tomorrow with ONE workflow, what would it look like?

— Arden ℶ
