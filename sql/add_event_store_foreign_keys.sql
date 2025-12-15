-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS TO EVENT STORE TABLES
-- =====================================================
-- Links event store tables to postings table for referential integrity
-- Created: November 19, 2025
-- =====================================================

-- 1. posting_state_projection -> postings
ALTER TABLE posting_state_projection 
ADD CONSTRAINT fk_posting_state_projection_posting 
FOREIGN KEY (posting_id) REFERENCES postings(posting_id) 
ON DELETE CASCADE;

COMMENT ON CONSTRAINT fk_posting_state_projection_posting ON posting_state_projection IS
'Ensures posting_id references valid posting. Cascade delete removes projection when posting deleted.';

-- 2. posting_state_snapshots -> postings  
ALTER TABLE posting_state_snapshots 
ADD CONSTRAINT fk_posting_state_snapshots_posting 
FOREIGN KEY (posting_id) REFERENCES postings(posting_id) 
ON DELETE CASCADE;

COMMENT ON CONSTRAINT fk_posting_state_snapshots_posting ON posting_state_snapshots IS
'Ensures posting_id references valid posting. Cascade delete removes snapshots when posting deleted.';

-- 3. Validate execution_events posting references
-- Note: Cannot add FK on TEXT column (aggregate_id) but we can validate the data
DO $$
DECLARE
    invalid_count INT;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM execution_events e
    WHERE e.aggregate_type = 'posting'
      AND NOT EXISTS (
          SELECT 1 FROM postings p 
          WHERE p.posting_id::text = e.aggregate_id
      );
    
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % execution_events with invalid posting_ids', invalid_count;
    ELSE
        RAISE NOTICE '✅ All execution_events with aggregate_type=posting have valid posting_ids';
    END IF;
END $$;

-- =====================================================
-- VERIFICATION
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Foreign Key Constraints Added Successfully';
    RAISE NOTICE '';
    RAISE NOTICE 'Constraints Added:';
    RAISE NOTICE '  - posting_state_projection.posting_id -> postings.posting_id (CASCADE)';
    RAISE NOTICE '  - posting_state_snapshots.posting_id -> postings.posting_id (CASCADE)';
    RAISE NOTICE '';
    RAISE NOTICE 'Validation:';
    RAISE NOTICE '  - execution_events posting references validated (FK not possible on TEXT column)';
    RAISE NOTICE '';
    RAISE NOTICE 'Referential Integrity: ENFORCED';
END $$;
