-- Migration 050: Add Conversation Tagging System
-- Purpose: Enable discovery and organization of conversations across multiple .yoga applications
-- Date: 2025-11-19
-- Author: Arden (Schema & Architecture Lead)

BEGIN;

-- Step 1: Add application scope to workflows and conversations
-- This isolates workflows/conversations by product (talent, news, write, research, contract)

ALTER TABLE workflows 
ADD COLUMN IF NOT EXISTS app_scope TEXT;

COMMENT ON COLUMN workflows.app_scope IS 
'Application scope: talent, news, write, research, contract. Isolates workflows by product.';

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS app_scope TEXT;

COMMENT ON COLUMN conversations.app_scope IS 
'Application scope: talent, news, write, research, contract. Inherited from workflow or set independently for reusable conversations.';

-- Step 2: Create conversation_tags junction table
-- Enables multi-tag assignment using application-agnostic action verbs

CREATE TABLE IF NOT EXISTS conversation_tags (
    conversation_id INT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    
    PRIMARY KEY (conversation_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_conversation_tags_tag 
ON conversation_tags(tag);

COMMENT ON TABLE conversation_tags IS 
'Tag conversations with action verbs for cross-application discovery. Tags are application-agnostic and represent what the conversation does (extract, validate, match, etc.)';

-- Step 3: Define core tag vocabulary
-- Insert into a reference table so we can document what each tag means

CREATE TABLE IF NOT EXISTS conversation_tag_definitions (
    tag TEXT PRIMARY KEY,
    category TEXT NOT NULL,  -- 'data', 'analysis', 'generation', 'reasoning', 'quality'
    description TEXT NOT NULL,
    examples TEXT,  -- JSON array of example use cases
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE conversation_tag_definitions IS 
'Reference table defining valid conversation tags. Documents what each tag means and provides examples.';

-- Insert core tag definitions
INSERT INTO conversation_tag_definitions (tag, category, description, examples) VALUES

-- Data operations
('fetch', 'data', 'Retrieve data from external source (API, web, database)', 
 '["Fetch jobs from Deutsche Bank API", "Fetch news articles from RSS feeds"]'),
('extract', 'data', 'Extract structured information from unstructured content',
 '["Extract skills from job description", "Extract entities from news article", "Extract characters from novel chapter"]'),
('validate', 'data', 'Check data quality, completeness, format correctness',
 '["Validate profile JSON structure", "Validate contract provision format"]'),
('transform', 'data', 'Convert data from one format/structure to another',
 '["Transform job data to standardized schema", "Transform markdown to HTML"]'),
('save', 'data', 'Persist data to database or storage',
 '["Save extracted profile to database", "Save generated chapter to storage"]'),

-- Analysis operations
('classify', 'analysis', 'Categorize or label data into predefined classes',
 '["Classify job by industry", "Classify news topic", "Classify contract provision type"]'),
('score', 'analysis', 'Assign numerical rating or confidence score',
 '["Score job-candidate match", "Score article relevance"]'),
('rank', 'analysis', 'Order items by importance, relevance, or quality',
 '["Rank candidates by fit score", "Rank news articles by relevance"]'),
('match', 'analysis', 'Find relationships or similarities between entities',
 '["Match candidate skills to job requirements", "Match contract provisions"]'),
('compare', 'analysis', 'Identify differences and similarities between items',
 '["Compare contract versions", "Compare job descriptions"]'),

-- Generation operations
('summarize', 'generation', 'Create concise summary of longer content',
 '["Summarize job posting", "Summarize news article", "Summarize chapter"]'),
('generate', 'generation', 'Create new content from scratch or templates',
 '["Generate cover letter", "Generate newsletter", "Generate chapter outline"]'),
('translate', 'generation', 'Convert content between languages',
 '["Translate job description to German", "Translate contract to French"]'),
('format', 'generation', 'Apply styling, structure, or presentation rules',
 '["Format profile as HTML", "Format contract as PDF"]'),
('combine', 'generation', 'Merge multiple inputs into unified output',
 '["Combine multiple skill extractions", "Combine research notes into report"]'),

-- Reasoning operations
('analyze', 'reasoning', 'Deep examination to understand patterns, causes, implications',
 '["Analyze job market trends", "Analyze character motivations", "Analyze contract risks"]'),
('recommend', 'reasoning', 'Provide actionable suggestions based on analysis',
 '["Recommend go/no-go decision", "Recommend article topics", "Recommend plot developments"]'),
('explain', 'reasoning', 'Clarify reasoning, provide justification for decisions',
 '["Explain match score", "Explain recommendation rationale"]'),
('critique', 'reasoning', 'Evaluate quality, identify weaknesses, suggest improvements',
 '["Critique chapter draft", "Critique contract provisions"]'),

-- Quality operations
('review', 'quality', 'Human or AI examination for approval/rejection',
 '["Review extracted data for accuracy", "Review generated chapter"]'),
('verify', 'quality', 'Confirm correctness against known truth or rules',
 '["Verify skill taxonomy mapping", "Verify contract clause completeness"]'),
('audit', 'quality', 'Systematic examination for compliance or errors',
 '["Audit data pipeline for hallucinations", "Audit contract for missing provisions"]'),
('detect_errors', 'quality', 'Identify mistakes, inconsistencies, quality issues',
 '["Detect hallucinated skills", "Detect plot inconsistencies", "Detect contract contradictions"]')

ON CONFLICT (tag) DO NOTHING;

-- Step 4: Backfill app_scope for existing talent.yoga workflows
-- All current workflows are for talent.yoga

UPDATE workflows 
SET app_scope = 'talent'
WHERE app_scope IS NULL;

UPDATE conversations
SET app_scope = 'talent'
WHERE app_scope IS NULL;

-- Step 5: Create helper function to tag conversations
-- Makes it easy to add tags programmatically

CREATE OR REPLACE FUNCTION tag_conversation(
    p_conversation_id INT,
    p_tags TEXT[]
)
RETURNS void AS $$
BEGIN
    INSERT INTO conversation_tags (conversation_id, tag)
    SELECT p_conversation_id, unnest(p_tags)
    ON CONFLICT (conversation_id, tag) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION tag_conversation IS 
'Helper function to tag a conversation with multiple tags at once. Usage: SELECT tag_conversation(conversation_id, ARRAY[''extract'', ''validate'']);';

-- Step 6: Create discovery views

CREATE OR REPLACE VIEW v_conversation_discovery AS
SELECT 
    c.conversation_id,
    c.conversation_name,
    c.canonical_name,
    c.app_scope,
    c.conversation_description,
    a.actor_name,
    a.actor_type,
    a.url as actor_url,
    array_agg(DISTINCT ct.tag ORDER BY ct.tag) FILTER (WHERE ct.tag IS NOT NULL) as tags,
    string_agg(DISTINCT ctd.category, ', ' ORDER BY ctd.category) as tag_categories
FROM conversations c
LEFT JOIN actors a ON c.actor_id = a.actor_id
LEFT JOIN conversation_tags ct ON c.conversation_id = ct.conversation_id
LEFT JOIN conversation_tag_definitions ctd ON ct.tag = ctd.tag
GROUP BY c.conversation_id, c.conversation_name, c.canonical_name, c.app_scope, 
         c.conversation_description, a.actor_name, a.actor_type, a.url;

COMMENT ON VIEW v_conversation_discovery IS 
'Discovery view for conversations with app_scope, tags, and actor information. Use for finding reusable conversations.';

-- Step 7: Create helper queries (as comments for documentation)

/*
-- EXAMPLE QUERIES FOR CONVERSATION DISCOVERY:

-- 1. Find all extraction conversations across ALL apps
SELECT * FROM v_conversation_discovery 
WHERE 'extract' = ANY(tags);

-- 2. Find talent.yoga matching conversations
SELECT * FROM v_conversation_discovery
WHERE app_scope = 'talent' 
  AND 'match' = ANY(tags);

-- 3. Find all conversations that do generation work
SELECT * FROM v_conversation_discovery
WHERE tags && ARRAY['generate', 'summarize', 'translate', 'format', 'combine'];

-- 4. Find conversations by tag category (e.g., all quality operations)
SELECT DISTINCT c.*
FROM v_conversation_discovery c
JOIN conversation_tags ct ON c.conversation_id = ct.conversation_id
JOIN conversation_tag_definitions ctd ON ct.tag = ctd.tag
WHERE ctd.category = 'quality';

-- 5. Find conversations for a specific app and category
SELECT * FROM v_conversation_discovery
WHERE app_scope = 'write'
  AND tag_categories LIKE '%generation%';

-- 6. List all available tags with descriptions
SELECT tag, category, description, examples
FROM conversation_tag_definitions
ORDER BY category, tag;

-- 7. Tag a conversation (multiple tags at once)
SELECT tag_conversation(11261, ARRAY['extract', 'validate', 'save']);

-- 8. See which conversations are untagged (need attention)
SELECT conversation_id, conversation_name, app_scope
FROM conversations c
WHERE NOT EXISTS (
    SELECT 1 FROM conversation_tags ct 
    WHERE ct.conversation_id = c.conversation_id
);

*/

-- Step 8: Update WORKFLOW_CREATION_COOKBOOK note
-- Add reminder to tag conversations during creation

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '================================================================================';
    RAISE NOTICE 'Migration 050 Complete: Conversation Tagging System';
    RAISE NOTICE '================================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'ADDED:';
    RAISE NOTICE '  - workflows.app_scope (talent/news/write/research/contract)';
    RAISE NOTICE '  - conversations.app_scope (inherited from workflow or set independently)';
    RAISE NOTICE '  - conversation_tags (junction table for multi-tag assignment)';
    RAISE NOTICE '  - conversation_tag_definitions (23 core tags defined)';
    RAISE NOTICE '  - tag_conversation() helper function';
    RAISE NOTICE '  - v_conversation_discovery view';
    RAISE NOTICE '';
    RAISE NOTICE 'TAG CATEGORIES:';
    RAISE NOTICE '  - data: fetch, extract, validate, transform, save';
    RAISE NOTICE '  - analysis: classify, score, rank, match, compare';
    RAISE NOTICE '  - generation: summarize, generate, translate, format, combine';
    RAISE NOTICE '  - reasoning: analyze, recommend, explain, critique';
    RAISE NOTICE '  - quality: review, verify, audit, detect_errors';
    RAISE NOTICE '';
    RAISE NOTICE 'NEXT STEPS:';
    RAISE NOTICE '  1. Review tag definitions: SELECT * FROM conversation_tag_definitions;';
    RAISE NOTICE '  2. Tag existing conversations: SELECT tag_conversation(conv_id, ARRAY[''extract'', ''validate'']);';
    RAISE NOTICE '  3. Update WORKFLOW_CREATION_COOKBOOK.md to include tagging step';
    RAISE NOTICE '  4. When creating new workflows, always set app_scope and tag conversations';
    RAISE NOTICE '';
    RAISE NOTICE 'EXAMPLE USAGE:';
    RAISE NOTICE '  -- Find all extraction conversations';
    RAISE NOTICE '  SELECT * FROM v_conversation_discovery WHERE ''extract'' = ANY(tags);';
    RAISE NOTICE '';
    RAISE NOTICE '  -- Tag a conversation';
    RAISE NOTICE '  SELECT tag_conversation(11261, ARRAY[''extract'', ''validate'']);';
    RAISE NOTICE '';
    RAISE NOTICE '================================================================================';
END $$;

COMMIT;
