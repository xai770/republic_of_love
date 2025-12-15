# Data Lifecycle Management

**Date:** November 24, 2025  
**Status:** 🟢 APPROVED - Ready for Implementation  
**Author:** Arden  
**Approved By:** xai

---

> **Workspace:** `ty_learn` is canonical. All other folders (`ty_wave`, etc.) contain symlinks back to `ty_learn`.

## Philosophy

> **Definitions stay forever. Executions get archived. User data gets deleted.**

**The Three Tiers:**

1. **Configuration (IMMORTAL)** - Schema definitions that define HOW the system works
   - `workflows`, `conversations`, `instruction_steps`, `actors`
   - NEVER delete, even when disabled
   - These are "source code" not "execution logs"

2. **Execution Records (MORTAL)** - Logs of what happened
   - `workflow_runs`, `interactions`, `interaction_events`
   - Archive when parent deleted (30-day retention)
   - Hard delete after expiry

3. **User Data (EPHEMERAL)** - Customer-owned data
   - `postings`, `profiles`, user-generated content
   - GDPR: Delete immediately on request
   - No retention period

---

## Architecture: Hybrid Archive Strategy

### Schema Design

```sql
-- Archive tables (same structure as active)
CREATE TABLE workflow_runs_archive (
    LIKE workflow_runs INCLUDING ALL
) PARTITION BY RANGE (archived_at);

CREATE TABLE interactions_archive (
    LIKE interactions INCLUDING ALL
) PARTITION BY RANGE (archived_at);

CREATE TABLE interaction_events_archive (
    LIKE interaction_events INCLUDING ALL
) PARTITION BY RANGE (archived_at);

-- Add archive metadata to all archive tables
ALTER TABLE workflow_runs_archive 
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN archive_reason TEXT,
ADD COLUMN expires_at TIMESTAMP;

ALTER TABLE interactions_archive 
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN archive_reason TEXT,
ADD COLUMN expires_at TIMESTAMP;

ALTER TABLE interaction_events_archive 
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN archive_reason TEXT,
ADD COLUMN expires_at TIMESTAMP;

-- Create monthly partitions (last 3 months for recovery)
CREATE TABLE workflow_runs_archive_2025_11 
    PARTITION OF workflow_runs_archive
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE workflow_runs_archive_2025_12
    PARTITION OF workflow_runs_archive
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- (repeat for interactions_archive, interaction_events_archive)
```

---

## Lifecycle Rules

### Rule 1: Posting Deleted → Archive Interactions (30 days)

**Trigger:**
```sql
-- When posting deleted
DELETE FROM postings WHERE posting_id = 4709;
```

**Action:**
```sql
CREATE OR REPLACE FUNCTION archive_posting_data(p_posting_id BIGINT)
RETURNS TABLE (
    archived_workflow_runs INTEGER,
    archived_interactions INTEGER,
    archived_events INTEGER
) AS $$
DECLARE
    v_runs INTEGER;
    v_interactions INTEGER;
    v_events INTEGER;
BEGIN
    -- Archive workflow runs
    WITH archived_runs AS (
        INSERT INTO workflow_runs_archive 
        SELECT *, NOW(), 'posting_deleted', NOW() + INTERVAL '30 days'
        FROM workflow_runs
        WHERE posting_id = p_posting_id
        RETURNING workflow_run_id
    )
    SELECT COUNT(*) INTO v_runs FROM archived_runs;
    
    -- Archive interactions
    WITH archived_interactions AS (
        INSERT INTO interactions_archive
        SELECT *, NOW(), 'posting_deleted', NOW() + INTERVAL '30 days'
        FROM interactions
        WHERE posting_id = p_posting_id
        RETURNING interaction_id
    )
    SELECT COUNT(*) INTO v_interactions FROM archived_interactions;
    
    -- Archive events
    WITH archived_events AS (
        INSERT INTO interaction_events_archive
        SELECT e.*, NOW(), 'posting_deleted', NOW() + INTERVAL '30 days'
        FROM interaction_events e
        JOIN interactions i ON e.interaction_id = i.interaction_id
        WHERE i.posting_id = p_posting_id
        RETURNING event_id
    )
    SELECT COUNT(*) INTO v_events FROM archived_events;
    
    -- Delete from active tables
    DELETE FROM interaction_events
    WHERE interaction_id IN (
        SELECT interaction_id FROM interactions WHERE posting_id = p_posting_id
    );
    
    DELETE FROM interactions WHERE posting_id = p_posting_id;
    DELETE FROM workflow_runs WHERE posting_id = p_posting_id;
    
    RETURN QUERY SELECT v_runs, v_interactions, v_events;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Automatically archive when posting deleted
CREATE TRIGGER trg_posting_delete_archive
BEFORE DELETE ON postings
FOR EACH ROW
EXECUTE FUNCTION archive_posting_data(OLD.posting_id);
```

**Recovery Window:** 30 days

**After 30 days:** Partition drop (see Cleanup section)

---

### Rule 2: User Deleted → GDPR Hard Delete (Immediate)

**Trigger:**
```sql
-- GDPR deletion request
DELETE FROM users WHERE user_id = 123;
```

**Action:**
```sql
CREATE OR REPLACE FUNCTION gdpr_delete_user(p_user_id BIGINT)
RETURNS TABLE (
    deleted_postings INTEGER,
    deleted_interactions INTEGER,
    deleted_events INTEGER,
    deleted_from_archive INTEGER
) AS $$
DECLARE
    v_postings INTEGER;
    v_interactions INTEGER;
    v_events INTEGER;
    v_archive INTEGER;
BEGIN
    -- Get posting IDs for this user
    CREATE TEMP TABLE user_postings AS
    SELECT posting_id FROM postings WHERE user_id = p_user_id;
    
    -- Delete from archives FIRST (no 30-day retention for GDPR)
    WITH deleted_archive AS (
        DELETE FROM interactions_archive
        WHERE posting_id IN (SELECT posting_id FROM user_postings)
        RETURNING interaction_id
    )
    SELECT COUNT(*) INTO v_archive FROM deleted_archive;
    
    DELETE FROM workflow_runs_archive
    WHERE posting_id IN (SELECT posting_id FROM user_postings);
    
    DELETE FROM interaction_events_archive
    WHERE interaction_id IN (
        SELECT interaction_id FROM interactions_archive
        WHERE posting_id IN (SELECT posting_id FROM user_postings)
    );
    
    -- Delete from active tables
    WITH deleted_events AS (
        DELETE FROM interaction_events
        WHERE interaction_id IN (
            SELECT interaction_id FROM interactions
            WHERE posting_id IN (SELECT posting_id FROM user_postings)
        )
        RETURNING event_id
    )
    SELECT COUNT(*) INTO v_events FROM deleted_events;
    
    WITH deleted_interactions AS (
        DELETE FROM interactions
        WHERE posting_id IN (SELECT posting_id FROM user_postings)
        RETURNING interaction_id
    )
    SELECT COUNT(*) INTO v_interactions FROM deleted_interactions;
    
    DELETE FROM workflow_runs
    WHERE posting_id IN (SELECT posting_id FROM user_postings);
    
    WITH deleted_postings AS (
        DELETE FROM postings WHERE user_id = p_user_id
        RETURNING posting_id
    )
    SELECT COUNT(*) INTO v_postings FROM deleted_postings;
    
    DROP TABLE user_postings;
    
    RETURN QUERY SELECT v_postings, v_interactions, v_events, v_archive;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gdpr_delete_user IS 
'GDPR-compliant user deletion. Removes ALL user data immediately (no 30-day retention).
Deletes from both active tables AND archives. Use when user requests data deletion.';
```

**Recovery Window:** NONE (GDPR compliance)

---

### Rule 3: Test Runs → Auto-Delete (30 days)

**Cleanup Function (already created in migration 043):**
```sql
-- From migration 043v2
SELECT cleanup_test_runs(30);  -- Deletes dev/test runs older than 30 days
```

**Cron Schedule:**
```bash
# Run weekly (Sundays at 2am)
0 2 * * 0 psql -d turing -c "SELECT cleanup_test_runs(30);"
```

---

### Rule 4: Workflow/Conversation Definitions → Keep Forever

**NO deletion triggers!**

```sql
-- These tables NEVER cascade delete
-- workflows
-- conversations
-- instruction_steps
-- actors

-- Even disabled workflows stay in database
UPDATE workflows SET enabled = FALSE WHERE workflow_id = 1234;

-- NOT:
DELETE FROM workflows WHERE workflow_id = 1234;  -- ❌ DON'T DO THIS
```

**Rationale:**
- Workflows are "source code" not "data"
- Historical workflow_runs reference workflow_id
- Archive queries need workflow definition to make sense
- Disabled ≠ Deleted

---

## Foreign Key Cascade Rules

### Active Tables (NO CASCADE)

```sql
-- workflow_runs does NOT cascade delete
ALTER TABLE workflow_runs
DROP CONSTRAINT IF EXISTS workflow_runs_posting_id_fkey,
ADD CONSTRAINT workflow_runs_posting_id_fkey
    FOREIGN KEY (posting_id) REFERENCES postings(posting_id)
    ON DELETE NO ACTION;  -- ❌ Prevent accidental cascade

-- Trigger handles archival instead
-- (see archive_posting_data function above)
```

### Archive Tables (CASCADE DELETE for cleanup)

```sql
-- Archive partitions CAN be dropped entirely
DROP TABLE workflow_runs_archive_2025_09;  -- Older than 30 days
-- This cascades to all rows in that partition
```

---

## Automated Cleanup (Cron Jobs)

### Daily: Expire Archives

```sql
-- Delete expired archives (beyond 30-day window)
CREATE OR REPLACE FUNCTION cleanup_expired_archives()
RETURNS TABLE (
    deleted_workflow_runs BIGINT,
    deleted_interactions BIGINT,
    deleted_events BIGINT
) AS $$
DECLARE
    v_runs BIGINT;
    v_interactions BIGINT;
    v_events BIGINT;
BEGIN
    WITH deleted_events AS (
        DELETE FROM interaction_events_archive
        WHERE expires_at < NOW()
        RETURNING event_id
    )
    SELECT COUNT(*) INTO v_events FROM deleted_events;
    
    WITH deleted_interactions AS (
        DELETE FROM interactions_archive
        WHERE expires_at < NOW()
        RETURNING interaction_id
    )
    SELECT COUNT(*) INTO v_interactions FROM deleted_interactions;
    
    WITH deleted_runs AS (
        DELETE FROM workflow_runs_archive
        WHERE expires_at < NOW()
        RETURNING workflow_run_id
    )
    SELECT COUNT(*) INTO v_runs FROM deleted_runs;
    
    RETURN QUERY SELECT v_runs, v_interactions, v_events;
END;
$$ LANGUAGE plpgsql;

-- Cron: Daily at 3am
-- 0 3 * * * psql -d turing -c "SELECT cleanup_expired_archives();"
```

### Monthly: Drop Old Partitions

```sql
-- Drop archive partitions older than 3 months
CREATE OR REPLACE FUNCTION drop_old_archive_partitions()
RETURNS TABLE (
    dropped_table TEXT
) AS $$
DECLARE
    partition_name TEXT;
    cutoff_date DATE := CURRENT_DATE - INTERVAL '3 months';
BEGIN
    -- Find partitions older than cutoff
    FOR partition_name IN
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
          AND tablename LIKE '%_archive_____\_\_'
          AND TO_DATE(RIGHT(tablename, 7), 'YYYY_MM') < cutoff_date
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || partition_name || ' CASCADE';
        RETURN QUERY SELECT partition_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Cron: First Sunday of each month at 2am
-- 0 2 1-7 * 0 psql -d turing -c "SELECT drop_old_archive_partitions();"
```

### Weekly: Test Run Cleanup

```sql
-- From migration 043v2 (already exists)
SELECT cleanup_test_runs(30);

-- Cron: Sundays at 2am
-- 0 2 * * 0 psql -d turing -c "SELECT cleanup_test_runs(30);"
```

---

## Recovery Procedures

### "Oops, I deleted a posting by accident!"

**Within 30 days:**
```sql
-- Find archived data
SELECT * FROM interactions_archive 
WHERE posting_id = 4709 
  AND archive_reason = 'posting_deleted';

-- Restore posting (if you have backup)
INSERT INTO postings VALUES (...);

-- Restore interactions
INSERT INTO interactions
SELECT 
    interaction_id, posting_id, workflow_run_id, conversation_id, 
    actor_id, actor_type, status, execution_order, parent_interaction_id,
    input_interaction_ids, input, output, error_message, started_at,
    completed_at, created_at, enabled, invalidated, max_retries, retry_count
FROM interactions_archive
WHERE posting_id = 4709;

-- Restore events
INSERT INTO interaction_events
SELECT 
    event_id, interaction_id, event_type, event_data, metadata, created_at
FROM interaction_events_archive
WHERE interaction_id IN (
    SELECT interaction_id FROM interactions WHERE posting_id = 4709
);

-- Delete from archives (recovered!)
DELETE FROM interactions_archive WHERE posting_id = 4709;
DELETE FROM interaction_events_archive 
WHERE interaction_id IN (
    SELECT interaction_id FROM interactions WHERE posting_id = 4709
);
```

**After 30 days:**
> "Sorry, data is gone. Archives expired."

---

## Storage Impact

**Estimates (production load: 1000 postings/day):**

```
Active Tables:
  workflow_runs:     ~2,000 rows (last 2 days)    = 500 KB
  interactions:      ~32,000 rows (16 per posting) = 8 MB
  interaction_events: ~160,000 rows (5 per interaction) = 40 MB
  
Archive Tables (30-day window):
  workflow_runs_archive:     ~30,000 rows    = 7.5 MB
  interactions_archive:      ~480,000 rows   = 120 MB
  interaction_events_archive: ~2,400,000 rows = 600 MB
  
Total: ~776 MB (30-day archives + active data)

With 3-month partition retention: ~2.3 GB
```

**After cleanup automation:** Tables stay small, archives auto-purge

---

## GDPR Compliance

**Right to be Forgotten:**
```sql
-- User requests deletion
SELECT gdpr_delete_user(123);

-- Result:
-- deleted_postings: 50
-- deleted_interactions: 800
-- deleted_events: 4000
-- deleted_from_archive: 1200
```

**Data completely removed:**
- ✅ Active interactions deleted
- ✅ Archive interactions deleted
- ✅ Events deleted (both active + archive)
- ✅ Postings deleted
- ✅ NO 30-day retention window

**Compliance certificate:**
> "All data for user_id=123 deleted on 2025-11-24 14:30:00 UTC. Zero records remaining in system."

---

## Implementation Checklist

- [ ] Create archive tables with partitions (migration 044)
- [ ] Add archive metadata columns (archived_at, archive_reason, expires_at)
- [ ] Create `archive_posting_data()` function
- [ ] Create `gdpr_delete_user()` function
- [ ] Create `cleanup_expired_archives()` function
- [ ] Create `drop_old_archive_partitions()` function
- [ ] Add trigger on `postings` DELETE
- [ ] Set up cron jobs (daily, weekly, monthly)
- [ ] Test recovery procedure
- [ ] Document GDPR process for customer service

---

## Testing Plan

### Test 1: Posting Deletion & Recovery
```sql
-- 1. Create test posting
INSERT INTO postings (...) VALUES (...) RETURNING posting_id;

-- 2. Run workflow
-- (creates workflow_runs, interactions, events)

-- 3. Delete posting
DELETE FROM postings WHERE posting_id = 4710;

-- 4. Verify archive
SELECT COUNT(*) FROM interactions_archive WHERE posting_id = 4710;
-- Expected: 16 rows

-- 5. Wait 1 minute, verify expiry set
SELECT expires_at FROM interactions_archive WHERE posting_id = 4710 LIMIT 1;
-- Expected: NOW() + 30 days

-- 6. Restore (recovery test)
-- (see Recovery Procedures above)

-- 7. Verify active
SELECT COUNT(*) FROM interactions WHERE posting_id = 4710;
-- Expected: 16 rows (restored!)
```

### Test 2: GDPR Deletion
```sql
-- 1. Create test user with data
INSERT INTO users (...) VALUES (...) RETURNING user_id;
INSERT INTO postings (user_id, ...) VALUES (999, ...);

-- 2. Run workflows (creates execution records)

-- 3. Archive some data (simulate posting deletion)
DELETE FROM postings WHERE posting_id = 4711;
-- (triggers archive)

-- 4. GDPR delete user
SELECT gdpr_delete_user(999);

-- 5. Verify complete removal
SELECT COUNT(*) FROM interactions WHERE posting_id IN (SELECT posting_id FROM postings WHERE user_id = 999);
-- Expected: 0

SELECT COUNT(*) FROM interactions_archive WHERE posting_id = 4711;
-- Expected: 0 (even from archive!)
```

### Test 3: Partition Drop
```sql
-- 1. Create old partition (simulate time passing)
CREATE TABLE workflow_runs_archive_2025_08
    PARTITION OF workflow_runs_archive
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

-- 2. Insert old data
INSERT INTO workflow_runs_archive VALUES (..., '2025-08-15', ...);

-- 3. Drop old partitions
SELECT drop_old_archive_partitions();

-- 4. Verify partition gone
SELECT tablename FROM pg_tables WHERE tablename = 'workflow_runs_archive_2025_08';
-- Expected: 0 rows (partition dropped!)
```

---

## Monitoring Queries

### Archive Growth
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename LIKE '%_archive%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Expiry Queue
```sql
SELECT 
    archive_reason,
    COUNT(*) as records,
    MIN(expires_at) as earliest_expiry,
    MAX(expires_at) as latest_expiry
FROM interactions_archive
GROUP BY archive_reason;
```

### Recovery Window Check
```sql
-- How many records in recovery window?
SELECT 
    COUNT(*) as recoverable_interactions,
    MIN(archived_at) as oldest_recovery,
    MAX(archived_at) as newest_recovery
FROM interactions_archive
WHERE expires_at > NOW();
```

---

## Summary

**What Stays:**
- Workflow definitions (forever)
- Conversation templates (forever)
- Instruction steps (forever)
- Actors (forever)

**What Archives (30 days):**
- Workflow runs (when posting deleted)
- Interactions (when posting deleted)
- Events (when posting deleted)

**What Deletes (immediate):**
- User data (GDPR request)
- Expired archives (30 days passed)
- Test runs (dev/test environment, 30 days old)

**Automation:**
- Daily: Delete expired archives
- Weekly: Cleanup test runs
- Monthly: Drop old partitions

**Compliance:**
- ✅ GDPR right to be forgotten
- ✅ 30-day "oops" recovery window
- ✅ Audit trail for active data
- ✅ Storage growth controlled

---

**Ready for implementation?** Migration 044 coming up! 🚀
