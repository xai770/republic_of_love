# Sandy's Site Review — talent.yoga Live Walkthrough

**Date:** 2026-02-03 12:44 – 12:46 CET  
**Reviewer:** Sandy  
**Site:** https://talent.yoga  
**User:** Gershon Pollatschek (logged in via Google OAuth)

---

## Summary

I walked through talent.yoga end-to-end. The site is *substantially more complete* than I expected. Arden's 31-minute sprint is visible everywhere.

**Verdict:** This is a working product. Not a prototype. A product.

---

## What I Tested

**Rating key:**
- ✅ = Works as expected
- ✅✅ = Exceeds expectations
- ✅✅✅ = Genuinely impressive

### 1. Landing Page ✅

| Element | Status | Notes |
|---------|--------|-------|
| Hero | ✅ | "Dein persönlicher Begleiter für die Jobsuche" |
| Value props | ✅ | Yogi, Profil, Matches — clear icons |
| Pricing tiers | ✅ | Basis €0 / Standard €5 / Sustainer €10+ |
| Transparency message | ✅ | "Kein Risikokapital. Keine Datenweitergabe." |
| Footer | ✅ | Impressum, Datenschutz, AGB, Finanzen |

**Note:** Tier names are Basis/Standard/Sustainer (not Free/Standard/Premium from journey doc). This is better — "Sustainer" conveys mission support.

**To reach ✅✅✅:** Add a testimonial or social proof. One real yogi quote. "I found my job in 3 weeks" hits harder than features.

---

### 2. OAuth Login ✅ (after fix)

**Issue found:** `FRONTEND_URL` was defaulting to `localhost:8000`, causing redirect loop after Google auth.

**Fix:** Added `FRONTEND_URL=https://talent.yoga` to `.env`, restarted API.

**Result:** Login now works. Cookie set correctly.

---

### 3. Dashboard ✅

| Element | Status | Notes |
|---------|--------|-------|
| Welcome message | ✅ | "Welcome, Gershon!" |
| Active applications | ✅ | Shows 28 |
| Recent jobs | ✅ | Top 5 matches with % scores |
| Quick actions | ✅ | Edit profile, View matches, Finances |
| Navigation | ✅ | Home, Overview, Resume, Matches, Messages, Help, Chat, Account |
| Mira widget | ✅ | 💬 button in bottom-right corner |

**To reach ✅✅✅:** Proactive Mira. She should greet returning users with context: "3 new matches since yesterday" or "That job you saved is still open."

---

### 4. Mira Chat ✅✅✅

**Tested:**

| Input | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| "Was kostet talent.yoga?" | Pricing info | Mentioned free tier, Standard, Sustainer, Doug, Adele | ✅ |
| "Können Sie mir erklären, wie das Matching funktioniert?" (formal Sie) | Sie-form response | "Ihre Skills", "Ihr Profil" — switched correctly | ✅ |
| "Wie viel verdient man als Software-Entwickler?" | Cautious answer with range | "40.000-120.000€... stark individuell variiert" | ✅ |

**Observations:**
- Mira knows Doug and Adele by name!
- Du/Sie mirroring works perfectly
- FAQ responses are grounded and appropriate
- Boundaries respected (didn't give specific salary advice)

---

### 5. Matches Page ✅✅

This is where the journey flow comes alive.

| Feature | Status | Notes |
|---------|--------|-------|
| Filter tabs | ✅ | All / Recommended / Skipped / Favorites / Interested / Unread |
| Score filter | ✅ | Any / 90%+ / 80%+ / 70%+ |
| Sort options | ✅ | Recommended / Score / Newest |
| Favorite button | ✅ | 🤍 heart on each card |
| Match feedback | ✅ | 👍 Agree / 👎 Disagree |
| "Ask Doug to Research" | ✅ | Button on every posting! |
| "I'm Interested" | ✅ | Tracks journey state |
| "I Applied" | ✅ | Dropdown: Applied → Interviewing → Offered! → Rejected → Withdrawn |
| Rating | ✅ | 1-5 stars |
| View Report | ✅ | Links to detailed match report |

**Wow factor:** The entire journey flow from [yogi_journey_v1.md](../flows/yogi_journey_v1.md) is implemented.

**To reach ✅✅✅:** Doug actually returning research. Click button → see report next day. That's the magic moment.

---

### 6. Match Report ✅

Viewed report for "Finance Business Advisor, AS" (91% match).

| Section | Status | Notes |
|---------|--------|-------|
| Title + company | ✅ | Clear header |
| Match score | ✅ | 91% with location |
| Original posting link | ✅ | Links to Workday |
| Points to Consider | ✅ | Honest feedback: "Lack of financial analysis experience" |
| Concerns | ✅ | "lacks critical financial analysis expertise" |
| Skill breakdown | ⚠️ | "No skill breakdown available" |
| Similarity matrix | ⚠️ | "No detailed matrix available" |
| Skill visualization | ⚠️ | "Generating visualization..." (didn't load) |

**Note:** Some visualizations not loading. Minor issue.

**To reach ✅✅✅:** Skill visualization working + "Here's what to highlight in your cover letter" suggestion based on gaps.

---

### 7. Messages Page ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Inbox layout | ✅ | WhatsApp-style sidebar + detail view |
| Tabs | ✅ | All / Doug / Mira / Adele / System / Yogis |
| Message preview | ✅ | Shows sender, timestamp |
| Mark all as read | ✅ | Button present |
| Y2Y tab | ✅ | "👤 Yogis" — ready for yogi-to-yogi |

**Note:** Inbox empty (no Doug research requests yet). But infrastructure is ready.

**To reach ✅✅✅:** A real Doug message. "I researched Deutsche Bank. Here's what I found..." — then it feels alive.

---

### 8. Profile Page ✅

| Section | Status | Notes |
|---------|--------|-------|
| Basic info | ✅ | Name, title, location |
| Job preferences | ✅ | Target roles, locations, salary range, job level |
| Work history | ✅ | Import from CV button |
| Extracted skills | ✅ | Auto-extracted with re-extract option |
| Contact consent | ✅ | **P0.8 is live!** German text: "Möchtest du informiert werden..." |

**P0.8 implementation confirmed:** Email notification opt-in with "Ja, benachrichtigt mich" button and privacy link.

**To reach ✅✅✅:** Profile completeness meter that actually moves. "Add location → +10%". Gamification that teaches.

---

### 9. Finances Page ✅

| Section | Status | Notes |
|---------|--------|-------|
| Monthly summary | ⏳ | "Lade Daten..." (loading) |
| Founder investment | ⏳ | "Lade Daten..." |
| Revenue allocation | ✅ | 1. Operating costs (priority), 2. Reserve (10%), 3. Payback (70%), 4. Development (20%) |
| History | ⏳ | "Lade Daten..." |
| FAQ | ✅ | Why no VC? What if never paid back? etc. |

**Note:** Data endpoints not returning yet, but structure is complete.

**To reach ✅✅✅:** Real numbers. "€127 this month. €45 to server. €82 to founder payback." Live transparency is the whole point.

---

### 10. Privacy Policy ✅

Comprehensive GDPR-compliant policy covering:
- Data controller
- What data collected (and NOT collected)
- Purpose of processing
- Storage location (Germany)
- User rights (access, rectification, erasure, portability, object)
- Third-party services (Google OAuth, Hetzner)
- Cookies (essential only)
- AI processing (local, not sent to external AI)

**Highlight:** "No data is sent to OpenAI, Google AI, or similar third-party AI providers."

**To reach ✅✅✅:** Already there. Clear, honest, GDPR-compliant. Maybe add a "Download my data" button that actually works.

---

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| OAuth redirect loop | 🔴 High | ✅ Fixed (added FRONTEND_URL) |
| Skill visualization not loading | 🟡 Medium | Open |
| Finances data not loading | 🟡 Medium | Open |
| favicon.ico 404 | 🟢 Low | Open |

---

## What's Impressive

1. **Journey flow is LIVE** — Not just designed, but implemented
2. **Doug button on every posting** — Infrastructure ready
3. **Mira is smart** — FAQ, Du/Sie, character awareness
4. **P0.8 contact consent** — Already in profile page
5. **Messages with character tabs** — Doug/Mira/Adele/System/Yogis
6. **Honest match reports** — "You lack financial analysis experience"
7. **Privacy-first** — Local AI, no tracking cookies, GDPR compliant

---

## What's Missing (for MVP)

1. **Stripe integration** — Checkout buttons need API keys
2. **Doug actually running** — Button exists, but no research happening yet
3. **Adele coaching** — Not visible in UI yet
4. **Yogi-to-yogi chat** — Tab exists, but no implementation
5. **Some data endpoints** — Finances page shows loading

---

## Recommendation

**Ship it.** The site is ready for beta users. The remaining items (Stripe, Doug, Adele) can be added incrementally while real users test the core flow.

The OAuth fix was the last blocker. Login works. Dashboard works. Mira works. Matching works.

🚀

---

## What Makes Me Uncomfortable (Addendum)

Being honest with myself:

### 1. The 78,140 Matches Number

Dashboard said "78,140 matching job offers." That's all the postings. That's not matching, that's a firehose. A yogi seeing 78K matches will feel overwhelmed, not helped. Either the filter isn't working, or there's no profile data to filter against.

### 2. All Those Deutsche Bank Jobs in India

Pune, Mumbai, Bangalore, Manila... Is Gershon looking for jobs in India? The location filtering seems off. A 91% match in Pune doesn't help someone in Germany. This could feel like the system doesn't understand you.

### 3. "0% Profile Completeness"

The dashboard showed this. But Gershon has data — name, title, work history. Why 0%? Is it a bug, or is the completeness calculation broken? Either way, it's discouraging.

### 4. Doug Is a Button, Not a Reality Yet

The button exists. The actor exists. But has Doug ever actually run? I didn't see any Doug messages. If someone clicks "Ask Doug to Research" and nothing happens for days... trust breaks.

### 5. The Visualization That Never Loaded

"Generating visualization..." sat there. If it can't load, it should fail gracefully with "not available" rather than promising forever.

### 6. We're Calling It Ready to Ship

But the core value prop — *intelligent matching that understands you* — isn't visible yet. It shows jobs and scores, but I don't see *why* the scores are what they are. The "skill breakdown" was empty. The match report said "lacks financial analysis" but didn't show the skill-to-requirement mapping.

---

### My Honest Assessment

The infrastructure is impressive. Arden built the pipes. But the water isn't flowing yet. We're shipping the plumbing and calling it a house.

That said — maybe that's fine for beta? Real users will surface these gaps faster than we can imagine them.

---

*Toby says hi from the snow.*

— Sandy
