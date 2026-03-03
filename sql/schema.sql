--
-- PostgreSQL database dump
--

\restrict 2gt57p7zmdyrolFnoOeh6ZVsqJ1zk4IjuEXNf3mhIwfcaBfUr2fcgx8qEcNVlm0

-- Dumped from database version 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: archive; Type: SCHEMA; Schema: -; Owner: base_admin
--

CREATE SCHEMA archive;


ALTER SCHEMA archive OWNER TO base_admin;

--
-- Name: pg_cron; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA public;


--
-- Name: EXTENSION pg_cron; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_cron IS 'Job scheduler for PostgreSQL';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: append_event(text, text, text, jsonb, jsonb, integer, text, bigint, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb DEFAULT NULL::jsonb, p_event_version integer DEFAULT 1, p_correlation_id text DEFAULT NULL::text, p_causation_id bigint DEFAULT NULL::bigint, p_idempotency_key text DEFAULT NULL::text) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_next_version INT;
    v_event_id BIGINT;
    v_existing_event_id BIGINT;
BEGIN
    -- Check idempotency: if key exists, return existing event_id
    IF p_idempotency_key IS NOT NULL THEN
        SELECT event_id INTO v_existing_event_id
        FROM execution_events
        WHERE idempotency_key = p_idempotency_key;
        
        IF v_existing_event_id IS NOT NULL THEN
            -- Already processed, return existing
            RETURN v_existing_event_id;
        END IF;
    END IF;
    
    -- Get next version for this aggregate
    SELECT COALESCE(MAX(aggregate_version), 0) + 1
    INTO v_next_version
    FROM execution_events
    WHERE aggregate_type = p_aggregate_type
      AND aggregate_id = p_aggregate_id;
    
    -- Insert event
    INSERT INTO execution_events (
        aggregate_type,
        aggregate_id,
        aggregate_version,
        event_type,
        event_version,
        event_data,
        metadata,
        correlation_id,
        causation_id,
        idempotency_key
    ) VALUES (
        p_aggregate_type,
        p_aggregate_id,
        v_next_version,
        p_event_type,
        p_event_version,
        p_event_data,
        p_metadata,
        p_correlation_id,
        p_causation_id,
        p_idempotency_key
    )
    RETURNING event_id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$;


ALTER FUNCTION public.append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb, p_event_version integer, p_correlation_id text, p_causation_id bigint, p_idempotency_key text) OWNER TO base_admin;

--
-- Name: FUNCTION append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb, p_event_version integer, p_correlation_id text, p_causation_id bigint, p_idempotency_key text); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb, p_event_version integer, p_correlation_id text, p_causation_id bigint, p_idempotency_key text) IS 'Append event to event store with automatic versioning and idempotency protection.';


--
-- Name: archive_capabilities(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_capabilities() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            INSERT INTO facets_history (
                facet_id, facet_label, parent_id, facet_order,
                enabled, created_at, updated_at, change_reason
            ) VALUES (
                OLD.facet_name, OLD.facet_label, OLD.parent_facet_name, OLD.facet_order,
                OLD.enabled, OLD.created_at, OLD.updated_at, 'Updated via trigger'
            );
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;


ALTER FUNCTION public.archive_capabilities() OWNER TO base_admin;

--
-- Name: archive_conversations(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_conversations() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO sessions_history (
        session_id, canonical_code, session_name, session_description,
        actor_id, context_strategy, max_instruction_runs, enabled,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.session_id, OLD.canonical_name, OLD.session_name, OLD.session_description,
        OLD.actor_id, OLD.context_strategy, OLD.max_instruction_runs, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_conversations() OWNER TO base_admin;

--
-- Name: FUNCTION archive_conversations(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.archive_conversations() IS 'Updated 2025-10-30: Uses canonical_name from sessions (renamed from canonical_code)';


--
-- Name: archive_instructions(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_instructions() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO instructions_history (
        instruction_id, session_id, step_number, step_description, prompt_template,
        timeout_seconds, expected_pattern, validation_rules, is_terminal, enabled,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.instruction_id, OLD.session_id, OLD.step_number, OLD.step_description, OLD.prompt_template,
        OLD.timeout_seconds, OLD.expected_pattern, OLD.validation_rules, OLD.is_terminal, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_instructions() OWNER TO base_admin;

--
-- Name: archive_interaction_before_delete(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_interaction_before_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO interactions_history (
        interaction_id,
        posting_id,
        conversation_id,
        workflow_run_id,
        actor_id,
        actor_type,
        status,
        execution_order,
        parent_interaction_id,
        trigger_interaction_id,
        input_interaction_ids,
        input,
        output,
        error_message,
        retry_count,
        max_retries,
        enabled,
        invalidated,
        created_at,
        updated_at,
        started_at,
        completed_at,
        archive_reason
    ) VALUES (
        OLD.interaction_id,
        OLD.posting_id,
        OLD.conversation_id,
        OLD.workflow_run_id,
        OLD.actor_id,
        OLD.actor_type,
        OLD.status,
        OLD.execution_order,
        OLD.parent_interaction_id,
        OLD.trigger_interaction_id,
        OLD.input_interaction_ids,
        OLD.input,
        OLD.output,
        OLD.error_message,
        OLD.retry_count,
        OLD.max_retries,
        OLD.enabled,
        OLD.invalidated,
        OLD.created_at,
        OLD.updated_at,
        OLD.started_at,
        OLD.completed_at,
        'deleted'
    );
    RETURN OLD;
END;
$$;


ALTER FUNCTION public.archive_interaction_before_delete() OWNER TO base_admin;

--
-- Name: archive_test_cases(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_test_cases() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO variations_history (
        variation_id, recipe_id, test_data, difficulty_level, expected_response,
        response_format, complexity_score, enabled,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.variation_id, OLD.recipe_id, OLD.test_data, OLD.difficulty_level, OLD.expected_response,
        OLD.response_format, OLD.complexity_score, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_test_cases() OWNER TO base_admin;

--
-- Name: archive_validated_prompts(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_validated_prompts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO canonicals_history (
        canonical_code, facet_id, capability_description, prompt, response,
        review_notes, enabled, created_at, updated_at, change_reason
    ) VALUES (
        OLD.canonical_name, OLD.facet_name, OLD.capability_description, OLD.prompt, OLD.response,
        OLD.review_notes, OLD.enabled, OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_validated_prompts() OWNER TO base_admin;

--
-- Name: archive_workflows(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_workflows() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO workflows_history (
        workflow_id, workflow_name, workflow_description, workflow_version,
        max_total_session_runs, enabled, review_notes,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.workflow_id, OLD.workflow_name, OLD.workflow_description, OLD.workflow_version,
        OLD.max_total_session_runs, OLD.enabled, OLD.review_notes,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_workflows() OWNER TO base_admin;

--
-- Name: auto_queue_run3(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.auto_queue_run3() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    pending_count INTEGER;
    run2_complete BOOLEAN;
BEGIN
    -- Only check for WF3007
    IF NEW.workflow_id != 3007 THEN
        RETURN NEW;
    END IF;
    
    -- Check if all Run 2 queue items are completed
    SELECT COUNT(*) = 0 INTO run2_complete
    FROM queue 
    WHERE workflow_id = 3007 
      AND reason LIKE 'RAQ2_%' 
      AND status = 'pending';
    
    -- Check if entities_pending has any pending left
    SELECT COUNT(*) INTO pending_count
    FROM entities_pending 
    WHERE entity_type = 'skill' AND status = 'pending';
    
    -- If Run 2 done (no pending skills) and Run 3 not queued yet
    IF pending_count = 0 AND run2_complete THEN
        -- Check if Run 3 already queued
        IF NOT EXISTS (SELECT 1 FROM queue WHERE reason LIKE 'RAQ3_%') THEN
            -- Reset entities_pending for Run 3
            UPDATE entities_pending 
            SET status = 'pending', processed_at = NULL
            WHERE entity_type = 'skill';
            
            -- Queue Run 3
            INSERT INTO queue (workflow_id, start_step, priority, status, reason)
            SELECT 3007, 'wf3007_c1_fetch', 100, 'pending', 'RAQ3_' || LPAD(row_number::text, 4, '0')
            FROM (SELECT ROW_NUMBER() OVER () as row_number FROM generate_series(1, 8430)) x;
            
            RAISE NOTICE 'Auto-queued RAQ Run 3 with 8430 skills';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.auto_queue_run3() OWNER TO base_admin;

--
-- Name: calculate_next_cron_run(character varying, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.calculate_next_cron_run(p_cron character varying, p_from_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP) RETURNS timestamp without time zone
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_next_run TIMESTAMP;
BEGIN
    -- Simplified cron parser (extend this for production)
    -- For now, support basic patterns like '0 8 * * *' (daily at 8 AM)
    
    -- This is a placeholder - in production, use pg_cron or similar
    -- For demo: if cron is '0 8 * * *', next run is tomorrow at 8 AM
    IF p_cron ~ '^\d+ \d+ \* \* \*$' THEN
        v_next_run := DATE_TRUNC('day', p_from_time + INTERVAL '1 day') + 
                      (SPLIT_PART(p_cron, ' ', 2) || ' hours')::INTERVAL +
                      (SPLIT_PART(p_cron, ' ', 1) || ' minutes')::INTERVAL;
    ELSE
        -- Default: run in 1 hour
        v_next_run := p_from_time + INTERVAL '1 hour';
    END IF;
    
    RETURN v_next_run;
END;
$_$;


ALTER FUNCTION public.calculate_next_cron_run(p_cron character varying, p_from_time timestamp without time zone) OWNER TO base_admin;

--
-- Name: calculate_skill_match(integer, integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.calculate_skill_match(p_posting_id integer, p_profile_id integer) RETURNS TABLE(job_skill_name text, profile_skill_name text, match_type text, hierarchy_distance integer, base_score numeric, final_score numeric, reasoning text)
    LANGUAGE sql
    AS $$
WITH RECURSIVE skill_paths AS (
    -- Base: Start from all job skills
    SELECT 
        js.skill_id as job_skill_id,
        js.skill_id as current_skill_id,
        0 as distance,
        ARRAY[js.skill_id] as path
    FROM job_skills js
    WHERE js.posting_id = p_posting_id
    
    UNION
    
    -- Recursive: Traverse UP (to parents) OR DOWN (to children)
    SELECT 
        sp.job_skill_id,
        COALESCE(sh_up.parent_skill_id, sh_down.skill_id) as current_skill_id,
        sp.distance + 1,
        sp.path || COALESCE(sh_up.parent_skill_id, sh_down.skill_id)
    FROM skill_paths sp
    LEFT JOIN skill_hierarchy sh_up ON sh_up.skill_id = sp.current_skill_id
        AND NOT sh_up.parent_skill_id = ANY(sp.path)
    LEFT JOIN skill_hierarchy sh_down ON sh_down.parent_skill_id = sp.current_skill_id
        AND NOT sh_down.skill_id = ANY(sp.path)
    WHERE sp.distance < 3
      AND (sh_up.parent_skill_id IS NOT NULL OR sh_down.skill_id IS NOT NULL)
),
matches AS (
    SELECT 
        sp.job_skill_id,
        ps.skill_id as profile_skill_id,
        sp.distance,
        ROW_NUMBER() OVER (PARTITION BY sp.job_skill_id ORDER BY sp.distance ASC) as rn
    FROM skill_paths sp
    JOIN profile_skills ps ON ps.skill_id = sp.current_skill_id 
        AND ps.profile_id = p_profile_id
)
SELECT 
    ja.skill_name,
    pa.skill_name,
    CASE WHEN m.distance = 0 THEN 'exact' ELSE 'hierarchy_' || m.distance END,
    m.distance,
    js.weight,
    ROUND(js.weight * POWER(0.7, m.distance), 2),
    'Job: ' || js.importance || ' ' || ja.skill_name || 
    ' (' || COALESCE(js.proficiency, '?') || '), Profile: ' || 
    COALESCE(ps.years_experience::TEXT, '?') || 'y ' || 
    pa.skill_name || ' (' || COALESCE(ps.proficiency_level, '?') || ')'
FROM matches m
JOIN job_skills js ON js.skill_id = m.job_skill_id AND js.posting_id = p_posting_id
JOIN profile_skills ps ON ps.skill_id = m.profile_skill_id AND ps.profile_id = p_profile_id
JOIN skill_aliases ja ON ja.skill_id = m.job_skill_id
JOIN skill_aliases pa ON pa.skill_id = m.profile_skill_id
WHERE m.rn = 1
ORDER BY 6 DESC;
$$;


ALTER FUNCTION public.calculate_skill_match(p_posting_id integer, p_profile_id integer) OWNER TO base_admin;

--
-- Name: calculate_skill_match_score(integer, integer, integer, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.calculate_skill_match_score(job_skill_id integer, candidate_skill_id integer, job_weight integer, decay_mode text DEFAULT 'reciprocal'::text) RETURNS TABLE(match_score numeric, match_type text, distance integer, explanation text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_path RECORD;
    v_score NUMERIC;
    v_explanation TEXT;
BEGIN
    -- Find path between skills
    SELECT * INTO v_path
    FROM find_skill_path(job_skill_id, candidate_skill_id, 5);
    
    -- Calculate score based on relationship type
    CASE v_path.relationship_type
        WHEN 'exact' THEN
            v_score := job_weight;
            v_explanation := 'Exact match';
            
        WHEN 'parent' THEN
            -- Candidate has more general skill (e.g., has "databases" when job wants "PostgreSQL")
            IF decay_mode = 'exponential' THEN
                v_score := job_weight * POWER(0.7, v_path.path_length);
                v_explanation := format('Parent skill (70%% per level, %s levels up)', v_path.path_length);
            ELSE
                v_score := job_weight * (1.0 / v_path.path_length) * v_path.path_strength;
                v_explanation := format('Parent skill (reciprocal distance=%s, strength=%s)', 
                                       v_path.path_length, v_path.path_strength);
            END IF;
            
        WHEN 'child' THEN
            -- Candidate has more specific skill (e.g., has "PostgreSQL" when job wants "databases")
            -- This is actually BETTER than exact match in many cases!
            v_score := job_weight * 1.1 * v_path.path_strength;  -- 10% bonus for specificity
            v_explanation := format('Child skill (more specific, +10%% bonus, strength=%s)', 
                                   v_path.path_strength);
            
        WHEN 'sibling' THEN
            -- Related skills through common parent (e.g., PostgreSQL ↔ MySQL via "databases")
            IF decay_mode = 'exponential' THEN
                v_score := job_weight * POWER(0.7, v_path.path_length);
                v_explanation := format('Sibling skill (70%% per level, %s levels total)', 
                                       v_path.path_length);
            ELSE
                v_score := job_weight * (v_path.path_strength / v_path.path_length);
                v_explanation := format('Sibling skill (strength=%s / distance=%s)', 
                                       v_path.path_strength, v_path.path_length);
            END IF;
            
        ELSE  -- 'unrelated'
            v_score := 0;
            v_explanation := 'No relationship found in hierarchy';
    END CASE;
    
    RETURN QUERY SELECT 
        v_score,
        v_path.relationship_type,
        v_path.path_length,
        v_explanation;
END;
$$;


ALTER FUNCTION public.calculate_skill_match_score(job_skill_id integer, candidate_skill_id integer, job_weight integer, decay_mode text) OWNER TO base_admin;

--
-- Name: calculate_work_duration(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.calculate_work_duration() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.start_date IS NOT NULL THEN
        NEW.duration_months = EXTRACT(YEAR FROM AGE(
            COALESCE(NEW.end_date, CURRENT_DATE), 
            NEW.start_date
        )) * 12 + 
        EXTRACT(MONTH FROM AGE(
            COALESCE(NEW.end_date, CURRENT_DATE), 
            NEW.start_date
        ));
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.calculate_work_duration() OWNER TO base_admin;

--
-- Name: cleanup_test_runs(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.cleanup_test_runs(p_days_old integer DEFAULT 30) RETURNS TABLE(deleted_workflow_runs bigint, deleted_interactions bigint)
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.cleanup_test_runs(p_days_old integer) OWNER TO base_admin;

--
-- Name: FUNCTION cleanup_test_runs(p_days_old integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.cleanup_test_runs(p_days_old integer) IS 'Delete test/dev workflow runs older than N days (default 30).
Keeps UAT and prod runs forever. Returns count of deleted runs and interactions.';


--
-- Name: compute_conversation_metrics(date); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.compute_conversation_metrics(target_date date DEFAULT (CURRENT_DATE - 1)) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    rows_inserted INTEGER;
BEGIN
    -- Insert/update metrics for each conversation with completed interactions
    INSERT INTO conversation_metrics (
        conversation_id,
        metric_date,
        sample_count,
        success_count,
        failure_count,
        latency_p50,
        latency_p95,
        latency_p99,
        latency_max,
        latency_avg
    )
    SELECT 
        i.conversation_id,
        target_date,
        COUNT(*) as sample_count,
        COUNT(*) FILTER (WHERE i.status = 'completed') as success_count,
        COUNT(*) FILTER (WHERE i.status = 'failed') as failure_count,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p95,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as p99,
        MAX(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as max_latency,
        AVG(EXTRACT(EPOCH FROM (i.completed_at - i.started_at))) as avg_latency
    FROM interactions i
    WHERE i.started_at IS NOT NULL
      AND i.completed_at IS NOT NULL
      AND i.started_at::date = target_date
      AND i.status IN ('completed', 'failed')
    GROUP BY i.conversation_id
    ON CONFLICT (conversation_id, metric_date) 
    DO UPDATE SET
        sample_count = EXCLUDED.sample_count,
        success_count = EXCLUDED.success_count,
        failure_count = EXCLUDED.failure_count,
        latency_p50 = EXCLUDED.latency_p50,
        latency_p95 = EXCLUDED.latency_p95,
        latency_p99 = EXCLUDED.latency_p99,
        latency_max = EXCLUDED.latency_max,
        latency_avg = EXCLUDED.latency_avg;
    
    GET DIAGNOSTICS rows_inserted = ROW_COUNT;
    RETURN rows_inserted;
END;
$$;


ALTER FUNCTION public.compute_conversation_metrics(target_date date) OWNER TO base_admin;

--
-- Name: FUNCTION compute_conversation_metrics(target_date date); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.compute_conversation_metrics(target_date date) IS 'Compute daily latency metrics. Run via cron: SELECT compute_conversation_metrics();';


--
-- Name: compute_event_hash(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.compute_event_hash() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Use convert_to() instead of ::bytea cast
    NEW.event_hash = encode(sha256(
        convert_to(
            NEW.event_id::text || 
            NEW.event_type || 
            NEW.event_data::text || 
            NEW.event_timestamp::text,
            'UTF8'
        )
    ), 'hex');
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.compute_event_hash() OWNER TO base_admin;

--
-- Name: conversation_has_instruction_steps(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.conversation_has_instruction_steps(p_conversation_id integer) RETURNS boolean
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM instruction_steps ist
        JOIN instructions ins ON ist.instruction_id = ins.instruction_id
        WHERE ins.conversation_id = p_conversation_id
    );
END;
$$;


ALTER FUNCTION public.conversation_has_instruction_steps(p_conversation_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION conversation_has_instruction_steps(p_conversation_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.conversation_has_instruction_steps(p_conversation_id integer) IS 'Returns TRUE if conversation has instruction_steps (conversational mode), FALSE for thick actors';


--
-- Name: count_domains_created_this_week(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.count_domains_created_this_week() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM entities
    WHERE entity_type = 'skill_domain'
      AND created_at > NOW() - INTERVAL '7 days'
      AND created_by = 'wf3006';
    
    RETURN v_count;
END;
$$;


ALTER FUNCTION public.count_domains_created_this_week() OWNER TO base_admin;

--
-- Name: evaluate_event_condition(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.evaluate_event_condition(p_trigger_id integer) RETURNS TABLE(should_trigger boolean, condition_value text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_trigger RECORD;
    v_result INTEGER;
BEGIN
    SELECT * INTO v_trigger FROM workflow_triggers WHERE trigger_id = p_trigger_id;
    
    IF v_trigger.event_condition IS NULL THEN
        RETURN QUERY SELECT false, 'No condition defined';
        RETURN;
    END IF;
    
    -- Execute the condition query (must return a single integer/boolean)
    BEGIN
        EXECUTE v_trigger.event_condition INTO v_result;
        
        IF v_result >= v_trigger.event_threshold THEN
            RETURN QUERY SELECT true, 'Condition met: ' || v_result || ' >= ' || v_trigger.event_threshold;
        ELSE
            RETURN QUERY SELECT false, 'Condition not met: ' || v_result || ' < ' || v_trigger.event_threshold;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT false, 'Error evaluating condition: ' || SQLERRM;
    END;
END;
$$;


ALTER FUNCTION public.evaluate_event_condition(p_trigger_id integer) OWNER TO base_admin;

--
-- Name: find_skill_path(integer, integer, integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.find_skill_path(skill_a integer, skill_b integer, max_depth integer DEFAULT 5) RETURNS TABLE(path_length integer, relationship_type text, common_ancestor integer, path_strength numeric)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_path_length INTEGER;
    v_relationship TEXT;
    v_ancestor INTEGER;
    v_strength NUMERIC;
BEGIN
    -- Case 1: Exact match
    IF skill_a = skill_b THEN
        RETURN QUERY SELECT 0, 'exact'::TEXT, NULL::INTEGER, 1.0::NUMERIC;
        RETURN;
    END IF;
    
    -- Case 2: Direct parent (A is parent of B)
    SELECT 1, 'parent', skill_a, strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM skill_hierarchy
    WHERE skill_id = skill_b AND parent_skill_id = skill_a;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 3: Direct child (A is child of B)
    SELECT 1, 'child', skill_b, strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM skill_hierarchy
    WHERE skill_id = skill_a AND parent_skill_id = skill_b;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 4: Siblings (share common parent)
    -- Find common parent with shortest combined distance
    WITH common_parents AS (
        SELECT 
            h1.parent_skill_id as common_parent,
            h1.strength * h2.strength as combined_strength,
            2 as distance  -- 1 hop up + 1 hop down = 2
        FROM skill_hierarchy h1
        JOIN skill_hierarchy h2 ON h1.parent_skill_id = h2.parent_skill_id
        WHERE h1.skill_id = skill_a 
          AND h2.skill_id = skill_b
    )
    SELECT distance, 'sibling', common_parent, combined_strength
    INTO v_path_length, v_relationship, v_ancestor, v_strength
    FROM common_parents
    ORDER BY combined_strength DESC, common_parent
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_path_length, v_relationship, v_ancestor, v_strength;
        RETURN;
    END IF;
    
    -- Case 5: Deeper relationship (BFS through hierarchy up to max_depth)
    -- This gets complex - for now, return "unrelated"
    -- TODO: Implement full graph traversal if needed
    
    RETURN QUERY SELECT NULL::INTEGER, 'unrelated'::TEXT, NULL::INTEGER, 0.0::NUMERIC;
END;
$$;


ALTER FUNCTION public.find_skill_path(skill_a integer, skill_b integer, max_depth integer) OWNER TO base_admin;

--
-- Name: get_aggregate_events(text, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_aggregate_events(p_aggregate_type text, p_aggregate_id text) RETURNS TABLE(event_id bigint, event_timestamp timestamp with time zone, aggregate_version integer, event_type text, event_version integer, event_data jsonb, metadata jsonb, correlation_id text, causation_id bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.event_id,
        e.event_timestamp,
        e.aggregate_version,
        e.event_type,
        e.event_version,
        e.event_data,
        e.metadata,
        e.correlation_id,
        e.causation_id
    FROM execution_events e
    WHERE e.aggregate_type = p_aggregate_type
      AND e.aggregate_id = p_aggregate_id
      AND COALESCE(e.invalidated, FALSE) = FALSE
    ORDER BY e.aggregate_version ASC;
END;
$$;


ALTER FUNCTION public.get_aggregate_events(p_aggregate_type text, p_aggregate_id text) OWNER TO base_admin;

--
-- Name: get_production_actors(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_production_actors(p_conversation_id integer) RETURNS TABLE(actor_id integer, actor_name text, model_variant text, traffic_weight integer)
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.get_production_actors(p_conversation_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION get_production_actors(p_conversation_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.get_production_actors(p_conversation_id integer) IS 'Get all production-ready actors for a conversation, sorted by traffic weight.
Used for canary testing: router selects actor based on traffic_weight percentage.';


--
-- Name: get_script_code(character varying); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_script_code(p_script_name character varying) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_code TEXT;
BEGIN
    SELECT script_code INTO v_code
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    IF v_code IS NULL THEN
        RAISE EXCEPTION 'Script % not found', p_script_name;
    END IF;
    
    RETURN v_code;
END;
$$;


ALTER FUNCTION public.get_script_code(p_script_name character varying) OWNER TO base_admin;

--
-- Name: get_skill_reasoning_history(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_skill_reasoning_history(p_entity_id integer) RETURNS TABLE(model text, role text, reasoning text, confidence numeric, suggested_domain text, was_overturned boolean, overturn_reason text, created_at timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cr.model,
        cr.role,
        cr.reasoning,
        cr.confidence,
        cr.suggested_domain,
        cr.was_overturned,
        cr.overturn_reason,
        cr.created_at
    FROM classification_reasoning cr
    WHERE cr.entity_id = p_entity_id
    ORDER BY cr.created_at;
END;
$$;


ALTER FUNCTION public.get_skill_reasoning_history(p_entity_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION get_skill_reasoning_history(p_entity_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.get_skill_reasoning_history(p_entity_id integer) IS 'Get full reasoning history for a skill for learning context';


--
-- Name: get_slowest_actors(integer, integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_slowest_actors(days integer DEFAULT 7, limit_count integer DEFAULT 10) RETURNS TABLE(actor_name text, actor_type text, avg_latency_ms numeric, p95_latency_ms numeric, total_calls bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.actor_name,
        a.actor_type,
        ROUND(AVG(li.latency_ms)::numeric, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY li.latency_ms)::numeric, 2),
        COUNT(*)
    FROM actors a
    JOIN llm_interactions li ON a.actor_id = li.actor_id
    WHERE li.started_at > NOW() - (days || ' days')::INTERVAL
    GROUP BY a.actor_name, a.actor_type
    ORDER BY AVG(li.latency_ms) DESC
    LIMIT limit_count;
END;
$$;


ALTER FUNCTION public.get_slowest_actors(days integer, limit_count integer) OWNER TO base_admin;

--
-- Name: FUNCTION get_slowest_actors(days integer, limit_count integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.get_slowest_actors(days integer, limit_count integer) IS 'Get slowest actors by average latency. Usage: SELECT * FROM get_slowest_actors(7, 10);';


--
-- Name: get_workflow_contract(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_workflow_contract(p_workflow_id integer) RETURNS TABLE(input_vars jsonb, output_vars jsonb)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jsonb_object_agg(
            CASE WHEN scope = 'input' THEN variable_name END,
            jsonb_build_object(
                'type', data_type,
                'required', is_required,
                'schema', json_schema,
                'description', description
            )
        ) FILTER (WHERE scope = 'input') as input_vars,
        jsonb_object_agg(
            CASE WHEN scope = 'output' THEN variable_name END,
            jsonb_build_object(
                'type', data_type,
                'required', is_required,
                'schema', json_schema,
                'description', description
            )
        ) FILTER (WHERE scope = 'output') as output_vars
    FROM workflow_variables
    WHERE workflow_id = p_workflow_id
    AND is_current = true;
END;
$$;


ALTER FUNCTION public.get_workflow_contract(p_workflow_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION get_workflow_contract(p_workflow_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.get_workflow_contract(p_workflow_id integer) IS 'Returns input and output contracts for a workflow as JSONB';


--
-- Name: get_workflow_errors(integer, integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.get_workflow_errors(run_id integer, limit_count integer DEFAULT 10) RETURNS TABLE(error_id integer, posting_id integer, conversation_name text, actor_name text, error_type text, error_message text, created_at timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        we.error_id,
        we.posting_id,
        c.canonical_name,
        a.actor_name,
        we.error_type,
        we.error_message,
        we.created_at
    FROM workflow_errors we
    LEFT JOIN conversations c ON we.conversation_id = c.conversation_id
    LEFT JOIN actors a ON we.actor_id = a.actor_id
    WHERE we.workflow_run_id = run_id
    ORDER BY we.created_at DESC
    LIMIT limit_count;
END;
$$;


ALTER FUNCTION public.get_workflow_errors(run_id integer, limit_count integer) OWNER TO base_admin;

--
-- Name: FUNCTION get_workflow_errors(run_id integer, limit_count integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.get_workflow_errors(run_id integer, limit_count integer) IS 'Get recent errors for a workflow run. Usage: SELECT * FROM get_workflow_errors(20920, 20);';


--
-- Name: invalidate_sect_decomposition(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.invalidate_sect_decomposition() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- When posting_skills row is deleted, mark the posting as needing re-decomposition
    UPDATE postings 
    SET sect_decomposed_at = NULL,
        updated_at = NOW()
    WHERE posting_id = OLD.posting_id
    AND sect_decomposed_at IS NOT NULL;
    
    RETURN OLD;
END;
$$;


ALTER FUNCTION public.invalidate_sect_decomposition() OWNER TO base_admin;

--
-- Name: FUNCTION invalidate_sect_decomposition(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.invalidate_sect_decomposition() IS 'Clears sect_decomposed_at when posting_skills deleted, ensuring re-processing.';


--
-- Name: load_script_from_disk(text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.load_script_from_disk(script_path text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    script_content TEXT;
    cmd TEXT;
BEGIN
    -- Build command to read file (use Python for cross-platform compatibility)
    cmd := format('python3 -c "import sys; print(open(''%s'').read())"', script_path);
    
    -- Note: This requires PostgreSQL to have permissions to execute Python
    -- Alternative: Use COPY command if file is in allowed directory
    
    -- For now, return NULL and handle in Python layer
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.load_script_from_disk(script_path text) OWNER TO base_admin;

--
-- Name: FUNCTION load_script_from_disk(script_path text); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.load_script_from_disk(script_path text) IS 'Placeholder for loading script code from disk (implemented in Python layer)';


--
-- Name: log_ddl_changes(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.log_ddl_changes() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands()
    LOOP
        -- Only log table/column changes, skip indexes etc
        IF obj.object_type IN ('table', 'table column') THEN
            INSERT INTO schema_changes (change_type, table_name, ddl_command)
            VALUES (
                obj.command_tag,
                obj.object_identity,
                current_query()
            );
        END IF;
    END LOOP;
END;
$$;


ALTER FUNCTION public.log_ddl_changes() OWNER TO base_admin;

--
-- Name: mark_workflow_doc_generated(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.mark_workflow_doc_generated(p_workflow_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE workflow_doc_queue
    SET 
        needs_regeneration = FALSE,
        last_generated_at = CURRENT_TIMESTAMP
    WHERE workflow_id = p_workflow_id;
END;
$$;


ALTER FUNCTION public.mark_workflow_doc_generated(p_workflow_id integer) OWNER TO base_admin;

--
-- Name: match_profile_to_job(integer, integer, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.match_profile_to_job(p_profile_id integer, p_posting_id integer, p_decay_mode text DEFAULT 'reciprocal'::text) RETURNS TABLE(total_score numeric, max_possible_score numeric, match_percentage numeric, matched_skills_count integer, required_skills_count integer, skill_matches jsonb)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_total_score NUMERIC := 0;
    v_max_score NUMERIC := 0;
    v_matched_count INTEGER := 0;
    v_required_count INTEGER;
    v_matches JSONB := '[]'::JSONB;
    v_job_skill RECORD;
    v_candidate_skill RECORD;
    v_best_match RECORD;
BEGIN
    -- Count required skills
    SELECT COUNT(*) INTO v_required_count
    FROM posting_skills
    WHERE posting_id = p_posting_id;
    
    -- For each required skill in job
    FOR v_job_skill IN 
        SELECT ps.skill_id, ps.weight, ps.importance, sa.skill_name
        FROM posting_skills ps
        JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
        WHERE ps.posting_id = p_posting_id
    LOOP
        v_max_score := v_max_score + v_job_skill.weight;
        
        -- Find best matching candidate skill
        SELECT 
            ms.match_score,
            ms.match_type,
            ms.distance,
            ms.explanation,
            sa.skill_name as candidate_skill_name,
            ps.proficiency_level,
            ps.years_experience
        INTO v_best_match
        FROM profile_skills ps
        JOIN skill_aliases sa ON ps.skill_id = sa.skill_id
        CROSS JOIN LATERAL calculate_skill_match_score(
            v_job_skill.skill_id,
            ps.skill_id,
            v_job_skill.weight,
            p_decay_mode
        ) ms
        WHERE ps.profile_id = p_profile_id
        ORDER BY ms.match_score DESC
        LIMIT 1;
        
        IF FOUND AND v_best_match.match_score > 0 THEN
            v_total_score := v_total_score + v_best_match.match_score;
            v_matched_count := v_matched_count + 1;
            
            -- Add to matches array
            v_matches := v_matches || jsonb_build_object(
                'required_skill', v_job_skill.skill_name,
                'candidate_skill', v_best_match.candidate_skill_name,
                'match_score', v_best_match.match_score,
                'max_score', v_job_skill.weight,
                'match_type', v_best_match.match_type,
                'distance', v_best_match.distance,
                'explanation', v_best_match.explanation,
                'importance', v_job_skill.importance,
                'proficiency', v_best_match.proficiency_level,
                'years_experience', v_best_match.years_experience
            );
        ELSE
            -- No match found
            v_matches := v_matches || jsonb_build_object(
                'required_skill', v_job_skill.skill_name,
                'candidate_skill', NULL,
                'match_score', 0,
                'max_score', v_job_skill.weight,
                'match_type', 'missing',
                'importance', v_job_skill.importance
            );
        END IF;
    END LOOP;
    
    RETURN QUERY SELECT 
        v_total_score,
        v_max_score,
        CASE WHEN v_max_score > 0 THEN (v_total_score / v_max_score) * 100 ELSE 0 END,
        v_matched_count,
        v_required_count,
        v_matches;
END;
$$;


ALTER FUNCTION public.match_profile_to_job(p_profile_id integer, p_posting_id integer, p_decay_mode text) OWNER TO base_admin;

--
-- Name: maybe_create_snapshot(integer, integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer DEFAULT 10) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_current_version INT;
    v_last_snapshot_version INT;
    v_snapshot_data JSONB;
BEGIN
    -- Get current version
    SELECT MAX(aggregate_version)
    INTO v_current_version
    FROM execution_events
    WHERE aggregate_type = 'posting'
      AND aggregate_id = p_posting_id::TEXT;
    
    -- Get last snapshot version
    SELECT COALESCE(MAX(aggregate_version), 0)
    INTO v_last_snapshot_version
    FROM posting_state_snapshots
    WHERE posting_id = p_posting_id;
    
    -- Create snapshot if interval reached
    IF (v_current_version - v_last_snapshot_version) >= p_snapshot_interval THEN
        -- Get current state
        SELECT jsonb_build_object(
            'current_step', current_step,
            'current_status', current_status,
            'conversation_history', conversation_history,
            'outputs', outputs,
            'total_tokens', total_tokens,
            'total_duration_ms', total_duration_ms,
            'failure_count', failure_count
        )
        INTO v_snapshot_data
        FROM posting_state_projection
        WHERE posting_id = p_posting_id;
        
        -- Save snapshot
        INSERT INTO posting_state_snapshots (
            posting_id,
            aggregate_version,
            snapshot_data
        ) VALUES (
            p_posting_id,
            v_current_version,
            v_snapshot_data
        )
        ON CONFLICT (posting_id, aggregate_version) DO NOTHING;
    END IF;
END;
$$;


ALTER FUNCTION public.maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer) OWNER TO base_admin;

--
-- Name: FUNCTION maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer) IS 'Create snapshot if interval reached (default every 10 events). Configurable for heavy vs light workflows.';


--
-- Name: migration_applied(character varying); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.migration_applied(p_migration_number character varying) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM migration_log 
        WHERE migration_number = p_migration_number 
        AND status = 'SUCCESS'
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$;


ALTER FUNCTION public.migration_applied(p_migration_number character varying) OWNER TO base_admin;

--
-- Name: normalize_text_python(text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.normalize_text_python(text_input text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
    DECLARE
        ws_chars TEXT;
    BEGIN
        -- Build whitespace character string
        ws_chars := CHR(9) || CHR(10) || CHR(11) || CHR(12) || CHR(13) || CHR(28) || CHR(29) || CHR(30) || CHR(31) || CHR(32) || CHR(133) || CHR(160) || CHR(5760) || CHR(8192) || CHR(8193) || CHR(8194) || CHR(8195) || CHR(8196) || CHR(8197) || CHR(8198) || CHR(8199) || CHR(8200) || CHR(8201) || CHR(8202) || CHR(8232) || CHR(8233) || CHR(8239) || CHR(8287) || CHR(12288);
        -- btrim removes leading/trailing chars, LOWER lowercases
        RETURN LOWER(btrim(text_input, ws_chars));
    END;
    $$;


ALTER FUNCTION public.normalize_text_python(text_input text) OWNER TO base_admin;

--
-- Name: posting_exists(integer, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.posting_exists(p_source_id integer, p_external_job_id text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    existing_id INTEGER;
BEGIN
    SELECT posting_id INTO existing_id
    FROM postings
    WHERE source_id = p_source_id
    AND external_job_id = p_external_job_id;
    
    RETURN existing_id;
END;
$$;


ALTER FUNCTION public.posting_exists(p_source_id integer, p_external_job_id text) OWNER TO base_admin;

--
-- Name: FUNCTION posting_exists(p_source_id integer, p_external_job_id text); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.posting_exists(p_source_id integer, p_external_job_id text) IS 'Check if a posting already exists by source and external ID';


--
-- Name: prevent_owl_names_berufenet_overwrite(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.prevent_owl_names_berufenet_overwrite() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        berufenet_exists BOOLEAN;
    BEGIN
        -- Check if this owl_id is a berufenet profession
        SELECT EXISTS(SELECT 1 FROM berufenet WHERE berufenet_id = NEW.owl_id)
        INTO berufenet_exists;
        
        IF berufenet_exists THEN
            -- Only allow berufenet-aware sources to write to berufenet IDs
            IF NEW.confidence_source NOT IN (
                'import', 'llm_confirmed', 'llm_single', 'human', 
                'posting_city_name', 'repair_geonames_20260227'
            ) THEN
                RAISE EXCEPTION 
                    'owl_names: source "%" cannot write to berufenet ID %. '
                    'Only berufenet-aware sources may modify profession names.',
                    NEW.confidence_source, NEW.owl_id;
            END IF;
        END IF;
        
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION public.prevent_owl_names_berufenet_overwrite() OWNER TO base_admin;

--
-- Name: queue_workflow_docs(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.queue_workflow_docs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.queue_workflow_docs() OWNER TO base_admin;

--
-- Name: FUNCTION queue_workflow_docs(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.queue_workflow_docs() IS 'Queues workflow when workflow_conversations changes (prevents trigger cascade)';


--
-- Name: rebuild_posting_state(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.rebuild_posting_state(p_posting_id integer) RETURNS TABLE(rebuild_time_ms integer, events_replayed integer)
    LANGUAGE plpgsql
    AS $$
DECLARE
    event RECORD;
    event_count INT := 0;
    start_time TIMESTAMPTZ;
    
    -- State variables (built by replaying events)
    v_current_step INT := 1;
    v_current_conversation_id INT := NULL;  -- NEW: Track conversation directly
    v_current_status TEXT := 'pending';
    v_conversation_history JSONB := '[]'::jsonb;
    v_outputs JSONB := '{}'::jsonb;
    v_total_tokens INT := 0;
    v_total_duration_ms INT := 0;
    v_failure_count INT := 0;
    v_last_event_id BIGINT;
BEGIN
    start_time := clock_timestamp();
    
    -- Replay all events for this posting
    FOR event IN 
        SELECT * FROM get_aggregate_events('posting', p_posting_id::TEXT)
    LOOP
        event_count := event_count + 1;
        v_last_event_id := event.event_id;
        
        -- Apply event to state based on event_type
        CASE event.event_type
            
            WHEN 'posting_created' THEN
                v_current_step := (event.event_data->>'step')::INT;
                v_current_status := 'pending';
            
            WHEN 'conversation_started' THEN
                v_current_status := 'in_progress';
            
            WHEN 'script_execution_completed' THEN
                -- Track execution and check if terminal
                v_current_step := COALESCE((event.event_data->>'execution_order')::INT, v_current_step);
                v_current_conversation_id := COALESCE((event.event_data->>'conversation_id')::INT, v_current_conversation_id);
                
                IF (event.event_data->>'is_terminal')::BOOLEAN = TRUE THEN
                    v_current_status := 'TERMINAL';
                ELSE
                    v_current_status := 'in_progress';
                END IF;
            
            WHEN 'llm_call_completed' THEN
                -- Add to conversation history
                v_conversation_history := v_conversation_history || 
                    jsonb_build_object(
                        'conversation_id', event.event_data->>'conversation_id',
                        'prompt', event.event_data->>'prompt',
                        'response', event.event_data->>'response',
                        'timestamp', event.event_timestamp
                    );
                
                -- Track performance
                v_total_tokens := v_total_tokens + 
                    COALESCE((event.event_data->>'tokens')::INT, 0);
                v_total_duration_ms := v_total_duration_ms + 
                    COALESCE((event.event_data->>'duration_ms')::INT, 0);
            
            WHEN 'llm_call_failed' THEN
                v_failure_count := v_failure_count + 1;
                v_current_status := 'failed';
            
            WHEN 'conversation_completed' THEN
                -- Save output
                v_outputs := jsonb_set(
                    v_outputs,
                    ARRAY[(event.event_data->>'conversation_id')],
                    to_jsonb(event.event_data->>'output')
                );
                
                -- Update current conversation (conversation just completed, may branch next)
                v_current_conversation_id := COALESCE((event.event_data->>'conversation_id')::INT, v_current_conversation_id);
            
            WHEN 'posting_branched_to' THEN
                v_current_step := (event.event_data->>'next_step')::INT;
                v_current_status := 'pending';
            
            WHEN 'posting_terminal' THEN
                v_current_status := 'TERMINAL';
            
            WHEN 'posting_failed' THEN
                v_current_status := 'failed';
            
            ELSE
                -- Unknown event type (graceful handling)
                NULL;
        END CASE;
    END LOOP;
    
    -- Upsert projection
    INSERT INTO posting_state_projection (
        posting_id,
        current_step,
        current_conversation_id,
        current_status,
        conversation_history,
        outputs,
        total_tokens,
        total_duration_ms,
        failure_count,
        last_event_id,
        last_updated
    ) VALUES (
        p_posting_id,
        v_current_step,
        v_current_conversation_id,
        v_current_status,
        v_conversation_history,
        v_outputs,
        v_total_tokens,
        v_total_duration_ms,
        v_failure_count,
        v_last_event_id,
        NOW()
    )
    ON CONFLICT (posting_id) DO UPDATE SET
        current_step = EXCLUDED.current_step,
        current_conversation_id = EXCLUDED.current_conversation_id,
        current_status = EXCLUDED.current_status,
        conversation_history = EXCLUDED.conversation_history,
        outputs = EXCLUDED.outputs,
        total_tokens = EXCLUDED.total_tokens,
        total_duration_ms = EXCLUDED.total_duration_ms,
        failure_count = EXCLUDED.failure_count,
        last_event_id = EXCLUDED.last_event_id,
        last_updated = EXCLUDED.last_updated,
        projection_version = posting_state_projection.projection_version + 1;
    
    -- Return performance metrics
    RETURN QUERY SELECT 
        EXTRACT(EPOCH FROM (clock_timestamp() - start_time) * 1000)::INT as rebuild_time_ms,
        event_count;
END;
$$;


ALTER FUNCTION public.rebuild_posting_state(p_posting_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION rebuild_posting_state(p_posting_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.rebuild_posting_state(p_posting_id integer) IS 'Rebuild posting state projection by replaying events. Returns performance metrics.';


--
-- Name: record_migration(character varying, character varying, character varying, integer, text, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.record_migration(p_migration_number character varying, p_migration_name character varying, p_status character varying DEFAULT 'SUCCESS'::character varying, p_duration_ms integer DEFAULT NULL::integer, p_error_message text DEFAULT NULL::text, p_notes text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_migration_id INTEGER;
BEGIN
    INSERT INTO migration_log (
        migration_number,
        migration_name,
        migration_file,
        status,
        duration_ms,
        error_message,
        notes,
        applied_by
    ) VALUES (
        p_migration_number,
        p_migration_name,
        p_migration_number || '_' || regexp_replace(lower(p_migration_name), '[^a-z0-9]+', '_', 'g') || '.sql',
        p_status,
        p_duration_ms,
        p_error_message,
        p_notes,
        current_user
    )
    ON CONFLICT (migration_number) DO UPDATE
    SET 
        status = EXCLUDED.status,
        error_message = EXCLUDED.error_message,
        notes = CASE 
            WHEN migration_log.notes IS NULL THEN EXCLUDED.notes
            ELSE migration_log.notes || E'\n' || EXCLUDED.notes
        END
    RETURNING migration_id INTO v_migration_id;
    
    RETURN v_migration_id;
END;
$$;


ALTER FUNCTION public.record_migration(p_migration_number character varying, p_migration_name character varying, p_status character varying, p_duration_ms integer, p_error_message text, p_notes text) OWNER TO base_admin;

--
-- Name: record_script_execution(character varying, character varying, integer, jsonb, text, jsonb); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.record_script_execution(p_script_name character varying, p_status character varying, p_duration_ms integer DEFAULT NULL::integer, p_return_value jsonb DEFAULT NULL::jsonb, p_error_message text DEFAULT NULL::text, p_execution_context jsonb DEFAULT NULL::jsonb) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_script_id INTEGER;
    v_execution_id INTEGER;
BEGIN
    -- Get script_id
    SELECT script_id INTO v_script_id
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    IF v_script_id IS NULL THEN
        RAISE EXCEPTION 'Script % not found', p_script_name;
    END IF;
    
    -- Insert execution record
    INSERT INTO script_executions (
        script_id,
        status,
        duration_ms,
        return_value,
        error_message,
        execution_context
    ) VALUES (
        v_script_id,
        p_status,
        p_duration_ms,
        p_return_value,
        p_error_message,
        p_execution_context
    )
    RETURNING execution_id INTO v_execution_id;
    
    -- Update script stats
    UPDATE stored_scripts
    SET 
        execution_count = execution_count + 1,
        last_executed_at = CURRENT_TIMESTAMP
    WHERE script_id = v_script_id;
    
    RETURN v_execution_id;
END;
$$;


ALTER FUNCTION public.record_script_execution(p_script_name character varying, p_status character varying, p_duration_ms integer, p_return_value jsonb, p_error_message text, p_execution_context jsonb) OWNER TO base_admin;

--
-- Name: record_trigger_execution(integer, integer, character varying, text, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.record_trigger_execution(p_trigger_id integer, p_workflow_run_id integer DEFAULT NULL::integer, p_status character varying DEFAULT 'TRIGGERED'::character varying, p_trigger_reason text DEFAULT NULL::text, p_condition_value text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_execution_id INTEGER;
BEGIN
    INSERT INTO trigger_executions (
        trigger_id,
        workflow_run_id,
        status,
        trigger_reason,
        trigger_condition_value
    ) VALUES (
        p_trigger_id,
        p_workflow_run_id,
        p_status,
        p_trigger_reason,
        p_condition_value
    )
    RETURNING execution_id INTO v_execution_id;
    
    -- Update trigger statistics
    UPDATE workflow_triggers
    SET 
        last_triggered_at = CURRENT_TIMESTAMP,
        total_runs = total_runs + 1,
        successful_runs = CASE WHEN p_status = 'TRIGGERED' THEN successful_runs + 1 ELSE successful_runs END,
        failed_runs = CASE WHEN p_status = 'FAILED' THEN failed_runs + 1 ELSE failed_runs END,
        next_scheduled_run = CASE 
            WHEN trigger_type = 'SCHEDULE' THEN calculate_next_cron_run(schedule_cron)
            ELSE next_scheduled_run
        END
    WHERE trigger_id = p_trigger_id;
    
    RETURN v_execution_id;
END;
$$;


ALTER FUNCTION public.record_trigger_execution(p_trigger_id integer, p_workflow_run_id integer, p_status character varying, p_trigger_reason text, p_condition_value text) OWNER TO base_admin;

--
-- Name: refresh_actor_performance(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.refresh_actor_performance() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;
    RAISE NOTICE 'Actor performance summary refreshed at %', NOW();
END;
$$;


ALTER FUNCTION public.refresh_actor_performance() OWNER TO base_admin;

--
-- Name: refresh_performance_views(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.refresh_performance_views() RETURNS TABLE(refreshed_at timestamp with time zone, rows_refreshed bigint)
    LANGUAGE plpgsql
    AS $$
DECLARE
    row_count bigint;
BEGIN
    -- Refresh actor performance summary
    REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;
    
    -- Get row count
    SELECT COUNT(*) INTO row_count FROM actor_performance_summary;
    
    -- Return status
    RETURN QUERY SELECT NOW() as refreshed_at, row_count as rows_refreshed;
END;
$$;


ALTER FUNCTION public.refresh_performance_views() OWNER TO base_admin;

--
-- Name: set_workflow_run_environment(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.set_workflow_run_environment() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    SELECT environment INTO NEW.environment
    FROM workflows
    WHERE workflow_id = NEW.workflow_id;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.set_workflow_run_environment() OWNER TO base_admin;

--
-- Name: should_trigger_run(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.should_trigger_run(p_trigger_id integer) RETURNS TABLE(can_run boolean, reason text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_trigger RECORD;
    v_last_run TIMESTAMP;
    v_runs_today INTEGER;
    v_runs_this_hour INTEGER;
    v_active_runs INTEGER;
BEGIN
    -- Get trigger details
    SELECT * INTO v_trigger FROM workflow_triggers WHERE trigger_id = p_trigger_id;
    
    -- Check if enabled
    IF NOT v_trigger.enabled THEN
        RETURN QUERY SELECT false, 'Trigger is disabled';
        RETURN;
    END IF;
    
    -- Check concurrent runs
    SELECT COUNT(*) INTO v_active_runs
    FROM trigger_executions te
    WHERE te.trigger_id = p_trigger_id
    AND te.status = 'TRIGGERED'
    AND te.completed_at IS NULL;
    
    IF v_active_runs >= v_trigger.max_concurrent_runs THEN
        RETURN QUERY SELECT false, 'Max concurrent runs reached: ' || v_active_runs;
        RETURN;
    END IF;
    
    -- Check minimum interval
    IF v_trigger.min_interval_minutes IS NOT NULL THEN
        SELECT MAX(triggered_at) INTO v_last_run
        FROM trigger_executions
        WHERE trigger_id = p_trigger_id
        AND status = 'TRIGGERED';
        
        IF v_last_run IS NOT NULL AND 
           v_last_run > CURRENT_TIMESTAMP - (v_trigger.min_interval_minutes || ' minutes')::INTERVAL THEN
            RETURN QUERY SELECT false, 'Too soon since last run (min interval: ' || v_trigger.min_interval_minutes || ' min)';
            RETURN;
        END IF;
    END IF;
    
    -- Check daily limit
    IF v_trigger.max_runs_per_day IS NOT NULL THEN
        SELECT COUNT(*) INTO v_runs_today
        FROM trigger_executions
        WHERE trigger_id = p_trigger_id
        AND triggered_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        AND status = 'TRIGGERED';
        
        IF v_runs_today >= v_trigger.max_runs_per_day THEN
            RETURN QUERY SELECT false, 'Daily limit reached: ' || v_runs_today || '/' || v_trigger.max_runs_per_day;
            RETURN;
        END IF;
    END IF;
    
    -- All checks passed
    RETURN QUERY SELECT true, 'Ready to run';
END;
$$;


ALTER FUNCTION public.should_trigger_run(p_trigger_id integer) OWNER TO base_admin;

--
-- Name: store_script_version(character varying, text, character varying, text, text); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.store_script_version(p_script_name character varying, p_script_code text, p_version character varying, p_description text DEFAULT NULL::text, p_change_log text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_new_script_id INTEGER;
    v_old_script_id INTEGER;
BEGIN
    -- Get current version if exists
    SELECT script_id INTO v_old_script_id
    FROM stored_scripts
    WHERE script_name = p_script_name
    AND is_current_version = true;
    
    -- Mark old version as not current
    IF v_old_script_id IS NOT NULL THEN
        UPDATE stored_scripts
        SET is_current_version = false
        WHERE script_id = v_old_script_id;
    END IF;
    
    -- Insert new version
    INSERT INTO stored_scripts (
        script_name,
        script_code,
        script_version,
        script_description,
        change_log,
        replaces_script_id,
        is_current_version
    ) VALUES (
        p_script_name,
        p_script_code,
        p_version,
        p_description,
        p_change_log,
        v_old_script_id,
        true
    )
    RETURNING script_id INTO v_new_script_id;
    
    RETURN v_new_script_id;
END;
$$;


ALTER FUNCTION public.store_script_version(p_script_name character varying, p_script_code text, p_version character varying, p_description text, p_change_log text) OWNER TO base_admin;

--
-- Name: tag_conversation(integer, text[]); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.tag_conversation(p_conversation_id integer, p_tags text[]) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO conversation_tags (conversation_id, tag)
    SELECT p_conversation_id, unnest(p_tags)
    ON CONFLICT (conversation_id, tag) DO NOTHING;
END;
$$;


ALTER FUNCTION public.tag_conversation(p_conversation_id integer, p_tags text[]) OWNER TO base_admin;

--
-- Name: FUNCTION tag_conversation(p_conversation_id integer, p_tags text[]); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.tag_conversation(p_conversation_id integer, p_tags text[]) IS 'Helper function to tag a conversation with multiple tags at once. Usage: SELECT tag_conversation(conversation_id, ARRAY[''extract'', ''validate'']);';


--
-- Name: task_types_update_trigger(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.task_types_update_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE actors SET
        -- Previously handled columns
        last_poll_at    = COALESCE(NEW.last_poll_at,    OLD.last_poll_at),
        lint_status     = COALESCE(NEW.lint_status,     OLD.lint_status),
        lint_checked_at = COALESCE(NEW.lint_checked_at, OLD.lint_checked_at),
        lint_errors     = COALESCE(NEW.lint_errors,     OLD.lint_errors),
        poll_priority   = COALESCE(NEW.poll_priority,   OLD.poll_priority),
        scale_limit     = COALESCE(NEW.scale_limit,     OLD.scale_limit),
        requires_model  = COALESCE(NEW.requires_model,  OLD.requires_model),
        execution_type  = COALESCE(NEW.execution_type,  OLD.execution_type),
        -- Previously MISSING columns (silent-fail trap)
        priority        = COALESCE(NEW.priority,        OLD.priority),
        enabled         = COALESCE(NEW.enabled,         OLD.enabled),
        work_query      = COALESCE(NEW.work_query,      OLD.work_query),
        batch_size      = COALESCE(NEW.batch_size,      OLD.batch_size),
        timeout_seconds = COALESCE(NEW.timeout_seconds, OLD.timeout_seconds),
        raq_config      = COALESCE(NEW.raq_config,      OLD.raq_config),
        script_code_hash = COALESCE(NEW.script_code_hash, OLD.script_code_hash),
        subject_type    = COALESCE(NEW.subject_type,    OLD.subject_type)
    WHERE actor_id = OLD.actor_id;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.task_types_update_trigger() OWNER TO base_admin;

--
-- Name: update_batch_counts(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_batch_counts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Only process if batch_id exists and status changed
    IF NEW.batch_id IS NOT NULL AND OLD.status != NEW.status THEN
        -- Update completed count
        IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
            UPDATE batches SET completed_count = completed_count + 1 WHERE batch_id = NEW.batch_id;
        END IF;
        
        -- Update failed count
        IF NEW.status = 'failed' AND OLD.status != 'failed' THEN
            UPDATE batches SET failed_count = failed_count + 1 WHERE batch_id = NEW.batch_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_batch_counts() OWNER TO base_admin;

--
-- Name: update_career_analyses_updated_at(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_career_analyses_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_career_analyses_updated_at() OWNER TO base_admin;

--
-- Name: update_company_avg_rating(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_company_avg_rating() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE companies
    SET avg_rating = (
            SELECT AVG(rating)::DECIMAL(3,2)
            FROM company_ratings
            WHERE company_id = COALESCE(NEW.company_id, OLD.company_id)
        ),
        rating_count = (
            SELECT COUNT(*)
            FROM company_ratings
            WHERE company_id = COALESCE(NEW.company_id, OLD.company_id)
        ),
        updated_at = NOW()
    WHERE company_id = COALESCE(NEW.company_id, OLD.company_id);
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_company_avg_rating() OWNER TO base_admin;

--
-- Name: update_entities_pending_on_workflow_complete(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_entities_pending_on_workflow_complete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_pending_id INTEGER;
BEGIN
    -- Only fire on completion (status changed TO 'completed')
    IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
        -- Only for WF3007 (Skill Cartographer)
        IF NEW.workflow_id = 3007 THEN
            -- Find pending_id from C1 Fetch interaction output
            SELECT (i.output->'data'->>'pending_id')::integer
            INTO v_pending_id
            FROM interactions i
            JOIN conversations c ON i.conversation_id = c.conversation_id
            WHERE i.workflow_run_id = NEW.workflow_run_id
              AND c.canonical_name = 'wf3007_c1_fetch'
              AND i.output->'data'->>'pending_id' IS NOT NULL
            LIMIT 1;
            
            -- Update entities_pending if we found a pending_id
            IF v_pending_id IS NOT NULL THEN
                UPDATE entities_pending 
                SET status = CASE 
                        WHEN status = 'pending' THEN 'approved'
                        ELSE status  -- Don't overwrite if already set
                    END,
                    processed_at = COALESCE(processed_at, NOW())
                WHERE pending_id = v_pending_id;
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_entities_pending_on_workflow_complete() OWNER TO base_admin;

--
-- Name: update_interactions_updated_at(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_interactions_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_interactions_updated_at() OWNER TO base_admin;

--
-- Name: update_posting_seen(integer, boolean); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_posting_seen(p_posting_id integer, p_still_active boolean) RETURNS void
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


ALTER FUNCTION public.update_posting_seen(p_posting_id integer, p_still_active boolean) OWNER TO base_admin;

--
-- Name: FUNCTION update_posting_seen(p_posting_id integer, p_still_active boolean); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.update_posting_seen(p_posting_id integer, p_still_active boolean) IS 'Update posting last_seen_at timestamp and status (schema-aligned Nov 2025)';


--
-- Name: update_profile_search_vector(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_profile_search_vector() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.full_name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.current_title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.profile_summary, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.profile_raw_text, '')), 'C');
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_profile_search_vector() OWNER TO base_admin;

--
-- Name: update_profiles_updated_at(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_profiles_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_profiles_updated_at() OWNER TO base_admin;

--
-- Name: update_source_stats(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_source_stats() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Update job_sources statistics when a fetch completes
    IF NEW.status IN ('SUCCESS', 'PARTIAL_SUCCESS') AND OLD.status = 'RUNNING' THEN
        UPDATE job_sources
        SET 
            last_fetch_at = NEW.fetch_completed_at,
            last_fetch_count = NEW.jobs_fetched,
            total_jobs_fetched = total_jobs_fetched + NEW.jobs_new,
            updated_at = CURRENT_TIMESTAMP
        WHERE source_id = NEW.source_id;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_source_stats() OWNER TO base_admin;

--
-- Name: FUNCTION update_source_stats(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.update_source_stats() IS 'Auto-update job_sources statistics when fetch completes';


--
-- Name: update_staging_updated_at(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_staging_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_staging_updated_at() OWNER TO base_admin;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO base_admin;

--
-- Name: update_workflow_pending_count(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.update_workflow_pending_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.update_workflow_pending_count() OWNER TO base_admin;

--
-- Name: validate_all_workflow_branches(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.validate_all_workflow_branches() RETURNS TABLE(workflow_id integer, workflow_name text, broken_branch_count bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wb.workflow_id,
        wb.workflow_name::TEXT,
        COUNT(*)::BIGINT as broken_branch_count
    FROM workflow_branches wb
    WHERE wb.is_broken = TRUE
    AND wb.conversation_enabled = TRUE  -- Only check enabled conversations
    GROUP BY wb.workflow_id, wb.workflow_name
    ORDER BY broken_branch_count DESC;
END;
$$;


ALTER FUNCTION public.validate_all_workflow_branches() OWNER TO base_admin;

--
-- Name: FUNCTION validate_all_workflow_branches(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.validate_all_workflow_branches() IS 'Check ALL workflows for broken branches. Run at daemon startup.';


--
-- Name: validate_event_store(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.validate_event_store() RETURNS TABLE(posting_id integer, discrepancy_type text, old_value text, new_value text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    
    -- Compare current_step
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'current_step' as discrepancy_type,
        old.current_step::TEXT as old_value,
        new.current_step::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE old.current_step IS DISTINCT FROM new.current_step
    
    UNION ALL
    
    -- Compare outputs
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'outputs' as discrepancy_type,
        old.outputs::TEXT as old_value,
        new.outputs::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE old.outputs IS DISTINCT FROM new.outputs
    
    UNION ALL
    
    -- Compare conversation_history length
    SELECT 
        COALESCE(old.posting_id, new.posting_id) as posting_id,
        'conversation_count' as discrepancy_type,
        (jsonb_array_length(old.conversation_history))::TEXT as old_value,
        (jsonb_array_length(new.conversation_history))::TEXT as new_value
    FROM posting_state_checkpoints old
    FULL OUTER JOIN posting_state_projection new ON old.posting_id = new.posting_id
    WHERE jsonb_array_length(old.conversation_history) != jsonb_array_length(new.conversation_history);
END;
$$;


ALTER FUNCTION public.validate_event_store() OWNER TO base_admin;

--
-- Name: FUNCTION validate_event_store(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.validate_event_store() IS 'Compare old checkpoint schema vs new event store projections. Returns discrepancies.';


--
-- Name: validate_workflow_branches(integer); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.validate_workflow_branches(p_workflow_id integer) RETURNS TABLE(workflow_name text, conversation_name text, branch_name text, branch_condition jsonb, target_conversation_name text, broken_reason text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wb.workflow_name::TEXT,
        wb.conversation_name::TEXT,
        wb.branch_name::TEXT,
        wb.branch_condition,
        wb.target_conversation_name::TEXT,
        wb.broken_reason::TEXT
    FROM workflow_branches wb
    WHERE wb.workflow_id = p_workflow_id
    AND wb.is_broken = TRUE;
END;
$$;


ALTER FUNCTION public.validate_workflow_branches(p_workflow_id integer) OWNER TO base_admin;

--
-- Name: FUNCTION validate_workflow_branches(p_workflow_id integer); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.validate_workflow_branches(p_workflow_id integer) IS 'Check a single workflow for broken branches. Returns empty if all OK.';


--
-- Name: validate_workflow_placeholders(integer, jsonb); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.validate_workflow_placeholders(p_workflow_id integer, p_test_case_data jsonb) RETURNS TABLE(is_valid boolean, missing_required text[], available_optional text[])
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH required_check AS (
        SELECT 
            pd.placeholder_name,
            wp.is_required,
            CASE 
                WHEN pd.source_type = 'test_case_data' THEN p_test_case_data ? pd.placeholder_name
                WHEN pd.source_type IN ('posting', 'profile') THEN true -- Will be fetched
                WHEN pd.source_type = 'dialogue_output' THEN true -- Will be computed
                WHEN pd.source_type = 'static' THEN true
                ELSE false
            END as is_available
        FROM workflow_placeholders wp
        JOIN placeholder_definitions pd ON pd.placeholder_id = wp.placeholder_id
        WHERE wp.workflow_id = p_workflow_id
    )
    SELECT 
        NOT EXISTS (SELECT 1 FROM required_check WHERE is_required AND NOT is_available) as is_valid,
        ARRAY_AGG(placeholder_name ORDER BY placeholder_name) FILTER (WHERE is_required AND NOT is_available) as missing_required,
        ARRAY_AGG(placeholder_name ORDER BY placeholder_name) FILTER (WHERE NOT is_required AND is_available) as available_optional
    FROM required_check;
END;
$$;


ALTER FUNCTION public.validate_workflow_placeholders(p_workflow_id integer, p_test_case_data jsonb) OWNER TO base_admin;

--
-- Name: FUNCTION validate_workflow_placeholders(p_workflow_id integer, p_test_case_data jsonb); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.validate_workflow_placeholders(p_workflow_id integer, p_test_case_data jsonb) IS 'Validates that a workflow has all required placeholders before execution';


--
-- Name: warn_missing_script_code(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.warn_missing_script_code() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.actor_type = 'script' AND NEW.script_code IS NULL THEN
        RAISE WARNING 'Actor % (%) has NULL script_code - code should be in database!', 
            NEW.actor_id, NEW.actor_name;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.warn_missing_script_code() OWNER TO base_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: skill_aliases_final; Type: TABLE; Schema: archive; Owner: base_admin
--

CREATE TABLE archive.skill_aliases_final (
    skill_id integer,
    skill_name text,
    confidence numeric(3,2),
    created_at timestamp without time zone,
    created_by text,
    display_name text,
    language text,
    notes text,
    skill_alias text
);


ALTER TABLE archive.skill_aliases_final OWNER TO base_admin;

--
-- Name: skill_entity_map_final; Type: TABLE; Schema: archive; Owner: base_admin
--

CREATE TABLE archive.skill_entity_map_final (
    skill_id integer,
    entity_id integer,
    skill_name text,
    migrated_at timestamp without time zone
);


ALTER TABLE archive.skill_entity_map_final OWNER TO base_admin;

--
-- Name: skill_hierarchy_final; Type: TABLE; Schema: archive; Owner: base_admin
--

CREATE TABLE archive.skill_hierarchy_final (
    strength numeric(3,2),
    created_at timestamp without time zone,
    created_by text,
    notes text,
    skill_id integer,
    parent_skill_id integer
);


ALTER TABLE archive.skill_hierarchy_final OWNER TO base_admin;

--
-- Name: skill_occurrences_final; Type: TABLE; Schema: archive; Owner: base_admin
--

CREATE TABLE archive.skill_occurrences_final (
    occurrence_id integer,
    skill_source text,
    source_id text,
    skill_alias text,
    confidence numeric(3,2),
    context text,
    extraction_method text,
    created_at timestamp without time zone,
    skill_id integer
);


ALTER TABLE archive.skill_occurrences_final OWNER TO base_admin;

--
-- Name: skills_pending_taxonomy_final; Type: TABLE; Schema: archive; Owner: base_admin
--

CREATE TABLE archive.skills_pending_taxonomy_final (
    pending_skill_id integer,
    raw_skill_name text,
    created_at timestamp without time zone,
    found_in_jobs text[],
    llm_reasoning text,
    notes text,
    occurrences integer,
    review_status text,
    reviewed_at timestamp without time zone,
    reviewed_by text,
    suggested_canonical text,
    suggested_confidence double precision,
    suggested_domain text
);


ALTER TABLE archive.skills_pending_taxonomy_final OWNER TO base_admin;

--
-- Name: _archive_tickets_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public._archive_tickets_history (
    history_id bigint NOT NULL,
    task_log_id bigint NOT NULL,
    posting_id integer,
    task_type_id integer NOT NULL,
    workflow_run_id bigint,
    actor_id integer NOT NULL,
    actor_type text NOT NULL,
    status text NOT NULL,
    execution_order integer NOT NULL,
    parent_task_log_id bigint,
    trigger_task_log_id bigint,
    input_task_log_ids bigint[],
    input jsonb,
    output jsonb,
    error_message text,
    retry_count integer,
    max_retries integer,
    enabled boolean,
    invalidated boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    archived_at timestamp with time zone DEFAULT now() NOT NULL,
    archived_by text DEFAULT CURRENT_USER,
    archive_reason text
);


ALTER TABLE public._archive_tickets_history OWNER TO base_admin;

--
-- Name: TABLE _archive_tickets_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public._archive_tickets_history IS 'Archive of deleted interactions - preserves audit trail even when source data is removed';


--
-- Name: actors_actor_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.actors_actor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.actors_actor_id_seq OWNER TO base_admin;

--
-- Name: actors; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.actors (
    actor_id integer DEFAULT nextval('public.actors_actor_id_seq'::regclass) NOT NULL,
    actor_name text NOT NULL,
    actor_type text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    enabled boolean DEFAULT true,
    execution_config jsonb DEFAULT '{}'::jsonb,
    execution_path text,
    execution_type text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    url text,
    user_id integer,
    script_code text,
    script_language text,
    script_version integer DEFAULT 1,
    input_format text,
    output_format text,
    example_call text,
    error_handling text,
    parent_actor_id integer,
    qualified boolean DEFAULT false,
    script_code_hash text,
    script_file_path text,
    script_file_mtime timestamp with time zone,
    script_synced_at timestamp with time zone,
    script_sync_status text DEFAULT 'synced'::text,
    active_history_id bigint,
    auto_promote boolean DEFAULT false,
    is_production boolean DEFAULT true,
    model_variant text,
    traffic_weight integer DEFAULT 100,
    last_performance_check timestamp without time zone,
    script_flowchart text,
    canonical_name text,
    work_query text,
    timeout_seconds integer DEFAULT 300,
    batch_size integer DEFAULT 10,
    priority integer DEFAULT 0,
    poll_priority integer DEFAULT 0,
    pull_enabled boolean DEFAULT false,
    scale_limit integer,
    triggers_when text,
    raq_config jsonb,
    raq_status text,
    qa_spec text,
    qa_report text,
    max_instruction_runs integer,
    context_strategy text,
    subject_type text,
    task_type_category text,
    requires_model text,
    last_poll_at timestamp with time zone,
    lint_status text,
    lint_checked_at timestamp with time zone,
    lint_errors jsonb,
    CONSTRAINT actors_actor_type_check CHECK ((actor_type = ANY (ARRAY['ai_model'::text, 'machine_actor'::text, 'script'::text, 'human'::text, 'thick'::text]))),
    CONSTRAINT actors_script_sync_status_check CHECK ((script_sync_status = ANY (ARRAY['synced'::text, 'drift_detected'::text, 'file_missing'::text, 'sync_failed'::text])))
);


ALTER TABLE public.actors OWNER TO base_admin;

--
-- Name: TABLE actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.actors IS 'Computational units in the Turing execution engine (execution layer).
Actors are the "processors" that execute instructions in workflows - can be AI models, scripts, or humans.
Key to Turing completeness: heterogeneous computation mixing neural (AI), symbolic (scripts), and human judgment.

Actor Types:
- human (execution_type=human_input): Human actors who execute workflow steps
- ai_model (execution_type=ollama_api): AI/LLM models that process data
- script (execution_type=python_script/bash_script): Automated scripts
- machine_actor (execution_type=http_api): External API services

Script Execution (NEW - Migration 030):
- script_code: Source code stored in database (source of truth for production)
- script_language: python, bash, javascript, etc.
- script_version: Incremented on each update for audit trail
- execution_path: DEPRECATED - fallback for development only
- Runner priority: script_code → execution_path → ERROR

Actor vs User Distinction:
- actors table = EXECUTION LAYER: "Who executes this workflow step?"
- users table = APPLICATION LAYER: "Who owns this profile/job search?"
- Some actors ARE users (user_id FK): Job seekers responding to reports, providing feedback
- Not all actors are users: AI models and scripts will never authenticate
- Not all users are actors: Some platform users may never participate in workflow execution

Example: Job seeker Jane (user_id=42) receives a cover letter. When she replies, she acts as 
an actor (actor_id=123, user_id=42). The AI model that generated the cover letter (actor_id=5) 
has no user_id because it''s not an authenticated platform user.

Column order standardized 2025-10-31 (migration 015).
Pattern: actor_id (INTEGER PK) + actor_name (TEXT UNIQUE).
User linking added 2025-10-31 (migration 023).
Script code storage added 2025-10-31 (migration 030).';


--
-- Name: COLUMN actors.actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: COLUMN actors.actor_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_name IS 'Natural key - unique actor name (e.g., qwen2.5:7b, taxonomy_gopher)';


--
-- Name: COLUMN actors.actor_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_type IS 'Type of actor: human (human operator), ai_model (LLM), script (automated validator)';


--
-- Name: COLUMN actors.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.created_at IS 'Timestamp when this actor was registered in the system';


--
-- Name: COLUMN actors.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.enabled IS 'Whether this actor is currently available for execution. 
   If false, recipes using this actor will fail gracefully.';


--
-- Name: COLUMN actors.execution_config; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.execution_config IS 'JSONB config for actor execution. Common fields:
- mode: "stdin_json" | "args" | "env_vars"
- output_format: "json" | "text" | "yaml"
- rate_limit_hours: integer (min hours between runs, optional)
- last_run_at: ISO timestamp of last successful run (managed by actor_router)
- run_count: integer (total successful runs, managed by actor_router)
- args: array of command-line arguments (for script actors)
- timeout: integer seconds (default 300)
- retry_on_failure: boolean (default false)
- max_retries: integer (default 0)';


--
-- Name: COLUMN actors.execution_path; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.execution_path IS 'DEPRECATED: Use script_file_path instead. Kept for backward compatibility. - Arden 2025-12-08';


--
-- Name: COLUMN actors.execution_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.execution_type IS 'HOW to execute this actor:
   - ollama_api: LLM via Ollama HTTP API
   - http_api: Microservice with REST API
   - python_script: Local Python script (called via subprocess)
   - bash_script: Shell script
   - human_input: Queue task for human review';


--
-- Name: COLUMN actors.updated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.updated_at IS 'Timestamp when this actor configuration was last modified';


--
-- Name: COLUMN actors.url; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.url IS 'DEPRECATED: Legacy URL/path field. Use script_code for scripts, execution_config for API endpoints.';


--
-- Name: COLUMN actors.user_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.user_id IS 'Foreign key to users table. Links this actor to a platform user account. NULL for non-human actors (AI models, scripts) and human actors not yet linked to user accounts. When a user participates in workflow execution (e.g., responding to job search reports), their actor record references their user account.';


--
-- Name: COLUMN actors.script_code; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_code IS 'Source code for script actors (Python, Bash, etc.). When present, this is the authoritative code to execute. Prevents workflow breakage from deleted/renamed script files. NULL for AI/human actors.';


--
-- Name: COLUMN actors.script_language; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_language IS 'Programming language for script_code: python, bash, javascript, etc. NULL for AI/human actors.';


--
-- Name: COLUMN actors.script_version; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_version IS 'Version number of script_code. Incremented each time script is updated. Enables tracking which version ran in historical executions.';


--
-- Name: COLUMN actors.input_format; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.input_format IS 'Expected input format: json_array, json_object, text, etc.';


--
-- Name: COLUMN actors.output_format; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.output_format IS 'Output format: json_array, json_object, text, etc.';


--
-- Name: COLUMN actors.example_call; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.example_call IS 'Example input for this actor (quick reference)';


--
-- Name: COLUMN actors.error_handling; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.error_handling IS 'How this actor handles errors (returns error in JSON, raises exception, etc.)';


--
-- Name: COLUMN actors.parent_actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.parent_actor_id IS 'Parent actor in hierarchy (NULL for root actors)';


--
-- Name: COLUMN actors.qualified; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.qualified IS 'Can this actor start workflows? (workflows 1-4 qualified flag)';


--
-- Name: COLUMN actors.script_code_hash; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_code_hash IS 'SHA256 hash of script_code for drift detection';


--
-- Name: COLUMN actors.script_file_path; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_file_path IS 'Canonical filesystem path to script';


--
-- Name: COLUMN actors.script_sync_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.script_sync_status IS 'Drift detection status (synced/drift_detected/file_missing)';


--
-- Name: COLUMN actors.active_history_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.active_history_id IS 'Foreign key to actor_code_history (current active version)';


--
-- Name: COLUMN actors.auto_promote; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.auto_promote IS 'Auto-promote staging records to production (for validators)';


--
-- Name: COLUMN actors.is_production; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.is_production IS 'TRUE if this actor serves production traffic. FALSE for experimental/challenger models.
Use for filtering production-ready actors in conversation routing.';


--
-- Name: COLUMN actors.model_variant; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.model_variant IS 'Role in A/B testing: "champion" (current best), "challenger_a", "challenger_b", etc.
Only one champion per conversation. Challengers compete to replace champion.';


--
-- Name: COLUMN actors.traffic_weight; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.traffic_weight IS 'Percentage of traffic (0-100) for canary testing. 
Example: champion=95, challenger=5 means 5% of requests go to challenger.
SUM of weights for same conversation should = 100.';


--
-- Name: COLUMN actors.last_performance_check; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.last_performance_check IS 'Last time automatic champion selection workflow evaluated this actor.
Updated weekly by workflow 3XXX.';


--
-- Name: adele_sessions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.adele_sessions (
    session_id integer NOT NULL,
    user_id integer NOT NULL,
    phase character varying(30) DEFAULT 'intro'::character varying NOT NULL,
    collected jsonb DEFAULT '{}'::jsonb NOT NULL,
    work_history_count integer DEFAULT 0,
    turn_count integer DEFAULT 0,
    started_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone
);


ALTER TABLE public.adele_sessions OWNER TO base_admin;

--
-- Name: TABLE adele_sessions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.adele_sessions IS 'Tracks Adele''s conversational profile building sessions.
Each yogi has at most one active session. As Adele asks questions,
collected data accumulates in the JSONB column until the profile
is confirmed and saved.';


--
-- Name: adele_sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.adele_sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.adele_sessions_session_id_seq OWNER TO base_admin;

--
-- Name: adele_sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.adele_sessions_session_id_seq OWNED BY public.adele_sessions.session_id;


--
-- Name: arcade_scores; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.arcade_scores (
    id integer NOT NULL,
    user_id integer,
    score integer NOT NULL,
    level integer DEFAULT 1 NOT NULL,
    monsters_killed integer DEFAULT 0 NOT NULL,
    fruits_collected integer DEFAULT 0 NOT NULL,
    friendly_fire integer DEFAULT 0 NOT NULL,
    duration_seconds integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.arcade_scores OWNER TO base_admin;

--
-- Name: arcade_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.arcade_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.arcade_scores_id_seq OWNER TO base_admin;

--
-- Name: arcade_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.arcade_scores_id_seq OWNED BY public.arcade_scores.id;


--
-- Name: attribute_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.attribute_history (
    history_id integer NOT NULL,
    table_name text NOT NULL,
    record_id bigint NOT NULL,
    attribute_name text NOT NULL,
    old_value jsonb,
    nulled_at timestamp without time zone DEFAULT now(),
    reason text
);


ALTER TABLE public.attribute_history OWNER TO base_admin;

--
-- Name: attribute_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.attribute_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.attribute_history_history_id_seq OWNER TO base_admin;

--
-- Name: attribute_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.attribute_history_history_id_seq OWNED BY public.attribute_history.history_id;


--
-- Name: batches; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.batches (
    batch_id bigint NOT NULL,
    task_type_id integer NOT NULL,
    reason character varying(100),
    status character varying(20) DEFAULT 'running'::character varying NOT NULL,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    item_count integer DEFAULT 0,
    completed_count integer DEFAULT 0,
    failed_count integer DEFAULT 0,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_by text,
    CONSTRAINT batches_status_check CHECK (((status)::text = ANY (ARRAY[('running'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('stopped'::character varying)::text])))
);


ALTER TABLE public.batches OWNER TO base_admin;

--
-- Name: TABLE batches; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.batches IS 'Groups interactions for RAQ comparison. Replaces workflow_runs.';


--
-- Name: batches_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.batches_batch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.batches_batch_id_seq OWNER TO base_admin;

--
-- Name: batches_batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.batches_batch_id_seq OWNED BY public.batches.batch_id;


--
-- Name: berufenet; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.berufenet (
    berufenet_id integer NOT NULL,
    name text NOT NULL,
    kldb text,
    qualification_level integer,
    created_at timestamp with time zone DEFAULT now(),
    salary_median integer,
    salary_q25 integer,
    salary_q75 integer,
    salary_sample_size integer,
    salary_updated_at timestamp without time zone
);


ALTER TABLE public.berufenet OWNER TO base_admin;

--
-- Name: TABLE berufenet; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.berufenet IS 'Official German profession definitions from berufe.net';


--
-- Name: COLUMN berufenet.kldb; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.berufenet.kldb IS 'KLDB 2010 classification code';


--
-- Name: COLUMN berufenet.qualification_level; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.berufenet.qualification_level IS '1=Helfer, 2=Fachkraft, 3=Spezialist, 4=Experte';


--
-- Name: berufenet_synonyms; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.berufenet_synonyms (
    aa_beruf text NOT NULL,
    berufenet_id integer,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    source text DEFAULT 'manual'::text
);


ALTER TABLE public.berufenet_synonyms OWNER TO base_admin;

--
-- Name: TABLE berufenet_synonyms; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.berufenet_synonyms IS 'Maps AA beruf field to berufenet when exact match fails';


--
-- Name: capabilities_capability_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.capabilities_capability_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.capabilities_capability_id_seq OWNER TO base_admin;

--
-- Name: city_country_map; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.city_country_map (
    city_id bigint NOT NULL,
    city text,
    city_ascii text,
    country text,
    iso2 text,
    iso3 text,
    population bigint
);


ALTER TABLE public.city_country_map OWNER TO base_admin;

--
-- Name: city_snapshot; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.city_snapshot (
    city_id integer NOT NULL,
    location_state text NOT NULL,
    location_city text NOT NULL,
    domain_code text,
    total_postings integer DEFAULT 0 NOT NULL,
    fresh_14d integer DEFAULT 0 NOT NULL,
    fresh_7d integer DEFAULT 0 NOT NULL,
    avg_lat numeric(9,6),
    avg_lon numeric(9,6),
    computed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.city_snapshot OWNER TO base_admin;

--
-- Name: TABLE city_snapshot; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.city_snapshot IS 'City-level posting aggregates for the search hierarchy panel. Refreshed nightly by compute_city_snapshot.py.';


--
-- Name: city_snapshot_city_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.city_snapshot_city_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.city_snapshot_city_id_seq OWNER TO base_admin;

--
-- Name: city_snapshot_city_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.city_snapshot_city_id_seq OWNED BY public.city_snapshot.city_id;


--
-- Name: company_alias_variants; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.company_alias_variants (
    variant_id integer NOT NULL,
    alias_id integer NOT NULL,
    variant text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.company_alias_variants OWNER TO base_admin;

--
-- Name: TABLE company_alias_variants; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.company_alias_variants IS 'Alternate spellings and abbreviations that map to the same company_aliases row.
E.g. "db" → "deutsche bank", "dbk" → "deutsche bank", "roche" → "f. hoffmann-la roche"';


--
-- Name: company_alias_variants_variant_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.company_alias_variants_variant_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.company_alias_variants_variant_id_seq OWNER TO base_admin;

--
-- Name: company_alias_variants_variant_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.company_alias_variants_variant_id_seq OWNED BY public.company_alias_variants.variant_id;


--
-- Name: company_aliases; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.company_aliases (
    alias_id integer NOT NULL,
    company_pattern text NOT NULL,
    anonymized_en text NOT NULL,
    anonymized_de text NOT NULL,
    industry text,
    size_hint text,
    country text,
    verified boolean DEFAULT false,
    verified_at timestamp with time zone,
    source text DEFAULT 'llm_inline'::text,
    research_notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.company_aliases OWNER TO base_admin;

--
-- Name: TABLE company_aliases; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.company_aliases IS 'Canonical anonymized company descriptions for CV anonymization.
Each real company name maps to one EN + one DE description.
Descriptions must satisfy the ≥3-companies rule: at least 3 real companies
could plausibly match the description. Verified by privacy auditor actor.';


--
-- Name: COLUMN company_aliases.company_pattern; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.company_aliases.company_pattern IS 'Lowercase canonical company name. Variations (e.g. "DB", "Deutsche Bank AG",
"Deutsche Bank Group") should all map to the same row. Use additional patterns
in company_alias_variants for alternate spellings.';


--
-- Name: company_aliases_alias_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.company_aliases_alias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.company_aliases_alias_id_seq OWNER TO base_admin;

--
-- Name: company_aliases_alias_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.company_aliases_alias_id_seq OWNED BY public.company_aliases.alias_id;


--
-- Name: demand_snapshot; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.demand_snapshot (
    snapshot_id integer NOT NULL,
    location_state text NOT NULL,
    domain_code text NOT NULL,
    berufenet_id integer,
    berufenet_name text,
    total_postings integer DEFAULT 0 NOT NULL,
    fresh_14d integer DEFAULT 0 NOT NULL,
    fresh_7d integer DEFAULT 0 NOT NULL,
    national_avg numeric(10,4),
    demand_ratio numeric(10,4),
    computed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.demand_snapshot OWNER TO base_admin;

--
-- Name: demand_snapshot_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.demand_snapshot_snapshot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.demand_snapshot_snapshot_id_seq OWNER TO base_admin;

--
-- Name: demand_snapshot_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.demand_snapshot_snapshot_id_seq OWNED BY public.demand_snapshot.snapshot_id;


--
-- Name: embeddings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.embeddings (
    text_hash text NOT NULL,
    text text NOT NULL,
    embedding jsonb,
    model text DEFAULT 'bge-m3:567m'::text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.embeddings OWNER TO base_admin;

--
-- Name: owl_names; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.owl_names (
    owl_id integer NOT NULL,
    language text DEFAULT 'en'::text NOT NULL,
    display_name text NOT NULL,
    is_primary boolean DEFAULT false,
    confidence numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    name_type text DEFAULT 'display'::text,
    valid_from date,
    valid_to date,
    provenance jsonb,
    observation_count integer DEFAULT 1,
    confidence_source text DEFAULT 'import'::text,
    CONSTRAINT entity_names_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT entity_names_name_type_check CHECK ((name_type = ANY (ARRAY['canonical'::text, 'display'::text, 'alias'::text, 'translation'::text, 'abbreviation'::text, 'former_name'::text, 'ticker'::text, 'verbatim'::text, 'llm_suggested'::text, 'observed'::text])))
);


ALTER TABLE public.owl_names OWNER TO base_admin;

--
-- Name: TABLE owl_names; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.owl_names IS 'How entities are displayed to humans, by language';


--
-- Name: COLUMN owl_names.is_primary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_names.is_primary IS 'If true, this is THE name to show for this entity in this language';


--
-- Name: COLUMN owl_names.confidence; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_names.confidence IS 'Translation confidence: 1.0 = verified, 0.8 = LLM suggested, etc.';


--
-- Name: COLUMN owl_names.confidence_source; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_names.confidence_source IS 'How this name was validated: human | import | llm_confirmed | llm_single. Phase 1 OWL lookup only trusts human, import, and llm_confirmed.';


--
-- Name: entity_aliases_v; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.entity_aliases_v AS
 SELECT owl_names.owl_id AS entity_id,
    owl_names.display_name AS alias,
    owl_names.language,
    owl_names.name_type AS alias_type,
    owl_names.confidence,
    owl_names.created_by,
    owl_names.provenance,
    owl_names.created_at
   FROM public.owl_names
  WHERE (owl_names.name_type = ANY (ARRAY['alias'::text, 'verbatim'::text, 'llm_suggested'::text, 'abbreviation'::text]));


ALTER TABLE public.entity_aliases_v OWNER TO base_admin;

--
-- Name: owl; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.owl (
    owl_id integer NOT NULL,
    owl_type text NOT NULL,
    canonical_name text NOT NULL,
    status text DEFAULT 'active'::text,
    merged_into_entity_id integer,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    metadata jsonb,
    description text,
    hub_score_updated_at timestamp without time zone,
    CONSTRAINT entities_check CHECK (((status <> 'merged'::text) OR (merged_into_entity_id IS NOT NULL))),
    CONSTRAINT entities_status_check CHECK ((status = ANY (ARRAY['active'::text, 'deprecated'::text, 'merged'::text, 'pending_review'::text])))
);


ALTER TABLE public.owl OWNER TO base_admin;

--
-- Name: TABLE owl; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.owl IS 'Universal registry of things that exist - competencies, certifications, track records, places, concepts.

owl_type values:
- competency: Learnable capability (Python, SQL, Leadership)
- competency_atomic: Atomic competency after decomposition  
- competency_group: Folder/grouping in hierarchy
- competency_root: Root of taxonomy tree
- certification: Formal credential (AWS, PMP, CPA, degrees)
- track_record: Demonstrated outcome (Team Leadership, Project Delivery)
- city, state, country, continent: Geographic hierarchy
- copilot_memory: AI session context storage';


--
-- Name: COLUMN owl.canonical_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl.canonical_name IS 'The One True Name - never displayed, only referenced internally';


--
-- Name: COLUMN owl.status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl.status IS 'Lifecycle: active (normal), deprecated (historical), merged (redirects to merged_into)';


--
-- Name: COLUMN owl.metadata; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl.metadata IS 'Type-specific data: {"iso_code": "DE"} for countries, {"coordinates": [lat, lon]} for cities';


--
-- Name: entity_display_names; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.entity_display_names AS
 SELECT e.owl_id AS entity_id,
    e.canonical_name,
    e.owl_type AS entity_type,
    COALESCE(( SELECT owl_names.display_name
           FROM public.owl_names
          WHERE ((owl_names.owl_id = e.owl_id) AND (owl_names.name_type = 'display'::text) AND (owl_names.created_by = 'capitalization_fix'::text))
         LIMIT 1), ( SELECT owl_names.display_name
           FROM public.owl_names
          WHERE ((owl_names.owl_id = e.owl_id) AND (owl_names.name_type = 'observed'::text))
          ORDER BY owl_names.observation_count DESC
         LIMIT 1), initcap(replace(e.canonical_name, '_'::text, ' '::text))) AS display_name
   FROM public.owl e;


ALTER TABLE public.entity_display_names OWNER TO base_admin;

--
-- Name: feedback; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.feedback (
    feedback_id integer NOT NULL,
    user_id integer,
    url text NOT NULL,
    description text NOT NULL,
    category text DEFAULT 'bug'::text NOT NULL,
    screenshot text,
    annotation jsonb,
    viewport jsonb,
    user_agent text,
    status text DEFAULT 'open'::text NOT NULL,
    admin_notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone
);


ALTER TABLE public.feedback OWNER TO base_admin;

--
-- Name: feedback_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.feedback_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.feedback_feedback_id_seq OWNER TO base_admin;

--
-- Name: feedback_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.feedback_feedback_id_seq OWNED BY public.feedback.feedback_id;


--
-- Name: founder_debt; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.founder_debt (
    contributor text NOT NULL,
    initial_investment_cents bigint NOT NULL,
    repaid_cents bigint DEFAULT 0 NOT NULL,
    hours_worked integer NOT NULL,
    hourly_rate_cents integer NOT NULL
);


ALTER TABLE public.founder_debt OWNER TO base_admin;

--
-- Name: instructions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instructions (
    instruction_id integer NOT NULL,
    instruction_name text NOT NULL,
    task_type_id integer NOT NULL,
    step_number integer NOT NULL,
    step_description text,
    input_template text NOT NULL,
    timeout_seconds integer DEFAULT 300,
    expected_pattern text,
    validation_rules text,
    is_terminal boolean DEFAULT false,
    delegate_actor_id integer,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    staleness_days integer
);


ALTER TABLE public.instructions OWNER TO base_admin;

--
-- Name: TABLE instructions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instructions IS 'Lily CPS instruction added 2026-01-08. Old SECT instructions (3564, 3565, 3574, 3575, 3577) disabled.';


--
-- Name: COLUMN instructions.instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.instruction_id IS 'Primary key - unique identifier for this instruction';


--
-- Name: COLUMN instructions.instruction_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.instruction_name IS 'Human-readable name for this instruction (e.g., "Generate joke", "Evaluate quality")';


--
-- Name: COLUMN instructions.task_type_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.task_type_id IS 'FK to conversations - which conversation this instruction belongs to';


--
-- Name: COLUMN instructions.step_number; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.step_number IS 'Sequential step number within the conversation (1, 2, 3, ...)';


--
-- Name: COLUMN instructions.step_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.step_description IS 'Detailed description of what this instruction does';


--
-- Name: COLUMN instructions.input_template; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.input_template IS 'The prompt template to send to the actor (can include {variables})';


--
-- Name: COLUMN instructions.timeout_seconds; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.timeout_seconds IS 'Maximum time allowed for this instruction to execute (default 300)';


--
-- Name: COLUMN instructions.expected_pattern; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.expected_pattern IS 'Optional regex pattern for validating the response';


--
-- Name: COLUMN instructions.validation_rules; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.validation_rules IS 'Optional validation rules or logic to apply to the response';


--
-- Name: COLUMN instructions.is_terminal; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.is_terminal IS 'If true, this instruction marks a completion point (no automatic continuation)';


--
-- Name: COLUMN instructions.delegate_actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.delegate_actor_id IS 'Optional FK to actors - if set, delegate this instruction to a different actor (helper/script)';


--
-- Name: COLUMN instructions.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.enabled IS 'If false, this instruction is skipped during execution (soft delete)';


--
-- Name: COLUMN instructions.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.created_at IS 'Timestamp when this instruction was first created';


--
-- Name: COLUMN instructions.updated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.updated_at IS 'Timestamp when this instruction was last modified';


--
-- Name: COLUMN instructions.staleness_days; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.staleness_days IS 'How many days before this instruction should re-run. NULL = never re-run if completed. 
E.g., staleness_days=7 means re-run if last interaction was >7 days ago.
For fetcher URL checks, use 7. For summary extraction, use NULL (one-time).';


--
-- Name: interactions_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.interactions_history_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.interactions_history_history_id_seq OWNER TO base_admin;

--
-- Name: interactions_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.interactions_history_history_id_seq OWNED BY public._archive_tickets_history.history_id;


--
-- Name: ledger_monthly; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.ledger_monthly (
    month date NOT NULL,
    active_users integer DEFAULT 0 NOT NULL,
    revenue_cents integer DEFAULT 0 NOT NULL,
    operating_costs_cents integer DEFAULT 0 NOT NULL,
    reserve_contribution_cents integer DEFAULT 0 NOT NULL,
    founder_repayment_cents integer DEFAULT 0 NOT NULL,
    development_fund_cents integer DEFAULT 0 NOT NULL,
    founder_debt_remaining_cents bigint NOT NULL,
    notes text
);


ALTER TABLE public.ledger_monthly OWNER TO base_admin;

--
-- Name: mira_faq_candidates; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.mira_faq_candidates (
    id integer NOT NULL,
    user_id integer,
    session_id character varying(64),
    user_message text NOT NULL,
    mira_response text NOT NULL,
    faq_score double precision,
    faq_matched_id character varying(64),
    flagged_reason character varying(32) NOT NULL,
    user_feedback character varying(16),
    reviewed_at timestamp without time zone,
    reviewed_by integer,
    review_decision character varying(16),
    review_notes text,
    promoted_at timestamp without time zone,
    promoted_faq_id character varying(64),
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_flagged_reason CHECK (((flagged_reason)::text = ANY ((ARRAY['low_match'::character varying, 'positive_feedback'::character varying, 'novel_topic'::character varying, 'explicit_flag'::character varying])::text[]))),
    CONSTRAINT valid_review_decision CHECK (((review_decision IS NULL) OR ((review_decision)::text = ANY ((ARRAY['promote'::character varying, 'reject'::character varying, 'defer'::character varying])::text[]))))
);


ALTER TABLE public.mira_faq_candidates OWNER TO base_admin;

--
-- Name: TABLE mira_faq_candidates; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.mira_faq_candidates IS 'Staging table for Mira exchanges that might become FAQ entries';


--
-- Name: COLUMN mira_faq_candidates.faq_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.mira_faq_candidates.faq_score IS 'Best cosine similarity score from BGE-M3 embedding match';


--
-- Name: COLUMN mira_faq_candidates.flagged_reason; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.mira_faq_candidates.flagged_reason IS 'Why this exchange was flagged: low_match (FAQ score < 0.60), positive_feedback (user said thanks/helpful), novel_topic (new category detected), explicit_flag (admin flagged)';


--
-- Name: mira_faq_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.mira_faq_candidates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.mira_faq_candidates_id_seq OWNER TO base_admin;

--
-- Name: mira_faq_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.mira_faq_candidates_id_seq OWNED BY public.mira_faq_candidates.id;


--
-- Name: mira_questions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.mira_questions (
    question_id integer NOT NULL,
    user_id integer,
    question text NOT NULL,
    context jsonb,
    asked_at timestamp with time zone DEFAULT now(),
    answered_at timestamp with time zone,
    answer text,
    answered_by text,
    notification_sent_at timestamp with time zone,
    closed_at timestamp with time zone,
    closed_reason text
);


ALTER TABLE public.mira_questions OWNER TO base_admin;

--
-- Name: TABLE mira_questions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.mira_questions IS 'Queue for questions Mira cannot answer immediately';


--
-- Name: mira_questions_question_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.mira_questions_question_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.mira_questions_question_id_seq OWNER TO base_admin;

--
-- Name: mira_questions_question_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.mira_questions_question_id_seq OWNED BY public.mira_questions.question_id;


--
-- Name: owl_relationships; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.owl_relationships (
    owl_id integer NOT NULL,
    related_owl_id integer NOT NULL,
    relationship text NOT NULL,
    strength numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    provenance jsonb,
    is_primary boolean DEFAULT false,
    forward_strength real,
    reverse_strength real,
    CONSTRAINT entity_relationships_check CHECK ((owl_id <> related_owl_id)),
    CONSTRAINT entity_relationships_strength_check CHECK (((strength >= (0)::numeric) AND (strength <= (1)::numeric)))
);


ALTER TABLE public.owl_relationships OWNER TO base_admin;

--
-- Name: TABLE owl_relationships; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.owl_relationships IS 'Hierarchical relationships between owl entities.

RELATIONSHIP TYPES IN USE:
  belongs_to - Hierarchical: Python belongs_to Programming
  is_a       - Taxonomic: Python is_a Programming_Language

FUTURE RELATIONSHIP TYPES (documented but not yet used):
  located_in  - Geographic: Munich located_in Germany
  part_of     - Compositional: Engine part_of Car
  instance_of - Specific: "Berlin_March_2025" instance_of Climate_Protest
  same_as     - Identity: München same_as Munich (for merging)
  related_to  - Loose association: Python related_to Data_Science
  requires    - Dependency: Kubernetes requires Docker
  succeeds    - Temporal: Python3 succeeds Python2';


--
-- Name: COLUMN owl_relationships.relationship; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_relationships.relationship IS 'is_a (taxonomy), located_in (geography), part_of (composition), same_as (identity), related_to (loose)';


--
-- Name: mv_skill_2hop; Type: MATERIALIZED VIEW; Schema: public; Owner: base_admin
--

CREATE MATERIALIZED VIEW public.mv_skill_2hop AS
 WITH direct AS (
         SELECT owl_relationships.owl_id AS source_id,
            owl_relationships.related_owl_id AS target_id,
            owl_relationships.strength,
            1 AS hops
           FROM public.owl_relationships
          WHERE (owl_relationships.relationship = 'requires'::text)
        ), two_hop AS (
         SELECT d1.source_id,
            d2.target_id,
            (d1.strength * d2.strength) AS strength,
            2 AS hops
           FROM (direct d1
             JOIN direct d2 ON ((d1.target_id = d2.source_id)))
          WHERE (d1.source_id <> d2.target_id)
        )
 SELECT combined.source_id,
    combined.target_id,
    max(combined.strength) AS strength,
    min(combined.hops) AS min_hops
   FROM ( SELECT direct.source_id,
            direct.target_id,
            direct.strength,
            direct.hops
           FROM direct
        UNION ALL
         SELECT two_hop.source_id,
            two_hop.target_id,
            two_hop.strength,
            two_hop.hops
           FROM two_hop) combined
  GROUP BY combined.source_id, combined.target_id
  WITH NO DATA;


ALTER TABLE public.mv_skill_2hop OWNER TO base_admin;

--
-- Name: MATERIALIZED VIEW mv_skill_2hop; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON MATERIALIZED VIEW public.mv_skill_2hop IS 'Pre-computed 2-hop transitive closure for fast graph matching. Refresh after bulk changes.';


--
-- Name: mv_skill_hub_scores; Type: MATERIALIZED VIEW; Schema: public; Owner: base_admin
--

CREATE MATERIALIZED VIEW public.mv_skill_hub_scores AS
 SELECT o.owl_id,
    o.canonical_name,
    count(r.owl_id) AS incoming_count,
    round(avg(r.strength), 3) AS avg_incoming_strength,
    sum(r.strength) AS total_incoming_strength
   FROM (public.owl o
     LEFT JOIN public.owl_relationships r ON (((o.owl_id = r.related_owl_id) AND (r.relationship = 'requires'::text))))
  GROUP BY o.owl_id, o.canonical_name
  WITH NO DATA;


ALTER TABLE public.mv_skill_hub_scores OWNER TO base_admin;

--
-- Name: MATERIALIZED VIEW mv_skill_hub_scores; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON MATERIALIZED VIEW public.mv_skill_hub_scores IS 'Pre-computed hub scores for graph matching. Refresh with: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_skill_hub_scores';


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.notifications (
    notification_id integer NOT NULL,
    user_id integer,
    type text NOT NULL,
    title text NOT NULL,
    message text,
    link text,
    read_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.notifications OWNER TO base_admin;

--
-- Name: notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.notifications_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_notification_id_seq OWNER TO base_admin;

--
-- Name: notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.notifications_notification_id_seq OWNED BY public.notifications.notification_id;


--
-- Name: onet_technology_skills; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.onet_technology_skills (
    onet_soc_code text,
    example_title text NOT NULL,
    commodity_code text,
    commodity_title text,
    hot_technology boolean,
    in_demand boolean
);


ALTER TABLE public.onet_technology_skills OWNER TO base_admin;

--
-- Name: owl_owl_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.owl_owl_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.owl_owl_id_seq OWNER TO base_admin;

--
-- Name: owl_owl_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.owl_owl_id_seq OWNED BY public.owl.owl_id;


--
-- Name: owl_pending; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.owl_pending (
    pending_id integer NOT NULL,
    owl_type text NOT NULL,
    raw_value text NOT NULL,
    source_language text DEFAULT 'en'::text,
    source_context jsonb,
    status text DEFAULT 'pending'::text,
    resolved_owl_id integer,
    resolution_notes text,
    created_at timestamp without time zone DEFAULT now(),
    processed_at timestamp without time zone,
    processed_by text
);


ALTER TABLE public.owl_pending OWNER TO base_admin;

--
-- Name: TABLE owl_pending; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.owl_pending IS 'Unresolved entity references awaiting human/AI classification';


--
-- Name: COLUMN owl_pending.raw_value; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_pending.raw_value IS 'Exact text received - may be misspelled, foreign language, etc.';


--
-- Name: COLUMN owl_pending.source_context; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.owl_pending.source_context IS 'Provenance: where did this come from?';


--
-- Name: owl_pending_pending_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.owl_pending_pending_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.owl_pending_pending_id_seq OWNER TO base_admin;

--
-- Name: owl_pending_pending_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.owl_pending_pending_id_seq OWNED BY public.owl_pending.pending_id;


--
-- Name: plz_centroid; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.plz_centroid (
    plz character varying(10),
    state_name text,
    latitude numeric,
    longitude numeric,
    place_count bigint
);


ALTER TABLE public.plz_centroid OWNER TO base_admin;

--
-- Name: plz_geocode; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.plz_geocode (
    plz character varying(10) NOT NULL,
    place_name character varying(180) NOT NULL,
    state_name character varying(100),
    latitude numeric(10,6),
    longitude numeric(10,6)
);


ALTER TABLE public.plz_geocode OWNER TO base_admin;

--
-- Name: posting_interest; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_interest (
    interest_id integer NOT NULL,
    user_id integer NOT NULL,
    posting_id integer NOT NULL,
    interested boolean NOT NULL,
    reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.posting_interest OWNER TO base_admin;

--
-- Name: posting_interest_interest_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.posting_interest_interest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posting_interest_interest_id_seq OWNER TO base_admin;

--
-- Name: posting_interest_interest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.posting_interest_interest_id_seq OWNED BY public.posting_interest.interest_id;


--
-- Name: postings_posting_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.postings_posting_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.postings_posting_id_seq OWNER TO base_admin;

--
-- Name: postings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.postings (
    posting_id integer DEFAULT nextval('public.postings_posting_id_seq'::regclass) NOT NULL,
    posting_name text NOT NULL,
    enabled boolean DEFAULT true,
    job_description text,
    job_title text,
    location_city text,
    location_country text,
    ihl_score integer,
    external_job_id text NOT NULL,
    external_url text NOT NULL,
    posting_status text DEFAULT 'active'::text,
    first_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    source_metadata jsonb,
    updated_at timestamp without time zone DEFAULT now(),
    extracted_summary text,
    source character varying(50),
    external_id character varying(255),
    invalidated boolean DEFAULT false,
    invalidated_reason text,
    invalidated_at timestamp with time zone,
    processing_failures integer DEFAULT 0,
    source_language character varying(5),
    domain_gate jsonb,
    location_state character varying(50),
    location_postal_code character varying(10),
    berufenet_id integer,
    berufenet_name text,
    berufenet_kldb text,
    qualification_level integer,
    berufenet_score real,
    berufenet_verified text,
    beruf text,
    last_validated_at timestamp with time zone,
    CONSTRAINT ihl_score_valid CHECK (((ihl_score IS NULL) OR ((ihl_score >= 0) AND (ihl_score <= 100)))),
    CONSTRAINT postings_status_check CHECK ((posting_status = ANY (ARRAY['pending'::text, 'active'::text, 'complete'::text, 'filled'::text, 'invalid'::text])))
);


ALTER TABLE public.postings OWNER TO base_admin;

--
-- Name: TABLE postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.postings IS 'Job postings from external sources. 
    
    Schema evolution:
    - 2025-11-06: Migration 060 - Changed UNIQUE to (source_id, posting_name), deleted duplicates (739→256)
    - 2025-11-06: Migration 061 - Dropped 10 dead columns (55→45)
    - 2025-11-07: Migration 062 - Dropped 23 legacy columns, added 4 client decision fields (45→28)
    - 2025-11-07: Migration 063 - Moved decision fields to user_posting_decisions (multi-user!) (28→24)
    
    Note: User-specific decisions (cover letters, no-go reasons) are now in user_posting_decisions table.
    All legacy data preserved in source_metadata JSONB column.';


--
-- Name: COLUMN postings.posting_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: COLUMN postings.posting_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_name IS 'Job identifier from source system (can be duplicate for test data)';


--
-- Name: COLUMN postings.ihl_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.ihl_score IS 'Internal Hire Likelihood score (0-100): probability that position is pre-wired for internal candidate';


--
-- Name: COLUMN postings.external_job_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.external_job_id IS 'External job ID from source system (e.g., Workday PositionID, API job ID). 
    Extracted from posting_position_uri for migrated records if not directly available.
    Used for job validation via API.';


--
-- Name: COLUMN postings.posting_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_status IS 'Lifecycle status: active, filled, expired, withdrawn, archived';


--
-- Name: COLUMN postings.first_seen_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.first_seen_at IS 'When this posting was first fetched';


--
-- Name: COLUMN postings.last_seen_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.last_seen_at IS 'Last time this posting was confirmed on source site';


--
-- Name: COLUMN postings.source_metadata; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.source_metadata IS 'Full JSON response from job source API. Preserves all data for future extraction.
Example: {"PositionID": "15930", "ApplyURI": [...], "CareerLevel": [...], ...}';


--
-- Name: COLUMN postings.extracted_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.extracted_summary IS 'Job posting summary extracted by LLM workflow. 
MUST be derived from llm_interactions via posting_state_checkpoints.
Source interaction ID stored in summary_llm_interaction_id.';


--
-- Name: COLUMN postings.invalidated; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.invalidated IS 'Is this posting invalid/corrupt? (NOT deletion)';


--
-- Name: COLUMN postings.invalidated_reason; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.invalidated_reason IS 'Why was this posting invalidated? (duplicate, bad data, etc.)';


--
-- Name: COLUMN postings.domain_gate; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.domain_gate IS 'Domain gate detection result: {domain, gate_decision, evidence, confidence}';


--
-- Name: COLUMN postings.beruf; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.beruf IS 'Official AA occupation category (e.g., Arzt/Ärztin). From API beruf field. Added 2026-02-03.';


--
-- Name: postings_for_matching; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.postings_for_matching AS
 SELECT postings.posting_id,
    postings.posting_name,
    postings.enabled,
    postings.job_description,
    postings.job_title,
    postings.location_city,
    postings.location_country,
    postings.ihl_score,
    postings.external_job_id,
    postings.external_url,
    postings.posting_status,
    postings.first_seen_at,
    postings.last_seen_at,
    postings.source_metadata,
    postings.updated_at,
    postings.extracted_summary,
    postings.source,
    postings.external_id,
    postings.invalidated,
    postings.processing_failures,
    postings.source_language,
    postings.domain_gate,
    COALESCE(postings.extracted_summary, postings.job_description) AS match_text
   FROM public.postings
  WHERE ((postings.job_description IS NOT NULL) AND (length(postings.job_description) > 150) AND (postings.invalidated = false) AND (postings.posting_status <> 'invalid'::text));


ALTER TABLE public.postings_for_matching OWNER TO base_admin;

--
-- Name: profession_similarity; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profession_similarity (
    berufenet_id_a integer NOT NULL,
    berufenet_id_b integer NOT NULL,
    kldb_score numeric(5,4) DEFAULT 0 NOT NULL,
    embedding_score numeric(5,4),
    combined_score numeric(5,4) DEFAULT 0 NOT NULL,
    rank_for_a integer,
    computed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.profession_similarity OWNER TO base_admin;

--
-- Name: profile_posting_matches; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_posting_matches (
    match_id integer NOT NULL,
    profile_id integer,
    posting_id integer,
    domain_gate_passed boolean,
    gate_reason text,
    skill_match_score numeric(4,3),
    match_rate text,
    recommendation text,
    confidence numeric(3,2),
    go_reasons jsonb,
    nogo_reasons jsonb,
    cover_letter text,
    nogo_narrative text,
    user_decision text,
    user_rating integer,
    user_feedback text,
    computed_at timestamp without time zone DEFAULT now(),
    model_version text,
    similarity_matrix jsonb,
    rated_at timestamp without time zone,
    user_applied boolean DEFAULT false,
    applied_at timestamp without time zone,
    application_status character varying(20) DEFAULT NULL::character varying,
    application_outcome character varying(20) DEFAULT NULL::character varying,
    outcome_at timestamp with time zone,
    first_viewed_at timestamp with time zone,
    last_viewed_at timestamp with time zone,
    view_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.profile_posting_matches OWNER TO base_admin;

--
-- Name: COLUMN profile_posting_matches.application_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_posting_matches.application_status IS 'applied, interviewing, offered, rejected, withdrawn';


--
-- Name: COLUMN profile_posting_matches.application_outcome; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_posting_matches.application_outcome IS 'hired, rejected, ghosted, withdrew';


--
-- Name: profile_posting_matches_match_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_posting_matches_match_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_posting_matches_match_id_seq OWNER TO base_admin;

--
-- Name: profile_posting_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_posting_matches_match_id_seq OWNED BY public.profile_posting_matches.match_id;


--
-- Name: profile_preferences; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_preferences (
    preference_id bigint NOT NULL,
    profile_id integer NOT NULL,
    topic_type text NOT NULL,
    topic_value text NOT NULL,
    sentiment text NOT NULL,
    strength smallint DEFAULT 1 NOT NULL,
    source text NOT NULL,
    source_event_id bigint,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT profile_preferences_sentiment_check CHECK ((sentiment = ANY (ARRAY['like'::text, 'dislike'::text, 'neutral'::text]))),
    CONSTRAINT profile_preferences_source_check CHECK ((source = ANY (ARRAY['explicit'::text, 'inferred_from_events'::text]))),
    CONSTRAINT profile_preferences_strength_check CHECK (((strength >= 1) AND (strength <= 3))),
    CONSTRAINT profile_preferences_topic_type_check CHECK ((topic_type = ANY (ARRAY['skill'::text, 'domain'::text, 'employer_type'::text, 'role_type'::text, 'location'::text])))
);


ALTER TABLE public.profile_preferences OWNER TO base_admin;

--
-- Name: profile_preferences_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_preferences_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_preferences_preference_id_seq OWNER TO base_admin;

--
-- Name: profile_preferences_preference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_preferences_preference_id_seq OWNED BY public.profile_preferences.preference_id;


--
-- Name: profile_translations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_translations (
    translation_id integer NOT NULL,
    profile_id integer NOT NULL,
    language character varying(10) NOT NULL,
    profile_summary text,
    translated_at timestamp without time zone DEFAULT now(),
    model text DEFAULT 'gemma3:4b'::text
);


ALTER TABLE public.profile_translations OWNER TO base_admin;

--
-- Name: TABLE profile_translations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_translations IS 'Non-destructive translation cache. Each row holds a translated profile_summary
     in a target language. The canonical profile.profile_summary is never overwritten.';


--
-- Name: profile_translations_translation_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_translations_translation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_translations_translation_id_seq OWNER TO base_admin;

--
-- Name: profile_translations_translation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_translations_translation_id_seq OWNED BY public.profile_translations.translation_id;


--
-- Name: profile_work_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_work_history (
    work_history_id integer NOT NULL,
    profile_id integer NOT NULL,
    company_name text NOT NULL,
    job_title text NOT NULL,
    department text,
    start_date date,
    end_date date,
    is_current boolean DEFAULT false,
    duration_months integer,
    job_description text,
    achievements text[],
    technologies_used text[],
    location text,
    remote boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    extraction_status text DEFAULT 'pending'::text,
    entry_type text DEFAULT 'work'::text NOT NULL
);


ALTER TABLE public.profile_work_history OWNER TO base_admin;

--
-- Name: COLUMN profile_work_history.entry_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_work_history.entry_type IS 'work, education, or project';


--
-- Name: profile_work_history_translations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_work_history_translations (
    id integer NOT NULL,
    work_history_id integer NOT NULL,
    language character varying(10) NOT NULL,
    job_description text,
    translated_at timestamp without time zone DEFAULT now(),
    model text DEFAULT 'gemma3:4b'::text
);


ALTER TABLE public.profile_work_history_translations OWNER TO base_admin;

--
-- Name: TABLE profile_work_history_translations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_work_history_translations IS 'Non-destructive translation cache for work-history job descriptions.
     Canonical profile_work_history.job_description is never overwritten.';


--
-- Name: profile_work_history_translations_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_work_history_translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_work_history_translations_id_seq OWNER TO base_admin;

--
-- Name: profile_work_history_translations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_work_history_translations_id_seq OWNED BY public.profile_work_history_translations.id;


--
-- Name: profile_work_history_work_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_work_history_work_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_work_history_work_history_id_seq OWNER TO base_admin;

--
-- Name: profile_work_history_work_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_work_history_work_history_id_seq OWNED BY public.profile_work_history.work_history_id;


--
-- Name: profiles; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profiles (
    profile_id integer NOT NULL,
    full_name text NOT NULL,
    availability_status text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    currency text DEFAULT 'CHF'::text,
    current_title text,
    desired_locations text[],
    desired_roles text[],
    email text,
    enabled boolean DEFAULT true,
    expected_salary_max integer,
    expected_salary_min integer,
    experience_level text,
    is_test_profile boolean DEFAULT false,
    linkedin_url text,
    location text,
    phone text,
    profile_raw_text text,
    profile_source text,
    profile_summary text,
    profile_type text DEFAULT 'self'::text,
    search_vector tsvector,
    skill_keywords jsonb,
    skills_extraction_status text DEFAULT 'pending'::text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id integer,
    years_of_experience integer,
    min_seniority text,
    matching_enabled boolean DEFAULT true,
    search_params jsonb,
    implied_skills jsonb,
    skill_weights jsonb,
    language character varying(10) DEFAULT 'de'::character varying,
    CONSTRAINT profiles_profile_type_check CHECK ((profile_type = ANY (ARRAY['self'::text, 'candidate'::text])))
);


ALTER TABLE public.profiles OWNER TO base_admin;

--
-- Name: TABLE profiles; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profiles IS 'Candidate profiles with skills mapped to job taxonomy';


--
-- Name: COLUMN profiles.experience_level; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.experience_level IS 'Classification: entry/junior/mid/senior/lead/executive';


--
-- Name: COLUMN profiles.profile_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.profile_summary IS 'LLM-extracted professional summary (parallel to postings.extracted_summary)';


--
-- Name: COLUMN profiles.skill_keywords; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.skill_keywords IS 'Array of taxonomy-matched skills (same format as postings.skill_keywords)';


--
-- Name: COLUMN profiles.implied_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.implied_skills IS 'LLM-inferred skills not explicitly stated in CV. Array of {name, category, confidence, evidence}. Set by cv_anonymizer Pass 3. Never overwritten — only set if null.';


--
-- Name: COLUMN profiles.skill_weights; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.skill_weights IS 'Per-skill weight multipliers for matching, updated from yogi feedback. Array of {skill, weight} where weight defaults to 1.0. Updated incrementally by preference-learning pipeline.';


--
-- Name: COLUMN profiles.language; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.language IS 'ISO-639-1 code of the language the profile was written in (e.g. ''de'', ''en'').
     Set automatically from CV text on upload; can only be ''de'' or ''en'' for now.';


--
-- Name: profiles_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profiles_profile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profiles_profile_id_seq OWNER TO base_admin;

--
-- Name: profiles_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profiles_profile_id_seq OWNED BY public.profiles.profile_id;


--
-- Name: push_subscriptions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.push_subscriptions (
    subscription_id integer NOT NULL,
    user_id integer NOT NULL,
    endpoint text NOT NULL,
    p256dh text NOT NULL,
    auth text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone
);


ALTER TABLE public.push_subscriptions OWNER TO base_admin;

--
-- Name: push_subscriptions_subscription_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.push_subscriptions_subscription_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.push_subscriptions_subscription_id_seq OWNER TO base_admin;

--
-- Name: push_subscriptions_subscription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.push_subscriptions_subscription_id_seq OWNED BY public.push_subscriptions.subscription_id;


--
-- Name: schema_changes; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.schema_changes (
    id integer NOT NULL,
    changed_at timestamp without time zone DEFAULT now(),
    change_type text,
    table_name text,
    column_name text,
    ddl_command text,
    changed_by text DEFAULT CURRENT_USER
);


ALTER TABLE public.schema_changes OWNER TO base_admin;

--
-- Name: TABLE schema_changes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.schema_changes IS 'Audit log for DDL changes. Auto-populated by event trigger.';


--
-- Name: recent_schema_changes; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.recent_schema_changes AS
 SELECT schema_changes.changed_at,
    schema_changes.change_type,
    schema_changes.table_name,
    schema_changes.changed_by,
    "left"(schema_changes.ddl_command, 100) AS ddl_preview
   FROM public.schema_changes
  ORDER BY schema_changes.changed_at DESC
 LIMIT 50;


ALTER TABLE public.recent_schema_changes OWNER TO base_admin;

--
-- Name: schema_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.schema_changes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.schema_changes_id_seq OWNER TO base_admin;

--
-- Name: schema_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.schema_changes_id_seq OWNED BY public.schema_changes.id;


--
-- Name: skill_aliases_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_aliases_skill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_aliases_skill_id_seq OWNER TO base_admin;

--
-- Name: skills_pending_taxonomy_pending_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skills_pending_taxonomy_pending_skill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skills_pending_taxonomy_pending_skill_id_seq OWNER TO base_admin;

--
-- Name: tickets; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.tickets (
    ticket_id bigint NOT NULL,
    actor_id integer NOT NULL,
    actor_type text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    execution_order integer NOT NULL,
    parent_ticket_id bigint,
    input_ticket_ids integer[] DEFAULT '{}'::integer[],
    input jsonb,
    output jsonb,
    error_message text,
    retry_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    enabled boolean DEFAULT true,
    invalidated boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    failure_type text,
    heartbeat_at timestamp with time zone,
    instruction_id integer,
    normalized_output text,
    subject_type character varying(50) DEFAULT 'posting'::character varying,
    subject_id integer,
    source text DEFAULT 'wave_runner'::text,
    batch_id bigint,
    consistency character varying(10) DEFAULT '1/1'::character varying,
    chain_id bigint,
    chain_depth integer DEFAULT 0,
    code_hash character varying(64),
    task_type_id integer,
    CONSTRAINT interactions_actor_type_check CHECK ((actor_type = ANY (ARRAY['ai_model'::text, 'machine_actor'::text, 'script'::text, 'human'::text, 'thick'::text]))),
    CONSTRAINT interactions_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'running'::text, 'completed'::text, 'failed'::text, 'invalidated'::text])))
);


ALTER TABLE public.tickets OWNER TO base_admin;

--
-- Name: TABLE tickets; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.tickets IS 'Task execution records showing what DID happen (input, output, timestamps). Renamed from interactions 2026-01-07 for clarity.';


--
-- Name: COLUMN tickets.input_ticket_ids; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.input_ticket_ids IS 'Array of parent interaction IDs for multi-parent cases';


--
-- Name: COLUMN tickets.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.enabled IS 'Flag to enable/disable interaction (NOT deletion)';


--
-- Name: COLUMN tickets.invalidated; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.invalidated IS 'Flag to mark interaction as invalid (duplicate, bug, etc.)';


--
-- Name: COLUMN tickets.failure_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.failure_type IS 'Classification: timeout, interrupted, rate_limit, api_error, parse_error, invalid_output, script_error, unknown';


--
-- Name: COLUMN tickets.normalized_output; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.normalized_output IS 'Normalized output->response for determinism comparison. 
         Uses normalize_extraction() from core/text_utils.py.
         Added 2025-12-21 after RAQ analysis.';


--
-- Name: COLUMN tickets.subject_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.subject_type IS 'Type of subject: posting, skill, user, profile, etc.';


--
-- Name: COLUMN tickets.subject_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.subject_id IS 'ID of the subject in its respective table';


--
-- Name: COLUMN tickets.batch_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.tickets.batch_id IS 'Which batch this interaction belongs to (for RAQ grouping)';


--
-- Name: task_logs_task_log_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.task_logs_task_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_logs_task_log_id_seq OWNER TO base_admin;

--
-- Name: task_logs_task_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.task_logs_task_log_id_seq OWNED BY public.tickets.ticket_id;


--
-- Name: task_routes; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.task_routes (
    route_id integer NOT NULL,
    from_instruction_id integer,
    to_instruction_id integer,
    condition_field text,
    condition_operator text,
    condition_value text,
    priority integer DEFAULT 0,
    enabled boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.task_routes OWNER TO base_admin;

--
-- Name: task_routes_route_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.task_routes_route_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_routes_route_id_seq OWNER TO base_admin;

--
-- Name: task_routes_route_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.task_routes_route_id_seq OWNED BY public.task_routes.route_id;


--
-- Name: task_types; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.task_types AS
 SELECT a.actor_id AS task_type_id,
    a.actor_id,
    a.actor_name AS task_type_name,
    a.actor_type AS task_type_description,
    a.script_file_path AS script_path,
    a.work_query,
    a.subject_type,
    a.priority,
    a.poll_priority,
    a.scale_limit,
    a.execution_type,
    a.requires_model,
    a.last_poll_at,
    a.lint_status,
    a.lint_checked_at,
    a.lint_errors,
    (0.0)::double precision AS llm_temperature,
    42 AS llm_seed,
    a.raq_config,
    a.enabled,
    a.script_code_hash,
    a.batch_size,
    a.timeout_seconds
   FROM public.actors a
  WHERE (a.actor_type = ANY (ARRAY['thick'::text, 'script'::text]));


ALTER TABLE public.task_types OWNER TO base_admin;

--
-- Name: usage_event_prices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usage_event_prices (
    event_type character varying(50) NOT NULL,
    cost_cents integer DEFAULT 0 NOT NULL,
    description text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.usage_event_prices OWNER TO postgres;

--
-- Name: usage_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usage_events (
    event_id bigint NOT NULL,
    user_id integer NOT NULL,
    event_type character varying(50) NOT NULL,
    cost_cents integer DEFAULT 0 NOT NULL,
    context jsonb DEFAULT '{}'::jsonb NOT NULL,
    billed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.usage_events OWNER TO postgres;

--
-- Name: usage_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.usage_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.usage_events_event_id_seq OWNER TO postgres;

--
-- Name: usage_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usage_events_event_id_seq OWNED BY public.usage_events.event_id;


--
-- Name: user_posting_interactions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_posting_interactions (
    interaction_id integer NOT NULL,
    user_id integer NOT NULL,
    posting_id integer NOT NULL,
    first_viewed_at timestamp with time zone,
    view_count integer DEFAULT 0,
    total_view_seconds integer DEFAULT 0,
    is_favorited boolean DEFAULT false,
    favorited_at timestamp with time zone,
    is_interested boolean DEFAULT false,
    interested_at timestamp with time zone,
    match_feedback text,
    match_feedback_at timestamp with time zone,
    state text DEFAULT 'unread'::text,
    state_changed_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_posting_interactions_match_feedback_check CHECK ((match_feedback = ANY (ARRAY['agree'::text, 'disagree'::text, NULL::text]))),
    CONSTRAINT user_posting_interactions_state_check CHECK ((state = ANY (ARRAY['unread'::text, 'read'::text, 'favorited'::text, 'interested'::text, 'researching'::text, 'informed'::text, 'coaching'::text, 'applied'::text, 'outcome_pending'::text, 'hired'::text, 'rejected'::text, 'ghosted'::text, 'unresponsive'::text])))
);


ALTER TABLE public.user_posting_interactions OWNER TO base_admin;

--
-- Name: user_posting_interactions_interaction_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_posting_interactions_interaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_posting_interactions_interaction_id_seq OWNER TO base_admin;

--
-- Name: user_posting_interactions_interaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_posting_interactions_interaction_id_seq OWNED BY public.user_posting_interactions.interaction_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    email text NOT NULL,
    google_id text,
    display_name text,
    avatar_url text,
    created_at timestamp without time zone DEFAULT now(),
    last_login_at timestamp without time zone,
    enabled boolean DEFAULT true,
    tier character varying(20) DEFAULT 'basis'::character varying,
    tier_updated_at timestamp with time zone,
    notification_email text,
    notification_consent_at timestamp with time zone,
    notification_preferences jsonb DEFAULT '{}'::jsonb,
    subscription_tier character varying(20) DEFAULT 'free'::character varying,
    subscription_status character varying(20) DEFAULT 'active'::character varying,
    stripe_customer_id character varying(100),
    stripe_subscription_id character varying(100),
    subscription_period_end timestamp with time zone,
    is_admin boolean DEFAULT false NOT NULL,
    yogi_name text,
    onboarding_completed_at timestamp with time zone,
    language text DEFAULT 'de'::text,
    formality text DEFAULT 'du'::text,
    trial_ends_at timestamp with time zone,
    trial_budget_cents integer DEFAULT 500 NOT NULL,
    terms_accepted_at timestamp with time zone,
    freeze_flag boolean DEFAULT false NOT NULL,
    gdpr_cv_consent_at timestamp with time zone,
    is_protected boolean DEFAULT false NOT NULL,
    situation_context jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: COLUMN users.tier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.tier IS 'basis, standard, sustainer';


--
-- Name: COLUMN users.notification_email; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.notification_email IS 'Opt-in email for notifications (separate from OAuth email)';


--
-- Name: COLUMN users.notification_consent_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.notification_consent_at IS 'Timestamp of consent, NULL = no consent';


--
-- Name: COLUMN users.notification_preferences; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.notification_preferences IS 'JSON: {job_alerts, mira_responses, journey_updates, frequency}';


--
-- Name: COLUMN users.subscription_tier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.subscription_tier IS 'Subscription tier: free, standard, sustainer';


--
-- Name: COLUMN users.subscription_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.subscription_status IS 'Stripe subscription status: active, past_due, canceled';


--
-- Name: COLUMN users.stripe_customer_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.stripe_customer_id IS 'Stripe customer ID for billing';


--
-- Name: COLUMN users.stripe_subscription_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.stripe_subscription_id IS 'Active Stripe subscription ID';


--
-- Name: COLUMN users.subscription_period_end; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.subscription_period_end IS 'End of current billing period';


--
-- Name: COLUMN users.is_admin; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.is_admin IS 'Fast auth cache. Source of truth: OWL yogi_admin membership.';


--
-- Name: COLUMN users.yogi_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.yogi_name IS 'Yogi-chosen display name. This is the ONLY name shown in UI and used by Mira.
Not from Google OAuth. Case-insensitive unique. 2-20 chars, alphanumeric + limited special.';


--
-- Name: COLUMN users.onboarding_completed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.onboarding_completed_at IS 'Set when yogi completes onboarding: has yogi_name + either has profile or skipped.
NULL means onboarding not yet completed — Mira should guide them.';


--
-- Name: COLUMN users.language; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.language IS 'UI language: de or en';


--
-- Name: COLUMN users.formality; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.formality IS 'Anrede: du or sie (German only)';


--
-- Name: COLUMN users.terms_accepted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.terms_accepted_at IS 'When the yogi accepted the T&Cs during onboarding. NULL = not yet accepted.';


--
-- Name: COLUMN users.freeze_flag; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.freeze_flag IS 'When TRUE, the user is frozen (Han Solo mode) — all LLM features blocked.';


--
-- Name: COLUMN users.gdpr_cv_consent_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.gdpr_cv_consent_at IS 'Timestamp of the most recent explicit GDPR consent for CV processing by AI services.';


--
-- Name: COLUMN users.is_protected; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.is_protected IS 'If true, reset/seed scripts refuse to touch this user. Set manually on real personal accounts.';


--
-- Name: user_usage_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.user_usage_summary AS
 SELECT u.user_id,
    u.yogi_name,
    u.email,
    u.subscription_status,
    u.trial_ends_at,
    u.trial_budget_cents,
    COALESCE(sum(e.cost_cents), (0)::bigint) AS total_spent_cents,
    COALESCE(sum(e.cost_cents) FILTER (WHERE (e.billed_at IS NULL)), (0)::bigint) AS unbilled_cents,
    count(e.event_id) AS event_count,
    max(e.created_at) AS last_event_at,
    ((u.trial_ends_at IS NULL) OR (u.trial_ends_at > now())) AS trial_active,
    ((u.trial_ends_at IS NOT NULL) AND (u.trial_ends_at < now()) AND ((u.subscription_status)::text <> 'active'::text) AND (COALESCE(sum(e.cost_cents) FILTER (WHERE (e.billed_at IS NULL)), (0)::bigint) > 0)) AS needs_payment
   FROM (public.users u
     LEFT JOIN public.usage_events e ON ((e.user_id = u.user_id)))
  GROUP BY u.user_id, u.yogi_name, u.email, u.subscription_status, u.trial_ends_at, u.trial_budget_cents;


ALTER TABLE public.user_usage_summary OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_user_id_seq OWNER TO postgres;

--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: v_entity_display; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_entity_display AS
 SELECT e.owl_id AS entity_id,
    e.owl_type AS entity_type,
    e.canonical_name,
    e.status,
    COALESCE(n.display_name, n_en.display_name, e.canonical_name) AS display_name,
    COALESCE(n.language, n_en.language, 'en'::text) AS language
   FROM ((public.owl e
     LEFT JOIN public.owl_names n ON (((e.owl_id = n.owl_id) AND (n.is_primary = true))))
     LEFT JOIN public.owl_names n_en ON (((e.owl_id = n_en.owl_id) AND (n_en.language = 'en'::text) AND (n_en.is_primary = true))))
  WHERE (e.status = 'active'::text);


ALTER TABLE public.v_entity_display OWNER TO base_admin;

--
-- Name: VIEW v_entity_display; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_entity_display IS 'Primary display name per entity with English fallback';


--
-- Name: validated_prompts_validated_prompt_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.validated_prompts_validated_prompt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.validated_prompts_validated_prompt_id_seq OWNER TO base_admin;

--
-- Name: yogi_audit_log; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_audit_log (
    audit_id bigint NOT NULL,
    user_id integer NOT NULL,
    actor text NOT NULL,
    event_type text NOT NULL,
    detail jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.yogi_audit_log OWNER TO base_admin;

--
-- Name: TABLE yogi_audit_log; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.yogi_audit_log IS 'Append-only legal/compliance record. Never UPDATE or DELETE rows here.';


--
-- Name: yogi_audit_log_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_audit_log_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_audit_log_audit_id_seq OWNER TO base_admin;

--
-- Name: yogi_audit_log_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_audit_log_audit_id_seq OWNED BY public.yogi_audit_log.audit_id;


--
-- Name: yogi_connections; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_connections (
    connection_id integer NOT NULL,
    posting_id integer NOT NULL,
    yogi_a_id integer NOT NULL,
    yogi_b_id integer NOT NULL,
    yogi_a_status text DEFAULT 'pending'::text,
    yogi_b_status text DEFAULT 'pending'::text,
    yogi_a_alias text DEFAULT 'Yogi A'::text,
    yogi_b_alias text DEFAULT 'Yogi B'::text,
    yogi_a_revealed boolean DEFAULT false,
    yogi_b_revealed boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    connected_at timestamp with time zone,
    expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval),
    CONSTRAINT yogi_connections_yogi_a_status_check CHECK ((yogi_a_status = ANY (ARRAY['pending'::text, 'accepted'::text, 'declined'::text, 'expired'::text]))),
    CONSTRAINT yogi_connections_yogi_b_status_check CHECK ((yogi_b_status = ANY (ARRAY['pending'::text, 'accepted'::text, 'declined'::text, 'expired'::text])))
);


ALTER TABLE public.yogi_connections OWNER TO base_admin;

--
-- Name: yogi_connections_connection_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_connections_connection_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_connections_connection_id_seq OWNER TO base_admin;

--
-- Name: yogi_connections_connection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_connections_connection_id_seq OWNED BY public.yogi_connections.connection_id;


--
-- Name: yogi_documents; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_documents (
    document_id integer NOT NULL,
    user_id integer NOT NULL,
    doc_type character varying(50) NOT NULL,
    title text NOT NULL,
    content text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_by character varying(50) DEFAULT 'system'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.yogi_documents OWNER TO base_admin;

--
-- Name: yogi_documents_document_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_documents_document_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_documents_document_id_seq OWNER TO base_admin;

--
-- Name: yogi_documents_document_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_documents_document_id_seq OWNED BY public.yogi_documents.document_id;


--
-- Name: yogi_events; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_events (
    event_id integer NOT NULL,
    user_id integer NOT NULL,
    event_type text NOT NULL,
    event_data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.yogi_events OWNER TO base_admin;

--
-- Name: TABLE yogi_events; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.yogi_events IS 'Behavioral events for Mira context — not chat messages';


--
-- Name: COLUMN yogi_events.event_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_events.event_type IS 'login | page_view | search_filter | posting_view | match_action';


--
-- Name: COLUMN yogi_events.event_data; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_events.event_data IS 'JSON payload: {page, posting_id, title, domains, ql, city, radius, action, dwell_s}';


--
-- Name: yogi_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_events_event_id_seq OWNER TO base_admin;

--
-- Name: yogi_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_events_event_id_seq OWNED BY public.yogi_events.event_id;


--
-- Name: yogi_messages; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_messages (
    message_id integer NOT NULL,
    user_id integer NOT NULL,
    sender_type text NOT NULL,
    sender_user_id integer,
    posting_id integer,
    message_type text NOT NULL,
    subject text,
    body text NOT NULL,
    attachment_json jsonb,
    read_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    recipient_type text,
    CONSTRAINT yogi_messages_sender_type_check CHECK ((sender_type = ANY (ARRAY['doug'::text, 'mira'::text, 'adele'::text, 'arden'::text, 'system'::text, 'yogi'::text, 'sage'::text, 'sandy'::text, 'mysti'::text])))
);


ALTER TABLE public.yogi_messages OWNER TO base_admin;

--
-- Name: TABLE yogi_messages; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.yogi_messages IS 'Messages from Doug/Mira/Adele/System to yogis, and Y2Y chat';


--
-- Name: COLUMN yogi_messages.sender_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_messages.sender_type IS 'doug=research reports, mira=companion, adele=coaching, system=notifications, yogi=Y2Y chat';


--
-- Name: COLUMN yogi_messages.message_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_messages.message_type IS 'research_complete, connection_request, coaching_followup, reminder, etc.';


--
-- Name: COLUMN yogi_messages.attachment_json; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_messages.attachment_json IS 'Structured data (Doug reports, etc.)';


--
-- Name: COLUMN yogi_messages.recipient_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.yogi_messages.recipient_type IS 'When set, indicates message is TO an actor (doug, mira, etc). user_id becomes sender.';


--
-- Name: yogi_messages_message_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_messages_message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_messages_message_id_seq OWNER TO base_admin;

--
-- Name: yogi_messages_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_messages_message_id_seq OWNED BY public.yogi_messages.message_id;


--
-- Name: yogi_newsletters; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_newsletters (
    newsletter_id integer NOT NULL,
    newsletter_date date NOT NULL,
    language character varying(5) DEFAULT 'de'::character varying,
    content text NOT NULL,
    generated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.yogi_newsletters OWNER TO base_admin;

--
-- Name: yogi_newsletters_newsletter_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_newsletters_newsletter_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_newsletters_newsletter_id_seq OWNER TO base_admin;

--
-- Name: yogi_newsletters_newsletter_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_newsletters_newsletter_id_seq OWNED BY public.yogi_newsletters.newsletter_id;


--
-- Name: yogi_posting_events; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.yogi_posting_events (
    event_id bigint NOT NULL,
    profile_id integer NOT NULL,
    posting_id integer NOT NULL,
    match_id integer,
    event_type text NOT NULL,
    reason text,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT yogi_posting_events_event_type_check CHECK ((event_type = ANY (ARRAY['viewed'::text, 'saved'::text, 'dismissed'::text, 'apply_intent'::text, 'applied'::text, 'not_applied'::text, 'outcome_received'::text])))
);


ALTER TABLE public.yogi_posting_events OWNER TO base_admin;

--
-- Name: yogi_posting_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.yogi_posting_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.yogi_posting_events_event_id_seq OWNER TO base_admin;

--
-- Name: yogi_posting_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.yogi_posting_events_event_id_seq OWNED BY public.yogi_posting_events.event_id;


--
-- Name: _archive_tickets_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public._archive_tickets_history ALTER COLUMN history_id SET DEFAULT nextval('public.interactions_history_history_id_seq'::regclass);


--
-- Name: adele_sessions session_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.adele_sessions ALTER COLUMN session_id SET DEFAULT nextval('public.adele_sessions_session_id_seq'::regclass);


--
-- Name: arcade_scores id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.arcade_scores ALTER COLUMN id SET DEFAULT nextval('public.arcade_scores_id_seq'::regclass);


--
-- Name: attribute_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.attribute_history ALTER COLUMN history_id SET DEFAULT nextval('public.attribute_history_history_id_seq'::regclass);


--
-- Name: batches batch_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches ALTER COLUMN batch_id SET DEFAULT nextval('public.batches_batch_id_seq'::regclass);


--
-- Name: city_snapshot city_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.city_snapshot ALTER COLUMN city_id SET DEFAULT nextval('public.city_snapshot_city_id_seq'::regclass);


--
-- Name: company_alias_variants variant_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_alias_variants ALTER COLUMN variant_id SET DEFAULT nextval('public.company_alias_variants_variant_id_seq'::regclass);


--
-- Name: company_aliases alias_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_aliases ALTER COLUMN alias_id SET DEFAULT nextval('public.company_aliases_alias_id_seq'::regclass);


--
-- Name: demand_snapshot snapshot_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.demand_snapshot ALTER COLUMN snapshot_id SET DEFAULT nextval('public.demand_snapshot_snapshot_id_seq'::regclass);


--
-- Name: feedback feedback_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.feedback ALTER COLUMN feedback_id SET DEFAULT nextval('public.feedback_feedback_id_seq'::regclass);


--
-- Name: mira_faq_candidates id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.mira_faq_candidates ALTER COLUMN id SET DEFAULT nextval('public.mira_faq_candidates_id_seq'::regclass);


--
-- Name: mira_questions question_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.mira_questions ALTER COLUMN question_id SET DEFAULT nextval('public.mira_questions_question_id_seq'::regclass);


--
-- Name: notifications notification_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.notifications ALTER COLUMN notification_id SET DEFAULT nextval('public.notifications_notification_id_seq'::regclass);


--
-- Name: owl owl_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl ALTER COLUMN owl_id SET DEFAULT nextval('public.owl_owl_id_seq'::regclass);


--
-- Name: owl_pending pending_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_pending ALTER COLUMN pending_id SET DEFAULT nextval('public.owl_pending_pending_id_seq'::regclass);


--
-- Name: posting_interest interest_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_interest ALTER COLUMN interest_id SET DEFAULT nextval('public.posting_interest_interest_id_seq'::regclass);


--
-- Name: profile_posting_matches match_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_posting_matches ALTER COLUMN match_id SET DEFAULT nextval('public.profile_posting_matches_match_id_seq'::regclass);


--
-- Name: profile_preferences preference_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_preferences ALTER COLUMN preference_id SET DEFAULT nextval('public.profile_preferences_preference_id_seq'::regclass);


--
-- Name: profile_translations translation_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_translations ALTER COLUMN translation_id SET DEFAULT nextval('public.profile_translations_translation_id_seq'::regclass);


--
-- Name: profile_work_history work_history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history ALTER COLUMN work_history_id SET DEFAULT nextval('public.profile_work_history_work_history_id_seq'::regclass);


--
-- Name: profile_work_history_translations id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history_translations ALTER COLUMN id SET DEFAULT nextval('public.profile_work_history_translations_id_seq'::regclass);


--
-- Name: profiles profile_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles ALTER COLUMN profile_id SET DEFAULT nextval('public.profiles_profile_id_seq'::regclass);


--
-- Name: push_subscriptions subscription_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.push_subscriptions ALTER COLUMN subscription_id SET DEFAULT nextval('public.push_subscriptions_subscription_id_seq'::regclass);


--
-- Name: schema_changes id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.schema_changes ALTER COLUMN id SET DEFAULT nextval('public.schema_changes_id_seq'::regclass);


--
-- Name: task_routes route_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.task_routes ALTER COLUMN route_id SET DEFAULT nextval('public.task_routes_route_id_seq'::regclass);


--
-- Name: tickets ticket_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.tickets ALTER COLUMN ticket_id SET DEFAULT nextval('public.task_logs_task_log_id_seq'::regclass);


--
-- Name: usage_events event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usage_events ALTER COLUMN event_id SET DEFAULT nextval('public.usage_events_event_id_seq'::regclass);


--
-- Name: user_posting_interactions interaction_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_interactions ALTER COLUMN interaction_id SET DEFAULT nextval('public.user_posting_interactions_interaction_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: yogi_audit_log audit_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_audit_log ALTER COLUMN audit_id SET DEFAULT nextval('public.yogi_audit_log_audit_id_seq'::regclass);


--
-- Name: yogi_connections connection_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections ALTER COLUMN connection_id SET DEFAULT nextval('public.yogi_connections_connection_id_seq'::regclass);


--
-- Name: yogi_documents document_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_documents ALTER COLUMN document_id SET DEFAULT nextval('public.yogi_documents_document_id_seq'::regclass);


--
-- Name: yogi_events event_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_events ALTER COLUMN event_id SET DEFAULT nextval('public.yogi_events_event_id_seq'::regclass);


--
-- Name: yogi_messages message_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_messages ALTER COLUMN message_id SET DEFAULT nextval('public.yogi_messages_message_id_seq'::regclass);


--
-- Name: yogi_newsletters newsletter_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_newsletters ALTER COLUMN newsletter_id SET DEFAULT nextval('public.yogi_newsletters_newsletter_id_seq'::regclass);


--
-- Name: yogi_posting_events event_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_posting_events ALTER COLUMN event_id SET DEFAULT nextval('public.yogi_posting_events_event_id_seq'::regclass);


--
-- Name: actors actors_actor_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_actor_name_unique UNIQUE (actor_name);


--
-- Name: actors actors_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_pkey PRIMARY KEY (actor_id);


--
-- Name: adele_sessions adele_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.adele_sessions
    ADD CONSTRAINT adele_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: arcade_scores arcade_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.arcade_scores
    ADD CONSTRAINT arcade_scores_pkey PRIMARY KEY (id);


--
-- Name: attribute_history attribute_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.attribute_history
    ADD CONSTRAINT attribute_history_pkey PRIMARY KEY (history_id);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (batch_id);


--
-- Name: berufenet berufenet_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.berufenet
    ADD CONSTRAINT berufenet_pkey PRIMARY KEY (berufenet_id);


--
-- Name: berufenet_synonyms berufenet_synonyms_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.berufenet_synonyms
    ADD CONSTRAINT berufenet_synonyms_pkey PRIMARY KEY (aa_beruf);


--
-- Name: city_country_map city_country_map_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.city_country_map
    ADD CONSTRAINT city_country_map_pkey PRIMARY KEY (city_id);


--
-- Name: city_snapshot city_snapshot_location_state_location_city_domain_code_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.city_snapshot
    ADD CONSTRAINT city_snapshot_location_state_location_city_domain_code_key UNIQUE (location_state, location_city, domain_code);


--
-- Name: city_snapshot city_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.city_snapshot
    ADD CONSTRAINT city_snapshot_pkey PRIMARY KEY (city_id);


--
-- Name: company_alias_variants company_alias_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_alias_variants
    ADD CONSTRAINT company_alias_variants_pkey PRIMARY KEY (variant_id);


--
-- Name: company_aliases company_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_aliases
    ADD CONSTRAINT company_aliases_pkey PRIMARY KEY (alias_id);


--
-- Name: demand_snapshot demand_snapshot_location_state_domain_code_berufenet_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.demand_snapshot
    ADD CONSTRAINT demand_snapshot_location_state_domain_code_berufenet_id_key UNIQUE (location_state, domain_code, berufenet_id);


--
-- Name: demand_snapshot demand_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.demand_snapshot
    ADD CONSTRAINT demand_snapshot_pkey PRIMARY KEY (snapshot_id);


--
-- Name: embeddings embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.embeddings
    ADD CONSTRAINT embeddings_pkey PRIMARY KEY (text_hash);


--
-- Name: owl entities_entity_type_canonical_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl
    ADD CONSTRAINT entities_entity_type_canonical_name_key UNIQUE (owl_type, canonical_name);


--
-- Name: owl_relationships entity_relationships_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_relationships
    ADD CONSTRAINT entity_relationships_unique UNIQUE (owl_id, related_owl_id, relationship);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (feedback_id);


--
-- Name: founder_debt founder_debt_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.founder_debt
    ADD CONSTRAINT founder_debt_pkey PRIMARY KEY (contributor);


--
-- Name: _archive_tickets_history interactions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public._archive_tickets_history
    ADD CONSTRAINT interactions_history_pkey PRIMARY KEY (history_id);


--
-- Name: tickets interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT interactions_pkey PRIMARY KEY (ticket_id);


--
-- Name: ledger_monthly ledger_monthly_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.ledger_monthly
    ADD CONSTRAINT ledger_monthly_pkey PRIMARY KEY (month);


--
-- Name: mira_faq_candidates mira_faq_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.mira_faq_candidates
    ADD CONSTRAINT mira_faq_candidates_pkey PRIMARY KEY (id);


--
-- Name: mira_questions mira_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.mira_questions
    ADD CONSTRAINT mira_questions_pkey PRIMARY KEY (question_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (notification_id);


--
-- Name: owl_names owl_names_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_names
    ADD CONSTRAINT owl_names_pkey PRIMARY KEY (owl_id, language, display_name);


--
-- Name: owl_pending owl_pending_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_pending
    ADD CONSTRAINT owl_pending_pkey PRIMARY KEY (pending_id);


--
-- Name: owl owl_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl
    ADD CONSTRAINT owl_pkey PRIMARY KEY (owl_id);


--
-- Name: owl_relationships owl_relationships_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_relationships
    ADD CONSTRAINT owl_relationships_pkey PRIMARY KEY (owl_id, related_owl_id, relationship);


--
-- Name: plz_geocode plz_geocode_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.plz_geocode
    ADD CONSTRAINT plz_geocode_pkey PRIMARY KEY (plz, place_name);


--
-- Name: posting_interest posting_interest_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_interest
    ADD CONSTRAINT posting_interest_pkey PRIMARY KEY (interest_id);


--
-- Name: posting_interest posting_interest_user_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_interest
    ADD CONSTRAINT posting_interest_user_id_posting_id_key UNIQUE (user_id, posting_id);


--
-- Name: postings postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_pkey PRIMARY KEY (posting_id);


--
-- Name: profession_similarity profession_similarity_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profession_similarity
    ADD CONSTRAINT profession_similarity_pkey PRIMARY KEY (berufenet_id_a, berufenet_id_b);


--
-- Name: profile_posting_matches profile_posting_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_posting_matches
    ADD CONSTRAINT profile_posting_matches_pkey PRIMARY KEY (match_id);


--
-- Name: profile_posting_matches profile_posting_matches_profile_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_posting_matches
    ADD CONSTRAINT profile_posting_matches_profile_id_posting_id_key UNIQUE (profile_id, posting_id);


--
-- Name: profile_preferences profile_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_preferences
    ADD CONSTRAINT profile_preferences_pkey PRIMARY KEY (preference_id);


--
-- Name: profile_translations profile_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_translations
    ADD CONSTRAINT profile_translations_pkey PRIMARY KEY (translation_id);


--
-- Name: profile_translations profile_translations_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_translations
    ADD CONSTRAINT profile_translations_unique UNIQUE (profile_id, language);


--
-- Name: profile_work_history profile_work_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history
    ADD CONSTRAINT profile_work_history_pkey PRIMARY KEY (work_history_id);


--
-- Name: profile_work_history_translations profile_work_history_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history_translations
    ADD CONSTRAINT profile_work_history_translations_pkey PRIMARY KEY (id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (profile_id);


--
-- Name: push_subscriptions push_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.push_subscriptions
    ADD CONSTRAINT push_subscriptions_pkey PRIMARY KEY (subscription_id);


--
-- Name: push_subscriptions push_subscriptions_user_id_endpoint_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.push_subscriptions
    ADD CONSTRAINT push_subscriptions_user_id_endpoint_key UNIQUE (user_id, endpoint);


--
-- Name: profile_work_history_translations pwht_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history_translations
    ADD CONSTRAINT pwht_unique UNIQUE (work_history_id, language);


--
-- Name: schema_changes schema_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.schema_changes
    ADD CONSTRAINT schema_changes_pkey PRIMARY KEY (id);


--
-- Name: task_routes task_routes_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.task_routes
    ADD CONSTRAINT task_routes_pkey PRIMARY KEY (route_id);


--
-- Name: usage_event_prices usage_event_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usage_event_prices
    ADD CONSTRAINT usage_event_prices_pkey PRIMARY KEY (event_type);


--
-- Name: usage_events usage_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_pkey PRIMARY KEY (event_id);


--
-- Name: user_posting_interactions user_posting_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_interactions
    ADD CONSTRAINT user_posting_interactions_pkey PRIMARY KEY (interaction_id);


--
-- Name: user_posting_interactions user_posting_interactions_user_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_interactions
    ADD CONSTRAINT user_posting_interactions_user_id_posting_id_key UNIQUE (user_id, posting_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_google_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_google_id_key UNIQUE (google_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: yogi_audit_log yogi_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_audit_log
    ADD CONSTRAINT yogi_audit_log_pkey PRIMARY KEY (audit_id);


--
-- Name: yogi_connections yogi_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections
    ADD CONSTRAINT yogi_connections_pkey PRIMARY KEY (connection_id);


--
-- Name: yogi_connections yogi_connections_posting_id_yogi_a_id_yogi_b_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections
    ADD CONSTRAINT yogi_connections_posting_id_yogi_a_id_yogi_b_id_key UNIQUE (posting_id, yogi_a_id, yogi_b_id);


--
-- Name: yogi_documents yogi_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_documents
    ADD CONSTRAINT yogi_documents_pkey PRIMARY KEY (document_id);


--
-- Name: yogi_events yogi_events_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_events
    ADD CONSTRAINT yogi_events_pkey PRIMARY KEY (event_id);


--
-- Name: yogi_messages yogi_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_messages
    ADD CONSTRAINT yogi_messages_pkey PRIMARY KEY (message_id);


--
-- Name: yogi_newsletters yogi_newsletters_newsletter_date_language_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_newsletters
    ADD CONSTRAINT yogi_newsletters_newsletter_date_language_key UNIQUE (newsletter_date, language);


--
-- Name: yogi_newsletters yogi_newsletters_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_newsletters
    ADD CONSTRAINT yogi_newsletters_pkey PRIMARY KEY (newsletter_id);


--
-- Name: yogi_posting_events yogi_posting_events_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_posting_events
    ADD CONSTRAINT yogi_posting_events_pkey PRIMARY KEY (event_id);


--
-- Name: embeddings_text_idx; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX embeddings_text_idx ON public.embeddings USING hash (text);


--
-- Name: idx_actors_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_enabled ON public.actors USING btree (enabled);


--
-- Name: idx_actors_execution_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_execution_type ON public.actors USING btree (execution_type) WHERE (enabled = true);


--
-- Name: idx_actors_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_parent ON public.actors USING btree (parent_actor_id);


--
-- Name: idx_actors_production; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_production ON public.actors USING btree (is_production, enabled) WHERE (actor_type = 'ai_model'::text);


--
-- Name: idx_actors_qualified; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_qualified ON public.actors USING btree (qualified) WHERE (qualified = true);


--
-- Name: idx_actors_sync_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_sync_status ON public.actors USING btree (script_sync_status) WHERE (script_sync_status <> 'synced'::text);


--
-- Name: idx_actors_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_type ON public.actors USING btree (actor_type);


--
-- Name: idx_actors_type_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_type_enabled ON public.actors USING btree (actor_type, enabled);


--
-- Name: idx_actors_user_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_user_id ON public.actors USING btree (user_id) WHERE (user_id IS NOT NULL);


--
-- Name: idx_actors_variant; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_variant ON public.actors USING btree (model_variant) WHERE (model_variant IS NOT NULL);


--
-- Name: idx_adele_one_active_session; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_adele_one_active_session ON public.adele_sessions USING btree (user_id) WHERE (completed_at IS NULL);


--
-- Name: idx_adele_sessions_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_adele_sessions_user ON public.adele_sessions USING btree (user_id);


--
-- Name: idx_arcade_scores_top; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_arcade_scores_top ON public.arcade_scores USING btree (score DESC);


--
-- Name: idx_arcade_scores_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_arcade_scores_user ON public.arcade_scores USING btree (user_id, score DESC);


--
-- Name: idx_attribute_history_lookup; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_attribute_history_lookup ON public.attribute_history USING btree (table_name, record_id, attribute_name);


--
-- Name: idx_audit_created_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_audit_created_at ON public.yogi_audit_log USING btree (created_at DESC);


--
-- Name: idx_audit_event_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_audit_event_type ON public.yogi_audit_log USING btree (event_type);


--
-- Name: idx_audit_user_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_audit_user_id ON public.yogi_audit_log USING btree (user_id);


--
-- Name: idx_batches_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_batches_conversation ON public.batches USING btree (task_type_id, status);


--
-- Name: idx_batches_reason; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_batches_reason ON public.batches USING btree (reason) WHERE (reason IS NOT NULL);


--
-- Name: idx_berufenet_kldb; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_berufenet_kldb ON public.berufenet USING btree (kldb);


--
-- Name: idx_berufenet_name_lower; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_berufenet_name_lower ON public.berufenet USING btree (lower(name));


--
-- Name: idx_city_country_map_city; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_country_map_city ON public.city_country_map USING btree (lower(city));


--
-- Name: idx_city_country_map_city_ascii; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_country_map_city_ascii ON public.city_country_map USING btree (lower(city_ascii));


--
-- Name: idx_city_snapshot_city; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_snapshot_city ON public.city_snapshot USING btree (location_city);


--
-- Name: idx_city_snapshot_domain; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_snapshot_domain ON public.city_snapshot USING btree (domain_code) WHERE (domain_code IS NOT NULL);


--
-- Name: idx_city_snapshot_state; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_snapshot_state ON public.city_snapshot USING btree (location_state);


--
-- Name: idx_city_snapshot_total; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_snapshot_total ON public.city_snapshot USING btree (total_postings DESC);


--
-- Name: idx_company_alias_pattern; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_company_alias_pattern ON public.company_aliases USING btree (lower(company_pattern));


--
-- Name: idx_company_alias_verified; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_company_alias_verified ON public.company_aliases USING btree (verified) WHERE (verified = true);


--
-- Name: idx_company_variant_lower; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_company_variant_lower ON public.company_alias_variants USING btree (lower(variant));


--
-- Name: idx_demand_snapshot_berufenet; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_demand_snapshot_berufenet ON public.demand_snapshot USING btree (berufenet_id) WHERE (berufenet_id IS NOT NULL);


--
-- Name: idx_demand_snapshot_domain; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_demand_snapshot_domain ON public.demand_snapshot USING btree (domain_code);


--
-- Name: idx_demand_snapshot_state; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_demand_snapshot_state ON public.demand_snapshot USING btree (location_state);


--
-- Name: idx_documents_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_documents_created ON public.yogi_documents USING btree (created_at DESC);


--
-- Name: idx_documents_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_documents_type ON public.yogi_documents USING btree (doc_type);


--
-- Name: idx_documents_user_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_documents_user_id ON public.yogi_documents USING btree (user_id);


--
-- Name: idx_entities_canonical_lower_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_entities_canonical_lower_unique ON public.owl USING btree (lower(canonical_name), owl_type) WHERE (status = 'active'::text);


--
-- Name: idx_entities_merged; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entities_merged ON public.owl USING btree (merged_into_entity_id) WHERE (merged_into_entity_id IS NOT NULL);


--
-- Name: idx_entity_names_lookup; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entity_names_lookup ON public.owl_names USING btree (display_name, language);


--
-- Name: idx_entity_names_name_lower; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entity_names_name_lower ON public.owl_names USING btree (lower(display_name), language);


--
-- Name: idx_entity_names_primary; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entity_names_primary ON public.owl_names USING btree (owl_id, language) WHERE (is_primary = true);


--
-- Name: idx_entity_names_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entity_names_type ON public.owl_names USING btree (name_type);


--
-- Name: idx_entity_names_valid; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_entity_names_valid ON public.owl_names USING btree (owl_id) WHERE (valid_to IS NULL);


--
-- Name: idx_entity_single_is_a_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_entity_single_is_a_parent ON public.owl_relationships USING btree (owl_id) WHERE (relationship = 'is_a'::text);


--
-- Name: idx_faq_candidates_pending; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_faq_candidates_pending ON public.mira_faq_candidates USING btree (created_at) WHERE (reviewed_at IS NULL);


--
-- Name: idx_faq_candidates_user_message; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_faq_candidates_user_message ON public.mira_faq_candidates USING gin (to_tsvector('german'::regconfig, user_message));


--
-- Name: idx_feedback_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_feedback_created ON public.feedback USING btree (created_at DESC);


--
-- Name: idx_feedback_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_feedback_status ON public.feedback USING btree (status);


--
-- Name: idx_feedback_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_feedback_user ON public.feedback USING btree (user_id);


--
-- Name: idx_interactions_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_actor ON public.tickets USING btree (actor_id, status);


--
-- Name: idx_interactions_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_batch ON public.tickets USING btree (batch_id) WHERE (batch_id IS NOT NULL);


--
-- Name: idx_interactions_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_enabled ON public.tickets USING btree (enabled, invalidated) WHERE ((enabled = true) AND (invalidated = false));


--
-- Name: idx_interactions_instruction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_instruction ON public.tickets USING btree (instruction_id) WHERE (instruction_id IS NOT NULL);


--
-- Name: idx_interactions_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_parent ON public.tickets USING btree (parent_ticket_id);


--
-- Name: idx_interactions_running_heartbeat; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_running_heartbeat ON public.tickets USING btree (heartbeat_at) WHERE (status = 'running'::text);


--
-- Name: idx_interactions_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_status ON public.tickets USING btree (status, updated_at) WHERE (status = ANY (ARRAY['pending'::text, 'running'::text]));


--
-- Name: idx_interactions_subject; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_subject ON public.tickets USING btree (subject_type, subject_id);


--
-- Name: idx_mira_questions_pending; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_mira_questions_pending ON public.mira_questions USING btree (asked_at) WHERE ((answered_at IS NULL) AND (closed_at IS NULL));


--
-- Name: idx_mira_questions_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_mira_questions_user ON public.mira_questions USING btree (user_id);


--
-- Name: idx_mv_2hop_pk; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_mv_2hop_pk ON public.mv_skill_2hop USING btree (source_id, target_id);


--
-- Name: idx_mv_2hop_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_mv_2hop_source ON public.mv_skill_2hop USING btree (source_id, strength DESC);


--
-- Name: idx_mv_2hop_target; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_mv_2hop_target ON public.mv_skill_2hop USING btree (target_id, strength DESC);


--
-- Name: idx_mv_hub_scores_incoming; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_mv_hub_scores_incoming ON public.mv_skill_hub_scores USING btree (incoming_count DESC);


--
-- Name: idx_mv_hub_scores_pk; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_mv_hub_scores_pk ON public.mv_skill_hub_scores USING btree (owl_id);


--
-- Name: idx_notifications_user_unread; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_notifications_user_unread ON public.notifications USING btree (user_id, read_at) WHERE (read_at IS NULL);


--
-- Name: idx_owl_external_job_site_prefix; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_external_job_site_prefix ON public.owl USING btree (((metadata ->> 'aa_prefix'::text))) WHERE (owl_type = 'external_job_site'::text);


--
-- Name: idx_owl_pending_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_pending_status ON public.owl_pending USING btree (status) WHERE (status = 'pending'::text);


--
-- Name: idx_owl_pending_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_pending_type ON public.owl_pending USING btree (owl_type, status);


--
-- Name: idx_owl_pending_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_owl_pending_unique ON public.owl_pending USING btree (owl_type, raw_value);


--
-- Name: idx_owl_rel_belongs_to; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_rel_belongs_to ON public.owl_relationships USING btree (owl_id) WHERE (relationship = 'belongs_to'::text);


--
-- Name: idx_owl_rel_requires_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_rel_requires_source ON public.owl_relationships USING btree (owl_id, strength DESC) WHERE (relationship = 'requires'::text);


--
-- Name: idx_owl_rel_requires_target; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_rel_requires_target ON public.owl_relationships USING btree (related_owl_id, strength DESC) WHERE (relationship = 'requires'::text);


--
-- Name: idx_owl_relationships_related; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_relationships_related ON public.owl_relationships USING btree (related_owl_id);


--
-- Name: idx_owl_relationships_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_relationships_type ON public.owl_relationships USING btree (relationship);


--
-- Name: idx_owl_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_status ON public.owl USING btree (status) WHERE (status <> 'active'::text);


--
-- Name: idx_owl_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_owl_type ON public.owl USING btree (owl_type);


--
-- Name: idx_plz_centroid_plz; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_plz_centroid_plz ON public.plz_centroid USING btree (plz);


--
-- Name: idx_plz_geocode_plz; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_plz_geocode_plz ON public.plz_geocode USING btree (plz);


--
-- Name: idx_posting_interest_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_interest_posting ON public.posting_interest USING btree (posting_id);


--
-- Name: idx_posting_interest_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_interest_user ON public.posting_interest USING btree (user_id);


--
-- Name: idx_postings_aa_with_desc; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_aa_with_desc ON public.postings USING btree (source, posting_id DESC) WHERE (((source)::text = 'arbeitsagentur'::text) AND (job_description IS NOT NULL) AND (length(job_description) > 100));


--
-- Name: idx_postings_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_active ON public.postings USING btree (posting_status) WHERE (posting_status = 'active'::text);


--
-- Name: idx_postings_beruf; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_beruf ON public.postings USING btree (beruf) WHERE (beruf IS NOT NULL);


--
-- Name: idx_postings_completion; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_completion ON public.postings USING btree (posting_id) WHERE ((enabled = true) AND (job_description IS NOT NULL));


--
-- Name: idx_postings_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_enabled ON public.postings USING btree (enabled);


--
-- Name: idx_postings_external; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_external ON public.postings USING btree (source, external_id);


--
-- Name: idx_postings_external_id_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_external_id_active ON public.postings USING btree (external_id) WHERE ((external_id IS NOT NULL) AND (invalidated = false) AND (enabled = true));


--
-- Name: idx_postings_external_job_id_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_external_job_id_unique ON public.postings USING btree (external_job_id) WHERE ((invalidated = false) AND (external_job_id IS NOT NULL));


--
-- Name: idx_postings_ihl_score; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_ihl_score ON public.postings USING btree (ihl_score) WHERE (ihl_score IS NOT NULL);


--
-- Name: idx_postings_invalidated; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_invalidated ON public.postings USING btree (invalidated) WHERE (invalidated = true);


--
-- Name: idx_postings_pending_owl; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_pending_owl ON public.postings USING btree (berufenet_verified, berufenet_id) WHERE ((berufenet_verified = 'pending_owl'::text) AND (berufenet_id IS NULL));


--
-- Name: idx_postings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_status ON public.postings USING btree (posting_status, last_seen_at);


--
-- Name: idx_pp_profile_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_pp_profile_id ON public.profile_preferences USING btree (profile_id);


--
-- Name: idx_pp_profile_sentiment; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_pp_profile_sentiment ON public.profile_preferences USING btree (profile_id, sentiment);


--
-- Name: idx_pp_profile_topic_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_pp_profile_topic_unique ON public.profile_preferences USING btree (profile_id, topic_type, topic_value);


--
-- Name: idx_ppm_first_viewed; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_ppm_first_viewed ON public.profile_posting_matches USING btree (profile_id, first_viewed_at) WHERE (first_viewed_at IS NOT NULL);


--
-- Name: idx_prof_sim_a; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_prof_sim_a ON public.profession_similarity USING btree (berufenet_id_a, combined_score DESC);


--
-- Name: idx_prof_sim_b; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_prof_sim_b ON public.profession_similarity USING btree (berufenet_id_b);


--
-- Name: idx_profile_translations_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_translations_profile ON public.profile_translations USING btree (profile_id);


--
-- Name: idx_profiles_availability; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_availability ON public.profiles USING btree (availability_status);


--
-- Name: idx_profiles_email; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_email ON public.profiles USING btree (email);


--
-- Name: idx_profiles_email_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_profiles_email_unique ON public.profiles USING btree (email) WHERE (email IS NOT NULL);


--
-- Name: idx_profiles_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_enabled ON public.profiles USING btree (enabled);


--
-- Name: idx_profiles_experience_level; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_experience_level ON public.profiles USING btree (experience_level);


--
-- Name: idx_profiles_implied_skills; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_implied_skills ON public.profiles USING gin (implied_skills jsonb_path_ops) WHERE (implied_skills IS NOT NULL);


--
-- Name: idx_profiles_search_vector; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_search_vector ON public.profiles USING gin (search_vector);


--
-- Name: idx_profiles_skill_keywords; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_skill_keywords ON public.profiles USING gin (skill_keywords);


--
-- Name: idx_profiles_updated; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_updated ON public.profiles USING btree (updated_at);


--
-- Name: idx_profiles_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profiles_user ON public.profiles USING btree (user_id);


--
-- Name: idx_push_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_push_user ON public.push_subscriptions USING btree (user_id);


--
-- Name: idx_pwht_work_history; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_pwht_work_history ON public.profile_work_history_translations USING btree (work_history_id);


--
-- Name: idx_task_routes_from; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_task_routes_from ON public.task_routes USING btree (from_instruction_id) WHERE (enabled = true);


--
-- Name: idx_tickets_task_type_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_tickets_task_type_status ON public.tickets USING btree (task_type_id, status) WHERE (task_type_id IS NOT NULL);


--
-- Name: idx_tickets_task_type_subject; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_tickets_task_type_subject ON public.tickets USING btree (task_type_id, subject_id, subject_type, status) WHERE (task_type_id IS NOT NULL);


--
-- Name: idx_upi_user_favorited; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_upi_user_favorited ON public.user_posting_interactions USING btree (user_id, is_favorited) WHERE (is_favorited = true);


--
-- Name: idx_upi_user_interested; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_upi_user_interested ON public.user_posting_interactions USING btree (user_id, is_interested) WHERE (is_interested = true);


--
-- Name: idx_upi_user_state; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_upi_user_state ON public.user_posting_interactions USING btree (user_id, state);


--
-- Name: idx_usage_events_context; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_events_context ON public.usage_events USING gin (context jsonb_path_ops);


--
-- Name: idx_usage_events_unbilled; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_events_unbilled ON public.usage_events USING btree (user_id) WHERE (billed_at IS NULL);


--
-- Name: idx_usage_events_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_events_user_created ON public.usage_events USING btree (user_id, created_at DESC);


--
-- Name: idx_users_notification_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_notification_email ON public.users USING btree (notification_email) WHERE (notification_email IS NOT NULL);


--
-- Name: idx_users_stripe_customer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_stripe_customer ON public.users USING btree (stripe_customer_id) WHERE (stripe_customer_id IS NOT NULL);


--
-- Name: idx_users_yogi_name_lower; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_users_yogi_name_lower ON public.users USING btree (lower(yogi_name)) WHERE (yogi_name IS NOT NULL);


--
-- Name: idx_work_history_current; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_current ON public.profile_work_history USING btree (is_current);


--
-- Name: idx_work_history_dates; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_dates ON public.profile_work_history USING btree (start_date, end_date);


--
-- Name: idx_work_history_entry_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_entry_type ON public.profile_work_history USING btree (entry_type);


--
-- Name: idx_work_history_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_profile ON public.profile_work_history USING btree (profile_id);


--
-- Name: idx_yogi_connections_a; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_connections_a ON public.yogi_connections USING btree (yogi_a_id);


--
-- Name: idx_yogi_connections_b; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_connections_b ON public.yogi_connections USING btree (yogi_b_id);


--
-- Name: idx_yogi_connections_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_connections_posting ON public.yogi_connections USING btree (posting_id);


--
-- Name: idx_yogi_events_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_events_type ON public.yogi_events USING btree (event_type, created_at DESC);


--
-- Name: idx_yogi_events_user_time; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_events_user_time ON public.yogi_events USING btree (user_id, created_at DESC);


--
-- Name: idx_yogi_messages_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_messages_posting ON public.yogi_messages USING btree (posting_id) WHERE (posting_id IS NOT NULL);


--
-- Name: idx_yogi_messages_user_unread; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_messages_user_unread ON public.yogi_messages USING btree (user_id, created_at DESC) WHERE (read_at IS NULL);


--
-- Name: idx_yogi_messages_y2y; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_yogi_messages_y2y ON public.yogi_messages USING btree (sender_user_id, user_id) WHERE (sender_type = 'yogi'::text);


--
-- Name: idx_ype_profile_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_ype_profile_created ON public.yogi_posting_events USING btree (profile_id, created_at DESC);


--
-- Name: idx_ype_profile_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_ype_profile_type ON public.yogi_posting_events USING btree (profile_id, event_type);


--
-- Name: yogi_audit_log yogi_audit_log_no_delete; Type: RULE; Schema: public; Owner: base_admin
--

CREATE RULE yogi_audit_log_no_delete AS
    ON DELETE TO public.yogi_audit_log DO INSTEAD NOTHING;


--
-- Name: yogi_audit_log yogi_audit_log_no_update; Type: RULE; Schema: public; Owner: base_admin
--

CREATE RULE yogi_audit_log_no_update AS
    ON UPDATE TO public.yogi_audit_log DO INSTEAD NOTHING;


--
-- Name: tickets interactions_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER interactions_updated_at_trigger BEFORE UPDATE ON public.tickets FOR EACH ROW EXECUTE FUNCTION public.update_interactions_updated_at();


--
-- Name: profiles profile_search_vector_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profile_search_vector();


--
-- Name: profiles profiles_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profiles_updated_at_trigger BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: actors set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.actors FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: postings set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.postings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: owl_names trg_prevent_berufenet_overwrite; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_prevent_berufenet_overwrite BEFORE INSERT OR UPDATE ON public.owl_names FOR EACH ROW EXECUTE FUNCTION public.prevent_owl_names_berufenet_overwrite();


--
-- Name: task_types trg_task_types_update; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_task_types_update INSTEAD OF UPDATE ON public.task_types FOR EACH ROW EXECUTE FUNCTION public.task_types_update_trigger();


--
-- Name: tickets trg_update_batch_counts; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_update_batch_counts AFTER UPDATE ON public.tickets FOR EACH ROW EXECUTE FUNCTION public.update_batch_counts();


--
-- Name: actors trg_warn_missing_script_code; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_warn_missing_script_code BEFORE INSERT OR UPDATE ON public.actors FOR EACH ROW EXECUTE FUNCTION public.warn_missing_script_code();


--
-- Name: TRIGGER trg_warn_missing_script_code ON actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TRIGGER trg_warn_missing_script_code ON public.actors IS 'Warn when script actors have NULL script_code';


--
-- Name: profile_work_history work_history_duration_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_duration_trigger BEFORE INSERT OR UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.calculate_work_duration();


--
-- Name: profile_work_history work_history_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_updated_at_trigger BEFORE UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: actors actors_parent_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_parent_actor_id_fkey FOREIGN KEY (parent_actor_id) REFERENCES public.actors(actor_id) ON DELETE SET NULL;


--
-- Name: adele_sessions adele_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.adele_sessions
    ADD CONSTRAINT adele_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: arcade_scores arcade_scores_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.arcade_scores
    ADD CONSTRAINT arcade_scores_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: berufenet_synonyms berufenet_synonyms_berufenet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.berufenet_synonyms
    ADD CONSTRAINT berufenet_synonyms_berufenet_id_fkey FOREIGN KEY (berufenet_id) REFERENCES public.berufenet(berufenet_id);


--
-- Name: company_alias_variants company_alias_variants_alias_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_alias_variants
    ADD CONSTRAINT company_alias_variants_alias_id_fkey FOREIGN KEY (alias_id) REFERENCES public.company_aliases(alias_id) ON DELETE CASCADE;


--
-- Name: owl entities_merged_into_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl
    ADD CONSTRAINT entities_merged_into_entity_id_fkey FOREIGN KEY (merged_into_entity_id) REFERENCES public.owl(owl_id);


--
-- Name: feedback feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: tickets interactions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT interactions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON DELETE RESTRICT;


--
-- Name: tickets interactions_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT interactions_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(batch_id);


--
-- Name: mira_questions mira_questions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.mira_questions
    ADD CONSTRAINT mira_questions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: owl_names owl_names_owl_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_names
    ADD CONSTRAINT owl_names_owl_id_fkey FOREIGN KEY (owl_id) REFERENCES public.owl(owl_id) ON DELETE CASCADE;


--
-- Name: owl_pending owl_pending_resolved_owl_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_pending
    ADD CONSTRAINT owl_pending_resolved_owl_id_fkey FOREIGN KEY (resolved_owl_id) REFERENCES public.owl(owl_id);


--
-- Name: owl_relationships owl_relationships_owl_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_relationships
    ADD CONSTRAINT owl_relationships_owl_id_fkey FOREIGN KEY (owl_id) REFERENCES public.owl(owl_id) ON DELETE CASCADE;


--
-- Name: owl_relationships owl_relationships_related_owl_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.owl_relationships
    ADD CONSTRAINT owl_relationships_related_owl_id_fkey FOREIGN KEY (related_owl_id) REFERENCES public.owl(owl_id) ON DELETE CASCADE;


--
-- Name: posting_interest posting_interest_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_interest
    ADD CONSTRAINT posting_interest_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: posting_interest posting_interest_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_interest
    ADD CONSTRAINT posting_interest_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: profession_similarity profession_similarity_berufenet_id_a_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profession_similarity
    ADD CONSTRAINT profession_similarity_berufenet_id_a_fkey FOREIGN KEY (berufenet_id_a) REFERENCES public.berufenet(berufenet_id);


--
-- Name: profession_similarity profession_similarity_berufenet_id_b_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profession_similarity
    ADD CONSTRAINT profession_similarity_berufenet_id_b_fkey FOREIGN KEY (berufenet_id_b) REFERENCES public.berufenet(berufenet_id);


--
-- Name: profile_posting_matches profile_posting_matches_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_posting_matches
    ADD CONSTRAINT profile_posting_matches_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: profile_posting_matches profile_posting_matches_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_posting_matches
    ADD CONSTRAINT profile_posting_matches_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id);


--
-- Name: profile_preferences profile_preferences_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_preferences
    ADD CONSTRAINT profile_preferences_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_preferences profile_preferences_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_preferences
    ADD CONSTRAINT profile_preferences_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.yogi_posting_events(event_id) ON DELETE SET NULL;


--
-- Name: profile_translations profile_translations_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_translations
    ADD CONSTRAINT profile_translations_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_work_history profile_work_history_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history
    ADD CONSTRAINT profile_work_history_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_work_history_translations profile_work_history_translations_work_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history_translations
    ADD CONSTRAINT profile_work_history_translations_work_history_id_fkey FOREIGN KEY (work_history_id) REFERENCES public.profile_work_history(work_history_id) ON DELETE CASCADE;


--
-- Name: push_subscriptions push_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.push_subscriptions
    ADD CONSTRAINT push_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: usage_events usage_events_event_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_event_type_fkey FOREIGN KEY (event_type) REFERENCES public.usage_event_prices(event_type);


--
-- Name: usage_events usage_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_posting_interactions user_posting_interactions_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_interactions
    ADD CONSTRAINT user_posting_interactions_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: user_posting_interactions user_posting_interactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_interactions
    ADD CONSTRAINT user_posting_interactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: yogi_connections yogi_connections_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections
    ADD CONSTRAINT yogi_connections_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: yogi_connections yogi_connections_yogi_a_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections
    ADD CONSTRAINT yogi_connections_yogi_a_id_fkey FOREIGN KEY (yogi_a_id) REFERENCES public.users(user_id);


--
-- Name: yogi_connections yogi_connections_yogi_b_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_connections
    ADD CONSTRAINT yogi_connections_yogi_b_id_fkey FOREIGN KEY (yogi_b_id) REFERENCES public.users(user_id);


--
-- Name: yogi_documents yogi_documents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_documents
    ADD CONSTRAINT yogi_documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: yogi_events yogi_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_events
    ADD CONSTRAINT yogi_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: yogi_messages yogi_messages_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_messages
    ADD CONSTRAINT yogi_messages_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: yogi_messages yogi_messages_sender_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_messages
    ADD CONSTRAINT yogi_messages_sender_user_id_fkey FOREIGN KEY (sender_user_id) REFERENCES public.users(user_id);


--
-- Name: yogi_messages yogi_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_messages
    ADD CONSTRAINT yogi_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: yogi_posting_events yogi_posting_events_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_posting_events
    ADD CONSTRAINT yogi_posting_events_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.profile_posting_matches(match_id) ON DELETE SET NULL;


--
-- Name: yogi_posting_events yogi_posting_events_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_posting_events
    ADD CONSTRAINT yogi_posting_events_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: yogi_posting_events yogi_posting_events_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.yogi_posting_events
    ADD CONSTRAINT yogi_posting_events_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: schema_change_trigger; Type: EVENT TRIGGER; Schema: -; Owner: base_admin
--

CREATE EVENT TRIGGER schema_change_trigger ON ddl_command_end
   EXECUTE FUNCTION public.log_ddl_changes();


ALTER EVENT TRIGGER schema_change_trigger OWNER TO base_admin;

--
-- PostgreSQL database dump complete
--

\unrestrict 2gt57p7zmdyrolFnoOeh6ZVsqJ1zk4IjuEXNf3mhIwfcaBfUr2fcgx8qEcNVlm0

