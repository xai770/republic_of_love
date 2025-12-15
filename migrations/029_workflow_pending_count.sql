-- Migration 029: Add pending_count to workflow_runs (trigger-maintained)
-- Date: 2025-12-14
-- Author: Copilot
-- Purpose: Fast workflow completion checks without scanning interactions table

-- 1. Add pending_count column
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS pending_count INTEGER DEFAULT 0;
COMMENT ON COLUMN workflow_runs.pending_count IS 
    'Trigger-maintained count of pending interactions. When 0, workflow is complete.';

-- 2. Initialize current values from existing data
UPDATE workflow_runs wr
SET pending_count = (
    SELECT COUNT(*) 
    FROM interactions i 
    WHERE i.workflow_run_id = wr.workflow_run_id 
      AND i.status = 'pending'
);

-- 3. Create trigger function to maintain count
CREATE OR REPLACE FUNCTION update_workflow_pending_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Handle INSERT
    IF TG_OP = 'INSERT' THEN
        IF NEW.status = 'pending' AND NEW.workflow_run_id IS NOT NULL THEN
            UPDATE workflow_runs 
            SET pending_count = pending_count + 1,
                updated_at = NOW()
            WHERE workflow_run_id = NEW.workflow_run_id;
        END IF;
        RETURN NEW;
    
    -- Handle UPDATE (status change)
    ELSIF TG_OP = 'UPDATE' THEN
        -- Leaving pending status
        IF OLD.status = 'pending' AND NEW.status != 'pending' AND NEW.workflow_run_id IS NOT NULL THEN
            UPDATE workflow_runs 
            SET pending_count = GREATEST(pending_count - 1, 0),
                updated_at = NOW()
            WHERE workflow_run_id = NEW.workflow_run_id;
        -- Entering pending status (rare, but handle it)
        ELSIF OLD.status != 'pending' AND NEW.status = 'pending' AND NEW.workflow_run_id IS NOT NULL THEN
            UPDATE workflow_runs 
            SET pending_count = pending_count + 1,
                updated_at = NOW()
            WHERE workflow_run_id = NEW.workflow_run_id;
        END IF;
        RETURN NEW;
    
    -- Handle DELETE
    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.status = 'pending' AND OLD.workflow_run_id IS NOT NULL THEN
            UPDATE workflow_runs 
            SET pending_count = GREATEST(pending_count - 1, 0),
                updated_at = NOW()
            WHERE workflow_run_id = OLD.workflow_run_id;
        END IF;
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 4. Create trigger on interactions table
DROP TRIGGER IF EXISTS trg_update_workflow_pending_count ON interactions;
CREATE TRIGGER trg_update_workflow_pending_count
    AFTER INSERT OR UPDATE OF status OR DELETE ON interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_pending_count();

-- 5. Add index for fast pending lookups
CREATE INDEX IF NOT EXISTS idx_workflow_runs_pending_count ON workflow_runs(pending_count) WHERE pending_count > 0;

-- 6. Verification
SELECT 
    wr.workflow_run_id,
    wr.pending_count as trigger_count,
    (SELECT COUNT(*) FROM interactions i WHERE i.workflow_run_id = wr.workflow_run_id AND i.status = 'pending') as actual_count
FROM workflow_runs wr
WHERE wr.status = 'running'
ORDER BY wr.workflow_run_id DESC
LIMIT 10;
