# Extraction Model Benchmark Report

**Generated:** 2025-12-01 14:03:02

**Postings Tested:** 3
**Models Tested:** 7

## 📊 Results Summary

| Rank | Model | Clean Rate | Avg Latency | Degenerate | Recommendation |
|------|-------|------------|-------------|------------|----------------|
| 1 | `llama3.2:latest` | 100% | 4200ms | 0 | ✅ CHAMPION |
| 2 | `phi4-mini:latest` | 100% | 5763ms | 0 | ✅ Qualified |
| 3 | `gemma3:4b` | 100% | 6777ms | 0 | ✅ Qualified |
| 4 | `qwen2.5:7b` | 100% | 8833ms | 0 | ✅ Qualified |
| 5 | `mistral:latest` | 100% | 11682ms | 0 | ✅ Qualified |
| 6 | `gemma2:latest` | 100% | 31697ms | 0 | ✅ Qualified |
| 7 | `gemma3:1b` | 67% | 8600ms | 1 | ❌ Not recommended |

---

## 🔍 Detailed Results

### llama3.2:latest

- **Clean Rate:** 100%
- **Avg Latency:** 4200ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 5947ms | - |
| 5133 | ✅ Clean | 3085ms | - |
| 5144 | ✅ Clean | 3568ms | - |

### phi4-mini:latest

- **Clean Rate:** 100%
- **Avg Latency:** 5763ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 7008ms | - |
| 5133 | ✅ Clean | 4654ms | - |
| 5144 | ✅ Clean | 5627ms | - |

### gemma3:4b

- **Clean Rate:** 100%
- **Avg Latency:** 6777ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 9934ms | - |
| 5133 | ✅ Clean | 4853ms | - |
| 5144 | ✅ Clean | 5544ms | - |

### qwen2.5:7b

- **Clean Rate:** 100%
- **Avg Latency:** 8833ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 10754ms | - |
| 5133 | ✅ Clean | 10362ms | - |
| 5144 | ✅ Clean | 5384ms | - |

### mistral:latest

- **Clean Rate:** 100%
- **Avg Latency:** 11682ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 14738ms | - |
| 5133 | ✅ Clean | 9218ms | - |
| 5144 | ✅ Clean | 11089ms | - |

### gemma2:latest

- **Clean Rate:** 100%
- **Avg Latency:** 31697ms
- **Degenerate:** 0

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 39077ms | - |
| 5133 | ✅ Clean | 29438ms | - |
| 5144 | ✅ Clean | 26577ms | - |

### gemma3:1b

- **Clean Rate:** 67%
- **Avg Latency:** 8600ms
- **Degenerate:** 1

| Posting | Status | Latency | Issues |
|---------|--------|---------|--------|
| 5120 | ✅ Clean | 4257ms | - |
| 5133 | ✅ Clean | 4760ms | - |
| 5144 | ⚠️ DEGEN | 16782ms | Repetition detected: 4 repeats of same line, Looping pattern detected |

## 📝 Sample Output from Best Model (llama3.2:latest)

### Posting 5120

```
===OUTPUT TEMPLATE===
**Role:** Senior Business Functional Analyst
**Company:** Deutsche Bank Group
**Location:** Pune, India
**Job ID:** (not available)

**Key Responsibilities:**
- Capture, challenge, and document business requirements with precision and clarity.
- Model business processes using BPMN and document data mapping between sources, API endpoints, and process inputs/outputs.
- Stakeholder Engagement Liaise with stakeholders across business, operations, and IT delivery teams to ensure
...
```

### Posting 5133

```
===OUTPUT TEMPLATE===
**Role:** Risk Officer
**Company:** Synthix (Fintech)
**Location:** London
**Job ID:** Not available

**Key Responsibilities:**
- Own the first-line risk framework for Synthix
- Lead Risk assessment and governance with Operational and Technology Risk Ownership
- Support Client Assurance & due diligence

**Requirements:**
- Experience in first line risk role within a high growth Fintech or Financial SaaS environment
- Strong understanding of cloud native architecture (prefer
...
```

