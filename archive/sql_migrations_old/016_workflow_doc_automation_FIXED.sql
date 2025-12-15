-- Migration 016 (REVISED): Simplified Workflow Documentation Automation
-- Single trigger point to avoid cascading

-- Step 1: Create queue table
CREATE TABLE IF NOT EXISTS workflow_doc_queue (
    workflow_id INT PRIMARY KEY REFERENCES workflows(workflow_id) ON DELETE CASCADE,
    needs_regeneration BOOLEAN DEFAULT TRUE,
    last_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_generated_at TIMESTAMP,
    change_count INT DEFAULT 1
);

-- Step 2: Add updated_at to workflows
ALTER TABLE workflows 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 3: ❌ REMOVE OLD TRIGGERS (if they exist)
DROP TRIGGER IF EXISTS conversations_changed ON conversations;
DROP TRIGGER IF EXISTS instructions_changed ON instructions;
DROP FUNCTION IF EXISTS queue_related_workflow_docs();

-- Step 4: Single trigger function (workflow_conversations only)
CREATE OR REPLACE FUNCTION queue_workflow_docs()
RETURNS TRIGGER AS $$
BEGIN
    -- Determine workflow_id (handle INSERT vs DELETE)
    DECLARE
        target_workflow_id INT;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            target_workflow_id := OLD.workflow_id;
        ELSE
            target_workflow_id := NEW.workflow_id;
        END IF;
        
        -- Queue workflow for doc regeneration
        INSERT INTO workflow_doc_queue (workflow_id, needs_regeneration, last_changed_at, change_count)
        VALUES (target_workflow_id, TRUE, CURRENT_TIMESTAMP, 1)
        ON CONFLICT (workflow_id) 
        DO UPDATE SET 
            needs_regeneration = TRUE,
            last_changed_at = CURRENT_TIMESTAMP,
            change_count = workflow_doc_queue.change_count + 1;
        
        -- Update workflow timestamp
        UPDATE workflows 
        SET updated_at = CURRENT_TIMESTAMP
        WHERE workflow_id = target_workflow_id;
        
        RETURN COALESCE(NEW, OLD);
    END;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Trigger ONLY on workflow_conversations
DROP TRIGGER IF EXISTS workflow_conversations_changed ON workflow_conversations;
CREATE TRIGGER workflow_conversations_changed
AFTER INSERT OR UPDATE OR DELETE ON workflow_conversations
FOR EACH ROW 
EXECUTE FUNCTION queue_workflow_docs();

-- Step 6: View for checking stale documentation
CREATE OR REPLACE VIEW workflow_doc_status AS
SELECT 
    w.workflow_id,
    w.workflow_name,
    w.updated_at as workflow_last_modified,
    wdq.last_changed_at as queue_last_changed,
    wdq.last_generated_at,
    wdq.needs_regeneration,
    wdq.change_count,
    CASE 
        WHEN wdq.last_generated_at IS NULL THEN TRUE
        WHEN wdq.last_generated_at < wdq.last_changed_at THEN TRUE
        ELSE FALSE
    END as is_stale,
    -- Debounce: Only consider stale if unchanged for 10 minutes
    CASE 
        WHEN wdq.last_changed_at < NOW() - INTERVAL '10 minutes' THEN TRUE
        ELSE FALSE
    END as ready_for_regen
FROM workflows w
LEFT JOIN workflow_doc_queue wdq ON w.workflow_id = wdq.workflow_id
WHERE w.enabled = TRUE
ORDER BY wdq.needs_regeneration DESC, w.workflow_id;

-- Step 7: Function to mark doc as generated
CREATE OR REPLACE FUNCTION mark_workflow_doc_generated(p_workflow_id INT)
RETURNS VOID AS $$
BEGIN
    UPDATE workflow_doc_queue
    SET 
        needs_regeneration = FALSE,
        last_generated_at = CURRENT_TIMESTAMP
    WHERE workflow_id = p_workflow_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE workflow_doc_queue IS 'Tracks workflows needing doc regeneration (single trigger on workflow_conversations)';
COMMENT ON FUNCTION queue_workflow_docs() IS 'Queues workflow when workflow_conversations changes (prevents trigger cascade)';
COMMENT ON VIEW workflow_doc_status IS 'Shows stale docs with 10-minute debounce';
COMMENT ON COLUMN workflow_doc_status.ready_for_regen IS 'TRUE if stale AND unchanged for 10+ minutes (prevents mid-edit regeneration)';
