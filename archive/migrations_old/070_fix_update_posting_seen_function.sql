-- Migration 070: Fix update_posting_seen function to match current schema
-- Remove references to deleted columns: times_checked, status_changed_at, status_reason
-- Date: 2025-11-09

CREATE OR REPLACE FUNCTION update_posting_seen(p_posting_id integer, p_still_active boolean)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_still_active THEN
        -- Still live on source site
        UPDATE postings
        SET 
            last_seen_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            posting_status = 'active'
        WHERE posting_id = p_posting_id;
    ELSE
        -- No longer on source site
        UPDATE postings
        SET 
            posting_status = 'filled',
            updated_at = CURRENT_TIMESTAMP
        WHERE posting_id = p_posting_id
        AND posting_status = 'active';
    END IF;
END;
$$;

COMMENT ON FUNCTION update_posting_seen IS 'Update posting last_seen_at timestamp and status (schema-aligned Nov 2025)';
