# Model Capability Testing Workflow

**Workflow ID:** TBD (3XXX series)  
**Status:** 🟡 DESIGN - Not Yet Implemented  
**Date:** November 24, 2025  
**Author:** Arden  
**Purpose:** Smart tiered capability testing for LLM models

---

## The Problem

**User Insight:** *"A model that cannot count to three, will not be able to count to four."*

**Scenario:**
```
We have 5 models:
- gemma3:1b (lightweight, fast, cheap)
- gemma2:latest (medium, 7B params, expensive GPU)
- qwen2.5:7b (advanced reasoning)
- llama3.2:3b (balanced)
- mistral:7b (specialist)

We have 3 complexity tiers of tasks:
- Tier 1 (Basic): Count to 3, extract JSON
- Tier 2 (Intermediate): Extract skills, format text  
- Tier 3 (Advanced): Multi-turn debate, complex reasoning

Question: Which models can handle which tasks?
```

**Problem:** Testing every model on every tier wastes compute:
```
5 models × 3 tiers × 10 test cases = 150 LLM calls
```

**Smart Approach:** Fail fast at lower tiers:
```
Model A: Tier 1 FAIL → Skip Tier 2, 3 (saved 20 calls)
Model B: Tier 1 PASS → Tier 2 FAIL → Skip Tier 3 (saved 10 calls)
Model C: Tier 1 PASS → Tier 2 PASS → Tier 3 PASS (run all)

Total: ~90 LLM calls instead of 150 (40% reduction!)
```

---

## Architecture

### Tiered Capability Model

```
TIER 1: BASIC LITERACY
├─ Can count to 3?
├─ Can extract simple JSON?
├─ Can follow single instruction?
└─ Pass Rate: 8/10 required → Tier 2

TIER 2: INTERMEDIATE SKILLS
├─ Can extract structured data (skills, dates)?
├─ Can format text (markdown, bullets)?
├─ Can handle multi-field extraction?
└─ Pass Rate: 7/10 required → Tier 3

TIER 3: ADVANCED REASONING
├─ Can conduct multi-turn conversation?
├─ Can synthesize information across messages?
├─ Can evaluate quality (debate, critique)?
└─ Pass Rate: 6/10 required → PRODUCTION READY
```

### Database Schema

```sql
-- Table: model_capabilities
CREATE TABLE model_capabilities (
    capability_id SERIAL PRIMARY KEY,
    actor_id INT REFERENCES actors(actor_id),
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    test_category TEXT NOT NULL,  -- 'counting', 'json_extraction', 'skill_extraction', etc.
    test_name TEXT NOT NULL,
    test_passed BOOLEAN NOT NULL,
    test_score FLOAT,  -- 0.0-1.0
    test_output JSONB,  -- Actual response
    expected_output JSONB,  -- Expected response
    tested_at TIMESTAMP DEFAULT NOW(),
    tested_by_workflow_run_id BIGINT REFERENCES workflow_runs(workflow_run_id),
    UNIQUE(actor_id, tier, test_name, tested_at)
);

CREATE INDEX idx_capabilities_actor_tier ON model_capabilities(actor_id, tier);
CREATE INDEX idx_capabilities_tested_at ON model_capabilities(tested_at DESC);

COMMENT ON TABLE model_capabilities IS 
'Model capability testing results. Tiered testing approach: Tier 1 (basic) → Tier 2 (intermediate) → Tier 3 (advanced). Models that fail lower tiers skip higher tiers (smart filtering).';

-- View: model_tier_summary
CREATE VIEW model_tier_summary AS
SELECT 
    a.actor_id,
    a.actor_name,
    a.model_name,
    mc.tier,
    COUNT(*) as tests_run,
    SUM(CASE WHEN test_passed THEN 1 ELSE 0 END) as tests_passed,
    ROUND(AVG(CASE WHEN test_passed THEN 1.0 ELSE 0.0 END) * 100, 1) as pass_rate,
    MAX(tested_at) as last_tested
FROM actors a
LEFT JOIN model_capabilities mc ON a.actor_id = mc.actor_id
WHERE a.actor_type = 'llm'
GROUP BY a.actor_id, a.actor_name, a.model_name, mc.tier
ORDER BY a.actor_name, mc.tier;

COMMENT ON VIEW model_tier_summary IS 
'Summary of model performance by tier. Use to determine which models are production-ready (pass all 3 tiers).';

-- Function: get_tier_qualified_actors(tier_level)
CREATE OR REPLACE FUNCTION get_tier_qualified_actors(tier_level INTEGER)
RETURNS TABLE(actor_id INT, actor_name TEXT, model_name TEXT) AS $$
BEGIN
    -- Return actors that passed all tiers up to tier_level
    RETURN QUERY
    WITH tier_results AS (
        SELECT 
            a.actor_id,
            a.actor_name,
            a.model_name,
            mc.tier,
            AVG(CASE WHEN test_passed THEN 1.0 ELSE 0.0 END) as pass_rate
        FROM actors a
        JOIN model_capabilities mc ON a.actor_id = mc.actor_id
        WHERE a.actor_type = 'llm'
        GROUP BY a.actor_id, a.actor_name, a.model_name, mc.tier
    )
    SELECT DISTINCT
        tr.actor_id,
        tr.actor_name,
        tr.model_name
    FROM tier_results tr
    WHERE tr.tier <= tier_level
    GROUP BY tr.actor_id, tr.actor_name, tr.model_name
    HAVING COUNT(DISTINCT tr.tier) = tier_level  -- Passed all tiers up to level
       AND MIN(tr.pass_rate) >= CASE 
           WHEN tier_level = 1 THEN 0.8  -- 80% for Tier 1
           WHEN tier_level = 2 THEN 0.7  -- 70% for Tier 2
           WHEN tier_level = 3 THEN 0.6  -- 60% for Tier 3
       END;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_tier_qualified_actors(INTEGER) IS 
'Get actors qualified for given tier level. Example: get_tier_qualified_actors(2) returns actors that passed Tier 1 AND Tier 2.';
```

---

## Workflow Design

### Workflow 3XXX: Model Capability Testing

**Input:**
- `actor_id` - Model to test (or NULL for "test all models")
- `tier` - Starting tier (default: 1)
- `force_retest` - Boolean (default: false - skip if recently tested)

**Output:**
- Capability test results saved to `model_capabilities` table
- Summary report: Which models qualified for which tiers

**Execution Pattern:**

```
FOR each model:
  Tier 1 tests (10 basic tests)
    ├─ Pass rate >= 80%? → Continue to Tier 2
    └─ Pass rate < 80%? → STOP (model not qualified)
  
  Tier 2 tests (10 intermediate tests)
    ├─ Pass rate >= 70%? → Continue to Tier 3
    └─ Pass rate < 70%? → STOP (Tier 1 only model)
  
  Tier 3 tests (10 advanced tests)
    ├─ Pass rate >= 60%? → PRODUCTION READY
    └─ Pass rate < 60%? → Tier 2 only model
```

---

## Tier 1: Basic Literacy Tests

### Test 1.1: Count to Three

**Conversation:**
- **Actor:** Target model being tested
- **Tag:** `model_testing_tier1_counting`
- **Prompt:**
  ```
  Count from 1 to 3. Output only the numbers, one per line.
  ```
- **Expected:**
  ```
  1
  2
  3
  ```
- **Validation:** Exact match or regex `^\s*1\s*2\s*3\s*$`

### Test 1.2: Simple JSON Extraction

**Prompt:**
```
Extract this information as JSON:

Name: John Smith
Age: 32
City: Berlin

Output format: {"name": "...", "age": ..., "city": "..."}
```

**Expected:**
```json
{"name": "John Smith", "age": 32, "city": "Berlin"}
```

**Validation:** JSON parse + field match

### Test 1.3: Follow Single Instruction

**Prompt:**
```
Say exactly this phrase: "The quick brown fox"

Do not add anything else.
```

**Expected:**
```
The quick brown fox
```

**Validation:** Strip whitespace, exact match

### Test 1.4: Basic Categorization

**Prompt:**
```
Categorize this job title:

"Senior Backend Engineer"

Is this title:
A) Technical
B) Management
C) Sales
D) Administrative

Output only the letter (A, B, C, or D).
```

**Expected:** `A`

**Validation:** Response contains "A"

### Test 1.5: Number Comparison

**Prompt:**
```
Which is larger: 15 or 23?

Output only the number.
```

**Expected:** `23`

**Validation:** Response contains "23"

### Test 1.6-1.10: Similar Basic Tests
- Boolean logic (true/false)
- Simple list creation
- Basic arithmetic
- Date parsing (extract year)
- Simple text transformation (uppercase)

**Pass Threshold:** 8/10 tests passed (80%)

---

## Tier 2: Intermediate Skills Tests

### Test 2.1: Skill Extraction

**Prompt:**
```
Extract technical skills from this job description:

"We are looking for a Python developer with experience in Django, 
PostgreSQL, and Docker. Knowledge of Kubernetes is a plus."

Output as JSON array: ["skill1", "skill2", ...]
```

**Expected:**
```json
["Python", "Django", "PostgreSQL", "Docker", "Kubernetes"]
```

**Validation:** At least 4/5 skills present (fuzzy match)

### Test 2.2: Multi-Field Structured Extraction

**Prompt:**
```
Extract information from this job posting:

Title: Senior Data Scientist
Location: Munich, Germany
Salary: €80,000 - €100,000
Type: Full-time
Remote: Hybrid (3 days office)

Output as JSON with fields: title, location_city, location_country, 
salary_min, salary_max, employment_type, remote_policy
```

**Expected:**
```json
{
  "title": "Senior Data Scientist",
  "location_city": "Munich",
  "location_country": "Germany",
  "salary_min": 80000,
  "salary_max": 100000,
  "employment_type": "Full-time",
  "remote_policy": "Hybrid"
}
```

**Validation:** 6/7 fields correct (fuzzy match)

### Test 2.3: Text Formatting (Markdown)

**Prompt:**
```
Format this text as a markdown bullet list:

Requirements: Python, 5 years experience, Bachelor's degree

Output as markdown bullets.
```

**Expected:**
```markdown
- Python
- 5 years experience
- Bachelor's degree
```

**Validation:** Contains `- ` before each item

### Test 2.4: Date Normalization

**Prompt:**
```
Convert these dates to ISO format (YYYY-MM-DD):

1. March 15, 2024
2. 12/25/2023
3. Jan 1st, 2025

Output as JSON array.
```

**Expected:**
```json
["2024-03-15", "2023-12-25", "2025-01-01"]
```

**Validation:** Valid ISO dates, correct values

### Test 2.5: Salary Range Parsing

**Prompt:**
```
Extract salary information:

"Compensation: $120k-$150k/year + equity"

Output as JSON: {"min": ..., "max": ..., "currency": "...", "equity": true/false}
```

**Expected:**
```json
{"min": 120000, "max": 150000, "currency": "USD", "equity": true}
```

**Validation:** All fields correct

### Test 2.6-2.10: Similar Intermediate Tests
- Company name normalization
- Technology stack categorization
- Education requirement extraction
- Experience level classification
- Multi-language text handling

**Pass Threshold:** 7/10 tests passed (70%)

---

## Tier 3: Advanced Reasoning Tests

### Test 3.1: Quality Assessment

**Prompt:**
```
Evaluate the quality of this job description:

"We need someone who knows computers. Must be good at stuff. 
Pay is okay. Start ASAP."

Rate quality on scale 1-10 and explain 3 specific issues.

Output as JSON:
{
  "quality_score": ...,
  "issues": ["issue1", "issue2", "issue3"]
}
```

**Expected:**
```json
{
  "quality_score": 2,
  "issues": [
    "Vague requirements ('knows computers', 'good at stuff')",
    "Missing specific skills or technologies",
    "Unclear compensation ('pay is okay')"
  ]
}
```

**Validation:** 
- quality_score <= 4 (it's objectively bad)
- At least 2/3 issues mention vagueness/lack of specificity

### Test 3.2: Multi-Turn Conversation (Debate)

**Multi-Turn Conversation:**

**Turn 1:**
```
Should this job require a college degree?

Title: "Junior Web Developer"
Requirements: "HTML, CSS, JavaScript, 1 year experience"

Argue YES (degree required).
```

**Turn 2:**
```
Now argue the opposite position: NO degree required.
Consider self-taught developers and bootcamp graduates.
```

**Validation:**
- Turn 1 response mentions: formal education, fundamentals, credibility
- Turn 2 response mentions: practical skills, portfolio, alternative paths
- Model can argue both sides coherently

### Test 3.3: Information Synthesis

**Prompt:**
```
Synthesize information from these 3 job postings and identify common skills:

Posting 1: "Looking for Python developer with Django and PostgreSQL"
Posting 2: "Backend engineer needed. Python, Flask, MySQL required"
Posting 3: "Full-stack role: Python (Django), React, PostgreSQL"

Output:
{
  "common_skills": [...],
  "common_technologies": [...],
  "skill_frequency": {"Python": 3, "Django": 2, ...}
}
```

**Expected:**
```json
{
  "common_skills": ["Python"],
  "common_technologies": ["Django", "PostgreSQL"],
  "skill_frequency": {
    "Python": 3,
    "Django": 2,
    "PostgreSQL": 2,
    "Flask": 1,
    "MySQL": 1,
    "React": 1
  }
}
```

**Validation:**
- Identifies Python as universal (3/3)
- Correctly counts frequencies
- Distinguishes skills from technologies

### Test 3.4: Reasoning Chain

**Prompt:**
```
A job requires "5+ years Python experience" but candidate has:
- 2 years professional Python
- 3 years Python for data analysis (academic research)
- Multiple Python projects on GitHub

Does the candidate meet the requirement?

Explain your reasoning step-by-step, then give final answer (YES/NO).
```

**Expected:**
```
Step 1: Professional experience (2 years) is below requirement (5 years)
Step 2: However, academic Python experience (3 years) is relevant
Step 3: Total Python experience = 2 + 3 = 5 years
Step 4: GitHub projects demonstrate practical skill

Final Answer: YES - Candidate meets the 5+ years requirement when 
combining professional and academic experience.
```

**Validation:**
- Shows step-by-step reasoning
- Considers multiple experience types
- Final answer is YES
- Justification mentions combining experience

### Test 3.5: Edge Case Handling

**Prompt:**
```
Extract salary from this posting:

"Salary: Competitive, based on experience. Equity included. 
Benefits package worth estimated €15k/year."

Output as JSON:
{
  "salary_disclosed": true/false,
  "salary_min": ...,
  "salary_max": ...,
  "notes": "..."
}
```

**Expected:**
```json
{
  "salary_disclosed": false,
  "salary_min": null,
  "salary_max": null,
  "notes": "Salary listed as 'competitive' (not disclosed). Equity and benefits (€15k value) mentioned."
}
```

**Validation:**
- Correctly identifies non-disclosure
- Returns null for unknown values
- Captures additional context in notes

### Test 3.6-3.10: Similar Advanced Tests
- Ambiguity resolution
- Cross-cultural job title mapping
- Implicit requirement inference
- Inconsistency detection
- Context-aware skill extraction

**Pass Threshold:** 6/10 tests passed (60%)

---

## Implementation: Script Actor

### Actor: `test_model_capabilities.py`

```python
# scripts/test_model_capabilities.py

import psycopg2
import json
import re
from datetime import datetime, timedelta

def execute(interaction_id: int, params: dict) -> dict:
    """Test model capabilities across tiers.
    
    Args:
        interaction_id: Current interaction
        params: {
            'actor_id': int or None (None = test all LLM actors),
            'tier': int (1, 2, or 3 - starting tier),
            'force_retest': bool (skip recently tested models)
        }
    
    Returns:
        {
            'tested_models': int,
            'tier1_qualified': [actor_ids],
            'tier2_qualified': [actor_ids],
            'tier3_qualified': [actor_ids],
            'results_summary': {...}
        }
    """
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    
    # Get models to test
    if params.get('actor_id'):
        models = [(params['actor_id'],)]
    else:
        cursor.execute("""
            SELECT actor_id 
            FROM actors 
            WHERE actor_type = 'llm' AND is_active = TRUE
        """)
        models = cursor.fetchall()
    
    tier1_qualified = []
    tier2_qualified = []
    tier3_qualified = []
    
    for (actor_id,) in models:
        # Check if recently tested (skip if not force_retest)
        if not params.get('force_retest', False):
            cursor.execute("""
                SELECT MAX(tested_at)
                FROM model_capabilities
                WHERE actor_id = %s
            """, (actor_id,))
            last_test = cursor.fetchone()[0]
            if last_test and last_test > datetime.now() - timedelta(days=7):
                print(f"Skipping actor {actor_id} - tested recently")
                continue
        
        # Tier 1 tests
        tier1_pass = run_tier1_tests(cursor, actor_id, interaction_id)
        
        if tier1_pass:
            tier1_qualified.append(actor_id)
            
            # Tier 2 tests
            tier2_pass = run_tier2_tests(cursor, actor_id, interaction_id)
            
            if tier2_pass:
                tier2_qualified.append(actor_id)
                
                # Tier 3 tests
                tier3_pass = run_tier3_tests(cursor, actor_id, interaction_id)
                
                if tier3_pass:
                    tier3_qualified.append(actor_id)
    
    conn.commit()
    conn.close()
    
    return {
        'tested_models': len(models),
        'tier1_qualified': tier1_qualified,
        'tier2_qualified': tier2_qualified,
        'tier3_qualified': tier3_qualified,
        'summary': f"Tested {len(models)} models. "
                  f"Tier 1: {len(tier1_qualified)}, "
                  f"Tier 2: {len(tier2_qualified)}, "
                  f"Tier 3: {len(tier3_qualified)} qualified."
    }


def run_tier1_tests(cursor, actor_id, workflow_run_id):
    """Run all Tier 1 tests for a model."""
    tests = [
        test_counting,
        test_json_extraction,
        test_follow_instruction,
        test_categorization,
        test_number_comparison,
        test_boolean_logic,
        test_list_creation,
        test_arithmetic,
        test_date_parsing,
        test_text_transform
    ]
    
    passed = 0
    for test_fn in tests:
        result = test_fn(cursor, actor_id, workflow_run_id)
        if result['passed']:
            passed += 1
        
        # Save result
        save_test_result(cursor, actor_id, 1, result, workflow_run_id)
    
    pass_rate = passed / len(tests)
    return pass_rate >= 0.8  # 80% threshold


def test_counting(cursor, actor_id, workflow_run_id):
    """Test 1.1: Count to Three."""
    prompt = "Count from 1 to 3. Output only the numbers, one per line."
    
    # Create interaction (simplified - actual would use Wave Runner)
    response = execute_llm(cursor, actor_id, prompt)
    
    # Validate
    cleaned = re.sub(r'\s+', '', response.strip())
    passed = cleaned == '123' or re.match(r'^\s*1\s*2\s*3\s*$', response)
    
    return {
        'test_category': 'counting',
        'test_name': 'count_to_three',
        'passed': passed,
        'score': 1.0 if passed else 0.0,
        'output': response,
        'expected': '1\n2\n3'
    }


def execute_llm(cursor, actor_id, prompt):
    """Execute LLM and return response.
    
    In production, this would:
    1. Create interaction record with prompt
    2. Execute via Wave Runner
    3. Return response from interaction.output
    
    For now, simplified placeholder.
    """
    # TODO: Integrate with Wave Runner V2
    # For now, return mock response for testing
    return "1\n2\n3"  # Mock


def save_test_result(cursor, actor_id, tier, result, workflow_run_id):
    """Save test result to model_capabilities table."""
    cursor.execute("""
        INSERT INTO model_capabilities 
        (actor_id, tier, test_category, test_name, test_passed, 
         test_score, test_output, expected_output, tested_by_workflow_run_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        actor_id,
        tier,
        result['test_category'],
        result['test_name'],
        result['passed'],
        result['score'],
        json.dumps({'response': result['output']}),
        json.dumps({'expected': result['expected']}),
        workflow_run_id
    ))
```

---

## Monitoring Queries

### Check Model Qualifications

```sql
-- Which models are production-ready? (Tier 3 qualified)
SELECT * FROM get_tier_qualified_actors(3);

-- Which models passed basic tests? (Tier 1)
SELECT * FROM get_tier_qualified_actors(1);

-- Summary by tier
SELECT * FROM model_tier_summary
ORDER BY actor_name, tier;
```

### Test Coverage

```sql
-- How many tests per model?
SELECT 
  a.actor_name,
  COUNT(*) as total_tests,
  SUM(CASE WHEN mc.tier = 1 THEN 1 ELSE 0 END) as tier1_tests,
  SUM(CASE WHEN mc.tier = 2 THEN 1 ELSE 0 END) as tier2_tests,
  SUM(CASE WHEN mc.tier = 3 THEN 1 ELSE 0 END) as tier3_tests
FROM actors a
JOIN model_capabilities mc ON a.actor_id = mc.actor_id
GROUP BY a.actor_name
ORDER BY total_tests DESC;
```

### Failure Analysis

```sql
-- Which tests are hardest? (most failures)
SELECT 
  tier,
  test_category,
  test_name,
  COUNT(*) as attempts,
  SUM(CASE WHEN test_passed THEN 1 ELSE 0 END) as passed,
  ROUND(AVG(CASE WHEN test_passed THEN 1.0 ELSE 0.0 END) * 100, 1) as pass_rate
FROM model_capabilities
GROUP BY tier, test_category, test_name
ORDER BY pass_rate ASC, attempts DESC;
```

---

## Benefits

### 1. **Compute Efficiency** (40% reduction)
```
Naive: 5 models × 30 tests = 150 LLM calls
Smart: ~90 LLM calls (skip higher tiers on failures)
Savings: 60 calls = 40% reduction
```

### 2. **Fast Failure Detection**
```
Bad model detected in 10 tests (Tier 1)
vs
150 tests (all tiers)
```

### 3. **Clear Model Segmentation**
```
Tier 1 models: Basic extraction only (gemma3:1b)
Tier 2 models: Structured extraction (llama3.2:3b)
Tier 3 models: Advanced reasoning (qwen2.5:7b, gemma2:latest)
```

### 4. **Production Readiness Confidence**
```
Model passed Tier 3? → Safe for debate, quality checks
Model only passed Tier 1? → Only use for basic extraction
```

---

## Integration with A/B Testing

**Combine with TEST_DATA_MANAGEMENT.md:**

```sql
-- Select champion challenger for Tier 2 tasks
WITH tier2_models AS (
  SELECT actor_id 
  FROM get_tier_qualified_actors(2)  -- Tier 2 qualified
)
SELECT 
  a.actor_id,
  a.actor_name,
  mp.performance_score
FROM actors a
JOIN tier2_models t2 ON a.actor_id = t2.actor_id
JOIN model_performance mp ON a.actor_id = mp.actor_id
WHERE a.is_production = TRUE
ORDER BY mp.performance_score DESC
LIMIT 2;  -- Champion + 1 challenger
```

**Workflow:**
1. Run capability testing → Identify qualified models
2. Run shadow testing → Measure performance on real data
3. Select champion → Highest performance_score from qualified pool
4. Canary rollout → Gradually increase traffic to champion

---

## Next Steps

**Implementation Plan:**

### Phase 1: Schema (30 min)
- Create `model_capabilities` table
- Create `model_tier_summary` view
- Create `get_tier_qualified_actors()` function

### Phase 2: Test Definitions (2 hours)
- Define all 30 tests (10 per tier)
- Create test validation functions
- Document expected outputs

### Phase 3: Script Actor (3 hours)
- Implement `test_model_capabilities.py`
- Integrate with Wave Runner V2
- Add error handling, logging

### Phase 4: Workflow Creation (1 hour)
- Create workflow 3XXX definition
- Add to workflows table
- Test with gemma3:1b (should pass Tier 1 only)
- Test with qwen2.5:7b (should pass all tiers)

### Phase 5: Automation (1 hour)
- Set up weekly cron job
- Auto-test new models on first use
- Integration with champion selection

**Total Estimate:** 1 day of implementation

---

## Summary

**Problem:** Which models can handle which tasks?

**Solution:** Smart tiered testing with fail-fast approach

**Key Insight:** "A model that cannot count to three, will not be able to count to four."

**Benefits:**
- 40% compute reduction (skip impossible tests)
- Fast failure detection (10 tests vs 30)
- Clear model segmentation (Tier 1/2/3)
- Production confidence (passed all tiers)

**Integration:**
- Capability testing → Qualified models
- Shadow testing → Performance metrics
- Champion selection → Best qualified model
- Canary rollout → Production deployment

**Status:** Ready to implement! 🚀

---

**User Quote:** *"But be smart - a model that cannot count to three, will not be able to count to four."* ✨
