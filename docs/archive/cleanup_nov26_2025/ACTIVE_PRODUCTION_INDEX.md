# Active Production Files (November 2025)

**Last Updated:** 2025-11-12 09:54  
**Purpose:** Quick reference for active production files after workspace cleanup

---

## 🚀 Daily Operations

### Automated Workflows
- `scripts/production/run_workflow_3001.sh` - Daily 08:00 cron job
- `tools/complete_job_processing_pipeline_compiled.py` - 15-stage pipeline (compiled)
- `tools/fake_job_detector_compiled.py` - IHL scoring (compiled)

### Monitoring & Backup
- `scripts/production/backup_by.sh` - Database backups
- `scripts/production/setup_cron.sh` - Cron configuration
- `monitor_org.sh` - System monitoring (root level)

---

## 📚 Core Documentation

### Primary References
- `docs/PROJECT_PLAN_TURING.md` - Overall project vision & roadmap
- `docs/TURING_SQL_COOKBOOK.md` - SQL query patterns & examples
- `docs/DATABASE_SCHEMA_GUIDE.md` - Complete schema reference
- `docs/WORKFLOW_CREATION_COOKBOOK.md` - How to build workflows

### Quick References
- `docs/___ARDEN_CHEAT_SHEET.md` - Daily operations guide
- `docs/ARDEN_QUICKREF_SCHEMA.md` - Schema quick reference
- `docs/TURING_ORCHESTRATOR_QUICKREF.md` - Orchestrator API
- `TURING_ORCHESTRATOR_COMPLETE.md` - Complete orchestrator guide (root level)

### Architecture & Philosophy
- `docs/WHAT_WE_ARE_REALLY_BUILDING.md` - Vision statement
- `docs/WHY_TURING.md` - Technical rationale
- `docs/ARCHITECTURE.md` - System architecture
- `ARCHITECTURE_PLAN.md` - Architecture plan (root level)

---

## ⚙️ Active Workflows

### Production Workflows
- `docs/workflows/3001_complete_job_processing_pipeline.md` - 15-stage complete pipeline
  - Steps 1: Fetch jobs
  - Steps 2-10: Workflow 1114 (extraction + skills)
  - Steps 11-12: Hybrid skills
  - Steps 13-15: Workflow 1124 (IHL scoring)

### Component Workflows
- `docs/workflows/1114_self_healing_dual_grader.md` - 9-stage extraction with QA
- `docs/workflows/1124_fake_job_detector.md` - 3-actor debate (IHL)
- `docs/workflows/1126_profile_extraction.md` - Profile processing (if exists)

---

## 🗄️ Database

### Schema & Migrations
- `migrations/057_rename_job_to_posting_consistency.sql` - **PENDING** (table renames)
- `sql/add_updated_at_trigger.sql` - Timestamp automation
- `sql/add_all_updated_at_triggers.sql` - Applied to 27 tables

### Backup Strategy
- Daily full backups: `backups/by_full_YYYYMMDD_HHMMSS.backup`
- Daily data-only: `backups/by_data_only_YYYYMMDD_HHMMSS.backup`
- Version backups: `/home/xai/Documents_Versions/ty_learn/`

---

## 🔧 Development Tools

### Batch Processing
- `scripts/batch/batch_process_postings.py` - Process multiple postings
- `scripts/batch/batch_run_ihl_analysis.sh` - Batch IHL scoring
- `tools/process_ihl_optimized.py` - Optimized IHL batch processor

### Testing & Validation
- `scripts/development/quick_status.sh` - Check system status
- `scripts/development/manual_prompt_validator.py` - Test prompts
- `test_autonomous_execution.py` - Orchestrator tests (root level)

### Migration Tools
- `scripts/migration/migrate_scripts_to_db.py` - Script → DB migration
- `scripts/migration/db_update_summary.py` - Migration reports
- `update_runner_schema.py` - Schema updates (root level)

---

## 📊 Data Quality

### Current Status (as of Nov 12, 2025)
- **IHL Scoring:** 1,797/1,900 postings (94.6%)
- **Skill Normalization:** 163/1,701 postings (9.6%) - **NEEDS WORK**
- **Score Distribution:** Range 3-7, Average 5.40
- **Data Sources:** Deutsche Bank (primary), more to come

### Quality Guides
- `docs/FUZZY_SKILL_MATCHING_GUIDE.md` - Skill matching algorithms
- `docs/DEUTSCHE_BANK_DATA_ANALYSIS_COOKBOOK.md` - Data source analysis
- `COLUMN_CLEANUP_RECOMMENDATION.md` - Schema cleanup notes (root level)

---

## 🎯 Next Steps

1. **Execute Migration 057** - Rename job_* tables to posting_*
2. **Skill Normalization** - Process 1,538 postings with orphaned skills
3. **Complete IHL Scoring** - Process remaining 103 postings
4. **Profile Import** - Import Gershon's profile with workflow 1126/1127
5. **Matching Engine** - Build profile ↔ posting matching

---

## 📁 Archive Locations

### Recently Archived (Nov 12, 2025)
- Historical docs: `archive/docs_nov12_2025/`
  - Session summaries
  - Completed workflow docs
  - Migration documentation
  - Historical guides
  - LLM session notes
  
- Legacy scripts: `archive/scripts_nov12_2025/legacy/`
  - Old recipe runners
  - Deprecated batch processors
  - Superseded workflows

### Older Archives
- `archive/legacy_docs/` - Pre-October documentation
- `archive/legacy_scripts/` - Pre-October scripts
- `archive/scripts_oct28_2025/` - October 28 snapshot

---

## 🆘 Help & References

### For Arden (AI Assistant)
- Start here: `docs/START_HERE_ARDEN.md`
- Quick ref: `docs/___ARDEN_CHEAT_SHEET.md`
- Schema: `docs/ARDEN_QUICKREF_SCHEMA.md`

### For Sage (Project Lead)
- Briefing: `SAGE_BRIEFING_TURING_SYSTEM.md`
- Handovers: `docs/handovers/`
- QA notes: `docs/FOR_SAGE_QA.md`

### For Protégé (Future Developers)
- Guide: `PROTEGE_GUIDE.md`
- Philosophy: `docs/philosophy/`
- Tool registry: `docs/TOOL_REGISTRY.md`

---

**Remember:** Everything is backed up in `/home/xai/Documents_Versions/ty_learn/`  
**Philosophy:** Fix issues at their root so we don't get confused later.
