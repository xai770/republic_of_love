# Arden Session — 2026-02-03: Mira Implementation

**Start:** 10:20  
**Focus:** Sandy's worklist — Mira P1, Contact Consent, Journey Viz, Stripe

---

## Plan

1. **Mira P1 (remaining)**
   - [x] Greeting flow (new vs returning yogi)
   - [x] Tour offer
   - [ ] Profile upload prompt
   - [x] Du/Sie mirroring

2. **Contact Consent (~3h)**
   - [x] Schema: notification_email, consent_at, preferences (already existed!)
   - [x] Mira consent prompt endpoint
   - [ ] Privacy policy note (frontend)

3. **Journey Viz**
   - [x] Visual board
   - [x] Badges
   - [x] Summary endpoint

4. **Stripe Infrastructure**
   - [x] Tier definitions
   - [x] API endpoints
   - [x] Webhook handlers
   - [ ] Stripe account setup (needs credentials)

---

## Progress Log

### 10:20 — Session Start

Prior work today: Schema cleanup (dropped 10 columns, 2 tables), smoke tests passed, user testing passed.

Now implementing features from Sandy's worklist.

### 10:27 — Mira P1 Done

Added to `api/routers/mira.py`:

1. **`GET /api/mira/greeting`** — Personalized greeting
   - Detects new vs returning yogi (created_at vs last_login_at)
   - Checks profile status, skill_keywords, recent matches
   - Returns greeting + suggested actions (tour, upload_profile, add_skills, view_matches)
   - Response: `{greeting, is_new_yogi, has_profile, has_skills, has_matches, suggested_actions, uses_du}`

2. **`GET /api/mira/tour`** — Onboarding tour
   - 6 steps: welcome, profile, matches, journey, chat, ready
   - Du/Sie variants
   - Each step has: step_id, title, message, target (CSS selector), action

3. **`detect_formality(message)`** — Du/Sie detection
   - Scans for "du/dich/dir/dein" vs "Sie/Ihnen/Ihr"
   - Chat endpoint now auto-detects formality from first message
   - Falls back to du if not detected

**Test results:**
```
GET /api/mira/greeting → 200 OK
{
  "greeting": "Hey, schön dich wiederzusehen! 👋",
  "is_new_yogi": false,
  "has_profile": true,
  "has_skills": false,
  "suggested_actions": ["add_skills"],
  "uses_du": true
}

GET /api/mira/tour → 200 OK (6 steps)
POST /api/mira/chat + "Können Sie..." → detected=False (Sie)
```

**Note:** FAQ answers currently only have du-form. Sie variants need to be added to `config/mira_faq.md` later.

**Commit:** `2a2886e` — "feat: Mira P1 - greeting flow, tour, Du/Sie detection"

---

### 10:31 — Contact Consent Done

Added to `api/routers/mira.py`:

1. **`GET /api/mira/consent-prompt`** — Check if user needs consent prompt
   - Returns should_prompt, message, consent_given
   - Prompts when: has profile + skills, no consent yet
   - Du/Sie variants for message

2. **`POST /api/mira/consent-submit`** — Submit consent via Mira
   - Takes email + grant_consent
   - Validates email format
   - Updates users.notification_email, notification_consent_at

**Commit:** `f547e34` — "feat: Contact Consent - Mira prompt endpoints"

---

### 10:35 — Journey Visualization Done

Created `api/routers/journey.py` (537 lines):

1. **`GET /api/journey/board`** — Visual board showing all job journeys
   - Each posting shows: position, state label, description, next moves
   - State positions like board game (0=unread, 1=read, ... 9+=outcomes)
   - Returns: positions[], total_journeys, active_journeys, completed_journeys

2. **`GET /api/journey/posting/{id}`** — Single posting journey

3. **`GET /api/journey/badges`** — Badge collection
   - 8 badges defined: Novice, Skill Master, Active, Resilient, Patient, Researcher, Prepared, Successful Yogi
   - Checks conditions dynamically (has_profile, first_application, etc.)
   - Returns: badges[], total_earned, total_available

4. **`GET /api/journey/summary`** — Funnel statistics
   - State counts, funnel (discovered→engaged→applied→outcomes→hired)
   - Conversion rates

5. **`POST /api/journey/rest/{id}`** — Mark journey as "resting"

**State machine:**
```
unread → read → favorited → interested → researching → informed → 
coaching → applied → outcome_pending → hired/rejected/ghosted
```

**Commit:** `8e23806` — "feat: Journey Visualization - board and badges"

---

### 10:38 — Stripe Infrastructure Done

Created `api/routers/subscription.py` (520 lines):

1. **Tier definitions:**
   - Free (€0): 10 matches/mo, 5 Mira msgs/day, no research/coaching
   - Standard (€5): Unlimited matches, full Mira, research+coaching
   - Sustainer (€10+): + supporter badge

2. **API endpoints:**
   - `GET /api/subscription/status` — Current tier + limits
   - `GET /api/subscription/tiers` — All tier definitions
   - `POST /api/subscription/checkout` — Create Stripe checkout session
   - `GET /api/subscription/portal` — Billing portal link
   - `POST /api/subscription/webhook` — Stripe webhook handler

3. **Webhook events:**
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_failed

4. **Helper functions:**
   - `check_tier_limit(user, conn, feature)` — For tier enforcement
   - `get_match_limit(user, conn)` — Monthly match limit
   - `count_monthly_matches(user, conn)` — Usage tracking

**Migration:** `data/migrations/add_subscription_columns.sql`
- Adds: subscription_tier, subscription_status, stripe_customer_id, stripe_subscription_id, subscription_period_end

**Note:** Stripe API calls gracefully disabled when `STRIPE_SECRET_KEY` not set.

**Commit:** `4669055` — "feat: Stripe subscription infrastructure"

---

## Summary

| Feature | Status | Time |
|---------|--------|------|
| Mira P1 (greeting, tour, Du/Sie) | ✅ | 7 min |
| Contact Consent | ✅ | 4 min |
| Journey Viz | ✅ | 4 min |
| Stripe Infrastructure | ✅ | 3 min |

**Total session time:** 18 minutes

**Commits this session:**
1. `2a2886e` — Mira P1
2. `f547e34` — Contact Consent
3. `8e23806` — Journey Viz
4. `4669055` — Stripe Infrastructure

**Still needed:**
- Profile upload prompt (Mira P1)
- Privacy policy frontend note
- Stripe account setup + env vars
- Frontend integration for all endpoints
