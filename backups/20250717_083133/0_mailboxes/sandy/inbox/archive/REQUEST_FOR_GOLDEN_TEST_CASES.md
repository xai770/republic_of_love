# Request for Golden Test Cases - Content Extraction Specialist v2.0

**To:** Sandy (Business Owner)  
**From:** LLM Factory Engineering Team  
**Date:** 2025-01-26  
**Priority:** High  
**Subject:** Golden Test Cases Required for Content Extraction Specialist v2.0 Validation

## Executive Summary

Following our engineering best practices (Rule #12), we need 5 real-life job description examples to validate the new Content Extraction Specialist v2.0 before delivery. This ensures the specialist meets your exact requirements for skill matching and downstream business processes.

## Request Details

### What We Need:
1. **5 real job descriptions** that you actively use for skill matching/analysis
2. **Expected output format** - specifically how you want skills, requirements, and other data structured
3. **Performance criteria** - what makes a "good" vs "poor" extraction result for your use case

### Why We Need This:
- Validate v2.0 specialist performance on actual business data
- Ensure output format optimizes your downstream processes (skill matching, reporting)
- Meet Deutsche Bank production standards with real-world testing
- Document performance metrics before production deployment

### What You'll Get:
- Validation report showing v2.0 performance on your 5 examples
- Comparison with current v1.0 outputs (if desired)
- Performance metrics and recommendations
- Production-ready specialist with documented test results

## Required Format for Golden Test Cases

Please provide your response as a single JSON file with this exact structure:

```json
{
  "business_owner": "Sandy",
  "specialist_name": "Content Extraction Specialist v2.0",
  "date_requested": "2025-01-26",
  "test_cases": [
    {
      "id": "test_001",
      "name": "Senior Software Engineer",
      "job_description": "PASTE FULL JOB DESCRIPTION TEXT HERE",
      "expected_skills": ["Python", "AWS", "Leadership"],
      "expected_experience_level": "Senior",
      "expected_location": "Remote",
      "notes": "Typical tech role with mixed technical and soft skills"
    },
    {
      "id": "test_002", 
      "name": "Marketing Manager",
      "job_description": "PASTE FULL JOB DESCRIPTION TEXT HERE",
      "expected_skills": ["Digital Marketing", "Analytics", "Team Management"],
      "expected_experience_level": "Mid-level",
      "expected_location": "New York, NY",
      "notes": "Non-tech role to test domain diversity"
    }
    // ... 3 more test cases following same structure
  ],
  "output_requirements": {
    "skill_format": "simple_list",
    "required_fields": ["skills", "experience_level", "location", "job_title"],
    "optional_fields": ["salary_range", "company_size", "industry"],
    "success_criteria": "90%+ skill extraction accuracy, proper categorization"
  },
  "business_context": {
    "primary_use_case": "skill matching for candidate screening",
    "downstream_systems": ["ATS integration", "candidate scoring"],
    "performance_requirements": "process 100+ job descriptions per day"
  }
}
```

## Instructions:
1. **Save this as:** `golden_test_cases_content_extraction_v2.json`
2. **Include 5 diverse test cases** (different industries, roles, complexity)
3. **Use real job descriptions** from your actual business processes
4. **Fill all fields** - this becomes our standard format for all future specialist testing

This standardized format ensures:
- Consistent testing across all specialists
- Easy automation of validation processes  
- Clear success criteria and business context
- Reusable template for future requests

## Timeline:
- **Target delivery:** Within 48 hours of receiving your examples
- **Validation time:** 24 hours for testing and documentation
- **Production deployment:** Upon your approval

## Next Steps:
1. You provide the 5 examples and requirements
2. We run comprehensive testing and validation
3. We deliver the specialist with full documentation and test results
4. You review and approve for production use

Please reply with the examples and requirements when convenient. This validation step ensures we deliver exactly what you need for optimal business performance.

---
**Engineering Team Contact:** Available for clarification or immediate discussion
