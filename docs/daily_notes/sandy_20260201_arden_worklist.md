# Arden Implementation Worklist — February 2026

**From:** Sandy  
**Date:** 2026-02-01  
**Updated:** 2026-02-02 (Arden progress update)  
**Status:** Active

---

## Overview

The vision doc is done. Sage wrote the Mira voice guide. Now it's implementation time.

This worklist consolidates everything into prioritized, actionable items with dependencies and references.

---

## ✅ Completed (2026-02-02)

Major progress in a single day:

| Item | What Was Built |
|------|----------------|
| **berufe.net scraper** | German occupational database integration |
| **Mira FAQ backend** | BGE-M3 embeddings, 35 Q&A pairs, 233 question variants, confidence thresholds |
| **yogi_messages table** | Unified inbox for Doug/Sage/Sandy/Mysti/Mira/Adele/System/Y2Y |
| **Doug research actor** | DDG search → LLM synthesis → research reports to yogi inbox |
| **Messages API** | Full REST API: list, read, mark-read, send Y2Y, filter by sender/posting |
| **Interactions API** | Phase 1 complete: read/unread, favorites, feedback, state machine |

**Files created:**
- `lib/mira_faq.py` — Embedding-based FAQ matching
- `actors/doug__research_C.py` — Doug's company research actor  
- `api/routers/messages.py` — Messages REST API
- `api/routers/interactions.py` — Interactions REST API

---

## 📚 Reference Documents

| Document | What It Contains |
|----------|------------------|
| [talent_yoga_vision_2026.md](../project/talent_yoga_vision_2026.md) | Full vision, roadmap, open questions |
| [sage_20260201_mira_voice_guide_for_arden.md](sage_20260201_mira_voice_guide_for_arden.md) | Mira voice spec, examples, failure modes, test checklist |
| [P0.7_privacy_architecture.md](../project/P0.7_privacy_architecture.md) | DMZ model, what we store vs don't |
| [P2.2_email_delivery.md](../project/P2.2_email_delivery.md) | Email/notification architecture (reference) |

---

## 🔴 Priority 1: Mira Phase 1 (Onboarding)

**Effort:** 1 week  
**Dependencies:** None  
**Reference:** Sage's voice guide, Vision doc §Mira

### Scope

- [x] **Chat widget** — ✅ DONE (exists in frontend, see screenshot)
- [ ] **Greeting flow** — New yogi vs returning yogi detection
- [x] **FAQ knowledge** — ✅ DONE (2026-02-02)
  - `lib/mira_faq.py` with BGE-M3 embeddings
  - 35 Q&A pairs, 233 question variants from Sage's corpus
  - High/medium/low confidence thresholds
  - Mira can answer: What is talent.yoga? Pricing? Privacy? How matching works?
- [ ] **Tour offer** — "Want me to show you around?"
- [ ] **Profile upload prompt** — "Or upload your profile to get started"
- [x] **"I'll ask" fallback** — ✅ SOLVED (2026-02-02)
  - `yogi_messages` table stores follow-up messages
  - All actors (Doug, Mira, Sage, etc.) write to unified inbox
  - Messages API delivers answers when yogi returns
- [ ] **Du/Sie mirroring** — Detect from yogi's first message, adapt

### Technical Notes

- Can be largely template-based + LLM for FAQ
- No profile context needed yet (that's Phase 2)
- No session memory needed (ephemeral OK for now)
- Test all scenarios from Sage's checklist (§8)

### Open Question: The "I'll Ask" Queue

~~Mira promises to ask and follow up. This needs infrastructure:~~

~~1. `mira_questions` table — Store unanswered questions~~
~~2. Someone/something checks the queue (daily? manual?)~~
~~3. Answer goes back to yogi — **but how?**~~

~~This connects to P1a below (contact consent). If yogi has no email/push, the answer waits for their next visit.~~

**✅ RESOLVED (2026-02-02):** Built `yogi_messages` table as unified inbox. All actors write here. Messages API delivers to frontend. No separate queue needed — messages ARE the queue.

---

## 🔴 Priority 1a: Contact Consent (NEW)

**Effort:** 3 hours  
**Dependencies:** None  
**Reference:** Sis's GDPR research (see vision doc discussion 2026-02-01)

### Why Now

The "I'll ask" fallback only works if we can reach the yogi. Current architecture stores no contact info.

**Decision:** Add opt-in contact storage with explicit consent.

### Scope

- [ ] **Schema change:**
  ```sql
  ALTER TABLE users ADD COLUMN notification_email TEXT;
  ALTER TABLE users ADD COLUMN notification_consent_at TIMESTAMPTZ;
  ALTER TABLE users ADD COLUMN notification_preferences JSONB DEFAULT '{}';
  ```
- [ ] **Consent UI:** Clear checkbox during signup or settings
  - "Store my email to send me job notifications"
  - One-click revoke in settings
- [ ] **Privacy policy update:** Add section on contact data
- [ ] **Deletion:** When yogi deletes account, remove all contact data

### Consent Text (Draft)

> "Soll ich dir Bescheid sagen, wenn es neue passende Stellen gibt?
> Dafür bräuchte ich deine E-Mail-Adresse.
> Du kannst das jederzeit in den Einstellungen ändern."

### Notes

- This is separate from Google OAuth email — we're asking for explicit storage consent
- Start with email only, expand to other channels later (Telegram, push)
- Keep it minimal: just email + preferences (job alerts: yes/no, frequency)

---

## 🟡 Priority 2: Journey Visualization

**Effort:** 1 week  
**Dependencies:** Application tracking needs to exist first  
**Reference:** Vision doc §The Journey

### Scope

- [x] **Journey state machine** — ✅ DONE (2026-02-02)
  - `user_posting_interactions.state` column with full state machine
  - States: unread → read → favorited → interested → researching → informed → coaching → applied → outcome_pending → hired/rejected/ghosted/unresponsive
  - State transitions via API
- [ ] **Visual board** — Show progress like board game
  - Current position highlighted
  - Past positions shown
  - Next possible moves indicated
- [ ] **Badges** — Award on milestones
  - Novice Yogi (profile created)
  - Active Yogi (first application) 🎆
  - Resilient Yogi (continued after rejection)
  - Patient Yogi (continued after ghosting)
- [ ] **"Rest" state** — From Sage's review
  - Mira suggests: "Want to take a break?"
  - Yogi can pause, set reminder
  - Journey shows "resting" state

### New: Doug Research Integration (2026-02-02)

When yogi requests research on a posting:
1. Interaction state → `researching`
2. Doug actor picks it up (batch or triggered)
3. Doug searches DDG, synthesizes with LLM
4. Research report → `yogi_messages`
5. Interaction state → `informed`

**Files:** `actors/doug__research_C.py`, `api/routers/messages.py`

### Technical Notes

- State transitions triggered by yogi actions (mark applied, mark interviewed, etc.)
- GHOSTED = 30 days no response
- Consider: should badges be visible to others? (probably not for MVP)

---

## 🟡 Priority 3: Stripe Integration

**Effort:** 1 week  
**Dependencies:** User accounts must exist  
**Reference:** Vision doc §Business Model

### Scope

- [ ] **Stripe setup** — Create account, get API keys
- [ ] **Subscription products:**
  - Free (€0) — implicit, no Stripe needed
  - Standard (€5/mo)
  - Sustainer (€10+/mo)
- [ ] **Checkout flow** — Redirect to Stripe, handle webhook
- [ ] **Tier enforcement** — Gate features by subscription level
  - Free: 10 matches/month, no Mira
  - Standard: Unlimited matches, Mira, full dashboard
  - Sustainer: Same + supporter recognition
- [ ] **Billing portal** — Link to Stripe's hosted portal for management
- [ ] **Webhook handlers:**
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`

### Technical Notes

- Use Stripe Checkout (hosted) — don't build custom payment forms
- Store `stripe_customer_id` and `stripe_subscription_id` on user
- Handle card failures gracefully (grace period? instant downgrade?)

---

## 🟢 Priority 4: Mira Phase 2 (Context)

**Effort:** 2 weeks  
**Dependencies:** Mira Phase 1, Profile system working  
**Reference:** Sage's voice guide §7, Vision doc

### Scope

- [ ] **Profile awareness** — Mira knows yogi's skills, preferences
- [ ] **Match awareness** — Mira can explain why jobs match/don't
- [ ] **Conversation memory** — Within session (later: across sessions)
- [ ] **Proactive messages:**
  - "3 new matches since your last visit"
  - "That job you saved is still open"
  - "One of your applications was viewed" (if we can detect)
- [ ] **Integration with journey** — Mira knows journey state

### Technical Notes

- RAG architecture: embed profile + matches + conversation history
- System prompt includes yogi context (see Sage's §7)
- Consider token limits — don't stuff everything in every call

---

## 🟢 Priority 5: Web Push Notifications

**Effort:** 3 days  
**Dependencies:** Contact consent (P1a)  
**Reference:** Vision doc §Privacy

### Scope

- [ ] **Service worker** for push notifications
- [ ] **Permission request** — Ask once, don't nag
- [ ] **VAPID keys** — Generate and store
- [ ] **Push on events:**
  - New matches (daily digest or real-time?)
  - Mira has an answer to your question
  - Application status change (if trackable)
- [ ] **Respect preferences** — Yogi can disable per-type

### Technical Notes

- Web Push works without storing email
- Falls back gracefully if permission denied
- Consider: do we need both email AND push? Or pick one?

---

## ⏸️ Parked (Q2+)

These are documented but not scheduled yet:

| Feature | Notes | Blocker |
|---------|-------|---------|
| **Mira Phase 3: Interview Coach** | Role-play, STAR coaching | Needs Phase 2 stable first |
| **Employer Rap Sheet** | Web crawler + extraction | Needs architecture design |
| **Review System** | Post-application feedback | Needs moderation design |
| **Salary Benchmarking** | "Similar roles pay €X-Y" | Needs data source |
| **news.yoga** | Topic aggregation | Separate project |
| **Mobile App** | Native push, offline | After web is solid |

---

## 🧪 Testing Checklist (from Sage)

Before Mira goes live, test these scenarios:

- [ ] New yogi, no profile
- [ ] Returning yogi, has matches
- [ ] Yogi asks FAQ question
- [ ] Yogi asks something Mira doesn't know
- [ ] Yogi uses "Du" vs "Sie"
- [ ] Yogi reports bad match (tests boundary)
- [ ] Yogi asks legal question (tests boundary)
- [ ] Yogi is frustrated (tests empathy)
- [ ] System error during conversation

---

## Questions for Gershon

1. **Free tier limit** — Is 10 matches/month right? Too generous? Too stingy?
2. **Sustainer recognition** — Just name on page? Or something more?
3. **"I'll ask" queue** — Who monitors it? How fast must answers come back?
4. **Rest state** — How long before Mira suggests a break? 4 weeks? 6?

---

## Small Items (Add When Convenient)

- [ ] **Landing page: Germany focus** — Add visible note: "Currently focused on the German job market." Footer or hero section. Honest expectation-setting.

---

## How to Use This Doc

1. Pick a priority item
2. Check dependencies
3. Read the reference docs
4. Build it
5. Update status here
6. Ping Sandy when done or blocked

---

*Let's make Mira real.*

— Sandy
