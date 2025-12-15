--
-- PostgreSQL database dump
--

\restrict cpAXh3N7ypFw3AN0QRAsN4ttmAGMrAKtPGNjUgemsQ10gLIDgsQegG78SZ01fYk

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
-- Name: pg_cron; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA public;


--
-- Name: EXTENSION pg_cron; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_cron IS 'Job scheduler for PostgreSQL';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: append_event(text, text, text, jsonb, jsonb, integer, text, bigint, text); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb, p_event_version integer, p_correlation_id text, p_causation_id bigint, p_idempotency_key text) OWNER TO postgres;

--
-- Name: FUNCTION append_event(p_aggregate_type text, p_aggregate_id text, p_event_type text, p_event_data jsonb, p_metadata jsonb, p_event_version integer, p_correlation_id text, p_causation_id bigint, p_idempotency_key text); Type: COMMENT; Schema: public; Owner: postgres
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
-- Name: calculate_skill_match(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.calculate_skill_match(p_posting_id integer, p_profile_id integer) OWNER TO postgres;

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
-- Name: cleanup_test_runs(integer); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.cleanup_test_runs(p_days_old integer) OWNER TO postgres;

--
-- Name: FUNCTION cleanup_test_runs(p_days_old integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.cleanup_test_runs(p_days_old integer) IS 'Delete test/dev workflow runs older than N days (default 30).
Keeps UAT and prod runs forever. Returns count of deleted runs and interactions.';


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
-- Name: get_aggregate_events(text, text); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.get_aggregate_events(p_aggregate_type text, p_aggregate_id text) OWNER TO postgres;

--
-- Name: get_production_actors(integer); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.get_production_actors(p_conversation_id integer) OWNER TO postgres;

--
-- Name: FUNCTION get_production_actors(p_conversation_id integer); Type: COMMENT; Schema: public; Owner: postgres
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
-- Name: maybe_create_snapshot(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer) OWNER TO postgres;

--
-- Name: FUNCTION maybe_create_snapshot(p_posting_id integer, p_snapshot_interval integer); Type: COMMENT; Schema: public; Owner: postgres
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
-- Name: rebuild_posting_state(integer); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.rebuild_posting_state(p_posting_id integer) OWNER TO postgres;

--
-- Name: FUNCTION rebuild_posting_state(p_posting_id integer); Type: COMMENT; Schema: public; Owner: postgres
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
-- Name: set_workflow_run_environment(); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.set_workflow_run_environment() OWNER TO postgres;

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
-- Name: tag_conversation(integer, text[]); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.tag_conversation(p_conversation_id integer, p_tags text[]) OWNER TO postgres;

--
-- Name: FUNCTION tag_conversation(p_conversation_id integer, p_tags text[]); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.tag_conversation(p_conversation_id integer, p_tags text[]) IS 'Helper function to tag a conversation with multiple tags at once. Usage: SELECT tag_conversation(conversation_id, ARRAY[''extract'', ''validate'']);';


--
-- Name: update_career_analyses_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_career_analyses_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_career_analyses_updated_at() OWNER TO postgres;

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
-- Name: validate_event_store(); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.validate_event_store() OWNER TO postgres;

--
-- Name: FUNCTION validate_event_store(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.validate_event_store() IS 'Compare old checkpoint schema vs new event store projections. Returns discrepancies.';


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
-- Name: actor_code_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.actor_code_history (
    history_id bigint NOT NULL,
    actor_id integer NOT NULL,
    script_code text NOT NULL,
    script_code_hash text NOT NULL,
    change_type text NOT NULL,
    change_reason text,
    changed_by_actor_id integer,
    source_file_path text,
    git_commit_hash text,
    version_tag text,
    activated_at timestamp with time zone DEFAULT now(),
    deactivated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT actor_code_history_change_type_check CHECK ((change_type = ANY (ARRAY['initial'::text, 'manual_deploy'::text, 'auto_sync'::text, 'rollback'::text, 'bug_fix'::text])))
);


ALTER TABLE public.actor_code_history OWNER TO base_admin;

--
-- Name: TABLE actor_code_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.actor_code_history IS 'Version history for script actors (rollback, audit trail, drift detection)';


--
-- Name: COLUMN actor_code_history.change_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actor_code_history.change_type IS 'How this version was created (manual_deploy, auto_sync, rollback, etc.)';


--
-- Name: COLUMN actor_code_history.activated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actor_code_history.activated_at IS 'When this version became active';


--
-- Name: COLUMN actor_code_history.deactivated_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actor_code_history.deactivated_at IS 'When this version was replaced (NULL = currently active)';


--
-- Name: actor_code_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.actor_code_history_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.actor_code_history_history_id_seq OWNER TO base_admin;

--
-- Name: actor_code_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.actor_code_history_history_id_seq OWNED BY public.actor_code_history.history_id;


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
    url text NOT NULL,
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
    CONSTRAINT actors_actor_type_check CHECK ((actor_type = ANY (ARRAY['human'::text, 'ai_model'::text, 'script'::text, 'machine_actor'::text]))),
    CONSTRAINT actors_execution_type_check CHECK ((execution_type = ANY (ARRAY['ollama_api'::text, 'http_api'::text, 'python_script'::text, 'bash_script'::text, 'human_input'::text]))),
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
-- Name: llm_interactions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.llm_interactions (
    interaction_id integer NOT NULL,
    workflow_run_id integer NOT NULL,
    conversation_run_id integer NOT NULL,
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
    CONSTRAINT llm_interactions_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'SUCCESS'::text, 'TIMEOUT'::text, 'ERROR'::text, 'RATE_LIMITED'::text, 'QUOTA_EXCEEDED'::text, 'INVALID_REQUEST'::text, 'FAILED'::text]))),
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
-- Name: actor_performance_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: base_admin
--

CREATE MATERIALIZED VIEW public.actor_performance_summary AS
 SELECT a.actor_id,
    a.actor_name,
    a.actor_type,
    count(*) AS total_calls,
    count(*) FILTER (WHERE (li.status = 'SUCCESS'::text)) AS success_count,
    count(*) FILTER (WHERE (li.status <> 'SUCCESS'::text)) AS error_count,
    round(((100.0 * (count(*) FILTER (WHERE (li.status = 'SUCCESS'::text)))::numeric) / (count(*))::numeric), 2) AS success_rate,
    round(avg(li.latency_ms), 2) AS avg_latency_ms,
    round((percentile_cont((0.50)::double precision) WITHIN GROUP (ORDER BY ((li.latency_ms)::double precision)))::numeric, 2) AS p50_latency_ms,
    round((percentile_cont((0.95)::double precision) WITHIN GROUP (ORDER BY ((li.latency_ms)::double precision)))::numeric, 2) AS p95_latency_ms,
    round((percentile_cont((0.99)::double precision) WITHIN GROUP (ORDER BY ((li.latency_ms)::double precision)))::numeric, 2) AS p99_latency_ms,
    min(li.started_at) AS first_used,
    max(li.started_at) AS last_used,
    COALESCE(sum(li.cost_usd), (0)::numeric) AS total_cost_usd
   FROM (public.actors a
     LEFT JOIN public.llm_interactions li ON ((a.actor_id = li.actor_id)))
  WHERE (li.started_at > (now() - '30 days'::interval))
  GROUP BY a.actor_id, a.actor_name, a.actor_type
  WITH NO DATA;


ALTER TABLE public.actor_performance_summary OWNER TO base_admin;

--
-- Name: MATERIALIZED VIEW actor_performance_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON MATERIALIZED VIEW public.actor_performance_summary IS 'Actor performance metrics over last 30 days. Refresh with: REFRESH MATERIALIZED VIEW CONCURRENTLY actor_performance_summary;';


--
-- Name: actor_rate_control; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.actor_rate_control (
    rate_control_id integer NOT NULL,
    actor_id integer NOT NULL,
    check_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    was_allowed boolean NOT NULL,
    rate_limit_hours numeric(5,2),
    last_successful_run timestamp without time zone,
    reason text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.actor_rate_control OWNER TO base_admin;

--
-- Name: TABLE actor_rate_control; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.actor_rate_control IS 'Audit trail of rate limit checks for actors. Tracks both allowed and denied access attempts, enabling observability and rate limit effectiveness analysis.';


--
-- Name: COLUMN actor_rate_control.was_allowed; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actor_rate_control.was_allowed IS 'TRUE if actor was allowed to run, FALSE if rate-limited (denied).';


--
-- Name: COLUMN actor_rate_control.reason; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actor_rate_control.reason IS 'Human-readable reason for decision, e.g., "Rate limited: actor ran 2.3h ago, next run in 21.7h"';


--
-- Name: actor_rate_control_rate_control_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.actor_rate_control_rate_control_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.actor_rate_control_rate_control_id_seq OWNER TO base_admin;

--
-- Name: actor_rate_control_rate_control_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.actor_rate_control_rate_control_id_seq OWNED BY public.actor_rate_control.rate_control_id;


--
-- Name: app_users; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.app_users (
    user_id integer NOT NULL,
    oauth_provider character varying(50) DEFAULT 'google'::character varying NOT NULL,
    oauth_subject_hash character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_login_at timestamp with time zone,
    is_active boolean DEFAULT true,
    deleted_at timestamp with time zone,
    deletion_reason character varying(100)
);


ALTER TABLE public.app_users OWNER TO base_admin;

--
-- Name: TABLE app_users; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.app_users IS 'Minimal identity stub. Contains NO PII. 
OAuth subject is hashed - we cannot reverse it to get email/name.
We know a user EXISTS, not WHO they are.
Named app_users to avoid conflict with existing users table.';


--
-- Name: COLUMN app_users.oauth_subject_hash; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.app_users.oauth_subject_hash IS 'SHA256(provider + ":" + subject_id). One-way hash. 
Google cannot be asked "who is this hash" - it is irreversible.';


--
-- Name: app_users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.app_users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.app_users_user_id_seq OWNER TO base_admin;

--
-- Name: app_users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.app_users_user_id_seq OWNED BY public.app_users.user_id;


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
-- Name: circuit_breaker_events; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.circuit_breaker_events (
    event_id integer NOT NULL,
    actor_id integer NOT NULL,
    event_type text NOT NULL,
    failure_count integer,
    cooldown_seconds integer,
    created_at timestamp without time zone DEFAULT now(),
    context jsonb,
    CONSTRAINT circuit_breaker_events_event_type_check CHECK ((event_type = ANY (ARRAY['failure'::text, 'open'::text, 'half_open'::text, 'closed'::text, 'success'::text])))
);


ALTER TABLE public.circuit_breaker_events OWNER TO base_admin;

--
-- Name: TABLE circuit_breaker_events; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.circuit_breaker_events IS 'Historical log of circuit breaker state changes for monitoring';


--
-- Name: COLUMN circuit_breaker_events.event_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.circuit_breaker_events.event_type IS 'Type of event: failure (actor failed), open (circuit opened), half_open (testing), closed (circuit closed), success (call succeeded)';


--
-- Name: COLUMN circuit_breaker_events.failure_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.circuit_breaker_events.failure_count IS 'Number of failures when circuit opened';


--
-- Name: COLUMN circuit_breaker_events.cooldown_seconds; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.circuit_breaker_events.cooldown_seconds IS 'Cooldown period in seconds (when circuit opens)';


--
-- Name: circuit_breaker_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.circuit_breaker_events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.circuit_breaker_events_event_id_seq OWNER TO base_admin;

--
-- Name: circuit_breaker_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.circuit_breaker_events_event_id_seq OWNED BY public.circuit_breaker_events.event_id;


--
-- Name: city_country_map; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.city_country_map (
    city_id bigint NOT NULL,
    city text NOT NULL,
    city_ascii text NOT NULL,
    country text NOT NULL,
    iso2 character(2),
    iso3 character(3),
    admin_name text,
    lat numeric(10,6),
    lng numeric(10,6),
    population numeric,
    capital text
);


ALTER TABLE public.city_country_map OWNER TO base_admin;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.companies (
    company_id integer NOT NULL,
    company_name character varying(200) NOT NULL,
    avg_rating numeric(3,2),
    rating_count integer DEFAULT 0,
    industry character varying(100),
    headquarters_location character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.companies OWNER TO base_admin;

--
-- Name: TABLE companies; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.companies IS 'Companies that can be rated. Seeded from job postings.
Ratings are aggregated here, individual ratings in company_ratings.';


--
-- Name: companies_company_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.companies_company_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.companies_company_id_seq OWNER TO base_admin;

--
-- Name: companies_company_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.companies_company_id_seq OWNED BY public.companies.company_id;


--
-- Name: company_ratings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.company_ratings (
    rating_id integer NOT NULL,
    user_id integer,
    company_id integer,
    rating integer NOT NULL,
    review_text text,
    is_verified boolean DEFAULT false,
    verification_id integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT company_ratings_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.company_ratings OWNER TO base_admin;

--
-- Name: TABLE company_ratings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.company_ratings IS 'User ratings of companies. Note: Rating does NOT imply user worked there.
Verification is separate - a user can rate without proving employment.';


--
-- Name: company_ratings_rating_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.company_ratings_rating_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.company_ratings_rating_id_seq OWNER TO base_admin;

--
-- Name: company_ratings_rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.company_ratings_rating_id_seq OWNED BY public.company_ratings.rating_id;


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
    conversation_run_name text,
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
    active_actor_id integer,
    CONSTRAINT conversation_runs_quality_score_check CHECK ((quality_score = ANY (ARRAY['A'::text, 'B'::text, 'C'::text, 'D'::text, 'F'::text, NULL::text]))),
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
-- Name: conversation_tag_definitions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_tag_definitions (
    tag text NOT NULL,
    category text NOT NULL,
    description text NOT NULL,
    examples text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.conversation_tag_definitions OWNER TO postgres;

--
-- Name: TABLE conversation_tag_definitions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.conversation_tag_definitions IS 'Reference table defining valid conversation tags. Documents what each tag means and provides examples.';


--
-- Name: conversation_tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.conversation_tags (
    conversation_id integer NOT NULL,
    tag text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    created_by text DEFAULT 'system'::text
);


ALTER TABLE public.conversation_tags OWNER TO postgres;

--
-- Name: TABLE conversation_tags; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.conversation_tags IS 'Tag conversations with action verbs for cross-application discovery. Tags are application-agnostic and represent what the conversation does (extract, validate, match, etc.)';


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
-- Name: execution_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_events (
    event_id bigint NOT NULL,
    event_timestamp timestamp with time zone DEFAULT now() NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    aggregate_version integer NOT NULL,
    event_type text NOT NULL,
    event_data jsonb NOT NULL,
    correlation_id text,
    causation_id bigint,
    idempotency_key text,
    metadata jsonb,
    invalidated boolean DEFAULT false,
    invalidation_reason text,
    CONSTRAINT check_event_data_not_empty CHECK (((jsonb_typeof(event_data) = 'object'::text) AND (event_data <> '{}'::jsonb))),
    CONSTRAINT valid_aggregate_type CHECK ((aggregate_type = ANY (ARRAY['posting'::text, 'workflow_run'::text, 'actor'::text])))
);


ALTER TABLE public.execution_events OWNER TO postgres;

--
-- Name: TABLE execution_events; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.execution_events IS 'Immutable append-only event log. Events are facts about what happened. Never update or delete.';


--
-- Name: COLUMN execution_events.aggregate_version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.aggregate_version IS 'Version number for optimistic locking. Prevents concurrent modifications to same aggregate.';


--
-- Name: COLUMN execution_events.correlation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.correlation_id IS 'Links all events in a workflow run. Query all events for a run with this ID.';


--
-- Name: COLUMN execution_events.causation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.causation_id IS 'References event_id that caused this event. Enables causality graph construction.';


--
-- Name: COLUMN execution_events.idempotency_key; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.idempotency_key IS 'Deterministic key (e.g., "posting_3001_conv_4_1732012345"). Prevents duplicate events on retries.';


--
-- Name: COLUMN execution_events.invalidated; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.invalidated IS 'TRUE if this event execution was invalid (e.g., missing required input data). Invalid events are kept for completeness but excluded from monitoring/metrics.';


--
-- Name: COLUMN execution_events.invalidation_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.execution_events.invalidation_reason IS 'Human-readable explanation of why this event was invalidated';


--
-- Name: execution_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.execution_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_events_event_id_seq OWNER TO postgres;

--
-- Name: execution_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.execution_events_event_id_seq OWNED BY public.execution_events.event_id;


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
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    staleness_days integer
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
-- Name: COLUMN instructions.staleness_days; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.staleness_days IS 'How many days before this instruction should re-run. NULL = never re-run if completed. 
E.g., staleness_days=7 means re-run if last interaction was >7 days ago.
For fetcher URL checks, use 7. For summary extraction, use NULL (one-time).';


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
-- Name: interaction_events; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.interaction_events (
    event_id bigint NOT NULL,
    interaction_id bigint,
    event_type text NOT NULL,
    event_data jsonb NOT NULL,
    event_timestamp timestamp with time zone DEFAULT now(),
    causation_event_id bigint,
    correlation_id text,
    event_hash text,
    CONSTRAINT interaction_events_event_type_check CHECK ((event_type = ANY (ARRAY['interaction_created'::text, 'interaction_started'::text, 'interaction_completed'::text, 'interaction_failed'::text, 'interaction_invalidated'::text, 'interaction_branched'::text, 'interaction_retried'::text])))
);


ALTER TABLE public.interaction_events OWNER TO base_admin;

--
-- Name: TABLE interaction_events; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.interaction_events IS 'Immutable audit log for all interaction events (time travel, compliance, forensics)';


--
-- Name: COLUMN interaction_events.causation_event_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_events.causation_event_id IS 'Parent event that caused this event (event provenance)';


--
-- Name: COLUMN interaction_events.correlation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_events.correlation_id IS 'workflow_run_id to trace all events in a workflow run';


--
-- Name: COLUMN interaction_events.event_hash; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interaction_events.event_hash IS 'SHA256 hash for tamper detection';


--
-- Name: interaction_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.interaction_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.interaction_events_event_id_seq OWNER TO base_admin;

--
-- Name: interaction_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.interaction_events_event_id_seq OWNED BY public.interaction_events.event_id;


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
-- Name: interactions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.interactions (
    interaction_id bigint NOT NULL,
    posting_id integer,
    conversation_id integer NOT NULL,
    workflow_run_id bigint,
    actor_id integer NOT NULL,
    actor_type text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    execution_order integer NOT NULL,
    parent_interaction_id bigint,
    input_interaction_ids integer[] DEFAULT '{}'::integer[],
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
    trigger_interaction_id bigint,
    CONSTRAINT interactions_actor_type_check CHECK ((actor_type = ANY (ARRAY['ai_model'::text, 'script'::text, 'human'::text]))),
    CONSTRAINT interactions_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'running'::text, 'completed'::text, 'failed'::text, 'invalidated'::text])))
);


ALTER TABLE public.interactions OWNER TO base_admin;

--
-- Name: TABLE interactions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.interactions IS 'Wave Runner V2 core operational table - tracks all workflow interactions';


--
-- Name: COLUMN interactions.input_interaction_ids; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interactions.input_interaction_ids IS 'Array of parent interaction IDs for multi-parent cases';


--
-- Name: COLUMN interactions.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interactions.enabled IS 'Flag to enable/disable interaction (NOT deletion)';


--
-- Name: COLUMN interactions.invalidated; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interactions.invalidated IS 'Flag to mark interaction as invalid (duplicate, bug, etc.)';


--
-- Name: COLUMN interactions.trigger_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.interactions.trigger_interaction_id IS 'The workflow run interaction that triggered this work. Links child interactions back to the script/command that started the batch.';


--
-- Name: interactions_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.interactions_history (
    history_id bigint NOT NULL,
    interaction_id bigint NOT NULL,
    posting_id integer,
    conversation_id integer NOT NULL,
    workflow_run_id bigint,
    actor_id integer NOT NULL,
    actor_type text NOT NULL,
    status text NOT NULL,
    execution_order integer NOT NULL,
    parent_interaction_id bigint,
    trigger_interaction_id bigint,
    input_interaction_ids bigint[],
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


ALTER TABLE public.interactions_history OWNER TO base_admin;

--
-- Name: TABLE interactions_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.interactions_history IS 'Archive of deleted interactions - preserves audit trail even when source data is removed';


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

ALTER SEQUENCE public.interactions_history_history_id_seq OWNED BY public.interactions_history.history_id;


--
-- Name: interactions_interaction_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.interactions_interaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.interactions_interaction_id_seq OWNER TO base_admin;

--
-- Name: interactions_interaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.interactions_interaction_id_seq OWNED BY public.interactions.interaction_id;


--
-- Name: job_skills_staging; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_skills_staging (
    staging_id bigint NOT NULL,
    interaction_id bigint NOT NULL,
    raw_data jsonb NOT NULL,
    posting_id integer,
    skill_name text,
    skill_category text,
    required_or_preferred text,
    importance_score numeric(3,2),
    context text,
    validation_status text DEFAULT 'pending'::text,
    validation_errors jsonb,
    validated_at timestamp with time zone,
    validated_by_actor_id integer,
    promoted_to_requirement_id integer,
    promoted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT job_skills_staging_required_or_preferred_check CHECK ((required_or_preferred = ANY (ARRAY['required'::text, 'preferred'::text, 'nice_to_have'::text]))),
    CONSTRAINT job_skills_staging_validation_status_check CHECK ((validation_status = ANY (ARRAY['pending'::text, 'passed'::text, 'failed'::text, 'promoted'::text])))
);


ALTER TABLE public.job_skills_staging OWNER TO base_admin;

--
-- Name: TABLE job_skills_staging; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_skills_staging IS 'Staging area for job skill extractor output - validated before promotion to job_requirements';


--
-- Name: job_skills_staging_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.job_skills_staging_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_skills_staging_staging_id_seq OWNER TO base_admin;

--
-- Name: job_skills_staging_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.job_skills_staging_staging_id_seq OWNED BY public.job_skills_staging.staging_id;


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

COMMENT ON TABLE public.job_sources IS 'Workflow-driven job fetching sources (fetch_workflow_id, scheduling)';


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
-- Name: llm_performance_metrics; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.llm_performance_metrics AS
 SELECT ((execution_events.metadata ->> 'actor_id'::text))::integer AS actor_id,
    execution_events.event_type,
    count(*) AS event_count,
    avg(((execution_events.event_data ->> 'tokens'::text))::integer) AS avg_tokens,
    avg(((execution_events.event_data ->> 'duration_ms'::text))::integer) AS avg_duration_ms,
    percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((((execution_events.event_data ->> 'duration_ms'::text))::integer)::double precision)) AS median_duration_ms,
    percentile_cont((0.95)::double precision) WITHIN GROUP (ORDER BY ((((execution_events.event_data ->> 'duration_ms'::text))::integer)::double precision)) AS p95_duration_ms
   FROM public.execution_events
  WHERE ((execution_events.event_type = ANY (ARRAY['llm_call_completed'::text, 'llm_call_failed'::text])) AND ((execution_events.metadata ->> 'actor_id'::text) IS NOT NULL))
  GROUP BY ((execution_events.metadata ->> 'actor_id'::text))::integer, execution_events.event_type
  WITH NO DATA;


ALTER TABLE public.llm_performance_metrics OWNER TO postgres;

--
-- Name: MATERIALIZED VIEW llm_performance_metrics; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON MATERIALIZED VIEW public.llm_performance_metrics IS 'Performance metrics by actor and event type. Refresh periodically: REFRESH MATERIALIZED VIEW llm_performance_metrics;';


--
-- Name: model_performance; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.model_performance AS
 SELECT a.actor_id,
    a.actor_name,
    a.model_variant,
    a.is_production,
    i.conversation_id,
    count(*) AS execution_count,
    avg(((i.output ->> 'latency_ms'::text))::integer) AS avg_latency_ms,
    stddev(((i.output ->> 'latency_ms'::text))::integer) AS latency_stddev,
    min(((i.output ->> 'latency_ms'::text))::integer) AS min_latency_ms,
    max(((i.output ->> 'latency_ms'::text))::integer) AS max_latency_ms,
    percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((((i.output ->> 'latency_ms'::text))::integer)::double precision)) AS p50_latency_ms,
    percentile_cont((0.95)::double precision) WITHIN GROUP (ORDER BY ((((i.output ->> 'latency_ms'::text))::integer)::double precision)) AS p95_latency_ms,
    count(*) FILTER (WHERE (i.status = 'completed'::text)) AS success_count,
    count(*) FILTER (WHERE (i.status = 'failed'::text)) AS failure_count,
    ((count(*) FILTER (WHERE (i.status = 'completed'::text)))::double precision / (NULLIF(count(*), 0))::double precision) AS success_rate,
    min(i.created_at) AS first_execution,
    max(i.created_at) AS last_execution,
        CASE
            WHEN (avg(((i.output ->> 'latency_ms'::text))::integer) > (0)::numeric) THEN (((1000.0 / avg(((i.output ->> 'latency_ms'::text))::integer)))::double precision * ((count(*) FILTER (WHERE (i.status = 'completed'::text)))::double precision / (NULLIF(count(*), 0))::double precision))
            ELSE (0)::double precision
        END AS performance_score
   FROM (public.interactions i
     JOIN public.actors a ON ((i.actor_id = a.actor_id)))
  WHERE ((i.created_at > (now() - '7 days'::interval)) AND (a.actor_type = 'ai_model'::text) AND (i.output IS NOT NULL))
  GROUP BY a.actor_id, a.actor_name, a.model_variant, a.is_production, i.conversation_id;


ALTER TABLE public.model_performance OWNER TO postgres;

--
-- Name: VIEW model_performance; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.model_performance IS '7-day rolling performance metrics for all AI models.
Used by workflow 3XXX (automatic champion selection) to compare models.
Performance score = (1000/avg_latency_ms) * success_rate (higher is better).';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.organizations (
    organization_id integer NOT NULL,
    organization_name text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
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
-- Name: posting_fetch_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_fetch_runs (
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


ALTER TABLE public.posting_fetch_runs OWNER TO base_admin;

--
-- Name: TABLE posting_fetch_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_fetch_runs IS 'History of fetch operations from job_sources';


--
-- Name: COLUMN posting_fetch_runs.fetch_metadata; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.posting_fetch_runs.fetch_metadata IS 'API response metadata, rate limits, pagination info, etc.';


--
-- Name: posting_fetch_runs_fetch_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.posting_fetch_runs ALTER COLUMN fetch_run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.posting_fetch_runs_fetch_run_id_seq
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
    summary_extracted_at timestamp without time zone,
    skills_extracted boolean DEFAULT false,
    ihl_analyzed_at timestamp without time zone,
    ihl_workflow_run_id integer,
    processing_notes text
);


ALTER TABLE public.posting_processing_status OWNER TO base_admin;

--
-- Name: TABLE posting_processing_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_processing_status IS 'Track which processing stages have been completed for each posting';


--
-- Name: posting_skills; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.posting_skills (
    posting_skill_id integer NOT NULL,
    posting_id integer NOT NULL,
    skill_id integer,
    importance text,
    weight integer,
    proficiency text,
    years_required integer,
    reasoning text,
    extracted_by text,
    recipe_run_id integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    raw_skill_name text,
    CONSTRAINT posting_skills_importance_check CHECK ((importance = ANY (ARRAY['essential'::text, 'critical'::text, 'important'::text, 'preferred'::text, 'bonus'::text]))),
    CONSTRAINT posting_skills_proficiency_check CHECK ((proficiency = ANY (ARRAY['expert'::text, 'advanced'::text, 'intermediate'::text, 'beginner'::text]))),
    CONSTRAINT posting_skills_weight_check CHECK (((weight >= 10) AND (weight <= 100)))
);


ALTER TABLE public.posting_skills OWNER TO base_admin;

--
-- Name: TABLE posting_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.posting_skills IS 'Skills extracted from job postings, normalized to skill_aliases taxonomy';


--
-- Name: posting_skills_posting_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

ALTER TABLE public.posting_skills ALTER COLUMN posting_skill_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.posting_skills_posting_skill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


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
-- Name: posting_state_projection; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posting_state_projection (
    posting_id integer NOT NULL,
    current_step integer NOT NULL,
    current_status text NOT NULL,
    outputs jsonb DEFAULT '{}'::jsonb NOT NULL,
    total_tokens integer DEFAULT 0,
    failure_count integer DEFAULT 0,
    last_updated timestamp with time zone DEFAULT now(),
    current_conversation_id integer
);


ALTER TABLE public.posting_state_projection OWNER TO postgres;

--
-- Name: TABLE posting_state_projection; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posting_state_projection IS 'Materialized view of posting state. Rebuilt from events. Optimized for fast queries.';


--
-- Name: COLUMN posting_state_projection.current_conversation_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.posting_state_projection.current_conversation_id IS 'Current conversation_id (e.g., 9144, 3350). Used by monitor for JOIN with conversations table. Distinct from current_step which stores execution_order.';


--
-- Name: posting_state_snapshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.posting_state_snapshots (
    snapshot_id bigint NOT NULL,
    posting_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.posting_state_snapshots OWNER TO postgres;

--
-- Name: TABLE posting_state_snapshots; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.posting_state_snapshots IS 'Periodic snapshots of posting state. Enables fast state reconstruction without replaying all events.';


--
-- Name: posting_state_snapshots_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.posting_state_snapshots_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posting_state_snapshots_snapshot_id_seq OWNER TO postgres;

--
-- Name: posting_state_snapshots_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.posting_state_snapshots_snapshot_id_seq OWNED BY public.posting_state_snapshots.snapshot_id;


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
    employment_career_level text,
    enabled boolean DEFAULT true,
    job_description text,
    job_title text,
    location_city text,
    location_country text,
    skill_keywords jsonb,
    source_id integer,
    ihl_score integer,
    external_job_id text NOT NULL,
    external_url text NOT NULL,
    posting_status text DEFAULT 'active'::text,
    first_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    source_metadata jsonb,
    updated_at timestamp without time zone DEFAULT now(),
    extracted_summary text,
    processing_notes text,
    source character varying(50),
    external_id character varying(255),
    created_by_interaction_id bigint,
    updated_by_interaction_id bigint,
    invalidated boolean DEFAULT false,
    invalidated_reason text,
    invalidated_at timestamp with time zone,
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
-- Name: COLUMN postings.created_by_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.created_by_interaction_id IS 'Interaction that created this posting (audit trail)';


--
-- Name: COLUMN postings.updated_by_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.updated_by_interaction_id IS 'Last interaction that updated this posting';


--
-- Name: COLUMN postings.invalidated; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.invalidated IS 'Is this posting invalid/corrupt? (NOT deletion)';


--
-- Name: COLUMN postings.invalidated_reason; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.invalidated_reason IS 'Why was this posting invalidated? (duplicate, bad data, etc.)';


--
-- Name: postings_staging_backup; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.postings_staging_backup (
    staging_id bigint,
    interaction_id bigint,
    raw_data jsonb,
    source_website text,
    job_title text,
    company_name text,
    location text,
    job_description text,
    posting_url text,
    salary_range text,
    posted_date date,
    validation_status text,
    validation_errors jsonb,
    validated_at timestamp with time zone,
    validated_by_actor_id integer,
    promoted_to_posting_id integer,
    promoted_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE public.postings_staging_backup OWNER TO base_admin;

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
-- Name: profile_skills_staging; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profile_skills_staging (
    staging_id bigint NOT NULL,
    interaction_id bigint NOT NULL,
    raw_data jsonb NOT NULL,
    profile_id integer,
    skill_name text,
    proficiency_level text,
    years_experience integer,
    context text,
    validation_status text DEFAULT 'pending'::text,
    validation_errors jsonb,
    validated_at timestamp with time zone,
    validated_by_actor_id integer,
    promoted_to_skill_id integer,
    promoted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT profile_skills_staging_validation_status_check CHECK ((validation_status = ANY (ARRAY['pending'::text, 'passed'::text, 'failed'::text, 'promoted'::text])))
);


ALTER TABLE public.profile_skills_staging OWNER TO base_admin;

--
-- Name: TABLE profile_skills_staging; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_skills_staging IS 'Staging area for skill extractor output - validated before promotion to profile_skills';


--
-- Name: profile_skills_staging_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_skills_staging_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_skills_staging_staging_id_seq OWNER TO base_admin;

--
-- Name: profile_skills_staging_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_skills_staging_staging_id_seq OWNED BY public.profile_skills_staging.staging_id;


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
-- Name: qa_findings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.qa_findings (
    finding_id integer NOT NULL,
    posting_id integer NOT NULL,
    check_type character varying(50) NOT NULL,
    check_category character varying(100),
    severity character varying(20) NOT NULL,
    pattern_matched character varying(100),
    description text,
    evidence text,
    field_checked character varying(50),
    field_length integer,
    metric_value numeric,
    detected_at timestamp without time zone DEFAULT now(),
    detected_by character varying(50),
    qa_run_id integer,
    status character varying(20) DEFAULT 'open'::character varying,
    reviewed_by character varying(50),
    reviewed_at timestamp without time zone,
    resolution_notes text,
    CONSTRAINT qa_findings_check_type_check CHECK (((check_type)::text = ANY ((ARRAY['hallucination'::character varying, 'length_outlier'::character varying, 'processing_time_outlier'::character varying, 'manual_review'::character varying, 'data_quality'::character varying, 'other'::character varying])::text[]))),
    CONSTRAINT qa_findings_severity_check CHECK (((severity)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying, 'info'::character varying])::text[])))
);


ALTER TABLE public.qa_findings OWNER TO base_admin;

--
-- Name: TABLE qa_findings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.qa_findings IS 'Stores data quality findings from automated and manual QA checks';


--
-- Name: COLUMN qa_findings.check_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.check_type IS 'Type of QA check performed';


--
-- Name: COLUMN qa_findings.check_category; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.check_category IS 'Specific category within the check type';


--
-- Name: COLUMN qa_findings.pattern_matched; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.pattern_matched IS 'Name of the specific pattern that triggered this finding';


--
-- Name: COLUMN qa_findings.evidence; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.evidence IS 'Sample text or excerpt demonstrating the issue';


--
-- Name: COLUMN qa_findings.metric_value; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.metric_value IS 'Quantitative metric associated with this finding';


--
-- Name: COLUMN qa_findings.qa_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.qa_findings.qa_run_id IS 'Groups findings from the same QA execution';


--
-- Name: qa_findings_finding_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.qa_findings_finding_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.qa_findings_finding_id_seq OWNER TO base_admin;

--
-- Name: qa_findings_finding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.qa_findings_finding_id_seq OWNED BY public.qa_findings.finding_id;


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
    change_reason text,
    environment character varying(10)
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
-- Name: skill_aliases_staging; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_aliases_staging (
    staging_id bigint NOT NULL,
    interaction_id bigint NOT NULL,
    raw_data jsonb NOT NULL,
    skill_name text,
    canonical_skill_name text,
    confidence_score numeric(3,2),
    reasoning text,
    validation_status text DEFAULT 'pending'::text,
    validation_errors jsonb,
    validated_at timestamp with time zone,
    validated_by_actor_id integer,
    promoted_to_alias_id integer,
    promoted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT skill_aliases_staging_validation_status_check CHECK ((validation_status = ANY (ARRAY['pending'::text, 'passed'::text, 'failed'::text, 'promoted'::text])))
);


ALTER TABLE public.skill_aliases_staging OWNER TO base_admin;

--
-- Name: TABLE skill_aliases_staging; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_aliases_staging IS 'Staging area for skill mapper output - validated before promotion to skill_aliases';


--
-- Name: skill_aliases_staging_staging_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_aliases_staging_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_aliases_staging_staging_id_seq OWNER TO base_admin;

--
-- Name: skill_aliases_staging_staging_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.skill_aliases_staging_staging_id_seq OWNED BY public.skill_aliases_staging.staging_id;


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
-- Name: user_company_verifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_company_verifications (
    user_id integer NOT NULL,
    company_id integer NOT NULL,
    is_verified boolean NOT NULL,
    confidence numeric(3,2),
    verification_method character varying(50),
    verified_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone
);


ALTER TABLE public.user_company_verifications OWNER TO postgres;

--
-- Name: TABLE user_company_verifications; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.user_company_verifications IS 'Records that user CAN rate this company (verified employment).
Does NOT store: job title, dates, duration, role, or how we verified.
The verification evidence is deleted after verification completes.';


--
-- Name: COLUMN user_company_verifications.is_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_company_verifications.is_verified IS 'Did verification succeed?';


--
-- Name: COLUMN user_company_verifications.confidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_company_verifications.confidence IS 'Confidence score 0.0-1.0';


--
-- Name: user_feedback; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_feedback (
    feedback_id integer NOT NULL,
    user_id integer,
    report_id integer,
    posting_id integer,
    feedback_type character varying(50) NOT NULL,
    feedback_text text,
    feedback_structured jsonb,
    processed boolean DEFAULT false,
    processed_at timestamp with time zone,
    preferences_updated jsonb,
    created_at timestamp with time zone DEFAULT now(),
    anonymization_model character varying(100)
);


ALTER TABLE public.user_feedback OWNER TO base_admin;

--
-- Name: TABLE user_feedback; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_feedback IS 'User feedback on recommendations. Raw text is anonymized before storage.
Local LLM extracts structured preferences from feedback.';


--
-- Name: user_feedback_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_feedback_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_feedback_feedback_id_seq OWNER TO base_admin;

--
-- Name: user_feedback_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_feedback_feedback_id_seq OWNED BY public.user_feedback.feedback_id;


--
-- Name: user_posting_decisions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_posting_decisions (
    decision_id integer NOT NULL,
    user_id integer NOT NULL,
    posting_id integer NOT NULL,
    cover_letter_draft text,
    no_go_reason text,
    decision_generated_at timestamp with time zone DEFAULT now(),
    decision_workflow_run_id integer,
    CONSTRAINT check_one_decision CHECK ((((cover_letter_draft IS NOT NULL) AND (no_go_reason IS NULL)) OR ((cover_letter_draft IS NULL) AND (no_go_reason IS NOT NULL))))
);


ALTER TABLE public.user_posting_decisions OWNER TO postgres;

--
-- Name: TABLE user_posting_decisions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.user_posting_decisions IS 'User-specific decisions about job postings.
    Each user gets their own cover_letter_draft (if applying) or no_go_reason (if skipping).
    This is multi-user aware - same job can be APPLY for one user, SKIP for another.';


--
-- Name: COLUMN user_posting_decisions.cover_letter_draft; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_posting_decisions.cover_letter_draft IS 'AI-generated personalized cover letter for this user applying to this job. Only set if recommendation is APPLY.';


--
-- Name: COLUMN user_posting_decisions.no_go_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.user_posting_decisions.no_go_reason IS 'AI explanation why this user should NOT apply to this job. Examples: skill gaps, level mismatch, location conflict, high IHL risk. Only set if recommendation is SKIP.';


--
-- Name: user_posting_decisions_decision_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_posting_decisions_decision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_posting_decisions_decision_id_seq OWNER TO postgres;

--
-- Name: user_posting_decisions_decision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_posting_decisions_decision_id_seq OWNED BY public.user_posting_decisions.decision_id;


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

COMMENT ON TABLE public.user_preferences IS 'User matching preferences. Both explicit (user said "no tax jobs") 
and inferred (feedback processor detected pattern).
Weight indicates strength: -1=dealbreaker, +1=must-have.';


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
-- Name: user_profiles; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_profiles (
    profile_id integer NOT NULL,
    user_id integer,
    years_experience integer,
    career_level character varying(50),
    skills jsonb DEFAULT '[]'::jsonb,
    work_history jsonb DEFAULT '[]'::jsonb,
    education jsonb DEFAULT '[]'::jsonb,
    target_roles jsonb DEFAULT '[]'::jsonb,
    target_locations jsonb DEFAULT '[]'::jsonb,
    target_industries jsonb DEFAULT '[]'::jsonb,
    salary_min integer,
    salary_max integer,
    version integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    anonymization_model character varying(100),
    anonymization_timestamp timestamp with time zone
);


ALTER TABLE public.user_profiles OWNER TO base_admin;

--
-- Name: TABLE user_profiles; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_profiles IS 'Anonymized career profile. Extracted from user-provided resume/CV.
The original document is NEVER stored. Only this anonymized extract exists.
Contains NO: names, company names, school names, dates, contact info.';


--
-- Name: user_profiles_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_profiles_profile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_profiles_profile_id_seq OWNER TO base_admin;

--
-- Name: user_profiles_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_profiles_profile_id_seq OWNED BY public.user_profiles.profile_id;


--
-- Name: user_reports; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_reports (
    report_id integer NOT NULL,
    user_id integer,
    report_type character varying(50) DEFAULT 'weekly'::character varying,
    report_period_start date,
    report_period_end date,
    postings jsonb NOT NULL,
    delivered_at timestamp with time zone,
    opened_at timestamp with time zone,
    feedback_received integer DEFAULT 0,
    matching_algorithm_version character varying(20),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_reports OWNER TO base_admin;

--
-- Name: TABLE user_reports; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_reports IS 'Weekly job recommendation reports sent to users.
Stores which postings were recommended and why.';


--
-- Name: user_reports_report_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_reports_report_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_reports_report_id_seq OWNER TO base_admin;

--
-- Name: user_reports_report_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_reports_report_id_seq OWNED BY public.user_reports.report_id;


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
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_sessions (
    session_id integer NOT NULL,
    user_id integer,
    session_token_hash character varying(64),
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone,
    revoked_at timestamp with time zone,
    device_type character varying(20)
);


ALTER TABLE public.user_sessions OWNER TO base_admin;

--
-- Name: TABLE user_sessions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_sessions IS 'Minimal session tracking. No IP addresses, no detailed device info.
Just enough to manage authentication state.';


--
-- Name: user_sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_sessions_session_id_seq OWNER TO base_admin;

--
-- Name: user_sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_sessions_session_id_seq OWNED BY public.user_sessions.session_id;


--
-- Name: user_verifications; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.user_verifications (
    verification_id integer NOT NULL,
    user_id integer,
    verification_type character varying(50) NOT NULL,
    claimed_value character varying(200),
    is_verified boolean NOT NULL,
    confidence numeric(3,2),
    verification_method character varying(50),
    verified_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone
);


ALTER TABLE public.user_verifications OWNER TO base_admin;

--
-- Name: TABLE user_verifications; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.user_verifications IS 'Verification results using "verify then forget" pattern.
We verify claims (e.g., "worked at Goldman") via web search,
but store ONLY the yes/no result, not the search data.
This protects privacy while enabling trust.';


--
-- Name: user_verifications_verification_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.user_verifications_verification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_verifications_verification_id_seq OWNER TO base_admin;

--
-- Name: user_verifications_verification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.user_verifications_verification_id_seq OWNED BY public.user_verifications.verification_id;


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
    enabled boolean DEFAULT true NOT NULL,
    is_entry_point boolean DEFAULT false NOT NULL,
    entry_condition text,
    execute_once_per_run boolean DEFAULT false,
    CONSTRAINT workflow_conversations_execute_condition_check CHECK ((execute_condition = ANY (ARRAY['always'::text, 'on_success'::text, 'on_failure'::text]))),
    CONSTRAINT workflow_conversations_on_failure_action_check CHECK ((on_failure_action = ANY (ARRAY['stop'::text, 'retry'::text, 'skip_to'::text]))),
    CONSTRAINT workflow_conversations_on_success_action_check CHECK ((on_success_action = ANY (ARRAY['continue'::text, 'skip_to'::text, 'stop'::text])))
);


ALTER TABLE public.workflow_conversations OWNER TO base_admin;

--
-- Name: TABLE workflow_conversations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_conversations IS 'Maps conversations to workflows in execution order. Step 2 (validation) added Nov 26, 2025 to prevent processing postings with NULL/short job_description.';


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

COMMENT ON COLUMN public.workflow_conversations.execute_condition IS 'SQL expression or keyword to determine if conversation should execute. 
Examples: 
  - "always" (default)
  - "skip" (never execute)
  - SQL expression that returns boolean (future enhancement)';


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
-- Name: COLUMN workflow_conversations.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.enabled IS 'Soft enable/disable flag - allows deactivating workflow steps without deletion';


--
-- Name: COLUMN workflow_conversations.is_entry_point; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.is_entry_point IS 'True if postings can enter workflow at this conversation';


--
-- Name: COLUMN workflow_conversations.entry_condition; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.entry_condition IS 'SQL condition for when this entry point applies (e.g., "extracted_summary IS NULL")';


--
-- Name: COLUMN workflow_conversations.execute_once_per_run; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_conversations.execute_once_per_run IS 'If TRUE, this step executes ONCE at workflow start (not per-posting). Used for data ingestion steps like "Fetch Jobs from API".';


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
-- Name: workflow_doc_queue; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_doc_queue (
    workflow_id integer NOT NULL,
    needs_regeneration boolean DEFAULT true,
    last_changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_generated_at timestamp without time zone,
    change_count integer DEFAULT 1
);


ALTER TABLE public.workflow_doc_queue OWNER TO base_admin;

--
-- Name: TABLE workflow_doc_queue; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_doc_queue IS 'Tracks workflows needing doc regeneration (single trigger on workflow_conversations)';


--
-- Name: workflow_errors; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_errors (
    error_id integer NOT NULL,
    workflow_run_id integer,
    posting_id integer,
    conversation_id integer,
    actor_id integer,
    execution_order integer,
    error_type text NOT NULL,
    error_message text,
    actor_output text,
    stack_trace text,
    context jsonb,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone,
    resolution_notes text
);


ALTER TABLE public.workflow_errors OWNER TO base_admin;

--
-- Name: TABLE workflow_errors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_errors IS 'Tracks all workflow execution errors with full context. Enables debugging without log files.';


--
-- Name: workflow_errors_error_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_errors_error_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_errors_error_id_seq OWNER TO base_admin;

--
-- Name: workflow_errors_error_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_errors_error_id_seq OWNED BY public.workflow_errors.error_id;


--
-- Name: workflow_metrics; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_metrics (
    metric_id integer NOT NULL,
    workflow_run_id integer NOT NULL,
    conversation_id integer,
    posting_id integer,
    metric_name text NOT NULL,
    metric_value numeric,
    metric_unit text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.workflow_metrics OWNER TO base_admin;

--
-- Name: TABLE workflow_metrics; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_metrics IS 'Performance metrics for workflow executions';


--
-- Name: COLUMN workflow_metrics.metric_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_metrics.metric_name IS 'Metric type: latency_ms, tokens_input, tokens_output, cost_usd, throughput';


--
-- Name: COLUMN workflow_metrics.metric_value; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_metrics.metric_value IS 'Numeric value of metric';


--
-- Name: COLUMN workflow_metrics.metric_unit; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_metrics.metric_unit IS 'Unit of measurement: ms, tokens, usd, postings/sec';


--
-- Name: workflow_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_metrics_metric_id_seq OWNER TO base_admin;

--
-- Name: workflow_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_metrics_metric_id_seq OWNED BY public.workflow_metrics.metric_id;


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
-- Name: workflow_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_runs (
    workflow_run_id bigint NOT NULL,
    workflow_id integer NOT NULL,
    posting_id integer,
    status text DEFAULT 'running'::text NOT NULL,
    started_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    created_by text,
    metadata jsonb,
    environment text NOT NULL,
    state jsonb DEFAULT '{}'::jsonb,
    updated_at timestamp with time zone DEFAULT now(),
    seed_interaction_id bigint,
    CONSTRAINT workflow_runs_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'stopped'::text, 'interrupted'::text])))
);


ALTER TABLE public.workflow_runs OWNER TO base_admin;

--
-- Name: TABLE workflow_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_runs IS 'Metadata index for workflow execution monitoring (NOT a container)';


--
-- Name: COLUMN workflow_runs.environment; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.environment IS 'Inherited from workflows.environment. Used to filter/cleanup test runs.
Cleanup policy: DELETE test/dev runs older than 30 days, keep uat/prod forever.';


--
-- Name: COLUMN workflow_runs.seed_interaction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_runs.seed_interaction_id IS 'The first interaction that kicked off this workflow run. Links workflow_run to its complete interaction chain.';


--
-- Name: workflow_runs_workflow_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_runs_workflow_run_id_seq
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
-- Name: workflow_step_metrics; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_step_metrics (
    metric_id integer NOT NULL,
    workflow_run_id integer NOT NULL,
    conversation_id integer NOT NULL,
    conversation_name character varying(255),
    execution_order integer,
    started_at timestamp without time zone DEFAULT now() NOT NULL,
    completed_at timestamp without time zone,
    duration_seconds numeric(10,2),
    postings_processed integer DEFAULT 0,
    postings_succeeded integer DEFAULT 0,
    postings_failed integer DEFAULT 0,
    avg_time_per_posting numeric(10,2),
    min_time_per_posting numeric(10,2),
    max_time_per_posting numeric(10,2),
    total_llm_calls integer DEFAULT 0,
    total_tokens_input integer DEFAULT 0,
    total_tokens_output integer DEFAULT 0,
    total_cost_usd numeric(10,6) DEFAULT 0,
    avg_latency_ms integer,
    status character varying(50) DEFAULT 'in_progress'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.workflow_step_metrics OWNER TO base_admin;

--
-- Name: TABLE workflow_step_metrics; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_step_metrics IS 'Tracks performance metrics for each conversation/step execution in a workflow run';


--
-- Name: workflow_step_metrics_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_step_metrics_metric_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_step_metrics_metric_id_seq OWNER TO base_admin;

--
-- Name: workflow_step_metrics_metric_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_step_metrics_metric_id_seq OWNED BY public.workflow_step_metrics.metric_id;


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
    event_fetch_query text,
    CONSTRAINT workflow_triggers_trigger_type_check CHECK (((trigger_type)::text = ANY ((ARRAY['SCHEDULE'::character varying, 'EVENT'::character varying, 'MANUAL'::character varying, 'DEPENDENCY'::character varying])::text[])))
);


ALTER TABLE public.workflow_triggers OWNER TO base_admin;

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
-- Name: workflow_variables; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.workflow_variables (
    variable_id integer NOT NULL,
    variable_name text NOT NULL,
    workflow_id integer,
    scope text NOT NULL,
    data_type text NOT NULL,
    json_schema jsonb,
    is_required boolean DEFAULT false,
    default_value jsonb,
    description text,
    example_value jsonb,
    python_type text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    is_current boolean DEFAULT true,
    version integer DEFAULT 1,
    CONSTRAINT workflow_variables_scope_check CHECK ((scope = ANY (ARRAY['input'::text, 'output'::text, 'internal'::text, 'global'::text])))
);


ALTER TABLE public.workflow_variables OWNER TO base_admin;

--
-- Name: TABLE workflow_variables; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.workflow_variables IS 'Registry of all workflow input/output variables with type contracts';


--
-- Name: COLUMN workflow_variables.scope; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_variables.scope IS 'Variable scope: input (passed to workflow), output (returned), internal (used during execution), global (cross-workflow)';


--
-- Name: COLUMN workflow_variables.json_schema; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_variables.json_schema IS 'JSON Schema for validation (auto-generated from Python dataclasses)';


--
-- Name: COLUMN workflow_variables.python_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_variables.python_type IS 'Python type annotation for code generation';


--
-- Name: COLUMN workflow_variables.is_current; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflow_variables.is_current IS 'False for deprecated versions, true for current contract';


--
-- Name: workflow_variables_variable_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.workflow_variables_variable_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.workflow_variables_variable_id_seq OWNER TO base_admin;

--
-- Name: workflow_variables_variable_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.workflow_variables_variable_id_seq OWNED BY public.workflow_variables.variable_id;


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
    documentation text,
    environment character varying(10) DEFAULT 'DEV'::character varying NOT NULL,
    app_scope text,
    skip_data_writes boolean DEFAULT false,
    CONSTRAINT workflows_environment_check CHECK (((environment)::text = ANY ((ARRAY['dev'::character varying, 'test'::character varying, 'uat'::character varying, 'prod'::character varying, 'old'::character varying])::text[])))
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

COMMENT ON COLUMN public.workflows.workflow_id IS 'Workflow 1126: Profile Document Import - LLM-based extraction with validation';


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
-- Name: COLUMN workflows.environment; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.environment IS 'Execution environment: dev (development), test (shadow testing), uat (stakeholder review), prod (production), old (archived).
Test/UAT workflows should set skip_data_writes=TRUE to prevent writing to postings/profiles tables.';


--
-- Name: COLUMN workflows.app_scope; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.app_scope IS 'Application scope: talent, news, write, research, contract. Isolates workflows by product.';


--
-- Name: COLUMN workflows.skip_data_writes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.workflows.skip_data_writes IS 'If TRUE, saver scripts will skip writing to data tables (postings, profiles, etc).
Used for shadow testing where we want to compare model outputs without affecting production data.';


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
-- Name: actor_code_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_code_history ALTER COLUMN history_id SET DEFAULT nextval('public.actor_code_history_history_id_seq'::regclass);


--
-- Name: actor_rate_control rate_control_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_rate_control ALTER COLUMN rate_control_id SET DEFAULT nextval('public.actor_rate_control_rate_control_id_seq'::regclass);


--
-- Name: app_users user_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.app_users ALTER COLUMN user_id SET DEFAULT nextval('public.app_users_user_id_seq'::regclass);


--
-- Name: batches batch_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches ALTER COLUMN batch_id SET DEFAULT nextval('public.batches_batch_id_seq'::regclass);


--
-- Name: circuit_breaker_events event_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.circuit_breaker_events ALTER COLUMN event_id SET DEFAULT nextval('public.circuit_breaker_events_event_id_seq'::regclass);


--
-- Name: companies company_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.companies ALTER COLUMN company_id SET DEFAULT nextval('public.companies_company_id_seq'::regclass);


--
-- Name: company_ratings rating_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_ratings ALTER COLUMN rating_id SET DEFAULT nextval('public.company_ratings_rating_id_seq'::regclass);


--
-- Name: conversation_dialogue dialogue_step_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversation_dialogue ALTER COLUMN dialogue_step_id SET DEFAULT nextval('public.conversation_dialogue_dialogue_step_id_seq'::regclass);


--
-- Name: conversations_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations_history ALTER COLUMN history_id SET DEFAULT nextval('public.sessions_history_history_id_seq'::regclass);


--
-- Name: execution_events event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_events ALTER COLUMN event_id SET DEFAULT nextval('public.execution_events_event_id_seq'::regclass);


--
-- Name: instruction_step_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_step_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.instruction_branch_executions_execution_id_seq'::regclass);


--
-- Name: instructions_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions_history ALTER COLUMN history_id SET DEFAULT nextval('public.instructions_history_history_id_seq'::regclass);


--
-- Name: interaction_events event_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_events ALTER COLUMN event_id SET DEFAULT nextval('public.interaction_events_event_id_seq'::regclass);


--
-- Name: interactions interaction_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions ALTER COLUMN interaction_id SET DEFAULT nextval('public.interactions_interaction_id_seq'::regclass);


--
-- Name: interactions_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions_history ALTER COLUMN history_id SET DEFAULT nextval('public.interactions_history_history_id_seq'::regclass);


--
-- Name: job_skills_staging staging_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills_staging ALTER COLUMN staging_id SET DEFAULT nextval('public.job_skills_staging_staging_id_seq'::regclass);


--
-- Name: posting_state_snapshots snapshot_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_state_snapshots ALTER COLUMN snapshot_id SET DEFAULT nextval('public.posting_state_snapshots_snapshot_id_seq'::regclass);


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
-- Name: profile_skills_staging staging_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills_staging ALTER COLUMN staging_id SET DEFAULT nextval('public.profile_skills_staging_staging_id_seq'::regclass);


--
-- Name: profile_work_history work_history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history ALTER COLUMN work_history_id SET DEFAULT nextval('public.profile_work_history_work_history_id_seq'::regclass);


--
-- Name: profiles profile_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles ALTER COLUMN profile_id SET DEFAULT nextval('public.profiles_profile_id_seq'::regclass);


--
-- Name: qa_findings finding_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.qa_findings ALTER COLUMN finding_id SET DEFAULT nextval('public.qa_findings_finding_id_seq'::regclass);


--
-- Name: script_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.script_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.script_executions_execution_id_seq'::regclass);


--
-- Name: skill_aliases_staging staging_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases_staging ALTER COLUMN staging_id SET DEFAULT nextval('public.skill_aliases_staging_staging_id_seq'::regclass);


--
-- Name: skill_occurrences occurrence_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences ALTER COLUMN occurrence_id SET DEFAULT nextval('public.skill_occurrences_occurrence_id_seq'::regclass);


--
-- Name: stored_scripts script_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.stored_scripts ALTER COLUMN script_id SET DEFAULT nextval('public.stored_scripts_script_id_seq'::regclass);


--
-- Name: user_feedback feedback_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_feedback ALTER COLUMN feedback_id SET DEFAULT nextval('public.user_feedback_feedback_id_seq'::regclass);


--
-- Name: user_posting_decisions decision_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_posting_decisions ALTER COLUMN decision_id SET DEFAULT nextval('public.user_posting_decisions_decision_id_seq'::regclass);


--
-- Name: user_profiles profile_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_profiles ALTER COLUMN profile_id SET DEFAULT nextval('public.user_profiles_profile_id_seq'::regclass);


--
-- Name: user_reports report_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_reports ALTER COLUMN report_id SET DEFAULT nextval('public.user_reports_report_id_seq'::regclass);


--
-- Name: user_sessions session_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_sessions ALTER COLUMN session_id SET DEFAULT nextval('public.user_sessions_session_id_seq'::regclass);


--
-- Name: user_verifications verification_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_verifications ALTER COLUMN verification_id SET DEFAULT nextval('public.user_verifications_verification_id_seq'::regclass);


--
-- Name: workflow_conversations step_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_conversations ALTER COLUMN step_id SET DEFAULT nextval('public.workflow_conversations_step_id_seq'::regclass);


--
-- Name: workflow_dependencies dependency_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_dependencies ALTER COLUMN dependency_id SET DEFAULT nextval('public.workflow_dependencies_dependency_id_seq'::regclass);


--
-- Name: workflow_errors error_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_errors ALTER COLUMN error_id SET DEFAULT nextval('public.workflow_errors_error_id_seq'::regclass);


--
-- Name: workflow_metrics metric_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.workflow_metrics_metric_id_seq'::regclass);


--
-- Name: workflow_runs workflow_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs ALTER COLUMN workflow_run_id SET DEFAULT nextval('public.workflow_runs_workflow_run_id_seq'::regclass);


--
-- Name: workflow_step_metrics metric_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_step_metrics ALTER COLUMN metric_id SET DEFAULT nextval('public.workflow_step_metrics_metric_id_seq'::regclass);


--
-- Name: workflow_triggers trigger_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers ALTER COLUMN trigger_id SET DEFAULT nextval('public.workflow_triggers_trigger_id_seq'::regclass);


--
-- Name: workflow_variables variable_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_variables ALTER COLUMN variable_id SET DEFAULT nextval('public.workflow_variables_variable_id_seq'::regclass);


--
-- Name: workflows workflow_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows ALTER COLUMN workflow_id SET DEFAULT nextval('public.workflows_workflow_id_seq'::regclass);


--
-- Name: workflows_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflows_history ALTER COLUMN history_id SET DEFAULT nextval('public.recipes_history_history_id_seq'::regclass);


--
-- Name: actor_code_history actor_code_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_code_history
    ADD CONSTRAINT actor_code_history_pkey PRIMARY KEY (history_id);


--
-- Name: actor_rate_control actor_rate_control_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_rate_control
    ADD CONSTRAINT actor_rate_control_pkey PRIMARY KEY (rate_control_id);


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
-- Name: app_users app_users_oauth_provider_oauth_subject_hash_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_oauth_provider_oauth_subject_hash_key UNIQUE (oauth_provider, oauth_subject_hash);


--
-- Name: app_users app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (user_id);


--
-- Name: batches batches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches
    ADD CONSTRAINT batches_pkey PRIMARY KEY (batch_id);


--
-- Name: circuit_breaker_events circuit_breaker_events_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.circuit_breaker_events
    ADD CONSTRAINT circuit_breaker_events_pkey PRIMARY KEY (event_id);


--
-- Name: city_country_map city_country_map_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.city_country_map
    ADD CONSTRAINT city_country_map_pkey PRIMARY KEY (city_id);


--
-- Name: companies companies_company_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_company_name_key UNIQUE (company_name);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (company_id);


--
-- Name: company_ratings company_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_ratings
    ADD CONSTRAINT company_ratings_pkey PRIMARY KEY (rating_id);


--
-- Name: company_ratings company_ratings_user_id_company_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_ratings
    ADD CONSTRAINT company_ratings_user_id_company_id_key UNIQUE (user_id, company_id);


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
-- Name: conversation_tag_definitions conversation_tag_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_tag_definitions
    ADD CONSTRAINT conversation_tag_definitions_pkey PRIMARY KEY (tag);


--
-- Name: conversation_tags conversation_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_tags
    ADD CONSTRAINT conversation_tags_pkey PRIMARY KEY (conversation_id, tag);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id);


--
-- Name: execution_events execution_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_events
    ADD CONSTRAINT execution_events_pkey PRIMARY KEY (event_id);


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
-- Name: interaction_events interaction_events_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_events
    ADD CONSTRAINT interaction_events_pkey PRIMARY KEY (event_id);


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
-- Name: interactions_history interactions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions_history
    ADD CONSTRAINT interactions_history_pkey PRIMARY KEY (history_id);


--
-- Name: interactions interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_pkey PRIMARY KEY (interaction_id);


--
-- Name: job_skills_staging job_skills_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills_staging
    ADD CONSTRAINT job_skills_staging_pkey PRIMARY KEY (staging_id);


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
-- Name: posting_fetch_runs posting_fetch_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_fetch_runs
    ADD CONSTRAINT posting_fetch_runs_pkey PRIMARY KEY (fetch_run_id);


--
-- Name: posting_field_mappings posting_field_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_field_mappings
    ADD CONSTRAINT posting_field_mappings_pkey PRIMARY KEY (mapping_id);


--
-- Name: posting_processing_status posting_processing_status_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_pkey PRIMARY KEY (posting_id);


--
-- Name: posting_skills posting_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_skills
    ADD CONSTRAINT posting_skills_pkey PRIMARY KEY (posting_skill_id);


--
-- Name: posting_skills posting_skills_posting_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_skills
    ADD CONSTRAINT posting_skills_posting_id_skill_id_key UNIQUE (posting_id, skill_id);


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
-- Name: posting_state_projection posting_state_projection_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_state_projection
    ADD CONSTRAINT posting_state_projection_pkey PRIMARY KEY (posting_id);


--
-- Name: posting_state_snapshots posting_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_state_snapshots
    ADD CONSTRAINT posting_state_snapshots_pkey PRIMARY KEY (snapshot_id);


--
-- Name: postings postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_pkey PRIMARY KEY (posting_id);


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
-- Name: profile_skills_staging profile_skills_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills_staging
    ADD CONSTRAINT profile_skills_staging_pkey PRIMARY KEY (staging_id);


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
-- Name: qa_findings qa_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.qa_findings
    ADD CONSTRAINT qa_findings_pkey PRIMARY KEY (finding_id);


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
-- Name: skill_aliases_staging skill_aliases_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases_staging
    ADD CONSTRAINT skill_aliases_staging_pkey PRIMARY KEY (staging_id);


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
-- Name: postings unique_external_id_per_source; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT unique_external_id_per_source UNIQUE (source_id, external_id);


--
-- Name: execution_events unique_idempotency_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_events
    ADD CONSTRAINT unique_idempotency_key UNIQUE (idempotency_key);


--
-- Name: user_company_verifications user_company_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_company_verifications
    ADD CONSTRAINT user_company_verifications_pkey PRIMARY KEY (user_id, company_id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (feedback_id);


--
-- Name: user_posting_decisions user_posting_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_posting_decisions
    ADD CONSTRAINT user_posting_decisions_pkey PRIMARY KEY (decision_id);


--
-- Name: user_posting_decisions user_posting_decisions_user_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_posting_decisions
    ADD CONSTRAINT user_posting_decisions_user_id_posting_id_key UNIQUE (user_id, posting_id);


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
-- Name: user_profiles user_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (profile_id);


--
-- Name: user_reports user_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_reports
    ADD CONSTRAINT user_reports_pkey PRIMARY KEY (report_id);


--
-- Name: user_saved_postings user_saved_postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_saved_postings
    ADD CONSTRAINT user_saved_postings_pkey PRIMARY KEY (user_id, posting_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: user_verifications user_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_verifications
    ADD CONSTRAINT user_verifications_pkey PRIMARY KEY (verification_id);


--
-- Name: user_verifications user_verifications_user_id_verification_type_claimed_value_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_verifications
    ADD CONSTRAINT user_verifications_user_id_verification_type_claimed_value_key UNIQUE (user_id, verification_type, claimed_value);


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
-- Name: workflow_doc_queue workflow_doc_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_doc_queue
    ADD CONSTRAINT workflow_doc_queue_pkey PRIMARY KEY (workflow_id);


--
-- Name: workflow_errors workflow_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_errors
    ADD CONSTRAINT workflow_errors_pkey PRIMARY KEY (error_id);


--
-- Name: workflow_metrics workflow_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_metrics
    ADD CONSTRAINT workflow_metrics_pkey PRIMARY KEY (metric_id);


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
-- Name: workflow_step_metrics workflow_step_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_step_metrics
    ADD CONSTRAINT workflow_step_metrics_pkey PRIMARY KEY (metric_id);


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
-- Name: workflow_variables workflow_variables_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_variables
    ADD CONSTRAINT workflow_variables_pkey PRIMARY KEY (variable_id);


--
-- Name: workflow_variables workflow_variables_workflow_id_variable_name_scope_version_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_variables
    ADD CONSTRAINT workflow_variables_workflow_id_variable_name_scope_version_key UNIQUE (workflow_id, variable_name, scope, version);


--
-- Name: CONSTRAINT workflow_variables_workflow_id_variable_name_scope_version_key ON workflow_variables; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON CONSTRAINT workflow_variables_workflow_id_variable_name_scope_version_key ON public.workflow_variables IS 'Ensures uniqueness per workflow + variable name + scope + version. 
Same variable name can exist in different scopes (input vs output).';


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
-- Name: idx_actor_code_history_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actor_code_history_active ON public.actor_code_history USING btree (actor_id) WHERE (deactivated_at IS NULL);


--
-- Name: idx_actor_code_history_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actor_code_history_actor ON public.actor_code_history USING btree (actor_id, activated_at DESC);


--
-- Name: idx_actor_code_history_hash; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actor_code_history_hash ON public.actor_code_history USING btree (script_code_hash);


--
-- Name: idx_actor_perf_actor_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_actor_perf_actor_id ON public.actor_performance_summary USING btree (actor_id);


--
-- Name: idx_actor_rate_control_actor_time; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actor_rate_control_actor_time ON public.actor_rate_control USING btree (actor_id, check_time DESC);


--
-- Name: idx_actor_rate_control_denied; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_actor_rate_control_denied ON public.actor_rate_control USING btree (check_time DESC) WHERE (was_allowed = false);


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
-- Name: idx_aggregate_events; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_aggregate_events ON public.execution_events USING btree (aggregate_type, aggregate_id, aggregate_version);


--
-- Name: idx_aggregate_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_aggregate_version ON public.execution_events USING btree (aggregate_type, aggregate_id, aggregate_version);


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
-- Name: idx_causation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_causation ON public.execution_events USING btree (causation_id);


--
-- Name: idx_certifications_expiration; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_expiration ON public.profile_certifications USING btree (expiration_date);


--
-- Name: idx_certifications_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_profile ON public.profile_certifications USING btree (profile_id);


--
-- Name: idx_circuit_breaker_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_circuit_breaker_actor ON public.circuit_breaker_events USING btree (actor_id, created_at DESC);


--
-- Name: idx_circuit_breaker_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_circuit_breaker_type ON public.circuit_breaker_events USING btree (event_type, created_at DESC);


--
-- Name: idx_city_country_map_city; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_country_map_city ON public.city_country_map USING btree (lower(city));


--
-- Name: idx_city_country_map_city_ascii; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_city_country_map_city_ascii ON public.city_country_map USING btree (lower(city_ascii));


--
-- Name: idx_companies_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_companies_name ON public.companies USING btree (company_name);


--
-- Name: idx_company_ratings_company; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_company_ratings_company ON public.company_ratings USING btree (company_id);


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
-- Name: idx_conversation_tags_tag; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_conversation_tags_tag ON public.conversation_tags USING btree (tag);


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
-- Name: idx_correlation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_correlation ON public.execution_events USING btree (correlation_id, event_timestamp);


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
-- Name: idx_event_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_timestamp ON public.execution_events USING btree (event_timestamp DESC);


--
-- Name: idx_event_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_type ON public.execution_events USING btree (event_type, event_timestamp DESC);


--
-- Name: idx_execution_events_aggregate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_aggregate ON public.execution_events USING btree (aggregate_type, aggregate_id);


--
-- Name: idx_execution_events_aggregate_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_aggregate_time ON public.execution_events USING btree (aggregate_id, event_timestamp DESC);


--
-- Name: idx_execution_events_conversation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_conversation ON public.execution_events USING btree (((metadata ->> 'conversation_id'::text)));


--
-- Name: idx_execution_events_invalidated; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_invalidated ON public.execution_events USING btree (invalidated) WHERE (invalidated = false);


--
-- Name: idx_execution_events_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_timestamp ON public.execution_events USING btree (event_timestamp DESC);


--
-- Name: idx_execution_events_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_execution_events_type ON public.execution_events USING btree (event_type);


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
-- Name: idx_interaction_events_causation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interaction_events_causation ON public.interaction_events USING btree (causation_event_id);


--
-- Name: idx_interaction_events_correlation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interaction_events_correlation ON public.interaction_events USING btree (correlation_id);


--
-- Name: idx_interaction_events_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interaction_events_interaction ON public.interaction_events USING btree (interaction_id, event_timestamp);


--
-- Name: idx_interaction_events_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interaction_events_type ON public.interaction_events USING btree (event_type, event_timestamp);


--
-- Name: idx_interactions_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_actor ON public.interactions USING btree (actor_id, status);


--
-- Name: idx_interactions_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_conversation ON public.interactions USING btree (posting_id, conversation_id);


--
-- Name: idx_interactions_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_enabled ON public.interactions USING btree (enabled, invalidated) WHERE ((enabled = true) AND (invalidated = false));


--
-- Name: idx_interactions_history_archived_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_history_archived_at ON public.interactions_history USING btree (archived_at);


--
-- Name: idx_interactions_history_conversation_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_history_conversation_id ON public.interactions_history USING btree (conversation_id);


--
-- Name: idx_interactions_history_interaction_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_history_interaction_id ON public.interactions_history USING btree (interaction_id);


--
-- Name: idx_interactions_history_posting_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_history_posting_id ON public.interactions_history USING btree (posting_id);


--
-- Name: idx_interactions_history_workflow_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_history_workflow_run ON public.interactions_history USING btree (workflow_run_id);


--
-- Name: idx_interactions_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_parent ON public.interactions USING btree (parent_interaction_id);


--
-- Name: idx_interactions_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_posting ON public.interactions USING btree (posting_id, conversation_id, execution_order);


--
-- Name: idx_interactions_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_status ON public.interactions USING btree (status, updated_at) WHERE (status = ANY (ARRAY['pending'::text, 'running'::text]));


--
-- Name: idx_interactions_trigger; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_trigger ON public.interactions USING btree (trigger_interaction_id) WHERE (trigger_interaction_id IS NOT NULL);


--
-- Name: idx_interactions_workflow_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_interactions_workflow_run ON public.interactions USING btree (workflow_run_id, status);


--
-- Name: idx_job_skills_staging_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_staging_interaction ON public.job_skills_staging USING btree (interaction_id);


--
-- Name: idx_job_skills_staging_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_staging_posting ON public.job_skills_staging USING btree (posting_id);


--
-- Name: idx_job_skills_staging_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_staging_status ON public.job_skills_staging USING btree (validation_status);


--
-- Name: idx_job_sources_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_sources_active ON public.job_sources USING btree (is_active, priority);


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
-- Name: idx_llm_interactions_idempotency; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_interactions_idempotency ON public.llm_interactions USING btree (workflow_run_id, status) WHERE (status = 'SUCCESS'::text);


--
-- Name: idx_llm_interactions_status_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_llm_interactions_status_conversation ON public.llm_interactions USING btree (status, conversation_run_id) WHERE (status = 'SUCCESS'::text);


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
-- Name: idx_metrics_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_metrics_conversation ON public.workflow_metrics USING btree (conversation_id, created_at DESC);


--
-- Name: idx_metrics_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_metrics_name ON public.workflow_metrics USING btree (metric_name, created_at DESC);


--
-- Name: idx_metrics_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_metrics_posting ON public.workflow_metrics USING btree (posting_id, created_at DESC);


--
-- Name: idx_metrics_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_metrics_run ON public.workflow_metrics USING btree (workflow_run_id);


--
-- Name: idx_organizations_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_organizations_name ON public.organizations USING btree (organization_name);


--
-- Name: idx_perf_metrics_actor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_perf_metrics_actor ON public.llm_performance_metrics USING btree (actor_id);


--
-- Name: idx_placeholder_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_placeholder_name ON public.placeholder_definitions USING btree (placeholder_name);


--
-- Name: idx_placeholder_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_placeholder_source ON public.placeholder_definitions USING btree (source_type, source_table);


--
-- Name: idx_posting_fetch_runs_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_fetch_runs_source ON public.posting_fetch_runs USING btree (source_id, fetch_started_at DESC);


--
-- Name: idx_posting_fetch_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_fetch_runs_status ON public.posting_fetch_runs USING btree (status, fetch_started_at DESC);


--
-- Name: idx_posting_fetch_runs_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_fetch_runs_workflow ON public.posting_fetch_runs USING btree (workflow_run_id);


--
-- Name: idx_posting_skills_importance; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_skills_importance ON public.posting_skills USING btree (importance);


--
-- Name: idx_posting_skills_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_skills_posting ON public.posting_skills USING btree (posting_id);


--
-- Name: idx_posting_skills_raw_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_skills_raw_name ON public.posting_skills USING btree (lower(raw_skill_name));


--
-- Name: idx_posting_skills_raw_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_posting_skills_raw_unique ON public.posting_skills USING btree (posting_id, lower(raw_skill_name)) WHERE (skill_id IS NULL);


--
-- Name: idx_posting_skills_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_skills_skill ON public.posting_skills USING btree (skill_id);


--
-- Name: idx_posting_skills_weight; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_skills_weight ON public.posting_skills USING btree (weight);


--
-- Name: idx_posting_sources_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_posting_sources_active ON public.posting_sources USING btree (is_active);


--
-- Name: idx_postings_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_active ON public.postings USING btree (posting_status) WHERE (posting_status = 'active'::text);


--
-- Name: idx_postings_completion; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_completion ON public.postings USING btree (posting_id) WHERE ((enabled = true) AND (job_description IS NOT NULL));


--
-- Name: idx_postings_created_by_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_created_by_interaction ON public.postings USING btree (created_by_interaction_id);


--
-- Name: idx_postings_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_enabled ON public.postings USING btree (enabled);


--
-- Name: idx_postings_external; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_external ON public.postings USING btree (source, external_id);


--
-- Name: idx_postings_external_id; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_external_id ON public.postings USING btree (source_id, external_job_id);


--
-- Name: idx_postings_external_job_id_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_external_job_id_unique ON public.postings USING btree (external_job_id) WHERE ((invalidated = false) AND (external_job_id IS NOT NULL));


--
-- Name: idx_postings_external_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_postings_external_unique ON public.postings USING btree (source_id, external_job_id) WHERE (external_job_id IS NOT NULL);


--
-- Name: idx_postings_ihl_score; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_ihl_score ON public.postings USING btree (ihl_score) WHERE (ihl_score IS NOT NULL);


--
-- Name: idx_postings_invalidated; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_invalidated ON public.postings USING btree (invalidated) WHERE (invalidated = true);


--
-- Name: idx_postings_skills; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_skills ON public.postings USING gin (skill_keywords);


--
-- Name: idx_postings_source_metadata_gin; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_source_metadata_gin ON public.postings USING gin (source_metadata);


--
-- Name: INDEX idx_postings_source_metadata_gin; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_postings_source_metadata_gin IS 'GIN index for fast JSONB queries on source_metadata';


--
-- Name: idx_postings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_status ON public.postings USING btree (posting_status, last_seen_at);


--
-- Name: idx_postings_with_skills; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_with_skills ON public.postings USING btree (posting_id) WHERE (skill_keywords IS NOT NULL);


--
-- Name: INDEX idx_postings_with_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON INDEX public.idx_postings_with_skills IS 'Partial index for postings with extracted skills';


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
-- Name: idx_profile_skills_staging_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_staging_interaction ON public.profile_skills_staging USING btree (interaction_id);


--
-- Name: idx_profile_skills_staging_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_staging_profile ON public.profile_skills_staging USING btree (profile_id);


--
-- Name: idx_profile_skills_staging_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_staging_status ON public.profile_skills_staging USING btree (validation_status);


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
-- Name: idx_projection_conversation_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projection_conversation_id ON public.posting_state_projection USING btree (current_conversation_id);


--
-- Name: idx_projection_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projection_status ON public.posting_state_projection USING btree (current_status);


--
-- Name: idx_projection_step; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projection_step ON public.posting_state_projection USING btree (current_step);


--
-- Name: idx_qa_findings_check_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_check_type ON public.qa_findings USING btree (check_type);


--
-- Name: idx_qa_findings_detected_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_detected_at ON public.qa_findings USING btree (detected_at);


--
-- Name: idx_qa_findings_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_posting ON public.qa_findings USING btree (posting_id);


--
-- Name: idx_qa_findings_qa_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_qa_run ON public.qa_findings USING btree (qa_run_id);


--
-- Name: idx_qa_findings_severity; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_severity ON public.qa_findings USING btree (severity);


--
-- Name: idx_qa_findings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_qa_findings_status ON public.qa_findings USING btree (status);


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
-- Name: idx_skill_aliases_staging_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_aliases_staging_interaction ON public.skill_aliases_staging USING btree (interaction_id);


--
-- Name: idx_skill_aliases_staging_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_aliases_staging_skill ON public.skill_aliases_staging USING btree (skill_name);


--
-- Name: idx_skill_aliases_staging_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_aliases_staging_status ON public.skill_aliases_staging USING btree (validation_status);


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
-- Name: idx_user_company_verifications_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_company_verifications_company ON public.user_company_verifications USING btree (company_id);


--
-- Name: idx_user_feedback_unprocessed; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_feedback_unprocessed ON public.user_feedback USING btree (processed) WHERE (processed = false);


--
-- Name: idx_user_feedback_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_feedback_user ON public.user_feedback USING btree (user_id);


--
-- Name: idx_user_posting_decisions_generated; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_posting_decisions_generated ON public.user_posting_decisions USING btree (decision_generated_at);


--
-- Name: idx_user_posting_decisions_posting; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_posting_decisions_posting ON public.user_posting_decisions USING btree (posting_id);


--
-- Name: idx_user_posting_decisions_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_posting_decisions_user ON public.user_posting_decisions USING btree (user_id);


--
-- Name: idx_user_preferences_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_preferences_active ON public.user_preferences USING btree (user_id, is_active) WHERE (is_active = true);


--
-- Name: idx_user_prefs_active; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_prefs_active ON public.user_preferences USING btree (is_active);


--
-- Name: idx_user_prefs_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_prefs_user ON public.user_posting_preferences USING btree (user_id);


--
-- Name: idx_user_profiles_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_profiles_user ON public.user_profiles USING btree (user_id);


--
-- Name: idx_user_reports_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_reports_user ON public.user_reports USING btree (user_id);


--
-- Name: idx_user_saved_postings_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_saved_postings_status ON public.user_saved_postings USING btree (application_status);


--
-- Name: idx_user_saved_postings_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_saved_postings_user ON public.user_saved_postings USING btree (user_id);


--
-- Name: idx_user_sessions_token; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_sessions_token ON public.user_sessions USING btree (session_token_hash) WHERE (revoked_at IS NULL);


--
-- Name: idx_user_sessions_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_sessions_user ON public.user_sessions USING btree (user_id);


--
-- Name: idx_user_verifications_user; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_user_verifications_user ON public.user_verifications USING btree (user_id);


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
-- Name: idx_workflow_conversations_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_enabled ON public.workflow_conversations USING btree (enabled);


--
-- Name: idx_workflow_conversations_entry_point; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_conversations_entry_point ON public.workflow_conversations USING btree (workflow_id, is_entry_point) WHERE (is_entry_point = true);


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
-- Name: idx_workflow_errors_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_errors_created ON public.workflow_errors USING btree (created_at DESC);


--
-- Name: idx_workflow_errors_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_errors_posting ON public.workflow_errors USING btree (posting_id);


--
-- Name: idx_workflow_errors_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_errors_type ON public.workflow_errors USING btree (error_type);


--
-- Name: idx_workflow_errors_workflow_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_errors_workflow_run ON public.workflow_errors USING btree (workflow_run_id);


--
-- Name: idx_workflow_placeholders_required; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_placeholders_required ON public.workflow_placeholders USING btree (workflow_id, is_required);


--
-- Name: idx_workflow_placeholders_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_placeholders_workflow ON public.workflow_placeholders USING btree (workflow_id);


--
-- Name: idx_workflow_runs_environment; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_environment ON public.workflow_runs USING btree (environment, started_at);


--
-- Name: idx_workflow_runs_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_posting ON public.workflow_runs USING btree (posting_id);


--
-- Name: idx_workflow_runs_seed_interaction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_seed_interaction ON public.workflow_runs USING btree (seed_interaction_id);


--
-- Name: idx_workflow_runs_state; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_state ON public.workflow_runs USING gin (state);


--
-- Name: idx_workflow_runs_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_runs_workflow ON public.workflow_runs USING btree (workflow_id, status);


--
-- Name: idx_workflow_step_metrics_conversation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_step_metrics_conversation ON public.workflow_step_metrics USING btree (conversation_id);


--
-- Name: idx_workflow_step_metrics_started_at; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_step_metrics_started_at ON public.workflow_step_metrics USING btree (started_at DESC);


--
-- Name: idx_workflow_step_metrics_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_step_metrics_status ON public.workflow_step_metrics USING btree (status);


--
-- Name: idx_workflow_step_metrics_workflow_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_step_metrics_workflow_run ON public.workflow_step_metrics USING btree (workflow_run_id);


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
-- Name: idx_workflow_variables_current; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_variables_current ON public.workflow_variables USING btree (is_current);


--
-- Name: idx_workflow_variables_scope; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_variables_scope ON public.workflow_variables USING btree (scope);


--
-- Name: idx_workflow_variables_workflow; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflow_variables_workflow ON public.workflow_variables USING btree (workflow_id);


--
-- Name: idx_workflows_documentation_fts; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_documentation_fts ON public.workflows USING gin (to_tsvector('english'::regconfig, COALESCE(documentation, ''::text)));


--
-- Name: idx_workflows_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_enabled ON public.workflows USING btree (enabled);


--
-- Name: idx_workflows_environment; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_environment ON public.workflows USING btree (environment) WHERE (enabled = true);


--
-- Name: idx_workflows_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_workflows_name ON public.workflows USING btree (workflow_name);


--
-- Name: interactions archive_interactions_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER archive_interactions_trigger BEFORE DELETE ON public.interactions FOR EACH ROW EXECUTE FUNCTION public.archive_interaction_before_delete();


--
-- Name: TRIGGER archive_interactions_trigger ON interactions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TRIGGER archive_interactions_trigger ON public.interactions IS 'Automatically archives interactions to history table before deletion';


--
-- Name: workflows archive_workflows_on_update; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER archive_workflows_on_update BEFORE UPDATE ON public.workflows FOR EACH ROW EXECUTE FUNCTION public.archive_workflows();


--
-- Name: profile_certifications certifications_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER certifications_updated_at_trigger BEFORE UPDATE ON public.profile_certifications FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: profile_education education_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER education_updated_at_trigger BEFORE UPDATE ON public.profile_education FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: interaction_events event_hash_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER event_hash_trigger BEFORE INSERT ON public.interaction_events FOR EACH ROW EXECUTE FUNCTION public.compute_event_hash();


--
-- Name: interactions interactions_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER interactions_updated_at_trigger BEFORE UPDATE ON public.interactions FOR EACH ROW EXECUTE FUNCTION public.update_interactions_updated_at();


--
-- Name: job_skills_staging job_skills_staging_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER job_skills_staging_updated_at_trigger BEFORE UPDATE ON public.job_skills_staging FOR EACH ROW EXECUTE FUNCTION public.update_staging_updated_at();


--
-- Name: profiles profile_search_vector_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profile_search_vector_trigger BEFORE INSERT OR UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profile_search_vector();


--
-- Name: profile_skills_staging profile_skills_staging_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profile_skills_staging_updated_at_trigger BEFORE UPDATE ON public.profile_skills_staging FOR EACH ROW EXECUTE FUNCTION public.update_staging_updated_at();


--
-- Name: profiles profiles_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER profiles_updated_at_trigger BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: actors set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.actors FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: conversation_dialogue set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.conversation_dialogue FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: conversations set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: conversations_history set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.conversations_history FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: instruction_steps set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.instruction_steps FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: instructions set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.instructions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: instructions_history set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.instructions_history FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: job_sources set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.job_sources FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organizations set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: placeholder_definitions set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.placeholder_definitions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: posting_skills set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.posting_skills FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: posting_sources set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.posting_sources FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: postings set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.postings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: test_cases set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.test_cases FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: user_preferences set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.user_preferences FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: workflow_variables set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.workflow_variables FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: workflows set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.workflows FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: workflows_history set_updated_at; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.workflows_history FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: skill_aliases_staging skill_aliases_staging_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER skill_aliases_staging_updated_at_trigger BEFORE UPDATE ON public.skill_aliases_staging FOR EACH ROW EXECUTE FUNCTION public.update_staging_updated_at();


--
-- Name: test_cases test_cases_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER test_cases_history_trigger BEFORE UPDATE ON public.test_cases FOR EACH ROW EXECUTE FUNCTION public.archive_test_cases();

ALTER TABLE public.test_cases DISABLE TRIGGER test_cases_history_trigger;


--
-- Name: company_ratings trg_update_company_rating; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_update_company_rating AFTER INSERT OR DELETE OR UPDATE ON public.company_ratings FOR EACH ROW EXECUTE FUNCTION public.update_company_avg_rating();


--
-- Name: posting_fetch_runs trg_update_source_stats; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_update_source_stats AFTER UPDATE ON public.posting_fetch_runs FOR EACH ROW WHEN (((old.status = 'RUNNING'::text) AND (new.status = ANY (ARRAY['SUCCESS'::text, 'PARTIAL_SUCCESS'::text, 'ERROR'::text])))) EXECUTE FUNCTION public.update_source_stats();


--
-- Name: actors trg_warn_missing_script_code; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_warn_missing_script_code BEFORE INSERT OR UPDATE ON public.actors FOR EACH ROW EXECUTE FUNCTION public.warn_missing_script_code();


--
-- Name: TRIGGER trg_warn_missing_script_code ON actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TRIGGER trg_warn_missing_script_code ON public.actors IS 'Warn when script actors have NULL script_code';


--
-- Name: workflow_runs trg_workflow_run_environment; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER trg_workflow_run_environment BEFORE INSERT ON public.workflow_runs FOR EACH ROW EXECUTE FUNCTION public.set_workflow_run_environment();


--
-- Name: profile_work_history work_history_duration_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_duration_trigger BEFORE INSERT OR UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.calculate_work_duration();


--
-- Name: profile_work_history work_history_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_updated_at_trigger BEFORE UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: workflow_conversations workflow_conversations_changed; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER workflow_conversations_changed AFTER INSERT OR DELETE OR UPDATE ON public.workflow_conversations FOR EACH ROW EXECUTE FUNCTION public.queue_workflow_docs();


--
-- Name: workflows workflows_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER workflows_history_trigger BEFORE UPDATE ON public.workflows FOR EACH ROW EXECUTE FUNCTION public.archive_workflows();


--
-- Name: actor_code_history actor_code_history_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_code_history
    ADD CONSTRAINT actor_code_history_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON DELETE CASCADE;


--
-- Name: actor_code_history actor_code_history_changed_by_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_code_history
    ADD CONSTRAINT actor_code_history_changed_by_actor_id_fkey FOREIGN KEY (changed_by_actor_id) REFERENCES public.actors(actor_id);


--
-- Name: actor_rate_control actor_rate_control_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actor_rate_control
    ADD CONSTRAINT actor_rate_control_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON DELETE CASCADE;


--
-- Name: actors actors_active_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_active_history_id_fkey FOREIGN KEY (active_history_id) REFERENCES public.actor_code_history(history_id) ON DELETE SET NULL;


--
-- Name: actors actors_parent_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_parent_actor_id_fkey FOREIGN KEY (parent_actor_id) REFERENCES public.actors(actor_id) ON DELETE SET NULL;


--
-- Name: actors actors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.actors
    ADD CONSTRAINT actors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: circuit_breaker_events circuit_breaker_events_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.circuit_breaker_events
    ADD CONSTRAINT circuit_breaker_events_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


--
-- Name: company_ratings company_ratings_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_ratings
    ADD CONSTRAINT company_ratings_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id) ON DELETE CASCADE;


--
-- Name: company_ratings company_ratings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.company_ratings
    ADD CONSTRAINT company_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


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
-- Name: conversation_tags conversation_tags_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.conversation_tags
    ADD CONSTRAINT conversation_tags_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE;


--
-- Name: conversations conversations_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: instruction_steps fk_instruction_steps_instruction_id; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT fk_instruction_steps_instruction_id FOREIGN KEY (instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE CASCADE;


--
-- Name: instruction_steps fk_instruction_steps_next_conversation_id; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT fk_instruction_steps_next_conversation_id FOREIGN KEY (next_conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE SET NULL;


--
-- Name: instruction_steps fk_instruction_steps_next_instruction_id; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_steps
    ADD CONSTRAINT fk_instruction_steps_next_instruction_id FOREIGN KEY (next_instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE SET NULL;


--
-- Name: posting_state_projection fk_posting_state_projection_posting; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_state_projection
    ADD CONSTRAINT fk_posting_state_projection_posting FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: posting_state_snapshots fk_posting_state_snapshots_posting; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.posting_state_snapshots
    ADD CONSTRAINT fk_posting_state_snapshots_posting FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


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
-- Name: interaction_events interaction_events_causation_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_events
    ADD CONSTRAINT interaction_events_causation_event_id_fkey FOREIGN KEY (causation_event_id) REFERENCES public.interaction_events(event_id) ON DELETE SET NULL;


--
-- Name: interaction_events interaction_events_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interaction_events
    ADD CONSTRAINT interaction_events_interaction_id_fkey FOREIGN KEY (interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE CASCADE;


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
-- Name: interactions interactions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON DELETE RESTRICT;


--
-- Name: interactions interactions_parent_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_parent_interaction_id_fkey FOREIGN KEY (parent_interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE SET NULL;


--
-- Name: interactions interactions_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE SET NULL;


--
-- Name: CONSTRAINT interactions_posting_id_fkey ON interactions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON CONSTRAINT interactions_posting_id_fkey ON public.interactions IS 'SET NULL on delete - interactions are audit records and must survive posting deletion';


--
-- Name: interactions interactions_trigger_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_trigger_interaction_id_fkey FOREIGN KEY (trigger_interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE SET NULL;


--
-- Name: interactions interactions_workflow_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.interactions
    ADD CONSTRAINT interactions_workflow_run_id_fkey FOREIGN KEY (workflow_run_id) REFERENCES public.workflow_runs(workflow_run_id) ON DELETE SET NULL;


--
-- Name: job_skills_staging job_skills_staging_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills_staging
    ADD CONSTRAINT job_skills_staging_interaction_id_fkey FOREIGN KEY (interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE CASCADE;


--
-- Name: job_skills_staging job_skills_staging_validated_by_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills_staging
    ADD CONSTRAINT job_skills_staging_validated_by_actor_id_fkey FOREIGN KEY (validated_by_actor_id) REFERENCES public.actors(actor_id);


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
-- Name: posting_fetch_runs posting_fetch_runs_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_fetch_runs
    ADD CONSTRAINT posting_fetch_runs_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.job_sources(source_id) ON DELETE CASCADE;


--
-- Name: posting_field_mappings posting_field_mappings_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_field_mappings
    ADD CONSTRAINT posting_field_mappings_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.posting_sources(source_id);


--
-- Name: posting_processing_status posting_processing_status_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_processing_status
    ADD CONSTRAINT posting_processing_status_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: posting_skills posting_skills_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_skills
    ADD CONSTRAINT posting_skills_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: posting_skills posting_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.posting_skills
    ADD CONSTRAINT posting_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id);


--
-- Name: postings postings_created_by_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_created_by_interaction_id_fkey FOREIGN KEY (created_by_interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE SET NULL;


--
-- Name: postings postings_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.posting_sources(source_id);


--
-- Name: postings postings_updated_by_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_updated_by_interaction_id_fkey FOREIGN KEY (updated_by_interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE SET NULL;


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
-- Name: profile_skills profile_skills_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills
    ADD CONSTRAINT profile_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skill_aliases(skill_id);


--
-- Name: profile_skills_staging profile_skills_staging_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills_staging
    ADD CONSTRAINT profile_skills_staging_interaction_id_fkey FOREIGN KEY (interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE CASCADE;


--
-- Name: profile_skills_staging profile_skills_staging_validated_by_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills_staging
    ADD CONSTRAINT profile_skills_staging_validated_by_actor_id_fkey FOREIGN KEY (validated_by_actor_id) REFERENCES public.actors(actor_id);


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
-- Name: qa_findings qa_findings_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.qa_findings
    ADD CONSTRAINT qa_findings_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: script_executions script_executions_script_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.script_executions
    ADD CONSTRAINT script_executions_script_id_fkey FOREIGN KEY (script_id) REFERENCES public.stored_scripts(script_id);


--
-- Name: skill_aliases_staging skill_aliases_staging_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases_staging
    ADD CONSTRAINT skill_aliases_staging_interaction_id_fkey FOREIGN KEY (interaction_id) REFERENCES public.interactions(interaction_id) ON DELETE CASCADE;


--
-- Name: skill_aliases_staging skill_aliases_staging_validated_by_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_aliases_staging
    ADD CONSTRAINT skill_aliases_staging_validated_by_actor_id_fkey FOREIGN KEY (validated_by_actor_id) REFERENCES public.actors(actor_id);


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
-- Name: user_company_verifications user_company_verifications_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_company_verifications
    ADD CONSTRAINT user_company_verifications_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id) ON DELETE CASCADE;


--
-- Name: user_company_verifications user_company_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_company_verifications
    ADD CONSTRAINT user_company_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


--
-- Name: user_feedback user_feedback_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE SET NULL;


--
-- Name: user_feedback user_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_feedback
    ADD CONSTRAINT user_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


--
-- Name: user_posting_decisions user_posting_decisions_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_posting_decisions
    ADD CONSTRAINT user_posting_decisions_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: user_posting_decisions user_posting_decisions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_posting_decisions
    ADD CONSTRAINT user_posting_decisions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_preferences(user_id);


--
-- Name: user_posting_preferences user_posting_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_posting_preferences
    ADD CONSTRAINT user_posting_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_profiles user_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_profiles
    ADD CONSTRAINT user_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


--
-- Name: user_reports user_reports_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_reports
    ADD CONSTRAINT user_reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


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
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


--
-- Name: user_verifications user_verifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.user_verifications
    ADD CONSTRAINT user_verifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(user_id) ON DELETE CASCADE;


--
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(organization_id);


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
-- Name: workflow_doc_queue workflow_doc_queue_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_doc_queue
    ADD CONSTRAINT workflow_doc_queue_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id) ON DELETE CASCADE;


--
-- Name: workflow_errors workflow_errors_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_errors
    ADD CONSTRAINT workflow_errors_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


--
-- Name: workflow_errors workflow_errors_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_errors
    ADD CONSTRAINT workflow_errors_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


--
-- Name: workflow_errors workflow_errors_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_errors
    ADD CONSTRAINT workflow_errors_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id);


--
-- Name: workflow_metrics workflow_metrics_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_metrics
    ADD CONSTRAINT workflow_metrics_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


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
-- Name: workflow_runs workflow_runs_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON DELETE CASCADE;


--
-- Name: workflow_runs workflow_runs_seed_interaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_seed_interaction_id_fkey FOREIGN KEY (seed_interaction_id) REFERENCES public.interactions(interaction_id);


--
-- Name: workflow_runs workflow_runs_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_runs
    ADD CONSTRAINT workflow_runs_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id) ON DELETE CASCADE;


--
-- Name: workflow_step_metrics workflow_step_metrics_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_step_metrics
    ADD CONSTRAINT workflow_step_metrics_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id);


--
-- Name: workflow_triggers workflow_triggers_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_triggers
    ADD CONSTRAINT workflow_triggers_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: workflow_variables workflow_variables_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.workflow_variables
    ADD CONSTRAINT workflow_variables_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflows(workflow_id);


--
-- Name: SCHEMA cron; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA cron TO base_admin;


--
-- Name: TABLE job; Type: ACL; Schema: cron; Owner: postgres
--

GRANT ALL ON TABLE cron.job TO base_admin;


--
-- Name: TABLE job_run_details; Type: ACL; Schema: cron; Owner: postgres
--

GRANT ALL ON TABLE cron.job_run_details TO base_admin;


--
-- Name: TABLE execution_events; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.execution_events TO base_admin;


--
-- Name: SEQUENCE execution_events_event_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.execution_events_event_id_seq TO base_admin;


--
-- Name: TABLE llm_performance_metrics; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.llm_performance_metrics TO base_admin;


--
-- Name: TABLE posting_state_projection; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.posting_state_projection TO base_admin;


--
-- Name: TABLE posting_state_snapshots; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.posting_state_snapshots TO base_admin;


--
-- Name: SEQUENCE posting_state_snapshots_snapshot_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.posting_state_snapshots_snapshot_id_seq TO base_admin;


--
-- Name: TABLE user_company_verifications; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_company_verifications TO base_admin;


--
-- Name: SEQUENCE user_posting_decisions_decision_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,USAGE ON SEQUENCE public.user_posting_decisions_decision_id_seq TO base_admin;


--
-- PostgreSQL database dump complete
--

\unrestrict cpAXh3N7ypFw3AN0QRAsN4ttmAGMrAKtPGNjUgemsQ10gLIDgsQegG78SZ01fYk

