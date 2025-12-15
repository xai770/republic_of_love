#!/bin/bash
# Fix Recipe 1114 - Session 7 should use session_1_output when grading passes

export PGPASSWORD='base_yoga_secure_2025'

psql -h localhost -U base_admin -d base_yoga << 'SQL'

-- Update Session 7 to use session_1_output (the original extraction)
-- This makes sense: if grading passed, format the original extraction
UPDATE instructions
SET prompt_template = 'Clean this job posting summary by following these rules EXACTLY:

INPUT:
{session_1_output}

RULES:
1. Remove ALL markdown code block markers (```, ```json, etc.)
2. Keep ONLY these section headers in this order:
   - **Role:**
   - **Company:**
   - **Location:**
   - **Job ID:**
   - **Key Responsibilities:**
   - **Requirements:**
   - **Details:**

3. Remove any "Type:", "Skills and Experience:", "Benefits:" sections - merge content into appropriate sections above
4. Format consistently:
   - Use "- " for all bullet points
   - Keep sections concise
   - No nested formatting
   - No extra blank lines between sections

5. Output PLAIN TEXT ONLY - no markdown wrappers

Return ONLY the cleaned version, nothing else.'
WHERE session_id = (SELECT session_id FROM sessions WHERE session_name = 'Format Standardization')
  AND step_number = 1;

SELECT 'Updated Session 7 template to use session_1_output' as status;

SQL
