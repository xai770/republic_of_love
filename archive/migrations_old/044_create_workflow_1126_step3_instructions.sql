-- ============================================================================
-- Migration 044: Create Workflow 1126 - Step 3: Instructions
-- ============================================================================
-- Purpose: Add instructions (prompts) to each conversation
-- Follows: WORKFLOW_CREATION_COOKBOOK.md Step 3
-- ============================================================================

BEGIN;

-- ============================================================================
-- Instruction 1: Extract Profile Data (Conversation 1)
-- ============================================================================

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
    'Extract Profile Data from Document',
    conversation_id,
    1,
    'Parse document and extract structured JSON with profile info, work history, skills, education',
    $PROMPT$You are an expert at extracting structured career data from profile documents.

DOCUMENT:
{document_text}

Your task: Extract ALL information into structured JSON format. Be thorough and accurate.

OUTPUT FORMAT (valid JSON only, no markdown, no code blocks):
{
  "profile": {
    "full_name": "string (REQUIRED)",
    "email": "string or null",
    "phone": "string or null", 
    "location": "string or null",
    "current_title": "string or null (most recent job title)",
    "linkedin_url": "string or null",
    "years_of_experience": number (calculate from dates, e.g., 2025 - 1996 = 29),
    "experience_level": "entry|junior|mid|senior|lead|executive (infer from roles)",
    "profile_summary": "string or null (2-3 sentence summary)"
  },
  "work_history": [
    {
      "company_name": "string (REQUIRED)",
      "job_title": "string (REQUIRED)",
      "department": "string or null",
      "start_date": "YYYY-MM-DD (use YYYY-01-01 if only year known)",
      "end_date": "YYYY-MM-DD or null if current",
      "is_current": boolean,
      "location": "string or null",
      "job_description": "string (2-4 sentences)",
      "achievements": ["array of key achievements"],
      "technologies_used": ["array of tools, technologies, methodologies"]
    }
  ],
  "skills": ["array of all skills mentioned"],
  "languages": [
    {
      "language_name": "string",
      "proficiency_level": "native|fluent|professional|intermediate|basic"
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field_of_study": "string or null",
      "start_year": number or null,
      "end_year": number or null,
      "is_current": boolean
    }
  ],
  "certifications": [
    {
      "certification_name": "string",
      "issuing_organization": "string or null",
      "issue_date": "YYYY-MM-DD or null",
      "expiry_date": "YYYY-MM-DD or null"
    }
  ]
}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no code blocks
2. If information missing, use null (not empty strings)
3. Dates always YYYY-MM-DD format
4. Work history ordered by start_date DESC (most recent first)
5. is_current = true if end_date is null
6. Experience level: executive (C-level/VP/Director 15+ years), lead (Senior+Team Lead 10+ years), senior (10+ years), mid (5-10), junior (2-5), entry (<2)
7. Extract ALL work history entries, not just recent ones
8. For technologies_used: include programming languages, tools, frameworks, methodologies, platforms

Output the JSON now:$PROMPT$,
    300,
    false,
    true
FROM conversations
WHERE canonical_name = 'w1126_c1_extract';

-- ============================================================================
-- Instruction 2: Validate Extracted Data (Conversation 2)
-- ============================================================================

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
    'Validate Extracted Profile Data',
    conversation_id,
    1,
    'Review extracted data for completeness, accuracy, and quality. Provide corrections if needed.',
    $PROMPT$You are a data quality validator. Review the extracted profile data.

EXTRACTED DATA:
{session_r1_output}

VALIDATION CHECKLIST:
1. ✅ Required fields present: full_name, work_history with company_name + job_title + start_date
2. ✅ Date formats valid: YYYY-MM-DD, start_date < end_date
3. ✅ Boolean fields correct: is_current matches end_date (null = true)
4. ✅ Experience level reasonable: Years match level (executive needs 15+ years)
5. ✅ Work history ordered: Most recent first (start_date DESC)
6. ✅ Arrays non-empty: achievements, technologies_used have content
7. ✅ No placeholder data: No "N/A", "Not specified", "Unknown"
8. ✅ Skills extracted: skills array has reasonable content (10+ items expected)

OUTPUT FORMAT (valid JSON only, no markdown):
{
  "validation_status": "PASS|FAIL|WARNING",
  "issues": [
    {
      "severity": "ERROR|WARNING",
      "field": "string (e.g., 'profile.full_name' or 'work_history[0].start_date')",
      "issue": "string (what's wrong)",
      "suggestion": "string (how to fix)"
    }
  ],
  "corrected_data": {
    "work_history": [
      {
        "company_name": "Corrected value if needed"
      }
    ]
  },
  "summary": "string (1-2 sentence validation summary)"
}

RULES:
- If PASS, corrected_data should be empty {}
- ERROR = cannot import (missing required fields, invalid dates)
- WARNING = can import but has quality issues
- For corrections, provide ONLY the fixed fields in same structure as input
- If dates are wrong, fix them in corrected_data
- If experience_level doesn't match years, correct it

Output the validation result now:$PROMPT$,
    120,
    false,
    true
FROM conversations
WHERE canonical_name = 'w1126_c2_validate';

-- ============================================================================
-- Instruction 3: Import to Database (Conversation 3)
-- ============================================================================

INSERT INTO instructions (
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    delegate_actor_id,
    enabled
) 
SELECT
    'Import Profile to Database',
    c.conversation_id,
    1,
    'Merge validated data and insert into database tables. Return profile_id.',
    $PROMPT$You are a database import script. Execute the following task:

ORIGINAL_DATA:
{session_r1_output}

VALIDATION_RESULT:
{session_r2_output}

TASK: 
1. Parse both JSON inputs
2. If validation has corrected_data, merge corrections into original_data
3. Insert into database tables:
   - profiles (basic info) → Returns profile_id
   - profile_work_history (jobs/projects)
   - profile_languages (if present)
   - profile_education (if present)
   - profile_certifications (if present)

Expected output format (JSON):
{
  "status": "SUCCESS|FAILED",
  "profile_id": number or null,
  "records_inserted": {
    "profiles": 1,
    "work_history": number,
    "languages": number,
    "education": number,
    "certifications": number
  },
  "error": "string or null"
}

If validation_status was FAIL, return status=FAILED with error message.
If validation_status was PASS or WARNING, proceed with import.$PROMPT$,
    60,
    false,
    a.actor_id,
    true
FROM conversations c
JOIN actors a ON a.actor_name = 'taxonomy_gopher'
WHERE c.canonical_name = 'w1126_c3_import';

-- ============================================================================
-- Instruction 4: Generate Error Report (Conversation 4)
-- ============================================================================

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
    'Generate Error Report',
    conversation_id,
    1,
    'Create human-readable error report for failed extraction/validation/import',
    $PROMPT$Generate a clear error report for the failed profile import.

CONTEXT:
- Extraction output: {session_r1_output}
- Validation output: {session_r2_output}
- Import output: {session_r3_output}

Create a helpful error report in this format:

# Profile Import Failed

## What Happened
[Brief summary of where the failure occurred: extraction, validation, or import]

## Issues Identified
[List each issue with severity level]

1. **[ERROR/WARNING]** Field: `profile.full_name` - Issue description
2. **[ERROR/WARNING]** Field: `work_history[0].start_date` - Issue description

## Recommendations
[What needs to be fixed in the source document]

- Add missing required fields
- Correct date formats
- Clarify ambiguous information

## Technical Details
[Any technical error messages for debugging]

Keep it clear and actionable for a human to fix the source document.$PROMPT$,
    60,
    true,
    true
FROM conversations
WHERE canonical_name = 'w1126_c4_error';

COMMIT;

-- ============================================================================
-- Verification Step 3
-- ============================================================================
SELECT 
    c.conversation_name,
    c.canonical_name,
    i.instruction_id,
    i.step_number,
    i.instruction_name,
    i.timeout_seconds,
    i.is_terminal,
    COALESCE(da.actor_name, a.actor_name) as actor_name,
    LENGTH(i.prompt_template) as prompt_length
FROM conversations c
JOIN instructions i ON c.conversation_id = i.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN actors da ON i.delegate_actor_id = da.actor_id
WHERE c.canonical_name LIKE 'w1126_%'
ORDER BY c.conversation_id, i.step_number;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ Step 3 Complete: 4 instructions created (one per conversation)';
END $$;
