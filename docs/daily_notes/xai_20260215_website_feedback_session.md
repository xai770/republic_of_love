# 2026-02-15 — Website Feedback Session

After the morning pipeline/codebase work, switched to user-facing feedback.
All feedback filed via the in-app widget on talent.yoga and stored in the
`feedback` table. Resolved 8 items (feedbacks #5–#15, skipping some IDs).

---

## Feedback #5 — Qualification level bars on search page

**Filed:** bug, /search
**Issue:** "We need either vertical bars or a pie diagram to show the
percentages/numbers of postings per qualification level."

**Fix** (`06d386f`, `5b8d052`):
- Added QL bar chart to search page — 4 horizontal bars (Helfer, Fachkraft,
  Spezialist, Experte) with counts and percentages
- Backend: new `/api/search/ql-distribution` endpoint querying
  `berufenet_qualifications` via KldB code prefix
- Bars were initially invisible in certain themes — second commit bumped CSS
  cache, increased bar thickness, and improved contrast for both light/dark mode

---

## Feedback #6 — Dark mode search bar text unreadable

**Filed:** bug, /dashboard
**Issue:** "Text in search bar is white on light grey in dark mode —
unreadable. When text is entered, the situation doesn't improve."

**Fix** (`92393ab`):
- Set explicit `color` and `background-color` CSS variables on search inputs
  for `[data-theme="dark"]`
- Input text now uses `var(--text-primary)` on `var(--bg-secondary)`

---

## Feedback #7 — Sidebar feedback panel layout

**Filed:** bug, /dashboard
**Issue:** "The sidebar 'Report an issue' covers the right margin of the
webpage, so it's invisible. Also — the bug icon in the header isn't great.
Humans don't like bugs. A telephone or lightbulb might work as icons."

**Fix** (`892ab85`, `904270b`, `8485f16`):
- Changed bug icon 🐛 to lightbulb 💡
- Made feedback panel semi-transparent (`backdrop-filter: blur`)
- Reduced panel opacity from 0.88 → 0.45/0.5 so underlying content is visible
- Drew visual rectangles over sidebar to indicate it overlays, not replaces
- Moved controls (feedback + notification badge) into the sidebar

---

## Feedback #8 — Messages dark mode + chat history + greeting suppression

**Filed:** bug, /messages (3 sub-items)
**Issue:**
1. "Visibility issue in Dark mode in messages."
2. "I sent a few feedback — these should be in my chat history. I should get
   confirmation and thank you."
3. "The chat needs to include logon/logoff events, so Mira sees what the yogi
   is doing. That way, Mira can stay closed after the yogi has ignored her
   three times."

**Fix** (`d861455`, `0709f7f`):

### Dark mode messages
- Added `[data-theme="dark"]` overrides for message bubbles, input box,
  timestamps — all text now readable against dark backgrounds

### Feedback → chat history
- `api/routers/feedback.py`: after inserting feedback, now also inserts:
  - A system event: `[feedback:{category}] {description[:200]}`
  - A Mira thank-you message (bilingual DE/EN based on description language)
- User sees their feedback appear in Mira's chat with a thank-you response

### Logon/logoff events + greeting suppression
- `api/routers/auth.py`: inserts `logon` event in OAuth callback, `logoff`
  event in logout (decodes JWT before clearing cookie to get user_id)
- `api/routers/mira/greeting.py`: new suppression logic — counts consecutive
  "ignored" sessions (logon→logoff with no yogi chat messages between them).
  If 3+ consecutive ignores → `suppress_greeting: true`
- `api/routers/mira/models.py`: added `suppress_greeting: bool` to
  `GreetingResponse`
- `frontend/templates/dashboard.html` + `search.html`: `triggerMiraGreeting()`
  checks `suppress_greeting` flag. If suppressed, stores greeting as pending
  and only shows it when user manually opens the Mira widget

---

## Feedback #9 — Search results tiles with detail modal

**Filed:** bug, /search
**Issue:** "Let's add postings that match the filter here. Can be tiles or
rows. Once the yogi clicks on a tile, the details open. When closed, he is
asked to click either interested or not interested and can provide a reason."

**Fix** (`5d562f3`):
- Created a search results grid with responsive tiles (company, title,
  location, match score, qualification badge)
- Click → detail modal with full description, requirements, apply link
- On modal close → interest feedback prompt (👍 interested / 👎 not interested
  + optional reason text)
- Created `posting_interest` table for storing feedback
- 3 new API endpoints:
  - `GET /api/search/results` — filtered search with pagination
  - `POST /api/search/interest` — record interest/disinterest
  - `GET /api/postings/{id}` — full posting detail
- Full dark/light mode support, i18n labels in DE/EN

---

## Feedback #10 — Journey tracker dashboard

**Filed:** design change, /dashboard
**Issue:** "Replace tiles with three larger ones: Resume / Search / Apply,
each with sub-steps and status icons (💤 not started, 🛠 in progress,
✔ complete)."

**Fix** (`1d906c2`):
- Replaced entire dashboard tile grid with 3-column journey board
- Columns: **Resume** (3 steps), **Search** (3 steps), **Apply** (4 steps)
- New `/api/home/journey` endpoint computing 10 step statuses from DB state:
  - Upload/Create → checks `profiles` table
  - Fix gaps → checks skill_keywords count
  - Confirm skills → checks `skills_confirmed_at`
  - Define search → checks saved search filters
  - Review matches → checks unread match count
  - Select favorites → checks `posting_interest` with positive sentiment
  - Ship CV → checks applications sent
  - Await reply → checks application status
  - Train with coach → placeholder (not_started)
  - Interview → placeholder (not_started)
- Profile completeness progress bar at top
- CSS: 3 responsive columns, step cards with status emoji

---

## Feedback #11 — Remove yellow tint from in-progress steps

**Filed:** suggestion, /dashboard
**Issue:** "Let's not underlay the tile with the color of the status bar, in
this case yellow. Looks depressing :-)"

**Fix** (`a328a31`):
- Removed amber/yellow background from `.step-card.in-progress`
- Steps now use same neutral background regardless of status
- Only the status emoji (🛠) indicates in-progress state

---

## Feedback #15 — Message truncation + Mira prompt issue

**Filed:** bug, /messages
**Issue:**
1. "My message is truncated. Messages need to be shown in full."
2. "Mira's reply is off. I tell her that I am the author and testing the
   website. She tells me that she is ready for my CV."

**Fix** (`e1f358f`):

### Message truncation
- Root cause: `MessageSummary` model in `api/routers/messages.py` only had a
  `preview` field (body truncated to 100 chars). The list endpoint returned
  `preview` but not `body`.
- Frontend JS: `msg.body || msg.preview` — since `body` was undefined, it
  always fell back to the truncated preview
- Fix: added `body: str` field to `MessageSummary`, populated it alongside
  `preview` in the list endpoint response

### Mira ignoring user context
- Root cause: system prompt had aggressive onboarding push ("encourage them
  to create a profile") even when user already had one. The 7b model followed
  the prompt instruction over the user's actual message.
- Fix (in `core/mira_llm.py`):
  - Added to both EN/DE system prompts: "LISTEN to what the user actually
    says. If they tell you something about themselves, acknowledge it and
    respond naturally. Do NOT ignore their message and push onboarding steps."
  - When profile exists: explicit instruction "do NOT suggest uploading a CV"
  - Softened no-profile instruction from "encourage" to "mention if relevant"
  - Context card now shows profile status with role-appropriate guidance

---

## Commits (website feedback session)

| Hash | Feedback | Description |
|------|----------|-------------|
| `06d386f` | #5 | QL bar chart on search page |
| `5b8d052` | #5 | QL bars contrast fix |
| `92393ab` | #6 | Dark mode search bar text |
| `892ab85` | #7 | Lightbulb icon, semi-transparent panel |
| `904270b` | #7 | Panel transparency increase |
| `8485f16` | #7 | Controls moved to sidebar |
| `d861455` | #8 | Dark mode messages visibility |
| `0709f7f` | #8 | Chat history, logon/logoff, greeting suppression |
| `5d562f3` | #9 | Search results tiles + interest feedback |
| `1d906c2` | #10 | Journey tracker dashboard |
| `a328a31` | #11 | Remove yellow tint |
| `e1f358f` | #15 | Full message body + Mira context awareness |

## Observations

- The feedback widget → DB → fix → resolve cycle works well. Filing from the
  live site keeps the user in context and the screenshot captures exact state.
- Feedback IDs 12–14 don't exist — user filed 5–11, then jumped to 15.
  Likely deleted drafts or the IDs were consumed by other tables.
- The 7b model (qwen2.5) needs very explicit prompt instructions. It follows
  the loudest instruction — if the prompt says "encourage profile creation"
  and the user says "I'm the developer", the model picks the prompt over
  the user. Explicit "LISTEN to the user" rules help.
- All 8 feedback items resolved in one session. The pattern of small,
  incremental commits per feedback item keeps changes reviewable.
