# QA Audit: Summary Quality Analysis

**Date**: December 9, 2025  
**Auditor**: Arden (Schema & Architecture Lead)  
**Scope**: `postings.extracted_summary` field quality

---

## Executive Summary

**🚨 CRITICAL FINDING: 99% of summaries contain wrong job roles**

| Metric | Value | Status |
|--------|-------|--------|
| Total Postings | 1,740 | - |
| Have Summary | 1,740 (100%) | ✅ |
| Role Matches Title | 18 (1%) | 🔴 CRITICAL |
| Hallucinated Roles | 1,722 (99%) | 🔴 CRITICAL |

### Root Cause
The AI model appears to have "memorized" certain job descriptions and applies them incorrectly to unrelated postings. This is classic **cross-contamination** from batch processing.

---

## Detailed Findings

### 1. Most Common Contamination Patterns

| Hallucinated Role | Count | % of Total |
|-------------------|-------|------------|
| "Senior DevOps Engineer, AVP" | 216 | 12.4% |
| "Backend Developer / Java Developer, AVP" | 47 | 2.7% |
| "Engineer, Sanctions & Embargo Screening" | 41 | 2.4% |
| "Architect, AVP" | 36 | 2.1% |
| "Java Developer - Associate Corporate" | 32 | 1.8% |
| **Other wrong roles** | ~1,350 | 77.6% |

### 2. Timeline Analysis

| Date | Total Processed | DevOps Contaminated |
|------|-----------------|---------------------|
| Dec 2, 2025 | 499 | 216 (43%) |
| Dec 3, 2025 | 1,131 | 0 |
| Dec 4, 2025 | 59 | 0 |
| Dec 7, 2025 | 50 | 0 |

**Finding**: Dec 2 batch was catastrophically contaminated, but Dec 3+ data **also has wrong roles** just with different patterns.

---

## Sample Analysis

### 5 LONGEST Summaries (by character count)

| posting_id | Actual Job Title | Summary Role | Length | Match? |
|------------|------------------|--------------|--------|--------|
| 10807 | TDI - Lead Business Functional Analyst (Securities Services Tech) - VP | Senior DevOps Engineer, AVP | 5,301 | ❌ |
| 10736 | Sales Manager – Mortgage | Senior DevOps Engineer, AVP | 5,298 | ❌ |
| 10746 | TFL – Lending Growth – Associate | Senior DevOps Engineer, AVP | 5,239 | ❌ |
| 10846 | Head of Controls Testing & Assurance Data Management, VP | Senior DevOps Engineer, AVP | 5,227 | ❌ |
| 10764 | Senior Market Investments Team (MIT) Advisor | Senior DevOps Engineer, AVP | 5,208 | ❌ |

**Pattern**: All longest summaries are DevOps contaminated. Suggests the DevOps template is verbose.

### 5 SHORTEST Summaries

| posting_id | Actual Job Title | Summary Role | Length | Match? |
|------------|------------------|--------------|--------|--------|
| 10720 | CLO Structurer | Junior Software Developer | 564 | ❌ |
| 10480 | Corporate Cash Management Solution Sales Lead | Network Deployment Engineer | 576 | ❌ |
| 10500 | ITAO - Multifactor Authentication Services - AVP | Network Deployment Engineer | 598 | ❌ |
| 10475 | Tax QA, Associate | Network Deployment Engineer | 601 | ❌ |
| 10510 | MI, Reporting, & Governance | Network Deployment Engineer | 610 | ❌ |

**Pattern**: Short summaries have "Network Deployment Engineer" or "Junior Software Developer" templates.

### 5 RANDOM Samples

| posting_id | Actual Job Title | Summary Role | Match? |
|------------|------------------|--------------|--------|
| 10945 | Internship - Corporate Advisory Team, mid-market M&A | Operations Manager, VP | ❌ |
| 11153 | KYC Role, NCT | Implementation Specialist | ❌ |
| 11808 | Compliance Officer - AFC & Compliance Testing | COO of Private Customer Bank | ❌ |
| 11471 | Workflow Engineering Chapter Lead | Senior Platform Engineer | ❌ |
| 12007 | Corporate Coverage Intern | Platform Engineer | ❌ |

**Pattern**: Random sample confirms universal contamination.

### 5 Most Duplicated Summaries

| Summary Opening (first 50 chars) | Count |
|----------------------------------|-------|
| "Role: Senior DevOps Engineer, AVP..." | 202 |
| "Role: Backend Developer / Java Developer, AVP..." | 47 |
| "Role: Engineer, Sanctions & Embargo Screening..." | 41 |
| "Role: Architect, AVP..." | 36 |
| "Role: Java Developer - Associate Corporate..." | 32 |

### 5 CORRECT Matches (the 1%)

| posting_id | Job Title | Summary Role | Match? |
|------------|-----------|--------------|--------|
| 10466 | Business Banking Advisor – Branch Banking, AS | Business Banking Advisor – Branch Banking | ✅ |
| 10469 | Associate Engineer | Associate Engineer | ✅ |
| 10771 | Senior DevOps Engineer, AVP | Senior DevOps Engineer, AVP | ✅ |
| 11128 | Backend Developer / Java Developer, AVP | Backend Developer / Java Developer, AVP | ✅ |
| 12147 | Product Manager - Data | Product Manager - Data | ✅ |

**Pattern**: Correct matches are postings that **happen to have** the same title as the contaminating template.

---

## Root Cause Analysis

### Hypothesis 1: Context Window Pollution (LIKELY)

When batch processing, the model retained context from previous postings:
```
Posting 1: DevOps Engineer → Summary: DevOps role
Posting 2: Sales Manager → Summary: DevOps role (WRONG - context bleed)
Posting 3: KYC Analyst → Summary: DevOps role (WRONG - context bleed)
```

### Hypothesis 2: Template Substitution Bug (POSSIBLE)

The `{job_description}` variable may not have been correctly substituted, causing the model to use a cached/default response.

See: `docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md`

### Hypothesis 3: Wrong Posting Data in Prompt (POSSIBLE)

The WaveRunner may have passed the wrong posting's job_description to the model.

---

## Impact Assessment

### Skills Extraction Impact

If summaries are wrong, skill extraction from those summaries is also wrong:
- 10,430 `posting_skills` records exist
- Unknown % are based on hallucinated summaries
- Skills may be for completely different roles

### Entity Registry Impact

Skills extracted from wrong summaries:
- Populated `entities_pending` with wrong skills
- Fed incorrect data into WF3005 classification
- May have created bogus entity_relationships

### User Impact

If job matching uses extracted_summary:
- Candidates matched to wrong jobs
- Skills profiles incorrectly built
- IHL scores meaningless

---

## Recommended Actions

### Immediate (Priority 1)

1. **STOP all summary-dependent workflows** until fixed
2. **Clear and regenerate** all extracted_summary values
3. **Add QA gate** to detect role/title mismatch before saving

### Short-term (Priority 2)

4. **Regenerate posting_skills** from fresh summaries
5. **Clear entities_pending** and rerun WF3005
6. **Add hallucination detection** to workflow before save step

### Long-term (Priority 3)

7. **Single-posting processing** instead of batch (slower but safer)
8. **Multi-model validation** - second model verifies role matches title
9. **Automated regression tests** with known-good postings

---

## QA Check to Add

```python
def check_role_title_match(posting_id: int, conn) -> Dict:
    """
    Verify extracted summary role matches actual job title.
    Returns QA finding if mismatch detected.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_title, 
               SUBSTRING(extracted_summary FROM 'Role:? ?([^\n*]+)') as extracted_role
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    job_title = row['job_title'].lower()
    extracted_role = (row['extracted_role'] or '').lower()
    
    # Check if any significant words from title appear in extracted role
    title_words = set(job_title.split()) - {'the', 'a', 'an', '-', '–'}
    role_words = set(extracted_role.split()) - {'the', 'a', 'an', '-', '–'}
    
    overlap = title_words & role_words
    if len(overlap) < 2:  # Less than 2 words in common
        return {
            'check_type': 'hallucination',
            'severity': 'high',
            'pattern_matched': 'role_title_mismatch',
            'description': f"Summary role '{extracted_role}' doesn't match job title '{job_title}'",
            'evidence': f"Title: {row['job_title']}, Role: {row['extracted_role']}"
        }
    
    return None
```

---

## Conclusion

The summary extraction system has a **catastrophic quality failure**. 99% of summaries describe a different job than the actual posting. This invalidates:

- All downstream skill extraction
- Entity registry classifications  
- Any matching/scoring based on summaries

**Immediate regeneration required before any production use.**

---

## Appendix: Raw Queries Used

```sql
-- Contamination stats
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE extracted_summary LIKE 'Role: Senior DevOps%') as devops,
    COUNT(*) FILTER (WHERE extracted_summary LIKE 'Role: Backend Developer%') as backend,
    COUNT(*) FILTER (WHERE extracted_summary LIKE 'Role: Engineer, Sanctions%') as sanctions
FROM postings;

-- Role match rate
WITH role_extract AS (
    SELECT posting_id, job_title,
           TRIM(SUBSTRING(extracted_summary FROM 'Role:? ?([^\n*]+)')) as extracted_role
    FROM postings WHERE extracted_summary IS NOT NULL
)
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE LOWER(job_title) LIKE '%' || LOWER(SUBSTRING(extracted_role, 1, 15)) || '%') as matches,
    ROUND(100.0 * COUNT(*) FILTER (WHERE LOWER(job_title) LIKE '%' || LOWER(SUBSTRING(extracted_role, 1, 15)) || '%') / COUNT(*), 1) as pct
FROM role_extract;

-- Most common contamination
SELECT LEFT(extracted_summary, 50), COUNT(*) 
FROM postings 
WHERE extracted_summary IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```
