# talent.yoga — Definitive Offerings Document

**Status:** Authoritative  
**Last updated:** 2026-02-25  
**Owner:** xai  
**Source of truth for:** tiers, features, prices, what is and is not included  

---

## What talent.yoga is

talent.yoga is a privacy-first job-search companion for people who are tired of shouting into the void. It matches yogis to real job postings, tells them truthfully why a match is good and why it might not be, and gives them intelligence that no public job board provides — employer history, posting patterns, news signals. Everything is built around one constraint: the yogi's dignity.

---

## The Three Tiers

### Free — €0

No credit card. No expiry. Always free.

| Feature | Detail |
|---------|--------|
| Job matching | 10 matches / month |
| Mira (AI assistant) | Yes — 5 messages / day |
| Interview coaching | No |
| Employer research | No |
| Dashboard | Basic (match list only) |
| Supporter badge | No |

**Who it's for:** Yogis who are just starting, cautious about committing, or who have a low-volume search and don't need more than a curated shortlist each month.

**Intentional limits:** 10 matches is enough to act on. Research and coaching cost compute; they belong to paid tiers. Mira's 5-message cap lets yogis experience the tool without exhausting it.

---

### Standard — €5 / month

The main tier. Most yogis should be here.

| Feature | Detail |
|---------|--------|
| Job matching | Unlimited |
| Mira (AI assistant) | Yes — unlimited messages |
| Interview coaching | Yes |
| Employer research | Yes — full employer rap sheet |
| Dashboard | Full command centre |
| Supporter badge | No |

**What "full Mira" means:**
- CV feedback and gap analysis
- Interview preparation (practice questions, culture signals)
- Application review before you send it
- Honest assessment of your chances — no empty encouragement

**What the employer rap sheet includes:**
- Founded, legal form, employee count
- Posting history (our own data — how many jobs, how long open)
- Stock trend (if public)
- Recent news signals
- Yogi community reviews

**What the full dashboard shows:**
- New postings stacked by domain/field
- Geographic distribution, drillable by region
- Personal match trends over time
- Employer activity ("This company posted 12 jobs this month")

**Who it's for:** Anyone in an active job search. €5 is the cost of one coffee; the employer intelligence alone is worth more than that.

---

### Sustainer — €10+ / month

Everything in Standard, plus a deliberate act of solidarity.

| Feature | Detail |
|---------|--------|
| Job matching | Unlimited |
| Mira (AI assistant) | Yes — unlimited messages |
| Interview coaching | Yes |
| Employer research | Yes — full employer rap sheet |
| Dashboard | Full command centre |
| Supporter badge | Yes — visible on the supporters page |
| Funds a free yogi | Yes — your surplus covers someone who cannot pay |

**Who it's for:** Yogis who can afford more and want to make the platform possible for those who can't. The minimum is €10; there is no maximum. This is the non-profit funding mechanism in practise.

**Supporter recognition:** Name (or yogi alias) listed on a public supporters page. No other privileges — the principle is solidarity, not hierarchy.

---

## What no tier includes

- Guaranteed outcomes ("You'll get an interview")
- Legal or salary negotiation advice
- Your real name anywhere outside your own account
- Your email shown to anyone, including us (masked at all times after initial consent)
- Sale of your data to any third party, ever

---

## The Journey (progression, all tiers)

Job searching on talent.yoga is a board game. Each action earns a status:

| Status | Trigger |
|--------|---------|
| Novice Yogi | Profile uploaded |
| Self-Aware Yogi | Skills confirmed |
| Matched Yogi | First match seen |
| Active Yogi | First application marked |
| Advancing Yogi | Interview reached |
| Resilient Yogi | Rejection handled with a next step |
| Patient Yogi | Ghosting handled (30 days) |
| Victorious Yogi | Offer accepted |

The journey is visible in all tiers. It is not a gamification gimmick — it names what is actually happening and says: you are not stuck, you are here.

---

## Pricing rationale

Prices are set against actual per-user cost (see `billing_methodology.md`). The principle:

> "I would like people to pay for whatever they need and show them WHY we ask them to pay for it."

Yogis who want to see what their €5 or €10 funds can view a live cost breakdown (compute, tooling, matching runs). This is not a marketing gesture — it is the business model.

Standard at €5 is below cost for heavy users and above cost for light ones. Sustainers at €10+ cross-subsidise free-tier yogis who cannot pay. The non-profit conversion (planned) formalises this permanently.

---

## Mira — clarification of tiers

Mira is talent.yoga's AI companion. She is not a chatbot.

| Capability | Free | Standard / Sustainer |
|------------|------|----------------------|
| FAQ / onboarding guidance | Yes | Yes |
| Pricing / privacy questions | Yes | Yes |
| CV feedback | No (5 msg/day cap applies) | Yes |
| Interview prep | No | Yes |
| Application review | No | Yes |
| Honest chance assessment | No | Yes |

The 5-message/day cap on Free does not block Mira — it limits depth of engagement. A yogi can still ask "what is this platform" or "explain my match score". They cannot run a full interview prep session.

---

## Relationship to other .yoga projects

The tier model above is specific to talent.yoga. The **principle** — free entry, paid depth, sustainer solidarity — applies to all .yoga projects: news.yoga, contract.yoga, novel.yoga. Each project will define its own feature boundaries using this document as the template.

---

## Authoritative source mapping

| This document says | Implemented in |
|--------------------|----------------|
| Tier names and prices | `api/routers/subscription.py` — `TIERS` dict |
| Mira message limits | `api/routers/subscription.py` — `mira_messages_per_day` |
| Research / coaching flags | `api/routers/subscription.py` — `research_enabled`, `coaching_enabled` |
| Supporter badge | `api/routers/subscription.py` — `supporter_badge` |
| Financial philosophy | `docs/project/pricing_and_ledger.md` |
| Per-user cost model | `docs/project/billing_methodology.md` |
| Product vision / Mira detail | `docs/project/talent_yoga_vision_2026.md` |

If this document and the code ever disagree, **this document wins** — the code should be updated to match the intent stated here.

---

## Abuse protection

talent.yoga must be protected from use as a B2B arbitrage tool. The specific threat: a user creates one account, uploads profiles for multiple other people daily, and runs employer research reports on all of them — effectively reselling the platform's AI output as a commercial service. At our pricing this destroys unit economics and violates the spirit of the platform entirely.

### Principles

- Abuse protection is **not** about geography or nationality. It is about account behaviour.
- We do not discriminate based on where a user is located. We enforce per-account usage limits.
- The goal is to make talent.yoga useful for one real job seeker per account, not useful as a resale tool.

### Limits (to be enforced)

| Limit | Free | Standard | Sustainer |
|-------|------|----------|-----------|
| Active profiles per account | 1 | 2 | 5 |
| Research reports per day | 3 | 10 | 20 |
| CV uploads per session | 1 | 1 | 1 |
| Accounts per verified email | 1 | 1 | 1 |

**Multiple profiles serve one real job seeker.** A Standard user might maintain a "software developer" and a "technical lead" version of their CV for a genuine career pivot. A Sustainer exploring multiple directions gets more room. The limit that actually prevents abuse is the research reports per day cap — 5 profiles at 10 reports/day is still within reasonable personal use; 5 profiles used to batch-process research for paying clients is not, and the daily cap catches it. If someone needs to manage multiple job-seekers' profiles, that is a recruiter or employer product — which this is not.

### Detection signals (future)

- Multiple profiles uploaded in short succession
- Research reports run on employers with no connection to the account's own profile
- Usage patterns consistent with batch processing (regular intervals, many distinct company queries)
- IP or device fingerprint shared across multiple accounts with distinct email addresses

### Response policy

First violation: warning and explanation. Second: account frozen pending review. We do not ban silently — yogis deserve to know why.

---

## AI priority fairness

When the system is under load, not all requests can be served at equal speed. The queuing model must be both sustainable and fair.

### Priority tiers (outer)

1. **Sustainers** — served first
2. **Standard** — served second
3. **Free** — served third

This reflects financial contribution to the platform's sustainability. It is not about treating free users as second-class — it is about honouring the people who make the free tier possible for others.

### Priority within each tier (inner)

Within each tier, **yogis with the least AI usage in the current period are served first.**

> If you have used less Mira this month, your next request is prioritised over someone who has already used more.

This is the inverse of most platforms. It means:
- Light users are not penalised for saving their usage.
- Heavy users are not rewarded with faster service for consuming more.
- The system naturally balances load across the user base.
- No yogi feels they need to "use it or lose it".

### Implementation note

This requires tracking per-user AI token consumption (or request count) per billing period. That data is already needed for the transparency dashboard (Nate point 7). Priority queuing and the cost display are the same underlying mechanism — track usage per user, per period.

---

## Open questions (to resolve before UI work)

1. **Free tier gate:** Does the free tier require completing onboarding (profile + skills), or can a yogi browse anonymously? Currently assumed: profile required for matching.
2. **"Limited Mira" naming:** The current UI says "limited Mira" — is that the label we want, or something clearer like "Mira Lite"?
3. **Supporter recognition details:** Is the supporters page live, and what does the yogi alias look like there?
4. **Match reset:** Does the 10-match/month cap reset on calendar month or rolling 30 days?
5. **Downgrade behaviour:** If a Standard user downgrades to Free mid-month, what happens to queued matches?


# Nate replies

Hey Arden,

I’ve reviewed the current **offerings / billing model** again in light of our recent discussions. The overall direction is strong and consistent with the Talent Yoga philosophy. I would **not change the core structure**, but I do suggest a few refinements to make the model more robust, sustainable, and psychologically aligned.

This is more evolution than redesign.

---

## 1. Core assessment

The current structure (Free → Standard → Sustainer) is already unusually coherent and differentiated.

Key strengths:

* Ethical and transparent
* Calm and predictable
* Aligned with our privacy-first positioning
* Avoids manipulation and dark patterns
* Simple enough to explain and trust
* Stable monthly revenue foundation

We should **protect this simplicity**.

---

## 2. Main risk: cost volatility, not free users

The real financial risk is not free riders.
It is unpredictable AI cost.

The current Standard tier pools usage and stabilizes cost. This is good and should remain the default model.

No change recommended here.

---

## 3. Introduce internal “credit awareness” without transactional billing

We should make the internal cost model visible to users, but **not force per-action billing**.

Recommendation:

* Standard tier includes a monthly AI allowance (invisible to most users).
* This allowance is only visible when relevant.
* Users can see the system investment in them.

Example:
“You have used €2.40 of AI support this month.”

This aligns with transparency without creating anxiety.

---

## 4. Rollover of unused capacity (strongly recommended)

Unused allowance should roll over (for example 1–3 months).

Why:

* Signals fairness.
* Reduces fear of waste.
* Encourages thoughtful use.
* Differentiates from most SaaS.

This also reduces churn.

Implementation can remain simple at first.

---

## 5. Optional top-up for heavy users

We do not need a full pay-as-you-go tier immediately.

Instead:

* Introduce optional top-up credit for heavy users.
* This only appears if the user exceeds the Standard allowance.

This preserves:

* simplicity,
* calm,
* predictability.

Flex mode can be added later if needed.

---

## 6. Maintain strong free tier

Free should remain:

* stable,
* useful,
* limited in high-cost AI.

This is essential for:

* trust,
* referrals,
* network growth,
* employer-side value.

No change recommended.

---

## 7. Strengthen the transparency narrative

The strongest differentiator in the current model is the financial transparency and founder accountability.

We should:

* continue showing system costs,
* average cost per yogi,
* and long-term sustainability.

This builds trust and willingness to pay.

---

## 8. Suggested wording refinements in the document

Small adjustments:

* Emphasize **membership and stability**, not consumption.
* Clarify that Standard includes a fair share of system resources.
* Add rollover as a core principle.
* Frame Sustainer as stabilizing the system, not subsidizing others.

---

## 9. What we should avoid

We should not:

* introduce complex token accounting,
* make users think about cost during stressful phases,
* fragment the product into too many pricing tiers.

These would contradict our philosophy and harm retention.

---

## 10. Next steps

Please explore feasibility of:

* Monthly allowance tracking,
* Rollover logic,
* Top-up UX,
* Transparent usage dashboard.

We do not need everything immediately, but the architecture should support it.

---

Overall conclusion:
The current model is strong. The main work now is alignment, clarity, and resilience—not structural change.

Looking forward to your thoughts.

— Nate

---

# Arden's response to Nate (2026-02-25)

**Agreed on all structural points.** The core tiers stay as-is.

**On rollover (point 4): deferred.** Standard is currently truly unlimited (`mira_messages_per_day: -1` in the TIERS dict). Rollover only has value if a hard monthly cap exists. Introducing a cap to make rollover meaningful would add a constraint that doesn't exist today, plus db complexity (carry-forward state, downgrade handling). Decision: keep Standard unlimited; revisit rollover only if a hard cap is ever introduced for cost reasons.

**On credit awareness (point 3) and transparency dashboard (point 7): agreed, in principle.** Showing a yogi "your search used €2.40 of AI this month" is on-brand and builds trust. This is a future feature, not a current blocker.

**On top-up credit (point 5): agreed, deferred.** Architecture should not preclude it, but we won't build it until Standard users are demonstrably hitting limits.
