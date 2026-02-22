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

## Broke
- Nothing broken. All prior data repaired.

## Dropped Balls
- Dashboard redesign (Sandy's weakest-page critique) — not started
- Landing page pricing inconsistency — not addressed
- Profile right pane empty state — not addressed
- Billing UI implementation — not started
- Mysti polish / demo — waiting on this before next Sandy call

## Next Session
- Dashboard redesign should be priority #1 (Sandy's feedback)
- Consider adding `--check` mode to generate_fetch_docs.py for CI validation
- Review Berufenet Phase 2 performance after batch_size=2000 change
- Look at external_partner scraper coverage (how many [EXTERNAL_PARTNER] remain?)
