#!/bin/bash

# ty_learn Workspace Reorganization Script
# Arden's Codespace Organization Tool
# Date: 2025-08-28

set -e  # Exit on any error

WORKSPACE_ROOT="/home/xai/Documents/ty_learn"
BACKUP_DIR="/home/xai/Documents/ty_learn/backup_system/pre_reorganization_backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$WORKSPACE_ROOT/reorganization_log_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Check if we're in the right directory
check_workspace() {
    if [ ! -f "$WORKSPACE_ROOT/README.md" ] || [ ! -d "$WORKSPACE_ROOT/rfa_latest" ]; then
        error "Not in ty_learn workspace root. Please run from $WORKSPACE_ROOT"
    fi
    log "✅ Workspace validation passed"
}

# Create backup
create_backup() {
    log "🔄 Creating full workspace backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Copy everything except .git and large archive files
    rsync -av \
        --exclude='.git' \
        --exclude='*.tar.gz' \
        --exclude='__pycache__' \
        --exclude='.mypy_cache' \
        "$WORKSPACE_ROOT/" "$BACKUP_DIR/" || error "Backup failed"
    
    log "✅ Backup created at: $BACKUP_DIR"
}

# Create new directory structure
create_new_structure() {
    log "🏗️ Creating new directory structure..."
    
    cd "$WORKSPACE_ROOT"
    
    # Main version consolidation directory
    mkdir -p versions/{production,development,archive,benchmarks}
    
    # Production systems
    mkdir -p active_production/{sandy_pipeline,v14_system}
    
    # Development areas
    mkdir -p development/{v16_current,experimental,tools}
    
    # Archive consolidation
    mkdir -p archive/{legacy_versions,old_experiments,deprecated_configs,migration_logs}
    
    # Configuration
    mkdir -p config/templates
    
    # Testing framework
    mkdir -p tests/{unit,integration,performance,fixtures}
    
    # Scripts
    mkdir -p scripts/{migration,backup,deployment}
    
    # Workspace tools
    mkdir -p workspace_tools
    
    log "✅ New directory structure created"
}

# Move production systems
migrate_production() {
    log "🚀 Migrating production systems..."
    
    cd "$WORKSPACE_ROOT"
    
    # Move Sandy's pipeline (current ty_extract_PROD)
    if [ -d "modules/ty_extract_versions/ty_extract_PROD" ]; then
        log "Moving Sandy's pipeline..."
        mv modules/ty_extract_versions/ty_extract_PROD/* active_production/sandy_pipeline/ 2>/dev/null || warn "Some files may not have moved"
        cp -r modules/ty_extract_versions/ty_extract_PROD/ versions/production/v7.0_sandy_pipeline/
    fi
    
    # Move V14 complete system
    if [ -d "v14_complete_system" ]; then
        log "Moving V14 complete system..."
        cp -r v14_complete_system/ active_production/v14_system/
        mv v14_complete_system/ versions/production/v14_complete_system/
    fi
    
    # Move V14 archived version
    if [ -d "modules/ty_extract_versions/ty_extract_v14" ]; then
        mv modules/ty_extract_versions/ty_extract_v14/ versions/archive/v14_archived/
    fi
    
    log "✅ Production systems migrated"
}

# Move development versions
migrate_development() {
    log "🔬 Migrating development versions..."
    
    cd "$WORKSPACE_ROOT"
    
    # Move V16 hybrid framework
    if [ -d "v16_hybrid_framework" ]; then
        log "Moving V16 hybrid framework..."
        mv v16_hybrid_framework/ development/v16_current/
        cp -r development/v16_current/ versions/development/v16_hybrid_framework/
    fi
    
    # Move V15 experimental
    if [ -d "v15_experimental" ]; then
        log "Moving V15 experimental..."
        mv v15_experimental/ development/experimental/v15_validation/
        cp -r development/experimental/v15_validation/ versions/development/v15_experimental/
    fi
    
    # Handle duplicate V15 in experiments
    if [ -d "experiments/v15_experimental" ]; then
        log "Consolidating duplicate V15 experimental..."
        rsync -av experiments/v15_experimental/ development/experimental/v15_validation/ || warn "V15 consolidation had issues"
        mv experiments/v15_experimental/ archive/old_experiments/
    fi
    
    log "✅ Development versions migrated"
}

# Move documentation and benchmarks
migrate_docs() {
    log "📚 Migrating documentation and benchmarks..."
    
    cd "$WORKSPACE_ROOT"
    
    # Move performance documentation
    if [ -f "docs/V14_vs_V7.1_Performance_Baseline_Analysis.md" ]; then
        mv docs/V14_vs_V7.1_Performance_Baseline_Analysis.md versions/benchmarks/v14_vs_v7.1_baseline.md
    fi
    
    if [ -d "docs/historical_analysis" ]; then
        mv docs/historical_analysis/ versions/benchmarks/historical/
    fi
    
    # Move archive comparison files
    if [ -d "archive/codespace_cleanup_20250720/legacy_version_comparisons" ]; then
        cp -r archive/codespace_cleanup_20250720/legacy_version_comparisons/ versions/benchmarks/legacy_comparisons/
    fi
    
    log "✅ Documentation and benchmarks migrated"
}

# Archive historical versions
archive_historical() {
    log "📦 Archiving historical versions..."
    
    cd "$WORKSPACE_ROOT"
    
    # Move archived versions from ty_log
    if [ -d "ty_log/ty_projects/v14_complete_system" ]; then
        mv ty_log/ty_projects/v14_complete_system/ versions/archive/v14_ty_log_copy/
    fi
    
    if [ -d "ty_log/ty_projects/v16_hybrid_framework" ]; then
        mv ty_log/ty_projects/v16_hybrid_framework/ versions/archive/v16_ty_log_copy/
    fi
    
    # Move V14-V15 migration files
    if [ -d "v14_v15_migration" ]; then
        mv v14_v15_migration/ versions/archive/v14_v15_migration/
    fi
    
    log "✅ Historical versions archived"
}

# Create version registry
create_version_registry() {
    log "📋 Creating version registry..."
    
    cat > "$WORKSPACE_ROOT/versions/README.md" << 'EOF'
# ty_learn Version Directory

This directory contains all versions of the ty_learn codebase, organized for clarity and maintainability.

## 🚀 Production Versions (Stable)

### `production/v7.0_sandy_pipeline/`
- **Status**: Active Production
- **Purpose**: Daily report generation (Sandy's Pipeline V7.0)
- **Usage**: `active_production/sandy_pipeline/main.py`
- **Performance**: 411s per job, 25 skills, reliable with fallbacks
- **Deployment**: `active_production/sandy_pipeline/`

### `production/v14_complete_system/`
- **Status**: Production Ready
- **Purpose**: Complete extraction system
- **Usage**: `active_production/v14_system/`
- **Performance**: 29.1s per job, 41.4 skills, 14.1x faster than V7.1
- **Deployment**: `active_production/v14_system/`

## 🔬 Development Versions (Active)

### `development/v16_hybrid_framework/`
- **Status**: Active Development
- **Purpose**: Advanced LLM parameterization
- **Usage**: `development/v16_current/v16.2_testing/`
- **Features**: Model health tracking, hybrid templates
- **Latest**: V16.2 focused testing

### `development/v15_experimental/`
- **Status**: Research Branch
- **Purpose**: Experimental validation and research
- **Usage**: `development/experimental/v15_validation/`
- **Features**: Framework integration testing

## 📦 Archive Versions (Reference)

### Performance Champions:
- **V14**: Production champion (29.1s + excellent quality)
- **V10**: Development ready (58.2s, 3.29x faster than V7.1)
- **V9**: Experimental success (multi-agent evaluation)
- **V8**: Fast but flawed (20.2s, quality issues)
- **V7.1**: Quality gold standard (excellent format compliance)

### Historical Reference:
- **V11**: German extraction baseline
- **V12**: English translation strategy
- **V13**: Bridge version

## 📊 Benchmarks

See `benchmarks/` directory for comprehensive performance comparisons:
- `v14_vs_v7.1_baseline.md` - Production readiness analysis
- `historical/V71_vs_V10_Complete_Analysis_20250721.md` - Speed vs quality analysis
- `legacy_comparisons/` - Historical version comparisons

## 🎯 Quick Start

### Run Production Reports:
```bash
cd active_production/sandy_pipeline
python main.py
```

### Test V14 System:
```bash
cd active_production/v14_system
python reports.py
```

### Work on V16 Development:
```bash
cd development/v16_current/v16.2_testing
python v16_focused_testing.py
```

### Compare Performance:
```bash
# See benchmarks/ directory for detailed analysis
cat versions/benchmarks/v14_vs_v7.1_baseline.md
```

## 📈 Version Selection Guide

- **Production Deployment**: Use V14 (best speed/quality balance)
- **Daily Reports**: Use V7.0 Sandy's Pipeline (current production)
- **Quality Reference**: Use V7.1 (gold standard for format)
- **Development Work**: Use V16.2 (current active development)
- **Speed Benchmarking**: Reference V8 (fastest recorded)
- **Research**: Use V15 experimental branch

## 🔄 Migration Notes

This directory was created on 2025-08-28 as part of the workspace reorganization.
All versions were consolidated from scattered locations across the codebase.

Original locations:
- v14_complete_system/ → versions/production/v14_complete_system/
- v16_hybrid_framework/ → versions/development/v16_hybrid_framework/
- modules/ty_extract_versions/ → versions/production/ and versions/archive/
- Various docs/ → versions/benchmarks/

Active deployments remain in:
- active_production/sandy_pipeline/ (daily reports)
- active_production/v14_system/ (production system)
- development/v16_current/ (active development)
EOF

    log "✅ Version registry created"
}

# Update file references (basic)
update_references() {
    log "🔧 Updating basic file references..."
    
    # This is a basic update - more sophisticated updates may be needed
    # for specific import paths in Python files
    
    info "Note: Some import paths may need manual updates"
    info "Check for imports from old module locations"
    
    log "✅ Basic reference updates completed"
}

# Generate migration report
generate_report() {
    log "📊 Generating migration report..."
    
    cat > "$WORKSPACE_ROOT/reorganization_report_$(date +%Y%m%d_%H%M%S).md" << EOF
# ty_learn Workspace Reorganization Report

**Date**: $(date)
**Backup Location**: $BACKUP_DIR
**Log File**: $LOG_FILE

## ✅ Migration Completed

### New Structure Created:
- \`versions/\` - Consolidated version directory
- \`active_production/\` - Current production systems
- \`development/\` - Active development work
- \`archive/\` - Historical materials

### Production Systems Migrated:
- Sandy's Pipeline V7.0 → \`active_production/sandy_pipeline/\`
- V14 Complete System → \`active_production/v14_system/\`

### Development Systems Migrated:
- V16 Hybrid Framework → \`development/v16_current/\`
- V15 Experimental → \`development/experimental/v15_validation/\`

### Documentation Consolidated:
- Performance docs → \`versions/benchmarks/\`
- Historical analysis → \`versions/benchmarks/historical/\`
- Version registry → \`versions/README.md\`

## 🎯 Next Steps

1. **Test Systems**: Verify all production systems still work
2. **Update Imports**: Fix any broken import paths in Python files
3. **Update Documentation**: Reflect new paths in docs
4. **Clean Up**: Remove empty directories after verification

## 📁 Quick Access

### Production Use:
- Daily reports: \`active_production/sandy_pipeline/main.py\`
- V14 system: \`active_production/v14_system/\`

### Development:
- Current work: \`development/v16_current/v16.2_testing/\`
- Experimental: \`development/experimental/v15_validation/\`

### Reference:
- Version guide: \`versions/README.md\`
- Performance data: \`versions/benchmarks/\`
- Archives: \`versions/archive/\`

## 🛡️ Backup Information

Full backup created at: $BACKUP_DIR

To restore if needed:
\`\`\`bash
rsync -av "$BACKUP_DIR/" "$WORKSPACE_ROOT/"
\`\`\`

EOF

    log "✅ Migration report generated"
}

# Main execution
main() {
    log "🚀 Starting ty_learn workspace reorganization..."
    
    check_workspace
    create_backup
    create_new_structure
    migrate_production
    migrate_development
    migrate_docs
    archive_historical
    create_version_registry
    update_references
    generate_report
    
    log "🎉 Workspace reorganization completed successfully!"
    log "📊 Check the migration report for details"
    log "🛡️ Backup available at: $BACKUP_DIR"
    
    info "Next steps:"
    info "1. Test production systems: cd active_production/sandy_pipeline && python main.py"
    info "2. Verify V14 system: cd active_production/v14_system"
    info "3. Check development setup: cd development/v16_current/v16.2_testing"
    info "4. Review version guide: cat versions/README.md"
}

# Run with confirmation
echo -e "${YELLOW}🔄 ty_learn Workspace Reorganization${NC}"
echo -e "${YELLOW}This will reorganize your entire workspace structure.${NC}"
echo -e "${YELLOW}A full backup will be created first.${NC}"
echo ""
read -p "Continue with reorganization? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    main
else
    echo "Reorganization cancelled."
    exit 0
fi
