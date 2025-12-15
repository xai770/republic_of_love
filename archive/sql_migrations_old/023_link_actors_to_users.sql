-- Migration 023: Link actors to users
-- Date: 2025-10-31
-- Purpose: Add user_id to actors table to link human actors to user accounts
--          Add comprehensive comments to clarify actor vs user distinction

-- This migration resolves the actor/user relationship:
-- 1. actors table = execution layer (who executes workflow steps)
-- 2. users table = application layer (who owns profiles/searches)
-- 3. Some actors ARE users (e.g., job seeker responding to cover letter)
-- 4. Not all actors are users (AI models, scripts never authenticate)
-- 5. Not all users are actors (some users may never participate in workflows)

BEGIN;

-- Step 1: Add user_id column to actors table (nullable - not all actors are users)
ALTER TABLE actors ADD COLUMN user_id INTEGER;

-- Step 2: Add foreign key constraint to users table
ALTER TABLE actors 
    ADD CONSTRAINT actors_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL;

-- Step 3: Create index for lookups
CREATE INDEX idx_actors_user_id ON actors(user_id) WHERE user_id IS NOT NULL;

-- Step 4: Update comprehensive comments on actors table
COMMENT ON TABLE actors IS 'Computational units in the Turing execution engine (execution layer).
Actors are the "processors" that execute instructions in workflows - can be AI models, scripts, or humans.
Key to Turing completeness: heterogeneous computation mixing neural (AI), symbolic (scripts), and human judgment.

Actor Types:
- human (execution_type=human_input): Human actors who execute workflow steps
- ai_model (execution_type=ollama_api): AI/LLM models that process data
- script (execution_type=python_script/bash_script): Automated scripts
- machine_actor (execution_type=http_api): External API services

Actor vs User Distinction:
- actors table = EXECUTION LAYER: "Who executes this workflow step?"
- users table = APPLICATION LAYER: "Who owns this profile/job search?"
- Some actors ARE users (user_id FK): Job seekers responding to reports, providing feedback
- Not all actors are users: AI models and scripts will never authenticate
- Not all users are actors: Some platform users may never participate in workflow execution

Example: Job seeker Jane (user_id=42) receives a cover letter. When she replies, she acts as 
an actor (actor_id=123, user_id=42). The AI model that generated the cover letter (actor_id=5) 
has no user_id because it''s not an authenticated platform user.

Column order standardized 2025-10-31 (migration 015).
Pattern: actor_id (INTEGER PK) + actor_name (TEXT UNIQUE).
User linking added 2025-10-31 (migration 023).';

COMMENT ON COLUMN actors.user_id IS 'Foreign key to users table. Links this actor to a platform user account. NULL for non-human actors (AI models, scripts) and human actors not yet linked to user accounts. When a user participates in workflow execution (e.g., responding to job search reports), their actor record references their user account.';

-- Step 5: Update comprehensive comments on users table
COMMENT ON TABLE users IS 'Platform users (application layer) - authenticated accounts for talent.yoga.
Supports multiple roles via flags: job seekers, recruiters, and admins.

User vs Actor Distinction:
- users table = APPLICATION LAYER: Authentication, authorization, profile ownership
- actors table = EXECUTION LAYER: Workflow execution, instruction processing
- Users become actors when they participate in workflows (linked via actors.user_id)
- Users own data (profiles, saved postings, workflow_runs.user_id)
- Actors execute steps (instructions, human_tasks, conversations)

Example: Job seeker Jane has:
- User record (user_id=42): email, password, preferences, profile ownership
- Actor record (actor_id=123, user_id=42): executes workflow steps when she provides input

Not all users need actor records (browse-only users), and not all actors are users (AI/scripts).';

COMMENT ON COLUMN users.user_id IS 'Unique identifier for this user account. Referenced by profiles, workflow_runs (ownership), and actors.user_id (execution identity).';
COMMENT ON COLUMN users.email IS 'Unique email address for authentication and communication';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hash of user password for secure authentication';
COMMENT ON COLUMN users.full_name IS 'User''s full name for display and personalization';
COMMENT ON COLUMN users.status IS 'Account status: active, suspended, or deleted';
COMMENT ON COLUMN users.is_job_seeker IS 'Flag: true if user is searching for jobs (may have profile)';
COMMENT ON COLUMN users.is_recruiter IS 'Flag: true if user is hiring/posting jobs';
COMMENT ON COLUMN users.is_admin IS 'Flag: true if user has administrative privileges';
COMMENT ON COLUMN users.organization_id IS 'Foreign key to organizations table (for recruiters/admins)';
COMMENT ON COLUMN users.created_at IS 'Timestamp when user account was created';
COMMENT ON COLUMN users.last_login_at IS 'Timestamp of most recent login';
COMMENT ON COLUMN users.email_verified_at IS 'Timestamp when email was verified (NULL if unverified)';
COMMENT ON COLUMN users.preferences IS 'JSONB object with user preferences (notifications, display settings, etc.)';

COMMIT;

-- Verification queries (run after migration)
-- SELECT actor_id, actor_name, actor_type, user_id FROM actors WHERE actor_type = 'human';
-- \d actors
-- SELECT obj_description('actors'::regclass, 'pg_class');
