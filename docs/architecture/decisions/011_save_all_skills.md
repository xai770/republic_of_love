# ADR-011: Skill Extraction - Save All Skills

**Status:** Accepted  
**Date:** 2025-11-30  
**Deciders:** xai, Sandy  
**Tags:** skills, data-preservation, schema

---

## Context

The skill extraction pipeline was losing 77% of extracted skills because only taxonomy-matched skills were saved to `posting_skills`.

### The Problem

**Before fix:**
- Total skills extracted (in `skill_keywords`): 12,881
- Skills saved to `posting_skills`: 2,931
- **Lost: 9,950 skills (77.2%)**

**Why?** The `posting_skills_saver.py` only saved skills that matched entries in `skill_aliases`. Non-taxonomy skills were discarded.

---

## Decision

**Save ALL extracted skills, with taxonomy matching optional.**

### Schema Change

```sql
-- Allow skill_id to be NULL for non-taxonomy skills
ALTER TABLE posting_skills ALTER COLUMN skill_id DROP NOT NULL;

-- Add column for raw skill names
ALTER TABLE posting_skills ADD COLUMN raw_skill_name TEXT;

-- Index for lookups
CREATE INDEX idx_posting_skills_raw_name ON posting_skills(LOWER(raw_skill_name));

-- Prevent duplicates for non-taxonomy skills
CREATE UNIQUE INDEX idx_posting_skills_raw_unique 
ON posting_skills(posting_id, LOWER(raw_skill_name)) 
WHERE skill_id IS NULL;
```

### Code Change

File: `core/wave_runner/actors/posting_skills_saver.py`

Now handles both:
1. **Taxonomy skills:** `skill_id` populated, `raw_skill_name` NULL
2. **Non-taxonomy skills:** `skill_id` NULL, `raw_skill_name` populated

---

## Consequences

### Positive

1. **0% skill loss** - All extracted skills preserved
2. **Future matching** - Can retroactively match skills when taxonomy expands
3. **Better analytics** - See what skills LLM extracts vs what's in taxonomy

### Negative

1. **More rows** - `posting_skills` table grows faster
2. **Duplicate names possible** - "Python" and "python" could both exist

---

## Verification

```sql
-- Check skills are being saved
SELECT 
    COUNT(*) FILTER (WHERE skill_id IS NOT NULL) as taxonomy_skills,
    COUNT(*) FILTER (WHERE skill_id IS NULL) as non_taxonomy_skills
FROM posting_skills;
```
