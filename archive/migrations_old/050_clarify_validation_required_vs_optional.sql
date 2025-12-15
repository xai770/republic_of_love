-- Migration 050: Clarify REQUIRED vs OPTIONAL fields in validation
-- Issue: Validation treats optional fields (email, phone) as critical, outputs [WARNING]
-- Solution: Update prompt to clearly define REQUIRED fields only, treat rest as optional
-- Date: 2025-11-04

BEGIN;

UPDATE instructions
SET prompt_template = E'You are a data quality validator. Review the extracted profile data.

EXTRACTED DATA:
{session_1_output}

VALIDATION CHECKLIST:
1. ✅ REQUIRED FIELDS (must have for [PASS]):
   - profile.full_name (cannot be null or empty)
   - work_history array (must have at least 1 entry)
   - work_history[].company_name (cannot be null)
   - work_history[].job_title (cannot be null)
   - work_history[].start_date (cannot be null)

2. ✅ OPTIONAL FIELDS (warnings only, do not cause [FAIL]):
   - profile.email, phone, linkedin_url, location
   - education, certifications, languages arrays

3. ✅ DATA QUALITY CHECKS:
   - Date formats valid: YYYY-MM-DD, start_date < end_date (if both present)
   - Boolean fields correct: is_current matches end_date (null = true)
   - Experience level reasonable: Years roughly match level
   - Work history ordered: Most recent first (start_date DESC)
   - No placeholder data: No "N/A", "Not specified", "Unknown"

OUTPUT FORMAT (valid JSON only, no markdown):
{
  "validation_status": "PASS|FAIL",
  "issues": [
    {
      "severity": "ERROR|WARNING",
      "field": "string (e.g., \'profile.full_name\' or \'work_history[0].start_date\')",
      "issue": "string (what\'s wrong)",
      "suggestion": "string (how to fix)"
    }
  ],
  "corrected_data": {
    "comment": "Include ONLY fields that need correction, in same structure as input"
  },
  "summary": "string (1-2 sentence validation summary)"
}

CRITICAL RULES:
- Output [PASS] if ALL REQUIRED fields are present and valid (WARNINGs for optional fields are OK)
- Output [FAIL] ONLY if REQUIRED fields are missing/invalid or dates are malformed
- ERROR severity = blocks import (missing required fields, invalid dates)
- WARNING severity = import OK but quality could be better (missing optional fields)
- If PASS, corrected_data should be empty {}
- For corrections, provide ONLY the fixed fields in same structure as input

Output the validation result now:

After your validation report, output:
- [PASS] if all required fields are present (WARNING status is acceptable for import)
- [FAIL] if any critical errors found (validation_status = FAIL)'
WHERE instruction_id = 3363;

-- Verify update
SELECT 
    instruction_id,
    instruction_name,
    CASE 
        WHEN prompt_template LIKE '%REQUIRED FIELDS (must have for [PASS])%' THEN '✅ Updated with clear REQUIRED/OPTIONAL'
        ELSE '❌ Not updated'
    END as status,
    LENGTH(prompt_template) as prompt_length
FROM instructions
WHERE instruction_id = 3363;

COMMIT;
