--
-- PostgreSQL database dump
--

\restrict pebSqSWD7HeH9o9IR29Kh3Mo5Ym8KDK87xANrKjLrmVRP5ZqCAI5srctW4MRqXz

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
-- Name: archive_canonicals(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_canonicals() RETURNS trigger
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


ALTER FUNCTION public.archive_canonicals() OWNER TO base_admin;

--
-- Name: archive_facets(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_facets() RETURNS trigger
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


ALTER FUNCTION public.archive_facets() OWNER TO base_admin;

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
-- Name: archive_recipes(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_recipes() RETURNS trigger
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


ALTER FUNCTION public.archive_recipes() OWNER TO base_admin;

--
-- Name: archive_sessions(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_sessions() RETURNS trigger
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


ALTER FUNCTION public.archive_sessions() OWNER TO base_admin;

--
-- Name: FUNCTION archive_sessions(); Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON FUNCTION public.archive_sessions() IS 'Updated 2025-10-30: Uses canonical_name from sessions (renamed from canonical_code)';


--
-- Name: archive_variations(); Type: FUNCTION; Schema: public; Owner: base_admin
--

CREATE FUNCTION public.archive_variations() RETURNS trigger
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


ALTER FUNCTION public.archive_variations() OWNER TO base_admin;

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
    actor_name text NOT NULL,
    actor_type text NOT NULL,
    url text NOT NULL,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    execution_type text,
    execution_path text,
    execution_config jsonb DEFAULT '{}'::jsonb,
    actor_id integer DEFAULT nextval('public.actors_actor_id_seq'::regclass) NOT NULL,
    CONSTRAINT actors_actor_type_check CHECK ((actor_type = ANY (ARRAY['human'::text, 'ai_model'::text, 'script'::text, 'machine_actor'::text]))),
    CONSTRAINT actors_execution_type_check CHECK ((execution_type = ANY (ARRAY['ollama_api'::text, 'http_api'::text, 'python_script'::text, 'bash_script'::text, 'human_input'::text])))
);


ALTER TABLE public.actors OWNER TO base_admin;

--
-- Name: TABLE actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.actors IS 'Execution agents: LLMs, scripts, humans (47 entries). Standardized 2025-10-30.
Pattern: actor_id (INTEGER PK) + actor_name (TEXT UNIQUE).
Types: ollama_api, python_script, bash_script, http_api.';


--
-- Name: COLUMN actors.actor_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_name IS 'Natural key - unique actor name (e.g., qwen2.5:7b, taxonomy_gopher)';


--
-- Name: COLUMN actors.actor_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_type IS 'Type of actor: human (human operator), ai_model (LLM), script (automated validator)';


--
-- Name: COLUMN actors.url; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.url IS 'Connection string. AI models: ollama://model:tag, Humans: mailto:email or cli://username, Scripts: file:///path';


--
-- Name: COLUMN actors.enabled; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.enabled IS 'Whether this actor is currently available for execution. 
   If false, recipes using this actor will fail gracefully.';


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
-- Name: COLUMN actors.execution_path; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.execution_path IS 'WHERE to execute:
   - ollama_api: model name (e.g., "phi3:latest")
   - http_api: full endpoint URL (e.g., "http://localhost:5000/api/explore")
   - python_script: absolute file path (e.g., "/path/to/script.py")
   - bash_script: absolute file path
   - human_input: NULL (not applicable)';


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
-- Name: COLUMN actors.actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.actors.actor_id IS 'Surrogate key - stable integer identifier for joins';


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
-- Name: canonicals_canonical_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.canonicals_canonical_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.canonicals_canonical_id_seq OWNER TO base_admin;

--
-- Name: canonicals; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.canonicals (
    canonical_name text NOT NULL,
    facet_name text NOT NULL,
    capability_description text,
    prompt text,
    response text NOT NULL,
    review_notes text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    canonical_id integer DEFAULT nextval('public.canonicals_canonical_id_seq'::regclass) NOT NULL,
    facet_id integer NOT NULL
);


ALTER TABLE public.canonicals OWNER TO base_admin;

--
-- Name: TABLE canonicals; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.canonicals IS 'Canonical skill/capability definitions (62 entries). Standardized 2025-10-30.
Pattern: canonical_id (INTEGER PK) + canonical_name (TEXT UNIQUE).';


--
-- Name: COLUMN canonicals.canonical_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.canonicals.canonical_name IS 'Natural key - unique canonical code (e.g., PYTHON_PROGRAMMING)';


--
-- Name: COLUMN canonicals.prompt; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.canonicals.prompt IS 'Master prompt template (optional - may be defined at session/instruction level)';


--
-- Name: COLUMN canonicals.response; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.canonicals.response IS 'Expected correct response for validation';


--
-- Name: canonicals_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.canonicals_history (
    history_id integer NOT NULL,
    canonical_code text NOT NULL,
    facet_id text NOT NULL,
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


ALTER TABLE public.canonicals_history OWNER TO base_admin;

--
-- Name: TABLE canonicals_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.canonicals_history IS 'Audit trail of all changes to canonicals table. Triggered automatically on UPDATE/DELETE via archive_canonicals() function. Preserves old values before modification.';


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

ALTER SEQUENCE public.canonicals_history_history_id_seq OWNED BY public.canonicals_history.history_id;


--
-- Name: facets_facet_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.facets_facet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.facets_facet_id_seq OWNER TO base_admin;

--
-- Name: facets; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.facets (
    facet_name text NOT NULL,
    parent_facet_name text,
    short_description text,
    remarks text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    facet_id integer DEFAULT nextval('public.facets_facet_id_seq'::regclass) NOT NULL,
    parent_id integer
);


ALTER TABLE public.facets OWNER TO base_admin;

--
-- Name: TABLE facets; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.facets IS 'Hierarchical facet taxonomy (74 entries). Standardized 2025-10-30.
Pattern: facet_id (INTEGER PK) + facet_name (TEXT UNIQUE).
Self-referencing: parent_id → facet_id.';


--
-- Name: COLUMN facets.facet_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.facet_name IS 'Natural key - unique facet name (e.g., TECHNICAL_SKILLS)';


--
-- Name: COLUMN facets.parent_facet_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.parent_facet_name IS 'Parent facet for hierarchical organization (NULL for root facets)';


--
-- Name: COLUMN facets.facet_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.facet_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: COLUMN facets.parent_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.parent_id IS 'Self-referencing FK to parent facet (NULL for root facets)';


--
-- Name: facets_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.facets_history (
    history_id integer NOT NULL,
    facet_id text NOT NULL,
    parent_id text,
    short_description text,
    remarks text,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.facets_history OWNER TO base_admin;

--
-- Name: TABLE facets_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.facets_history IS 'Audit trail of all changes to facets table. Triggered automatically on UPDATE/DELETE via archive_facets() function. Preserves old values before modification.';


--
-- Name: facets_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.facets_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.facets_history_history_id_seq OWNER TO base_admin;

--
-- Name: facets_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.facets_history_history_id_seq OWNED BY public.facets_history.history_id;


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
-- Name: instruction_branch_executions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instruction_branch_executions (
    execution_id integer NOT NULL,
    instruction_run_id integer NOT NULL,
    branch_id integer NOT NULL,
    condition_matched text NOT NULL,
    iteration_count integer DEFAULT 1,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.instruction_branch_executions OWNER TO base_admin;

--
-- Name: TABLE instruction_branch_executions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instruction_branch_executions IS 'Audit log of branch decisions. Records which branch was taken, what output pattern matched, and iteration count for loop tracking.';


--
-- Name: COLUMN instruction_branch_executions.condition_matched; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branch_executions.condition_matched IS 'The actual output text that matched the branch_condition regex. Useful for debugging pattern matching.';


--
-- Name: COLUMN instruction_branch_executions.iteration_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branch_executions.iteration_count IS 'How many times this specific branch has been taken in the current session_run. Used to enforce max_iterations limit.';


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

ALTER SEQUENCE public.instruction_branch_executions_execution_id_seq OWNED BY public.instruction_branch_executions.execution_id;


--
-- Name: instruction_branches; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instruction_branches (
    branch_id integer NOT NULL,
    instruction_id integer NOT NULL,
    branch_condition text NOT NULL,
    next_instruction_id integer,
    next_session_id integer,
    max_iterations integer,
    branch_priority integer DEFAULT 5,
    branch_description text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_branch_target CHECK ((((next_instruction_id IS NOT NULL) AND (next_session_id IS NULL)) OR ((next_instruction_id IS NULL) AND (next_session_id IS NOT NULL)) OR ((next_instruction_id IS NULL) AND (next_session_id IS NULL)))),
    CONSTRAINT chk_positive_iterations CHECK (((max_iterations IS NULL) OR (max_iterations > 0)))
);


ALTER TABLE public.instruction_branches OWNER TO base_admin;

--
-- Name: TABLE instruction_branches; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instruction_branches IS 'Conditional branching logic for instructions. Enables Turing-complete workflows with loops, conditionals, and state transitions. Evaluation order: priority DESC → first matching condition wins.';


--
-- Name: COLUMN instruction_branches.instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.instruction_id IS 'Source instruction. After this instruction executes, evaluate its branches.';


--
-- Name: COLUMN instruction_branches.branch_condition; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.branch_condition IS 'Regex pattern to match against instruction output. Use "^\\[PASS\\]" for exact prefix match, ".*error.*" for substring, or "*" for catch-all. Evaluated in priority order.';


--
-- Name: COLUMN instruction_branches.next_instruction_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.next_instruction_id IS 'Target instruction to execute if condition matches (same session). NULL with NULL next_session_id = end session.';


--
-- Name: COLUMN instruction_branches.next_session_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.next_session_id IS 'Target session to jump to if condition matches (cross-session jump). Mutually exclusive with next_instruction_id.';


--
-- Name: COLUMN instruction_branches.max_iterations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.max_iterations IS 'Maximum times this branch can be taken within a single session_run (loop guard). NULL = unlimited. Prevents infinite loops in retry logic.';


--
-- Name: COLUMN instruction_branches.branch_priority; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.branch_priority IS 'Evaluation order (DESC). Higher priority = evaluated first. Use: 10=exact match, 5=common patterns (PASS/FAIL), 1=loose patterns, 0=catch-all (*). Default: 5.';


--
-- Name: COLUMN instruction_branches.branch_description; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_branches.branch_description IS 'Human-readable explanation of what this branch does. Example: "If grading passes, skip to format session" or "If failed 3 times, create error ticket".';


--
-- Name: instruction_branches_branch_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.instruction_branches_branch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instruction_branches_branch_id_seq OWNER TO base_admin;

--
-- Name: instruction_branches_branch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.instruction_branches_branch_id_seq OWNED BY public.instruction_branches.branch_id;


--
-- Name: instruction_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instruction_runs (
    instruction_run_id integer NOT NULL,
    session_run_id integer NOT NULL,
    instruction_id integer NOT NULL,
    step_number integer NOT NULL,
    prompt_rendered text,
    response_received text,
    latency_ms integer,
    error_details text,
    status text DEFAULT 'PENDING'::text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT instruction_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'TIMEOUT'::text, 'ERROR'::text])))
);


ALTER TABLE public.instruction_runs OWNER TO base_admin;

--
-- Name: TABLE instruction_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instruction_runs IS 'Individual instruction execution results. SHARED by both testing and production. Tracks what was sent, what was received, and performance metrics.';


--
-- Name: COLUMN instruction_runs.prompt_rendered; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_runs.prompt_rendered IS 'Actual prompt sent to actor after variable substitution. In test mode uses variation.test_data, in production uses posting fields.';


--
-- Name: COLUMN instruction_runs.latency_ms; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instruction_runs.latency_ms IS 'Response time in milliseconds. Critical for performance comparison between test and production.';


--
-- Name: instruction_runs_instruction_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.instruction_runs_instruction_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instruction_runs_instruction_run_id_seq OWNER TO base_admin;

--
-- Name: instruction_runs_instruction_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.instruction_runs_instruction_run_id_seq OWNED BY public.instruction_runs.instruction_run_id;


--
-- Name: instructions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.instructions (
    instruction_id integer NOT NULL,
    session_id integer NOT NULL,
    step_number integer NOT NULL,
    step_description text,
    prompt_template text NOT NULL,
    timeout_seconds integer DEFAULT 300,
    expected_pattern text,
    validation_rules text,
    is_terminal boolean DEFAULT false,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    delegate_actor_name text,
    delegate_actor_id integer
);


ALTER TABLE public.instructions OWNER TO base_admin;

--
-- Name: TABLE instructions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instructions IS 'Step-by-step prompts within a session. Instructions execute sequentially unless branching logic redirects.';


--
-- Name: COLUMN instructions.prompt_template; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.prompt_template IS 'Prompt template with dynamic variable substitution.

Supported Placeholders:
  {variations_param_1}   - Input data from test variations
  {job_description}      - For production: posting.raw_job_description  
  {profile_text}         - For production: profiles.profile_raw_text
  {session_N_output}     - Output from session N (e.g., {session_1_output})
  {taxonomy}             - Dynamic taxonomy from skill_hierarchy table
  
Fallback Syntax:
  {session_4_output?session_1_output} - Use session 4 if available, else session 1
  
Context Availability:
- Session outputs accumulate across instructions
- Both primary and delegated actors receive same context
- Enables chaining: extract → validate → improve → format

Example:
  Session 1, Instruction 1: "Extract skills from {job_description}"
    → Output: ["Python", "SQL"]
  
  Session 1, Instruction 2: "Map these to taxonomy: {session_1_output}"
    → Receives: ["Python", "SQL"]
    → Output: ["PYTHON", "SQL"]';


--
-- Name: COLUMN instructions.is_terminal; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.is_terminal IS 'If TRUE, this instruction ends the session (no next step)';


--
-- Name: COLUMN instructions.delegate_actor_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.delegate_actor_name IS 'Optional: Override session primary actor for THIS INSTRUCTION ONLY.

🎯 Use Cases:
- Query skill_gopher for taxonomy navigation
- Execute SQL scripts for data operations  
- Run validators for quality checks
- Call Python scripts for transformations

⚙️ Execution Logic:
  IF delegate_actor_id IS NOT NULL:
      Execute with delegated actor
  ELSE:
      Execute with session.actor_id (primary)

📋 Context Inheritance:
- Delegated helper receives same session context
- Helper output added to session_outputs
- Primary actor can reference helper output in next instruction
- Example: {session_2_output} works whether session 2 used helper or not

💡 Example:
  session.actor_id = "qwen2.5:7b"            (primary actor)
  instruction.delegate_actor_id = "skill_gopher" (helper for one instruction)
  
  → Instruction executed by skill_gopher
  → Output stored in session_outputs  
  → Next instruction (primary actor) can use: {session_2_output}

🔄 Pattern:
  Instruction 1: Primary actor extracts data
  Instruction 2: Helper actor (delegate) processes/validates  ← Uses delegate_actor_id
  Instruction 3: Primary actor formats result (has access to both outputs)';


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
    change_reason text
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

CREATE SEQUENCE public.instructions_instruction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instructions_instruction_id_seq OWNER TO base_admin;

--
-- Name: instructions_instruction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.instructions_instruction_id_seq OWNED BY public.instructions.instruction_id;


--
-- Name: job_nodes; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_nodes (
    node_id integer NOT NULL,
    skill_name text NOT NULL,
    category text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.job_nodes OWNER TO base_admin;

--
-- Name: TABLE job_nodes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_nodes IS 'Skill graph nodes. Each node represents a skill extracted from job postings.';


--
-- Name: job_nodes_node_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.job_nodes_node_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_nodes_node_id_seq OWNER TO base_admin;

--
-- Name: job_nodes_node_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.job_nodes_node_id_seq OWNED BY public.job_nodes.node_id;


--
-- Name: job_skill_edges; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_skill_edges (
    edge_id integer NOT NULL,
    source_node_id integer NOT NULL,
    target_node_id integer NOT NULL,
    weight integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.job_skill_edges OWNER TO base_admin;

--
-- Name: TABLE job_skill_edges; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_skill_edges IS 'Skill co-occurrence relationships. Weight = how many jobs require both skills together.';


--
-- Name: job_skill_edges_edge_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.job_skill_edges_edge_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_skill_edges_edge_id_seq OWNER TO base_admin;

--
-- Name: job_skill_edges_edge_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.job_skill_edges_edge_id_seq OWNED BY public.job_skill_edges.edge_id;


--
-- Name: job_skills; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.job_skills (
    job_skill_id integer NOT NULL,
    posting_name text NOT NULL,
    skill_id integer NOT NULL,
    required boolean DEFAULT true,
    min_years_experience integer,
    mentioned_count integer DEFAULT 1,
    context_snippet text,
    extracted_by text,
    recipe_run_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    source_language text,
    original_term text,
    posting_id integer NOT NULL
);


ALTER TABLE public.job_skills OWNER TO base_admin;

--
-- Name: TABLE job_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.job_skills IS 'Skills required by job postings, extracted via Recipe 1120 and normalized to canonical taxonomy. Links postings → skills for matching.';


--
-- Name: COLUMN job_skills.mentioned_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_skills.mentioned_count IS 'Frequency tracking. "Python" mentioned 5 times = higher importance than skill mentioned once.';


--
-- Name: COLUMN job_skills.source_language; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_skills.source_language IS 'Language detected in original posting: en, de, fr, zh, ja, etc.';


--
-- Name: COLUMN job_skills.original_term; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.job_skills.original_term IS 'Original skill term before translation to canonical English. 
Example: "Python-Programmierung" (German) → canonical_skill_id points to "Python" (English)';


--
-- Name: job_skills_job_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.job_skills_job_skill_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_skills_job_skill_id_seq OWNER TO base_admin;

--
-- Name: job_skills_job_skill_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.job_skills_job_skill_id_seq OWNED BY public.job_skills.job_skill_id;


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
    posting_name text NOT NULL,
    metadata_source text,
    metadata_created_at timestamp without time zone,
    metadata_last_modified timestamp without time zone,
    metadata_status text,
    metadata_processor text,
    job_title text,
    job_description text,
    job_requirements jsonb,
    location_city text,
    location_state text,
    location_country text,
    location_remote_options boolean,
    employment_type text,
    employment_schedule text,
    employment_career_level text,
    employment_salary_range text,
    employment_benefits jsonb,
    organization_name text,
    organization_division text,
    organization_division_id integer,
    posting_publication_date date,
    posting_position_uri text,
    posting_hiring_year text,
    imported_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    enabled boolean DEFAULT true,
    skill_keywords jsonb,
    complexity_score real,
    processing_notes text,
    extracted_summary text,
    summary_extracted_at timestamp without time zone,
    summary_extraction_status text DEFAULT 'pending'::text,
    is_test_posting boolean DEFAULT false,
    posting_id integer DEFAULT nextval('public.postings_posting_id_seq'::regclass) NOT NULL
);


ALTER TABLE public.postings OWNER TO base_admin;

--
-- Name: TABLE postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.postings IS 'Job postings (76 entries). Standardized 2025-10-30.
Pattern: posting_id (INTEGER PK) + posting_name (TEXT, not unique).
Note: posting_name can have duplicates (e.g., test data like TEST_ORACLE_DBA_001).';


--
-- Name: COLUMN postings.posting_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_name IS 'Job identifier from source system (can be duplicate for test data)';


--
-- Name: COLUMN postings.metadata_source; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.metadata_source IS 'Data source: deutsche_bank, arbeitsagentur, company_website, etc.';


--
-- Name: COLUMN postings.job_requirements; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.job_requirements IS 'JSONB array of requirements. Structured for analysis.';


--
-- Name: COLUMN postings.skill_keywords; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.skill_keywords IS 'Extracted skills for matching. Computed field populated by analysis recipes.';


--
-- Name: COLUMN postings.posting_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.posting_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: production_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.production_runs (
    production_run_id integer NOT NULL,
    recipe_id integer NOT NULL,
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
    posting_id integer NOT NULL
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
    years_experience double precision,
    proficiency_level text,
    is_implicit boolean DEFAULT false,
    derivation_reason text,
    last_used_date date,
    evidence_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.profile_skills OWNER TO base_admin;

--
-- Name: TABLE profile_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profile_skills IS 'Candidate/CV skills parsed and normalized to canonical taxonomy. Includes explicit skills (stated) and implicit skills (derived).';


--
-- Name: COLUMN profile_skills.is_implicit; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_skills.is_implicit IS 'TRUE = derived via inference rules. Examples: (1) Hierarchical: has "Kubernetes" → implies "Container Orchestration". (2) Common sense: "Traveling Salesman" → implies "Driver''s License".';


--
-- Name: COLUMN profile_skills.derivation_reason; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profile_skills.derivation_reason IS 'Audit trail for implicit skills. LLM explanation or rule name that generated this inference.';


--
-- Name: profile_skills_profile_skill_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.profile_skills_profile_skill_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_skills_profile_skill_id_seq OWNER TO base_admin;

--
-- Name: profile_skills_profile_skill_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.profile_skills_profile_skill_id_seq OWNED BY public.profile_skills.profile_skill_id;


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
    email text,
    phone text,
    location text,
    linkedin_url text,
    profile_source text,
    profile_raw_text text,
    profile_summary text,
    skill_keywords jsonb,
    skills_extraction_status text DEFAULT 'pending'::text,
    experience_level text,
    years_of_experience integer,
    current_title text,
    desired_roles text[],
    desired_locations text[],
    availability_status text,
    expected_salary_min integer,
    expected_salary_max integer,
    currency text DEFAULT 'CHF'::text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_activity_date timestamp without time zone,
    search_vector tsvector,
    is_test_profile boolean DEFAULT false
);


ALTER TABLE public.profiles OWNER TO base_admin;

--
-- Name: TABLE profiles; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profiles IS 'Candidate profiles with skills mapped to job taxonomy';


--
-- Name: COLUMN profiles.profile_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.profile_summary IS 'LLM-extracted professional summary (parallel to postings.extracted_summary)';


--
-- Name: COLUMN profiles.skill_keywords; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.skill_keywords IS 'Array of taxonomy-matched skills (same format as postings.skill_keywords)';


--
-- Name: COLUMN profiles.experience_level; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.experience_level IS 'Classification: entry/junior/mid/senior/lead/executive';


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
-- Name: recipe_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.recipe_runs (
    recipe_run_id integer NOT NULL,
    recipe_id integer NOT NULL,
    variation_id integer NOT NULL,
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
    CONSTRAINT recipe_runs_batch_number_check CHECK ((batch_number > 0)),
    CONSTRAINT recipe_runs_completed_sessions_check CHECK ((completed_sessions >= 0)),
    CONSTRAINT recipe_runs_execution_mode_check CHECK ((execution_mode = ANY (ARRAY['testing'::text, 'production'::text]))),
    CONSTRAINT recipe_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'PARTIAL'::text, 'ERROR'::text]))),
    CONSTRAINT recipe_runs_target_batch_count_check CHECK ((target_batch_count > 0)),
    CONSTRAINT recipe_runs_total_sessions_check CHECK ((total_sessions > 0))
);


ALTER TABLE public.recipe_runs OWNER TO base_admin;

--
-- Name: TABLE recipe_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.recipe_runs IS 'Test execution instances. Links recipe + variation + batch. Used in TESTING mode with synthetic variations.';


--
-- Name: COLUMN recipe_runs.output_data; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_runs.output_data IS 'Final output from recipe execution (e.g., concise job description from Recipe 1114)';


--
-- Name: COLUMN recipe_runs.execution_mode; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_runs.execution_mode IS 'Execution mode: "testing" (5 batches for validation) or "production" (1 batch for real data)';


--
-- Name: COLUMN recipe_runs.target_batch_count; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_runs.target_batch_count IS 'How many batch runs should be completed for this variation (5 for testing, 1 for production)';


--
-- Name: COLUMN recipe_runs.batch_number; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_runs.batch_number IS 'Which batch iteration this is (1-N where N = target_batch_count)';


--
-- Name: recipe_runs_recipe_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.recipe_runs_recipe_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recipe_runs_recipe_run_id_seq OWNER TO base_admin;

--
-- Name: recipe_runs_recipe_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.recipe_runs_recipe_run_id_seq OWNED BY public.recipe_runs.recipe_run_id;


--
-- Name: recipe_sessions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.recipe_sessions (
    recipe_session_id integer NOT NULL,
    recipe_id integer NOT NULL,
    session_id integer NOT NULL,
    execution_order integer NOT NULL,
    execute_condition text DEFAULT 'always'::text,
    depends_on_recipe_session_id integer,
    on_success_action text DEFAULT 'continue'::text,
    on_failure_action text DEFAULT 'stop'::text,
    on_success_goto_order integer,
    on_failure_goto_order integer,
    max_retry_attempts integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT recipe_sessions_execute_condition_check CHECK ((execute_condition = ANY (ARRAY['always'::text, 'on_success'::text, 'on_failure'::text]))),
    CONSTRAINT recipe_sessions_on_failure_action_check CHECK ((on_failure_action = ANY (ARRAY['stop'::text, 'retry'::text, 'skip_to'::text]))),
    CONSTRAINT recipe_sessions_on_success_action_check CHECK ((on_success_action = ANY (ARRAY['continue'::text, 'skip_to'::text, 'stop'::text])))
);


ALTER TABLE public.recipe_sessions OWNER TO base_admin;

--
-- Name: TABLE recipe_sessions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.recipe_sessions IS 'Junction table defining which sessions belong to which recipes and in what order. Enables session reuse across recipes. One session can be used in many recipes!';


--
-- Name: COLUMN recipe_sessions.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_sessions.execution_order IS 'Sequence number for this session within the recipe (1, 2, 3...). Defines execution order.';


--
-- Name: COLUMN recipe_sessions.execute_condition; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_sessions.execute_condition IS 'When to execute: always (default), on_success (previous succeeded), on_failure (previous failed)';


--
-- Name: COLUMN recipe_sessions.on_success_action; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_sessions.on_success_action IS 'What to do after success: continue (next session), skip_to (jump), stop (end recipe)';


--
-- Name: COLUMN recipe_sessions.on_failure_action; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_sessions.on_failure_action IS 'What to do after failure: stop (end), retry (run again), skip_to (jump to error handler)';


--
-- Name: COLUMN recipe_sessions.max_retry_attempts; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipe_sessions.max_retry_attempts IS 'Maximum times this session can be retried in this recipe (prevents infinite retry loops)';


--
-- Name: recipe_sessions_recipe_session_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.recipe_sessions_recipe_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recipe_sessions_recipe_session_id_seq OWNER TO base_admin;

--
-- Name: recipe_sessions_recipe_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.recipe_sessions_recipe_session_id_seq OWNED BY public.recipe_sessions.recipe_session_id;


--
-- Name: recipes; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.recipes (
    recipe_id integer NOT NULL,
    recipe_name text NOT NULL,
    recipe_description text,
    recipe_version integer DEFAULT 1,
    max_total_session_runs integer DEFAULT 100,
    enabled boolean DEFAULT true,
    review_notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    documentation text
);


ALTER TABLE public.recipes OWNER TO base_admin;

--
-- Name: TABLE recipes; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.recipes IS 'Multi-phase workflows orchestrating multiple sessions. Like a restaurant menu combining multiple courses (canonicals). Tested with variations, deployed with postings.';


--
-- Name: COLUMN recipes.recipe_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipes.recipe_name IS 'Human-readable name (e.g., "Job Quality Pipeline", "Skill Extraction Workflow")';


--
-- Name: COLUMN recipes.max_total_session_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipes.max_total_session_runs IS 'Maximum total session executions allowed across all recipe sessions (prevents infinite recipe loops). Recipe-level budget.';


--
-- Name: COLUMN recipes.documentation; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.recipes.documentation IS 'Comprehensive recipe documentation in Markdown format. Includes architecture, sessions, performance metrics, troubleshooting, and usage examples.';


--
-- Name: recipes_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.recipes_history (
    history_id integer NOT NULL,
    recipe_id integer NOT NULL,
    recipe_name text,
    recipe_description text,
    recipe_version integer,
    max_total_session_runs integer,
    enabled boolean,
    review_notes text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.recipes_history OWNER TO base_admin;

--
-- Name: TABLE recipes_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.recipes_history IS 'Audit trail of all changes to recipes table. Tracks recipe modifications over time, enabling "what changed when I broke it?" debugging.';


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

ALTER SEQUENCE public.recipes_history_history_id_seq OWNED BY public.recipes_history.history_id;


--
-- Name: recipes_recipe_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.recipes_recipe_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.recipes_recipe_id_seq OWNER TO base_admin;

--
-- Name: recipes_recipe_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.recipes_recipe_id_seq OWNED BY public.recipes.recipe_id;


--
-- Name: schema_documentation_documentation_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.schema_documentation_documentation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.schema_documentation_documentation_id_seq OWNER TO base_admin;

--
-- Name: schema_documentation; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.schema_documentation (
    table_name text NOT NULL,
    column_name text NOT NULL,
    data_type text,
    description text NOT NULL,
    example_value text,
    constraints text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    documentation_id integer DEFAULT nextval('public.schema_documentation_documentation_id_seq'::regclass) NOT NULL
);


ALTER TABLE public.schema_documentation OWNER TO base_admin;

--
-- Name: TABLE schema_documentation; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.schema_documentation IS 'Schema metadata and documentation (4 entries). Standardized 2025-10-30.
Pattern: documentation_id (INTEGER PK) + (table_name, column_name) UNIQUE composite key.';


--
-- Name: COLUMN schema_documentation.documentation_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.schema_documentation.documentation_id IS 'Surrogate key - stable integer identifier';


--
-- Name: session_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.session_runs (
    session_run_id integer NOT NULL,
    session_id integer NOT NULL,
    recipe_session_id integer NOT NULL,
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
    CONSTRAINT session_runs_quality_score_check CHECK ((quality_score = ANY (ARRAY['A'::text, 'B'::text, 'C'::text, 'D'::text, 'F'::text, NULL::text]))),
    CONSTRAINT session_runs_run_type_check CHECK ((run_type = ANY (ARRAY['testing'::text, 'production'::text]))),
    CONSTRAINT session_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'TIMEOUT'::text, 'ERROR'::text]))),
    CONSTRAINT session_runs_validation_status_check CHECK ((validation_status = ANY (ARRAY['PASS'::text, 'FAIL'::text, NULL::text])))
);


ALTER TABLE public.session_runs OWNER TO base_admin;

--
-- Name: TABLE session_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.session_runs IS 'Execution instances of sessions. Tracks which sessions ran in which order.

Session Context:
- Each session_run maintains output history for all its instructions
- Primary actor has access to ALL previous instruction outputs
- Helpers (via delegate_actor_id) also receive session context
- Enables multi-step reasoning chains and data transformation pipelines

Execution Flow:
  recipe_run → session_runs (ordered) → instruction_runs (sequential)
  
Run Type:
- run_type=''testing'': Uses recipe_runs (synthetic test data)
- run_type=''production'': Uses production_runs (real job postings)';


--
-- Name: COLUMN session_runs.execution_order; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.execution_order IS 'Sequence number matching recipe_sessions.execution_order.
Indicates which position this session occupies in recipe execution flow.

⚠️ Naming Convention: Always use ''execution_order'' consistently
- recipe_sessions.execution_order (definition)
- session_runs.execution_order (tracking)

This replaced the old ''session_number'' column for semantic clarity.';


--
-- Name: COLUMN session_runs.completed_at; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.completed_at IS 'Timestamp when session execution finished (success or failure).

⚠️ Naming Convention: Always use ''completed_at'' (not ''ended_at'')
This is the standard across all execution tracking tables:
- recipe_runs.completed_at
- production_runs.completed_at
- session_runs.completed_at';


--
-- Name: COLUMN session_runs.quality_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.quality_score IS 'Academic grading: A (excellent), B (good), C (acceptable), D (poor), F (failed)';


--
-- Name: COLUMN session_runs.validation_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.validation_status IS 'Pass/fail validation: PASS (met requirements), FAIL (did not meet requirements)';


--
-- Name: COLUMN session_runs.error_details; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.error_details IS 'Error message if session failed. NULL if successful.

⚠️ Naming Convention: Always use ''error_details'' (not ''error_message'')
This is the standard across all execution tracking tables:
- recipe_runs.error_details
- production_runs.error_details  
- session_runs.error_details
- instruction_runs.error_details';


--
-- Name: COLUMN session_runs.run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.run_id IS 'Unified run identifier. Replaces old recipe_run_id/production_run_id split.

References:
- recipe_runs.recipe_run_id (when run_type=''testing'')
- production_runs.production_run_id (when run_type=''production'')

Migration Note: This column consolidates what were previously two mutually
exclusive foreign keys into a single, cleaner design.';


--
-- Name: COLUMN session_runs.run_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.run_type IS 'Execution mode: ''testing'' or ''production''.

- testing: Uses synthetic test variations (recipe_runs)
- production: Uses real job postings (production_runs)

Determines which parent table run_id references.';


--
-- Name: session_runs_production; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.session_runs_production AS
 SELECT sr.session_run_id,
    sr.run_id,
    sr.session_id,
    sr.recipe_session_id,
    sr.execution_order,
    sr.started_at,
    sr.completed_at,
    sr.status,
    sr.error_details,
    pr.recipe_id,
    pr.posting_name AS posting_id
   FROM (public.session_runs sr
     JOIN public.production_runs pr ON ((sr.run_id = pr.production_run_id)))
  WHERE (sr.run_type = 'production'::text);


ALTER TABLE public.session_runs_production OWNER TO base_admin;

--
-- Name: VIEW session_runs_production; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.session_runs_production IS 'Session runs in production mode with production_runs context.
   Simplified query access without needing run_type filter.';


--
-- Name: session_runs_session_run_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.session_runs_session_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.session_runs_session_run_id_seq OWNER TO base_admin;

--
-- Name: session_runs_session_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.session_runs_session_run_id_seq OWNED BY public.session_runs.session_run_id;


--
-- Name: session_runs_testing; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.session_runs_testing AS
 SELECT sr.session_run_id,
    sr.run_id,
    sr.session_id,
    sr.recipe_session_id,
    sr.execution_order,
    sr.started_at,
    sr.completed_at,
    sr.status,
    sr.error_details,
    rr.recipe_id,
    rr.variation_id,
    rr.batch_id
   FROM (public.session_runs sr
     JOIN public.recipe_runs rr ON ((sr.run_id = rr.recipe_run_id)))
  WHERE (sr.run_type = 'testing'::text);


ALTER TABLE public.session_runs_testing OWNER TO base_admin;

--
-- Name: VIEW session_runs_testing; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.session_runs_testing IS 'Session runs in testing mode with recipe_runs context.
   Simplified query access without needing run_type filter.';


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.sessions (
    session_id integer NOT NULL,
    canonical_name text NOT NULL,
    session_name text NOT NULL,
    session_description text,
    actor_name text NOT NULL,
    context_strategy text DEFAULT 'isolated'::text,
    max_instruction_runs integer DEFAULT 50,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    canonical_id integer,
    actor_id integer NOT NULL,
    CONSTRAINT sessions_context_strategy_check CHECK ((context_strategy = ANY (ARRAY['isolated'::text, 'inherit_previous'::text, 'shared_conversation'::text])))
);


ALTER TABLE public.sessions OWNER TO base_admin;

--
-- Name: TABLE sessions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.sessions IS 'Complete interaction templates that execute one canonical capability. Reusable across multiple recipes. Session = atomic testable unit.';


--
-- Name: COLUMN sessions.canonical_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.canonical_name IS 'Which canonical capability does this session implement? Links session to facet taxonomy.';


--
-- Name: COLUMN sessions.actor_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.actor_name IS 'Primary actor for all instructions in this session (unless overridden by delegate_actor_id).

This actor maintains session context and has access to all previous instruction outputs.
Individual instructions can delegate to helpers via instructions.delegate_actor_id,
but control returns to primary actor for subsequent instructions.

See instructions.delegate_actor_id for helper/delegate pattern details.';


--
-- Name: COLUMN sessions.context_strategy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.context_strategy IS 'How to manage conversation context: isolated (fresh), inherit_previous (from prior session), shared_conversation (persistent)';


--
-- Name: COLUMN sessions.max_instruction_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.max_instruction_runs IS 'Maximum instruction executions allowed in this session (prevents infinite loops). Budget per session.';


--
-- Name: sessions_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.sessions_history (
    history_id integer NOT NULL,
    session_id integer NOT NULL,
    canonical_code text NOT NULL,
    session_name text,
    session_description text,
    actor_id text,
    context_strategy text,
    max_instruction_runs integer,
    enabled boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    archived_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    change_reason text
);


ALTER TABLE public.sessions_history OWNER TO base_admin;

--
-- Name: TABLE sessions_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.sessions_history IS 'Audit trail of all changes to sessions table. Preserves session template changes, crucial for understanding why old recipe runs behaved differently.';


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

ALTER SEQUENCE public.sessions_history_history_id_seq OWNED BY public.sessions_history.history_id;


--
-- Name: sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sessions_session_id_seq OWNER TO base_admin;

--
-- Name: sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.sessions_session_id_seq OWNED BY public.sessions.session_id;


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
    skill_alias text NOT NULL,
    skill_name text NOT NULL,
    display_name text,
    language text DEFAULT 'en'::text,
    confidence numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    skill_id integer DEFAULT nextval('public.skill_aliases_skill_id_seq'::regclass) NOT NULL
);


ALTER TABLE public.skill_aliases OWNER TO base_admin;

--
-- Name: TABLE skill_aliases; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_aliases IS 'Master list of 896 skills with canonical names and aliases. Standardized 2025-10-30.
Pattern: skill_id (INTEGER PK) + skill_name (TEXT UNIQUE) for AI consistency.';


--
-- Name: COLUMN skill_aliases.skill_alias; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_alias IS 'Any variation: lowercase, uppercase, hyphenated, translated, etc.';


--
-- Name: COLUMN skill_aliases.skill_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_name IS 'Natural key - canonical skill name in UPPER_SNAKE_CASE (unique)';


--
-- Name: COLUMN skill_aliases.display_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.display_name IS 'Pretty format for UI display (e.g., "Python", "SQLite", "iShares")';


--
-- Name: COLUMN skill_aliases.skill_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_id IS 'Surrogate key - stable integer identifier for joins';


--
-- Name: skill_extraction_log; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_extraction_log (
    log_id integer NOT NULL,
    job_id text NOT NULL,
    extraction_attempt integer DEFAULT 1,
    raw_skills_found text[],
    mapped_skills text[],
    unmapped_skills text[],
    extraction_method text,
    llm_model text,
    processing_time_seconds double precision,
    success boolean DEFAULT true,
    error_message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.skill_extraction_log OWNER TO base_admin;

--
-- Name: TABLE skill_extraction_log; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_extraction_log IS 'Audit trail of all skill extraction attempts for debugging and improvement.';


--
-- Name: skill_extraction_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_extraction_log_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_extraction_log_log_id_seq OWNER TO base_admin;

--
-- Name: skill_extraction_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.skill_extraction_log_log_id_seq OWNED BY public.skill_extraction_log.log_id;


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
-- Name: skill_inference_rules; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_inference_rules (
    rule_id integer NOT NULL,
    rule_name text NOT NULL,
    rule_type text NOT NULL,
    source_skill_id integer,
    inferred_skill_id integer,
    confidence double precision DEFAULT 0.8,
    rule_description text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.skill_inference_rules OWNER TO base_admin;

--
-- Name: TABLE skill_inference_rules; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_inference_rules IS 'Rules for deriving implicit skills. Types: (1) Hierarchical = parent propagation, (2) Common sense = domain knowledge, (3) LLM-powered = contextual inference.';


--
-- Name: COLUMN skill_inference_rules.rule_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_inference_rules.rule_type IS 'hierarchical: Has "Kubernetes" → implies all parents. common_sense: "Traveling Salesman" → "Driver''s License". llm_powered: Ask LLM for context-specific inference.';


--
-- Name: skill_inference_rules_rule_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_inference_rules_rule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_inference_rules_rule_id_seq OWNER TO base_admin;

--
-- Name: skill_inference_rules_rule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.skill_inference_rules_rule_id_seq OWNED BY public.skill_inference_rules.rule_id;


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
-- Name: skill_relationships; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_relationships (
    relationship_type text NOT NULL,
    strength numeric(3,2) DEFAULT 1.0,
    source text,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    subject_skill_id integer NOT NULL,
    object_skill_id integer NOT NULL,
    CONSTRAINT skill_relationships_relationship_type_check CHECK ((relationship_type = ANY (ARRAY['requires'::text, 'alternative_to'::text, 'obsoletes'::text])))
);


ALTER TABLE public.skill_relationships OWNER TO base_admin;

--
-- Name: TABLE skill_relationships; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_relationships IS 'Semantic relationships between skills (0 rows currently). Fully integer-based.
Composite PK: (subject_skill_id, relationship_type, object_skill_id).';


--
-- Name: COLUMN skill_relationships.relationship_type; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_relationships.relationship_type IS 'CONSTRAINED to: requires, alternative_to, obsoletes. Add more via ALTER TABLE CHECK.';


--
-- Name: skill_synonyms; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_synonyms (
    synonym_id integer NOT NULL,
    synonym_text text NOT NULL,
    canonical_skill_id integer NOT NULL,
    confidence double precision DEFAULT 1.0,
    source text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_by text,
    review_notes text,
    language text DEFAULT 'en'::text
);


ALTER TABLE public.skill_synonyms OWNER TO base_admin;

--
-- Name: TABLE skill_synonyms; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_synonyms IS 'Maps alternative skill names to canonical taxonomy entries. Used for normalizing raw skill extractions.';


--
-- Name: COLUMN skill_synonyms.confidence; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_synonyms.confidence IS '1.0 = human verified (gold standard), 0.7-0.9 = LLM high confidence (auto-add), <0.7 = requires human review';


--
-- Name: COLUMN skill_synonyms.language; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_synonyms.language IS 'ISO 639-1 language code: en, de, fr, es, zh, ja, etc. Canonical skills are always "en".';


--
-- Name: skill_synonyms_synonym_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.skill_synonyms_synonym_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.skill_synonyms_synonym_id_seq OWNER TO base_admin;

--
-- Name: skill_synonyms_synonym_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.skill_synonyms_synonym_id_seq OWNED BY public.skill_synonyms.synonym_id;


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
    raw_skill_name text NOT NULL,
    occurrences integer DEFAULT 1,
    suggested_domain text,
    suggested_canonical text,
    suggested_confidence double precision,
    review_status text DEFAULT 'pending'::text,
    found_in_jobs text[],
    llm_reasoning text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    reviewed_at timestamp without time zone,
    reviewed_by text,
    notes text,
    pending_skill_id integer DEFAULT nextval('public.skills_pending_taxonomy_pending_skill_id_seq'::regclass) NOT NULL,
    CONSTRAINT skills_pending_taxonomy_review_status_check CHECK ((review_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'duplicate'::text])))
);


ALTER TABLE public.skills_pending_taxonomy OWNER TO base_admin;

--
-- Name: TABLE skills_pending_taxonomy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skills_pending_taxonomy IS 'Skills awaiting taxonomy classification (1090 entries). Standardized 2025-10-30.
Pattern: pending_skill_id (INTEGER PK) + raw_skill_name (TEXT UNIQUE).';


--
-- Name: COLUMN skills_pending_taxonomy.raw_skill_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skills_pending_taxonomy.raw_skill_name IS 'Natural key - raw skill text extracted from postings (unique)';


--
-- Name: COLUMN skills_pending_taxonomy.pending_skill_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skills_pending_taxonomy.pending_skill_id IS 'Surrogate key - stable integer identifier';


--
-- Name: v_actor_delegation_stats; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_actor_delegation_stats AS
 SELECT a.actor_name AS actor_id,
    a.actor_type,
    a.execution_type,
    count(DISTINCT i.instruction_id) AS delegated_instruction_count,
    count(DISTINCT i.session_id) AS delegated_in_sessions,
    a.enabled
   FROM (public.actors a
     LEFT JOIN public.instructions i ON ((a.actor_name = i.delegate_actor_name)))
  GROUP BY a.actor_name, a.actor_type, a.execution_type, a.enabled
 HAVING (count(DISTINCT i.instruction_id) > 0)
  ORDER BY (count(DISTINCT i.instruction_id)) DESC;


ALTER TABLE public.v_actor_delegation_stats OWNER TO base_admin;

--
-- Name: VIEW v_actor_delegation_stats; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_actor_delegation_stats IS 'Statistics showing which actors are used for instruction delegation.
   Use to understand delegation patterns across recipes.';


--
-- Name: v_canonicals_orphaned; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_canonicals_orphaned AS
 SELECT c.canonical_name AS canonical_code,
    c.facet_name AS facet_id,
    c.capability_description
   FROM public.canonicals c
  WHERE ((c.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.sessions s
          WHERE ((s.canonical_name = c.canonical_name) AND (s.enabled = true))))))
  ORDER BY c.canonical_name;


ALTER TABLE public.v_canonicals_orphaned OWNER TO base_admin;

--
-- Name: v_instruction_actors; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_instruction_actors AS
 SELECT i.instruction_id,
    i.session_id,
    s.session_name,
    i.step_number,
    i.step_description,
    s.actor_name AS session_primary_actor,
    i.delegate_actor_name AS delegate_actor_id,
    COALESCE(i.delegate_actor_name, s.actor_name) AS effective_actor,
        CASE
            WHEN (i.delegate_actor_name IS NOT NULL) THEN 'delegated'::text
            ELSE 'primary'::text
        END AS execution_mode,
    a_primary.actor_type AS primary_actor_type,
    a_delegate.actor_type AS delegate_actor_type
   FROM (((public.instructions i
     JOIN public.sessions s ON ((i.session_id = s.session_id)))
     LEFT JOIN public.actors a_primary ON ((s.actor_name = a_primary.actor_name)))
     LEFT JOIN public.actors a_delegate ON ((i.delegate_actor_name = a_delegate.actor_name)))
  ORDER BY i.session_id, i.step_number;


ALTER TABLE public.v_instruction_actors OWNER TO base_admin;

--
-- Name: VIEW v_instruction_actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_instruction_actors IS 'Shows which actor will execute each instruction (primary or delegated).
   Use this to understand instruction execution flow in sessions.';


--
-- Name: v_instruction_flow; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_instruction_flow AS
 SELECT i.instruction_id,
    s.session_name,
    i.step_number,
    i.step_description AS instruction_desc,
    ib.branch_id,
    ib.branch_condition,
    ib.branch_priority,
    ib.branch_description,
    ib.max_iterations,
        CASE
            WHEN (ib.next_instruction_id IS NOT NULL) THEN ('INSTRUCTION: '::text || ni.step_description)
            WHEN (ib.next_session_id IS NOT NULL) THEN ('SESSION: '::text || ns.session_name)
            ELSE 'END_SESSION'::text
        END AS branch_target,
    ib.enabled AS branch_enabled
   FROM ((((public.instructions i
     JOIN public.sessions s ON ((i.session_id = s.session_id)))
     LEFT JOIN public.instruction_branches ib ON ((i.instruction_id = ib.instruction_id)))
     LEFT JOIN public.instructions ni ON ((ib.next_instruction_id = ni.instruction_id)))
     LEFT JOIN public.sessions ns ON ((ib.next_session_id = ns.session_id)))
  ORDER BY s.session_name, i.step_number, ib.branch_priority DESC;


ALTER TABLE public.v_instruction_flow OWNER TO base_admin;

--
-- Name: VIEW v_instruction_flow; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_instruction_flow IS 'Human-readable view of instruction flow with branching logic. Shows what happens after each instruction based on output conditions.';


--
-- Name: variations; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.variations (
    variation_id integer NOT NULL,
    recipe_id integer NOT NULL,
    test_data jsonb NOT NULL,
    difficulty_level integer DEFAULT 1,
    expected_response text,
    response_format text,
    complexity_score real,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.variations OWNER TO base_admin;

--
-- Name: TABLE variations; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.variations IS 'Test data for recipes across difficulty levels. Each variation tests the same recipe with different inputs. Used in TESTING mode.';


--
-- Name: COLUMN variations.test_data; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.variations.test_data IS 'JSON object with test parameters. Schema varies by canonical. Example: {"job_description": "Senior Engineer role...", "max_words": 100}';


--
-- Name: COLUMN variations.difficulty_level; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.variations.difficulty_level IS 'Progressive difficulty: 1 (trivial), 2 (easy), 3 (medium), 4 (hard), 5 (expert)';


--
-- Name: v_pipeline_execution; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_pipeline_execution AS
 SELECT r.recipe_id,
    r.recipe_name,
    s.canonical_name AS canonical_code,
    s.session_name,
    (v.variation_id)::text AS input_id,
    'test'::text AS execution_mode,
    rr.batch_id,
    sr.session_run_id,
    sr.started_at,
    sr.completed_at,
    sr.quality_score,
    sr.validation_status
   FROM ((((public.recipe_runs rr
     JOIN public.recipes r ON ((rr.recipe_id = r.recipe_id)))
     JOIN public.variations v ON ((rr.variation_id = v.variation_id)))
     JOIN public.session_runs sr ON (((rr.recipe_run_id = sr.run_id) AND (sr.run_type = 'testing'::text))))
     JOIN public.sessions s ON ((sr.session_id = s.session_id)))
UNION ALL
 SELECT r.recipe_id,
    r.recipe_name,
    s.canonical_name AS canonical_code,
    s.session_name,
    pr.posting_name AS input_id,
    'production'::text AS execution_mode,
    NULL::integer AS batch_id,
    sr.session_run_id,
    sr.started_at,
    sr.completed_at,
    sr.quality_score,
    sr.validation_status
   FROM ((((public.production_runs pr
     JOIN public.recipes r ON ((pr.recipe_id = r.recipe_id)))
     JOIN public.postings p ON ((pr.posting_name = p.posting_name)))
     JOIN public.session_runs sr ON (((pr.production_run_id = sr.run_id) AND (sr.run_type = 'production'::text))))
     JOIN public.sessions s ON ((sr.session_id = s.session_id)));


ALTER TABLE public.v_pipeline_execution OWNER TO base_admin;

--
-- Name: VIEW v_pipeline_execution; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_pipeline_execution IS 'Unified view of all pipeline executions (testing + production).
   Now uses session_runs.run_id + run_type for cleaner joins.';


--
-- Name: v_recipes_missing_sessions; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_recipes_missing_sessions AS
 SELECT r.recipe_id,
    r.recipe_name,
    r.recipe_description,
    r.recipe_version
   FROM public.recipes r
  WHERE ((r.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.recipe_sessions rs
          WHERE (rs.recipe_id = r.recipe_id)))))
  ORDER BY r.recipe_id;


ALTER TABLE public.v_recipes_missing_sessions OWNER TO base_admin;

--
-- Name: v_recipes_missing_variations; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_recipes_missing_variations AS
 SELECT r.recipe_id,
    r.recipe_name,
    r.recipe_description,
    r.recipe_version
   FROM public.recipes r
  WHERE ((r.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.variations v
          WHERE ((v.recipe_id = r.recipe_id) AND (v.enabled = true))))))
  ORDER BY r.recipe_id;


ALTER TABLE public.v_recipes_missing_variations OWNER TO base_admin;

--
-- Name: v_recipes_ready_for_testing; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_recipes_ready_for_testing AS
 SELECT r.recipe_id,
    r.recipe_name,
    r.recipe_description,
    r.recipe_version,
    count(DISTINCT v.variation_id) AS variation_count,
    count(DISTINCT rs.session_id) AS session_count,
    count(DISTINCT i.instruction_id) AS instruction_count,
    COALESCE(( SELECT count(*) AS count
           FROM public.recipe_runs rr
          WHERE (rr.recipe_id = r.recipe_id)), (0)::bigint) AS run_count,
    5 AS runs_needed
   FROM ((((public.recipes r
     LEFT JOIN public.variations v ON (((v.recipe_id = r.recipe_id) AND (v.enabled = true))))
     LEFT JOIN public.recipe_sessions rs ON ((rs.recipe_id = r.recipe_id)))
     LEFT JOIN public.sessions s ON (((s.session_id = rs.session_id) AND (s.enabled = true))))
     LEFT JOIN public.instructions i ON (((i.session_id = s.session_id) AND (i.enabled = true))))
  WHERE ((r.enabled = true) AND (EXISTS ( SELECT 1
           FROM public.variations v2
          WHERE ((v2.recipe_id = r.recipe_id) AND (v2.enabled = true)))) AND (EXISTS ( SELECT 1
           FROM public.recipe_sessions rs2
          WHERE (rs2.recipe_id = r.recipe_id))) AND (EXISTS ( SELECT 1
           FROM ((public.recipe_sessions rs3
             JOIN public.sessions s3 ON ((rs3.session_id = s3.session_id)))
             JOIN public.instructions i2 ON ((i2.session_id = s3.session_id)))
          WHERE ((rs3.recipe_id = r.recipe_id) AND (i2.enabled = true)))))
  GROUP BY r.recipe_id, r.recipe_name, r.recipe_description, r.recipe_version
  ORDER BY r.recipe_id;


ALTER TABLE public.v_recipes_ready_for_testing OWNER TO base_admin;

--
-- Name: v_sessions_missing_instructions; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_sessions_missing_instructions AS
 SELECT s.session_id,
    s.canonical_name AS canonical_code,
    s.session_name
   FROM public.sessions s
  WHERE ((s.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.instructions i
          WHERE ((i.session_id = s.session_id) AND (i.enabled = true))))))
  ORDER BY s.session_id;


ALTER TABLE public.v_sessions_missing_instructions OWNER TO base_admin;

--
-- Name: v_pipeline_health; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_pipeline_health AS
 SELECT ( SELECT count(*) AS count
           FROM public.v_canonicals_orphaned) AS canonicals_orphaned,
    ( SELECT count(*) AS count
           FROM public.v_recipes_missing_variations) AS recipes_missing_variations,
    ( SELECT count(*) AS count
           FROM public.v_recipes_missing_sessions) AS recipes_missing_sessions,
    ( SELECT count(*) AS count
           FROM public.v_sessions_missing_instructions) AS sessions_missing_instructions,
    ( SELECT count(*) AS count
           FROM public.v_recipes_ready_for_testing) AS recipes_ready_for_testing;


ALTER TABLE public.v_pipeline_health OWNER TO base_admin;

--
-- Name: v_production_qa; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_production_qa AS
 SELECT pr.production_run_id,
    p.posting_name AS job_id,
    p.job_title,
    p.organization_name,
    r.recipe_id,
    r.recipe_name,
    pr.status AS run_status,
    pr.started_at,
    pr.completed_at,
    (pr.completed_at - pr.started_at) AS total_duration,
    count(sr.session_run_id) AS session_count,
    sum(
        CASE
            WHEN (sr.validation_status = 'PASS'::text) THEN 1
            ELSE 0
        END) AS passed_sessions,
    sum(
        CASE
            WHEN (sr.validation_status = 'FAIL'::text) THEN 1
            ELSE 0
        END) AS failed_sessions,
    sum(
        CASE
            WHEN (sr.status = 'ERROR'::text) THEN 1
            ELSE 0
        END) AS error_sessions,
    avg(ir.latency_ms) AS avg_instruction_latency_ms
   FROM ((((public.production_runs pr
     JOIN public.postings p ON ((p.posting_name = pr.posting_name)))
     JOIN public.recipes r ON ((r.recipe_id = pr.recipe_id)))
     LEFT JOIN public.session_runs sr ON (((sr.run_id = pr.production_run_id) AND (sr.run_type = 'production'::text))))
     LEFT JOIN public.instruction_runs ir ON ((ir.session_run_id = sr.session_run_id)))
  GROUP BY pr.production_run_id, p.posting_name, p.job_title, p.organization_name, r.recipe_id, r.recipe_name, pr.status, pr.started_at, pr.completed_at
  ORDER BY pr.started_at DESC;


ALTER TABLE public.v_production_qa OWNER TO base_admin;

--
-- Name: VIEW v_production_qa; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_production_qa IS 'Production run quality metrics.
   Now uses session_runs.run_id + run_type for cleaner joins.';


--
-- Name: v_recipe_orchestration; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_recipe_orchestration AS
 SELECT r.recipe_id,
    r.recipe_name,
    r.recipe_version,
    r.enabled AS recipe_enabled,
    rs.recipe_session_id,
    rs.execution_order,
    s.session_id,
    s.session_name,
    c.canonical_name AS canonical_code,
    c.capability_description AS what_it_does,
    a.actor_name AS actor_id,
    a.actor_type,
    rs.execute_condition,
    rs.on_success_action,
    rs.on_failure_action,
    rs.max_retry_attempts,
    count(i.instruction_id) AS instruction_count
   FROM (((((public.recipes r
     JOIN public.recipe_sessions rs ON ((rs.recipe_id = r.recipe_id)))
     JOIN public.sessions s ON ((s.session_id = rs.session_id)))
     JOIN public.canonicals c ON ((c.canonical_name = s.canonical_name)))
     JOIN public.actors a ON ((a.actor_name = s.actor_name)))
     LEFT JOIN public.instructions i ON ((i.session_id = s.session_id)))
  GROUP BY r.recipe_id, r.recipe_name, r.recipe_version, r.enabled, rs.recipe_session_id, rs.execution_order, s.session_id, s.session_name, c.canonical_name, c.capability_description, a.actor_name, a.actor_type, rs.execute_condition, rs.on_success_action, rs.on_failure_action, rs.max_retry_attempts
  ORDER BY r.recipe_id, rs.execution_order;


ALTER TABLE public.v_recipe_orchestration OWNER TO base_admin;

--
-- Name: VIEW v_recipe_orchestration; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_recipe_orchestration IS 'Shows how recipes combine sessions. Use for Orchestrate View in GUI. Shows multi-phase workflow composition.';


--
-- Name: variations_history; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.variations_history (
    history_id integer NOT NULL,
    variation_id integer NOT NULL,
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


ALTER TABLE public.variations_history OWNER TO base_admin;

--
-- Name: TABLE variations_history; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.variations_history IS 'Audit trail of all changes to variations table. Tracks test data evolution, helps identify when variations were modified that might affect test reproducibility.';


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

ALTER SEQUENCE public.variations_history_history_id_seq OWNED BY public.variations_history.history_id;


--
-- Name: variations_variation_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.variations_variation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.variations_variation_id_seq OWNER TO base_admin;

--
-- Name: variations_variation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.variations_variation_id_seq OWNED BY public.variations.variation_id;


--
-- Name: batches batch_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.batches ALTER COLUMN batch_id SET DEFAULT nextval('public.batches_batch_id_seq'::regclass);


--
-- Name: canonicals_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals_history ALTER COLUMN history_id SET DEFAULT nextval('public.canonicals_history_history_id_seq'::regclass);


--
-- Name: facets_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets_history ALTER COLUMN history_id SET DEFAULT nextval('public.facets_history_history_id_seq'::regclass);


--
-- Name: instruction_branch_executions execution_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branch_executions ALTER COLUMN execution_id SET DEFAULT nextval('public.instruction_branch_executions_execution_id_seq'::regclass);


--
-- Name: instruction_branches branch_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branches ALTER COLUMN branch_id SET DEFAULT nextval('public.instruction_branches_branch_id_seq'::regclass);


--
-- Name: instruction_runs instruction_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_runs ALTER COLUMN instruction_run_id SET DEFAULT nextval('public.instruction_runs_instruction_run_id_seq'::regclass);


--
-- Name: instructions instruction_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions ALTER COLUMN instruction_id SET DEFAULT nextval('public.instructions_instruction_id_seq'::regclass);


--
-- Name: instructions_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions_history ALTER COLUMN history_id SET DEFAULT nextval('public.instructions_history_history_id_seq'::regclass);


--
-- Name: job_nodes node_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_nodes ALTER COLUMN node_id SET DEFAULT nextval('public.job_nodes_node_id_seq'::regclass);


--
-- Name: job_skill_edges edge_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skill_edges ALTER COLUMN edge_id SET DEFAULT nextval('public.job_skill_edges_edge_id_seq'::regclass);


--
-- Name: job_skills job_skill_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills ALTER COLUMN job_skill_id SET DEFAULT nextval('public.job_skills_job_skill_id_seq'::regclass);


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
-- Name: profile_skills profile_skill_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills ALTER COLUMN profile_skill_id SET DEFAULT nextval('public.profile_skills_profile_skill_id_seq'::regclass);


--
-- Name: profile_work_history work_history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history ALTER COLUMN work_history_id SET DEFAULT nextval('public.profile_work_history_work_history_id_seq'::regclass);


--
-- Name: profiles profile_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles ALTER COLUMN profile_id SET DEFAULT nextval('public.profiles_profile_id_seq'::regclass);


--
-- Name: recipe_runs recipe_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_runs ALTER COLUMN recipe_run_id SET DEFAULT nextval('public.recipe_runs_recipe_run_id_seq'::regclass);


--
-- Name: recipe_sessions recipe_session_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions ALTER COLUMN recipe_session_id SET DEFAULT nextval('public.recipe_sessions_recipe_session_id_seq'::regclass);


--
-- Name: recipes recipe_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipes ALTER COLUMN recipe_id SET DEFAULT nextval('public.recipes_recipe_id_seq'::regclass);


--
-- Name: recipes_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipes_history ALTER COLUMN history_id SET DEFAULT nextval('public.recipes_history_history_id_seq'::regclass);


--
-- Name: session_runs session_run_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs ALTER COLUMN session_run_id SET DEFAULT nextval('public.session_runs_session_run_id_seq'::regclass);


--
-- Name: sessions session_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions ALTER COLUMN session_id SET DEFAULT nextval('public.sessions_session_id_seq'::regclass);


--
-- Name: sessions_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions_history ALTER COLUMN history_id SET DEFAULT nextval('public.sessions_history_history_id_seq'::regclass);


--
-- Name: skill_extraction_log log_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_extraction_log ALTER COLUMN log_id SET DEFAULT nextval('public.skill_extraction_log_log_id_seq'::regclass);


--
-- Name: skill_inference_rules rule_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_inference_rules ALTER COLUMN rule_id SET DEFAULT nextval('public.skill_inference_rules_rule_id_seq'::regclass);


--
-- Name: skill_occurrences occurrence_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences ALTER COLUMN occurrence_id SET DEFAULT nextval('public.skill_occurrences_occurrence_id_seq'::regclass);


--
-- Name: skill_synonyms synonym_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_synonyms ALTER COLUMN synonym_id SET DEFAULT nextval('public.skill_synonyms_synonym_id_seq'::regclass);


--
-- Name: variations variation_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.variations ALTER COLUMN variation_id SET DEFAULT nextval('public.variations_variation_id_seq'::regclass);


--
-- Name: variations_history history_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.variations_history ALTER COLUMN history_id SET DEFAULT nextval('public.variations_history_history_id_seq'::regclass);


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
-- Name: canonicals canonicals_canonical_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals
    ADD CONSTRAINT canonicals_canonical_name_unique UNIQUE (canonical_name);


--
-- Name: canonicals_history canonicals_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals_history
    ADD CONSTRAINT canonicals_history_pkey PRIMARY KEY (history_id);


--
-- Name: canonicals canonicals_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals
    ADD CONSTRAINT canonicals_pkey PRIMARY KEY (canonical_id);


--
-- Name: facets facets_facet_name_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets
    ADD CONSTRAINT facets_facet_name_unique UNIQUE (facet_name);


--
-- Name: facets_history facets_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets_history
    ADD CONSTRAINT facets_history_pkey PRIMARY KEY (history_id);


--
-- Name: facets facets_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets
    ADD CONSTRAINT facets_pkey PRIMARY KEY (facet_id);


--
-- Name: human_tasks human_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_pkey PRIMARY KEY (task_id);


--
-- Name: instruction_branch_executions instruction_branch_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branch_executions
    ADD CONSTRAINT instruction_branch_executions_pkey PRIMARY KEY (execution_id);


--
-- Name: instruction_branches instruction_branches_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branches
    ADD CONSTRAINT instruction_branches_pkey PRIMARY KEY (branch_id);


--
-- Name: instruction_runs instruction_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_runs
    ADD CONSTRAINT instruction_runs_pkey PRIMARY KEY (instruction_run_id);


--
-- Name: instructions_history instructions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions_history
    ADD CONSTRAINT instructions_history_pkey PRIMARY KEY (history_id);


--
-- Name: instructions instructions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_pkey PRIMARY KEY (instruction_id);


--
-- Name: instructions instructions_session_id_step_number_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_session_id_step_number_key UNIQUE (session_id, step_number);


--
-- Name: job_nodes job_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_nodes
    ADD CONSTRAINT job_nodes_pkey PRIMARY KEY (node_id);


--
-- Name: job_nodes job_nodes_skill_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_nodes
    ADD CONSTRAINT job_nodes_skill_name_key UNIQUE (skill_name);


--
-- Name: job_skill_edges job_skill_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skill_edges
    ADD CONSTRAINT job_skill_edges_pkey PRIMARY KEY (edge_id);


--
-- Name: job_skill_edges job_skill_edges_source_node_id_target_node_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skill_edges
    ADD CONSTRAINT job_skill_edges_source_node_id_target_node_id_key UNIQUE (source_node_id, target_node_id);


--
-- Name: job_skills job_skills_job_id_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_job_id_skill_id_key UNIQUE (posting_name, skill_id);


--
-- Name: job_skills job_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_pkey PRIMARY KEY (job_skill_id);


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
    ADD CONSTRAINT production_runs_recipe_id_posting_id_key UNIQUE (recipe_id, posting_name);


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
-- Name: recipe_runs recipe_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_runs
    ADD CONSTRAINT recipe_runs_pkey PRIMARY KEY (recipe_run_id);


--
-- Name: recipe_sessions recipe_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions
    ADD CONSTRAINT recipe_sessions_pkey PRIMARY KEY (recipe_session_id);


--
-- Name: recipe_sessions recipe_sessions_recipe_id_execution_order_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions
    ADD CONSTRAINT recipe_sessions_recipe_id_execution_order_key UNIQUE (recipe_id, execution_order);


--
-- Name: recipes_history recipes_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipes_history
    ADD CONSTRAINT recipes_history_pkey PRIMARY KEY (history_id);


--
-- Name: recipes recipes_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipes
    ADD CONSTRAINT recipes_pkey PRIMARY KEY (recipe_id);


--
-- Name: recipes recipes_recipe_name_recipe_version_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipes
    ADD CONSTRAINT recipes_recipe_name_recipe_version_key UNIQUE (recipe_name, recipe_version);


--
-- Name: schema_documentation schema_documentation_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.schema_documentation
    ADD CONSTRAINT schema_documentation_pkey PRIMARY KEY (documentation_id);


--
-- Name: schema_documentation schema_documentation_table_column_unique; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.schema_documentation
    ADD CONSTRAINT schema_documentation_table_column_unique UNIQUE (table_name, column_name);


--
-- Name: session_runs session_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs
    ADD CONSTRAINT session_runs_pkey PRIMARY KEY (session_run_id);


--
-- Name: sessions_history sessions_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions_history
    ADD CONSTRAINT sessions_history_pkey PRIMARY KEY (history_id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


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
-- Name: skill_extraction_log skill_extraction_log_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_extraction_log
    ADD CONSTRAINT skill_extraction_log_pkey PRIMARY KEY (log_id);


--
-- Name: skill_hierarchy skill_hierarchy_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_pkey PRIMARY KEY (skill_id, parent_skill_id);


--
-- Name: skill_inference_rules skill_inference_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_inference_rules
    ADD CONSTRAINT skill_inference_rules_pkey PRIMARY KEY (rule_id);


--
-- Name: skill_inference_rules skill_inference_rules_rule_name_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_inference_rules
    ADD CONSTRAINT skill_inference_rules_rule_name_key UNIQUE (rule_name);


--
-- Name: skill_inference_rules skill_inference_rules_source_skill_id_inferred_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_inference_rules
    ADD CONSTRAINT skill_inference_rules_source_skill_id_inferred_skill_id_key UNIQUE (source_skill_id, inferred_skill_id);


--
-- Name: skill_occurrences skill_occurrences_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences
    ADD CONSTRAINT skill_occurrences_pkey PRIMARY KEY (occurrence_id);


--
-- Name: skill_relationships skill_relationships_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_relationships
    ADD CONSTRAINT skill_relationships_pkey PRIMARY KEY (subject_skill_id, relationship_type, object_skill_id);


--
-- Name: skill_synonyms skill_synonyms_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_synonyms
    ADD CONSTRAINT skill_synonyms_pkey PRIMARY KEY (synonym_id);


--
-- Name: skill_synonyms skill_synonyms_synonym_text_canonical_skill_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_synonyms
    ADD CONSTRAINT skill_synonyms_synonym_text_canonical_skill_id_key UNIQUE (synonym_text, canonical_skill_id);


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
-- Name: variations_history variations_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.variations_history
    ADD CONSTRAINT variations_history_pkey PRIMARY KEY (history_id);


--
-- Name: variations variations_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.variations
    ADD CONSTRAINT variations_pkey PRIMARY KEY (variation_id);


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

CREATE INDEX idx_branch_exec_branch ON public.instruction_branch_executions USING btree (branch_id);


--
-- Name: idx_branch_exec_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_branch_exec_run ON public.instruction_branch_executions USING btree (instruction_run_id);


--
-- Name: idx_branches_instruction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_branches_instruction ON public.instruction_branches USING btree (instruction_id) WHERE (enabled = true);


--
-- Name: idx_branches_priority; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_branches_priority ON public.instruction_branches USING btree (instruction_id, branch_priority DESC) WHERE (enabled = true);


--
-- Name: idx_canonicals_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_canonicals_enabled ON public.canonicals USING btree (enabled);


--
-- Name: idx_canonicals_facet; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_canonicals_facet ON public.canonicals USING btree (facet_name);


--
-- Name: idx_certifications_expiration; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_expiration ON public.profile_certifications USING btree (expiration_date);


--
-- Name: idx_certifications_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_certifications_profile ON public.profile_certifications USING btree (profile_id);


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
-- Name: idx_facets_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_facets_enabled ON public.facets USING btree (enabled);


--
-- Name: idx_facets_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_facets_parent ON public.facets USING btree (parent_facet_name);


--
-- Name: idx_human_tasks_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_human_tasks_actor ON public.human_tasks USING btree (actor_name, status);


--
-- Name: idx_human_tasks_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_human_tasks_status ON public.human_tasks USING btree (status, created_at);


--
-- Name: idx_inference_rules_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_inference_rules_enabled ON public.skill_inference_rules USING btree (enabled) WHERE (enabled = true);


--
-- Name: idx_inference_rules_inferred; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_inference_rules_inferred ON public.skill_inference_rules USING btree (inferred_skill_id);


--
-- Name: idx_inference_rules_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_inference_rules_source ON public.skill_inference_rules USING btree (source_skill_id);


--
-- Name: idx_instruction_runs_instruction; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_runs_instruction ON public.instruction_runs USING btree (instruction_id);


--
-- Name: idx_instruction_runs_session_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_runs_session_run ON public.instruction_runs USING btree (session_run_id);


--
-- Name: idx_instruction_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instruction_runs_status ON public.instruction_runs USING btree (status);


--
-- Name: idx_instructions_delegate_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_delegate_actor ON public.instructions USING btree (delegate_actor_name) WHERE (delegate_actor_name IS NOT NULL);


--
-- Name: idx_instructions_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_enabled ON public.instructions USING btree (enabled);


--
-- Name: idx_instructions_session; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_instructions_session ON public.instructions USING btree (session_id);


--
-- Name: idx_job_nodes_category; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_nodes_category ON public.job_nodes USING btree (category);


--
-- Name: idx_job_skill_edges_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skill_edges_source ON public.job_skill_edges USING btree (source_node_id);


--
-- Name: idx_job_skill_edges_target; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skill_edges_target ON public.job_skill_edges USING btree (target_node_id);


--
-- Name: idx_job_skills_job; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_job ON public.job_skills USING btree (posting_name);


--
-- Name: idx_job_skills_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_recipe ON public.job_skills USING btree (recipe_run_id);


--
-- Name: idx_job_skills_required; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_required ON public.job_skills USING btree (required) WHERE (required = true);


--
-- Name: idx_job_skills_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_job_skills_skill ON public.job_skills USING btree (skill_id);


--
-- Name: idx_languages_proficiency; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_languages_proficiency ON public.profile_languages USING btree (proficiency_level);


--
-- Name: idx_languages_profile; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_languages_profile ON public.profile_languages USING btree (profile_id);


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
-- Name: idx_postings_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_enabled ON public.postings USING btree (enabled);


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
-- Name: idx_postings_summary_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_summary_status ON public.postings USING btree (summary_extraction_status) WHERE (summary_extraction_status = 'pending'::text);


--
-- Name: idx_postings_test; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_postings_test ON public.postings USING btree (is_test_posting) WHERE (is_test_posting = true);


--
-- Name: idx_production_runs_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_posting ON public.production_runs USING btree (posting_name);


--
-- Name: idx_production_runs_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_recipe ON public.production_runs USING btree (recipe_id);


--
-- Name: idx_production_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_status ON public.production_runs USING btree (status);


--
-- Name: idx_profile_skills_implicit; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_profile_skills_implicit ON public.profile_skills USING btree (is_implicit);


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
-- Name: idx_recipe_runs_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_batch ON public.recipe_runs USING btree (batch_id);


--
-- Name: idx_recipe_runs_batch_tracking; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_batch_tracking ON public.recipe_runs USING btree (variation_id, batch_number, status);


--
-- Name: idx_recipe_runs_execution_mode; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_execution_mode ON public.recipe_runs USING btree (recipe_id, execution_mode, status);


--
-- Name: idx_recipe_runs_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_recipe ON public.recipe_runs USING btree (recipe_id);


--
-- Name: idx_recipe_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_status ON public.recipe_runs USING btree (status);


--
-- Name: idx_recipe_runs_variation; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_runs_variation ON public.recipe_runs USING btree (variation_id);


--
-- Name: idx_recipe_sessions_order; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_sessions_order ON public.recipe_sessions USING btree (recipe_id, execution_order);


--
-- Name: idx_recipe_sessions_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_sessions_recipe ON public.recipe_sessions USING btree (recipe_id);


--
-- Name: idx_recipe_sessions_session; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipe_sessions_session ON public.recipe_sessions USING btree (session_id);


--
-- Name: idx_recipes_documentation_fts; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipes_documentation_fts ON public.recipes USING gin (to_tsvector('english'::regconfig, COALESCE(documentation, ''::text)));


--
-- Name: idx_recipes_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipes_enabled ON public.recipes USING btree (enabled);


--
-- Name: idx_recipes_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipes_name ON public.recipes USING btree (recipe_name);


--
-- Name: idx_session_runs_session; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_runs_session ON public.session_runs USING btree (session_id);


--
-- Name: idx_session_runs_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_runs_status ON public.session_runs USING btree (status);


--
-- Name: idx_sessions_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_sessions_actor ON public.sessions USING btree (actor_name);


--
-- Name: idx_sessions_canonical; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_sessions_canonical ON public.sessions USING btree (canonical_name);


--
-- Name: idx_sessions_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_sessions_enabled ON public.sessions USING btree (enabled);


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
-- Name: idx_skill_extraction_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_extraction_created ON public.skill_extraction_log USING btree (created_at DESC);


--
-- Name: idx_skill_extraction_job; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_extraction_job ON public.skill_extraction_log USING btree (job_id);


--
-- Name: idx_skill_occ_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_created ON public.skill_occurrences USING btree (created_at);


--
-- Name: idx_skill_occ_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_source ON public.skill_occurrences USING btree (skill_source, source_id);


--
-- Name: idx_skill_rel_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_rel_type ON public.skill_relationships USING btree (relationship_type);


--
-- Name: idx_skills_pending_occurrences; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skills_pending_occurrences ON public.skills_pending_taxonomy USING btree (occurrences DESC);


--
-- Name: idx_skills_pending_status; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skills_pending_status ON public.skills_pending_taxonomy USING btree (review_status);


--
-- Name: idx_synonyms_canonical; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_synonyms_canonical ON public.skill_synonyms USING btree (canonical_skill_id);


--
-- Name: idx_synonyms_confidence; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_synonyms_confidence ON public.skill_synonyms USING btree (confidence) WHERE (confidence < (0.7)::double precision);


--
-- Name: idx_synonyms_language; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_synonyms_language ON public.skill_synonyms USING btree (language);


--
-- Name: idx_synonyms_text_lower; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_synonyms_text_lower ON public.skill_synonyms USING btree (lower(synonym_text));


--
-- Name: idx_variations_difficulty; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_variations_difficulty ON public.variations USING btree (difficulty_level);


--
-- Name: idx_variations_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_variations_enabled ON public.variations USING btree (enabled);


--
-- Name: idx_variations_recipe; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_variations_recipe ON public.variations USING btree (recipe_id);


--
-- Name: idx_variations_test_data; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_variations_test_data ON public.variations USING gin (test_data);


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
-- Name: recipe_runs_unique_success_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX recipe_runs_unique_success_batch ON public.recipe_runs USING btree (recipe_id, variation_id, batch_id, execution_mode) WHERE (status = 'SUCCESS'::text);


--
-- Name: canonicals canonicals_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER canonicals_history_trigger BEFORE UPDATE ON public.canonicals FOR EACH ROW EXECUTE FUNCTION public.archive_canonicals();


--
-- Name: profile_certifications certifications_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER certifications_updated_at_trigger BEFORE UPDATE ON public.profile_certifications FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: profile_education education_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER education_updated_at_trigger BEFORE UPDATE ON public.profile_education FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: facets facets_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER facets_history_trigger BEFORE UPDATE ON public.facets FOR EACH ROW EXECUTE FUNCTION public.archive_facets();


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
-- Name: recipes recipes_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER recipes_history_trigger BEFORE UPDATE ON public.recipes FOR EACH ROW EXECUTE FUNCTION public.archive_recipes();


--
-- Name: sessions sessions_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER sessions_history_trigger BEFORE UPDATE ON public.sessions FOR EACH ROW EXECUTE FUNCTION public.archive_sessions();


--
-- Name: variations variations_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER variations_history_trigger BEFORE UPDATE ON public.variations FOR EACH ROW EXECUTE FUNCTION public.archive_variations();


--
-- Name: profile_work_history work_history_duration_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_duration_trigger BEFORE INSERT OR UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.calculate_work_duration();


--
-- Name: profile_work_history work_history_updated_at_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER work_history_updated_at_trigger BEFORE UPDATE ON public.profile_work_history FOR EACH ROW EXECUTE FUNCTION public.update_profiles_updated_at();


--
-- Name: canonicals canonicals_facet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals
    ADD CONSTRAINT canonicals_facet_id_fkey FOREIGN KEY (facet_id) REFERENCES public.facets(facet_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: facets facets_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets
    ADD CONSTRAINT facets_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.facets(facet_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: instruction_branch_executions fk_branch; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branch_executions
    ADD CONSTRAINT fk_branch FOREIGN KEY (branch_id) REFERENCES public.instruction_branches(branch_id) ON DELETE CASCADE;


--
-- Name: instruction_branches fk_instruction; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branches
    ADD CONSTRAINT fk_instruction FOREIGN KEY (instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE CASCADE;


--
-- Name: instruction_branch_executions fk_instruction_run; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branch_executions
    ADD CONSTRAINT fk_instruction_run FOREIGN KEY (instruction_run_id) REFERENCES public.instruction_runs(instruction_run_id) ON DELETE CASCADE;


--
-- Name: instruction_branches fk_next_instruction; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branches
    ADD CONSTRAINT fk_next_instruction FOREIGN KEY (next_instruction_id) REFERENCES public.instructions(instruction_id) ON DELETE SET NULL;


--
-- Name: instruction_branches fk_next_session; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_branches
    ADD CONSTRAINT fk_next_session FOREIGN KEY (next_session_id) REFERENCES public.sessions(session_id) ON DELETE SET NULL;


--
-- Name: human_tasks human_tasks_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: human_tasks human_tasks_instruction_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_instruction_run_id_fkey FOREIGN KEY (instruction_run_id) REFERENCES public.instruction_runs(instruction_run_id);


--
-- Name: human_tasks human_tasks_session_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.human_tasks
    ADD CONSTRAINT human_tasks_session_run_id_fkey FOREIGN KEY (session_run_id) REFERENCES public.session_runs(session_run_id);


--
-- Name: instruction_runs instruction_runs_instruction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_runs
    ADD CONSTRAINT instruction_runs_instruction_id_fkey FOREIGN KEY (instruction_id) REFERENCES public.instructions(instruction_id);


--
-- Name: instruction_runs instruction_runs_session_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instruction_runs
    ADD CONSTRAINT instruction_runs_session_run_id_fkey FOREIGN KEY (session_run_id) REFERENCES public.session_runs(session_run_id);


--
-- Name: instructions instructions_delegate_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_delegate_actor_id_fkey FOREIGN KEY (delegate_actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: instructions instructions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.instructions
    ADD CONSTRAINT instructions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id);


--
-- Name: job_skill_edges job_skill_edges_source_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skill_edges
    ADD CONSTRAINT job_skill_edges_source_node_id_fkey FOREIGN KEY (source_node_id) REFERENCES public.job_nodes(node_id);


--
-- Name: job_skill_edges job_skill_edges_target_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skill_edges
    ADD CONSTRAINT job_skill_edges_target_node_id_fkey FOREIGN KEY (target_node_id) REFERENCES public.job_nodes(node_id);


--
-- Name: job_skills job_skills_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: job_skills job_skills_recipe_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_recipe_run_id_fkey FOREIGN KEY (recipe_run_id) REFERENCES public.recipe_runs(recipe_run_id);


--
-- Name: production_runs production_runs_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(posting_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: production_runs production_runs_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(recipe_id);


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
-- Name: profile_languages profile_languages_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_languages
    ADD CONSTRAINT profile_languages_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: profile_work_history profile_work_history_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_work_history
    ADD CONSTRAINT profile_work_history_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(profile_id) ON DELETE CASCADE;


--
-- Name: recipe_runs recipe_runs_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_runs
    ADD CONSTRAINT recipe_runs_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batches(batch_id);


--
-- Name: recipe_runs recipe_runs_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_runs
    ADD CONSTRAINT recipe_runs_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(recipe_id);


--
-- Name: recipe_runs recipe_runs_variation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_runs
    ADD CONSTRAINT recipe_runs_variation_id_fkey FOREIGN KEY (variation_id) REFERENCES public.variations(variation_id);


--
-- Name: recipe_sessions recipe_sessions_depends_on_recipe_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions
    ADD CONSTRAINT recipe_sessions_depends_on_recipe_session_id_fkey FOREIGN KEY (depends_on_recipe_session_id) REFERENCES public.recipe_sessions(recipe_session_id);


--
-- Name: recipe_sessions recipe_sessions_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions
    ADD CONSTRAINT recipe_sessions_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(recipe_id);


--
-- Name: recipe_sessions recipe_sessions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.recipe_sessions
    ADD CONSTRAINT recipe_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id);


--
-- Name: session_runs session_runs_recipe_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs
    ADD CONSTRAINT session_runs_recipe_session_id_fkey FOREIGN KEY (recipe_session_id) REFERENCES public.recipe_sessions(recipe_session_id);


--
-- Name: session_runs session_runs_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs
    ADD CONSTRAINT session_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id);


--
-- Name: sessions sessions_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: sessions sessions_canonical_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_canonical_id_fkey FOREIGN KEY (canonical_id) REFERENCES public.canonicals(canonical_id) ON UPDATE CASCADE ON DELETE SET NULL;


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
-- Name: skill_relationships skill_relationships_object_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_relationships
    ADD CONSTRAINT skill_relationships_object_skill_id_fkey FOREIGN KEY (object_skill_id) REFERENCES public.skill_aliases(skill_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_relationships skill_relationships_subject_skill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_relationships
    ADD CONSTRAINT skill_relationships_subject_skill_id_fkey FOREIGN KEY (subject_skill_id) REFERENCES public.skill_aliases(skill_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: variations variations_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.variations
    ADD CONSTRAINT variations_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(recipe_id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

GRANT ALL ON SCHEMA public TO base_admin;


--
-- PostgreSQL database dump complete
--

\unrestrict pebSqSWD7HeH9o9IR29Kh3Mo5Ym8KDK87xANrKjLrmVRP5ZqCAI5srctW4MRqXz

