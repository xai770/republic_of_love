-- Migration 051: Update Workflow 1126 to use profile_importer actor
-- Issue: Import step uses taxonomy_gopher (wrong actor, no SUCCESS marker)
-- Solution: Switch to profile_importer script actor
-- Date: 2025-11-04
-- Following: Cookbook workflow design best practices

BEGIN;

-- Update import conversation to use profile_importer
UPDATE conversations
SET actor_id = (SELECT actor_id FROM actors WHERE actor_name = 'profile_importer')
WHERE conversation_name = 'w1126_import_to_database';

-- Update import instruction prompt to work with script actor
-- Script expects JSON input, outputs JSON result with [SUCCESS]/[FAIL] marker
UPDATE instructions
SET 
    prompt_template = E'Import the validated profile data into the Turing database.

EXTRACTION DATA:
{session_1_output}

VALIDATION RESULT:
{session_2_output}

Your task is to insert the profile data into the following tables:
- profiles (main profile information)
- work_history (employment records)
- languages (language proficiencies)  
- education (degrees and institutions)
- certifications (professional certifications)
- Link skills to taxonomy (for matching)

The profile_importer script will:
1. Parse the validated JSON data
2. Use corrected_data if validation made corrections
3. Insert records into all relevant tables
4. Return profile_id and statistics

Expected output format:
{
  "status": "SUCCESS|FAILED",
  "profile_id": number or null,
  "records_inserted": {
    "profiles": 1,
    "work_history": number,
    "languages": number,
    "education": number,
    "certifications": number,
    "skills": number
  },
  "message": "Profile imported successfully (profile_id=123)",
  "error": "string or null"
}

After import, output:
- [SUCCESS] if profile was imported successfully
- [FAIL] if import failed',
    
    -- Remove delegate_actor since the conversation actor itself handles import
    delegate_actor_id = NULL,
    
    -- Keep same timeout (180s should be plenty for database insert)
    timeout_seconds = 180
    
WHERE instruction_id = 3364;

-- Verify updates
SELECT 
    c.conversation_name,
    a.actor_name as conversation_actor,
    i.instruction_name,
    i.delegate_actor_id,
    da.actor_name as delegate_actor,
    i.timeout_seconds
FROM conversations c
JOIN actors a ON c.actor_id = a.actor_id
JOIN instructions i ON i.conversation_id = c.conversation_id
LEFT JOIN actors da ON i.delegate_actor_id = da.actor_id
WHERE c.conversation_name = 'w1126_import_to_database';

COMMIT;

-- Migration complete!
-- Next: Test with: python3 runners/workflow_1126_runner.py --file "docs/Gershon Pollatschek Projects.md"
-- Should see: profile_importer executing and returning profile_id with [SUCCESS] marker
