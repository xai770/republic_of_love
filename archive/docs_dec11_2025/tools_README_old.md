# Turing Tools

User-facing utilities for working with the Turing AI execution engine.

## Purpose

This directory contains **production-ready tools** for operators, QA engineers, and analysts. These are NOT experimental scripts - they are maintained, documented, and safe to use.

For experimental/legacy scripts, see the `scripts/` directory.

---

## Available Tools

### 📊 `generate_skills_qa_report.py`

Generate markdown QA reports for skills extraction validation.

**Purpose:** Review skills extracted from job postings with quality metrics and flags.

**Usage:**
```bash
# Generate report for all postings
python tools/generate_skills_qa_report.py

# Generate report for specific posting
python tools/generate_skills_qa_report.py --posting-id 2

# Generate report for date range
python tools/generate_skills_qa_report.py --from-date 2025-11-01 --to-date 2025-11-02

# Include only postings with warnings
python tools/generate_skills_qa_report.py --warnings-only
```

**Output:** `reports/skills_qa_YYYYMMDD_HHMMSS.md`

**What It Shows:**
- Original job description
- Extracted summary
- Skills table (importance, proficiency, years, reasoning)
- Quality flags (too few/many skills, generic skills, potential gaps)
- Extraction metadata (workflow, actor, latency)
- Lineage tracking (which LLM interaction created this)

---

### 🔄 `sync_contracts_to_db.py` ⭐ NEW (Nov 6, 2025)

Sync Python workflow contracts to `workflow_variables` database table.

**Purpose:** Keep database registry in sync with Python dataclass contracts for type safety.

**Usage:**
```bash
# Dry-run first (see what would change)
source venv/bin/activate  # REQUIRED!
python tools/sync_contracts_to_db.py --dry-run

# Actually sync to database
python tools/sync_contracts_to_db.py
```

**Output:** 
```
🔄 SYNCING WORKFLOW CONTRACTS TO DATABASE
📋 Found 2 registered contracts:
   - Workflow 1121: Job Skills Extraction
   - Workflow 2002: Profile Skills Extraction

📝 Processing Workflow 1121: Job Skills Extraction
   ✅ Created: input.posting_id
   ✅ Created: output.skills
   ✅ Created: output.posting_id

✅ Synced 6 variables to database
```

**When to Run:**
- After editing `contracts/__init__.py`
- After adding new `@register_workflow_contract` decorators
- When database and code are out of sync

**Related Files:**
- `contracts/README.md` - Full contract system documentation
- `migrations/057_add_workflow_variables_registry.sql` - Table schema
- `migrations/058_fix_workflow_variables_unique_constraint.sql` - Bug fix

---

## Future Tools (Planned)

### 🔍 `compare_actor_performance.py`
Compare extraction quality across different AI actors (qwen, gemma, phi3, etc.)

### 🐛 `workflow_debugger.py`
Interactive debugger for failed workflows with lineage visualization

### 📈 `cost_analyzer.py`
Analyze LLM costs per workflow, actor, and time period

### 🔗 `lineage_visualizer.py`
Generate visual graphs of interaction causation chains

---

## Tool Development Guidelines

When adding new tools to this directory:

1. **Documentation First:** Update this README before committing code
2. **Argparse Required:** All tools must support `--help`
3. **Error Handling:** Fail gracefully with clear error messages
4. **Output to reports/:** Don't clutter working directories
5. **Database Read-Only:** Tools should NOT modify database (use migrations for that)
6. **Config from membridge.yaml:** Use existing database config

---

## Dependencies

Tools use the same dependencies as the main Turing system:
- psycopg2 (PostgreSQL)
- PyYAML (config parsing)
- Standard library (no exotic deps)

See main `requirements.txt` for full list.

---

**Questions?** Read the tool's `--help` output or check `SAGE_BRIEFING_TURING_SYSTEM.md` for system architecture.
