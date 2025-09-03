# ty_learn Clean Architecture

This workspace follows a clean architecture that separates **lifecycles**, **purposes**, and **artifacts**.

## 🎯 Architecture Principles

1. **Single Purpose per Directory** - Each folder has one clear responsibility
2. **Lifecycle Separation** - Current work vs historical artifacts
3. **Clear Boundaries** - No conceptual overlap between directories
4. **Standard Patterns** - Follows common development conventions

## 📁 Directory Structure

```
ty_learn/
├── config/              # Configuration files
├── data/                # Datasets and data files
├── docs/                # Documentation
├── modules/             # Core maintained code
│   └── llm_framework/   # LLM framework (unified location)
├── tests/               # Automated tests
├── validation/          # Validation & QA harnesses
├── artifacts/           # Experimental outputs & test artifacts
├── experiments/         # Research & prototype work
│   ├── research/        # V16 experimental development
│   ├── prototypes/      # Trial implementations
│   └── legacy_development/ # Historical development work
├── tools/               # Workspace & helper scripts
├── production/          # Current deployed versions
│   ├── v14/            # Production-ready V14 system (with own output/)
│   └── v7/             # Sandy's Pipeline (current production, with own output/)
└── archive/             # Legacy and historical materials (unified)
    ├── consolidated/    # Organized historical content
    ├── migrations/      # Historical migration work
    └── legacy/          # Original archive materials
```

## 🎯 Usage Guide

### For Production Work:
```bash
# Use current production (Sandy's Pipeline)
cd production/v7 && python main.py

# Deploy V14 production system
cd production/v14 && python reports.py
```

### For Development/Research:
```bash
# Work on V16 development
cd experiments/research/v16_development

# Use LLM framework
cd modules/llm_framework

# Check experimental artifacts
ls artifacts/
```

### For Tools & Utilities:
```bash
# Use workspace tools
cd tools && ./reorganize_workspace.sh

# Run tests
cd tests && python -m pytest
```

### For Reference:
```bash
# Check legacy versions
ls archive/legacy/versions/

# Review migration history
ls archive/migrations/
```

## 🏆 Benefits

✅ **Clear Mental Model** - Purpose of each directory is obvious  
✅ **No Overlap** - Each item has exactly one logical place  
✅ **Lifecycle Clarity** - Current work vs historical artifacts separated  
✅ **Standard Patterns** - Follows common development conventions  
✅ **Easy Navigation** - Know exactly where to find what you need  

## 🔄 Migration Notes

This structure was created on 2025-08-28 from the previous mixed-lifecycle organization.

**Key Changes:**
- `active_production/` + `versions/production/` → `production/`
- `archive/` + `archive_consolidated/` → `archive/` (unified)
- `development/` + `experiments/` → `experiments/` (with research/prototypes)
- `llm_framework/` → `modules/llm_framework/` (unified core code)
- `output/` → `artifacts/` (experimental outputs, distinct from production)
- `workspace_tools/` → `tools/`
- `backup_system/` → `archive/legacy/` (historical infrastructure)
- `v14_v15_migration/` → `archive/migrations/`

**Overlap Fixes (2025-08-28):**
- Eliminated duplicate archive structures (drift risk)
- Unified all core code under `modules/`
- Clarified experimental vs production outputs
- Removed development/experimental duplication

**Backup:** Available at `/home/xai/Documents_archive/ty_learn`
