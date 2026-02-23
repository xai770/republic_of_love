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
