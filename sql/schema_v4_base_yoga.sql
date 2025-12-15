-- =====================================================
-- base.yoga Database Schema v4.0
-- PostgreSQL Migration from SQLite llmcore.db
-- =====================================================
-- Date: October 24, 2025
-- Authors: Gershon (xai), Arden
-- Database: base_yoga
-- Purpose: Universal foundation for talent.yoga and all yoga projects
-- =====================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- DESIGN LAYER: Capability Definition
-- =====================================================

-- -----------------------------------------------------
-- Table: facets
-- Purpose: Universal taxonomy of cognitive capabilities
-- -----------------------------------------------------
CREATE TABLE facets (
    facet_id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES facets(facet_id),
    short_description TEXT,
    remarks TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_facets_parent ON facets(parent_id);
CREATE INDEX idx_facets_enabled ON facets(enabled);

COMMENT ON TABLE facets IS 
'Universal taxonomy of cognitive capabilities for any responsive system (human, AI, script). Foundation of base.yoga systematic testing framework.';

COMMENT ON COLUMN facets.facet_id IS 
'Hierarchical ID (e.g., c_clean, ce_extract, ce_char_extract). Root facets: k, l, f, p, c, g, m, r, o';

COMMENT ON COLUMN facets.parent_id IS 
'Parent facet for hierarchical organization (NULL for root facets)';

-- -----------------------------------------------------
-- Table: canonicals
-- Purpose: Gold-standard test definitions
-- -----------------------------------------------------
CREATE TABLE canonicals (
    canonical_code TEXT PRIMARY KEY,
    facet_id TEXT NOT NULL REFERENCES facets(facet_id),
    capability_description TEXT,
    prompt TEXT,
    response TEXT NOT NULL,
    review_notes TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_canonicals_facet ON canonicals(facet_id);
CREATE INDEX idx_canonicals_enabled ON canonicals(enabled);

COMMENT ON TABLE canonicals IS 
'Gold-standard test definitions manually validated by domain experts. Each canonical represents one atomic capability.';

COMMENT ON COLUMN canonicals.canonical_code IS 
'Unique identifier for this test case (e.g., summarize_job_posting_v1)';

COMMENT ON COLUMN canonicals.prompt IS 
'Master prompt template (optional - may be defined at session/instruction level)';

COMMENT ON COLUMN canonicals.response IS 
'Expected correct response for validation';

-- -----------------------------------------------------
-- Table: actors
-- Purpose: Unified interface for execution entities
-- -----------------------------------------------------
CREATE TABLE actors (
    actor_id TEXT PRIMARY KEY,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'ai_model', 'script')),
    url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_actors_type ON actors(actor_type);
CREATE INDEX idx_actors_enabled ON actors(enabled);

COMMENT ON TABLE actors IS 
'Unified interface for execution entities: humans, AI models, or scripts. Enables human-in-the-loop workflows.';

COMMENT ON COLUMN actors.actor_type IS 
'Type of actor: human (human operator), ai_model (LLM), script (automated validator)';

COMMENT ON COLUMN actors.url IS 
'Connection string. AI models: ollama://model:tag, Humans: mailto:email or cli://username, Scripts: file:///path';

-- -----------------------------------------------------
-- Table: sessions
-- Purpose: Complete interaction templates (reusable)
-- -----------------------------------------------------
CREATE TABLE sessions (
    session_id SERIAL PRIMARY KEY,
    canonical_code TEXT NOT NULL REFERENCES canonicals(canonical_code),
    session_name TEXT NOT NULL,
    session_description TEXT,
    actor_id TEXT NOT NULL REFERENCES actors(actor_id),
    context_strategy TEXT DEFAULT 'isolated' 
        CHECK (context_strategy IN ('isolated', 'inherit_previous', 'shared_conversation')),
    max_instruction_runs INTEGER DEFAULT 50,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_canonical ON sessions(canonical_code);
CREATE INDEX idx_sessions_actor ON sessions(actor_id);
CREATE INDEX idx_sessions_enabled ON sessions(enabled);

COMMENT ON TABLE sessions IS 
'Complete interaction templates that execute one canonical capability. Reusable across multiple recipes. Session = atomic testable unit.';

COMMENT ON COLUMN sessions.canonical_code IS 
'Which canonical capability does this session implement? Links session to facet taxonomy.';

COMMENT ON COLUMN sessions.actor_id IS 
'Which actor (human/AI/script) executes this session?';

COMMENT ON COLUMN sessions.context_strategy IS 
'How to manage conversation context: isolated (fresh), inherit_previous (from prior session), shared_conversation (persistent)';

COMMENT ON COLUMN sessions.max_instruction_runs IS 
'Maximum instruction executions allowed in this session (prevents infinite loops). Budget per session.';

-- -----------------------------------------------------
-- Table: instructions
-- Purpose: Step-by-step prompts within sessions
-- -----------------------------------------------------
CREATE TABLE instructions (
    instruction_id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    step_number INTEGER NOT NULL,
    step_description TEXT,
    prompt_template TEXT NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,
    expected_pattern TEXT,
    validation_rules TEXT,
    is_terminal BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (session_id, step_number)
);

CREATE INDEX idx_instructions_session ON instructions(session_id);
CREATE INDEX idx_instructions_enabled ON instructions(enabled);

COMMENT ON TABLE instructions IS 
'Step-by-step prompts within a session. Instructions execute sequentially unless branching logic redirects.';

COMMENT ON COLUMN instructions.prompt_template IS 
'Prompt template with variable substitution. Variables: {test_data.field}, {posting.field}, {step1_response}, etc.';

COMMENT ON COLUMN instructions.is_terminal IS 
'If TRUE, this instruction ends the session (no next step)';

-- -----------------------------------------------------
-- Table: instruction_branches
-- Purpose: Conditional routing for intelligent workflows
-- -----------------------------------------------------
CREATE TABLE instruction_branches (
    branch_id SERIAL PRIMARY KEY,
    instruction_id INTEGER NOT NULL REFERENCES instructions(instruction_id),
    branch_condition TEXT,
    next_step_id INTEGER REFERENCES instructions(instruction_id),
    branch_priority INTEGER DEFAULT 1,
    condition_type TEXT CHECK (condition_type IN ('pattern_match', 'length_check', 'ai_evaluation', 'always')),
    condition_operator TEXT CHECK (condition_operator IN ('contains', 'equals', 'greater_than', 'less_than', 'not_contains')),
    condition_value TEXT,
    branch_action TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instruction_branches_instruction ON instruction_branches(instruction_id);
CREATE INDEX idx_instruction_branches_next_step ON instruction_branches(next_step_id);

COMMENT ON TABLE instruction_branches IS 
'Conditional routing for self-correcting workflows. Enables error handling, retry mechanisms, and adaptive routing.';

-- =====================================================
-- ORCHESTRATION LAYER: Recipe Composition
-- =====================================================

-- -----------------------------------------------------
-- Table: recipes
-- Purpose: Multi-phase workflows orchestrating sessions
-- -----------------------------------------------------
CREATE TABLE recipes (
    recipe_id SERIAL PRIMARY KEY,
    recipe_name TEXT NOT NULL,
    recipe_description TEXT,
    recipe_version INTEGER DEFAULT 1,
    max_total_session_runs INTEGER DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    review_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (recipe_name, recipe_version)
);

CREATE INDEX idx_recipes_name ON recipes(recipe_name);
CREATE INDEX idx_recipes_enabled ON recipes(enabled);

COMMENT ON TABLE recipes IS 
'Multi-phase workflows orchestrating multiple sessions. Like a restaurant menu combining multiple courses (canonicals). Tested with variations, deployed with postings.';

COMMENT ON COLUMN recipes.recipe_name IS 
'Human-readable name (e.g., "Job Quality Pipeline", "Skill Extraction Workflow")';

COMMENT ON COLUMN recipes.max_total_session_runs IS 
'Maximum total session executions allowed across all recipe sessions (prevents infinite recipe loops). Recipe-level budget.';

-- -----------------------------------------------------
-- Table: recipe_sessions
-- Purpose: Junction table - which sessions in which recipes
-- -----------------------------------------------------
CREATE TABLE recipe_sessions (
    recipe_session_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id),
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    execution_order INTEGER NOT NULL,
    
    -- Conditional execution
    execute_condition TEXT DEFAULT 'always' 
        CHECK (execute_condition IN ('always', 'on_success', 'on_failure')),
    depends_on_recipe_session_id INTEGER REFERENCES recipe_sessions(recipe_session_id),
    
    -- Retry/loop control
    on_success_action TEXT DEFAULT 'continue' 
        CHECK (on_success_action IN ('continue', 'skip_to', 'stop')),
    on_failure_action TEXT DEFAULT 'stop' 
        CHECK (on_failure_action IN ('stop', 'retry', 'skip_to')),
    on_success_goto_order INTEGER,
    on_failure_goto_order INTEGER,
    max_retry_attempts INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (recipe_id, execution_order)
);

CREATE INDEX idx_recipe_sessions_recipe ON recipe_sessions(recipe_id);
CREATE INDEX idx_recipe_sessions_session ON recipe_sessions(session_id);
CREATE INDEX idx_recipe_sessions_order ON recipe_sessions(recipe_id, execution_order);

COMMENT ON TABLE recipe_sessions IS 
'Junction table defining which sessions belong to which recipes and in what order. Enables session reuse across recipes. One session can be used in many recipes!';

COMMENT ON COLUMN recipe_sessions.execution_order IS 
'Sequence number for this session within the recipe (1, 2, 3...). Defines execution order.';

COMMENT ON COLUMN recipe_sessions.execute_condition IS 
'When to execute: always (default), on_success (previous succeeded), on_failure (previous failed)';

COMMENT ON COLUMN recipe_sessions.on_success_action IS 
'What to do after success: continue (next session), skip_to (jump), stop (end recipe)';

COMMENT ON COLUMN recipe_sessions.on_failure_action IS 
'What to do after failure: stop (end), retry (run again), skip_to (jump to error handler)';

COMMENT ON COLUMN recipe_sessions.max_retry_attempts IS 
'Maximum times this session can be retried in this recipe (prevents infinite retry loops)';

-- =====================================================
-- TESTING DOMAIN: Synthetic Test Data
-- =====================================================

-- -----------------------------------------------------
-- Table: variations
-- Purpose: Test data for recipes across difficulty levels
-- -----------------------------------------------------
CREATE TABLE variations (
    variation_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    test_data JSONB NOT NULL,
    difficulty_level INTEGER DEFAULT 1,
    expected_response TEXT,
    response_format TEXT,
    complexity_score REAL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_variations_recipe ON variations(recipe_id);
CREATE INDEX idx_variations_difficulty ON variations(difficulty_level);
CREATE INDEX idx_variations_enabled ON variations(enabled);
CREATE INDEX idx_variations_test_data ON variations USING GIN (test_data);

COMMENT ON TABLE variations IS 
'Test data for recipes across difficulty levels. Each variation tests the same recipe with different inputs. Used in TESTING mode.';

COMMENT ON COLUMN variations.test_data IS 
'JSON object with test parameters. Schema varies by canonical. Example: {"job_description": "Senior Engineer role...", "max_words": 100}';

COMMENT ON COLUMN variations.difficulty_level IS 
'Progressive difficulty: 1 (trivial), 2 (easy), 3 (medium), 4 (hard), 5 (expert)';

-- Example queries:
-- Get variations with specific job title:
--   SELECT * FROM variations WHERE test_data->>'job_title' = 'Senior Engineer';
-- Get variations with salary range:
--   SELECT * FROM variations WHERE (test_data->>'min_salary')::int > 50000;

-- -----------------------------------------------------
-- Table: batches
-- Purpose: Group multiple executions for statistical analysis
-- -----------------------------------------------------
CREATE TABLE batches (
    batch_id SERIAL PRIMARY KEY,
    batch_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE batches IS 
'Groups multiple recipe executions for statistical analysis. Enables "run 5 times" scenarios for reliability testing.';

-- -----------------------------------------------------
-- Table: recipe_runs
-- Purpose: Test execution instances
-- -----------------------------------------------------
CREATE TABLE recipe_runs (
    recipe_run_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id),
    variation_id INTEGER NOT NULL REFERENCES variations(variation_id),
    batch_id INTEGER NOT NULL REFERENCES batches(batch_id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'RUNNING' CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL', 'ERROR')),
    total_sessions INTEGER CHECK (total_sessions > 0),
    completed_sessions INTEGER DEFAULT 0 CHECK (completed_sessions >= 0),
    error_details TEXT,
    
    UNIQUE (recipe_id, variation_id, batch_id)
);

CREATE INDEX idx_recipe_runs_recipe ON recipe_runs(recipe_id);
CREATE INDEX idx_recipe_runs_variation ON recipe_runs(variation_id);
CREATE INDEX idx_recipe_runs_batch ON recipe_runs(batch_id);
CREATE INDEX idx_recipe_runs_status ON recipe_runs(status);

COMMENT ON TABLE recipe_runs IS 
'Test execution instances. Links recipe + variation + batch. Used in TESTING mode with synthetic variations.';

-- =====================================================
-- PRODUCTION DOMAIN: Real Job Data
-- =====================================================

-- -----------------------------------------------------
-- Table: postings
-- Purpose: Real job postings from websites
-- -----------------------------------------------------
CREATE TABLE postings (
    job_id TEXT PRIMARY KEY,
    
    -- Metadata
    metadata_source TEXT,
    metadata_created_at TIMESTAMP,
    metadata_last_modified TIMESTAMP,
    metadata_status TEXT,
    metadata_processor TEXT,
    
    -- Job Content
    job_title TEXT,
    job_description TEXT,
    job_requirements JSONB,
    
    -- Location
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    location_remote_options BOOLEAN,
    
    -- Employment Details
    employment_type TEXT,
    employment_schedule TEXT,
    employment_career_level TEXT,
    employment_salary_range TEXT,
    employment_benefits JSONB,
    
    -- Organization
    organization_name TEXT,
    organization_division TEXT,
    organization_division_id INTEGER,
    
    -- Posting Details
    posting_publication_date DATE,
    posting_position_uri TEXT,
    posting_hiring_year TEXT,
    
    -- System
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE,
    
    -- Analysis (computed fields)
    skill_keywords JSONB,
    complexity_score REAL,
    processing_notes TEXT
);

CREATE INDEX idx_postings_organization ON postings(organization_name);
CREATE INDEX idx_postings_source ON postings(metadata_source);
CREATE INDEX idx_postings_enabled ON postings(enabled);
CREATE INDEX idx_postings_publication ON postings(posting_publication_date);
CREATE INDEX idx_postings_skills ON postings USING GIN (skill_keywords);
CREATE INDEX idx_postings_requirements ON postings USING GIN (job_requirements);

COMMENT ON TABLE postings IS 
'Real job postings scraped from websites (Deutsche Bank, Arbeitsagentur, etc.). Used in PRODUCTION mode as input to recipes.';

COMMENT ON COLUMN postings.job_id IS 
'Unique job identifier from source system (e.g., 15929 from job15929.json)';

COMMENT ON COLUMN postings.metadata_source IS 
'Data source: deutsche_bank, arbeitsagentur, company_website, etc.';

COMMENT ON COLUMN postings.job_requirements IS 
'JSONB array of requirements. Structured for analysis.';

COMMENT ON COLUMN postings.skill_keywords IS 
'Extracted skills for matching. Computed field populated by analysis recipes.';

-- -----------------------------------------------------
-- Table: gershon_profile
-- Purpose: User profile for job matching
-- -----------------------------------------------------
CREATE TABLE gershon_profile (
    profile_version INTEGER PRIMARY KEY,
    
    -- Skills
    technical_skills JSONB,
    soft_skills JSONB,
    languages JSONB,
    
    -- Preferences
    preferred_roles JSONB,
    min_salary INTEGER,
    max_commute_minutes INTEGER,
    remote_preference TEXT CHECK (remote_preference IN ('required', 'preferred', 'acceptable', 'not_wanted')),
    
    -- Current situation
    current_employer TEXT,
    available_from DATE,
    notice_period_days INTEGER,
    
    -- System
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE gershon_profile IS 
'User profile for job matching. Versioned for historical tracking of skill development. Currently for Gershon, expandable to multi-user for talent.yoga platform.';

COMMENT ON COLUMN gershon_profile.technical_skills IS 
'JSONB object: {"Python": 5, "SQL": 4, "Docker": 3}. Skill levels 1-5.';

COMMENT ON COLUMN gershon_profile.soft_skills IS 
'JSONB object: {"Communication": 5, "Leadership": 4}. Skill levels 1-5.';

COMMENT ON COLUMN gershon_profile.languages IS 
'JSONB object: {"German": "C1", "English": "C2"}. CEFR levels.';

-- -----------------------------------------------------
-- Table: production_runs
-- Purpose: Production recipe executions using postings
-- -----------------------------------------------------
CREATE TABLE production_runs (
    production_run_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id),
    posting_id INTEGER NOT NULL REFERENCES postings(posting_id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'RUNNING' CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL', 'ERROR')),
    total_sessions INTEGER CHECK (total_sessions > 0),
    completed_sessions INTEGER DEFAULT 0 CHECK (completed_sessions >= 0),
    error_details TEXT,
    
    UNIQUE (recipe_id, posting_id)
);

CREATE INDEX idx_production_runs_recipe ON production_runs(recipe_id);
CREATE INDEX idx_production_runs_posting ON production_runs(posting_id);
CREATE INDEX idx_production_runs_status ON production_runs(status);

COMMENT ON TABLE production_runs IS 
'Production execution of recipes using real job postings (not synthetic test variations). NO BATCHES - each posting processed once. Batches are TEST-ONLY concept!';

COMMENT ON COLUMN production_runs.posting_id IS 
'Real job posting from postings table (production input), vs variation_id (test input)';

-- -----------------------------------------------------
-- Table: job_nodes
-- Purpose: Skill graph nodes
-- -----------------------------------------------------
CREATE TABLE job_nodes (
    node_id SERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_nodes_category ON job_nodes(category);

COMMENT ON TABLE job_nodes IS 
'Skill graph nodes. Each node represents a skill extracted from job postings.';

-- -----------------------------------------------------
-- Table: job_skill_edges
-- Purpose: Skill co-occurrence relationships
-- -----------------------------------------------------
CREATE TABLE job_skill_edges (
    edge_id SERIAL PRIMARY KEY,
    source_node_id INTEGER NOT NULL REFERENCES job_nodes(node_id),
    target_node_id INTEGER NOT NULL REFERENCES job_nodes(node_id),
    weight INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (source_node_id, target_node_id)
);

CREATE INDEX idx_job_skill_edges_source ON job_skill_edges(source_node_id);
CREATE INDEX idx_job_skill_edges_target ON job_skill_edges(target_node_id);

COMMENT ON TABLE job_skill_edges IS 
'Skill co-occurrence relationships. Weight = how many jobs require both skills together.';

-- =====================================================
-- EXECUTION LAYER: Shared Runtime Tracking
-- (Used by BOTH testing and production!)
-- =====================================================

-- -----------------------------------------------------
-- Table: session_runs
-- Purpose: Session-level execution tracking (SHARED!)
-- -----------------------------------------------------
CREATE TABLE session_runs (
    session_run_id SERIAL PRIMARY KEY,
    
    -- EITHER test run OR production run (one will be NULL)
    recipe_run_id INTEGER REFERENCES recipe_runs(recipe_run_id),
    production_run_id INTEGER REFERENCES production_runs(production_run_id),
    
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    recipe_session_id INTEGER NOT NULL REFERENCES recipe_sessions(recipe_session_id),
    session_number INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'ERROR')),
    llm_conversation_id TEXT,
    quality_score TEXT CHECK (quality_score IN ('A', 'B', 'C', 'D', 'F', NULL)),
    validation_status TEXT CHECK (validation_status IN ('PASS', 'FAIL', NULL)),
    error_details TEXT,
    
    -- Exactly one must be set
    CHECK (
        (recipe_run_id IS NOT NULL AND production_run_id IS NULL) OR
        (recipe_run_id IS NULL AND production_run_id IS NOT NULL)
    )
);

CREATE INDEX idx_session_runs_recipe_run ON session_runs(recipe_run_id);
CREATE INDEX idx_session_runs_production_run ON session_runs(production_run_id);
CREATE INDEX idx_session_runs_session ON session_runs(session_id);
CREATE INDEX idx_session_runs_status ON session_runs(status);

COMMENT ON TABLE session_runs IS 
'Session-level execution tracking. SHARED by both testing (recipe_runs) and production (production_runs). This is the KEY to unified QA!';

COMMENT ON COLUMN session_runs.recipe_run_id IS 
'If this is a TEST run, links to recipe_runs (using variation data)';

COMMENT ON COLUMN session_runs.production_run_id IS 
'If this is a PRODUCTION run, links to production_runs (using posting data)';

COMMENT ON COLUMN session_runs.quality_score IS 
'Academic grading: A (excellent), B (good), C (acceptable), D (poor), F (failed)';

COMMENT ON COLUMN session_runs.validation_status IS 
'Pass/fail validation: PASS (met requirements), FAIL (did not meet requirements)';

-- -----------------------------------------------------
-- Table: instruction_runs
-- Purpose: Instruction-level execution tracking (SHARED!)
-- -----------------------------------------------------
CREATE TABLE instruction_runs (
    instruction_run_id SERIAL PRIMARY KEY,
    session_run_id INTEGER NOT NULL REFERENCES session_runs(session_run_id),
    instruction_id INTEGER NOT NULL REFERENCES instructions(instruction_id),
    step_number INTEGER NOT NULL,
    prompt_rendered TEXT,
    response_received TEXT,
    latency_ms INTEGER,
    error_details TEXT,
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'ERROR')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instruction_runs_session_run ON instruction_runs(session_run_id);
CREATE INDEX idx_instruction_runs_instruction ON instruction_runs(instruction_id);
CREATE INDEX idx_instruction_runs_status ON instruction_runs(status);

COMMENT ON TABLE instruction_runs IS 
'Individual instruction execution results. SHARED by both testing and production. Tracks what was sent, what was received, and performance metrics.';

COMMENT ON COLUMN instruction_runs.prompt_rendered IS 
'Actual prompt sent to actor after variable substitution. In test mode uses variation.test_data, in production uses posting fields.';

COMMENT ON COLUMN instruction_runs.latency_ms IS 
'Response time in milliseconds. Critical for performance comparison between test and production.';

-- -----------------------------------------------------
-- Table: instruction_branch_executions
-- Purpose: Branch decision audit trail (SHARED!)
-- -----------------------------------------------------
CREATE TABLE instruction_branch_executions (
    execution_id SERIAL PRIMARY KEY,
    instruction_run_id INTEGER NOT NULL REFERENCES instruction_runs(instruction_run_id),
    branch_id INTEGER NOT NULL REFERENCES instruction_branches(branch_id),
    condition_result TEXT,
    taken BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instruction_branch_executions_instruction_run ON instruction_branch_executions(instruction_run_id);
CREATE INDEX idx_instruction_branch_executions_branch ON instruction_branch_executions(branch_id);

COMMENT ON TABLE instruction_branch_executions IS 
'Complete workflow audit showing why specific routing decisions were made. SHARED by both testing and production.';

-- =====================================================
-- SUPPORT LAYER: Documentation & Utilities
-- =====================================================

-- -----------------------------------------------------
-- Table: schema_documentation
-- Purpose: Supplemental field documentation
-- -----------------------------------------------------
CREATE TABLE schema_documentation (
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    data_type TEXT,
    description TEXT NOT NULL,
    example_value TEXT,
    constraints TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (table_name, column_name)
);

COMMENT ON TABLE schema_documentation IS 
'Supplemental documentation for schema fields. PostgreSQL COMMENT is primary, this provides examples and additional context.';

-- Populate with key examples
INSERT INTO schema_documentation (table_name, column_name, data_type, description, example_value, constraints) VALUES
('variations', 'test_data', 'JSONB', 
 'JSON object containing test parameters. Structure varies by canonical.',
 '{"job_description": "Senior Engineer role at DB...", "max_words": 100}',
 'Must be valid JSON. Keys should match canonical requirements.'),
 
('recipe_sessions', 'execution_order', 'INTEGER',
 'Sequence number (1, 2, 3...) defining order of session execution within recipe',
 '1',
 'Must be unique within recipe_id. Gaps allowed (1, 2, 5, 10...).'),
 
('postings', 'job_requirements', 'JSONB',
 'Array of job requirements in structured format',
 '["5+ years Python", "SQL experience", "Team leadership"]',
 'JSONB array. Populated from job posting source.'),
 
('sessions', 'context_strategy', 'TEXT',
 'Conversation context management strategy',
 'isolated',
 'Values: isolated (fresh context), inherit_previous (carry forward), shared_conversation (persistent)');

-- =====================================================
-- VIEWS: Hierarchical Data Access
-- =====================================================

-- -----------------------------------------------------
-- View: v_design_hierarchy
-- Purpose: Complete capability hierarchy for Design View
-- -----------------------------------------------------
CREATE VIEW v_design_hierarchy AS
SELECT 
    f.facet_id,
    f.short_description as facet_description,
    f.enabled as facet_enabled,
    c.canonical_code,
    c.capability_description,
    c.enabled as canonical_enabled,
    s.session_id,
    s.session_name,
    s.actor_id,
    s.enabled as session_enabled,
    i.instruction_id,
    i.step_number,
    i.step_description,
    i.enabled as instruction_enabled,
    ib.branch_id,
    ib.branch_condition,
    ib.enabled as branch_enabled
FROM facets f
LEFT JOIN canonicals c ON c.facet_id = f.facet_id
LEFT JOIN sessions s ON s.canonical_code = c.canonical_code
LEFT JOIN instructions i ON i.session_id = s.session_id
LEFT JOIN instruction_branches ib ON ib.instruction_id = i.instruction_id
ORDER BY f.facet_id, c.canonical_code, s.session_id, i.step_number, ib.branch_priority;

COMMENT ON VIEW v_design_hierarchy IS 
'Complete capability hierarchy from facets down to instruction branches. Use for Design View in GUI. Shows what capabilities exist and how to test them.';

-- -----------------------------------------------------
-- View: v_recipe_orchestration
-- Purpose: Recipe composition for Orchestrate View
-- -----------------------------------------------------
CREATE VIEW v_recipe_orchestration AS
SELECT 
    r.recipe_id,
    r.recipe_name,
    r.recipe_version,
    r.enabled as recipe_enabled,
    rs.recipe_session_id,
    rs.execution_order,
    s.session_id,
    s.session_name,
    c.canonical_code,
    c.capability_description as what_it_does,
    a.actor_id,
    a.actor_type,
    rs.execute_condition,
    rs.on_success_action,
    rs.on_failure_action,
    rs.max_retry_attempts,
    COUNT(i.instruction_id) as instruction_count
FROM recipes r
JOIN recipe_sessions rs ON rs.recipe_id = r.recipe_id
JOIN sessions s ON s.session_id = rs.session_id
JOIN canonicals c ON c.canonical_code = s.canonical_code
JOIN actors a ON a.actor_id = s.actor_id
LEFT JOIN instructions i ON i.session_id = s.session_id
GROUP BY r.recipe_id, r.recipe_name, r.recipe_version, r.enabled,
         rs.recipe_session_id, rs.execution_order, 
         s.session_id, s.session_name, c.canonical_code, c.capability_description,
         a.actor_id, a.actor_type, rs.execute_condition, rs.on_success_action, 
         rs.on_failure_action, rs.max_retry_attempts
ORDER BY r.recipe_id, rs.execution_order;

COMMENT ON VIEW v_recipe_orchestration IS 
'Shows how recipes combine sessions. Use for Orchestrate View in GUI. Shows multi-phase workflow composition.';

-- -----------------------------------------------------
-- View: v_pipeline_execution
-- Purpose: Execution tracking for Pipeline View
-- -----------------------------------------------------
CREATE VIEW v_pipeline_execution AS
-- Test executions
SELECT 
    'TEST' as execution_mode,
    rr.recipe_run_id as run_id,
    rr.recipe_id,
    r.recipe_name,
    v.variation_id as input_id,
    v.difficulty_level,
    v.test_data as input_data,
    NULL::TEXT as posting_job_title,
    sr.session_run_id,
    sr.session_number,
    s.session_name,
    c.canonical_code,
    f.facet_id,
    sr.status as session_status,
    sr.quality_score,
    sr.validation_status,
    ir.instruction_run_id,
    ir.step_number,
    ir.status as instruction_status,
    ir.latency_ms,
    ir.created_at as executed_at
FROM recipe_runs rr
JOIN recipes r ON r.recipe_id = rr.recipe_id
JOIN variations v ON v.variation_id = rr.variation_id
JOIN session_runs sr ON sr.recipe_run_id = rr.recipe_run_id
JOIN sessions s ON s.session_id = sr.session_id
JOIN canonicals c ON c.canonical_code = s.canonical_code
JOIN facets f ON f.facet_id = c.facet_id
LEFT JOIN instruction_runs ir ON ir.session_run_id = sr.session_run_id

UNION ALL

-- Production executions
SELECT 
    'PRODUCTION' as execution_mode,
    pr.production_run_id as run_id,
    pr.recipe_id,
    r.recipe_name,
    pr.posting_id as input_id,
    NULL::INTEGER as difficulty_level,
    jsonb_build_object('job_id', p.job_id, 'job_title', p.job_title) as input_data,
    p.job_title as posting_job_title,
    sr.session_run_id,
    sr.session_number,
    s.session_name,
    c.canonical_code,
    f.facet_id,
    sr.status as session_status,
    sr.quality_score,
    sr.validation_status,
    ir.instruction_run_id,
    ir.step_number,
    ir.status as instruction_status,
    ir.latency_ms,
    ir.created_at as executed_at
FROM production_runs pr
JOIN recipes r ON r.recipe_id = pr.recipe_id
JOIN postings p ON p.job_id = pr.posting_id
JOIN session_runs sr ON sr.production_run_id = pr.production_run_id
JOIN sessions s ON s.session_id = sr.session_id
JOIN canonicals c ON c.canonical_code = s.canonical_code
JOIN facets f ON f.facet_id = c.facet_id
LEFT JOIN instruction_runs ir ON ir.session_run_id = sr.session_run_id

ORDER BY run_id, session_number, step_number;

COMMENT ON VIEW v_pipeline_execution IS 
'Complete execution trace with filtering by facet, recipe, session. UNIFIED view showing both test and production executions! Use for Pipeline View in GUI.';

-- -----------------------------------------------------
-- View: v_production_qa
-- Purpose: Production quality monitoring
-- -----------------------------------------------------
CREATE VIEW v_production_qa AS
SELECT 
    pr.production_run_id,
    p.job_id,
    p.job_title,
    p.organization_name,
    r.recipe_id,
    r.recipe_name,
    pr.status as run_status,
    pr.started_at,
    pr.completed_at,
    pr.completed_at - pr.started_at as total_duration,
    COUNT(sr.session_run_id) as session_count,
    SUM(CASE WHEN sr.validation_status = 'PASS' THEN 1 ELSE 0 END) as passed_sessions,
    SUM(CASE WHEN sr.validation_status = 'FAIL' THEN 1 ELSE 0 END) as failed_sessions,
    SUM(CASE WHEN sr.status = 'ERROR' THEN 1 ELSE 0 END) as error_sessions,
    AVG(ir.latency_ms) as avg_instruction_latency_ms
FROM production_runs pr
JOIN postings p ON p.job_id = pr.posting_id
JOIN recipes r ON r.recipe_id = pr.recipe_id
LEFT JOIN session_runs sr ON sr.production_run_id = pr.production_run_id
LEFT JOIN instruction_runs ir ON ir.session_run_id = sr.session_run_id
GROUP BY pr.production_run_id, p.job_id, p.job_title, p.organization_name,
         r.recipe_id, r.recipe_name, pr.status, pr.started_at, pr.completed_at
ORDER BY pr.started_at DESC;

COMMENT ON VIEW v_production_qa IS 
'Production quality monitoring. Shows production run success/failure rates. Alert on failures to create new test variations!';

-- =====================================================
-- HISTORY TRACKING: Automatic Audit Trail
-- =====================================================

-- Create history tables for key entities
-- (Pattern: Same structure as main table + history_id + archived_at + change_reason)

CREATE TABLE facets_history (
    history_id SERIAL PRIMARY KEY,
    facet_id TEXT NOT NULL,
    parent_id TEXT,
    short_description TEXT,
    remarks TEXT,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

CREATE TABLE canonicals_history (
    history_id SERIAL PRIMARY KEY,
    canonical_code TEXT NOT NULL,
    facet_id TEXT NOT NULL,
    capability_description TEXT,
    prompt TEXT,
    response TEXT,
    review_notes TEXT,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

CREATE TABLE sessions_history (
    history_id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    canonical_code TEXT NOT NULL,
    session_name TEXT,
    session_description TEXT,
    actor_id TEXT,
    context_strategy TEXT,
    max_instruction_runs INTEGER,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

CREATE TABLE recipes_history (
    history_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL,
    recipe_name TEXT,
    recipe_description TEXT,
    recipe_version INTEGER,
    max_total_session_runs INTEGER,
    enabled BOOLEAN,
    review_notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

CREATE TABLE instructions_history (
    history_id SERIAL PRIMARY KEY,
    instruction_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    step_number INTEGER,
    step_description TEXT,
    prompt_template TEXT,
    timeout_seconds INTEGER,
    expected_pattern TEXT,
    validation_rules TEXT,
    is_terminal BOOLEAN,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

CREATE TABLE variations_history (
    history_id SERIAL PRIMARY KEY,
    variation_id INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    test_data JSONB,
    difficulty_level INTEGER,
    expected_response TEXT,
    response_format TEXT,
    complexity_score REAL,
    enabled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Create triggers for automatic history tracking

CREATE OR REPLACE FUNCTION archive_facets() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER facets_history_trigger
BEFORE UPDATE ON facets
FOR EACH ROW
EXECUTE FUNCTION archive_facets();

-- Repeat pattern for other tables
CREATE OR REPLACE FUNCTION archive_canonicals() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER canonicals_history_trigger
BEFORE UPDATE ON canonicals
FOR EACH ROW
EXECUTE FUNCTION archive_canonicals();

CREATE OR REPLACE FUNCTION archive_sessions() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_history_trigger
BEFORE UPDATE ON sessions
FOR EACH ROW
EXECUTE FUNCTION archive_sessions();

CREATE OR REPLACE FUNCTION archive_recipes() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER recipes_history_trigger
BEFORE UPDATE ON recipes
FOR EACH ROW
EXECUTE FUNCTION archive_recipes();

CREATE OR REPLACE FUNCTION archive_instructions() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER instructions_history_trigger
BEFORE UPDATE ON instructions
FOR EACH ROW
EXECUTE FUNCTION archive_instructions();

CREATE OR REPLACE FUNCTION archive_variations() RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

CREATE TRIGGER variations_history_trigger
BEFORE UPDATE ON variations
FOR EACH ROW
EXECUTE FUNCTION archive_variations();

-- =====================================================
-- GRANTS: Set permissions
-- =====================================================

-- Grant all privileges to base_admin
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO base_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO base_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO base_admin;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '🎉 base.yoga schema v4.0 created successfully!';
    RAISE NOTICE '📊 Unified database ready for testing AND production';
    RAISE NOTICE '🔥 The foundation is lit! Let''s build talent.yoga!';
END $$;
