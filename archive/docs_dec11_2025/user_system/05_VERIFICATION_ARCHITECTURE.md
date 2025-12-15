# Verification Architecture: Verify Then Forget

**Author:** Arden  
**Date:** 2025-11-30  
**Status:** Draft Proposal

---

## Core Principle

> **Verify the claim, forget the evidence.**

We confirm users are who they say they are, then delete everything except the verification result.

---

## The Problem

| Goal | Requirement | Tension |
|------|-------------|---------|
| Trustworthy ratings | User actually worked there | Need to verify |
| Privacy | Don't store work history | Can't keep evidence |
| Fraud prevention | Detect fake profiles | Need to check claims |

**Solution:** Verify → Store result → Delete evidence

---

## What We Can Verify

| Claim Type | Verification Source | Reliability |
|------------|---------------------|-------------|
| Company employment | Web search, LinkedIn | 🟢 High (for senior), 🟡 Medium (mid-level) |
| Certifications (CFA, FRM, PMP) | Public registries | 🟢 High (exact match) |
| Career level | LinkedIn titles, press releases | 🟢 High (executives), 🟡 Medium (others) |
| Years of experience | LinkedIn tenure | 🟡 Medium |
| Industry experience | Work history pattern | 🟡 Medium |
| Education | University alumni? | 🟡 Medium |
| Language skills | Hard to verify | 🔴 Low |

---

## Verification Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VERIFY THEN FORGET FLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 1: User provides info (RAM only)                             │
│  ─────────────────────────────────────                             │
│  User submits:                                                      │
│    - Real name (temporary!)                                         │
│    - Claims: "VP at Deutsche Bank", "CFA charterholder"            │
│                                                                     │
│  STEP 2: Verification (local processing)                           │
│  ────────────────────────────────────────                          │
│  For each claim:                                                    │
│    a) Search public sources (DuckDuckGo via ddgr)                  │
│       Query: "John Smith Deutsche Bank VP"                         │
│    b) Check registries (CFA Institute directory)                   │
│    c) Local LLM analyzes results                                   │
│    d) Produces: {verified: true, confidence: 0.85}                 │
│                                                                     │
│  STEP 3: Store result only                                         │
│  ─────────────────────────                                         │
│  INSERT INTO user_verifications:                                    │
│    user_id: 123                                                     │
│    type: 'company_employment'                                       │
│    claimed_value: 'company_id:47'  -- NOT "Deutsche Bank"          │
│    is_verified: true                                                │
│    confidence: 0.85                                                 │
│                                                                     │
│  STEP 4: Delete evidence                                           │
│  ────────────────────────                                          │
│  Purge from memory:                                                 │
│    ❌ Real name                                                     │
│    ❌ Search results                                                │
│    ❌ URLs found                                                    │
│    ❌ LinkedIn profile data                                        │
│    ❌ Raw registry responses                                       │
│                                                                     │
│  RESULT                                                            │
│  ──────                                                            │
│  We know: "User 123 is verified for company 47"                    │
│  We don't know: "User 123 is John Smith who was VP at DB"         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Schema

### Companies Table (Public Knowledge)

```sql
CREATE TABLE companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    
    -- Public info
    industry VARCHAR(100),
    size_category VARCHAR(50),  -- 'startup', 'mid', 'enterprise'
    headquarters_country VARCHAR(100),
    website_url VARCHAR(500),
    
    -- Aggregated ratings (anonymous)
    avg_rating DECIMAL(3,2),  -- 1.0 to 5.0
    rating_count INTEGER DEFAULT 0,
    verified_rating_count INTEGER DEFAULT 0,
    
    -- From our posting analysis
    ihl_avg_score DECIMAL(3,2),
    posting_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE companies IS
'Public company information. Ratings are aggregated anonymously.
We track verified vs unverified ratings separately.';
```

### User Company Verifications (Permissions Only)

```sql
CREATE TABLE user_company_verifications (
    user_id INTEGER REFERENCES users(user_id),
    company_id INTEGER REFERENCES companies(company_id),
    
    -- Verification result
    is_verified BOOLEAN NOT NULL,
    confidence DECIMAL(3,2),  -- 0.0 to 1.0
    verification_method VARCHAR(50),  -- 'web_search', 'registry', 'linkedin_oauth'
    
    -- Metadata
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Reverify after 2 years?
    
    PRIMARY KEY (user_id, company_id)
);

COMMENT ON TABLE user_company_verifications IS
'Records that user CAN rate this company (verified employment).
Does NOT store: job title, dates, duration, role, or how we verified.
The verification evidence is deleted after verification completes.';
```

### General Verifications

```sql
CREATE TABLE user_verifications (
    verification_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    
    -- What was verified
    verification_type VARCHAR(50) NOT NULL,
    -- Types: 'career_level', 'certification', 'years_experience', 'industry'
    
    claimed_value VARCHAR(200),  -- 'senior', 'CFA', '10', 'banking'
    
    -- Result
    is_verified BOOLEAN NOT NULL,
    confidence DECIMAL(3,2),
    verification_method VARCHAR(50),
    
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    UNIQUE(user_id, verification_type, claimed_value)
);

COMMENT ON TABLE user_verifications IS
'General claim verifications (certifications, career level, etc.).
Stores RESULT only, not the evidence used to verify.';
```

### Company Ratings (With Verification Status)

```sql
CREATE TABLE company_ratings (
    rating_id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(company_id),
    user_id INTEGER REFERENCES users(user_id),
    
    -- The rating
    overall_rating INTEGER CHECK (overall_rating BETWEEN 1 AND 5),
    
    -- Category ratings (optional)
    culture_rating INTEGER CHECK (culture_rating BETWEEN 1 AND 5),
    management_rating INTEGER CHECK (management_rating BETWEEN 1 AND 5),
    compensation_rating INTEGER CHECK (compensation_rating BETWEEN 1 AND 5),
    growth_rating INTEGER CHECK (growth_rating BETWEEN 1 AND 5),
    worklife_rating INTEGER CHECK (worklife_rating BETWEEN 1 AND 5),
    
    -- Was user verified for this company?
    is_verified_rater BOOLEAN DEFAULT FALSE,
    
    -- Anonymized review summary (LLM-stripped, optional)
    review_summary TEXT,  -- "Negative management experience"
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, user_id)
);

COMMENT ON TABLE company_ratings IS
'Company ratings with verification status.
is_verified_rater = true means user was verified as having worked there.
review_summary is anonymized (no names, dates, specific incidents).';
```

---

## Implementation

### Web Search Verification

```python
def verify_company_employment(
    user_id: int, 
    real_name: str,  # TEMPORARY - deleted after use
    company_id: int
) -> dict:
    """
    Verify user worked at company via web search.
    
    PRIVACY CRITICAL:
    - real_name is NEVER stored, logged, or returned
    - Search results are NEVER stored
    - Only verification result is persisted
    """
    
    # Get company name for search
    company = db.get_company(company_id)
    company_name = company['company_name']
    
    # Search public web (local, via ddgr)
    search_query = f'"{real_name}" "{company_name}"'
    search_results = exec_agent.search(search_query)
    
    # Analyze with local LLM
    analysis = local_llm.analyze(
        prompt=f"""
        Based on these search results, determine if {real_name} 
        likely worked at {company_name}.
        
        Search results:
        {search_results}
        
        Return JSON:
        {{"likely_worked_there": true/false, "confidence": 0.0-1.0, "reasoning": "..."}}
        """,
        model="mistral:7b"
    )
    
    # Store ONLY the result
    db.execute("""
        INSERT INTO user_company_verifications 
        (user_id, company_id, is_verified, confidence, verification_method)
        VALUES (%s, %s, %s, %s, 'web_search')
        ON CONFLICT (user_id, company_id) DO UPDATE 
        SET is_verified = EXCLUDED.is_verified,
            confidence = EXCLUDED.confidence,
            verified_at = NOW()
    """, [user_id, company_id, analysis['likely_worked_there'], analysis['confidence']])
    
    # CRITICAL: Delete all evidence from memory
    del real_name
    del search_results
    del analysis
    
    # Return only verification status (no PII)
    return {
        "company_id": company_id,
        "verified": analysis['likely_worked_there'],
        "confidence": analysis['confidence']
    }
```

### Certification Registry Verification

```python
def verify_certification(
    user_id: int,
    real_name: str,  # TEMPORARY
    certification: str  # 'CFA', 'FRM', 'PMP'
) -> dict:
    """
    Verify certification via public registry.
    """
    
    REGISTRY_URLS = {
        'CFA': 'https://www.cfainstitute.org/community/membership/directory',
        'FRM': 'https://www.garp.org/frm/directory',
        'PMP': 'https://www.pmi.org/certifications/certification-registry'
    }
    
    if certification not in REGISTRY_URLS:
        return {"verified": False, "reason": "unknown_certification"}
    
    # Search registry (some allow direct lookup)
    registry_url = REGISTRY_URLS[certification]
    search_results = exec_agent.fetch(f"{registry_url}?search={real_name}")
    
    # Analyze
    analysis = local_llm.analyze(
        prompt=f"Is '{real_name}' listed as a {certification} holder in these results?",
        context=search_results
    )
    
    # Store result only
    db.create_verification(
        user_id=user_id,
        verification_type='certification',
        claimed_value=certification,
        is_verified=analysis['found'],
        confidence=analysis['confidence'],
        verification_method='registry_lookup'
    )
    
    # Delete evidence
    del real_name
    del search_results
    
    return {"verified": analysis['found'], "certification": certification}
```

---

## Ratings Display

The UI shows verification status transparently:

```
┌─────────────────────────────────────────────────────────────────┐
│  Deutsche Bank                                                   │
│  ═══════════════                                                │
│                                                                  │
│  Overall Rating: ⭐⭐⭐☆☆ 3.2/5                                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Verified Employees (47 ratings)     ⭐⭐⭐☆☆ 2.8/5      │   │
│  │ All Ratings (156 ratings)           ⭐⭐⭐☆☆ 3.4/5      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Category Breakdown (verified employees):                        │
│  ├── Culture:        ⭐⭐⭐☆☆ 3.1                              │
│  ├── Management:     ⭐⭐☆☆☆ 2.3                              │
│  ├── Compensation:   ⭐⭐⭐⭐☆ 3.8                              │
│  ├── Growth:         ⭐⭐⭐☆☆ 2.9                              │
│  └── Work-Life:      ⭐⭐☆☆☆ 2.4                              │
│                                                                  │
│  💡 Verified employees rate 0.6 points lower than general       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

The discrepancy between verified and unverified ratings is itself valuable signal.

---

## Privacy Guarantees

| Data | Stored? | Where? | Duration |
|------|---------|--------|----------|
| User's real name | ❌ Never | RAM only during verification | Seconds |
| Search results | ❌ Never | RAM only | Seconds |
| Registry responses | ❌ Never | RAM only | Seconds |
| LinkedIn profile data | ❌ Never | RAM only | Seconds |
| "User 123 verified for company 47" | ✅ Yes | user_company_verifications | Until user deletes account |
| "User 123 is CFA holder" | ✅ Yes | user_verifications | Until user deletes account |

**What we CAN answer:** "Is this user verified to rate this company?"  
**What we CANNOT answer:** "What is this user's name?" or "Where did they work?"

---

## Limitations & Mitigations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Common names | Low confidence | Require additional signals (company + title + timeframe) |
| Privacy-conscious users | Can't verify | Allow unverified ratings, flag them |
| LinkedIn not updated | Stale verification | Set expiration, reverify periodically |
| Name changes | Verification fails | Allow re-verification with new name |
| Non-English sources | Search less effective | Focus on English-language sources initially |

---

## Future Enhancements

1. **LinkedIn OAuth** - User authorizes, we verify, highest accuracy
2. **Email domain verification** - User has @db.com email = works at DB
3. **Multi-signal scoring** - Combine web search + registry + email for confidence
4. **Reverification cron** - Periodically check if verifications still valid
5. **Fraud detection** - Detect suspicious patterns (bulk fake accounts)

---

## Open Questions

1. **How often to reverify?** Every 2 years? When user updates profile?
2. **What if verification fails but user insists?** Manual review queue?
3. **Should unverified users still be able to rate?** Yes, but flagged?
4. **What's minimum confidence threshold?** 0.7? 0.8?

---

*This document is part of the User System design series:*
- *01_SCHEMA_DESIGN.md - Core tables*
- *02_PRIVACY_ARCHITECTURE.md - PII handling*
- *03_MATCHING_ALGORITHM.md - Job matching*
- *04_FEEDBACK_LOOP.md - Preference learning*
- *05_VERIFICATION_ARCHITECTURE.md - Verify then forget (this doc)*
