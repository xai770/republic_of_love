
## Cascade Invalidation Not Automatic (Dec 2025)

**Issue:** When invalidating interactions at one step, downstream steps that depend on that output are NOT automatically invalidated. This leads to stale data persisting through the pipeline.

**Example:** When phi4-mini extraction interactions were invalidated, the grading, formatting, and save steps still had "completed" status from previous runs. The reprocessed extractions would flow through but the save step would be skipped due to idempotency check.

**Current Workaround:** Manually invalidate all downstream interactions:
```sql
UPDATE interactions
SET invalidated = true, status = 'invalidated'
WHERE posting_id IN (SELECT posting_id FROM postings WHERE <condition>)
  AND conversation_id IN (<all downstream conversation_ids>)
  AND invalidated = false;
```

**Proper Solution:** 
1. Track data lineage - each interaction should reference the interaction(s) whose output it consumed
2. When invalidating, automatically cascade to all interactions that consumed its output
3. OR: Add a `--cascade` flag to invalidation that walks the workflow graph

**Related:** Duration validation (detect impossibly fast completions that indicate skipped work)
