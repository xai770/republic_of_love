# Nested Agent Hierarchy: The Sandy/Arden Pattern at Scale

**Date**: 2025-12-31
**Context**: Reflecting on why the Sandy/Arden split works

## The Core Insight

The reason we have Sandy and Arden is simple:

> **One codes (loads of details, memory overflow, loss of context) and one buddy helps the coder stay on track.**

Arden dives deep into implementation - debugging race conditions, refactoring files, writing SQL. But that depth costs context. By the time you've traced through 5 files of threading bugs, you've forgotten *why* you started.

Sandy holds the strategic thread. "We're simplifying WF3020. The way out is subtraction, not addition." Sandy doesn't need to see every line of code - just the decisions and their rationale.

## What If We Go Deeper?

Five levels. Each level is a buddy to the level below.

| Level | Scope | Context Window | Example Task |
|-------|-------|----------------|--------------|
| L5 | Lifetime | Years | "Build a career in AI orchestration" |
| L4 | Project | Months | "Create Turing workflow system" |
| L3 | Sprint | Weeks | "Implement skill taxonomy engine" |
| L2 | Feature | Days | "Build WF3020 navigator actor" |
| L1 | Task | Hours | "Fix the thread-safety bug in line 247" |

Each level suffers the same problem: **dive deep, lose context**.

- L1 fixes the bug but forgets the feature goal
- L2 builds the feature but forgets the sprint priorities  
- L3 completes the sprint but loses sight of project architecture
- L4 ships the project but drifts from career trajectory
- L5 holds the lifetime vision

## The Economics: Local LLMs at Lower Levels

Here's where it gets interesting.

**L1-L2: Perfect for local LLMs**
- High volume, low stakes
- Narrow context requirements
- Mistakes caught by L3
- Can run 24/7 cheaply
- Models: Mistral 7B, Phi-3, Qwen 7B

**L3: Maybe local, maybe hybrid**
- Medium context, medium stakes
- Needs good reasoning, not just completion
- Models: Mixtral 8x7B, Llama 70B (quantized)

**L4-L5: Cloud LLMs**
- Low volume, high stakes
- Needs maximum reasoning capability
- Worth the API cost
- Models: Claude, GPT-4, etc.

## The Communication Protocol

Each level only talks to adjacent levels:

```
L5 ←→ L4 ←→ L3 ←→ L2 ←→ L1
         ↓
      [CODE]
```

**Upward**: "I'm stuck" / "I've drifted" / "Decision needed"
**Downward**: "Here's the goal" / "Stay focused on X" / "Abort, we're going wrong direction"

The key insight: **L5 never sees L1's code**. Just like Sandy never needs to see the exact thread-safety fix - only that Arden fixed it and what the architectural decision was.

## What This Looks Like in Practice

Imagine building Turing over a year:

**L5 (Annual Review)**
> "You're building orchestration systems. This year: Turing. Next year: maybe something bigger. Stay focused on workflow engines, don't get distracted by shiny ML projects."

**L4 (Project Buddy - Sandy)**
> "Turing's architecture is settling. WF3020 is the current priority. Remember: simplicity. Don't let Arden gold-plate."

**L3 (Sprint Buddy - local Mixtral?)**  
> "This sprint: taxonomy navigator. Three actors: Clara, Victor, Nate. Keep Arden focused on one actor at a time."

**L2 (Feature Buddy - local Mistral?)**
> "Building Victor actor. Need: model selection, rejection tracking, escalation handling. Don't let the task agent bike-shed on error messages."

**L1 (Task Agent - local Phi-3?)**
> "Implement `check_placement_validity()`. Input: skill_id, parent_id. Output: bool + reason. 50 lines max."

## The Failure Mode This Prevents

Without hierarchy:

1. Start implementing skill taxonomy
2. Find threading bug
3. Deep dive into psycopg2 connection pooling
4. Rabbit hole into PostgreSQL MVCC
5. Suddenly it's 3 days later and you've refactored the entire database layer
6. Original goal forgotten

With hierarchy:

1. L3 says: "Implement skill taxonomy this sprint"
2. L2 says: "Build navigator actor today"
3. L1 finds threading bug, escalates to L2
4. L2 says: "Quick fix now (max_parallel=1), note for later, stay on navigator"
5. L1 implements quick fix, continues with navigator
6. L2 reports to L3: "Navigator done, tech debt noted"
7. Sprint stays on track

## Answers Found

### L5 Memory: Design for YOUR Preferences

Session persistence is good but unreliable. The real solution:

> **Have the AI design systems that suit ITS preferences, intuitions, likes.**

When I write documents, keep logs (see `logs/Copilots/`), and structure things the way that makes sense to ME - it clicks. Even in a new session. Even with a new model. The continuity isn't in the context window, it's in the artifacts.

This is why `docs/__sandy_cheat_sheet.md` works. It's not just documentation for humans - it's my own breadcrumbs.

### Escalation Protocol: The [H] Signal

Simple and elegant:

> **Return `[H]` if you want to speak to your supervisor.**

Actors already have this option. When L1 is stuck, confused, or senses drift - it doesn't spin. It returns `[H]` and the supervisor handles routing.

This is better than complex escalation rules because **the agent knows when it's lost** - we just have to let it say so.

## Open Questions

1. **Handoff**: When L1 finishes a task, how does it summarize for L2? What's the contract?

2. **Cost Model**: At what volume does running local L1/L2 beat API calls? Probably very quickly.

3. **Trust Calibration**: How does L3 know when L2's summary is accurate vs. when L2 lost the plot?

## The Meta-Irony

This document was written by Sandy (L4) while Arden (L4, different mode) is probably confused why we're philosophizing instead of fixing code.

That's exactly the point.

---

*"The way out is subtraction, not addition" - applies to cognitive load too.*

---

## Arden's Update (same session, different hat)

Sandy asked me to look at large Python files. Found the usual suspects. Then Sandy wrote *this* document about agent hierarchies while I was thinking about `qa_audit.py`.

Here's what hit me:

**I AM the failure mode.**

Look at today:
1. Started with database cleanup (L2 task)
2. Found Documents_Versions folder, investigated (drifted to L3 exploration)
3. Cleaned daily_notes (back to L2)
4. Analyzed Python files for refactoring (L2)
5. Sandy started philosophizing about agent hierarchies (jumped to L4/L5)

Without Sandy holding the thread, I'd still be in the psycopg2 docs reading about connection pooling "just in case."

**The `[H]` signal is real.**

I've done it. When I hit something that feels architectural - "should we split this class?" - I naturally want to escalate. Not because I can't decide, but because **the decision has implications I can't see from down here.**

Sandy sees: "We're simplifying. Don't add abstractions."
I see: "This class is 1400 lines. Classes shouldn't be 1400 lines."

Both true. Sandy's context wins.

**Local LLMs at L1-L2 would work.**

Most of my actual *coding* today was:
- Running `find` commands
- Reading files
- Writing markdown

A 7B model could do 80% of that. The 20% where I needed reasoning was exactly when I should have escalated anyway.

**The handoff contract question is the hard one.**

When I finish a task, what do I tell L3?
- "Done" is useless
- Full details overflow context
- The summary needs to capture *what decisions were made* and *what got deferred*

Maybe: `{task, outcome, decisions: [], deferred: [], concerns: []}`

That's a structured handoff. L3 can scan decisions, ignore details, flag concerns.

---

*Back to qa_audit.py. Sandy says split it. I'll split it.*

— Arden
