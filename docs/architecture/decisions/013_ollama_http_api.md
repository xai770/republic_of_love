# ADR-013: Use Ollama HTTP API, Not CLI

**Status:** Accepted  
**Date:** 2025-12-08  
**Author:** Sandy (discovered), Arden (approved)

## Context

The `AIModelExecutor` in `core/wave_runner/executors.py` was invoking Ollama via CLI subprocess:

```python
subprocess.run(['ollama', 'run', model_name], input=prompt, ...)
```

This approach has a **critical flaw**: the CLI ignores all model options including:
- `temperature` (controls randomness)
- `seed` (controls reproducibility)
- `top_k`, `top_p` (sampling parameters)
- `num_ctx` (context window size)

The model runs with its defaults regardless of what we specify in `actors.execution_config`.

### Discovery

This bug was discovered during WF3005 determinism testing. Even with `temperature=0` set in the database, running the same workflow 3 times produced different results:
- Run 1: 20 decisions
- Run 2: 19/20 same classifications, different confidence scores
- Run 3: 20 decisions (different from Run 2)

Investigation revealed the temperature setting was never being passed to Ollama.

## Decision

Use the Ollama HTTP API (`POST /api/generate`) instead of CLI:

```python
import requests

payload = {
    "model": model_name,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0,
        "seed": 42
    }
}

if system_prompt:
    payload["system"] = system_prompt

response = requests.post(
    "http://localhost:11434/api/generate",
    json=payload,
    timeout=self.timeout
)
```

### Changes Made

1. **`core/wave_runner/executors.py`** - Replaced `subprocess.run` with `requests.post`
2. **`core/wave_runner/database.py`** - Added `execution_config` to `get_interaction_by_id()` query
3. **`core/wave_runner/runner.py`** - Extract temperature/seed from config and pass to executor

### Actor Configuration

Set deterministic config for AI actors:

```sql
UPDATE actors 
SET execution_config = jsonb_set(
    jsonb_set(COALESCE(execution_config, '{}'::jsonb), '{temperature}', '0'),
    '{seed}', '42'
)
WHERE actor_id IN (14, 23, 45);  -- gemma3:4b, mistral:latest, qwen2.5:7b
```

## Consequences

### Positive

- ✅ **Temperature and seed are now respected** - model behavior is controllable
- ✅ **Deterministic results for testing** - same inputs produce same outputs
- ✅ **Consistent behavior across runs** - no more "works sometimes" bugs
- ✅ **Easier to debug** - can log full request payload
- ✅ **Better error messages** - API returns structured error responses

### Negative

- ⚠️ **Requires `requests` library** - already in dependencies
- ⚠️ **Requires Ollama server running** - same as before, no change
- ⚠️ **Slightly different error handling** - now catches `requests.exceptions` instead of subprocess errors

## Verification

After implementation, determinism test passed:

| Run | Skills Processed | Match with Run 1 |
|-----|-----------------|------------------|
| Run 1 | 20/20 | baseline |
| Run 2 | 20/20 | ✅ 100% IDENTICAL |
| Run 3 | 20/20 | ✅ 100% IDENTICAL |

## Notes

- For **testing/debugging**: Use `temperature=0, seed=42` for full determinism
- For **production**: Consider `temperature=0.1` for slight variance while staying mostly deterministic
- The seed value (42) is arbitrary but should be consistent across runs

## Related

- WF3005: Entity Registry - Skill Maintenance workflow
- `docs/daily_notes/2025-12-08_entity_registry_reset.md` - full debugging story
