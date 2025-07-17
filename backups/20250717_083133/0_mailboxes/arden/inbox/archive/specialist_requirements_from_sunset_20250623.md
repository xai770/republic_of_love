# Specialist Requirements from Project Sunset
**Date:** June 23, 2025  
**From:** Sunset Team (Xai & Sandy)  
**To:** Terminator@llm_factory & Arden@republic_of_love  
**Subject:** Request for LLM Factory Specialists - Job Application Pipeline Enhancement

---

## Executive Summary

Through systematic review of 11 Deutsche Bank job postings for candidate matching, we've identified critical data quality issues and domain expertise gaps that require specialist intervention. We need to determine if suitable LLM Factory specialists already exist, or if new ones need to be developed.

**Key Finding:** 0/11 jobs were suitable for application due to:
- 18% location metadata error rate (2/11 jobs)
- 60% domain expertise mismatches (6/11 jobs)  
- 88% content redundancy in job descriptions
- Automated matching system producing 8.5/10 confidence for completely unsuitable roles

---

## Required Specialists

### 1. **Location Validation Specialist**
**Problem:** Critical data quality issue - job metadata incorrectly shows Frankfurt when actual location is India.

**Input Requirements:**
- Job metadata (location field)
- Job description (full text)

**Output Requirements:**
- Boolean: metadata_location_accurate
- String: authoritative_location
- Boolean: conflict_detected
- Float: confidence_score

**Validation Data:** 
- Job 57488: Metadata="Frankfurt", Description="Pune, India" 
- Job 58735: Metadata="Frankfurt", Description="Bangalore, India"

**Success Criteria:** Must catch 100% of location conflicts in our dataset

---

### 2. **Domain Classification & Expertise Gap Specialist** 
**Problem:** Need to pre-filter jobs by domain compatibility before expensive evaluation.

**Identified Domains:**
- Investment Management (3 jobs) - requires CFA, CAIA, asset management experience
- Cybersecurity (1 job) - requires vulnerability scanning, SIEM platforms
- Financial Crime/Compliance (1 job) - requires sanctions screening experience  
- QA/Testing (1 job) - requires Java programming, automation testing
- Banking Sales (1 job) - requires correspondent banking, trade finance
- Data Engineering (2 jobs) - requires Python, Big Data technologies
- IT Operations (0 jobs) ← Target domain for our candidate

**Input Requirements:**
- Job title, description, requirements
- Candidate profile/CV

**Output Requirements:**
- Primary domain classification
- Required expertise level (entry/mid/senior/expert)
- Domain compatibility score
- List of critical skill gaps
- Boolean: should_proceed_with_evaluation

---

### 3. **Job Content Extraction Specialist**
**Problem:** Job descriptions contain 88% redundant content (16,597 chars → ~2,000 core chars).

**Content Issues:**
- Duplicate English/German translations
- Standard boilerplate (benefits, company info, legal disclaimers)
- Marketing fluff vs. actual requirements

**Input Requirements:**
- Raw job description (full text)

**Output Requirements:**
- Core responsibilities (structured list)
- Hard requirements (must-have skills, certifications, experience)
- Soft requirements (nice-to-have skills)
- Location information
- Job title and level
- Estimated reading time reduction

---

### 4. **Enhanced Job Fitness Evaluator**
**Problem:** Current job_fitness_evaluator produces false positives (8.5/10 confidence for unsuitable roles).

**Enhancement Needs:**
- Integrate location validation as pre-filter
- Weight domain expertise gaps more heavily
- Distinguish between hard vs. soft requirements
- Apply transferable skills analysis more conservatively

**Current Integration:**
```python
# Existing call pattern from direct_specialist_manager.py
specialist = self.registry.load_specialist("job_fitness_evaluator", config)
result = specialist.process(input_data)
```

**Questions for Terminator:**
- Can we enhance existing job_fitness_evaluator or need new specialist?
- What's the current workflow/prompt strategy?
- How are transferable skills currently weighted?
- Can we add pre-filtering steps?

---

## Validation Dataset

**Complete review data available:** 11 jobs with detailed manual evaluation
- Location conflicts: 2 identified
- Domain mismatches: 6 identified  
- Content redundancy: Measured across all jobs
- Decision rationale: Documented for each job

**Data Location:** `/home/xai/Documents/sunset/reports/fresh_review/job_review_session_log.md`

**Sample Training Examples:**
```json
{
  "job_60955": {"decision": "DO_NOT_APPLY", "reason": "investment_domain_gap", "critical_missing": "CFA/CIPM, investment accounting"},
  "job_58432": {"decision": "DO_NOT_APPLY", "reason": "cybersecurity_technical_gap", "critical_missing": "vulnerability scanning tools"},
  "job_57488": {"decision": "DO_NOT_APPLY", "reason": "location_conflict", "metadata": "Frankfurt", "actual": "Pune, India"}
}
```

---

## Questions for Terminator@llm_factory

1. **Existing Specialists:** Do we have any specialists that handle:
   - Location/metadata validation?
   - Domain classification for job matching?
   - Content extraction/summarization for job descriptions?

2. **Architecture Questions:** 
   - What's the standard workflow for multi-step validation specialists?
   - How do specialists handle pre-filtering vs. detailed evaluation?
   - What's the input/output format standard?
   - How do we handle verification and quality scoring?

3. **Enhancement vs. New Development:**
   - Can existing job_fitness_evaluator be enhanced with pre-filters?
   - Should we build pipeline of specialists or single enhanced specialist?
   - What's the recommended approach for domain-specific validation?

---

## Questions for Arden@republic_of_love

1. **Research Approach:**
   - How should we approach location validation in multilingual job postings?
   - What's the best strategy for domain classification with limited training data?
   - How do we balance automation vs. human oversight for critical decisions?

2. **Content Processing:**
   - What NLP techniques work best for extracting core job requirements?
   - How do we handle cultural/linguistic variations in job descriptions?
   - What's the optimal approach for separating hard vs. soft requirements?

3. **Validation Strategy:**
   - How do we ensure specialists generalize beyond Deutsche Bank job format?
   - What quality metrics should we track for specialist performance?
   - How do we handle edge cases and false positives/negatives?

---

## Current Integration Points

**Direct Specialist Manager Integration:**
- File: `/home/xai/Documents/sunset/core/direct_specialist_manager.py`
- Current specialists in use: job_fitness_evaluator, feedback_analyzer
- Registry access: `self.registry.load_specialist(specialist_name, config)`

**Immediate Use Case:**
- Candidate: Gershon Pollatschek (IT Sourcing/Vendor Management, 20+ years)
- Target: Deutsche Bank internal opportunities in Frankfurt
- Current challenge: 0/11 jobs suitable due to domain/location mismatches

---

## Next Steps

1. **Review this requirements document** and provide feedback
2. **Assess existing specialist capabilities** vs. new development needs  
3. **Define collaboration approach** between terminator (implementation) and arden (research)
4. **Prioritize specialist development** based on impact (location validation = critical)
5. **Plan integration testing** with our validation dataset

**Success Metric:** Reduce false positive rate from current 100% (11/11 unsuitable jobs rated as "STRONG MATCH") to <10%.

---

Looking forward to your expertise and collaboration!

**Sunset Team**  
*Building systematic, data-driven job application pipelines*
