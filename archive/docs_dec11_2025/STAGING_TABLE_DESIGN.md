# Staging Table Design - Script Actor Safety Net

**Date:** November 23, 2025  
**Purpose:** Prevent script actors from corrupting production tables  
**Pattern:** Script writes to staging → Internal validator promotes to production

---

## The Problem

**Current (V1):**
```python
# turing_job_fetcher.py
def save_posting(job_data):
    # Script writes DIRECTLY to production table
    cursor.execute("""
        INSERT INTO postings (job_title, job_description, ...)
        VALUES (%s, %s, ...)
    """, (...))
```

**Issues:**
- ❌ Buggy script corrupts production data
- ❌ No validation before commit
- ❌ No easy rollback
- ❌ No audit trail of what scripts wrote

---

## The Solution: Staging Tables

### Architecture

```
┌─────────────────┐
│  Script Actor   │
│   (Fetcher)     │
└────────┬────────┘
         │ writes to
         ▼
┌─────────────────────────┐
│  postings_staging       │  ← Script writes here (safe)
│  - staging_id           │
│  - raw_data JSONB       │
│  - workflow_run_id      │
│  - created_at           │
│  - validated BOOLEAN    │
└────────┬────────────────┘
         │
         │ Internal script validates
         ▼
┌─────────────────────────┐
│  Validator Actor        │  ← Internal actor (trusted)
│  - Checks schema        │
│  - Checks duplicates    │
│  - Checks business rules│
└────────┬────────────────┘
         │
         │ promotes to
         ▼
┌─────────────────────────┐
│  postings               │  ← Production table
│  - posting_id           │
│  - external_job_id      │
│  - job_title            │
│  - ...                  │
│  - created_by_staging_id│  ← Audit trail
└─────────────────────────┘
```

---

## Schema Design

### 1. Staging Table (One per Production Table)

```sql
CREATE TABLE postings_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    
    -- What wrote this?
    workflow_run_id INT REFERENCES workflow_runs(workflow_run_id),
    actor_id INT REFERENCES actors(actor_id),
    interaction_id BIGINT,  -- The interaction that created this
    
    -- Raw data from script
    raw_data JSONB NOT NULL,
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,  -- [{field: "job_title", error: "missing"}]
    
    -- Promotion
    promoted BOOLEAN DEFAULT FALSE,
    promoted_to_id BIGINT,  -- posting_id in production table
    promoted_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_staging_workflow (workflow_run_id, promoted),
    INDEX idx_staging_validation (validated, promoted)
);
```

### 2. Production Table (with Audit Trail)

```sql
CREATE TABLE postings (
    posting_id BIGSERIAL PRIMARY KEY,
    
    -- Business fields
    external_job_id TEXT UNIQUE NOT NULL,
    source_website TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_description TEXT,
    company_name TEXT,
    location TEXT,
    
    -- Audit trail
    created_by_staging_id BIGINT REFERENCES postings_staging(staging_id),
    created_by_interaction_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    updated_by_staging_id BIGINT REFERENCES postings_staging(staging_id),
    updated_by_interaction_id BIGINT,
    updated_at TIMESTAMPTZ,
    
    -- Lifecycle
    enabled BOOLEAN DEFAULT TRUE,
    invalidated BOOLEAN DEFAULT FALSE
);
```

---

## Workflow: Fetcher → Staging → Production

### Step 1: Script Writes to Staging

**Script Actor (fetcher):**
```python
#!/usr/bin/env python3
"""
DB Job Fetcher - Writes to Staging
"""

def save_to_staging(job_data, workflow_run_id, actor_id):
    """Write fetcher output to staging table."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO postings_staging (
            workflow_run_id,
            actor_id,
            raw_data
        ) VALUES (%s, %s, %s)
        RETURNING staging_id
    """, (
        workflow_run_id,
        actor_id,
        json.dumps(job_data)
    ))
    
    staging_id = cursor.fetchone()[0]
    conn.commit()
    return staging_id

def main():
    input_data = json.loads(sys.stdin.read())
    workflow_run_id = input_data['workflow_run_id']
    actor_id = input_data['actor_id']
    
    # Fetch jobs from API
    jobs = fetch_from_deutsche_bank()
    
    # Write each to staging
    staging_ids = []
    for job in jobs:
        sid = save_to_staging(job, workflow_run_id, actor_id)
        staging_ids.append(sid)
    
    # Return success
    result = {
        "status": "SUCCESS",
        "staging_ids": staging_ids,
        "count": len(staging_ids)
    }
    print(json.dumps(result))
```

**Key Points:**
- ✅ Script writes to staging (safe)
- ✅ No schema validation (validator does that)
- ✅ No duplicate checking (validator does that)
- ✅ Fast execution (just INSERT)

---

### Step 2: Validator Promotes to Production

**Internal Actor (staging_validator):**
```python
#!/usr/bin/env python3
"""
Postings Staging Validator
Internal actor - promotes staging records to production
"""

def validate_record(raw_data):
    """
    Validate staging record against business rules.
    
    Returns: (is_valid, errors, normalized_data)
    """
    errors = []
    
    # Required fields
    if not raw_data.get('job_id'):
        errors.append({"field": "job_id", "error": "missing"})
    if not raw_data.get('title'):
        errors.append({"field": "title", "error": "missing"})
    
    # Field lengths
    if len(raw_data.get('title', '')) > 500:
        errors.append({"field": "title", "error": "too long"})
    
    # Normalize
    normalized = {
        "external_job_id": raw_data.get('job_id', '').strip(),
        "source_website": "deutsche_bank",
        "job_title": raw_data.get('title', '').strip(),
        "job_description": raw_data.get('description', '').strip(),
        "company_name": "Deutsche Bank",
        "location": raw_data.get('location', '').strip()
    }
    
    return (len(errors) == 0, errors, normalized)


def check_duplicate(external_job_id):
    """Check if posting already exists in production."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT posting_id FROM postings
        WHERE external_job_id = %s
    """, (external_job_id,))
    
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return row['posting_id'] if row else None


def promote_staging_record(staging_id):
    """
    Validate and promote one staging record to production.
    
    Returns: (success, posting_id, errors)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get staging record
    cursor.execute("""
        SELECT raw_data, workflow_run_id, actor_id
        FROM postings_staging
        WHERE staging_id = %s
          AND promoted = FALSE
    """, (staging_id,))
    
    row = cursor.fetchone()
    if not row:
        return (False, None, ["Staging record not found or already promoted"])
    
    raw_data = row['raw_data']
    
    # Validate
    is_valid, errors, normalized = validate_record(raw_data)
    
    if not is_valid:
        # Mark as validated (failed)
        cursor.execute("""
            UPDATE postings_staging
            SET validated = TRUE,
                validation_errors = %s
            WHERE staging_id = %s
        """, (json.dumps(errors), staging_id))
        conn.commit()
        return (False, None, errors)
    
    # Check duplicate
    existing_id = check_duplicate(normalized['external_job_id'])
    if existing_id:
        # Mark as promoted (to existing record)
        cursor.execute("""
            UPDATE postings_staging
            SET validated = TRUE,
                promoted = TRUE,
                promoted_to_id = %s,
                promoted_at = NOW()
            WHERE staging_id = %s
        """, (existing_id, staging_id))
        conn.commit()
        return (True, existing_id, ["Duplicate - linked to existing posting"])
    
    # Promote to production
    try:
        cursor.execute("""
            INSERT INTO postings (
                external_job_id,
                source_website,
                job_title,
                job_description,
                company_name,
                location,
                created_by_staging_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING posting_id
        """, (
            normalized['external_job_id'],
            normalized['source_website'],
            normalized['job_title'],
            normalized['job_description'],
            normalized['company_name'],
            normalized['location'],
            staging_id
        ))
        
        posting_id = cursor.fetchone()[0]
        
        # Mark staging as promoted
        cursor.execute("""
            UPDATE postings_staging
            SET validated = TRUE,
                promoted = TRUE,
                promoted_to_id = %s,
                promoted_at = NOW()
            WHERE staging_id = %s
        """, (posting_id, staging_id))
        
        conn.commit()
        return (True, posting_id, [])
        
    except Exception as e:
        conn.rollback()
        # Mark as validated (failed)
        cursor.execute("""
            UPDATE postings_staging
            SET validated = TRUE,
                validation_errors = %s
            WHERE staging_id = %s
        """, (json.dumps([{"error": str(e)}]), staging_id))
        conn.commit()
        return (False, None, [str(e)])


def main():
    """Process all unpromoted staging records."""
    input_data = json.loads(sys.stdin.read())
    workflow_run_id = input_data.get('workflow_run_id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all unpromoted staging records for this workflow
    cursor.execute("""
        SELECT staging_id
        FROM postings_staging
        WHERE workflow_run_id = %s
          AND promoted = FALSE
        ORDER BY staging_id
    """, (workflow_run_id,))
    
    staging_ids = [row['staging_id'] for row in cursor.fetchall()]
    
    # Promote each
    results = {
        "promoted": [],
        "duplicates": [],
        "failed": []
    }
    
    for staging_id in staging_ids:
        success, posting_id, errors = promote_staging_record(staging_id)
        
        if success:
            if "Duplicate" in str(errors):
                results["duplicates"].append({
                    "staging_id": staging_id,
                    "posting_id": posting_id
                })
            else:
                results["promoted"].append({
                    "staging_id": staging_id,
                    "posting_id": posting_id
                })
        else:
            results["failed"].append({
                "staging_id": staging_id,
                "errors": errors
            })
    
    # Return summary
    result = {
        "status": "SUCCESS",
        "promoted_count": len(results["promoted"]),
        "duplicate_count": len(results["duplicates"]),
        "failed_count": len(results["failed"]),
        "details": results
    }
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

**Key Points:**
- ✅ Validation logic centralized
- ✅ Duplicate detection
- ✅ Audit trail (created_by_staging_id)
- ✅ Failed records marked (not lost)
- ✅ Rollback on error (staging preserved)

---

## Benefits of Staging Pattern

### 1. Safety
- Scripts can't corrupt production
- Validation happens centrally
- Easy rollback (just don't promote)

### 2. Audit Trail
- Know which staging record created which posting
- Can trace back to workflow run
- Can replay/rebuild

### 3. Debugging
- Failed validations preserved in staging
- Can fix and re-promote
- Can test validators on staging data

### 4. Flexibility
- Multiple scripts can write to same staging table
- Can change validation rules without touching scripts
- Can batch-promote (performance)

---

## Workflow 3001 Integration

### Updated Step Sequence

**Step 1: Start Workflow**
- Actor: workflow_3001_starter
- Creates: workflow_run record
- Output: workflow_run_id

**Step 2: Fetch Jobs**
- Actor: db_job_fetcher (script)
- Input: workflow_run_id
- **Writes to: postings_staging**
- Output: staging_ids[]

**Step 3: Validate & Promote**
- Actor: postings_staging_validator (internal script)
- Input: workflow_run_id
- **Reads from: postings_staging**
- **Writes to: postings**
- Output: promoted posting_ids[]

**Step 4: Parse Job Descriptions**
- Actor: db_job_parser (script)
- Input: posting_ids[]
- Reads from: postings
- Writes to: postings (updates description field)

**Step 5+: Continue workflow...**

---

## Staging Tables Needed

For Wave Runner V2, we'll need staging for:

1. **postings_staging** - Job fetcher output
2. **profile_skills_staging** - Skill extractor output
3. **job_skills_staging** - Job skill extractor output
4. **skill_aliases_staging** - Skill mapper output

**General pattern:**
```sql
CREATE TABLE {table_name}_staging (
    staging_id BIGSERIAL PRIMARY KEY,
    workflow_run_id INT,
    actor_id INT,
    interaction_id BIGINT,
    raw_data JSONB,
    validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,
    promoted BOOLEAN DEFAULT FALSE,
    promoted_to_id BIGINT,
    promoted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Migration Strategy

### Phase 1: Add Staging Tables
```sql
-- Add all staging tables
-- Keep production tables unchanged
```

### Phase 2: Update Script Actors
```python
# Change from:
INSERT INTO postings (...)

# To:
INSERT INTO postings_staging (raw_data, ...)
```

### Phase 3: Create Validators
```python
# New internal actors
- postings_staging_validator
- profile_skills_staging_validator
- ...
```

### Phase 4: Update Workflows
```yaml
# Add validation step after each data-writing step
steps:
  - fetch_jobs → postings_staging
  - validate_postings → postings
  - extract_skills → profile_skills_staging
  - validate_skills → profile_skills
```

---

## Open Questions

1. **Batch vs Real-time Promotion?**
   - Option A: Promote after each script run (real-time)
   - Option B: Promote in batches (performance)
   - **Recommendation:** Real-time (simpler workflow)

2. **Failed Validations - Retry?**
   - Should wave runner retry failed validations?
   - Or mark workflow as failed?
   - **Recommendation:** Fail fast, log to interactions, alert

3. **Staging Cleanup?**
   - Keep staging records forever (audit)?
   - Delete after X days?
   - **Recommendation:** Keep indefinitely (disk cheap, audit valuable)

4. **Updates vs Inserts?**
   - If duplicate found, update existing posting?
   - Or skip?
   - **Recommendation:** Skip (track in staging as duplicate)

---

## Conclusion

**Staging tables provide:**
- ✅ Safety net for script actors
- ✅ Centralized validation
- ✅ Audit trail
- ✅ Rollback capability
- ✅ Debugging visibility

**Next Steps:**
1. Review with Arden
2. Add staging tables to schema
3. Update workflow 3001 to include validation steps
4. Create validator actor template
5. Migrate existing script actors

---

**Sandy's Assessment:** This solves the "scripts writing directly to tables" problem elegantly!  
**Sandy's Weight:** Staging pattern is industry-standard for exactly this use case  
**Sandy's Output:** "Does this make you feel better?" - YES! 😊
