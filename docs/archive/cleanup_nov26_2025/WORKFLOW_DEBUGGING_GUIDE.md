# Workflow Debugging Guide

**Last Updated:** 2025-11-15  
**Status:** Living document - update after each major debugging session

---

## Table of Contents

1. [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
2. [Common Failure Patterns](#common-failure-patterns)
3. [Template System Architecture](#template-system-architecture)
4. [Debugging Workflow Crashes](#debugging-workflow-crashes)
5. [Tools & Commands](#tools--commands)
6. [Known Issues & Solutions](#known-issues--solutions)
7. [Circuit Breaker Behavior](#circuit-breaker-behavior)
8. [Prevention Checklist](#prevention-checklist)

---

## Quick Diagnostic Checklist

When a workflow stops or fails, check in this order:

1. **Is the process running?**
   ```bash
   ps aux | grep wave_batch_processor | grep -v grep
   ```

2. **Check the latest log tail:**
   ```bash
   tail -100 $(ls -t logs/workflow_3001_full_run_*.log | head -1)
   ```

3. **Look for specific error patterns:**
   ```bash
   tail -1000 <logfile> | grep -E "ERROR|circuit_breaker|missing.*placeholders"
   ```

4. **Check current progress:**
   ```bash
   python3 tools/workflow_step_monitor.py --workflow 3001
   ```

5. **Verify database state:**
   - Are checkpoints being created?
   - Are llm_interactions being logged?
   - Is data being written to postings table?

---

## Common Failure Patterns

### Pattern 1: Template Parsing Errors on Script Actors

**Symptoms:**
```
missing=['\"true\": \"[SKIP]\"', '\"query\": \"SELECT...' (unknown type)']
circuit_breaker_open
batch_completed (premature termination)
```

**Root Cause:**  
`render_prompt()` being called on JSON templates used by script actors. The function treats JSON keys (`"true"`, `"false"`, `"query"`) as template variables.

**Solution:**  
Script actors should use simple string replacement, NOT full template rendering.

**Fix Location:** `core/wave_batch_processor.py`, around line 808:

```python
# CORRECT PATTERN:
if conv['actor_type'] == 'script':
    # Script actors: Just do simple {posting_id} replacement in JSON
    prompt = prompt_template.replace('{posting_id}', str(posting.posting_id))
else:
    # AI models: Full template rendering with session_outputs
    prompt = self._render_prompt(prompt_template, posting, current_execution_order)
```

**Prevention:**  
Always check actor_type before calling `_render_prompt()`.

---

### Pattern 2: Wrong Session References in Templates

**Symptoms:**
```
missing=['session_1_output (unknown type)', 'session_4_output (FORWARD REFERENCE)']
```
Models generate hallucinated content (fake companies, fictional job descriptions).

**Root Cause:**  
Templates referencing wrong execution_order numbers. Example: Step 4 referencing `{session_1_output}` when it should reference `{session_3_output}`.

**How Session Numbers Work:**
- `{session_N_output}` = output from execution_order N
- Step 1 (API fetch) rarely runs in resume scenarios
- Step 3 (extractor) is usually the FIRST step that produces usable output
- Steps 4-9 should reference Step 3's output: `{session_3_output}`

**Diagnosis:**
```sql
-- Find all instruction templates with session references
SELECT 
    c.conversation_name,
    wc.execution_order,
    i.prompt_template::text
FROM instructions i
JOIN conversations c ON i.conversation_id = c.conversation_id
JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
WHERE wc.workflow_id = 3001
  AND i.prompt_template::text LIKE '%session_%'
ORDER BY wc.execution_order;
```

**Fix Pattern:**
1. Identify which step produces the data you need
2. Use that step's execution_order in template: `{session_N_output}`
3. For fallbacks, use multi-fallback syntax: `{session_7?session_6?session_3}`

---

### Pattern 3: Multi-Fallback Syntax Not Supported

**Symptoms:**
```
missing=['session_6_output?session_3_output (unknown type)']
```

**Root Cause:**  
Old `render_prompt()` only split on first `?`, treating `session_6?session_3` as a single placeholder name.

**Solution:**  
`core/prompt_renderer.py` must split on ALL `?` characters and iterate through options:

```python
if '?' in placeholder_name:
    fallback_options = [opt.strip() for opt in placeholder_name.split('?')]
    
    # Try each option in order until we find one that exists
    value = None
    for option_name in fallback_options:
        if option_name.startswith('session_') and option_name.endswith('_output'):
            match = re.match(r'session_(\d+)_output', option_name)
            if match:
                session_num = int(match.group(1))
                if session_num in session_outputs:
                    value = session_outputs[session_num] or ""
                    break  # Found a value, stop trying fallbacks
```

**Valid Syntax:**
- `{session_3_output}` - single reference
- `{session_7?session_3}` - two-level fallback
- `{session_7?session_6?session_3}` - unlimited fallback chain

---

### Pattern 4: Circuit Breaker Death Spiral

**Symptoms:**
- Repeated `circuit_breaker_open` warnings
- Cooldown times: 26s, 52s, 104s, 168s (exponential backoff)
- Workflow terminates with `batch_completed` despite unfinished work

**Root Cause:**  
Errors (like template parsing failures) trigger circuit breaker. As breaker opens, waves retry with smaller batches, hitting the same error. Eventually all postings exhausted.

**Circuit Breaker Behavior:**
- Opens after 3 consecutive failures
- Cooldown doubles: 26s → 52s → 104s → 168s (max)
- Wave processor reduces batch size when circuit opens: 10 → 6 → 5 → 4 → 3 → 2 → 1
- At batch size 1, if error persists, posting is skipped

**Prevention:**
- Fix template errors BEFORE running large batches
- Test with `--limit 1` or `--limit 5` first
- Monitor logs for warnings early

**Recovery:**
- Kill the workflow
- Fix the underlying issue (template, database, etc.)
- Circuit breaker resets on restart

---

### Pattern 5: Entry Point Mismatches

**Symptoms:**
```
ERROR: No entry point found for stage 'needs_summary'
```

**Root Cause:**  
Hardcoded entry points in `wave_batch_processor.py` don't match database execution_order values.

**Diagnosis:**
```sql
-- Find actual entry points in database
SELECT execution_order, conversation_name 
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
WHERE workflow_id = 3001 
  AND conversation_name LIKE 'check_%'
ORDER BY execution_order;
```

**Fix Location:** `core/wave_batch_processor.py`, around line 276:

```python
STAGE_ENTRY_POINTS = {
    'needs_summary': 2,   # Check if Summary Exists
    'needs_skills': 11,   # Check if Skills Exist  
    'needs_ihl': 16       # Check if IHL Score Exists
}
```

**Prevention:**  
Entry points should be configurable from database, not hardcoded.

---

## Template System Architecture

### Two Types of Templates

| Type | Used By | Format | Rendering |
|------|---------|--------|-----------|
| **AI Model Templates** | llama3, gemma2, qwen2.5, phi3 | Plain text with `{placeholders}` | Full `render_prompt()` |
| **Script Actor Templates** | sql_query_executor, summary_saver, etc. | JSON with `{posting_id}` only | Simple string replacement |

### Template Variable Reference

**For AI Models:**

| Variable | Description | Example |
|----------|-------------|---------|
| `{variations_param_1}` | Job description text | Full posting text |
| `{posting_id}` | Current posting ID | `12345` |
| `{session_N_output}` | Output from execution_order N | Step 3 extractor output |
| `{session_A?session_B}` | Fallback chain | Try A, then B if A missing |
| `{conversation_N_output}` | Legacy format (deprecated) | Use session_N instead |

**For Script Actors:**

| Variable | Description | Example |
|----------|-------------|---------|
| `{posting_id}` | Current posting ID | `12345` |

That's it. Script actors should NOT use `{session_N_output}` or any complex variables.

### Critical Rule

**NEVER call `render_prompt()` on JSON templates!**

JSON keys like `"true"`, `"false"`, `"query"` will be parsed as template variables, causing:
- Missing placeholder warnings
- Circuit breaker triggers
- Workflow crashes

---

## Debugging Workflow Crashes

### Step 1: Find the Log File

```bash
# List recent workflow logs
ls -lth logs/workflow_3001_full_run_*.log | head -5

# Get latest
LATEST_LOG=$(ls -t logs/workflow_3001_full_run_*.log | head -1)
```

### Step 2: Identify the Failure Point

```bash
# Last 100 lines
tail -100 $LATEST_LOG

# Look for batch_completed (normal end) vs crash
tail -1 $LATEST_LOG | grep -q batch_completed && echo "Normal end" || echo "Crashed"

# Find last successful activity
grep "posting_completed\|wave_started" $LATEST_LOG | tail -20
```

### Step 3: Extract Error Patterns

```bash
# Template errors
grep "missing.*placeholders" $LATEST_LOG | tail -5

# Circuit breaker
grep "circuit_breaker" $LATEST_LOG | tail -10

# Actual errors
grep -E "ERROR|FAILED" $LATEST_LOG | tail -20
```

### Step 4: Identify Problematic Step

```bash
# Which conversation/step failed?
grep "circuit_breaker_open\|ERROR" $LATEST_LOG | grep -oP 'conversation_id":\s*\K\d+' | sort | uniq -c
```

### Step 5: Check Database State

```sql
-- Last checkpoints created
SELECT 
    c.conversation_name,
    wc.execution_order,
    COUNT(*) as checkpoint_count,
    MAX(psc.created_at) as last_checkpoint
FROM posting_state_checkpoints psc
JOIN conversations c ON psc.conversation_id = c.conversation_id
JOIN workflow_conversations wc ON c.conversation_id = wc.conversation_id
WHERE wc.workflow_id = 3001
  AND psc.created_at > NOW() - INTERVAL '1 hour'
GROUP BY c.conversation_name, wc.execution_order
ORDER BY last_checkpoint DESC;
```

### Step 6: Examine the Failing Template

```sql
-- Get template for problematic conversation
SELECT 
    c.conversation_name,
    a.actor_name,
    a.actor_type,
    i.prompt_template
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
JOIN instructions i ON c.conversation_id = i.conversation_id
WHERE c.conversation_id = <CONVERSATION_ID_FROM_STEP4>;
```

---

## Tools & Commands

### Monitoring

```bash
# Real-time progress
python3 tools/workflow_step_monitor.py --workflow 3001

# Continuous watch (refresh every 5s)
python3 tools/workflow_step_monitor.py --workflow 3001 --watch --interval 5

# Check if running
ps aux | grep wave_batch_processor | grep -v grep
```

### Testing

```bash
# Test with single posting
python3 -m core.wave_batch_processor --workflow 3001 --limit 1

# Test with small batch
python3 -m core.wave_batch_processor --workflow 3001 --limit 5

# Resume mode (skip checkpoints)
python3 -m core.wave_batch_processor --workflow 3001
```

### Database Queries

```sql
-- Count postings by stage
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE extracted_summary IS NOT NULL) as has_summary,
    COUNT(*) FILTER (WHERE skill_keywords IS NOT NULL) as has_skills,
    COUNT(*) FILTER (WHERE ihl_score IS NOT NULL) as has_ihl
FROM postings 
WHERE enabled = TRUE AND job_description IS NOT NULL;

-- Find postings stuck at a step
SELECT p.posting_id, p.posting_name
FROM postings p
WHERE NOT EXISTS (
    SELECT 1 FROM posting_state_checkpoints psc
    WHERE psc.posting_id = p.posting_id
      AND psc.conversation_id = <CONVERSATION_ID>
)
  AND p.enabled = TRUE
ORDER BY p.posting_id
LIMIT 20;

-- Check template for a conversation
SELECT prompt_template 
FROM instructions 
WHERE conversation_id = <CONVERSATION_ID>;
```

### Log Analysis

```bash
# Count errors by type
grep ERROR $LATEST_LOG | cut -d'"' -f6 | sort | uniq -c | sort -rn

# Track progress over time
grep "batch_completed\|wave_started" $LATEST_LOG | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}'

# Find which postings failed
grep "circuit_breaker_open" $LATEST_LOG | grep -oP 'posting_id":\s*\K\d+' | sort -u
```

---

## Known Issues & Solutions

### Issue 1: Template Parsing on Script Actors
**Fixed:** 2025-11-15  
**Location:** `core/wave_batch_processor.py` line 808  
**Solution:** Check `actor_type` before calling `_render_prompt()`

### Issue 2: Multi-Fallback Not Supported
**Fixed:** 2025-11-15  
**Location:** `core/prompt_renderer.py` lines 73-90  
**Solution:** Split on all `?` characters, iterate through options

### Issue 3: Wrong Session References
**Fixed:** 2025-11-15  
**Affected:** Instructions 3329, 3330, 3331, 3333, 3334  
**Solution:** Changed `session_1_output` → `session_3_output`

### Issue 4: Step 10 Template Format
**Fixed:** 2025-11-15  
**Location:** Instruction 3392  
**Solution:** Changed from JSON to key-value format for `summary_saver` script

### Issue 5: Entry Point Hardcoding
**Status:** Known limitation  
**Workaround:** Manually verify `STAGE_ENTRY_POINTS` matches database execution_order

---

## Circuit Breaker Behavior

### States

1. **CLOSED** (normal operation)
   - All calls go through
   - Failures are counted

2. **OPEN** (blocking calls)
   - Actor has failed 3+ times consecutively
   - All calls return `[CIRCUIT_BREAKER_OPEN]`
   - Cooldown period active

3. **HALF_OPEN** (testing)
   - Cooldown expired
   - Next call is a test
   - Success → CLOSED
   - Failure → OPEN (longer cooldown)

### Cooldown Schedule

| Failure Count | Cooldown |
|--------------|----------|
| 3 | 26 seconds |
| 4 | 52 seconds |
| 5 | 104 seconds |
| 6+ | 168 seconds (max) |

### When Circuit Opens

**Wave behavior:**
1. Reduce batch size by 1
2. Retry with smaller batch
3. If batch size reaches 1 and still failing → skip posting
4. Move to next wave

**Result:**  
Workflow may complete with some postings unprocessed if underlying error not fixed.

### How to Reset

Circuit breaker state is in-memory only:
- Restart workflow → circuit resets
- Fix underlying issue → restart → should work

---

## Prevention Checklist

### Before Running a Workflow

- [ ] Test with `--limit 1` first
- [ ] Verify all entry points exist in database
- [ ] Check that template variables match execution_order
- [ ] Confirm script actors use simple string replacement
- [ ] Verify AI model templates use full `render_prompt()`
- [ ] Check that fallback syntax is supported
- [ ] Ensure posting data exists (job_description not null)
- [ ] Review previous run logs for warnings

### After Modifying Templates

- [ ] Test the specific conversation with 1 posting
- [ ] Check for template parsing warnings in logs
- [ ] Verify output is written to correct database column
- [ ] Confirm no hallucinations in AI output
- [ ] Check circuit breaker doesn't open

### When Adding New Conversations

- [ ] Set correct execution_order
- [ ] Match actor_type to template format
- [ ] Add to entry points if it's a checkpoint
- [ ] Test in isolation before adding to workflow
- [ ] Document template variables used

---

## Lessons Learned (2025-11-15)

### Session Context

Investigated workflow 3001 crash after 172 postings. Multiple restarts, all failing at Step 2 (check_summary_exists) with circuit breaker opening.

### Key Insights

1. **Template rendering is context-dependent**
   - Script actors need JSON intact → simple replacement
   - AI models need full rendering → complex substitution
   - Mixing these causes catastrophic failures

2. **Circuit breaker is a symptom, not the disease**
   - Don't fight the circuit breaker
   - Find and fix the underlying template/data issue
   - Restart with clean state

3. **Test small before scaling**
   - 1,769 postings with broken templates = wasted hours
   - 1 posting test would have caught it in seconds
   - Always use `--limit 1` for new workflows

4. **Execution order matters**
   - Step 1 often doesn't run (data already fetched)
   - Step 3 is typically first usable output
   - Template refs must match reality, not design docs

5. **JSON and template parsers don't mix**
   - `render_prompt()` sees `{"true": ...}` as template variable `{\"true\"}`
   - This is a fundamental architectural issue
   - Must separate script vs AI rendering paths

### What We Fixed Tonight

1. **Script actor rendering** - Skip `render_prompt()` for actor_type='script'
2. **Multi-fallback support** - Handle unlimited `?` chains
3. **Session references** - Updated 5 templates to use correct execution_order
4. **Step 10 format** - Changed from JSON to key-value for summary_saver
5. **Entry points** - Fixed hardcoded values to match database

### What NOT to Do Again

1. ❌ Don't call `render_prompt()` on JSON templates
2. ❌ Don't reference `session_1_output` in Steps 4-9 (it's usually empty)
3. ❌ Don't run large batches without testing small first
4. ❌ Don't add two-layer checking with OR clauses in SQL (template parser breaks)
5. ❌ Don't ignore circuit breaker warnings - they indicate real problems

### What TO Do

1. ✅ Check actor_type before rendering
2. ✅ Test with `--limit 1` after ANY template change
3. ✅ Use `session_3_output` as baseline for extraction pipeline
4. ✅ Monitor logs in real-time with `tail -f`
5. ✅ Accept pragmatic tradeoffs (1% redundancy vs architectural refactor)

---

## Future Improvements

### Short Term

1. Make entry points database-driven (remove hardcoding)
2. Add template validation before workflow starts
3. Better error messages for template issues
4. Auto-detect actor_type in rendering logic

### Medium Term

1. Separate template renderer for script vs AI actors
2. Template variable documentation generator
3. Dry-run mode to test templates without executing
4. Circuit breaker dashboard/monitoring

### Long Term

1. Visual workflow debugger
2. Template IDE with syntax checking
3. Automated recovery from circuit breaker states
4. Machine learning on error patterns

---

## Emergency Procedures

### Workflow Won't Start

1. Check database connection
2. Verify workflow_id exists
3. Check for active workflow_run locks
4. Review previous crash logs

### Workflow Stuck/Frozen

1. Check process is running (`ps aux`)
2. Look for circuit breaker loops in logs
3. Check database for stuck transactions
4. Monitor system resources (CPU, memory, I/O)

### Data Corruption/Hallucinations

1. **STOP IMMEDIATELY** - Kill the workflow
2. Identify affected postings (check summaries manually)
3. Delete bad data and checkpoints
4. Fix template issues
5. Test with `--limit 1`
6. Resume with corrected templates

### Circuit Breaker Won't Reset

1. Circuit breaker is in-memory - restart workflow
2. If still failing, underlying issue not fixed
3. Test the failing actor in isolation
4. Check actor is running (Ollama, scripts, etc.)

---

**Document Maintenance:**
- Update after each major debugging session
- Add new patterns as discovered
- Document all template changes
- Keep examples current with production code

