-- ============================================================================
-- Migration 044: Create Workflow 1126 - Profile Document Import
-- ============================================================================
-- Purpose: Extract structured profile data from documents using LLM extraction
--          with validation and database import
-- Author: Arden
-- Date: 2025-11-04
--
-- Architecture:
--   Conversation 1: Extract profile data (qwen2.5:7b)
--   Conversation 2: Validate extracted data (gemma2:latest)  
--   Conversation 3: Import to database (taxonomy_gopher script)
--   Conversation 4: Error handling (qwen2.5:7b)
--
-- Output: profile_id (ready for Workflow 1122 skill extraction)
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Create Workflow 1126
-- ============================================================================

INSERT INTO workflows (
    workflow_id,
    workflow_name,
    workflow_description,
    max_total_session_runs,
    enabled
) VALUES (
    1126,
    'Profile Document Import',
    'LLM-based profile extraction: Parse documents → Extract structured data → Validate with second model → Import to profiles/work_history. Output: profile_id for skill extraction.',
    100,
    true
) ON CONFLICT (workflow_id) DO UPDATE SET
    workflow_name = EXCLUDED.workflow_name,
    workflow_description = EXCLUDED.workflow_description,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- STEP 2: Create Conversations with Canonical Names
-- ============================================================================

-- Conversation 1: Extract Profile Data (Qwen2.5:7b)
DO $$
DECLARE
    v_conv_id_extract INTEGER;
    v_conv_id_validate INTEGER;
    v_conv_id_import INTEGER;
    v_conv_id_error INTEGER;
    v_actor_qwen INTEGER;
    v_actor_gemma INTEGER;
    v_actor_gopher INTEGER;
BEGIN
    -- Get actor IDs
    SELECT actor_id INTO v_actor_qwen FROM actors WHERE actor_name = 'qwen2.5:7b' LIMIT 1;
    SELECT actor_id INTO v_actor_gemma FROM actors WHERE actor_name = 'gemma2:latest' LIMIT 1;
    SELECT actor_id INTO v_actor_gopher FROM actors WHERE actor_name = 'taxonomy_gopher' LIMIT 1;

    -- Create or update Conversation 1: Extract
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w1126_extract_profile_data',
        'w1126_c1_extract',
        'Parse document and extract structured profile data (work history, education, skills, languages) into JSON format',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        conversation_description = EXCLUDED.conversation_description,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_id_extract;

    -- Create or update Conversation 2: Validate
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w1126_validate_profile_data',
        'w1126_c2_validate',
        'Independent validation of extracted profile data. Check required fields, date formats, data quality. Provide corrections if needed.',
        v_actor_gemma,
        'single_actor',
        'isolated',
        true
    )
    ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        conversation_description = EXCLUDED.conversation_description,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_id_validate;

    -- Create or update Conversation 3: Import
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w1126_import_to_database',
        'w1126_c3_import',
        'Merge validated data and insert into profiles, profile_work_history, profile_languages, profile_education tables. Returns profile_id.',
        v_actor_gopher,
        'single_actor',
        'isolated',
        true
    )
    ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        conversation_description = EXCLUDED.conversation_description,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_id_import;

    -- Create or update Conversation 4: Error
    INSERT INTO conversations (
        conversation_name,
        canonical_name,
        conversation_description,
        actor_id,
        conversation_type,
        context_strategy,
        enabled
    ) VALUES (
        'w1126_generate_error_report',
        'w1126_c4_error',
        'Generate human-readable error report when extraction/validation/import fails',
        v_actor_qwen,
        'single_actor',
        'isolated',
        true
    )
    ON CONFLICT (canonical_name) DO UPDATE SET
        conversation_name = EXCLUDED.conversation_name,
        conversation_description = EXCLUDED.conversation_description,
        enabled = EXCLUDED.enabled
    RETURNING conversation_id INTO v_conv_id_error;

    -- Link conversations to workflow
    DELETE FROM workflow_conversations WHERE workflow_id = 1126;
    
    INSERT INTO workflow_conversations (workflow_id, conversation_id, execution_order)
    VALUES 
        (1126, v_conv_id_extract, 1),
        (1126, v_conv_id_validate, 2),
        (1126, v_conv_id_import, 3),
        (1126, v_conv_id_error, 4);
        
    RAISE NOTICE 'Created conversations: extract=%, validate=%, import=%, error=%', 
        v_conv_id_extract, v_conv_id_validate, v_conv_id_import, v_conv_id_error;
END $$;

-- ============================================================================
-- STEP 3: Create Instructions
-- ============================================================================

-- Instruction 1.1: Extract Profile Data
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
1. Output ONLY valid JSON - no markdown, no explanations
2. If information missing, use null (not empty strings)
3. Dates always YYYY-MM-DD format
4. Work history ordered by start_date DESC (most recent first)
5. is_current = true if end_date is null
6. Experience level: executive (C-level/VP/Director), lead (Senior+Team Lead), senior (10+ years), mid (5-10), junior (2-5), entry (<2)
7. Extract ALL work history entries, not just recent ones

Output the JSON now:$PROMPT$,
    300,
    false,
    true
) ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- Instruction 2.1: Validate Extracted Data
INSERT INTO instructions (
    instruction_id,
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    enabled
) VALUES (
    112602,
    'Validate Extracted Profile Data',
    11262,
    1,
    'Review extracted data for completeness, accuracy, and quality. Provide corrections if needed.',
    $PROMPT$You are a data quality validator. Review the extracted profile data.

EXTRACTED DATA:
{session_r1_output}

VALIDATION CHECKLIST:
1. Required fields present: full_name, work_history with company_name + job_title + start_date
2. Date formats valid: YYYY-MM-DD, start_date < end_date
3. Boolean fields correct: is_current matches end_date (null = true)
4. Experience level reasonable: Years match level (executive needs 15+ years)
5. Work history ordered: Most recent first (start_date DESC)
6. Arrays non-empty: achievements, technologies_used have content
7. No placeholder data: No "N/A", "Not specified", "Unknown"
8. Skills extracted: skills array has reasonable content (10+ items)

OUTPUT FORMAT (valid JSON only, no markdown):
{
  "validation_status": "PASS|FAIL|WARNING",
  "issues": [
    {
      "severity": "ERROR|WARNING",
      "field": "string (e.g., 'profile.full_name')",
      "issue": "string (what's wrong)",
      "suggestion": "string (how to fix)"
    }
  ],
  "corrected_data": {
    // Only include fields that need correction
    // Use same structure as input
  },
  "summary": "string (1-2 sentence validation summary)"
}

RULES:
- If PASS, corrected_data should be empty {}
- ERROR = cannot import (missing required fields, invalid dates)
- WARNING = can import but has quality issues
- For corrections, provide ONLY the fixed fields

Output the validation result:$PROMPT$,
    120,
    false,
    true
) ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- Instruction 3.1: Import to Database
INSERT INTO instructions (
    instruction_id,
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
    112603,
    'Import Profile to Database',
    11263,
    1,
    'Merge validated data and insert into database tables. Return profile_id.',
    $PROMPT$ORIGINAL_DATA:
{session_r1_output}

VALIDATION_RESULT:
{session_r2_output}

TASK: Merge data (apply corrections from validation) and insert into database.

Tables to populate:
1. profiles (basic info) → Returns profile_id
2. profile_work_history (jobs/projects)
3. profile_languages (if present)
4. profile_education (if present)
5. profile_certifications (if present)

Output format:
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
}$PROMPT$,
    60,
    false,
    actor_id,
    true
FROM actors WHERE actor_name = 'taxonomy_gopher' LIMIT 1
ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- Instruction 4.1: Generate Error Report
INSERT INTO instructions (
    instruction_id,
    instruction_name,
    conversation_id,
    step_number,
    step_description,
    prompt_template,
    timeout_seconds,
    is_terminal,
    enabled
) VALUES (
    112604,
    'Generate Error Report',
    11264,
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
[Brief summary of the failure]

## Issues Identified
[List each issue with severity and field]

## Recommendations
[What needs to be fixed in the source document]

## Technical Details
[Any technical error messages]

Keep it clear and actionable for a human to fix the source document.$PROMPT$,
    60,
    true,
    true
) ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    is_terminal = EXCLUDED.is_terminal,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- STEP 5: Create Instruction Steps (Branching Logic)
-- ============================================================================

-- Step 1.1 → 2.1: Extraction successful, go to validation
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126001,
    'Extraction successful - validate data',
    112601,
    '[SUCCESS]',
    11262,
    10,
    'If extraction produced valid JSON with required fields, proceed to validation',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    next_conversation_id = EXCLUDED.next_conversation_id,
    enabled = EXCLUDED.enabled;

-- Step 1.1 → 4.1: Extraction failed, go to error handling
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126002,
    'Extraction failed - generate error report',
    112601,
    '[FAIL]',
    11264,
    5,
    'If extraction failed or produced invalid JSON, generate error report',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    next_conversation_id = EXCLUDED.next_conversation_id,
    enabled = EXCLUDED.enabled;

-- Step 2.1 → 3.1: Validation passed or has corrections, go to import
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126003,
    'Validation passed - import to database',
    112602,
    '[PASS]',
    11263,
    10,
    'If validation status is PASS or WARNING (with corrections), proceed to database import',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    next_conversation_id = EXCLUDED.next_conversation_id,
    enabled = EXCLUDED.enabled;

-- Step 2.1 → 4.1: Validation failed without recovery, go to error handling
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126004,
    'Validation failed - cannot recover',
    112602,
    '[FAIL]',
    11264,
    5,
    'If validation found unrecoverable errors (missing required fields), generate error report',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    next_conversation_id = EXCLUDED.next_conversation_id,
    enabled = EXCLUDED.enabled;

-- Step 3.1 → TERMINAL: Import successful, workflow complete
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    next_instruction_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126005,
    'Import successful - workflow complete',
    112603,
    '[SUCCESS]',
    NULL,
    NULL,
    10,
    'Database import successful. profile_id available for Workflow 1122 (skill extraction)',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    enabled = EXCLUDED.enabled;

-- Step 3.1 → 4.1: Import failed, go to error handling
INSERT INTO instruction_steps (
    instruction_step_id,
    instruction_step_name,
    instruction_id,
    branch_condition,
    next_conversation_id,
    branch_priority,
    branch_description,
    enabled
) VALUES (
    1126006,
    'Import failed - database error',
    112603,
    '[FAIL]',
    11264,
    5,
    'Database import failed (constraint violation, connection error, etc.)',
    true
) ON CONFLICT (instruction_step_id) DO UPDATE SET
    branch_condition = EXCLUDED.branch_condition,
    next_conversation_id = EXCLUDED.next_conversation_id,
    enabled = EXCLUDED.enabled;

-- ============================================================================
-- STEP 6: Comments
-- ============================================================================

COMMENT ON COLUMN workflows.workflow_id IS 'Workflow 1126: Profile Document Import - LLM extraction with validation';

COMMIT;

-- ============================================================================
-- Verification
-- ============================================================================

-- Check workflow and conversations
SELECT 
    w.workflow_id,
    w.workflow_name,
    w.workflow_description,
    wc.execution_order,
    c.conversation_id,
    c.conversation_name,
    a.actor_name
FROM workflows w
JOIN workflow_conversations wc ON w.workflow_id = wc.workflow_id
JOIN conversations c ON wc.conversation_id = c.conversation_id
JOIN actors a ON c.actor_id = a.actor_id
WHERE w.workflow_id = 1126
ORDER BY wc.execution_order;

-- Check instructions
SELECT 
    c.conversation_name,
    i.instruction_id,
    i.step_number,
    i.instruction_name,
    i.timeout_seconds,
    i.is_terminal,
    da.actor_name as delegate_actor
FROM conversations c
JOIN instructions i ON c.conversation_id = i.conversation_id
LEFT JOIN actors da ON i.delegate_actor_id = da.actor_id
WHERE c.conversation_id BETWEEN 11261 AND 11264
ORDER BY c.conversation_id, i.step_number;

-- Check instruction steps (branching)
SELECT 
    ist.instruction_step_id,
    ist.instruction_step_name,
    i.instruction_name as from_instruction,
    ist.branch_condition,
    c.conversation_name as next_conversation,
    ist.branch_priority
FROM instruction_steps ist
JOIN instructions i ON ist.instruction_id = i.instruction_id
LEFT JOIN conversations c ON ist.next_conversation_id = c.conversation_id
WHERE ist.instruction_step_id BETWEEN 1126001 AND 1126006
ORDER BY ist.instruction_step_id;
SELECT
    1126001,
    1126,
    1,
    'Extract Profile Data',
    $PROMPT$You are an expert at extracting structured career data from profile documents.

DOCUMENT:
{document_text}

Your task: Extract ALL information into structured JSON format. Be thorough and accurate.

OUTPUT FORMAT (valid JSON only, no markdown):
{{
  "profile": {{
    "full_name": "string (REQUIRED)",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "current_title": "string or null (most recent job title)",
    "linkedin_url": "string or null",
    "years_of_experience": number (calculate from dates, e.g., 2025 - 1996 = 29),
    "experience_level": "entry|junior|mid|senior|lead|executive (infer from roles and years)",
    "profile_summary": "string or null (2-3 sentence professional summary)"
  }},
  "work_history": [
    {{
      "company_name": "string (REQUIRED)",
      "job_title": "string (REQUIRED)",
      "department": "string or null",
      "start_date": "YYYY-MM-DD format (REQUIRED, use YYYY-01-01 if only year known)",
      "end_date": "YYYY-MM-DD or null if current",
      "is_current": boolean,
      "location": "string or null",
      "job_description": "string (2-4 sentences summarizing the role)",
      "achievements": ["string array of key achievements/responsibilities"],
      "technologies_used": ["string array of tools, technologies, methodologies"]
    }}
  ],
  "skills": [
    "string array of all skills mentioned (technical, business, soft)"
  ],
  "languages": [
    {{
      "language_name": "string",
      "proficiency_level": "native|fluent|professional|intermediate|basic"
    }}
  ],
  "education": [
    {{
      "institution": "string",
      "degree": "string",
      "field_of_study": "string or null",
      "start_year": number or null,
      "end_year": number or null,
      "is_current": boolean
    }}
  ],
  "certifications": [
    {{
      "certification_name": "string",
      "issuing_organization": "string or null",
      "issue_date": "YYYY-MM-DD or null",
      "expiry_date": "YYYY-MM-DD or null"
    }}
  ]
}}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no code blocks, no explanations
2. If information is missing, use null (not empty strings)
3. For dates: Always use YYYY-MM-DD format. If only year known, use YYYY-01-01
4. For work_history: Order by start_date DESC (most recent first)
5. For is_current: true if end_date is null or contains "present", "today", "current"
6. For experience_level: executive (C-level, VP, Director), lead (Senior+Team Lead), senior (10+ years), mid (5-10 years), junior (2-5 years), entry (<2 years)
7. For technologies_used: Include programming languages, tools, frameworks, methodologies, platforms
8. Be thorough - extract ALL work history entries, not just recent ones

BEGIN EXTRACTION:$PROMPT$,
    actor_id,
    300,  -- 5 minutes for extraction
    true
FROM actors
WHERE actor_name = 'qwen2.5:7b'
LIMIT 1
ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- Instruction 2: Validate extracted data (Gemma2:latest - different model for validation)
INSERT INTO instructions (instruction_id, workflow_id, instruction_order, instruction_name, prompt_template, delegate_actor_id, timeout_seconds, enabled)
SELECT
    1126002,
    1126,
    2,
    'Validate Profile Data',
    $PROMPT$You are a data quality validator. Review the extracted profile data for accuracy and completeness.

EXTRACTED DATA:
{r1_output}

VALIDATION CHECKLIST:
1. **Required fields present**: full_name, work_history with company_name + job_title + start_date
2. **Date formats valid**: All dates in YYYY-MM-DD format, start_date < end_date
3. **Boolean fields correct**: is_current values match end_date (null = true, else false)
4. **Experience level reasonable**: Years match experience_level (executive needs 15+ years)
5. **Work history ordered**: Most recent first (by start_date DESC)
6. **Arrays non-empty**: achievements, technologies_used have content
7. **No placeholder data**: No "N/A", "Not specified", "Unknown" values
8. **Skills extracted**: skills array has reasonable content (10+ items expected)

OUTPUT FORMAT (valid JSON only):
{{
  "validation_status": "PASS|FAIL|WARNING",
  "issues": [
    {{
      "severity": "ERROR|WARNING",
      "field": "string (e.g., 'profile.full_name' or 'work_history[0].start_date')",
      "issue": "string (description of problem)",
      "suggestion": "string (how to fix it)"
    }}
  ],
  "corrected_data": {{
    // Only include fields that need correction
    // Use same structure as input data
  }},
  "summary": "string (1-2 sentence validation summary)"
}}

RULES:
1. If validation_status = "PASS" and no issues, corrected_data should be empty {{}}
2. If issues found, provide corrected_data with ONLY the fixed fields
3. ERROR severity = data cannot be imported (missing required fields, invalid dates)
4. WARNING severity = data can be imported but has quality issues (missing optional fields, incomplete arrays)

BEGIN VALIDATION:$PROMPT$,
    actor_id,
    120,  -- 2 minutes for validation
    true
FROM actors
WHERE actor_name = 'gemma2:latest'
LIMIT 1
ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- Instruction 3: Merge and prepare for database (Synthesis)
INSERT INTO instructions (instruction_id, workflow_id, instruction_order, instruction_name, prompt_template, delegate_actor_id, timeout_seconds, enabled)
SELECT
    1126003,
    1126,
    3,
    'Merge Validated Data',
    $PROMPT$Merge the extracted data with validation corrections.

ORIGINAL EXTRACTION:
{r1_output}

VALIDATION RESULT:
{r2_output}

OUTPUT FORMAT (valid JSON only):
{{
  "final_data": {{
    // Complete merged data structure (same as extraction format)
    // Apply all corrections from validation
    // Use original data where validation found no issues
  }},
  "import_ready": boolean,
  "validation_summary": "string (what was corrected)"
}}

RULES:
1. If validation found errors, apply ALL corrections from corrected_data
2. Preserve all original data where no corrections needed
3. Set import_ready = false if validation_status was FAIL
4. Output complete data structure ready for database insertion

BEGIN MERGE:$PROMPT$,
    actor_id,
    60,  -- 1 minute for merge
    true
FROM actors
WHERE actor_name = 'qwen2.5:7b'
LIMIT 1
ON CONFLICT (instruction_id) DO UPDATE SET
    prompt_template = EXCLUDED.prompt_template,
    timeout_seconds = EXCLUDED.timeout_seconds,
    enabled = EXCLUDED.enabled;

-- =================================================================
-- STEP 3: Comments
-- =================================================================

COMMENT ON COLUMN workflows.workflow_id IS 'Workflow 1126: Profile Document Import - LLM-based extraction with validation';

-- =================================================================
-- Verification
-- =================================================================

SELECT 
    w.workflow_id,
    w.workflow_name,
    w.workflow_type,
    COUNT(i.instruction_id) as instruction_count,
    ARRAY_AGG(i.instruction_name ORDER BY i.instruction_order) as instructions
FROM workflows w
LEFT JOIN instructions i ON w.workflow_id = i.workflow_id
WHERE w.workflow_id = 1126
GROUP BY w.workflow_id, w.workflow_name, w.workflow_type;
