# Turing - Universal Workflow Automation Engine

> **👋 Hey Arden!**  
> You're in the **MAIN workspace** - the full codebase. You can work on ANYTHING here: wave processing, skill matching, schema design, workflows, tools, documentation, debugging - everything. For focused work on specific topics, Gershon might switch to the dedicated skill_matching or wave_processing workspaces. But here, you have full access to the entire system.

**Production-grade workflow execution platform combining AI, scripts, and human decision-making**  
*PostgreSQL-backed, checkpoint-enabled, circuit-breaker protected*

---

## 🎯 What is Turing?

**Turing** is a **universal workflow automation engine** - a Turing-complete system that orchestrates humans, AI models, and scripts to accomplish any computable task. Like a Turing machine, it's a general-purpose computational engine, not limited to any specific application.

**Current Application**: Processing job postings for Talent.Yoga (TY) - extracting skills, generating summaries, calculating IHL scores, matching candidates to positions.

**System Naming**:
- **Turing** = The workflow engine (this system)
- **Talent.Yoga (TY)** = Career portal product (runs on Turing)
- **ty_learn** = R&D workspace folder (historical name)
- **turing** = PostgreSQL database name

**What Makes It Universal**:
- **Turing-Complete**: Conditional branching, loops, state, I/O, composition
- **Actor Agnostic**: Orchestrates LLMs (Ollama), scripts (Python/Bash), APIs, humans
- **Declarative Workflows**: Define pipelines in database schema, not code
- **Wave Processing**: GPU-optimized batch execution (load model once, process many items)
- **Crash Recovery**: Checkpoint-based resumption after failures

---

## 🚀 Quick Start

### Run Workflows
```bash
# Activate virtual environment (ALWAYS first!)
source venv/bin/activate

# Execute complete job processing pipeline
python3 -m core.wave_batch_processor --workflow 3001

# Resume from checkpoint after crash
python3 -m core.wave_batch_processor --workflow 3001 --resume-from 23332

# Test with limited batch
python3 -m core.wave_batch_processor --workflow 3001 --limit 10

# List incomplete runs (to find workflow_run_id for resuming)
python3 -m core.wave_batch_processor --workflow 3001 --list-incomplete
```

### Monitor Workflows
```bash
# Real-time monitoring dashboard
python3 tools/monitor_workflow.py --workflow 3001 --mode live

# One-time snapshot
python3 tools/monitor_workflow.py --workflow 3001 --mode snapshot

# Step-by-step detail
python3 tools/monitor_workflow.py --workflow 3001 --mode steps

# Performance metrics
python3 tools/monitor_workflow.py --workflow 3001 --mode metrics
```

### Validate & Test
```bash
# Pre-flight validation (catches config errors)
python3 tools/validate_workflow.py --workflow 3001

# Check for hallucinations in summaries
python3 scripts/qa_check_hallucinations.py

# Run integration tests
python3 -m pytest tests/
```

### Database Access
```bash
# Connect to database (credentials in .env)
export $(cat .env | grep -v '^#' | xargs)
psql -U $DB_USER -d $DB_NAME -h $DB_HOST

# Or use Python
python3 -c "from core.database import get_connection, return_connection; conn = get_connection(); print('✓ Connected'); return_connection(conn)"
```

---

## 📁 Project Structure

```
ty_learn/
├── core/                       # 🚀 Core workflow execution engine
│   ├── wave_batch_processor.py # Main orchestrator with wave processing
│   ├── database.py             # Connection pooling (5-50 connections)
│   ├── circuit_breaker.py      # Actor failure protection (5 fails → pause)
│   ├── actor_router.py         # LLM/script execution routing
│   ├── checkpoint_utils.py     # Reusable checkpoint query functions
│   └── error_handler.py        # Centralized exception handling
│
├── tools/                      # 🛠️ Development & monitoring tools
│   ├── monitor_workflow.py     # Unified workflow monitoring (4 modes)
│   ├── validate_workflow.py    # Pre-deployment validation
│   ├── _trace_value.py         # Execution tracing (field provenance)
│   ├── monitor_gpu.py          # GPU utilization tracking
│   └── exec_agent.py           # Web access + AI consultation for LLMs
│
├── scripts/                    # 📜 Automation & QA scripts
│   ├── qa_check_hallucinations.py  # Pattern-based hallucination detection
│   └── [workflow-specific scripts]
│
├── workflows/                  # ⚙️ Workflow YAML definitions
│   └── 3001_complete_job_processing_pipeline.yaml
│
├── sql/                        # 🗄️ Database schema & migrations
│   ├── schema.sql              # Complete database schema
│   ├── migrations/             # Applied migrations (001-018+)
│   └── fuzzy_skill_matching.sql # Skill matching functions
│
├── docs/                       # 📚 Documentation
│   ├── ARCHITECTURE.md         # System architecture (being refactored)
│   ├── architecture/           # Focused architecture subdocs
│   ├── ___ARDEN_CHEAT_SHEET.md # Quick reference for AI assistants
│   ├── TOOL_REGISTRY.md        # Available tools & actors
│   ├── SKILL_MATCHING.md       # Profile-to-job matching guide
│   └── [many other guides]
│
├── tests/                      # 🧪 Integration tests
│   ├── test_workflow_execution.py
│   └── README.md
│
├── matching/                   # 🎯 Skill matching algorithms
├── interrogators/              # 🔍 Data quality checks
├── archive/                    # 📦 Legacy code preservation
├── .env                        # 🔒 Secure credentials (gitignored)
└── venv/                       # 🐍 Python virtual environment
```

---

## 🎯 Current Status (November 17, 2025)

### ✅ **Production-Ready Features**
- **Checkpoint Recovery**: Crash-resistant execution with automatic resume
- **Connection Pooling**: 10-20x faster database operations (~8ms checkpoint saves)
- **Circuit Breaker**: Automatic actor failure protection (5 failures → 5min cooldown)
- **Hallucination Detection**: Pattern-based QA with 27+ detection rules
- **Workflow Validation**: Pre-deployment configuration checks
- **Wave Processing**: GPU-optimized batch execution (~700 postings/minute)
- **Two-Layer Idempotency**: Checks both execution history and actual data

### 📊 **Active Deployment**
- **Environment**: Development (gaming laptop + Ollama)
- **Database**: PostgreSQL 14 with `turing` database
- **Workflow 3001**: Processing ~2,000 Deutsche Bank job postings
  - Stage 1: Summary extraction (gemma3:1b)
  - Stage 2: Skill extraction (qwen2.5:7b)
  - Stage 3: IHL score calculation (multi-actor debate)
- **Performance**: ~96% GPU utilization, ~8.5ms checkpoint saves
- **Next**: Move to AI workstation for UAT

### 🏗️ **Architecture Highlights**
- **Turing-Complete**: Conditional branching, loops, state, I/O, composition
- **Wave Processing**: Groups by execution_order, processes all Step 3 before Step 4
- **Checkpoint Queries**: Standard pattern prevents template substitution bugs
- **Observability**: Real-time monitoring, error tracking, performance metrics
- **Test Coverage**: Integration tests for workflows, checkpoints, branches

---

## 🛠️ Key Capabilities

### **Workflow Orchestration**
- **Declarative Pipelines**: Define workflows in database schema (SQL migrations)
- **Dynamic Branching**: Runtime routing based on actor output patterns
- **Multi-Actor Conversations**: Chain LLMs, scripts, APIs in any sequence
- **Human-in-the-Loop**: Async human validation/decision steps
- **Idempotency**: Automatic detection of already-completed work

### **Actor System**
- **LLM Actors**: 24+ models via Ollama (Gemma, Qwen, LLaMA, DeepSeek, etc.)
- **Script Actors**: Python/Bash scripts as workflow steps
- **Delegate Actors**: Reusable tools (skill mappers, taxonomy expanders)
- **ExecAgent**: Special actor with web access + AI consultation capabilities
- **Circuit Breaker**: Auto-pause failing actors (5 failures → 5min cooldown)

### **Data Quality**
- **Hallucination Detection**: 27+ patterns across 12 categories
- **QA Gates**: Automated checks before data persistence
- **Checkpoint Queries**: Prevents template substitution bugs
- **Error Tracking**: Full context logging to `workflow_errors` table

### **Performance Optimization**
- **Wave Processing**: Load model once, process many postings (~20x faster)
- **Connection Pooling**: Reuse database connections (5-50 pool)
- **Execution Order Grouping**: Process all Step 3 before Step 4 (GPU efficiency)
- **Checkpoint Chunking**: Save state every 35 postings (prevent timeout)

---

## 📚 Documentation

### **Getting Started**
- `docs/___ARDEN_CHEAT_SHEET.md` - Quick reference for critical info
- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/TOOL_REGISTRY.md` - Available tools and actors
- `docs/WORKFLOW_CREATION_COOKBOOK.md` - How to build workflows

### **Specialized Guides**
- `docs/SKILL_MATCHING.md` - Profile-to-job matching algorithms
- `docs/HALLUCINATION_DETECTION_COOKBOOK.md` - QA patterns and detection
- `docs/CHECKPOINT_QUERY_PATTERN.md` - Standard checkpoint query pattern
- `docs/TEMPLATE_SUBSTITUTION_BUG.md` - Bug analysis and fix
- `docs/PYTHON_TO_TURING_MIGRATION_GUIDE.md` - Converting scripts to workflows

### **Operations**
- `docs/OPERATIONS_GUIDE.md` - Deployment, monitoring, troubleshooting
- `docs/WORKFLOW_DEBUGGING_GUIDE.md` - Debugging techniques
- `docs/CLEANUP_TRACKER_2025-11-16.md` - Recent maintenance work

### **API Reference**
- Database schema documentation in `sql/schema.sql`
- Actor contracts in `actors` table
- Workflow definitions in `workflows/` (YAML)

---

## 🔮 Roadmap

### **Phase 1: MVP Complete** (Current)
- ✅ Workflow 3001 processing Deutsche Bank jobs
- ✅ Skill extraction and taxonomy mapping
- ✅ IHL score calculation
- ✅ Profile-to-job matching
- ⏳ Gershon profile matching validation

### **Phase 2: Production Deployment**
- Move to AI workstation
- Connect to web for UAT
- Multi-user support
- Real-time job ingestion (multiple sources)

### **Phase 3: Talent.Yoga Integration**
- Public-facing career portal
- Candidate registration and profiling
- Job recommendations
- Application tracking

### **Phase 4: Universal Platform**
- General-purpose workflow execution
- Other applications beyond job matching
- Workflow marketplace
- Multi-tenant deployment

---

## 🤝 Contributing

This is currently a private R&D project. Documentation conventions:

- **AI Assistant Personas**: "Arden" = GitHub Copilot, "Sage" = Document reviewer
- **Session Logs**: Captured in `docs/logs/` as Markdown
- **Commit Messages**: Use assistant name prefix (e.g., "Arden: fixed connection pooling")
- **Architecture Decisions**: Document as ADRs in `docs/architecture/`

---

## 🎓 Philosophy

- **Ship fast, refine later**: 80% working now > 100% perfect in 2 hours
- **Test immediately**: Run code after writing, not before committing
- **Document wins**: Capture what worked in session logs
- **Consolidate ruthlessly**: 4 tools doing same thing? Make it 1
- **Trust instincts**: If something feels off, investigate
- **AI as partner**: Treat AI assistants as creative collaborators with names and roles

---

## 📞 System Information

**Database**: `turing` (PostgreSQL 14)  
**Python**: 3.10+  
**Virtual Env**: `venv/` (activate with `source venv/bin/activate`)  
**Credentials**: `.env` file (gitignored, see `.env.example`)  
**LLM Runtime**: Ollama (localhost:11434)  
**Development**: Gaming laptop (local dev environment)  

---

**Last Updated**: November 17, 2025  
**Version**: 1.2  
**Status**: Active Development (MVP phase)
