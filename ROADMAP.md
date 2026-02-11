# ROADMAP.md - talent.yoga

*Last updated: February 11, 2026*

## The Vision

**talent.yoga** — Career navigation for Germany's labor market. Job matching based on skills, not keywords. Powered by Berufenet classification, OWL synonym registry, and Mira (AI career companion).

---

## Current State (Feb 2026)

| Metric | Count |
|--------|-------|
| Active postings | 205,054 |
| Berufenet-mapped | 165,946 (81%) |
| OWL synonym names | 31,354 |
| User profiles | 5 |
| Profile-posting matches | 28 |
| API routers | 27 |
| Test suite | 192 tests (all green) |
| PostgreSQL cache hit | 99.97% |

### Infrastructure
- **Stack:** Python 3.10 / FastAPI / PostgreSQL 14 / Ollama (qwen2.5:7b)
- **Server:** i5-13420H, 33 GB RAM, NVMe, RTX 3050 6GB
- **PG tuning:** shared_buffers=8GB, effective_cache_size=24GB (tuned Feb 11)
- **Pipeline:** Nightly fetch via `scripts/turing_fetch.sh` (cron 22:00)
- **Logging:** Structured JSON via `core.logging_config`

### Architecture
```
actors/     17 actors (7 class-based, 10 script-based)
api/        FastAPI app, 27 routers (mira split into 8-file package)
core/       Database, logging, text utils, error handler, circuit breaker
lib/        Berufenet matching, FAQ detection
frontend/   Jinja2 templates + static assets
tests/      8 test files, 192 tests (pytest)
```

---

## Active Work

### Nightly Pipeline (automated)
- [x] Arbeitsagentur fetch + dedup
- [x] Deutsche Bank fetch
- [x] External description scraping
- [x] Berufenet classification (embed + LLM triage)
- [x] OWL synonym resolution
- [x] Embedding generation
- [x] Qualification level backfill (cascade)
- [ ] Skills extraction (paused — waiting for pipeline redesign)

### Mira (AI Career Companion)
- [x] Bilingual chat (DE/EN) with language detection
- [x] Formality detection (du/Sie)
- [x] Tour onboarding flow
- [x] Greeting with context
- [x] Job search integration (intent detection → DB query)
- [x] Proactive engagement + consent flow
- [x] FAQ candidate detection
- [ ] Doug newsletter integration (actor exists, delivery TBD)
- [ ] Whats-new detection → surface pipeline results

### Matching
- [x] Profile-to-posting matching (basic)
- [x] Match confidence classification
- [x] Clara match report generation
- [ ] Match quality feedback loop
- [ ] Scale to all profiles

---

## Completed (Recent)

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
- [ ] **Profile builder UI** — let yogis create profiles in-app
- [ ] **Match notification** — email/push when new matches appear
- [ ] **Mira memory** — persist conversation context across sessions
- [ ] **Skills extraction v2** — actor redesign for 205k posting scale

### Medium Priority
- [ ] Multi-source job fetching (StepStone, LinkedIn scraping)
- [ ] Company intelligence (Glassdoor, kununu)
- [ ] Salary benchmarking from postings
- [ ] Search/filter UI for postings

### Technical Debt
- [ ] Dedupe postings at download time (check `external_job_id`)
- [ ] Pydantic V2 migration (suppress deprecation warnings)
- [ ] Test coverage for `core/database.py`, `core/navigator.py`
- [ ] CI pipeline (GitHub Actions)

### Future
- [ ] Multi-tenant support
- [ ] Public API for partners
- [ ] Mobile-responsive frontend
- [ ] Analytics dashboard for admins

---

## Key Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| Feb 11, 2026 | PG shared_buffers 8GB (25% RAM) | Cache hit 46% → 99.97% |
| Feb 11, 2026 | print→logging everywhere | Structured JSON logs, proper levels |
| Feb 11, 2026 | Test suite from scratch | 12 legacy tests were all broken pseudo-tests |
| Feb 11, 2026 | `pip install -e .` + pyproject.toml | Killed 18 `sys.path.insert` hacks |
| Jan 2026 | Berufenet as canonical taxonomy | German federal classification = ground truth |
| Dec 2025 | Queue-based actor architecture | Decoupled workers, crash recovery, idempotent |
| Dec 2025 | Skills in `posting_skills` table | Relational > JSON column for querying |

---

*This is a living document. Update it, don't let it rot.*
