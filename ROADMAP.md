# ROADMAP.md - Turing Ecosystem

*Last updated: December 11, 2025*

## The Vision

**Turing** is the universal workflow engine. It orchestrates humans, AI, and scripts.

The `.yoga` products are **applications** that run on Turing:
- **talent.yoga** - Career navigation (job analysis, skills, matching)
- **news.yoga** - News intelligence (TBD)
- **contract.yoga** - Contract analysis (TBD)

---

## Current Focus: talent.yoga

### Active Work (December 2025)
- [x] Skills extraction pipeline (workflow 3001)
- [x] IHL scoring (human-in-loop)
- [ ] Skills extraction complete (711/1753 = 41%) ← ETA Dec 12 ~02:00
- [ ] IHL scoring complete (1708/1753 = 97%) ← ETA Dec 11 ~22:00
- [ ] **THEN:** Entity registry cleanup (workflow 3005) - 48 orphan skills
- [ ] Profile-to-job matching

### Queue Status
```
3001 running: skills_extraction (1042), ihl_analyst (45)
3005 queued:  Run after 3001 completes (not queue-based, runs standalone)
```

### Next Up
- [ ] Candidate profile import
- [ ] Skills matching algorithm
- [ ] Match scoring dashboard
- [ ] Application narrative generation

### Backlog
- [ ] Multi-source job fetching (RemoteOK, LinkedIn, etc.)
- [ ] Company intelligence integration
- [ ] Salary benchmarking
- [ ] Legal documentation generator

---

## Turing Engine - Core Improvements

### Recently Completed
- [x] Universal `turing.py` dashboard
- [x] Queue-based worker system
- [x] Wave processing (GPU optimization)
- [x] Circuit breaker (failure protection)
- [x] Codebase cleanup (Dec 11)

### Planned
- [ ] Multi-workflow support (run skills + IHL in parallel)
- [ ] Better retry/backoff for failed items
- [ ] Metrics export (Prometheus?)
- [ ] Admin GUI improvements (Streamlit)

### Technical Debt
- [ ] Dedupe postings at download time (check `external_job_id` before insert)
- [ ] Skip duplicate postings in interrogator before they enter pipeline

### Future
- [ ] Web API for external access
- [ ] Multi-tenant support
- [ ] Workflow designer UI
- [ ] Plugin system for new actors

---

## Product Pipeline

### 1. talent.yoga (NOW)
**Status:** MVP in development
**Focus:** Job posting analysis for Gershon's immediate needs → scale to 2M unemployed

### 2. news.yoga (PLANNED)
**Concept:** News analysis and intelligence
**Dependencies:** Turing entity registry, extraction patterns

### 3. contract.yoga (CONCEPT)
**Concept:** Contract analysis and risk assessment
**Dependencies:** Document processing, legal templates

---

## Session Handoff Protocol

When ending a session, update:
1. This ROADMAP.md with completed items
2. Any blocking issues in ISSUES.md (if exists)
3. The context summary for next AI session

When starting a session:
1. Run `./scripts/turing.py --status` to see current state
2. Read this ROADMAP.md for context
3. Check `git log --oneline -10` for recent changes

---

## Key Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Job postings processed | 1,753 | 10,000+ |
| Skills extracted | 711 | 1,753 |
| IHL scores | 1,708 | 1,753 |
| Profiles imported | 1 | 100+ |
| Matches generated | 0 | 1,000+ |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Dec 11, 2025 | Archived 200+ legacy files | Clean codebase for AI navigation |
| Dec 11, 2025 | Skills stored in `posting_skills` table | Relational > JSON column |
| Dec 7, 2025 | Queue-based architecture | Decoupled workers, crash recovery |

---

*This is a living document. Update it, don't let it rot.*
