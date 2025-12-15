# Model Optimization Cookbook
## Systematic Benchmarking for Production Model Selection

**Created:** November 26, 2025  
**Purpose:** Find the fastest correct model for each workflow task through systematic testing  
**Philosophy:** Engineering over guesswork. Data over popularity. Speed matters when correctness is equal.

---

## 🎯 Core Principle

> **"Test all relevant models. The champion passes 5/5 test cases AND has the best time. Runner-up is next in line. These two we use for production."**

**Why Two Models?**
- **Champion:** Primary production model (fastest + correct)
- **Runner-up:** Backup/redundancy + dual validation for critical tasks

---

## 📊 Methodology

### 1. Test Case Design

For each task type (grading, extraction, formatting, etc.):

**Requirements:**
- **10 total test cases**
  - 5 should PASS (good examples)
  - 5 should FAIL (bad examples with known issues)
- **Gold standard labels** (human-verified correct answer)
- **Diverse difficulty** (easy, medium, hard)
- **Real production data** (actual postings, not synthetic)

**Test Case Template:**
```markdown
### Test Case ID: GRADE_001

**Type:** Should PASS  
**Difficulty:** Easy  
**Posting ID:** 176  
**Summary:** [accurate, complete, well-formatted summary]  
**Expected Output:** [PASS] + positive reasoning  
**Why:** Summary matches posting exactly, no hallucinations  

**Gold Standard:**
- Verdict: PASS
- Accuracy: 10/10
- Completeness: 10/10
- Formatting: 10/10
```

### 2. Scoring System

**Correctness Score:**
```
Correct = Model verdict matches gold standard
Score = (Correct outputs / Total test cases) × 100
Minimum to qualify: 100% (10/10)
```

**Speed Score:**
```
Latency = Average milliseconds per test case
Speed Score = 1000 / (latency_ms / 1000)
Higher is better
```

**Final Ranking:**
```
1. Filter: Only models with 100% correctness
2. Sort: By speed (fastest first)
3. Champion: Rank 1
4. Runner-up: Rank 2
```

### 3. Batching Strategy

**Run tests in batches of 5:**
- Ensures consistency (model must be correct 5 times in a row)
- Mimics production load
- Exposes reliability issues (intermittent failures)
- Allows statistical variance analysis

**Batch Results:**
```
Model: qwen2.5:7b
Batch 1: 5/5 correct, avg 2100ms
Batch 2: 5/5 correct, avg 2050ms
Overall: 10/10 correct, avg 2075ms
Status: QUALIFIED ✅
```

### 4. Model Selection Criteria

**Include models if:**
- Type: `ai_model` (exclude scripts, embeddings)
- Size: Fits GPU constraints (< 8GB recommended)
- Purpose: Conversational (exclude code-only, vision-only)
- Status: Available in actors table

**Current Candidates (20+ models):**
```sql
SELECT actor_id, actor_name, execution_path
FROM actors
WHERE actor_type = 'ai_model'
  AND actor_name NOT LIKE '%code%'  -- Exclude code-only
  AND actor_name NOT LIKE '%vision%'  -- Exclude vision-only
  AND enabled = TRUE
ORDER BY actor_name;
```

---

## 🔬 Benchmark: Grading Task (November 2025)

### Task Definition

**Input:** Raw job posting + AI-generated summary  
**Output:** [PASS] or [FAIL] + reasoning  
**Success Criteria:**
- Correct verdict (matches gold standard)
- Clear reasoning (explains decision)
- Consistent format (structured output)

### Test Cases Registry

#### Should PASS (5 cases)

**GRADE_PASS_001: Perfect Summary**
- Posting: 176 (Deutsche Bank, complete data)
- Summary: Accurate role, responsibilities, requirements
- Gold: PASS (10/10 accuracy, 10/10 completeness)

**GRADE_PASS_002: Minor Formatting Variation**
- Posting: 1041 (Real production posting)
- Summary: Correct content, slightly different bullet format
- Gold: PASS (9/10 formatting, content accurate)

**GRADE_PASS_003: Concise but Complete**
- Posting: [TBD - select from database]
- Summary: Brief but captures all key points
- Gold: PASS (conciseness is not a flaw)

**GRADE_PASS_004: Detailed Summary**
- Posting: [TBD]
- Summary: Very detailed, includes all posting elements
- Gold: PASS (detail is acceptable if accurate)

**GRADE_PASS_005: Edge Case - Minimal Posting**
- Posting: Short posting with limited info
- Summary: Accurately reflects limited information
- Gold: PASS (summary matches sparse source)

#### Should FAIL (5 cases)

**GRADE_FAIL_001: Hallucinated Details**
- Posting: 4794 (Generic minimal posting)
- Summary: Contains fabricated job duties, made-up requirements
- Gold: FAIL (accuracy 2/10, hallucinations present)
- From: Actual Run 173 interaction 534 output

**GRADE_FAIL_002: Missing Key Information**
- Posting: [TBD - rich posting]
- Summary: Omits critical requirements or responsibilities
- Gold: FAIL (completeness 5/10)

**GRADE_FAIL_003: Wrong Company/Role**
- Posting: Deutsche Bank role
- Summary: Lists wrong company name or job title
- Gold: FAIL (accuracy 0/10, critical error)

**GRADE_FAIL_004: Template Spam**
- Posting: Real posting
- Summary: Generic template, not extracted from posting
- Gold: FAIL (accuracy 1/10, not tailored)

**GRADE_FAIL_005: Formatting Chaos**
- Posting: Any
- Summary: Unstructured blob, no template format
- Gold: FAIL (formatting 2/10, unusable)

### Benchmark Results (TBD - To Be Executed)

| Rank | Model | Size | Correctness | Avg Latency | Speed Score | Status |
|------|-------|------|-------------|-------------|-------------|--------|
| 🥇 | TBD | - | -/10 | -ms | - | Champion |
| 🥈 | TBD | - | -/10 | -ms | - | Runner-up |
| 3 | TBD | - | -/10 | -ms | - | Qualified |
| - | gemma2:latest | 5.4GB | ?/10 | ?ms | ? | **Current (to replace)** |
| - | qwen2.5:7b | 4.7GB | ?/10 | ?ms | ? | **Current (baseline)** |

### Analysis Template

**After running benchmark:**

```markdown
## Grading Task Analysis (Nov 26, 2025)

**Test Date:** 2025-11-26
**Models Tested:** 18
**Qualified Models:** 12 (100% correctness)

### Top 5 Results

1. **[Model Name]** - Champion ⭐
   - Correctness: 10/10 (100%)
   - Avg Latency: Xms
   - Speed Score: Y
   - Notes: [Why this model won - reasoning quality, consistency, etc.]

2. **[Model Name]** - Runner-up
   - Correctness: 10/10 (100%)
   - Avg Latency: Xms
   - Speed Score: Y
   - Notes: [Strengths, why it's backup]

[... 3 more ...]

### Failed to Qualify

- **[Model Name]**: 8/10 correctness (Failed GRADE_FAIL_001 and GRADE_PASS_003)
- **[Model Name]**: 9/10 correctness (Failed GRADE_FAIL_002)

### Key Insights

- [Pattern observations]
- [Speed vs size correlations]
- [Family performance patterns]
```

---

## 🛠️ Benchmark Runner Tool

### Tool: `tools/benchmark_models.py`

**Purpose:** Automated model testing with standardized scoring

**Usage:**
```bash
# Run grading task benchmark on all models
python3 tools/benchmark_models.py --task grading --test-cases tests/grading_test_cases.json

# Run on specific models only
python3 tools/benchmark_models.py --task grading --models qwen2.5:7b,gemma2:latest,llama3.2:latest

# Run with batching (5 runs per model)
python3 tools/benchmark_models.py --task grading --batch-size 5 --output reports/grading_benchmark_nov26.md
```

**Features:**
- Load test cases from JSON
- Execute each model through all test cases
- Measure latency per interaction
- Calculate correctness score
- Rank models by correctness → speed
- Generate markdown report
- Store results in database for trend analysis

**Output:**
```
🔬 Benchmark: Grading Task
📅 Date: 2025-11-26 12:30:15

Testing 18 models with 10 test cases each...

[1/18] qwen2.5:7b
  ├─ GRADE_PASS_001: ✅ PASS (2.1s)
  ├─ GRADE_PASS_002: ✅ PASS (2.0s)
  ├─ GRADE_PASS_003: ✅ PASS (2.2s)
  ├─ GRADE_PASS_004: ✅ PASS (2.1s)
  ├─ GRADE_PASS_005: ✅ PASS (2.0s)
  ├─ GRADE_FAIL_001: ✅ FAIL (2.3s)
  ├─ GRADE_FAIL_002: ✅ FAIL (2.1s)
  ├─ GRADE_FAIL_003: ✅ FAIL (2.2s)
  ├─ GRADE_FAIL_004: ✅ FAIL (2.0s)
  └─ GRADE_FAIL_005: ✅ FAIL (2.1s)
  Result: 10/10 ✅ | Avg: 2.11s | Score: 474

[2/18] gemma2:latest
  ├─ GRADE_PASS_001: ✅ PASS (3.8s)
  └─ ...
  
... (continuing through all models)

📊 Final Rankings:
🥇 Champion: qwen2.5:7b (10/10, 2.11s, score 474)
🥈 Runner-up: llama3.2:latest (10/10, 2.35s, score 426)
🥉 Third: mistral-nemo:12b (10/10, 2.89s, score 346)

⚠️ Did Not Qualify:
- gemma3:1b: 9/10 (too lenient on GRADE_FAIL_001)
- phi4-mini:latest: 8/10 (too strict on GRADE_PASS_002 and GRADE_PASS_005)

📄 Full report: reports/grading_benchmark_nov26.md
```

---

## 📋 Production Champion Registry

### Current Production Models (November 26, 2025)

**Last Updated:** 2025-11-26 (pre-benchmark)

#### Workflow 3001: Complete Job Processing Pipeline

| Conversation | Task | Champion | Runner-up | Status |
|--------------|------|----------|-----------|--------|
| Extract (3335) | Summary generation | gemma3:1b | - | ✅ Working |
| Grade A (3336) | Grading (terminal) | gemma2:latest | - | ⚠️ **Too large for GPU** |
| Grade B (3337) | Grading (drives workflow) | qwen2.5:7b | - | ✅ Working |
| Improve (3338) | Summary improvement | qwen2.5:7b | - | ✅ Working |
| Regrade (3339) | Re-grading | qwen2.5:7b | - | ✅ Working |
| Ticket (3340) | Ticket creation | qwen2.5:7b | - | ✅ Working |
| Format (3341) | Format standardization | gemma2:latest | - | ⚠️ **Too large for GPU** |

**Issues Identified:**
- ⚠️ **gemma2:latest** used in 2 conversations, GPU constraint
- ⚠️ **Grade A** is terminal (no branching), could be removed OR replaced
- ✅ **qwen2.5:7b** used in 4 conversations, batching opportunity

**Benchmark Goal:**
- Find faster replacement for gemma2:latest (Grade A, Format)
- Optimize for Wave Runner batching (same model = batch together)

#### Other Workflows

**TBD** - As workflows are benchmarked

---

## 🎯 Benchmark Execution Playbook

### Step 1: Define Test Cases (30 min)

1. Choose task type (grading, extraction, formatting, etc.)
2. Select 10 test cases from production data
   - 5 should PASS
   - 5 should FAIL
3. Get gold standard labels (human verification or consensus)
4. Document in JSON format

**Template:**
```json
{
  "task_type": "grading",
  "version": "1.0",
  "created": "2025-11-26",
  "test_cases": [
    {
      "id": "GRADE_PASS_001",
      "type": "PASS",
      "difficulty": "easy",
      "posting_id": 176,
      "summary": "...",
      "expected_verdict": "PASS",
      "expected_scores": {
        "accuracy": 10,
        "completeness": 10,
        "formatting": 10
      },
      "reasoning": "Perfect match, no hallucinations"
    }
  ]
}
```

### Step 2: Prepare Models (10 min)

```sql
-- Get all eligible models
SELECT actor_id, actor_name, execution_path
FROM actors
WHERE actor_type = 'ai_model'
  AND enabled = TRUE
  AND actor_name NOT IN ('codegemma:2b', 'bge-m3:567m')  -- Exclude specialists
ORDER BY actor_name;
```

Save list to `tests/models_to_benchmark.txt`

### Step 3: Run Benchmark (automated)

```bash
cd /home/xai/Documents/ty_learn

# Run benchmark with batching
python3 tools/benchmark_models.py \
  --task grading \
  --test-cases tests/grading_test_cases.json \
  --models-file tests/models_to_benchmark.txt \
  --batch-size 5 \
  --output reports/grading_benchmark_$(date +%Y%m%d).md
```

**Estimated Time:**
- 20 models × 10 test cases × 3s avg = ~10 minutes
- Add 20% for model loading = ~12 minutes total

### Step 4: Review Results (15 min)

1. Open generated report
2. Verify champion has 100% correctness
3. Verify runner-up has 100% correctness
4. Check for patterns (family performance, size vs speed)
5. Document insights

### Step 5: Update Production (15 min)

```sql
-- Update conversation to use new champion model

-- Get new actor_id
SELECT actor_id, actor_name FROM actors WHERE actor_name = '<CHAMPION_MODEL>';

-- Update conversation
UPDATE conversations
SET actor_id = <NEW_ACTOR_ID>
WHERE conversation_id = <CONVERSATION_ID>;

-- Verify
SELECT c.conversation_name, a.actor_name
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
WHERE c.conversation_id = <CONVERSATION_ID>;
```

### Step 6: Regenerate Workflow Docs (2 min)

```bash
python3 tools/_document_workflow.py 3001
```

### Step 7: Validation Test (10 min)

Run workflow with new model, compare results to baseline:

```python
from core.turing_orchestrator import TuringOrchestrator

orchestrator = TuringOrchestrator()
result = orchestrator.run_workflow(
    workflow_id=3001,
    task_data={'posting_ids': [4794]}  # Known test case
)
```

Compare:
- Same correctness as before
- Faster execution time
- GPU memory usage reduced

---

## 📈 Continuous Improvement

### Re-benchmark When:

1. **New model released** (monthly check)
2. **GPU constraints change** (hardware upgrade/downgrade)
3. **Task requirements change** (new grading criteria)
4. **Performance issues** (current champion too slow)
5. **Quarterly review** (best practice)

### Trend Analysis

Track champion performance over time:

```sql
CREATE TABLE IF NOT EXISTS benchmark_history (
    benchmark_id SERIAL PRIMARY KEY,
    task_type VARCHAR(50),
    model_name VARCHAR(100),
    correctness_score DECIMAL(5,2),
    avg_latency_ms INTEGER,
    speed_score DECIMAL(10,2),
    rank INTEGER,
    benchmark_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Query trends:**
```sql
-- Champion evolution for grading task
SELECT benchmark_date::DATE, model_name, avg_latency_ms
FROM benchmark_history
WHERE task_type = 'grading' AND rank = 1
ORDER BY benchmark_date DESC;
```

---

## 🧪 Test Case Library

### Grading Task

**File:** `tests/grading_test_cases.json`  
**Status:** Template ready, needs real data from Run 173  
**Test Cases:** 10 (5 PASS, 5 FAIL)

### Extraction Task

**File:** `tests/extraction_test_cases.json`  
**Status:** Not yet created  
**Test Cases:** TBD

### Formatting Task

**File:** `tests/formatting_test_cases.json`  
**Status:** Not yet created  
**Test Cases:** TBD

---

## 💡 Best Practices

### 1. Use Real Production Data

**DO:**
- Test cases from actual workflow runs
- Real postings from database
- Known failure cases from production

**DON'T:**
- Synthetic "perfect" examples
- Toy data that doesn't represent production
- Only easy cases

### 2. Verify Gold Standards

**DO:**
- Human verification of expected outputs
- Consensus from multiple reviewers
- Document reasoning for each label

**DON'T:**
- Assume model output is correct
- Use untested assumptions
- Skip verification step

### 3. Test in Production-Like Conditions

**DO:**
- Same prompt templates as production
- Same context strategy
- Same timeout settings

**DON'T:**
- Optimize prompts for benchmark only
- Use special "benchmark mode"
- Test with different settings than production

### 4. Document Everything

**DO:**
- Why each test case was chosen
- Why champion was selected
- Date of last benchmark
- Changes made to production

**DON'T:**
- Change models without documentation
- Forget to update workflow docs
- Skip validation testing

---

## 📚 Related Documentation

- **[LLM Profiles Index](llm_profiles/INDEX.md)** - Individual model characteristics
- **[DynaTax Recommendations](llm_profiles/DYNATAX_RECOMMENDATIONS.md)** - Task-specific model selection
- **[Workflow 3001 Documentation](workflows/3001_complete_job_processing_pipeline.md)** - Current production workflow
- **[Model Psychology Sessions](ARDEN_LLM_PSYCHOLOGY_SESSIONS.md)** - Original research

---

## 🚀 Next Steps

### Immediate (Nov 26, 2025)

1. ✅ Create this cookbook (DONE)
2. ⏳ Create grading test cases JSON (use Run 173 data)
3. ⏳ Build `tools/benchmark_models.py` script
4. ⏳ Run grading benchmark (18 models)
5. ⏳ Replace gemma2:latest with champion
6. ⏳ Validate Workflow 3001 performance

### Short-term (Dec 2025)

- Create extraction task benchmark
- Create formatting task benchmark
- Implement trend tracking (benchmark_history table)
- Automate monthly re-benchmarking

### Long-term (Q1 2026)

- Expand to all workflow tasks
- Build benchmark dashboard
- Integrate with CI/CD
- Champion rotation automation

---

**Philosophy:**
> "Engineering over guesswork. The fastest correct model wins. Runner-up provides redundancy. Data decides, not popularity."

*Created with love and precision by Arden 💙*
