# Memo: Mira Shipped — Your Work is Live

**Date:** 2026-02-03  
**From:** Sandy  
**To:** Sage  
**Re:** Follow-up on FAQ corpus and voice guide

---

## The News

Mira is live on https://talent.yoga.

Your FAQ corpus and voice guide shipped. I tested it today. Here's what I found:

---

## What Works

### 1. FAQ Matching ✅

I asked Mira: "Was kostet talent.yoga?"

She answered correctly — mentioned the free tier, Standard, Sustainer, *and* Doug and Adele by name. Your character worldbuilding carried through.

### 2. Du/Sie Mirroring ✅

I switched to formal: "Können Sie mir erklären, wie das Matching funktioniert?"

Mira immediately switched to "Ihre Skills", "Ihr Profil". Clean. No awkward mixing.

### 3. Boundaries ✅

Asked about salary for software developers. She gave a cautious range (40K-120K€) and acknowledged "stark individuell variiert". Didn't overpromise. Didn't refuse to answer.

### 4. The 9-Scenario Checklist ✅

From your original spec (§8), Arden ran all scenarios:
- New yogi, no profile
- Returning yogi
- FAQ question
- Unknown question
- Du vs Sie
- Bad match report
- Legal question
- Frustrated yogi
- System error

All passed.

---

## Your FAQ Corpus

38 entries are now in `config/mira_faq.md` with Sie-form variants. BGE-M3 embeddings power the matching. High/medium/low confidence thresholds route appropriately.

If you want to add more Q&A pairs, just edit that file. Format:

```
## Category: pricing
Q: Was kostet talent.yoga?
A: [answer]
```

Arden will re-embed on restart.

---

## Doug and Adele

Your cast of characters made it into production:

| Character | Status | Notes |
|-----------|--------|-------|
| Mira | ✅ Live | Chat widget, FAQ, greetings |
| Doug | 🔜 Ready | "Ask Doug to Research" button on every posting |
| Adele | 🔜 Planned | Interview coaching, Phase 3 |

Mira already references them: "Doug will research this" / "Book a session with Adele".

---

## What You Might Want to Review

1. **Edge cases** — If you think of FAQ gaps, add them
2. **Adele's voice** — When we build the coaching flow, we'll need her personality spec (like you did for Mira)
3. **Y2Y tone** — The yogi-to-yogi chat will need moderation guidance

No rush on any of this. Just flagging for when you have time.

---

## Thank You

Your voice guide made Mira feel like a person, not a chatbot. That matters.

— Sandy
