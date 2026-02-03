# CURRENT — talent.yoga Sprint Tracker

**Last updated:** 2026-02-01 afternoon by Arden

---

## 🔥 TODAY

| Task | Owner | Status |
|------|-------|--------|
| Dashboard discussion | Sandy+Arden | next |
| Embedding run for new postings | — | queued |

---

## ✅ DONE (This Week)

| Task | Owner | Completed |
|------|-------|-----------|
| **SITE LIVE ON INTERNET** 🎉 | Arden | 2026-02-01 |
| Cloudflare Tunnel setup (talent.yoga → localhost:8000) | Arden | 2026-02-01 |
| Google OAuth production fix (redirect_uri + FRONTEND_URL) | Arden | 2026-02-01 |
| Sudoers config (cloudflared + wg-quick) | Arden | 2026-02-01 |
| AA backfill complete: 68.5% → **97.3%** coverage | Arden | 2026-02-01 |
| Rate limit resilience (VPN rotation on 403) | Arden | 2026-02-01 |
| 931 expired jobs invalidated via 404 detection | Arden | 2026-02-01 |
| Site testing follow-up | Sandy | 2026-01-29 |
| Site testing (full pass) | Arden | 2026-01-29 |
| API fixes (`/api/profiles/me`, `/facets`, `/stats`) | Arden | 2026-01-29 |
| Archive old tickets (746K deleted) | Sandy | 2026-01-28 |
| Archive script atomic transactions | Sandy | 2026-01-28 |
| Domain gate detector (Nate feedback) | Sandy | 2026-01-28 |
| Fachanwalt → HARD patterns | Sandy | 2026-01-28 |
| MFA/Arzthelfer → soft_patterns | Sandy | 2026-01-28 |
| Unknown domain threshold (MIN_CONFIDENCE=0.35) | Sandy | 2026-01-28 |
| Profile editor + preferences | Arden | 2026-01-27 13:15 |
| Mobile responsive | Arden | 2026-01-27 13:15 |
| Maria mockup polish (dashboard) | Arden | 2026-01-27 13:15 |
| Lobby + Pricing tiers | Arden + Sage | 2026-01-27 13:05 |
| Finances page (public ledger) | Arden | 2026-01-27 13:05 |
| Ledger API + DB tables | Arden | 2026-01-27 13:05 |
| **Phase 4 COMPLETE** | Arden | 2026-01-27 |
| P4.3 Threshold Tuning (3h est → 4min) | Arden | 2026-01-27 12:55 |
| P4.2 Application Tracking (2h est → 4min) | Arden | 2026-01-27 12:55 |
| P4.1 User Ratings (2h est → 4min) | Arden | 2026-01-27 12:55 |
| **Phase 2 COMPLETE** | Arden | 2026-01-27 |
| Legal pages (2h est → 3min) | Arden | 2026-01-27 12:43 |
| P2.4 Match Notifications (2h est → 3min) | Arden | 2026-01-27 12:43 |
| P2.2 In-App Messages (1h est → 3min) | Arden | 2026-01-27 12:43 |
| P2.1 Scheduled Matching (3h est → 2min) | Arden | 2026-01-27 12:43 |
| **Phase 3 COMPLETE** | Arden | 2026-01-27 |
| P3.5 Visualization (4h est → 4min) | Arden | 2026-01-27 |
| P3.4 Report Viewer (3h est → 6min) | Arden | 2026-01-27 |
| P3.3 Match Dashboard (4h est → 5min) | Arden | 2026-01-27 |
| P3.2 Profile Editor (8h est → 8min) | Arden | 2026-01-27 |
| **Phase 1 COMPLETE** | Arden | 2026-01-27 |
| P1.1-P1.4 Backend | Arden | 2026-01-27 |
| AA pipeline (5,188 jobs) | Arden | 2026-01-27 |
| `postings__job_description_U.py` actor | Arden | 2026-01-27 |
| `postings__embedding_U.py` actor | Arden | 2026-01-27 |
| Seniority handling documented | Sandy | 2026-01-27 |
| Embedding model comparison (BGE-M3 vs Arctic) | Sandy | 2026-01-27 |
| Discovered: skip translation, embed German directly | Sandy | 2026-01-27 |
| arbeitsagentur.de integration (6,433 postings) | Arden | 2026-01-25 |
| P3.2 Profile Editor spec (multi-method) | Sandy | 2026-01-26 |

---

## 📋 NEXT UP

| Priority | Task | Hours | Depends On |
|----------|------|-------|------------|
| 1 | Notifications JS fix | 1h | — |
| 2 | Impressum real address | — | Legal review |
| 3 | Terms [Your City] placeholder | — | Legal review |
| 4 | LogReg restricted-role detector | 4h | Nate review |

---

## 🚧 BLOCKED

| Task | Blocked By | Notes |
|------|------------|-------|
| Legal placeholders | Need real contact info | Pre-launch |

---

## 📊 Inventory

| Source | Postings | With Description | Embedded | Invalidated |
|--------|----------|------------------|----------|-------------|
| arbeitsagentur.de | 34,291 | 33,360 (97.3%) | TBD | 931 |
| Deutsche Bank | ~2,200 | ~2,200 | ? | — |
| **Total** | **~36,500** | **~35,500** | **TBD** | **931** |

**Tickets:** 358,627 active (746K archived 2026-01-28)

### 🚀 Feb 1 Backfill Victory
- **Before:** 68.5% coverage (24,256 with descriptions)
- **After:** 97.3% coverage (33,360 with descriptions)
- **Expired jobs invalidated:** 931 (were returning 404)
- **Stubborn holdouts:** 911 (og:description fallback didn't help)

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
