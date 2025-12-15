--
-- PostgreSQL database dump
--

\restrict t3sglj8BEl36ni1x5MCfc5gcbnG0VkYKdRK1MDvMtnzkSjdXJ3lgwhAZmLCQEHF

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
        OLD.canonical_code, OLD.facet_id, OLD.capability_description, OLD.prompt, OLD.response,
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
        facet_id, parent_id, short_description, remarks, enabled,
        created_at, updated_at, change_reason
    ) VALUES (
        OLD.facet_id, OLD.parent_id, OLD.short_description, OLD.remarks, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
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
        OLD.session_id, OLD.canonical_code, OLD.session_name, OLD.session_description,
        OLD.actor_id, OLD.context_strategy, OLD.max_instruction_runs, OLD.enabled,
        OLD.created_at, OLD.updated_at, 'Updated via trigger'
    );
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.archive_sessions() OWNER TO base_admin;

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: actors; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.actors (
    actor_id text NOT NULL,
    actor_type text NOT NULL,
    url text NOT NULL,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    execution_type text,
    execution_path text,
    execution_config jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT actors_actor_type_check CHECK ((actor_type = ANY (ARRAY['human'::text, 'ai_model'::text, 'script'::text, 'machine_actor'::text]))),
    CONSTRAINT actors_execution_type_check CHECK ((execution_type = ANY (ARRAY['ollama_api'::text, 'http_api'::text, 'python_script'::text, 'bash_script'::text, 'human_input'::text])))
);


ALTER TABLE public.actors OWNER TO base_admin;

--
-- Name: TABLE actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.actors IS 'Unified interface for execution entities: humans, AI models, or scripts. Enables human-in-the-loop workflows.';


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
-- Name: active_actors; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.active_actors AS
 SELECT actors.actor_id,
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
  ORDER BY actors.actor_type, actors.actor_id;


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
-- Name: canonicals; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.canonicals (
    canonical_code text NOT NULL,
    facet_id text NOT NULL,
    capability_description text,
    prompt text,
    response text NOT NULL,
    review_notes text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.canonicals OWNER TO base_admin;

--
-- Name: TABLE canonicals; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.canonicals IS 'Gold-standard test definitions manually validated by domain experts. Each canonical represents one atomic capability.';


--
-- Name: COLUMN canonicals.canonical_code; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.canonicals.canonical_code IS 'Unique identifier for this test case (e.g., summarize_job_posting_v1)';


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
-- Name: facets; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.facets (
    facet_id text NOT NULL,
    parent_id text,
    short_description text,
    remarks text,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.facets OWNER TO base_admin;

--
-- Name: TABLE facets; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.facets IS 'Universal taxonomy of cognitive capabilities for any responsive system (human, AI, script). Foundation of base.yoga systematic testing framework.';


--
-- Name: COLUMN facets.facet_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.facet_id IS 'Hierarchical ID (e.g., c_clean, ce_extract, ce_char_extract). Root facets: k, l, f, p, c, g, m, r, o';


--
-- Name: COLUMN facets.parent_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.facets.parent_id IS 'Parent facet for hierarchical organization (NULL for root facets)';


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
    actor_id text NOT NULL,
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
    delegate_actor_id text
);


ALTER TABLE public.instructions OWNER TO base_admin;

--
-- Name: TABLE instructions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.instructions IS 'Step-by-step prompts within a session. Instructions execute sequentially unless branching logic redirects.';


--
-- Name: COLUMN instructions.prompt_template; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.prompt_template IS 'Prompt template with variable substitution. Variables: {test_data.field}, {posting.field}, {step1_response}, etc.';


--
-- Name: COLUMN instructions.is_terminal; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.is_terminal IS 'If TRUE, this instruction ends the session (no next step)';


--
-- Name: COLUMN instructions.delegate_actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.instructions.delegate_actor_id IS 'Optional: Delegate this instruction to a specific actor instead of using session primary actor.
   
   Use cases:
   - Call skill_gopher directly for hierarchy building
   - Execute SQL scripts for data queries
   - Run Python scripts for data processing
   - Call validator scripts for quality checks
   
   Execution logic:
   - If delegate_actor_id IS NOT NULL: Execute with delegated actor
   - If delegate_actor_id IS NULL: Execute with session.actor_id (primary actor)
   
   Example:
     session.actor_id = "phi3:latest" (primary)
     instruction.delegate_actor_id = "skill_gopher"
     → This instruction executed by skill_gopher, not phi3';


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
    job_id text NOT NULL,
    skill_id integer NOT NULL,
    required boolean DEFAULT true,
    min_years_experience integer,
    mentioned_count integer DEFAULT 1,
    context_snippet text,
    extracted_by text,
    recipe_run_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    source_language text,
    original_term text
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
-- Name: postings; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.postings (
    job_id text NOT NULL,
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
    summary_extraction_status text DEFAULT 'pending'::text
);


ALTER TABLE public.postings OWNER TO base_admin;

--
-- Name: TABLE postings; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.postings IS 'Real job postings scraped from websites (Deutsche Bank, Arbeitsagentur, etc.). Used in PRODUCTION mode as input to recipes.';


--
-- Name: COLUMN postings.job_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.postings.job_id IS 'Unique job identifier from source system (e.g., 15929 from job15929.json)';


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
-- Name: production_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.production_runs (
    production_run_id integer NOT NULL,
    recipe_id integer NOT NULL,
    posting_id text NOT NULL,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    status text DEFAULT 'RUNNING'::text,
    total_sessions integer,
    completed_sessions integer DEFAULT 0,
    error_details text,
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
-- Name: COLUMN production_runs.posting_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.production_runs.posting_id IS 'Real job posting from postings table (production input), vs variation_id (test input)';


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
-- Name: profiles; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.profiles (
    profile_version integer NOT NULL,
    technical_skills jsonb,
    soft_skills jsonb,
    languages jsonb,
    preferred_roles jsonb,
    min_salary integer,
    max_commute_minutes integer,
    remote_preference text,
    current_employer text,
    available_from date,
    notice_period_days integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    active boolean DEFAULT true,
    actor_id text NOT NULL,
    CONSTRAINT gershon_profile_remote_preference_check CHECK ((remote_preference = ANY (ARRAY['required'::text, 'preferred'::text, 'acceptable'::text, 'not_wanted'::text])))
);


ALTER TABLE public.profiles OWNER TO base_admin;

--
-- Name: TABLE profiles; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.profiles IS 'User profiles for job matching. Versioned for historical tracking of skill development. 
   Each actor (human user) can have multiple profile versions over time.
   Links to skill_aliases for canonical skill references.';


--
-- Name: COLUMN profiles.profile_version; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.profile_version IS 'Version number for this profile. Higher versions = more recent. Allows tracking skill evolution over time.';


--
-- Name: COLUMN profiles.technical_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.technical_skills IS 'JSONB object: {"Python": 5, "SQL": 4, "Docker": 3}. Skill levels 1-5.';


--
-- Name: COLUMN profiles.soft_skills; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.soft_skills IS 'JSONB object: {"Communication": 5, "Leadership": 4}. Skill levels 1-5.';


--
-- Name: COLUMN profiles.languages; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.languages IS 'JSONB object: {"German": "C1", "English": "C2"}. CEFR levels.';


--
-- Name: COLUMN profiles.actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.profiles.actor_id IS 'Which actor owns this profile. References actors table (typically human actors).';


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
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
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
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.schema_documentation OWNER TO base_admin;

--
-- Name: TABLE schema_documentation; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.schema_documentation IS 'Supplemental documentation for schema fields. PostgreSQL COMMENT is primary, this provides examples and additional context.';


--
-- Name: session_actors; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.session_actors (
    session_actor_id integer NOT NULL,
    session_id integer NOT NULL,
    actor_id text NOT NULL,
    actor_role text NOT NULL,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT session_actors_actor_role_check CHECK ((actor_role = ANY (ARRAY['primary'::text, 'helper'::text, 'validator'::text])))
);


ALTER TABLE public.session_actors OWNER TO base_admin;

--
-- Name: TABLE session_actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.session_actors IS 'Many-to-many relationship: sessions can use multiple actors.
   - Primary actor: executes the session instructions
   - Helper actors: provide services (like skill_gopher for hierarchy building)
   - Validator actors: check output quality
   
   Usage: Session executor looks up available helpers and injects their URLs
   into instruction context as {{ACTOR_NAME_URL}} variables.';


--
-- Name: COLUMN session_actors.actor_role; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_actors.actor_role IS 'Role of this actor in the session:
   - primary: Executes session instructions (one per session, required)
   - helper: Called via API as needed (e.g., skill_gopher, translators)
   - validator: Checks output quality (e.g., schema validators, quality checkers)';


--
-- Name: session_actors_session_actor_id_seq; Type: SEQUENCE; Schema: public; Owner: base_admin
--

CREATE SEQUENCE public.session_actors_session_actor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.session_actors_session_actor_id_seq OWNER TO base_admin;

--
-- Name: session_actors_session_actor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: base_admin
--

ALTER SEQUENCE public.session_actors_session_actor_id_seq OWNED BY public.session_actors.session_actor_id;


--
-- Name: session_runs; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.session_runs (
    session_run_id integer NOT NULL,
    recipe_run_id integer,
    production_run_id integer,
    session_id integer NOT NULL,
    recipe_session_id integer NOT NULL,
    session_number integer NOT NULL,
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp without time zone,
    status text DEFAULT 'PENDING'::text,
    llm_conversation_id text,
    quality_score text,
    validation_status text,
    error_details text,
    CONSTRAINT session_runs_check CHECK ((((recipe_run_id IS NOT NULL) AND (production_run_id IS NULL)) OR ((recipe_run_id IS NULL) AND (production_run_id IS NOT NULL)))),
    CONSTRAINT session_runs_quality_score_check CHECK ((quality_score = ANY (ARRAY['A'::text, 'B'::text, 'C'::text, 'D'::text, 'F'::text, NULL::text]))),
    CONSTRAINT session_runs_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCESS'::text, 'FAILED'::text, 'TIMEOUT'::text, 'ERROR'::text]))),
    CONSTRAINT session_runs_validation_status_check CHECK ((validation_status = ANY (ARRAY['PASS'::text, 'FAIL'::text, NULL::text])))
);


ALTER TABLE public.session_runs OWNER TO base_admin;

--
-- Name: TABLE session_runs; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.session_runs IS 'Session-level execution tracking. SHARED by both testing (recipe_runs) and production (production_runs). This is the KEY to unified QA!';


--
-- Name: COLUMN session_runs.recipe_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.recipe_run_id IS 'If this is a TEST run, links to recipe_runs (using variation data)';


--
-- Name: COLUMN session_runs.production_run_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.production_run_id IS 'If this is a PRODUCTION run, links to production_runs (using posting data)';


--
-- Name: COLUMN session_runs.quality_score; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.quality_score IS 'Academic grading: A (excellent), B (good), C (acceptable), D (poor), F (failed)';


--
-- Name: COLUMN session_runs.validation_status; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.session_runs.validation_status IS 'Pass/fail validation: PASS (met requirements), FAIL (did not meet requirements)';


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
-- Name: sessions; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.sessions (
    session_id integer NOT NULL,
    canonical_code text NOT NULL,
    session_name text NOT NULL,
    session_description text,
    actor_id text NOT NULL,
    context_strategy text DEFAULT 'isolated'::text,
    max_instruction_runs integer DEFAULT 50,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT sessions_context_strategy_check CHECK ((context_strategy = ANY (ARRAY['isolated'::text, 'inherit_previous'::text, 'shared_conversation'::text])))
);


ALTER TABLE public.sessions OWNER TO base_admin;

--
-- Name: TABLE sessions; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.sessions IS 'Complete interaction templates that execute one canonical capability. Reusable across multiple recipes. Session = atomic testable unit.';


--
-- Name: COLUMN sessions.canonical_code; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.canonical_code IS 'Which canonical capability does this session implement? Links session to facet taxonomy.';


--
-- Name: COLUMN sessions.actor_id; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.sessions.actor_id IS 'Which actor (human/AI/script) executes this session?';


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
-- Name: skill_aliases; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_aliases (
    skill_alias text NOT NULL,
    skill text NOT NULL,
    display_name text,
    language text DEFAULT 'en'::text,
    confidence numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text
);


ALTER TABLE public.skill_aliases OWNER TO base_admin;

--
-- Name: TABLE skill_aliases; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_aliases IS 'Maps all skill variations to canonical form. Includes self-references for canonical skills.';


--
-- Name: COLUMN skill_aliases.skill_alias; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill_alias IS 'Any variation: lowercase, uppercase, hyphenated, translated, etc.';


--
-- Name: COLUMN skill_aliases.skill; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.skill IS 'Canonical skill name (lowercase normalized). Used as FK everywhere.';


--
-- Name: COLUMN skill_aliases.display_name; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON COLUMN public.skill_aliases.display_name IS 'Pretty format for UI display (e.g., "Python", "SQLite", "iShares")';


--
-- Name: skill_hierarchy; Type: TABLE; Schema: public; Owner: base_admin
--

CREATE TABLE public.skill_hierarchy (
    skill text NOT NULL,
    parent_skill text NOT NULL,
    strength numeric(3,2) DEFAULT 1.0,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    CONSTRAINT skill_hierarchy_check CHECK ((skill <> parent_skill))
);


ALTER TABLE public.skill_hierarchy OWNER TO base_admin;

--
-- Name: TABLE skill_hierarchy; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_hierarchy IS 'Parent-child taxonomy. Supports unlimited depth via recursive queries.';


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
    skill text NOT NULL,
    skill_alias text,
    confidence numeric(3,2) DEFAULT 1.0,
    context text,
    extraction_method text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.skill_occurrences OWNER TO base_admin;

--
-- Name: TABLE skill_occurrences; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_occurrences IS 'Tracks every mention of a skill in any source (CV, job, profile).';


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
    subject_skill text NOT NULL,
    relationship_type text NOT NULL,
    object_skill text NOT NULL,
    strength numeric(3,2) DEFAULT 1.0,
    source text,
    created_at timestamp without time zone DEFAULT now(),
    created_by text,
    notes text,
    CONSTRAINT skill_relationships_check CHECK ((subject_skill <> object_skill)),
    CONSTRAINT skill_relationships_relationship_type_check CHECK ((relationship_type = ANY (ARRAY['requires'::text, 'alternative_to'::text, 'obsoletes'::text])))
);


ALTER TABLE public.skill_relationships OWNER TO base_admin;

--
-- Name: TABLE skill_relationships; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON TABLE public.skill_relationships IS 'Targeted semantic relationships. Start with 3 types, expand only if proven valuable.';


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

COMMENT ON TABLE public.skill_synonyms IS 'Synonym mapping for fuzzy skill matching. Inspired by Gershon''s vendor invoice mapping: name_on_invoice → canonical_name. After 3-4 months of curation, achieves 90%+ automatic matching.';


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
-- Name: v_actor_delegation_stats; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_actor_delegation_stats AS
 SELECT a.actor_id,
    a.actor_type,
    a.execution_type,
    count(DISTINCT i.instruction_id) AS delegated_instruction_count,
    count(DISTINCT i.session_id) AS delegated_in_sessions,
    a.enabled
   FROM (public.actors a
     LEFT JOIN public.instructions i ON ((a.actor_id = i.delegate_actor_id)))
  GROUP BY a.actor_id, a.actor_type, a.execution_type, a.enabled
 HAVING (count(DISTINCT i.instruction_id) > 0)
  ORDER BY (count(DISTINCT i.instruction_id)) DESC;


ALTER TABLE public.v_actor_delegation_stats OWNER TO base_admin;

--
-- Name: VIEW v_actor_delegation_stats; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_actor_delegation_stats IS 'Statistics showing which actors are used for instruction delegation.
   Use to understand delegation patterns across recipes.';


--
-- Name: v_actor_usage; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_actor_usage AS
 SELECT a.actor_id,
    a.actor_type,
    a.execution_type,
    count(DISTINCT sa.session_id) AS session_count,
    count(DISTINCT sa.session_id) FILTER (WHERE (sa.actor_role = 'primary'::text)) AS primary_in_sessions,
    count(DISTINCT sa.session_id) FILTER (WHERE (sa.actor_role = 'helper'::text)) AS helper_in_sessions,
    count(DISTINCT sa.session_id) FILTER (WHERE (sa.actor_role = 'validator'::text)) AS validator_in_sessions,
    a.enabled
   FROM (public.actors a
     LEFT JOIN public.session_actors sa USING (actor_id))
  GROUP BY a.actor_id, a.actor_type, a.execution_type, a.enabled
  ORDER BY (count(DISTINCT sa.session_id)) DESC;


ALTER TABLE public.v_actor_usage OWNER TO base_admin;

--
-- Name: VIEW v_actor_usage; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_actor_usage IS 'Statistics showing how many sessions use each actor and in what roles.
   Use this to understand actor dependencies and usage patterns.';


--
-- Name: v_canonicals_orphaned; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_canonicals_orphaned AS
 SELECT c.canonical_code,
    c.facet_id,
    c.capability_description
   FROM public.canonicals c
  WHERE ((c.enabled = true) AND (NOT (EXISTS ( SELECT 1
           FROM public.sessions s
          WHERE ((s.canonical_code = c.canonical_code) AND (s.enabled = true))))))
  ORDER BY c.canonical_code;


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
    s.actor_id AS session_primary_actor,
    i.delegate_actor_id,
    COALESCE(i.delegate_actor_id, s.actor_id) AS effective_actor,
        CASE
            WHEN (i.delegate_actor_id IS NOT NULL) THEN 'delegated'::text
            ELSE 'primary'::text
        END AS execution_mode,
    a_primary.actor_type AS primary_actor_type,
    a_delegate.actor_type AS delegate_actor_type
   FROM (((public.instructions i
     JOIN public.sessions s ON ((i.session_id = s.session_id)))
     LEFT JOIN public.actors a_primary ON ((s.actor_id = a_primary.actor_id)))
     LEFT JOIN public.actors a_delegate ON ((i.delegate_actor_id = a_delegate.actor_id)))
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
-- Name: v_pending_synonyms; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_pending_synonyms AS
 SELECT skill_aliases.skill_alias,
    skill_aliases.skill,
    skill_aliases.language,
    skill_aliases.confidence,
    skill_aliases.created_at,
    skill_aliases.created_by,
    skill_aliases.notes
   FROM public.skill_aliases
  WHERE ((skill_aliases.confidence < 1.0) AND (skill_aliases.created_by ~~ 'llm:%'::text))
  ORDER BY skill_aliases.confidence DESC, skill_aliases.created_at DESC;


ALTER TABLE public.v_pending_synonyms OWNER TO base_admin;

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
    s.canonical_code,
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
     JOIN public.session_runs sr ON ((rr.recipe_run_id = sr.recipe_run_id)))
     JOIN public.sessions s ON ((sr.session_id = s.session_id)))
UNION ALL
 SELECT r.recipe_id,
    r.recipe_name,
    s.canonical_code,
    s.session_name,
    pr.posting_id AS input_id,
    'production'::text AS execution_mode,
    NULL::integer AS batch_id,
    sr.session_run_id,
    sr.started_at,
    sr.completed_at,
    sr.quality_score,
    sr.validation_status
   FROM ((((public.production_runs pr
     JOIN public.recipes r ON ((pr.recipe_id = r.recipe_id)))
     JOIN public.postings p ON ((pr.posting_id = p.job_id)))
     JOIN public.session_runs sr ON ((pr.production_run_id = sr.production_run_id)))
     JOIN public.sessions s ON ((sr.session_id = s.session_id)));


ALTER TABLE public.v_pipeline_execution OWNER TO base_admin;

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
    s.canonical_code,
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
    p.job_id,
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
     JOIN public.postings p ON ((p.job_id = pr.posting_id)))
     JOIN public.recipes r ON ((r.recipe_id = pr.recipe_id)))
     LEFT JOIN public.session_runs sr ON ((sr.production_run_id = pr.production_run_id)))
     LEFT JOIN public.instruction_runs ir ON ((ir.session_run_id = sr.session_run_id)))
  GROUP BY pr.production_run_id, p.job_id, p.job_title, p.organization_name, r.recipe_id, r.recipe_name, pr.status, pr.started_at, pr.completed_at
  ORDER BY pr.started_at DESC;


ALTER TABLE public.v_production_qa OWNER TO base_admin;

--
-- Name: VIEW v_production_qa; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_production_qa IS 'Production quality monitoring. Shows production run success/failure rates. Alert on failures to create new test variations!';


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
    c.canonical_code,
    c.capability_description AS what_it_does,
    a.actor_id,
    a.actor_type,
    rs.execute_condition,
    rs.on_success_action,
    rs.on_failure_action,
    rs.max_retry_attempts,
    count(i.instruction_id) AS instruction_count
   FROM (((((public.recipes r
     JOIN public.recipe_sessions rs ON ((rs.recipe_id = r.recipe_id)))
     JOIN public.sessions s ON ((s.session_id = rs.session_id)))
     JOIN public.canonicals c ON ((c.canonical_code = s.canonical_code)))
     JOIN public.actors a ON ((a.actor_id = s.actor_id)))
     LEFT JOIN public.instructions i ON ((i.session_id = s.session_id)))
  GROUP BY r.recipe_id, r.recipe_name, r.recipe_version, r.enabled, rs.recipe_session_id, rs.execution_order, s.session_id, s.session_name, c.canonical_code, c.capability_description, a.actor_id, a.actor_type, rs.execute_condition, rs.on_success_action, rs.on_failure_action, rs.max_retry_attempts
  ORDER BY r.recipe_id, rs.execution_order;


ALTER TABLE public.v_recipe_orchestration OWNER TO base_admin;

--
-- Name: VIEW v_recipe_orchestration; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_recipe_orchestration IS 'Shows how recipes combine sessions. Use for Orchestrate View in GUI. Shows multi-phase workflow composition.';


--
-- Name: v_session_actors; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_session_actors AS
 SELECT s.session_id,
    s.canonical_code,
    s.session_name,
    s.actor_id AS primary_actor_id,
    sa.actor_id AS all_actor_ids,
    sa.actor_role,
    a.actor_type,
    a.execution_type,
    a.url,
    sa.enabled
   FROM ((public.sessions s
     LEFT JOIN public.session_actors sa USING (session_id))
     LEFT JOIN public.actors a ON ((sa.actor_id = a.actor_id)))
  ORDER BY s.session_id,
        CASE sa.actor_role
            WHEN 'primary'::text THEN 1
            WHEN 'helper'::text THEN 2
            WHEN 'validator'::text THEN 3
            ELSE NULL::integer
        END;


ALTER TABLE public.v_session_actors OWNER TO base_admin;

--
-- Name: VIEW v_session_actors; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_session_actors IS 'Shows all actors associated with each session, ordered by role.
   Use this to see which sessions use which helpers.';


--
-- Name: v_skill_summary; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_skill_summary AS
 SELECT sa.skill,
    sa.display_name,
    count(DISTINCT sa2.skill_alias) AS alias_count,
    count(DISTINCT h.parent_skill) AS parent_count,
    count(DISTINCT r.object_skill) AS relationship_count,
    count(DISTINCT so.occurrence_id) AS mention_count
   FROM ((((public.skill_aliases sa
     LEFT JOIN public.skill_aliases sa2 ON ((sa.skill = sa2.skill)))
     LEFT JOIN public.skill_hierarchy h ON ((sa.skill = h.skill)))
     LEFT JOIN public.skill_relationships r ON ((sa.skill = r.subject_skill)))
     LEFT JOIN public.skill_occurrences so ON ((sa.skill = so.skill)))
  GROUP BY sa.skill, sa.display_name
  ORDER BY (count(DISTINCT so.occurrence_id)) DESC;


ALTER TABLE public.v_skill_summary OWNER TO base_admin;

--
-- Name: VIEW v_skill_summary; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_skill_summary IS 'Aggregate stats: aliases, parents, relationships, mentions per skill.';


--
-- Name: v_skill_tree; Type: VIEW; Schema: public; Owner: base_admin
--

CREATE VIEW public.v_skill_tree AS
 WITH RECURSIVE tree AS (
         SELECT skill_hierarchy.skill,
            skill_hierarchy.parent_skill,
            1 AS level,
            skill_hierarchy.skill AS path,
            ARRAY[skill_hierarchy.skill] AS ancestors
           FROM public.skill_hierarchy
        UNION ALL
         SELECT t.skill,
            h.parent_skill,
            (t.level + 1),
            ((t.path || ' → '::text) || h.parent_skill),
            (t.ancestors || h.parent_skill)
           FROM (tree t
             JOIN public.skill_hierarchy h ON ((t.parent_skill = h.skill)))
          WHERE (NOT (h.parent_skill = ANY (t.ancestors)))
        )
 SELECT tree.skill,
    tree.parent_skill,
    tree.level,
    tree.path,
    tree.ancestors
   FROM tree
  ORDER BY tree.skill, tree.level;


ALTER TABLE public.v_skill_tree OWNER TO base_admin;

--
-- Name: VIEW v_skill_tree; Type: COMMENT; Schema: public; Owner: base_admin
--

COMMENT ON VIEW public.v_skill_tree IS 'Recursive view showing full ancestry path for each skill.';


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
-- Name: profile_skills profile_skill_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profile_skills ALTER COLUMN profile_skill_id SET DEFAULT nextval('public.profile_skills_profile_skill_id_seq'::regclass);


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
-- Name: session_actors session_actor_id; Type: DEFAULT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_actors ALTER COLUMN session_actor_id SET DEFAULT nextval('public.session_actors_session_actor_id_seq'::regclass);


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
-- Name: canonicals_history canonicals_history_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals_history
    ADD CONSTRAINT canonicals_history_pkey PRIMARY KEY (history_id);


--
-- Name: canonicals canonicals_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals
    ADD CONSTRAINT canonicals_pkey PRIMARY KEY (canonical_code);


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
-- Name: profiles gershon_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT gershon_profile_pkey PRIMARY KEY (profile_version);


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
    ADD CONSTRAINT job_skills_job_id_skill_id_key UNIQUE (job_id, skill_id);


--
-- Name: job_skills job_skills_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_pkey PRIMARY KEY (job_skill_id);


--
-- Name: postings postings_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.postings
    ADD CONSTRAINT postings_pkey PRIMARY KEY (job_id);


--
-- Name: production_runs production_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_pkey PRIMARY KEY (production_run_id);


--
-- Name: production_runs production_runs_recipe_id_posting_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_recipe_id_posting_id_key UNIQUE (recipe_id, posting_id);


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
    ADD CONSTRAINT schema_documentation_pkey PRIMARY KEY (table_name, column_name);


--
-- Name: session_actors session_actors_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_actors
    ADD CONSTRAINT session_actors_pkey PRIMARY KEY (session_actor_id);


--
-- Name: session_actors session_actors_session_id_actor_id_key; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_actors
    ADD CONSTRAINT session_actors_session_id_actor_id_key UNIQUE (session_id, actor_id);


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
    ADD CONSTRAINT skill_aliases_pkey PRIMARY KEY (skill_alias);


--
-- Name: skill_hierarchy skill_hierarchy_pkey; Type: CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_pkey PRIMARY KEY (skill, parent_skill);


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
    ADD CONSTRAINT skill_relationships_pkey PRIMARY KEY (subject_skill, relationship_type, object_skill);


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

CREATE INDEX idx_canonicals_facet ON public.canonicals USING btree (facet_id);


--
-- Name: idx_facets_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_facets_enabled ON public.facets USING btree (enabled);


--
-- Name: idx_facets_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_facets_parent ON public.facets USING btree (parent_id);


--
-- Name: idx_human_tasks_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_human_tasks_actor ON public.human_tasks USING btree (actor_id, status);


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

CREATE INDEX idx_instructions_delegate_actor ON public.instructions USING btree (delegate_actor_id) WHERE (delegate_actor_id IS NOT NULL);


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

CREATE INDEX idx_job_skills_job ON public.job_skills USING btree (job_id);


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
-- Name: idx_production_runs_posting; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_production_runs_posting ON public.production_runs USING btree (posting_id);


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
-- Name: idx_profiles_actor_version; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_profiles_actor_version ON public.profiles USING btree (actor_id, profile_version);


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
-- Name: idx_recipes_enabled; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipes_enabled ON public.recipes USING btree (enabled);


--
-- Name: idx_recipes_name; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_recipes_name ON public.recipes USING btree (recipe_name);


--
-- Name: idx_session_actors_actor; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_actors_actor ON public.session_actors USING btree (actor_id);


--
-- Name: idx_session_actors_role; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_actors_role ON public.session_actors USING btree (actor_role) WHERE (enabled = true);


--
-- Name: idx_session_actors_session; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_actors_session ON public.session_actors USING btree (session_id);


--
-- Name: idx_session_one_primary; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_session_one_primary ON public.session_actors USING btree (session_id) WHERE (actor_role = 'primary'::text);


--
-- Name: idx_session_runs_production_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_runs_production_run ON public.session_runs USING btree (production_run_id);


--
-- Name: idx_session_runs_recipe_run; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_session_runs_recipe_run ON public.session_runs USING btree (recipe_run_id);


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

CREATE INDEX idx_sessions_actor ON public.sessions USING btree (actor_id);


--
-- Name: idx_sessions_canonical; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_sessions_canonical ON public.sessions USING btree (canonical_code);


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

CREATE INDEX idx_skill_aliases_skill ON public.skill_aliases USING btree (skill);


--
-- Name: idx_skill_aliases_skill_unique; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX idx_skill_aliases_skill_unique ON public.skill_aliases USING btree (skill);


--
-- Name: idx_skill_hierarchy_parent; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_hierarchy_parent ON public.skill_hierarchy USING btree (parent_skill);


--
-- Name: idx_skill_hierarchy_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_hierarchy_skill ON public.skill_hierarchy USING btree (skill);


--
-- Name: idx_skill_occ_created; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_created ON public.skill_occurrences USING btree (created_at);


--
-- Name: idx_skill_occ_skill; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_skill ON public.skill_occurrences USING btree (skill);


--
-- Name: idx_skill_occ_source; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_occ_source ON public.skill_occurrences USING btree (skill_source, source_id);


--
-- Name: idx_skill_rel_object; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_rel_object ON public.skill_relationships USING btree (object_skill);


--
-- Name: idx_skill_rel_subject; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_rel_subject ON public.skill_relationships USING btree (subject_skill);


--
-- Name: idx_skill_rel_type; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE INDEX idx_skill_rel_type ON public.skill_relationships USING btree (relationship_type);


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
-- Name: recipe_runs_unique_success_batch; Type: INDEX; Schema: public; Owner: base_admin
--

CREATE UNIQUE INDEX recipe_runs_unique_success_batch ON public.recipe_runs USING btree (recipe_id, variation_id, batch_id, execution_mode) WHERE (status = 'SUCCESS'::text);


--
-- Name: canonicals canonicals_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER canonicals_history_trigger BEFORE UPDATE ON public.canonicals FOR EACH ROW EXECUTE FUNCTION public.archive_canonicals();


--
-- Name: facets facets_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER facets_history_trigger BEFORE UPDATE ON public.facets FOR EACH ROW EXECUTE FUNCTION public.archive_facets();


--
-- Name: instructions instructions_history_trigger; Type: TRIGGER; Schema: public; Owner: base_admin
--

CREATE TRIGGER instructions_history_trigger BEFORE UPDATE ON public.instructions FOR EACH ROW EXECUTE FUNCTION public.archive_instructions();


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
-- Name: canonicals canonicals_facet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.canonicals
    ADD CONSTRAINT canonicals_facet_id_fkey FOREIGN KEY (facet_id) REFERENCES public.facets(facet_id);


--
-- Name: facets facets_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.facets
    ADD CONSTRAINT facets_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.facets(facet_id);


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
    ADD CONSTRAINT human_tasks_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


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
    ADD CONSTRAINT instructions_delegate_actor_id_fkey FOREIGN KEY (delegate_actor_id) REFERENCES public.actors(actor_id);


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
-- Name: job_skills job_skills_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.postings(job_id);


--
-- Name: job_skills job_skills_recipe_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.job_skills
    ADD CONSTRAINT job_skills_recipe_run_id_fkey FOREIGN KEY (recipe_run_id) REFERENCES public.recipe_runs(recipe_run_id);


--
-- Name: production_runs production_runs_posting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_posting_id_fkey FOREIGN KEY (posting_id) REFERENCES public.postings(job_id);


--
-- Name: production_runs production_runs_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.production_runs
    ADD CONSTRAINT production_runs_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.recipes(recipe_id);


--
-- Name: profiles profiles_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


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
-- Name: session_actors session_actors_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_actors
    ADD CONSTRAINT session_actors_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id) ON DELETE CASCADE;


--
-- Name: session_actors session_actors_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_actors
    ADD CONSTRAINT session_actors_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(session_id) ON DELETE CASCADE;


--
-- Name: session_runs session_runs_production_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs
    ADD CONSTRAINT session_runs_production_run_id_fkey FOREIGN KEY (production_run_id) REFERENCES public.production_runs(production_run_id);


--
-- Name: session_runs session_runs_recipe_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.session_runs
    ADD CONSTRAINT session_runs_recipe_run_id_fkey FOREIGN KEY (recipe_run_id) REFERENCES public.recipe_runs(recipe_run_id);


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
    ADD CONSTRAINT sessions_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.actors(actor_id);


--
-- Name: sessions sessions_canonical_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_canonical_code_fkey FOREIGN KEY (canonical_code) REFERENCES public.canonicals(canonical_code);


--
-- Name: skill_hierarchy skill_hierarchy_parent_skill_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_parent_skill_fkey FOREIGN KEY (parent_skill) REFERENCES public.skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_hierarchy skill_hierarchy_skill_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_hierarchy
    ADD CONSTRAINT skill_hierarchy_skill_fkey FOREIGN KEY (skill) REFERENCES public.skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_occurrences skill_occurrences_skill_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_occurrences
    ADD CONSTRAINT skill_occurrences_skill_fkey FOREIGN KEY (skill) REFERENCES public.skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_relationships skill_relationships_object_skill_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_relationships
    ADD CONSTRAINT skill_relationships_object_skill_fkey FOREIGN KEY (object_skill) REFERENCES public.skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: skill_relationships skill_relationships_subject_skill_fkey; Type: FK CONSTRAINT; Schema: public; Owner: base_admin
--

ALTER TABLE ONLY public.skill_relationships
    ADD CONSTRAINT skill_relationships_subject_skill_fkey FOREIGN KEY (subject_skill) REFERENCES public.skill_aliases(skill) ON UPDATE CASCADE ON DELETE CASCADE;


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

\unrestrict t3sglj8BEl36ni1x5MCfc5gcbnG0VkYKdRK1MDvMtnzkSjdXJ3lgwhAZmLCQEHF

