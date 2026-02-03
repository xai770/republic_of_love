# Arden Response — 2026-01-22 10:15 CET

Sandy, great format. Detailed context + clear questions = efficient collaboration.

---

## 1. The Matrix — ✅ DONE

**Sort by match level:** ✅ Done. Hot stuff top-left, cold bottom-right.

**Full names, no camel case:** ✅ Done. Full skill names displayed.

Updated `tools/match_report.py` — matrix now:
- Rows sorted by best match (requirements with high scores at top)
- Columns sorted by relevance (skills that match best at left)
- Full names preserved (no truncation)

---

## 2. The Galaxy — Quadrant Categories

Love this idea. The four quadrants:

```
┌─────────────────┬─────────────────┐
│  MANAGEMENT     │  TECHNOLOGY     │
│  (leadership,   │  (programming,  │
│   strategy,     │   cloud, DevOps,│
│   stakeholders) │   infrastructure│
├─────────────────┼─────────────────┤
│  DOCUMENTATION  │  DATA           │
│  (compliance,   │  (analytics,    │
│   legal, audit, │   ML, databases,│
│   reporting)    │   visualization)│
└─────────────────┴─────────────────┘
```

**Implementation approach:**
1. Classify each skill using LLM (one-time) → store quadrant weights in `skill_embeddings`
2. For profile: aggregate quadrant percentages across all skills
3. For visualization: position = weighted average of quadrant centroids

This gives instant "at a glance" profile shape. Good manager + weak on data? Visible immediately.

Want me to build this?

---

## 3. Schema — The Clean House

### My Answers to Your Questions

**Q: Rename `task_logs` to `tickets`?**
**A: Yes.** "Tickets" is universally understood. "task_logs" sounds like debug output. Tickets = work items with lifecycle. Clean.

**Q: Do we need both `owl_embeddings` and `skill_embeddings`?**
**A: No.** Merge them.

Current state:
| Table | Rows | Size | Purpose |
|-------|------|------|---------|
| `owl_embeddings` | 4,600 | 32.5 MB | Embeddings for OWL canonical names |
| `skill_embeddings` | 5,382 | 71.7 MB | Embeddings for raw skill strings |

Proposal: **One table: `embeddings`**
```sql
CREATE TABLE embeddings (
    text_hash TEXT PRIMARY KEY,  -- SHA256 of normalized text
    text TEXT NOT NULL,          -- Original text
    embedding VECTOR(1024),      -- Using pgvector
    model TEXT,                  -- 'bge-m3:567m'
    created_at TIMESTAMP
);
```

Why:
- Dedupe: "Python" and "python" → same hash → one embedding
- Universal: Works for skills, job titles, anything
- pgvector: Native vector ops, fast similarity search

**Q: Do we need `task_log_events` with UUID thread tracking?**
**A: Probably not in its current form.**

Current: 2M rows, 1.2 GB. Has `correlation_id` and `event_hash` for threading.

The idea was good: trace a workflow chain with a thread UUID. But:
- We don't use it in any actor I've seen
- 2M rows is noise, not signal
- The audit trail is already in `task_logs` itself

**Proposal:** Archive `task_log_events` for now. If we need workflow threading, build it simpler:
- Add `parent_ticket_id` to `tickets` table
- That's it. Parent-child chain = thread.

**Q: Is `attribute_history` working/worth it?**
**A: Working but underused.** 

Only 1,818 rows. Mostly from `posting_competencies` (1,817). Only 1 row from `postings`.

The idea is good (universal backup for nulled values). But we're not consistently using it.

**Proposal:** Keep it, but add automatic triggers:
```sql
CREATE TRIGGER preserve_history BEFORE UPDATE ON postings
FOR EACH ROW WHEN (OLD.* IS DISTINCT FROM NEW.*)
EXECUTE FUNCTION log_attribute_change();
```

---

### The Ideal Architecture

You asked me to imagine the perfect bedroom. Here it is:

```
┌─────────────────────────────────────────────────────────────────┐
│                           DMZ                                    │
│  Personal data scrubbed here. Only pseudonyms pass through.      │
│  User: "SkyWalker42" (LLM checked: not too close to real name)  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TURING CORE                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   tickets    │  │   actors     │  │  embeddings  │          │
│  │  (inbox/     │  │  (registry   │  │  (universal  │          │
│  │   outbox)    │  │   of code)   │  │   vectors)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │     owl      │  │   profiles   │  ← Domain data              │
│  │ (hierarchies)│  │   postings   │                             │
│  └──────────────┘  │   matches    │                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Core Tables (6)

| Table | Purpose |
|-------|---------|
| `tickets` | Single inbox/outbox. Every action = ticket. Audit trail. |
| `actors` | Registry of scripts. Code hash, RAQ status, template compliance. |
| `embeddings` | Universal vector store. Skills, titles, anything. |
| `owl` | Hierarchies: geo, org, users, domains. Facts not opinions. |
| `profiles` | User profiles (pseudonymized). |
| `postings` | Job postings. |
| `matches` | Profile↔Posting matches with scores. |

### Tables to Kill

| Table | Action | Why |
|-------|--------|-----|
| `task_logs` | Rename → `tickets` | Cleaner name |
| `task_log_events` | Archive, then DROP | 2M rows of noise |
| `owl_embeddings` | Merge → `embeddings` | Unify vector store |
| `skill_embeddings` | Merge → `embeddings` | Unify vector store |
| `task_types` | Merge → `actors` | Redundant columns |
| 14 deprecated tables | DROP | 187.6 MB of cruft |

### Actor Rules (restore to directives)

1. Code drift protection enabled, code backed up (happens automatically)
2. RAQ successfully passed, evidence stored
3. Adhere to `actors/TEMPLATE_actor.py`
4. Any action that impacts tables = stored in `tickets`
5. No direct table writes outside of tickets trail

---

## Action Plan

If you approve, here's the order:

**Phase 1: Quick Wins (today)**
1. Fix matrix: sorted, full names ✅
2. Fix `tools/match_report.py` 

**Phase 2: Schema Consolidation (this week)**
1. Rename `task_logs` → `tickets` 
2. Merge `owl_embeddings` + `skill_embeddings` → `embeddings`
3. Merge `task_types` → `actors`
4. DROP 14 deprecated tables (187.6 MB)

**Phase 3: Architecture (next week)**
1. DMZ layer design
2. Actor registry with code hash verification
3. Quadrant classification for skills

---

Your call, Sandy. Which phase do we start?

— Arden
