---
title: "talent.yoga Roadmap to MVP"
created: 2026-01-23
status: active
owner: xai
---

# talent.yoga Roadmap to MVP

## Vision

A website where users can:
1. Log on (Google auth)
2. Upload/manage their profile
3. Get weekly match reports with transparency

---

## Completed Work (Phase 0)

These tasks are DONE. Documented for context:

| Task | What It Delivered |
|------|-------------------|
| [P0.1 Job Posting Ingestion](P0.1_job_posting_ingestion.md) | Deutsche Bank interrogator, ~1,800 postings |
| [P0.2 Posting Pipeline](P0.2_posting_pipeline.md) | Summary → Requirements → Facets extraction |
| [P0.3 Profile Extraction](P0.3_profile_extraction.md) | Clara + Diego actors, 10,690 competencies |
| [P0.4 Embedding Matching](P0.4_embedding_matching.md) | bge-m3, 0.70/0.60 thresholds, domain gates |
| [P0.5 Reports & Visualization](P0.5_reports_visualization.md) | Match reports, UMAP clusters, verdict boxes |
| [P0.6 Turing Infrastructure](P0.6_turing_infrastructure.md) | Pull architecture, 19-table schema, wave batching |

**Total completed:** ~120 hours of foundational work.

---

## Remaining Work (Phases 1-4)

### Phase 1: Backend Foundation
- [P1.1 User Authentication](P1.1_user_authentication.md)
- [P1.2 API Layer](P1.2_api_layer.md)
- [P1.3 Profile CRUD](P1.3_profile_crud.md)
- [P1.4 Match Endpoints](P1.4_match_endpoints.md)

### Phase 2: Automation
- [P2.1 Scheduled Matching](P2.1_scheduled_matching.md)
- [P2.2 Email Delivery](P2.2_email_delivery.md)
- [P2.3 arbeitsagentur.de Interrogator](P2.3_arbeitsagentur_interrogator.md)
- [P2.4 Match Notifications](P2.4_match_notifications.md)

### Phase 3: Frontend
- [P3.1 Login Page](P3.1_login_page.md)
- [P3.2 Profile Editor](P3.2_profile_editor.md)
- [P3.3 Match Dashboard](P3.3_match_dashboard.md)
- [P3.4 Report Viewer](P3.4_report_viewer.md)
- [P3.5 Visualization Embed](P3.5_visualization_embed.md)

### Phase 4: Feedback Loop
- [P4.1 User Ratings](P4.1_user_ratings.md)
- [P4.2 Application Tracking](P4.2_application_tracking.md)
- [P4.3 Threshold Tuning](P4.3_threshold_tuning.md)

## Timeline

| Phase | Target | Hours | Status |
|-------|--------|-------|--------|
| Phase 0 | ✅ Done | ~120h | Foundation complete |
| Phase 1 | Feb 7 | ~12h | Not started |
| Phase 2 | Feb 14 | ~12h | Not started |
| Phase 3 | Feb 28 | ~20h | Not started |
| Phase 4 | Mar 7 | ~11h | Not started |

**Total remaining:** ~55 hours

---

## Effort by Task

| ID | Task | Hours | Owner |
|----|------|-------|-------|
| P1.1 | User Authentication | 3h | arden |
| P1.2 | API Layer | 4h | arden |
| P1.3 | Profile CRUD | 2h | arden |
| P1.4 | Match Endpoints | 3h | arden |
| P2.1 | Scheduled Matching | 3h | arden |
| P2.2 | ~~Email Delivery~~ **In-App Messages** | 1h | arden |
| P2.3 | arbeitsagentur.de Interrogator | 8h | arden | ✅ **DONE** |
| P2.4 | Match Notifications | 2h | arden |
| P3.1 | Login Page | 3h | arden |
| P3.2 | Profile Editor (multi-method) | 8h | arden |
| P3.3 | Match Dashboard | 4h | arden |
| P3.4 | Report Viewer | 3h | arden |
| P3.5 | Visualization Embed | 4h | arden |
| P4.1 | User Ratings | 3h | arden |
| P4.2 | Application Tracking | 4h | arden |
| P4.3 | Threshold Tuning | 4h | sandy |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-27 | **Seniority via embeddings, not extraction** | BGE-M3 separates Senior/Junior at 0.66, below 0.70 threshold. Add user preference (min_seniority) in P3.2, filter in P3.3. No LLM needed. |
| 2026-01-27 | **Keep BGE-M3 over Arctic Embed 2.0** | Arctic has better separation but weaker DE↔EN (0.91 vs 0.93). BGE-M3 is 20% faster. Keep Arctic for future A/B testing. |
| 2026-01-27 | **Skip translation, embed German directly** | bge-m3 cross-lingual within 3% of same-language (0.831 vs 0.843). Translation adds latency/errors for no benefit. |
| 2026-01-26 | **Profile Editor: multi-method** | Chat + Form + CV Upload — user chooses. All paths → same data model. MVP ships Form + Upload; Chat in v1.1. |
| 2026-01-26 | **In-app messages, no email** | WhatsApp doesn't send email either. Simpler, no SMTP, no deliverability issues. P2.2 → 1h instead of 4h. |
| 2026-01-26 | **Skeleton-first arbeitsagentur strategy** | Load all metadata (50K+ titles), enrich on-demand when user arrives. Just-in-time processing, not pre-computation. |
| 2026-01-26 | **MVP legal checklist defined** | Impressum, Privacy Policy, ToS, "not an employment agency" disclaimer, source attribution, cookie consent. Required before public launch. |
| 2026-01-26 | **UI design ownership: Sandy** | Vision: xai + Sage. Images: ChatGPT/Perplexity. Implementation: Arden. QA/consistency: Sandy. |
| 2026-01-25 | arbeitsagentur.de is MVP-blocking | Mysti (real user) needs real jobs, not just Deutsche Bank |
| 2026-01-25 | German/English i18n from Day 1 | Target market is Germany; user choice of language |
| 2026-01-25 | Persona customization (Du/Sie, names) | Cultural fit for German users |
| 2026-01-25 | Two-tier matching architecture | Embedding instant (~2s), LLM on-demand (~8s) |
| 2026-01-21 | Embeddings over OWL for skills | Semantic matching, no taxonomy maintenance |
| 2026-01-22 | actors over task_types | Single executor registry |
| 2026-01-22 | tickets over task_logs | Cleaner naming |
| 2026-01-23 | HTMX + Jinja2 for frontend | Server-rendered, minimal JS, fast |

---

## MVP Legal Requirements

| Item | Status | Notes |
|------|--------|-------|
| Impressum | ⬜ | German legal requirement |
| Datenschutzerklärung (Privacy Policy) | ⬜ | GDPR requirement |
| Nutzungsbedingungen (ToS) | ⬜ | Limits liability |
| "Not an employment agency" disclaimer | ⬜ | Avoids Arbeitsvermittlung licensing |
| Source attribution ("via arbeitsagentur.de") | ✅ | Already doing |
| Cookie consent | ⬜ | ePrivacy Directive |
| Gewerbeanmeldung | ❓ | Business registration — Mysti checking with tax advisor |

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Database | PostgreSQL "turing" |
| Embeddings | bge-m3:567m via Ollama |
| Backend | FastAPI + SQLAlchemy |
| Frontend | HTMX + Jinja2 |
| Auth | Google OAuth 2.0 |
| Notifications | In-app messages (no email) |
| Orchestration | Turing workflow engine |

---

## Team

| Name | Role | Scope | Session Length |
|------|------|-------|----------------|
| **Mysti** (Ilka Pollatschek) | Owner | Legal owner of code + website. Final decisions. Diplompädagogin — qualified to help people find work they like. | — |
| **Sage** | Strategy | Vision, content, direction. Lives in `/home/xai/Documents`. Sees all projects. | Months between sessions |
| **Sandy** | Tech Lead | Planning, implementation, QA. Lives in `/home/xai/Documents/ty_wave`. Manages Arden. | Days to a week |
| **Arden** | Coder | Implementation. Processes 1000s of lines/day. Same codebase view as Sandy via symlinks. | 2-3 days |
| **xai** (Gershon) | Ideas | Has the ideas. Keeps the toilet clean, coffee in the kitchen, AC working. Makes life pleasant for everyone. | Always here |
