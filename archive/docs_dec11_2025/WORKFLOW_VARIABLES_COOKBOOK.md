# Workflow Variables Cookbook

**Last Updated**: 2025-12-09  
**Status**: Canonical reference for template variables

---

## Quick Reference

### Variable Syntax
```
{variable_name}
```
Variables in `prompt_template` are replaced at runtime with actual values.

### Variable Sources (Priority Order)
1. **Posting columns** - Direct from `postings` table
2. **Parent outputs** - Results from previous conversations
3. **Profile data** - For profile-based workflows
4. **Workflow state** - Accumulated results during execution

---

## Variable Categories

### 1. Posting Variables (Direct Column Access)

These map directly to `postings` table columns:

| Variable | Source Column | Example |
|----------|--------------|---------|
| `{job_description}` | `postings.job_description` | Full job text |
| `{job_title}` | `postings.job_title` | "Risk Analyst" |
| `{posting_id}` | `postings.posting_id` | "12345" |
| `{location_city}` | `postings.location_city` | "Frankfurt" |
| `{location_country}` | `postings.location_country` | "Germany" |

**Legacy Aliases** (still work, but prefer direct names):
| Legacy | Maps To |
|--------|---------|
| `{variations_param_1}` | `{job_description}` |
| `{variations_param_2}` | `{job_title}` |
| `{variations_param_3}` | `{location_city}` |

### 2. Parent Output Variables

Reference output from previous conversations in the workflow:

#### By Conversation ID (Recommended)
```
{conversation_3335_output}  → Output from conversation 3335
{conversation_3341_output}  → Output from conversation 3341
```

#### By Execution Order (Legacy)
```
{session_1_output}  → First parent's output
{session_2_output}  → Second parent's output
{session_3_output}  → Third parent's output
```

#### Latest Parent
```
{parent_response}  → Most recent parent's output
```

### 3. Workflow State Variables

Semantic keys accumulated during workflow execution:

| Variable | Set By | Contains |
|----------|--------|----------|
| `{extract_summary}` | Extract step | Initial summary |
| `{improved_summary}` | Improve step | Revised summary |
| `{current_summary}` | Any summary step | Latest summary |
| `{extracted_skills}` | Skill extraction | JSON skills array |
| `{ihl_analyst_verdict}` | IHL Analyst | [PASS]/[FAIL] verdict |
| `{ihl_skeptic_verdict}` | IHL Skeptic | [PASS]/[FAIL] verdict |

### 4. Profile Variables (WF1122, WF2002)

For profile-based workflows:

| Variable | Source | Contains |
|----------|--------|----------|
| `{profile_raw_text}` | `profiles.profile_raw_text` | Full CV/resume text |

---

## Examples from WF3001

### Step 1: Extract Summary (conversation 3335)
```
Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:
===OUTPUT TEMPLATE===
**Role:** [job title]...
```
- `{variations_param_1}` → replaced with `job_description`

### Step 2: Grade Summary (conversation 3336)
```
# Instructions:
## 1. Read the following **raw posting**:

--- start raw posting ---
{variations_param_1}
--- end raw posting ---

## 2. Read the following **summary**:
{session_1_output}
```
- `{variations_param_1}` → `job_description`
- `{session_1_output}` → output from conversation 3335

### Step 3: Improve Summary (conversation 3338)
```
# Your Task: Improve the job summary based on previous feedback

## Previous Grading Result:
{session_3_output}

## Original Job Posting:
{variations_param_1}
```
- `{session_3_output}` → grading output from step 2
- `{variations_param_1}` → original job description

### Step 4: Save Summary (conversation 9168)
```
posting_id: {posting_id}
summary: {conversation_3341_output}
```
- `{posting_id}` → numeric posting ID
- `{conversation_3341_output}` → formatted summary from standardization step

---

## How Variable Resolution Works

### The Resolution Pipeline (executors.py)

```python
# 1. Query posting data
posting = get_posting(posting_id)

# 2. Query parent outputs from checkpoint
parents = get_checkpoint_data(workflow_run_id)

# 3. Build variable dictionary
variables = {
    # Posting columns
    'job_description': posting.get('job_description', ''),
    'job_title': posting.get('job_title', ''),
    'posting_id': str(posting_id),
    ...
    
    # Legacy aliases
    'variations_param_1': posting.get('job_description', ''),
    ...
    
    # Workflow state
    'extract_summary': workflow_state.get('extract_summary', ''),
    ...
}

# 4. Add parent outputs dynamically
for conv_id, parent_output in parents.items():
    variables[f'conversation_{conv_id}_output'] = parent_output['response']

# 5. Add session_X patterns
for idx, (conv_id, output) in enumerate(parents.items(), start=1):
    variables[f'session_{idx}_output'] = output['response']

# 6. Substitute into template
actual_prompt = template.format(**variables)
```

---

## Common Mistakes

### ❌ Wrong: Session number mismatch
```
# Parent order: 3335 → 3336 → 3337
# But template says:
{session_3_output}  # Expects 3rd parent, but workflow only has 2 parents
```
**Result**: Empty string substituted, causes hallucination

### ❌ Wrong: Hardcoded conversation ID that doesn't exist
```
{conversation_9999_output}  # No such conversation in workflow
```
**Result**: KeyError or empty string

### ❌ Wrong: Using template variable for script actors
Script actors receive JSON via stdin, not template substitution:
```python
# Script actor reads:
input_data = json.load(sys.stdin)
posting_id = input_data.get('posting_id')
```

### ✅ Right: Use conversation ID for specific parent
```
{conversation_3335_output}  # Explicitly reference by ID
```

### ✅ Right: Use session_N for relative position
```
{session_1_output}  # "My first parent's output"
{session_2_output}  # "My second parent's output"
```

---

## Debugging Variable Substitution

### 1. Check What Variables Are Available
```sql
-- See parent chain for a conversation
SELECT c.conversation_id, c.canonical_name, 
       ARRAY_AGG(is.parent_conversation_id) as parents
FROM conversations c
JOIN instruction_steps is ON c.conversation_id = is.conversation_id
WHERE c.conversation_id = 3338
GROUP BY c.conversation_id, c.canonical_name;
```

### 2. Check Actual Substituted Prompt
```sql
-- After execution, see what was actually sent
SELECT input->>'prompt' as actual_prompt
FROM interactions
WHERE posting_id = 123
  AND conversation_id = 3338
ORDER BY created_at DESC
LIMIT 1;
```

### 3. Check Checkpoint Data
```sql
-- What outputs are stored for a workflow run
SELECT checkpoint_data->'conversation_outputs' as outputs
FROM posting_state_checkpoints
WHERE workflow_run_id = 5986
  AND posting_id = 123;
```

### 4. Use Trace Reporter
```bash
python3 tools/debugging/generate_retrospective_trace.py --posting-id 123 --workflow-id 3001
# Creates reports/trace_posting_123.md with full variable mapping
```

---

## Best Practices

### 1. Prefer Conversation ID Over Session Number
```
# Good - explicit and stable
{conversation_3335_output}

# Risky - depends on parent order
{session_1_output}
```

### 2. Use Semantic Variables for Workflow State
```
# Good - clear intent
{current_summary}
{extracted_skills}

# Bad - magic numbers
{conversation_3341_output}  # What is 3341?
```

### 3. Document Variable Dependencies
In `instruction_steps` or workflow docs, list required variables:
```
Required: job_description, posting_id
Parents: conversation_3335 (provides extract_summary)
```

### 4. Test Variable Resolution
Before production, verify all variables resolve:
```python
# In test
template = "Summary: {extract_summary}\nSkills: {extracted_skills}"
variables = {'extract_summary': 'test', 'extracted_skills': '[]'}
result = template.format(**variables)  # Should not raise KeyError
```

---

## Adding New Variables

### 1. From Posting Table
Add to `executors.py` variable dictionary:
```python
variables = {
    ...
    'new_column': posting.get('new_column', ''),
}
```

### 2. From Parent Output
Automatic - any conversation output creates:
- `{conversation_XXXX_output}`
- `{session_N_output}` (based on parent order)

### 3. New Semantic Key
Add to workflow state accumulation:
```python
# In workflow_state processing
if 'skill_categories' in parent_output:
    workflow_state['skill_categories'] = parent_output['skill_categories']
```
Then use `{skill_categories}` in templates.

---

## Reference: placeholder_definitions Table

The `placeholder_definitions` table documents available placeholders:
```sql
SELECT placeholder_name, source_table, source_column, description
FROM placeholder_definitions
ORDER BY placeholder_name;
```

This is metadata only - actual resolution happens in `executors.py`.
