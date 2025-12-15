-- Migration 016: Automatic Workflow Documentation Regeneration
-- Creates trigger to detect workflow changes and queue doc regeneration

-- Step 1: Create queue table for tracking which workflows need docs regenerated
CREATE TABLE IF NOT EXISTS workflow_doc_queue (
    workflow_id INT PRIMARY KEY REFERENCES workflows(workflow_id) ON DELETE CASCADE,
    needs_regeneration BOOLEAN DEFAULT TRUE,
    last_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_generated_at TIMESTAMP,
    change_count INT DEFAULT 1
);

-- Step 2: Add updated_at to workflows table if not exists
ALTER TABLE workflows 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 3: Function to queue workflow for doc regeneration
CREATE OR REPLACE FUNCTION queue_workflow_docs()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update queue entry
    INSERT INTO workflow_doc_queue (workflow_id, needs_regeneration, last_changed_at, change_count)
    VALUES (NEW.workflow_id, TRUE, CURRENT_TIMESTAMP, 1)
    ON CONFLICT (workflow_id) 
    DO UPDATE SET 
        needs_regeneration = TRUE,
        last_changed_at = CURRENT_TIMESTAMP,
        change_count = workflow_doc_queue.change_count + 1;
    
    -- Update workflow timestamp
    UPDATE workflows 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE workflow_id = NEW.workflow_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Trigger on workflow_conversations changes
CREATE TRIGGER workflow_conversations_changed
AFTER INSERT OR UPDATE OR DELETE ON workflow_conversations
FOR EACH ROW 
EXECUTE FUNCTION queue_workflow_docs();

-- Step 5: Trigger on conversations changes (affects workflow docs)
CREATE OR REPLACE FUNCTION queue_related_workflow_docs()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue all workflows using this conversation
    INSERT INTO workflow_doc_queue (workflow_id, needs_regeneration, last_changed_at, change_count)
    SELECT wc.workflow_id, TRUE, CURRENT_TIMESTAMP, 1
    FROM workflow_conversations wc
    WHERE wc.conversation_id = NEW.conversation_id
    ON CONFLICT (workflow_id)
    DO UPDATE SET
        needs_regeneration = TRUE,
        last_changed_at = CURRENT_TIMESTAMP,
        change_count = workflow_doc_queue.change_count + 1;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_changed
AFTER UPDATE ON conversations
FOR EACH ROW
EXECUTE FUNCTION queue_related_workflow_docs();

-- Step 6: Trigger on instructions changes (affects conversation docs)
CREATE TRIGGER instructions_changed
AFTER INSERT OR UPDATE OR DELETE ON instructions
FOR EACH ROW
EXECUTE FUNCTION queue_related_workflow_docs();

-- Step 7: View for checking stale documentation
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
    END as is_stale
FROM workflows w
LEFT JOIN workflow_doc_queue wdq ON w.workflow_id = wdq.workflow_id
WHERE w.enabled = TRUE
ORDER BY wdq.needs_regeneration DESC, w.workflow_id;

-- Step 8: Function to mark doc as generated (called by Python tool)
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

COMMENT ON TABLE workflow_doc_queue IS 'Tracks which workflows need documentation regenerated';
COMMENT ON FUNCTION queue_workflow_docs() IS 'Automatically queues workflow for doc regeneration when changed';
COMMENT ON VIEW workflow_doc_status IS 'Shows which workflows have stale documentation';
COMMENT ON FUNCTION mark_workflow_doc_generated(INT) IS 'Call this after generating docs to mark as up-to-date';
