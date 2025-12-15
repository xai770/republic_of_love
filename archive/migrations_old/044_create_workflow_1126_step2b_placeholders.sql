-- ============================================================================
-- Migration 044: Create Workflow 1126 - Step 2b: Register Placeholders
-- ============================================================================
-- Purpose: Register placeholder variables used in Workflow 1126 instructions
-- IMPORTANT: This step should happen BEFORE creating instructions (step 3)
-- ============================================================================

BEGIN;

-- ============================================================================
-- Workflow 1126 Placeholders
-- ============================================================================

-- Placeholder 1: document_text (initial input)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'document_text',
    'test_case_data',
    true,
    'Profile document text input for Workflow 1126 (markdown/text format)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Placeholder 2: session_r1_output (Extract conversation output)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r1_output',
    'dialogue_output',
    false,
    'Output from conversation execution_order=1 (Extract Profile Data)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Placeholder 3: session_r2_output (Validate conversation output)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r2_output',
    'dialogue_output',
    false,
    'Output from conversation execution_order=2 (Validate Profile Data)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Placeholder 4: session_r3_output (Import conversation output)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r3_output',
    'dialogue_output',
    false,
    'Output from conversation execution_order=3 (Import to Database)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

-- Placeholder 5: session_r4_output (Error conversation output)
INSERT INTO placeholder_definitions (
    placeholder_name,
    source_type,
    is_required,
    description
)
VALUES (
    'session_r4_output',
    'dialogue_output',
    false,
    'Output from conversation execution_order=4 (Error Handling)'
)
ON CONFLICT (placeholder_name) DO NOTHING;

COMMIT;

-- ============================================================================
-- Verification Step 2b
-- ============================================================================
SELECT 
    placeholder_id,
    placeholder_name,
    source_type,
    is_required,
    description
FROM placeholder_definitions
WHERE placeholder_name IN (
    'document_text',
    'session_r1_output',
    'session_r2_output',
    'session_r3_output',
    'session_r4_output'
)
ORDER BY placeholder_name;

-- Success message
DO $$ BEGIN
    RAISE NOTICE '✅ Step 2b Complete: 5 placeholders registered for Workflow 1126';
END $$;
