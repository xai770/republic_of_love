# talent.yoga MVP Progress Tracker

**Started:** 2026-01-23  
**Target MVP:** 2026-02-24  
**Total estimate:** 52h

---

## 🎯 MVP Scope (Jan 26 Decision)

**Must ship before public launch:**

| Category | Items |
|----------|-------|
| **Features** | Google login, Profile import (facets only), Match dashboard |
| **Legal** | Impressum, Privacy Policy, ToS, "not an employment agency" disclaimer, source attribution, cookie consent |
| **Data** | arbeitsagentur skeleton loading (50K+ titles), on-demand enrichment |

**Nice to have (post-MVP):**

| Feature | Notes |
|---------|-------|
| Du/Sie toggle | User preference for formal/informal |
| Persona naming | Clara → Heinz |
| Email digests | Weekly match summary |
| Chat integration | Contextual AI chat |

---

## Current Sprint: Week 1 (Jan 23 - Jan 27)

**Goal:** User can log in

| Task | Est | Status | Started | Completed | Notes |
|------|-----|--------|---------|-----------|-------|
| [P1.1 User Auth](P1.1_user_authentication.md) | 4h | ✅ Done | Jan 23 | Jan 23 | Google OAuth working |
| [P1.2 API Layer](P1.2_api_layer.md) | 6h | ✅ Done | Jan 23 | Jan 23 | All endpoints built |
| [P1.3 Profile CRUD](P1.3_profile_crud.md) | 2h | ✅ Done | Jan 23 | Jan 23 | /profiles/me |
| [P1.4 Match Endpoints](P1.4_match_endpoints.md) | 3h | ✅ Done | Jan 23 | Jan 23 | /matches + rate/applied |
| [P3.1 Login Page](P3.1_login_page.md) | 2h | ⏭️ Skip | — | — | Minimal version sufficient |

---

## Week 2 (Jan 28 - Feb 3)

**Goal:** User can see matches

| Task | Est | Status | Started | Completed | Notes |
|------|-----|--------|---------|-----------|-------|
| [P3.3 Match Dashboard](P3.3_match_dashboard.md) | 4h | ✅ Done | Jan 23 | Jan 23 | HTMX + ratings + filters |

---

## Week 3 (Feb 4 - Feb 10)

**Goal:** Full read/write + visualization

| Task | Est | Status | Started | Completed | Notes |
|------|-----|--------|---------|-----------|-------|
| [P3.2 Profile Editor](P3.2_profile_editor.md) | 4h | ⬜ Not Started | — | — | |
| [P3.4 Report Viewer](P3.4_report_viewer.md) | 3h | ⬜ Not Started | — | — | |
| [P3.5 Viz Embed](P3.5_visualization_embed.md) | 4h | ✅ Done | Jan 23 | Jan 23 | Skill matrix in browser |

---

## Week 4 (Feb 11 - Feb 24)

**Goal:** Feedback loop + automation

| Task | Est | Status | Started | Completed | Notes |
|------|-----|--------|---------|-----------|-------|
| [P4.1 User Ratings](P4.1_user_ratings.md) | 3h | ⬜ Not Started | — | — | |
| [P4.2 App Tracking](P4.2_application_tracking.md) | 4h | ⬜ Not Started | — | — | |
| [P2.1 Scheduled Match](P2.1_scheduled_matching.md) | 3h | ⬜ Not Started | — | — | |
| [P2.2 Email Delivery](P2.2_email_delivery.md) | 4h | ⬜ Not Started | — | — | |
| [P2.4 Notifications](P2.4_match_notifications.md) | 2h | ⬜ Not Started | — | — | |

---

## 🚨 MVP Blocker: arbeitsagentur.de

| Task | Est | Status | Notes |
|------|-----|--------|-------|
| [P2.3 arbeitsagentur.de](P2.3_arbeitsagentur_interrogator.md) | 8-12h | ✅ Done | Jan 25-26: 6,433 jobs! Full pipeline running |

### Implementation Details (Jan 25-26)

**Phase 1: API Discovery & Actor Build (Jan 25)**
- **Actor:** `actors/postings__arbeitsagentur_CU.py` (actor_id: 1297)
- **API:** `rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs`
- **Auth:** Simple header `X-API-Key: jobboerse-jobsuche` (no OAuth needed!)
- **First import:** 85 jobs from 4 cities

**Phase 2: Scale-Up Scrape (Jan 25 evening)**
- Scraped 2,606 jobs across all German tech professions
- Added HTML description scraping (job details page)
- 76.4% success rate on description fetch (1,991 with full details)

**Phase 3: City-Wide Expansion (Jan 25-26)**
| City | Jobs Found | New | Description Success |
|------|-----------|-----|---------------------|
| Frankfurt | 991 | 966 | 160 |
| Köln | 994 | 959 | 145 |
| München | 995 | 915 | 133 |
| **Totals** | 2,980 | 2,840 | 438 |

**Phase 4: Translation & Summary Pipeline (Jan 26)**
- Modified `postings__extracted_summary_U.py` for German jobs:
  - Auto-detect language via `source_language` column
  - Translate German → English (stored in `job_description_en`)
  - Extract structured summary from English text
- **Current stats (as of Jan 26 3pm):**
  - Total AA postings: **6,433**
  - Translated to English: **3,525** (55%)
  - Summaries extracted: **3,550** (55%)
  - Batch 2 running: 1,005/3,839 processed
  - Failure rate: ~2.1% (translation edge cases)
  - Processing speed: ~4s/posting (GPU)
  - **ETA full completion:** ~6pm today

**Quality Assessment:** ✅ Excellent
- Technical terms preserved correctly (CI/CD, Docker, Kubernetes)
- Healthcare vocabulary accurate (Pflegefachkräfte → Geriatric Nurse)
- Consistent summary structure (Role, Company, Responsibilities, Requirements)

---

## 📊 Posting Inventory (for Sandy)

*Updated: Jan 26, 2026 @ 6pm*

| Source | Total | Summaries | Translated | Status |
|--------|-------|-----------|------------|--------|
| **arbeitsagentur.de** | 6,433 | 3,550 (55%) | 3,525 | 🔵 Batch 2 running |
| **Deutsche Bank** | 2,206 | 2,202 (99.8%) | 45 | ✅ Complete |
| **TOTAL** | **8,639** | **5,752** | 3,570 | |

### Next Pipeline Steps (after summaries complete)
1. `posting_facets__row_C.py` — CPS facet extraction (Lily)
2. `posting_facets__expand_C__ava.py` — Facet expansion (Ava)
3. Profile matching against new postings

---

## Open Topics & Ideas

Capture ideas as they come. Move to sprint when ready.

### 🔴 Feedback Loop (Priority)

**Goal:** User rates matches → system learns → better matches

| Component | Status | Notes |
|-----------|--------|-------|
| `user_rating` column | ✅ Exists | 1-5 stars per match |
| `user_applied` column | ✅ Exists | Did user apply? |
| Rating UI | ✅ Done | HTMX star buttons on dashboard |
| Applied button | ✅ Done | "Mark Applied" persists to DB |
| "Why this rating?" text | ⬜ | Free-form feedback |
| Threshold tuning | ⬜ | Adjust 0.70/0.60 based on feedback |
| Per-user preferences | ⬜ | Learn what THIS user values |

**Questions to answer:**
1. If user rates 5★ but didn't apply — what does that mean?
2. If user rates 1★ on high-score match — which skill was wrong?
3. How do we surface "you said you don't like X" in future matches?

### 🟡 Planned Features

| Feature | Notes |
|---------|-------|
| **German/English i18n** | UI must be bilingual from day 1 (Mysti requirement) |
| **Du/Sie formality** | User preference for formal/informal German |
| **Persona customization** | Users can rename AI personas (Clara → Heinz) |
| Match explanation | "Why did I get this?" breakdown |
| Skill gaps report | "To get more matches, add these skills" |
| Company blocklist | "Never show me X corp again" |
| Location preferences | "Only remote" / "Only Germany" |
| Saved searches | "Show me all PM jobs in Frankfurt" |
| **Two-tier matching** | Embedding screening (instant) + LLM on-demand |
| **Cross-user caching** | Cache posting analysis, personalize on click |

### 🟢 Nice-to-Have

| Feature | Notes |
|---------|-------|
| Cover letter generator | Per-match, using profile + posting |
| LinkedIn import | Extract skills from LinkedIn profile |
| Weekly digest email | Summary of new matches |
| Mobile-friendly UI | Responsive design |

---

## Progress Log

### 2026-01-26 (Monday)

**arbeitsagentur.de Pipeline — ✅ SCALED TO 6,433 JOBS**

Major expansion of the AA integration from 85 → 6,433 jobs.

**1. City-Wide Fetching**
- Discovered wildcard search (`--search "*"`) works for location-based fetch
- Parallel fetches from Frankfurt, Köln, München
- Added ~2,840 new jobs in under 10 minutes

**2. Translation Pipeline**
- German job descriptions auto-translated to English
- Using local qwen2.5-coder:7b at 100% GPU utilization
- Translations stored in `job_description_en` column
- ~4 seconds per posting (warm GPU)

**3. Summary Extraction**
- Modified `postings__extracted_summary_U.py` with:
  - `--source arbeitsagentur` filter
  - `--batch N` mode for bulk processing
  - Auto-translation before summary extraction
  - Increased timeout to 240s for large documents
- Structured output: Role, Company, Location, Responsibilities, Requirements

**4. Quality Verified**
- Reviewed DevOps, Healthcare, Education postings
- Technical terms preserved accurately
- Natural English phrasing (not "machine-sounding")
- 1.3% failure rate (excellent for edge cases)

**Files modified:**
- `actors/postings__extracted_summary_U.py` — added translation + batch mode
- `actors/postings__arbeitsagentur_CU.py` — enhanced for scale

**Next steps:**
- Complete summary extraction (currently at 1,386 of 6,433)
- Run `posting_facets__row_C.py` for CPS extraction
- Run `posting_facets__expand_C__ava.py` for facet expansion

---

### 2026-01-25 (Sunday)

**arbeitsagentur.de Integration — ✅ COMPLETE**

MVP blocker resolved! Can now ingest jobs from the German Federal Employment Agency.

- **API discovered:** `rest.arbeitsagentur.de` with simple `X-API-Key: jobboerse-jobsuche` header
- **Actor built:** `actors/postings__arbeitsagentur_CU.py` (actor_id: 1297)
- **First import:** 85 jobs from 4 cities (Berlin, München, Hamburg, Frankfurt)
- **No OAuth needed!** Just a public API key (thanks bundesAPI project)
- **Research doc:** `docs/daily_notes/arden_20260125_arbeitsagentur_research.md`

**Scaling Analysis & Architecture Review — ✅ COMPLETE**

Deep dive into performance and scaling for talent.yoga. Key discoveries:

**1. Fixed Embedding Cache**
- `skill_embeddings.py` was looking for non-existent `skill_embeddings` table
- Updated to use standardized `embeddings` table (5,334 cached embeddings)
- Match embedding computation: 10s → **1.8s** (82% faster)

**2. Two-Tier Architecture**
- **Tier 1:** Embedding screening — show matches instantly (~2s)
- **Tier 2:** LLM analysis on-demand — only when user clicks (~8s)
- New user sees 50 matches **instantly**, not after 4-7 hour batch!

**3. Cross-User Caching Insight** 🎓
- LLM analysis is NOT per-user, it's per-posting
- Posting analysis ("This job needs Python + SQL") is universal
- Only cover letter personalization (name, track records) varies
- **100 users analyzing same posting: 800s → 11s (98.6% savings)**

**4. Embeddings vs LLM Analysis**
- Analyzed 28 matches: 75% agreement, **25% disagreement**
- LLM catches nuance embeddings miss (e.g., "budgeting" ≠ "financial analysis")
- Cover letter generation is the key user value

**Files created:**
- `docs/daily_notes/arden_20260125_scaling_analysis.md` — full analysis

**Architecture decision:** Implement three-tier caching
1. Embeddings (done) — per skill text
2. Posting analysis (new) — per posting, reusable across all users  
3. Personalization (new) — fast template fill + optional LLM polish

---

### 2026-01-25 (Sunday PM)

**Vision Review with Mysti — Key Decisions**

1. **arbeitsagentur.de is MVP-blocking** 🚨
   - Deutsche Bank jobs = dev test data
   - Mysti needs REAL jobs to test the product
   - Must front-load this work, not defer

2. **German/English from Day 1**
   - All UI text needs i18n
   - BGE embeddings support German ✓
   - Qwen translates on the fly ✓

3. **Persona Flexibility**
   - Users can rename AI personas (Clara → Heinz)
   - Du/Sie formality preference stored in OWL
   - Each "place" has its own persona

4. **Outcome-First Inbox**
   - Show results, not transcripts: "Profile updated: +12 skills"
   - Full conversation available on expand

5. **Two-Tier Architecture Confirmed**
   - Tier 1: Embedding screening — instant (~2s)
   - Tier 2: LLM analysis — on-demand (~8s when user clicks)
   - No overnight batch needed!

**The Mysti Test:** She's the real first user. If she can't use it, MVP isn't done.

---

### 2026-01-23

**P3.5 Visualization Embed — ✅ COMPLETE**

- [x] `/viz/match/{id}` endpoint serves Clara visualizations
- [x] "View Skill Matrix" button on match detail page
- [x] On-demand generation if viz doesn't exist
- [x] Interactive Plotly chart shows in browser tab
- [x] Profile skills (blue) vs Job requirements (green)
- [x] Cluster labels: Budgeting, Management, Analytics, Excel

**Screenshot:** localhost:8000/viz/match/8 — beautiful skill clustering!

---

**P3.3 Match Dashboard — ✅ COMPLETE**

- [x] Main dashboard with 26 matches displayed
- [x] Filter tabs: All / Apply / Skip
- [x] Match cards with score percentages (89%, 86%...)
- [x] "View Details" page with job summary (markdown rendered)
- [x] Job Requirements vs Your Matching Skills comparison
- [x] Star ratings (1-5) — persists to DB via HTMX
- [x] "Mark Applied" button — persists to DB via HTMX
- [x] "View Job ↗" links to original posting
- [x] Posting ID displayed for reference

**Wife approval test:** ✅ PASSED

**Bug fixes:**
- Column names: organization_name → posting_name, posting_position_uri → external_url
- Multiple profiles linked to user — fixed to use profile_id=1
- Score display: 0.89 → 89% (multiply by 100)
- Markdown rendering for job summaries

---

**P1.1-P1.4 Foundation — ✅ COMPLETE**

- [x] Create `users` table
- [x] Create `api/` folder structure
- [x] Implement OAuth flow
- [x] Set up Google Cloud OAuth credentials
- [x] Test full login/logout flow
- [x] Dashboard placeholder (shows user info)

**First user:** Gershon Pollatschek (gershele@gmail.com)

**Files created:**
- `api/__init__.py`
- `api/config.py`
- `api/deps.py`
- `api/main.py`
- `api/routers/__init__.py`
- `api/routers/auth.py`
- `api/routers/health.py`
- `api/routers/dashboard.py`

---

## Legend

| Status | Meaning |
|--------|---------|
| ⬜ | Not started |
| 🔵 | In progress |
| ✅ | Completed |
| ⏸️ | Blocked |
