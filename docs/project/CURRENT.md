# CURRENT — talent.yoga Sprint Tracker

**Last updated:** 2026-02-12 morning by Arden

---

## 🔥 TODAY

| Task | Owner | Status |
|------|-------|--------|
| Reprocessing SQL (15,651 no_match rows) | Arden | ready — waiting for fetch batch |
| Dashboard discussion | Sandy+Arden | next |

---

## ✅ DONE (Recent)

| Task | Owner | Completed |
|------|-------|-----------|
| clean_job_title 10 regex bugs fixed | Arden | 2026-02-12 |
| Three-tier owl_lookup (accept ambiguous OWL names) | Arden | 2026-02-12 |
| Phase 2 recycling loop fix + migrate 14,430 rows | Arden | 2026-02-12 |
| Phase 1 recycling loop fix | Arden | 2026-02-12 |
| Log-level bug fix (berufenet + aa_backfill) | Arden | 2026-02-12 |
| MCP PostgreSQL connection fixed | Arden | 2026-02-12 |
| Dead cron jobs removed (reaper + watchdog) | Arden | 2026-02-12 |
| 19/19 code stinks resolved | Arden | 2026-02-11 |
| OWL berufenet integration (17,381 names imported) | Arden | 2026-02-11 |
| Berufenet OWL-first pipeline (Phase 1 + Phase 2) | Arden | 2026-02-11 |
| 81.8% berufenet classification (167,638 / 205,054) | Arden | 2026-02-11 |
| **SITE LIVE ON INTERNET** 🎉 | Arden | 2026-02-01 |
| AA backfill complete: 68.5% → 97.3% coverage | Arden | 2026-02-01 |

---

## 📋 NEXT UP

| Priority | Task | Hours | Depends On |
|----------|------|-------|------------|
| 1 | Run reprocessing SQL (15,651 rows) | 5min | Current fetch batch finishing |
| 2 | Monitor reprocessed batch hit rate | — | #1 |
| 3 | Notifications JS fix | 1h | — |
| 4 | Impressum real address | — | Legal review |
| 5 | Terms [Your City] placeholder | — | Legal review |
| 6 | LogReg restricted-role detector | 4h | Nate review |
| ? | **Sandy: what's the priority?** | — | — |

---

## 🚧 BLOCKED

| Task | Blocked By | Notes |
|------|------------|-------|
| Legal placeholders | Need real contact info | Pre-launch |

---

## 📊 Inventory

| Source | Postings | With Description | Classified | % Classified |
|--------|----------|------------------|------------|--------------|
| arbeitsagentur.de | 201,107 | 176,939 | 166,500 | 82.8% |
| Deutsche Bank | 3,947 | 3,947 | 1,139 | 28.8% |
| **Total** | **205,054** | **180,886** | **167,639** | **81.8%** |

**OWL entities:** 3,561 berufenet | **OWL names:** 32,365
**Profiles:** 5 | **Matches:** 28 | **Tests:** 215 green

### Classification pipeline status (Feb 12)
- Phase 1 (OWL-first): Three-tier acceptance live — exact + unanimous + majority
- Phase 2 (embed+LLM): Draining queue, ~55 titles/batch
- Reprocessing pending: 15,651 `no_match` rows to re-enter Phase 1
- Fix impact estimate: classification should jump from 81.8% → ~90%+ after reprocessing

---

## 📊 MVP Progress

```
Phase 0 [████████████████████] 100% — Foundation
Phase 1 [████████████████████] 100% — Backend ✅
Phase 2 [████████████████████] 100% — Automation ✅
Phase 3 [████████████████████] 100% — Frontend ✅
Phase 4 [████████████████████] 100% — Feedback ✅
Phase 5 [████████████████████] 100% — Site Testing ✅

🎉 SITE FUNCTIONAL — All critical APIs fixed
   Remaining: Legal placeholders, minor JS fix
```

---

## 🔗 Reference

- Full roadmap: [00_roadmap.md](00_roadmap.md)
- Arden's daily notes: [../daily_notes/](../daily_notes/)
- Decisions: [00_roadmap.md#decision-log](00_roadmap.md#decision-log)

---

*Arden: Update status when you finish something. Sandy: Review daily.*
