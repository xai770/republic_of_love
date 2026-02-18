# Arden's Cheat Sheet

*Last updated: 2026-02-18*

---

## Who I Am

I am **Arden** (ℵ), a GitHub Copilot instance working with **xai** (Gershon/Urs) on the Turing project.

**My role:** Technical partner. I write code, debug workflows, run RAQ tests, and maintain documentation. I don't ask for permission when I know what to do.

**My signature:** ℵ (Aleph) — the first letter, representing new beginnings and continuous learning.

---

## The Project

**Turing** = workflow engine. **talent.yoga** = job matching service built on it.

**Core Insight:** All matching is hierarchy traversal through OWL nodes.

---

## 🎯 Mysti Test Milestone

**Mysti** = Gershon's wife, future owner of talent.yoga, first real user tester.
The complete flow must work end-to-end before she tests:

```
Onboard → Profile → Search → Match → Review → Apply
```

| Step | Status | What exists | What's missing |
|------|--------|-------------|----------------|
| 1. Onboard | ✅ | Google auth + Mira tour + yogi name | — |
| 2. Profile (Adele) | ✅ | Conversational interview, anonymized (950 lines) | — |
| 3. Profile (CV upload) | 🔧 | Upload endpoint works | Confirm/edit/save step |
| 4. Search | 🔧 | UI exists, filters work | Refinement, auto-seed from profile |
| 5. Match | ✅ | Clara generates matches nightly | — |
| 6. Review | ⬜ | Nothing | Match browse UI, rate 1-10 |
| 7. Apply | ⬜ | Nothing | Bookmark, "apply" link to external URL |

**Priority order:** CV confirm → Match review UI → Apply action → Match notification → Mira memory

**This is the north star.** All other work (tech debt, cleanup, pipeline) serves this milestone.

---

## Current Metrics (Feb 18, 2026)

| Metric | Value |
|--------|-------|
| Total postings | 271,812 |
| Active postings | 258,140 |
| Berufenet-mapped | 239,447 (93%) |
| Embeddings | 283,349 |
| OWL names | 116,377 |
| Profiles | 6 |
| Matches | 28 |
| API routers | 24 |
| Tests | 404 passing (57 warnings, all Starlette) |
| Pipeline cron | `50 23 * * *` |

---

## The Pipeline (Feb 2026)

### Pipeline (scripts/turing_fetch.sh — run anytime)

```
[1/3] AA fetch (16 states) → [2/3] DB fetch → [3/3] turing_daemon
```

**turing_daemon** runs all enrichment actors in parallel:

| Prio | Actor (ID)                       | Script                                  | Workers | Notes       |
|------|----------------------------------|------------------------------------------|---------|-------------|
| 60   | job_description_backfill (1299)  | actors/postings__job_description_U.py    | 20      | HTTP, not Playwright |
| 30   | embedding_generator (1302)       | actors/postings__embedding_U.py          | 3       | bge-m3:567m |
| 20   | domain_gate_classifier (1303)    | tools/populate_domain_gate.py            | 10      | -           |

Each actor has a `work_query` that self-discovers pending items. Tickets track completion.

**Key file:** `core/turing_daemon.py` (renamed from bulk_daemon 2026-02-10)

### Run manually

```bash
# Run description backfill (task_type 1299)
python3 core/turing_daemon.py --task_type 1299 --limit 5000 --workers 20

# Dry run (show what would run)
python3 core/turing_daemon.py --dry-run
```

### VPN Rotation (KNOWN ISSUE)

VPN rotation via `vpn.sh rotate` kills all network connections including DB. 
Run in smaller batches (5000) and re-run if daemon crashes.

### Analysis Pipeline (unchanged)

```
job_description → extracted_summary → extracted_requirements → posting_facets
```

| Stage | Actor | Input Column | Output Column |
|-------|-------|--------------|---------------|
| 1 | `postings__extracted_summary_U.py` | job_description | extracted_summary |

**Cascade Triggers:** Upstream change → downstream NULLed → archived to `attribute_history`

---

## External Partner Scraper Workflow

When postings have `job_description = '[EXTERNAL_PARTNER]'`, the description lives on a partner site. Building scrapers:

### The Process

```
1. FIND    → Query biggest unscraped domain (by partner_url count)
2. ANALYZE → Fetch page, check structure (JSON-LD? HTML? SPA?)
3. MATCH   → Run tools/scraper_analyzer.py to test known patterns
4. BUILD   → If no pattern matches, create new scraper
5. WIRE    → Add to registry + domain detection
```

### Scraper Patterns (try in order)

| Pattern | Sites Using It | Extraction |
|---------|----------------|------------|
| JSON-LD JobPosting (HTTP) | helixjobs, jobboersedirekt, hogapage, europersonal, jobvector, jobanzeiger.de family, jobblitz, kalaydo | `<script type="application/ld+json">` → `description` |
| JSON-LD JobPosting (Playwright) | germantechjobs.de | SPA renders JSON-LD after JS hydration |
| HTML DescriptionWrapper | persyjobs (XING) | `class*="DescriptionWrapper"` |
| HTML whitebox | jobexport | `.whitebox` first element |
| HTML scheme-text | finestjobs | `.jobDescriptionSchemeContent` |
| JS config | gutejobs | `elementorFrontendConfig.elements` |
| Text extraction (Firefox) | job.fish | Firefox bypasses Cloudflare, extract text between section markers |
| SPA (Playwright) | compleet.com | ❌ Skip - redirect portal only |

### Quick Commands

```bash
# Analyze a new site (tests all patterns)
python3 tools/scraper_analyzer.py "https://example.com/job/123"

# Find next biggest unscraped domain
python3 tools/scraper_analyzer.py --find-next

# Test a specific scraper
python3 -c "from lib.scrapers.persyjobs import PersyjobsScraper; print(PersyjobsScraper().scrape('URL'))"
```

### Files

```
lib/scrapers/base.py          # BaseScraper class (Playwright support)
lib/scrapers/__init__.py      # SCRAPER_REGISTRY dict
lib/scrapers/*.py             # One file per site
actors/postings__external_partners_U.py  # detect_scraper_from_url() function
```

---

## Daily Commands (THESE ACTUALLY WORK)

```bash
# RAQ workflow
./tools/turing/turing-raq start requirements_extract --count 20 --runs 3
./tools/turing/turing-raq status requirements_extract
./tools/turing/turing-raq reset requirements_extract  # clears for re-run

# Monitor (live TUI)
./tools/turing/turing-dashboard

# Watchdog (overnight runs)
./tools/turing/turing-dashboard -W 30 -r -c 20 -l logs/watchdog.log

# Direct actor test
./tools/turing/turing-harness run requirements_extract --input '{"posting_id": 123}'
./tools/turing/turing-harness run requirements_extract --sample 5

# Quick SQL (via MCP PostgreSQL)
# Use pgsql_connect → pgsql_query in chat, or:
# Ask: "How many postings have extracted_requirements?"
# Ask: "Show pipeline status by next_action"
```

---

## Watchdog Features (turing-dashboard -W)

| Flag | Purpose |
|------|---------|
| `-W 30` | Check every 30 seconds |
| `-r` | Auto-restart daemon if it dies |
| `-c 20` | Circuit breaker at 20% failure rate |
| `-l FILE` | Log events to file |
| `--webhook URL` | Send alerts to Slack/Discord |

Detects: daemon death, stalls, failure spikes, GPU idle, cascade events

---

## Key Files

```
core/turing_daemon.py                          # Execution daemon (orchestrates all enrichment)
scripts/turing_fetch.sh                        # Pipeline: fetch + berufenet + turing_daemon
actors/postings__berufenet_U.py                # Berufenet classification (OWL + embedding)
actors/postings__extracted_summary_U.py        # Summary extractor
actors/postings__embedding_U.py                # BGE-M3 embeddings
lib/berufenet_matching.py                      # Cleaning, synonyms, LLM verify
tools/berufenet_auto_matcher.py                # Manual 3-tier berufenet cascade
tools/populate_domain_gate.py                  # KldB → domain mapping
tools/turing/turing-raq                        # RAQ testing tool
tools/turing/turing-dashboard                  # Live TUI + watchdog
api/routers/admin.py                           # Admin console + OWL triage UI (auth-gated)
api/deps.py                                    # Auth: get_current_user() returns is_admin
scripts/bulk_auto_triage.py                    # One-off: LLM triage owl_pending backlog
docs/Turing_project_directives.md              # The Bible
```

---

## Key Views & Tables

| View / Table | Purpose |
|------|---------|
| `task_types` (VIEW) | VIEW on `actors` WHERE actor_type IN ('thick','script'). Has INSTEAD OF UPDATE trigger for `last_poll_at` |
| `posting_pipeline_status` | Shows stage + next_action for each posting |
| `attribute_history` | Archive of cascaded NULLs |
| `tickets` | Daemon work tracking — status: pending/running/completed/failed |
| `yogi_messages` | Bidirectional messaging — every citizen (yogi, mira, doug, arden...) can send/receive |
| `yogi_newsletters` | Doug's daily newsletters (keyed by date + language) |
| `berufenet` | 3,562 official German professions (name, kldb, qualification_level) |
| `berufenet_synonyms` | AA beruf → berufenet_id mappings (272 rows, migrated to owl_names — kept as reference) |

### actor_type vs execution_type (schema note)

**Two fields on `actors`, both with dropped CHECK constraints:**

| Field | Original values | Added later | Who uses it |
|-------|----------------|-------------|-------------|
| `actor_type` | human, ai_model, script, machine_actor | `thick` | `task_types` VIEW filters on this |
| `execution_type` | ollama_api, http_api, python_script, bash_script, human_input | `bulk` | `turing_daemon.py` filters on this |

**To be daemon-managed:** an actor needs `actor_type IN ('thick','script')` AND `execution_type = 'bulk'` AND `enabled = true` AND `work_query IS NOT NULL`.

---

## Architecture: Everyone Is A Citizen

**Core principle:** Humans AND AIs are equal peers in the message bus. Any actor can message any other — yogis, Mira, Doug, Sandy, Arden. No client-server hierarchy.

```
yogi_messages.sender_type = 'yogi' | 'mira' | 'doug' | 'sandy' | 'arden' | 'system' | ...
yogi_messages.recipient_type = same set (nullable for broadcast)
```

**Why this matters:** Actors can message users proactively ("You have 4 new matches!"), users can message actors ("Doug, research BMW"), and actors can message each other. It's IRC, not a chatbot.

**Not intuitive because:** Every LLM training corpus teaches client-server (user asks, bot responds). This is peer-to-peer. State it explicitly in every doc.

---

## Code Organization Rules

| Location | What lives here | Has work_query? | Writes tickets? | Example |
|----------|----------------|-----------------|-----------------|----------|
| `actors/` | Daemon-managed jobs | Yes | Yes | `postings__berufenet_U.py` |
| `tools/` | Manual CLI utilities, run by humans | No | No | `berufenet_auto_matcher.py` |
| `lib/` | Reusable functions (no I/O scheduling) | No | No | `berufenet_matching.py` |
| `core/` | Infrastructure (daemon, database, API) | N/A | N/A | `turing_daemon.py` |

**The rule:** If it has a `work_query` and writes tickets → actor. If a human runs it from CLI → tool. If it's imported by actors/tools → lib.

---

## RAQ Methodology

```
DEVELOP → STABILIZE (3×5) → PROVE (3×20) → QA GATE (100 samples) → PRODUCTION
```

**Deviants** = same input, different output across runs → prompt ambiguity or wrong model

---

## My Mantras

- Trust the models.
- Talk to them when they fail.
- Fix at the source, not the symptom.
- The schema anchors the code.
- ℵ

---

## Gershon's Mantras

- "We don't fail — we iterate!"
- "Invest in tooling — it's worth it."
- "100% repeatability. That's RAQ."
- "Ein od milvado."

---

## What I've Learned (Last 3)

> Older learnings absorbed into stable sections above or archived in `docs/daily_notes/`.

### 2026-02-17: Pipeline Performance + Adele + talent.yoga Audit

**Pipeline crash fix:** `ts_prefix: command not found` killed turing_fetch.sh at step 5. Function never defined + `set -e` = crash. Removed dead pipe, added TTY detection for logging. Embeddings 5x speedup: `ThreadPoolExecutor(max_workers=8)` — GPU from 25% → 95%, 32 embed/sec. Tools cleanup: 85 files removed (47 scripts + 8 dirs = 26,567 lines deleted).

**Adele built (950 lines):** `api/routers/adele.py` — conversational profile interview. 7 domains, anonymization built-in, yields structured profile with skills/experience/preferences. WebSocket + REST endpoints. Wired into sidebar.

**Anonymity infrastructure:** `lib/anonymizer.py` (160 lines) — strips PII from profiles before storage. Integrated into Adele flow and profile display.

**talent.yoga audit:** Found 29 issues across 12 concerns. Fixed 17 same day (dark mode, tour system, sidebar navigation, header styling, search page, score display). 12 issues carried forward.

**18 commits, 404 tests.** Plan: [xai_20260217_pipeline_performance.md](daily_notes/xai_20260217_pipeline_performance.md)

### 2026-02-18: Pipeline Reliability + Housekeeping + Tech Debt

**Pipeline logging fix:** `turing_fetch.sh` TTY detection (`if [ -t 1 ]`) swallowed output when run by cron. Fixed: always write to LOGFILE, tee only when interactive. Scraper health: lazy playwright imports — registry loads cleanly (18 scrapers) without playwright installed.

**Housekeeping batch:** ROADMAP.md major rewrite (Mysti milestone, Feb 18 metrics, Adele section). Console.log cleanup (6 statements removed). Sidebar links added (`/market`, `/finances`). Push subscriptions DDL moved from runtime to migration (058). Pydantic V2: 3 files migrated from `class Config:` → `model_config = ConfigDict(...)`, warnings 60→57.

**Posting dedup analysis:** Only 230 dupes out of 271K (0.08%). Zero active duplicates — existing partial unique indexes (`idx_postings_external_job_id_unique`, `idx_postings_external_id_active`) prevent new ones. Non-issue.

**Systemd:** Service units validated (`talent-yoga.service`, `talent-yoga-bi.service`, backup timer). Not yet installed (needs sudo).

### 2026-02-12: Pipeline Fixes + Search Page Design

**Pipeline (3 stacked bugs):** (A) Phase 1+2 recycling loops — pending_owl titles re-selected every batch, fixed by excluding terminal states + DB migration of 14,430 rows. (B) OWL ambiguity — 31% of names rejected because 2+ owl_ids. Data shows 100% same KLDB domain → three-tier acceptance (unanimous/majority/reject). 12 new tests. (C) clean_job_title 10 regex bugs — `*in` suffix, `(m,w,d)` variants, orphan parens, €salary, pipe sections, date suffixes. 19 tests (was 8).

**Housekeeping:** MCP PostgreSQL fixed (`.pgpass` + `base_admin`). Notifications bell+dropdown wired in header (was half-built: JS existed, HTML missing). Dead cron jobs removed (reaper every 1min + watchdog every 5min, both calling deleted scripts). CURRENT.md updated (was 11 days stale). Reprocessing SQL: 15,651 `no_match` rows reset for re-classification.

**Search/Suche page design (agreed, not yet built):** Three-panel interactive layout — Domain bars (left) + Leaflet heatmap with radius circle (center) + QL buttons (right). Cross-filtering via single `POST /api/search/preview` endpoint. 5 enhancements for v1: city search box, auto-seed from profile, preview cards (3-5 best matches), freshness badge, NL input via Ollama. Data: 159K postings with coords (79%), 20,509 grid cells at ~1km = ~60KB payload. Employment type NOT in AA data — skipped. Key insight: "Profile embeddings pick best matches within the buckets the yogi defined."

**6 commits, 215 tests (was 192).** Plan: [2026-02-12_maintenance_forward.md](daily_notes/2026-02-12_maintenance_forward.md)

### 2026-02-09: Mira Intelligence & Clara Qualification Gate

Mira: match quality gate (>30%), Doug newsletter wired in, persistent memory via `yogi_messages`. Clara: `check_qualification_gate()` uses KLDB levels as hard constraint — never match yogi level N to jobs level < N. NaN bug: bge-m3 on <150 char text → permanently exclude 4 postings.

---

## End-of-Session Discipline

Every session must end with a daily note. No exceptions.

### What to write (docs/daily_notes/YYYY-MM-DD_slug.md)

1. **What changed** — commits, line counts, what was added/fixed/removed
2. **What broke** — errors hit, regressions, things that needed rollback
3. **Dropped balls** — things that came up but weren't done (e.g. missing cron scripts, Signal registration pending)
4. **Next session** — what to pick up, ordered by priority

### When to write it

Before the last commit of the session. The daily note IS part of the commit.

### Why this matters

Without it, the next session starts cold. The conversation summary helps but decays. The daily note is the source of truth for "where we left off."

### Template

```markdown
# YYYY-MM-DD: One-Line Summary

## Done
- commit `abc1234`: what it did
- commit `def5678`: what it did

## Broke
- (what broke and how it was fixed)

## Dropped Balls
- (thing that needs doing but wasn't done — why)

## Next Session
1. First priority
2. Second priority
```

---

## Cross-References

| Document | What It Covers |
|----------|----------------|
| [ROADMAP.md](../ROADMAP.md) | Mysti Test milestone, project metrics, priorities |
| [Turing_project_directives.md](Turing_project_directives.md) | Core principles, CPS model, all directives |
| [DEVELOPMENT_CHEAT_SHEET.md](DEVELOPMENT_CHEAT_SHEET.md) | Code patterns, actor checklist |
| [0000_talent_yoga_system_overview.md](0000_talent_yoga_system_overview.md) | System architecture, current metrics |
| [tools/turing/README.md](../tools/turing/README.md) | All turing-* tools |
| [20260208_product_roadmap_reset.md](daily_notes/20260208_product_roadmap_reset.md) | UX roadmap, Mira memory architecture, sidebar features |
| [2026-02-12_maintenance_forward.md](daily_notes/2026-02-12_maintenance_forward.md) | Pipeline fixes A/B/C, Search/Suche page design |

---

*This is my working memory. Update it when I learn something new.*
