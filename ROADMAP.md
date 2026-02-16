# ROADMAP.md - talent.yoga

*Last updated: February 16, 2026*

## The Vision

**talent.yoga** — Career navigation for Germany's labor market. Job matching based on skills, not keywords. Powered by Berufenet classification, OWL synonym registry, and Mira (AI career companion).

---

## Current State (Feb 16, 2026)

| Metric | Count |
|--------|-------|
| Total postings | 242,444 |
| Active postings | 232,669 |
| Berufenet-mapped | 219,942 (91%) |
| Embeddings | 268,232 |
| OWL synonym names | 98,516 |
| User profiles | 6 |
| Profile-posting matches | 28 |
| API routers | 30 |
| Test suite | 354 tests (352 green, 2 skip: archived actor) |
| PostgreSQL cache hit | 99.97% |

### Infrastructure
- **Stack:** Python 3.10 / FastAPI / PostgreSQL 14 / Ollama (qwen2.5:7b + bge-m3)
- **Server:** i5-13420H, 33 GB RAM, NVMe, RTX 3050 6GB
- **PG tuning:** shared_buffers=8GB, effective_cache_size=24GB (tuned Feb 11)
- **Pipeline:** Nightly fetch via `scripts/turing_fetch.sh` (cron 23:50 CET)
- **Logging:** Structured JSON via `core.logging_config`
- **Services:** Ollama via systemd; FastAPI + Streamlit BI via @reboot cron (systemd units ready in `config/systemd/`)
- **Backups:** Daily incremental + weekly full USB backup; nightly PG dump; schema export at 03:05

### Architecture
```
actors/     17 actors (7 class-based, 10 script-based)
api/        FastAPI app, 30 routers (mira split into 8-file package)
core/       Database, logging, text utils, error handler, circuit breaker
lib/        Berufenet matching, FAQ detection
frontend/   Jinja2 templates + static assets
tests/      13 test files, 328 tests (pytest)
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

### Matching
- [x] Profile-to-posting matching (basic)
- [x] Match confidence classification
- [x] Clara match report generation
- [ ] Match quality feedback loop
- [ ] Scale to all profiles

### Frontend (ongoing)
- [x] Dark mode (full CSS fix, Feb 13-14)
- [x] Search results with detail modal + interest feedback
- [x] Journey tracker (3-column layout)
- [x] WhatsApp-style messages page (no sidebar)
- [x] Feedback widget (screenshot + annotation)
- [x] BI dashboard redirect (bi.talent.yoga)
- [x] Logon/logoff event rendering in messages
- [ ] Profile builder UI — let yogis create profiles in-app
- [ ] Search/filter UI for postings (UI exists, needs refinement)

---

## Completed (Recent)

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

### High Priority
- [x] **Pipeline alerting** — errors → Signal via signal-cli (lib/signal_notify.py)
- [ ] **Profile builder UI** — let yogis create profiles in-app
- [ ] **Match notification** — email/push when new matches appear
- [ ] **Mira memory** — persist conversation context across sessions
- [ ] **Skills extraction v2** — actor redesign for 242k posting scale
- [x] **CSS consolidation** — inline dark-mode styles merged into style.css (landscape, documents)

### Medium Priority
- [ ] Multi-source job fetching (StepStone, LinkedIn scraping)
- [ ] Company intelligence (Glassdoor, kununu)
- [ ] Salary benchmarking from postings
- [ ] User behavior intelligence (Mira proactive engagement based on click patterns)

### Technical Debt
- [ ] Dedupe postings at download time (check `external_id` — known duplicates exist)
- [ ] Pydantic V2 migration (suppress deprecation warnings)
- [ ] Test coverage for `core/database.py`, `core/navigator.py`
- [ ] CI pipeline (GitHub Actions)
- [ ] Systemd services installation (run `sudo bash config/systemd/install.sh`)
- [ ] Stale posting cleanup (invalidated postings still count in totals)

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

---

*This is a living document. Update it, don't let it rot.*
