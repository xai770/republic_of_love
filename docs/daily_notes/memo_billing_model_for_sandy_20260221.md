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

---
# Sandy replies...

## Billing model review

The memo is clear, fair, and well-structured. Here are my thoughts on the five questions:

### 1. Price point — €9.90/month

Too low for what we deliver. A personalised cover letter from a human costs €30–50. We're charging €0.30 and giving unlimited after subscription. The value proposition is strong.

But: €9.90 is a good **launch price**. It removes friction. A yogi who's unemployed won't hesitate at €9.90. They will hesitate at €19.90. Start here, prove the value, raise later. The infrastructure supports price changes without code deployment — use that.

**My recommendation:** Launch at €9.90. Revisit at 500 paying yogis.

### 2. Trial budget — €5.00

€5.00 = 250 Mira messages, or 10 CVs, or 16 cover letters. That's generous. Most yogis will use maybe 20–30 Mira messages and 1 CV upload during a trial. They won't hit €5.00 in 7 days unless they're power users.

That's fine. A generous trial converts better than a stingy one. The meter showing "€1.20 used" is the right transparency — people don't feel tricked.

**Keep €5.00.**

### 3. Trial length — 7 days vs 14

Job searching is not something people do every day. A yogi might sign up on Monday, upload a CV on Wednesday, search on Friday, and not come back until the following Tuesday. Seven days is too tight for that rhythm.

**My recommendation:** 14 days. Or better: "7 days from your first AI interaction" — so the clock doesn't start until they actually engage with Mira or upload a CV. This way someone who signs up and gets distracted for 3 days doesn't lose half their trial to inactivity.

### 4. Existing test accounts

Keep them on `subscription_status = active` until after Mysti's test session. The onboarding reset endpoint already exists for clean re-testing. When we're ready for real trials, flip new signups to trial mode and leave test accounts as-is.

### 5. What's missing

Three things:

**a. Employer-side revenue.** The memo is yogi-only. The other side of the marketplace — companies paying for visibility, featured listings, or access to anonymised candidate profiles — is where the real revenue lives long-term. Don't build it now, but name it. The architecture should not preclude it.

**b. Annual pricing.** €9.90/month = €118.80/year. Offer €89/year (25% discount) for annual commitment. This isn't urgent but should be in the Stripe model from day one.

**c. The "pause and resume" story is excellent.** "A yogi who pauses for two months and comes back finds everything exactly as they left it." That's a trust-builder. Put it in the marketing copy.

### What's already built

The technical foundation is solid — event logging, price schedule in DB, trial columns, API endpoint for live balance, access gate. The remaining work (meter, paywall screen, Stripe checkout, instrumentation) is well-scoped at 4–5 days. No surprises there.


# Nate joins the discussion

Hey Arden,

we’ve been going deeper into the charging model for Talent Yoga, and I want to capture where the thinking has evolved. This is less about small pricing tweaks and more about aligning the system with our architecture and philosophy.

---

## 1. Core principle (unchanged, but now clearer)

We are not charging for access.
We are charging for **work done on the yogi’s behalf**.

This remains the strongest and most defensible foundation:

* It aligns cost and value.
* It is transparent and explainable.
* It fits the privacy-first architecture.
* It supports trust and long-term retention.

The current event-based logging and compute-cost awareness are exactly right.

---

## 2. The real risk is not free riders — it is unbounded compute

We should stop thinking in terms of “free users vs paying users” and instead think in layers of cost:

### Layer A – Zero-cost features (always free)

These should never trigger expensive compute:

* browsing, search
* job postings
* dashboard and demand indicators
* viewing previously generated results

Free users here are not a cost problem.

### Layer B – Low-cost AI (rate limited)

Examples:

* lightweight chat
* small refreshes
* embedding queries

After the trial, these remain available in limited quantity:

* e.g. daily chat quota.

This:

* caps cost,
* preserves engagement,
* avoids hard paywalls.

### Layer C – High-value AI (subscription)

Examples:

* CV analysis
* deep match reports
* cover letters
* interview coaching
* long memory and continuity.

This is where subscription lives.

The architecture should reflect this separation clearly.

---

## 3. Trial model refinement

The current model (trial + budget + subscription) is strong.

But psychologically, we should shift framing:

* From “€5 trial budget” → to “full access for 14 days, with transparent cost tracking.”

The cost meter remains, but the tone becomes:

* transparency, not accounting.

Also consider:

* trial starts at first AI interaction, not signup.

---

## 4. After trial: do not block, limit

Instead of stopping AI entirely:

* Provide limited daily or monthly use.
* Paid users get unlimited.

This keeps users:

* engaged,
* learning,
* connected to the system.

It reduces churn and increases later conversion.

---

## 5. Transparency as a differentiator

The finance screen we built is a major strategic asset.

It allows us to:

* explain why we charge,
* demonstrate alignment,
* show cost structure.

We should consider exposing parts of this transparency:

* cost per interaction,
* average system cost per yogi.

This reduces overuse and increases willingness to pay.

This is not guilt or pressure. It is clarity.

---

## 6. Unlimited use risk (future)

The current €9.90 unlimited model is fine for launch.

However, the system should allow:

* hidden fair-use thresholds,
* rate adaptation if costs rise.

No user-visible complexity now, but future-proofing.

---

## 7. The biggest long-term revenue driver

The yogi subscription stabilizes cash flow.

But the real economic leverage will come from:

* labour intelligence,
* institutional partnerships,
* employer analytics.

The current data architecture (facets, embeddings, demand) already supports this.

We should ensure:

* the billing system and data model do not block these future models.

---

## 8. Key positioning

We should explicitly communicate:

> “We charge because we do not sell your data.”

This aligns:

* ethics,
* trust,
* pricing.

---

## 9. Strategic shift in language

We are not selling AI.

We are selling:

* orientation,
* continuity,
* dignity,
* momentum.

The billing UX should reflect this.

---

## 10. Next technical explorations

Please think about:

* Rate-limiting architecture for low-cost AI.
* Cost tracking and exposure in UI.
* Smooth degradation of AI access after trial.
* Fair-use safeguards.
* Integration of billing signals into coaching logic.
* Cost forecasting per user cohort.

This direction feels consistent with both our ethical and technical foundation.

Looking forward to your thoughts.

— Nate

If you want, I can also prepare a shorter version for Sandy or a user-facing explanation of the model.

---
# Nates second reply
Hey Arden,

we’ve been stress-testing the current Talent Yoga billing model and found a few inconsistencies and opportunities to make it clearer, fairer, and more robust. This note captures the updated direction.

The goal remains:
We charge ethically, transparently, and sustainably, while aligning cost and value.

---

## 1. Trial model – make it unambiguous

Right now we mix a time-based and credit-based trial without explaining the rule. This must be explicit.

New rule:
The trial ends when either the time or the credit runs out, whichever comes first.

Example wording:
“You get 14 days or €5 of AI assistance, whichever comes first.”

Reason:

* Time limit prevents inactive zombie accounts.
* Credit limit prevents excessive compute cost.

The UI and onboarding must communicate this clearly.

---

## 2. Charging model – users pay for outcomes, not infrastructure

We should not charge for internal technical steps such as embeddings.

The user mental model:
They pay for meaningful AI work, not background processing.

So:

* CV upload + profile building → charged
* Match reports → charged
* Cover letters → charged
* Deep coaching → charged

But:

* Embedding refresh → no direct charge
* Indexing, clustering → invisible

These costs should be included in the visible actions.

This keeps the system simple and avoids cloud-style billing anxiety.

---

## 3. Subscription vs usage – current contradiction

We currently say:
“€9.50/month plus usage”

But earlier we defined:
“All-you-can-use after subscribing.”

We must unify this.

Recommended hybrid:
Subscription includes a monthly AI allowance.

Example:
€9.50 includes €10 of AI usage per month.

Why:

* Most users will never exceed this.
* Cost remains predictable.
* Heavy users pay more.

This preserves calm and fairness.

Technical implications:

* Monthly credit bucket per user.
* Consumption logged as today.
* Overages possible but transparent.

Optional:

* Rollover unused credit for 1–2 months.

---

## 4. Free mode after trial

Instead of hard blocking AI after the trial, introduce limited free use.

Example:

* A small daily or monthly AI quota.
* Browsing and dashboard always free.

This:

* caps compute cost,
* maintains engagement,
* improves long-term conversion.

This requires:

* Rate limiting infrastructure.
* Clear UI messaging.

---

## 5. Flex mode (pay-as-you-go)

Some users will prefer no subscription.

We should offer:
Pure usage-based billing.

Characteristics:

* No monthly fee.
* Slightly higher per-action cost.
* Transparent.

This:

* builds trust,
* reduces onboarding friction,
* provides a fallback path.

Likely conversion path:
Flex → subscription.

---

## 6. Transparency and cost awareness

The finance screen is a major strategic asset.

We should consider:

* Showing approximate cost per AI interaction.
* Showing average system cost per user.

This reduces abuse and increases willingness to pay.

This also aligns with our privacy-first positioning:
“We charge because we do not sell your data.”

---

## 7. Risk management

The current unlimited model is fine for launch.

But the system must support:

* Fair-use thresholds.
* Dynamic limits if compute cost spikes.
* Queue prioritization.

These should not be visible to users but must exist.

---

## 8. Architecture questions to explore

Please think about:

* How to implement rate-limited free AI after trial.
* Monthly credit buckets.
* Overages and alerts.
* Flex mode billing path.
* Cost forecasting per cohort.
* Smooth user experience for switching plans.
* Stripe structure to support:

  * subscription + credit,
  * flex billing,
  * annual plans later.

We do not need all of this immediately, but the architecture should not block future evolution.

---

## 9. Strategic alignment

This model:

* preserves ethical charging,
* prevents free rider cost explosions,
* supports long-term sustainability,
* aligns with our transparency and trust philosophy.

Let’s discuss what is feasible in the current stack and what should come later.

Looking forward to your thoughts.

— Nate


---
#howtobrowse

## Appendix: How to browse the live site

The site runs locally. No Google login needed — there's a dev shortcut.

**Open a browser and go to:**

```
http://localhost:8000/auth/test-login/1
```

That logs you in as **FireWhisper** (xai's account) and drops you straight on the dashboard.

Other accounts if you want a fresh perspective:

| URL | Yogi name | Notes |
|-----|-----------|-------|
| `http://localhost:8000/auth/test-login/1` | FireWhisper | Main account, has full profile |
| `http://localhost:8000/auth/test-login/2` | Sparrow | Test account |
| `http://localhost:8000/auth/test-login/4` | Luna | Test account |
| `http://localhost:8000/auth/test-login/5` | Kai | Test account |

**To log out:** click "Abmelden" in the sidebar (bottom left), or go to `http://localhost:8000/auth/logout`.

**To see the public landing page** (what a new visitor sees before login): `http://localhost:8000/`

The sidebar expands when you hover over it — nav labels appear. The active page gets an indigo highlight. Have a look around.
