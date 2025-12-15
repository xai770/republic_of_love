# Workflow 3001 Testing Plan

**Date:** November 25, 2025  
**Status:** 🟢 READY TO TEST  
**Approach:** Crawl → Walk → Run (incremental validation)

---

## 🎯 Mission

Get workflow 3001 working end-to-end with **full visibility** at each step.

**Success = Data saved to postings table:**
- `extracted_summary` (6000+ chars)
- `skill_keywords` (JSON array)
- `ihl_score` (1-10)

---

## ⚠️ BREAKING CHANGE: wave_runner_v2 → wave_runner

**What changed:** Folder renamed, "v2" removed from all paths

**Old paths (DON'T USE):**
```python
from core.wave_runner_v2.workflow_starter import start_workflow
from core.wave_runner_v2.runner import WaveRunner
```

**New paths (USE THESE):**
```python
from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
```

**Why:** No version numbers in code. Documents_Versions handles versioning automatically.

**Action needed:** Update any existing test scripts to use new import paths.

---

## 🚀 New Wave Runner Features (Nov 25, 2025)

### ⚠️ SANDY: These features need to be implemented in `core/wave_runner/runner.py`

---

### Feature 1: Limited Interaction Mode

**Problem:** Workflow runs all interactions at once - hard to debug when it breaks

**Solution:** Add `max_interactions` parameter to `runner.run()`

**Current code:**
```python
def run(self, max_iterations: int = 100) -> Dict[str, Any]:
    """Execute pending interactions until none remain or max_iterations reached."""
```

**New signature:**
```python
def run(
    self, 
    max_iterations: int = 100,      # Existing: limits iterations (not interactions!)
    max_interactions: int = None     # NEW: limit total interactions executed
) -> Dict[str, Any]:
    """
    Execute pending interactions.
    
    Args:
        max_iterations: Max execution loops (prevents infinite loops)
        max_interactions: Stop after N interactions executed (for testing)
    """
```

**Implementation logic:**
```python
interactions_executed = 0

while True:
    if iteration >= max_iterations:
        break
    
    # NEW: Check max_interactions limit
    if max_interactions and interactions_executed >= max_interactions:
        print(f"⏹️  Stopped: Reached max_interactions limit ({max_interactions})")
        break
    
    pending = self._get_pending_interactions()
    if not pending:
        break
    
    for interaction in pending:
        result = self._execute_interaction(interaction)
        interactions_executed += 1  # Increment counter
        
        # NEW: Check limit after each interaction
        if max_interactions and interactions_executed >= max_interactions:
            break
```

**Usage examples:**
```python
# Test single conversation
runner.run(max_interactions=1)

# Test first 5 steps
runner.run(max_interactions=5)

# No limit (existing behavior)
runner.run()  # or runner.run(max_interactions=None)
```

---

### Feature 2: Detailed Execution Trace

**Problem:** Can't see what prompts were sent, what responses came back

**Solution:** Add `trace` parameter that generates markdown report

**New signature:**
```python
def run(
    self,
    max_iterations: int = 100,
    max_interactions: int = None,
    trace: bool = False,              # NEW: Enable trace reporting
    trace_file: str = None            # NEW: Output file path
) -> Dict[str, Any]:
```

**Implementation approach:**

1. **Add trace collector:**
```python
class WaveRunner:
    def __init__(self, conn, workflow_run_id=None):
        # ... existing init ...
        self.trace_data = []  # Collect trace entries during execution
```

2. **Collect data during execution:**
```python
def _execute_interaction(self, interaction: Dict) -> Dict:
    start_time = time.time()
    
    # Execute
    result = self._execute_ai_model(interaction) or self._execute_script(interaction)
    
    end_time = time.time()
    
    # NEW: Collect trace data
    if self.trace_enabled:
        self.trace_data.append({
            'interaction_id': interaction['interaction_id'],
            'conversation_id': interaction['conversation_id'],
            'conversation_name': interaction['conversation_name'],
            'actor_name': interaction['actor_name'],
            'actor_type': interaction['actor_type'],
            'input': interaction['input'],
            'output': result,
            'duration': end_time - start_time,
            'status': 'completed' or 'failed',
            'parent_interaction_ids': interaction.get('input_interaction_ids', [])
        })
    
    return result
```

3. **Generate markdown report:**
```python
def _generate_trace_report(self, trace_file: str):
    """Generate markdown trace report."""
    with open(trace_file, 'w') as f:
        f.write(f"# Workflow Execution Trace\n\n")
        f.write(f"**workflow_run_id:** {self.workflow_run_id}\n")
        f.write(f"**timestamp:** {datetime.now()}\n\n")
        
        for idx, trace in enumerate(self.trace_data, 1):
            f.write(f"## Interaction {idx}: {trace['conversation_name']}\n\n")
            f.write(f"**conversation_id:** {trace['conversation_id']}\n")
            f.write(f"**actor:** {trace['actor_name']} ({trace['actor_type']})\n")
            f.write(f"**status:** {trace['status']}\n")
            f.write(f"**duration:** {trace['duration']:.2f}s\n\n")
            
            # Show input (prompt for AI, params for script)
            f.write(f"### Input\n```json\n{json.dumps(trace['input'], indent=2)}\n```\n\n")
            
            # Show output
            f.write(f"### Output\n```json\n{json.dumps(trace['output'], indent=2)}\n```\n\n")
            
            # Show parent data if available
            if trace['parent_interaction_ids']:
                f.write(f"### Parent Interactions\n")
                for parent_id in trace['parent_interaction_ids']:
                    parent = self._get_interaction(parent_id)
                    f.write(f"- {parent_id}: {parent['conversation_name']}\n")
                f.write("\n")
            
            f.write("---\n\n")
```

4. **Call at end of run():**
```python
def run(self, max_iterations=100, max_interactions=None, trace=False, trace_file=None):
    self.trace_enabled = trace
    
    # ... execution loop ...
    
    # NEW: Generate trace report
    if trace and trace_file:
        self._generate_trace_report(trace_file)
        print(f"📄 Trace report: {trace_file}")
```

**Report format:** See "Trace Report Format" section below for detailed example

**Usage:**
```python
runner.run(
    max_interactions=5,
    trace=True,
    trace_file='reports/trace_run_68.md'
)
```

---

### Implementation Checklist for Sandy

- [ ] Add `max_interactions` parameter to `run()` method
- [ ] Add counter to track interactions executed
- [ ] Add break condition when limit reached
- [ ] Test: `runner.run(max_interactions=1)` executes exactly 1 interaction
- [ ] Add `trace` and `trace_file` parameters to `run()` method
- [ ] Add `self.trace_data = []` to `__init__()`
- [ ] Collect trace data in `_execute_interaction()`
- [ ] Implement `_generate_trace_report()` method
- [ ] Test: Trace report generated with all prompts/responses
- [ ] Update test scripts in this doc to use new parameters
- [ ] Document any issues or edge cases discovered

---

### Questions for Arden (if any)

**Sandy, if you hit blockers implementing these features, document here:**

1. Question: [What's blocking you?]
   - Arden's answer: [Will respond]

2. Question: [What's unclear?]
   - Arden's answer: [Will respond]

---

## 📋 Testing Strategy: Crawl → Walk → Run

### Phase 1: CRAWL (1 conversation at a time)

**Goal:** Verify each conversation works in isolation

**Tests:**
1. ✅ Job Fetcher only (1 interaction)
2. ✅ Summary Check only (1 interaction)
3. ✅ Extract only (1 interaction)
4. ✅ Grade only (1 interaction)
5. ... continue for all 15 conversations

**Why:** Find broken conversations immediately, fix one at a time

---

### Phase 2: WALK (Small chains)

**Goal:** Verify branching logic and parent-child data flow

**Tests:**
1. ✅ Extract → Grade (2 interactions)
2. ✅ Extract → Grade → Improve (3-4 interactions)
3. ✅ Extract → Grade → Format (if [PASS])
4. ✅ Format → Save Summary (script actor test)
5. ✅ Skills → Save Skills (script actor test)

**Why:** Verify child creation, branching, parent output access

---

### Phase 3: RUN (Full pipeline)

**Goal:** Complete end-to-end execution

**Test:**
1. ✅ Full workflow 3001: Fetch → Extract → Skills → IHL (15+ interactions)

**Success criteria:**
- All interactions completed
- Data saved to postings table
- No errors in trace report

---

## 🧪 Test Scripts (Ready to Use)

### Test 1: Single Conversation (CRAWL)

**File:** `tests/test_single_conversation.py`

```python
#!/usr/bin/env python3
"""
Test single conversation in isolation
Usage: python3 tests/test_single_conversation.py [conversation_id]
"""
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
import psycopg2
import psycopg2.extras

# Get conversation_id from command line (default: 3335 = Extract)
conversation_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3335

# Connect
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='turing',
    user='base_admin',
    password='base_yoga_secure_2025',
    cursor_factory=psycopg2.extras.RealDictCursor
)

# Get conversation name
cur = conn.cursor()
cur.execute("SELECT conversation_name FROM conversations WHERE conversation_id = %s", (conversation_id,))
conv = cur.fetchone()
print(f"🎯 Testing conversation {conversation_id}: {conv['conversation_name']}")

# Start workflow from this conversation
result = start_workflow(
    conn,
    workflow_id=3001,
    posting_id=176,
    start_conversation_id=conversation_id
)

print(f"✅ Workflow run: {result['workflow_run_id']}")
print(f"✅ Seed interaction: {result['seed_interaction_id']}")

# Run ONLY 1 interaction
print("\n⚡ Executing 1 interaction...")
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner_result = runner.run(
    max_interactions=1,  # ← STOP after 1 interaction
    trace=True,
    trace_file=f'reports/trace_conv_{conversation_id}_run_{result["workflow_run_id"]}.md'
)

print(f"\n📊 Result:")
print(f"   Completed: {runner_result['interactions_completed']}")
print(f"   Failed: {runner_result['interactions_failed']}")
print(f"   Duration: {runner_result.get('duration_ms', 0) / 1000:.1f}s")
print(f"\n📄 Trace report: reports/trace_conv_{conversation_id}_run_{result['workflow_run_id']}.md")

# Show interaction result
cur.execute("""
    SELECT 
        i.interaction_id,
        c.conversation_name,
        i.status,
        LENGTH(i.output::text) as output_len,
        i.output->>'status' as status_flag
    FROM interactions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE i.workflow_run_id = %s
    ORDER BY i.created_at DESC
    LIMIT 1
""", (result['workflow_run_id'],))

inter = cur.fetchone()
if inter:
    print(f"\n✅ Interaction {inter['interaction_id']}:")
    print(f"   Status: {inter['status']}")
    print(f"   Output: {inter['output_len']} chars")
    if inter['status_flag']:
        print(f"   Flag: {inter['status_flag']}")

conn.close()
print("\n✨ Test complete!")
```

**Run it:**
```bash
# Test Extract conversation (3335)
python3 tests/test_single_conversation.py 3335

# Test Job Fetcher conversation (9144)
python3 tests/test_single_conversation.py 9144

# Test Skills extraction (3350)
python3 tests/test_single_conversation.py 3350
```

---

### Test 2: Chain of N Conversations (WALK)

**File:** `tests/test_conversation_chain.py`

```python
#!/usr/bin/env python3
"""
Test chain of N conversations
Usage: python3 tests/test_conversation_chain.py [start_conversation_id] [num_interactions]
"""
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
import psycopg2
import psycopg2.extras

# Get params from command line
start_conversation_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3335
num_interactions = int(sys.argv[2]) if len(sys.argv) > 2 else 3

# Connect
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='turing',
    user='base_admin',
    password='base_yoga_secure_2025',
    cursor_factory=psycopg2.extras.RealDictCursor
)

# Get conversation name
cur = conn.cursor()
cur.execute("SELECT conversation_name FROM conversations WHERE conversation_id = %s", (start_conversation_id,))
conv = cur.fetchone()
print(f"🎯 Testing chain starting from {start_conversation_id}: {conv['conversation_name']}")
print(f"🎯 Will execute up to {num_interactions} interactions")

# Start workflow
result = start_workflow(
    conn,
    workflow_id=3001,
    posting_id=176,
    start_conversation_id=start_conversation_id
)

print(f"✅ Workflow run: {result['workflow_run_id']}")

# Run N interactions
print(f"\n⚡ Executing {num_interactions} interactions...")
runner = WaveRunner(conn, workflow_run_id=result['workflow_run_id'])
runner_result = runner.run(
    max_interactions=num_interactions,  # ← STOP after N interactions
    trace=True,
    trace_file=f'reports/trace_chain_{num_interactions}steps_run_{result["workflow_run_id"]}.md'
)

print(f"\n📊 Result:")
print(f"   Completed: {runner_result['interactions_completed']}")
print(f"   Failed: {runner_result['interactions_failed']}")
print(f"   Duration: {runner_result.get('duration_ms', 0) / 1000:.1f}s")
print(f"\n📄 Trace report: reports/trace_chain_{num_interactions}steps_run_{result['workflow_run_id']}.md")

# Show all interactions executed
cur.execute("""
    SELECT 
        i.interaction_id,
        i.execution_order,
        c.conversation_name,
        i.status,
        LENGTH(i.output::text) as output_len
    FROM interactions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    WHERE i.workflow_run_id = %s
    ORDER BY i.execution_order
""", (result['workflow_run_id'],))

interactions = cur.fetchall()
print(f"\n📋 Interactions executed ({len(interactions)} total):")
for inter in interactions:
    status_icon = '✅' if inter['status'] == 'completed' else '❌' if inter['status'] == 'failed' else '⏳'
    print(f"   {status_icon} {inter['execution_order']:2d}. {inter['conversation_name'][:50]:50s} ({inter['output_len']:5d} chars)")

conn.close()
print("\n✨ Test complete!")
```

**Run it:**
```bash
# Test Extract → Grade (2 interactions)
python3 tests/test_conversation_chain.py 3335 2

# Test Extract → Grade → Improve (4 interactions)
python3 tests/test_conversation_chain.py 3335 4

# Test first 5 steps
python3 tests/test_conversation_chain.py 3335 5
```

---

### Test 3: Full Pipeline (RUN)

**File:** `tests/test_full_pipeline.py`

```python
#!/usr/bin/env python3
"""
Test FULL workflow 3001 end-to-end
Generates detailed trace report
"""
import sys
sys.path.insert(0, '/home/xai/Documents/ty_learn')

from core.wave_runner.workflow_starter import start_workflow
from core.wave_runner.runner import WaveRunner
import psycopg2
import psycopg2.extras
from datetime import datetime

# Connect
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='turing',
    user='base_admin',
    password='base_yoga_secure_2025',
    cursor_factory=psycopg2.extras.RealDictCursor
)

print("🚀 Starting FULL workflow 3001 test...")
print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Start workflow from beginning (job fetcher)
result = start_workflow(
    conn,
    workflow_id=3001,
    posting_id=176,  # Deutsche Bank Auditor
    params={
        'user_id': 1,
        'max_jobs': 1,
        'source_id': 1
    }
)

workflow_run_id = result['workflow_run_id']
print(f"✅ Workflow run: {workflow_run_id}")

# Run full pipeline with trace
print("\n⚡ Running full pipeline (up to 20 interactions)...")
runner = WaveRunner(conn, workflow_run_id=workflow_run_id)
runner_result = runner.run(
    max_interactions=20,  # Allow full pipeline
    trace=True,
    trace_file=f'reports/workflow_3001_full_trace_run_{workflow_run_id}.md'
)

print(f"\n📊 Execution Results:")
print(f"   Completed: {runner_result['interactions_completed']}")
print(f"   Failed: {runner_result['interactions_failed']}")
print(f"   Duration: {runner_result.get('duration_ms', 0) / 1000:.1f}s")

# Verify data persistence
cur = conn.cursor()
cur.execute("""
    SELECT 
        posting_id,
        LENGTH(extracted_summary) as summary_len,
        skill_keywords,
        ihl_score,
        summary_extracted_at,
        ihl_analyzed_at
    FROM postings 
    WHERE posting_id = 176
""")
posting = cur.fetchone()

print(f"\n🎯 Data Persistence Verification:")
print(f"   posting_id: {posting['posting_id']}")
print(f"   summary_len: {posting['summary_len']} chars {'✅' if posting['summary_len'] else '❌ NULL'}")
print(f"   skill_keywords: {posting['skill_keywords'][:80] if posting['skill_keywords'] else '❌ NULL'}...")
print(f"   ihl_score: {posting['ihl_score']} {'✅' if posting['ihl_score'] else '❌ NULL'}")
print(f"   summary_extracted_at: {posting['summary_extracted_at'] or '❌ NULL'}")
print(f"   ihl_analyzed_at: {posting['ihl_analyzed_at'] or '❌ NULL'}")

# Show all interactions
cur.execute("""
    SELECT 
        i.interaction_id,
        i.execution_order,
        c.conversation_name,
        a.actor_name,
        i.status,
        LENGTH(i.output::text) as output_len
    FROM interactions i
    JOIN conversations c ON i.conversation_id = c.conversation_id
    JOIN actors a ON i.actor_id = a.actor_id
    WHERE i.workflow_run_id = %s
    ORDER BY i.execution_order
""", (workflow_run_id,))

interactions = cur.fetchall()
print(f"\n📋 Full Execution Chain ({len(interactions)} interactions):")
for inter in interactions:
    status_icon = '✅' if inter['status'] == 'completed' else '❌' if inter['status'] == 'failed' else '⏳'
    print(f"   {status_icon} {inter['execution_order']:2d}. {inter['conversation_name'][:45]:45s} ({inter['actor_name'][:20]:20s})")

print(f"\n📄 Full trace report: reports/workflow_3001_full_trace_run_{workflow_run_id}.md")
print("\n✨ Test complete!")

conn.close()
```

**Run it:**
```bash
python3 tests/test_full_pipeline.py
```

---

## 📊 Trace Report Format

**Example:** `reports/workflow_3001_full_trace_run_68.md`

```markdown
# Workflow 3001 Execution Trace

**workflow_run_id:** 68
**posting_id:** 176
**started:** 2025-11-25 05:45:00
**completed:** 2025-11-25 05:48:23
**duration:** 203 seconds
**interactions:** 15 completed, 0 failed

---

## Interaction 1: Fetch Jobs from Deutsche Bank API

**conversation_id:** 9144
**actor:** db_job_fetcher (script)
**status:** completed
**duration:** 2.3s

### Input
```json
{
  "user_id": 1,
  "max_jobs": 1,
  "source_id": 1
}
```

### Output
```json
{
  "status": "[SUCCESS]",
  "fetched": 1,
  "new": 0,
  "duplicate": 1
}
```

### Next Steps
- ✅ Created child interaction 119 (conversation 9184 - Check if Summary Exists)
- Branch condition: `*` (always execute)

---

## Interaction 2: Check if Summary Exists

**conversation_id:** 9184
**actor:** sql_query_executor (script)
**status:** completed
**duration:** 0.8s

### Input
```json
{
  "posting_id": 176,
  "query": "SELECT extracted_summary FROM postings WHERE posting_id = 176"
}
```

### Output
```json
{
  "status": "[SKIP]",
  "reason": "Summary already exists (6442 chars)"
}
```

### Next Steps
- ⏭️ Branching on [SKIP]
- Next conversation: 3350 (Extract Skills)

---

## Interaction 3: Extract (gemma3:1b)

**conversation_id:** 3335
**actor:** gemma3:1b (ai_model)
**status:** completed
**duration:** 12.4s

### Prompt (verbatim)
```
Create a concise job description summary for this job posting:

**Position:** Auditor (Finance) – Associate
**Company:** Deutsche Bank
**Location:** Jacksonville, FL

[... full 6593 char job description ...]

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
...
===END TEMPLATE===

Output ONLY the filled template above, no other text.
After the template, add [SUCCESS] on a new line.
```

### Response (verbatim)
```
===OUTPUT TEMPLATE===
**Role:** Auditor
**Company:** Deutsche Bank
**Location:** Jacksonville, FL
**Job ID:** Not Available

**Key Responsibilities:**
- Support audits covering the CFO Finance and Regulatory Reporting functions...
[... full 3741 char response ...]

[SUCCESS]
```

### Next Steps
- ✅ Created child interaction 121 (conversation 3336 - Grade)
- Branch condition: `[SUCCESS]` detected

---

[... continues for all 15 interactions ...]
```

---

## 🎯 Success Criteria

**Phase 1 (CRAWL) - Complete when:**
- [ ] Each conversation tested individually
- [ ] Trace reports generated for each
- [ ] All conversations complete successfully
- [ ] No JSONDecodeError from scripts
- [ ] No missing instruction_steps

**Phase 2 (WALK) - Complete when:**
- [ ] Extract → Grade chain works (2 interactions)
- [ ] Branching logic works ([PASS] vs [FAIL])
- [ ] Parent outputs accessible to children
- [ ] Script actors execute (sql_query, summary_saver)
- [ ] Trace shows parent data flow

**Phase 3 (RUN) - Complete when:**
- [ ] Full pipeline executes (15+ interactions)
- [ ] All interactions completed, 0 failed
- [ ] Data saved to postings table:
  - [ ] `extracted_summary` NOT NULL (6000+ chars)
  - [ ] `skill_keywords` NOT NULL (JSON array)
  - [ ] `ihl_score` NOT NULL (1-10)
- [ ] Trace report complete and reviewable
- [ ] Results documented in this file

---

## 📝 Test Results Log

### Test Run 1: [Date/Time]
**Phase:** CRAWL  
**Test:** Single conversation (3335 - Extract)  
**Result:** [SUCCESS/FAILED]  
**Notes:** [What worked, what didn't]  
**Trace:** `reports/trace_conv_3335_run_XX.md`

### Test Run 2: [Date/Time]
**Phase:** WALK  
**Test:** Extract → Grade chain (2 interactions)  
**Result:** [SUCCESS/FAILED]  
**Notes:** [What worked, what didn't]  
**Trace:** `reports/trace_chain_2steps_run_XX.md`

### Test Run 3: [Date/Time]
**Phase:** RUN  
**Test:** Full pipeline (15 interactions)  
**Result:** [SUCCESS/FAILED]  
**Notes:** [What worked, what didn't]  
**Trace:** `reports/workflow_3001_full_trace_run_XX.md`

---

## 🚧 Known Issues

### Issue 1: Job Fetcher Options
- Current: Using `db_job_fetcher.py` (simple, no dependencies)
- Alternative: `turing_job_fetcher.py` (needs contracts.py - exists but not tested)
- Status: db_job_fetcher working, stick with it

### Issue 2: Script Output Format
- Requirement: All scripts MUST output JSON
- Bad: `print("[SAVED]")` ← plain text
- Good: `print(json.dumps({"status": "[SAVED]"}))` ← JSON
- Status: sql_query.py fixed, need to verify all script actors

### Issue 3: Missing Instruction Steps
- Some conversations have no instruction_steps
- Breaks child interaction creation
- Status: Add as discovered during testing

---

## 📚 Reference

### Workflow 3001 Conversation Sequence
1. 9144 - Fetch Jobs from Deutsche Bank API (db_job_fetcher)
2. 9184 - Check if Summary Exists (sql_query_executor)
3. 3335 - Extract (gemma3:1b)
4. 3336 - Grade (gemma2:latest)
5. 3337 - Grade (qwen2.5:7b)
6. 3338 - Improve (qwen2.5:7b)
7. 3339 - Regrade (qwen2.5:7b)
8. 3341 - Format Standardization (phi3:latest)
9. 9168 - Save Summary (summary_saver)
10. 3350 - Extract Skills (qwen2.5:7b)
11. 9161 - IHL Analyst (qwen2.5:7b)
12. 9162 - IHL Skeptic (gemma2:latest)
13. 9163 - IHL HR Expert (qwen2.5:7b)
14. [Skills saver conversation - TBD]
15. [IHL saver conversation - TBD]

### Database Quick Queries

**Check workflow run status:**
```sql
SELECT 
    workflow_run_id,
    workflow_id,
    posting_id,
    status,
    created_at
FROM workflow_runs
WHERE workflow_id = 3001
ORDER BY workflow_run_id DESC
LIMIT 5;
```

**Check interactions:**
```sql
SELECT 
    i.interaction_id,
    i.execution_order,
    c.conversation_name,
    i.status,
    LENGTH(i.output::text) as output_len
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE i.workflow_run_id = [YOUR_RUN_ID]
ORDER BY i.execution_order;
```

**Check data persistence:**
```sql
SELECT 
    posting_id,
    LENGTH(extracted_summary) as summary_len,
    skill_keywords,
    ihl_score
FROM postings 
WHERE posting_id = 176;
```

---

## 🎯 Next Actions for Sandy

1. **Create test directories:**
   ```bash
   mkdir -p /home/xai/Documents/ty_learn/tests
   mkdir -p /home/xai/Documents/ty_learn/reports
   ```

2. **Copy test scripts** from this document into `tests/` directory

3. **Start with CRAWL phase:**
   ```bash
   python3 tests/test_single_conversation.py 3335  # Test Extract
   ```

4. **Review trace report:**
   ```bash
   cat reports/trace_conv_3335_run_XX.md
   ```

5. **Document results** in "Test Results Log" section above

6. **Progress to WALK phase** once all conversations tested individually

7. **Finally RUN phase** for full pipeline validation

---

**Remember:** Crawl → Walk → Run. One step at a time. Full visibility every step.

---

**Prepared by:** Arden & xai  
**Date:** November 25, 2025  
**Status:** Ready for Sandy to begin testing
