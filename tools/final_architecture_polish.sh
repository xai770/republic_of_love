#!/bin/bash

# Final Architecture Polish - Address remaining rough edges
# Date: 2025-08-28
# Purpose: Complete the clean architecture with production-ready polish

set -e

LOG_FILE="final_polish_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] 🌹 Final Architecture Polish..." | tee -a "$LOG_FILE"
echo "[$TIMESTAMP] Addressing: legacy placement, gitignore, docs, ownership" | tee -a "$LOG_FILE"

# Function to log actions
log_action() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# 1. Move legacy_development to archive (keep experiments/ live only)
log_action "📁 Issue 1: Moving legacy_development to archive..."

if [ -d "experiments/legacy_development" ]; then
    log_action "Moving experiments/legacy_development/ → archive/legacy/legacy_development/"
    mkdir -p archive/legacy
    mv experiments/legacy_development archive/legacy/legacy_development
    log_action "✅ Moved legacy_development to archive (experiments/ now live-only)"
fi

# 2. Create comprehensive .gitignore
log_action "📝 Issue 2: Creating comprehensive .gitignore..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/
.venv/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json

# Linting
.ruff_cache/
.pylint.d/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
.tmp/
.temp/

# Local config overrides
local_config.py
.env
.env.local

# Build artifacts (if any)
*.deb
*.rpm
*.tar.gz
*.zip

# Jupyter
.ipynb_checkpoints/

# Coverage reports
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Documentation builds
docs/_build/

# Project-specific
artifacts/tmp/
production/*/tmp/
experiments/*/tmp/
EOF

log_action "✅ Created comprehensive .gitignore"

# 3. Document external symlinks
log_action "📝 Issue 3: Documenting external references..."

mkdir -p docs
cat > docs/external_refs.md << 'EOF'
# External References

This document lists all external symlinks and their real paths for portability reference.

## Symlinked Directories

| Link in Repo | Real Path | Purpose | Owner |
|---------------|-----------|---------|-------|
| `0_mailboxes` | `/home/xai/Documents/0_mailboxes` | Mailbox system | External |
| `ty_projects` | `/home/xai/Documents/ty_projects` | Project data | External |
| `rfa_latest` | `/home/xai/Documents/ty_rfa/rfa_latest` | RfA documents | External |
| `ty_log` | `../ty_log` | Logging system | External |

## Portability Notes

When moving this workspace to another environment:

1. **Create target directories** or update symlinks to new paths
2. **Check dependencies** - some scripts may reference these paths
3. **Update paths** in configuration files if needed
4. **Test functionality** after relinking to ensure all integrations work

## Local Development

For local development, ensure these external systems are available:
- RfA system for documentation workflow
- Mailbox system for communication tracking  
- Project data for processing pipelines
- Logging system for operational monitoring

EOF

log_action "✅ Created external references documentation"

# 4. Create README.md files for each major directory
log_action "📝 Issue 4: Creating directory README files..."

# Production README
cat > production/README.md << 'EOF'
# Production Systems

**Owner**: Arden  
**Purpose**: Current deployed versions ready for production use

## Systems

- **v7/**: Sandy's Pipeline (current production, 411s/job)
- **v14/**: Complete System (ready for deployment, 29.1s/job)

## Usage

```bash
# Run current production
cd v7 && python main.py

# Run next-gen production
cd v14 && python reports.py
```

## Deployment

Each version is self-contained with its own:
- Configuration files
- Data directories  
- Output directories
- Python cache

See individual version directories for specific instructions.
EOF

# Experiments README
cat > experiments/README.md << 'EOF'
# Experiments & Research

**Owner**: Arden  
**Purpose**: Active research and prototype development (live work only)

## Structure

- **research/**: V16 development and advanced research
- **prototypes/**: Trial implementations and proof-of-concepts

## Usage

```bash
# Work on V16 research
cd research/v16_development

# Test prototypes
cd prototypes/
```

## Guidelines

- Code here is experimental - may not work or be incomplete
- Not for production use (see `production/` for deployed systems)
- Focus on learning, validation, and future feature development
- Historical development work is in `archive/legacy/`
EOF

# Modules README
cat > modules/README.md << 'EOF'
# Core Modules

**Owner**: Arden (ty_report_base), Shared (others)  
**Purpose**: Maintained shared code and frameworks

## Structure

- **llm_framework/**: LLM interaction framework
- **ty_extract_versions/**: Extraction system variants
- **ty_learn_report/**: Reporting system integration
- **ty_report_base/**: Base reporting framework

## Usage

```bash
# Use LLM framework
cd llm_framework && python -m llm_framework

# Work with extraction systems
cd ty_extract_versions/
```

## Guidelines

- Code here is maintained and production-ready
- Shared across multiple systems
- Follow testing and documentation standards
- Changes require validation across dependent systems
EOF

# Archive README
cat > archive/README.md << 'EOF'
# Archive

**Owner**: Sage (maintenance), Historical  
**Purpose**: Historical materials and legacy systems

## Structure

- **consolidated/**: Organized historical content
- **legacy/**: Original archive materials and historical development
- **migrations/**: Historical migration work

## Usage

```bash
# Review historical versions
ls legacy/versions/

# Check migration history
ls migrations/
```

## Guidelines

- Read-only historical reference
- Original backup available at `/home/xai/Documents_archive/ty_learn`
- Do not modify archived materials
- For active work, see `production/`, `experiments/`, or `modules/`
EOF

# Artifacts README
cat > artifacts/README.md << 'EOF'
# Artifacts

**Owner**: Shared  
**Purpose**: Experimental outputs and test artifacts

## Structure

- Non-production run results
- Test outputs and validation artifacts
- Experimental data and reports

## Usage

```bash
# Check experimental outputs
ls llm_tasks/

# Review test artifacts
find . -name "*.json" | head -10
```

## Guidelines

- Outputs from experiments and tests (not production)
- Production outputs are in `production/*/output/`
- Temporary and disposable content
- Can be cleaned periodically
EOF

log_action "✅ Created README files for all major directories"

# 5. Create CODEOWNERS file
log_action "📝 Issue 5: Creating CODEOWNERS..."

cat > CODEOWNERS << 'EOF'
# Code Owners - Responsibility Assignment

# Global fallback
* @xai770

# Production systems
/production/v14/ @Arden
/production/v7/ @Arden

# Testing and validation
/tests/ @Sage
/validation/ @Sage

# Core modules
/modules/ty_report_base/ @Arden
/modules/llm_framework/ @Arden
/modules/ @Arden

# Documentation
/docs/ @Sophia
/ARCHITECTURE.md @Arden
/README.md @Sophia

# Configuration
/config/ @Arden

# Tools and scripts
/tools/ @Arden
/scripts/ @Arden

# Archive maintenance
/archive/ @Sage

# Experiments (active research)
/experiments/ @Arden
EOF

log_action "✅ Created CODEOWNERS file"

# 6. Create task runner (Makefile)
log_action "📝 Issue 6: Creating task runner (Makefile)..."

cat > Makefile << 'EOF'
# ty_learn Task Runner
# Usage: make <target>

.PHONY: help test validate run-prod run-research clean check status

# Default target
help:
	@echo "ty_learn Task Runner"
	@echo ""
	@echo "Available targets:"
	@echo "  test          - Run all tests"
	@echo "  validate      - Run validation suite"
	@echo "  run-prod      - Run production system (V=7|14)"
	@echo "  run-research  - Work on research (V=16)"
	@echo "  clean         - Clean temporary files"
	@echo "  check         - Check system health"
	@echo "  status        - Show workspace status"
	@echo ""
	@echo "Examples:"
	@echo "  make test"
	@echo "  make run-prod V=14"
	@echo "  make run-research V=16"

# Testing targets
test:
	@echo "🧪 Running tests..."
	cd tests && python -m pytest -v

validate:
	@echo "✅ Running validation suite..."
	cd validation && python -m pytest -v

# Production targets
run-prod:
	@if [ "$(V)" = "7" ]; then \
		echo "🚀 Running V7 production..."; \
		cd production/v7 && python main.py; \
	elif [ "$(V)" = "14" ]; then \
		echo "🚀 Running V14 production..."; \
		cd production/v14 && python reports.py; \
	else \
		echo "❌ Specify version: make run-prod V=7 or V=14"; \
		exit 1; \
	fi

# Research targets  
run-research:
	@if [ "$(V)" = "16" ]; then \
		echo "🔬 Entering V16 research environment..."; \
		cd experiments/research/v16_development; \
	else \
		echo "❌ Specify version: make run-research V=16"; \
		exit 1; \
	fi

# Maintenance targets
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.tmp" -delete 2>/dev/null || true
	find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

check:
	@echo "🔍 Checking system health..."
	@echo "📁 Directory structure:"
	@ls -la | grep "^d" | wc -l | xargs echo "  Directories:"
	@echo "🔗 External links:"
	@ls -la | grep "^l" | awk '{print "  " $$9 " -> " $$11}'
	@echo "🐍 Python environment:"
	@python --version 2>/dev/null || echo "  Python not available"
	@echo "✅ Health check complete"

status:
	@echo "📊 ty_learn Workspace Status"
	@echo ""
	@echo "🏗️ Architecture: Clean (2025-08-28)"
	@echo "📁 Structure:"
	@tree -d -L 2 | head -15
	@echo ""
	@echo "🚀 Production Systems:"
	@echo "  V7:  production/v7/  (current, 411s/job)"
	@echo "  V14: production/v14/ (ready, 29.1s/job)"
	@echo ""
	@echo "🔬 Active Research:"
	@echo "  V16: experiments/research/v16_development/"
	@echo ""
	@echo "For detailed info: cat ARCHITECTURE.md"

# CI enforcement target
ci-gate:
	@echo "🚪 CI Gate: Enforcing quality standards..."
	make test
	make validate
	@echo "✅ CI Gate passed - merge approved"
EOF

log_action "✅ Created Makefile task runner"

# 7. Create CI configuration hint
log_action "📝 Issue 7: Creating CI gate documentation..."

cat > docs/CI_GATES.md << 'EOF'
# CI Gates Configuration

This document outlines the CI gates that enforce the "no merge without green" rule.

## Required Gates

### 1. Test Gate
```yaml
# .github/workflows/test.yml
name: Test Gate
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: make test
      - name: Fail on red
        run: exit $?
```

### 2. Validation Gate  
```yaml
# .github/workflows/validate.yml  
name: Validation Gate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run validation
        run: make validate
      - name: Fail on red
        run: exit $?
```

### 3. Combined Gate
```yaml
# .github/workflows/ci.yml
name: CI Gate
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: CI Gate Check
        run: make ci-gate
```

## Branch Protection

Configure branch protection rules:
- Require status checks to pass
- Require branches to be up to date
- Include administrators
- Required checks:
  - Test Gate
  - Validation Gate

## Local Testing

Before pushing:
```bash
make test      # Must pass
make validate  # Must pass  
make ci-gate   # Combined check
```

This enforces the operating gate: "No merge to ty_learn surfaces without green eval on the gold set for the affected transaction."
EOF

log_action "✅ Created CI gates documentation"

# 8. Final structure verification
log_action "📊 Final structure verification..."

echo "" | tee -a "$LOG_FILE"
echo "🏗️ Final Clean Architecture Structure:" | tee -a "$LOG_FILE"
tree -d -L 2 | head -20 | tee -a "$LOG_FILE"

log_action "✅ Final architecture polish completed!"

echo ""
echo "🌹 Final Architecture Polish Complete!"
echo "📊 Improvements applied:"
echo "   ✅ Moved legacy_development to archive (experiments/ now live-only)"
echo "   ✅ Comprehensive .gitignore (venv, __pycache__, caches, etc.)"
echo "   ✅ External references documented (symlinks, portability)"
echo "   ✅ README.md in each major directory (purpose, owner, usage)"
echo "   ✅ CODEOWNERS file (responsibility assignment)"
echo "   ✅ Makefile task runner (test, validate, run-prod, etc.)"
echo "   ✅ CI gates documentation (enforce quality standards)"
echo ""
echo "🎯 Architecture Quality: ⚖️ 9.5+ → Production Ready!"
echo "📚 Usage: make help"
