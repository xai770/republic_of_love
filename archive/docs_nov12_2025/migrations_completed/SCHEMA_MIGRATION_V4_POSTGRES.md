# base.yoga Schema v4.0 - PostgreSQL Migration Plan

**Date:** October 24, 2025  
**Authors:** Gershon (xai), Arden  
**Status:** DRAFT - Ready for execution

---

## Executive Summary

**What:** Migrate from SQLite (llmcore.db) to PostgreSQL (base.yoga) with comprehensive schema redesign  
**Why:** Built-in documentation, JSON support, production-ready foundation for talent.yoga and future projects  
**When:** NOW - During schema redesign phase  
**Risk:** LOW - Database backed up, fresh start opportunity

**Database Name:** `base_yoga` (underscore for PostgreSQL compatibility)  
**Project Name:** base.yoga (the universal foundation for all yoga projects)

---

## Key Changes

### 1. **Database Platform**
- ❌ SQLite → ✅ PostgreSQL 14+
- **Reason:** Native COMMENT support, better JSON, production-ready

### 2. **Canonical → Session Relationship**
- ❌ `canonicals → recipes → sessions`
- ✅ `canonicals → sessions` (session IS a canonical instance)
- ✅ `recipes → recipe_sessions → sessions` (orchestration)

### 3. **Timestamp Standardization**
- ❌ Mixed: `timestamp`, `updated_at`, `created_at`
- ✅ Consistent: `created_at`, `updated_at`, `started_at`, `completed_at`

### 4. **Variations Data**
- ❌ `variations_param_1/2/3` (generic, limited)
- ✅ `test_data JSONB` (flexible, self-documenting)

### 5. **Loop Control**
- ✅ Add `recipes.max_total_session_runs` (recipe-level budget)
- ✅ Add `sessions.max_instruction_runs` (session-level budget)
- ❌ Remove `recipes.max_instruction_cycles` (unclear naming)

### 6. **Context Management**
- ❌ Remove `sessions.maintain_llm_context` (redundant)
- ✅ Keep only `sessions.context_strategy`

### 7. **Instruction Scoring**
- ❌ Remove `instruction_runs.pass_fail/academic_score/value_add/rank_in_group`
- ✅ Add `session_runs.quality_score`, `session_runs.validation_status`

### 8. **Recipe-Session Junction**
- ✅ New table: `recipe_sessions` (many-to-many with execution logic)

---

## New Schema Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ UNIFIED DATABASE: base_yoga                                  │
│ The Universal Foundation for talent.yoga and all projects   │
│ Testing Domain + Production Domain in ONE Database          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ DESIGN LAYER - Capability Definition                        │
├─────────────────────────────────────────────────────────────┤
│ facets (taxonomy)                                           │
│   ↓                                                         │
│ canonicals (gold-standard tests)                            │
│   ↓                                                         │
│ sessions (complete interaction templates)                   │
│   ↓                                                         │
│ instructions (step-by-step prompts)                         │
│   ↓                                                         │
│ instruction_branches (conditional routing)                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATION LAYER - Recipe Composition                    │
├─────────────────────────────────────────────────────────────┤
│ recipes (multi-phase workflows)                             │
│   ↓                                                         │
│ recipe_sessions (junction table with execution order)       │
│   ↓                                                         │
│ sessions (reusable across recipes)                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TESTING DOMAIN - Synthetic Test Data                        │
├─────────────────────────────────────────────────────────────┤
│ variations (JSONB test data)                                │
│ recipe_runs (test executions)                               │
│   ↓                                                         │
│ session_runs (shared execution tracking)                    │
│   ↓                                                         │
│ instruction_runs (shared execution tracking)                │
│   ↓                                                         │
│ instruction_branch_executions (shared execution tracking)   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PRODUCTION DOMAIN - Real Job Data                           │
├─────────────────────────────────────────────────────────────┤
│ postings (real job postings from websites)                  │
│ gershon_profile (skills, preferences, history)              │
│ production_runs (production executions)                     │
│   ↓                                                         │
│ session_runs (SAME TABLE as testing!)                       │
│   ↓                                                         │
│ instruction_runs (SAME TABLE as testing!)                   │
│   ↓                                                         │
│ instruction_branch_executions (SAME TABLE as testing!)      │
│                                                              │
│ job_nodes, job_skill_edges (skill graph analysis)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SUPPORT LAYER - Shared Infrastructure                       │
├─────────────────────────────────────────────────────────────┤
│ actors (humans, AI models, scripts)                         │
│ batches (execution grouping)                                │
│ schema_documentation (field explanations)                   │
└─────────────────────────────────────────────────────────────┘

KEY INSIGHT: Same recipes tested with variations, deployed with postings!
             Continuous QA: Production failures → new test variations
```

---

## Table Changes Detail

### **facets** ✅ Minor changes
```sql
CREATE TABLE facets (
    facet_id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES facets(facet_id),
    short_description TEXT,
    remarks TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE facets IS 
'Universal taxonomy of cognitive capabilities for any responsive system (human, AI, script). Foundation of base.yoga systematic testing framework.';

COMMENT ON COLUMN facets.facet_id IS 
'Hierarchical ID (e.g., c_clean, ce_extract, ce_char_extract)';

COMMENT ON COLUMN facets.parent_id IS 
'Parent facet for hierarchical organization (NULL for root facets)';
```

**Changes:**
- ✅ `timestamp` → `created_at`
- ✅ Add `updated_at`
- ✅ `INTEGER` enabled → `BOOLEAN`
- ✅ Add COMMENT documentation

---

### **canonicals** ✅ Minor changes
```sql
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

COMMENT ON TABLE canonicals IS 
'Gold-standard test definitions manually validated by domain experts. Each canonical represents one atomic capability.';

COMMENT ON COLUMN canonicals.canonical_code IS 
'Unique identifier for this test case (e.g., summarize_job_posting_v1)';

COMMENT ON COLUMN canonicals.prompt IS 
'Master prompt template (optional - may be defined at session level)';

COMMENT ON COLUMN canonicals.response IS 
'Expected correct response for validation';
```

**Changes:**
- ✅ Keep `updated_at` (already exists)
- ✅ Add `created_at`
- ✅ Add COMMENT documentation

---

### **sessions** 🔥 MAJOR CHANGES
```sql
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

COMMENT ON TABLE sessions IS 
'Complete interaction templates that execute one canonical capability. Reusable across multiple recipes.';

COMMENT ON COLUMN sessions.canonical_code IS 
'Which canonical capability does this session implement? (NEW - migrated from recipes)';

COMMENT ON COLUMN sessions.actor_id IS 
'Which actor (human/AI/script) executes this session?';

COMMENT ON COLUMN sessions.context_strategy IS 
'How to manage conversation context: isolated (fresh), inherit_previous (from prior session), shared_conversation (persistent)';

COMMENT ON COLUMN sessions.max_instruction_runs IS 
'Maximum instruction executions allowed in this session (prevents infinite loops)';
```

**Changes:**
- 🔥 **BREAKING:** Add `canonical_code` (migrated from recipes)
- ❌ **REMOVE:** `recipe_id` (moved to recipe_sessions)
- ❌ **REMOVE:** `session_number` (moved to recipe_sessions.execution_order)
- ❌ **REMOVE:** `maintain_llm_context` (redundant with context_strategy)
- ❌ **REMOVE:** `execution_order` (moved to recipe_sessions)
- ❌ **REMOVE:** `depends_on_session_id` (handled by recipe_sessions)
- ✅ **ADD:** `max_instruction_runs` (loop budget)
- ✅ `created_at` already exists
- ✅ Add `updated_at`

---

### **recipe_sessions** 🆕 NEW TABLE
```sql
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
    
    UNIQUE (recipe_id, execution_order),
    FOREIGN KEY (recipe_id, on_success_goto_order) 
        REFERENCES recipe_sessions(recipe_id, execution_order) DEFERRABLE,
    FOREIGN KEY (recipe_id, on_failure_goto_order) 
        REFERENCES recipe_sessions(recipe_id, execution_order) DEFERRABLE
);

CREATE INDEX idx_recipe_sessions_recipe ON recipe_sessions(recipe_id);
CREATE INDEX idx_recipe_sessions_session ON recipe_sessions(session_id);
CREATE INDEX idx_recipe_sessions_order ON recipe_sessions(recipe_id, execution_order);

COMMENT ON TABLE recipe_sessions IS 
'Junction table defining which sessions belong to which recipes and in what order. Enables session reuse across recipes.';

COMMENT ON COLUMN recipe_sessions.execution_order IS 
'Sequence number for this session within the recipe (1, 2, 3...)';

COMMENT ON COLUMN recipe_sessions.execute_condition IS 
'When to execute: always (default), on_success (previous succeeded), on_failure (previous failed)';

COMMENT ON COLUMN recipe_sessions.on_success_action IS 
'What to do after success: continue (next session), skip_to (jump), stop (end recipe)';

COMMENT ON COLUMN recipe_sessions.on_failure_action IS 
'What to do after failure: stop (end), retry (run again), skip_to (jump to error handler)';

COMMENT ON COLUMN recipe_sessions.max_retry_attempts IS 
'Maximum times this session can be retried in this recipe (prevents infinite retry loops)';
```

**Purpose:** Enable session reuse, recipe-specific execution order, retry/jump logic

---

### **recipes** ✅ Simplified
```sql
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

COMMENT ON TABLE recipes IS 
'Multi-phase workflows orchestrating multiple sessions. Like a restaurant menu combining multiple courses (canonicals).';

COMMENT ON COLUMN recipes.recipe_name IS 
'Human-readable name (e.g., "Job Quality Pipeline")';

COMMENT ON COLUMN recipes.max_total_session_runs IS 
'Maximum total session executions allowed (prevents infinite recipe loops)';
```

**Changes:**
- ❌ **REMOVE:** `canonical_code` (moved to sessions)
- ❌ **REMOVE:** `max_instruction_cycles` (renamed/clarified)
- ✅ **ADD:** `recipe_name` (required!)
- ✅ **ADD:** `recipe_description`
- ✅ **ADD:** `max_total_session_runs` (recipe-level loop budget)
- ✅ `timestamp` → `created_at`, add `updated_at`

---

### **instructions** ✅ Minor changes
```sql
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

COMMENT ON TABLE instructions IS 
'Step-by-step prompts within a session. Instructions execute sequentially unless branching logic redirects.';

COMMENT ON COLUMN instructions.prompt_template IS 
'Prompt template with variable substitution: {variations_param_1}, {step1_response}, etc.';

COMMENT ON COLUMN instructions.is_terminal IS 
'If TRUE, this instruction ends the session (no next step)';
```

**Changes:**
- ✅ Add `updated_at`
- ✅ Add COMMENT documentation

---

### **variations** 🔥 MAJOR CHANGES
```sql
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
CREATE INDEX idx_variations_test_data ON variations USING GIN (test_data);

COMMENT ON TABLE variations IS 
'Test data for recipes across difficulty levels. Each variation tests the same recipe with different inputs.';

COMMENT ON COLUMN variations.test_data IS 
'JSON object with test parameters. Schema varies by canonical. Example: {"job_description": "...", "max_words": 100}';

COMMENT ON COLUMN variations.difficulty_level IS 
'Progressive difficulty: 1 (trivial), 2 (easy), 3 (medium), 4 (hard), 5 (expert)';

-- Example queries:
-- Get variations with specific job title:
-- SELECT * FROM variations WHERE test_data->>'job_title' = 'Senior Engineer';
-- 
-- Get variations with salary range:
-- SELECT * FROM variations WHERE (test_data->>'min_salary')::int > 50000;
```

**Changes:**
- 🔥 **BREAKING:** `variations_param_1/2/3` → `test_data JSONB`
- ❌ **REMOVE:** `input_length` (can be computed from test_data)
- ✅ `timestamp` → `created_at`, add `updated_at`
- ✅ Add GIN index for JSON queries

---

### **session_runs** ✅ Add scoring
```sql
CREATE TABLE session_runs (
    session_run_id SERIAL PRIMARY KEY,
    recipe_run_id INTEGER NOT NULL REFERENCES recipe_runs(recipe_run_id),
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    recipe_session_id INTEGER NOT NULL REFERENCES recipe_sessions(recipe_session_id),
    session_number INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'PENDING',
    llm_conversation_id TEXT,
    quality_score TEXT,  -- NEW: A-F grading
    validation_status TEXT,  -- NEW: PASS/FAIL
    error_details TEXT,
    
    UNIQUE (recipe_run_id, session_number)
);

CREATE INDEX idx_session_runs_recipe_run ON session_runs(recipe_run_id);
CREATE INDEX idx_session_runs_session ON session_runs(session_id);

COMMENT ON COLUMN session_runs.quality_score IS 
'Academic grading: A (excellent), B (good), C (acceptable), D (poor), F (failed)';

COMMENT ON COLUMN session_runs.validation_status IS 
'Pass/fail validation: PASS (met requirements), FAIL (did not meet requirements)';
```

**Changes:**
- ✅ **ADD:** `quality_score` (A-F grading)
- ✅ **ADD:** `validation_status` (PASS/FAIL)
- ✅ **ADD:** `recipe_session_id` (track which recipe_sessions entry)

---

### **instruction_runs** ❌ Remove scoring
```sql
CREATE TABLE instruction_runs (
    instruction_run_id SERIAL PRIMARY KEY,
    session_run_id INTEGER NOT NULL REFERENCES session_runs(session_run_id),
    recipe_run_id INTEGER NOT NULL REFERENCES recipe_runs(recipe_run_id),
    instruction_id INTEGER NOT NULL REFERENCES instructions(instruction_id),
    step_number INTEGER NOT NULL,
    prompt_rendered TEXT,
    response_received TEXT,
    latency_ms INTEGER,
    error_details TEXT,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Remove these indexes (refer to non-existent columns):
-- CREATE INDEX idx_instruction_runs_new_session_run...

CREATE INDEX idx_instruction_runs_session_run ON instruction_runs(session_run_id);
CREATE INDEX idx_instruction_runs_recipe_run ON instruction_runs(recipe_run_id);
CREATE INDEX idx_instruction_runs_instruction ON instruction_runs(instruction_id);
CREATE INDEX idx_instruction_runs_status ON instruction_runs(status);

COMMENT ON TABLE instruction_runs IS 
'Individual instruction execution results. Tracks what was sent, what was received, and performance metrics.';
```

**Changes:**
- ❌ **REMOVE:** `pass_fail`, `academic_score`, `value_add`, `rank_in_group`
- ✅ `timestamp` → `created_at`
- ✅ Keep: `status`, `latency_ms`, `error_details`

---

### **schema_documentation** 🆕 NEW TABLE
```sql
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

-- Populate with examples:
INSERT INTO schema_documentation VALUES
('variations', 'test_data', 'JSONB', 
 'JSON object containing test parameters. Structure varies by canonical.',
 '{"job_description": "Senior Engineer role...", "max_words": 100}',
 'Must be valid JSON. Keys should match canonical requirements.',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
 
('recipe_sessions', 'execution_order', 'INTEGER',
 'Sequence number (1, 2, 3...) defining order of session execution within recipe',
 '1',
 'Must be unique within recipe_id. Gaps allowed (1, 2, 5, 10...).',
 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
```

---

## Migration Steps

### **Phase 1: Setup PostgreSQL**
```bash
# Install PostgreSQL 14+
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE base_yoga;
CREATE USER base_admin WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE base_yoga TO base_admin;
\q

# Test connection
psql -h localhost -U base_admin -d base_yoga
```

### **Phase 2: Create New Schema**
```bash
# Execute migration script (to be created)
psql -h localhost -U base_admin -d base_yoga -f schema_v4_base_yoga.sql
```

### **Phase 3: Data Migration**
```python
# Python script to migrate data from SQLite to Postgres
# - Export from SQLite
# - Transform (canonical_code migration, JSON conversion)
# - Import to Postgres
# - Validate counts and relationships
```

### **Phase 4: Update Application Code**
- Update database connection (SQLite → Postgres)
- Update queries (especially JSON queries for variations)
- Update GUI to use new schema
- Update test_runner to use recipe_sessions logic

### **Phase 5: Testing**
- Unit tests for each table
- Integration tests for recipe execution
- GUI testing with new views
- Performance testing

---

## GUI View Definitions

### **Design View: Capability Hierarchy**
```sql
CREATE VIEW v_design_hierarchy AS
SELECT 
    f.facet_id,
    f.short_description as facet_description,
    c.canonical_code,
    c.capability_description,
    s.session_id,
    s.session_name,
    i.instruction_id,
    i.step_number,
    i.step_description,
    ib.branch_id,
    ib.branch_condition
FROM facets f
LEFT JOIN canonicals c ON c.facet_id = f.facet_id
LEFT JOIN sessions s ON s.canonical_code = c.canonical_code
LEFT JOIN instructions i ON i.session_id = s.session_id
LEFT JOIN instruction_branches ib ON ib.instruction_id = i.instruction_id
ORDER BY f.facet_id, c.canonical_code, s.session_id, i.step_number, ib.branch_priority;

COMMENT ON VIEW v_design_hierarchy IS 
'Complete capability hierarchy from facets down to instruction branches. Use for Design View in GUI.';
```

### **Orchestrate View: Recipe Composition**
```sql
CREATE VIEW v_recipe_orchestration AS
SELECT 
    r.recipe_id,
    r.recipe_name,
    r.recipe_version,
    rs.execution_order,
    s.session_id,
    s.session_name,
    c.canonical_code,
    c.capability_description as what_it_does,
    a.actor_id,
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
GROUP BY r.recipe_id, r.recipe_name, r.recipe_version, rs.execution_order, 
         s.session_id, s.session_name, c.canonical_code, c.capability_description,
         a.actor_id, rs.execute_condition, rs.on_success_action, 
         rs.on_failure_action, rs.max_retry_attempts
ORDER BY r.recipe_id, rs.execution_order;

COMMENT ON VIEW v_recipe_orchestration IS 
'Shows how recipes combine sessions. Use for Orchestrate View in GUI.';
```

### **Pipeline View: Execution Tracking**
```sql
CREATE VIEW v_pipeline_execution AS
SELECT 
    rr.recipe_run_id,
    r.recipe_name,
    v.variation_id,
    v.difficulty_level,
    v.test_data,
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
ORDER BY rr.recipe_run_id, sr.session_number, ir.step_number;

COMMENT ON VIEW v_pipeline_execution IS 
'Complete execution trace with filtering by facet, recipe, session. Use for Pipeline View in GUI.';
```

---

## Test Runner Updates

### **Current Logic (Broken)**
```python
# Old approach: Assumes recipe has canonical_code
recipe = get_recipe(recipe_id)
canonical = get_canonical(recipe.canonical_code)  # WRONG!
instructions = get_instructions_for_recipe(recipe_id)  # WRONG!
```

### **New Logic (Correct)**
```python
# New approach: Recipe → recipe_sessions → sessions → instructions
recipe = get_recipe(recipe_id)

# Get ordered sessions for this recipe
recipe_sessions = get_recipe_sessions(recipe_id, order_by='execution_order')

for rs in recipe_sessions:
    session = get_session(rs.session_id)
    canonical = get_canonical(session.canonical_code)
    instructions = get_instructions(session.session_id)
    actor = get_actor(session.actor_id)
    
    # Execute session with retry logic
    session_run = execute_session(
        session=session,
        instructions=instructions,
        actor=actor,
        max_retries=rs.max_retry_attempts,
        on_success=rs.on_success_action,
        on_failure=rs.on_failure_action
    )
    
    # Handle branching
    if session_run.status == 'FAILED' and rs.on_failure_action == 'skip_to':
        jump_to_order = rs.on_failure_goto_order
        continue
```

---

## Rollback Plan

**If migration fails:**
1. Keep SQLite backup intact
2. Switch database connection back to SQLite
3. Document what failed for retry
4. No data loss (all backed up)

**SQLite backup location:** `/home/xai/Documents/ty_learn/data/llmcore (14th copy).db`

---

## Success Criteria

✅ All tables created with proper constraints  
✅ All foreign keys validated  
✅ All indexes created  
✅ All COMMENT documentation added  
✅ All views created and working  
✅ Data migrated with 100% accuracy  
✅ GUI connects to new database  
✅ Test runner works with new schema  
✅ All three hierarchical views functional  

---

## Timeline Estimate

**Phase 1 (Setup):** 30 minutes  
**Phase 2 (Schema):** 1 hour  
**Phase 3 (Data Migration):** 2 hours  
**Phase 4 (Code Updates):** 3 hours  
**Phase 5 (Testing):** 2 hours  

**Total:** ~8 hours of focused work

---

## Next Steps

1. **Review this document** - Gershon approves migration plan
2. **Create SQL migration script** - Arden writes `schema_v4_postgres.sql`
3. **Create data migration script** - Arden writes Python migration tool
4. **Execute migration** - Step by step with validation
5. **Update GUI** - New views and filters
6. **Update test runner** - New execution logic
7. **Test everything** - Unit, integration, end-to-end

---

**Questions? Concerns? Let's discuss before we proceed!**

💙 This is a BIG change, but the RIGHT change! Clean slate with proper documentation!
