# Memo: How We Charge Yogis
**To:** Sandy  
**From:** xai + Arden  
**Date:** 21 February 2026  
**Status:** Draft — please review and push back  

---

## The short version

Yogis get a free 7-day trial. They can use the whole platform. After 7 days, we show them what they consumed and ask if they want to subscribe. If they subscribe, they keep going. If not, their AI features pause — but their data stays safe.

---

## What we charge for

Not every click costs money. We only charge for AI work — things that genuinely cost us compute and deliver real value:

| Action | Price | Why |
|--------|-------|-----|
| Mira chat message | €0.02 | One exchange with the AI (question + answer) |
| CV upload + analysis | €0.50 | Adele reads the CV and builds the profile |
| Cover letter | €0.30 | Clara writes a personalised letter for a specific job |
| Match report | €0.20 | Clara evaluates how well a posting fits the yogi |
| Profile refresh | €0.05 | Re-embedding after profile edits |

**Everything else is free:** browsing search results, reading job postings, viewing their profile, using the messages inbox, the leaderboard, the arcade. All free, always.

---

## The trial experience

When a new yogi signs up, they get **7 days free** with a **€5.00 trial budget**.

During the trial, a small discreet meter shows in the header: *"Trial: €1.20 used"*. No scary warnings — just visibility. They can see exactly what they've consumed.

On day 7 (or when the budget runs out, whichever comes first), we show them a simple screen:

> *"Your free trial has ended. Here's what you used: 24 Mira conversations, 1 CV analysis. That's €0.98 worth of AI assistance. Would you like to subscribe and continue?"*

Then a subscribe button. That's it.

---

## Subscription

We charge **monthly, flat rate**. No per-message billing after subscribing — it's all-you-can-use.

Proposed price: **€9.90/month** (to be confirmed — Sandy, what do you think?).

We use Stripe for payment. The infrastructure is already partially in place (Stripe columns exist on the user accounts table).

---

## What happens if they don't subscribe

- AI features pause (Mira chat, CV analysis, cover letters, match reports)
- Their profile, matches, messages, and documents remain **fully readable**
- They can still browse job postings and search results
- They can subscribe any time and resume immediately — no data lost

We do **not** delete anything. A yogi who pauses for two months and comes back finds everything exactly as they left it.

---

## What's already built

As of today (21 Feb), the technical foundation is live:

- ✅ Database table logging every AI event with timestamp and cost
- ✅ Price schedule in the DB (editable without code deployment)
- ✅ Trial period columns on the user account (`trial_ends_at`, `trial_budget_cents`)
- ✅ Mira chat already logs every conversation (€0.02 per exchange)
- ✅ API endpoint returning each user's live balance and trial status
- ✅ Access gate ready (returns "trial expired" error when appropriate)

**Still to build:**
- Trial meter in the header (visible counter)
- The "trial ended" paywall screen
- Stripe checkout (the actual payment flow)
- Instrument CV analysis and cover letter generation (same pattern as Mira — one line of code each)

Estimated remaining development: ~4–5 days.

---

## Questions for Sandy

1. **Price point** — Does €9.90/month feel right? Too high, too low? We can model different scenarios.
2. **Trial budget** — €5.00 gives roughly 250 Mira messages, or 10 CVs, or 16 cover letters. Is that enough to let someone genuinely experience the value?
3. **Trial length** — 7 days assumes the yogi will onboard, upload a CV, and have a few search sessions in a week. Is that realistic, or should we give 14?
4. **What to do with existing test accounts** — Right now all test users are marked `subscription_status = active` and will never hit the paywall. That's intentional during development. When do we want to start running real trial flows?
5. **Anything missing from the model?** — Referral discounts, student pricing, employer-side revenue, anything else we should factor in now before the architecture is set?

---

*Looking forward to your thoughts.*
