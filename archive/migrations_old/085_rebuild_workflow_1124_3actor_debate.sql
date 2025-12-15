-- Migration 085: Rebuild Workflow 1124 as 3-Actor Debate
-- Date: 2025-11-10
-- Purpose: Replace single harsh judge with proper 3-actor debate (Analyst → Skeptic → HR Expert)
-- Previous issue: 100% of jobs scored as suspicious (7-9), no balanced judgment

BEGIN;

-- Step 1: Create Analyst Instruction (Step 2) - Find red flags
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    enabled
)
SELECT
    'IHL Analyst - Find Red Flags',
    conversation_id,
    2,
    'Actor 1: Analyze job posting to identify suspicious patterns and red flags',
    $PROMPT$You are a SKEPTICAL HR analyst who specializes in detecting fake job postings created for visa compliance theater.

Your role: Find as many red flags as possible. Be HARSH and suspicious.

JOB POSTING:
{job_description}

ANALYSIS FRAMEWORK:

**RED FLAGS TO CHECK:**
1. Overly specific years of experience with rare skill combinations
   Example: "Exactly 7 years Python + 5 years Kubernetes + 3 years in German banking"

2. Requirements for internal systems/tools only this company uses
   Example: "Experience with our proprietary ACME_TRADER platform required"

3. Impossibly narrow candidate pool
   Example: Geographic + industry + technical stack that rarely overlap

4. Resume-like specificity
   Example: "Led migration from Oracle 11g to 12c in Q2 2019"

5. Contradictory seniority signals
   Example: "Entry level" with "10+ years experience required"

**YOUR TASK:**
Output a JSON analysis identifying ALL red flags you can find. Suggest a HIGH IHL score (7-10) if you find ANY red flags.

```json
{
  "analyst_verdict": "PRE_WIRED|COMPLIANCE_THEATER|SUSPICIOUS",
  "suggested_ihl_score": <7-10>,
  "red_flags": [
    {
      "flag": "description of red flag",
      "evidence": "quote from posting",
      "severity": "LOW|MEDIUM|HIGH"
    }
  ],
  "reasoning": "1-2 sentences explaining why this job looks fake"
}
```

Output ONLY the JSON above, then add [SUCCESS] on a new line.
$PROMPT$,
    300,
    false,
    true
FROM conversations
WHERE conversation_id = 9125;

-- Step 2: Create Skeptic Instruction (Step 3) - Challenge the Analyst
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    enabled
)
SELECT
    'IHL Skeptic - Challenge Analyst',
    conversation_id,
    3,
    'Actor 2: Challenge the Analyst findings, argue job is legitimate',
    $PROMPT$You are a DEVIL'S ADVOCATE who challenges overly harsh assessments of job postings.

Your role: Review the Analyst's findings and argue for the job being GENUINE. Be OPTIMISTIC.

ORIGINAL JOB POSTING:
{job_description}

ANALYST'S VERDICT:
{session_r1_output}

**YOUR TASK:**
Challenge the Analyst's red flags. Find reasons why this could be a legitimate job posting:
- Are the requirements actually reasonable for the industry?
- Could specificity just mean they know what they want?
- Are there signs this is a REAL opening (application process, salary info, clear responsibilities)?

```json
{
  "skeptic_verdict": "GENUINE|PLAUSIBLE|WEAK_CASE",
  "suggested_ihl_score": <1-5>,
  "counter_arguments": [
    {
      "analyst_flag": "which red flag you're challenging",
      "counter_evidence": "why this might be legitimate",
      "severity_downgrade": "why this isn't as suspicious as claimed"
    }
  ],
  "reasoning": "1-2 sentences explaining why this job might be genuine"
}
```

Output ONLY the JSON above, then add [SUCCESS] on a new line.
$PROMPT$,
    300,
    false,
    true
FROM conversations
WHERE conversation_id = 9125;

-- Step 3: Create HR Expert Instruction (Step 4) - Final Balanced Decision
INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    enabled
)
SELECT
    'IHL HR Expert - Final Verdict',
    conversation_id,
    4,
    'Actor 3: Review both arguments and make balanced final decision',
    $PROMPT$You are a BALANCED HR expert with 20+ years experience. You've reviewed TWO perspectives on this job posting.

ORIGINAL JOB POSTING:
{job_description}

ANALYST VERDICT (Harsh):
{session_r1_output}

SKEPTIC VERDICT (Optimistic):
{session_r2_output}

**YOUR TASK:**
Review BOTH arguments. Make a BALANCED final decision.

**SCORING SCALE (0-10):**
- **0-3: GENUINE OPENING** - Normal job with reasonable requirements
- **4-6: BORDERLINE** - Some suspicious patterns but could be legitimate
- **7-9: COMPLIANCE THEATER** - Likely posted for formality, pre-wired candidate
- **10: FAKE JOB** - Clearly describes one specific person's resume

**REQUIRED OUTPUT FORMAT:**

```json
{
  "ihl_score": <number 0-10>,
  "verdict": "GENUINE|BORDERLINE|COMPLIANCE_THEATER|FAKE",
  "confidence": "LOW|MEDIUM|HIGH",
  "red_flags": [
    {
      "flag": "description of red flag",
      "evidence": "quote from posting",
      "severity": "LOW|MEDIUM|HIGH"
    }
  ],
  "candidate_pool_estimate": "LARGE (1000+)|MEDIUM (100-1000)|SMALL (10-100)|TINY (<10)",
  "recommendation": "APPLY|CAUTION|SKIP",
  "reasoning": "2-3 sentences explaining your final decision, considering both perspectives"
}
```

**IMPORTANT:**
1. Output ONLY the JSON above, no other text
2. Consider BOTH perspectives - don't just side with Analyst or Skeptic
3. Be FAIR - not all specific jobs are fake, not all vague jobs are genuine
4. After outputting the JSON, add [SUCCESS] on a new line

Output the JSON analysis now:
$PROMPT$,
    300,
    false,
    true
FROM conversations
WHERE conversation_id = 9125;

-- Step 4: Create Database Write Instruction (Step 4) - Script Execution
-- TODO: This will be a script_execution instruction that parses the JSON from Step 3
-- and writes to postings table. For now, we'll handle this separately.

COMMIT;

-- Verify new instructions
SELECT 
    i.instruction_id,
    i.instruction_name,
    i.step_number,
    i.enabled,
    LENGTH(i.prompt_template) as prompt_length
FROM instructions i
WHERE i.conversation_id = 9125
ORDER BY i.step_number;
