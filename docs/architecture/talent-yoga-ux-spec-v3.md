# talent.yoga — Mira UX Overhaul Specification v3

**Document:** `nate_mira_ux_spec_v3`
**Author:** Computer-Nate (Perplexity) + Gershon, reviewed by Arden
**Date:** 2026-03-25 (Section 0, 6, 8a, 23–25 added 2026-03-29 by Arden; Nate review applied 2026-03-29; Section 14, 21, 23, 24 updated 2026-03-30 by Arden)
**Status:** Approved for implementation — Phases 1–3
**Supersedes:** v2 (same date, pre-review draft)
**Company:** Turing Tango UG (haftungsbeschränkt), Berlin

---

## Table of Contents

0. [Yogi Journey Map](#0-yogi-journey-map)
1. [Executive Summary](#1-executive-summary)
2. [Design Principles](#2-design-principles)
3. [Mira — Character & Visual Identity](#3-mira--character--visual-identity)
4. [Guidance Escalation Ladder](#4-guidance-escalation-ladder)
5. [Illustration Asset Inventory](#5-illustration-asset-inventory)
6. [Onboarding Flow](#6-onboarding-flow)
7. [Profile Page](#7-profile-page)
8. [Search/Start](#8-searchstart)
8a. [Search Data Flow — Focus, Field, Plan](#8a-search-data-flow--focus-field-plan)
9. [Search/Field (Berufsfeld)](#9-searchfield-berufsfeld)
10. [Search/Qualification (Qualifikation)](#10-searchqualification-qualifikation)
11. [Search/Location (Standort)](#11-searchlocation-standort)
12. [Search/Postings (Stellen)](#12-searchpostings-stellen)
13. [Search/Power Search](#13-searchpower-search)
14. [Overview Page (formerly Home/Start)](#14-overview-page-formerly-homestart)
15. [Messages](#15-messages)
16. [Account/Settings](#16-accountsettings)
17. [Posting Status Engine](#17-posting-status-engine)
18. [Mira Chat Widget Specification](#18-mira-chat-widget-specification)
19. [Mira Tour Overlay Specification](#19-mira-tour-overlay-specification)
20. [i18n Requirements](#20-i18n-requirements)
21. [Implementation Priority](#21-implementation-priority)
22. [Decision Log](#22-decision-log-resolved-2026-03-26)
23. [Tier Model](#23-tier-model)
24. [Mira Content Inventory](#24-mira-content-inventory)
25. [Open Questions for Nate](#25-open-questions-for-nate)

---

## 0. Yogi Journey Map

The complete end-to-end flow a yogi experiences, from first visit to job outcome.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        YOGI JOURNEY — END TO END                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ARRIVE                                                              │
│     Anonymous visitor lands on talent.yoga                              │
│     └─→ Landing page (public, no auth required)                        │
│                                                                         │
│  2. ONBOARD                                                             │
│     Google Sign-in → 12 steps (EN) or 13 steps (DE, +Du/Sie)           │
│     Key moments: language, auth, data consent, yogi name, CV upload    │
│     └─→ Redirect to /search                                           │
│                                                                         │
│  3. ORIENT (Search/Start — flip cards)                                  │
│     Three self-assessment questions:                                    │
│     • Focus — how narrow or broad is this search?                      │
│     • Field — stay in my field or explore others?                      │
│     • Plan — actively searching, exploring, or preparing?             │
│     These shape Mira's coaching behavior and result ranking.           │
│     └─→ Search/Field                                                   │
│                                                                         │
│  4. DEFINE SCOPE                                                        │
│     Search/Field → sort profession fields by interest (Kanban)         │
│     Search/Qualification → pick experience levels (4 cards)            │
│     Search/Location → pin locations on map + radius                    │
│     └─→ Search/Postings                                                │
│                                                                         │
│  5. BROWSE & DECIDE (Search/Postings)                                   │
│     View matched postings. For each posting:                           │
│     viewed → saved / dismissed / apply_intent → applied → outcome     │
│     Session framework: time-budgeted browsing with Mira coaching       │
│     └─→ Overview (home base) or keep browsing                         │
│                                                                         │
│  6. TRACK (Overview page)                                               │
│     Journey flowchart — see where you are                              │
│     Yogi-Meter — activity statistics                                   │
│     Activity Log — Bewerbungsprotokoll (BA compliance)                 │
│                                                                         │
│  7. APPLY & FOLLOW UP                                                   │
│     Cover letter generation (Clara) → Submit application               │
│     Track outcomes: response, interview, offer, rejection              │
│     Activity log auto-fills for Agentur für Arbeit compliance          │
│                                                                         │
│  8. STAY CONNECTED                                                      │
│     Even after finding a job, yogis can stay on the free tier.         │
│     When they need a new job — upgrade, and the pipeline is ready.     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key principles in the journey

- **No gates:** A yogi can skip profile/CV setup and go straight to browsing. Match scores are disabled; results sort by recency. A reminder appears, but nothing blocks.
- **Mira is the thread:** From onboarding through search to applications, Mira is the single guide. She adapts her coaching to the yogi's Plan setting.
- **Everything serves the Bewerbungsprotokoll:** Every posted application is automatically logged in the format the Agentur für Arbeit expects. The yogi never has to maintain a separate spreadsheet.
- **The yogi decides the pace:** Session framework is advisory. No lockouts, no pressure.

---

## 1. Executive Summary

We introduce Mira as a unified AI guide across every screen. Mira bridges the gap between scripted tutorials (guided tours), AI chat, and page-specific FAQs. She provides visual continuity through a consistent illustrated character, contextual guidance through tour overlays, and always-available help through a persistent chat widget.

### Key changes 

- Onboarding: 12 steps (EN) / 13 steps (DE, +Du/Sie), plus Google Sign-in auth. Includes Mira introduction screen added in UX v3.
- Auth step documented: Google OAuth between language selection and step 2
- Adele persona removed from profile page — Mira is the sole user-facing guide
- Every screen gets a Mira tour, a Mira avatar widget, and (where applicable) a player widget
- `/home` renamed to `/overview` ("Overview" in EN, "Überblick" in DE)
- New posting status engine with 8 event types
- 20 total Mira illustrations (7 onboarding + 4 pointing + 8 screen-specific + 1 glasses variant)

---

## 2. Design Principles

### Mira never interrupts
Mira only appears automatically if the user has not interacted with any control on the current page. Once the user clicks anything, Mira stays silent. The user can always manually invoke Mira via her avatar.

### Graceful degradation
Users who skip profile/CV setup can still use all search features. Match scores are disabled; results sort by recency instead of relevance. A non-intrusive reminder appears on the Postings tab.

### No manipulative patterns
No dark patterns, no guilt-tripping for skipped steps. The "Decline" button was removed from the Mira intro screen — users proceed or go back, never get locked out.

### Consent-forward
The Mira intro screen explains what Mira is (AI + human fallback) before the user continues. The "don't auto-show" checkbox is always available in the Mira chat panel.

### Player widgets are separate from Mira
Player widgets (blue/white, bottom-center) handle screen-specific step navigation. Mira's avatar (lower-right corner) handles chat, FAQ, and guided tours. These are distinct UI systems that communicate but never merge.

---

## 3. Mira — Character & Visual Identity

### Description

Mira is a semi-stylized digital character designed as a calm, trustworthy AI career guide for talent.yoga.

### Visual prompt (locked)

**Fixed elements (never change):**
- Same face, young adult appearance
- Short, slightly tousled dark brown hair
- Simple teal hoodie
- Natural eyes with faint violet iridescent iris ring
- Calm, kind expression
- Clean white/transparent background, modern anime-inspired digital illustration style

**Variable elements:**
- Hand/arm gestures, gaze direction, pose angle
- Pointing direction (left, right, up, down)
- Props (clipboard, star, gear, cards, etc.)
- Slight expression shifts (attentive, encouraging, thoughtful)

### Illustration generation guidelines

From nate@chatgpt — all new Mira illustrations must follow these rules:

- Start prompts with: "Create a new illustration of Mira, keeping her face, age, hairstyle, hoodie, and overall visual style consistent with the approved Mira images. Clean modern digital illustration, soft shading, adult proportions, transparent background, no border glow, no blur fade."
- Be explicit about: pointing direction, body crop (bust-up or half-body), gaze direction, empty space for UI overlay
- Do not let Mira become childlike or chibi-proportioned
- Avoid dramatic fashion, extra accessories, fantasy elements, photorealism, or random backgrounds
- **Profile interview mode:** When Mira conducts the profile interview (using the Adele system prompt), swap to a glasses variant illustration to signal the shift in mode. Same character, different role.

### Avatar

`mira_avatar.png` — circular crop, confetti detail, bust-up portrait. Used as the persistent clickable avatar in the lower-right corner of every page. Also used in the Mira chat widget header.

### Mira intro screen copy

**English:**

> Hi, I'm Mira — your career guide. Made with real humans.
>
> I'm here to make your job search as easy as possible. Need help? Click my avatar anytime — I'll show you what to do, or you can just ask me.
>
> Let's get you set up.

Buttons: **Back** | **Next**

**Deutsch (Du):**

> Hi, ich bin Mira — deine Karrierebegleiterin. Mit echten Menschen gemacht.
>
> Ich bin hier, um deine Jobsuche so einfach wie möglich zu machen. Brauchst du Hilfe? Klick einfach auf mein Avatar — ich zeig dir, was zu tun ist, oder du fragst mich einfach.
>
> Lass uns loslegen.

Buttons: **Zurück** | **Weiter**

**Deutsch (Sie):**

> Hallo, ich bin Mira — Ihre Karrierebegleiterin. Mit echten Menschen gemacht.
>
> Ich bin hier, um Ihre Jobsuche so einfach wie möglich zu gestalten. Brauchen Sie Hilfe? Klicken Sie einfach auf mein Avatar — ich zeige Ihnen, was zu tun ist, oder Sie fragen mich direkt.
>
> Lassen Sie uns beginnen.

Buttons: **Zurück** | **Weiter**

---

## 4. Guidance Escalation Ladder

Every page uses a single escalation sequence — not three independent systems. Only two elements are always visible: the player widget and Mira's avatar. Everything else is triggered by user inactivity or explicit request.

### What's always on screen

**Player widget** — Blue and white, bottom-center. Handles screen-specific step navigation (dots, progress, back/next). Clicking the play/next button walks the user through the cards or controls on that screen in sequence.

| Screen               | Player Widget                | Description                                                                                                                                                                                              |
| -------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search/Start         | 5-dot player bar             | Situation → Direction → Level → Location → Opportunities                                                                                                                                                 |
| Search/Field         | Kanban guided mode           | Card sorting walkthrough                                                                                                                                                                                 |
| Search/Qualification | None                         | Simple card selection, no steps needed                                                                                                                                                                   |
| Search/Location      | None                         | Direct map/sidebar interaction                                                                                                                                                                           |
| Search/Postings      | 5-dot player bar (read-only) + session timer | Shows completed search steps as filter summary. **Guided walkthrough** on first visit (Mira walks through one posting). **Session framework** on return visits (time budget + progress bar). |
| Search/Power         | None                         | Advanced mode, no guidance                                                                                                                                                                               |
| Profile              | 3-dot player bar             | Provide → Discover → Done                                                                                                                                                                                |
| Overview             | Flowchart IS the player      | Next-step highlight in the journey flowchart                                                                                                                                                             |
| Messages             | None                         | No multi-step workflow                                                                                                                                                                                   |
| Account              | None                         | No multi-step workflow                                                                                                                                                                                   |

**Mira avatar** — `mira_avatar.png`, 48px circular, lower-right corner. Replaces the current chat icon. Visible whenever Mira's guided tour is NOT active. Opens the chat panel (see Section 18) which includes FAQ pills and a "Guided tour" link. **During a guided tour, the avatar is hidden** — the full Mira illustration replaces it.

**Mira's illustration is NOT on screen** unless she is actively giving a guided tour.
### Escalation sequence (first visit to any screen)

```
t=0s   User lands on screen.
       Player widget visible (bottom-center).
       Mira avatar visible (lower-right, small).
       Mira illustration NOT visible.

t=10s  No interaction detected.
       → Player widget dances: flash, vibrate, grow-and-shrink.
         Purpose: draw attention to the guided mode button.

t=20s  Still no interaction.
       → Mira guided tour auto-starts.
         Avatar hides. Full illustration appears with speech bubble
         + 40% overlay + teal border glow on the target control.
         First speech bubble includes: "Click anywhere to stop this tour."
         Tour walks through each control with Next/Back/End buttons.
         Clicking anywhere outside the speech bubble/buttons ends the tour.

ANY    User activates ANY control at any point.
       → Escalation stops immediately.
       → Mira stays in her avatar corner.
       → Player widget returns to normal appearance.
```

### "Mira never interrupts" — clarification

If the user has activated any control on the current screen, the escalation ladder does not fire. Mira only auto-appears when the user is idle — she is filling silence, not interrupting action.

### Manual access (always available)

- Click Mira avatar → chat panel opens
- Chat panel includes FAQ pills specific to the current screen
- First pill is always **"Guided tour"** — starts Mira's tour on demand, regardless of the auto-tour setting
- **"Don't auto-show"** checkbox in chat panel settings → stored in `localStorage` key `mira_auto_tour_disabled` → disables the t=20s auto-trigger, but NOT the manual "Guided tour" button

### Tour dismissal

Mira's first speech bubble in every guided tour includes a dismissal hint:
- **EN:** "Click anywhere to stop this tour."
- **DE (Du):** "Klick irgendwo, um die Tour zu beenden."
- **DE (Sie):** "Klicken Sie irgendwo, um die Tour zu beenden."

Clicking anywhere outside the speech bubble or its navigation buttons (Next/Back/End) immediately ends the tour. The avatar reappears. The overlay fades out.

---

## 5. Illustration Asset Inventory

### Onboarding illustrations

| File | Description | Screen |
|---|---|---|
| `mira_waive.png` | Mira waving at the user | Mira intro screen (NEW step 3 EN / step 4 DE) |
| `mira_t_and_cs.png` | Mira holding Terms & Conditions document | Step 4 EN / Step 5 DE |
| `mira_manifesto.png` | Mira pointing at flip chart with diagrams | Step 5 EN / Step 6 DE |
| `mira_crystal_ball.png` | Mira holding crystal ball | Step 6 EN / Step 7 DE |
| `mira_cv.png` | Mira with filing cabinet, CV visible | Step 9 EN / Step 10 DE |
| `mira_email.png` | Mira pointing at mailbox with @ symbol | Step 11 EN / Step 12 DE |
| `mira_paper_snake.png` | Mira celebrating, thumbs up, party blower | Step 12 EN / Step 13 DE (celebration) |

### Pointing illustrations (guided tours)

| File | Usage |
|---|---|
| `mira_pointing_up.png` | Point to element in upper area of screen |
| `mira_pointing_center.png` | Point to element in center of screen |
| `mira_pointing_left.png` | Point to element in left area of screen |
| `mira_pointing_center_bottom.png` | Point to element in center-bottom area |

### Screen-specific illustrations (NEW)

| File | Screen | Description |
|---|---|---|
| `mira_clipboard.png` | Profile | Mira holding clipboard with teal checkmarks, pen in hand |
| `mira_pointing_down.png` | Search/Start | Mira pointing downward (toward player bar), open-palm gesture |
| `mira_sorting_cards.png` | Search/Field | Mira holding two plain cards, weighing a decision |
| `mira_star_badge.png` | Search/Qualification | Mira holding up gold star, pointing at it |
| `mira_checklist_flow.png` | Overview (dashboard) | Mira pointing at glowing middle node of 3-node flowchart |
| `mira_speech_bubbles.png` | Messages | Mira with speech bubbles floating above open palm |
| `mira_gear.png` | Account/Settings | Mira holding a gear/cog icon |
| `mira_postings.png` | Search/Postings | Mira holding fanned-out cards, pulling one forward |
| `mira_map.png` | Search/Location + Onboarding Language Confirmation (Step 10 EN / Step 11 DE)¹ | Mira pointing at world map with location pin |

**Total: 20 unique illustration files** (11 existing + 8 new screen-specific + 1 glasses variant for profile interview, all generated and approved)

¹ `mira_map.png` serves double duty — onboarding Language Confirmation AND Search/Location guided tour. It is one asset, listed in both tables for clarity.

| `mira_glasses.png` | Profile (interview mode) | Mira wearing glasses, attentive expression — signals profile interview mode |

**Image generation prompt for `mira_glasses.png`** (pass to DALL-E with the Mira reference sheet):

> Anime-inspired character illustration, transparent background, consistent with existing Mira character sheet. Young woman in teal hoodie with long dark hair. She wears round, modern reading glasses with subtle teal-tinted frames. Leaning slightly forward, head tilted — active listening pose. One hand holds a clipboard with teal checkmarks, the other hand has a pen poised mid-air, ready to write. Expression: warm but focused, "I'm paying attention to every word you say." The glasses catch a small highlight to draw the eye. Clean linework, soft cel-shading, full body visible, no background. The glasses are the key differentiator from her standard look — they signal "interview mode."

---

## 6. Onboarding Flow

### Step count

**Current implementation (in code):**
- English: 11 numbered steps + Google auth = 12 screens
- German: 12 numbered steps + Google auth = 13 screens (extra step: Du/Sie formality)

**After UX v3 (adds Mira introduction screen):**
- English: 12 numbered steps + Google auth = 13 screens
- German: 13 numbered steps + Google auth = 14 screens

### Auth step (conditional)

Between step 1 (Language selection) and step 2 (Data sources), unauthenticated users see a Google Sign-in screen. This step is **not numbered** — it uses `data-step="auth"` internally. Authenticated users (returning via cookie) skip it entirely.

- **Method:** Google OAuth only → `/auth/google`
- **Cookie:** `ob_lang` preserves language selection across auth redirect
- **After auth return:** If `ob_lang` or `lang` cookie exists, step 1 auto-skips and flow starts at step 2
- **Card width:** Shrinks to 480px for this step (tighter layout than regular steps)

**Auth step copy:**

| Element | EN | DE |
|---------|-----|-----|
| Button | Sign in with Google | Mit Google anmelden |
| Subtitle | Find jobs that match your skills | Finde Jobs, die zu deinen Fähigkeiten passen |
| Footer | Privacy · Terms · Impressum | Datenschutz · AGB · Impressum |

### English flow (12 steps + auth, after UX v3)

| # | Internal `data-step` | Screen | Illustration | Description |
|---|---|---|---|---|
| 1 | `1` | Language selection | — | Welcome letter. Pick 🇩🇪 Deutsch or 🇬🇧 English. |
| — | `auth` | Google Sign-in | — | Conditional. Only if not authenticated. |
| 2 | `2` | Data sources | — | "Where do the jobs come from?" 335K+ postings, 50+ sources, Germany-focused. Flag-map image. |
| 3 | **NEW** | Mira introduction | `mira_waive.png` | Mira intro copy (see Section 3). Back / Next buttons. |
| 4 | `4` | Terms & Privacy | `mira_t_and_cs.png` | Privacy bullet points. Must view T&C and Privacy Policy overlays, then tick checkbox. |
| 5 | `5` | Our Commitment | `mira_manifesto.png` | "How talent.yoga works" operating principles document. |
| 6 | `6` | Describe your vibe | `mira_crystal_ball.png` | Enter keywords + pick gender (neutral/feminine/masculine) for name generation. |
| 7 | `7` | Name grid | — | LLM-generated yogi name suggestions. Pick one. Link to manual entry. |
| 8 | `8` | Manual name entry | — | Type your own yogi name (min 3 chars, validated via dry-run API). |
| 9 | `9` | CV upload | `mira_cv.png` | Drag/drop PDF/DOCX/TXT. GDPR consent checkbox required. Skippable. |
| 10 | `10` | Language confirmation | `mira_map.png` | Two dropdowns: UI language + content/profile language. |
| 11 | `11` | Notification opt-in | `mira_email.png` | Optional email for job match notifications (encrypted storage). |
| 12 | `12` | Celebration | `mira_paper_snake.png` | "Welcome to the team!" Confetti, tier table, CTA → `/search`. |

### German flow (13 steps + auth, after UX v3)

| # | Internal `data-step` | Screen | Illustration | Description |
|---|---|---|---|---|
| 1 | `1` | Sprachauswahl | — | Willkommensbrief. Pick 🇩🇪 Deutsch or 🇬🇧 English. |
| — | `auth` | Google-Anmeldung | — | Conditional. |
| 2 | `2` | Datenquellen | — | "Woher kommen die Stellen?" |
| 3 | `3` | Du / Sie | — | Formality selection. Two side-by-side cards. Hover previews tone. Selection immediately advances (400ms delay). Default: Du. |
| 4 | **NEW** | Mira-Vorstellung | `mira_waive.png` | Mira intro copy (Du or Sie variant). Zurück / Weiter. |
| 5 | `4` | AGB & Datenschutz | `mira_t_and_cs.png` | Same as EN step 4, German copy. |
| 6 | `5` | Unser Versprechen | `mira_manifesto.png` | German commitment document. |
| 7 | `6` | Beschreib deinen Vibe | `mira_crystal_ball.png` | Keywords + Geschlecht. |
| 8 | `7` | Namensvorschläge | — | LLM-generated names from keywords. |
| 9 | `8` | Name eingeben | — | Manual entry. Du: "Gib deinen Yogi-Namen ein" / Sie: "Geben Sie Ihren Yogi-Namen ein". |
| 10 | `9` | Lebenslauf hochladen | `mira_cv.png` | PDF/DOCX/TXT, DSGVO-Einwilligung. |
| 11 | `10` | Sprachbestätigung | `mira_map.png` | UI-Sprache + Inhaltssprache. |
| 12 | `11` | Benachrichtigungen | `mira_email.png` | Optional email. |
| 13 | `12` | Willkommen! | `mira_paper_snake.png` | Confetti, Tarif-Tabelle, CTA → `/search`. |

### Du/Sie formality effects

The Du/Sie selection on step 3 (DE only) affects **all subsequent onboarding copy**. Every title, subtitle, and body text has a separate variant. English always uses the informal (`du`) equivalent internally.

Examples of the pervasive difference:
- Du: "Gib **deinen** Yogi-Namen ein" / Sie: "Geben **Sie Ihren** Yogi-Namen ein"
- Du: "**dein** Lebenslauf" / Sie: "**Ihr** Lebenslauf"
- Du: "**du** bekommst eine Benachrichtigung" / Sie: "**Sie** erhalten eine Benachrichtigung"

The formality preference is stored in the user's profile and carries through to all Mira interactions, search copy, and account settings throughout the app.

### Post-onboarding redirect

After the celebration screen, the user is redirected to **`/search`** (Search/Start tab, the "situation" flip cards). Mira picks up from there and guides the user through all search tabs end-to-end.

**Implementation note:** The current code redirects to `/` (homepage). This must change to `/search` for UX v3.

### Onboarding completion API call

The `completeOnboarding()` function fires at step 7 (confirm grid name) or step 8 (confirm manual name):

```
POST /api/onboarding/complete
Body: { language, formality, yogi_name, terms_accepted }
```

This creates the user profile. Steps 9–12 continue after the profile exists. The yogi can close the browser after step 8 and their account is saved.

### CV skip behavior

If the user skips the CV upload step during onboarding:
- Search/Field Kanban starts empty (no pre-selection)
- Search/Qualification cards start unselected
- Search/Postings shows results sorted by recency, no match scores
- A persistent but dismissible reminder appears on Search/Postings

### API endpoints

- `POST /api/onboarding/complete` — creates profile (fires at step 7 or 8)
- `POST /api/profiles/me/parse-cv` — CV extraction
- `PUT /api/profiles/me/yogi-name` — set/change yogi name
- `GET /api/profiles/me/yogi-name/suggest-from-keywords` — LLM name generation
- `PUT /api/account/language-settings` — UI + content language
- `POST /api/account/email-consent` — notification email opt-in
- `GET /auth/google` — Google OAuth initiation

---

## 7. Profile Page

**URL:** `/profile`
**Illustration:** `mira_clipboard.png`
**Player widget:** 3-dot player bar (Provide → Discover → Done)

### Architecture change

Adele's user-facing persona is absorbed into Mira. The user always sees Mira, but when Mira conducts the profile interview, she runs the Adele system prompt underneath and her illustration switches to the **glasses variant** (same character, different mode signal).

The profile page becomes:
- **Left pane:** Mira chat (conversational profile building, powered by Adele system prompt)
- **Right pane:** Profile form with Upload / Form / Translate tabs, completion percentage

### Three input methods

All three methods feed the same profile data. Users can combine them.

1. **Upload CV** — fastest path. CV is parsed, profile auto-populates
2. **Chat with Mira** — conversational. Mira asks about roles, skills, experience. Profile fills from answers
3. **Fill form manually** — direct input. User types job titles, skills, education

### Player widget behavior

| Dot | Label | Advances when |
|---|---|---|
| 1 | Provide | User has entered at least one job title + one skill (via any method) |
| 2 | Discover | Implied skills extraction runs automatically after sufficient data |
| 3 | Done | User confirms profile |

### Mira tour (first visit)

**Mira says:** "This is your profile. It helps me find jobs that match you. Three ways to set it up — upload a CV, chat with me, or fill in the form. See the player at the bottom? Click Next and I'll walk you through it."

**Illustration:** `mira_clipboard.png` (lower-right, pointing left toward the profile panes)

### Completion indicator

Move the percentage indicator from the small top-right position to a prominent progress bar spanning the top of the right pane, or integrated into the profile header. The completion percentage is the primary motivator for users to keep filling in their profile.

### Profile opt-out copy

If the profile is empty and the user navigates to Search/Postings:

**EN:** "We have not entered your profile. Jobs will appear, but match scores aren't available until you add some info."

**DE (Du):** "Wir haben dein Profil noch nicht erfasst. Stellen werden angezeigt, aber ohne Match-Bewertung — dafür brauchen wir noch ein paar Angaben."

**DE (Sie):** "Ihr Profil ist leer. Stellen werden angezeigt, aber ohne Match-Bewertung — dafür benötigen wir noch einige Angaben."

### API endpoints

- `POST /api/mira/chat` (replaces `/api/adele/chat` — uses Adele system prompt when in profile interview mode)
- `POST /api/profiles/me/parse-cv`
- `PUT /api/profiles/me`
- `GET /api/profiles/me/implied-skills`

---

## 8. Search/Start

**URL:** `/search` (tab: `situation`)
**Illustration:** `mira_pointing_down.png`
**Player widget:** 5-dot player bar (Start → Field → Qualification → Location → Postings)

### Current state

Three flip cards: My Focus (search mode), My Field (field change), My Plan (intention). Each has a front (teaser) and back (question with options). Player bar at bottom with step dots and action buttons.

### Mira tour (first visit)

**Mira says:** "Welcome to your job search. This is where it all starts. See the player at the bottom? Click Next to walk through each step — I'll be right here if you need me."

**Illustration:** `mira_pointing_down.png` (lower-right, pointing down toward the player bar)

**Tour steps:**
1. Highlight flip cards → "These cards help us understand your situation. Flip each one and answer the question."
2. Highlight player bar → "Use this player to navigate between search steps. Click the arrow to move forward."

### Behavior notes

- After onboarding, this is the first screen the user sees
- Mira auto-appears if user doesn't interact within the configured timeout
- Player bar shows which steps are complete via green checkmarks

---

## 8a. Search Data Flow — Focus, Field, Plan

The three flip cards on Search/Start are the yogi's self-assessment. They answer: *What kind of search is this?* Each card produces a value stored server-side in `users.situation_context` (JSONB). Together, these three signals shape result ranking, cross-field suggestions, and Mira's coaching behavior.

**Current state (code):** All three values are stored in the DB but do NOT yet affect search results. They only control step-progress checkmarks in the UI. **UX v3 changes this** — each signal must influence the search pipeline as documented below.

### Card 1: Focus (`search_mode`, values 1–5)

*"Do we limit postings to the yogi's declared search criteria, or do we also suggest jobs that match their profile even if outside their explicit filters?"*

| Value | Label (EN) | Label (DE) | Effect on results |
|---|---|---|---|
| 5 | Very focused — I know exactly what I'm looking for | Sehr fokussiert — ich weiß genau, was ich suche | **Strict filter.** Only postings matching declared fields + QL + location. No cross-field suggestions. Profile similarity used only for sort order within results. |
| 4 | Mostly focused — but open to close alternatives | Überwiegend fokussiert — offen für nahe Alternativen | **Near match.** Include postings from closely related professions (same KLDB 2-digit domain). |
| 3 | Balanced — both focused and open | Ausgewogen — ich suche gezielt, bin aber auch offen | **Default.** Show filtered results + up to 10% "You might also like" suggestions from related fields. |
| 2 | Exploring — open to related opportunities | Erkundend — offen für verwandte Möglichkeiten | **Wide net.** Include postings from Kanban "To Review" fields. Profile similarity drives ranking. |
| 1 | Very open — I want to see a wide range of options | Sehr offen — ich möchte einen breiten Überblick | **Everything.** All active postings, ranked by profile similarity. Filters still apply to QL and location, but field restrictions removed. |

**Implementation:** The `search_mode` value should map to a `scope` parameter in `_build_posting_where()`. At mode 5, only `state.domains` and `state.professions` pass through. At mode 1, the domain filter is dropped and cosine similarity ranking takes over.

### Card 2: Field (`field_change`, values 1–5)

*"Does the yogi want to see postings outside their declared fields?"*

This is related to Focus but distinct. Focus controls the overall search breadth; Field controls whether the yogi is open to a career change.

| Value | Label (EN) | Label (DE) | Effect on suggestions |
|---|---|---|---|
| 5 | Very important — stay in my field | Sehr wichtig — in meinem Bereich bleiben | Only postings in Kanban "Very Interesting" + "Interesting" columns. |
| 4 | Important — open to related fields | Wichtig — verwandte Bereiche | Include "To Review" column fields. |
| 3 | Balanced — familiar and new | Ausgewogen — vertraute und neue | Include "To Review" + suggest 1–2 fields from unreviewed domains based on profile skills. |
| 2 | Open — other fields possible | Offen — auch andere Bereiche | Actively suggest fields the yogi hasn't considered, based on transferable skills. |
| 1 | Very open — change is welcome | Sehr offen — Wechsel erwünscht | Show cross-field matches prominently. "People with your skills also work in [X]" Mira nudge. |

**Implementation:** `field_change` modifies which Kanban columns are included in `state.domains` when building the search. At value 5, only "Interesting" columns. At value 1, all domains are eligible and Mira surfaces cross-field matches.

### Card 3: Plan (`intention`, values 1–3)

*"What are the yogi's expectations? This controls Mira's coaching behavior, not the search results."*

| Value | Label (EN) | Label (DE) | Effect on Mira's behavior |
|---|---|---|---|
| 1 | Actively searching — find a role soon | Aktiv suchend — zeitnah eine passende Stelle | **Action-oriented coaching.** Mira nudges toward applications. Tracks pace: "You saved 5 postings but haven't applied to any — ready to start?" Suggests cover letter generation. Session framework defaults to 20 min. |
| 2 | Exploring — looking at what's out there | Erkundend — welche Möglichkeiten es gibt | **Low-pressure guidance.** Mira highlights interesting postings. No application nudges. "Take your time — save anything that catches your eye." Session framework defaults to 10 min. |
| 3 | Preparing — building skills for the future | Vorbereitend — Fähigkeiten und Optionen | **Skills-focused coaching.** Mira focuses on profile completion, skills gap analysis, market overview. "Your profile mentions X — here's how demand looks in that area." Session framework defaults to 5 min. |

**Consistency check:** If a yogi sets Plan=1 (actively searching) but never applies after viewing 20+ postings, Mira gently checks in: *"You mentioned you're actively searching. Would you like help with an application, or has your plan changed?"* The yogi can update their Plan at any time from Search/Start.

**Implementation:** `intention` does NOT affect SQL queries. It configures Mira's system prompt context and session framework defaults. Stored in `users.situation_context` alongside `search_mode` and `field_change`.

### How filters become a search query

The complete pipeline from UI to SQL:

```
Search/Field Kanban    ─→ state.domains[]     (KLDB 2-digit codes)
                        ─→ state.professions[] (berufenet names)
Search/Qualification   ─→ state.ql[]          (levels 1-4)
Search/Location        ─→ state.geoLocations[] ({lat,lon,radius_km})
                        ─→ state.states[]      (Bundesland names)
Focus (search_mode)    ─→ scope modifier      (strict → wide)
Field (field_change)   ─→ domain expansion    (which Kanban cols to include)
Profile embedding      ─→ cosine similarity   (sort order when score=true)
```

All filters combine with AND logic:
```sql
WHERE enabled = true
  AND invalidated = false
  AND (domain_match OR profession_match OR profile_match)  -- subject
  AND (ql_match)                                            -- level
  AND (state_match OR haversine_match)                      -- location
ORDER BY cosine_similarity DESC                             -- if profile exists
```

**API endpoints:**
- `POST /api/search/preview` — counts per filter combination (no posting data)
- `POST /api/search/results` — paginated postings with optional cosine ranking
- `GET /api/search/profile-scope` — infer initial filters from profile data
- `GET/POST/DELETE /api/search/situation` — CRUD for flip card answers

---

## 9. Search/Field (Berufsfeld)

**URL:** `/search` (tab: `direction`)
**Illustration:** `mira_sorting_cards.png`
**Player widget:** Kanban guided mode (integrated into the field sorting flow)

### Current state

Field Kanban with 4 columns: To Review, Very Interesting, Interesting, Not Interesting. Fields are cards with names and position counts. Clicking a field opens a detail modal with profession list and smiley rating buttons.

### Changes needed

**Detail modal improvements:**
1. Move the three rating smileys (Very Interesting / Interesting / Not Interesting) to the top, below the field name and stats. Decision first, detail second.
2. Limit the profession list to 10 items by default, with an "Show all" expand toggle
3. If CV data exists, highlight matching professions with a teal indicator
4. NEW: Allow selecting individual professions to limit the search scope (multi-select checkboxes on professions)

### Pre-fill from CV

If the user uploaded a CV during onboarding, the Kanban pre-sorts fields based on CV content. User can change all pre-filled selections.

### Mira tour (first visit)

**Mira says:** "Here's where you sort job fields by interest. Think of it like organizing a deck of cards — put fields you like on the left, ones you don't on the right. Click any field to see what's inside."

**Illustration:** `mira_sorting_cards.png` (lower-right)

---

## 10. Search/Qualification (Qualifikation)

**URL:** `/search` (tab: `level`)
**Illustration:** `mira_star_badge.png`
**Player widget:** None

### Changes needed

Redesign the current QL strip into four cards (dropping level 0 "Nicht klassifiziert"):

| Card | Level | EN Label | DE Label |
|---|---|---|---|
| 1 | 1 | Skilled Worker | Helfer/in |
| 2 | 2 | Professional | Fachkraft |
| 3 | 3 | Specialist | Spezialist/in |
| 4 | 4 | Expert | Experte/Expertin |

**Selection behavior:**
- Click to toggle selection (multi-select)
- If no cards are selected, ALL qualification levels are included in the search (equivalent to "show everything")
- Pre-fill from CV if available

### Mira tour (first visit)

**Mira says:** "Pick the levels that match your experience. Choose one or more — if you skip this, you'll see everything."

**DE (Du):** "Wähl die Stufen, die zu deiner Erfahrung passen. Du kannst mehrere auswählen — wenn du keine wählst, siehst du alles."

**DE (Sie):** "Wählen Sie die Stufen, die zu Ihrer Erfahrung passen. Sie können mehrere auswählen — wenn Sie keine wählen, sehen Sie alles."

**Illustration:** `mira_star_badge.png` (lower-right, pointing at the cards)

---

## 11. Search/Location (Standort)

**URL:** `/search` (tab: `location`)
**Illustration:** `mira_map.png`
**Player widget:** None

### Layout changes

| Current | New |
|---|---|
| City search + radius above map | Remove — redundant |
| Map (center-left) | Map (fills right side) |
| State/city sidebar (right) | Sidebar moves to LEFT |
| Separate search input in sidebar | Remains in sidebar, add radius dropdown here |

**New layout:** `[Sidebar: search input + radius + state/city tree] | [Map (full remaining width)]`

### Interaction model

Three ways to select location, all synced to the same map:
1. **Click the map** → pin drops, radius circle appears
2. **Type a city** (sidebar search) → map zooms, pin drops
3. **Click a state** (sidebar tree or map) → state highlights

All three produce the same geographic filter. The user doesn't need to understand that there are three methods.

**State selection purpose:** "Can't find a job here? They need you in Bavaria." States show position counts and serve as a quick way to explore where demand is.

### Pre-fill from CV/onboarding

If the user selected locations during onboarding, those carry over as pre-selected.

### Mira tour (first visit)

**Mira says:** "Pick where you want to work. Type a city, click on the map, or choose a whole state. The circle shows how far you'd commute."

**DE (Du):** "Wähl aus, wo du arbeiten möchtest. Gib eine Stadt ein, klick auf die Karte oder wähl ein Bundesland. Der Kreis zeigt dir deinen Pendelbereich."

**DE (Sie):** "Wählen Sie aus, wo Sie arbeiten möchten. Geben Sie eine Stadt ein, klicken Sie auf die Karte oder wählen Sie ein Bundesland. Der Kreis zeigt Ihren Pendelbereich."

**Illustration:** `mira_map.png` (lower-right)

---

## 12. Search/Postings (Stellen)

**URL:** `/search` (tab: `opportunities`)
**Illustration:** `mira_postings.png`
**Player widget:** 5-dot player bar (read-only, showing completed search steps)

### Filter pills

Display active search filters as dismissible pills above the results grid. Only on this tab — not on other search tabs.

Format: `[Beruf & Profil: IT & Technologie ×] [Qualifikation: Spezialist × Experte ×] [Ort: Baden-Württemberg ×]`

### Results grid

Card layout with: level badge, NEW tag, job title, location, date, "View details" button.

**With profile:** Cards include a match percentage badge. Sorted by relevance (match score).
**Without profile:** No match percentage. Sorted by recency. Persistent dismissible reminder: "Upload your profile for personalized match scores."

### Posting detail modal

Modal opens on "View details" click. On mobile (`<768px`), opens as full-page view instead of modal. Contains:
- Job title, level badge, location, start date, source, "seen since" date
- Job description rendered as markdown
- "View job listing" external link button
- Interest buttons at the bottom (read first, decide second)

**Button mapping to status engine:**
- "Interested" / "Save for later" → `saved` event
- "Not interested" / "Skip" → `dismissed` event (minimal rationale)

### Engagement tracking

Track these events when a user opens a posting detail modal:

| Event | Trigger | Purpose |
|---|---|---|
| `viewed` | Modal opens | State machine entry |
| `time_in_modal` | Modal close timestamp - open timestamp | Engagement depth |
| `scroll_depth` | Max scroll position as % of content height | Did they read? |
| `maximized` | User clicks maximize button | Deep interest signal |
| `external_click` | User clicks "View job listing" | Intent to apply externally |

This data feeds the Yogi-meter on the Overview page and can trigger Mira nudges: if a user opens many postings but never scrolls past the first paragraph, Mira can suggest reading more carefully.

### Guided Mode — First Visit (Mira Walkthrough)

On the yogi's **first ever visit** to the Postings tab (tracked via `localStorage`), Mira runs a one-time guided walkthrough through a single posting:

**Step 1 — Welcome**
Mira appears with `mira_postings.png`:
*"Du hast es geschafft! Das sind die Stellen, die zu deiner Suche passen. Wollen wir uns die erste gemeinsam ansehen?"*
Pills: `Ja, los geht's` / `Nein, ich schaffe das allein`

If "Nein" → mark tour complete, yogi browses freely. Never ask again.

**Step 2 — Open first posting**
Mira "clicks" the first posting — modal opens automatically.
*"Das ist eine Stelle, die zu deiner Suche passt. Scroll nach unten, wenn du bereit bist."*

**Step 3 — After scroll**
When yogi scrolls past 50% of content:
*"Super! Jetzt haben wir die ganze Stelle gesehen. Findest du sie interessant? Klick auf den passenden Button, um deine Entscheidung festzuhalten."*

**Step 4 — After decision**
Yogi clicks interested/not interested → next posting loads automatically. Mira's final message:
*"Klasse! Du hast deine erste Stelle bearbeitet. Wie du siehst — wenn du eine Stelle abgeschlossen hast, erscheint die nächste. Wenn du aufhören willst, klick einfach irgendwo außerhalb des Fensters."*

Mira disappears. Tour complete, stored in `localStorage`. Never repeats.

### Guided Mode — Return Visits (Session Framework)

On every subsequent visit, Mira greets briefly and offers a time-budgeted session:

**Session start:**
Mira appears: *"Willkommen zurück! Klick auf eine Stelle, um deine Sitzung zu starten."*
Below the greeting, time budget pills: `5 Min` `10 Min` `20 Min` (10 min pre-selected).
Clicking a pill updates the selected duration. No separate "Start" button — the session starts when the yogi clicks any posting.

**During session:**
- A green progress bar is visible at all times while the session is running (bottom of screen or below the filter pills — thin, unobtrusive)
- Bar fills left→right over the chosen duration
- Color: green throughout (no anxiety-inducing color changes)

**Session end:**
When the bar fills completely, a non-blocking toast/banner slides in (does NOT cover postings, does NOT interrupt):
*"Deine Sitzung ist vorbei. Du hast heute [N] Stellen angesehen und [M] gespeichert. Gut gemacht!"*
Buttons: `Weiter machen` / `Fertig für heute`
- `Weiter machen` → resets the bar for another session of the same duration
- `Fertig für heute` → dismisses the banner, yogi can still browse freely

The session is purely advisory — the yogi is never locked out of postings.

### Mira tour text (without profile)

*"Das sind Stellen, die zu deiner Suche passen. Willst du bessere Ergebnisse? Geh zu deinem Profil und lade einen Lebenslauf hoch — dann kann ich sie danach sortieren, wie gut sie zu dir passen."*

---

## 13. Search/Power Search

**URL:** `/search` (tab: `power`)
**Illustration:** (use `mira_pointing_left.png` pointing toward the three-panel layout)
**Player widget:** None

### Current state

Three-panel layout: Sector/Profession tree (left), Map (center), Sparkline + Location tree (right). Filter pills at top. Results grid below. Advanced mode for data-savvy users.

### Changes needed

- Fix broken map rendering
- Add Mira avatar widget (persistent, lower-right)
- One-shot Mira tour

### Mira tour (first visit only)

**Mira says:** "This is Power Search — all controls on one screen. Click categories to filter. If you prefer step-by-step guidance, use the standard search tabs."

**DE (Du):** "Das ist die Power-Suche — alle Filter auf einem Bildschirm. Klick auf Kategorien, um sie an- oder abzuwählen. Wenn du lieber Schritt für Schritt vorgehst, nutz die normalen Such-Tabs."

**DE (Sie):** "Das ist die Power-Suche — alle Filter auf einem Bildschirm. Klicken Sie auf Kategorien, um sie an- oder abzuwählen. Wenn Sie lieber Schritt für Schritt vorgehen, nutzen Sie die normalen Such-Tabs."

---

## 14. Overview Page (formerly Home/Start)

**URL:** `/overview` (renamed from `/home`)
**Illustration:** `mira_checklist_flow.png`
**Player widget:** The flowchart IS the player widget

### URL and label rename

| From | To |
|---|---|
| `/home` | `/overview` |
| EN navbar: "Home" | EN navbar: "Overview" |
| DE navbar: "Start" | DE navbar: "Überblick" |

### Three zones

**Zone 1 (Top): Journey Flowchart**
Horizontal flow showing the user's progress through the job search process. Completed steps have teal checkmarks. The current "next step" is highlighted/glowing. Clicking the next step navigates to the relevant screen with guided mode active.

**Flowchart nodes (left to right):**

```
[Profile] → [Situation] → [Fields] → [Qualifications] → [Location] → [Postings] → [Apply] → [Outcome]
```

| Node | Screen | Completion condition |
|------|--------|---------------------|
| Profile | `/profile` | Profile has name + at least one skill or CV uploaded |
| Situation | `/search` tab Situation | All flip cards answered |
| Fields | `/search` tab Fields | At least 1 field sorted into "Interesting" |
| Qualifications | `/search` tab Qualifications | At least 1 qualification card completed |
| Location | `/search` tab Location | Location radius set |
| Postings | `/search` tab Postings | At least 1 posting viewed |
| Apply | (posting detail) | At least 1 application submitted (`applied` event) |
| Outcome | (posting detail) | At least 1 outcome received (`outcome_received` event) |

**State styling:**
- ✅ Completed: teal fill (`#0d9488`), white checkmark
- 🔵 Current (next step): teal border, pulsing glow animation
- ⬜ Future: gray border, muted text

This flowchart IS the player widget for the Overview page. No separate player bar needed.

**Zone 2 (Middle): Yogi-Meter**
Activity statistics derived from `yogi_posting_events`. Passive display, no guidance needed.

**Counter fields:**

| Counter | Label (EN) | Label (DE) | Source query |
|---------|-----------|-----------|-------------|
| Received | Postings received | Stellenangebote erhalten | `COUNT(DISTINCT posting_id)` from matched postings |
| Viewed | Postings viewed | Angesehen | `COUNT(*) WHERE event_type = 'viewed'` |
| Saved | Saved | Gespeichert | `COUNT(*) WHERE event_type = 'saved'` |
| Dismissed | Dismissed | Aussortiert | `COUNT(*) WHERE event_type = 'dismissed'` |
| Apply intent | Preparing to apply | Bewerbung vorbereiten | `COUNT(*) WHERE event_type = 'apply_intent'` |
| Applied | Applications sent | Bewerbungen gesendet | `COUNT(*) WHERE event_type = 'applied'` |
| Outcomes | Responses received | Rückmeldungen erhalten | `COUNT(*) WHERE event_type = 'outcome_received'` |

**Visual layout:** Single row of pill-shaped counters with teal accent on non-zero values. On mobile, wraps to 2 rows (4 + 3). Each counter shows the number large and the label small below.

**API endpoint:** `GET /api/overview/yogi-meter` — returns all counts in one response.

**Zone 3 (Bottom): Activity Log**
Chronological log of all job search activities. Required for Bewerbungsprotokoll (compliance requirement for job seekers in Germany per §2 SGB II, §§138/159 SGB III).

**Canonical 7-column BA schema** (Agentur für Arbeit standard form):

| # | Column | German label | Description | Required |
|---|--------|-------------|-------------|----------|
| 1 | Datum | Datum | Date of the activity | Yes |
| 2 | Firma | Name und Anschrift der Firma | Company name and address | Yes |
| 3 | Ansprechpartner | Ansprechpartner/in | Contact person (nullable for online/email applications) | No |
| 4 | Tätigkeit | Angestrebte Tätigkeit | Position / job title applied for | Yes |
| 5 | Art der Bewerbung | Art der Bewerbung | Application method: persönlich, schriftlich, telefonisch, online, email | Yes |
| 6 | Ergebnis | Ergebnis | Outcome: offen, Vorstellungsgespräch, Angebot, Absage, keine Rückmeldung | No (updated later) |
| 7 | Vermerke | Vermerke | Internal notes (admin/export only — never shown in yogi-facing UI) | No |

**Database table:** `activity_log`

```sql
CREATE TABLE activity_log (
  id               BIGSERIAL PRIMARY KEY,
  yogi_id          UUID NOT NULL REFERENCES users(id),
  activity_date    DATE NOT NULL,
  company_name     TEXT NOT NULL,
  company_address  TEXT,
  contact_person   TEXT,
  position_title   TEXT NOT NULL,
  application_type ENUM('persoenlich','schriftlich','telefonisch','online','email') NOT NULL,
  result           ENUM('offen','vorstellungsgespraech','angebot','absage','keine_rueckmeldung'),
  notes            TEXT,
  source_url       TEXT,
  posting_id       UUID,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);
```

**Auto-fill:** When a yogi applies through the platform, `company_name`, `position_title`, `application_type`, `source_url`, and `posting_id` are populated automatically from the posting record. The yogi only confirms and can add `contact_person`.

**PDF export:** Renders all 7 BA columns (even if empty) so the Sachbearbeiter recognizes the standard format immediately.

**Export button:**
- Position: Top-right of Zone 3 (Activity Log), aligned with the zone heading
- Label: EN "Export PDF" / DE "PDF exportieren"
- Icon: Download icon (↓) left of text
- Style: Secondary button (outline, not filled) — this is a utility, not a CTA
- Always visible, even if the log is empty (exports a blank form with headers)

**PDF format:**
- Title: "Bewerbungsprotokoll — [Yogi Name or Yogi-Name]" (uses real name if set, otherwise yogi-name)
- Date range: Covers all entries, or filterable by month (dropdown next to export button)
- Table: All 7 BA columns with German headers (Datum, Firma, Ansprechpartner/in, Tätigkeit, Art, Ergebnis, Vermerke)
- Footer: "Erstellt am [date] über Talent Yoga — talent-yoga.de"
- No branding beyond the footer line — this is an official document

**API endpoint:** `GET /api/overview/activity-log/export?format=pdf&month=YYYY-MM` (optional month filter; omit for all)

**Free:** This feature is always free, regardless of credit balance. It's a compliance tool, not a product.

Full schema rationale: see `docs/architecture/activity-log-schema.md`.

### Mira tour (first visit)

**Mira says:** "This is your home base. The top shows where you are in your job search. See that next step? Click it and I'll guide you through it. Below, your activity stats and a log of everything you've done."

**Illustration:** `mira_checklist_flow.png` (lower-right, pointing at the flowchart)

---

## 15. Messages

**URL:** `/messages`
**Illustration:** `mira_speech_bubbles.png`
**Player widget:** None

### Architecture change

Mira replaces Adele in the ALWAYS_SHOW list. Update messages.html:

```javascript
// Before
const ACTORS = {
    mira: { name: 'Mira', role: 'Your Guide', emoji: '🧘' },
    adele: { name: 'Adele', role: 'Interview Coach', emoji: '🎯' },
    // ...
};
const ALWAYS_SHOW = ['mira', 'adele'];

// After
const ACTORS = {
    mira: { name: 'Mira', role: 'Your Guide', emoji: '🧘' },
    // adele removed
    // ...
};
const ALWAYS_SHOW = ['mira'];
```

Note: Mira's avatar in the chat list should use `mira_avatar.png` instead of the 🧘 emoji.

### Mira tour (first visit)

**Mira says:** "This is your inbox. You can chat with your AI assistants, receive messages from support staff, and connect with other yogis. Pick a conversation on the left to start."

**DE (Du):** "Das ist dein Postfach. Hier kannst du mit deinen KI-Assistenten chatten, Nachrichten vom Support erhalten und dich mit anderen Yogis austauschen. Wähl links ein Gespräch aus."

**DE (Sie):** "Das ist Ihr Postfach. Hier können Sie mit Ihren KI-Assistenten chatten, Nachrichten vom Support erhalten und sich mit anderen Yogis austauschen. Wählen Sie links ein Gespräch aus."

**Illustration:** `mira_speech_bubbles.png` (lower-right)

---

## 16. Account/Settings

**URL:** `/account`
**Illustration:** `mira_gear.png`
**Player widget:** None

### Mira tour (first visit)

**Mira says:** "This is where you manage your account — language, email preferences, privacy. Nothing urgent, just good to know it's here."

**DE (Du):** "Hier verwaltest du dein Konto — Sprache, E-Mail-Einstellungen, Datenschutz. Nichts Dringendes, aber gut zu wissen, dass es da ist."

**DE (Sie):** "Hier verwalten Sie Ihr Konto — Sprache, E-Mail-Einstellungen, Datenschutz. Nichts Dringendes, aber gut zu wissen, dass es hier ist."

**Illustration:** `mira_gear.png` (lower-right)

---

## 17. Posting Status Engine

### State machine

```
start
  → visible (posting appears in grid)
    → viewed (user opens detail modal or clicks external link)
      → dismissed (instant skip, minimal rationale) → archived
      → saved (bookmarked, undecided)
        → apply_intent (plans to apply) OR dismissed (changed mind) → archived
      → apply_intent (plans to apply)
        → applied (application submitted) OR not_applied (deliberate non-application, rationale required) → archived
          → outcome_received (employer reply) → resolved → archived
```

### Event types

| event_type | Description | Rationale | Terminal |
|---|---|---|---|
| `viewed` | User opens posting detail or clicks external link | — | No |
| `dismissed` | Quick instinctive skip, minimal interest | Optional (brief) | Yes → archived |
| `saved` | Bookmarked, interested but undecided | — | No |
| `apply_intent` | User plans to apply ("Unterlagen vorbereiten") | — | No |
| `not_applied` | Deliberate non-application after research | Required (for Bewerbungsprotokoll) | Yes → archived |
| `applied` | Application submitted | — | No |
| `outcome_received` | Employer reply/feedback received | — | No |
| `archived` | Final state, posting leaves active pipeline | — | Yes |

### Transition rules

- `viewed` → `dismissed`, `saved`, `apply_intent`
- `saved` → `apply_intent`, `dismissed` (changed mind)
- `apply_intent` → `applied`, `not_applied`
- `applied` → `outcome_received`
- `dismissed`, `not_applied` → `archived`
- `outcome_received` → `archived` (resolved)

### Database table

`yogi_posting_events`:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| yogi_id | UUID | FK to user |
| posting_id | UUID | FK to posting |
| event_type | ENUM | One of the 8 types above |
| rationale | TEXT | Required for `not_applied`, optional for `dismissed` |
| metadata | JSONB | Engagement tracking (time_in_modal, scroll_depth, maximized, external_click) |
| created_at | TIMESTAMP | Event timestamp |

---

## 18. Mira Chat Widget Specification

### Component structure

Extract into `mira-widget.html` partial, include in `base.html` so it appears on every page.

### HTML structure

```html
<div id="mira-widget" class="mira-widget">
  <!-- Avatar button (always visible) -->
  <button class="mira-avatar-btn" id="mira-avatar-btn">
    <img src="/static/img/mira_avatar.png" alt="Mira" class="mira-avatar-img">
  </button>

  <!-- Chat panel (hidden by default) -->
  <div class="mira-chat-panel" id="mira-chat-panel">
    <div class="mira-panel-header">
      <img src="/static/img/mira_avatar.png" alt="Mira" class="mira-header-avatar">
      <div class="mira-header-info">
        <span class="mira-name">Mira</span>
        <span class="mira-status">Your Guide</span>
      </div>
      <button class="mira-minimize" id="mira-minimize-btn">−</button>
    </div>

    <!-- FAQ / follow-up buttons (screen-specific) -->
    <div class="mira-quick-actions" id="mira-quick-actions">
      <!-- Populated by MIRA_CONTEXTS config per page -->
    </div>

    <!-- Chat messages -->
    <div class="mira-messages" id="mira-messages"></div>

    <!-- Settings -->
    <div class="mira-settings">
      <label>
        <input type="checkbox" id="mira-auto-tour-off">
        Don't show guided tours automatically
      </label>
    </div>

    <!-- Input -->
    <div class="mira-input-area">
      <textarea id="mira-input" placeholder="Ask Mira..." rows="1"></textarea>
      <button class="mira-send" id="mira-send-btn">➤</button>
    </div>

    <!-- Guided tour button (always last) -->
    <button class="mira-tour-btn" id="mira-tour-btn">
      🗺️ Guided tour
    </button>
  </div>
</div>
```

### MIRA_CONTEXTS configuration

Each page defines its own context. Follow-up buttons are screen-specific. "Guided tour" is always the last button.

```javascript
window.MIRA_CONTEXTS = {
  '/search': {
    tab_situation: {
      greeting: "Let's figure out your situation first.",
      quickActions: [
        { label: "What do the cards mean?", message: "explain_cards" },
        { label: "Can I skip this?", message: "skip_situation" },
      ]
    },
    tab_direction: {
      greeting: "Sort fields by how interesting they are to you.",
      quickActions: [
        { label: "How does the Kanban work?", message: "explain_kanban" },
        { label: "What if I'm not sure?", message: "unsure_field" },
      ]
    },
    // ... per tab
  },
  '/profile': {
    greeting: "Ready to build your profile?",
    quickActions: [
      { label: "What's the fastest way?", message: "fastest_profile" },
      { label: "Why does this matter?", message: "why_profile" },
    ]
  },
  // ... per page
};
```

### "Don't auto-show" setting

- Checkbox in the Mira chat panel settings area
- Stored in `localStorage` key: `mira_auto_tour_disabled`
- Global scope — applies to all pages
- Does NOT disable manual "Guided tour" button — only auto-trigger

### API endpoints

- `GET /api/mira/greeting` — contextual greeting based on current page
- `POST /api/mira/chat` — free-text chat with Mira
- `POST /api/account/mira-preferences` — save auto-tour preference

### New FAQ pipeline

When a user asks Mira a question that Mira cannot answer:
1. Question is logged and flagged for human review
2. Human (Gershon) writes the answer
3. Answer is added to the FAQ list for that screen
4. FAQ becomes a new quick-action button in MIRA_CONTEXTS

### LLM Error and Fallback States

When Ollama / the LLM is unavailable, Mira degrades gracefully. The chat widget remains visible — only free-text responses are affected.

**Failure modes:**

| Failure | Detection | Fallback behavior |
|---------|-----------|-------------------|
| Ollama not running | Connection refused on `POST /api/mira/chat` | Show template greeting + quick-action buttons only. Free-text input disabled with placeholder text. |
| LLM timeout (>15s) | Request timeout | Show apologetic message. Retry button appears. |
| Model not loaded | Ollama returns 404 / model error | Same as "not running" — template mode. |
| Malformed LLM response | JSON parse error or empty response | Show generic fallback message. Log error server-side. |

**Fallback copy:**

| State | EN | DE (Du) | DE (Sie) |
|-------|-----|---------|----------|
| LLM unavailable | "I'm having trouble thinking right now. Try the quick buttons below, or check back in a moment." | "Ich hab gerade einen Hänger. Probier die Schnellbuttons unten, oder versuch es gleich nochmal." | "Ich habe gerade einen Hänger. Probieren Sie die Schnellbuttons unten, oder versuchen Sie es gleich nochmal." |
| Timeout | "That took too long — sorry! Want to try again?" | "Das hat zu lange gedauert — tut mir leid! Nochmal versuchen?" | "Das hat zu lange gedauert — Entschuldigung! Möchten Sie es nochmal versuchen?" |
| Generic error | "Something went wrong. The quick buttons still work!" | "Da ist was schiefgelaufen. Die Schnellbuttons funktionieren aber!" | "Da ist etwas schiefgelaufen. Die Schnellbuttons funktionieren aber!" |

**Implementation notes:**
- Quick-action buttons always work (they trigger predefined responses, no LLM needed)
- Guided tours always work (static content, no LLM needed)
- Template greetings (from `MIRA_CONTEXTS`) always work as fallback for LLM-generated greetings
- Error state is per-request, not sticky — next message retries the LLM

---

## 19. Mira Tour Overlay Specification

### Overlay system

When a guided tour is active:

1. **Dim overlay:** 40% dark overlay covers the entire page
2. **Target highlight:** The target control gets a cutout in the overlay with a glowing teal border (`#0d9488`)
3. **Mira illustration:** Appropriate pointing illustration appears, positioned to point at the target
4. **Speech bubble:** Text bubble near Mira with the tour step copy
5. **Navigation:** "Next" / "Back" / "End tour" buttons in the speech bubble
6. **Progress:** "Step X of Y" indicator

### Tour configuration per page

Each page defines a `TOUR_CONFIG` array:

```javascript
window.TOUR_CONFIGS = {
  '/search:situation': [
    {
      target: '#flip-cards-row',
      illustration: 'mira_pointing_left.png',
      position: 'right',
      text_en: 'These cards help us understand your situation. Flip each one and answer the question.',
      text_de_du: 'Diese Karten helfen uns, deine Situation zu verstehen. Dreh jede um und beantworte die Frage.',
      text_de_sie: 'Diese Karten helfen uns, Ihre Situation zu verstehen. Drehen Sie jede um und beantworten Sie die Frage.',
    },
    {
      target: '#search-player',
      illustration: 'mira_pointing_center_bottom.png',
      position: 'above',
      text_en: 'Use this player to navigate between search steps. Click the arrow to move forward.',
      text_de_du: 'Benutze diesen Player, um zwischen den Suchschritten zu wechseln. Klick auf den Pfeil, um weiterzugehen.',
      text_de_sie: 'Benutzen Sie diesen Player, um zwischen den Suchschritten zu wechseln. Klicken Sie auf den Pfeil, um weiterzugehen.',
    },
  ],
  '/search:field': [
    {
      target: '#kanban-board',
      illustration: 'mira_sorting_cards.png',
      position: 'right',
      text_en: "Here's where you sort job fields by interest. Think of it like organizing a deck of cards — put fields you like on the left, ones you don't on the right. Click any field to see what's inside.",
      text_de_du: 'Hier sortierst du Berufsfelder nach Interesse. Stell dir vor, du ordnest einen Kartenstapel — Felder die dich interessieren nach links, die anderen nach rechts. Klick auf ein Feld, um reinzuschauen.',
      text_de_sie: 'Hier sortieren Sie Berufsfelder nach Interesse. Stellen Sie sich vor, Sie ordnen einen Kartenstapel — Felder die Sie interessieren nach links, die anderen nach rechts. Klicken Sie auf ein Feld, um reinzuschauen.',
    },
  ],
  '/search:qualification': [
    {
      target: '#qualification-cards',
      illustration: 'mira_star_badge.png',
      position: 'right',
      text_en: "Pick the levels that match your experience. Choose one or more — if you skip this, you'll see everything.",
      text_de_du: 'Wähl die Stufen, die zu deiner Erfahrung passen. Du kannst mehrere auswählen — wenn du keine wählst, siehst du alles.',
      text_de_sie: 'Wählen Sie die Stufen, die zu Ihrer Erfahrung passen. Sie können mehrere auswählen — wenn Sie keine wählen, sehen Sie alles.',
    },
  ],
  '/search:location': [
    {
      target: '#location-map',
      illustration: 'mira_map.png',
      position: 'right',
      text_en: "Pick where you want to work. Type a city, click on the map, or choose a whole state. The circle shows how far you'd commute.",
      text_de_du: 'Wähl aus, wo du arbeiten möchtest. Gib eine Stadt ein, klick auf die Karte oder wähl ein Bundesland. Der Kreis zeigt dir deinen Pendelbereich.',
      text_de_sie: 'Wählen Sie aus, wo Sie arbeiten möchten. Geben Sie eine Stadt ein, klicken Sie auf die Karte oder wählen Sie ein Bundesland. Der Kreis zeigt Ihren Pendelbereich.',
    },
  ],
  '/search:postings': [
    // First-visit: guided walkthrough (4 steps) — see "Guided Mode" in Section 12
    // Return visits: session framework greeting only, no overlay tour
  ],
  '/search:power': [
    {
      target: '#power-search-layout',
      illustration: 'mira_pointing_left.png',
      position: 'right',
      text_en: "This is Power Search — all controls on one screen. Click categories to filter. If you prefer step-by-step guidance, use the standard search tabs.",
      text_de_du: 'Das ist die Power-Suche — alle Filter auf einem Bildschirm. Klick auf Kategorien, um sie an- oder abzuwählen. Wenn du lieber Schritt für Schritt vorgehst, nutz die normalen Such-Tabs.',
      text_de_sie: 'Das ist die Power-Suche — alle Filter auf einem Bildschirm. Klicken Sie auf Kategorien, um sie an- oder abzuwählen. Wenn Sie lieber Schritt für Schritt vorgehen, nutzen Sie die normalen Such-Tabs.',
    },
  ],
  '/profile': [
    {
      target: '#profile-panes',
      illustration: 'mira_clipboard.png',
      position: 'right',
      text_en: "This is your profile. It helps me find jobs that match you. Three ways to set it up — upload a CV, chat with me, or fill in the form. See the player at the bottom? Click Next and I'll walk you through it.",
      text_de_du: 'Das ist dein Profil. Es hilft mir, passende Stellen für dich zu finden. Drei Wege zum Einrichten — Lebenslauf hochladen, mit mir chatten oder das Formular ausfüllen. Siehst du den Player unten? Klick auf Weiter und ich begleite dich.',
      text_de_sie: 'Das ist Ihr Profil. Es hilft mir, passende Stellen für Sie zu finden. Drei Wege zum Einrichten — Lebenslauf hochladen, mit mir chatten oder das Formular ausfüllen. Sehen Sie den Player unten? Klicken Sie auf Weiter und ich begleite Sie.',
    },
  ],
  '/overview': [
    {
      target: '#journey-flowchart',
      illustration: 'mira_checklist_flow.png',
      position: 'right',
      text_en: "This is your home base. The top shows where you are in your job search. See that next step? Click it and I'll guide you through it. Below, your activity stats and a log of everything you've done.",
      text_de_du: 'Das ist deine Zentrale. Oben siehst du, wo du in deiner Jobsuche stehst. Siehst du den nächsten Schritt? Klick drauf und ich begleite dich. Darunter findest du deine Aktivitäten und ein Protokoll über alles, was du gemacht hast.',
      text_de_sie: 'Das ist Ihre Zentrale. Oben sehen Sie, wo Sie in Ihrer Jobsuche stehen. Sehen Sie den nächsten Schritt? Klicken Sie darauf und ich begleite Sie. Darunter finden Sie Ihre Aktivitäten und ein Protokoll über alles, was Sie gemacht haben.',
    },
  ],
  '/messages': [
    {
      target: '#conversation-list',
      illustration: 'mira_speech_bubbles.png',
      position: 'right',
      text_en: 'This is your inbox. You can chat with your AI assistants, receive messages from support staff, and connect with other yogis. Pick a conversation on the left to start.',
      text_de_du: 'Das ist dein Postfach. Hier kannst du mit deinen KI-Assistenten chatten, Nachrichten vom Support erhalten und dich mit anderen Yogis austauschen. Wähl links ein Gespräch aus.',
      text_de_sie: 'Das ist Ihr Postfach. Hier können Sie mit Ihren KI-Assistenten chatten, Nachrichten vom Support erhalten und sich mit anderen Yogis austauschen. Wählen Sie links ein Gespräch aus.',
    },
  ],
  '/account': [
    {
      target: '#account-settings',
      illustration: 'mira_gear.png',
      position: 'right',
      text_en: "This is where you manage your account — language, email preferences, privacy. Nothing urgent, just good to know it's here.",
      text_de_du: 'Hier verwaltest du dein Konto — Sprache, E-Mail-Einstellungen, Datenschutz. Nichts Dringendes, aber gut zu wissen, dass es da ist.',
      text_de_sie: 'Hier verwalten Sie Ihr Konto — Sprache, E-Mail-Einstellungen, Datenschutz. Nichts Dringendes, aber gut zu wissen, dass es hier ist.',
    },
  ],
};
```

### Completion tracking

- `localStorage` key per page: `mira_tour_completed_{page_id}`
- Stored as boolean
- Used to determine if auto-tour should trigger on first visit
- Reset when the user clicks "Guided tour" manually (tour runs again regardless)

### Mobile Behavior (breakpoint: `<768px`)

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Mira avatar button | Bottom-right corner, fixed | Bottom-right corner, fixed (same) |
| Chat panel | Slides up from avatar, 360px wide | Full-screen overlay with close button |
| Tour overlay | 40% dim + cutout highlight | Same dim + cutout, but speech bubble fills bottom 40% of screen |
| Tour illustration | Positioned next to target | Hidden (screen too small — speech bubble only) |
| Tour navigation | "Next / Back / End tour" in bubble | Same, but buttons are full-width tappable bars |
| Posting detail modal | Modal overlay | Full-page view (per Q12 decision) |
| Journey flowchart (Overview) | Horizontal row | Horizontal scroll with snap points |
| Yogi-Meter pills (Overview) | Single row | 2 rows (4 + 3) |
| Player widget (Search) | Fixed bottom bar | Fixed bottom bar, slightly taller touch target (48px min) |
| Guided mode overlay (Search/Postings) | Side panel or modal | Full-page step view |

**Touch targets:** All interactive elements in Mira UI must meet 44×44px minimum tap target (Apple HIG / WCAG 2.5.5).

### Accessibility and ARIA

**Mira avatar button:**
```html
<button class="mira-avatar-btn" aria-label="Open Mira assistant" aria-expanded="false" aria-controls="mira-chat-panel">
```
- `aria-expanded` toggles with panel open/close
- Announce state change: `aria-live="polite"` on the chat panel container

**Chat panel:**
- Role: `role="dialog"` with `aria-label="Mira assistant chat"`
- Focus trap when open (Tab cycles within panel, Escape closes)
- Chat messages container: `role="log"` with `aria-live="polite"` for new messages
- Input: `aria-label="Message to Mira"`

**Tour overlay:**
- Role: `role="dialog"` with `aria-modal="true"`
- Focus moves to speech bubble on tour step start
- Target highlight: `aria-describedby` linking target to speech bubble text
- "Next / Back / End tour" buttons have `aria-label` with step context (e.g., "Next: step 2 of 5")
- Escape key ends tour

**Quick-action buttons:**
- `role="button"` (already native if using `<button>`)
- Clear label text (no icon-only buttons without `aria-label`)

**Keyboard navigation:**
- Avatar: focusable via Tab
- Panel open: Enter/Space on avatar
- Panel close: Escape, or click minimize button
- Tour: arrow keys for Next/Back, Escape to end

**Screen reader announcements:**
- Tour start: "Mira guided tour started. Step 1 of N."
- Tour end: "Guided tour complete."
- New Mira message: announced via `aria-live="polite"` on message container
- Error states: announced via `role="alert"`

---

## 20. i18n Requirements

### Scope

All Mira copy exists in three language variants:
- **EN** — English
- **DE/Du** — German, informal (du)
- **DE/Sie** — German, formal (Sie)

### New i18n keys needed

Add to `en.json`, `de.json` (with formality variants):

**Mira intro screen:**
- `onboarding.mira_intro_title`
- `onboarding.mira_intro_body`
- `onboarding.mira_intro_cta`

**Mira tour copy per screen:** (see individual screen sections above for text)
- `mira.tour.{page}.{step}.text`

**Mira chat widget:**
- `mira.chat.placeholder`
- `mira.chat.auto_tour_label`
- `mira.chat.guided_tour_btn`
- `mira.chat.greeting.{page}`
- `mira.chat.quick_action.{page}.{action}`

**Profile opt-out reminder:**
- `search.postings.no_profile_reminder`

**Overview page labels:**
- `nav.overview` (replaces `nav.home`)

---

## 21. Implementation Priority

*Revised 2026-03-30 after all design decisions finalized.*

### Phase 1: Make It Work (immediate)

**Goal:** The core loop — onboarding → search → find postings → track applications — works end-to-end with all spec changes applied. Yogis can use the product daily. Payment is visible but honestly deferred.

| # | Task | What changes | Touches |
|---|------|-------------|---------|
| 1 | **Focus/Field/Plan affect search** | `situation_context` JSONB (already stored) feeds into `_build_posting_where()`. Focus narrows domain weight, Field filters `berufenet_codes`, Plan adjusts recency/distance. | `search-app.js`, `api/routers/search.py`, `matching/` |
| 2 | **Rename /home → /overview** | URL, navbar labels (EN: Overview, DE: Überblick), redirect old URL | `dashboard.html` → `overview.html`, `base.html`, `header.html`, routes |
| 3 | **Overview page: Journey Flowchart** | Zone 1 — horizontal progress nodes with completion conditions | `overview.html` (new), `api/routers/overview.py` (new) |
| 4 | **Overview page: Yogi-Meter** | Zone 2 — activity counters from `yogi_posting_events` | `overview.html`, `GET /api/overview/yogi-meter` |
| 5 | **Overview page: Activity Log + PDF export** | Zone 3 — `activity_log` table, auto-fill from postings, BA-format PDF export | `overview.html`, `activity_log` table, `GET /api/overview/activity-log/export` |
| 6 | **Posting status engine** | `yogi_posting_events` table + API. Save / dismiss / apply-intent / applied / outcome events. | `POST /api/yogi-posting-events`, search results UI |
| 7 | **Mira widget extraction** | Extract into `mira-widget.html` partial, include in `base.html` (every page gets Mira) | `mira-widget.html` (new), `base.html` |
| 8 | **Mira introduction in onboarding** | New step after Data Sources, before T&Cs. Mira introduces herself. | `onboarding.html` |
| 9 | **Replace Adele with Mira in Messages** | Update ACTORS, ALWAYS_SHOW, avatar. Adele disappears from UI. | `messages.html` |
| 10 | **Onboarding tier table update** | Step 12 tier table reflects Free/Credits/Sustainer (not old tiers) | `onboarding.html` |
| 11 | **Stripe placeholder UX** | All paid buttons visible, clickable, show "coming soon" dialogs. Log clicks. | All screens with paid touchpoints |
| 12 | **Update `mira_llm.py` FAQ_KNOWLEDGE** | Condensed FAQ in system prompt reflects current 51-entry corpus | `core/mira_llm.py` |

### Phase 2: Make It Guided

**Goal:** Mira becomes contextually aware per screen. Quick-action pills, tours, and the `MIRA_CONTEXTS` system go live. Yogis get guided through unfamiliar screens.

| # | Task | What changes | Touches |
|---|------|-------------|---------|
| 13 | **MIRA_CONTEXTS configuration** | Per-screen context objects: greeting, pills, illustration, player config | `core/mira_contexts.py` (new), `mira-widget.html` |
| 14 | **Tour overlay system** | `TOUR_CONFIGS` with step-by-step guided walkthroughs | `mira-tour.js` (new), `mira-widget.html` |
| 15 | **Search/Start Mira tour** | Focus/Field/Plan card explainers, first-visit guidance | `search.html`, `MIRA_CONTEXTS` |
| 16 | **Search/Field improvements** | Detail modal (smileys to top, profession limit, profession selection) | `search.html` |
| 17 | **Search/Qualification redesign** | Redesign as 4 cards (from current layout) | `search.html` |
| 18 | **Search/Location improvements** | Sidebar to left, remove duplicate search, sync interactions | `search.html` |
| 19 | **Search/Postings improvements** | Filter pills, match score display, engagement tracking | `search.html` |
| 20 | **Quick-action pills for 6 screens** | Gershon + Arden draft pills, Nate reviews tone (see N5) | `MIRA_CONTEXTS`, `config/mira_faq.md` |
| 21 | **Profile page: replace Adele with Mira** | 3-dot player widget, Mira context for profile building | `profile.html` |

### Phase 3: Make It Sustainable

**Goal:** Stripe goes live. Yogis can buy credits, pay for Clara/Doug deliverables, become Sustainers. The product has a revenue path.

| # | Task | What changes | Touches |
|---|------|-------------|---------|
| 22 | **Stripe integration** | Mysti sets up Stripe. One-time top-ups + Sustainer recurring. | Stripe dashboard, `api/routers/payments.py` (new) |
| 23 | **Credit system backend** | `users.credit_balance`, `credit_transactions` table, pre-check middleware | DB migration, `api/deps.py` |
| 24 | **Clara paid deliverables** | Match report behind credit check. Confirmation dialog. | `profile_posting_matches__report_C__clara.py`, API |
| 25 | **Doug paid deliverables** | Employer research behind credit check. Confirmation dialog. | `doug__research_C.py`, API |
| 26 | **Balance display** | Credit balance in Mira widget header + account page | `mira-widget.html`, `account.html` |
| 27 | **Top-up flow** | €5 / €10 / €20 packs via Stripe checkout | `account.html`, payment API |
| 28 | **Sustainer flow** | Monthly recurring, choose-your-amount, supporters page | `account.html`, payment API |
| 29 | **Remove Stripe placeholders** | Replace "coming soon" dialogs with real payment flows | All placeholder touchpoints |

### Phase 4: Polish

| # | Task |
|---|------|
| 30 | Search/Power — fix map, add Mira one-shot |
| 31 | FAQ pipeline (new questions → human review → auto-add to quick actions) |
| 32 | Engagement tracking (time in modal, scroll depth, maximize, external clicks) |
| 33 | Mobile adaptations |
| 34 | Account page Mira tour |

---

## Appendix: File Reference

### HTML files (current codebase)

| File | Lines | Description |
|---|---|---|
| `onboarding.html` | 2139 | Onboarding flow |
| `search.html` | 674 | All search tabs |
| `profile.html` | ~2000+ | Profile builder |
| `messages.html` | 536 | Messaging interface |
| `dashboard.html` | ~1200 | Dashboard (to become overview.html) |
| `base.html` | — | Base template (Mira widget goes here) |
| `header.html` | — | Header partial |
| `sidebar.html` | — | Sidebar navigation |
| `account.html` | — | Account settings |

### i18n files

| File | Description |
|---|---|
| `en.json` | English translations (540 lines) |
| `de.json` | German translations with Du/Sie variants |

### API endpoints (complete list)

**Onboarding:**
- `POST /api/onboarding/complete`
- `POST /api/profiles/me/parse-cv`
- `PUT /api/profiles/me/yogi-name`
- `GET /api/profiles/me/yogi-name/suggest-from-keywords`
- `PUT /api/account/language-settings`
- `PUT /api/account/email-consent`

**Mira:**
- `GET /api/mira/greeting`
- `POST /api/mira/chat`
- `POST /api/account/mira-preferences`

**Profile:**
- `PUT /api/profiles/me`
- `GET /api/profiles/me/implied-skills`

**Postings:**
- `POST /api/yogi-posting-events` (new — for status engine)
- `GET /api/yogi-posting-events/:posting_id` (new — for status retrieval)

**Messages:**
- `GET /api/messages/?limit=200`
- `GET /api/messages/unread-counts`
- `GET /api/messages/:id`
- `POST /api/messages/send`

---

## 22. Decision Log (Resolved 2026-03-26)

Questions surfaced during Arden's review (2026-03-25), resolved by Gershon on 2026-03-26.

### Architecture & Infrastructure

**Q1. Mira chat backend — what powers it?**
The spec defines `POST /api/mira/chat` but doesn't specify what LLM drives Mira's free-text responses. Current Mira uses the existing message bus (`yogi_messages`). Options:
- (a) Local Ollama model (cheap, private, but quality?)
- (b) OpenRouter / Claude API (better quality, cost per message)
- (c) Scripted responses only — no free-text chat, just FAQ pills + guided tours
Decision affects Phase 1 scope significantly. If (c), the chat widget is simpler.

**Decision:** LLM-powered with FAQ context injection. Logic lives in `core/mira_llm.py`, FAQ content in `config/mira_faq.md`. Must be EN + DE capable — check prior test results in `tests/test_mira_.py`, retest if needed. On each page load, the LLM receives the page-specific FAQ context. On new session start, the LLM is also fed the yogi's last interactions from `yogi_messages`. Priority is response quality over cost.


**Q2. Mira chat statefulness — per-page or continuous?**
When the user navigates from `/search` to `/profile`, does the chat history reset or persist? The `MIRA_CONTEXTS` config switches per page, but does the conversation carry over?

**Decision:** Continuous. Conversation carries over across page navigations. The yogi can read the full Mira conversation history in their Messages view.

**Q3. `yogi_posting_events` table — UUID or integer PKs?**
Spec says UUID. Our `postings` table uses integer `posting_id`. Mixing PK types adds friction. Recommendation: use integer `BIGSERIAL` to match existing schema convention.

**Decision:** Integer `BIGSERIAL` to match existing schema convention.

**Q4. Profile gate removal — confirm scope.**
We agreed to remove the `🔒 Erstelle zuerst dein Profil` blocker on Search/Start and replace with graceful degradation (no match scores, recency sort, dismissible reminder on Postings tab). Can I ship this immediately as a pre-UX3 change?

**Decision:** Yes, remove the gate. Ship immediately as pre-UX3 change. Files: `search.html` lines 62-67, `search-app.js` `applyProfileGate()`, `style.css` `.profile-gate`.

### Mira Illustrations

**Q5. `mira_glasses.png` — does it exist yet?**
The glasses variant for profile interview mode is specified but wasn't in the image batch. Needs generation before Profile page work begins.

**Decision:** ~~Does not exist yet.~~ **Update (2026-03-27):** `mira_glasses.png` has been generated and saved to `images/Mira/` and copied to `frontend/static/images/Mira/`. Illustration shows anime Mira with teal glasses, clipboard, and pen. Ready for implementation.

**Q6. Eye color consistency across illustrations.**
Several of the pointing variants have different eye colors (violet vs blue). Does this matter, or is it fine at 48px avatar size? If it matters, which illustrations need regeneration?

**Decision:** Keep illustrations as-is. Manual color fix if users notice. Not worth regeneration at 48px avatar size.

**Q7. `mira_play_button.png` filename.**
The image shows Mira pointing downward with both hands — no play button visible. Rename to `mira_presenting.png` or `mira_pointing_down.png`? Or keep the current name since it's used on the Search/Start screen where the player widget lives?

**Decision:** Rename the PNG — current name is confusing. Use `mira_pointing_down.png`. Update all references in spec and code.
### UX Behavior

**Q8. Escalation timer — 10s + 10s, or configurable?**
The spec hardcodes 10 seconds for player dance, 10 more for tour auto-start. Should these be configurable (e.g., in `MIRA_CONTEXTS` per page) so we can experiment? Some screens might need longer idle time (Location map requires study time).

**Decision:** Keep static (10s + 10s) for now. Design the code with configurability in mind so we can switch to per-page timers later without refactoring.

**Q9. Escalation on return visits.**
The escalation ladder fires on "first visit." What counts as first visit? Options:
- (a) First time ever (tracked via `localStorage`)
- (b) First time this session (tracked via `sessionStorage`)
- (c) Every time the page loads, unless user checked "Don't auto-show"
Recommendation: (a) for the tour auto-trigger, (c) for the player widget dance.

**Decision:** Confirmed. Tour auto-trigger uses `localStorage` (fires once ever per screen). Player widget dance uses page-load trigger (fires every visit unless dismissed).

**Q10. Player widget on screens marked "None".**
Search/Qualification, Search/Location, Messages, and Account have "None" for player widget. But the escalation ladder assumes a player widget exists to dance at t=10s. What happens on these screens? Options:
- (a) Skip straight to Mira tour at t=10s (no dance step)
- (b) Mira avatar pulses instead of player dance
- (c) No escalation on these screens (manual tour only)

**Decision:** Screen-specific behavior:
- **Search/Qualification:** Qualification cards wiggle in sequence at t=10s (acts as the "dance" step).
- **Search/Location, Messages, Account:** No dance step — Mira tour starts directly at t=20s (skip t=10s entirely).

**Q11. Profile interview mode transition — how does the user know?**
When Mira enters profile interview mode (glasses variant + Adele prompt), is there a visible transition? A speech bubble like "Let me put on my interview glasses"? Or does the illustration just swap silently?

**Decision:** Speech bubble transition. Mira says something like *"Lass mich meine Brille aufsetzen — jetzt bin ich ganz Ohr!"* ("Let me put on my glasses — I'm all ears!") before the illustration swaps to the glasses variant. This is consistent with the guided tour system, which already uses speech bubbles as the primary Mira communication mechanism (see Section 19 tour overlay + Section 4 escalation ladder).

**Q12. Posting detail modal — inline or full page on mobile?**
The spec describes a modal. On mobile screens (Mysti's phone), modals over grids are cramped. Should posting details be a full-page view on small screens?

**Decision:** Yes. Full-page view on mobile (breakpoint: `<768px`). Modal on desktop.

### Data & Backend

**Q13. Engagement tracking — when does it ship?**
The posting status engine ships in full (all 8 event types). But scroll_depth, time_in_modal, maximize, and external_click are metadata on those events. Build the tracking JS now alongside the events, or defer the metadata collection?

**Decision:** Build it now. Tracking JS ships alongside the posting status engine in the same phase. All metadata fields (scroll_depth, time_in_modal, maximize, external_click) are collected from day one.

**Q14. `POST /api/mira/chat` — does it write to `yogi_messages`?**
Currently Mira messages go through the citizen message bus. Should the new Mira chat widget also write to `yogi_messages` (maintaining the "everyone is a citizen" architecture), or use a separate chat storage?

**Decision:** Yes. Mira chat writes to `yogi_messages`. The conversation appears in the yogi's Messages view. Maintains the unified message bus architecture.

**Q15. Bewerbungsprotokoll compliance — what's the minimum?**
The Activity Log on the Overview page serves the Agentur für Arbeit requirement. What fields are legally required? Date + company + position + action + rationale? Need to verify before building the table schema.

**Decision:** Nate's research is in `docs/architecture/activity-log-schema.md`. Use the canonical 7-column BA form (Datum, Firma, Ansprechpartner, Tätigkeit, Art der Bewerbung, Ergebnis, Vermerke). Schema and compliance details are fully specified in that document.


### Content & i18n

**Q16. Mira tour copy — who writes final text?**
The spec has draft tour text for each screen. Is this final copy, or placeholder for Gershon/Nate to polish? Implementation can use placeholder text, but the tone needs to be consistent across all screens.

**Decision:** Joint review. Current text is draft — Gershon and Arden will polish the wording together before each phase ships.

**Q17. New i18n keys — how many total?**
The spec mentions keys per screen for tours, chat greetings, quick actions, and UI labels. Rough estimate: ~80-100 new keys across EN + DE (Du/Sie). Should we create a dedicated `mira.json` i18n file or extend existing `en.json`/`de.json`?

**Decision:** Dedicated `mira.json` i18n file. Keeps Mira-specific keys isolated from existing UI translations, easier to hand off for review, and avoids merge conflicts with ongoing work on `en.json`/`de.json`.

---

*End of original specification.*

---

## 23. Tier Model

**STATUS: DECIDED (Gershon, 2026-03-29)**

### Design Principle

Mira is the interface — she's free. The **deliverables** she arranges are the product. Pricing is value-based, not cost-based (marginal compute cost per action is ~€0.0003 on local Ollama/RTX 3050).

### What's Free (Always)

| Capability | Why free |
|---|---|
| Browse & search postings | Core value prop — yogis come here to find jobs |
| View posting details | No AI cost, just data display |
| Save / dismiss / track postings | UX essentials |
| Mira chat (unlimited) | Mira is the receptionist, not the product. FAQ pills + full LLM conversation. No message limits. |
| Profile creation & editing | Profile is the input to everything else |
| CV upload & parse | Gets data into the system — benefits us too |
| Adele interview (profile builder) | Same — populates the profile |
| Activity log / Bewerbungsprotokoll + PDF export | Legal requirement for ALG II recipients; must stay free. Includes BA-format PDF export. |
| Doug newsletter | Shared across all yogis, not per-user |
| Embeddings, classification, indexing | Backend infrastructure, invisible to yogis |

### What's Paid (Credit-Based)

| Deliverable | What the Yogi Gets | Price | Model |
|---|---|---|---|
| **Clara match report** | Match score + reasoning + cover letter draft + no-go rationale | TBD (€0.30–€0.50?) | qwen2.5:7b |
| **Doug employer research** | Deep-dive report on a specific company (culture, reviews, salary range) | TBD (€0.20–€0.40?) | qwen2.5:7b + DDG |

> **Pricing note:** These are value-based prices, not cost-based. Compute cost per Clara report is ~€0.0003. The prices above reflect what a job-seeker might reasonably pay for a tailored cover letter or research report. Final prices TBD after user testing.

> **Roadmap:** Interview coaching (mock interview session with AI feedback) is planned but not included in Phase 1–3. Will be designed as a separate deliverable when infrastructure and prompt engineering are ready.

### Credit Mechanics

| Aspect | Decision |
|---|---|
| **Trial** | New users get €5 in credits + 2 weeks, whichever runs out first. Full access during trial. |
| **Top-up** | One-time packs: €5, €10, €20. No subscription required to pay. |
| **Credits never expire** | Yogi stays dormant (has a job), comes back a year later — credits still there. |
| **Pre-check** | Before any paid action: "This costs €X.XX from your balance of €Y.YY — go?" If insufficient: "Top up to continue." Action never starts without confirmed funds. |
| **Balance display** | Visible in Mira widget header + account page. Mira can answer "What's my balance?" |
| **Badge** | 🌱 (zero balance) → 🌿 (has credits) |

### Sustainer (Optional Monthly)

Kept as a separate concept — not a "higher tier" but a solidarity model.

| Aspect | Detail |
|---|---|
| **Price** | €10+/month (choose your amount) |
| **What you get** | Unlimited AI actions (no credit spend) + you fund one free user's trial |
| **Badge** | 🌳 |
| **Supporters page** | Name listed (opt-in) |

Three states, not three tiers: **Free** (Mira + search + profile), **Credits** (pay-per-deliverable), **Sustainer** (unlimited + sponsor).

### Transition

**Grandfather.** Any existing credit balances carry over. No resets.

### Resolved Questions (from earlier discussion)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| T1 | Viewing posting detail: free or paid? | **Free** | No AI cost, just displaying data |
| T2 | Mira chat limits on free tier? | **Unlimited** | Mira is the interface, not the product |
| T3 | Pricing model? | **Fixed € prices** | No credit abstraction — show real euros |
| T4 | Credits mid-action? | **Pre-check** | Never start without confirmed funds |
| T5 | ALG II special pricing? | **No special tier** | Free tier is already generous enough |
| T6 | Sustainer coexistence? | **Keep it** | Drop "Member" — three states: Free / Credits / Sustainer |
| T7 | Transition? | **Grandfather** | Carry over existing balances |

### Implementation Requirements

- `users.credit_balance` column (integer, cents)
- `credit_transactions` table (top-up, spend, refund, type, deliverable_ref)
- Pre-action credit check middleware
- Confirmation dialog component: "This costs €X.XX from your balance of €Y.YY"
- Credit balance display in Mira widget header and account page
- Stripe integration for top-up (one-time payments, not subscriptions)
- Sustainer: Stripe recurring payment, separate from credit system
- Update: `config/mira_faq.md` pricing entries (faq_pricing_001–004)
- Update: `core/mira_llm.py` FAQ_KNOWLEDGE pricing section
- Update: `onboarding.html` step 12 tier table
- Update: commitment document (step 5)

### Stripe Placeholder UX (Phase 1)

Stripe integration will be set up by Mysti after spec implementation review. Until then, every paid touchpoint works but shows honest "coming soon" messaging instead of a payment flow.

**Behaviour:**

| Touchpoint | What happens | Message |
|------------|-------------|---------|
| "Get Clara Report" button | Button is visible and clickable | Dialog: "Clara reports will be available soon. We're setting up payments — check back shortly." |
| "Get Doug Research" button | Button is visible and clickable | Dialog: "Doug research reports will be available soon. We're setting up payments — check back shortly." |
| "Top Up Credits" (account page) | Link/button visible | Dialog: "Credit top-ups are coming soon. During the preview period, all features are free." |
| "Become a Sustainer" | Link/button visible | Dialog: "Sustainer subscriptions are coming soon. Thank you for your interest!" |
| Credit balance display | Shows €0.00 | Tooltip: "Payment system coming soon — all features free during preview" |

**Design rules:**
- Never hide the paid features. Yogis should see what's coming.
- Never fake a payment flow. No "processing..." animations.
- Use Mira's voice in dialogs (warm, honest, short).
- Log every click on a placeholder button (`placeholder_click` event with `feature` field) — this is demand signal data.

---

## 24. Mira Content Inventory

Mira needs content to be effective. This section inventories what exists, what's missing, and what needs updating.

### What exists today

**`config/mira_faq.md`** — 51 curated Q&A entries, 19 categories:

| Category | Entries | Coverage |
|----------|---------|----------|
| Pricing | 4 | Free/Credits/Sustainer model — current |
| Privacy | 4 | GDPR, data deletion, no-name policy — current |
| How It Works | 3 | Matching, sources, pipeline — current |
| Profile | 3 | CV upload, skills, editing — current |
| Matches | 3 | Scoring, explanations, accuracy — current |
| Market/Sources | 3 | Arbeitsagentur, 50+ sources, Germany focus — current |
| Mira | 3 | Who is Mira, what can she do, limitations — current |
| Doug | 2 | Employer research, what Doug finds — current |
| Adele | 1 | Profile builder mode (adele_001) — current. Interview coach entry removed (feature not built). |
| Journey | 2 | Job search as practice, yogi concept — current |
| Contact | 2 | How to reach humans, support channels — current |
| Boundaries | 4 | Legal, predictions, promises, scope limits — current |
| Misc | 3 | Browser support, mobile, languages — current |
| Search | 3 | Focus/Field/Plan explainers — current |
| Status | 2 | Posting status engine — current |
| Log | 2 | Activity log / Bewerbungsprotokoll — current |
| Applications | 3 | Application tracking — current |
| Career | 3 | Career guidance boundaries — current |
| Work Types | 1 | Contract types — current |

**`core/mira_llm.py`** — LLM-first chat implementation:
- Model: Gemma3:4b (3.3GB, good German, low hallucination)
- Condensed FAQ baked into system prompt (~2000 tokens DE + EN)
- Du/Sie-aware prompt construction
- Fallback messages for LLM failures
- Yogi context injection (profile, situation, recent interactions)

### Content gaps (identified)

| Gap | Priority | Status |
|-----|----------|--------|
| **Search flow FAQ** | High | ✅ Done — 3 entries added (search_001–003) |
| **Posting status FAQ** | High | ✅ Done — 2 entries added (status_001–002) |
| **Tier model FAQ** | High | ✅ Done — pricing_001–004 rewritten for credit model |
| **Adele → Mira migration** | Medium | ✅ Done — adele_001 rewritten, adele_002 removed |
| **Activity log FAQ** | Medium | ✅ Done — 2 entries added (log_001–002) |
| **Onboarding explainers** | Medium | Not started — Phase 2 (quick-action pills) |
| **Error scenario content** | Low | Not started |
| **Screen-specific explainers** | Low | Not started |

### Per-screen Mira quick-actions (from Section 18 MIRA_CONTEXTS)

These are the FAQ pills that appear when a yogi clicks Mira's avatar. Each screen needs its own set.

| Screen | Quick-action pills needed | Status |
|--------|--------------------------|--------|
| Search/Start | "What do the cards mean?" "Can I skip this?" "What's my Focus?" | Defined in spec, not yet in code |
| Search/Field | "How does the Kanban work?" "What if I'm not sure?" | Defined in spec |
| Search/Qualification | "What do the levels mean?" | Not defined |
| Search/Location | "How does the radius work?" "Can I pick multiple cities?" | Not defined |
| Search/Postings | "How are these sorted?" "What does the score mean?" "No good matches?" | Not defined |
| Search/Power | "What is Power Search?" | Defined in spec |
| Profile | "What's the fastest way?" "Why does this matter?" | Defined in spec |
| Overview | "What is this flowchart?" "How do I export my log?" | Not defined |
| Messages | "Who can message me?" "Is this private?" | Not defined |
| Account | "How do I delete my data?" "Can I change my language?" | Not defined |

### Content authoring process

1. Gershon identifies a question yogis will ask (from support, testing, or imagination)
2. Gershon writes the answer in Mira's voice (2-4 sentences, three language variants)
3. Answer is added to `config/mira_faq.md` as a new entry
4. Condensed version is added to `core/mira_llm.py` FAQ_KNOWLEDGE if it's a common question
5. If the answer maps to a specific screen, it becomes a quick-action pill in `MIRA_CONTEXTS`

### Content that needs immediate attention

All previously identified urgent content gaps have been addressed:

1. ~~**Rewrite `faq_adele_001` and `faq_adele_002`**~~ — ✅ Done. adele_001 rewritten for Mira profile-builder mode. adele_002 removed (interview coach not built).
2. ~~**Rewrite `faq_pricing_001` through `faq_pricing_004`**~~ — ✅ Done. Reflects Free/Credits/Sustainer model.
3. ~~**Add Focus/Field/Plan FAQ entries**~~ — ✅ Done. search_001–003 added.
4. ~~**Add Bewerbungsprotokoll FAQ**~~ — ✅ Done. log_001–002 added.

---

## 25. Open Questions for Nate — Resolved

All N-series questions answered by Nate (2026-03-29).

| # | Question | Decision | Action |
|---|----------|----------|--------|
| N1 | Language Confirmation illustration | **No illustration needed.** If card feels bare, small teal globe icon inline — not a full Mira illustration. *Update: `mira_map.png` assigned per N6 decision.* | Done — Section 5 + 6 updated |
| N2 | Tier model (Section 23) | **Approved as written.** FAQ pricing entries already reflect new model. | Done |
| N3 | Focus/Field scale: 5-level vs 3-level | **Keep 5 levels.** Present as slider with anchor labels at each end, no numbered labels. Graduated scale maps to search SQL scope modifier. | No spec change needed |
| N4 | Mira intro position in onboarding | **Current placement correct** (after Data Sources, before T&Cs). Mira can frame next step. | No change needed |
| N5 | Quick-action pills for 6 screens | **Gershon + Arden draft, Nate reviews tone.** Screens: Qualification, Location, Postings, Overview, Messages, Account. | Phase 2 work |
| N6 | `mira_map.png` reuse | **Use for Language Confirmation step** (Step 10 EN / Step 11 DE). World map + pin is semantically right for language/location confirmation. | Done — Section 5 + 6 updated |

---

*End of specification.*

