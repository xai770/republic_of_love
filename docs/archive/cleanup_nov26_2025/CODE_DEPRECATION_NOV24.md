# Code Deprecation - November 24, 2025

**Date:** November 24, 2025 15:00  
**Context:** Wave Runner V2 is production (A+ 99/100) - old code deprecated  
**Action:** Renamed deprecated code to carry `_DEPRECATED_OLD_CODE` suffix

---

## What Was Deprecated

### Directories Renamed

**1. core/wave_processor → core/wave_processor_DEPRECATED_OLD_CODE**
- **Era:** Pre-Wave Runner V2 (before Nov 2025)
- **Purpose:** Event-sourced workflow processor with custom event store
- **Files:**
  - `__init__.py` - WaveBatchProcessor orchestrator
  - `cli.py` - Command-line interface
  - `workflow_loader.py` - Posting loader from projection
  - `workflow_db.py` - Database ops
  - `checkpoint_manager.py` - Checkpoint system
  - `step_metrics.py` - Metrics tracking

**Replaced By:** `core/wave_runner_v2/` (production system)

**Why Deprecated:**
- Wave Runner V2 is production ready (A+ grade)
- Uses different architecture (interaction_events table vs custom event store)
- No template substitution, cleaner code
- Better tested (2,119 lines of tests)

### Files Renamed

**2. core/event_store.py → core/event_store_DEPRECATED_OLD_CODE.py**
- **Era:** Pre-Wave Runner V2 event sourcing
- **Purpose:** Custom EventStore class (append_event, rebuild_projection)
- **Size:** 10,479 bytes

**Replaced By:** `interaction_events` table + Wave Runner V2 event handling

**Why Deprecated:**
- Wave Runner V2 uses built-in database event sourcing
- interaction_events table is the event log
- No need for custom EventStore class

**Already Deprecated (Pre-Nov 24):**
- `core/wave_executor.py.OLD` - Old wave executor
- `core/workflow_executor.py.OLD` - Old workflow executor

---

## Files in core/ (Still Active vs Deprecated)

### Active Files (Used by Production Code)

**Database & Config:**
- `database.py` - Legacy database wrapper (may be used by old scripts)
- `db_context.py` - Database context manager
- `logging_config.py` - Logging configuration

**Utilities (Might Be Used):**
- `circuit_breaker.py` - Circuit breaker pattern
- `error_handler.py` - Error handling utilities

**Status:** Need to check if these are actually used by anything

### Deprecated Files (NOT Used by Wave Runner V2)

**Legacy Workflow Code:**
- `actor_router.py` - Old actor routing (Wave Runner V2 has own routing)
- `checkpoint_utils.py` - Old checkpoint system (Wave Runner V2 queries DB)
- `posting_state.py` - Old PostingState data structure
- `result_saver.py` - Old result saver
- `taxonomy_helper.py` - Taxonomy utilities (may still be useful?)
- `turing_job_fetcher.py` - Old job fetcher (18KB - might have useful logic)
- `turing_orchestrator.py` - Old orchestrator (31KB - large file!)

**Status:** Candidates for renaming to `_DEPRECATED_OLD_CODE.py`

---

## Analysis: Should We Deprecate More?

### Step 1: Check Usage

```bash
# Check if any active code imports these files
cd /home/xai/Documents/ty_learn

# Check scripts
grep -r "from core.actor_router" scripts/ workflows/ || echo "Not used"
grep -r "from core.checkpoint_utils" scripts/ workflows/ || echo "Not used"
grep -r "from core.turing_job_fetcher" scripts/ workflows/ || echo "Not used"
grep -r "from core.turing_orchestrator" scripts/ workflows/ || echo "Not used"

# Check tests
grep -r "from core.actor_router" tests/ || echo "Not used"
grep -r "from core.turing_orchestrator" tests/ || echo "Not used"
```

### Step 2: Preserve Useful Logic

**Files with potential value:**
1. **turing_job_fetcher.py** (18KB) - Deutsche Bank API integration
   - May have useful parsing logic
   - Migrated to `core/wave_runner_v2/actors/db_job_fetcher.py`?
   - Check if new version has all the logic

2. **taxonomy_helper.py** (3KB) - Taxonomy utilities
   - May have useful skill taxonomy logic
   - Check if skills_taxonomy/ has this logic

3. **circuit_breaker.py** (8KB) - Circuit breaker pattern
   - Generic pattern, might be reusable
   - Check if Wave Runner V2 uses circuit breakers

### Step 3: Rename Low-Value Files

**Clear candidates for deprecation:**
- `actor_router.py` - Wave Runner V2 has own routing
- `checkpoint_utils.py` - Wave Runner V2 queries DB directly
- `posting_state.py` - Wave Runner V2 has own models
- `result_saver.py` - Wave Runner V2 has own database.py
- `turing_orchestrator.py` - Completely replaced by Wave Runner V2

---

## Recommendation

### Phase 1: Already Done ✅
- ✅ Renamed `core/wave_processor/` → `core/wave_processor_DEPRECATED_OLD_CODE/`
- ✅ Renamed `core/event_store.py` → `core/event_store_DEPRECATED_OLD_CODE.py`

### Phase 2: Check Usage (Next)
```bash
# Run these checks to see if anything imports the old files
cd /home/xai/Documents/ty_learn

for file in actor_router checkpoint_utils posting_state result_saver turing_orchestrator turing_job_fetcher taxonomy_helper; do
  echo "=== Checking $file ==="
  grep -r "from core.$file" . --include="*.py" | grep -v "__pycache__" | grep -v "DEPRECATED"
done
```

### Phase 3: Deprecate Based on Results
If nothing imports them:
```bash
# Rename deprecated files
cd /home/xai/Documents/ty_learn/core

mv actor_router.py actor_router_DEPRECATED_OLD_CODE.py
mv checkpoint_utils.py checkpoint_utils_DEPRECATED_OLD_CODE.py
mv posting_state.py posting_state_DEPRECATED_OLD_CODE.py
mv result_saver.py result_saver_DEPRECATED_OLD_CODE.py
mv turing_orchestrator.py turing_orchestrator_DEPRECATED_OLD_CODE.py
```

### Phase 4: Consider Archiving (Later)
Move all `_DEPRECATED_OLD_CODE` files to `archive/legacy_core/`:
```bash
mkdir -p archive/legacy_core
mv core/*_DEPRECATED_OLD_CODE* archive/legacy_core/
mv core/wave_processor_DEPRECATED_OLD_CODE archive/legacy_core/
```

---

## Impact

**Before:**
- 12 Python files in `core/`
- 1 directory `wave_processor/`
- 2 files with `.OLD` suffix
- Unclear what's active vs deprecated

**After Phase 1:**
- 10 Python files in `core/` (without clear suffix)
- 1 directory `wave_processor_DEPRECATED_OLD_CODE/` (clear!)
- 3 files with suffix (2 `.OLD`, 1 `_DEPRECATED_OLD_CODE.py`)
- Slightly clearer, but more work needed

**After Phase 3 (If all deprecated):**
- 3-5 Python files in `core/` (only utilities)
- 1 directory `wave_processor_DEPRECATED_OLD_CODE/`
- 8-10 files with `_DEPRECATED_OLD_CODE.py` suffix
- Crystal clear what's active!

---

## Benefits

✅ **No accidental imports** - Sandy won't import old code  
✅ **Clear codebase** - Obvious what's production vs legacy  
✅ **Preserve sparks of genius** - Code still accessible for reference  
✅ **Easy cleanup later** - Can move to archive/ when confident

---

## Next Steps

**Waiting for user decision:**
1. Run usage checks to see if old core files are imported anywhere?
2. Rename unused files to `_DEPRECATED_OLD_CODE.py`?
3. Move all deprecated code to `archive/legacy_core/`?

**User, please confirm:**
- [ ] Run usage checks on remaining core/*.py files?
- [ ] Deprecate files that aren't imported?
- [ ] Archive all deprecated code to archive/legacy_core/?

---

**Status:** ✅ Phase 1 complete - wave_processor and event_store deprecated!  
**Next:** Check if other core/*.py files are actually used 🔍
