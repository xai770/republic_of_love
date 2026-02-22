# Daily Note — 2026-02-22 (Sunday)

## Done

### Embedding Data Integrity (commit 660c9e6)
- Fixed `save_embedding()` to use `normalize_text_python()` server-side — eliminates Python `.strip()` vs SQL `btrim` unicode drift
- Changed `ON CONFLICT DO NOTHING` → `ON CONFLICT DO UPDATE` — stale embeddings get replaced
- Updated `get_postings_needing_embeddings()` to use `text_hash` index — catches both missing AND stale
- Updated DB work_query for embedding_generator actor
- Repaired 12,772 duplicate embedding rows + 7,608 corrupted hashes
- Fixed pipeline_report.py to show embeddable vs embedded with certification
- Added post-enrichment embedding sweep + certification step to turing_fetch.sh
- **Result:** 167,733/167,733 = 100.0% embedded → CERTIFIED CLEAN

### Pipeline Report (scripts/pipeline_report.py)
- Built from scratch, iterated 5 times through hash-matching bugs
- Per-source ASCII table: total, active, has_desc, has_summary, has_embedding
- Final version uses `normalize_text_python()` inside SHA256 for accurate hash matching
- Outputs `✅ CERTIFIED CLEAN` or `⚠️ NOT CLEAN` with itemized issues

### Auto-Documentation (scripts/generate_fetch_docs.py)
- Introspects turing_fetch.sh steps, DB actor configs, Python actor files, DB views
- Generates 1,400+ line markdown doc with mermaid flowcharts and per-actor deep dives
- Covers all 15 pipeline components: I/O tables, normalization, dependencies, failure modes, data contracts
- Internal flowcharts for Berufenet Classification, Embedding Generation, Turing Daemon
- Output: docs/workflows/turing_fetch_pipeline.md
- Post-commit git hook auto-regenerates on every commit

### Embedding Bottleneck
- Daemon had `batch_size=100, scale_limit=3` → bumped to `batch_size=5000, scale_limit=20`
- Full pipeline test: all 5 steps green, 1,117 new AA postings, 777 embeddings, only 2 pending

### Billing Methodology + Cost Assumptions (commit 6af5d02)
- Created `docs/project/billing_assumptions.yaml` — all tunable cost numbers in one reviewable file
  - 8 sections: AI event prices, hardware amortization (€2500 GPU / 36mo), electricity, services, compute cost per event, founder debt, allocation waterfall, subscription tiers, pipeline costs
- Created `docs/project/billing_methodology.md` — how a per-yogi bill works
  - Bill mockup (German/English), data flow diagram, SQL queries per section
  - Every tier gets a bill (trial, free, full) — transparency instrument, not invoice
  - Section A: Direct AI usage, B: Cost to serve, C: Contribution allocation, D: Community context
  - Open questions for Sandy/Nate review
- References `docs/project/pricing_and_ledger.md` (Sage, Jan 27) for philosophy

### Transaction Drill-Down (commit f31421b)
- `GET /api/account/transactions?month=YYYY-MM` — paginated event list with German labels
  - e.g. "Mira: Wie finde ich einen Job?", "Anschreiben: Deutsche Bank AG — Data Engineer"
- `GET /api/account/transactions/{event_id}` — full drill-down into any charge
  - Shows the chat messages, cover letter text, match analysis, or CV session summary
- Context JSONB schema: each `usage_events` row stores linkable IDs (message_id, match_id, session_id)
- Mira chat handler now captures `message_id` via `INSERT ... RETURNING`
- Migration 060: GIN index on `usage_events.context` for efficient JSONB lookups
- Updated methodology doc with full API contract + examples

## Broke
- Nothing broken. All prior data repaired.

## Dropped Balls
- Dashboard redesign (Sandy's weakest-page critique) — not started
- Landing page pricing inconsistency — not addressed
- Profile right pane empty state — not addressed
- Billing UI (meter, paywall screen, Stripe checkout) — not started
- Mysti polish / demo — waiting on this before next Sandy call
- Instrument remaining endpoints (CV, cover letter, match report, profile embed) — `log_event()` one-liners needed

## Next Session
- Dashboard redesign should be priority #1 (Sandy's feedback)
- Instrument CV/cover letter/match report/profile embed with `log_event()` calls
- Sandy/Nate review `billing_assumptions.yaml` — adjust numbers until they fit
- Build bill generation script (`scripts/generate_yogi_bill.py`)
- Review Berufenet Phase 2 performance after batch_size=2000 change
- Look at external_partner scraper coverage (how many [EXTERNAL_PARTNER] remain?)
