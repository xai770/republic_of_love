# Disaster Recovery Plan - Full System Restore

**Date:** November 19, 2025  
**Purpose:** Complete restoration instructions if event sourcing migration fails catastrophically  
**Philosophy:** "Hope for the best, plan for the worst"

---

## Current System State (Pre-Event Sourcing)

**Working Components:**
- ✅ Workflow 3001 running successfully (2062 postings)
- ✅ Checkpoint-first architecture (all state in `posting_state_checkpoints`)
- ✅ Model-first batching (efficient GPU usage)
- ✅ Recent fixes: chunked batching, retry logic, configurable circuit breaker

**Database Schema:**
- `posting_state_checkpoints` - Primary state source
- `postings` - Job posting data (input only, never read for state)
- `workflows`, `conversations`, `workflow_conversations` - Workflow definitions
- `actors` - LLM/script actor configs
- `workflow_runs` - Workflow execution tracking

**Code Version:**
- Repository: `republic_of_love` (xai770)
- Branch: `master`
- Key files:
  - `core/workflow_executor.py` (1452 lines)
  - `core/model_batch_executor.py` (647 lines)
  - `core/checkpoint_utils.py` (321 lines)

---

## Full Backup Procedure

### 1. Database Backup

```bash
# Complete PostgreSQL dump
pg_dump -U base_admin -d turing -F c -b -v \
  -f /home/xai/backups/turing_pre_event_sourcing_$(date +%Y%m%d_%H%M%S).backup

# Schema-only dump (for reference)
pg_dump -U base_admin -d turing -s \
  -f /home/xai/backups/turing_schema_$(date +%Y%m%d_%H%M%S).sql

# Data-only dump (for partial restore)
pg_dump -U base_admin -d turing -a \
  -f /home/xai/backups/turing_data_$(date +%Y%m%d_%H%M%S).sql

# Critical tables only (fastest restore)
pg_dump -U base_admin -d turing -F c \
  -t posting_state_checkpoints \
  -t postings \
  -t workflows \
  -t conversations \
  -t workflow_conversations \
  -t actors \
  -t workflow_runs \
  -f /home/xai/backups/turing_critical_tables_$(date +%Y%m%d_%H%M%S).backup
```

### 2. Code Backup

```bash
# Git commit current state
cd /home/xai/Documents/ty_wave
git add -A
git commit -m "Pre-event sourcing snapshot - working state"
git tag pre-event-sourcing-$(date +%Y%m%d)

# Create tarball (in case git gets corrupted)
cd /home/xai/Documents
tar -czf ty_wave_backup_$(date +%Y%m%d_%H%M%S).tar.gz ty_wave/

# Copy to safe location
cp ty_wave_backup_*.tar.gz /home/xai/backups/
```

### 3. Documentation Backup

```bash
# Export current architecture docs
cd /home/xai/Documents/ty_wave/docs
tar -czf /home/xai/backups/docs_$(date +%Y%m%d_%H%M%S).tar.gz *.md

# Export SQL migrations
cd /home/xai/Documents/ty_wave/sql
tar -czf /home/xai/backups/sql_$(date +%Y%m%d_%H%M%S).tar.gz *
```

### 4. Verify Backups

```bash
# Check backup files exist and are not empty
ls -lh /home/xai/backups/ | tail -10

# Test database backup is valid
pg_restore --list /home/xai/backups/turing_pre_event_sourcing_*.backup | head -20

# Test code tarball is valid
tar -tzf /home/xai/backups/ty_wave_backup_*.tar.gz | head -20
```

---

## Complete Restore Procedure

### Scenario 1: Database Corrupted, Code Intact

**Symptoms:**
- Event sourcing migration created inconsistent state
- Projections don't match reality
- Checkpoints deleted or corrupted
- Can't process postings

**Solution: Restore Database Only**

```bash
# 1. Stop all running workflows
pkill -f "workflow_executor"
pkill -f "wave_batch_processor"

# 2. Drop and recreate database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS turing;"
sudo -u postgres psql -c "CREATE DATABASE turing OWNER base_admin;"

# 3. Restore from backup
pg_restore -U base_admin -d turing -v \
  /home/xai/backups/turing_pre_event_sourcing_YYYYMMDD_HHMMSS.backup

# 4. Verify restoration
psql -U base_admin -d turing -c "SELECT COUNT(*) FROM posting_state_checkpoints;"
psql -U base_admin -d turing -c "SELECT COUNT(*) FROM postings;"

# 5. Restart workflow
cd /home/xai/Documents/ty_wave
nohup python3 -m core.workflow_executor --workflow 3001 > logs/workflow_3001_RESTORED_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

### Scenario 2: Code Corrupted, Database Intact

**Symptoms:**
- Event sourcing code has bugs
- EventStore class causing errors
- Workflow executor crashes
- Import errors

**Solution: Restore Code Only**

```bash
# 1. Stop all running workflows
pkill -f "workflow_executor"

# 2. Backup current broken code (for forensics)
cd /home/xai/Documents
mv ty_wave ty_wave_BROKEN_$(date +%Y%m%d_%H%M%S)

# 3. Restore from tarball
cd /home/xai/Documents
tar -xzf /home/xai/backups/ty_wave_backup_YYYYMMDD_HHMMSS.tar.gz

# 4. Or restore from Git tag
cd /home/xai/Documents/ty_wave
git checkout pre-event-sourcing-YYYYMMDD

# 5. Verify restoration
python3 -c "from core.workflow_executor import WorkflowExecutor; print('✅ Import OK')"
python3 -c "from core.model_batch_executor import ModelBatchExecutor; print('✅ Import OK')"

# 6. Restart workflow
nohup python3 -m core.workflow_executor --workflow 3001 > logs/workflow_3001_RESTORED_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

### Scenario 3: Everything Corrupted (Nuclear Option)

**Symptoms:**
- Both database and code broken
- Can't figure out what went wrong
- System completely unusable
- "Burn it all down and start over"

**Solution: Full System Restore**

```bash
# 1. STOP EVERYTHING
pkill -f "workflow_executor"
pkill -f "python"  # Careful: stops all Python processes

# 2. Restore Database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS turing;"
sudo -u postgres psql -c "CREATE DATABASE turing OWNER base_admin;"
pg_restore -U base_admin -d turing -v \
  /home/xai/backups/turing_pre_event_sourcing_YYYYMMDD_HHMMSS.backup

# 3. Restore Code
cd /home/xai/Documents
rm -rf ty_wave  # Nuclear: delete everything
tar -xzf /home/xai/backups/ty_wave_backup_YYYYMMDD_HHMMSS.tar.gz

# 4. Restore Python Environment
cd /home/xai/Documents/ty_wave
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary structlog

# 5. Verify Everything
psql -U base_admin -d turing -c "SELECT COUNT(*) FROM posting_state_checkpoints;"
python3 -c "from core.workflow_executor import WorkflowExecutor; print('✅ Code OK')"

# 6. Test with Single Posting
python3 -c "
from core.checkpoint_utils import get_posting_current_state
state = get_posting_current_state(3001)
print(f'✅ Posting 3001 state: {state}')
"

# 7. Restart Workflow
nohup python3 -m core.workflow_executor --workflow 3001 > logs/workflow_3001_RESTORED_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 8. Monitor for 5 minutes
tail -f logs/workflow_3001_RESTORED_*.log
```

---

## Partial Restore (Surgical Recovery)

### Restore Only Checkpoints Table

```bash
# If only posting_state_checkpoints is corrupted
pg_restore -U base_admin -d turing -v \
  -t posting_state_checkpoints \
  --clean \
  /home/xai/backups/turing_critical_tables_YYYYMMDD_HHMMSS.backup
```

### Restore Single Posting State

```sql
-- If a specific posting got corrupted during event migration
-- Manually insert from backup

-- 1. Query backup database
psql -U base_admin -d turing_backup -c "
SELECT * FROM posting_state_checkpoints 
WHERE posting_id = 3001;
"

-- 2. Insert into current database
INSERT INTO posting_state_checkpoints (
    posting_id, conversation_id, execution_order, 
    state_snapshot, is_terminal, checkpoint_timestamp
)
VALUES (
    3001, 4, 4,
    '{"outputs": {...}, "execution_sequence": [1,2,3,4]}'::JSONB,
    false, NOW()
);
```

---

## Pre-Flight Checklist (Before Event Sourcing Migration)

**Run these BEFORE starting event sourcing work:**

```bash
#!/bin/bash
# pre_flight_backup.sh

echo "=== PRE-EVENT SOURCING BACKUP ==="
echo "Date: $(date)"

# 1. Database backup
echo "📦 Backing up database..."
pg_dump -U base_admin -d turing -F c -b -v \
  -f /home/xai/backups/turing_pre_event_sourcing_$(date +%Y%m%d_%H%M%S).backup

# 2. Code backup
echo "📦 Backing up code..."
cd /home/xai/Documents
tar -czf /home/xai/backups/ty_wave_backup_$(date +%Y%m%d_%H%M%S).tar.gz ty_wave/

# 3. Git tag
echo "📦 Creating Git tag..."
cd /home/xai/Documents/ty_wave
git add -A
git commit -m "Pre-event sourcing snapshot - $(date)"
git tag pre-event-sourcing-$(date +%Y%m%d)

# 4. Verify backups
echo "✅ Verifying backups..."
LATEST_DB_BACKUP=$(ls -t /home/xai/backups/turing_pre_event_sourcing_*.backup | head -1)
LATEST_CODE_BACKUP=$(ls -t /home/xai/backups/ty_wave_backup_*.tar.gz | head -1)

echo "   Database backup: $LATEST_DB_BACKUP ($(du -h $LATEST_DB_BACKUP | cut -f1))"
echo "   Code backup: $LATEST_CODE_BACKUP ($(du -h $LATEST_CODE_BACKUP | cut -f1))"

# 5. Test restore (dry run)
echo "🧪 Testing database backup integrity..."
pg_restore --list $LATEST_DB_BACKUP | head -5

echo ""
echo "✅ BACKUP COMPLETE"
echo "   Database: $LATEST_DB_BACKUP"
echo "   Code: $LATEST_CODE_BACKUP"
echo "   Git tag: pre-event-sourcing-$(date +%Y%m%d)"
echo ""
echo "⚠️  KEEP THESE SAFE - You can restore with:"
echo "   pg_restore -U base_admin -d turing -v $LATEST_DB_BACKUP"
echo "   tar -xzf $LATEST_CODE_BACKUP"
```

**Make executable and run:**

```bash
chmod +x scripts/pre_flight_backup.sh
./scripts/pre_flight_backup.sh
```

---

## Recovery Testing (Validate Backups Work)

**Test restoration in a safe environment:**

```bash
# 1. Create test database
sudo -u postgres psql -c "CREATE DATABASE turing_test OWNER base_admin;"

# 2. Restore to test database
pg_restore -U base_admin -d turing_test -v \
  /home/xai/backups/turing_pre_event_sourcing_*.backup

# 3. Verify data
psql -U base_admin -d turing_test -c "
SELECT 
    COUNT(*) as checkpoint_count,
    MAX(checkpoint_timestamp) as latest_checkpoint
FROM posting_state_checkpoints;
"

# 4. Test query
psql -U base_admin -d turing_test -c "
SELECT posting_id, conversation_id, is_terminal 
FROM posting_state_checkpoints 
WHERE posting_id = 3001;
"

# 5. Cleanup
sudo -u postgres psql -c "DROP DATABASE turing_test;"

echo "✅ Backup restoration tested successfully"
```

---

## Critical File Locations

**Backups:**
```
/home/xai/backups/
├── turing_pre_event_sourcing_YYYYMMDD_HHMMSS.backup  (full DB)
├── turing_critical_tables_YYYYMMDD_HHMMSS.backup     (critical tables only)
├── ty_wave_backup_YYYYMMDD_HHMMSS.tar.gz             (full code)
├── docs_YYYYMMDD_HHMMSS.tar.gz                       (documentation)
└── sql_YYYYMMDD_HHMMSS.tar.gz                        (migrations)
```

**Git Tags:**
```
git tag --list | grep pre-event-sourcing
# pre-event-sourcing-20251119
```

**Log Files:**
```
/home/xai/Documents/ty_wave/logs/
├── workflow_3001_CHUNKED_RETRY_20251119_073642.log   (current run)
├── workflow_3001_FIXED_WILDCARD_20251119_045957.log  (previous run)
└── workflow_3001_FIXED_KEYERROR_20251119_012808.log  (earlier run)
```

---

## What NOT to Restore

**Don't restore these (temporary/generated files):**
- `logs/` - Old log files (keep current run only)
- `__pycache__/` - Python bytecode
- `venv/` - Virtual environment (recreate fresh)
- `.git/` - Git history (restore from remote if needed)

**Don't restore old workflow runs:**
- If workflow 3001 was 50% complete before disaster, DON'T try to resume
- Restart from beginning after restore
- Checkpoints will show which postings are done (skip them)

---

## Recovery Decision Tree

```
Disaster occurred?
├─ Database seems wrong?
│  ├─ Checkpoints missing/corrupted?
│  │  └─ Restore database from backup
│  ├─ New event tables causing issues?
│  │  └─ Drop event tables, restore checkpoints
│  └─ Everything broken?
│     └─ Full database restore
│
├─ Code won't run?
│  ├─ Import errors?
│  │  └─ Restore code from tarball or git tag
│  ├─ EventStore class broken?
│  │  └─ Git checkout pre-event-sourcing tag
│  └─ Dependencies missing?
│     └─ Recreate venv, reinstall packages
│
└─ Both database AND code broken?
   └─ NUCLEAR OPTION: Full system restore
      1. Restore database
      2. Restore code
      3. Recreate venv
      4. Test with single posting
      5. Restart workflow
```

---

## Emergency Contacts (Internal Notes)

**Key Documentation:**
- Current architecture: `docs/CURRENT_WAVE_ARCHITECTURE.md`
- Arden's code review: `docs/CODE_REVIEW_ARDEN_NOV19_2025.md`
- Event sourcing plan: `docs/EVENT_SOURCING_IMPLEMENTATION_PLAN.md`

**Database Connection:**
- Host: localhost
- Database: turing
- User: base_admin
- Port: 5432

**Critical Functions:**
- Checkpoint loading: `core/checkpoint_utils.py::get_posting_current_state()`
- Workflow execution: `core/workflow_executor.py::WorkflowExecutor`
- Batch processing: `core/model_batch_executor.py::ModelBatchExecutor`

---

## Post-Restore Validation

**After any restore, verify these:**

```bash
# 1. Database connectivity
psql -U base_admin -d turing -c "SELECT NOW();"

# 2. Critical tables exist
psql -U base_admin -d turing -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'posting_state_checkpoints',
    'postings',
    'workflows',
    'conversations',
    'actors'
  )
ORDER BY table_name;
"

# 3. Checkpoint data present
psql -U base_admin -d turing -c "
SELECT COUNT(*) as total_checkpoints FROM posting_state_checkpoints;
"

# 4. Code imports work
python3 -c "
from core.workflow_executor import WorkflowExecutor
from core.model_batch_executor import ModelBatchExecutor
from core.checkpoint_utils import get_posting_current_state
print('✅ All imports successful')
"

# 5. Test checkpoint retrieval
python3 -c "
from core.checkpoint_utils import get_posting_current_state
state = get_posting_current_state(3001)
print(f'✅ Checkpoint retrieval works: posting 3001 at conversation {state.get(\"conversation_id\")}')
"

# 6. Test workflow can start
python3 -c "
from core.workflow_executor import WorkflowExecutor
executor = WorkflowExecutor(workflow_id=3001)
print('✅ Workflow executor initialized')
"
```

**If all checks pass:**
```bash
echo "✅ SYSTEM RESTORED AND VALIDATED"
echo "   Safe to restart workflow processing"
```

---

## Philosophy: "Defensive Optimism"

**We're optimistic:** Event sourcing will work great, Arden's architecture is solid

**But we're defensive:** 
- Backups before every major change
- Test restores before we need them
- Git tags for known-good states
- Multiple backup formats (dump, tarball, git)

**Why this matters:**
- You can't lose data you've backed up
- You can't break code you've tagged
- You can't get lost if you have a map back

**The rule:** 
> "Never make a change you can't undo in 5 minutes"

With these backups, any disaster = 5 minute restore + restart workflow. That's acceptable risk.

---

## Backup Schedule Recommendation

**Before event sourcing migration:**
- ✅ Full backup (database + code)
- ✅ Git tag
- ✅ Test restore

**During migration (dual-write phase):**
- Daily database backups
- Git commit after each phase
- Validation queries every hour

**After successful migration:**
- Weekly database backups
- Git commits per feature
- Keep old tables archived for 30 days

---

## Final Checklist

**Before starting event sourcing work:**

- [ ] Run `./scripts/pre_flight_backup.sh`
- [ ] Verify backups created (check /home/xai/backups/)
- [ ] Test restore to temporary database
- [ ] Git tag created and pushed
- [ ] Read this disaster recovery doc
- [ ] Know where backups are
- [ ] Know how to restore (practice once)

**Then proceed with confidence:** You can't permanently break what you've backed up.

---

**Created:** November 19, 2025  
**Purpose:** Sleep well knowing we can recover from anything  
**Last Updated:** Before event sourcing migration begins
