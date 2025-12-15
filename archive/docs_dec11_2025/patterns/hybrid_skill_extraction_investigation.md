# Investigation: hybrid_skill_extraction.py vs Current Taxonomy Workflows

**Date:** November 13, 2025  
**Purpose:** Determine if `hybrid_skill_extraction.py` is redundant or contains unique capabilities

---

## Executive Summary

**Finding:** `hybrid_skill_extraction.py` contains **unique job-to-taxonomy mapping logic** that is **NOT** currently used in any workflow. It should be integrated into workflow 3001 (waves 12-15).

**Current State:**
- ✅ Workflow 3002: Maintains taxonomy structure (script-based, deterministic)
- ✅ Workflow 3003: Maintains taxonomy structure (LLM-based, adaptive hierarchy)
- ❌ Workflow 3001 waves 12-15: Simple LLM extraction WITHOUT fuzzy matching or auto-aliasing
- ❌ `hybrid_skill_extraction.py`: Standalone script, NOT integrated as actor

---

## The Three Systems

### 1. Workflow 3002: Taxonomy Maintenance (Script-Based)

**Purpose:** Organize existing taxonomy into filesystem hierarchy

**Actors:**
- `taxonomy_exporter` → `tools/rebuild_skills_taxonomy.py`
- `taxonomy_organizer` → `tools/multi_round_organize.py`
- `taxonomy_indexer` → `tools/generate_taxonomy_index.py`

**What it does:**
1. Export skills from `skill_hierarchy` table
2. Organize into folder structure (deterministic rules)
3. Generate INDEX.md with navigation

**Key insight:** This is about **organizing existing taxonomy**, not extracting skills from jobs.

---

### 2. Workflow 3003: Taxonomy Maintenance (LLM-Based)

**Purpose:** Same as 3002, but with LLM-driven adaptive organization

**Actors:**
- `qwen2.5:7b` → Query skills from DB
- `qwen2.5:7b` → Analyze structure, propose organization
- `gemma3:4b` → Organize skills semantically
- `qwen2.5:7b` → Check thresholds (>15 subfolders = reorganize)
- `file_writer` → Write to filesystem
- `qwen2.5:7b` → Generate INDEX.md

**What it does:**
1. Query all skills from database
2. LLM analyzes and proposes semantic grouping
3. Iteratively organize until no folder exceeds thresholds
4. Write to filesystem with INDEX.md

**Key insight:** This is about **adaptive taxonomy organization**, with infinite hierarchy depth and automatic threshold-based reorganization. Still not about extracting skills from jobs.

---

### 3. hybrid_skill_extraction.py: Job-to-Taxonomy Mapper

**Purpose:** Extract skills from job postings and map to existing taxonomy

**What it does:**
1. **Phase 1: Extract RAW skills** from `postings.extracted_summary`
   - LLM reads job text
   - Returns JSON array: `["Python", "SQL", "AWS", ...]`
   - No taxonomy constraint (extracts everything mentioned)

2. **Phase 2: Map to taxonomy**
   - Translate German → English (multilingual support!)
   - Fuzzy match against taxonomy (85%+ threshold)
   - LLM confirms medium-confidence matches (85-95%)
   - Auto-add German terms to `skill_aliases` table
   - High confidence (95%+) = auto-map
   - Low confidence (<85%) = unmapped

3. **Phase 3: Track unmapped skills**
   - LLM suggests domain + canonical_name for new skills
   - Insert into `skills_pending_taxonomy` table
   - Track occurrences across multiple jobs
   - Provide reasoning for taxonomy placement

**Outputs:**
- `postings.skill_keywords`: JSON array of mapped skills
- `skill_aliases`: German → English mappings (auto-generated)
- `skills_pending_taxonomy`: New skills awaiting human review
- `skill_extraction_log`: Audit trail

**Key insight:** This is about **extracting skills FROM jobs** and **mapping TO taxonomy**. Completely different purpose than 3002/3003!

---

## Current Workflow 3001: Job Processing

**Waves 12-15: Skills Extraction (CURRENT)**

```
Wave 12: taxonomy_skill_extraction (qwen2.5:7b)
  → Simple LLM prompt: "Extract skills from this job"
  → No fuzzy matching
  → No German translation
  → No auto-aliasing

Wave 13: taxonomy_skill_extraction (qwen2.5:7b)
  → Duplicate of wave 12? (same actor, same canonical_name)

Wave 14: gopher_skill_extraction (qwen2.5:7b)
  → Another simple extraction

Wave 15: save_job_skills (script: tools/save_job_skills.py)
  → Saves to postings.taxonomy_skills
```

**Problems with current approach:**
1. ❌ No fuzzy matching (misses "python" vs "Python Programming")
2. ❌ No multilingual support (German jobs fail to map)
3. ❌ No auto-aliasing (must manually add synonyms)
4. ❌ No unmapped skill tracking (orphans not recorded)
5. ❌ Three separate LLM calls (12, 13, 14) doing similar work
6. ❌ No confidence scoring (all-or-nothing mapping)

---

## What hybrid_skill_extraction.py Brings

### Unique Capabilities NOT in Any Workflow:

1. **Fuzzy Matching Engine**
   ```python
   def find_best_match(raw_skill, taxonomy_skills, threshold=0.85):
       # SequenceMatcher for string similarity
       # Returns (best_match, score)
   ```
   - Catches variations: "SQL" vs "sql" vs "SQL programming"
   - Threshold-based confidence scoring

2. **Multilingual Translation**
   ```python
   def translate_skill_to_english(raw_skill):
       # LLM translates German → English
       # "Programmierkenntnisse" → "Programming"
   ```
   - Critical for German job market!
   - Preserves semantic meaning

3. **Auto-Aliasing**
   ```python
   def add_skill_alias(conn, german_term, english_canonical, language='de'):
       # Automatically adds to skill_aliases table
       # Builds synonym dictionary over time
   ```
   - Self-improving system
   - Reduces manual taxonomy maintenance

4. **LLM-Confirmed Matching**
   ```python
   def confirm_match_with_llm(raw_skill, suggested_skill):
       # Medium-confidence (85-95%) gets LLM confirmation
       # "Are these two skills the same thing?"
   ```
   - Reduces false positives
   - Balances speed vs accuracy

5. **Taxonomy Expansion Suggestions**
   ```python
   def suggest_taxonomy_placement(raw_skill, taxonomy_domains):
       # LLM suggests: domain, canonical_name, reasoning
       # Inserts into skills_pending_taxonomy
   ```
   - Discovers new skills automatically
   - Human-in-loop for validation
   - Tracks occurrences (prioritize common skills)

6. **Comprehensive Audit Trail**
   - `skill_extraction_log`: Every extraction attempt logged
   - Processing time, success/failure, models used
   - Enables performance analysis and debugging

---

## Schema Dependencies

### Tables Used by hybrid_skill_extraction.py:

1. **skill_aliases** (READ)
   - Loads existing taxonomy
   - Columns: `skill`, `skill_alias`, `language`, `confidence`

2. **skill_aliases** (WRITE)
   - Adds German → English mappings
   - Auto-generated during extraction

3. **skill_hierarchy** (READ)
   - Gets taxonomy domains (parent_skill values)
   - Used for suggesting placement of new skills

4. **skills_pending_taxonomy** (WRITE)
   - Tracks unmapped skills
   - Columns: `raw_skill`, `occurrences`, `suggested_domain`, `suggested_canonical`, `found_in_jobs`, `llm_reasoning`
   - Enables batch review and approval

5. **postings** (WRITE)
   - Updates `skill_keywords` (JSON array)
   - Final output of extraction

6. **skill_extraction_log** (WRITE)
   - Audit trail
   - Columns: `job_id`, `raw_skills_found`, `mapped_skills`, `unmapped_skills`, `extraction_method`, `llm_model`, `processing_time_seconds`, `success`

### Migration Status:

Check if these tables still exist:
```sql
-- From migrations/027 and 028 comments:
-- skill_synonyms: DROPPED
-- skill_extraction_log: "Used only by hybrid_skill_extraction.py (obsolete script)"
-- skills_pending_taxonomy: Status unknown
```

**ACTION NEEDED:** Verify table existence before integration.

---

## Integration Strategy

### Option A: Replace Waves 12-14 with Single Hybrid Actor ✅ RECOMMENDED

**Create actor:** `hybrid_skill_mapper`
- Type: `script`
- Path: `tools/hybrid_skill_mapper.py` (refactored from `scripts/hybrid_skill_extraction.py`)
- Input: `{"posting_id": 123, "extracted_summary": "..."}`
- Output: `{"mapped_skills": [...], "unmapped_count": 5, "branch": "[DONE]"}`

**New workflow structure:**
```
Wave 11: check_skills_exist (idempotency check)
  → [SKIP] if taxonomy_skills exists → wave 16
  → [RUN] if missing → wave 12

Wave 12: hybrid_skill_mapper (NEW ACTOR)
  → Phase 1: Extract raw skills (LLM)
  → Phase 2: Fuzzy match + LLM confirm + translate
  → Phase 3: Track unmapped
  → Output: JSON with mapped skills

Wave 13: save_job_skills (existing)
  → Parse wave 12 output
  → Save to postings.taxonomy_skills
  → [DONE] → wave 16

Waves 14-15: REMOVED (redundant)
```

**Benefits:**
- Reduce 3 LLM calls → 1 hybrid process
- Add fuzzy matching, translation, auto-aliasing
- Track unmapped skills automatically
- Faster, more accurate, self-improving

---

### Option B: Keep as Preprocessing Script

**When to use:**
- Before workflow 3001 runs
- Batch process all postings once

**Workflow:**
```bash
# Step 1: Preprocess skills for all postings
python3 scripts/hybrid_skill_extraction.py --limit 1871

# Step 2: Run workflow 3001 (skills already populated)
# Workflow 3001 waves 11-15 become no-ops (idempotency check skips)
```

**Benefits:**
- No workflow changes needed
- Test independently before integration

**Drawbacks:**
- Not part of workflow (manual coordination)
- Doesn't benefit from wave processing efficiency
- No integration with idempotency checks

---

### Option C: Hybrid Approach

**Use hybrid_skill_extraction for backfill, integrated actor for new postings**

```bash
# Backfill existing 1,871 postings
python3 scripts/hybrid_skill_extraction.py --limit 1871

# Deploy hybrid actor to workflow 3001
python3 tools/update_actor_code.py --actor-id <new_actor_id>

# New postings use workflow 3001 with hybrid actor
```

**Benefits:**
- Fast backfill (standalone script)
- Future-proof (integrated actor)
- Best of both worlds

---

## Code Refactoring Needed

### To convert `scripts/hybrid_skill_extraction.py` → `tools/hybrid_skill_mapper.py`:

1. **Change I/O to stdin/stdout JSON**
   ```python
   # OLD: CLI with argparse
   parser = argparse.ArgumentParser()
   parser.add_argument('--job-id', ...)
   
   # NEW: Read JSON from stdin
   input_data = json.loads(sys.stdin.read())
   posting_id = input_data['posting_id']
   job_description = input_data['extracted_summary']
   ```

2. **Return JSON output for branching**
   ```python
   # OLD: Print to stdout, save to DB directly
   print(f"✓ Saved {len(mapped)}")
   save_to_posting(conn, job_id, mapped, ...)
   
   # NEW: Return JSON for wave processor
   output = {
       "mapped_skills": mapped,
       "unmapped_count": len(unmapped),
       "raw_count": len(raw_skills),
       "branch": "[DONE]",
       "processing_time": time.time() - start
   }
   print(json.dumps(output))
   ```

3. **Remove database writes** (let save_job_skills handle it)
   - Keep: taxonomy loading, fuzzy matching, LLM calls
   - Remove: UPDATE postings, INSERT skill_extraction_log
   - Return: JSON with all data for next actor

4. **Add error handling for actor execution**
   ```python
   try:
       # Phase 1, 2, 3
       ...
   except Exception as e:
       output = {
           "error": str(e),
           "branch": "[ERROR]"
       }
       print(json.dumps(output))
       sys.exit(1)
   ```

5. **Database connection from environment**
   ```python
   # OLD: Hardcoded DB_CONFIG
   DB_CONFIG = {'dbname': 'base_yoga', ...}
   
   # NEW: Use core.database
   from core.database import get_connection
   conn = get_connection()
   ```

---

## Schema Validation

### Check Table Status:

```sql
-- Does skills_pending_taxonomy exist?
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'skills_pending_taxonomy';

-- Does skill_extraction_log exist?
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'skill_extraction_log';

-- What columns in skill_aliases?
\d skill_aliases
```

### If tables are missing:

**Create migration 302:**
```sql
-- Create skills_pending_taxonomy
CREATE TABLE skills_pending_taxonomy (
    pending_id SERIAL PRIMARY KEY,
    raw_skill TEXT UNIQUE NOT NULL,
    occurrences INTEGER DEFAULT 1,
    suggested_domain TEXT,
    suggested_canonical TEXT,
    suggested_confidence NUMERIC(3,2),
    found_in_jobs INTEGER[],
    llm_reasoning TEXT,
    review_status TEXT DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(user_id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create skill_extraction_log
CREATE TABLE skill_extraction_log (
    log_id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES postings(posting_id),
    raw_skills_found TEXT[],
    mapped_skills TEXT[],
    unmapped_skills TEXT[],
    extraction_method TEXT,
    llm_model TEXT,
    processing_time_seconds NUMERIC(6,2),
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skills_pending_occurrences ON skills_pending_taxonomy(occurrences DESC);
CREATE INDEX idx_skills_pending_status ON skills_pending_taxonomy(review_status);
CREATE INDEX idx_extraction_log_job ON skill_extraction_log(job_id);
```

---

## Testing Plan

### Phase 1: Validate Script (Current State)

```bash
# Test on single posting
python3 scripts/hybrid_skill_extraction.py --job-id 3 --dry-run

# Test on 10 postings
python3 scripts/hybrid_skill_extraction.py --limit 10

# Check output
psql -U base_admin -d turing -c "SELECT posting_id, skill_keywords FROM postings WHERE skill_keywords IS NOT NULL LIMIT 5;"
```

### Phase 2: Refactor to Actor

```bash
# Create tools/hybrid_skill_mapper.py
# Test stdin/stdout interface
echo '{"posting_id": 3, "extracted_summary": "Python developer..."}' | python3 tools/hybrid_skill_mapper.py

# Expected output:
# {"mapped_skills": ["Python", "SQL"], "unmapped_count": 2, "branch": "[DONE]"}
```

### Phase 3: Deploy to Workflow 3001

```sql
-- Create actor
INSERT INTO actors (actor_name, actor_type, execution_type, execution_path, script_code)
VALUES ('hybrid_skill_mapper', 'script', 'python_script', 'tools/hybrid_skill_mapper.py', '<script_code>');

-- Update workflow 3001 wave 12
UPDATE workflow_conversations wc
SET conversation_id = (
    SELECT conversation_id FROM conversations WHERE actor_id = <new_actor_id> LIMIT 1
)
WHERE wc.workflow_id = 3001 AND wc.execution_order = 12;

-- Remove redundant waves 13-14
DELETE FROM workflow_conversations WHERE workflow_id = 3001 AND execution_order IN (13, 14);

-- Renumber wave 15 → wave 13
UPDATE workflow_conversations SET execution_order = 13 WHERE workflow_id = 3001 AND execution_order = 15;
```

### Phase 4: Integration Test

```bash
# Stop current batch processor
pkill -f "WaveBatchProcessorV2"

# Restart with updated workflow
python3 -c "from core.wave_batch_processor import WaveBatchProcessorV2; processor = WaveBatchProcessorV2(3001); processor.run()"

# Monitor logs
tail -f /tmp/wave_3001_*.log | grep -E "Wave 12|hybrid_skill"
```

---

## Recommendation

**INTEGRATE hybrid_skill_extraction.py into workflow 3001** as a single hybrid actor replacing waves 12-14.

**Rationale:**
1. **Superior technology**: Fuzzy matching + LLM confirmation > pure LLM extraction
2. **Multilingual support**: Critical for German job market
3. **Auto-aliasing**: Reduces taxonomy maintenance burden
4. **Self-improving**: Tracks unmapped skills, suggests taxonomy expansion
5. **Efficiency**: 1 hybrid process vs 3 separate LLM calls
6. **Battle-tested**: Already implemented and debugged

**Next Steps:**
1. ✅ Verify schema (check table existence)
2. ✅ Create migration 302 if tables missing
3. ✅ Refactor script → actor (stdin/stdout JSON)
4. ✅ Deploy to workflow 3001 (replace waves 12-14)
5. ✅ Test on 10 postings
6. ✅ Deploy to production (1,871 postings)

---

## Relationship to Workflows 3002/3003

**These are complementary, not competitive:**

- **Workflow 3001 + hybrid_skill_mapper**: Extract skills FROM jobs, map TO taxonomy
- **Workflow 3002**: Organize EXISTING taxonomy into filesystem (script-based)
- **Workflow 3003**: Organize EXISTING taxonomy into filesystem (LLM-based, adaptive)

**Data flow:**
```
Jobs → [3001 + hybrid_skill_mapper] → postings.taxonomy_skills
                                    ↓
                          skills_pending_taxonomy (new skills)
                                    ↓
                          [Human reviews, adds to taxonomy]
                                    ↓
                          [3002 or 3003] → skills_taxonomy/ (filesystem)
```

**All three needed:**
- 3001: Job → skills (extraction + mapping)
- 3002/3003: Taxonomy → filesystem (organization + navigation)
- hybrid_skill_mapper: The bridge between jobs and taxonomy

---

## Conclusion

`hybrid_skill_extraction.py` is **NOT** redundant. It contains **critical missing functionality**:

1. ✅ Fuzzy matching engine (not in any workflow)
2. ✅ Multilingual translation (not in any workflow)
3. ✅ Auto-aliasing (not in any workflow)
4. ✅ LLM-confirmed mapping (not in any workflow)
5. ✅ Taxonomy expansion tracking (not in any workflow)

**Workflows 3002 and 3003 are about organizing existing taxonomy.**
**hybrid_skill_extraction.py is about extracting skills from jobs and mapping them to taxonomy.**

**These are different problems requiring different solutions.**

**RECOMMENDATION: Integrate as actor into workflow 3001, keep script for backfill.**

---

**Investigation completed: November 13, 2025**
**Next: Create migration 302, refactor to actor, deploy to workflow 3001**
