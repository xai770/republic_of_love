-- Migration 067: Add IHL Calculator Instruction to Workflow 2001
-- Replaces conversation 9125 (which has no instructions) with working IHL calculation
--
-- IHL (Intrinsic Hiring Logic) detects "fake jobs" posted for compliance but already staffed internally
-- Scoring: 1-10 where 8-10 = PRE-WIRED/FAKE, 4-7 = COMPLIANCE THEATER, 1-3 = GENUINE
--
-- Author: GitHub Copilot + xai
-- Date: 2025-11-09

BEGIN;

-- Step 1: Create instruction for conversation 9125 (IHL Calculator)
-- This conversation already exists and is linked to Workflow 2001 at execution_order=20
-- We just need to add the instruction that was missing

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
    'Calculate IHL Score (Intrinsic Hiring Logic)',
    9125,  -- Existing conversation: "Fake Job Detector Debate"
    1,     -- First step
    'Analyze job posting to detect if it is pre-wired for a specific candidate (compliance theater vs genuine opening)',
    $PROMPT$You are a seasoned HR expert with 20+ years experience analyzing job market patterns.

TASK: Analyze this job posting and determine if it's a GENUINE opening or a PRE-WIRED "fake job" posted for compliance but already staffed.

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

**SCORING SCALE (1-10):**
- **1-3: GENUINE OPENING** - Selective but reasonable requirements for the role
- **4-7: COMPLIANCE THEATER** - Suspicious patterns but could be plausible
- **8-10: PRE-WIRED / FAKE JOB** - Clearly describes one specific person's resume

**REQUIRED OUTPUT FORMAT:**

```json
{
  "ihl_score": <number 1-10>,
  "verdict": "<GENUINE|COMPLIANCE_THEATER|PRE_WIRED>",
  "confidence": "<LOW|MEDIUM|HIGH>",
  "red_flags": [
    {
      "flag": "<description of red flag>",
      "evidence": "<quote from posting>",
      "severity": "<LOW|MEDIUM|HIGH>"
    }
  ],
  "candidate_pool_estimate": "<LARGE (1000+)|MEDIUM (100-1000)|SMALL (10-100)|TINY (<10)>",
  "recommendation": "<APPLY|CAUTION|SKIP>",
  "reasoning": "<1-2 sentence justification for the score>"
}
```

**IMPORTANT INSTRUCTIONS:**
1. Output ONLY the JSON above, no other text
2. Be decisive - make a clear verdict
3. Quote specific evidence from the posting
4. Consider industry context (finance/healthcare have stricter requirements)
5. After outputting the JSON, add [SUCCESS] on a new line

Output the JSON analysis now:$PROMPT$,
    300,   -- 5 minute timeout
    true,  -- is_terminal (end of conversation)
    true
WHERE NOT EXISTS (
    SELECT 1 FROM instructions 
    WHERE conversation_id = 9125 AND step_number = 1
);

-- Step 2: Register placeholder for IHL output
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r20_output',
    'dialogue_output',
    false,
    'Output from execution_order=20 (IHL Calculator - fake job detection score)'
)
ON CONFLICT (placeholder_name) DO UPDATE SET
    description = EXCLUDED.description;

-- Step 3: Update workflow description to reflect IHL step
UPDATE workflows 
SET workflow_description = 'Job Ingestion Pipeline: Extract skills (1121) → Calculate IHL/Fake Job Score (1124) → Map to taxonomy hierarchy (fuzzy matching)'
WHERE workflow_id = 2001;

COMMIT;

-- Verification
\echo ''
\echo '=== Updated Workflow 2001 with IHL Instruction ==='
SELECT 
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    i.instruction_id,
    i.instruction_name,
    i.is_terminal
FROM workflow_conversations wc
JOIN conversations c ON wc.conversation_id = c.conversation_id
LEFT JOIN instructions i ON c.conversation_id = i.conversation_id
WHERE wc.workflow_id = 2001
ORDER BY wc.execution_order, i.step_number;

\echo ''
\echo '✅ Workflow 2001 now includes IHL Calculator with instruction!'
\echo '   Step 10: Skills Extraction'
\echo '   Step 20: IHL/Fake Job Detection (NEW instruction added)'
\echo '   Step 30: Taxonomy Mapping'
