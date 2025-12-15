-- Pipeline V2 Migration
-- Date: 2025-12-11
-- Authors: Arden, Sandy
-- 
-- Creates: runs, queue tables
-- Modifies: interactions (adds run_id)
--
-- To run: ./scripts/q.sh -f sql/migrations/001_pipeline_v2.sql

BEGIN;

-- ============================================================================
-- Table: runs
-- Groups interactions into logical units. Answers "why did we process this?"
-- ============================================================================
CREATE TABLE IF NOT EXISTS runs (
    run_id SERIAL PRIMARY KEY,
    posting_id INT REFERENCES postings(posting_id),
    reason VARCHAR(100),                -- 'initial_processing', 'QA_flagged', 'model_upgrade'
    triggered_by VARCHAR(50),           -- 'scheduler', 'manual', 'worker'
    start_step VARCHAR(50),             -- Where to start (for partial reprocessing)
    model_config JSONB,                 -- Model overrides if any
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE runs IS 'Groups interactions into logical units. WHY we processed something.';
COMMENT ON COLUMN runs.reason IS 'Human-readable reason: initial_processing, QA_flagged, model_upgrade, etc.';
COMMENT ON COLUMN runs.triggered_by IS 'Who/what triggered: scheduler, manual, worker';
COMMENT ON COLUMN runs.start_step IS 'Which step to start from (for partial reprocessing)';
COMMENT ON COLUMN runs.model_config IS 'Model overrides as JSON, e.g. {"summary": "qwen2.5:7b"}';

-- ============================================================================
-- Table: queue
-- Pending work. Ephemeral - deleted on success, kept on failure for debugging.
-- ============================================================================
CREATE TABLE IF NOT EXISTS queue (
    queue_id SERIAL PRIMARY KEY,
    posting_id INT REFERENCES postings(posting_id),
    run_id INT REFERENCES runs(run_id), -- NULL until claimed by worker
    start_step VARCHAR(50) DEFAULT 'extract_summary',
    priority INT DEFAULT 0,             -- Higher = processed first
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, failed
    reason VARCHAR(100),
    model_override JSONB,
    error_message TEXT,                 -- For failed jobs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ
);

COMMENT ON TABLE queue IS 'Pending work. WHAT TO DO NEXT. Mutable, can clear/retry.';
COMMENT ON COLUMN queue.run_id IS 'NULL on insert, set when worker claims job';
COMMENT ON COLUMN queue.status IS 'pending → processing → DELETE (success) or failed (keep for debug)';
COMMENT ON COLUMN queue.priority IS 'Higher priority = processed first. Default 0.';
COMMENT ON COLUMN queue.error_message IS 'Populated when status=failed for debugging';

-- Partial indexes for worker claim query
CREATE INDEX IF NOT EXISTS idx_queue_pending 
    ON queue(priority DESC, created_at) 
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_queue_failed 
    ON queue(created_at) 
    WHERE status = 'failed';

-- ============================================================================
-- Alter: interactions
-- Add run_id to link interactions to their logical run
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'interactions' AND column_name = 'run_id'
    ) THEN
        ALTER TABLE interactions ADD COLUMN run_id INT REFERENCES runs(run_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_interactions_run ON interactions(run_id);

COMMENT ON COLUMN interactions.run_id IS 'Links to runs table for grouping. NULL for legacy interactions.';

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Pipeline V2 migration complete.';
    RAISE NOTICE 'Tables created: runs, queue';
    RAISE NOTICE 'Column added: interactions.run_id';
    RAISE NOTICE '';
    RAISE NOTICE 'Workflow:';
    RAISE NOTICE '  1. Enqueue:  INSERT INTO queue (posting_id, reason)';
    RAISE NOTICE '  2. Claim:    UPDATE queue SET status=processing + INSERT INTO runs';
    RAISE NOTICE '  3. Execute:  Create interactions with run_id';
    RAISE NOTICE '  4. Complete: UPDATE runs SET completed_at, DELETE FROM queue';
    RAISE NOTICE '  5. Fail:     UPDATE queue SET status=failed, error_message=...';
END $$;

COMMIT;
