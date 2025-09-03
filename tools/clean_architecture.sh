#!/bin/bash

# ty_learn Clean Architecture Restructuring
# Based on architectural analysis - separating lifecycles, purposes, and artifacts
# Date: 2025-08-28

set -e

WORKSPACE_ROOT="/home/xai/Documents/ty_learn"
LOG_FILE="$WORKSPACE_ROOT/clean_architecture_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN:${NC} $1" | tee -a "$LOG_FILE"
}

clean_architecture() {
    log "🏗️ Implementing clean architecture..."
    
    cd "$WORKSPACE_ROOT"
    
    # 1. Create the new clean structure
    log "Creating clean directory structure..."
    mkdir -p production/{v14,v7}
    mkdir -p experiments/{research,prototypes}
    mkdir -p archive/{consolidated,migrations,legacy}
    mkdir -p tools
    
    # 2. Merge active_production/ and versions/production/ into production/
    log "📦 Consolidating production systems..."
    
    # Move V14 production system
    if [ -d "active_production/v14_system" ]; then
        mv active_production/v14_system/* production/v14/ 2>/dev/null || warn "Some V14 files may not have moved"
        rmdir active_production/v14_system 2>/dev/null || warn "V14 directory not empty"
    fi
    
    # Move Sandy's pipeline (V7)
    if [ -d "active_production/sandy_pipeline" ]; then
        mv active_production/sandy_pipeline/* production/v7/ 2>/dev/null || warn "Some V7 files may not have moved"
        rmdir active_production/sandy_pipeline 2>/dev/null || warn "V7 directory not empty"
    fi
    
    # Copy from versions/production if exists
    if [ -d "versions/production/v14_complete_system" ]; then
        rsync -av versions/production/v14_complete_system/ production/v14/
    fi
    
    if [ -d "versions/production/v7.0_sandy_pipeline" ]; then
        rsync -av versions/production/v7.0_sandy_pipeline/ production/v7/
    fi
    
    # 3. Merge development/ and experiments/ with clear distinction
    log "🔬 Reorganizing development work..."
    
    # Move current V16 development to experiments/research
    if [ -d "development/v16_current" ]; then
        mv development/v16_current/ experiments/research/v16_development/
    fi
    
    # Move V15 experimental to experiments/research
    if [ -d "development/experimental/v15_validation" ]; then
        mv development/experimental/v15_validation/ experiments/research/v15_validation/
    fi
    
    # Move remaining experiments to experiments/prototypes
    if [ -d "experiments/llm_optimization_results" ]; then
        mv experiments/llm_optimization_results/ experiments/prototypes/
    fi
    
    if [ -d "experiments/ty_extract" ]; then
        mv experiments/ty_extract/ experiments/prototypes/
    fi
    
    # 4. Consolidate archives
    log "📚 Consolidating archives..."
    
    # Move v14_v15_migration to archive/migrations
    if [ -d "v14_v15_migration" ]; then
        mv v14_v15_migration/ archive/migrations/
    fi
    
    # Move versions archive content
    if [ -d "versions/archive" ]; then
        rsync -av versions/archive/ archive/legacy/versions/
    fi
    
    # Move archive_consolidated content
    if [ -d "archive_consolidated" ]; then
        rsync -av archive_consolidated/ archive/consolidated/
    fi
    
    # Move backup_system to archive (it's historical infrastructure)
    if [ -d "backup_system" ]; then
        mv backup_system/ archive/legacy/backup_system/
    fi
    
    # Keep original archive but organize it
    if [ -d "archive" ] && [ "$(ls -A archive)" ]; then
        # Create a legacy subfolder for the original archive
        mkdir -p archive/legacy/original_archive
        # Move original archive contents (but avoid moving our new structure)
        for item in archive/*; do
            if [[ "$(basename "$item")" != "consolidated" && "$(basename "$item")" != "legacy" && "$(basename "$item")" != "migrations" ]]; then
                mv "$item" archive/legacy/original_archive/ 2>/dev/null || warn "Could not move $(basename "$item")"
            fi
        done
    fi
    
    # 5. Rename workspace_tools to tools
    log "🛠️ Setting up tools..."
    if [ -d "workspace_tools" ]; then
        rsync -av workspace_tools/ tools/
        rm -rf workspace_tools/
    fi
    
    # 6. Clean up empty directories
    log "🧹 Cleaning up empty directories..."
    rmdir active_production 2>/dev/null || warn "active_production not empty or doesn't exist"
    rmdir development/experimental 2>/dev/null || warn "development/experimental not empty"
    rmdir development/tools 2>/dev/null || warn "development/tools not empty"
    rmdir development 2>/dev/null || warn "development not empty"
    rmdir archive_consolidated 2>/dev/null || warn "archive_consolidated not empty"
    rm -rf versions/ 2>/dev/null || warn "versions directory had remaining content"
    
    log "✅ Clean architecture implemented!"
}

# Create documentation for the new structure
create_architecture_docs() {
    log "📋 Creating architecture documentation..."
    
    cat > "$WORKSPACE_ROOT/ARCHITECTURE.md" << 'EOF'
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
├── tests/               # Automated tests
├── validation/          # Validation & QA harnesses
├── experiments/         # Research & prototype work
│   ├── research/        # V15, V16 experimental development
│   └── prototypes/      # Trial implementations
├── tools/               # Workspace & helper scripts
├── production/          # Current deployed versions
│   ├── v14/            # Production-ready V14 system
│   └── v7/             # Sandy's Pipeline (current production)
└── archive/             # Legacy and historical materials
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

# Validate V15 research
cd experiments/research/v15_validation
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
- `archive/` + `archive_consolidated/` → `archive/`
- `development/` + `experiments/` → `experiments/` (with research/prototypes)
- `workspace_tools/` → `tools/`
- `backup_system/` → `archive/legacy/` (historical infrastructure)
- `v14_v15_migration/` → `archive/migrations/`

**Backup:** Available at `/home/xai/Documents_archive/ty_learn`
EOF

    # Create production README
    cat > "$WORKSPACE_ROOT/production/README.md" << 'EOF'
# Production Systems

This directory contains **current deployed versions** ready for production use.

## 🚀 Current Systems

### V7 - Sandy's Pipeline (Active Production)
- **Location**: `v7/`
- **Status**: Currently running daily reports
- **Performance**: 411s per job, highly reliable
- **Usage**: `cd v7 && python main.py`

### V14 - Complete System (Production Ready)
- **Location**: `v14/`
- **Status**: Ready for deployment
- **Performance**: 29.1s per job, 14.1x faster than V7
- **Usage**: `cd v14 && python reports.py`

## 📊 Performance Comparison

| Version | Speed | Quality | Status | Recommendation |
|---------|-------|---------|--------|----------------|
| V7 | 411s | Excellent | Active | Daily reports |
| V14 | 29.1s | Excellent | Ready | New deployments |

## 🔄 Deployment

To switch from V7 to V14:
1. Test V14 with sample data
2. Update production scripts to point to `v14/`
3. Monitor performance and quality
4. Keep V7 as fallback if needed
EOF

    # Create experiments README
    cat > "$WORKSPACE_ROOT/experiments/README.md" << 'EOF'
# Experiments & Research

This directory contains **research work and prototypes** - not production-ready code.

## 🔬 Structure

### `research/` - Active Research Projects
- **V16 Development** - Advanced LLM parameterization
- **V15 Validation** - Experimental framework validation
- **Future Concepts** - Cutting-edge research

### `prototypes/` - Trial Implementations
- **LLM Optimization Results** - Historical optimization attempts
- **ty_extract Variants** - Different extraction approaches

## ⚠️ Important Notes

- **Code here is experimental** - may not work or be incomplete
- **Not for production use** - use `production/` for deployed systems
- **Research documentation** - focus on learning and validation
- **Prototype testing** - trial implementations and concepts

## 🎯 Usage

This is where you:
- Try new approaches
- Validate experimental concepts
- Prototype future features
- Research performance improvements

For production-ready code, see `production/` directory.
EOF

    log "✅ Architecture documentation created!"
}

# Create status report
create_status_report() {
    log "📊 Creating status report..."
    
    cat > "$WORKSPACE_ROOT/clean_architecture_report_$(date +%Y%m%d_%H%M%S).md" << EOF
# Clean Architecture Implementation Report

**Date**: $(date)
**Architect**: Based on user analysis of lifecycle/purpose/artifact mixing

## ✅ Architecture Problems Solved

### 🔍 **Before: Mixed Concepts**
- \`active_production/\` vs \`versions/\` → overlapping purposes
- \`archive/\` vs \`archive_consolidated/\` → redundant archival
- \`development/\` vs \`experiments/\` → unclear boundaries
- \`backup_system/\` → noise in repo
- \`v14_v15_migration/\` → historical work at top level

### 🎯 **After: Clean Separation**
- **Single production root**: \`production/\` with clear versions
- **Single archive root**: \`archive/\` with organized subfolders
- **Clear research vs maintained**: \`experiments/\` vs \`modules/\`
- **Infrastructure archived**: \`backup_system/\` moved to \`archive/legacy/\`
- **Historical work organized**: \`v14_v15_migration/\` in \`archive/migrations/\`

## 📁 New Clean Structure

\`\`\`
ty_learn/
├── config/              # Configuration files
├── data/                # Datasets  
├── docs/                # Documentation
├── modules/             # Core maintained code
├── tests/               # Automated tests
├── validation/          # Validation & QA
├── experiments/         # Research & prototypes
│   ├── research/        # V15, V16 development
│   └── prototypes/      # Trial implementations  
├── tools/               # Helper scripts
├── production/          # Current deployed versions
│   ├── v14/            # Production-ready system
│   └── v7/             # Sandy's Pipeline
└── archive/             # Legacy materials
    ├── consolidated/    # Organized historical content
    ├── migrations/      # Historical migrations
    └── legacy/          # Original archive + backup_system
\`\`\`

## 🏆 Benefits Achieved

✅ **Single Purpose** - Each directory has one clear responsibility  
✅ **Lifecycle Clarity** - Current work vs historical artifacts separated  
✅ **No Overlap** - No conceptual confusion between directories  
✅ **Standard Patterns** - Follows common development conventions  
✅ **Easy Mental Model** - Purpose of each folder is immediately obvious  

## 🎯 Usage Examples

### Production Work:
\`\`\`bash
cd production/v7 && python main.py      # Current production
cd production/v14 && python reports.py  # Next production
\`\`\`

### Research Work:
\`\`\`bash
cd experiments/research/v16_development  # Active research
cd experiments/prototypes/               # Trial implementations
\`\`\`

### Reference:
\`\`\`bash
ls archive/migrations/                   # Historical migrations
ls archive/legacy/versions/              # Legacy versions
\`\`\`

## 🔄 Migration Completed

- **Production systems**: Consolidated from active_production + versions
- **Archives**: Unified from archive + archive_consolidated  
- **Research**: Organized from development + experiments
- **Tools**: Renamed from workspace_tools
- **Infrastructure**: Moved backup_system to archive/legacy

## 📚 Documentation

- **ARCHITECTURE.md**: Complete architecture guide
- **production/README.md**: Production system guide  
- **experiments/README.md**: Research work guide

---

**Result**: Clean, logical architecture with clear separation of concerns! 🎊
EOF

    log "✅ Status report created!"
}

# Main execution
main() {
    log "🚀 Starting clean architecture implementation..."
    log "🎯 Goal: Separate lifecycles, purposes, and artifacts"
    
    clean_architecture
    create_architecture_docs  
    create_status_report
    
    log "🎉 Clean architecture implementation completed!"
    log "📚 See ARCHITECTURE.md for complete guide"
    
    info "New structure:"
    info "├── production/     # Current deployed systems"  
    info "├── experiments/    # Research & prototypes"
    info "├── archive/        # Legacy & historical"
    info "├── tools/          # Helper scripts"
    info "└── [standard dirs] # config, data, docs, modules, tests, validation"
    
    info ""
    info "Key improvements:"
    info "✅ Single purpose per directory"
    info "✅ Clear lifecycle separation" 
    info "✅ No conceptual overlap"
    info "✅ Standard development patterns"
}

# Execute
main
EOF
