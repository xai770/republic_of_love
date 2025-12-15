# Migration 088: Add Parallel Batch Processing to TuringOrchestrator

## Problem
Currently TuringOrchestrator processes jobs sequentially (1 at a time).
GPU graph shows bursts to 100% then idle time between jobs.
We have 1764 jobs remaining, ~23 hours at current rate.

## Solution
Add parallel processing to TuringOrchestrator:
- Process N jobs concurrently using ThreadPoolExecutor
- Keep GPU busy with multiple LLM conversations running simultaneously
- Configurable worker count (default: 4 workers for safety)

## Implementation Plan

### Phase 1: Add parallel processing method to TuringOrchestrator

Add new method `process_pending_tasks_parallel()` that:
1. Groups pending jobs into batches
2. Uses ThreadPoolExecutor to process N jobs simultaneously
3. Collects results and reports progress
4. Respects max_tasks limit across all workers

### Phase 2: Add configuration

Environment variables:
- `TURING_PARALLEL_WORKERS`: Number of concurrent workers (default: 4)
- `TURING_BATCH_SIZE`: Items per worker batch (default: 50)

### Phase 3: Test with workflow 1124 (IHL scoring)

Test scenarios:
- 10 jobs with 2 workers
- 50 jobs with 4 workers
- Monitor GPU utilization (should stay high)
- Verify database integrity (no conflicts)

## Expected Results

**Before (sequential):**
- 1 job every ~47s
- GPU usage: spiky (bursts to 100%, then idle)
- 1764 jobs = ~23 hours

**After (4 workers):**
- 4 jobs every ~47s = 12s per job effective
- GPU usage: sustained 80-100%
- 1764 jobs = ~6 hours (4x faster)

## Safety Considerations

1. **Database concurrency**: PostgreSQL handles concurrent writes well
2. **LLM rate limits**: Ollama local, no rate limits
3. **Memory**: 4 workers × 3 actors = 12 models max (manageable)
4. **Error isolation**: One job failure doesn't crash the batch

## Rollback Plan

Keep original `process_pending_tasks()` method.
New parallel version is opt-in via separate method call.

## Status
- [ ] Code implementation
- [ ] Testing with 10 jobs
- [ ] Testing with 50 jobs
- [ ] GPU utilization validation
- [ ] Production deployment

Created: 2025-11-11 06:15
Status: PROPOSED
