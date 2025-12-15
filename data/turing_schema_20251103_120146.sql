--
-- PostgreSQL database dump
--

\restrict XLaJ0soL4JasM36RPtVlmt62ri5fgz9aTgGkvFzItp2g3Wm9RrgMtCFYjCSOs7o

-- Dumped from database version 14.19 (Ubuntu 14.19-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.19 (Ubuntu 14.19-0ubuntu0.22.04.1)

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
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


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
    INSERT INTO recipes_history (
        recipe_id, recipe_name, recipe_description, recipe_version,
        max_total_session_runs, enabled, review_notes,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.recipe_id, OLD.recipe_name, OLD.recipe_description, OLD.recipe_version,
        OLD.max_total_session_runs, OLD.enabled, OLD.review_notes,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_workflows() OWNER TO base_admin;

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
            times_checked = times_checked + 1,
            posting_status = 'active'
        WHERE posting_id = p_posting_id;
    ELSE
        -- No longer on source site
        UPDATE postings
        SET 
            posting_status = 'filled',
            status_changed_at = CURRENT_TIMESTAMP,
            status_reason = 'No longer found on source site during re-check',
            times_checked = times_checked + 1
        WHERE posting_id = p_posting_id
        AND posting_status = 'active';
    END IF;
END;
$$;


ALTER FUNCTION public.update_posting_seen(p_posting_id integer, p_still_active boolean) OWNER TO base_admin;

--
-- Name: FUNCTION update_posting_seen(p_posting_id integer, p_still_active boolean); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.update_posting_seen(p_posting_id integer, p_still_active boolean) IS 'Update posting status when re-checked (still active or disappeared)';


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
-- Name: actors_actor_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.actors_actor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.actors_actor_id_seq OWNER TO base_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

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
    url text NOT NULL,
    user_id integer,
    script_code text,
    script_language text,
    script_version integer DEFAULT 1,
    CONSTRAINT actors_actor_type_check CHECK ((actor_type = ANY (ARRAY['human'::text, 'ai_model'::text, 'script'::text, 'machine_actor'::text]))),
    CONSTRAINT actors_execution_type_check CHECK ((execution_type = ANY (ARRAY['ollama_api'::text, 'http_api'::text, 'python_script'::text, 'bash_script'::text, 'human_input'::text])))
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

COMMENT ON COLUMN public.actors.execution_config IS 'JSON configuration for execution:
   - timeout_seconds: max execution time
   - temperature: for AI models
   - retry_count: for network calls
   - notification_email: for human actors
   - default_args: script arguments
   - max_depth, branches_per_level: for Gopher';


--
-- Name: COLUMN actors.execution_path; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.execution_path IS 'DEPRECATED: File path to script (e.g., scripts/my_script.py). Kept for development convenience but script_code is source of truth for production. Runner checks script_code first, falls back to this if script_code is NULL.';


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
-- Name: active_actors; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.active_actors AS
 SELECT actors.actor_name AS actor_id,
    actors.actor_type,
    actors.execution_type,
    actors.execution_path,
    actors.url,
    actors.execution_config,
        CASE
            WHEN (actors.execution_type = 'ollama_api'::text) THEN (('AI Model ('::text || actors.execution_path) || ')'::text)
            WHEN (actors.execution_type = 'http_api'::text) THEN (('HTTP Service ('::text || actors.execution_path) || ')'::text)
            WHEN (actors.execution_type = 'python_script'::text) THEN (('Python Script ('::text || split_part(actors.execution_path, '/'::text, '-1'::integer)) || ')'::text)
            WHEN (actors.execution_type = 'bash_script'::text) THEN (('Bash Script ('::text || split_part(actors.execution_path, '/'::text, '-1'::integer)) || ')'::text)
            WHEN (actors.execution_type = 'human_input'::text) THEN 'Human Actor'::text
            ELSE 'Unknown'::text
        END AS display_name,
    actors.enabled
   FROM public.actors
  WHERE (actors.enabled = true)
  ORDER BY actors.actor_type, actors.actor_name;


ALTER TABLE public.active_actors OWNER TO base_admin;

--
-- Name: VIEW active_actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.active_actors IS 'All enabled actors with friendly display names. Use this for UI dropdowns.';


--
-- Name: batches; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.batches (
    batch_id integer NOT NULL,
    batch_name text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    batch_type text DEFAULT 'manual'::text,
    description text,
    tags jsonb DEFAULT '{}'::jsonb,
    enabled boolean DEFAULT true,
    CONSTRAINT batches_batch_type_check CHECK ((batch_type = ANY (ARRAY['test'::text, 'production'::text, 'experiment'::text, 'manual'::text, 'automated'::text])))
);


ALTER TABLE public.batches OWNER TO base_admin;

--
-- Name: TABLE batches; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.batches IS 'Groups multiple recipe executions for statistical analysis. Enables "run 5 times" scenarios for reliability testing.';


--
-- Name: COLUMN batches.batch_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.batches.batch_type IS 'Type of batch execution:
   - test: Testing recipe behavior with variations
   - production: Real job processing
   - experiment: R&D and parameter tuning
   - manual: User-initiated runs
   - automated: Scheduled/triggered runs';


--
-- Name: COLUMN batches.description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.batches.description IS 'Human-readable description of batch purpose and context.';


--
-- Name: COLUMN batches.tags; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.batches.tags IS 'Flexible JSON tags for categorization. Examples:
   {"environment": "staging", "recipe_id": 1120}
   {"purpose": "regression_test", "jira_ticket": "BY-123"}';


--
-- Name: batches_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.batches_batch_id_seq
    AS integer
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
-- Name: validated_prompts_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.validated_prompts_history (
    history_id integer NOT NULL,
    validated_prompt_code text NOT NULL,
    facet_name text NOT NULL,
    capability_description text,
    prompt text,
    response text,
    review_notes text,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.validated_prompts_history OWNER TO base_admin;

--
-- Name: TABLE validated_prompts_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.validated_prompts_history IS 'Audit trail of all changes to canonicals table. Triggered automatically on UPDATE/DELETE via archive_canonicals() function. Preserves old values before modification.';


--
-- Name: canonicals_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.canonicals_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.canonicals_history_history_id_seq OWNER TO base_admin;

--
-- Name: canonicals_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.canonicals_history_history_id_seq OWNED BY public.validated_prompts_history.history_id;


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
-- Name: capabilities; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.capabilities (
    capability_id integer DEFAULT nextval('public.capabilities_capability_id_seq'::regclass) NOT NULL,
    capability_name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    enabled boolean DEFAULT true,
    parent_capability_name text,
    parent_id integer,
    remarks text,
    short_description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.capabilities OWNER TO base_admin;

--
-- Name: TABLE capabilities; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.capabilities IS 'Hierarchical taxonomy of cognitive/computational capabilities (74 entries).
HISTORICAL NOTE: Previously named "facets" - see rfa_latest/rfa_facets.md for the conceptual foundation.

PURPOSE: Theoretical framework for decomposing intelligence into measurable primitives.
- Classify what operations DO (reason, extract, follow rules, etc.)
- Map recipes to required cognitive capabilities
- Track LLM performance across fundamental ability categories
- Enable systematic capability-based recipe discovery

STRUCTURE: 9 root capabilities (single letters) + 65 child capabilities (2+ chars)
ROOT CAPABILITIES:
  c - Clean (normalize, filter, extract, audit)
  f - Fulfill (execute prompts, follow rules exactly)
  g - Group (categorize, cluster)
  k - Know (factual knowledge, recall)
  l - Learn (adapt, improve)
  m - Memory (context retention)
  o - Output (format, structure results)
  p - Plan (strategize, sequence)
  r - Reason (logic, inference)

DESIGN PRINCIPLE: Start from theoretical clarity - this is the periodic table of AI capabilities.
Links to canonicals table for standard test cases per capability.

Pattern: capability_id (INTEGER PK) + capability_name (TEXT UNIQUE).
Self-referencing: parent_id → capability_id.
Standardized 2025-10-30. Renamed from facets 2025-10-31.';


--
-- Name: COLUMN capabilities.capability_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.capability_id IS 'Surrogate key - stable integer identifier for foreign key joins.
Used by canonicals table to link test cases to capabilities.
Historical: previously facet_id';


--
-- Name: COLUMN capabilities.capability_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.capability_name IS 'Unique capability identifier (natural key).
Examples: c, r, ce_char_extract, ff_exact_format_brackets, dynatax_skills
Naming: Root = 1 char, child = 2+ chars (parent prefix + descriptor)
Historical: previously facet_name';


--
-- Name: COLUMN capabilities.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.enabled IS 'Active flag - FALSE to disable capability from recipes/testing without deletion.
All 74 capabilities currently enabled (TRUE).';


--
-- Name: COLUMN capabilities.parent_capability_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.parent_capability_name IS 'Parent capability for hierarchical capability organization.
NULL for root capabilities (c, f, g, k, l, m, o, p, r).
Child capabilities inherit and specialize parent capabilities.
Historical: previously parent_facet_name';


--
-- Name: COLUMN capabilities.parent_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.parent_id IS 'Self-referencing FK to parent capability (NULL for root capabilities).
Enables hierarchical queries and capability inheritance tracking.';


--
-- Name: COLUMN capabilities.remarks; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.remarks IS 'Additional notes, usage patterns, or design rationale for this capability.';


--
-- Name: COLUMN capabilities.short_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.capabilities.short_description IS 'Human-readable description of the cognitive capability.
Examples: "Clean", "Reason", "Extract characters / count target letter"';


--
-- Name: capabilities_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.capabilities_history (
    history_id integer NOT NULL,
    capability_id text NOT NULL,
    parent_id text,
    short_description text,
    remarks text,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.capabilities_history OWNER TO base_admin;

--
-- Name: TABLE capabilities_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.capabilities_history IS 'Archive of all changes to capabilities table.
Historical: previously facets_history (renamed 2025-10-31).
See rfa_latest/rfa_facets.md for conceptual foundation.';


--
-- Name: capabilities_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.capabilities_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.capabilities_history_history_id_seq OWNER TO base_admin;

--
-- Name: capabilities_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.capabilities_history_history_id_seq OWNED BY public.capabilities_history.history_id;


--
-- Name: conversation_dialogue; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.conversation_dialogue (
    dialogue_step_id integer NOT NULL,
    dialogue_step_name text NOT NULL,
    conversation_id integer NOT NULL,
    actor_id integer NOT NULL,
    actor_role text NOT NULL,
    execution_order integer NOT NULL,
    reads_from_step_ids integer[],
    prompt_template text NOT NULL,
    timeout_seconds integer DEFAULT 300,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT conversation_dialogue_execution_order_check CHECK ((execution_order > 0))
);


ALTER TABLE public.conversation_dialogue OWNER TO base_admin;

--
-- Name: TABLE conversation_dialogue; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.conversation_dialogue IS 'Orchestrates multi-actor dialogues with scripted, deterministic turn-taking.
Each row defines one actor''s turn: who speaks, when, what they see, what they say.
Actors speak in execution_order sequence. No chaos, no snowballing - controlled dialogue.

Example: CV Review
  Step 1: career_coach reads CV → suggests improvements
  Step 2: industry_expert reads CV + step_1 → validates suggestions  
  Step 3: writing_expert reads all → polishes language
  Step 4: synthesizer reads all → generates final output

Example: Novel Scene (Mysti''s use case)
  Step 1: history_expert analyzes scene historically
  Step 2: magic_specialist reads step_1 → adds magic system constraints
  Step 3: psychologist reads step_1,2 → analyzes character psychology
  Step 4: synthesizer reads all → creates coherent scene';


--
-- Name: COLUMN conversation_dialogue.actor_role; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_dialogue.actor_role IS 'Semantic role of this actor in the dialogue: generator, critic, reviewer, validator, 
synthesizer, historian, psychologist, etc. Helps humans understand dialogue structure.';


--
-- Name: COLUMN conversation_dialogue.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_dialogue.execution_order IS 'Deterministic turn order. Actor at order=1 speaks first, order=2 second, etc.
No moderator needed - just follow the script.';


--
-- Name: COLUMN conversation_dialogue.reads_from_step_ids; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_dialogue.reads_from_step_ids IS 'Array of dialogue_step_ids this actor can see/read from. NULL = reads only conversation input.
Example: ARRAY[1,2] means this actor sees outputs from steps 1 and 2.
Use in prompt_template as {dialogue_step_1_output}, {dialogue_step_2_output}, etc.';


--
-- Name: COLUMN conversation_dialogue.prompt_template; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_dialogue.prompt_template IS 'Prompt template with placeholders:
- {dialogue_step_N_output} - Output from dialogue step N
- {test_case_data.param_1} - Input from test case
- Standard placeholders work too
Example: "Review this code: {dialogue_step_1_output}. Context: {test_case_data.param_1}"';


--
-- Name: conversation_dialogue_dialogue_step_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.conversation_dialogue_dialogue_step_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.conversation_dialogue_dialogue_step_id_seq OWNER TO base_admin;

--
-- Name: conversation_dialogue_dialogue_step_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.conversation_dialogue_dialogue_step_id_seq OWNED BY public.conversation_dialogue.dialogue_step_id;


--
-- Name: conversation_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.conversation_runs (
    conversation_run_id integer NOT NULL,
    conversation_run_name text NOT NULL,
    conversation_id integer NOT NULL,
    workflow_step_id integer NOT NULL,
    execution_order integer NOT NULL,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    status text DEFAULT 'PENDING'::text,
    llm_conversation_id text,
    quality_score text,
    validation_status text,
    error_details text,
    run_id integer NOT NULL,
    run_type text NOT NULL,
    dialogue_round integer DEFAULT 1,
    active_actor_id integer,
    CONSTRAINT conversation_runs_quality_score_check CHECK ((quality_score = ANY (ARRAY['A'::text, 'B'::text, 'C'::text, 'D'::text, 'F'::text, NULL::text]))),
    CONSTRAINT conversation_runs_run_type_check CHECK ((run_type = ANY (ARRAY['testing'::text, 'production'::text]))),
    CONSTRAINT conversation_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'TIMEOUT'::text, 'ERROR'::text]))),
    CONSTRAINT conversation_runs_validation_status_check CHECK ((validation_status = ANY (ARRAY['PASS'::text, 'FAIL'::text, NULL::text])))
);


ALTER TABLE public.conversation_runs OWNER TO base_admin;

--
-- Name: TABLE conversation_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.conversation_runs IS 'Execution instances of conversations within workflow steps. Each conversation_run tracks when and how a conversation was executed, maintaining output history for all instructions. Primary actors have access to ALL previous instruction outputs, enabling multi-step reasoning chains and data transformation pipelines. Execution flow: workflow_run → conversation_runs (ordered by execution_order) → instruction_runs (sequential). Run types: testing (uses test_cases) or production (uses real job postings).';


--
-- Name: COLUMN conversation_runs.conversation_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.conversation_run_id IS 'Unique identifier for this conversation execution instance';


--
-- Name: COLUMN conversation_runs.conversation_run_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.conversation_run_name IS 'Human-readable name for this conversation run';


--
-- Name: COLUMN conversation_runs.conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.conversation_id IS 'Foreign key to conversations table - which conversation was executed';


--
-- Name: COLUMN conversation_runs.workflow_step_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.workflow_step_id IS 'Foreign key to workflow_steps table - which workflow step this execution belongs to';


--
-- Name: COLUMN conversation_runs.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.execution_order IS 'Sequential order of this conversation run within the workflow step';


--
-- Name: COLUMN conversation_runs.started_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.started_at IS 'Timestamp when this conversation run started';


--
-- Name: COLUMN conversation_runs.completed_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.completed_at IS 'Timestamp when this conversation run completed (NULL if still running)';


--
-- Name: COLUMN conversation_runs.status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.status IS 'Execution status: PENDING, RUNNING, SUCCESS, FAILED, TIMEOUT, or ERROR';


--
-- Name: COLUMN conversation_runs.llm_conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.llm_conversation_id IS 'External LLM conversation identifier for tracking API calls';


--
-- Name: COLUMN conversation_runs.quality_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.quality_score IS 'Quality grade for this execution: A, B, C, D, or F';


--
-- Name: COLUMN conversation_runs.validation_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.validation_status IS 'Validation result: PASS or FAIL';


--
-- Name: COLUMN conversation_runs.error_details; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.error_details IS 'Error message or stack trace if status is FAILED or ERROR';


--
-- Name: COLUMN conversation_runs.run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.run_id IS 'Identifier for the parent run (workflow_run_id or production_run_id)';


--
-- Name: COLUMN conversation_runs.run_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.run_type IS 'Type of run: testing (test_cases) or production (real data)';


--
-- Name: COLUMN conversation_runs.dialogue_round; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.dialogue_round IS 'For multi-actor dialogues: which round of discussion is this (1, 2, 3...).';


--
-- Name: COLUMN conversation_runs.active_actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversation_runs.active_actor_id IS 'For multi-actor dialogues: which actor is currently speaking in this conversation run.';


--
-- Name: conversation_runs_conversation_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.conversation_runs ALTER COLUMN conversation_run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.conversation_runs_conversation_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.conversations (
    conversation_id integer NOT NULL,
    conversation_name text NOT NULL,
    conversation_description text,
    validated_prompt_id integer,
    actor_id integer NOT NULL,
    context_strategy text DEFAULT 'isolated'::text,
    max_instruction_runs integer DEFAULT 50,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    canonical_name text,
    conversation_type text DEFAULT 'single_actor'::text,
    CONSTRAINT conversations_context_strategy_check CHECK ((context_strategy = ANY (ARRAY['isolated'::text, 'inherit_previous'::text, 'shared_conversation'::text]))),
    CONSTRAINT conversations_conversation_type_check CHECK ((conversation_type = ANY (ARRAY['single_actor'::text, 'multi_turn'::text, 'multi_actor_sequential'::text, 'multi_actor_dialogue'::text])))
);


ALTER TABLE public.conversations OWNER TO base_admin;

--
-- Name: TABLE conversations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.conversations IS 'Conversational contexts for stateful interactions (569 entries).
A conversation maintains continuity between interactions (like our chat).
Each conversation has an actor and can reference a validated prompt template.
Conversations support context strategies (isolated, inherit_previous, shared_conversation).
Actors can delegate instructions to helper actors within a conversation.
Renamed from sessions 2025-10-31 for clarity.
Pattern: conversation_id (INTEGER PK) + conversation_name (TEXT).';


--
-- Name: COLUMN conversations.conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.conversation_id IS 'Primary key - unique identifier for this conversation';


--
-- Name: COLUMN conversations.conversation_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.conversation_name IS 'Name/label for this conversation (e.g., "joke_generation", "skill_extraction")';


--
-- Name: COLUMN conversations.conversation_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.conversation_description IS 'Description of what this conversation does or its purpose';


--
-- Name: COLUMN conversations.validated_prompt_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.validated_prompt_id IS 'Optional FK to validated_prompts - template prompt used in this conversation';


--
-- Name: COLUMN conversations.actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.actor_id IS 'FK to actors - which actor (AI model, human, script) handles this conversation';


--
-- Name: COLUMN conversations.context_strategy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.context_strategy IS 'How context flows: isolated (fresh), inherit_previous (sequential), shared_conversation (persistent)';


--
-- Name: COLUMN conversations.max_instruction_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.max_instruction_runs IS 'Maximum number of instruction executions allowed in this conversation (safety limit)';


--
-- Name: COLUMN conversations.canonical_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.canonical_name IS 'Legacy column - text reference to validated prompt name (use validated_prompt_id instead)';


--
-- Name: COLUMN conversations.conversation_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.conversations.conversation_type IS 'Type of conversation execution:
- single_actor: One AI executes all instructions (most common)
- multi_turn: One AI, multiple instructions in sequence (current behavior with multiple instructions)
- multi_actor_sequential: Multiple AIs, each assigned to specific instructions
- multi_actor_dialogue: Multiple AIs engaging in structured dialogue/debate';


--
-- Name: conversations_conversation_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.conversations ALTER COLUMN conversation_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.conversations_conversation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conversations_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.conversations_history (
    history_id integer NOT NULL,
    conversation_id integer NOT NULL,
    canonical_code text NOT NULL,
    conversation_name text,
    conversation_description text,
    actor_id text,
    context_strategy text,
    max_instruction_runs integer,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.conversations_history OWNER TO base_admin;

--
-- Name: TABLE conversations_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.conversations_history IS 'Audit trail of all changes to sessions table. Preserves session template changes, crucial for understanding why old recipe runs behaved differently.';


--
-- Name: dialogue_step_placeholders; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.dialogue_step_placeholders (
    dialogue_step_id integer NOT NULL,
    placeholder_id integer NOT NULL,
    is_required boolean DEFAULT false,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.dialogue_step_placeholders OWNER TO base_admin;

--
-- Name: TABLE dialogue_step_placeholders; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.dialogue_step_placeholders IS 'Links dialogue steps to their required/optional placeholders';


--
-- Name: llm_interactions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.llm_interactions (
    interaction_id integer NOT NULL,
    workflow_run_id integer NOT NULL,
    conversation_run_id integer NOT NULL,
    dialogue_step_run_id integer,
    actor_id integer NOT NULL,
    instruction_id integer,
    execution_order integer NOT NULL,
    prompt_sent text NOT NULL,
    response_received text,
    latency_ms integer,
    tokens_input integer,
    tokens_output integer,
    cost_usd numeric(10,6),
    status text DEFAULT 'PENDING'::text NOT NULL,
    error_message text,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    CONSTRAINT llm_interactions_cost_usd_check CHECK ((cost_usd >= (0)::numeric)),
    CONSTRAINT llm_interactions_execution_order_check CHECK ((execution_order > 0)),
    CONSTRAINT llm_interactions_latency_ms_check CHECK ((latency_ms >= 0)),
    CONSTRAINT llm_interactions_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'SUCCESS'::text, 'TIMEOUT'::text, 'ERROR'::text, 'RATE_LIMITED'::text, 'QUOTA_EXCEEDED'::text, 'INVALID_REQUEST'::text]))),
    CONSTRAINT llm_interactions_tokens_input_check CHECK ((tokens_input >= 0)),
    CONSTRAINT llm_interactions_tokens_output_check CHECK ((tokens_output >= 0))
);


ALTER TABLE public.llm_interactions OWNER TO base_admin;

--
-- Name: TABLE llm_interactions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.llm_interactions IS 'PRIMARY SOURCE OF TRUTH for all LLM interactions.
     Replaces legacy instruction_runs and dialogue_step_runs tables (dropped in migration 035).
     Use this table for all new queries and analytics.';


--
-- Name: COLUMN llm_interactions.interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.interaction_id IS 'Unique identifier for this LLM interaction';


--
-- Name: COLUMN llm_interactions.workflow_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.workflow_run_id IS 'Which workflow execution this belongs to';


--
-- Name: COLUMN llm_interactions.conversation_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.conversation_run_id IS 'Which conversation execution within the workflow';


--
-- Name: COLUMN llm_interactions.dialogue_step_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.dialogue_step_run_id IS 'Historical reference to dialogue_step_runs (table dropped in migration 035). 
     For multi-actor dialogues, this ID can be used to correlate with archived dialogue_step_runs data if needed.';


--
-- Name: COLUMN llm_interactions.instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.instruction_id IS 'For single-actor/multi-turn: which instruction template was used. NULL for multi-actor dialogues.';


--
-- Name: COLUMN llm_interactions.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.execution_order IS 'Order of execution within the conversation (1-based)';


--
-- Name: COLUMN llm_interactions.prompt_sent; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.prompt_sent IS 'The actual prompt sent to the LLM (after placeholder replacement)';


--
-- Name: COLUMN llm_interactions.response_received; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.response_received IS 'The response from the LLM';


--
-- Name: COLUMN llm_interactions.latency_ms; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.latency_ms IS 'Time taken for LLM to respond (milliseconds)';


--
-- Name: COLUMN llm_interactions.tokens_input; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.tokens_input IS 'Number of input tokens (if available from LLM API)';


--
-- Name: COLUMN llm_interactions.tokens_output; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.tokens_output IS 'Number of output tokens (if available from LLM API)';


--
-- Name: COLUMN llm_interactions.cost_usd; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.cost_usd IS 'Cost of this interaction in USD (if calculable)';


--
-- Name: COLUMN llm_interactions.status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.llm_interactions.status IS 'Execution status: SUCCESS, TIMEOUT, ERROR, etc.';


--
-- Name: dialogue_step_runs; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.dialogue_step_runs AS
 SELECT llm_interactions.dialogue_step_run_id,
    llm_interactions.conversation_run_id,
    NULL::integer AS dialogue_step_id,
    llm_interactions.actor_id,
    llm_interactions.execution_order,
    llm_interactions.prompt_sent AS prompt_rendered,
    llm_interactions.response_received,
    llm_interactions.latency_ms,
    llm_interactions.status,
    llm_interactions.completed_at
   FROM public.llm_interactions
  WHERE (llm_interactions.dialogue_step_run_id IS NOT NULL);


ALTER TABLE public.dialogue_step_runs OWNER TO base_admin;

--
-- Name: VIEW dialogue_step_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.dialogue_step_runs IS 'LEGACY VIEW - Compatibility layer for old queries. 
     Maps llm_interactions data to old dialogue_step_runs schema.
     DO NOT USE IN NEW CODE - Query llm_interactions directly instead.
     Note: dialogue_step_id is NULL as it is not tracked in llm_interactions.';


--
-- Name: human_tasks; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.human_tasks (
    task_id uuid DEFAULT gen_random_uuid() NOT NULL,
    actor_name text NOT NULL,
    session_run_id integer,
    instruction_run_id integer,
    prompt text NOT NULL,
    response text,
    status text DEFAULT 'PENDING'::text NOT NULL,
    priority integer DEFAULT 5,
    created_at timestamp without time zone DEFAULT now(),
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    timeout_at timestamp without time zone,
    actor_id integer NOT NULL,
    CONSTRAINT human_tasks_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'IN_PROGRESS'::text, 'COMPLETED'::text, 'CANCELLED'::text])))
);


ALTER TABLE public.human_tasks OWNER TO base_admin;

--
-- Name: TABLE human_tasks; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.human_tasks IS 'Queue of tasks awaiting human input. When execution_type=human_input, 
   system creates entry here and waits for human to provide response.';


--
-- Name: instruction_step_executions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instruction_step_executions (
    execution_id integer NOT NULL,
    instruction_run_id integer NOT NULL,
    instruction_step_id integer NOT NULL,
    condition_matched text NOT NULL,
    iteration_count integer DEFAULT 1,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.instruction_step_executions OWNER TO base_admin;

--
-- Name: TABLE instruction_step_executions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instruction_step_executions IS 'Audit log of branch decisions. Records which branch was taken, what output pattern matched, and iteration count for loop tracking.';


--
-- Name: COLUMN instruction_step_executions.condition_matched; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_step_executions.condition_matched IS 'The actual output text that matched the branch_condition regex. Useful for debugging pattern matching.';


--
-- Name: COLUMN instruction_step_executions.iteration_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_step_executions.iteration_count IS 'How many times this specific branch has been taken in the current session_run. Used to enforce max_iterations limit.';


--
-- Name: instruction_branch_executions_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.instruction_branch_executions_execution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instruction_branch_executions_execution_id_seq OWNER TO base_admin;

--
-- Name: instruction_branch_executions_execution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.instruction_branch_executions_execution_id_seq OWNED BY public.instruction_step_executions.execution_id;


--
-- Name: instruction_runs; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.instruction_runs AS
 SELECT llm_interactions.interaction_id AS instruction_run_id,
    llm_interactions.conversation_run_id AS session_run_id,
    llm_interactions.instruction_id,
    llm_interactions.execution_order AS step_number,
    llm_interactions.prompt_sent AS prompt_rendered,
    llm_interactions.response_received,
    llm_interactions.latency_ms,
    llm_interactions.error_message AS error_details,
    llm_interactions.status,
    llm_interactions.completed_at AS created_at
   FROM public.llm_interactions
  WHERE (llm_interactions.instruction_id IS NOT NULL);


ALTER TABLE public.instruction_runs OWNER TO base_admin;

--
-- Name: VIEW instruction_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.instruction_runs IS 'LEGACY VIEW - Compatibility layer for old queries. 
     Maps llm_interactions data to old instruction_runs schema.
     DO NOT USE IN NEW CODE - Query llm_interactions directly instead.';


--
-- Name: instruction_steps; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instruction_steps (
    instruction_step_id integer NOT NULL,
    instruction_step_name text NOT NULL,
    instruction_id integer NOT NULL,
    branch_condition text NOT NULL,
    next_instruction_id integer,
    next_conversation_id integer,
    max_iterations integer,
    branch_priority integer DEFAULT 5,
    branch_description text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_branch_target CHECK ((((next_instruction_id IS NOT NULL) AND (next_conversation_id IS NULL)) OR ((next_instruction_id IS NULL) AND (next_conversation_id IS NOT NULL)) OR ((next_instruction_id IS NULL) AND (next_conversation_id IS NULL)))),
    CONSTRAINT chk_positive_iterations CHECK (((max_iterations IS NULL) OR (max_iterations > 0)))
);


ALTER TABLE public.instruction_steps OWNER TO base_admin;

--
-- Name: TABLE instruction_steps; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instruction_steps IS 'Defines conditional control flow between instructions within conversations.
Each step evaluates a branch_condition to determine which instruction or conversation executes next.
Key to Turing completeness: enables if/else/switch logic, loops (max_iterations), and state transitions.

Hierarchy:
- workflows orchestrate conversations (via conversation_steps)
- conversations orchestrate instructions (via instruction_steps)
- instructions execute tasks (via actors)

Branching Logic (Complex):
- branch_condition: expression to evaluate (e.g., "[PASS]", "[FAIL]", "[SCORE > 80]")
- branch_priority: evaluation order (DESC) - higher priority evaluated first
- next_instruction_id: continue within same conversation
- next_conversation_id: jump to different conversation
- max_iterations: enable loops (NULL = no looping)

Unlike conversation_steps (simple success/fail), instruction_steps support complex conditional logic
because instructions may have nuanced outcomes requiring sophisticated routing decisions.

Evaluation: Ordered by branch_priority DESC → first matching branch_condition wins.

Formerly: instruction_branches → transitions → instruction_steps (migrations 019, 025).';


--
-- Name: COLUMN instruction_steps.instruction_step_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.instruction_step_id IS 'Unique identifier for this instruction step (formerly transition_id)';


--
-- Name: COLUMN instruction_steps.instruction_step_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.instruction_step_name IS 'Human-readable name for this instruction step (formerly transition_name)';


--
-- Name: COLUMN instruction_steps.instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.instruction_id IS 'Foreign key to instructions table - the instruction whose output triggers this conditional routing';


--
-- Name: COLUMN instruction_steps.branch_condition; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.branch_condition IS 'Expression to evaluate for this branch (e.g., "[PASS]", "[FAIL]", "[SCORE > 80]")';


--
-- Name: COLUMN instruction_steps.next_instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.next_instruction_id IS 'Foreign key to instructions table - next instruction to execute if condition matches (within same conversation)';


--
-- Name: COLUMN instruction_steps.next_conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.next_conversation_id IS 'Foreign key to conversations table - next conversation to execute if condition matches (jump to different conversation)';


--
-- Name: COLUMN instruction_steps.max_iterations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.max_iterations IS 'Maximum loop iterations if this creates a cycle (NULL = no looping, >0 = max iterations)';


--
-- Name: COLUMN instruction_steps.branch_priority; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.branch_priority IS 'Evaluation priority (DESC order) - higher values evaluated first. Default: 5';


--
-- Name: COLUMN instruction_steps.branch_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.branch_description IS 'Human-readable explanation of what this branch does and when it fires';


--
-- Name: COLUMN instruction_steps.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.enabled IS 'Whether this instruction step is active (true) or disabled (false)';


--
-- Name: COLUMN instruction_steps.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.created_at IS 'Timestamp when this instruction step was created';


--
-- Name: COLUMN instruction_steps.updated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_steps.updated_at IS 'Timestamp when this instruction step was last modified';


--
-- Name: instruction_steps_instruction_step_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.instruction_steps ALTER COLUMN instruction_step_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.instruction_steps_instruction_step_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: instructions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instructions (
    instruction_id integer NOT NULL,
    instruction_name text NOT NULL,
    conversation_id integer NOT NULL,
    step_number integer NOT NULL,
    step_description text,
    prompt_template text NOT NULL,
    timeout_seconds integer DEFAULT 300,
    expected_pattern text,
    validation_rules text,
    is_terminal boolean DEFAULT false,
    delegate_actor_id integer,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.instructions OWNER TO base_admin;

--
-- Name: TABLE instructions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instructions IS 'Individual execution steps within conversations (568 entries).
Each instruction is a single prompt/action that executes in sequence within a conversation.
Instructions can branch conditionally, delegate to helper actors, and mark completion points.
Together with instruction_branches, instructions form a Turing-complete execution model.
Updated 2025-10-31 to add instruction_name and remove redundant delegate_actor_name.
Pattern: instruction_id (INTEGER PK) + instruction_name (TEXT).';


--
-- Name: COLUMN instructions.instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.instruction_id IS 'Primary key - unique identifier for this instruction';


--
-- Name: COLUMN instructions.instruction_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.instruction_name IS 'Human-readable name for this instruction (e.g., "Generate joke", "Evaluate quality")';


--
-- Name: COLUMN instructions.conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.conversation_id IS 'FK to conversations - which conversation this instruction belongs to';


--
-- Name: COLUMN instructions.step_number; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.step_number IS 'Sequential step number within the conversation (1, 2, 3, ...)';


--
-- Name: COLUMN instructions.step_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.step_description IS 'Detailed description of what this instruction does';


--
-- Name: COLUMN instructions.prompt_template; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.prompt_template IS 'The prompt template to send to the actor (can include {variables})';


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
-- Name: instructions_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instructions_history (
    history_id integer NOT NULL,
    instruction_id integer NOT NULL,
    session_id integer NOT NULL,
    step_number integer,
    step_description text,
    prompt_template text,
    timeout_seconds integer,
    expected_pattern text,
    validation_rules text,
    is_terminal boolean,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text,
    instruction_name text
);


ALTER TABLE public.instructions_history OWNER TO base_admin;

--
-- Name: TABLE instructions_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instructions_history IS 'Audit trail of all changes to instructions table. Preserves instruction prompt changes, allowing rollback and analysis of how test definitions evolved.';


--
-- Name: instructions_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.instructions_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructions_history_history_id_seq OWNER TO base_admin;

--
-- Name: instructions_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.instructions_history_history_id_seq OWNED BY public.instructions_history.history_id;


--
-- Name: instructions_instruction_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.instructions ALTER COLUMN instruction_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.instructions_instruction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: interaction_lineage; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.interaction_lineage (
    lineage_id integer NOT NULL,
    downstream_interaction_id integer NOT NULL,
    upstream_interaction_id integer NOT NULL,
    influence_type text NOT NULL,
    placeholder_used text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT interaction_lineage_check CHECK ((downstream_interaction_id <> upstream_interaction_id)),
    CONSTRAINT interaction_lineage_influence_type_check CHECK ((influence_type = ANY (ARRAY['direct_read'::text, 'sequential'::text, 'parallel_sync'::text, 'conditional'::text, 'dialogue_context'::text])))
);


ALTER TABLE public.interaction_lineage OWNER TO base_admin;

--
-- Name: TABLE interaction_lineage; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.interaction_lineage IS 'Causation graph: tracks which LLM interactions influenced which others. Enables lineage analysis and change impact tracking.';


--
-- Name: COLUMN interaction_lineage.downstream_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_lineage.downstream_interaction_id IS 'The interaction that was influenced (reads/depends on upstream)';


--
-- Name: COLUMN interaction_lineage.upstream_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_lineage.upstream_interaction_id IS 'The interaction that provided influence (was read by downstream)';


--
-- Name: COLUMN interaction_lineage.influence_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_lineage.influence_type IS 'How upstream influenced downstream: direct_read, sequential, parallel_sync, conditional, dialogue_context';


--
-- Name: COLUMN interaction_lineage.placeholder_used; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_lineage.placeholder_used IS 'If direct_read: which placeholder was used (e.g., session_1_output, dialogue_step_2_output)';


--
-- Name: interaction_lineage_lineage_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.interaction_lineage ALTER COLUMN lineage_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.interaction_lineage_lineage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: job_fetch_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_fetch_runs (
    fetch_run_id integer NOT NULL,
    source_id integer NOT NULL,
    workflow_run_id integer,
    fetch_started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fetch_completed_at timestamp without time zone,
    duration_ms integer,
    jobs_fetched integer DEFAULT 0,
    jobs_new integer DEFAULT 0,
    jobs_updated integer DEFAULT 0,
    jobs_duplicate integer DEFAULT 0,
    jobs_error integer DEFAULT 0,
    status text DEFAULT 'RUNNING'::text NOT NULL,
    error_message text,
    fetch_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_fetch_status CHECK ((status = ANY (ARRAY['RUNNING'::text, 'SUCCESS'::text, 'PARTIAL_SUCCESS'::text, 'ERROR'::text])))
);


ALTER TABLE public.job_fetch_runs OWNER TO base_admin;

--
-- Name: TABLE job_fetch_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_fetch_runs IS 'Execution log for each job fetch operation';


--
-- Name: COLUMN job_fetch_runs.fetch_metadata; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_fetch_runs.fetch_metadata IS 'API response metadata, rate limits, pagination info, etc.';


--
-- Name: job_fetch_runs_fetch_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.job_fetch_runs ALTER COLUMN fetch_run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.job_fetch_runs_fetch_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: job_skills; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_skills (
    job_skill_id integer NOT NULL,
    posting_id integer NOT NULL,
    skill_id integer NOT NULL,
    importance text,
    weight integer,
    proficiency text,
    years_required integer,
    reasoning text,
    extracted_by text,
    recipe_run_id integer,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT job_skills_importance_check CHECK ((importance = ANY (ARRAY['essential'::text, 'critical'::text, 'important'::text, 'preferred'::text, 'bonus'::text]))),
    CONSTRAINT job_skills_proficiency_check CHECK ((proficiency = ANY (ARRAY['expert'::text, 'advanced'::text, 'intermediate'::text, 'beginner'::text]))),
    CONSTRAINT job_skills_weight_check CHECK (((weight >= 10) AND (weight <= 100)))
);


ALTER TABLE public.job_skills OWNER TO base_admin;

--
-- Name: TABLE job_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_skills IS 'Normalized skills extracted from postings.skill_keywords JSONB';


--
-- Name: job_skills_job_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.job_skills ALTER COLUMN job_skill_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.job_skills_job_skill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: job_sources; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_sources (
    source_id integer NOT NULL,
    source_name text NOT NULL,
    source_type text NOT NULL,
    source_url text,
    api_config jsonb,
    fetch_workflow_id integer,
    fetch_schedule text,
    last_fetch_at timestamp without time zone,
    last_fetch_count integer,
    next_fetch_at timestamp without time zone,
    total_jobs_fetched integer DEFAULT 0,
    total_jobs_active integer DEFAULT 0,
    is_active boolean DEFAULT true,
    priority integer DEFAULT 5,
    description text,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_priority CHECK (((priority >= 1) AND (priority <= 10))),
    CONSTRAINT valid_source_type CHECK ((source_type = ANY (ARRAY['api'::text, 'scraper'::text, 'manual_upload'::text, 'rss_feed'::text, 'webhook'::text])))
);


ALTER TABLE public.job_sources OWNER TO base_admin;

--
-- Name: TABLE job_sources; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_sources IS 'External job data sources (APIs, scrapers, feeds) that feed into Turing';


--
-- Name: COLUMN job_sources.api_config; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_sources.api_config IS 'JSONB config for API authentication, endpoints, pagination, etc.';


--
-- Name: COLUMN job_sources.fetch_workflow_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_sources.fetch_workflow_id IS 'Workflow that executes the fetch operation for this source';


--
-- Name: job_sources_source_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.job_sources ALTER COLUMN source_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.job_sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: llm_interactions_interaction_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.llm_interactions ALTER COLUMN interaction_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.llm_interactions_interaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: migration_log; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.migration_log (
    migration_id integer NOT NULL,
    migration_number character varying(10) NOT NULL,
    migration_name character varying(255) NOT NULL,
    migration_file character varying(255),
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    applied_by character varying(100),
    duration_ms integer,
    status character varying(50) DEFAULT 'SUCCESS'::character varying,
    error_message text,
    database_version character varying(50),
    notes text,
    depends_on character varying(10)[],
    is_data_migration boolean DEFAULT false,
    is_reversible boolean DEFAULT true,
    rollback_sql text
);


ALTER TABLE public.migration_log OWNER TO base_admin;

--
-- Name: migration_log_migration_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.migration_log_migration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.migration_log_migration_id_seq OWNER TO base_admin;

--
-- Name: migration_log_migration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.migration_log_migration_id_seq OWNED BY public.migration_log.migration_id;


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.organizations (
    organization_id integer NOT NULL,
    organization_name text NOT NULL,
    organization_type text,
    contact_email text,
    contact_phone text,
    website_url text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT organizations_organization_type_check CHECK ((organization_type = ANY (ARRAY['recruiting_firm'::text, 'outplacement'::text, 'employer'::text, 'other'::text])))
);


ALTER TABLE public.organizations OWNER TO base_admin;

--
-- Name: TABLE organizations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.organizations IS 'Optional organization membership for recruiting firms, employers, etc.';


--
-- Name: organizations_organization_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.organizations ALTER COLUMN organization_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.organizations_organization_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: placeholder_definitions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.placeholder_definitions (
    placeholder_id integer NOT NULL,
    placeholder_name text NOT NULL,
    source_type text NOT NULL,
    source_table text,
    source_column text,
    source_query text,
    is_required boolean DEFAULT false,
    default_value text,
    description text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_source_type CHECK ((source_type = ANY (ARRAY['test_case_data'::text, 'posting'::text, 'profile'::text, 'dialogue_output'::text, 'static'::text, 'custom_query'::text])))
);


ALTER TABLE public.placeholder_definitions OWNER TO base_admin;

--
-- Name: TABLE placeholder_definitions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.placeholder_definitions IS 'Registry of all available placeholders in the Turing system - first-class metadata management';


--
-- Name: COLUMN placeholder_definitions.placeholder_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.placeholder_definitions.placeholder_name IS 'The placeholder name used in templates: {placeholder_name}';


--
-- Name: COLUMN placeholder_definitions.source_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.placeholder_definitions.source_type IS 'Where to fetch the value: test_case_data, posting, profile, dialogue_output, static, custom_query';


--
-- Name: COLUMN placeholder_definitions.source_query; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.placeholder_definitions.source_query IS 'Custom SQL to resolve placeholder (overrides table/column). Use :job_id, :profile_id, :test_case_id parameters';


--
-- Name: placeholder_definitions_placeholder_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.placeholder_definitions ALTER COLUMN placeholder_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.placeholder_definitions_placeholder_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: posting_field_mappings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_field_mappings (
    mapping_id integer NOT NULL,
    source_id integer NOT NULL,
    source_field_name text NOT NULL,
    target_field_name text NOT NULL,
    transformation_rule text,
    confidence numeric DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text DEFAULT 'qwen_mapper'::text
);


ALTER TABLE public.posting_field_mappings OWNER TO base_admin;

--
-- Name: TABLE posting_field_mappings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_field_mappings IS 'Qwen-generated field mappings for dynamic source adaptation';


--
-- Name: posting_field_mappings_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.posting_field_mappings ALTER COLUMN mapping_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.posting_field_mappings_mapping_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: posting_processing_status; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_processing_status (
    posting_id integer NOT NULL,
    summary_extracted boolean DEFAULT false,
    summary_extracted_at timestamp without time zone,
    summary_workflow_run_id integer,
    skills_extracted boolean DEFAULT false,
    skills_extracted_at timestamp without time zone,
    skills_workflow_run_id integer,
    ihl_analyzed boolean DEFAULT false,
    ihl_analyzed_at timestamp without time zone,
    ihl_workflow_run_id integer,
    candidates_matched boolean DEFAULT false,
    candidates_matched_at timestamp without time zone,
    matching_workflow_run_id integer,
    processing_complete boolean GENERATED ALWAYS AS ((summary_extracted AND skills_extracted AND ihl_analyzed)) STORED,
    last_processed_at timestamp without time zone,
    processing_notes text
);


ALTER TABLE public.posting_processing_status OWNER TO base_admin;

--
-- Name: TABLE posting_processing_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_processing_status IS 'Track which processing stages have been completed for each posting';


--
-- Name: COLUMN posting_processing_status.processing_complete; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.posting_processing_status.processing_complete IS 'Auto-computed: true when summary, skills, and IHL are all extracted';


--
-- Name: posting_sources; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_sources (
    source_id integer NOT NULL,
    source_name text NOT NULL,
    base_url text NOT NULL,
    scraper_config jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    last_scraped_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.posting_sources OWNER TO base_admin;

--
-- Name: TABLE posting_sources; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_sources IS 'Tracks job posting sources (Deutsche Bank, Arbeitsagentur, etc.)';


--
-- Name: posting_sources_source_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.posting_sources ALTER COLUMN source_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.posting_sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


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
    complexity_score real,
    employment_benefits jsonb,
    employment_career_level text,
    employment_salary_range text,
    employment_schedule text,
    employment_type text,
    enabled boolean DEFAULT true,
    extracted_summary text,
    imported_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_test_posting boolean DEFAULT false,
    job_description text,
    job_requirements jsonb,
    job_title text,
    location_city text,
    location_country text,
    location_remote_options boolean,
    location_state text,
    metadata_created_at timestamp without time zone,
    metadata_last_modified timestamp without time zone,
    metadata_processor text,
    metadata_source text,
    metadata_status text,
    organization_division text,
    organization_division_id integer,
    organization_name text,
    posting_hiring_year text,
    posting_position_uri text,
    posting_publication_date date,
    posting_source_id text,
    processing_notes text,
    skill_keywords jsonb,
    source_id integer,
    summary_extracted_at timestamp without time zone,
    summary_extraction_status text DEFAULT 'pending'::text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ihl_score integer,
    ihl_category text,
    ihl_analyzed_at timestamp without time zone,
    ihl_workflow_run_id integer,
    external_job_id text,
    external_url text,
    fetched_at timestamp without time zone,
    last_checked_at timestamp without time zone,
    fetch_hash text,
    posting_status text DEFAULT 'active'::text,
    status_changed_at timestamp without time zone,
    status_reason text,
    first_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    times_checked integer DEFAULT 1,
    fetch_run_id integer,
    CONSTRAINT ihl_category_valid CHECK (((ihl_category IS NULL) OR (ihl_category = ANY (ARRAY['OPEN SEARCH'::text, 'COMPETITIVE'::text, 'INTERNAL LIKELY'::text, 'PRE-DETERMINED'::text])))),
    CONSTRAINT ihl_score_valid CHECK (((ihl_score IS NULL) OR ((ihl_score >= 0) AND (ihl_score <= 100)))),
    CONSTRAINT valid_posting_status CHECK ((posting_status = ANY (ARRAY['active'::text, 'filled'::text, 'expired'::text, 'withdrawn'::text, 'archived'::text])))
);


ALTER TABLE public.postings OWNER TO base_admin;

--
-- Name: TABLE postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.postings IS 'Job postings (76 entries). Standardized 2025-10-30.
Pattern: posting_id (INTEGER PK) + posting_name (TEXT, not unique).
Note: posting_name can have duplicates (e.g., test data like TEST_ORACLE_DBA_001).';


--
-- Name: COLUMN postings.posting_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: COLUMN postings.posting_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_name IS 'Job identifier from source system (can be duplicate for test data)';


--
-- Name: COLUMN postings.job_requirements; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.job_requirements IS 'JSONB array of requirements. Structured for analysis.';


--
-- Name: COLUMN postings.metadata_source; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.metadata_source IS 'Data source: deutsche_bank, arbeitsagentur, company_website, etc.';


--
-- Name: COLUMN postings.skill_keywords; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.skill_keywords IS 'Extracted skills for matching. Computed field populated by analysis recipes.';


--
-- Name: COLUMN postings.source_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.source_id IS 'Which job source this posting came from';


--
-- Name: COLUMN postings.ihl_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.ihl_score IS 'Internal Hire Likelihood score (0-100): probability that position is pre-wired for internal candidate';


--
-- Name: COLUMN postings.ihl_category; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.ihl_category IS 'IHL category: OPEN SEARCH (10-30%), COMPETITIVE (40-60%), INTERNAL LIKELY (70-85%), PRE-DETERMINED (90-100%)';


--
-- Name: COLUMN postings.ihl_analyzed_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.ihl_analyzed_at IS 'Timestamp when IHL analysis was performed';


--
-- Name: COLUMN postings.ihl_workflow_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.ihl_workflow_run_id IS 'Reference to workflow_run that generated this IHL score';


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
-- Name: COLUMN postings.times_checked; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.times_checked IS 'How many times we''ve checked if this posting still exists';


--
-- Name: production_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.production_runs (
    production_run_id integer NOT NULL,
    workflow_id integer NOT NULL,
    posting_name text NOT NULL,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    status text DEFAULT 'RUNNING'::text,
    total_sessions integer,
    completed_sessions integer DEFAULT 0,
    error_details text,
    posting_id integer,
    CONSTRAINT production_runs_completed_sessions_check CHECK ((completed_sessions >= 0)),
    CONSTRAINT production_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'PARTIAL'::text, 'ERROR'::text]))),
    CONSTRAINT production_runs_total_sessions_check CHECK ((total_sessions > 0))
);


ALTER TABLE public.production_runs OWNER TO base_admin;

--
-- Name: TABLE production_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.production_runs IS 'Production execution of recipes using real job postings (not synthetic test variations). Same recipes tested in recipe_runs, deployed here with real data!';


--
-- Name: COLUMN production_runs.posting_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.production_runs.posting_name IS 'Real job posting from postings table (production input), vs variation_id (test input)';


--
-- Name: production_runs_production_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.production_runs_production_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.production_runs_production_run_id_seq OWNER TO base_admin;

--
-- Name: production_runs_production_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.production_runs_production_run_id_seq OWNED BY public.production_runs.production_run_id;


--
-- Name: profile_certifications; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_certifications (
    certification_id integer NOT NULL,
    profile_id integer NOT NULL,
    certification_name text NOT NULL,
    issuing_organization text,
    credential_id text,
    credential_url text,
    issue_date date,
    expiration_date date,
    does_not_expire boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.profile_certifications OWNER TO base_admin;

--
-- Name: profile_certifications_certification_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_certifications_certification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_certifications_certification_id_seq OWNER TO base_admin;

--
-- Name: profile_certifications_certification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_certifications_certification_id_seq OWNED BY public.profile_certifications.certification_id;


--
-- Name: profile_education; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_education (
    education_id integer NOT NULL,
    profile_id integer NOT NULL,
    institution_name text NOT NULL,
    institution_location text,
    degree_type text,
    degree_name text,
    field_of_study text,
    start_date date,
    end_date date,
    graduation_year integer,
    is_current boolean DEFAULT false,
    gpa numeric(3,2),
    honors text,
    thesis_title text,
    relevant_coursework text[],
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.profile_education OWNER TO base_admin;

--
-- Name: profile_education_education_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_education_education_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_education_education_id_seq OWNER TO base_admin;

--
-- Name: profile_education_education_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_education_education_id_seq OWNED BY public.profile_education.education_id;


--
-- Name: profile_job_matches; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_job_matches (
    match_id integer NOT NULL,
    profile_id integer NOT NULL,
    posting_name text NOT NULL,
    overall_match_score numeric(5,2),
    skill_match_score numeric(5,2),
    experience_match_score numeric(5,2),
    location_match_score numeric(5,2),
    matched_skills jsonb,
    missing_skills jsonb,
    extra_skills jsonb,
    match_status text DEFAULT 'pending'::text,
    match_quality text,
    match_explanation text,
    matched_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamp without time zone,
    contacted_at timestamp without time zone,
    recruiter_notes text,
    posting_id integer NOT NULL,
    user_id integer
);


ALTER TABLE public.profile_job_matches OWNER TO base_admin;

--
-- Name: TABLE profile_job_matches; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_job_matches IS 'Match scores between profiles and job postings';


--
-- Name: COLUMN profile_job_matches.overall_match_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_job_matches.overall_match_score IS 'Composite score from 0-100';


--
-- Name: COLUMN profile_job_matches.matched_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_job_matches.matched_skills IS 'Skills that overlap between profile and job';


--
-- Name: profile_job_matches_match_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_job_matches_match_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_job_matches_match_id_seq OWNER TO base_admin;

--
-- Name: profile_job_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_job_matches_match_id_seq OWNED BY public.profile_job_matches.match_id;


--
-- Name: profile_languages; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_languages (
    language_id integer NOT NULL,
    profile_id integer NOT NULL,
    language_name text NOT NULL,
    proficiency_level text,
    speaking_level text,
    writing_level text,
    reading_level text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.profile_languages OWNER TO base_admin;

--
-- Name: profile_languages_language_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_languages_language_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_languages_language_id_seq OWNER TO base_admin;

--
-- Name: profile_languages_language_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_languages_language_id_seq OWNED BY public.profile_languages.language_id;


--
-- Name: profile_skills; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_skills (
    profile_skill_id integer NOT NULL,
    profile_id integer NOT NULL,
    skill_id integer NOT NULL,
    years_experience numeric,
    proficiency_level text,
    last_used_date date,
    is_implicit boolean DEFAULT false,
    evidence_text text,
    extracted_by text,
    recipe_run_id integer,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT profile_skills_proficiency_level_check CHECK ((proficiency_level = ANY (ARRAY['expert'::text, 'advanced'::text, 'intermediate'::text, 'beginner'::text])))
);


ALTER TABLE public.profile_skills OWNER TO base_admin;

--
-- Name: TABLE profile_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_skills IS 'Normalized skills extracted from profiles.skill_keywords JSONB';


--
-- Name: profile_skills_profile_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.profile_skills ALTER COLUMN profile_skill_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.profile_skills_profile_skill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


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
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.profile_work_history OWNER TO base_admin;

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
    last_activity_date timestamp without time zone,
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
-- Name: workflows_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflows_history (
    history_id integer NOT NULL,
    workflow_id integer NOT NULL,
    workflow_name text,
    workflow_description text,
    workflow_version integer,
    max_total_session_runs integer,
    enabled boolean,
    review_notes text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.workflows_history OWNER TO base_admin;

--
-- Name: TABLE workflows_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflows_history IS 'Audit trail of all changes to recipes table. Tracks recipe modifications over time, enabling "what changed when I broke it?" debugging.';


--
-- Name: recipes_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.recipes_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recipes_history_history_id_seq OWNER TO base_admin;

--
-- Name: recipes_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.recipes_history_history_id_seq OWNED BY public.workflows_history.history_id;


--
-- Name: script_executions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.script_executions (
    execution_id integer NOT NULL,
    script_id integer,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    executed_by character varying(100),
    execution_args jsonb,
    execution_context jsonb,
    status character varying(50),
    duration_ms integer,
    return_value jsonb,
    stdout_log text,
    stderr_log text,
    error_message text
);


ALTER TABLE public.script_executions OWNER TO base_admin;

--
-- Name: script_executions_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.script_executions_execution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.script_executions_execution_id_seq OWNER TO base_admin;

--
-- Name: script_executions_execution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.script_executions_execution_id_seq OWNED BY public.script_executions.execution_id;


--
-- Name: sessions_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.sessions_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sessions_history_history_id_seq OWNER TO base_admin;

--
-- Name: sessions_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.sessions_history_history_id_seq OWNED BY public.conversations_history.history_id;


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
-- Name: skill_aliases; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_aliases (
    skill_id integer DEFAULT nextval('public.skill_aliases_skill_id_seq'::regclass) NOT NULL,
    skill_name text NOT NULL,
    confidence numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    display_name text,
    language text DEFAULT 'en'::text,
    notes text,
    skill_alias text NOT NULL
);


ALTER TABLE public.skill_aliases OWNER TO base_admin;

--
-- Name: TABLE skill_aliases; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_aliases IS 'Master list of 896 skills with canonical names and aliases. Standardized 2025-10-30.
Pattern: skill_id (INTEGER PK) + skill_name (TEXT UNIQUE) for AI consistency.';


--
-- Name: COLUMN skill_aliases.skill_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: COLUMN skill_aliases.skill_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_name IS 'Natural key - canonical skill name in UPPER_SNAKE_CASE (unique)';


--
-- Name: COLUMN skill_aliases.display_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.display_name IS 'Pretty format for UI display (e.g., "Python", "SQLite", "iShares")';


--
-- Name: COLUMN skill_aliases.skill_alias; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_alias IS 'Any variation: lowercase, uppercase, hyphenated, translated, etc.';


--
-- Name: skill_hierarchy; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_hierarchy (
    strength numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    skill_id integer NOT NULL,
    parent_skill_id integer NOT NULL,
    CONSTRAINT skill_hierarchy_check CHECK ((skill_id <> parent_skill_id))
);


ALTER TABLE public.skill_hierarchy OWNER TO base_admin;

--
-- Name: TABLE skill_hierarchy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_hierarchy IS 'Parent-child relationships between skills (340 edges). Fully integer-based after migration 007.
Uses skill_id and parent_skill_id as composite PK, both FK to skill_aliases.';


--
-- Name: COLUMN skill_hierarchy.strength; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_hierarchy.strength IS 'Weight for matching: 1.0 = strong parent, 0.5 = weak/distant parent';


--
-- Name: skill_occurrences; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_occurrences (
    occurrence_id integer NOT NULL,
    skill_source text NOT NULL,
    source_id text NOT NULL,
    skill_alias text,
    confidence numeric(3,2) DEFAULT 1.0,
    context text,
    extraction_method text,
    created_at timestamp without time zone DEFAULT now(),
    skill_id integer
);


ALTER TABLE public.skill_occurrences OWNER TO base_admin;

--
-- Name: TABLE skill_occurrences; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_occurrences IS 'Tracks where skills appear in postings/profiles (404 rows). Uses skill_id FK to skill_aliases.';


--
-- Name: COLUMN skill_occurrences.skill_alias; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_occurrences.skill_alias IS 'Original text before normalization (e.g., "Python 3.11", "python-programming")';


--
-- Name: COLUMN skill_occurrences.context; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_occurrences.context IS 'Sentence or paragraph where skill was found (for debugging/validation)';


--
-- Name: skill_occurrences_occurrence_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_occurrences_occurrence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_occurrences_occurrence_id_seq OWNER TO base_admin;

--
-- Name: skill_occurrences_occurrence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.skill_occurrences_occurrence_id_seq OWNED BY public.skill_occurrences.occurrence_id;


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
-- Name: skills_pending_taxonomy; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skills_pending_taxonomy (
    pending_skill_id integer DEFAULT nextval('public.skills_pending_taxonomy_pending_skill_id_seq'::regclass) NOT NULL,
    raw_skill_name text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    found_in_jobs text[],
    llm_reasoning text,
    notes text,
    occurrences integer DEFAULT 1,
    review_status text DEFAULT 'pending'::text,
    reviewed_at timestamp without time zone,
    reviewed_by text,
    suggested_canonical text,
    suggested_confidence double precision,
    suggested_domain text,
    CONSTRAINT skills_pending_taxonomy_review_status_check CHECK ((review_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'duplicate'::text])))
);


ALTER TABLE public.skills_pending_taxonomy OWNER TO base_admin;

--
-- Name: TABLE skills_pending_taxonomy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skills_pending_taxonomy IS 'Skills awaiting taxonomy classification (1090 entries). Standardized 2025-10-30.
Pattern: pending_skill_id (INTEGER PK) + raw_skill_name (TEXT UNIQUE).';


--
-- Name: COLUMN skills_pending_taxonomy.pending_skill_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skills_pending_taxonomy.pending_skill_id IS 'Surrogate key - stable integer identifier';


--
-- Name: COLUMN skills_pending_taxonomy.raw_skill_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skills_pending_taxonomy.raw_skill_name IS 'Natural key - raw skill text extracted from postings (unique)';


--
-- Name: stored_scripts; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.stored_scripts (
    script_id integer NOT NULL,
    script_name character varying(255) NOT NULL,
    script_description text,
    script_version character varying(50) NOT NULL,
    script_language character varying(50) DEFAULT 'python'::character varying,
    script_category character varying(100),
    script_code text NOT NULL,
    requires_packages text[],
    requires_scripts integer[],
    entry_point character varying(255),
    expected_args text[],
    returns_data_type character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by character varying(100),
    is_current_version boolean DEFAULT true,
    replaces_script_id integer,
    usage_example text,
    change_log text,
    tags text[],
    is_production boolean DEFAULT false,
    last_executed_at timestamp without time zone,
    execution_count integer DEFAULT 0
);


ALTER TABLE public.stored_scripts OWNER TO base_admin;

--
-- Name: stored_scripts_script_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.stored_scripts_script_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.stored_scripts_script_id_seq OWNER TO base_admin;

--
-- Name: stored_scripts_script_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.stored_scripts_script_id_seq OWNED BY public.stored_scripts.script_id;


--
-- Name: test_cases; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.test_cases (
    test_case_id integer NOT NULL,
    test_case_name text NOT NULL,
    workflow_id integer NOT NULL,
    test_data jsonb NOT NULL,
    difficulty_level integer DEFAULT 1,
    expected_response text,
    response_format text,
    complexity_score real,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.test_cases OWNER TO base_admin;

--
-- Name: TABLE test_cases; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.test_cases IS 'Test cases for workflows with varying difficulty levels. Each test case contains input data (test_data) and expected outputs (expected_response) for validating workflow execution. Used in TESTING mode to verify workflows work correctly across different scenarios and complexity levels.';


--
-- Name: COLUMN test_cases.test_case_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.test_case_id IS 'Unique identifier for this test case';


--
-- Name: COLUMN test_cases.test_case_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.test_case_name IS 'Human-readable name for this test case';


--
-- Name: COLUMN test_cases.workflow_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.workflow_id IS 'Foreign key to workflows table - which workflow this test case validates';


--
-- Name: COLUMN test_cases.test_data; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.test_data IS 'JSONB object containing input parameters for the test case';


--
-- Name: COLUMN test_cases.difficulty_level; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.difficulty_level IS 'Integer representing test complexity (1=easy, 2=medium, 3=hard, etc.)';


--
-- Name: COLUMN test_cases.expected_response; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.expected_response IS 'Expected output from the workflow for validation';


--
-- Name: COLUMN test_cases.response_format; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.response_format IS 'Format specification for the expected response';


--
-- Name: COLUMN test_cases.complexity_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.complexity_score IS 'Computed complexity metric for this test case';


--
-- Name: COLUMN test_cases.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.enabled IS 'Whether this test case is active (true) or disabled (false)';


--
-- Name: COLUMN test_cases.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.created_at IS 'Timestamp when this test case was created';


--
-- Name: COLUMN test_cases.updated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.test_cases.updated_at IS 'Timestamp when this test case was last modified';


--
-- Name: test_cases_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.test_cases_history (
    history_id integer NOT NULL,
    test_case_id integer NOT NULL,
    recipe_id integer NOT NULL,
    test_data jsonb,
    difficulty_level integer,
    expected_response text,
    response_format text,
    complexity_score real,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.test_cases_history OWNER TO base_admin;

--
-- Name: TABLE test_cases_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.test_cases_history IS 'Audit trail of all changes to variations table. Tracks test data evolution, helps identify when variations were modified that might affect test reproducibility.';


--
-- Name: test_cases_test_case_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.test_cases ALTER COLUMN test_case_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_cases_test_case_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trigger_executions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.trigger_executions (
    execution_id integer NOT NULL,
    trigger_id integer,
    workflow_run_id integer,
    triggered_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    trigger_reason text,
    trigger_condition_value text,
    status character varying(50),
    status_reason text,
    completed_at timestamp without time zone,
    duration_ms integer,
    execution_context jsonb
);


ALTER TABLE public.trigger_executions OWNER TO base_admin;

--
-- Name: trigger_executions_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.trigger_executions_execution_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.trigger_executions_execution_id_seq OWNER TO base_admin;

--
-- Name: trigger_executions_execution_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.trigger_executions_execution_id_seq OWNED BY public.trigger_executions.execution_id;


--
-- Name: user_posting_preferences; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_posting_preferences (
    preference_id integer NOT NULL,
    user_id integer NOT NULL,
    preference_type text NOT NULL,
    preference_value text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT user_posting_preferences_preference_type_check CHECK ((preference_type = ANY (ARRAY['exclude_company'::text, 'exclude_sector'::text, 'exclude_location'::text, 'exclude_source'::text])))
);


ALTER TABLE public.user_posting_preferences OWNER TO base_admin;

--
-- Name: TABLE user_posting_preferences; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_posting_preferences IS 'User opt-out filters for companies, sectors, locations';


--
-- Name: user_posting_preferences_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.user_posting_preferences ALTER COLUMN preference_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.user_posting_preferences_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_preferences; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_preferences (
    user_id integer NOT NULL,
    user_name text NOT NULL,
    email text,
    preferred_career_levels text[],
    preferred_locations text[],
    preferred_divisions text[],
    preferred_companies text[],
    min_salary integer,
    max_salary integer,
    currency text DEFAULT 'EUR'::text,
    remote_only boolean DEFAULT false,
    willing_to_relocate boolean DEFAULT true,
    required_skills text[],
    preferred_skills text[],
    employment_types text[],
    max_travel_percentage integer,
    alert_on_new_jobs boolean DEFAULT true,
    alert_on_matches boolean DEFAULT true,
    alert_frequency text DEFAULT 'daily'::text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_alert_frequency CHECK ((alert_frequency = ANY (ARRAY['immediate'::text, 'daily'::text, 'weekly'::text, 'never'::text])))
);


ALTER TABLE public.user_preferences OWNER TO base_admin;

--
-- Name: TABLE user_preferences; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_preferences IS 'User job search preferences and filters';


--
-- Name: user_preferences_user_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.user_preferences ALTER COLUMN user_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.user_preferences_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_saved_postings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_saved_postings (
    user_id integer NOT NULL,
    posting_id integer NOT NULL,
    saved_at timestamp without time zone DEFAULT now(),
    notes text,
    tags jsonb DEFAULT '[]'::jsonb,
    application_status text,
    application_date date,
    CONSTRAINT user_saved_postings_application_status_check CHECK ((application_status = ANY (ARRAY['saved'::text, 'applied'::text, 'interviewing'::text, 'rejected'::text, 'accepted'::text, 'withdrawn'::text])))
);


ALTER TABLE public.user_saved_postings OWNER TO base_admin;

--
-- Name: TABLE user_saved_postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_saved_postings IS 'User bookmarks with application tracking';


--
-- Name: users; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    full_name text NOT NULL,
    status text DEFAULT 'active'::text,
    is_job_seeker boolean DEFAULT true,
    is_recruiter boolean DEFAULT false,
    is_admin boolean DEFAULT false,
    organization_id integer,
    created_at timestamp without time zone DEFAULT now(),
    last_login_at timestamp without time zone,
    email_verified_at timestamp without time zone,
    preferences jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT users_status_check CHECK ((status = ANY (ARRAY['active'::text, 'suspended'::text, 'deleted'::text])))
);


ALTER TABLE public.users OWNER TO base_admin;

--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.users IS 'Platform users (application layer) - authenticated accounts for talent.yoga.
Supports multiple roles via flags: job seekers, recruiters, and admins.

User vs Actor Distinction:
- users table = APPLICATION LAYER: Authentication, authorization, profile ownership
- actors table = EXECUTION LAYER: Workflow execution, instruction processing
- Users become actors when they participate in workflows (linked via actors.user_id)
- Users own data (profiles, saved postings, workflow_runs.user_id)
- Actors execute steps (instructions, human_tasks, conversations)

Example: Job seeker Jane has:
- User record (user_id=42): email, password, preferences, profile ownership
- Actor record (actor_id=123, user_id=42): executes workflow steps when she provides input

Not all users need actor records (browse-only users), and not all actors are users (AI/scripts).';


--
-- Name: COLUMN users.user_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.user_id IS 'Unique identifier for this user account. Referenced by profiles, workflow_runs (ownership), and actors.user_id (execution identity).';


--
-- Name: COLUMN users.email; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.email IS 'Unique email address for authentication and communication';


--
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.password_hash IS 'Bcrypt hash of user password for secure authentication';


--
-- Name: COLUMN users.full_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.full_name IS 'User''s full name for display and personalization';


--
-- Name: COLUMN users.status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.status IS 'Account status: active, suspended, or deleted';


--
-- Name: COLUMN users.is_job_seeker; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.is_job_seeker IS 'Flag: true if user is searching for jobs (may have profile)';


--
-- Name: COLUMN users.is_recruiter; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.is_recruiter IS 'Flag: true if user is hiring/posting jobs';


--
-- Name: COLUMN users.is_admin; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.is_admin IS 'Flag: true if user has administrative privileges';


--
-- Name: COLUMN users.organization_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.organization_id IS 'Foreign key to organizations table (for recruiters/admins)';


--
-- Name: COLUMN users.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.created_at IS 'Timestamp when user account was created';


--
-- Name: COLUMN users.last_login_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.last_login_at IS 'Timestamp of most recent login';


--
-- Name: COLUMN users.email_verified_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.email_verified_at IS 'Timestamp when email was verified (NULL if unverified)';


--
-- Name: COLUMN users.preferences; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.users.preferences IS 'JSONB object with user preferences (notifications, display settings, etc.)';


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.users ALTER COLUMN user_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: workflow_scripts; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_scripts (
    workflow_id integer NOT NULL,
    script_id integer NOT NULL,
    execution_order integer,
    is_required boolean DEFAULT true
);


ALTER TABLE public.workflow_scripts OWNER TO base_admin;

--
-- Name: v_current_scripts; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_current_scripts AS
 SELECT s.script_id,
    s.script_name,
    s.script_version,
    s.script_category,
    s.script_description,
    s.entry_point,
    s.created_at,
    s.is_production,
    s.execution_count,
    s.last_executed_at,
    COALESCE(array_length(s.requires_packages, 1), 0) AS dependency_count,
    COALESCE(( SELECT count(*) AS count
           FROM public.workflow_scripts ws
          WHERE (ws.script_id = s.script_id)), (0)::bigint) AS workflow_count
   FROM public.stored_scripts s
  WHERE (s.is_current_version = true)
  ORDER BY s.script_category, s.script_name;


ALTER TABLE public.v_current_scripts OWNER TO base_admin;

--
-- Name: v_database_state; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_database_state AS
 SELECT count(*) AS total_migrations,
    count(*) FILTER (WHERE ((migration_log.status)::text = 'SUCCESS'::text)) AS successful_migrations,
    count(*) FILTER (WHERE ((migration_log.status)::text = 'FAILED'::text)) AS failed_migrations,
    max((migration_log.migration_number)::text) AS latest_migration,
    max(migration_log.applied_at) AS last_migration_date
   FROM public.migration_log;


ALTER TABLE public.v_database_state OWNER TO base_admin;

--
-- Name: v_migration_history; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_migration_history AS
 SELECT migration_log.migration_number,
    migration_log.migration_name,
    migration_log.applied_at,
    migration_log.duration_ms,
    migration_log.status,
        CASE
            WHEN (migration_log.error_message IS NOT NULL) THEN '❌ ERROR'::text
            WHEN ((migration_log.status)::text = 'ROLLED_BACK'::text) THEN '⏮️ ROLLED BACK'::text
            ELSE '✅ SUCCESS'::text
        END AS status_icon
   FROM public.migration_log
  ORDER BY migration_log.migration_number;


ALTER TABLE public.v_migration_history OWNER TO base_admin;

--
-- Name: workflow_placeholders; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_placeholders (
    workflow_id integer NOT NULL,
    placeholder_id integer NOT NULL,
    is_required boolean DEFAULT false,
    description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.workflow_placeholders OWNER TO base_admin;

--
-- Name: TABLE workflow_placeholders; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_placeholders IS 'Links workflows to their required/optional placeholders';


--
-- Name: workflows; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflows (
    workflow_id integer NOT NULL,
    workflow_name text NOT NULL,
    workflow_description text,
    workflow_version integer DEFAULT 1,
    max_total_session_runs integer DEFAULT 100,
    enabled boolean DEFAULT true,
    review_notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    documentation text
);


ALTER TABLE public.workflows OWNER TO base_admin;

--
-- Name: TABLE workflows; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflows IS 'Executable workflows that orchestrate multiple conversations (66 entries).
A workflow is a program: it sequences conversations, handles dependencies, and manages control flow.
Think of it as a function that calls multiple subroutines (conversations) in a specific order.
Key to Turing completeness: workflows compose atomic conversations into complex algorithms.
Versioned for iteration: workflow_name + workflow_version = unique workflow definition.
Renamed from recipes 2025-10-31 for clarity (workflows is industry-standard term).
Pattern: workflow_id (INTEGER PK) + workflow_name (TEXT).';


--
-- Name: COLUMN workflows.workflow_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.workflow_id IS 'Primary key - unique identifier for this workflow';


--
-- Name: COLUMN workflows.workflow_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.workflow_name IS 'Human-readable name (e.g., "Job Quality Pipeline", "Skill Extraction Workflow")';


--
-- Name: COLUMN workflows.workflow_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.workflow_description IS 'Brief description of what this workflow does and when to use it';


--
-- Name: COLUMN workflows.workflow_version; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.workflow_version IS 'Version number for iterating on workflow logic (1, 2, 3...). workflow_name + workflow_version must be unique.';


--
-- Name: COLUMN workflows.max_total_session_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.max_total_session_runs IS 'Maximum total conversation executions allowed across all workflow steps (prevents infinite loops).
Workflow-level execution budget. Default: 100.';


--
-- Name: COLUMN workflows.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.enabled IS 'If false, this recipe cannot be executed (soft delete)';


--
-- Name: COLUMN workflows.review_notes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.review_notes IS 'Internal notes about recipe performance, issues, or improvement opportunities';


--
-- Name: COLUMN workflows.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.created_at IS 'Timestamp when this recipe was first created';


--
-- Name: COLUMN workflows.updated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.updated_at IS 'Timestamp when this recipe was last modified';


--
-- Name: COLUMN workflows.documentation; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.documentation IS 'Comprehensive recipe documentation in Markdown format.
Should include: architecture, conversation sequence, dependencies, performance metrics, troubleshooting, usage examples.';


--
-- Name: v_placeholder_usage; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_placeholder_usage AS
 SELECT pd.placeholder_name,
    pd.source_type,
    count(DISTINCT wp.workflow_id) AS workflow_count,
    count(DISTINCT dsp.dialogue_step_id) AS dialogue_step_count,
    string_agg(DISTINCT w.workflow_name, ', '::text ORDER BY w.workflow_name) AS used_in_workflows
   FROM (((public.placeholder_definitions pd
     LEFT JOIN public.workflow_placeholders wp ON ((wp.placeholder_id = pd.placeholder_id)))
     LEFT JOIN public.dialogue_step_placeholders dsp ON ((dsp.placeholder_id = pd.placeholder_id)))
     LEFT JOIN public.workflows w ON ((w.workflow_id = wp.workflow_id)))
  GROUP BY pd.placeholder_id, pd.placeholder_name, pd.source_type
  ORDER BY (count(DISTINCT wp.workflow_id)) DESC, pd.placeholder_name;


ALTER TABLE public.v_placeholder_usage OWNER TO base_admin;

--
-- Name: VIEW v_placeholder_usage; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_placeholder_usage IS 'Shows usage statistics for each placeholder';


--
-- Name: v_posting_status_summary; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_posting_status_summary AS
 SELECT postings.posting_status,
    count(*) AS count,
    min(postings.first_seen_at) AS oldest,
    max(postings.last_seen_at) AS newest,
    (avg(postings.times_checked))::integer AS avg_checks
   FROM public.postings
  GROUP BY postings.posting_status
  ORDER BY
        CASE postings.posting_status
            WHEN 'active'::text THEN 1
            WHEN 'filled'::text THEN 2
            WHEN 'expired'::text THEN 3
            WHEN 'withdrawn'::text THEN 4
            WHEN 'archived'::text THEN 5
            ELSE NULL::integer
        END;


ALTER TABLE public.v_posting_status_summary OWNER TO base_admin;

--
-- Name: VIEW v_posting_status_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_posting_status_summary IS 'Summary of postings by status';


--
-- Name: v_processing_pipeline_status; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_processing_pipeline_status AS
 SELECT count(*) AS total_postings,
    count(*) FILTER (WHERE posting_processing_status.summary_extracted) AS with_summary,
    count(*) FILTER (WHERE posting_processing_status.skills_extracted) AS with_skills,
    count(*) FILTER (WHERE posting_processing_status.ihl_analyzed) AS with_ihl,
    count(*) FILTER (WHERE posting_processing_status.candidates_matched) AS with_matches,
    count(*) FILTER (WHERE posting_processing_status.processing_complete) AS complete,
    count(*) FILTER (WHERE (NOT posting_processing_status.processing_complete)) AS incomplete,
    round((((count(*) FILTER (WHERE posting_processing_status.processing_complete))::numeric / (NULLIF(count(*), 0))::numeric) * (100)::numeric), 2) AS completion_percentage
   FROM public.posting_processing_status;


ALTER TABLE public.v_processing_pipeline_status OWNER TO base_admin;

--
-- Name: VIEW v_processing_pipeline_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_processing_pipeline_status IS 'Overall pipeline processing statistics';


--
-- Name: workflow_conversations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_conversations (
    step_id integer NOT NULL,
    workflow_id integer NOT NULL,
    conversation_id integer NOT NULL,
    execution_order integer NOT NULL,
    execute_condition text DEFAULT 'always'::text,
    depends_on_step_id integer,
    on_success_action text DEFAULT 'continue'::text,
    on_failure_action text DEFAULT 'stop'::text,
    on_success_goto_order integer,
    on_failure_goto_order integer,
    max_retry_attempts integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    parallel_group integer,
    wait_for_group boolean DEFAULT false,
    CONSTRAINT workflow_conversations_execute_condition_check CHECK ((execute_condition = ANY (ARRAY['always'::text, 'on_success'::text, 'on_failure'::text]))),
    CONSTRAINT workflow_conversations_on_failure_action_check CHECK ((on_failure_action = ANY (ARRAY['stop'::text, 'retry'::text, 'skip_to'::text]))),
    CONSTRAINT workflow_conversations_on_success_action_check CHECK ((on_success_action = ANY (ARRAY['continue'::text, 'skip_to'::text, 'stop'::text])))
);


ALTER TABLE public.workflow_conversations OWNER TO base_admin;

--
-- Name: TABLE workflow_conversations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_conversations IS 'Cross-reference table orchestrating which conversations belong to which workflows. 
Each row defines: workflow X executes conversation Y at position Z with specified control flow.
This enables conversation reusability across multiple workflows.';


--
-- Name: COLUMN workflow_conversations.step_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.step_id IS 'Primary key for this workflow-conversation association';


--
-- Name: COLUMN workflow_conversations.workflow_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.workflow_id IS 'Which workflow this conversation belongs to';


--
-- Name: COLUMN workflow_conversations.conversation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.conversation_id IS 'Which conversation to execute (reusable across workflows)';


--
-- Name: COLUMN workflow_conversations.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.execution_order IS 'Sequential position within the workflow (1, 2, 3...)';


--
-- Name: COLUMN workflow_conversations.execute_condition; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.execute_condition IS 'When to execute: always, on_success, on_failure';


--
-- Name: COLUMN workflow_conversations.depends_on_step_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.depends_on_step_id IS 'Optional: this step depends on another step completing first';


--
-- Name: COLUMN workflow_conversations.on_success_action; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.on_success_action IS 'What to do if conversation succeeds: continue, skip_to, stop';


--
-- Name: COLUMN workflow_conversations.on_failure_action; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.on_failure_action IS 'What to do if conversation fails: stop, retry, skip_to';


--
-- Name: COLUMN workflow_conversations.on_success_goto_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.on_success_goto_order IS 'If on_success_action=skip_to, jump to this execution_order';


--
-- Name: COLUMN workflow_conversations.on_failure_goto_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.on_failure_goto_order IS 'If on_failure_action=skip_to, jump to this execution_order';


--
-- Name: COLUMN workflow_conversations.max_retry_attempts; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.max_retry_attempts IS 'Maximum retry attempts if on_failure_action=retry';


--
-- Name: COLUMN workflow_conversations.created_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.created_at IS 'Timestamp when this conversation step was created';


--
-- Name: COLUMN workflow_conversations.parallel_group; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.parallel_group IS 'Conversations with the same parallel_group number execute concurrently within the workflow.
NULL = execute serially (default behavior).
Example: parallel_group=1 for steps 2,3,4 means they run simultaneously.';


--
-- Name: COLUMN workflow_conversations.wait_for_group; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.wait_for_group IS 'If true, workflow waits for ALL conversations in this parallel_group to complete before continuing.
Used as synchronization barrier for parallel execution.';


--
-- Name: v_recipes_missing_sessions; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_recipes_missing_sessions AS
 SELECT r.workflow_id AS recipe_id,
    r.workflow_name AS recipe_name,
    r.workflow_description AS recipe_description,
    r.workflow_version AS recipe_version
   FROM public.workflows r
  WHERE ((r.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.workflow_conversations rs
          WHERE (rs.workflow_id = r.workflow_id)))))
  ORDER BY r.workflow_id;


ALTER TABLE public.v_recipes_missing_sessions OWNER TO base_admin;

--
-- Name: v_script_execution_history; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_script_execution_history AS
 SELECT s.script_name,
    s.script_version,
    e.execution_id,
    e.executed_at,
    e.status,
    e.duration_ms,
    e.error_message,
    (e.execution_context ->> 'workflow_id'::text) AS workflow_id
   FROM (public.script_executions e
     JOIN public.stored_scripts s ON ((e.script_id = s.script_id)))
  ORDER BY e.executed_at DESC;


ALTER TABLE public.v_script_execution_history OWNER TO base_admin;

--
-- Name: v_source_health; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_source_health AS
 SELECT js.source_name,
    js.is_active,
    js.last_fetch_at,
    js.total_jobs_fetched,
    count(jfr.fetch_run_id) AS total_fetch_runs,
    count(jfr.fetch_run_id) FILTER (WHERE (jfr.status = 'SUCCESS'::text)) AS successful_runs,
    count(jfr.fetch_run_id) FILTER (WHERE (jfr.status = 'ERROR'::text)) AS failed_runs,
    avg(jfr.duration_ms) FILTER (WHERE (jfr.status = 'SUCCESS'::text)) AS avg_fetch_duration_ms,
    sum(jfr.jobs_new) AS total_new_jobs,
    max(jfr.fetch_started_at) AS last_run_at
   FROM (public.job_sources js
     LEFT JOIN public.job_fetch_runs jfr ON ((jfr.source_id = js.source_id)))
  GROUP BY js.source_id, js.source_name, js.is_active, js.last_fetch_at, js.total_jobs_fetched;


ALTER TABLE public.v_source_health OWNER TO base_admin;

--
-- Name: VIEW v_source_health; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_source_health IS 'Health metrics for each job source';


--
-- Name: workflow_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_runs (
    workflow_run_id integer NOT NULL,
    workflow_id integer NOT NULL,
    test_case_id integer NOT NULL,
    batch_id integer NOT NULL,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    status text DEFAULT 'RUNNING'::text,
    total_sessions integer,
    completed_sessions integer DEFAULT 0,
    error_details text,
    output_data text,
    execution_mode text DEFAULT 'testing'::text,
    target_batch_count integer DEFAULT 5,
    batch_number integer DEFAULT 1,
    user_id integer,
    parallel_groups_active integer DEFAULT 0,
    parallel_groups_completed integer DEFAULT 0,
    CONSTRAINT recipe_runs_batch_number_check CHECK ((batch_number > 0)),
    CONSTRAINT recipe_runs_completed_sessions_check CHECK ((completed_sessions >= 0)),
    CONSTRAINT recipe_runs_execution_mode_check CHECK ((execution_mode = ANY (ARRAY['testing'::text, 'production'::text]))),
    CONSTRAINT recipe_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'PARTIAL'::text, 'ERROR'::text]))),
    CONSTRAINT recipe_runs_target_batch_count_check CHECK ((target_batch_count > 0)),
    CONSTRAINT recipe_runs_total_sessions_check CHECK ((total_sessions > 0))
);


ALTER TABLE public.workflow_runs OWNER TO base_admin;

--
-- Name: TABLE workflow_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_runs IS 'Test execution instances. Links recipe + variation + batch. Used in TESTING mode with synthetic variations.';


--
-- Name: COLUMN workflow_runs.output_data; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.output_data IS 'Final output from recipe execution (e.g., concise job description from Recipe 1114)';


--
-- Name: COLUMN workflow_runs.execution_mode; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.execution_mode IS 'Execution mode: "testing" (5 batches for validation) or "production" (1 batch for real data)';


--
-- Name: COLUMN workflow_runs.target_batch_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.target_batch_count IS 'How many batch runs should be completed for this variation (5 for testing, 1 for production)';


--
-- Name: COLUMN workflow_runs.batch_number; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.batch_number IS 'Which batch iteration this is (1-N where N = target_batch_count)';


--
-- Name: COLUMN workflow_runs.parallel_groups_active; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.parallel_groups_active IS 'Number of parallel conversation groups currently executing in this workflow run.';


--
-- Name: COLUMN workflow_runs.parallel_groups_completed; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.parallel_groups_completed IS 'Number of parallel conversation groups that have completed in this workflow run.';


--
-- Name: workflow_triggers; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_triggers (
    trigger_id integer NOT NULL,
    workflow_id integer,
    trigger_name character varying(255) NOT NULL,
    trigger_description text,
    trigger_type character varying(50) NOT NULL,
    schedule_cron character varying(100),
    schedule_timezone character varying(50) DEFAULT 'Europe/Berlin'::character varying,
    event_condition text,
    event_threshold integer DEFAULT 1,
    event_check_interval_minutes integer DEFAULT 5,
    enabled boolean DEFAULT true,
    priority integer DEFAULT 50,
    max_concurrent_runs integer DEFAULT 1,
    timeout_minutes integer DEFAULT 60,
    depends_on_trigger_ids integer[],
    run_after_workflow_ids integer[],
    min_interval_minutes integer,
    max_runs_per_day integer,
    max_runs_per_hour integer,
    default_parameters jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by character varying(100),
    last_triggered_at timestamp without time zone,
    next_scheduled_run timestamp without time zone,
    total_runs integer DEFAULT 0,
    successful_runs integer DEFAULT 0,
    failed_runs integer DEFAULT 0,
    CONSTRAINT workflow_triggers_trigger_type_check CHECK (((trigger_type)::text = ANY ((ARRAY['SCHEDULE'::character varying, 'EVENT'::character varying, 'MANUAL'::character varying, 'DEPENDENCY'::character varying])::text[])))
);


ALTER TABLE public.workflow_triggers OWNER TO base_admin;

--
-- Name: v_trigger_execution_history; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_trigger_execution_history AS
 SELECT t.trigger_name,
    w.workflow_name,
    te.triggered_at,
    te.status,
    te.trigger_reason,
    te.duration_ms,
    wr.status AS workflow_status,
    te.execution_id
   FROM (((public.trigger_executions te
     JOIN public.workflow_triggers t ON ((te.trigger_id = t.trigger_id)))
     JOIN public.workflows w ON ((t.workflow_id = w.workflow_id)))
     LEFT JOIN public.workflow_runs wr ON ((te.workflow_run_id = wr.workflow_run_id)))
  ORDER BY te.triggered_at DESC;


ALTER TABLE public.v_trigger_execution_history OWNER TO base_admin;

--
-- Name: v_trigger_health; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_trigger_health AS
 SELECT t.trigger_id,
    t.trigger_name,
    t.trigger_type,
    t.enabled,
    t.total_runs,
    t.successful_runs,
    t.failed_runs,
        CASE
            WHEN (t.total_runs = 0) THEN NULL::numeric
            ELSE round(((100.0 * (t.successful_runs)::numeric) / (t.total_runs)::numeric), 1)
        END AS success_rate_pct,
    t.last_triggered_at,
    age(CURRENT_TIMESTAMP, (t.last_triggered_at)::timestamp with time zone) AS time_since_last_run,
        CASE
            WHEN (NOT t.enabled) THEN '⏸️ DISABLED'::text
            WHEN (t.last_triggered_at IS NULL) THEN '🆕 NEVER RUN'::text
            WHEN (t.last_triggered_at < (CURRENT_TIMESTAMP - '1 day'::interval)) THEN '⚠️ STALE'::text
            WHEN (((t.failed_runs)::double precision / (NULLIF(t.total_runs, 0))::double precision) > (0.5)::double precision) THEN '❌ UNHEALTHY'::text
            ELSE '✅ HEALTHY'::text
        END AS health_status
   FROM public.workflow_triggers t
  ORDER BY t.enabled DESC, t.priority DESC;


ALTER TABLE public.v_trigger_health OWNER TO base_admin;

--
-- Name: v_triggers_ready_to_run; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_triggers_ready_to_run AS
 SELECT t.trigger_id,
    t.trigger_name,
    t.workflow_id,
    w.workflow_name,
    t.trigger_type,
    t.priority,
    t.next_scheduled_run,
    t.last_triggered_at,
        CASE
            WHEN ((t.trigger_type)::text = 'SCHEDULE'::text) THEN (('Next run: '::text || COALESCE((t.next_scheduled_run)::text, 'Not scheduled'::text)))::character varying
            WHEN ((t.trigger_type)::text = 'EVENT'::text) THEN ((('Checking condition every '::text || t.event_check_interval_minutes) || ' min'::text))::character varying
            ELSE t.trigger_type
        END AS status_text
   FROM (public.workflow_triggers t
     JOIN public.workflows w ON ((t.workflow_id = w.workflow_id)))
  WHERE ((t.enabled = true) AND ((((t.trigger_type)::text = 'SCHEDULE'::text) AND (t.next_scheduled_run <= CURRENT_TIMESTAMP)) OR ((t.trigger_type)::text = 'EVENT'::text)))
  ORDER BY t.priority DESC, t.next_scheduled_run;


ALTER TABLE public.v_triggers_ready_to_run OWNER TO base_admin;

--
-- Name: v_user_matched_postings; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_user_matched_postings AS
 SELECT p.posting_id,
    p.posting_name,
    p.organization_name,
    p.location_city,
    p.employment_career_level,
    p.posting_status,
    p.ihl_score,
    p.ihl_category,
    p.fetched_at,
    p.last_seen_at,
    up.user_id,
    up.user_name,
    (((
        CASE
            WHEN (p.employment_career_level = ANY (up.preferred_career_levels)) THEN 30
            ELSE 0
        END +
        CASE
            WHEN (p.location_city = ANY (up.preferred_locations)) THEN 30
            ELSE 0
        END) +
        CASE
            WHEN ((p.ihl_score IS NOT NULL) AND (p.ihl_score <= 60)) THEN 20
            ELSE 0
        END) +
        CASE
            WHEN (p.posting_status = 'active'::text) THEN 20
            ELSE 0
        END) AS match_score,
    array_remove(ARRAY[
        CASE
            WHEN (p.employment_career_level = ANY (up.preferred_career_levels)) THEN 'Career Level Match'::text
            ELSE NULL::text
        END,
        CASE
            WHEN (p.location_city = ANY (up.preferred_locations)) THEN 'Location Match'::text
            ELSE NULL::text
        END,
        CASE
            WHEN ((p.ihl_score IS NOT NULL) AND (p.ihl_score <= 60)) THEN 'Low IHL (Open Position)'::text
            ELSE NULL::text
        END,
        CASE
            WHEN (p.posting_status = 'active'::text) THEN 'Currently Active'::text
            ELSE NULL::text
        END], NULL::text) AS match_reasons
   FROM (public.postings p
     CROSS JOIN public.user_preferences up)
  WHERE ((up.is_active = true) AND (p.posting_status = ANY (ARRAY['active'::text, 'filled'::text])) AND ((up.preferred_career_levels IS NULL) OR (p.employment_career_level = ANY (up.preferred_career_levels))) AND ((up.preferred_locations IS NULL) OR (p.location_city = ANY (up.preferred_locations))))
  ORDER BY (((
        CASE
            WHEN (p.employment_career_level = ANY (up.preferred_career_levels)) THEN 30
            ELSE 0
        END +
        CASE
            WHEN (p.location_city = ANY (up.preferred_locations)) THEN 30
            ELSE 0
        END) +
        CASE
            WHEN ((p.ihl_score IS NOT NULL) AND (p.ihl_score <= 60)) THEN 20
            ELSE 0
        END) +
        CASE
            WHEN (p.posting_status = 'active'::text) THEN 20
            ELSE 0
        END) DESC, p.fetched_at DESC;


ALTER TABLE public.v_user_matched_postings OWNER TO base_admin;

--
-- Name: VIEW v_user_matched_postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_user_matched_postings IS 'Jobs matching user preferences with scoring and reasons';


--
-- Name: v_user_dashboard; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_user_dashboard AS
 SELECT up.user_id,
    up.user_name,
    count(DISTINCT p.posting_id) AS total_matches,
    count(DISTINCT p.posting_id) FILTER (WHERE (p.posting_status = 'active'::text)) AS active_matches,
    count(DISTINCT p.posting_id) FILTER (WHERE (p.ihl_score <= 60)) AS open_positions,
    count(DISTINCT p.posting_id) FILTER (WHERE (p.fetched_at > (CURRENT_DATE - '7 days'::interval))) AS new_this_week,
    (avg(p.ihl_score) FILTER (WHERE (p.posting_status = 'active'::text)))::integer AS avg_ihl_active
   FROM ((public.user_preferences up
     LEFT JOIN public.v_user_matched_postings vump ON ((vump.user_id = up.user_id)))
     LEFT JOIN public.postings p ON ((p.posting_id = vump.posting_id)))
  WHERE (up.is_active = true)
  GROUP BY up.user_id, up.user_name;


ALTER TABLE public.v_user_dashboard OWNER TO base_admin;

--
-- Name: VIEW v_user_dashboard; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_user_dashboard IS 'User-level statistics for matched jobs';


--
-- Name: v_workflow_placeholder_requirements; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_workflow_placeholder_requirements AS
 SELECT w.workflow_id,
    w.workflow_name,
    pd.placeholder_name,
    pd.source_type,
    COALESCE(((pd.source_table || '.'::text) || pd.source_column), pd.source_query, 'dynamic'::text) AS source_location,
    wp.is_required,
    pd.description
   FROM ((public.workflow_placeholders wp
     JOIN public.workflows w ON ((w.workflow_id = wp.workflow_id)))
     JOIN public.placeholder_definitions pd ON ((pd.placeholder_id = wp.placeholder_id)))
  ORDER BY w.workflow_id, wp.is_required DESC, pd.placeholder_name;


ALTER TABLE public.v_workflow_placeholder_requirements OWNER TO base_admin;

--
-- Name: VIEW v_workflow_placeholder_requirements; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_workflow_placeholder_requirements IS 'Shows all placeholder requirements for each workflow';


--
-- Name: v_workflow_schedule_24h; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_workflow_schedule_24h AS
 SELECT t.trigger_name,
    w.workflow_name,
    t.next_scheduled_run,
    t.priority,
    t.schedule_cron,
    age((t.next_scheduled_run)::timestamp with time zone, CURRENT_TIMESTAMP) AS time_until_run
   FROM (public.workflow_triggers t
     JOIN public.workflows w ON ((t.workflow_id = w.workflow_id)))
  WHERE ((t.enabled = true) AND ((t.trigger_type)::text = 'SCHEDULE'::text) AND ((t.next_scheduled_run >= CURRENT_TIMESTAMP) AND (t.next_scheduled_run <= (CURRENT_TIMESTAMP + '24:00:00'::interval))))
  ORDER BY t.next_scheduled_run;


ALTER TABLE public.v_workflow_schedule_24h OWNER TO base_admin;

--
-- Name: v_workflow_script_dependencies; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_workflow_script_dependencies AS
 SELECT w.workflow_id,
    w.workflow_name,
    ws.execution_order,
    s.script_id,
    s.script_name,
    s.script_version,
    s.is_production,
    ws.is_required
   FROM ((public.workflow_scripts ws
     JOIN public.workflows w ON ((ws.workflow_id = w.workflow_id)))
     JOIN public.stored_scripts s ON ((ws.script_id = s.script_id)))
  WHERE (s.is_current_version = true)
  ORDER BY w.workflow_id, ws.execution_order;


ALTER TABLE public.v_workflow_script_dependencies OWNER TO base_admin;

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
-- Name: validated_prompts; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.validated_prompts (
    validated_prompt_id integer DEFAULT nextval('public.validated_prompts_validated_prompt_id_seq'::regclass) NOT NULL,
    validated_prompt_name text NOT NULL,
    capability_description text,
    capability_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    enabled boolean DEFAULT true,
    capability_name text NOT NULL,
    prompt text,
    response text NOT NULL,
    review_notes text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.validated_prompts OWNER TO base_admin;

--
-- Name: TABLE validated_prompts; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.validated_prompts IS 'Manually-tested prompt-response pairs (scrapbook of validated prompts).
Each entry is a canonical example of a specific capability test case with known-good prompt and expected response.
Used for: regression testing, LLM comparison, capability validation.

Formerly: canonicals → validated_prompts (migration 016).
Updated: facet_name → capability_name (migration 029).

Pattern: validated_prompt_id (INTEGER PK) + validated_prompt_name (TEXT UNIQUE).
Links to capabilities table via capability_id and capability_name.';


--
-- Name: COLUMN validated_prompts.validated_prompt_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.validated_prompt_id IS 'Primary key - unique identifier for this validated prompt';


--
-- Name: COLUMN validated_prompts.validated_prompt_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.validated_prompt_name IS 'Unique name for this validated prompt (e.g., ce_clean_extract, dynatax_skills_categorizer)';


--
-- Name: COLUMN validated_prompts.capability_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.capability_description IS 'Description of what this validated prompt demonstrates or achieves';


--
-- Name: COLUMN validated_prompts.capability_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.capability_id IS 'Foreign key to capabilities table - links this prompt to its cognitive capability';


--
-- Name: COLUMN validated_prompts.capability_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.capability_name IS 'Name of the capability being tested (references capabilities.capability_name). Formerly facet_name.';


--
-- Name: COLUMN validated_prompts.prompt; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.prompt IS 'The validated prompt text - proven to work through manual testing';


--
-- Name: COLUMN validated_prompts.response; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.response IS 'Expected/reference response format - what good output looks like';


--
-- Name: COLUMN validated_prompts.review_notes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.validated_prompts.review_notes IS 'Notes from manual testing sessions, learnings, edge cases discovered';


--
-- Name: variations_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.variations_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.variations_history_history_id_seq OWNER TO base_admin;

--
-- Name: variations_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.variations_history_history_id_seq OWNED BY public.test_cases_history.history_id;


--
-- Name: workflow_conversations_step_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_conversations_step_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_conversations_step_id_seq OWNER TO base_admin;

--
-- Name: workflow_conversations_step_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_conversations_step_id_seq OWNED BY public.workflow_conversations.step_id;


--
-- Name: workflow_dependencies; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_dependencies (
    dependency_id integer NOT NULL,
    workflow_id integer,
    depends_on_workflow_id integer,
    dependency_type character varying(50),
    pass_output_as_input boolean DEFAULT false,
    output_mapping jsonb,
    CONSTRAINT workflow_dependencies_dependency_type_check CHECK (((dependency_type)::text = ANY ((ARRAY['MUST_COMPLETE'::character varying, 'MUST_SUCCEED'::character varying, 'OPTIONAL'::character varying])::text[])))
);


ALTER TABLE public.workflow_dependencies OWNER TO base_admin;

--
-- Name: workflow_dependencies_dependency_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_dependencies_dependency_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_dependencies_dependency_id_seq OWNER TO base_admin;

--
-- Name: workflow_dependencies_dependency_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_dependencies_dependency_id_seq OWNED BY public.workflow_dependencies.dependency_id;


--
-- Name: workflow_runs_workflow_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_runs_workflow_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_runs_workflow_run_id_seq OWNER TO base_admin;

--
-- Name: workflow_runs_workflow_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_runs_workflow_run_id_seq OWNED BY public.workflow_runs.workflow_run_id;


--
-- Name: workflow_triggers_trigger_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_triggers_trigger_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_triggers_trigger_id_seq OWNER TO base_admin;

--
-- Name: workflow_triggers_trigger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_triggers_trigger_id_seq OWNED BY public.workflow_triggers.trigger_id;


--
-- Name: workflows_workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflows_workflow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflows_workflow_id_seq OWNER TO base_admin;

--
-- Name: workflows_workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflows_workflow_id_seq OWNED BY public.workflows.workflow_id;


--
-- Name: batches batch_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches ALTER COLUMN batch_id SET DEFAULT nextval('public.batches_batch_id_seq'::regclass);


--
-- Name: capabilities_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.capabilities_history ALTER COLUMN history_id SET DEFAULT nextval('public.capabilities_history_history_id_seq'::regclass);


--
-- Name: conversation_dialogue dialogue_step_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue ALTER COLUMN dialogue_step_id SET DEFAULT nextval('public.conversation_dialogue_dialogue_step_id_seq'::regclass);


--
-- Name: conversations_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations_history ALTER COLUMN history_id SET DEFAULT nextval('public.sessions_history_history_id_seq'::regclass);


--
-- Name: instruction_step_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_step_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.instruction_branch_executions_execution_id_seq'::regclass);


--
-- Name: instructions_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions_history ALTER COLUMN history_id SET DEFAULT nextval('public.instructions_history_history_id_seq'::regclass);


--
-- Name: migration_log migration_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.migration_log ALTER COLUMN migration_id SET DEFAULT nextval('public.migration_log_migration_id_seq'::regclass);


--
-- Name: production_runs production_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs ALTER COLUMN production_run_id SET DEFAULT nextval('public.production_runs_production_run_id_seq'::regclass);


--
-- Name: profile_certifications certification_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_certifications ALTER COLUMN certification_id SET DEFAULT nextval('public.profile_certifications_certification_id_seq'::regclass);


--
-- Name: profile_education education_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_education ALTER COLUMN education_id SET DEFAULT nextval('public.profile_education_education_id_seq'::regclass);


--
-- Name: profile_job_matches match_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches ALTER COLUMN match_id SET DEFAULT nextval('public.profile_job_matches_match_id_seq'::regclass);


--
-- Name: profile_languages language_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_languages ALTER COLUMN language_id SET DEFAULT nextval('public.profile_languages_language_id_seq'::regclass);


--
-- Name: profile_work_history work_history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history ALTER COLUMN work_history_id SET DEFAULT nextval('public.profile_work_history_work_history_id_seq'::regclass);


--
-- Name: profiles profile_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles ALTER COLUMN profile_id SET DEFAULT nextval('public.profiles_profile_id_seq'::regclass);


--
-- Name: script_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.script_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.script_executions_execution_id_seq'::regclass);


--
-- Name: skill_occurrences occurrence_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences ALTER COLUMN occurrence_id SET DEFAULT nextval('public.skill_occurrences_occurrence_id_seq'::regclass);


--
-- Name: stored_scripts script_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.stored_scripts ALTER COLUMN script_id SET DEFAULT nextval('public.stored_scripts_script_id_seq'::regclass);


--
-- Name: test_cases_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.test_cases_history ALTER COLUMN history_id SET DEFAULT nextval('public.variations_history_history_id_seq'::regclass);


--
-- Name: trigger_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.trigger_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.trigger_executions_execution_id_seq'::regclass);


--
-- Name: validated_prompts_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.validated_prompts_history ALTER COLUMN history_id SET DEFAULT nextval('public.canonicals_history_history_id_seq'::regclass);


--
-- Name: workflow_conversations step_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations ALTER COLUMN step_id SET DEFAULT nextval('public.workflow_conversations_step_id_seq'::regclass);


--
-- Name: workflow_dependencies dependency_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies ALTER COLUMN dependency_id SET DEFAULT nextval('public.workflow_dependencies_dependency_id_seq'::regclass);


--
-- Name: workflow_runs workflow_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs ALTER COLUMN workflow_run_id SET DEFAULT nextval('public.workflow_runs_workflow_run_id_seq'::regclass);


--
-- Name: workflow_triggers trigger_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers ALTER COLUMN trigger_id SET DEFAULT nextval('public.workflow_triggers_trigger_id_seq'::regclass);


--
-- Name: workflows workflow_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows ALTER COLUMN workflow_id SET DEFAULT nextval('public.workflows_workflow_id_seq'::regclass);


--
-- Name: workflows_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows_history ALTER COLUMN history_id SET DEFAULT nextval('public.recipes_history_history_id_seq'::regclass);


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
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (batch_id);


--
-- Name: validated_prompts_history canonicals_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.validated_prompts_history
    ADD CONSTRAINT canonicals_history_pkey PRIMARY KEY (history_id);


--
-- Name: capabilities capabilities_capability_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_capability_name_unique UNIQUE (capability_name);


--
-- Name: capabilities_history capabilities_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.capabilities_history
    ADD CONSTRAINT capabilities_history_pkey PRIMARY KEY (history_id);


--
-- Name: capabilities capabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_pkey PRIMARY KEY (capability_id);


--
-- Name: conversation_dialogue conversation_dialogue_conversation_id_execution_order_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue
    ADD CONSTRAINT conversation_dialogue_conversation_id_execution_order_key UNIQUE (conversation_id, execution_order);


--
-- Name: conversation_dialogue conversation_dialogue_dialogue_step_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue
    ADD CONSTRAINT conversation_dialogue_dialogue_step_name_key UNIQUE (dialogue_step_name);


--
-- Name: conversation_dialogue conversation_dialogue_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue
    ADD CONSTRAINT conversation_dialogue_pkey PRIMARY KEY (dialogue_step_id);


--
-- Name: conversation_runs conversation_runs_conversation_run_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_runs
    ADD CONSTRAINT conversation_runs_conversation_run_name_key UNIQUE (conversation_run_name);


--
-- Name: conversation_runs conversation_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_runs
    ADD CONSTRAINT conversation_runs_pkey PRIMARY KEY (conversation_run_id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id);


--
-- Name: dialogue_step_placeholders dialogue_step_placeholders_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.dialogue_step_placeholders
    ADD CONSTRAINT dialogue_step_placeholders_pkey PRIMARY KEY (dialogue_step_id, placeholder_id);


--
-- Name: human_tasks human_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_pkey PRIMARY KEY (task_id);


--
-- Name: instruction_step_executions instruction_branch_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_step_executions
    ADD CONSTRAINT instruction_branch_executions_pkey PRIMARY KEY (execution_id);


--
-- Name: instruction_steps instruction_steps_instruction_step_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT instruction_steps_instruction_step_name_key UNIQUE (instruction_step_name);


--
-- Name: instruction_steps instruction_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT instruction_steps_pkey PRIMARY KEY (instruction_step_id);


--
-- Name: instructions instructions_conversation_id_step_number_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_conversation_id_step_number_key UNIQUE (conversation_id, step_number);


--
-- Name: instructions_history instructions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions_history
    ADD CONSTRAINT instructions_history_pkey PRIMARY KEY (history_id);


--
-- Name: instructions instructions_new_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_new_pkey PRIMARY KEY (instruction_id);


--
-- Name: interaction_lineage interaction_lineage_downstream_interaction_id_upstream_inte_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_lineage
    ADD CONSTRAINT interaction_lineage_downstream_interaction_id_upstream_inte_key UNIQUE (downstream_interaction_id, upstream_interaction_id, influence_type);


--
-- Name: interaction_lineage interaction_lineage_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_lineage
    ADD CONSTRAINT interaction_lineage_pkey PRIMARY KEY (lineage_id);


--
-- Name: job_fetch_runs job_fetch_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_fetch_runs
    ADD CONSTRAINT job_fetch_runs_pkey PRIMARY KEY (fetch_run_id);


--
-- Name: job_skills job_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_pkey PRIMARY KEY (job_skill_id);


--
-- Name: job_skills job_skills_posting_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_posting_id_skill_id_key UNIQUE (posting_id, skill_id);


--
-- Name: job_sources job_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_sources
    ADD CONSTRAINT job_sources_pkey PRIMARY KEY (source_id);


--
-- Name: llm_interactions llm_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.llm_interactions
    ADD CONSTRAINT llm_interactions_pkey PRIMARY KEY (interaction_id);


--
-- Name: migration_log migration_log_migration_number_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.migration_log
    ADD CONSTRAINT migration_log_migration_number_key UNIQUE (migration_number);


--
-- Name: migration_log migration_log_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.migration_log
    ADD CONSTRAINT migration_log_pkey PRIMARY KEY (migration_id);


--
-- Name: organizations organizations_organization_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_organization_name_key UNIQUE (organization_name);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (organization_id);


--
-- Name: placeholder_definitions placeholder_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.placeholder_definitions
    ADD CONSTRAINT placeholder_definitions_pkey PRIMARY KEY (placeholder_id);


--
-- Name: placeholder_definitions placeholder_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.placeholder_definitions
    ADD CONSTRAINT placeholder_name_unique UNIQUE (placeholder_name);


--
-- Name: posting_field_mappings posting_field_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_field_mappings
    ADD CONSTRAINT posting_field_mappings_pkey PRIMARY KEY (mapping_id);


--
-- Name: posting_field_mappings posting_field_mappings_source_id_source_field_name_target_f_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_field_mappings
    ADD CONSTRAINT posting_field_mappings_source_id_source_field_name_target_f_key UNIQUE (source_id, source_field_name, target_field_name);


--
-- Name: posting_processing_status posting_processing_status_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_pkey PRIMARY KEY (posting_id);


--
-- Name: posting_sources posting_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_sources
    ADD CONSTRAINT posting_sources_pkey PRIMARY KEY (source_id);


--
-- Name: posting_sources posting_sources_source_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_sources
    ADD CONSTRAINT posting_sources_source_name_key UNIQUE (source_name);


--
-- Name: postings postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_pkey PRIMARY KEY (posting_id);


--
-- Name: production_runs production_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_pkey PRIMARY KEY (production_run_id);


--
-- Name: production_runs production_runs_recipe_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_recipe_id_posting_id_key UNIQUE (workflow_id, posting_name);


--
-- Name: profile_certifications profile_certifications_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_certifications
    ADD CONSTRAINT profile_certifications_pkey PRIMARY KEY (certification_id);


--
-- Name: profile_education profile_education_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_education
    ADD CONSTRAINT profile_education_pkey PRIMARY KEY (education_id);


--
-- Name: profile_job_matches profile_job_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches
    ADD CONSTRAINT profile_job_matches_pkey PRIMARY KEY (match_id);


--
-- Name: profile_job_matches profile_job_matches_profile_id_job_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches
    ADD CONSTRAINT profile_job_matches_profile_id_job_id_key UNIQUE (profile_id, posting_name);


--
-- Name: profile_languages profile_languages_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_languages
    ADD CONSTRAINT profile_languages_pkey PRIMARY KEY (language_id);


--
-- Name: profile_skills profile_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_pkey PRIMARY KEY (profile_skill_id);


--
-- Name: profile_skills profile_skills_profile_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_profile_id_skill_id_key UNIQUE (profile_id, skill_id);


--
-- Name: profile_work_history profile_work_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history
    ADD CONSTRAINT profile_work_history_pkey PRIMARY KEY (work_history_id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (profile_id);


--
-- Name: workflows_history recipes_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows_history
    ADD CONSTRAINT recipes_history_pkey PRIMARY KEY (history_id);


--
-- Name: script_executions script_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.script_executions
    ADD CONSTRAINT script_executions_pkey PRIMARY KEY (execution_id);


--
-- Name: conversations_history sessions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations_history
    ADD CONSTRAINT sessions_history_pkey PRIMARY KEY (history_id);


--
-- Name: skill_aliases skill_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases
    ADD CONSTRAINT skill_aliases_pkey PRIMARY KEY (skill_id);


--
-- Name: skill_aliases skill_aliases_skill_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases
    ADD CONSTRAINT skill_aliases_skill_name_unique UNIQUE (skill_name);


--
-- Name: skill_hierarchy skill_hierarchy_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_pkey PRIMARY KEY (skill_id, parent_skill_id);


--
-- Name: skill_occurrences skill_occurrences_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences
    ADD CONSTRAINT skill_occurrences_pkey PRIMARY KEY (occurrence_id);


--
-- Name: skills_pending_taxonomy skills_pending_taxonomy_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skills_pending_taxonomy
    ADD CONSTRAINT skills_pending_taxonomy_pkey PRIMARY KEY (pending_skill_id);


--
-- Name: skills_pending_taxonomy skills_pending_taxonomy_raw_skill_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skills_pending_taxonomy
    ADD CONSTRAINT skills_pending_taxonomy_raw_skill_name_unique UNIQUE (raw_skill_name);


--
-- Name: stored_scripts stored_scripts_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.stored_scripts
    ADD CONSTRAINT stored_scripts_pkey PRIMARY KEY (script_id);


--
-- Name: stored_scripts stored_scripts_script_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.stored_scripts
    ADD CONSTRAINT stored_scripts_script_name_key UNIQUE (script_name);


--
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (test_case_id);


--
-- Name: test_cases test_cases_test_case_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_test_case_name_key UNIQUE (test_case_name);


--
-- Name: trigger_executions trigger_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.trigger_executions
    ADD CONSTRAINT trigger_executions_pkey PRIMARY KEY (execution_id);


--
-- Name: user_posting_preferences user_posting_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_preferences
    ADD CONSTRAINT user_posting_preferences_pkey PRIMARY KEY (preference_id);


--
-- Name: user_posting_preferences user_posting_preferences_user_id_preference_type_preference_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_preferences
    ADD CONSTRAINT user_posting_preferences_user_id_preference_type_preference_key UNIQUE (user_id, preference_type, preference_value);


--
-- Name: user_preferences user_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_pkey PRIMARY KEY (user_id);


--
-- Name: user_saved_postings user_saved_postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_saved_postings
    ADD CONSTRAINT user_saved_postings_pkey PRIMARY KEY (user_id, posting_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: validated_prompts validated_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.validated_prompts
    ADD CONSTRAINT validated_prompts_pkey PRIMARY KEY (validated_prompt_id);


--
-- Name: validated_prompts validated_prompts_validated_prompt_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.validated_prompts
    ADD CONSTRAINT validated_prompts_validated_prompt_name_unique UNIQUE (validated_prompt_name);


--
-- Name: test_cases_history variations_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.test_cases_history
    ADD CONSTRAINT variations_history_pkey PRIMARY KEY (history_id);


--
-- Name: workflow_conversations workflow_conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations
    ADD CONSTRAINT workflow_conversations_pkey PRIMARY KEY (step_id);


--
-- Name: workflow_conversations workflow_conversations_workflow_id_execution_order_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations
    ADD CONSTRAINT workflow_conversations_workflow_id_execution_order_key UNIQUE (workflow_id, execution_order);


--
-- Name: workflow_dependencies workflow_dependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies
    ADD CONSTRAINT workflow_dependencies_pkey PRIMARY KEY (dependency_id);


--
-- Name: workflow_dependencies workflow_dependencies_workflow_id_depends_on_workflow_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies
    ADD CONSTRAINT workflow_dependencies_workflow_id_depends_on_workflow_id_key UNIQUE (workflow_id, depends_on_workflow_id);


--
-- Name: workflow_placeholders workflow_placeholders_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_placeholders
    ADD CONSTRAINT workflow_placeholders_pkey PRIMARY KEY (workflow_id, placeholder_id);


--
-- Name: workflow_runs workflow_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_pkey PRIMARY KEY (workflow_run_id);


--
-- Name: workflow_scripts workflow_scripts_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_scripts
    ADD CONSTRAINT workflow_scripts_pkey PRIMARY KEY (workflow_id, script_id);


--
-- Name: workflow_triggers workflow_triggers_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers
    ADD CONSTRAINT workflow_triggers_pkey PRIMARY KEY (trigger_id);


--
-- Name: workflow_triggers workflow_triggers_workflow_id_trigger_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers
    ADD CONSTRAINT workflow_triggers_workflow_id_trigger_name_key UNIQUE (workflow_id, trigger_name);


--
-- Name: workflows workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_pkey PRIMARY KEY (workflow_id);


--
-- Name: workflows workflows_workflow_name_workflow_version_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_workflow_name_workflow_version_key UNIQUE (workflow_name, workflow_version);


--
-- Name: idx_actors_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_enabled ON public.actors USING btree (enabled);


--
-- Name: idx_actors_execution_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actors_execution_type ON public.actors USING btree (execution_type) WHERE (enabled = true);


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
-- Name: idx_batches_tags; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_batches_tags ON public.batches USING gin (tags);


--
-- Name: idx_batches_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_batches_type ON public.batches USING btree (batch_type) WHERE (enabled = true);


--
-- Name: idx_branch_exec_branch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_branch_exec_branch ON public.instruction_step_executions USING btree (instruction_step_id);


--
-- Name: idx_branch_exec_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_branch_exec_run ON public.instruction_step_executions USING btree (instruction_run_id);


--
-- Name: idx_capabilities_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_capabilities_enabled ON public.capabilities USING btree (enabled);


--
-- Name: idx_capabilities_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_capabilities_parent ON public.capabilities USING btree (parent_capability_name);


--
-- Name: idx_certifications_expiration; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_expiration ON public.profile_certifications USING btree (expiration_date);


--
-- Name: idx_certifications_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_profile ON public.profile_certifications USING btree (profile_id);


--
-- Name: idx_conversation_dialogue_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversation_dialogue_actor ON public.conversation_dialogue USING btree (actor_id);


--
-- Name: idx_conversation_dialogue_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversation_dialogue_conversation ON public.conversation_dialogue USING btree (conversation_id) WHERE (enabled = true);


--
-- Name: idx_conversation_dialogue_order; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversation_dialogue_order ON public.conversation_dialogue USING btree (conversation_id, execution_order);


--
-- Name: idx_conversation_runs_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversation_runs_conversation ON public.conversation_runs USING btree (conversation_id);


--
-- Name: idx_conversation_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversation_runs_status ON public.conversation_runs USING btree (status);


--
-- Name: idx_conversations_actor_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversations_actor_id ON public.conversations USING btree (actor_id);


--
-- Name: idx_conversations_canonical_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversations_canonical_name ON public.conversations USING btree (canonical_name);


--
-- Name: idx_conversations_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversations_enabled ON public.conversations USING btree (enabled);


--
-- Name: idx_conversations_validated_prompt_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_conversations_validated_prompt_id ON public.conversations USING btree (validated_prompt_id);


--
-- Name: idx_dialogue_step_placeholders_required; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_dialogue_step_placeholders_required ON public.dialogue_step_placeholders USING btree (dialogue_step_id, is_required);


--
-- Name: idx_dialogue_step_placeholders_step; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_dialogue_step_placeholders_step ON public.dialogue_step_placeholders USING btree (dialogue_step_id);


--
-- Name: idx_education_degree; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_education_degree ON public.profile_education USING btree (degree_type);


--
-- Name: idx_education_graduation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_education_graduation ON public.profile_education USING btree (graduation_year);


--
-- Name: idx_education_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_education_profile ON public.profile_education USING btree (profile_id);


--
-- Name: idx_fetch_runs_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_fetch_runs_source ON public.job_fetch_runs USING btree (source_id, fetch_started_at DESC);


--
-- Name: idx_fetch_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_fetch_runs_status ON public.job_fetch_runs USING btree (status, fetch_started_at DESC);


--
-- Name: idx_fetch_runs_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_fetch_runs_workflow ON public.job_fetch_runs USING btree (workflow_run_id);


--
-- Name: idx_field_mappings_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_field_mappings_source ON public.posting_field_mappings USING btree (source_id);


--
-- Name: idx_human_tasks_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_human_tasks_actor ON public.human_tasks USING btree (actor_name, status);


--
-- Name: idx_human_tasks_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_human_tasks_status ON public.human_tasks USING btree (status, created_at);


--
-- Name: idx_instruction_steps_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_steps_enabled ON public.instruction_steps USING btree (enabled);


--
-- Name: idx_instruction_steps_instruction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_steps_instruction ON public.instruction_steps USING btree (instruction_id) WHERE (enabled = true);


--
-- Name: idx_instruction_steps_priority; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_steps_priority ON public.instruction_steps USING btree (instruction_id, branch_priority DESC) WHERE (enabled = true);


--
-- Name: idx_instructions_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_conversation ON public.instructions USING btree (conversation_id);


--
-- Name: idx_instructions_delegate_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_delegate_actor ON public.instructions USING btree (delegate_actor_id) WHERE (delegate_actor_id IS NOT NULL);


--
-- Name: idx_instructions_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_enabled ON public.instructions USING btree (enabled);


--
-- Name: idx_job_skills_importance; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_importance ON public.job_skills USING btree (importance);


--
-- Name: idx_job_skills_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_posting ON public.job_skills USING btree (posting_id);


--
-- Name: idx_job_skills_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_skill ON public.job_skills USING btree (skill_id);


--
-- Name: idx_job_skills_weight; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_weight ON public.job_skills USING btree (weight);


--
-- Name: idx_job_sources_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_sources_active ON public.job_sources USING btree (is_active, priority);


--
-- Name: idx_job_sources_next_fetch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_sources_next_fetch ON public.job_sources USING btree (next_fetch_at) WHERE (is_active = true);


--
-- Name: idx_languages_proficiency; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_languages_proficiency ON public.profile_languages USING btree (proficiency_level);


--
-- Name: idx_languages_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_languages_profile ON public.profile_languages USING btree (profile_id);


--
-- Name: idx_lineage_downstream; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_lineage_downstream ON public.interaction_lineage USING btree (downstream_interaction_id);


--
-- Name: idx_lineage_placeholder; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_lineage_placeholder ON public.interaction_lineage USING btree (placeholder_used) WHERE (placeholder_used IS NOT NULL);


--
-- Name: idx_lineage_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_lineage_type ON public.interaction_lineage USING btree (influence_type);


--
-- Name: idx_lineage_upstream; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_lineage_upstream ON public.interaction_lineage USING btree (upstream_interaction_id);


--
-- Name: idx_llm_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_actor ON public.llm_interactions USING btree (actor_id);


--
-- Name: idx_llm_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_conversation ON public.llm_interactions USING btree (conversation_run_id);


--
-- Name: idx_llm_conversation_order; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_conversation_order ON public.llm_interactions USING btree (conversation_run_id, execution_order);


--
-- Name: idx_llm_dialogue_step; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_dialogue_step ON public.llm_interactions USING btree (dialogue_step_run_id) WHERE (dialogue_step_run_id IS NOT NULL);


--
-- Name: idx_llm_interactions_workflow_run_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_interactions_workflow_run_id ON public.llm_interactions USING btree (workflow_run_id);


--
-- Name: INDEX idx_llm_interactions_workflow_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_llm_interactions_workflow_run_id IS 'Speed up llm_interactions → workflow_runs joins';


--
-- Name: idx_llm_prompt_fts; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_prompt_fts ON public.llm_interactions USING gin (to_tsvector('english'::regconfig, prompt_sent));


--
-- Name: idx_llm_response_fts; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_response_fts ON public.llm_interactions USING gin (to_tsvector('english'::regconfig, COALESCE(response_received, ''::text)));


--
-- Name: idx_llm_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_status ON public.llm_interactions USING btree (status);


--
-- Name: idx_llm_timestamps; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_timestamps ON public.llm_interactions USING btree (started_at, completed_at);


--
-- Name: idx_llm_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_workflow ON public.llm_interactions USING btree (workflow_run_id);


--
-- Name: idx_matches_job; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_job ON public.profile_job_matches USING btree (posting_name);


--
-- Name: idx_matches_matched_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_matched_at ON public.profile_job_matches USING btree (matched_at DESC);


--
-- Name: idx_matches_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_profile ON public.profile_job_matches USING btree (profile_id);


--
-- Name: idx_matches_quality; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_quality ON public.profile_job_matches USING btree (match_quality);


--
-- Name: idx_matches_score; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_score ON public.profile_job_matches USING btree (overall_match_score DESC);


--
-- Name: idx_matches_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_matches_status ON public.profile_job_matches USING btree (match_status);


--
-- Name: idx_migration_log_date; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_migration_log_date ON public.migration_log USING btree (applied_at DESC);


--
-- Name: idx_migration_log_number; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_migration_log_number ON public.migration_log USING btree (migration_number);


--
-- Name: idx_migration_log_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_migration_log_status ON public.migration_log USING btree (status);


--
-- Name: idx_organizations_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_organizations_name ON public.organizations USING btree (organization_name);


--
-- Name: idx_placeholder_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_placeholder_name ON public.placeholder_definitions USING btree (placeholder_name);


--
-- Name: idx_placeholder_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_placeholder_source ON public.placeholder_definitions USING btree (source_type, source_table);


--
-- Name: idx_posting_processing_incomplete; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_processing_incomplete ON public.posting_processing_status USING btree (posting_id) WHERE (NOT processing_complete);


--
-- Name: idx_posting_processing_stages; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_processing_stages ON public.posting_processing_status USING btree (summary_extracted, skills_extracted, ihl_analyzed, candidates_matched);


--
-- Name: idx_posting_sources_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_sources_active ON public.posting_sources USING btree (is_active);


--
-- Name: idx_postings_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_active ON public.postings USING btree (posting_status) WHERE (posting_status = 'active'::text);


--
-- Name: idx_postings_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_enabled ON public.postings USING btree (enabled);


--
-- Name: idx_postings_external_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_external_id ON public.postings USING btree (source_id, external_job_id);


--
-- Name: idx_postings_external_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_external_unique ON public.postings USING btree (source_id, external_job_id) WHERE (external_job_id IS NOT NULL);


--
-- Name: idx_postings_fetch_hash; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_fetch_hash ON public.postings USING btree (fetch_hash);


--
-- Name: idx_postings_fetch_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_fetch_run ON public.postings USING btree (fetch_run_id);


--
-- Name: idx_postings_fetched_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_fetched_at ON public.postings USING btree (fetched_at DESC);


--
-- Name: idx_postings_ihl_category; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_ihl_category ON public.postings USING btree (ihl_category) WHERE (ihl_category IS NOT NULL);


--
-- Name: idx_postings_ihl_score; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_ihl_score ON public.postings USING btree (ihl_score) WHERE (ihl_score IS NOT NULL);


--
-- Name: idx_postings_organization; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_organization ON public.postings USING btree (organization_name);


--
-- Name: idx_postings_publication; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_publication ON public.postings USING btree (posting_publication_date);


--
-- Name: idx_postings_requirements; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_requirements ON public.postings USING gin (job_requirements);


--
-- Name: idx_postings_skills; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_skills ON public.postings USING gin (skill_keywords);


--
-- Name: idx_postings_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_source ON public.postings USING btree (metadata_source);


--
-- Name: idx_postings_source_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_source_id ON public.postings USING btree (posting_source_id);


--
-- Name: idx_postings_source_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_source_unique ON public.postings USING btree (source_id, posting_source_id) WHERE ((source_id IS NOT NULL) AND (posting_source_id IS NOT NULL));


--
-- Name: idx_postings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_status ON public.postings USING btree (posting_status, last_seen_at);


--
-- Name: idx_postings_summary_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_summary_status ON public.postings USING btree (summary_extraction_status) WHERE (summary_extraction_status = 'pending'::text);


--
-- Name: idx_postings_test; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_test ON public.postings USING btree (is_test_posting) WHERE (is_test_posting = true);


--
-- Name: idx_postings_with_skills; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_with_skills ON public.postings USING btree (posting_id) WHERE (skill_keywords IS NOT NULL);


--
-- Name: INDEX idx_postings_with_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_postings_with_skills IS 'Partial index for postings with extracted skills';


--
-- Name: idx_production_runs_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_posting ON public.production_runs USING btree (posting_name);


--
-- Name: idx_production_runs_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_recipe ON public.production_runs USING btree (workflow_id);


--
-- Name: idx_production_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_status ON public.production_runs USING btree (status);


--
-- Name: idx_profile_job_matches_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_job_matches_user ON public.profile_job_matches USING btree (user_id);


--
-- Name: idx_profile_skills_proficiency; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_proficiency ON public.profile_skills USING btree (proficiency_level);


--
-- Name: idx_profile_skills_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_profile ON public.profile_skills USING btree (profile_id);


--
-- Name: idx_profile_skills_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_skill ON public.profile_skills USING btree (skill_id);


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
-- Name: idx_script_executions_date; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_script_executions_date ON public.script_executions USING btree (executed_at DESC);


--
-- Name: idx_script_executions_script; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_script_executions_script ON public.script_executions USING btree (script_id);


--
-- Name: idx_skill_aliases_language; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_aliases_language ON public.skill_aliases USING btree (language);


--
-- Name: idx_skill_aliases_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_aliases_skill ON public.skill_aliases USING btree (skill_name);


--
-- Name: idx_skill_aliases_skill_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_skill_aliases_skill_unique ON public.skill_aliases USING btree (skill_name);


--
-- Name: idx_skill_occ_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_created ON public.skill_occurrences USING btree (created_at);


--
-- Name: idx_skill_occ_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_source ON public.skill_occurrences USING btree (skill_source, source_id);


--
-- Name: idx_skills_pending_occurrences; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skills_pending_occurrences ON public.skills_pending_taxonomy USING btree (occurrences DESC);


--
-- Name: idx_skills_pending_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skills_pending_status ON public.skills_pending_taxonomy USING btree (review_status);


--
-- Name: idx_stored_scripts_category; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_stored_scripts_category ON public.stored_scripts USING btree (script_category);


--
-- Name: idx_stored_scripts_current; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_stored_scripts_current ON public.stored_scripts USING btree (is_current_version) WHERE (is_current_version = true);


--
-- Name: idx_stored_scripts_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_stored_scripts_name ON public.stored_scripts USING btree (script_name);


--
-- Name: idx_test_cases_difficulty; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_test_cases_difficulty ON public.test_cases USING btree (difficulty_level);


--
-- Name: idx_test_cases_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_test_cases_enabled ON public.test_cases USING btree (enabled);


--
-- Name: idx_test_cases_test_data; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_test_cases_test_data ON public.test_cases USING gin (test_data);


--
-- Name: idx_test_cases_test_data_job_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_test_cases_test_data_job_id ON public.test_cases USING btree (((test_data ->> 'job_id'::text)));


--
-- Name: INDEX idx_test_cases_test_data_job_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_test_cases_test_data_job_id IS 'JSONB index for fast job_id lookups in test_data';


--
-- Name: idx_test_cases_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_test_cases_workflow ON public.test_cases USING btree (workflow_id);


--
-- Name: idx_trigger_executions_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_trigger_executions_status ON public.trigger_executions USING btree (status);


--
-- Name: idx_trigger_executions_time; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_trigger_executions_time ON public.trigger_executions USING btree (triggered_at DESC);


--
-- Name: idx_trigger_executions_trigger; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_trigger_executions_trigger ON public.trigger_executions USING btree (trigger_id);


--
-- Name: idx_user_prefs_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_prefs_active ON public.user_preferences USING btree (is_active);


--
-- Name: idx_user_prefs_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_prefs_user ON public.user_posting_preferences USING btree (user_id);


--
-- Name: idx_user_saved_postings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_saved_postings_status ON public.user_saved_postings USING btree (application_status);


--
-- Name: idx_user_saved_postings_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_saved_postings_user ON public.user_saved_postings USING btree (user_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_org; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_users_org ON public.users USING btree (organization_id);


--
-- Name: idx_users_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_users_status ON public.users USING btree (status);


--
-- Name: idx_validated_prompts_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_validated_prompts_enabled ON public.validated_prompts USING btree (enabled);


--
-- Name: idx_validated_prompts_facet; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_validated_prompts_facet ON public.validated_prompts USING btree (capability_name);


--
-- Name: idx_work_history_current; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_current ON public.profile_work_history USING btree (is_current);


--
-- Name: idx_work_history_dates; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_dates ON public.profile_work_history USING btree (start_date, end_date);


--
-- Name: idx_work_history_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_work_history_profile ON public.profile_work_history USING btree (profile_id);


--
-- Name: idx_workflow_conversations_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_conversation ON public.workflow_conversations USING btree (conversation_id);


--
-- Name: idx_workflow_conversations_order; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_order ON public.workflow_conversations USING btree (workflow_id, execution_order);


--
-- Name: idx_workflow_conversations_parallel; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_parallel ON public.workflow_conversations USING btree (workflow_id, parallel_group) WHERE (parallel_group IS NOT NULL);


--
-- Name: idx_workflow_conversations_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_workflow ON public.workflow_conversations USING btree (workflow_id);


--
-- Name: idx_workflow_placeholders_required; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_placeholders_required ON public.workflow_placeholders USING btree (workflow_id, is_required);


--
-- Name: idx_workflow_placeholders_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_placeholders_workflow ON public.workflow_placeholders USING btree (workflow_id);


--
-- Name: idx_workflow_runs_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_batch ON public.workflow_runs USING btree (batch_id);


--
-- Name: idx_workflow_runs_batch_tracking; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_batch_tracking ON public.workflow_runs USING btree (test_case_id, batch_number, status);


--
-- Name: idx_workflow_runs_execution_mode; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_execution_mode ON public.workflow_runs USING btree (workflow_id, execution_mode, status);


--
-- Name: idx_workflow_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_status ON public.workflow_runs USING btree (status);


--
-- Name: idx_workflow_runs_test_case_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_test_case_id ON public.workflow_runs USING btree (test_case_id);


--
-- Name: INDEX idx_workflow_runs_test_case_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_workflow_runs_test_case_id IS 'Speed up workflow_runs → test_cases joins';


--
-- Name: idx_workflow_runs_test_case_id_desc; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_test_case_id_desc ON public.workflow_runs USING btree (test_case_id, workflow_run_id DESC);


--
-- Name: INDEX idx_workflow_runs_test_case_id_desc; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_workflow_runs_test_case_id_desc IS 'Optimize ORDER BY workflow_run_id DESC LIMIT 1 queries';


--
-- Name: idx_workflow_runs_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_user ON public.workflow_runs USING btree (user_id);


--
-- Name: idx_workflow_runs_variation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_variation ON public.workflow_runs USING btree (test_case_id);


--
-- Name: idx_workflow_runs_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_workflow ON public.workflow_runs USING btree (workflow_id);


--
-- Name: idx_workflow_triggers_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_triggers_enabled ON public.workflow_triggers USING btree (enabled) WHERE (enabled = true);


--
-- Name: idx_workflow_triggers_next_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_triggers_next_run ON public.workflow_triggers USING btree (next_scheduled_run) WHERE (enabled = true);


--
-- Name: idx_workflow_triggers_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_triggers_type ON public.workflow_triggers USING btree (trigger_type);


--
-- Name: idx_workflows_documentation_fts; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_documentation_fts ON public.workflows USING gin (to_tsvector('english'::regconfig, COALESCE(documentation, ''::text)));


--
-- Name: idx_workflows_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_enabled ON public.workflows USING btree (enabled);


--
-- Name: idx_workflows_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_name ON public.workflows USING btree (workflow_name);


--
-- Name: workflow_runs_unique_success_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX workflow_runs_unique_success_batch ON public.workflow_runs USING btree (workflow_id, test_case_id, batch_id, execution_mode) WHERE (status = 'SUCCESS'::text);


--
-- Name: capabilities capabilities_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER capabilities_history_trigger BEFORE UPDATE ON public.capabilities FOR EACH ROW EXECUTE FUNCTION public.archive_capabilities();


--
-- Name: profile_certifications certifications_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER certifications_updated_at_trigger BEFORE UPDATE ON public.profile_certifications FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: conversations conversations_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER conversations_history_trigger BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION public.archive_conversations();


--
-- Name: profile_education education_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER education_updated_at_trigger BEFORE UPDATE ON public.profile_education FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: instructions instructions_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER instructions_history_trigger BEFORE UPDATE ON public.instructions FOR EACH ROW EXECUTE FUNCTION public.archive_instructions();


--
-- Name: profiles profile_search_vector_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profile_search_vector();


--
-- Name: profiles profiles_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profiles_updated_at_trigger BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: test_cases test_cases_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER test_cases_history_trigger BEFORE UPDATE ON public.test_cases FOR EACH ROW EXECUTE FUNCTION public.archive_test_cases();


--
-- Name: job_fetch_runs trg_update_source_stats; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_update_source_stats AFTER UPDATE ON public.job_fetch_runs FOR EACH ROW WHEN (((old.status = 'RUNNING'::text) AND (new.status = ANY (ARRAY['SUCCESS'::text, 'PARTIAL_SUCCESS'::text, 'ERROR'::text])))) EXECUTE FUNCTION public.update_source_stats();


--
-- Name: validated_prompts validated_prompts_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER validated_prompts_history_trigger BEFORE UPDATE ON public.validated_prompts FOR EACH ROW EXECUTE FUNCTION public.archive_validated_prompts();


--
-- Name: profile_work_history work_history_duration_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_duration_trigger BEFORE INSERT OR UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.calculate_work_duration();


--
-- Name: profile_work_history work_history_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_updated_at_trigger BEFORE UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: workflows workflows_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER workflows_history_trigger BEFORE UPDATE ON public.workflows FOR EACH ROW EXECUTE FUNCTION public.archive_workflows();


--
-- Name: actors actors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: capabilities capabilities_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.capabilities(capability_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: conversation_dialogue conversation_dialogue_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue
    ADD CONSTRAINT conversation_dialogue_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


--
-- Name: conversation_dialogue conversation_dialogue_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue
    ADD CONSTRAINT conversation_dialogue_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE;


--
-- Name: conversation_runs conversation_runs_active_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_runs
    ADD CONSTRAINT conversation_runs_active_actor_id_fkey FOREIGN KEY (active_actor_id) REFERENCES public.actors(actor_id);


--
-- Name: conversation_runs conversation_runs_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_runs
    ADD CONSTRAINT conversation_runs_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


--
-- Name: conversation_runs conversation_runs_workflow_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_runs
    ADD CONSTRAINT conversation_runs_workflow_step_id_fkey FOREIGN KEY (workflow_step_id) REFERENCES public.workflow_conversations(step_id);


--
-- Name: conversations conversations_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: conversations conversations_validated_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_validated_prompt_id_fkey FOREIGN KEY (validated_prompt_id) REFERENCES public.validated_prompts(validated_prompt_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: dialogue_step_placeholders dialogue_step_placeholders_dialogue_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.dialogue_step_placeholders
    ADD CONSTRAINT dialogue_step_placeholders_dialogue_step_id_fkey FOREIGN KEY (dialogue_step_id) REFERENCES public.conversation_dialogue(dialogue_step_id) ON DELETE CASCADE;


--
-- Name: dialogue_step_placeholders dialogue_step_placeholders_placeholder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.dialogue_step_placeholders
    ADD CONSTRAINT dialogue_step_placeholders_placeholder_id_fkey FOREIGN KEY (placeholder_id) REFERENCES public.placeholder_definitions(placeholder_id) ON DELETE CASCADE;


--
-- Name: human_tasks human_tasks_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: human_tasks human_tasks_conversation_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_conversation_run_id_fkey FOREIGN KEY (session_run_id) REFERENCES public.conversation_runs(conversation_run_id);


--
-- Name: instruction_step_executions instruction_step_executions_instruction_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_step_executions
    ADD CONSTRAINT instruction_step_executions_instruction_step_id_fkey FOREIGN KEY (instruction_step_id) REFERENCES public.instruction_steps(instruction_step_id) ON DELETE CASCADE;


--
-- Name: instruction_steps instruction_steps_instruction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT instruction_steps_instruction_id_fkey FOREIGN KEY (instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE CASCADE;


--
-- Name: instruction_steps instruction_steps_next_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT instruction_steps_next_conversation_id_fkey FOREIGN KEY (next_conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE SET NULL;


--
-- Name: instruction_steps instruction_steps_next_instruction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT instruction_steps_next_instruction_id_fkey FOREIGN KEY (next_instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE SET NULL;


--
-- Name: instructions instructions_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


--
-- Name: instructions instructions_delegate_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_delegate_actor_id_fkey FOREIGN KEY (delegate_actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: interaction_lineage interaction_lineage_downstream_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_lineage
    ADD CONSTRAINT interaction_lineage_downstream_interaction_id_fkey FOREIGN KEY (downstream_interaction_id) REFERENCES public.llm_interactions(interaction_id) ON DELETE CASCADE;


--
-- Name: interaction_lineage interaction_lineage_upstream_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_lineage
    ADD CONSTRAINT interaction_lineage_upstream_interaction_id_fkey FOREIGN KEY (upstream_interaction_id) REFERENCES public.llm_interactions(interaction_id) ON DELETE CASCADE;


--
-- Name: job_fetch_runs job_fetch_runs_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_fetch_runs
    ADD CONSTRAINT job_fetch_runs_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.job_sources(source_id) ON DELETE CASCADE;


--
-- Name: job_fetch_runs job_fetch_runs_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_fetch_runs
    ADD CONSTRAINT job_fetch_runs_workflow_run_id_fkey FOREIGN KEY (workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id) ON DELETE SET NULL;


--
-- Name: job_skills job_skills_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: job_skills job_skills_recipe_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_recipe_run_id_fkey FOREIGN KEY (recipe_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: job_skills job_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id);


--
-- Name: job_sources job_sources_fetch_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_sources
    ADD CONSTRAINT job_sources_fetch_workflow_id_fkey FOREIGN KEY (fetch_workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: llm_interactions llm_interactions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.llm_interactions
    ADD CONSTRAINT llm_interactions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


--
-- Name: llm_interactions llm_interactions_conversation_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.llm_interactions
    ADD CONSTRAINT llm_interactions_conversation_run_id_fkey FOREIGN KEY (conversation_run_id) REFERENCES public.conversation_runs(conversation_run_id) ON DELETE CASCADE;


--
-- Name: llm_interactions llm_interactions_instruction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.llm_interactions
    ADD CONSTRAINT llm_interactions_instruction_id_fkey FOREIGN KEY (instruction_id) REFERENCES public.instructions(instruction_id);


--
-- Name: llm_interactions llm_interactions_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.llm_interactions
    ADD CONSTRAINT llm_interactions_workflow_run_id_fkey FOREIGN KEY (workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id) ON DELETE CASCADE;


--
-- Name: posting_field_mappings posting_field_mappings_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_field_mappings
    ADD CONSTRAINT posting_field_mappings_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.posting_sources(source_id);


--
-- Name: posting_processing_status posting_processing_status_ihl_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_ihl_workflow_run_id_fkey FOREIGN KEY (ihl_workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: posting_processing_status posting_processing_status_matching_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_matching_workflow_run_id_fkey FOREIGN KEY (matching_workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: posting_processing_status posting_processing_status_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: posting_processing_status posting_processing_status_skills_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_skills_workflow_run_id_fkey FOREIGN KEY (skills_workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: posting_processing_status posting_processing_status_summary_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_summary_workflow_run_id_fkey FOREIGN KEY (summary_workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: postings postings_fetch_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_fetch_run_id_fkey FOREIGN KEY (fetch_run_id) REFERENCES public.job_fetch_runs(fetch_run_id);


--
-- Name: postings postings_ihl_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_ihl_workflow_run_id_fkey FOREIGN KEY (ihl_workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: postings postings_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.posting_sources(source_id);


--
-- Name: production_runs production_runs_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: production_runs production_runs_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: profile_certifications profile_certifications_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_certifications
    ADD CONSTRAINT profile_certifications_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_education profile_education_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_education
    ADD CONSTRAINT profile_education_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_job_matches profile_job_matches_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches
    ADD CONSTRAINT profile_job_matches_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: profile_job_matches profile_job_matches_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches
    ADD CONSTRAINT profile_job_matches_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_job_matches profile_job_matches_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_job_matches
    ADD CONSTRAINT profile_job_matches_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: profile_languages profile_languages_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_languages
    ADD CONSTRAINT profile_languages_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_skills profile_skills_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_skills profile_skills_recipe_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_recipe_run_id_fkey FOREIGN KEY (recipe_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: profile_skills profile_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id);


--
-- Name: profile_work_history profile_work_history_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history
    ADD CONSTRAINT profile_work_history_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profiles profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: workflow_runs recipe_runs_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT recipe_runs_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(batch_id);


--
-- Name: workflow_runs recipe_runs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT recipe_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: workflow_runs recipe_runs_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT recipe_runs_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: script_executions script_executions_script_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.script_executions
    ADD CONSTRAINT script_executions_script_id_fkey FOREIGN KEY (script_id) REFERENCES public.stored_scripts(script_id);


--
-- Name: skill_hierarchy skill_hierarchy_parent_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_parent_skill_id_fkey FOREIGN KEY (parent_skill_id) REFERENCES public.skill_aliases(skill_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_hierarchy skill_hierarchy_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_occurrences skill_occurrences_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences
    ADD CONSTRAINT skill_occurrences_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: stored_scripts stored_scripts_replaces_script_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.stored_scripts
    ADD CONSTRAINT stored_scripts_replaces_script_id_fkey FOREIGN KEY (replaces_script_id) REFERENCES public.stored_scripts(script_id);


--
-- Name: test_cases test_cases_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id) ON DELETE CASCADE;


--
-- Name: trigger_executions trigger_executions_trigger_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.trigger_executions
    ADD CONSTRAINT trigger_executions_trigger_id_fkey FOREIGN KEY (trigger_id) REFERENCES public.workflow_triggers(trigger_id);


--
-- Name: trigger_executions trigger_executions_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.trigger_executions
    ADD CONSTRAINT trigger_executions_workflow_run_id_fkey FOREIGN KEY (workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id);


--
-- Name: user_posting_preferences user_posting_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_preferences
    ADD CONSTRAINT user_posting_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_saved_postings user_saved_postings_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_saved_postings
    ADD CONSTRAINT user_saved_postings_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: user_saved_postings user_saved_postings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_saved_postings
    ADD CONSTRAINT user_saved_postings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(organization_id);


--
-- Name: validated_prompts validated_prompts_capability_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.validated_prompts
    ADD CONSTRAINT validated_prompts_capability_id_fkey FOREIGN KEY (capability_id) REFERENCES public.capabilities(capability_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: workflow_conversations workflow_conversations_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations
    ADD CONSTRAINT workflow_conversations_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


--
-- Name: workflow_conversations workflow_conversations_depends_on_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations
    ADD CONSTRAINT workflow_conversations_depends_on_step_id_fkey FOREIGN KEY (depends_on_step_id) REFERENCES public.workflow_conversations(step_id);


--
-- Name: workflow_conversations workflow_conversations_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations
    ADD CONSTRAINT workflow_conversations_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: workflow_dependencies workflow_dependencies_depends_on_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies
    ADD CONSTRAINT workflow_dependencies_depends_on_workflow_id_fkey FOREIGN KEY (depends_on_workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: workflow_dependencies workflow_dependencies_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies
    ADD CONSTRAINT workflow_dependencies_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: workflow_placeholders workflow_placeholders_placeholder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_placeholders
    ADD CONSTRAINT workflow_placeholders_placeholder_id_fkey FOREIGN KEY (placeholder_id) REFERENCES public.placeholder_definitions(placeholder_id) ON DELETE CASCADE;


--
-- Name: workflow_placeholders workflow_placeholders_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_placeholders
    ADD CONSTRAINT workflow_placeholders_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id) ON DELETE CASCADE;


--
-- Name: workflow_runs workflow_runs_test_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_test_case_id_fkey FOREIGN KEY (test_case_id) REFERENCES public.test_cases(test_case_id);


--
-- Name: workflow_scripts workflow_scripts_script_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_scripts
    ADD CONSTRAINT workflow_scripts_script_id_fkey FOREIGN KEY (script_id) REFERENCES public.stored_scripts(script_id);


--
-- Name: workflow_scripts workflow_scripts_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_scripts
    ADD CONSTRAINT workflow_scripts_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: workflow_triggers workflow_triggers_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers
    ADD CONSTRAINT workflow_triggers_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- PostgreSQL database dump complete
--

\unrestrict XLaJ0soL4JasM36RPtVlmt62ri5fgz9aTgGkvFzItp2g3Wm9RrgMtCFYjCSOs7o

