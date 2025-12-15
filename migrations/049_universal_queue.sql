-- Migration 049: Universal Queue
-- Makes the queue work for ANY subject type, not just postings
-- 
-- Author: Arden
-- Date: December 11, 2025

BEGIN;

-- Step 1: Add universal subject columns
ALTER TABLE queue 
ADD COLUMN IF NOT EXISTS subject_type VARCHAR(50) DEFAULT 'posting',
ADD COLUMN IF NOT EXISTS subject_id INTEGER,
ADD COLUMN IF NOT EXISTS workflow_id INTEGER;

-- Step 2: Migrate existing data (posting_id → subject_id)
UPDATE queue 
SET subject_id = posting_id,
    subject_type = 'posting',
    workflow_id = 3001  -- All existing queue items are from 3001
WHERE posting_id IS NOT NULL 
  AND subject_id IS NULL;

-- Step 3: Add workflow foreign key
ALTER TABLE queue
ADD CONSTRAINT queue_workflow_id_fkey 
FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id);

-- Step 4: Create indexes for universal querying
CREATE INDEX IF NOT EXISTS idx_queue_subject 
ON queue(subject_type, subject_id) 
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_queue_workflow 
ON queue(workflow_id, status);

-- Step 5: Add comment explaining the design
COMMENT ON TABLE queue IS 'Universal work queue for Turing workflows. 
subject_type: The type of entity being processed (posting, entity, profile, document, batch)
subject_id: The ID in the corresponding table
workflow_id: Which workflow processes this item
start_step: Which conversation to start from (allows mid-workflow queueing)';

COMMENT ON COLUMN queue.subject_type IS 'Type of subject: posting, entity, profile, document, batch, etc.';
COMMENT ON COLUMN queue.subject_id IS 'ID of the subject in its respective table';
COMMENT ON COLUMN queue.workflow_id IS 'Workflow that will process this queue item';

-- Note: We keep posting_id for backward compatibility during transition
-- Future: Remove posting_id column after all code migrated to subject_type/subject_id

COMMIT;

-- Verification query:
-- SELECT subject_type, COUNT(*) FROM queue GROUP BY subject_type;
