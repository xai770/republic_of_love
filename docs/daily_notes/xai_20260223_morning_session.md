# 2026-02-23 10:15–10:53 — Morning Session Notes

---

## What We Shipped Today

### `tools/pipeline_health.py`
- Fixed `ModuleNotFoundError: No module named 'core'` when run via VS Code play button  
  (`sys.path.insert(0, project_root)` at top of file)
- Added `migrations/embeddings_text_index_20260223.sql` — hash index on `embeddings(text)`  
  Query that was calling `normalize_text_python()` for every row now uses index lookups  
  Result: 10s total runtime instead of potentially minutes
- `get_data_anomalies()` now accepts `embed_gap` from `get_pending_work()` to avoid  
  running the expensive subquery twice

### Tour UX (`frontend/static/js/tour.js` + `style.css`)
- **5s delay** before auto-start (page breathes first)
- **0.5s fade-in** on every popover step
- **🎓 button spotlight** on step 0: wiggle → grow 3× → wiggle → shrink, with gold shimmer  
  sweep and pulsing amber glow ring. Only fires on auto-start + only if user hasn't touched  
  anything yet
- Overlay opacity 0.75 → **0.35** so sidebar stays visible and the spotlight actually shows
- Progress **inlined into title**: "📋 Dein Profil (3 von 7)" — no centering puzzle
- Footer layout: `[Abbrechen]` left / `[← Zurück][Weiter →]` right, clean and balanced
- All buttons equalised to `height: 42px` via `inline-flex`

Commit: `5ad8ba6`

---

## The Roadmap We Agreed On

### 1. turing_fetch — stable ✅
No action needed for now.

### 2. Onboarding — looks great ✅
Minor: Mysti might notice `(1 von 7)` is smaller than the title text. Intentional.  
Tour steps for individual pages deferred until page structures are finalised.

### 3. `/profile` — next up
Polish and tweak. What this means concretely, TBD in next session.

### 4. `/search` — ~80% done
Review after profile is in shape.

### 5. `/matches` — needs new thinking (see below)

### 6. `/dashboard` → rename to `/home`
Plus two new elements (see below).

---

## `/matches` — Paradigm Discussion

The state machine in `ty_postings_yogi_status.graphml` shows postings moving through:
- Seen on "My Search" or "My Matches"
- "Do you intend to apply?" → yes / no / later
- "Are you no longer interested?" → removes from active view

**You proposed:** folder paradigm or email inbox with categories.

**My read of those two:**
- **Folder paradigm** — good for "I filed this away", less good for showing momentum  
  and what to do next. Feels archival.
- **Email inbox with categories** (Unread / Starred / Archived) — familiar, but jobs  
  aren't messages. The metaphor breaks when you need to act on them over weeks.

**Third option I'd suggest: Kanban / pipeline board**  
Columns: `Neu` → `Angesehen` → `Interessant` → `Beworben` → `Antwort erhalten`  
Each posting is a card you drag (or click) across. The yogi sees at a glance where  
everything stands. This is also how recruiters think about candidates — mirror that  
mental model back to the yogi.

Downside: more complex to build than inbox. But it maps directly to the graphml state  
machine, so the data model is already there.

**My recommendation:** Kanban for `/matches`, inbox-style for notifications/messages.  
Happy to be talked out of it.

---

## `/home` — Two New Elements

### A. Yogi Activity Log
First-person log of actions taken:
> "2026-02-23 10:32 — Ich habe das Inserat 'IT Einkäufer' ([extern ↗](https://...)) gelesen  
>  und mich entschieden: **nicht bewerben** — Gehalt nicht angegeben, Standort unklar."

Notes from your spec:
- Read-only on site (no self-doxing risk from editing)
- Download as text/CSV for offline editing
- Show last N entries expanded; rest collapsed or paginated
- This is powerful for people dealing with the employment agency (Agentur für Arbeit)  
  who need to document their job search activity. talent.yoga does the logging automatically.  
  That alone could be a key differentiator.

### B. Yogimeter (progress visualiser)
You asked for a better name. Candidates:

| Name | Vibe |
|------|------|
| **Sadhana** | Sanskrit for daily practice/discipline — on-brand for yoga |
| **Fortschritt** | Straightforward German, no misreading |
| **Mutmesser** | "Courage meter" — emotional and accurate |
| **Wegweiser** | "Signpost" — shows progress and direction |

I'd vote for **Sadhana** if the yogis are comfortable with the Sanskrit, otherwise  
**Mutmesser** for its emotional honesty.

**Visualisation:** Waterfall / funnel chart showing:
```
Gesehen        ████████████████████  320
Interessiert   ████████              82
Beworben       ████                  31
Antwort        ██                    14
Zusage         ▌                      2
```
Shows courage concretely. Each bar is clickable → jumps to filtered `/matches` view.

---

## What You Might Have Missed

1. **Data capture for the activity log** — we don't currently record *when* a yogi  
   views or acts on a posting, only pipeline-side status. We'll need a  
   `yogi_posting_events` table (yogi_id, posting_id, event_type, reason, created_at)  
   before we can build the log or the yogimeter. Worth designing that schema soon  
   so it's in place before UI work starts.

2. **The `/matches` → `/home` feedback loop** — the activity log on home is only  
   useful if the Yogi actually logs decisions on `/matches`. That means the  
   "Do you intend to apply?" interaction on `/matches` needs to be frictionless  
   and clearly save to the log. UX on those two pages is tightly coupled.

3. **`/dashboard` rename** — need a redirect from `/dashboard` → `/home` and to  
   update all internal links, the tour steps, and the sidebar. Small but fiddly.

4. **Employment agency compliance angle** — the activity log idea is genuinely  
   valuable for ALG-I/ALG-II recipients who must document job applications.  
   Worth stating that explicitly in the UI ("Nachweisbar für die Agentur für Arbeit").  
   Might be a strong acquisition hook.

---

## Next Session Starting Point
→ `/profile` polish and tweak  
→ Schema design for `yogi_posting_events` (can happen in parallel)

---

## Afternoon Session — What We Actually Built

*(Started from the roadmap above and just kept going.)*

### Track A — Profile-aware Adele greeting `4265bfe`
- `build_profile_context(user_id, conn)` in `core/adele.py` — queries `profiles` +  
  `profile_work_history`, assembles a compact context string for the LLM
- Two new greeting variants: `_intro_has_profile_de()` / `_intro_has_profile_en()`  
  — Adele now opens differently if she already knows you
- `_ask_llm` / `_ask_llm_cascade` got a `system=` kwarg passed through to Ollama
- All 5 `_extract()` calls in `adele_chat` now receive `profile_ctx=`
- `greet` endpoint queries the DB before choosing which greeting to use

### Track B — Audit log, freeze flag, Han Solo button `51e7694`

**Schema** (`migrations/yogi_audit_log_20260223.sql`, applied):
- `yogi_audit_log` table — append-only, DB-level `NO UPDATE / NO DELETE` rules
- `users.freeze_flag BOOLEAN DEFAULT FALSE`
- Indexes on `user_id`, `event_type`, `created_at DESC`

**`lib/audit.py`** (new):
- `log_audit_event()` — never raises, returns -1 on failure
- `get_audit_timeline()` — newest-first, limit param
- `event_to_prose()` — human-readable sentences from raw events
- Event types: `login`, `logout`, `cv_upload`, `adele_save`, `profile_translate`,  
  `profile_embed`, `freeze`, `unfreeze`, `gdpr_consent`

**Wired into:**
- `auth.py` — login + logout
- `profiles.py` — CV upload + translation
- `adele.py` — `_try_save()`

**New API endpoints:**
- `GET /api/adele/audit` — prose timeline + raw events for the logged-in user
- `POST /admin/users/{id}/freeze` — sets freeze_flag, logs audit event
- `POST /admin/users/{id}/unfreeze`
- `GET /admin/users/frozen` — list all frozen accounts

**Han Solo button** (`by_admin/components/users.py` + `by_admin/app.py`):
- New **👥 Users** tab in Streamlit admin (5th tab)
- Summary metrics: total / frozen / disabled
- Per-user expandable rows: 🧊 Freeze / 🔓 Unfreeze buttons, last 10 audit events inline
- Email / name filter + "show frozen only" checkbox

### GDPR consent checkbox `71ee189` + `a1c3672`

**Schema** (`migrations/gdpr_cv_consent_20260223.sql`, applied):
- `users.gdpr_cv_consent_at TIMESTAMPTZ`

**Backend gate** (`parse_cv` endpoint):
- New `gdpr_consent: str = Form(default="")` parameter
- Returns **422** if not `"true"` — LLM never touches the CV without explicit consent
- On consent: stamps `gdpr_cv_consent_at`, writes `gdpr_consent` audit event

**Frontend** (both `profile.html` and onboarding step 9):
- Checkbox rendered above the dropzone; file input blocked + alert shown if unticked
- `gdpr_consent=true` appended to `FormData` on submit
- Plain-language label (not legalese): explains what AI reads, what gets anonymised,  
  that the CV is never shown to employers
- All three language variants: English, de-Du, de-Sie (formal)

---

## Final Commit List for the Day

| Hash | Description |
|------|-------------|
| `5ad8ba6` | Tour UX + pipeline_health fixes |
| `4265bfe` | Track A — profile-aware Adele greeting |
| `51e7694` | Track B — audit log, freeze flag, Han Solo button |
| `71ee189` | GDPR consent checkbox for CV upload |
| `a1c3672` | Plain-language GDPR consent copy |
| `0ea5ae4` | Loose ends: `require_unfrozen_user`, DELETE /cv-consent, account privacy section |
| `33c191c` | Deps and wiring cleanup |
| `6120eac` | Dual-language profile architecture + Experience/Skills tab split |

Eight commits. A full day.

---

## Evening Session — Dual-Language Architecture `6120eac`

### The Problem We Solved
BGE-M3 is multilingual but not perfectly cross-lingual. "Projektmanagement" and
"Project Management" don't sit at distance 0 in the vector space — they're close,
but not as close as a monolingual comparison. A DE-profile yogi systematically
undermatches EN job postings purely due to embedding geometry. Solution: embed
both language versions and route by posting language at match time.

### DB Migration (`migrations/profile_language_translations_20260223.sql`)
- `profiles.language VARCHAR(10) DEFAULT 'de'` — canonical language, set automatically  
  from CV text on import (langdetect, defaults to `'de'`).
- `profile_translations (profile_id, language, profile_summary, translated_at, model)`  
  — non-destructive summary cache. The canonical `profiles.profile_summary` is  
  **never overwritten**. `UNIQUE (profile_id, language)`.
- `profile_work_history_translations (work_history_id, language, job_description, ...)`  
  — same pattern for work-history descriptions. `UNIQUE (work_history_id, language)`.

### `api/routers/profiles.py`
- `_detect_language(text)` — langdetect wrapper, maps to `'de'` or `'en'`, default `'de'`
- `_run_translation` refactored — exclusively INSERTs/UPDATEs the cache tables;  
  after all sections complete it fires `_schedule_profile_embedding_for_language()`  
  for the target language automatically.
- `_build_profile_text_for_language(user_id, conn, language)` — joins  
  `profile_translations` for the requested language; falls back to canonical  
  text transparently if no translation cached yet.
- `_compute_profile_embedding_for_language_bg / _schedule_*` — same  
  fire-and-forget thread pattern as canonical embedding.
- `import_cv` — detects language from summary + work descriptions, persists  
  to `profiles.language`, returns `"language"` in response.
- `POST /me/translate` — rewritten: derives target as the *other* language  
  (DE→EN automatically, or EN→DE), rejects if target == canonical, requires  
  `require_unfrozen_user`, returns `canonical_lang` + `target_lang` + `had_existing_cache`.
- `GET /me/translation-status` — new: returns `canonical_lang` +  
  `translations[]` with `language`, `translated_at`, `has_summary` per cached version.

### `actors/profile_posting_matches__report_C__clara.py`
- `get_profile_data` now selects `user_id` + `profiles.language`.
- `get_posting_data` now selects `source_language`.
- `build_profile_text_for_language(conn, profile, language)` — loads translated  
  summary from `profile_translations` cache; falls back to canonical text.
- `compute_similarity` refactored — routes by `posting.source_language`:  
  EN posting → EN profile text, DE posting → DE profile text. Cross-lingual  
  penalty eliminated when translation exists.
- `similarity_matrix` now records `posting_lang`, `profile_lang`, `used_translation`.

### `frontend/templates/profile.html`
- Form modal split into two inner tabs: **💼 Experience** | **🎯 Skills**
  - Experience: Identity, Basics, Work history, Education, Projects, Preferences
  - Skills: skill chips (extracted + implied), add-skill row
- Translation status banner in the Skills tab:
  - If EN version exists: "✓ English version ready · last updated Feb 23 · used to  
    match English job postings" + **↻ Refresh** button
  - If not: "Match English job postings better · …translate once to unlock equal  
    matching." + **🌐 Generate** button
- `switchFormTab(name)` — tab switching
- `loadTranslationStatus()` — fetches `/me/translation-status`, renders banner;  
  fires non-blocking on page load and again after any translation job completes.

### Architecture Notes for Future Reference
- The `embeddings` table is keyed on `text_hash` (SHA-256). Because the translated  
  text hashes differently from the original, both embeddings coexist naturally — no  
  schema changes needed to `embeddings`.
- Clara always falls back to canonical text if no translation exists yet, so existing  
  yogis are unaffected until they opt into translation.
- `profiles.language` defaults to `'de'` for rows created before this migration.  
  The first CV re-import or manual translate will set the correct value.
- Cover letter language: still generated at match time by Clara (not stored);  
  language-routing here only concerns the *matching* embeddings, not letter generation.

---

## Tomorrow's Starting Point
- Test the translation banner UI end-to-end with a real account
- Possibly: backfill `profiles.language` for existing users via a one-off script
  (`langdetect` on `profile_summary` for those with text)
- `/matches` Kanban view — carry forward from this morning's roadmap discussion
