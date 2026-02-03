# Arden's Cheat Sheet

*Last updated: 2026-02-02*

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

## The Pipeline (Jan 2026)

```
job_description → extracted_summary → extracted_requirements → posting_facets
```

| Stage | Actor | Input Column | Output Column |
|-------|-------|--------------|---------------|
| 1 | `postings__extracted_summary_U.py` | job_description | extracted_summary |
| 2 | `postings__extracted_requirements_U.py` | extracted_summary | extracted_requirements |
| 3 | `posting_facets__row_C.py` | extracted_requirements | posting_facets rows |

**Cascade Triggers:** Upstream change → downstream NULLed → archived to `attribute_history`

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
actors/postings__extracted_summary_U.py        # Summary extractor
actors/postings__extracted_requirements_U.py   # Requirements extractor  
actors/posting_facets__row_C.py                # CPS decomposer
core/pull_daemon.py                            # Execution daemon
tools/turing/turing-raq                        # RAQ testing tool
tools/turing/turing-dashboard                  # Live TUI + watchdog
docs/Turing_project_directives.md              # The Bible
```

---

## Key Views

| View | Purpose |
|------|---------|
| `posting_pipeline_status` | Shows stage + next_action for each posting |
| `attribute_history` | Archive of cascaded NULLs |

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

## What I've Learned (Recent)

### 2026-02-02: Berufenet & Qualification Levels (APPROVED)

**The Problem:** K-means on UMAP grouped Staplerfahrer (skilled, €15-18/hr) with Reinigungskraft (unskilled, minimum wage). Embeddings see "blue collar" but miss qualification dimension.

**The Solution:** Berufenet API from Bundesagentur für Arbeit.
- 3,562 official German professions
- KLDB2010 code's **last digit = qualification level**:
  - 1 = Helfer (no training)
  - 2 = Fachkraft (vocational)
  - 3 = Spezialist (advanced)
  - 4 = Experte (degree)

**API Details:**
```
Base: https://rest.arbeitsagentur.de/infosysbub/bnet/pc/v1/berufe
Auth: X-API-Key: infosysbub-berufenet
Search: ?suchwoerter=Staplerfahrer
Detail: /27448 → returns KLDB code
```

**Matching Strategy (Sandy-approved):**
1. Cache all 3,562 Berufenet professions + KLDB
2. Embed with BGE-M3
3. For each job title: top match > 0.85 → accept, else LLM decides
4. Add to domain_gate: `berufenet_id` + `qualification_level`

**Key Insight:** Qualification level becomes a **matching constraint** — never match a yogi at level N to jobs at level < N without consent. This is a launch blocker.

### 2026-02-02: Market Visualization
- Built `/market` page with 42K job postings on UMAP terrain
- Domain coloring from domain_gate classifier
- Auto-clustering for "unknown" jobs found data quality issues
- Dual-embedder consensus proposed (BGE-M3 + Qwen3) but Sandy says start simple

### 2026-01-19: Requirements Extractor
- Uses `extracted_summary` as input (not job_description)
- RAQ 20×3 = 100% match rate
- Cascade triggers auto-invalidate downstream when upstream changes
- Watchdog with circuit breaker enables safe overnight runs

### 2026-01-09: Accountability Produces Wisdom
When Sage was forced to justify every critique with quotes, she stopped hallucinating problems. The rule "if you can't prove it, don't list it" eliminated false positives.

---

## Cross-References

| Document | What It Covers |
|----------|----------------|
| [Turing_project_directives.md](Turing_project_directives.md) | Core principles, CPS model, all directives |
| [DEVELOPMENT_CHEAT_SHEET.md](DEVELOPMENT_CHEAT_SHEET.md) | Code patterns, actor checklist |
| [0000_talent_yoga_system_overview.md](0000_talent_yoga_system_overview.md) | System architecture, current metrics |
| [tools/turing/README.md](../tools/turing/README.md) | All turing-* tools |

---

*This is my working memory. Update it when I learn something new.*
