# Arden Session — 2026-02-03: Mira Implementation

**Start:** 10:20  
**Focus:** Sandy's worklist — Mira P1, Contact Consent, Journey Viz

---

## Plan

1. **Mira P1 (remaining)**
   - [x] Greeting flow (new vs returning yogi)
   - [x] Tour offer
   - [ ] Profile upload prompt
   - [x] Du/Sie mirroring

2. **Contact Consent (~3h)**
   - [x] Schema: notification_email, consent_at, preferences (already existed!)
   - [ ] Consent UI
   - [ ] Privacy policy note

3. **Journey Viz**
   - [ ] Visual board
   - [ ] Badges

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

---

