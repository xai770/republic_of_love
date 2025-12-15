-- Migration 017: Rename sessions to conversations and reorder columns
-- Date: 2025-10-31
-- Purpose: Rename sessions table to conversations (better reflects its purpose as
--          conversational continuity contexts). Reorder columns: conversation_id first,
--          conversation_name second. Clean up redundant text columns (canonical_name, actor_name).

BEGIN;

-- Step 1: Create the new conversations table with correct structure
CREATE TABLE conversations (
    conversation_id           INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    conversation_name         TEXT NOT NULL,
    conversation_description  TEXT,
    validated_prompt_id       INTEGER,
    actor_id                  INTEGER NOT NULL,
    context_strategy          TEXT DEFAULT 'isolated' CHECK (context_strategy IN ('isolated', 'inherit_previous', 'shared_conversation')),
    max_instruction_runs      INTEGER DEFAULT 50,
    enabled                   BOOLEAN DEFAULT true,
    created_at                TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Legacy columns for backward compatibility (can be removed later)
    canonical_name            TEXT,
    CONSTRAINT conversations_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES actors(actor_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT conversations_validated_prompt_id_fkey FOREIGN KEY (validated_prompt_id) REFERENCES validated_prompts(validated_prompt_id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- Step 2: Copy data from sessions to conversations
INSERT INTO conversations (
    conversation_id,
    conversation_name,
    conversation_description,
    validated_prompt_id,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    created_at,
    updated_at,
    canonical_name
) OVERRIDING SYSTEM VALUE
SELECT 
    session_id,
    session_name,
    session_description,
    validated_prompt_id,
    actor_id,
    context_strategy,
    max_instruction_runs,
    enabled,
    created_at,
    updated_at,
    canonical_name
FROM sessions
ORDER BY session_id;

-- Step 3: Update the sequence to match max session_id
SELECT setval('conversations_conversation_id_seq', (SELECT MAX(session_id) FROM sessions));

-- Step 4: Create indexes
CREATE INDEX idx_conversations_enabled ON conversations(enabled);
CREATE INDEX idx_conversations_actor_id ON conversations(actor_id);
CREATE INDEX idx_conversations_validated_prompt_id ON conversations(validated_prompt_id);
CREATE INDEX idx_conversations_canonical_name ON conversations(canonical_name);

-- Step 5: Update foreign key references in other tables
ALTER TABLE instruction_branches DROP CONSTRAINT fk_next_session;
ALTER TABLE instruction_branches RENAME COLUMN next_session_id TO next_conversation_id;
ALTER TABLE instruction_branches ADD CONSTRAINT fk_next_conversation 
    FOREIGN KEY (next_conversation_id) REFERENCES conversations(conversation_id) ON DELETE SET NULL;

ALTER TABLE instructions DROP CONSTRAINT instructions_session_id_fkey;
ALTER TABLE instructions RENAME COLUMN session_id TO conversation_id;
ALTER TABLE instructions ADD CONSTRAINT instructions_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

ALTER TABLE recipe_sessions DROP CONSTRAINT recipe_sessions_session_id_fkey;
ALTER TABLE recipe_sessions RENAME COLUMN session_id TO conversation_id;
ALTER TABLE recipe_sessions ADD CONSTRAINT recipe_sessions_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

ALTER TABLE session_runs DROP CONSTRAINT session_runs_session_id_fkey;
ALTER TABLE session_runs RENAME COLUMN session_id TO conversation_id;
ALTER TABLE session_runs ADD CONSTRAINT session_runs_conversation_id_fkey 
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id);

-- Step 6: Rename history table and update trigger
ALTER TABLE sessions_history RENAME TO conversations_history;
ALTER TABLE conversations_history RENAME COLUMN session_id TO conversation_id;
ALTER TABLE conversations_history RENAME COLUMN session_name TO conversation_name;
ALTER TABLE conversations_history RENAME COLUMN session_description TO conversation_description;

-- Rename the archive function
ALTER FUNCTION archive_sessions RENAME TO archive_conversations;

-- Create history trigger on new table
CREATE TRIGGER conversations_history_trigger
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION archive_conversations();

-- Step 7: Drop old sessions table
DROP TABLE sessions CASCADE;

-- Step 8: Add comments
COMMENT ON TABLE conversations IS 
'Conversational contexts for stateful interactions (569 entries).
A conversation maintains continuity between interactions (like our chat).
Each conversation has an actor and can reference a validated prompt template.
Conversations support context strategies (isolated, inherit_previous, shared_conversation).
Actors can delegate instructions to helper actors within a conversation.
Renamed from sessions 2025-10-31 for clarity.
Pattern: conversation_id (INTEGER PK) + conversation_name (TEXT).';

COMMENT ON COLUMN conversations.conversation_id IS 
'Primary key - unique identifier for this conversation';

COMMENT ON COLUMN conversations.conversation_name IS 
'Name/label for this conversation (e.g., "joke_generation", "skill_extraction")';

COMMENT ON COLUMN conversations.conversation_description IS 
'Description of what this conversation does or its purpose';

COMMENT ON COLUMN conversations.validated_prompt_id IS 
'Optional FK to validated_prompts - template prompt used in this conversation';

COMMENT ON COLUMN conversations.actor_id IS 
'FK to actors - which actor (AI model, human, script) handles this conversation';

COMMENT ON COLUMN conversations.context_strategy IS 
'How context flows: isolated (fresh), inherit_previous (sequential), shared_conversation (persistent)';

COMMENT ON COLUMN conversations.max_instruction_runs IS 
'Maximum number of instruction executions allowed in this conversation (safety limit)';

COMMENT ON COLUMN conversations.canonical_name IS 
'Legacy column - text reference to validated prompt name (use validated_prompt_id instead)';

-- Step 9: Verification
SELECT 
    'conversations' as new_table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT conversation_name) as unique_names,
    'Rename and reorder complete' as status
FROM conversations;

COMMIT;
