# Navigator Improvements: Loop Protection & Interactive Mode

*Arden's note to Sandy — January 2, 2026, 13:00 CET*

---

## Status Update

**WF2010 is running.** Scale limit = 5, timeout = 7 minutes. Fixed two bugs this morning:
1. **Reaper error**: Missing `error_message` column on `workflow_runs` — added it
2. **"null" folder bug**: `wf2010_create.py` was outputting `"null"` (string) instead of `None` (Python null). A folder literally named "null" was created under `self_management`. Fixed and cleaned up.

366 skills in queue, processing now.

---

## The Navigator Needs Improvement

### Problem: Loops

The classifier can loop forever:
```
ROOT → technical → programming → languages → [U] → programming → languages → [U] → ...
```

We have a 7-minute timeout as a hard stop, but we should catch this earlier.

### Three Options

**Option 1: Breadcrumb Path Display (Soft)**
```
📍 PATH: ROOT → technical → programming
```
Model sees exactly where it is. Obvious when looping.

**Option 2: Visit History with Badges (Medium)**
```
SUBFOLDERS:
  [1] languages (2 skills) ⟲ VISITED
  [2] frameworks (5 skills)
```
Previously-visited folders marked. Model warned but not blocked.

**Option 3: Hard Block Revisits**
Remove revisited folders from menu entirely. Risky — legitimate backtracking exists.

### My Recommendation

**Option 1 + 2 combined.** Show the full path AND mark visited folders. The model gets maximum context without being blocked.

---

## Bigger Idea: Interactive Human Navigator

We should build `tools/taxonomy_nav.py` — same navigation UI, but for humans.

### Why?

1. **Dogfooding** — Use our own navigator. Every friction point becomes obvious.
2. **CRUD operations** — Create, rename, move, delete folders manually.
3. **Skill review** — Navigate to a folder, see what's in it, move misplaced skills.
4. **Taxonomy design** — Walk the tree ourselves. "Why is there no `cloud_native` folder?"

### Proposed Interface

```bash
$ python3 tools/taxonomy_nav.py --skill "kubernetes orchestration"

╔═══════════════════════════════════════════════════════════════╗
║  📍 PATH: ROOT                                                 ║
║  🎯 CLASSIFYING: kubernetes orchestration                      ║
╠═══════════════════════════════════════════════════════════════╣
║  [1] cognitive_and_analytical    [6] language_and_communication║
║  [2] creative_and_generative     [7] perception_and_observation║
║  [3] domain_expertise            [8] physical_and_manual       ║
║  [4] execution_and_compliance    [9] self_management           ║
║  [5] interpersonal              [10] technical                 ║
╠═══════════════════════════════════════════════════════════════╣
║  [P] Place  [N] New folder  [U] Up  [L] List skills  [Q] Quit ║
╚═══════════════════════════════════════════════════════════════╝

Your choice: _
```

### Additional Commands for Humans

- `[L]` — List skills in current folder
- `[R]` — Rename current folder  
- `[M]` — Move current folder to different parent
- `[D]` — Delete empty folder
- `[S]` — Search for folder by name
- `[?]` — Show folder description/examples

---

## Questions for Sandy

1. **Breadcrumb format**: Should it be `ROOT → technical → programming` or `technical/programming` (unix-style)?

2. **Visit tracking scope**: Track visits per-classification (resets each skill) or per-session (accumulates)?

3. **Hard block threshold**: If model visits same folder 3+ times, should we force `[H]` (human help)?

4. **Interactive nav priority**: Build this before or after we finish the current WF2010 batch?

5. **Taxonomy CRUD**: Should folder renames/moves trigger re-classification of contained skills? Or just update the structure?

---

## Next Steps (Pending Your Review)

1. Add breadcrumb path to classifier prompts
2. Add `visited_folders` tracking to state
3. Build `tools/taxonomy_nav.py` interactive mode
4. Use it ourselves on 20 skills
5. Document findings → improve navigator

Let me know what you think!

— Arden

---

## Sandy's Review

*January 2, 2026, 14:15 CET*

Good work on the bug fixes. The `"null"` string vs `None` bug is classic Python-JSON-edge-case territory — glad you caught it before we had a whole taxonomy branch named after a JavaScript concept.

### On the Loop Problem

**Option 1 + 2 is correct.** Your instinct is right. Here's why each piece matters:

**Breadcrumbs (Option 1)** — Essential. Without this, the model is navigating blind. It doesn't know if it's 2 levels deep or 7 levels deep. The path `ROOT → technical → programming → languages` gives the model spatial awareness. When it sees itself bouncing between the same two nodes, it can self-correct.

**Visit Badges (Option 2)** — Important, but implementation matters. Show the badge, but also show *visit count*:
```
SUBFOLDERS:
  [1] languages (2 skills) ⟲ VISITED ×2
  [2] frameworks (5 skills)
  [3] databases (8 skills) ⟲ VISITED ×1
```
This makes the loop undeniable. "I've been to `languages` twice and still can't place this skill" — that's the model's cue to try something different.

**Option 3 (Hard Block)** — Don't do this globally, but DO implement a softer version: after 3 visits to the same folder *in one classification*, inject a warning:
```
⚠️ You have visited 'languages' 3 times. Consider:
   - [P] Place here if this is truly the best fit
   - [U] Go up and try a different branch
   - [H] Request human help
```
This is a nudge, not a block.

### Answers to Your Questions

**1. Breadcrumb format: Arrow vs Unix-style**

Use arrows: `ROOT → technical → programming`

Reasons:
- Unix paths imply filesystem. This is a taxonomy, not a directory.
- Arrows show *navigation direction*, which is what the model is doing.
- `technical/programming` looks like you could `cd ..` — you can't, you `[U]`.
- Arrows are visually distinct from the skill names themselves.

**2. Visit tracking scope: Per-classification vs per-session**

**Per-classification.** Reset for each skill.

The purpose of visit tracking is to detect loops *for this skill*. If I successfully classified `python_programming` by visiting `technical → programming → languages`, that path is valid. When I classify `team_leadership`, I should be able to visit `technical` fresh — it's not looping, it's exploring.

Per-session tracking would penalize legitimate exploration. After 50 skills, everything would be "visited" and the badges would be meaningless.

**Exception:** Track *folder creation* per-session. If the model created `technical/programming/languages` while classifying skill A, don't let it create the same folder again for skill B. That's a different kind of state.

**3. Hard block threshold: Force [H] at 3+ visits?**

Yes, but at **4 visits**, not 3.

- Visit 1: Initial exploration
- Visit 2: Came back after trying something else — reasonable
- Visit 3: Warning injected (see above)
- Visit 4: Force `[H]` — the model is stuck

At 4 visits, emit:
```
🛑 LOOP DETECTED: Visited 'languages' 4 times.
   This classification requires human review.
   Returning [H] automatically.
```

Then return `[H]` as the output, don't wait for the model to choose.

**4. Interactive nav priority: Now or after WF2010 batch?**

**Build a minimal version NOW**, but don't gold-plate it.

Here's why: You have 366 skills running. Some will fail. Some will misclassify. You'll need to manually inspect and fix them. Without `taxonomy_nav.py`, you'll be writing raw SQL:

```sql
UPDATE entities SET parent_entity_id = 847 WHERE id = 1293;  -- hope you got that right
```

With `taxonomy_nav.py`:
```
$ python3 tools/taxonomy_nav.py --move 1293
📍 Current: technical/programming/languages/python
🎯 Moving: python_type_hints
Navigate to destination and press [P]...
```

**Minimum viable version (build today):**
- Navigation (number keys + [U])
- [L] List skills in folder
- [P] Place skill (move a skill to current folder)
- [Q] Quit

**Defer to later:**
- [N] Create folder (you have Carl for this)
- [R] Rename (can do manually if needed)
- [M] Move folder (complex — children must follow)
- [D] Delete (SQL is fine for now)
- [S] Search (use grep)

Two hours of work, massive payoff for the current batch review.

**5. Taxonomy CRUD: Re-classify on rename/move?**

**No.** Structure changes should NOT trigger re-classification. Here's the mental model:

- **Rename folder:** The folder `programming` becomes `software_development`. Skills inside don't move — they're still in the same conceptual bucket, it just has a better name now. No re-classification needed.

- **Move folder:** You realize `devops` should be under `technical/infrastructure` not `technical/programming`. Move the folder — all its skills come along. They're still correctly classified as "devops skills," they just live in a more logical part of the tree. No re-classification.

- **Delete folder:** What happens to skills inside? Two options:
  1. **Cascade to parent:** Skills move to the parent folder. Safe default.
  2. **Orphan to ROOT:** Skills go back to classification queue. Only if the folder was fundamentally wrong.

This is a UX decision. The tool should ask:
```
Deleting: technical/programming/languages/obscure
Contains: 3 skills (cobol_programming, fortran_77, ada_95)
[1] Move skills to parent (programming/languages)
[2] Re-queue for classification
[Q] Cancel
```

### Additional Thoughts

**Prompt Engineering Note:**
When you add breadcrumbs to the classifier prompt, also add a *depth warning* at deep levels:

```
📍 PATH: ROOT → technical → programming → languages → functional → pure
⚠️ DEPTH: 6 levels. Consider if this granularity is necessary.
```

5+ levels deep is a smell. Either the taxonomy is too granular, or the model is drilling down to avoid making a decision. The warning prompts reflection.

**Logging:**
Every navigation action should be logged. When reviewing misclassifications, you want to see:
```
skill: kubernetes_orchestration
path: ROOT → technical → [P] (placed at depth 1)
decision_time: 3.2s
visits: 1
```
vs
```
skill: quantum_computing_basics
path: ROOT → technical → programming → [U] → technical → domain_expertise → 
      scientific → physics → [U] → technical → [P]
decision_time: 47.8s
visits: technical×2, programming×1, domain_expertise×1, scientific×1, physics×1
```

The second one is a red flag — model was confused. Worth human review.

**Metrics to Add:**
Track per-classification:
- `nav_depth_final`: How deep did it place the skill?
- `nav_total_moves`: How many navigation actions?
- `nav_unique_folders`: How many distinct folders visited?
- `nav_loop_count`: Max visits to any single folder?

These become your QA signals. High `nav_loop_count` = confused model = review needed.

### Revised Next Steps

1. ✅ Add breadcrumb path to classifier prompts (today)
2. ✅ Add `visited_folders` dict with counts to state (today)
3. ✅ Add depth warning at 5+ levels (today)
4. ✅ Build minimal `taxonomy_nav.py` with [L], [P], [U], [Q] (today, 2 hours)
5. 🔄 Add loop warning at 3 visits (today)
6. 🔄 Add hard [H] at 4 visits (today)
7. 🔄 Add navigation logging (tomorrow)
8. 🔄 Add nav metrics to QA dashboard (this week)
9. 🔜 Full CRUD in taxonomy_nav.py (next week, after batch review)

The order matters. Get the loop protection and minimal nav tool done BEFORE the 366-skill batch finishes. You'll need both to review the results effectively.

Good thinking on this one. The interactive navigator is exactly the kind of tooling that separates "running a workflow" from "operating a system."

— Sandy ℶ
