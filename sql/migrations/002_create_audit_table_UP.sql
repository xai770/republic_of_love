-- Migration: 002_create_audit_table_UP.sql
-- Description: Create interaction_events table (audit layer with time travel)
-- Author: Sandy (GitHub Copilot)
-- Date: November 23, 2025
-- Phase: 1 (Foundation)
-- Reference: Appendix A (Audit Layer Architecture)

-- Create interaction_events table (partitioned by timestamp)
CREATE TABLE IF NOT EXISTS interaction_events (
    event_id BIGSERIAL PRIMARY KEY,
    interaction_id BIGINT REFERENCES interactions(interaction_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'interaction_created',
        'interaction_started',
        'interaction_completed',
        'interaction_failed',
        'interaction_invalidated',
        'interaction_branched',
        'interaction_retried'
    )),
    event_data JSONB NOT NULL,
    event_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Event provenance (causation chains)
    causation_event_id BIGINT REFERENCES interaction_events(event_id) ON DELETE SET NULL,
    correlation_id TEXT,  -- Links all events in workflow run
    
    -- Tamper detection (SHA256 hash - computed via trigger)
    event_hash TEXT
);

-- Trigger to compute event hash on insert
CREATE OR REPLACE FUNCTION compute_event_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.event_hash = encode(sha256(
        (NEW.event_id || NEW.event_type || NEW.event_data::text || NEW.event_timestamp::text)::bytea
    ), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER event_hash_trigger
    BEFORE INSERT ON interaction_events
    FOR EACH ROW
    EXECUTE FUNCTION compute_event_hash();

-- Indexes for performance
CREATE INDEX idx_interaction_events_interaction 
    ON interaction_events(interaction_id, event_timestamp);

CREATE INDEX idx_interaction_events_correlation 
    ON interaction_events(correlation_id);

CREATE INDEX idx_interaction_events_type 
    ON interaction_events(event_type, event_timestamp);

CREATE INDEX idx_interaction_events_causation 
    ON interaction_events(causation_event_id);

-- Comments for documentation
COMMENT ON TABLE interaction_events IS 'Immutable audit log for all interaction events (time travel, compliance, forensics)';
COMMENT ON COLUMN interaction_events.event_hash IS 'SHA256 hash for tamper detection';
COMMENT ON COLUMN interaction_events.causation_event_id IS 'Parent event that caused this event (event provenance)';
COMMENT ON COLUMN interaction_events.correlation_id IS 'workflow_run_id to trace all events in a workflow run';
