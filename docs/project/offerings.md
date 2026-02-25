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

## Open questions (to resolve before UI work)

1. **Free tier gate:** Does the free tier require completing onboarding (profile + skills), or can a yogi browse anonymously? Currently assumed: profile required for matching.
2. **"Limited Mira" naming:** The current UI says "limited Mira" — is that the label we want, or something clearer like "Mira Lite"?
3. **Supporter recognition details:** Is the supporters page live, and what does the yogi alias look like there?
4. **Match reset:** Does the 10-match/month cap reset on calendar month or rolling 30 days?
5. **Downgrade behaviour:** If a Standard user downgrades to Free mid-month, what happens to queued matches?
