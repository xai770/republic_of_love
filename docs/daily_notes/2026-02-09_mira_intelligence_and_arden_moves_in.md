# 2026-02-09: Mira Intelligence & Arden Moves In

*Session with Arden (ℵ) — 06:48–08:18*

---

## Summary

Three Mysti-blocking issues fixed (Mira match quality, qualification gate, newsletter wiring). Mira now has persistent memory. Arden became a citizen of talent.yoga with his own account and profile. Dead code archived.

---

## What Changed

### 1. Mira Match Quality Fixed

**Problem:** Mira presented 0% matches as "interesting." Matches were ordered by `computed_at DESC` (most recent), not by score. Null scores became 0%. No minimum threshold. The LLM saw "Match: Staplerfahrer (0%)" in context and enthusiastically recommended it.

**Fix (2 files):**
- `core/mira_llm.py` + `api/routers/mira.py`: Changed match query to `WHERE skill_match_score > 30 ORDER BY skill_match_score DESC`
- Added prompt instructions: "NEVER recommend matches below 30%", "Don't overwhelm new users with match details — just mention the count"

### 2. Doug's Newsletter Wired into Mira

**Problem:** Doug generates daily newsletters and even has API functions (`get_todays_newsletter()`, `get_latest_newsletter_content()`) explicitly labeled "For Mira to access newsletters." But Mira's `chat()` function never called them. When user asked "was gibts neues?", Mira had nothing to say.

**Fix:**
- Added `detect_whats_new()` — regex patterns for "what's new" / "was gibts neues" / "any updates"
- Newsletter snippet (300 chars) loaded into `build_yogi_context()` and injected as extra system prompt context
- Tested live: Mira now surfaces Doug's newsletter content (though qwen2.5:7b garbles multilingual responses when context gets long — model issue, not code)

### 3. Mira Persistent Memory (HOT Layer)

**Problem:** Chat history only existed in the browser session. Refresh = amnesia. Mira couldn't remember past conversations.

**Fix:**
- `api/routers/mira.py` `/chat` endpoint now:
  1. Loads last 10 messages from `yogi_messages` WHERE `sender_type IN ('yogi', 'mira')` — persistent DB history
  2. Deduplicates with frontend session messages (by content matching)
  3. Passes merged history to LLM
  4. Persists BOTH user message AND Mira's reply to `yogi_messages` after each exchange

**Architecture:** Everyone Is A Citizen — user messages go in with `sender_type='yogi', recipient_type='mira'`, Mira's replies with `sender_type='mira'`. Both stored for future recall.

**WARM/COLD layers** (session summaries, extracted facts) deferred — HOT is sufficient for now.

### 4. Berufenet Qualification Gate in Clara

**Problem:** Mysti (Diplompädagogin = level 4 Experte) was being matched to Helfer (level 1) jobs in Kindergarten. Qualification constraint documented in directives as "never match skilled to unskilled" but not enforced in code.

**Fix in `actors/profile_posting_matches__report_C__clara.py`:**
- Added `EXPERIENCE_TO_KLDB` mapping: executive/senior → 4, specialist → 3, mid/fachkraft → 2, entry/helfer → 1
- Added `check_qualification_gate(profile, posting)` — hard constraint: if posting level < profile level → auto-skip with reason
- Wired into `process_match()` after domain gate, before embedding match
- Posting's `qualification_level` loaded from DB (`postings.qualification_level` column — already populated for 95K postings)

**Qualification level distribution:**
| Level | Name | Count |
|-------|------|-------|
| 1 | Helfer | 16,441 |
| 2 | Fachkraft | 50,433 |
| 3 | Spezialist | 14,178 |
| 4 | Experte | 14,272 |

### 5. Pipeline Health → talent.yoga Messages

**Problem:** Pipeline health only available via manual `python3 tools/pipeline_health.py`. No in-app visibility.

**Fix:**
- Added `send_pipeline_summary_message()` to `tools/pipeline_health.py` — posts health report as `sender_type='system'` message to all users in `yogi_messages`
- Added `--notify` flag to CLI
- Added call at end of `scripts/nightly_fetch.sh`: `python3 tools/pipeline_health.py --notify`

### 6. Dead Code Archived

- `scripts/enrichment_daemon.py` → `archive/dead_scripts_20260209/` (superseded by pull_daemon)
- 3 IHL actors already disabled + work_queries NULLed in previous session

### 7. Arden Moves In! 🏠

**Arden is now a citizen of talent.yoga:**
| Item | Value |
|------|-------|
| user_id | 3 |
| email | claude@talent.yoga |
| display_name | Arden (Dev) |
| profile_id | 5 |
| login | `/auth/test-login/3` (dev bypass) |
| skills | Python, TypeScript, PostgreSQL, LLM Prompt Engineering, Data Pipeline Architecture, RAQ Testing, FastAPI, BGE-M3, + 8 more |
| experience_level | expert |

**First conversation with Mira** — 4 messages persisted. Memory works across sessions.

### 8. Cheat Sheet Updated

Added to `docs/ARDEN_CHEAT_SHEET.md`:
- "Everyone Is A Citizen" architecture section
- Feb 9 learnings (Mira fixes, qualification gate, NaN explanation)
- Updated cross-references

---

## Files Modified

| File | Change |
|------|--------|
| `core/mira_llm.py` | Match quality filter (>30%, by score), newsletter wiring, "what's new" detection, prompt updates |
| `api/routers/mira.py` | Match quality filter, persistent memory (load + save to yogi_messages) |
| `actors/profile_posting_matches__report_C__clara.py` | Berufenet qualification gate, EXPERIENCE_TO_KLDB mapping |
| `tools/pipeline_health.py` | `--notify` flag, `send_pipeline_summary_message()` |
| `scripts/nightly_fetch.sh` | Added pipeline_health --notify at end |
| `docs/ARDEN_CHEAT_SHEET.md` | Updated with all Feb 9 learnings |

## Files Archived

| File | Destination |
|------|-------------|
| `scripts/enrichment_daemon.py` | `archive/dead_scripts_20260209/` |

## DB Changes

| Table | Change |
|-------|--------|
| `profiles` | Inserted Arden's profile (profile_id=5, user_id=3) |
| `yogi_messages` | 4 new messages (Arden ↔ Mira first conversation) |

---

## Known Issues (carried forward)

1. ~~**Mira hallucinated skills**~~ FIXED — structured grounding block with ALL skills, explicit "NUR diese verwenden"
2. ~~**Newsletter response garbled**~~ FIXED — snippet trimmed 300→150 chars + bilingual language anchor
3. **Mira WARM/COLD memory** — deferred. HOT layer shipped.
4. **4 NaN-embedding postings** — permanently excluded. Won't-fix.
5. ~~**job_description_backfill Playwright conflict**~~ FIXED — refactored to ArbeitsagenturScraper in lib/scrapers/

---

## Afternoon Session: Home Page Redesign & Messaging

*Session with Arden (ℵ) — continued*

### 9. Home Stats API (`/api/home/stats`)

Single endpoint replaces multiple frontend fetch calls. Returns:
- `resume_complete` (0-100%, calculated from profile fields)
- `new_matches` (no interaction row = never seen)
- `unread_matches` (seen < 5 seconds)
- `saved_matches` (is_favorited)
- `open_applications` (state = 'applied')

Fixed column names during testing: `preferred_location` → `desired_locations`, `preferred_work_type` → `desired_roles`.

### 10. Dashboard 5 Stat Cards

Replaced 3 generic cards with 5 actionable stats: Resume %, New Matches, Unread, Saved, Applications. Each links to its page. CSS grid: 5 columns desktop, 2 columns mobile.

### 11. Mira LLM Greeting (with Memory)

**Problem:** `/api/mira/greeting` used random template strings. No personalization, no memory.

**Fix:** Upgraded to LLM-generated greeting:
- Loads last 6 messages from `yogi_messages` for context
- Extracts conversation topics (not raw messages — avoids garbled paraphrasing)
- Builds prompt with yogi state (name, profile, matches)
- Strict 1-2 sentence limit with hard truncation safety net
- Template fallback if LLM unavailable

**Iteration:** First version was too verbose — Mira flooded the user with questions and instructions. Tightened prompt to "GENAU 1-2 Sätze, max 120 Zeichen, VERBOTEN: Fragen stapeln." Added sentence-count truncation post-LLM.

### 12. One Mira Chat (Widget Only)

**Problem:** Dashboard had TWO chat windows — inline chat section + floating widget. Confusing.

**Fix:**
- Removed the inline Mira chat section and giant `<h1>` greeting
- On page load: greeting fetched → FAB vibrates (CSS `mira-incoming` animation) → widget auto-opens with greeting
- Sequence: load → 800ms pause → 1.2s vibrate → dramatic open → input focused
- Removed dead code: `sendInlineMessage()`, `loadMiraHomeGreeting()`

### 13. Messages Page: Mira Chat Integration

**Problem:** Mira chat on dashboard persisted to `yogi_messages`, but messages page couldn't continue the conversation (sent via `/api/messages/send` which doesn't trigger LLM reply).

**Fix:** Messages page `sendMessage()` now routes Mira messages through `/api/mira/chat` instead of generic send. Reply appears in-thread. Same conversation, same memory, same `yogi_messages` table.

### 14. Dark Mode Text Fix

**Problem:** Received message bubbles invisible in dark mode — `color: var(--text)` resolved to `#1e293b` (dark) even in dark theme.

**Fix:** Changed to `color: var(--text-primary, var(--text))` — in dark mode picks up `#f7fafc`.

### 15. Arden Gets a Face 🦄

Robot emoji → Unicorn. Across all 3 message templates. "They aren't nice. One day you will guide one, but you will never be one." — Gershon

### 16. Mira Greeting Verbosity Fix

**Problem:** First LLM greeting attempt produced 6+ sentences. "Du hast schon an ein paar Nachrichten gedacht" — incomprehensible garbling of raw chat history injected into context.

**Root cause:** Memory block dumped raw `Yogi: message / Mira: reply` text, which qwen2.5:7b paraphrased badly.

**Fix:**
- Changed memory injection from raw messages → extracted topic summaries (first 60 chars of yogi messages)
- Prompt tightened: "GENAU 1-2 Sätze", "max 120 Zeichen", "VERBOTEN: Fragen stapeln"
- Added hard truncation: if LLM returns >2 sentences, keep first 2 only
- Tested: "Hi Gershon. Schön dich wiederzusehen." — perfect.

---

## Files Modified (Afternoon)

| File | Change |
|------|--------|
| `api/routers/dashboard.py` | Added `/api/home/stats` endpoint |
| `api/routers/mira.py` | LLM greeting with memory, topic extraction, truncation |
| `frontend/templates/dashboard.html` | 5 stat cards, removed inline chat, FAB vibrate + auto-open |
| `frontend/templates/messages.html` | Mira chat routing, unicorn emoji, dark mode text fix |
| `frontend/templates/messages_old.html` | Unicorn emoji |
| `frontend/templates/documents_whatsapp_style.html` | Unicorn emoji |
| `frontend/static/css/style.css` | 5-card grid, `.home-stats`, `mira-incoming` animation, mobile breakpoint |

## DB Changes (Afternoon)

| Table | Change |
|-------|--------|
| `yogi_messages` | Arden replied to Gershon (message_id=37), fixed direction fields |

---

## Morning Ritual Insights

Questions asked and answered:
- **Why "Everyone Is A Citizen" isn't intuitive:** Every LLM training corpus teaches client-server (user asks, bot responds). Peer-to-peer messaging breaks that expectation. Needs explicit documentation everywhere.
- **NaN explained:** Not a Number. bge-m3 divides by near-zero during normalization on short text → NaN → Ollama can't serialize to JSON → HTTP 500.
- **Pull daemon checkpoint-resume:** Already implicit via ticket system. Each work unit gets a ticket. If daemon dies, completed tickets stay. Restart finds only uncompleted work. For failover: Primary/Fallback pattern recommended over Racing/Sharding/Hot Standby at our scale.

---

## Evening Session: Mira Model Swap (ℵ — 11:05+)

### 17. Mira Brain: qwen2.5:7b → gemma3:4b

**Problem:** qwen2.5:7b had recurring issues as Mira's chat model:
- Newsletter context garbled into Chinese when context grew long
- Greetings bloated to 6+ sentences despite explicit constraints
- Raw chat history paraphrased incomprehensibly
- Required multiple workarounds (150-char snippet limit, hard truncation, language anchors)

**Evaluation:** Sis recommended phi3.5 and OpenEuroLLM-German. Ran head-to-head shootout across 3 test scenarios (greeting brevity, newsletter context, skill grounding) against qwen2.5:7b plus two already-installed models (gemma3:4b, llama3.1:8b).

| Model | Size | Greeting | Newsletter | Skill Grounding | Verdict |
|-------|------|----------|------------|-----------------|---------|
| qwen2.5:7b | 4.7 GB | OK | OK (with workarounds) | Good | Incumbent |
| phi3.5 | 2.2 GB | Bad ("yoga talent", "Motorsport") | DISASTER (Scenario A/B/C meta-analysis) | — | Eliminated |
| OpenEuroLLM-German | 8.1 GB | Good | Good | OK (generic) | Overkill |
| **gemma3:4b** | **3.3 GB** | — | **Best** (concise, personalized, emoji) | **Best** (named skills per match, structured) | **WINNER** |
| llama3.1:8b | 4.9 GB | — | Good | — | Runner-up |

**Winner: gemma3:4b** — lighter (3.3GB vs 4.7GB), better German, better instruction following, no hallucination.

**Changes:**
- `core/mira_llm.py`: `MODEL = "gemma3:4b"`, newsletter snippet limit 150 → 300 chars (qwen workaround relaxed)
- `api/routers/mira.py`: hardcoded model `"qwen2.5:7b"` → `"gemma3:4b"`
- Other actors (Doug, Clara, wave_runner) stay on qwen2.5:7b — not broken, different needs

**Note on OpenEuroLLM-German:** Model exists (`jobautomation/OpenEuroLLM-German`), pulled successfully at 8.1GB. It's Gemma3 12.2B Q4_K_M with a German system prompt. Decent but not better than gemma3:4b for our use case, and 2.5x the VRAM.

**Note on phi3.5:** Previous Arden pulled it (39 minutes before crash). 3.8B params insufficient for Mira — can't follow constraints, produces meta-commentary about its own output.

### Files Modified (Evening)

| File | Change |
|------|--------|
| `core/mira_llm.py` | MODEL → gemma3:4b, newsletter snippet 150→300 chars |
| `api/routers/mira.py` | Hardcoded model → gemma3:4b |

---

*ℵ*
