# Arden Worklist — Site Polish Sprint

**Date:** 2026-02-03  
**From:** Sandy  
**Status:** 🟡 Active  
**Context:** Post-launch review by Sandy and Gershon. Infrastructure is solid. Now we iterate on UX and fix broken things.

---

## How This Works

1. Pick a ticket
2. Mark it `🔄 In Progress`
3. Do the work
4. Mark it `✅ Done` with commit hash
5. Pick next ticket

Priority order is a suggestion. Use your judgment. If something unblocks other work, do it first.

---

## 🔴 Priority 1: Broken Things

### T001: Mira Language Switch
**Status:** ✅ Done (2026-02-03, commit ff65af8)  
**Effort:** Medium  
**Problem:** User asked "can we switch to English?" and Mira responded in German with nonsense.  
**Root cause:** Pattern matching FAQ can't handle this. Need real LLM.  
**Fix:** 
- Detect language switch requests ("English please", "auf Deutsch", etc.)
- Switch Mira's response language accordingly
- Store language preference in session
**Acceptance:** User says "English please" → Mira responds in English from then on.
**Solution:** Implemented LLM-first Mira with language detection in system prompt.

---

### T002: Mira Nonsense Responses  
**Status:** ✅ Done (2026-02-03, commit ff65af8)  
**Effort:** Medium  
**Problem:** When FAQ doesn't match, Mira generates word salad. Example: "Ich verstehe, dass Sie in einer Situation sind, wo Sie sich auf eine Lösung freuen müssen..."  
**Root cause:** Fallback to weak model without proper prompting.  
**Fix:**
- Use llama3.2 (or qwen2.5:7b) as Mira's brain
- System prompt: Mira's personality + FAQ corpus + "if you don't know, say so"
- Temperature 0.3 for consistency
**Acceptance:** Mira gives coherent, on-brand responses even for unexpected questions. When she doesn't know, she says "Das weiß ich nicht, aber ich kann nachfragen."
**Ref:** [sage_20260201_mira_voice_guide_for_arden.md](sage_20260201_mira_voice_guide_for_arden.md)
**Solution:** qwen2.5:7b with few-shot examples, "companion not chatbot" framing per Sage's guide.

---

### T003: Sidebar Collapse Broken
**Status:** 🟡 Open  
**Effort:** Low-Medium  
**Problem:** Sidebar should show icons only, expand on hover. Currently stuck open. Clicking the blue half-circle hides content behind sidebar.  
**Fix Options:**
1. Fix the CSS animation/hover behavior
2. Fallback: non-collapsing sidebar with tooltips on icons
**Acceptance:** Either hover-expand works smoothly, OR we have a clean static sidebar with tooltips.

---

## 🟡 Priority 2: Wrong UX

### T004: Home Page Redesign — No Postings
**Status:** 🟡 Open  
**Effort:** Medium  
**Problem:** Current dashboard shows job postings immediately. This is hostile to burned-out job seekers. "Home is the locker room, not the arena."  
**New Design:**
1. **Mira greeting** — Front and center. "Welcome back, [name]! Here's what's happened..."
2. **Messages summary** — "You have 5 new messages" (clickable)
3. **Matches summary** — "382 matches, 7 reviewed, 2 interested" (clickable, NOT a list of jobs)
4. **Your progress** — Journey visualization (can be placeholder for now)
5. **Suggested next steps** — Auto-generated: review NEW postings (12), confirm skills, book Adele, etc.
6. **Sentence of the day** — Footer, grey, easter egg. Rotating quotes.

**Do NOT show:** Job posting cards, match percentages, "Recent Job Postings" section.  
**Acceptance:** Yogi lands on Home and feels welcomed, not overwhelmed. Postings are one click away, not in their face.

---

### T005: Landing Page — Germany Flag + Language
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** 
- No indication this is Germany-focused
- No way to switch DE ↔ EN
**Fix:**
- Add German flag icon or "🇩🇪 Fokus: Deutschland" badge
- Add DE/EN toggle in header (like dashboard has)
**Acceptance:** First-time visitor knows this is for German job market. Can switch language.

---

### T006: Landing Page — Text Fix
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** "...bis zur Bewerbung" should be "...bis zum Bewerbungsgespräch" (we offer interview coaching)  
**File:** Probably in frontend templates  
**Acceptance:** Text updated.

---

### T007: Login Page — Logo + Language
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** 
- Uses emoji 🎯 instead of actual logo
- Page is in English while landing was German
**Fix:**
- Use `frontend/static/images/icons/logo.png`
- Match language to user's selection (or browser default)
**Acceptance:** Login page has real logo. Language consistent with landing page.

---

## 🟢 Priority 3: Tech Debt / Architecture

### T008: Text Blurbs — Editable Storage
**Status:** 🟡 Open  
**Effort:** Medium  
**Problem:** All UI text is hardcoded in templates. Legal will need to review and change these. Multiple times.  
**Options:**
1. **MD files** in `content/` folder — Simple, git-tracked, easy to edit
2. **OWL storage** — Same place as other config, queryable
**Decision needed:** Which approach? (Sandy leans toward MD files for simplicity)
**Acceptance:** Marketing/legal text lives in one editable place. Template pulls from there.

---

### T009: User Privileges via OWL
**Status:** 🟡 Open  
**Effort:** Medium  
**Problem:** User tiers (Free/Standard/Sustainer) and feature access should be in OWL, not hardcoded.  
**Why OWL:**
- Already have People → Team/Yogis/B2B hierarchy
- Can store user config and interaction logs
- Single source of truth
**Acceptance:** Sidebar items, feature gates, and tier info come from OWL lookup.

---

### T010: Profile Completeness — Fix 0%
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** Dashboard shows "0% profile completeness" even when user has name, title, work history.  
**Root cause:** Calculation logic missing or broken.  
**Fix:** Implement actual completeness calculation:
- Name: +10%
- Title: +10%
- Location: +10%
- Work history (1+ entries): +30%
- Skills extracted: +20%
- Job preferences set: +20%
**Acceptance:** Percentage reflects actual profile state. Changes when user adds data.

---

### T011: Match Count — Fix 78K Firehose
**Status:** 🟡 Open  
**Effort:** Medium  
**Problem:** Dashboard shows "78,140 matching job offers" — that's ALL postings, not matches.  
**Root cause:** No filtering by user preferences, location, or minimum match score.  
**Fix:**
- Only count postings that pass user's preferences (location, level, etc.)
- Only count postings above minimum match threshold (e.g., 50%?)
- If no preferences set, show "Set your preferences to see matches"
**Acceptance:** Match count is meaningful, not terrifying.

---

### T012: Location Filtering — India Problem
**Status:** 🟡 Open  
**Effort:** Medium  
**Problem:** User in Germany sees 91% match for job in Pune, India. Location not factored into matching or filtering.  
**Fix:**
- User preferences include target locations
- Matches outside target locations deprioritized or filtered
- Match report shows location compatibility
**Acceptance:** German user primarily sees German jobs (or remote). Non-matching locations are flagged.

---

## 🔵 Priority 4: Polish

### T013: Skill Visualization — Fix Loading Forever
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** Match report shows "Generating visualization..." but never loads.  
**Fix:** Either make it work or show "Visualization not available" gracefully.  
**Acceptance:** No infinite loading states.

---

### T014: Finances Page — Data Loading
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** Shows "Lade Daten..." but data never loads.  
**Fix:** Connect to actual data source or show placeholder data.  
**Acceptance:** Page shows real numbers or honest "Coming soon."

---

### T015: Favicon 404
**Status:** 🟡 Open  
**Effort:** Low  
**Problem:** Browser console shows favicon.ico 404.  
**Fix:** Add favicon to static files.  
**Acceptance:** No 404 in console.

---

## Parking Lot (Not Yet Specified)

- ~~**Doug web research** — Button exists, actor exists, but not wired up~~ ✅ Done (2026-02-03, commits 3209d5a, 833d2c4) — Mira detects company research requests and fires Doug async
- **Adele coaching flow** — UI not built
- **Yogi-to-yogi chat** — Tab exists, no implementation
- **Stripe integration** — Needs API keys first
- **Journey progress visualization** — Needs design

---

## Reference Docs

- [sandy_20260203_site_review.md](sandy_20260203_site_review.md) — Sandy's walkthrough
- [xai_20260203_site_review.md](xai_20260203_site_review.md) — Gershon's review (the real one)
- [yogi_journey_v1.md](../flows/yogi_journey_v1.md) — Journey flow spec
- [sage_20260201_mira_voice_guide_for_arden.md](sage_20260201_mira_voice_guide_for_arden.md) — Mira's personality

---

*Pick a ticket. Ship it. Repeat.*

— Sandy
