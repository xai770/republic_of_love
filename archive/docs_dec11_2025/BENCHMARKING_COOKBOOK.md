# Benchmarking Cookbook 📊

> How to test and select the best AI model for any task in our workflow

**Author:** Sandy & xai  
**Date:** December 2, 2025  
**Status:** Active

---

## Table of Contents

1. [Why Benchmark?](#why-benchmark)
2. [The Three Failure Modes](#the-three-failure-modes)
3. [Benchmark Strategy](#benchmark-strategy)
4. [Running a Benchmark](#running-a-benchmark)
5. [Interpreting Results](#interpreting-results)
6. [Selecting a Model](#selecting-a-model)
7. [Model Qualification Framework](#model-qualification-framework)
8. [Golden Test Set](#golden-test-set)
9. [Grader Effectiveness Analysis](#grader-effectiveness-analysis)
10. [Quick Reference](#quick-reference)

---

## Why Benchmark?

Different AI models have different strengths:

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| gemma3:1b | ⚡⚡⚡ | ⭐⭐ | 💰 | Simple classification |
| llama3.2 | ⚡⚡⚡ | ⭐⭐⭐ | 💰 | Fast extraction |
| qwen2.5:7b | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Quality grading |
| mistral | ⚡⚡ | ⭐⭐⭐⭐ | 💰💰 | Balanced tasks |
| gemma2 | ⚡ | ⭐⭐⭐⭐ | 💰💰💰 | High quality (slow) |

**The goal:** Find the model that is *fast enough* and *good enough* for your specific task.

---

## The Three Failure Modes

When an LLM does a task, it can fail in three distinct ways:

### 1. Degeneration (The Loop) 🌀

The model gets stuck in a loop and produces garbage:

```
**Role:** Software Engineer
**Company:** Deutsche Bank Deutsche Bank Deutsche Bank Deutsche Bank
Deutsche Bank Deutsche Bank Deutsche Bank Deutsche Bank Deutsche Bank...
```

**Detection:** Easy - look for repeated patterns
```python
def is_degenerate(text):
    # Check if any line appears 3+ times
    lines = text.split('\n')
    for line in lines:
        if len(line) > 10 and lines.count(line) >= 3:
            return True
    return False
```

**History:** We saw this with llama3.2 on certain postings (Dec 1, 2025). The model's attention mechanism breaks and it gets stuck.

### 2. Omission (The Lazy Student) 📝

The output *looks* fine but is incomplete or inaccurate:

**Original posting has 10 responsibilities:**
```
1. Manage team of 5 engineers
2. Design system architecture  
3. Code review and mentoring
4. Sprint planning
5. Stakeholder communication
6. Budget management
7. Hiring decisions
8. Performance reviews
9. Technical documentation
10. Incident response
```

**Model only extracts 3:**
```
**Key Responsibilities:**
- Manage team of 5 engineers
- Design system architecture
- Code review and mentoring
```

**Detection:** Harder - needs a "grader" model to compare against original

---

## Benchmark Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                      BENCHMARK PIPELINE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   1. SELECT TEST CASES                                               │
│      └─ Use postings that FAILED in production (hard cases)         │
│                                                                      │
│   2. FOR EACH MODEL:                                                 │
│      ├─ Extract from all test cases                                 │
│      ├─ Measure latency                                             │
│      ├─ Check for degenerate output (local, fast)                   │
│      └─ Grade quality (uses AI teacher, slower)                     │
│                                                                      │
│   3. SCORE MODELS:                                                   │
│      └─ Combined score = (clean × 0.2) + (quality × 0.6) + (speed × 0.2)  │
│                                                                      │
│   4. SELECT WINNER                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Test Case Selection

**Best practice:** Test on cases that FAILED, not random ones.

```python
# Get postings that went to the "improve" step (failed initial grading)
SELECT DISTINCT posting_id FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE c.conversation_name = 'session_d_qwen25_improve'
```

Why? These are the *hard cases* that expose model weaknesses. If a model handles these well, it'll handle easy cases too.

### Quality Grading Prompt

We use a separate "teacher" model to grade extractions:

```
GRADING PROMPT:
───────────────────────────────────────────────────────────────────
You are grading a job description summary.

ORIGINAL JOB POSTING:
{original_posting}

STUDENT'S SUMMARY:
{extraction}

Grade on these criteria (0-100 each):

1. ACCURACY (25%): Is the information correct? No hallucinations?
2. COMPLETENESS (40%): Are key responsibilities and requirements included?
3. FORMATTING (10%): Does it follow the template?
4. ROLE TITLE (25%): Is the job title correct?

Provide:
- Individual scores for each criterion
- Overall weighted score (0-100)
- Brief explanation

Format:
ACCURACY: [score]
COMPLETENESS: [score]
FORMATTING: [score]
ROLE_TITLE: [score]
OVERALL: [weighted_score]
EXPLANATION: [1-2 sentences]
───────────────────────────────────────────────────────────────────
```

---

## Running a Benchmark

### Basic Usage

```bash
# Test on 5 random failed postings (quick sanity check)
python3 tools/benchmark_extraction.py --problematic 5

# Test specific postings you know are tricky
python3 tools/benchmark_extraction.py --posting-ids 10468,10471,10466

# Test only specific models
python3 tools/benchmark_extraction.py --models llama3.2:latest,qwen2.5:7b,mistral:latest

# Full benchmark with quality grading (slower, more accurate)
python3 tools/benchmark_extraction.py --problematic 15 --with-grading
```

### Recommended Workflow

1. **Quick Test (5 min):** Test 3 postings, no grading
   ```bash
   python3 tools/benchmark_extraction.py --problematic 3
   ```

2. **Medium Test (15 min):** Test 10 postings with grading
   ```bash
   python3 tools/benchmark_extraction.py --problematic 10 --with-grading
   ```

3. **Full Test (30 min):** Test all 15 failed postings with grading
   ```bash
   python3 tools/benchmark_extraction.py --problematic 15 --with-grading
   ```

---

## Interpreting Results

### The Report Card

```
┌──────────────────────────────────────────────────────────────────┐
│                    MODEL BENCHMARK RESULTS                        │
├──────────────────────────────────────────────────────────────────┤
│ Rank │ Model          │ Clean% │ Quality │ Speed  │ Score │ Rec  │
├──────────────────────────────────────────────────────────────────┤
│  1   │ qwen2.5:7b     │  100%  │  92/100 │  8.8s  │  91   │ ✅   │
│  2   │ mistral        │  100%  │  85/100 │ 11.7s  │  84   │ ✅   │
│  3   │ llama3.2       │  100%  │  70/100 │  4.2s  │  74   │ ⚠️   │
│  4   │ phi4-mini      │  100%  │  78/100 │  5.8s  │  79   │ ✅   │
│  5   │ gemma3:1b      │   67%  │  55/100 │  4.5s  │  52   │ ❌   │
└──────────────────────────────────────────────────────────────────┘
```

### Score Formula

```
Combined Score = (Clean% × 0.2) + (Quality × 0.6) + (Speed Score × 0.2)

Where Speed Score = max(0, 100 - (latency_seconds × 5))
  - 4s = 80 points
  - 10s = 50 points
  - 20s = 0 points
```

### What the Numbers Mean

| Clean Rate | Meaning |
|------------|---------|
| 100% | No degenerate outputs - safe to use |
| 80-99% | Occasional issues - needs monitoring |
| <80% | Frequent failures - not recommended |

| Quality Score | Meaning |
|---------------|---------|
| 90-100 | Excellent - rarely needs improvement step |
| 75-89 | Good - occasional improvement needed |
| 60-74 | Acceptable - frequent improvement needed |
| <60 | Poor - too many failures |

---

## Selecting a Model

### Decision Matrix

```
                    Quality Requirement
                    Low         Medium        High
                ┌───────────┬───────────┬───────────┐
         Fast   │ gemma3:1b │ llama3.2  │ phi4-mini │
Speed    ───────┼───────────┼───────────┼───────────┤
Req      Medium │ llama3.2  │ mistral   │ qwen2.5:7b│
         ───────┼───────────┼───────────┼───────────┤
         Slow   │ mistral   │ qwen2.5:7b│ gemma2    │
                └───────────┴───────────┴───────────┘
```

### Workflow 3001 Model Assignments

| Step | Current Model | Priority | Recommendation |
|------|---------------|----------|----------------|
| Extract | llama3.2 | Speed > Quality | Consider qwen2.5:7b for better 1st-pass |
| Grade | qwen2.5:7b | Quality | Keep - good at catching issues |
| Improve | qwen2.5:7b | Quality | Keep - needs to fix issues |
| Skills | qwen2.5:7b | Quality | Keep - structured extraction |

---

## Quick Reference

### Commands

```bash
# Quick benchmark (3 postings, no grading)
python3 tools/benchmark_extraction.py --problematic 3

# Full benchmark (15 postings, with grading)
python3 tools/benchmark_extraction.py --problematic 15 --with-grading

# Test specific models
python3 tools/benchmark_extraction.py --models qwen2.5:7b,mistral:latest

# Custom postings
python3 tools/benchmark_extraction.py --posting-ids 10468,10471
```

### Available Models (Local Ollama)

```bash
# List installed models
ollama list

# Common models for benchmarking
gemma3:1b        # Smallest, fastest
gemma3:4b        # Medium gemma
llama3.2:latest  # Fast, good quality
phi4-mini:latest # Small but capable
qwen2.5:7b       # Best quality
mistral:latest   # Good balance
gemma2:latest    # High quality, slow
```

### Interpreting Failures

| Failure Type | Symptom | Solution |
|--------------|---------|----------|
| Degenerate | Repeated text | Try different model |
| Incomplete | Missing sections | Use larger model or improve prompt |
| Inaccurate | Wrong role title | Check if posting is malformed |
| Slow | >20s per extraction | Try smaller model |

---

## Appendix: Sample Outputs

### Good Extraction (qwen2.5:7b)

```markdown
===OUTPUT TEMPLATE===
**Role:** Risk-Manager for FX Derivatives
**Company:** Deutsche Bank
**Location:** Singapore
**Job ID:** (not available)

**Key Responsibilities:**
- Managing portfolio risk-management for EM Asia Derivatives
- Oversee execution of client transactions and hedges
- Quoting the bank's franchise across currencies and derivatives
- Meeting with institutional and corporate clients
- Working with Sales and Structuring on new opportunities

**Requirements:**
- 6-10 years of prior work experience in FX Derivatives
- Specialty in EM Asia Currencies
- Experience with barrier derivatives, volatility swaps
- Strong analytical and quantitative skills

**Details:**
- Full-time, Singapore-based
- Hybrid working arrangement
- 25 days annual leave
```

### Poor Extraction (llama3.2) - Same Posting

```markdown
===OUTPUT TEMPLATE===
**Role:** FX Derivatives Trader    ← Wrong! Should be "Risk-Manager"
**Company:** Deutsche Bank
**Location:** Singapore

**Key Responsibilities:**
- Managing portfolio risk-management for EM Asia Derivatives
- Oversee execution of client transactions
- Quoting the bank's franchise         ← Truncated 3 more responsibilities

**Requirements:**
- 6-10 years of prior work experience
- Specialty in EM Asia Currencies      ← Missing details

**Details:**
- Full-time
- Hybrid working
```

---

## 8. Model Qualification Framework 🎯

When evaluating a model for production use, apply the **Five Pillars** test:

### Pillar 1: Stability (Does it crash?)
The model must produce parseable output 100% of the time on your test set.

**Test:** Run 100 diverse postings. Any degenerate loops = FAIL.

```python
stability_score = 1.0 - (degenerate_count / total_count)
# Requirement: stability_score >= 1.0 (zero tolerance)
```

### Pillar 2: Completeness (Does it find everything?)
The model must extract all the information a human would extract.

**Test:** Use golden test set with known answers. Count missing fields.

```python
completeness_score = extracted_fields / expected_fields
# Requirement: completeness_score >= 0.95
```

### Pillar 3: Accuracy (Is it correct?)
The extracted information must match the source document.

**Test:** Compare extracted values against source text. Count mismatches.

```python
accuracy_score = correct_extractions / total_extractions  
# Requirement: accuracy_score >= 0.98
```

### Pillar 4: Hallucination Rate (Does it make stuff up?)
The model must not invent information not present in the source.

**Test:** For each extracted skill/requirement, verify it appears in source.

```python
hallucination_rate = invented_fields / total_extracted_fields
# Requirement: hallucination_rate <= 0.01 (1%)
```

### Pillar 5: Speed (Is it fast enough?)
The model must process postings faster than alternatives.

**Test:** Measure average tokens/second and compare to baselines.

```python
speed_ratio = candidate_time / baseline_time
# Requirement: speed_ratio <= 1.5 (not more than 50% slower)
```

### Decision Matrix

| Pillar | Hard Fail | Soft Fail | Pass |
|--------|-----------|-----------|------|
| Stability | <100% | - | 100% |
| Completeness | <80% | 80-95% | >95% |
| Accuracy | <90% | 90-98% | >98% |
| Hallucination | >5% | 1-5% | <1% |
| Speed | >3x slower | 1.5-3x | <1.5x |

**Any Hard Fail = Reject the model.**

---

## 9. The Golden Test Set 🥇

A **Golden Test Set** is a collection of postings with **known correct answers**, verified by humans.

### Why Golden Tests?

When grading models, we face a circular problem:
- We use AI to grade AI
- The grader might be wrong
- We can't know if grades are accurate

Golden tests break the cycle by providing **ground truth**.

### Structure of a Golden Test

```json
{
  "posting_id": 12345,
  "source_text": "We're looking for a Senior Data Scientist...",
  "expected_extraction": {
    "title": "Senior Data Scientist",
    "company": "Acme Corp",
    "skills": ["Python", "Machine Learning", "SQL"],
    "experience_years": "5+"
  },
  "verified_by": "human",
  "verification_date": "2025-12-02"
}
```

### Creating Golden Tests

1. **Select diverse postings:** Mix of industries, lengths, complexities
2. **Extract manually:** Read source, write expected output
3. **Double-verify:** Have second person check
4. **Store permanently:** `tests/golden_extraction_cases.json`

### Using Golden Tests

```python
def grade_against_golden(extraction, golden):
    """Compare model extraction to golden truth."""
    errors = []
    
    for field, expected in golden['expected_extraction'].items():
        actual = extraction.get(field)
        if actual != expected:
            errors.append({
                'field': field,
                'expected': expected,
                'actual': actual
            })
    
    return {
        'score': 1.0 - len(errors) / len(golden['expected_extraction']),
        'errors': errors
    }
```

### Recommended Golden Set Size

- **Minimum:** 20 postings
- **Recommended:** 50-100 postings
- **Coverage:** At least 5 from each major industry vertical

---

## 10. Grading Consensus Analysis 🤝

When using multiple models (e.g., qwen for format grading, mistral for extraction grading), we need to know if the extra model adds value.

### The Question

> "Does qwen-grading-qwen-output catch anything that mistral alone wouldn't?"

### The Analysis Query

```sql
-- Compare grading verdicts between mistral and qwen graders
WITH grading_results AS (
    SELECT 
        posting_id,
        conversation_name,
        CASE 
            WHEN response ILIKE '%yes%' THEN 'yes'
            WHEN response ILIKE '%no%' THEN 'no'
            ELSE 'unclear'
        END as verdict
    FROM conversation_log
    WHERE conversation_name IN (
        'session_b_mistral_grade',
        'session_c_qwen25_grade'
    )
)
SELECT 
    m.verdict as mistral_verdict,
    q.verdict as qwen_verdict,
    COUNT(*) as count
FROM grading_results m
JOIN grading_results q ON m.posting_id = q.posting_id
WHERE m.conversation_name = 'session_b_mistral_grade'
  AND q.conversation_name = 'session_c_qwen25_grade'
GROUP BY m.verdict, q.verdict
ORDER BY count DESC;
```

### Interpreting Results

| Mistral | Qwen | What It Means |
|---------|------|---------------|
| yes | yes | ✅ Agreement - both pass |
| no | no | ✅ Agreement - both fail |
| yes | no | 🤔 Qwen more strict |
| no | yes | 🤔 Qwen more lenient |

### Decision Framework

```
If (yes, yes) + (no, no) > 95%:
    → Models agree, pick the faster one
    
If (yes, no) > 5%:
    → Qwen catches issues Mistral misses
    → Keep Qwen for quality
    
If (no, yes) > 5%:
    → Mistral is more strict
    → Keep Mistral, drop Qwen
```

### When to Use Two Graders

Use two graders when:
1. **Stakes are high:** Bad extractions have real cost
2. **Models have different biases:** One misses what another catches
3. **You're not sure:** Run consensus analysis first

Skip the second grader when:
1. **Consensus > 95%:** They agree anyway
2. **Speed matters more:** 2x latency isn't worth it
3. **Golden tests pass:** You have ground truth

---

*Last updated: December 2, 2025*
