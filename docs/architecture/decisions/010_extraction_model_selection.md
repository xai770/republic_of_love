# ADR-010: Extraction Model Selection

**Status:** Accepted  
**Date:** 2025-12-01  
**Deciders:** xai, Arden  
**Tags:** model-selection, extraction, benchmarking

---

## Context

The summary extraction step in Workflow 3001 (conversation `session_a_llama32_extract`, ID 3335) was originally using `gemma3:1b` (actor 13). During debugging of `session_e_qwen25_regrade` failures, we traced issues back to the extraction model.

### The Problem

**Symptoms:**
- `session_e_qwen25_regrade` interactions failing with `{session_4_output}` template variable not substituted
- When we fixed the template bug, we discovered the real issue: poor extraction quality triggering improvement+regrade loops

**Root cause discovered via benchmarking:**
- `gemma3:1b` produces **degenerate outputs** on certain postings
- Degeneration pattern: model enters infinite loop repeating phrases
- Example: `"work work work work work work..."` repeated 500+ times
- These degenerate outputs fail QA, trigger improvement, and still fail regrade

---

## Investigation

### Benchmark Tool Created

File: `tools/benchmark_extraction.py`

Tested 7 models on 3 problematic postings (IDs: 5144, 5150, 4804):

```bash
python3 tools/benchmark_extraction.py
```

### Results

| Model | Clean Rate | Avg Latency | Degeneration Detected |
|-------|------------|-------------|----------------------|
| **llama3.2:latest** | **100%** | **4200ms** | No |
| phi4-mini:latest | 100% | 5763ms | No |
| gemma3:4b | 100% | 6777ms | No |
| qwen2.5:7b | 100% | 7200ms | No |
| olmo2:latest | 100% | 8100ms | No |
| gemma3:1b | **67%** | 8600ms | **YES** (posting 5144) |
| gemma3n:e2b | 100% | 9200ms | No |

### Key Finding

`gemma3:1b` is the **only model** that degenerated. The 1B parameter count is too small for reliable extraction on complex job descriptions.

---

## Decision

**Replace `gemma3:1b` with `llama3.2:latest` for extraction.**

### Implementation

```sql
-- Update actor for extraction conversation
UPDATE conversations
SET actor_id = 21  -- llama3.2:latest
WHERE conversation_id = 3335;

-- Rename conversation to reflect model change
UPDATE conversations
SET conversation_name = 'session_a_llama32_extract'
WHERE conversation_id = 3335;
```

---

## Consequences

### Positive

1. **100% clean outputs** - No degeneration on any tested posting
2. **Fastest model** - 4200ms average (2x faster than gemma3:1b's 8600ms when it worked)
3. **Fewer improvement loops** - Better extraction → fewer QA failures → fewer regrade cycles
4. **Reduced GPU waste** - Degenerate outputs consumed full timeout before failing

### Negative

1. **llama3.2:latest is ~3GB vs gemma3:1b ~1GB** - Slightly more VRAM
2. **Need to monitor** - Other edge cases may exist we haven't tested

### Verification

After deploying, monitor:
```sql
-- Should see decrease in session_e_qwen25_regrade interactions
SELECT conversation_name, COUNT(*)
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE c.conversation_name LIKE 'session_%'
GROUP BY conversation_name;
```

---

## Model Selection Guidelines

Based on this investigation, document these rules:

1. **Always benchmark on problematic postings** - Not just random samples
2. **Test for degeneration** - Look for repetitive patterns, not just format compliance
3. **Smaller isn't always better** - 1B models can degenerate on complex inputs
4. **Speed AND quality matter** - llama3.2 won on both metrics

---

## Related

- `tools/benchmark_extraction.py` - Benchmark tool for extraction models
- `tools/benchmark_format.py` - Similar tool for format standardization (Nov 30)
- `tools/benchmark_models.py` - General model benchmark infrastructure
- ADR-009 (implied): Format standardization model change to qwen2.5:7b
