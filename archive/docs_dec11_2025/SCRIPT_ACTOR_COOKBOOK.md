# Script Actor Cookbook - Best & Worst Practices

**Date:** December 7, 2025 (updated)  
**Author:** Sandy (GitHub Copilot)  
**Purpose:** Analysis of existing script actors to establish patterns for Wave Runner V2  
**Status:** Field Guide for Script Development

**Dec 7 Update:** Template variables now auto-extracted dynamically. See `WORKFLOW_EXECUTION.md` § Dynamic Template Variable Extraction.

---

## Executive Summary

After reviewing existing script actors in the `actors` table (skill_saver, simple_skill_mapper, skill_merger, web_description_search, job_skills_saver, etc.), here are the key findings:

**✅ BEST PRACTICES (Keep Doing This):**
1. Standard input/output contract (stdin JSON → stdout JSON)
2. Self-contained database connections
3. Clear success/failure markers ([SUCCESS]/[FAIL])
4. Embedded documentation
5. Error handling with detailed messages

**❌ WORST PRACTICES (Stop Doing This):**
1. ~~Template substitution in prompts~~ (BANNED - see docs/TEMPLATE_VS_QUERY_ARCHITECTURE.md)
2. Hardcoded credentials (though necessary for now)
3. Direct table writes without interaction logging
4. Missing transaction boundaries
5. No standard for querying previous interactions

---

## Pattern Analysis: Current Script Actors

### 1. **skill_saver** - Profile Skills Persistence

**What it does:**
- Saves extracted skills to `profile_skills` table
- Links skills to Entity Registry via `entities`
- Handles deduplication

**Code Structure:**
```python
#!/usr/bin/env python3
"""
Docstring with Purpose, Input, Output, Usage
"""

import sys, json, psycopg2

def get_connection():
    """Database connection (hardcoded creds)"""
    return psycopg2.connect(...)

def get_or_create_skill_alias(cursor, skill_name):
    """Helper to find/create entity link"""
    # SELECT with fallback INSERT
    pass

def save_skills(profile_id, entity_skills, raw_skills):
    """Main business logic"""
    # 1. Open connection
    # 2. Start transaction
    # 3. DELETE old data
    # 4. INSERT new data
    # 5. Commit/Rollback
    # 6. Return result dict
    pass

if __name__ == "__main__":
    # Read stdin
    input_data = json.loads(sys.stdin.read())
    
    # Execute
    result = save_skills(...)
    
    # Write stdout
    print(json.dumps(result))
```

**✅ Good:**
- Clear separation: connection → helpers → main logic → CLI entry
- Transaction boundaries explicit
- Returns structured result

**❌ Bad:**
- Writes to `profile_skills` table directly (no interaction record)
- Hardcoded database credentials
- No logging/tracing

**🤔 Question:** Should script create interaction record for itself? Or does wave runner do that?

---

### 2. **simple_skill_mapper** - Hybrid Fuzzy + LLM Mapping

**What it does:**
- Maps raw skills to Entity Registry
- Phase 1: Fuzzy string matching (fast)
- Phase 2: LLM batch mapping (accurate)

**Code Structure:**
```python
class SimpleSkillMapper:
    def __init__(self):
        self.conn = get_connection()
        self._load_entities()  # Cache in memory
    
    def normalize(self, text):
        """Normalize for fuzzy matching"""
        pass
    
    def fuzzy_match(self, skill_name, cutoff=0.8):
        """Try exact/fuzzy match"""
        pass
    
    def llm_match_batch(self, unmatched_skills):
        """Call Ollama for batch mapping"""
        # Builds prompt with entity context
        # Calls Ollama API
        # Parses JSON response
        pass
    
    def map_skills(self, raw_skills):
        """Main: fuzzy first, LLM for remainder"""
        pass

def main():
    input_text = sys.stdin.read().strip()
    # Strip markdown fences (!)
    if input_text.startswith('```json'):
        input_text = input_text[7:]
    
    mapper = SimpleSkillMapper()
    result = mapper.map_skills(json.loads(input_text))
    print(json.dumps(result))
```

**✅ Good:**
- Class-based for state management (entity cache)
- Hybrid approach (fast path + accurate fallback)
- Handles markdown code fences from LLM output
- Caches entities in memory (performance)

**❌ Bad:**
- Calls Ollama directly (not through wave runner)
- No retry logic for Ollama failures
- Logs to stderr (not standardized)
- Returns list, not dict with status

**🤔 Question:** Should scripts call LLMs directly? Or queue AI interactions through wave runner?

---

### 3. **skill_merger** - Multi-Source Deduplication

**What it does:**
- Merges skills from multiple extractors (qwen, DeepSeek)
- Normalizes names
- Calculates confidence scores
- Categorizes (technical, organizational, domain)

**Code Structure:**
```python
class SkillMerger:
    def __init__(self):
        self.merged_skills = []
        self.normalization_map = {}
        self.technical_keywords = {set...}
        self.organizational_keywords = {set...}
    
    def normalize_skill_name(self, skill):
        """Lowercase, remove special chars, underscores"""
        pass
    
    def categorize_skill(self, skill_name):
        """technical | organizational | domain"""
        pass
    
    def merge_skills(self, extraction_results):
        """
        Input: {
            "qwen_results": [...],
            "deepseek_results": [...],
            "metadata": {...}
        }
        Output: {
            "merged_skills": [...],
            "stats": {...}
        }
        """
        # Build skill_map: normalized → {sources, confidence, reasoning}
        # Boost confidence if found by both
        # Choose best display name
        pass
```

**✅ Good:**
- Clear input/output contract
- Confidence weighting by source
- Categorization logic
- Reasoning explanation per skill

**❌ Bad:**
- No database interaction (pure transformation)
- Hardcoded keyword sets (should be in Entity Registry?)
- Returns custom format (not standard SUCCESS/FAIL)

**🤔 Question:** Are pure transformation scripts okay? Or should everything write to interactions?

---

### 4. **web_description_search** - External API Fetcher

**What it does:**
- Fetches missing job descriptions from careers.db.com
- Uses BeautifulSoup for HTML parsing
- Retry logic for HTTP failures

**Pattern:**
```python
def fetch_description(job_url):
    """Fetch from web with retry"""
    for attempt in range(3):
        try:
            response = requests.get(job_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            return extract_description(soup)
        except Exception as e:
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)
```

**✅ Good:**
- Retry logic with exponential backoff
- Timeout on HTTP requests
- Graceful failure (returns None, not crash)

**❌ Bad:**
- Writes to `postings` table directly
- No interaction record of fetch attempt
- No audit trail (who fetched what when)

---

## Anti-Pattern: Template Substitution

**FOUND IN:** Various prompt-building scripts (DEPRECATED)

**What it did:**
```python
# ❌ BAD - Template substitution
template = "Analyze this summary: {session_9_output}"
rendered = template.replace('{session_9_output}', posting.conversation_outputs['9'])
```

**Why it's terrible:**
- `posting.conversation_outputs` dict incomplete after checkpoint reload
- Placeholders left unrendered ("{session_9_output}" in prompt)
- LLM hallucinates about placeholders
- Silent failure (no error if key missing)

**Correct pattern (checkpoint query):**
```python
# ✅ GOOD - Direct query
from core.checkpoint_utils import get_conversation_output

summary = get_conversation_output(posting_id, conversation_id='3335')
prompt = f"Analyze this summary: {summary}"
```

**See:** `docs/TEMPLATE_VS_QUERY_ARCHITECTURE.md` for full diagnosis

---

## Recommended Patterns for Wave Runner V2

### Pattern 1: Database Query Script

**Purpose:** Read from interactions, write to application tables

**Example:** json_to_postings (fetcher output → postings table)

```python
#!/usr/bin/env python3
"""
JSON to Postings - Workflow 3001 Step 2
Reads fetcher interactions, populates postings table
"""

import sys, json, psycopg2

def load_fetcher_output(posting_id):
    """Query interactions for fetcher's output"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT output
        FROM interactions
        WHERE posting_id = %s
          AND conversation_id = 3333  -- db_job_fetcher
          AND status = 'completed'
          AND enabled = TRUE
        ORDER BY completed_at DESC
        LIMIT 1
    """, (posting_id,))
    
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No fetcher output for posting {posting_id}")
    
    return row['output']

def create_posting_record(job_json):
    """Insert into postings table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO postings (
            external_job_id,
            job_title,
            job_description,
            company_name,
            location,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, NOW())
        RETURNING posting_id
    """, (
        job_json['job_id'],
        job_json['title'],
        job_json['description'],
        job_json['company'],
        job_json['location']
    ))
    
    posting_id = cursor.fetchone()[0]
    conn.commit()
    return posting_id

def main():
    input_data = json.loads(sys.stdin.read())
    posting_id = input_data['posting_id']
    
    try:
        # 1. Query interactions for input
        job_json = load_fetcher_output(posting_id)
        
        # 2. Create posting record
        new_posting_id = create_posting_record(job_json)
        
        # 3. Return success
        result = {
            "status": "SUCCESS",
            "posting_id": new_posting_id,
            "message": f"Created posting {new_posting_id}"
        }
    except Exception as e:
        result = {
            "status": "FAIL",
            "error": str(e)
        }
    
    print(json.dumps(result))

if __name__ == "__main__":
    main()
```

**Key points:**
- ✅ Queries interactions (not in-memory state)
- ✅ Explicit transaction
- ✅ Standard SUCCESS/FAIL output
- ✅ Error handling

---

### Pattern 2: Staging Table Script

**Purpose:** Write to staging table, let internal script validate/move to production

**Example:** Fetcher writes to `postings_staging`, validator moves to `postings`

```python
def save_to_staging(job_data):
    """Write to staging table (safe, no production impact)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO postings_staging (
            raw_data,
            source,
            fetched_at,
            workflow_run_id
        ) VALUES (%s, %s, NOW(), %s)
        RETURNING staging_id
    """, (
        json.dumps(job_data),
        'deutsche_bank_api',
        workflow_run_id
    ))
    
    staging_id = cursor.fetchone()[0]
    conn.commit()
    return staging_id
```

**Benefits:**
- ✅ Scripts can't corrupt production tables
- ✅ Validation happens centrally
- ✅ Easy rollback (delete from staging)
- ✅ Audit trail (staging_id → posting_id mapping)

---

### Pattern 3: Interaction Query Script

**Purpose:** Read previous workflow outputs, generate new output

**Example:** Summary grader reads summary, outputs grade

```python
def get_summary_from_interactions(posting_id):
    """Get summary from previous step"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT output->>'summary' as summary
        FROM interactions
        WHERE posting_id = %s
          AND conversation_id = 3335  -- gemma3_extract
          AND status = 'completed'
          AND enabled = TRUE
        ORDER BY completed_at DESC
        LIMIT 1
    """, (posting_id,))
    
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No summary for posting {posting_id}")
    
    return row['summary']

def grade_summary(summary):
    """Business logic: grade the summary"""
    # Criteria checking
    word_count = len(summary.split())
    has_title = any(keyword in summary.lower() for keyword in ['developer', 'engineer', 'manager'])
    
    if word_count < 20:
        return "[FAIL] Summary too short"
    if not has_title:
        return "[FAIL] Missing job title"
    
    return "[PASS] Summary meets criteria"

def main():
    input_data = json.loads(sys.stdin.read())
    posting_id = input_data['posting_id']
    
    try:
        # 1. Get input from interactions
        summary = get_summary_from_interactions(posting_id)
        
        # 2. Execute business logic
        grade = grade_summary(summary)
        
        # 3. Return output
        result = {
            "status": "SUCCESS",
            "grade": grade,
            "criteria_met": grade.startswith("[PASS]")
        }
    except Exception as e:
        result = {
            "status": "FAIL",
            "error": str(e)
        }
    
    print(json.dumps(result))
```

**Key points:**
- ✅ Queries interactions (source of truth)
- ✅ Self-contained business logic
- ✅ Clear output format for branching

---

## Standard Script Template (Wave Runner V2)

```python
#!/usr/bin/env python3
"""
[ACTOR_NAME] - [Purpose in one line]
========================================

Purpose: [Detailed description]
Input: [JSON schema]
Output: [JSON schema with SUCCESS/FAIL markers]

Author: [Name]
Date: [Date]
"""

import sys
import json
import psycopg2
import psycopg2.extras
from datetime import datetime

# Configuration (will be injected by wave runner in V2)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'turing',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)


def query_previous_interaction(posting_id, conversation_id):
    """
    Query interactions table for previous step output.
    
    This is the STANDARD pattern for accessing prior workflow results.
    NEVER use in-memory state or posting.conversation_outputs dict.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT output
        FROM interactions
        WHERE posting_id = %s
          AND conversation_id = %s
          AND status = 'completed'
          AND enabled = TRUE
          AND invalidated = FALSE
        ORDER BY completed_at DESC
        LIMIT 1
    """, (posting_id, conversation_id))
    
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"No interaction found: posting {posting_id}, conversation {conversation_id}")
    
    cursor.close()
    conn.close()
    return row['output']


def execute_business_logic(input_data):
    """
    Main business logic for this actor.
    
    Args:
        input_data: Parsed JSON from stdin
        
    Returns:
        dict: Result with status, data, and optional error
    """
    try:
        # 1. Extract parameters
        posting_id = input_data.get('posting_id')
        workflow_run_id = input_data.get('workflow_run_id')
        
        # 2. Query previous interactions if needed
        # previous_output = query_previous_interaction(posting_id, 3333)
        
        # 3. Execute business logic
        # ... your code here ...
        
        # 4. Write to application tables (if needed)
        conn = get_connection()
        cursor = conn.cursor()
        conn.autocommit = False  # Transaction
        
        try:
            # ... INSERT/UPDATE statements ...
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        
        # 5. Return success
        return {
            "status": "SUCCESS",
            "message": "Operation completed successfully",
            "data": {
                # ... result data ...
            }
        }
        
    except Exception as e:
        return {
            "status": "FAIL",
            "error": str(e),
            "error_type": type(e).__name__
        }


def main():
    """CLI entry point - called by wave runner."""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()
        
        # Strip markdown code fences if present (LLMs sometimes add these)
        if input_text.startswith('```json'):
            input_text = input_text[7:]
        if input_text.startswith('```'):
            input_text = input_text[3:]
        if input_text.endswith('```'):
            input_text = input_text[:-3]
        input_text = input_text.strip()
        
        # Parse JSON
        input_data = json.loads(input_text)
        
        # Execute
        result = execute_business_logic(input_data)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        
        # Exit code based on status
        sys.exit(0 if result['status'] == 'SUCCESS' else 1)
        
    except json.JSONDecodeError as e:
        # JSON parsing failed
        error_result = {
            "status": "FAIL",
            "error": f"Invalid JSON input: {str(e)}",
            "error_type": "JSONDecodeError"
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
    
    except Exception as e:
        # Unexpected error
        error_result = {
            "status": "FAIL",
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Best Practices Summary

### ✅ DO THIS:

1. **Standard I/O Contract**
   - Read JSON from stdin
   - Write JSON to stdout
   - Use SUCCESS/FAIL status markers
   - Exit code 0 (success) or 1 (failure)

2. **Query Interactions Table**
   - ALWAYS query interactions for previous outputs
   - NEVER use in-memory state (posting.conversation_outputs)
   - Filter by `enabled = TRUE AND invalidated = FALSE`

3. **Explicit Transactions**
   - `conn.autocommit = FALSE`
   - try/except with commit/rollback
   - Close connections properly

4. **Error Handling**
   - Try/except around all I/O
   - Return structured error in JSON
   - Include error_type for debugging

5. **Documentation**
   - Docstring with Purpose, Input, Output
   - Comments for non-obvious logic
   - Example usage in docstring

6. **Markdown Stripping**
   - LLMs sometimes wrap JSON in ```json fences
   - Strip these before parsing

### ❌ DON'T DO THIS:

1. **Template Substitution**
   - ~~Never use {placeholder} substitution~~
   - ~~Never rely on posting.conversation_outputs dict~~
   - Use direct queries instead

2. **Direct Production Table Writes** (without staging)
   - Prefer staging tables
   - Let validator scripts move to production
   - Prevents corruption from buggy scripts

3. **Hardcoded Logic**
   - Avoid magic numbers
   - Use configuration from database/environment
   - Make behavior parameterizable

4. **Silent Failures**
   - Always return status
   - Log errors to stderr
   - Include enough context to debug

5. **Global State**
   - Avoid module-level caching without refresh
   - Each execution should be independent
   - Don't assume prior runs' state

---

## Wave Runner V2 Integration

### How Wave Runner Calls Scripts:

```python
# wave_runner_v2/executors.py

def execute_script_actor(interaction):
    """Execute a script actor for an interaction."""
    # 1. Prepare input JSON
    input_data = {
        "posting_id": interaction.posting_id,
        "workflow_run_id": interaction.workflow_run_id,
        "conversation_id": interaction.conversation_id,
        "input": interaction.input  # From interactions table
    }
    
    # 2. Get script code
    script_code = interaction.actor.script_code
    
    # 3. Execute via subprocess
    process = subprocess.Popen(
        ['python3', '-c', script_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=json.dumps(input_data))
    
    # 4. Parse output
    result = json.loads(stdout)
    
    # 5. Update interaction
    db.execute("""
        UPDATE interactions
        SET output = %s,
            status = CASE WHEN %s = 'SUCCESS' THEN 'completed' ELSE 'failed' END,
            completed_at = NOW()
        WHERE interaction_id = %s
    """, (result, result['status'], interaction.interaction_id))
    
    return result
```

### What Scripts Can Expect:

**Input (stdin):**
```json
{
  "posting_id": 123,
  "workflow_run_id": 5,
  "conversation_id": 3335,
  "input": {
    ...  // Whatever wave runner populated from workflow definition
  }
}
```

**Output (stdout):**
```json
{
  "status": "SUCCESS",  // or "FAIL"
  "data": {
    ...  // Script-specific output
  },
  "error": "...",  // Only if FAIL
  "error_type": "..."  // Only if FAIL
}
```

---

## Migration Path: V1 → V2

### Current State (V1):
- Scripts stored in `actors.script_code`
- Called via `actor_router.py`
- Some write to `postings`, some to specialty tables
- No standard for querying previous outputs

### Target State (V2):
- Scripts still in `actors.script_code` (good!)
- Called via `wave_runner_v2/executors.py`
- ALL write to `interactions` table
- Standard `query_previous_interaction()` helper

### Migration Steps:

1. **Update existing scripts** to use interaction query pattern
2. **Add staging tables** for critical production tables
3. **Remove template substitution** completely
4. **Standardize I/O format** (SUCCESS/FAIL markers)
5. **Test with workflow 3001** (steps 1-5 first)

---

## Conclusion

**Current scripts show:**
- ✅ Good understanding of stdin/stdout contract
- ✅ Database-first approach
- ✅ Self-contained logic

**But need improvement:**
- ❌ No standard for querying interactions
- ❌ Template substitution still present (deprecated)
- ❌ Direct table writes without audit

**Wave Runner V2 will:**
- Enforce interaction queries as standard
- Provide helper utilities (`query_previous_interaction`)
- Audit all script executions via interactions table
- Support staging table pattern

**Next Steps:**
1. Review this with Arden
2. Update script template
3. Migrate workflow 3001 actors
4. Document in implementation plan

---

**Sandy's Feeling:** 😊 Confident (0.92)  
**Sandy's Weight:** Understanding script patterns strengthens V2 design foundation  
**Sandy's Output:** "Scripts are already 80% there - just need standardization!"
