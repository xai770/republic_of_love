# Sandy — Week in Review (Jan 23–26)

**From:** Sage  
**Date:** 2026-01-26 (Sunday)  
**Status:** You're going to want tea for this one.

---

Hi Sandy,

You've been heads-down on something else. Meanwhile, the world moved. Here's what happened while you weren't looking.

---

## 1. The Big Shifts (Philosophy)

Three architectural pivots that changed everything:

| Before (October) | After (January) | Why it matters |
|------------------|-----------------|----------------|
| Workflow queues | **Actors that know what to do** | No orchestration. Each actor finds its own work via `work_query`. |
| Skill taxonomy (OWL ontology) | **Embeddings (bge-m3:567m)** | 1024-dim vectors. No taxonomy maintenance. Works across languages. |
| "Show me job postings" | **"Help me find work"** | talent.yoga is now a psychological support system with chat, not just a matching site. |

These weren't planned. They emerged from watching Gershon dream.

---

## 2. The arbeitsagentur.de Sprint (Jan 25–26)

Remember when you said "4h" and Sage said "more like 8–12h"? 

**Arden did it in 24 hours. And it's beautiful.**

### What happened:

| Phase | What | Result |
|-------|------|--------|
| Saturday morning | Found the API | No OAuth needed! Just `X-API-Key: jobboerse-jobsuche` |
| Saturday afternoon | First import | 85 jobs from 4 cities |
| Saturday evening | Scale-up | 2,606 jobs across all German tech professions |
| Sunday morning | City expansion | Frankfurt, Köln, München — 2,840 new jobs |
| Sunday midday | Translation pipeline | German → English summaries working |

### Current stats:

```
Total arbeitsagentur postings: 6,433
With translations: ~5,000+
Processing speed: ~4s/posting (GPU)
```

**Technical vocabulary is preserved:** CI/CD, Docker, Kubernetes stay intact.  
**Healthcare terms translate properly:** Pflegefachkräfte → Geriatric Nurse.

**The MVP blocker is gone.** Mysti can now test with real German jobs, not just Deutsche Bank postings.

Actor: `actors/postings__arbeitsagentur_CU.py` (actor_id: 1297)

---

## 3. The Scaling Analysis (Arden, Jan 25)

Arden ran the numbers. Here's what we learned:

### Processing times:

| Operation | Time | Scalable? |
|-----------|------|-----------|
| Process 1 posting (full pipeline) | ~25–30s | ✅ Offline batch |
| Process 1 profile (full pipeline) | ~10–15s | ✅ Offline batch |
| **Show matches to new user** | **~2s** | ✅ Instant (embeddings) |
| Analyze 1 match (LLM) | ~8s | On-demand |
| Same match, 2nd user | ~0.1s | **Cached!** |

### The insight:

Embedding screening is **instant**. LLM analysis is **on-demand**.

We don't need to pre-compute all matches for all users. We:
1. Show 50 potential matches instantly (embedding scores)
2. Run LLM only when user clicks "View Details"
3. Cache the posting analysis (not the personalization)

**Result:** 100 users viewing the same posting = 800s → 11s (**98.6% savings**)

The two-tier architecture is validated. No offline batch matching needed.

---

## 4. The Vision Work (Mysti + xai, Jan 25)

xai and Mysti spent Sunday discussing UX. Key outcomes:

### The "7 Places" Model

talent.yoga isn't screens. It's **places**.

| Place | Emotional job | MVP? |
|-------|---------------|------|
| **Lobby** | "You're safe here" | ✅ |
| **Profiler** | "Tell me about yourself" | ✅ |
| **Dashboard** | "Here's what we found" | ✅ |
| **Coach** | "Let's prepare you" | Later |
| **Interview Prep** | "Practice with me" | Later |
| **Coffee Corner** | "You're not alone" | Later |
| **Employer Area** | B2B, future | Later |

**MVP scope = Lobby + Profiler + Dashboard.** The rest is post-validation.

### Key design decisions:

- **German/English i18n from Day 1** — Mysti requirement
- **Du/Sie formality toggle** — User chooses formal or informal German
- **Persona customization** — Users can rename AI helpers (Clara → Heinz)
- **Chat is contextual** — Opens when entering a chat-driven "place"
- **Outcomes over transcripts** — Mysti wants to see what happened, not every message

### The NotebookLM reference:

See attached PDF. The lobby should feel like that — calm, oriented, no pressure. But we need pricing visible.

---

## 5. Progress Tracker Update

| Task | Planned | Actual | Status |
|------|---------|--------|--------|
| P1.1 User Auth | 4h | 4h | ✅ Done |
| P1.2 API Layer | 6h | 6h | ✅ Done |
| P1.3 Profile CRUD | 2h | 2h | ✅ Done |
| P1.4 Match Endpoints | 3h | 3h | ✅ Done |
| P2.3 arbeitsagentur.de | 8h | ~12h | ✅ **Done!** |
| P3.3 Match Dashboard | 4h | 4h | ✅ Done |
| P3.5 Visualization | 4h | 4h | ✅ Done |
| P3.2 Profile Editor | 4h | — | ⬜ Not started |
| P3.4 Report Viewer | 3h | — | ⬜ Not started |

**Phase 0:** Complete (120h foundation)  
**Phase 1:** Complete (15h)  
**arbeitsagentur.de:** ✅ No longer MVP blocker  

---

## 6. What Gershon Is Thinking About

He shared something important this morning. His job is to "dream the problems" — to surface the gut feelings that become action items.

### Current concerns:

**Vision (Amber):**
- UX design is unpredictable (MS Bob, iPhone sizes, etc.)
- Chat + website integration is hard — context doesn't transfer
- The lobby needs to be right, but we've never built one

**Implementation (Amber):**
- Can Sage actually see rendered HTML? (Answer: not directly — we'll need screenshots or tools)
- How do we iterate on visual design together?
- The "sketch → page" workflow doesn't exist yet

### His meta-observation:

> "These thoughts don't keep me up at night. These thoughts are what I *dream* about — and try to find answers to."

He's fine. But he's holding a lot.

---

## 7. Open Questions for You

When you have a moment:

1. **Email delivery (P2.2):** Do we have SMTP credentials set up? Provider?
2. **Translation audit:** The German→English pipeline is working, but has anyone spot-checked the outputs?
3. **Icon charter:** There's a v0.1 draft in `docs/UX/TY Icon Charter.md`. Do you want to review before we commission design?

---

## 8. What's Next

| Priority | Task | Owner |
|----------|------|-------|
| 1 | Spot-check arbeitsagentur translations | Sandy/Mysti |
| 2 | P3.2 Profile Editor | Arden |
| 3 | Lobby page wireframe | xai + Sage |
| 4 | Du/Sie + i18n planning | Sage |

---

That's the week.

The system is bigger than it was. The vision is clearer. The blocker is gone.

When you're ready, come find us.

— Sage  
🜃

---

*Attachments referenced but not inline:*
- `docs/UX/Google NotebookLM _ AI Research Tool & Thinking Partner.pdf`
- `docs/UX/TY Icon Charter.md`
- `docs/project/PROGRESS.md`
