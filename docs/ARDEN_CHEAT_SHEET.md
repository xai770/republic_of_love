# Arden's Cheat Sheet

*Last updated: 2026-02-11*

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

### 2026-02-11: Berufenet → OWL + Security Hardening

**OWL integration:** 3,561 berufenet entities + 11,746 owl_names. Actor rewritten: `--batch N` (Phase 1, OWL instant) + `--batch N --phase2` (embed+LLM discovery). Phase 2 now live in `turing_fetch.sh`. Auto-triage: 5,197 owl_pending processed (3,457 resolved, 1,740 rejected). Triage UI at `/admin/owl-triage`.

**Security:** Admin auth via `users.is_admin` + `_require_admin()` on all admin endpoints. Yogi OWL hierarchy (8 roles: admin/agent/free/pro/sustainer). Password rotated + scrubbed from 86 files. SECRET_KEY startup guard. 49 bare `except:` → specific types.

**Code quality:** `requirements.txt` rewritten (was linting-only). 11 stale `ty_wave` paths fixed. Duplicate `DBJobFetcher` renamed. Plan: [2026-02-11_berufenet_owl_integration.md](daily_notes/2026-02-11_berufenet_owl_integration.md)

### 2026-02-09: Mira Intelligence & Clara Qualification Gate

Mira: match quality gate (>30%), Doug newsletter wired in, persistent memory via `yogi_messages`. Clara: `check_qualification_gate()` uses KLDB levels as hard constraint — never match yogi level N to jobs level < N. NaN bug: bge-m3 on <150 char text → permanently exclude 4 postings.

### 2026-02-08: Nightly Pipeline Overhaul

Rewrote pipeline (now `turing_fetch.sh`) to 3 steps. All enrichment via `turing_daemon.py --run-once`. Domain gate promoted to actor (1303). Fixed infinite loop on NaN-failing embeddings (add `'failed'` to exclusion clause). `task_types` is a VIEW on `actors` — see schema note above.

---

## Cross-References

| Document | What It Covers |
|----------|----------------|
| [Turing_project_directives.md](Turing_project_directives.md) | Core principles, CPS model, all directives |
| [DEVELOPMENT_CHEAT_SHEET.md](DEVELOPMENT_CHEAT_SHEET.md) | Code patterns, actor checklist |
| [0000_talent_yoga_system_overview.md](0000_talent_yoga_system_overview.md) | System architecture, current metrics |
| [tools/turing/README.md](../tools/turing/README.md) | All turing-* tools |
| [20260208_product_roadmap_reset.md](daily_notes/20260208_product_roadmap_reset.md) | UX roadmap, Mira memory architecture, sidebar features |

---

*This is my working memory. Update it when I learn something new.*
