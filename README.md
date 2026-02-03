# Turing

**Universal workflow automation engine** - orchestrates humans, AI models, and scripts.

```
START HERE:  ./scripts/turing.py
```

---

## Quick Start

```bash
# Activate environment (always!)
source venv/bin/activate

# Launch workers + live dashboard
./scripts/turing.py

# Quick status check
./scripts/turing.py --status

# Stop everything
./scripts/turing.py --kill
```

---

## What is Turing?

**Turing** is a Turing-complete workflow engine. It processes anything that can be computed.

**Current Application**: Talent.Yoga job posting analysis
- Extract job summaries
- Extract skills from postings
- Calculate IHL (Ideal Human Lifespan) scores
- Match candidates to positions

**How it works**:
```
queue → workers → LLM/scripts → database
  ↓
postings table gets: summary, skills, ihl_score
```

---

## Project Structure

```
ty_learn/
├── scripts/turing.py       # 🎯 START HERE - launcher + dashboard
├── core/                   # 🔧 Engine (queue, wave_runner, database)
├── tools/                  # 🛠️ Utilities (admin, batch, monitoring)
├── docs/                   # 📚 Documentation
│   ├── architecture/       #     System design
│   └── workflows/          #     Workflow specs
├── by_admin/               # 🖥️ Admin GUI (Streamlit)
├── prototypes/             # 🧪 R&D experiments
├── tests/                  # ✅ Test suite
├── archive/                # 📦 Archived code
└── .env                    # 🔒 Database credentials
```

---

## Key Components

### Runtime (What's Actually Running)

| File | Purpose |
|------|---------|
| `scripts/turing.py` | Launch workers, show dashboard, check status |
| `core/queue_worker.py` | Claims work from queue, creates runs |
| `scripts/wave_runner_daemon.py` | Executes interactions (calls LLMs) |

### Core Engine (`core/`)

| File | Purpose |
|------|---------|
| `database.py` | Connection pooling |
| `wave_runner/` | Interaction execution |
| `circuit_breaker.py` | Failure protection |

### Tools (`tools/`)

See [tools/README.md](tools/README.md) for complete list.

Quick highlights:
```bash
python tools/admin/validate_workflow.py --workflow 3001
python tools/debugging/debug_posting.py 12345
python tools/monitoring/quick_eta.py
```

---

## Database

PostgreSQL database named `turing`. Key tables:

| Table | Purpose |
|-------|---------|
| `postings` | Job postings with extracted data |
| `posting_skills` | Skills extracted from postings (relational) |
| `queue` | Pending work items |
| `runs` | Workflow execution records |
| `interactions` | Individual LLM/script calls |
| `conversations` | Interaction templates |
| `actors` | LLM/script definitions |

Connect:
```bash
export $(cat .env | xargs) && psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

---

## Workflows

Workflows are defined in the database. Current active:

| ID | Name | Purpose |
|----|------|---------|
| 3001 | Complete Job Processing | Main pipeline (summary → skills → IHL) |
| 1121 | Skills Extraction | Extract skills from job posting |

Workflow definitions: `reports/workflows/`

---

## Common Tasks

### Check Progress
```bash
./scripts/turing.py --status
```

### Debug a Posting
```bash
python tools/debugging/debug_posting.py 12345
```

### Clean Stale Queue Entries
```bash
python scripts/cleanup_queue.py --dry-run  # preview
python scripts/cleanup_queue.py            # execute
```

### Admin GUI
```bash
cd by_admin && streamlit run app.py
```

---

## Architecture Docs

- [docs/architecture/](docs/architecture/) - System design
- [reports/workflows/](reports/workflows/) - Workflow specifications
- [core/README.md](core/README.md) - Engine internals

---

## Environment

- **Python**: 3.11+ with venv
- **Database**: PostgreSQL 14+
- **LLM**: Ollama (local)
- **Config**: `.env` file

---

## AI Assistants

If you're an AI picking this up:

1. **Start with `./scripts/turing.py --status`** to see what's running
2. **The engine is event-sourced**: queue → runs → interactions → results
3. **Skills are stored relationally**: `posting_skills` table, NOT `postings.skill_keywords`
4. **Workers run in background**: `queue_worker.py` + `wave_runner_daemon.py`
5. **Check `archive/`** for historical code - don't resurrect without asking

---

*Last updated: December 11, 2025*
