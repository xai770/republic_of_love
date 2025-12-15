# Dynamic Field Mapping for Multi-Source Job Extraction

**Status:** 🟡 DESIGN - Not Yet Implemented  
**Date:** November 24, 2025  
**Author:** Arden  
**Purpose:** Handle job postings from multiple sources with different schemas

---

## The Problem

**Scenario:**
```
Deutsche Bank API:
  { "PositionTitle": "...", "CareerLevel": [...], "PositionLocation": [...] }

LinkedIn API:
  { "title": "...", "seniority": "...", "location": { "city": "..." } }

Indeed Scraper:
  { "job_name": "...", "level": "...", "where": "..." }
```

**Same data, different field names!**

Our `postings` table expects:
```sql
job_title TEXT
location_city TEXT  
employment_career_level TEXT
```

**How do we extract from all 3 sources without hardcoding 3 different parsers?**

---

## Solution: LLM-Generated Field Mappings

### The Hybrid Approach (Option C)

**Step 1: First Time Seeing New Source**
```
New JSON arrives → LLM analyzes structure → Generates mapping → Cache in database
```

**Step 2: Subsequent Requests from Same Source**
```
Same source → Query cache → Use cached mapping → Fast extraction
```

**Step 3: Schema Change Detection**
```
New fields appear → LLM updates mapping → Cache updated → Continue
```

---

## Architecture

### Database Schema

```sql
-- Table for cached mappings
CREATE TABLE posting_field_mappings (
    mapping_id SERIAL PRIMARY KEY,
    source_identifier TEXT NOT NULL,  -- 'deutschebank_api', 'linkedin_api', 'indeed_scraper'
    source_version TEXT,               -- 'v1', 'v2', '2025-11', etc.
    field_mappings JSONB NOT NULL,     -- The actual mapping rules
    confidence_score FLOAT,            -- LLM's confidence (0.0-1.0)
    validation_status TEXT,            -- 'pending', 'validated', 'failed'
    sample_input JSONB,                -- Example JSON that was analyzed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_actor_id INT REFERENCES actors(actor_id),
    enabled BOOLEAN DEFAULT TRUE,
    UNIQUE(source_identifier, source_version)
);

CREATE INDEX idx_field_mappings_source ON posting_field_mappings(source_identifier) 
WHERE enabled = TRUE;

COMMENT ON TABLE posting_field_mappings IS 
'LLM-generated field mappings for dynamic source adaptation.
When new job source encountered, LLM analyzes JSON structure and generates mapping rules.
Cached for reuse on subsequent postings from same source.';

COMMENT ON COLUMN posting_field_mappings.field_mappings IS 
'JSONB mapping rules. Example:
{
  "job_title": {"path": "PositionTitle", "type": "string"},
  "location_city": {"path": "PositionLocation[0].CityName", "type": "string"},
  "employment_career_level": {"path": "CareerLevel[0].Name", "type": "string"},
  "job_description": {"path": "PositionDescription", "type": "string"}
}';
```

### Workflow 3XXX: Generate Field Mapping

**Trigger:** New job source encountered (no mapping in cache)

**Input:**
- `source_identifier` - e.g., "linkedin_api"
- `sample_json` - Example posting JSON from that source

**Output:**
- Field mapping cached in `posting_field_mappings` table

**Conversations:**

#### Conversation 1: Analyze Source Schema (qwen2.5:7b)

**Prompt:**
```
You are a data extraction expert. Analyze this JSON structure from a job posting API.

Source: {source_identifier}
Sample JSON:
{sample_json}

Our target schema requires these fields:
- job_title (TEXT)
- job_description (TEXT)  
- location_city (TEXT)
- location_country (TEXT)
- employment_type (TEXT) - "full-time", "part-time", "contract", etc.
- employment_career_level (TEXT) - "entry", "mid", "senior", "executive"
- employment_schedule (TEXT) - "on-site", "remote", "hybrid"
- external_url (TEXT)
- company_name (TEXT)

Generate a JSON mapping that extracts our fields from this source structure.

Output format:
{
  "job_title": {"path": "...", "type": "string", "required": true},
  "job_description": {"path": "...", "type": "string", "required": true},
  ...
}

For nested fields, use dot notation: "CareerLevel[0].Name"
For optional fields, set "required": false
For fields that need transformation, add "transform": "lowercase|uppercase|titlecase"
If field doesn't exist in source, set path to null.
```

**Branching:**
- `[VALID_MAPPING]` → Save mapping
- `[INSUFFICIENT_DATA]` → Request more samples
- `[SCHEMA_UNCLEAR]` → Create human task for review

#### Conversation 2: Validate Mapping (Script Actor)

**Script:** `validate_field_mapping.py`

**Logic:**
```python
def validate_mapping(mapping_json, sample_json):
    """Test mapping against sample data."""
    errors = []
    warnings = []
    
    for field, rules in mapping_json.items():
        path = rules.get('path')
        required = rules.get('required', False)
        
        if path is None:
            if required:
                errors.append(f"Required field '{field}' has no mapping")
            continue
        
        # Try to extract value
        try:
            value = extract_by_path(sample_json, path)
            if value is None and required:
                errors.append(f"Required field '{field}' extracted as null")
        except Exception as e:
            errors.append(f"Field '{field}' extraction failed: {e}")
    
    if errors:
        return {'status': 'FAILED', 'errors': errors}
    elif warnings:
        return {'status': 'WARNING', 'warnings': warnings}
    else:
        return {'status': 'VALIDATED'}
```

**Branching:**
- `[VALIDATED]` → Save to posting_field_mappings table
- `[FAILED]` → Loop back to Conversation 1 with error feedback
- `[WARNING]` → Save but mark as needs_review

#### Conversation 3: Save Mapping (Script Actor)

**Script:** `save_field_mapping.py`

**Logic:**
```python
def save_mapping(source_identifier, mapping_json, sample_json, confidence):
    """Save validated mapping to database."""
    cursor.execute("""
        INSERT INTO posting_field_mappings 
        (source_identifier, field_mappings, confidence_score, 
         validation_status, sample_input, created_by_actor_id)
        VALUES (%s, %s, %s, 'validated', %s, %s)
        ON CONFLICT (source_identifier, source_version) 
        DO UPDATE SET 
            field_mappings = EXCLUDED.field_mappings,
            confidence_score = EXCLUDED.confidence_score,
            updated_at = NOW()
        RETURNING mapping_id
    """, (source_identifier, json.dumps(mapping_json), confidence, 
          json.dumps(sample_json), actor_id))
    
    return {'mapping_id': cursor.fetchone()[0], 'status': 'SAVED'}
```

---

## Integration with Job Fetcher

### Enhanced Fetcher Logic

```python
# core/wave_runner_v2/actors/db_job_fetcher.py (enhanced)

def fetch_and_map_jobs(source_identifier, api_endpoint):
    """Fetch jobs and apply dynamic field mapping."""
    
    # 1. Fetch raw JSON from API
    raw_jobs = call_api(api_endpoint)
    
    # 2. Check if we have mapping for this source
    mapping = get_field_mapping(source_identifier)
    
    if mapping is None:
        # 3. First time seeing this source - generate mapping
        sample_json = raw_jobs[0]  # Use first result as sample
        
        # Trigger workflow 3XXX (field mapping generation)
        mapping_workflow_run = create_workflow_run(
            workflow_id=get_workflow_id('dynamic_field_mapping'),
            input_data={
                'source_identifier': source_identifier,
                'sample_json': sample_json
            }
        )
        
        # Wait for mapping to be generated (or timeout)
        mapping = wait_for_mapping(source_identifier, timeout=300)
        
        if mapping is None:
            raise Exception(f"Failed to generate mapping for {source_identifier}")
    
    # 4. Apply mapping to all fetched jobs
    mapped_jobs = []
    for raw_job in raw_jobs:
        mapped_job = apply_field_mapping(raw_job, mapping)
        mapped_jobs.append(mapped_job)
    
    # 5. Insert into postings_staging
    insert_staging_jobs(mapped_jobs, source_identifier)
    
    return {'fetched': len(raw_jobs), 'mapped': len(mapped_jobs)}


def apply_field_mapping(raw_json, mapping):
    """Extract fields using mapping rules."""
    result = {}
    
    for field, rules in mapping['field_mappings'].items():
        path = rules.get('path')
        if path is None:
            result[field] = None
            continue
        
        # Extract value by path
        value = extract_by_path(raw_json, path)
        
        # Apply transformations
        if 'transform' in rules:
            value = apply_transform(value, rules['transform'])
        
        result[field] = value
    
    return result


def extract_by_path(data, path):
    """Extract value from nested JSON using dot notation.
    
    Examples:
      "CareerLevel[0].Name" → data['CareerLevel'][0]['Name']
      "location.city" → data['location']['city']
    """
    import re
    
    parts = re.split(r'\.|\[|\]', path)
    parts = [p for p in parts if p]  # Remove empty strings
    
    current = data
    for part in parts:
        if part.isdigit():
            current = current[int(part)]
        else:
            current = current.get(part)
            if current is None:
                return None
    
    return current
```

---

## Schema Change Detection

### Problem: Source API changes schema

**Example:**
```
Week 1: { "PositionTitle": "..." }
Week 2: { "job_title": "..." }  ← Field renamed!
```

### Solution: Drift Detection

```python
def detect_schema_drift(source_identifier, current_json):
    """Check if current JSON matches cached mapping."""
    
    mapping = get_field_mapping(source_identifier)
    
    # Extract all paths from mapping
    expected_paths = [rules['path'] for rules in mapping['field_mappings'].values() 
                     if rules['path'] is not None]
    
    # Check if paths exist in current JSON
    missing_paths = []
    for path in expected_paths:
        value = extract_by_path(current_json, path)
        if value is None:
            missing_paths.append(path)
    
    if len(missing_paths) > 0.3 * len(expected_paths):
        # 30%+ of fields missing - likely schema change
        logger.warning(f"Schema drift detected for {source_identifier}")
        
        # Regenerate mapping
        trigger_mapping_regeneration(source_identifier, current_json)
        
        return {'drift_detected': True, 'missing_paths': missing_paths}
    
    return {'drift_detected': False}
```

---

## Example: Adding LinkedIn Source

### Step 1: First LinkedIn Job Arrives

```python
# Fetcher encounters unknown source
fetch_and_map_jobs(
    source_identifier='linkedin_api',
    api_endpoint='https://api.linkedin.com/v2/jobs'
)
```

### Step 2: LLM Analyzes Sample

```json
// Sample LinkedIn JSON
{
  "title": "Senior Backend Engineer",
  "company": {"name": "Tech Corp"},
  "location": {"city": "Berlin", "country": "Germany"},
  "description": "We are looking for...",
  "seniority": "Mid-Senior level",
  "employmentType": "Full-time",
  "workplaceType": "Remote",
  "applyUrl": "https://linkedin.com/jobs/123"
}
```

**LLM Output:**
```json
{
  "job_title": {"path": "title", "type": "string", "required": true},
  "job_description": {"path": "description", "type": "string", "required": true},
  "location_city": {"path": "location.city", "type": "string", "required": false},
  "location_country": {"path": "location.country", "type": "string", "required": false},
  "employment_type": {"path": "employmentType", "type": "string", "required": false, "transform": "lowercase"},
  "employment_career_level": {"path": "seniority", "type": "string", "required": false},
  "employment_schedule": {"path": "workplaceType", "type": "string", "required": false, "transform": "lowercase"},
  "external_url": {"path": "applyUrl", "type": "string", "required": true},
  "company_name": {"path": "company.name", "type": "string", "required": false}
}
```

### Step 3: Mapping Validated & Cached

```sql
INSERT INTO posting_field_mappings (source_identifier, field_mappings, ...)
VALUES ('linkedin_api', '{...}', ...);
```

### Step 4: Subsequent LinkedIn Jobs Use Cache

```python
# Next 1000 LinkedIn jobs
for job in fetch_jobs('linkedin_api'):
    mapped_job = apply_field_mapping(job, cached_mapping)
    # Fast! No LLM call needed
```

---

## Performance Impact

### Without Dynamic Mapping (Hardcoded)
```python
# 3 different parsers to maintain
def parse_deutschebank(json): ...
def parse_linkedin(json): ...  
def parse_indeed(json): ...

# Problem: Add 4th source = write new parser
```

### With Dynamic Mapping (LLM-Generated)
```python
# One generic parser
def parse_any_source(json, mapping): ...

# Add 4th source = LLM generates mapping automatically
# No code changes needed!
```

### Cost Analysis

**LinkedIn Example (1000 jobs/day):**

**First Day:**
- 1 LLM call (generate mapping): ~$0.001
- 1000 extractions (cached mapping): $0 (no LLM)
- **Total: $0.001**

**Days 2-365:**
- 0 LLM calls (use cache)
- 365,000 extractions: $0
- **Total: $0**

**Schema Change (once per year):**
- 1 LLM call (regenerate): ~$0.001
- **Total: $0.002/year**

**vs Hardcoded Parser:**
- Developer time: 4 hours @ $50/hr = $200
- Maintenance: 2 hours/year = $100/year

**ROI: $200 saved first year, $100/year ongoing**

---

## Error Handling

### Mapping Generation Failed

```python
if mapping_generation_timeout():
    # Fallback: Use generic heuristic mapping
    mapping = generate_heuristic_mapping(sample_json)
    # Flag for human review
    create_human_task(
        actor_name='xai',
        prompt=f"Mapping generation failed for {source_identifier}. Review sample and create manual mapping."
    )
```

### Extraction Failed

```python
try:
    mapped_job = apply_field_mapping(raw_job, mapping)
except Exception as e:
    logger.error(f"Extraction failed: {e}")
    # Save to error queue
    save_failed_extraction(raw_job, mapping, error=str(e))
    # Increment failure count
    increment_mapping_failures(source_identifier)
    
    # If failures > 10, flag for review
    if get_failure_count(source_identifier) > 10:
        trigger_mapping_regeneration(source_identifier, raw_job)
```

---

## Testing Strategy

### Test 1: Generate Mapping for New Source

```python
# Test with Indeed sample
sample_indeed = {
    "job_name": "Python Developer",
    "level": "Senior",
    "where": "Munich",
    "description": "...",
    "link": "https://indeed.com/job/123"
}

mapping = generate_field_mapping('indeed_scraper', sample_indeed)

assert 'job_title' in mapping['field_mappings']
assert mapping['field_mappings']['job_title']['path'] == 'job_name'
```

### Test 2: Apply Mapping

```python
mapped = apply_field_mapping(sample_indeed, mapping)

assert mapped['job_title'] == "Python Developer"
assert mapped['employment_career_level'] == "Senior"
assert mapped['location_city'] == "Munich"
```

### Test 3: Detect Schema Drift

```python
# Old schema
old_json = {"PositionTitle": "Engineer"}

# New schema (field renamed)
new_json = {"job_title": "Engineer"}

drift = detect_schema_drift('deutschebank_api', new_json)

assert drift['drift_detected'] == True
assert 'PositionTitle' in drift['missing_paths']
```

---

## Migration Path

### Phase 1: Deutsche Bank Only (Current)
- Hardcoded parser in `db_job_fetcher.py`
- No field mapping table

### Phase 2: Add Dynamic Mapping (Next)
- Create `posting_field_mappings` table
- Create workflow 3XXX (field mapping generation)
- Migrate Deutsche Bank to use dynamic mapping
- Test with sample data

### Phase 3: Add LinkedIn (Future)
- Configure LinkedIn API credentials
- First fetch triggers mapping generation
- Subsequent fetches use cached mapping

### Phase 4: Add Indeed, Glassdoor, etc. (Future)
- Same pattern repeats
- No code changes needed per source
- Just configure API endpoint + identifier

---

## Summary

**Problem Solved:** Extract job postings from multiple sources without hardcoding parsers

**Solution:** LLM generates field mapping → cache in database → reuse for all jobs from that source

**Benefits:**
- ✅ Add new sources without code changes
- ✅ Auto-adapt to schema changes
- ✅ One LLM call per source (not per job)
- ✅ Fast extraction (cached mapping)
- ✅ Maintainable (no parser spaghetti)

**Trade-offs:**
- ⚠️ First job from new source slower (LLM call + validation)
- ⚠️ Mapping quality depends on LLM accuracy
- ⚠️ Need human review for complex schemas

**Next Steps:**
1. Create migration 044 (add posting_field_mappings table)
2. Create workflow 3XXX (field mapping generation)
3. Enhance db_job_fetcher with dynamic mapping support
4. Test with Deutsche Bank (migrate from hardcoded)
5. Add LinkedIn source (prove it works)

---

**Status:** Ready for implementation when we add 2nd job source! 🚀
