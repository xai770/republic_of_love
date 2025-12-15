# User System Schema Design

**Author:** Arden  
**Date:** 2025-11-30  
**Status:** ✅ Implemented (Migration 046)

---

## Fundamental Principle

> **The ONLY entry point to Turing is via interactions.**

There is no "sign up" page. No registration flow. No "create account" button.

Users come into existence when they **interact with Turing** - through a chat, 
a recommendation request, a feedback submission. The interaction creates the user, 
not the other way around.

This means:
- `app_users` table is populated as a *side effect* of `interactions`
- First interaction → user record created automatically
- No user exists without at least one interaction
- The interaction is the relationship. Everything else follows from it.

---

## Design Principles

1. **Interactions First** - Users exist because they interacted
2. **Privacy First** - No PII in core tables
3. **Anonymization by Default** - User identity separate from user data
4. **Audit Everything** - Every preference change is traceable
5. **Soft Deletes** - Users can "disappear" without breaking FK integrity

---

## Core Tables

### 1. `app_users` - Identity Stub

The thinnest possible identity record. We know they exist, not who they are.

> **Note:** Named `app_users` to avoid conflict with existing `users` table (used by actors).

```sql
CREATE TABLE app_users (
    user_id SERIAL PRIMARY KEY,
    
    -- OAuth identity (hashed, not plaintext)
    oauth_provider VARCHAR(50) NOT NULL DEFAULT 'google',
    oauth_subject_hash VARCHAR(64) NOT NULL,  -- SHA256 of Google sub claim
    
    -- System metadata only
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- For GDPR deletion requests
    deleted_at TIMESTAMPTZ,
    deletion_reason VARCHAR(100),
    
    UNIQUE(oauth_provider, oauth_subject_hash)
);

COMMENT ON TABLE app_users IS 
'Minimal identity stub. Contains NO PII. 
OAuth subject is hashed - we cannot reverse it to get email/name.
We know a user EXISTS, not WHO they are.';

COMMENT ON COLUMN app_users.oauth_subject_hash IS
'SHA256(provider + ":" + subject_id). One-way hash. 
Google cannot be asked "who is this hash" - it is irreversible.';
```

### 2. `user_profiles` - Anonymized Career Data

Skills, experience, preferences - but no names. Company associations stored as IDs only (verified separately).

```sql
CREATE TABLE user_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Anonymized career data (extracted by local LLM)
    years_experience INTEGER,
    career_level VARCHAR(50),  -- 'junior', 'mid', 'senior', 'executive'
    
    -- Skills as JSONB array (links to our skill taxonomy)
    skills JSONB DEFAULT '[]',
    -- Example: [{"skill_id": 123, "proficiency": "expert", "years": 5}]
    
    -- Work history (anonymized - industries, not companies)
    work_history JSONB DEFAULT '[]',
    -- Example: [{"industry": "banking", "role_type": "risk", "years": 3}]
    -- NOTE: Company associations stored in user_company_verifications, not here
    
    -- Education (anonymized)
    education JSONB DEFAULT '[]',
    -- Example: [{"level": "masters", "field": "finance"}]
    -- NOTE: No school names, no graduation years
    
    -- Desired next role
    target_roles JSONB DEFAULT '[]',
    -- Example: ["risk_manager", "compliance_officer"]
    
    target_locations JSONB DEFAULT '[]',
    -- Example: ["frankfurt", "munich", "remote"]
    
    target_industries JSONB DEFAULT '[]',
    -- Example: ["banking", "fintech", "consulting"]
    
    -- Salary expectations (ranges only)
    salary_min INTEGER,  -- EUR annual
    salary_max INTEGER,
    
    -- Profile versioning
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Raw profile NEVER stored - only this anonymized extract
    anonymization_model VARCHAR(100),  -- e.g., 'mistral:7b'
    anonymization_timestamp TIMESTAMPTZ
);

COMMENT ON TABLE user_profiles IS
'Anonymized career profile. Extracted from user-provided resume/CV.
The original document is NEVER stored. Only this anonymized extract exists.
Contains NO: names, company names, school names, dates, contact info.';
```

### 3. `user_preferences` - Matching Rules

What they want and don't want.

```sql
CREATE TABLE user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Preference type
    preference_type VARCHAR(50) NOT NULL,
    -- Types: 'include_skill', 'exclude_skill', 'include_company', 
    --        'exclude_company', 'include_industry', 'exclude_industry',
    --        'min_salary', 'max_commute', 'remote_only', etc.
    
    -- The preference value (flexible)
    preference_key VARCHAR(100),  -- e.g., 'skill_id', 'company_id', 'industry'
    preference_value VARCHAR(500),  -- e.g., '123', 'banking', 'true'
    
    -- Strength of preference (-1.0 to 1.0)
    -- -1.0 = hard exclude (dealbreaker)
    -- -0.5 = soft exclude (prefer not)
    --  0.0 = neutral
    -- +0.5 = soft include (nice to have)
    -- +1.0 = hard include (must have)
    weight DECIMAL(3,2) DEFAULT 0.0,
    
    -- Source of preference
    source VARCHAR(50) DEFAULT 'user_explicit',
    -- Sources: 'user_explicit', 'feedback_inferred', 'profile_inferred', 'system_default'
    
    source_interaction_id INTEGER,  -- FK to interaction that created this
    
    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Some preferences are temporary
    
    -- Audit
    created_by VARCHAR(50),  -- 'user', 'system', 'feedback_processor'
    
    UNIQUE(user_id, preference_type, preference_key)
);

COMMENT ON TABLE user_preferences IS
'User matching preferences. Both explicit (user said "no tax jobs") 
and inferred (feedback processor detected pattern).
Weight indicates strength: -1=dealbreaker, +1=must-have.';

-- Index for fast preference lookup during matching
CREATE INDEX idx_user_preferences_active ON user_preferences(user_id, is_active) 
WHERE is_active = TRUE;
```

### 4. `user_feedback` - Raw Feedback Log

What they said about our recommendations.

```sql
CREATE TABLE user_feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- What they're responding to
    report_id INTEGER,  -- FK to weekly_reports if we have that
    posting_id INTEGER REFERENCES postings(posting_id),
    
    -- The feedback itself
    feedback_type VARCHAR(50) NOT NULL,
    -- Types: 'interested', 'not_interested', 'applied', 'rejected',
    --        'already_know', 'company_preference', 'skill_mismatch',
    --        'salary_mismatch', 'location_mismatch', 'other'
    
    -- Raw feedback text (anonymized before storage)
    feedback_text TEXT,
    -- Example: "I worked at this company, didn't like the culture"
    -- Stored as: "Negative company experience" (anonymized)
    
    -- Structured feedback (extracted by local LLM)
    feedback_structured JSONB,
    -- Example: {"sentiment": "negative", "reason": "company_culture", 
    --           "company_id": 47, "actionable": true}
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    preferences_updated JSONB,  -- Which preferences were created/modified
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    anonymization_model VARCHAR(100)
);

COMMENT ON TABLE user_feedback IS
'User feedback on recommendations. Raw text is anonymized before storage.
Local LLM extracts structured preferences from feedback.
Original verbatim text is NEVER stored if it contains PII.';
```

### 5. `user_reports` - Weekly Recommendation Batches

What we sent them.

```sql
CREATE TABLE user_reports (
    report_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Report metadata
    report_type VARCHAR(50) DEFAULT 'weekly',
    report_period_start DATE,
    report_period_end DATE,
    
    -- The recommendations
    postings JSONB NOT NULL,
    -- Example: [{"posting_id": 123, "score": 0.87, "reasons": ["skill_match", "location"]}]
    
    -- Delivery
    delivered_email BOOLEAN DEFAULT FALSE,
    delivered_site BOOLEAN DEFAULT FALSE,
    delivered_at TIMESTAMPTZ,
    
    -- Engagement
    opened_at TIMESTAMPTZ,
    feedback_received INTEGER DEFAULT 0,
    
    -- Generation metadata
    matching_model VARCHAR(100),
    matching_algorithm_version VARCHAR(20),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_reports IS
'Weekly job recommendation reports sent to users.
Stores which postings were recommended and why.
Tracks delivery and engagement for algorithm improvement.';
```

### 6. `user_sessions` - Login History (Minimal)

```sql
CREATE TABLE user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE,
    
    -- Session metadata (no IP addresses, no device fingerprints)
    session_token_hash VARCHAR(64),  -- Hashed, not plaintext
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    
    -- Minimal device info (for security, not tracking)
    device_type VARCHAR(20)  -- 'desktop', 'mobile', 'tablet'
);

COMMENT ON TABLE user_sessions IS
'Minimal session tracking. No IP addresses, no detailed device info.
Just enough to manage authentication state.';
```

---

## Relationships

```
app_users (identity stub)
  │
  ├── user_profiles (anonymized career data)
  │
  ├── user_preferences (matching rules)
  │     └── ← created by feedback_processor
  │
  ├── user_feedback (responses to recommendations)
  │     └── → triggers preference updates
  │
  ├── user_reports (what we sent them)
  │     └── → user_feedback references this
  │
  ├── user_sessions (auth state)
  │
  ├── company_ratings → companies
  │     └── User can rate companies (1-5 stars)
  │
  └── user_verifications
        └── "Verify then forget" - stores only yes/no result
```

---

## What We DON'T Store

| Data | Why Not |
|------|---------|
| Email addresses | OAuth provider handles this |
| Names | Anonymized at ingestion |
| Phone numbers | Never collected |
| Company names (in profile) | Generalized to industry |
| School names | Generalized to degree level |
| Dates of employment | Only duration in years |
| IP addresses | Not needed, privacy risk |
| Device fingerprints | Not needed, tracking concern |
| Original resume | Only anonymized extract |

---

## Migration

**Applied:** `migrations/046_user_system.sql` on 2025-11-30

Created tables:
1. `app_users` - identity stub
2. `user_profiles` - anonymized career data  
3. `user_preferences` - matching rules
4. `user_feedback` - feedback log
5. `user_reports` - recommendation batches
6. `user_sessions` - minimal auth state
7. `companies` - for ratings
8. `company_ratings` - user ratings (with auto-avg trigger)
9. `user_verifications` - "verify then forget" results

---

## Open Questions

1. **How do we verify identity without seeing it?** 
   - LinkedIn verification flow?
   - Trust Google OAuth completely?

2. **What about returning users whose profile changed?**
   - Detect resume edits?
   - Version profiles?

3. **How long do we keep feedback?**
   - Forever (for preference learning)?
   - GDPR retention limits?

4. **Should preferences decay over time?**
   - "No tax jobs" from 2 years ago - still valid?
   - Time-weighted preference strength?

---

*Next: [02_PRIVACY_ARCHITECTURE.md](02_PRIVACY_ARCHITECTURE.md) - The PII stripping workflow*
