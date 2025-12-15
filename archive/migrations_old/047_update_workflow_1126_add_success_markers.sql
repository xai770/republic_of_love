-- Migration 047: Add [SUCCESS] markers to Workflow 1126 prompts
-- Issue: LLMs don't output branch markers unless explicitly instructed
-- Solution: Update prompts to request [SUCCESS]/[FAIL] markers after output
-- Date: 2025-11-04
-- Tested with: llm_chat.py qwen2.5:7b (confirmed it works!)

BEGIN;

-- Update extraction instruction to output [SUCCESS] marker
UPDATE instructions
SET prompt_template = 'You are an expert at extracting structured career data from profile documents.

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

Output the JSON now, then on a new line output [SUCCESS]:'
WHERE instruction_id = 3362;

-- Update validation instruction to output [PASS]/[FAIL] markers
UPDATE instructions
SET prompt_template = prompt_template || '

After your validation report, output:
- [PASS] if all required fields are present and valid
- [FAIL] if any critical errors found'
WHERE instruction_id = 3363;

-- Update import instruction to output [SUCCESS]/[FAIL] markers
UPDATE instructions
SET prompt_template = prompt_template || '

After the import operation, output:
- [SUCCESS] if profile was imported successfully
- [FAIL] if import failed'
WHERE instruction_id = 3364;

-- Verify updates
SELECT 
    instruction_id,
    instruction_name,
    CASE 
        WHEN prompt_template LIKE '%[SUCCESS]%' THEN '✅ Has SUCCESS marker'
        WHEN prompt_template LIKE '%[PASS]%' THEN '✅ Has PASS marker'
        WHEN prompt_template LIKE '%[FAIL]%' THEN '✅ Has FAIL marker'
        ELSE '❌ No marker'
    END as marker_status,
    LENGTH(prompt_template) as prompt_length
FROM instructions
WHERE conversation_id IN (
    SELECT conversation_id 
    FROM workflow_conversations 
    WHERE workflow_id = 1126
)
ORDER BY instruction_id;

COMMIT;

-- Migration complete!
-- Next: Test with: python3 runners/workflow_1126_runner.py --file "docs/Gershon Pollatschek Projects.md" --dry-run
