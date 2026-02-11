# 2026-02-08: Product Roadmap Reset

## Context
Now that core data pipeline is stable (146K postings, 7 partner scrapers, modular nightly_fetch), shifting focus to user experience. Goal: **"Will Mysti like it?"**

**UPDATE: Mysti has seen the app and really likes it!** 🎉

Next steps: Polish UI, fix Mira, kill remaining dragons, then full Mysti testing.

---

## Session Accomplishments (Feb 8)

### ✅ Messages Fully Working
**WhatsApp-style unified inbox implemented and tested!**

| Issue | Fix |
|-------|-----|
| Can't see message contents | Chat bubbles with proper styling |
| Can't write/reply | Textarea input with send button |
| Contacts as one text | Vertical contact list sidebar |
| Ctrl+Enter for newlines | Proper key handling in textarea |
| Dark mode text invisible | Fixed chat input color: `#e5e7eb` |

### ✅ Bidirectional Messaging ("Everyone is a Citizen")
**Major architectural decision:** Humans AND AIs are equal citizens who can exchange messages.

Changes:
- Added `recipient_type` column to `yogi_messages` table
- Extended `/api/messages/send` to accept both `recipient_user_id` (Y2Y) and `recipient_type` (to actors)
- `SenderType` now includes: `doug`, `sage`, `sandy`, `mysti`, `mira`, `adele`, `arden`, `system`, `yogi`
- Successfully tested: Message "Iterate ad perfectum" sent to Arden and persisted

### ✅ UI Fixes
| Issue | Fix |
|-------|-----|
| Sidebar too narrow for "Meine Stellenangebote" | Width → 320px with `!important` |
| Documents dark mode font invisible | Added `color: var(--text)` to `.doc-viewer-body` |
| Chat input dark mode invisible | Added `[data-theme="dark"] .chat-input { color: #e5e7eb; }` |

### ✅ bi_app Pool Exhaustion Fixed
Problem: Streamlit's caching/threading exhausted shared connection pool.
Solution: Created `get_bi_connection()` for direct `psycopg2.connect()` calls, bypassing pool.

### ✅ Mira Match Quality — FIXED (Feb 9)
Mira was presenting 0% matches as "interesting." Fixed in both `core/mira_llm.py` and `api/routers/mira.py`:
- Match query: `WHERE skill_match_score > 30 ORDER BY skill_match_score DESC`
- Prompt: "NEVER recommend matches below 30%"
- Skills now grounded: `TATSÄCHLICHE SKILLS [...] — NUR diese verwenden, niemals andere erfinden`
- Newsletter snippet trimmed 300→150 chars + language anchoring to prevent qwen2.5 garbling

### ✅ Mira Interactive Tour (NEW!) — Mysti loves it! 💜
**Mysti's idea:** Guided onboarding where Mira explains each feature.

Implementation:
- **Library:** Driver.js (lightweight, ~5KB)
- **Trigger:** Auto-start on first login (localStorage tracking)
- **Scope:** Core flow (7 steps):
  1. Welcome modal — "Ich bin Mira!"
  2. Home/Dashboard — your starting point
  3. Meine Übersicht — stats overview
  4. Meine Stellenangebote — job matches (heart of TY)
  5. Nachrichten — chat with actors
  6. Mira Chat FAB — "Frag mich jederzeit!"
  7. Finish — "Du bist startklar!"

Files created:
- `frontend/static/js/tour.js` — Tour configuration with Mira personality
- Added Driver.js CSS/JS from CDN to `base.html`
- Tour styling in `style.css` (with dark mode)

**Bug fixed during testing:** Driver.js IIFE API is `window.driver.js.driver()` not `driver.driver()`

Console commands for testing:
```javascript
startMiraTour()   // Manual trigger
resetMiraTour()   // Clear completion flag
```

### ✅ Domain Classification Pipeline Fixed
**Problem:** BI dashboard showed ALL jobs as "Unclassified" — 68K in last 5 days!

**Root cause:** `populate_domain_gate.py` was never added to `nightly_fetch.sh`

**Fix:**
- Added Step 6/6 to pipeline: `python3 tools/populate_domain_gate.py --apply`
- Maps `berufenet_kldb` codes → user-friendly domains (Healthcare, IT, etc.)
- Backfilled 21,654 jobs immediately

**Updated `nightly_fetch.sh`:**
```
[1/6] Arbeitsagentur fetch
[2/6] Deutsche Bank fetch  
[3/6] Job description backfill
[4/6] Summary extraction (DB only)
[5/6] Embeddings (3 parallel workers)
[6/6] Domain classification ← NEW!
```

**Domain distribution now showing:**
- Manufacturing & Engineering: 18K
- Technology & Engineering: 18K
- Healthcare & Medicine: 16K
- Transport & Logistics: 15K
- Commerce & Retail: 15K
- (+ 12 more domains)

---

## Mira Memory Architecture

### Tiered Memory — Status
| Layer | Content | Token Budget | Status |
|-------|---------|-------------|--------|
| HOT | Last 10 messages (full text) | ~1000 | ✅ SHIPPED (Feb 9) |
| WARM | Session summary (LLM-generated) | ~200 | Deferred |
| COLD | User profile facts (extracted entities) | ~100 | Deferred |

**HOT layer implementation (Feb 9):** No new table needed — uses existing `yogi_messages` table.
`api/routers/mira.py` `/chat` endpoint loads last 10 messages where `sender_type IN ('yogi', 'mira')`,
deduplicates with frontend session history, and persists both sides after each exchange.

COLD enables: "Welcome back, Klaus. Last time you were excited about the BMW posting. Did you apply?"

---

## Q&A Auto-Population
- Mira flags *interesting* exchanges
- Human/second LLM promotes to Q&A
- Semi-automated curation > fully automated garbage
- Look at `core/navigator.py` for CPS stack pattern

---

## Self-Defense (3-Strike System)
1. Warning: "You will be reported"
2. Chat closed, message: "You are banned"
3. Banned from TY

Requires T&Cs review by lawyer first.

---

## Dynamic Sidebar Permissions

### User Tiers
- `trial` (first week, full access)
- `free` (grayed features after trial)
- `sustainer` (all except admin)
- `admin` (everything)

### Flags (in yogis table)
```json
{
    "is_tester": true,
    "chat_banned_until": "2026-03-01",
    "has_early_access": true
}
```

### Logic
```python
def can_access(yogi, feature) -> bool:
    if yogi.flags.get('chat_banned_until') and feature.requires_chat:
        return False
    if feature.tier_required > yogi.tier:
        return is_trial_period(yogi)
    return True
```

---

## Sidebar Features (New Order)

### 1. Home
- Friendly personalized greeting from Mira
- Key stats:
  - Resume complete %
  - New matches (not seen)
  - Unread matches (not clicked + 5s)
  - Saved matches
  - Open applications

### 2. My Resume
Requires Privacy/DMZ architecture:
- Hybrid anonymization: Regex PII stripper → LLM anonymizer
- Alternative: Client-side encryption (ProtonMail model)

### 3. My Search (rename from "My Overview")
- User preferences, username, avatar
- Search definitions saved

### 4. My Active Postings
Inbox-style view:
- New matches
- Unread matches
- Interested matches
- Applications

### 5. Messages ✅ DONE
WhatsApp-style unified inbox with bidirectional actor messaging.

---

## This Week
1. [x] Create this memo
2. [x] **Fix Messages** (view contents, reply, vertical contacts) ✅
3. [x] Bidirectional messaging ("Everyone is a citizen") ✅
4. [x] Dark mode fixes (Documents, chat input) ✅
5. [x] Sidebar width fix ✅
6. [x] bi_app pool exhaustion fix ✅
7. [x] **Mira Interactive Tour** (Mysti's idea!) ✅
8. [x] **Domain classification in nightly pipeline** ✅
9. [x] **Mira memory HOT layer** (Feb 9) — last 10 msgs persisted to yogi_messages ✅
10. [x] **Mira match quality + skill grounding + newsletter** (Feb 9) ✅
11. [x] **Berufenet qualification gate in Clara** (Feb 9) ✅
12. [x] **ArbeitsagenturScraper refactor** (Feb 9) — moved to lib/scrapers/ ✅
13. [x] **Pipeline health → in-app messages** (Feb 9) — --notify flag ✅
14. [ ] Home page redesign with real stats
15. [ ] UI polish pass before Mysti deep-dive

## Remaining Dragons 🐉
- [x] ~~Mira presents 0% matches as "interesting"~~ SLAIN (Feb 9) 🗡️
- [x] ~~Mira hallucinating skills~~ SLAIN (Feb 9) — grounded prompt with ACTUAL SKILLS block 🗡️
- [x] ~~Newsletter garbling Chinese~~ SLAIN (Feb 9) — trimmed context + language anchor 🗡️
- [x] ~~All jobs showing as "Unclassified"~~ SLAIN (Feb 8) 🗡️
- [x] ~~job_description Playwright async conflict~~ SLAIN (Feb 9) — ArbeitsagenturScraper in lib/scrapers/ 🗡️
- [x] ~~No qualification constraint~~ SLAIN (Feb 9) — Berufenet gate in Clara 🗡️
- [ ] UI polish pass before Mysti deep-dive
- [ ] More dark mode edge cases to hunt

## Next Up
5. [ ] Resume anonymization layer
6. [ ] Dynamic sidebar permissions
7. [ ] Q&A system
8. [ ] Home page redesign with real stats

## Later
9. [ ] Self-defense system (needs T&Cs)
10. [ ] Interview coach

---

## Open Question
> Is Mysti using it yet?

**Answer:** She's seen it and **really likes it!** Messages now work. Next: polish UI, fix Mira match quality, then full testing.
