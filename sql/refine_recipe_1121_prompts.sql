-- Refine Recipe 1121 prompts for cleaner output
-- Fix Steps 2, 4, and 5 to work better with gopher JSON output

BEGIN;

-- Instruction 2: Simpler skill extraction (less verbose)
UPDATE instructions SET
  prompt_template = $$You are a skill extraction expert. Read this job description and extract key skills.

{{PREVIOUS_RESPONSE}}

List ONLY the skill names, one per line. Be concise - use 2-4 words maximum per skill.

Examples:
Financial Advisory
Customer Service
Python Programming
Project Management
Communication

Extract the skills now:$$,
  updated_at = NOW()
WHERE instruction_id = 91212;

-- Instruction 4: Better JSON parsing for hierarchy
UPDATE instructions SET
  prompt_template = $$You received this JSON hierarchy from the skill gopher:

{{PREVIOUS_RESPONSE}}

Extract ONLY the paths from the "hierarchy" array and output them one per line.
Keep the full paths including ROOT/.

Example input JSON:
{"hierarchy": ["ROOT/TECH/PYTHON", "ROOT/SOFT/COMMUNICATION"], "stats": {...}}

Example output:
ROOT/TECH/PYTHON
ROOT/SOFT/COMMUNICATION

Now extract the paths:$$,
  updated_at = NOW()
WHERE instruction_id = 91214;

-- Instruction 5: Extract leaf skills from paths
UPDATE instructions SET
  prompt_template = $$These are skill hierarchy paths:

{{PREVIOUS_RESPONSE}}

Extract the final skill name from each path (the part after the last slash).
Output as a JSON array of lowercase strings.

Example input:
ROOT/TECHNICAL/PYTHON
ROOT/SOFT_SKILLS/COMMUNICATION
ROOT/DOMAIN/FINANCE

Example output:
["python", "communication", "finance"]

Now extract the skills as a JSON array:$$,
  updated_at = NOW()
WHERE instruction_id = 91215;

COMMIT;

-- Verify changes
SELECT 
  instruction_id,
  step_number,
  step_description,
  LEFT(prompt_template, 100) as prompt_preview
FROM instructions
WHERE session_id = 9121
ORDER BY step_number;
