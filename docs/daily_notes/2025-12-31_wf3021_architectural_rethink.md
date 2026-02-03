# WF3021 Architectural Rethink
**Date:** December 31, 2025  
**From:** Arden + Jakob  
**To:** Sandy  
**Status:** Discussion / Proposal

---

## Context

We spent a painful day debugging WF3021 (Skill Taxonomy Engine). Debug time went exponential - bug after bug, rerun after rerun. When that happens, it's a signal: something structural is wrong.

We stepped way back to examine what's really going on.

---

## What Feels Off

### 1. The Loop That Isn't A Loop

The workflow engine was designed for **linear** flows:
```
extract → classify → act → done
```

But WF3021 is **iterative**:
```
navigate → classify → navigate → classify... → place
```

We're faking loops with branching conditions that route back to earlier conversations. This creates **implicit state passing** - each iteration must reconstruct what happened before by digging through ancestor outputs.

That's where 3+ bugs lived yesterday:
- Getting the OLDEST ancestor instead of NEWEST
- OLD format vs NEW format options_map coexisting
- Variables not extracted in right order

### 2. Two Systems, One Purpose

There's `build_options` (old) and `build_options_v2` (new). There's:
```json
{"a": "__HERE__"}  // OLD format
{"a": {"action": "place", "group_id": 123}}  // NEW format
```

Both exist simultaneously. Every time we touch this code, we're asking "which format am I in?"

### 3. The 400-Line Conditional Monster

`wf3020_navigate.py` does TOO MUCH:
- Parse LLM letter selection
- Look up group from database
- Build new options for next level
- Handle backtrack (go back)
- Handle Victor (new category proposal)
- Handle place_here
- Handle new category creation
- Handle retry on invalid selection

That's 8 different code paths in one function.

---

## The Image That Came Up

**A GPS that keeps recalculating.**

You're driving. You take a turn. GPS says "recalculating..." You take another turn. "Recalculating..." 

Each recalculation looks at where you are NOW and figures out the route from scratch. But sometimes it misreads your position and sends you in circles.

That's what the ancestor extraction is doing - each navigate iteration "recalculates" the state from scratch by reading ancestor outputs. Sometimes it misreads.

---

## The Conceptual Problem

**The workflow engine has no concept of "iteration state."**

- **Linear workflow:** each conversation happens once, outputs flow forward
- **Iterative workflow:** same conversation type happens N times, state evolves

Currently, iteration state is smuggled through JSON outputs and reconstructed by ancestor extraction. This is **fragile and implicit**.

---

## Options for Moving Forward

### Option A: Make Navigation a Single Atomic Actor (Recommended)

Instead of:
```
lookup → (classify → navigate)×N → apply
```

Have:
```
lookup → navigate_until_placed → apply
```

The `navigate_until_placed` actor internally loops, calling the LLM as many times as needed, maintaining its own state. When done, it outputs `target_group`. No ancestor extraction needed.

**Pros:** Cleanest solution, eliminates entire bug classes  
**Cons:** Most work - rewriting core navigation logic

### Option B: Explicit Workflow State

Add a `workflow_state` JSONB column to `workflow_runs`. Each actor reads it, modifies it, writes it back. No more reconstructing state from ancestor outputs.

**Pros:** Works with existing conversation structure  
**Cons:** New pattern to maintain, migration needed

### Option C: Accept Complexity, Clean It Up

- Delete old format entirely (no more `__HERE__`)
- One options_map format everywhere
- Split navigate.py into smaller functions
- Add comprehensive logging for state at each step

**Pros:** Least disruptive  
**Cons:** Doesn't fix the fundamental "loop via branching" issue

---

## Our Take

**Option A is cleanest.** The "loop via branching" pattern is fighting the system's design. A single actor that owns the iteration would eliminate entire classes of bugs.

The current approach works *sometimes*, but debugging it is archaeology - reconstructing what happened from scattered ancestor outputs.

---

## Current Test Status

We have 100 skills running through WF3021 right now with the latest fixes:
- Removed PLACE HERE at TOP LEVEL
- Added `needs_review` catchall category
- Fixed ancestor extraction ordering

We'll see if it works, but even if it does, the fragility remains.

---

## Questions for Sandy

1. Does Option A (single atomic navigator) align with how you see the system evolving?
2. Are there other workflows that will need iteration? (If so, Option B might be more general)
3. Is there a simpler mental model we're missing entirely?

---

## Update: Bug Found and Fixed (07:30)

**Good news:** We found the root cause and WF3021 is now working!

### The Actual Bug

Two prompt-building paths exist:
1. `interaction_creator.py` - sorts ancestors by depth DESC (closest last, overwrites correctly)
2. `executors.py._build_ai_prompt()` - iterates in conv_id order with `if key not in variables` (first wins!)

The runner calls BOTH - interaction_creator builds the correct prompt, then executor rebuilds it WRONG and overwrites via `update_interaction_prompt()`.

**Result:** Classify prompt got `options_map` from lookup (TOP LEVEL) instead of from navigate (current navigation state). The LLM was shown the wrong options!

### Fixes Applied

1. **executors.py lines 138-142** - Removed `if key not in variables` check:
   ```python
   # Before (buggy):
   if key not in variables:
       variables[key] = str(value)
   
   # After (fixed):
   variables[key] = str(value)  # Later parents overwrite earlier
   ```

2. **wf3020_lookup.py** - Added `retry_feedback: ""` to nav_context (needed on first classify, navigate only sets it on retry)

### Test Results

**14 `belongs_to` relationships created!** Skills now properly placed:
- Budget-related skills → `financial_operations`
- `BPO/SSC Experience` → `financial_operations_support`  
- `Brand Awareness Enhancement` → `entrepreneurial_competencies`
- `Bug tracking software` → `problem_solving_&_innovation`
- Banking knowledge → `financial_services_products`

### Reflection on Architecture

This bug validates the concern in Option A. The "ancestor extraction" pattern is fragile because:
- Multiple code paths rebuild prompts differently
- Variable precedence rules are implicit and inconsistent
- Debugging requires archaeology through 3+ files

The fix works, but it's a band-aid. The fundamental issue - **implicit state passing through ancestor outputs** - remains. Every new workflow touching this pattern risks similar bugs.

**Recommendation stands:** Option A (single atomic navigator) would eliminate this entire bug class. But for now, WF3021 is functional and we can process skills while planning the refactor.

---

## Update: Batch Test Results & Fixes (08:15)

### Test Results Summary
- **Queue status:** 237 completed, 1 failed
- **Skills properly placed:** 83 (35%)
- **Placed at TOP LEVEL:** 12 (no `belongs_to` created)
- **Failed due to invalid letter loops:** 81

### Root Cause: LLM Letter Confusion

When the LLM drills down to a **leaf node** (no subcategories), the only valid options are:
- `[a]` - PLACE HERE
- `[z]` - GO BACK
- `[n]` - NEW CATEGORY

But the LLM has seen letters like `[p]` (problem_solving) earlier in navigation history. It picks `[p]` at the leaf node, navigate rejects it, LLM retries... and picks `[p]` again. Loop until max iterations.

### Fixes Applied

#### 1. Use `[p]` for PLACE HERE (work WITH the LLM)

Instead of fighting the LLM's tendency to pick `[p]`, we now make `[p]` = PLACE HERE:

```python
# wf3020_taxonomy_navigator.py - build_navigation_context()
options_lines.append(f"p. ** PLACE HERE ** - {place_desc}")
options_map['p'] = {'action': 'place', 'group_id': current_group_id}
```

This way, when the LLM picks `[p]` at a leaf, it's valid and means "place here" - exactly what we want.

#### 2. Enhanced Retry Feedback at Leaf Nodes

When the LLM picks an invalid letter at a leaf, the feedback is now explicit:

```
⚠️ INVALID: [a] is not available here.
You are at a LEAF NODE with NO subcategories to navigate into.
Your ONLY options are:
  [n] - NEW CATEGORY (propose subcategory)
  [p] - PLACE HERE (put skill in this category)
  [z] - GO BACK (return to parent)
Please respond with ONLY one of: [n], [p], [z]
```

### Files Modified
- `core/wave_runner/actors/wf3020_taxonomy_navigator.py` - Changed PLACE HERE from sequential letter to `[p]`
- `core/wave_runner/actors/wf3020_navigate.py` - Added `p` to letter normalization, enhanced leaf node retry feedback

### Expected Impact
- The 81 failures from invalid letter loops should now succeed (LLM picks `[p]`, it works)
- Clearer feedback helps LLM recover if it picks other invalid letters

---

*Happy New Year's Eve! Let's start 2025 with cleaner architecture.* 🎉
