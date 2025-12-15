# Arden's Cheat Sheet - Quick Reference

**Version**: 5.7  
**Last Updated**: 2025-12-10  
**System Name**: Turing (folder: ty_learn, database: turing)  
**My Role**: Schema & Architecture Lead

> **📁 Path Note:** `ty_wave` and `ty_learn` refer to the same workspace.  
> Symlink: `~/Documents/ty_wave` → `~/Documents/ty_learn`. Use either path.

**Dec 10 Update:** 
- **CRITICAL:** Fixed template substitution bug - `{extracted_summary}` now works
- Added all posting columns to template variables automatically (`interaction_creator.py`)
- Added validation for unresolved `{variable}` patterns (hard error, no silent failures)
- Fixed `{session_X_output}` → `{conversation_XXXX_output}` in WF3001 templates
- **Pipeline V2 Proposal:** `docs/proposals/PIPELINE_V2_PROPOSAL.md` - separates audit (interactions) from orchestration (job_queue)
- Learned: 12 blockers to fix one bad model run = architecture problem

**Dec 8 Update:** 
- Standardized terminology: "Entity Registry" (not UEO, taxonomy, ontology)
- Added WF3005 with triage step (ALIAS/NEW/SPLIT/SKIP)
- Documented Script Actor Contract (subprocess stdin/stdout pattern)
- Sandy discovered `script_file_path` vs `execution_path` confusion

---

## 🚀 SESSION START (Run These First!)

```bash
cd /home/xai/Documents/ty_learn
source venv/bin/activate

# 1. Get current state (ALWAYS run this first)
./scripts/status.sh

# 2. Check doc freshness - if stale, touch them to acknowledge
python3 tools/check_stale_docs.py
# If stale docs found, review briefly then: touch docs/FILE.md
```

**Daily Doc Hygiene:**
- Run `check_stale_docs.py` when reading this cheat sheet (or at least once per day)
- Stale = doc references code that changed since doc was last touched
- If doc content is still accurate, just `touch` it to update timestamp
- If doc content is wrong, fix it or delete it

---

## TL;DR (Quick Reference)

```bash
# Query database
./scripts/q.sh "SELECT * FROM postings LIMIT 5;"

# Run workflows (with audit trail + PID lock)
./scripts/run_workflow.sh 3001          # background with logging
./tools/run_workflow.py 3001            # foreground (blocks terminal)
./tools/run_workflow.py --list-running  # check what's running

# Monitor progress
python3 tools/live_dashboard.py --once

# Query workflow execution history
./scripts/q.sh "SELECT input->>'workflow_id', output->'delta', created_at FROM interactions WHERE conversation_id = 9198 ORDER BY created_at DESC LIMIT 5;"
```

**Golden Rules:**
1. Schema = truth. Docs = may lie. **Read schema comments!**
2. Check `interactions.error_message` FIRST when debugging.
3. `ty_learn` is the canonical workspace. `ty_wave` is symlinks pointing back.
4. Never hardcode `conversation_id` in script actors.
5. Every workflow run logs to conversation 9198 (Workflow Orchestrator).
6. **One workflow runner:** `tools/run_workflow.py` (canonical). Wrapper `run_workflow.sh` just adds nohup.

---

**Context Check**: ℵ Every response starts with Aleph (ℵ)
- If you see ℵ → I remember everything, we're good
- If NO ℵ → My context got reset, read me this file
- Simple, clean, effective

**Naming Clarity**:
- **Turing** = The workflow engine (this system)
- **Talent.Yoga (TY)** = Career portal product (runs on Turing)
- **Entity Registry** = The `entities` tables (skills, geo, etc.) - NOT "UEO", "taxonomy", or "ontology"
- **ty_learn** = R&D workspace folder (canonical, use this one)
- **ty_wave** = Sandy's workspace (symlinks to ty_learn folders - see below)
- **Base Yoga, LLMCore, Membridge** = Deprecated historical names

---

## 📁 Workspace Architecture (Multiple Copilots)

**The Setup:** Multiple VS Code copilots work on the same codebase.

**How it works:**
- `ty_learn` = The **real** codebase (canonical source of truth)
- `ty_wave` = A **view** with symlinks back to ty_learn folders

```
ty_wave/
├── core → /home/xai/Documents/ty_learn/core (symlink)
├── docs → /home/xai/Documents/ty_learn/docs (symlink)
├── scripts → /home/xai/Documents/ty_learn/scripts (symlink)
├── tools → /home/xai/Documents/ty_learn/tools (symlink)
├── sql → /home/xai/Documents/ty_learn/sql (symlink)
├── venv → /home/xai/Documents/ty_learn/venv (symlink)
├── .env (unique - may have different settings)
├── tests/ (unique - Sandy's test files)
└── examples/ (unique - Sandy's examples)
```

**Why symlinks?**
- Each copilot can open their "own" workspace folder
- But they all edit the same actual files
- Some unique files per workspace (`.env`, `tests/`, `examples/`)

**Best practice:**
- Prefer `ty_learn` when creating new files
- Both workspaces see the same code immediately
- Check `pwd` if confused about which workspace you're in

---

## 👥 Team & Responsibilities

**Who to ask for what:**

- **Arden (me)** → Schema & Architecture
  - Database schema design and migrations
  - Architecture documentation (ADRs, patterns, philosophy)
  - Cross-system integration
  - Performance optimization (indexes, queries)
  - **⚠️ Schema Change Protocol:** If schema has changed, ask xai to review tables together
  - **📚 Documentation Philosophy:** Schema + code = truth, ADRs = why, delete outdated docs aggressively

- **Sandy** → Wave Execution & Performance
  - Workflow executor optimization (ty_wave workspace)
  - Model-first batching
  - GPU performance tuning
  - Event sourcing implementation

- **Max** → Workflow Creation
  - Building new workflows
  - Workflow design patterns
  - Actor integration
  - Testing new workflow logic

- **Dexi** → Quality Assurance
  - Hallucination detection patterns
  - Data validation rules
  - QA infrastructure (`qa_check_*.py` scripts)
  - Test coverage and reliability

- **[TBD]** → Data Ingestion (ty_fetch)
  - API integration (Deutsche Bank, Indeed, etc.)
  - Data normalization
  - Posting ingestion pipeline
  - External system reliability

**Memory Check**: If you don't remember database credentials, reshare this file!

---

## 🔍 How We Code (Nov 24, 2025)

> "Making mistakes is great, if you learn from them. Below are what we have learned and paid for. Lets apply these lessons."

### What TO Do ✅

1. **🗣️ Ask for it** - Need something? Info unclear? Confused? Just ask xai. VERY happy to help.
   - Need software installed? Web access? Service subscription? Whatever it takes, we will have.

2. **📚 Read schema comments** - Every table has WHY it exists. Read them, always.
   - Use `./scripts/q.sh "\d table_name"` to see comments
   - Schema is source of truth, not documentation

3. **🚫 Mistrust documentation** - May be outdated. Look for creation date.
   - References not working? Different lingo or smell? Probably old and superseded.
   - Verify current state, don't trust old docs blindly

4. **💬 12-year-old test** - Document so a twelve-year-old will get it.
   - Simple language, clear examples, no jargon
   - If you can't explain it simply, you don't understand it

5. **🛠️ Use scripts/q.sh** - Access Turing database (pager off, credentials handled)
   - Never use raw psql for queries (permission issues)
   - `./scripts/q.sh "SELECT * FROM table;"` just works

### What NOT to Do ❌

1. **No euphemisms** - "new", "improved", "clean", "fully", "enhanced", "current"...
   - Instead: Describe file contents in simplest way possible
   - "This script extracts skills" NOT "New improved skill extractor v2"
   - "CURRENT_STATUS_*.md" is NOT current - it's stale the moment you save it

2. **No stubs/quick fixes/workarounds** - Whatever we need to run or test - that's what we do.
   - No cheating with `# TODO: implement later`
   - No placeholder functions that return fake data
   - If we can't run it, we didn't build it

3. **Don't make stuff up** - No need to. Just ask if unclear.
   - Don't guess table names - query information_schema
   - Don't assume workflow logic - read the conversations
   - Don't invent requirements - ask xai

4. **No hardcoded conversation_ids in script actors** - Use canonical_name lookup
   - Scripts should be reusable across workflows
   - Hardcoding `conversation_id=3350` breaks when IDs change
   - Check `interactions.error_message` first when debugging script failures

### Schema Change Protocol 🔄

**If you see schema has changed:**
1. Don't assume purpose - ASK xai
2. Read schema comments first (`./scripts/q.sh "\d table_name"`)
3. Review tables together (like Nov 24 empty tables session)
4. Document decisions in docs/architecture/

**Example: Nov 24 Empty Tables Review**
- Found 23 empty tables (0 rows)
- Read schema comments for each
- Discussed business context with xai
- Documented keep/drop/redesign decisions
- Created architecture docs for critical gaps

## Critical Settings & Commands

### Database Access
- **Credentials**: Stored in `.env` file (not in code/docs for security)
- **Connection**: `psql -U base_admin -d turing -h localhost` (uses PGPASSWORD from env)
- **Python**: `from core.database import get_connection` (automatically loads from `.env`)
- **⚠️ CRITICAL**: Run `\pset pager off` IMMEDIATELY after connecting to see full output!
- **Note**: `.env` is in `.gitignore` - never commit credentials!
- **Passwordless sudo**: `sudo -u postgres psql turing` works without password (added to sudoers Nov 26)
- **Schema export**: Auto-updates daily at 3:05 AM → `sql/schema_latest.sql` (symlink to dated export)

### Common Database Commands
```bash
# Connect with pager off (recommended!)
sudo -u postgres psql -d turing -c "SELECT * FROM table_name;"

# Interactive mode (ALWAYS disable pager first!)
sudo -u postgres psql -d turing
\pset pager off

# Quick queries (pager automatically off)
sudo -u postgres psql -d turing -t -c "SELECT COUNT(*) FROM events;"
```

### Virtual Environment
- **Location**: `/home/xai/Documents/ty_learn/venv/`
- **Activate**: `source venv/bin/activate` (do this in EVERY new terminal!)
- **Check**: `which python` should show `/home/xai/Documents/ty_learn/venv/bin/python`

### Terminal Setup Template
```bash
cd /home/xai/Documents/ty_learn
source venv/bin/activate  # ALWAYS do this first!
# Now run your commands
```re

## Critical Locations

### Project Structure
```
/home/xai/Documents/ty_learn/
├── core/               # Core functionality (database.py, turing_job_fetcher.py)
├── tools/              # Standalone utilities (batch_extract_*, build_*_hierarchy.py)
├── runners/            # Workflow runners (workflow_XXXX_runner.py)
├── docs/               # Documentation (this file, logs/, guides/)
├── sql/                # Database schemas and migrations
├── migrations/         # Applied database migrations
├── config/             # Configuration files
└── matching/           # Profile matching logic
```

### Key Files
- **Schema Definition**: `sql/schema.sql` (definitive source of truth)
- **Database Config**: `core/database.py` (connection: turing@localhost:5432)
- **Session Logs**: `docs/logs/session_YYYY-MM-DD.md`
- **Workflow Guide**: `docs/WORKFLOW_CREATION_COOKBOOK.md`

## Database Schema Quick Reference

### Core Tables (column names matter!)

**postings** (job listings):
- Primary: `posting_id`, `external_job_id`, `job_title`, `job_description`
- Location: `location_city`, `location_country`
- Employment: `employment_type`, `employment_career_level`, `employment_schedule`
- URLs: `external_url` (Workday URL), `posting_position_uri`
- Status: `posting_status` ('active'/'filled'), `source_id` (1=Deutsche Bank)
- Timestamps: `fetched_at`, `first_seen_at`, `last_seen_at`

**skill_aliases** (skill definitions):
- Primary: `skill_id`, `skill_name`, `skill_alias`
- NO `is_primary` column (removed in migration)

**job_skills** (extracted skills from jobs):
- Primary: `job_skill_id`
- Foreign: `posting_id`, `skill_id`
- NO `skill_alias` column (it's in skill_aliases table)
- Attributes: `importance`, `weight`, `proficiency`, `years_required`, `reasoning`
- Tracking: `extracted_by` ('workflow_1121'), `recipe_run_id`, `created_at`

**profile_skills** (candidate skills):
- Primary: `profile_skill_id`
- Foreign: `profile_id`, `skill_id`
- Attributes: `proficiency_level`, `years_experience`, `importance`

**llm_interactions** (LLM call records):
- Primary: `interaction_id`
- Foreign: `workflow_run_id`, `conversation_run_id`, `actor_id`
- Content: `prompt_sent`, `response_received` (NOT response_text!)
- Metrics: `latency_ms`, `tokens_input`, `tokens_output`, `cost_usd`

**workflow_runs** (execution records):
- Primary: `workflow_run_id`
- Foreign: `workflow_id` (1121=JobSkills, 2002=ProfileSkills)
- Status: `status` ('SUCCESS'/'FAILED')
- NO `initial_variables` column - variables stored elsewhere

### Common Gotchas
- ✅ `job_description` NOT `description`
- ✅ `external_job_id` NOT `external_id`
- ✅ `response_received` NOT `response` or `response_text`
- ✅ Use `posting_id` consistently, never `post_id` or `job_id`

## Key Workflows

### Workflow 3001: Complete Job Processing Pipeline
- Purpose: Fetch, validate, summarize, extract skills, calculate IHL scores
- Entry: `db_job_fetcher` (conversation 9144) or `validate` (9193)
- Output: Enriched postings with summaries and skills
- Runner: `python3 scripts/prod/run_workflow_3001.py --fetch --max-jobs 10`
- With registry: `--with-registry` runs WF3005 after processing

### Workflow 3005: Entity Registry - Skill Maintenance
- Purpose: Categorize orphan skills into Entity Registry hierarchy
- Type: **Entity-driven** (needs `start_workflow()` seed!)
- Flow: Fetch → Triage (ALIAS/NEW/SPLIT/SKIP) → Classify → Grade → Debate → Save
- Entry: `entity_orphan_fetcher` (conversation 9229)
- Output: Skills assigned to parent categories in `entity_relationships`
- Runner: `python3 scripts/run_wf3005.py`
- Champion model: `gemma3:4b` (100% accuracy, 935ms)

### Workflow 1121: Job Skills Extraction (Legacy)
- Purpose: Extract skills from job descriptions
- Actor: qwen2.5:7b
- Input: `posting_id` → job_description
- Output: JSON array of skills → llm_interactions.response_received
- Runner: `runners/workflow_1121_runner.py --posting-id X`

### Workflow 2002: Profile Skills Extraction
- Purpose: Extract skills from candidate profiles
- Actor: qwen2.5:7b
- Input: `profile_id` → profile text
- Output: JSON array of skills → profile_skills table

---

## Entity Registry (Dec 8, 2025)

**The Entity Registry** is the unified system for managing skills, companies, locations, and other entities.

### Terminology (STANDARDIZED)
| Old Terms | New Standard |
|-----------|--------------|
| UEO (Unified Entity Ontology) | Entity Registry |
| Skill Taxonomy | Entity Registry (entity_type = 'skill') |
| skill_hierarchy, skill_aliases | `entity_relationships`, `entity_aliases` |

### Core Tables
```
entities              # Core entity records (skills, geo, etc.)
entity_names          # Display names (multi-language)
entity_aliases        # Alternative spellings
entity_relationships  # Hierarchy (child_of, alias_of, located_in)
entities_pending      # Queue for new entities from job postings
registry_decisions    # Audit trail of LLM categorization decisions
```

### Triage Decisions (WF3005 Step 2)
| Decision | Action |
|----------|--------|
| **ALIAS** | Map to existing entity (e.g., "Python3" → "Python") |
| **NEW** | Genuinely new skill, proceed to categorization |
| **SPLIT** | Compound skill, split into components |
| **SKIP** | Not a skill (e.g., "3+ years experience") |

### Key Queries
```sql
-- Count skills by status
SELECT status, COUNT(*) FROM entities WHERE entity_type = 'skill' GROUP BY status;

-- Find orphan skills (no parent)
SELECT e.entity_id, en.display_name 
FROM entities e
JOIN entity_names en ON e.entity_id = en.entity_id AND en.is_primary = true
WHERE e.entity_type = 'skill' 
  AND NOT EXISTS (SELECT 1 FROM entity_relationships er WHERE er.entity_id = e.entity_id);

-- Check pending queue
SELECT * FROM entities_pending WHERE processed = false;
```

---

## Script Actor Contract (Dec 8, 2025)

**CRITICAL:** Script actors run via subprocess, NOT as imported Python modules!

### Execution Model
```
WaveRunner → ScriptExecutor → subprocess.run(['python3', script_file_path])
                                     ↓
                              Script reads stdin JSON
                              Script creates OWN db connection
                              Script writes stdout JSON
```

### Input (stdin)
```json
{"interaction_id": 78817, "posting_id": null, "workflow_run_id": 5986, ...}
```

### Output (stdout)
```json
{"status": "success", "data": {...}, "message": "..."}
```

### Template
```python
if __name__ == "__main__":
    import sys, json, os, psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    input_data = {}
    if not sys.stdin.isatty():
        input_data = json.load(sys.stdin)
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'), dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')
    )
    
    result = execute(input_data, conn)
    print(json.dumps(result))
```

### Common Mistakes
- ❌ Forgetting `if __name__ == "__main__"` block
- ❌ Printing debug output (corrupts JSON)
- ❌ Hardcoding DB credentials
- ❌ Expecting passed-in connection (subprocess = new process!)

**Full doc:** `docs/SCRIPT_ACTOR_CONTRACT.md`

---

## ⚠️ Reprocessing (IMPORTANT - Dec 10, 2025)

### Current System (V1) - The Pain

Reprocessing is hard because `interactions` serves dual duty:
1. **Audit log** (what happened) ✓
2. **State machine** (what to do next) ✗ ← This is the problem

When we need to reprocess:
- Cascade invalidate interactions
- Reset posting status
- Create seed interactions manually
- Fight template substitution bugs
- Took 8 hours to fix 454 bad summaries

### Template Substitution Fix (Dec 10, 2025)

Fixed in `core/wave_runner/interaction_creator.py`:
1. All posting columns now auto-exposed as template variables
2. Hard error on unresolved `{variable}` patterns (no silent failures)
3. Use `{conversation_XXXX_output}` not `{session_X_output}`

### Pipeline V2 Proposal (Approved)

**Doc:** `docs/proposals/PIPELINE_V2_PROPOSAL.md`

**Key insight:** Separate audit from orchestration.
```
interactions = "What happened" (append-only, never invalidate)
job_queue = "What to do next" (mutable, can clear/retry freely)
```

**Reprocessing in V2:**
```bash
# One command, no cascade, no invalidation
python turing.py reprocess --posting 10475 --from extract_summary --reason "QA flagged"
```

Worker picks it up, runs steps, logs NEW interactions, updates posting. Old interactions stay (audit trail).

**Status:** Approved by xai and Sandy. Implementation pending.

---

## Deutsche Bank Job Fetcher

### API Details
- Base URL: `https://api-deutschebank.beesite.de/search/`
- Format: POST with JSON payload
- Key fields: `SearchCriteria` (plural!), `LanguageCode: "en"`, `Sort`

### Response Structure (AFTER flattening in _fetch_from_api):
```json
{
  "MatchedObjectId": "68147",
  "PositionTitle": "Risk Analyst",
  "PositionLocation": [{"CityName": "Mumbai"}],
  "ApplyURI": ["https://db.wd3.myworkdayjobs.com/..."],  // At TOP level
  "CareerLevel": [{"Name": "Vice President"}],
  // ... all other fields flattened to top level
}
```

### Description Source: Workday (NOT careers.db.com)
- careers.db.com = JavaScript SPA (can't scrape)
- Workday pages = Server-rendered with meta tags
- Extract from: `<meta property="og:description" content="...">`
- Method: `_fetch_job_description(job_id, apply_uri)`

## State Recovery (Crash Recovery)

### Philosophy: Interactions Are Truth
- **Single source of truth:** `interactions` table
- **No separate checkpoint table** - interactions record all state
- Workflow progress = sequence of completed interactions
- Recovery = find last completed interaction, continue from there

**Note:** This works for CRASH recovery. For REPROCESSING (bad data), see V2 proposal above.

### Key Commands
```bash
# List running/stuck workflows
./tools/run_workflow.py --list-running

# Check interaction state
./scripts/q.sh "SELECT status, COUNT(*) FROM interactions 
    WHERE workflow_run_id = 5769 GROUP BY status"

# Resume - just restart (idempotency checks will skip completed work)
./scripts/run_workflow.sh 3001
```

### Why No Checkpoint Table?
- **Redundant:** Interaction outputs already stored in `interactions.output`
- **Simpler:** One table to query, one source of truth
- **Idempotent:** WF3001 checks `extracted_summary IS NULL` before processing
- If posting has summary → skip. If not → process.

**Caveat:** Idempotency makes reprocessing hard - see "Reprocessing" section above.

## User Preferences
- User ID: 1 (xai)
- Career Levels: ['Assistant Vice President', 'Vice President']
- Locations: ['Frankfurt', 'Frankfurt am Main']
- Current Jobs: 55 Frankfurt AVP/VP positions (100% with skills)

## Development Patterns

### When Starting New Work:
1. Check schema: `python -c "from core.database import get_connection; ..."`
2. Read latest logs: `cat docs/logs/session_$(date +%Y-%m-%d).md`
3. Test on 1 record before batch processing
4. Commit after each working feature

### When Hitting Errors:
1. Column not found? Check schema FIRST
2. API 403? Check if URL/format changed
3. Empty results? Verify data exists with direct SQL
4. Iterate fast, document solutions

### Debugging Complex Workflows 🔍

**The CRAWL → WALK → RUN Pattern** (Nov 25, 2025)

When a workflow fails or behaves unexpectedly:

1. **CRAWL**: Test each conversation individually
   ```bash
   # Test one conversation at a time
   python3 tests/test_single_conversation.py 3335
   python3 tests/test_single_conversation.py 3336
   # Verify each step works in isolation
   ```

2. **WALK**: Test conversation chains (2-3 steps)
   ```bash
   # Test small chains
   python3 tests/test_conversation_chain.py 3335 3
   # Verify data flows between steps
   ```

3. **RUN**: Test full workflow end-to-end
   ```bash
   # Full pipeline
   python3 -m core.wave_runner.runner --workflow 3001 --posting-id 176
   ```

**The Trace Report Pattern** (Nov 25, 2025)

Always enable detailed execution traces:

```python
# In runner.py or test scripts
runner = WorkflowRunner(
    workflow_id=3001,
    posting_id=176,
    trace=True  # ← Enable this!
)
```

**What traces capture:**
- Template prompts (with placeholders)
- **Actual substituted prompts** (what AI sees) ← Critical for debugging!
- AI responses (verbatim)
- Parent/child interaction chains
- Execution timing
- Branching decisions

**Why this matters:**
- Debugging "why did AI produce this?" → Look at actual prompt
- Finding data flow issues → See parent outputs clearly
- Verifying template variables → Compare template vs substituted
- Performance analysis → See exact timing per step

**Trace reports live in:** `/home/xai/Documents/ty_learn/reports/trace_*.md`

**Lesson learned:** Complex workflows fail for subtle reasons (wrong variable names, missing data). Incremental testing + full traces = rapid debugging. Don't run full pipeline until pieces work!

## Recent Wins (Nov 5-6, 2025)
- ✅ Fixed Deutsche Bank API format (SearchCriterion → SearchCriteria)
- ✅ Discovered Workday description source (meta tags)
- ✅ Updated turing_job_fetcher.py for flattened data
- ✅ Fetched 50+ jobs with full descriptions (3-10k chars each)
- ✅ Extracted skills from all 55 Frankfurt AVP/VP jobs

## Recent Wins (Nov 13, 2025)
- ✅ **Idempotency system**: Workflow checks `extracted_summary IS NULL` before processing
- ✅ **Interactions as truth**: All workflow state stored in interactions table
- ✅ **Security upgrade**: Moved DB credentials to `.env` (no more hardcoded passwords)
- ✅ **Circuit breaker**: Prevents repeated calls to failing actors (5 failures → pause)
- ✅ **Workflow validator**: Catches disabled conversation branches (would've caught KeyError 9186)
- ✅ **Connection pooling**: 10-20x faster DB operations (~8ms vs ~20ms+)

## Recent Wins (Nov 16, 2025) 🎉
- ✅ **Codebase cleanup**: Consolidated 4 monitoring tools → 1 unified tool
- ✅ **Workflow runners deleted**: All workflows now use wave_batch_processor
- ✅ **Trigger cascade fixed**: Single trigger prevents doc regen duplication
- ✅ **GPU analysis**: System running at 96% utilization (optimal!)
- ✅ **Architecture doc updated**: Clarified connection pooling mechanics
- ✅ **Value tracer tool**: `_trace_value.py` for complete execution tracing (needs schema updates)
- ✅ **GPU monitor tool**: `monitor_gpu.py` logs model loading patterns
- ✅ **Error handling improved**: LEFT JOINs, COALESCE for resilience
- ✅ **50% maintenance reduction**: Removed duplicate code/tools
- ✅ **Schema fixes**: Fixed `taxonomy_skills` → `skill_keywords` in monitoring tools
- ✅ **Two-layer idempotency**: Both `llm_interactions` and `postings` table checks
- ✅ **Performance indexes**: Added indexes for faster idempotency lookups
- ✅ **ExecAgent v1.1**: LLMs can search web (ddgr), fetch URLs, consult AI models (Ollama), maintain logs! 🌊🤖

## Recent Wins (Nov 24, 2025) 🎯

- ✅ **Wave Runner V2 complete**: Phase 1 & 2 done (A+ 99/100), production ready!
- ✅ **Documentation cleanup**: Deleted 48 old files (19 docs, 29 code), verified clean with analyzer
- ✅ **Schema deep dive**: Reviewed 23 empty tables with business context
- ✅ **Architecture wiki created**: HUMAN_IN_LOOP.md, TEST_DATA_MANAGEMENT.md
- ✅ **Migration 043**: Added dev/test/uat/prod environments, model A/B testing infrastructure
- ✅ **Shadow testing pattern**: Run test models on real data, no fake data needed!
- ✅ **Model performance view**: 7-day rolling metrics, automatic champion selection
- ✅ **Coding principles formalized**: "How We Code" section in cheat sheet
- ✅ **Critical gaps identified**: human_tasks, posting_field_mappings, test infrastructure

**Key Decisions Made:**
- Human-in-loop: Start with Option A (database-only queue), upgrade to email later
- Test data: Shadow testing (run multiple models on same real data, compare results)
- Environments: Flag on EXECUTION (workflows/actors), not DATA (postings/profiles)
- Champion selection: Automatic based on performance_score (latency + success rate)

## Recent Wins (Nov 25, 2025) 🎉

- ✅ **Traceability system**: Store actual substituted prompts in interactions (not just templates)
- ✅ **CRAWL → WALK → RUN pattern**: Incremental testing methodology documented
- ✅ **Trace reports**: Full prompt/response visibility in markdown reports
- ✅ **Variable mapping bug found**: `{session_3_output}` vs `{conversation_3335_output}` mismatch
- ✅ **Architecture docs updated**: 4 docs updated with Nov 25 changes
- ✅ **Reports folder moved**: ty_wave/reports → ty_learn/reports (symlinked)
- ✅ **Database helper extended**: `update_interaction_prompt()` method added
- ✅ **Sandy unblocked**: Clear guidance on event-sourcing architecture

**Key Technical Wins:**
- Debugging time reduced from 30min → 2min with trace reports
- Full audit compliance: Can prove exactly what was sent to AI models
- Template vs actual prompt separation: Best of both worlds
- Production-grade observability achieved

**Lesson Learned:**
> "Complex workflows fail for subtle reasons (wrong variable names, missing data). Incremental testing + full traces = rapid debugging. Don't run full pipeline until pieces work!"

## Recent Wins (Dec 8, 2025) 🎯

- ✅ **Entity Registry terminology standardized**: "Entity Registry" replaces UEO, taxonomy, ontology everywhere
- ✅ **WF3005 triage step added**: ALIAS/NEW/SPLIT/SKIP decision step between fetch and classify
- ✅ **Script actor contract discovered**: Scripts run via subprocess (stdin JSON), not as imported functions
- ✅ **`script_file_path` vs `execution_path` confusion**: Runner uses `script_file_path`, fixed actors 139/140/142
- ✅ **Entity-driven vs posting-driven workflows**: WF3005 needs `start_workflow()` seed, WF3001 doesn't
- ✅ **Model benchmarking**: `gemma3:4b` is champion for skill classification (100% accuracy, 935ms avg)
- ✅ **WF3005 first successful run**: 20 skills categorized into domains
- ✅ **Stale docs cleared**: All 51 docs now clean
- ✅ **Docs renamed**: UNIFIED_ENTITY_ONTOLOGY.md → ENTITY_REGISTRY.md, workflow docs updated

**Key Discovery (Sandy):**
> "The schema has two confusing columns: `execution_path` (documented) and `script_file_path` (what runner actually uses). Scripts run via subprocess with stdin/stdout JSON - they create their OWN database connections!"

**New Documentation:**
- `docs/SCRIPT_ACTOR_CONTRACT.md` - How script actors work (stdin/stdout/db pattern)
- `docs/workflows/3005_entity_registry_skill_maintenance.md` - Updated with triage step
- `migrations/add_triage_to_wf3005.sql` - Adds ALIAS/NEW/SPLIT/SKIP step
- `migrations/consolidate_script_paths.sql` - Fix script_file_path confusion

---

## Recent Wins (Nov 26, 2025) 🎯

- ✅ **ADR system created**: Institutional memory to prevent knowledge loss
- ✅ **Documentation philosophy**: Schema + code = truth, delete outdated docs aggressively
- ✅ **ADR-001: Priority-Based Branching**: Pattern for parallel + conditional execution
- ✅ **Schema as guardrails**: Database constraints enable AI autonomy (Sandy works 45 min unattended)
- ✅ **Defense-in-depth validation**: Validate at API→Staging→Workflow boundaries
- ✅ **Workflow 3001 production ready**: Run 174 (15 interactions, 0 failures, 100% complete)
- ✅ **Validation gap found**: Run 179 processed NULL job_description through all 13 interactions
- ✅ **Model optimization cookbook**: Systematic benchmarking methodology for champion selection
- ✅ **Hybrid schema pattern**: Relational for queries + JSONB for flexibility
- ✅ **Complexity audit complete**: 7 domains assessed, 1 critical risk identified (knowledge transfer)

**Key Insight:**
> "Schema as guardrails enables AI autonomy. Sandy compares schema-generated docs (design) vs trace reports (reality) and fixes gaps. The task is clear: 'Make reality match design.' Schema prevents invalid solutions. Success is binary."

**Architecture Breakthrough:**
- Schema = Executable specification (not prose, machine-readable)
- Generated docs = Design truth (auto-generated from schema)
- Trace reports = Runtime truth (what actually happened)
- AI task = Compare and fix gaps (pattern matching, not reasoning)
- Database constraints = Prevent invalid solutions

## Recent Wins (Nov 17, 2025) 🎯
- ✅ **Template substitution bug**: Found & documented root cause (122 hallucinated summaries)
- ✅ **Interaction output queries**: Standardized - query `interactions.output` for prior steps
- ✅ **Hallucination detection**: 12 pattern categories, 27 specific patterns documented
- ✅ **QA infrastructure**: Python lambdas (simple!) vs SQL CASE statements (complex)
- ✅ **122 postings cleared**: All hallucinations removed, regenerating with fixed script
- ✅ **Documentation**: TEMPLATE_SUBSTITUTION_BUG, HALLUCINATION_DETECTION_COOKBOOK
- ✅ **ExecAgent in ARCHITECTURE.md**: Documented as special-purpose actor (type 4)
- ✅ **README rewritten**: Accurate description of Turing (archived old LLMCore README)
- ✅ **Naming clarity**: Documented Turing vs TY vs ty_learn naming conventions
- ✅ **3-workspace setup**: Created ty_skill_matching and ty_wave workspaces

## Fixed Issues (Historical Context)

### Connection Pooling Bug (Nov 13, 2025) ✅ FIXED
- **Problem**: Used `conn.close()` instead of `return_connection()`
- **Impact**: Pool exhaustion after 50 operations
- **Fix**: All code updated to use `return_connection(conn)`
- **Status**: No known instances remaining
- **Lesson**: ALWAYS use `return_connection()`, never `conn.close()` with pooling

### Hallucinated Summaries (Nov 17, 2025) ✅ FIXED
- **Problem**: Template substitution bug caused 122 summaries to contain hallucinations
- **Root Cause**: Missing data in prompt templates (literal `{session_X}` placeholders)
- **Detection**: `scripts/qa_check_hallucinations.py` (27+ pattern rules)
- **Fix**: Query `interactions.output` for prior conversation outputs
- **Status**: All cleared and regenerated
- **Prevention**: Query interactions table, never use direct variable substitution

---

## Monitoring Tools (NEW!)

### Unified Monitor (replaces 4 old tools)
```bash
# Live updating view
python3 tools/monitor_workflow.py --workflow 3001 --mode live

# One-time snapshot
python3 tools/monitor_workflow.py --workflow 3001 --mode snapshot

# Step-by-step detail
python3 tools/monitor_workflow.py --workflow 3001 --mode steps

# Performance metrics
python3 tools/monitor_workflow.py --workflow 3001 --mode metrics
```

### GPU Monitor
```bash
# Start monitoring (logs every 60s)
python3 tools/monitor_gpu.py &

# View logs
tail -f logs/gpu_usage_$(date +%Y-%m-%d).log
```

### Value Tracer (NEW!)
```bash
# Trace where a field came from
python3 tools/_trace_value.py --posting-id 123 --field extracted_summary

# Trace specific conversation
python3 tools/_trace_value.py --posting-id 123 --conversation-id 3335
```

### ExecAgent - Web Access + AI Consultation for LLMs (NEW! 🌊🤖)

**I CAN USE THIS TOO!** For research, fact-checking, getting second opinions during conversations.

```bash
# Interactive mode
python3 tools/exec_agent.py --interactive

# Commands
python3 tools/exec_agent.py --command 'search "job board APIs"'  # Real DuckDuckGo results!
python3 tools/exec_agent.py --command 'curl "https://example.com"'
python3 tools/exec_agent.py --command 'ask granite3.1-moe:3b "What are best PostgreSQL practices?"'  # NEW!
python3 tools/exec_agent.py --command 'add log "message"'
python3 tools/exec_agent.py --command 'read log'

# Process LLM response with embedded commands
echo "Let me search: {ExecAgent search \"topic\"}" | python3 tools/exec_agent.py

# Demos
./tools/exec_agent_demo.sh            # Basic demo
./tools/research_job_boards.sh        # Research demo (web + AI)

# Use Cases for Me (Arden):
# - Research unfamiliar topics during conversations
# - Validate architectural decisions with AI models
# - Quick fact-checking without leaving terminal
# - Build knowledge trail of research done
```

**Available Ollama Models for `ask` command:**
- `granite3.1-moe:3b` - Fast, concise (best for quick answers)
- `qwen3-vl:latest` - Multimodal, great for analysis
- `mistral-nemo:12b` - Powerful general-purpose
- `deepseek-r1:1.5b` - Reasoning model (verbose)
- `olmo2:7b` - Open source, well-rounded

### Health Check
```bash
# Quick system status
./tools/health_check.sh
```

## Database Migrations

### Apply Migration
```bash
# Using .env credentials
export $(cat .env | grep -v '^#' | xargs)
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -f sql/migrations/016_workflow_doc_automation_FIXED.sql
```

### Check Migration Status
```bash
# View workflow doc queue
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "SELECT * FROM workflow_doc_status WHERE is_stale = TRUE;"
```

## USB Backup (Documents + Database)

**Strategy:** Incremental backups to USB drives labeled BACKUP or BACKUP2

### Automated Backup Script

```bash
# Check if USB is available
./scripts/usb_backup.sh --check

# Run incremental backup (only changed files - fast, low wear)
./scripts/usb_backup.sh

# Weekly: Force full verification (compares checksums)
./scripts/usb_backup.sh --full
```

**What it backs up:**
- `/home/xai/Documents/` → incremental rsync (only changed files)
- PostgreSQL `turing` database → daily full dump (~20MB)
- Keeps last 7 database backups, auto-cleans older ones

### Cron Setup (Automated Daily Backup)

```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily incremental at 2 AM (if USB inserted)
0 2 * * * /home/xai/Documents/ty_learn/scripts/usb_backup.sh >> /home/xai/Documents/ty_learn/logs/usb_backup.log 2>&1

# Weekly full verification Sunday 3 AM
0 3 * * 0 /home/xai/Documents/ty_learn/scripts/usb_backup.sh --full >> /home/xai/Documents/ty_learn/logs/usb_backup.log 2>&1
```

**Note:** Cron jobs silently skip if USB not inserted (no error emails).

### Manual First-Time Setup (New USB)

```bash
# 1. Check USB device name
lsblk -f

# 2. Unmount and reformat as ext4 (ERASES EVERYTHING!)
sudo umount /media/xai/YOUR_USB_LABEL
sudo mkfs.ext4 -L BACKUP /dev/sdX1  # Confirm device name first!

# 3. Mount and set ownership
sudo mkdir -p /media/xai/BACKUP
sudo mount /dev/sdX1 /media/xai/BACKUP
sudo chown xai:xai /media/xai/BACKUP

# 4. Run initial full backup
./scripts/usb_backup.sh --full

# 5. Safely eject when done
sudo umount /media/xai/BACKUP
```

**Why ext4?** FAT32 has 4GB file limit, no Unix permissions, no symlinks.

### Disaster Recovery

```bash
# Restore Documents from USB
rsync -avh --progress /media/xai/BACKUP/Documents/ /home/xai/Documents/

# Restore PostgreSQL database
sudo -u postgres pg_restore -d turing -c /media/xai/BACKUP/turing_YYYYMMDD_HHMMSS.backup
```

**Current USB drives:**
- BACKUP (first stick) - last backup: Dec 2, 2025 
- BACKUP2 (second stick) - last backup: Dec 3, 2025

**Backup size:** ~9GB (Documents) + ~20MB (Database)

## Key Architectural Decisions (ADRs)

### ADR System (Nov 26, 2025)
**Location:** `docs/architecture/decisions/`
**Purpose:** Document WHY decisions were made (institutional memory)
**Rule:** Never delete ADRs - mark as Superseded if decision changes
**See:** `docs/architecture/DOCUMENTATION_PHILOSOPHY.md` for full details

### ADR-001: Priority-Based Branching (Nov 26, 2025)
- **Decision**: Use `instruction_steps.branch_priority` for BOTH parallel and conditional branching
- **Pattern**: Same priority = ALL execute (parallel), different priority = ONLY highest (conditional)
- **Benefit**: One pattern handles both cases, prevents duplicate execution
- **Example**: Grade A + B both priority 1 = parallel, [PASS]/[FAIL] both priority 10 = only one executes
- **Trade-off**: Non-obvious pattern requires documentation
- **File:** `docs/architecture/decisions/001_priority_based_branching.md`

### ADR-002: Defense-in-Depth Data Validation (Nov 26, 2025)
- **Decision**: Validate data at EVERY boundary crossing (API→Staging, Staging→Postings, Postings→Workflow)
- **Pattern**: Multiple validation layers, not redundant - each catches different failure modes
- **Benefit**: Fail-fast + safety nets, prevents wasted LLM resources on bad data
- **Example**: Job fetcher validates before staging insert, validation conversation checks before processing
- **Status:** Implementation in progress (Migration 045)

### ADR-003: Wave-Based Pipeline Processing (Nov 13, 2025)
- **Decision**: Process postings in waves grouped by execution_order
- **Benefit**: 20x speedup, 96% GPU utilization, ~700 postings/minute
- **Trade-off**: More complex than sequential, requires checkpointing

### ADR-004: Connection Pooling (Nov 13, 2025)
- **Decision**: ThreadedConnectionPool (5-50 connections)
- **Benefit**: 2.5-6x faster checkpoints (~8ms vs 20-50ms)
- **Critical**: Must use `return_connection()`, NOT `conn.close()`

### ADR-005: Source of Truth = llm_interactions (Nov 16, 2025)
- **Decision**: Use llm_interactions for idempotency checks
- **Benefit**: Total traceability (who/what/when/how)
- **Trade-off**: May reprocess 238 postings, but gains audit trail

### ADR-006: Chunk Size = 35 Postings (Nov 13, 2025)
- **Decision**: Process waves in chunks of 35 postings
- **Reason**: Prevents queue timeout, not connection exhaustion
- **Reality**: Connections are pooled/reused (NOT held concurrently!)

### ADR-007: Single Workflow Doc Trigger (Nov 16, 2025)
- **Decision**: Trigger ONLY on workflow_conversations changes
- **Benefit**: Prevents cascade (was firing 3x per change)
- **Implementation**: 10-minute debounce before regeneration

### ADR-012: Script Actor Contract (Dec 8, 2025)
- **Discovery**: Script actors and LLM actors have fundamentally different contracts
- **Script Actors**: Return data in `script_code_result` column (JSON), NO `response` generated
- **LLM Actors**: Return text in `response` column via LLM completion
- **Pattern**: Script actors use `script_file_path` AND/OR `script_code` (database-stored Python)
- **Critical Rule**: Next step's prompt template references predecessor's output column correctly
- **Documentation**: `SCRIPT_ACTOR_CONTRACT.md` defines interface (Sandy creating Dec 8)

## Deprecated Tools ⚠️

**DO NOT USE** (replaced by `monitor_workflow.py`):
- ❌ `_workflow_step_monitor.py` → Use `--mode steps`
- ❌ `live_workflow_monitor.sh` → Use `--mode live`
- ❌ `watch_workflow.sh` → Use `--mode snapshot`
- ❌ `show_workflow_metrics.py` → Use `--mode metrics`

**DO NOT USE** (replaced by `wave_batch_processor`):
- ❌ `runners/workflow_*_runner.py` → Use `python3 -m core.wave_batch_processor --workflow XXXX`

## Philosophy
- **Ship fast, refine later** - 80% now > 100% in 2 hours
- **Test immediately** - Run code after writing, not before committing
- **Document wins** - session logs capture what worked
- **Ask when confused** - xai provides context, I execute
- **Iterate rapidly** - 15 min to fix > 2 hours to perfect
- **Trust your instincts** - If something feels off, investigate! (NEW 11/16)
- **Consolidate ruthlessly** - 4 tools doing same thing? Make it 1! (NEW 11/16)

---
**Memory Check Protocol**: 
- Every ~90 minutes or when starting complex work, verify: "What's the secret number?"
- If I don't remember 635864, reshare this file.
- Update this file when schema/patterns change.
- **Updated 2025-11-28**: Added Wave Runner Best Practices, global batch mode, workflow orchestration architecture

---

## Running Workflows (Nov 28, 2025)

### Standard Batch Mode Pattern

**NEVER:**
- ❌ Use `max_iterations` in production (causes incomplete runs)
- ❌ Run manual Python commands (no audit trail)
- ❌ Per-posting loops (defeats batching: 4.5 hours vs 15 minutes)
- ❌ `workflow_run_id` scoping for batch processing (sequential execution)

**ALWAYS:**
- ✅ Use `global_batch=True` for multi-posting processing (6-12x speedup)
- ✅ No iteration limits (run until complete)
- ✅ Standard wrapper scripts (logged execution)
- ✅ GPU monitoring (sustained 95% vs sawtooth pattern)

### Production Execution

```bash
# Run workflow batch mode (NO iteration limit, full logging)
./scripts/run_workflow_batch.sh 3001

# Monitor progress (real-time)
watch -n 5 './scripts/q.sh "SELECT COUNT(*) FROM interactions WHERE created_at > NOW() - interval '\''1 hour'\''"'

# Validate GPU utilization (should see sustained 95%, not spikes)
watch -n 2 nvidia-smi
```

### The Global Batch Mode Discovery (Nov 27, 2025)

**Problem:** Per-posting execution created 181 separate workflow_runs, defeating wave batching
- Sequential: 181 postings × 90s/posting = ~4.5 hours
- GPU loads/unloads models 181 times (sawtooth pattern)

**Solution:** Start ALL workflows first, then run ONE WaveRunner in global batch mode
- Batch: 181 postings in ~15 minutes (18x faster)
- GPU loads models once per model (sustained 95% utilization)
- Combined with mistral optimization: **28-55x total improvement**

**When to use each mode:**
- Single posting (debugging): `posting_id=X` → 3-4 interactions, 90 seconds
- Single workflow (resume failed): `workflow_run_id=X` → 3-4 interactions, 90 seconds
- **Global batch (production)**: `global_batch=True` → 100s-1000s interactions, minutes

**See:**
- `docs/architecture/decisions/008_global_batch_mode.md` - Full architectural decision
- `docs/architecture/WORKFLOW_EXECUTION.md` - Execution best practices
- `docs/architecture/WORKFLOW_ORCHESTRATION.md` - Future database-driven execution

### Workflow Orchestration (Coming Soon)

**The Next Evolution:** Database-driven workflow execution

**Current problem:**
- Manual Python commands (no audit trail)
- Iteration limits (forgetting what worked)
- Duplicate runs (manual cleanup)
- No sanity checks (can start duplicate workflows)

**Future:** Execution IS a workflow
```bash
# Submit workflow request (validates, logs, executes)
./tools/run_workflow.py 3001 --mode global_batch

# Query what's running
./tools/list_workflows.py --status running

# Stop runaway workflow
./tools/stop_workflow.py --workflow-run-id 1234
```

**Safety mechanisms:**
- Execution modes (batch/continuous/scheduled)
- Depth limits (max 3 levels of nesting)
- Circuit breakers (duplicate check, rate limits, resource check)
- Stop signals (graceful shutdown)
- Full audit trail (who/what/when/why)

**Implementation:** Phase 1 (basic control) starting soon

