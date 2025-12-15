# Prototypes → Turing Workflows

**Purpose**: This folder contains Python scripts that are **migration candidates** for Turing workflows.

## Migration Status

### ✅ Ready to Migrate
Scripts that are tested, working, and ready for Turing conversion:

- `fetch_remoteok_jobs.py` → **Workflow 3004** (Multi-Source Job Harvesting)
- `extract_user_search_skills.py` → **Workflow 3006-1** (Extract user skills for search)

### 🔨 In Development
Scripts being built/tested:

- `generate_job_search_query.py` → **Workflow 3006-2** (LLM creates search query) - Next to build

### 📋 Planned
Scripts we plan to build:

1. `extract_user_search_skills.py` → **Workflow 3006-1** (Get user skills for search)
2. `generate_job_search_query.py` → **Workflow 3006-2** (LLM creates search query)
3. `classify_job_site.py` → **Workflow 3006-3** (LLM determines if site is scrapable)
4. `search_for_job_sites.py` → **Workflow 3006-4** (Find job boards via web search)
5. `extract_job_fields_llm.py` → **Workflow 3006-5** (Parse arbitrary HTML with LLM)

## Rules

1. **One script = One workflow** (or one conversation within a workflow)
2. **Test before migrating** - Script must work standalone
3. **Document inputs/outputs** - What placeholders will it need?
4. **Keep it simple** - Complex logic should be split into multiple scripts
5. **Archive after migration** - Move to `/archive/prototypes/` when converted

## Migration Process

```
prototypes/my_script.py
  ↓ (test + validate)
migrations/workflow_XXXX_my_workflow.sql
  ↓ (deploy to database)
/archive/prototypes/my_script.py
```

## File Naming Convention

```
<action>_<object>_<method>.py

Examples:
- extract_user_search_skills.py      (extract what from where how)
- generate_job_search_query.py       (generate what how)
- fetch_remoteok_jobs.py             (fetch what from where)
- classify_job_site.py               (classify what)
```

## How to Use This Folder

### 1. Build Prototype
```bash
# Create new script
vim prototypes/my_new_feature.py

# Make it executable
chmod +x prototypes/my_new_feature.py

# Test it
python3 prototypes/my_new_feature.py --test
```

### 2. Document Migration Plan
Add to "Planned" section above with target workflow ID.

### 3. Migrate When Ready
Follow `docs/PYTHON_TO_TURING_MIGRATION_GUIDE.md` 5-step process.

### 4. Archive
```bash
# After successful migration
mv prototypes/my_new_feature.py archive/prototypes/
git commit -m "Migrated my_new_feature to Workflow XXXX"
```

## Current Priority

**This Week**: Build prototypes for Workflow 3006 (Job Discovery Pipeline)
1. Extract user skills from database
2. Generate search query via LLM
3. Classify job sites
4. Search web for job boards
5. Parse job fields with LLM

**Next Week**: Migrate all 5 scripts to Workflow 3006

---

**Remember**: Prototypes are throwaway code. Build fast, test, migrate, delete! 🚀
