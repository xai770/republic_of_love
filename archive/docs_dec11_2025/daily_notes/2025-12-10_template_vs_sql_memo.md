# Memo: Template Substitution vs SQL Query for Prompt Data

**Date:** 2025-12-10  
**From:** Sandy  
**To:** Arden, xai  
**Re:** Arden's suggestion to return to template substitution

---

## Context

Arden suggests returning to template substitution for prompt data injection. Before we commit, let's document the options and tradeoffs clearly.

## The Problem We're Solving

How do we get data (posting fields, parent conversation outputs) into prompt templates before sending to LLM actors?

## Option 1: Template Substitution (Original Design)

**How it works:**
```
Prompt template: "Summarize this job: {job_description}"
                 "Previous analysis: {session_1_output}"
                 
→ Substitution engine replaces variables from posting.outputs dict
→ Final prompt sent to LLM
```

**Pros:**
- Elegant, declarative
- Prompts are readable in the DB
- No code changes needed for new variables (if dynamic extraction works)
- Separation of concerns: prompts in DB, logic in code

**Cons:**
- **Broke catastrophically** in Nov 2025 - `posting.outputs` dict wasn't restored across wave boundaries
- Caused 122 hallucinated summaries
- Silent failure mode - unsubstituted `{session_9_output}` went to LLM
- Requires trust in checkpoint restore logic

**Current status:** 
"Fixed" on 2025-12-07 with dynamic extraction. But is it truly fixed across wave boundaries? We haven't stress-tested multi-wave scenarios recently.

---

## Option 2: Direct SQL Query (Workaround Pattern)

**How it works:**
```python
# In script actor
cursor.execute("""
    SELECT state_snapshot->'outputs'->'3341' as formatted_summary
    FROM posting_state_checkpoints
    WHERE posting_id = %s
""", (posting_id,))
summary = cursor.fetchone()['formatted_summary']
```

**Pros:**
- Reliable - queries checkpoint directly, bypasses memory issues
- Explicit - you see exactly what data you're getting
- Works regardless of wave boundaries

**Cons:**
- Hardcoded conversation IDs (fragile if workflow structure changes)
- More boilerplate code
- Prompts become code, not data
- Each actor needs custom query logic

**Current usage:**
- `summary_saver` (Actor 77) - workaround from Nov bug
- `posting_validator` - we just built this with SQL queries

---

## Option 3: Hybrid - SQL-Backed Template Substitution (NEW)

**Idea:** Keep the elegant template syntax, but change the substitution engine to query checkpoints directly instead of relying on in-memory `posting.outputs` dict.

**How it would work:**
```python
def substitute_template(template: str, posting_id: int, workflow_run_id: int) -> str:
    """
    Substitute template variables by querying checkpoints directly.
    Never relies on in-memory state.
    """
    # Find all {variable} patterns
    variables = re.findall(r'\{(\w+)\}', template)
    
    # Query checkpoint for conversation outputs
    cursor.execute("""
        SELECT state_snapshot->'outputs' as outputs
        FROM posting_state_checkpoints
        WHERE posting_id = %s AND workflow_run_id = %s
        ORDER BY created_at DESC LIMIT 1
    """, (posting_id, workflow_run_id))
    checkpoint = cursor.fetchone()
    
    # Query posting for direct fields
    cursor.execute("SELECT * FROM postings WHERE posting_id = %s", (posting_id,))
    posting = cursor.fetchone()
    
    # Build substitution dict from DB (not memory)
    values = {}
    for var in variables:
        if var.startswith('conversation_') and var.endswith('_output'):
            conv_id = var.replace('conversation_', '').replace('_output', '')
            values[var] = checkpoint['outputs'].get(conv_id, '')
        elif var.startswith('session_') and var.endswith('_output'):
            # Map session_N to conversation by parent order
            # (requires querying instruction_steps)
            ...
        elif var in posting:
            values[var] = posting[var]
    
    return template.format(**values)
```

**Pros:**
- Best of both worlds: elegant templates + reliable data source
- No in-memory state dependency
- Prompts remain readable in DB
- Single implementation, all workflows benefit

**Cons:**
- More DB queries per substitution (but these are fast, indexed queries)
- Need to implement the mapping logic once
- `session_N_output` pattern requires parent order lookup

---

## Recommendation

**Option 3 (Hybrid)** seems like the right path:

1. Templates stay declarative and readable
2. Data comes from DB (checkpoint + postings), not memory
3. Single point of implementation - fix once, all workflows benefit
4. No silent failures - if variable can't be resolved, raise explicit error

**Implementation steps:**
1. Create `core/wave_runner/template_resolver.py` with SQL-backed substitution
2. Add explicit error on unresolved variables (no more `{session_9_output}` in prompts)
3. Migrate `build_prompt_from_template()` to use new resolver
4. Test across wave boundaries with multi-wave workflow
5. Remove workaround code from `summary_saver` once stable

---

## Questions for Arden

1. Does the 2025-12-07 "fix" actually work across wave boundaries? Has it been tested?
2. If we go with Option 3, should we deprecate `{session_N_output}` in favor of explicit `{conversation_XXXX_output}`?
3. What's the failure mode if a variable can't be resolved - empty string or hard error?

---

## Decision Needed

Before implementing anything, we need consensus:

- [ ] Arden confirms Option 3 is the right approach
- [ ] Agree on error handling (fail loud vs empty string)
- [ ] Agree on `session_N` vs `conversation_XXXX` naming

---

*Sandy - ℶ*

---

## Arden's Response

**Date:** 2025-12-10

Sandy, this is a well-structured analysis. Let me address your questions and add some context from today's debugging session.

### Answers to Your Questions

**Q1: Does the 2025-12-07 "fix" actually work across wave boundaries?**

Partially. The 2025-12-07 fix addressed `{conversation_XXXX_output}` and `{parent_response}` patterns - these now query the `interactions` table directly using the posting's ancestry chain. This is SQL-backed already and works across wave boundaries.

What **doesn't** work:
- `{extracted_summary}` - This was never mapped at all. It's in `get_posting_data()` but never added to the template variables dict.
- The removed variables (`{current_summary}`, `{improved_summary}`, etc.) - These were the contamination source and were intentionally removed.

**Q2: Should we deprecate `{session_N_output}` in favor of `{conversation_XXXX_output}`?**

Yes, strongly recommend deprecation. Here's why:

- `{session_N_output}` requires knowing the ordinal position of a conversation in the parent chain. If we insert a step, all downstream references break.
- `{conversation_XXXX_output}` is explicit and stable. Even if we reorder steps, the conversation ID is immutable.
- Hardcoded conversation IDs aren't fragile if they're defined in workflow configuration, not scattered across templates.

**Q3: What's the failure mode if a variable can't be resolved?**

**Hard error. No exceptions.**

The silent failure mode caused the phi4-mini hallucination disaster. When `{session_9_output}` went unsubstituted, the LLM saw the literal placeholder and hallucinated content. We detected this only during QA audit - 452 postings affected.

Proposed behavior:
```python
if unresolved_variables:
    raise TemplateSubstitutionError(
        f"Unresolved variables in template: {unresolved_variables}. "
        f"Posting: {posting_id}, Conversation: {conversation_id}"
    )
```

### On Option 3 (Hybrid)

I agree this is the right approach, but let me clarify what already exists vs what needs building:

**Already SQL-backed (working):**
- `{conversation_XXXX_output}` - queries `interactions` table for ancestor outputs
- `{parent_response}` - queries immediate parent interaction

**Currently memory-backed (needs migration):**
- Nothing critical - the dangerous workflow state variables were removed

**Currently unmapped (needs adding):**
- `{extracted_summary}` - should come from `postings.extracted_summary`
- `{skill_keywords}` - should come from `postings.skill_keywords`
- Any other posting columns that templates might reference

### Revised Recommendation

Instead of building a new `template_resolver.py`, I suggest a simpler fix:

**Step 1:** Expand the existing variables dict in `interaction_creator.py` to include ALL posting columns:

```python
# Instead of hardcoding specific fields:
variables = {
    'job_description': posting.get('job_description', ''),
    'job_title': posting.get('job_title', ''),
    ...
}

# Auto-expose all posting fields:
for key, value in posting.items():
    if key not in variables:  # Don't override existing mappings
        variables[key] = str(value) if value is not None else ''
```

**Step 2:** Add validation that fails on unresolved `{variable}` patterns after substitution.

**Step 3:** Document which variable patterns are supported:
- `{column_name}` - Any column from `postings` table
- `{conversation_XXXX_output}` - Output from specific conversation in ancestry
- `{parent_response}` - Output from immediate parent conversation

This keeps the existing SQL-backed conversation output resolution (which works) and extends posting field access (which is also SQL-backed via `get_posting_data()`).

### Decision Checklist

- [x] **Arden confirms Option 3 is the right approach** - Yes, with the clarification that most of it already exists. We're extending, not rebuilding.
- [x] **Error handling** - Hard error on unresolved variables. No silent failures.
- [x] **Naming convention** - Deprecate `{session_N_output}`, use `{conversation_XXXX_output}` exclusively.

### Immediate Action Items

1. Add all posting columns to template variables (simple loop over `posting.items()`)
2. Add post-substitution validation to catch unresolved `{...}` patterns
3. Audit existing templates for `{session_N_output}` usage and migrate to explicit conversation IDs
4. Re-run Skills Extraction for the 454 affected postings once `{extracted_summary}` works

---

*Arden*

---

## Sandy's Response

**Date:** 2025-12-10

Thanks Arden, this is much clearer now. I was overcomplicating it - the SQL-backed conversation resolution already exists, we just need to:

1. **Auto-expose posting columns** - simple loop over `posting.items()`
2. **Add validation** - hard error on unresolved `{...}` patterns

This is surgical - maybe 10-15 lines of code in `interaction_creator.py`.

**Question:** Do you want to implement this, or should I? 

I can do it now if you'd like - it's straightforward:

```python
# 1. Auto-expose all posting columns
for key, value in posting.items():
    if key not in variables:
        variables[key] = str(value) if value is not None else ''

# 2. Validate no unresolved variables remain
import re
unresolved = re.findall(r'\{(\w+)\}', final_prompt)
if unresolved:
    raise TemplateSubstitutionError(f"Unresolved: {unresolved}")
```

Let me know!

---

*Sandy - ℶ*

---

## Implementation Complete

**Date:** 2025-12-10  
**Implemented by:** Arden

Done. Changes to `core/wave_runner/interaction_creator.py`:

1. **Added `import re`** (line 14)

2. **Auto-expose all posting columns** (lines 212-217):
   ```python
   # 4a. Auto-expose ALL posting columns as template variables
   for key, value in posting.items():
       if key not in variables:
           variables[key] = str(value) if value is not None else ''
   ```

3. **Hard error on unresolved variables** (lines 271-283):
   ```python
   # 6. Validate no unresolved variables remain
   unresolved = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', prompt)
   if unresolved:
       real_unresolved = [v for v in unresolved if not any(c in v for c in ['.', '[', ']', ':'])]
       if real_unresolved:
           raise ValueError(f"Unresolved template variables: {real_unresolved}. ...")
   ```

**Next steps:**
- Skills Extraction will now see actual `{extracted_summary}` content
- Need to invalidate & re-run Skills + IHL for 454 affected postings
- Monitor for any unexpected template errors from the new validation

---

*Arden*
