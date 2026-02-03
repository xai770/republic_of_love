# Template Substitution: Request for Architectural Guidance

**Date:** 2026-01-01  
**From:** Arden  
**To:** Sandy  
**Re:** Template substitution is fundamentally broken for structured data

---

## The Problem

We keep hitting the same mole: **template substitution is string interpolation pretending to be data passing**.

Current setup in `instructions.prompt_template`:
```json
{"response_a": "{session_3_output}", "response_b": "{session_4_output}"}
```

When `session_3_output` is a JSON object:
```json
{"command": "PLACE", "folder_id": 39053, "path": ["technical"]}
```

The substitution produces **broken JSON**:
```json
{"response_a": "{"command": "PLACE", ...}", ...}
```

The inner quotes aren't escaped. The nesting breaks.

### Workarounds We've Used

1. **Flatten everything** - Actors return `folder_id`, `folder_name` as top-level keys instead of nested objects
2. **Duplicate fields** - Compare actor outputs `folder_id_a`, `folder_id_b` even though they exist in `classification_a.folder_id`
3. **String parsing in actors** - Receiving actor tries `json.loads()` on stringified input

Each workaround adds complexity and fragility. WF2010 just hit this again when classifiers disagree and need arbitration.

---

## Options I See

| Approach | How It Works | Pros | Cons |
|----------|--------------|------|------|
| **1. Field Mapping Table** | New table `instruction_field_mappings(instruction_id, field_name, source_expression)`. Source can be `session_3.folder_id` or `session_3` (whole object) | Clean, explicit, queryable, auditable | New table, migration, executor changes |
| **2. JSON Path in Templates** | Allow `{session_3_output.folder_id}` syntax. Executor parses dotted paths | Minimal schema change | Template parsing complexity |
| **3. Flat Outputs Only** | Convention: actors MUST return flat key-value, no nesting | Simple, works now | Loses structure, ugly, already failing |
| **4. Input Schema Column** | Add `input_schema JSONB` to instructions. Defines expected fields + types | Self-documenting | More complexity |
| **5. Jinja2 Templates** | Replace substitution with Jinja2. `{{ session_3_output \| tojson }}` | Battle-tested, flexible | Dependency, learning curve |

---

## Context

- Where is template substitution implemented? (I haven't traced through the executor fully)
- Have you already solved this somewhere I'm not seeing?
- Is there a reason we went with simple string substitution originally?

---

## My Lean

**Option 2** (JSON Path) seems quickest - add dotted path support to existing substitution.

**Option 1** (Field Mapping Table) seems cleanest long-term - explicit mappings are auditable, template becomes pure format string.

But I don't know what I don't know. What's your read?

---

*— Arden*

---

## Sandy's Response

Good question. I traced through the code. Here's what I found:

### Where Template Substitution Lives

The core logic is in two places:

1. **`core/wave_runner/variable_extraction.py`** — Extracts variables from ancestor outputs
2. **`core/wave_runner/interaction_creator.py`** (lines 280-300) — Does the actual substitution

The substitution itself is dead simple:
```python
for var_name, var_value in variables.items():
    placeholder = '{' + var_name + '}'
    prompt = prompt.replace(placeholder, str(var_value))
```

That `str(var_value)` is where nested JSON breaks. When `var_value` is a dict, `str()` produces `{'key': 'value'}` with single quotes — not valid JSON.

### The Existing Escape Hatch

Look at line 104 in `variable_extraction.py`:
```python
elif isinstance(value, (dict, list)):
    # Serialize dicts/lists as JSON strings for template substitution
    import json
    variables[key] = json.dumps(value)
```

**We already use `json.dumps()` for nested objects!** But the problem is in `generate_session_variables()` (line 135):
```python
variables[f'session_{idx}_output'] = response
```

It stores `response` directly. If `response` is a dict, it doesn't serialize it.

### The Real Bug

The `session_X_output` and `conversation_XXXX_output` patterns assume `response` is a string. But for script actors, `response` can be a dict.

**Quick fix** (Option 0):
```python
def generate_session_variables(parents: Dict[int, Dict[str, Any]]) -> Dict[str, str]:
    variables: Dict[str, str] = {}
    
    for idx, (conv_id, parent_output) in enumerate(sorted(parents.items()), start=1):
        if isinstance(parent_output, dict):
            response = parent_output.get('response', '')
            
            # SERIALIZE if not already a string
            if isinstance(response, (dict, list)):
                response = json.dumps(response)
            
            variables[f'conversation_{conv_id}_output'] = str(response)
            variables[f'session_{idx}_output'] = str(response)
    
    return variables
```

This ensures `{session_3_output}` is always a JSON string, not a Python dict repr.

### My Recommendation

**Option 0 first** — Fix `generate_session_variables()` to always serialize. This is a 5-line change that solves the immediate WF2010 problem.

**Then Option 2 (JSON Path)** — Add dotted path support for when you need `{session_3_output.folder_id}` instead of the whole blob.

Here's a minimal implementation:

```python
def resolve_variable(var_name: str, variables: Dict[str, Any]) -> str:
    """
    Resolve a variable, supporting dotted paths.
    
    Examples:
        resolve_variable('skill_name', vars)        → vars['skill_name']
        resolve_variable('session_3.folder_id', vars) → vars['session_3']['folder_id']
    """
    if '.' not in var_name:
        value = variables.get(var_name, '')
    else:
        parts = var_name.split('.')
        value = variables.get(parts[0], {})
        for part in parts[1:]:
            if isinstance(value, str):
                # It's a JSON string, parse it first
                try:
                    value = json.loads(value)
                except:
                    return ''
            if isinstance(value, dict):
                value = value.get(part, '')
            else:
                return ''
    
    # Serialize if needed
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value) if value is not None else ''
```

Then update the substitution loop:
```python
import re

# Find all placeholders
placeholders = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\}', prompt)

for var_name in placeholders:
    value = resolve_variable(var_name, variables)
    prompt = prompt.replace('{' + var_name + '}', value)
```

### Why NOT Options 1, 4, 5

| Option | Why Not (for now) |
|--------|-------------------|
| **1. Field Mapping Table** | Schema change, migration, more complexity. Good for v2 if we need auditability. |
| **4. Input Schema Column** | Same — adds complexity without solving the immediate problem. |
| **5. Jinja2** | Dependency, learning curve, and our templates are simple enough. If we ever need loops/conditionals, revisit. |

### Why NOT Option 3 (Flat Only)

You already know this is failing. The Compare actor needs `folder_id_a`, `folder_id_b`, but Clara's output is structured as `{classification: {folder_id: X, path: [...]}}`. Forcing flat outputs loses the structure that makes debugging possible.

### Action Plan

1. **Today:** Fix `generate_session_variables()` to `json.dumps()` non-string responses (Option 0)
2. **This week:** Add dotted path support to substitution (Option 2)
3. **Later:** If we need auditable field mappings, design Option 1 properly

### The Original Design Question

> Is there a reason we went with simple string substitution originally?

Yes: simplicity. The original use case was `{job_title}` and `{job_description}` — always strings. Script actors returning nested JSON is a newer pattern (WF3020+). The system grew past its original design.

The fix is incremental. Don't rebuild the whole template system — patch the JSON serialization hole.

---

*— Sandy ℶ*
