# Turing Tools

Utilities for operators, developers, and analysts working with the Turing workflow engine.

## Directory Structure

```
tools/
├── admin/          # Workflow administration (validate, compile, visualize)
├── batch/          # Batch operations (backfill skills, summaries)
├── benchmarks/     # Model & extraction benchmarks
├── debugging/      # Debug specific postings, generate traces
├── monitoring/     # Progress checks, metrics, activity charts
├── one-off/        # Experimental/single-use scripts
├── qa/             # Quality assurance checks
└── *.py            # Top-level utilities
```

## Quick Reference

### Most Used Commands

```bash
# Validate workflow before running
python tools/admin/validate_workflow.py --workflow 3001

# Check posting status
python tools/monitoring/check_posting_status.py --posting-id 12345

# Debug a stuck posting
python tools/debugging/debug_posting.py 12345

# Get quick ETA on current work
python tools/monitoring/quick_eta.py

# Backfill missing skills (one-off catch-up)
python tools/batch/backfill_skills.py --dry-run
```

### Admin Tools (`admin/`)

| Tool | Purpose |
|------|---------|
| `validate_workflow.py` | Pre-flight check before running workflows |
| `compile_workflow.py` | Compile workflow definitions |
| `visualize_workflow.py` | Generate workflow diagrams |
| `update_actor_code.py` | Update actor code in database |
| `reprocess_postings.py` | Re-queue failed postings |
| `sync_contracts_to_db.py` | Sync Python contracts to DB |

### Batch Tools (`batch/`)

| Tool | Purpose |
|------|---------|
| `backfill_skills.py` | Re-extract skills for postings with sparse results |
| `backfill_summaries.py` | Re-generate summaries |
| `batch_ihl_scorer.py` | Batch IHL scoring |
| `fetch_missing_descriptions.py` | Fetch missing job descriptions |

### Monitoring Tools (`monitoring/`)

| Tool | Purpose |
|------|---------|
| `quick_eta.py` | Fast ETA for current queue |
| `activity_chart.py` | Visual activity chart |
| `check_posting_status.py` | Status for specific posting |
| `daily_summary.py` | Daily completion summary |
| `monitor_gpu.py` | GPU utilization monitor |

### Debugging Tools (`debugging/`)

| Tool | Purpose |
|------|---------|
| `debug_posting.py` | Deep-dive into a specific posting |
| `generate_retrospective_trace.py` | Generate trace for completed runs |

### QA Tools (`qa/`)

| Tool | Purpose |
|------|---------|
| `idempotency_check.py` | Verify idempotent operations |
| `validate_job_status.py` | Validate job posting status |
| `check_stale_docs.py` | Find outdated documentation |

## Top-Level Tools

| Tool | Purpose |
|------|---------|
| `run_workflow.py` | Run workflow for specific posting |
| `llm_chat.py` | Interactive LLM chat for testing |
| `sql_query.py` | Run SQL queries from command line |
| `import_profile.py` | Import candidate profile |
| `exec_agent.py` | Execute agent task |

## Guidelines

1. **All tools support `--help`** - Check usage before running
2. **Use `--dry-run`** when available - Preview before modifying
3. **Prefer `scripts/turing.py`** for monitoring - It's the unified dashboard
4. **Check `logs/`** for detailed output

## See Also

- `scripts/turing.py` - Main dashboard and launcher
- `docs/architecture/` - System architecture docs
- `by_admin/` - Streamlit admin GUI
