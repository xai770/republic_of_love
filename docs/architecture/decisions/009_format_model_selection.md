# ADR-009: Format Standardization Model Selection

**Status:** Accepted  
**Date:** 2025-11-30  
**Deciders:** xai, Sandy  
**Tags:** model-selection, format-standardization, benchmarking

---

## Context

The "Format Standardization" step in Workflow 3001 (conversation 3341) was using `gemma2:latest`, which had ~10.66s average latency. With hundreds of postings to process, this step was a significant bottleneck.

---

## Investigation

### Benchmark Tool

File: `tools/benchmark_format.py`

Tested 15+ models on 5 format standardization test cases:
1. Messy markdown with code blocks
2. Asterisk bullets needing standardization
3. Extra sections needing removal
4. Already clean input (regression test)
5. Code block wrappers to strip

---

## Results

| Rank | Model | Avg Latency | Correctness |
|------|-------|-------------|-------------|
| 🥇 | **qwen2.5:7b** | **2.93s** | 100% |
| 🥈 | olmo2:latest | 5.65s | 100% |
| 🥉 | olmo2:7b | 6.12s | 100% |
| 4 | gemma2:latest (old) | 10.66s | 100% |

**Failed Models (0% correctness):**
- mistral:latest - Doesn't follow formatting instructions
- llama3.2 - Same issue

---

## Decision

**Replace `gemma2:latest` with `qwen2.5:7b` for format standardization.**

```sql
UPDATE conversations
SET actor_id = 45  -- qwen2.5:7b
WHERE conversation_id = 3341;  -- Format Standardization
```

---

## Consequences

### Positive

1. **3.6x faster** than gemma2:latest baseline
2. **~8 seconds saved per posting**
3. **100% correctness maintained**

### Negative

1. qwen2.5:7b is larger model (~4GB vs ~2GB) - but we already use it for other steps

---

## Guidelines

1. Format tasks need models that follow instructions precisely
2. Creative/flexible models (mistral, llama) fail at strict formatting
3. Benchmark on realistic test cases before switching
