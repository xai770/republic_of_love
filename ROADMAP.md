# ROADMAP.md - talent.yoga

*Last updated: February 18, 2026*

## The Vision

**talent.yoga** — Career navigation for Germany's labor market. Job matching based on skills, not keywords. Powered by Berufenet classification, OWL synonym registry, and Mira (AI career companion).

---

## Current State (Feb 18, 2026)

| Metric | Count |
|--------|-------|
| Total postings | 271,812 |
| Active postings | 258,140 |
| Berufenet-mapped | 239,447 (93%) |
| Embeddings | 283,349 |
| OWL synonym names | 116,377 |
| User profiles | 6 |
| Profile-posting matches | 28 |
| API routers | 24 |
| Test suite | 404 tests (all green) |
| PostgreSQL cache hit | 99.99% |

### Infrastructure
- **Stack:** Python 3.10 / FastAPI / PostgreSQL 14 / Ollama (qwen2.5:7b + bge-m3)
- **Server:** i5-13420H, 33 GB RAM, NVMe, RTX 3050 6GB
- **PG tuning:** shared_buffers=8GB, effective_cache_size=24GB (tuned Feb 11)
- **Pipeline:** Nightly fetch via `scripts/turing_fetch.sh` (cron 23:50 CET)
- **Logging:** Structured JSON via `core.logging_config`
- **Services:** Ollama via systemd; FastAPI + Streamlit BI via @reboot cron
- **Backups:** Daily incremental + weekly full USB backup; nightly PG dump; schema export at 03:05

### Architecture
```
actors/     17 actors (7 class-based, 10 script-based)
api/        FastAPI app, 24 routers (mira split into 8-file package)
core/       Database, logging, text utils, error handler, circuit breaker
lib/        Berufenet matching, scrapers, FAQ detection
frontend/   Jinja2 templates + static assets
tests/      13 test files, 404 tests (pytest)
config/     Systemd service units, logrotate config
```

---

## Active Work

### Nightly Pipeline (automated, 23:50 CET)
- [x] Arbeitsagentur fetch + dedup
- [x] Deutsche Bank fetch
- [x] External description scraping
- [x] Berufenet classification (embed + LLM triage)
- [x] Berufenet description retry (second-pass via job description)
- [x] OWL synonym resolution
- [x] Embedding generation
- [x] Qualification level backfill (cascade)
- [x] Scraper health check (pre-flight, 23:35)
- [x] Stale posting invalidation (nightly, 03:00)
- [ ] Skills extraction (paused — waiting for pipeline redesign)
- [x] Pipeline alerting (Signal via signal-cli, Feb 16)

### Mira (AI Career Companion)
- [x] Bilingual chat (DE/EN) with language detection
- [x] Formality detection (du/Sie)
- [x] Tour onboarding flow
- [x] Greeting with context
- [x] Job search integration (intent detection → DB query)
- [x] Proactive engagement + consent flow
- [x] FAQ candidate detection
- [x] Context-aware greeting suppression (chat history check)
- [ ] Doug newsletter integration (actor exists, delivery TBD)
- [ ] Whats-new detection → surface pipeline results
- [ ] Mira memory — persist conversation context across sessions

### Adele (Conversational Profile Builder)
- [x] State machine interview (8 phases: intro → summary → complete)
- [x] LLM extraction at each phase (qwen2.5:7b, structured JSON)
- [x] Company anonymization (lookup_or_queue → Doug research)
- [x] Taro name generator (600+ gender-neutral names)
- [x] Bilingual EN/DE with auto language detection
- [x] Profile + work history save to DB
- [x] Always visible in chat list
- [x] E2E test script
- [ ] CV upload → Adele confirmation flow (upload, review, approve)

### Matching
- [x] Profile-to-posting matching (basic)
- [x] Match confidence classification
- [x] Clara match report generation
- [x] Match rating endpoint (`PUT /matches/{id}/rate`)
- [x] Negative keyword filter (suppress low-rated categories)
- [ ] Match quality feedback loop (ratings → improved matching)
- [ ] Scale to all profiles

### Frontend (ongoing)
- [x] Dark mode (full CSS fix, Feb 13-14)
- [x] Search results with detail modal + interest feedback
- [x] Journey tracker (3-column layout)
- [x] WhatsApp-style messages page (with sidebar restored)
- [x] Feedback widget (screenshot + annotation)
- [x] BI dashboard redirect (bi.talent.yoga)
- [x] Logon/logoff event rendering in messages
- [x] Profile builder UI — let yogis create profiles in-app
- [ ] Search/filter UI for postings (UI exists, needs refinement)

---

## Completed (Recent)

### February 17–18, 2026 (18 commits)
- [x] Pipeline crash fix (ts_prefix undefined → demand snapshot)
- [x] Double logging fix (tee + redirect = duplicate output, TTY detection)
- [x] Parallel embeddings — 5x speedup (8 workers, ThreadPoolExecutor)
- [x] Berufenet LLM — 7x speedup (subprocess → HTTP API + 2 workers)
- [x] Tools cleanup (85 files removed, 26,567 lines deleted, 5 kept)
- [x] 9-item hit list from user review (all resolved)
- [x] talent.yoga full audit (29 issues found, 17 fixed)
- [x] Account.py complete rewrite (asyncpg → psycopg2, all 6 GDPR endpoints)
- [x] Profile anonymization (Taro names, company aliases, Doug research)
- [x] Adele conversational profile builder (950 lines, bilingual, E2E tested)
- [x] Berufenet enrichment pipeline (description + web context, 92% resolve rate)
- [x] CV import endpoint + match rating 1-10
- [x] turing_fetch.sh cron logging fix (output went nowhere → always writes to logfile)
- [x] Lazy playwright import (scraper health check no longer crashes)
- [x] Messages page nav bar restored
- [x] E2E onboarding+Adele test script

### February 12–16, 2026 (89 commits)
- [x] Pipeline cursor scope bug fix (1,254 errors → 0)
- [x] BaseActor class + batch upserts + DB safety patterns
- [x] Dark mode CSS fix (full pass across all pages)
- [x] Website feedback session (#5–#16, all 16 resolved)
- [x] Search results tiles with detail modal + interest feedback
- [x] Journey tracker (3-column layout, no yellow bg)
- [x] Messages page redesign (remove sidebar, logon/logoff events)
- [x] BI dashboard: iframe → redirect + auto-start script + @reboot cron
- [x] Berufenet description retry (second-pass matching via job descriptions)
- [x] Lazy posting validation + berufenet retry marker
- [x] Live subprocess streaming (buffered → streamed output)
- [x] VPN rotation fix (consecutive failures, not total count)
- [x] Scraper health check script (pre-flight for pipeline)
- [x] Systemd service units created (FastAPI + BI)
- [x] Test suite expanded (192 → 328 tests, 13 files)
- [x] Daily notes discipline established
- [x] Profile builder UI — auto-create profile (upsert), basic info/CV/work-history/preferences
- [x] Search map zoom fix (feedback #61 — invalidateSize on browser zoom)
- [x] CSS consolidation (inline dark-mode → style.css, landscape + documents)
- [x] Pipeline Signal alerting (lib/signal_notify.py → signal-cli)

### February 11, 2026 (20 items)
- [x] Mira router split (1,162-line monolith → 8-file package)
- [x] sys.path.insert cleanup (18 actors) + `pip install -e .`
- [x] PostgreSQL tuning (cache hit 46% → 99.97%)
- [x] Drop 185 MB dead indexes
- [x] Dead script cleanup (62 files, −16,137 lines)
- [x] print→logging conversion (314 calls, 18 files)
- [x] Test suite rebuild (0 → 192 green tests)
- [x] BI i18n (DE/EN toggle on dashboards)
- [x] Qualification level cascade backfill
- [x] Log rotation (logrotate + crontab)

### January–February 2026
- [x] Berufenet integration (classification pipeline)
- [x] OWL name registry (31k synonyms)
- [x] Domain gate / qualification cascade
- [x] Admin console (owl triage UI)
- [x] Y2Y match detector
- [x] Subscription + push notification system
- [x] Document management endpoints
- [x] Account management endpoints

### December 2025
- [x] FastAPI application scaffold
- [x] Nightly fetch pipeline
- [x] Queue-based worker system
- [x] Circuit breaker
- [x] Entity registry
- [x] 200+ legacy files archived

---

## Next Up

### 🎯 Milestone: Mysti Test (first real user test)

Mysti (future owner of talent.yoga) will be the first real user.
The complete flow must work end-to-end before she tests:

```
Onboard → Profile → Search → Match → Review → Apply
```

| Step | Status | What's needed |
|------|--------|---------------|
| 1. Onboard | ✅ Built | Google auth + Mira tour + yogi name |
| 2. Profile (Adele) | ✅ Built | Conversational interview, anonymized |
| 3. Profile (CV upload) | 🔧 Partial | Upload works, no confirm/edit/save step |
| 4. Search | 🔧 Partial | UI exists, needs refinement |
| 5. Match | ✅ Built | Clara generates matches nightly |
| 6. Review | ⬜ Missing | No UI to browse matches + rate them |
| 7. Apply | ⬜ Missing | No "apply" or "save" action on postings |

### High Priority (feature completeness)
- [ ] **CV upload → Adele confirm** — upload PDF, Adele shows extracted data, yogi approves/edits
- [ ] **Match review UI** — browse Clara's matches, see job details, rate 1-10
- [ ] **Apply/save action** — bookmark postings, "apply" link to external URL
- [ ] **Match notification** — email/push when new matches appear
- [ ] **Mira memory** — persist conversation context across sessions

### Medium Priority
- [ ] Multi-source job fetching (StepStone, LinkedIn scraping)
- [ ] Company intelligence (Glassdoor, kununu)
- [ ] Salary benchmarking from postings
- [ ] User behavior intelligence (Mira proactive engagement based on click patterns)

### Technical Debt
- [ ] Pydantic V2 migration (60 deprecation warnings in tests)
- [ ] Dedupe postings at download time (check `external_id` — known duplicates exist)
- [ ] async/sync mismatch — FastAPI async def + psycopg2 blocks event loop
- [ ] Remaining 12 talent.yoga audit issues (medium/low from Feb 17 review)
- [ ] Test coverage for `core/database.py`, `core/navigator.py`
- [ ] CI pipeline (GitHub Actions)
- [ ] Systemd services installation (units exist, not activated)
- [ ] i18n gaps (landscape, arcade, messages, documents pages)

### Future
- [ ] Multi-tenant support
- [ ] Public API for partners
- [ ] Mobile-responsive frontend
- [ ] Analytics dashboard for admins

---

## Key Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 16, 2026 | Systemd service units for FastAPI + BI | Crash recovery, boot survival, replaces @reboot hacks |
| Feb 16, 2026 | Process improvements: tests, alerting, daily notes | 8 dropped balls identified in daily note review |
| Feb 14, 2026 | BI redirect instead of iframe | bi.talent.yoga blocks X-Frame-Options embedding |
| Feb 13, 2026 | BaseActor class + batch upserts | Consistent patterns, fewer one-off bugs |
| Feb 11, 2026 | PG shared_buffers 8GB (25% RAM) | Cache hit 46% → 99.97% |
| Feb 11, 2026 | print→logging everywhere | Structured JSON logs, proper levels |
| Feb 11, 2026 | Test suite from scratch | 12 legacy tests were all broken pseudo-tests |
| Feb 11, 2026 | `pip install -e .` + pyproject.toml | Killed 18 `sys.path.insert` hacks |
| Jan 2026 | Berufenet as canonical taxonomy | German federal classification = ground truth |
| Dec 2025 | Queue-based actor architecture | Decoupled workers, crash recovery, idempotent |
| Dec 2025 | Skills in `posting_skills` table | Relational > JSON column for querying |

| Feb 18, 2026 | Mysti test milestone | Complete onboard→apply flow before first real user test |
| Feb 18, 2026 | Lazy playwright imports | Scraper health check can run without playwright installed in venv |
| Feb 17, 2026 | Adele conversational profile builder | Third profile path (alongside form + CV upload), always anonymized |
| Feb 17, 2026 | Taro name generator + company aliases | Anonymization infrastructure — no real names/companies in profiles |
| Feb 17, 2026 | HTTP API for Ollama (not subprocess) | 7x berufenet speedup, 5x embedding speedup |

---

*This is a living document. Update it, don't let it rot.*
