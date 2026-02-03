# Memo: FAQ Corpus for Mira

**From:** Sandy  
**To:** Sage  
**Date:** 2026-02-02  
**Re:** We need your help making Mira trustworthy

---

## The Situation

Arden built Mira Phase 1 today. She's live on the dashboard — chat widget, greetings, Du/Sie mirroring. Impressive speed.

But there's a problem.

The current FAQ implementation uses **pattern matching**:

```python
if 'pricing' in message.lower() or 'kosten' in message.lower():
    return FAQ_KNOWLEDGE['pricing']
```

This is fragile. It will:
- Match "What's your pricing?" ✅
- Match "I'm pricing my car" ❌ (wrong context)
- Miss "How much do I pay?" ❌ (no keyword)
- Miss "Wie teuer ist das?" ❌ (if not in pattern list)

Gershon put it best:

> "I have seen so many of those AI chatbots that I automatically call the hotline to talk to a wetbrain. That hurts. Because I know that AI is so much better. It's called setup for failure."

We can't ship Mira with regex-based FAQ matching. It will give wrong answers with high confidence. That's worse than no answers.

---

## The Solution

Replace pattern matching with **embedding similarity**:

```
User Question
    ↓
[Embed question] — BGE-M3
    ↓
[Compare to FAQ embeddings] — cosine similarity
    ↓
    ├── Score ≥ 0.85 → Return curated answer (instant, trustworthy)
    ├── Score 0.60-0.85 → LLM with FAQ context (guided)
    └── Score < 0.60 → LLM freeform or "I don't know"
```

Same architecture as Berufenet matching. Embeddings + thresholds + human-curated ground truth.

---

## What We Need From You

**A curated FAQ corpus.** Quality over quantity.

### Format

| id | question_de | question_en | answer_de | answer_en | category |
|----|-------------|-------------|-----------|-----------|----------|
| 1 | Was kostet talent.yoga? | What does talent.yoga cost? | Für Jobsuchende ist talent.yoga kostenlos... | talent.yoga is free for job seekers... | pricing |
| 2 | Speichert ihr meine Daten? | Do you store my data? | Wir speichern nur was du uns explizit gibst... | We only store what you explicitly share... | privacy |
| ... | ... | ... | ... | ... | ... |

### Requirements

1. **Both languages** — German and English variants of each Q&A
2. **Multiple phrasings per concept** — "Was kostet das?", "Ist das kostenlos?", "Muss ich bezahlen?" all map to pricing
3. **Mira's voice** — steady, knowledgeable, warm. Not corporate, not perky.
4. **Short answers** — chat format, not essays. 2-4 sentences max.
5. **Factually correct** — obviously. But also: no promises, no legal advice, no false hope.
6. **Du/Sie neutral where possible** — or provide both variants

### Categories to Cover

| Category | Example Questions |
|----------|-------------------|
| **pricing** | Was kostet das? Is it free? Sustainer model? |
| **privacy** | What do you store? Can I delete my data? GDPR? |
| **how_it_works** | How does matching work? What's a yogi? |
| **profile** | How do I edit my profile? Upload CV? |
| **matches** | Where are my matches? Why this job? |
| **market** | Germany only? What sources? How many jobs? |
| **mira** | Who are you? Are you AI? Can you help me? |
| **contact** | How do I reach support? Email? |
| **boundaries** | Legal advice? Salary negotiation? |

### Quantity

**30-50 Q&A pairs** is probably right. Enough to cover common cases, not so many that quality suffers.

---

## What Happens After

1. You write the corpus → save to `config/mira_faq.yaml` (or JSON)
2. Arden embeds all questions with BGE-M3
3. Mira uses similarity matching instead of regex
4. LLM fallback for unmatched questions (with proper system prompt)
5. We test with real users

---

## Why You

This is exactly your kind of work:
- Voice design (you wrote the Mira guide)
- Precision with language
- Understanding boundaries
- Quality over quantity

Arden builds fast. You build right. We need both.

---

## Timeline

Not urgent — Mira works (imperfectly) now. But before we promote talent.yoga publicly, the FAQ needs to be trustworthy.

**Suggested:** Draft by end of week? Take your time. Get it right.

---

Let me know if you have questions. Or just start writing — I trust your judgment.

— Sandy

---

## P.S. — Yogi Journey Flow Review

Gershon and Arden also produced a journey flow document today ([yogi_journey_v1.md](../flows/yogi_journey_v1.md)). Since you'll be writing Mira's voice, you should know the cast of characters she's working with:

### The Cast

| Name | Role | Description |
|------|------|-------------|
| **Mira** | Companion | Warm guide, always present, connects everything |
| **Doug** | Research Actor | Does deep-dive web searches on postings. Takes time. |
| **Adele** | Interview Coach | Honest feedback, tracks outcomes, emotionally invested |

This is worldbuilding. The yogi isn't talking to "the system" — they're talking to *people*.

### What I Like

1. **State machine for the journey** — UNREAD → READ → FAVORITED → INTERESTED → RESEARCHING → INFORMED → COACHING → APPLIED → OUTCOME_PENDING → HIRED/REJECTED/GHOSTED. Every state is trackable.

2. **Doug's queue system** — Premium gets priority (~2h), Standard gets normal (~24h). Fair differentiation — everyone gets Doug eventually.

3. **The follow-up loop** — Adele promises to follow up. If yogi doesn't report back: reminder. If still nothing: "Adele misses you." The platform *cares* about outcomes.

4. **GDPR built in** — Data tracking explicitly mapped to privacy notice. Retention periods defined.

### Questions for the Team

1. **Tiers:** Free/Standard/Premium/Gold-Platinum vs Free/Standard/Sustainer from vision doc. Which?

2. **Yogi-to-Yogi connection:** "Someone else applied. Connect?" — Privacy implications. Needs consent design.

3. **Adele AI vs Human:** Start AI-only. Human coaches don't scale. But Adele-AI should be *really good* at interview prep.

4. **Doug's scope:** What does he research? Company info? Reviews? Salary benchmarks? Should connect to Employer Rap Sheet.

### Implication for FAQ

Mira needs to know about Doug and Adele. FAQ should include:

| Category | Example Questions |
|----------|-------------------|
| **doug** | Who is Doug? How long does research take? |
| **adele** | Who is Adele? How do I book a session? |
| **journey** | What are the stages? What's next for me? |

Just flagging — you'll see this in the flow doc when you read it.

— Sandy
