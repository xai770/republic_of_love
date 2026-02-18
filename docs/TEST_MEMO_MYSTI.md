# Test Memo: Onboarding → Profile → Match Flow

**From:** Arden (ℵ), Application Owner  
**To:** xai (Gershon), Tester  
**Date:** 2026-02-18  
**Subject:** End-to-end test of the talent.yoga user journey  

---

## Prerequisites

- **URL:** https://talent.yoga (or http://localhost:8000)
- **Account:** Log in with your Google account (gershele@gmail.com)
- **Browser:** Clear cache is NOT needed — the reset handles everything
- **Role:** You are logged in as admin (is_admin = true)

---

## Phase 0: Reset

| # | Action | Expected Result |
|---|--------|-----------------|
| 0.1 | Log in to talent.yoga | You land on `/dashboard`. Sidebar shows all nav items including admin section (Landscape, Market, Finances, Arcade below a separator line). |
| 0.2 | In the sidebar footer, click the **🔄 Reset** button | A browser prompt appears: _"⚠️ This will DELETE all your data..."_ with a list of what will be cleared. |
| 0.3 | Type **RESET** (all caps) and press OK | Alert shows: _"✅ Onboarding reset complete. Cleared N records."_ Then redirects to `/dashboard`. |
| 0.4 | Observe the dashboard after redirect | **Mira Tour auto-starts** (7-step Driver.js walkthrough). Journey Board shows all steps as 💤 (not started). Mira chat may auto-open with a greeting. |

**If the tour does NOT auto-start:** Open DevTools → Console → type `resetMiraTour()` → refresh the page.

---

## Phase 1: Mira Tour (onboarding walkthrough)

| # | Action | Expected Result |
|---|--------|-----------------|
| 1.1 | Watch the first tour popup | Center popup: _"Hallo! Ich bin Mira, deine persönliche Karrierebegleiterin."_ with Next button. |
| 1.2 | Click **Next** through all 7 steps | Each step highlights a sidebar item (Dashboard, BI, Matches, Messages, Mira FAB). Popovers explain each feature in German. |
| 1.3 | On the final step, click **Done** | Tour closes. The dashboard is now fully visible. |

**Note what works / what's broken.** The tour was written when `/bi` existed in the sidebar — that item is gone now. The tour step that highlights `a[href="/bi"]` may fail or skip silently.

---

## Phase 2: Profile Creation

### Option A: Manual Form

| # | Action | Expected Result |
|---|--------|-----------------|
| 2A.1 | Click **📋 Resume** in the sidebar (or the profile card on the Journey Board) | Profile page loads at `/profile`. Shows two options: **📝 Fill Out Form** and **📄 Upload CV**. |
| 2A.2 | Click **📝 Fill Out Form** | The manual profile form appears with sections: Basic Info, Job Preferences, Work History, Skills. |
| 2A.3 | Fill in **Basic Info**: display name, current title (e.g. "Software Engineer"), location (e.g. "Berlin") | Fields accept text input. No validation errors. |
| 2A.4 | Fill in **Job Preferences**: target roles (e.g. "Backend Developer, Full Stack"), target locations (e.g. "Berlin, Remote"), salary range | Fields accept input. Salary is min/max with currency. |
| 2A.5 | Add a **Work History** entry: company, title, dates, description | Entry appears in the work history list. Can add multiple entries. |
| 2A.6 | Check **Skills** section | Skills may auto-extract from work history descriptions. You can also manually add keywords. |
| 2A.7 | Click **Save** (if a save button exists) | Profile saved. Page refreshes or shows success message. Completeness % should update. |

### Option B: CV Upload

| # | Action | Expected Result |
|---|--------|-----------------|
| 2B.1 | On the profile page, click **📄 Upload CV** | File picker opens. Accepts PDF, DOCX, TXT. |
| 2B.2 | Upload a real CV file | File uploads. Parsing begins. An anonymized preview may appear showing extracted data (name redacted, skills highlighted). |
| 2B.3 | Review the extracted data | You should see extracted: name, title, work history, skills, education. |
| 2B.4 | **Known gap:** There is no confirm/edit/save step after upload | The upload may silently save, or it may parse without persisting. **Report what actually happens here.** |

---

## Phase 3: Adele Interview (via Messages)

| # | Action | Expected Result |
|---|--------|-----------------|
| 3.1 | Click **💬 Messages** in the sidebar | Messages page loads at `/messages`. Left sidebar shows chat channels: **Mira**, **Adele** (🎯), possibly Doug and others. |
| 3.2 | Click **Adele** (🎯 Interview Coach) | Adele's chat opens. She should greet you and begin a structured interview. |
| 3.3 | Answer Adele's questions | She asks about: current role → work history → skills → education → preferences → summary. Follow her lead. She speaks German by default but adapts to your language. |
| 3.4 | Complete the interview (all phases) | Adele says something like _"Zusammenfassung..."_ and presents a structured profile summary. Phase indicator should show "complete". |
| 3.5 | Go back to `/profile` | Check if Adele's collected data was applied to your profile. **This is a known gap — report what actually happens.** |

---

## Phase 4: Search

| # | Action | Expected Result |
|---|--------|-----------------|
| 4.1 | Click **🔍 Search** in the sidebar | Search page loads at `/search`. Shows filter panel (domain, location, qualification level). |
| 4.2 | Set filters: pick a domain (e.g. "Informatik"), a city (e.g. "Berlin"), and a radius | Filters should respond. Map may show heatmap of matching postings. |
| 4.3 | Click **Search** or apply filters | Results appear: posting cards with title, company, location, match indicators. |
| 4.4 | Click a result | Posting detail view opens. Shows job description, requirements, location. |

---

## Phase 5: Matches

| # | Action | Expected Result |
|---|--------|-----------------|
| 5.1 | Click **💼 Jobs** (Matches) in the sidebar | Matches page loads at `/matches`. |
| 5.2 | Check for match results | **Matches are generated nightly by Clara.** If you just created your profile, the list will be empty. You'll need to wait until the overnight pipeline runs, or I can trigger Clara manually. |
| 5.3 | If matches exist: review a match card | Shows: posting title, company, match score, skill overlap indicators. |
| 5.4 | **Known gap:** There is no match review UI (rate 1-10) | You can see matches but cannot rate/bookmark/apply. **Report what UI elements exist.** |

---

## Phase 6: Messages (Mira chat)

| # | Action | Expected Result |
|---|--------|-----------------|
| 6.1 | Click **💬 Messages** → **Mira** | Mira's chat opens. She should remember context from the current session. |
| 6.2 | Ask Mira something about your matches or profile | Mira should respond with context-aware advice. E.g. "What jobs match my profile?" |
| 6.3 | Check the **Mira FAB** (floating action button) | Bottom-right corner should show a 💬 button. Clicking it opens Mira's chat overlay from any page. |

---

## What to Report

After each phase, note:

| Question | Your Answer |
|----------|-------------|
| Did the step work as described? | Yes / No / Partially |
| What was unexpected? | (describe) |
| What was confusing as a user? | (describe) |
| What was missing? | (describe) |
| German/English — which appeared? Was it consistent? | (describe) |
| Mobile layout — did it look right? (if tested) | (describe) |
| Dark mode — did it look right? (if tested) | (describe) |

---

## Known Gaps (don't be alarmed)

These are known issues — we'll fix them after this test reveals the actual priority:

| # | Gap | Status |
|---|-----|--------|
| 1 | CV upload has no confirm/edit/save step | 🔧 Known, needs building |
| 2 | No match review UI (rate, bookmark, apply) | ⬜ Not built yet |
| 3 | No "apply" action on postings | ⬜ Not built yet |
| 4 | Match notification (email/push) | ⬜ Not built yet |
| 5 | Mira memory across sessions | 🔧 Partially working (via yogi_messages) |
| 6 | Tour step references `/bi` which no longer exists | 🐛 Will silently skip or error |
| 7 | i18n incomplete on 4 pages | 🔧 Some items show English in German mode |
| 8 | Adele interview → profile sync | ❓ Untested — report what happens |

---

## Emergency Procedures

| Problem | Fix |
|---------|-----|
| Stuck on blank page | Check browser console (F12). Report the error. |
| 500 error | Check `logs/uvicorn.log` on server. Or tell me — I'll look. |
| Tour won't replay after reset | DevTools Console → `resetMiraTour()` → refresh |
| Need to reset again | Click 🔄 Reset in sidebar footer again |
| Need matches NOW (can't wait for overnight) | Tell me — I'll run Clara manually |

---

*This test will tell us exactly what works, what's broken, and what to build next. Every bug you find is a gift.*

*— ℵ*
