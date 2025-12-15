-- Migration 043v2: Add Model Testing Infrastructure (Fixed)
-- Date: 2025-11-24
-- Author: Arden
-- Purpose: Add model testing columns + automatic champion selection
-- Note: workflows.environment already exists with values DEV/UAT/PROD/OLD

-- ============================================================================
-- PHASE 1: Fix workflows.environment (already exists, update constraints)
-- ============================================================================

-- Drop old constraint
ALTER TABLE workflows DROP CONSTRAINT IF EXISTS workflows_environment_check;

-- Add new constraint with lowercase + test
ALTER TABLE workflows 
ADD CONSTRAINT workflows_environment_check 
CHECK (environment IN ('dev', 'test', 'uat', 'prod', 'old', 'DEV', 'UAT', 'PROD', 'OLD'));

-- Update existing values to lowercase
UPDATE workflows SET environment = LOWER(environment);

-- Now enforce lowercase only
ALTER TABLE workflows DROP CONSTRAINT workflows_environment_check;
ALTER TABLE workflows 
ADD CONSTRAINT workflows_environment_check 
CHECK (environment IN ('dev', 'test', 'uat', 'prod', 'old'));

-- Add skip_data_writes column
ALTER TABLE workflows 
ADD COLUMN skip_data_writes BOOLEAN DEFAULT FALSE;

-- Create index for environment filtering
DROP INDEX IF EXISTS idx_workflows_environment;
CREATE INDEX idx_workflows_environment ON workflows(environment) WHERE enabled = TRUE;

-- Update comments
COMMENT ON COLUMN workflows.environment IS 
'Execution environment: dev (development), test (shadow testing), uat (stakeholder review), prod (production), old (archived).
Test/UAT workflows should set skip_data_writes=TRUE to prevent writing to postings/profiles tables.';

COMMENT ON COLUMN workflows.skip_data_writes IS 
'If TRUE, saver scripts will skip writing to data tables (postings, profiles, etc).
Used for shadow testing where we want to compare model outputs without affecting production data.';

-- ============================================================================
-- PHASE 2: Add environment to workflow_runs (if not exists)
-- ============================================================================

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'workflow_runs' AND column_name = 'environment'
    ) THEN
        ALTER TABLE workflow_runs ADD COLUMN environment TEXT;
        
        -- Backfill from workflows
        UPDATE workflow_runs wr
        SET environment = w.environment
        FROM workflows w
        WHERE wr.workflow_id = w.workflow_id;
        
        -- Make NOT NULL after backfill
        ALTER TABLE workflow_runs ALTER COLUMN environment SET NOT NULL;
        
        -- Create index
        CREATE INDEX idx_workflow_runs_environment ON workflow_runs(environment, started_at);
    END IF;
END $$;

-- Create trigger to auto-populate environment (drop if exists)
DROP TRIGGER IF EXISTS trg_workflow_run_environment ON workflow_runs;
DROP FUNCTION IF EXISTS set_workflow_run_environment();

CREATE OR REPLACE FUNCTION set_workflow_run_environment()
RETURNS TRIGGER AS $$
BEGIN
    SELECT environment INTO NEW.environment
    FROM workflows
    WHERE workflow_id = NEW.workflow_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_workflow_run_environment
BEFORE INSERT ON workflow_runs
FOR EACH ROW
EXECUTE FUNCTION set_workflow_run_environment();

COMMENT ON COLUMN workflow_runs.environment IS 
'Inherited from workflows.environment. Used to filter/cleanup test runs.
Cleanup policy: DELETE test/dev runs older than 30 days, keep uat/prod forever.';

-- ============================================================================
-- PHASE 3: Add model testing fields to actors
-- ============================================================================

-- Add production flag
ALTER TABLE actors 
ADD COLUMN IF NOT EXISTS is_production BOOLEAN DEFAULT TRUE;

-- Add model variant
ALTER TABLE actors 
ADD COLUMN IF NOT EXISTS model_variant TEXT;

-- Add traffic weight for canary testing
ALTER TABLE actors 
ADD COLUMN IF NOT EXISTS traffic_weight INTEGER DEFAULT 100;

-- Add performance tracking
ALTER TABLE actors
ADD COLUMN IF NOT EXISTS last_performance_check TIMESTAMP;

-- Create indexes
DROP INDEX IF EXISTS idx_actors_production;
CREATE INDEX idx_actors_production ON actors(is_production, enabled) 
WHERE actor_type = 'ai_model';

DROP INDEX IF EXISTS idx_actors_variant;
CREATE INDEX idx_actors_variant ON actors(model_variant) 
WHERE model_variant IS NOT NULL;

-- Add comments
COMMENT ON COLUMN actors.is_production IS 
'TRUE if this actor serves production traffic. FALSE for experimental/challenger models.
Use for filtering production-ready actors in conversation routing.';

COMMENT ON COLUMN actors.model_variant IS 
'Role in A/B testing: "champion" (current best), "challenger_a", "challenger_b", etc.
Only one champion per conversation. Challengers compete to replace champion.';

COMMENT ON COLUMN actors.traffic_weight IS 
'Percentage of traffic (0-100) for canary testing. 
Example: champion=95, challenger=5 means 5% of requests go to challenger.
SUM of weights for same conversation should = 100.';

COMMENT ON COLUMN actors.last_performance_check IS 
'Last time automatic champion selection workflow evaluated this actor.
Updated weekly by workflow 3XXX.';

-- ============================================================================
-- PHASE 4: Create model performance view
-- ============================================================================

DROP VIEW IF EXISTS model_performance;

CREATE VIEW model_performance AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.model_variant,
    a.is_production,
    i.conversation_id,
    COUNT(*) as execution_count,
    AVG(CAST(i.output->>'latency_ms' AS INT)) as avg_latency_ms,
    STDDEV(CAST(i.output->>'latency_ms' AS INT)) as latency_stddev,
    MIN(CAST(i.output->>'latency_ms' AS INT)) as min_latency_ms,
    MAX(CAST(i.output->>'latency_ms' AS INT)) as max_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST(i.output->>'latency_ms' AS INT)) as p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CAST(i.output->>'latency_ms' AS INT)) as p95_latency_ms,
    COUNT(*) FILTER (WHERE i.status = 'completed') as success_count,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failure_count,
    COUNT(*) FILTER (WHERE i.status = 'completed')::FLOAT / NULLIF(COUNT(*), 0) as success_rate,
    MIN(i.created_at) as first_execution,
    MAX(i.created_at) as last_execution,
    -- Performance score: balance speed and reliability
    CASE 
        WHEN AVG(CAST(i.output->>'latency_ms' AS INT)) > 0 THEN
            (1000.0 / AVG(CAST(i.output->>'latency_ms' AS INT))) * 
            (COUNT(*) FILTER (WHERE i.status = 'completed')::FLOAT / NULLIF(COUNT(*), 0))
        ELSE 0
    END as performance_score
FROM interactions i
JOIN actors a ON i.actor_id = a.actor_id
WHERE i.created_at > NOW() - INTERVAL '7 days'
  AND a.actor_type = 'ai_model'
  AND i.output IS NOT NULL
GROUP BY a.actor_id, a.actor_name, a.model_variant, a.is_production, i.conversation_id;

COMMENT ON VIEW model_performance IS 
'7-day rolling performance metrics for all AI models.
Used by workflow 3XXX (automatic champion selection) to compare models.
Performance score = (1000/avg_latency_ms) * success_rate (higher is better).';

-- ============================================================================
-- PHASE 5: Create helper functions
-- ============================================================================

-- Function: Get production actors for a conversation
DROP FUNCTION IF EXISTS get_production_actors(INT);

CREATE OR REPLACE FUNCTION get_production_actors(p_conversation_id INT)
RETURNS TABLE (
    actor_id INT,
    actor_name TEXT,
    model_variant TEXT,
    traffic_weight INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.actor_id,
        a.actor_name,
        a.model_variant,
        a.traffic_weight
    FROM actors a
    JOIN conversations c ON a.actor_id = c.actor_id
    WHERE c.conversation_id = p_conversation_id
      AND a.enabled = TRUE
      AND a.is_production = TRUE
    ORDER BY a.traffic_weight DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_production_actors IS 
'Get all production-ready actors for a conversation, sorted by traffic weight.
Used for canary testing: router selects actor based on traffic_weight percentage.';

-- Function: Cleanup old test runs
DROP FUNCTION IF EXISTS cleanup_test_runs(INT);

CREATE OR REPLACE FUNCTION cleanup_test_runs(p_days_old INT DEFAULT 30)
RETURNS TABLE (
    deleted_workflow_runs BIGINT,
    deleted_interactions BIGINT
) AS $$
DECLARE
    v_deleted_runs BIGINT;
    v_deleted_interactions BIGINT;
BEGIN
    -- Delete interactions first (FK constraint)
    WITH deleted_interactions AS (
        DELETE FROM interactions
        WHERE workflow_run_id IN (
            SELECT workflow_run_id 
            FROM workflow_runs
            WHERE environment IN ('dev', 'test')
              AND started_at < NOW() - (p_days_old || ' days')::INTERVAL
        )
        RETURNING interaction_id
    )
    SELECT COUNT(*) INTO v_deleted_interactions FROM deleted_interactions;
    
    -- Delete workflow runs
    WITH deleted_runs AS (
        DELETE FROM workflow_runs
        WHERE environment IN ('dev', 'test')
          AND started_at < NOW() - (p_days_old || ' days')::INTERVAL
        RETURNING workflow_run_id
    )
    SELECT COUNT(*) INTO v_deleted_runs FROM deleted_runs;
    
    RETURN QUERY SELECT v_deleted_runs, v_deleted_interactions;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_test_runs IS 
'Delete test/dev workflow runs older than N days (default 30).
Keeps UAT and prod runs forever. Returns count of deleted runs and interactions.';

-- ============================================================================
-- PHASE 6: Update existing data
-- ============================================================================

-- Mark all existing AI actors as production champions
UPDATE actors 
SET is_production = TRUE,
    model_variant = 'champion',
    traffic_weight = 100
WHERE actor_type = 'ai_model' 
  AND enabled = TRUE
  AND is_production IS NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check environments
SELECT environment, COUNT(*) as workflow_count
FROM workflows
GROUP BY environment
ORDER BY environment;

-- Check production actors
SELECT 
    actor_name, 
    model_variant, 
    is_production, 
    traffic_weight,
    enabled
FROM actors
WHERE actor_type = 'ai_model'
ORDER BY is_production DESC NULLS LAST, traffic_weight DESC;

-- Check if model_performance view works
SELECT 
    actor_name,
    conversation_id,
    execution_count,
    ROUND(CAST(avg_latency_ms AS NUMERIC)) as avg_latency,
    ROUND(CAST(COALESCE(success_rate, 0) * 100 AS NUMERIC), 1) || '%' as success_rate,
    ROUND(CAST(COALESCE(performance_score, 0) AS NUMERIC), 2) as score
FROM model_performance
WHERE execution_count >= 1
ORDER BY conversation_id, performance_score DESC NULLS LAST
LIMIT 20;
