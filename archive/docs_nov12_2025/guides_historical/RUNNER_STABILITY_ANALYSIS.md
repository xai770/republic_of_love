# Runner Analysis - Why It Got Stuck

## Issue Summary
The recipe_run_test_runner_v31.py occasionally hangs during execution, showing 0% GPU usage.

## Root Causes Identified

### 1. **Timeout-Prone Models**
From the test results, these models frequently timeout (30s default):
- **qwen3:1.7b** - 72% success rate (7 failures)
- **qwen3:4b** - 48% success rate (13 failures)

These models include "Thinking..." preambles in their responses which slow them down significantly (average 15-19 seconds per joke, sometimes exceeding 30s timeout).

### 2. **Database Transaction Issues** 
The runner experienced UNIQUE constraint violations:
```
sqlite3.IntegrityError: UNIQUE constraint failed: session_runs.recipe_run_id, session_runs.session_number
```

**Cause**: When the runner crashes or is killed mid-execution, it leaves recipe_runs in "RUNNING" status with partial session_runs/instruction_runs records. When restarted, it tries to re-execute these and hits the UNIQUE constraint.

**Solution Applied**: Reset RUNNING → PENDING and delete orphaned session_runs/instruction_runs before restart.

### 3. **No Automatic Recovery**
The runner lacks:
- Automatic cleanup of stuck RUNNING records on startup
- Detection of stale RUNNING records (e.g., older than 1 hour)
- Graceful handling of constraint errors (should skip and continue)

### 4. **No Progress Visibility**
- No built-in logging to file
- No heartbeat/keepalive indicator
- Hard to tell if runner is hung or just processing a slow model

## Recommendations

### Immediate Fixes
1. ✅ **Add --ids-file support** for selective test execution (DONE)
2. **Add startup cleanup** - Reset stale RUNNING records automatically
3. **Add constraint error recovery** - Skip problematic recipe_runs instead of crashing
4. **Increase timeout** for slow models (qwen3 family needs 60s+)

### Medium-term Improvements
1. **Add file logging** - Write detailed logs to /tmp/runner_{timestamp}.log
2. **Add heartbeat** - Update a timestamp every 10s to prove liveness
3. **Add model-specific timeouts** - Store timeout_seconds per actor
4. **Add resume capability** - Track last successful recipe_run_id

### Long-term Enhancements
1. **Parallel execution** - Run multiple recipe_runs concurrently (GPU permitting)
2. **Better error categorization** - Distinguish timeout vs crash vs constraint error
3. **Automatic retry logic** - Retry failed runs with exponential backoff
4. **Health monitoring** - Detect GPU hangs, OOM, etc.

## Code Changes Made (2025-10-21)

### recipe_run_test_runner_v31.py
- Added `--ids-file` argument to run specific recipe_run_ids
- Updated `run_all_pending()` to accept `specific_ids` parameter
- Updated `get_next_incomplete_recipe_run()` to filter by specific_ids

### llmcore_admin_v3/components/pipeline_status.py
- Added `render_selective_execution()` - UI for filtering and selecting tests
- Added `execute_selected_tests()` - Runs only selected recipe_runs
- Reorganized execution UI into tabs: "Select Tests" vs "Run All Pending"

### sql/joke_review.sql
- Created query to review all jokes with their grades
- Outputs comedian, topic, joke text, grade (IS_JOKE, QUALITY, REASON)
- Sorted by quality (best first)

## Testing Status
- ✅ 554/575 joke generation tests completed successfully (96.3%)
- ❌ 21 failures (mostly qwen3:1.7b and qwen3:4b timeouts)
- 📊 All jokes graded (though gemma3:1b gave 0% "IS_JOKE: YES" - very harsh!)

## Next Steps
1. Test selective execution feature in GUI
2. Implement automatic cleanup of stale RUNNING records
3. Consider disabling qwen3 models or increasing their timeout
4. Review joke quality - may need different grader or adjusted prompt
