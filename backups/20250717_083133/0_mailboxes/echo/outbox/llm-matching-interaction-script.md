# LLM Interaction Script for Job-CV Matching
## Detailed Prompt-Response Flow with Validation

---

## Overview
This document details the exact LLM interactions needed for matching CV data against job postings, including prompts, expected outputs, validation steps, and error handling.

---

## Phase 1: CV Skill Extraction

### Step 1.1: Raw CV Text → Structured Skills

**Input:**
```
CV_TEXT = """
John Smith
Senior Software Engineer

Experience:
- 8 years developing Python applications for financial services
- Led team of 5 engineers building high-frequency trading systems
- Implemented machine learning models using TensorFlow and scikit-learn
- Architected microservices using Docker and Kubernetes
- Proficient in SQL, PostgreSQL, MongoDB
"""
```

**Prompt to LLM:**
```
Extract technical skills from this CV. For each skill, identify:
1. Skill name (canonical form)
2. Proficiency level (beginner/intermediate/advanced/expert)
3. Years of experience (if mentioned)
4. Context (how it was used)

Return as JSON array. Be conservative - only extract explicitly mentioned skills.

CV Text:
{CV_TEXT}
```

**Expected LLM Output:**
```json
{
  "technical_skills": [
    {"skill": "Python", "level": "expert", "years": 8, "context": "financial applications"},
    {"skill": "TensorFlow", "level": "advanced", "years": null, "context": "machine learning"},
    {"skill": "scikit-learn", "level": "advanced", "years": null, "context": "machine learning"},
    {"skill": "Docker", "level": "advanced", "years": null, "context": "microservices"},
    {"skill": "Kubernetes", "level": "advanced", "years": null, "context": "microservices"},
    {"skill": "SQL", "level": "advanced", "years": null, "context": "general"},
    {"skill": "PostgreSQL", "level": "advanced", "years": null, "context": "databases"},
    {"skill": "MongoDB", "level": "advanced", "years": null, "context": "databases"}
  ]
}
```

**Validation Step:**
```python
def validate_skill_extraction(llm_output, original_cv):
    errors = []
    
    # Check 1: All skills actually appear in CV
    for skill in llm_output["technical_skills"]:
        if skill["skill"].lower() not in original_cv.lower():
            errors.append(f"Hallucinated skill: {skill['skill']}")
    
    # Check 2: No duplicate skills
    skill_names = [s["skill"] for s in llm_output["technical_skills"]]
    if len(skill_names) != len(set(skill_names)):
        errors.append("Duplicate skills detected")
        
    # Check 3: Proficiency levels are valid
    valid_levels = ["beginner", "intermediate", "advanced", "expert"]
    for skill in llm_output["technical_skills"]:
        if skill["level"] not in valid_levels:
            errors.append(f"Invalid level for {skill['skill']}: {skill['level']}")
    
    return errors
```

---

## Phase 2: Skill Normalization

### Step 2.1: Map Extracted Skills to Canonical Forms

**Problem:** CV says "JS", job requires "JavaScript"

**Input:**
```
EXTRACTED_SKILLS = ["Python", "JS", "React.js", "Postgres", "K8s"]
```

**Prompt to LLM:**
```
Normalize these technical skills to canonical forms. Map variations to standard names.

Rules:
- Use full names, not abbreviations (JS → JavaScript)
- Use official product names (Postgres → PostgreSQL)
- Remove version numbers unless critical (Python 3 → Python)
- Keep framework extensions (React.js → React)

Skills to normalize:
{EXTRACTED_SKILLS}

Return as JSON mapping: {"original": "canonical"}
```

**Expected LLM Output:**
```json
{
  "Python": "Python",
  "JS": "JavaScript",
  "React.js": "React",
  "Postgres": "PostgreSQL",
  "K8s": "Kubernetes"
}
```

**Validation Step:**
```python
def validate_normalization(original_skills, normalized_map):
    errors = []
    
    # Check 1: All original skills are mapped
    for skill in original_skills:
        if skill not in normalized_map:
            errors.append(f"Missing normalization for: {skill}")
    
    # Check 2: No information loss (e.g., "Python 3" → "Java")
    suspicious_maps = {
        "Python": ["Java", "JavaScript", "Ruby"],
        "Java": ["JavaScript", "Python", "C#"],
        # Add more confusable pairs
    }
    
    for orig, norm in normalized_map.items():
        if orig in suspicious_maps and norm in suspicious_maps[orig]:
            errors.append(f"Suspicious mapping: {orig} → {norm}")
    
    return errors
```

---

## Phase 3: Semantic Skill Grouping

### Step 3.1: Group Related Skills

**Problem:** "Marketing" skills vs "Campaign Management" requirements

**Input:**
```
CANDIDATE_SKILLS = ["Python", "TensorFlow", "scikit-learn", "SQL", "PostgreSQL"]
JOB_REQUIREMENTS = ["Machine Learning", "Deep Learning", "Python Programming", "Database Management"]
```

**Prompt to LLM:**
```
Group candidate skills with related job requirements. Consider semantic relationships.

Candidate skills:
{CANDIDATE_SKILLS}

Job requirements:
{JOB_REQUIREMENTS}

For each job requirement, list which candidate skills satisfy it.
Return as JSON mapping.
```

**Expected LLM Output:**
```json
{
  "Machine Learning": ["TensorFlow", "scikit-learn", "Python"],
  "Deep Learning": ["TensorFlow"],
  "Python Programming": ["Python"],
  "Database Management": ["SQL", "PostgreSQL"]
}
```

**Validation Step:**
```python
def validate_semantic_grouping(grouping, candidate_skills, job_requirements):
    errors = []
    
    # Check 1: No hallucinated skills
    all_mapped_skills = []
    for req, skills in grouping.items():
        all_mapped_skills.extend(skills)
    
    for skill in all_mapped_skills:
        if skill not in candidate_skills:
            errors.append(f"Hallucinated skill in mapping: {skill}")
    
    # Check 2: Reasonable mappings (use embeddings or rules)
    unreasonable_mappings = {
        "Database Management": ["Python", "TensorFlow"],  # These don't belong
        "Frontend Development": ["SQL", "PostgreSQL"],    # These don't belong
    }
    
    for req, wrong_skills in unreasonable_mappings.items():
        if req in grouping:
            for skill in grouping[req]:
                if skill in wrong_skills:
                    errors.append(f"Unreasonable mapping: {skill} → {req}")
    
    return errors
```

---

## Phase 4: Calculate Match Scores

### Step 4.1: Score Each Dimension

**Input:**
```
JOB_REQUIREMENTS = {
    "technical": [
        {"skill": "Python", "level": "advanced", "criticality": "critical"},
        {"skill": "Machine Learning", "level": "intermediate", "criticality": "important"},
        {"skill": "AWS", "level": "basic", "criticality": "optional"}
    ]
}

CANDIDATE_PROFILE = {
    "technical": [
        {"skill": "Python", "level": "expert"},
        {"skill": "TensorFlow", "level": "advanced"},
        {"skill": "scikit-learn", "level": "advanced"}
    ]
}

SEMANTIC_MAPPINGS = {
    "Machine Learning": ["TensorFlow", "scikit-learn"]
}
```

**Prompt to LLM:**
```
Calculate technical match score between candidate and job requirements.

Scoring rules:
1. Critical requirements (weight 1.0): Must have, major impact if missing
2. Important requirements (weight 0.7): Should have, moderate impact if missing  
3. Optional requirements (weight 0.3): Nice to have, minor impact if missing

Level matching:
- Exact match or higher: 100% score
- One level below: 70% score
- Two levels below: 30% score
- Missing: 0% score

Job requirements:
{JOB_REQUIREMENTS}

Candidate profile:
{CANDIDATE_PROFILE}

Semantic mappings:
{SEMANTIC_MAPPINGS}

Calculate overall technical match percentage and provide breakdown.
```

**Expected LLM Output:**
```json
{
  "overall_technical_match": 78.5,
  "breakdown": [
    {
      "requirement": "Python",
      "criticality": "critical",
      "weight": 1.0,
      "candidate_level": "expert",
      "required_level": "advanced",
      "match_score": 100,
      "weighted_score": 100
    },
    {
      "requirement": "Machine Learning",
      "criticality": "important",
      "weight": 0.7,
      "candidate_skills": ["TensorFlow", "scikit-learn"],
      "match_score": 100,
      "weighted_score": 70
    },
    {
      "requirement": "AWS",
      "criticality": "optional",
      "weight": 0.3,
      "candidate_level": "missing",
      "match_score": 0,
      "weighted_score": 0
    }
  ],
  "calculation": "(100 + 70 + 0) / (100 + 70 + 30) = 85%"
}
```

**Validation Step:**
```python
def validate_match_calculation(llm_output):
    errors = []
    
    # Check 1: Math is correct
    total_weighted = sum(item["weighted_score"] for item in llm_output["breakdown"])
    max_possible = sum(item["weight"] * 100 for item in llm_output["breakdown"])
    calculated_match = (total_weighted / max_possible) * 100
    
    if abs(calculated_match - llm_output["overall_technical_match"]) > 0.1:
        errors.append(f"Math error: {calculated_match} != {llm_output['overall_technical_match']}")
    
    # Check 2: Weights are correct
    weight_map = {"critical": 1.0, "important": 0.7, "optional": 0.3}
    for item in llm_output["breakdown"]:
        expected_weight = weight_map[item["criticality"]]
        if item["weight"] != expected_weight:
            errors.append(f"Wrong weight for {item['requirement']}")
    
    return errors
```

---

## Phase 5: Generate Recommendation

### Step 5.1: Create Application Decision

**Input:**
```
MATCH_SCORES = {
    "technical": 78.5,
    "business": 85.0,
    "soft_skills": 72.0,
    "experience": 90.0,
    "education": 100.0
}

MISSING_CRITICAL = ["AWS Certification"]
STRONG_MATCHES = ["Python expertise", "Banking experience", "Team leadership"]
```

**Prompt to LLM:**
```
Generate application recommendation based on match scores.

Decision rules:
- If ANY critical requirement is missing → NO-GO
- If overall match > 80% → STRONGLY RECOMMEND
- If overall match 60-80% and no critical gaps → RECOMMEND
- If overall match 40-60% → CONSIDER (with caveats)
- If overall match < 40% → NO-GO

Match scores:
{MATCH_SCORES}

Missing critical requirements:
{MISSING_CRITICAL}

Strong matches:
{STRONG_MATCHES}

Generate: decision, rationale, confidence, and improvement suggestions.
```

**Expected LLM Output:**
```json
{
  "decision": "RECOMMEND",
  "rationale": "Strong technical alignment (78.5%) with expert Python skills exceeding requirements. Excellent business domain match (85%) with direct banking experience. The missing AWS certification is marked as optional, not critical. Overall match of 81.1% indicates high compatibility.",
  "confidence": 82,
  "improvement_suggestions": [
    "Consider obtaining AWS certification to strengthen cloud skills",
    "Develop additional soft skills in presentation and communication"
  ],
  "key_strengths": [
    "Python expertise exceeds requirements",
    "Strong banking domain experience", 
    "Proven team leadership capabilities"
  ],
  "risk_factors": [
    "No cloud platform experience",
    "Soft skills score below ideal threshold"
  ]
}
```

**Validation Step:**
```python
def validate_recommendation(llm_output, match_scores, missing_critical):
    errors = []
    
    # Check 1: Decision aligns with rules
    overall_match = sum(match_scores.values()) / len(match_scores)
    
    if missing_critical and llm_output["decision"] != "NO-GO":
        errors.append("Should be NO-GO due to missing critical requirements")
    
    if overall_match > 80 and llm_output["decision"] not in ["STRONGLY RECOMMEND", "RECOMMEND"]:
        errors.append(f"High match {overall_match}% should recommend")
    
    # Check 2: Rationale mentions key facts
    rationale_lower = llm_output["rationale"].lower()
    if "python" not in rationale_lower:
        errors.append("Rationale should mention Python strength")
    
    return errors
```

---

## Error Handling Patterns

### Pattern 1: LLM Hallucination
```python
def handle_hallucination(llm_output, original_data):
    """Remove any data not traceable to source"""
    cleaned_output = {}
    for key, value in llm_output.items():
        if verify_in_source(value, original_data):
            cleaned_output[key] = value
        else:
            log_hallucination(key, value)
    return cleaned_output
```

### Pattern 2: Inconsistent Formatting
```python
def handle_format_errors(llm_output, expected_schema):
    """Retry with stricter prompt if format is wrong"""
    if not matches_schema(llm_output, expected_schema):
        stricter_prompt = original_prompt + "\nMUST return EXACT JSON format:\n" + expected_schema
        return retry_with_prompt(stricter_prompt)
    return llm_output
```

### Pattern 3: Confidence Calibration
```python
def calibrate_confidence(llm_confidence, validation_results):
    """Adjust LLM confidence based on validation"""
    penalty = len(validation_results.errors) * 10
    human_review_threshold = 60
    
    adjusted_confidence = max(0, llm_confidence - penalty)
    
    if adjusted_confidence < human_review_threshold:
        return route_to_human_review()
    
    return adjusted_confidence
```

---

## Complete Flow Example

```python
def match_candidate_to_job(cv_text, job_requirements):
    # Step 1: Extract skills from CV
    cv_skills = extract_skills_with_validation(cv_text)
    
    # Step 2: Normalize skill names
    normalized_skills = normalize_with_validation(cv_skills)
    
    # Step 3: Semantic grouping
    skill_mappings = create_semantic_mappings(normalized_skills, job_requirements)
    
    # Step 4: Calculate match scores
    match_scores = calculate_all_dimensions(normalized_skills, job_requirements, skill_mappings)
    
    # Step 5: Generate recommendation
    recommendation = generate_recommendation_with_validation(match_scores)
    
    # Step 6: Final validation
    if recommendation.confidence < 70:
        return escalate_to_human_review(recommendation)
    
    return recommendation
```

---

## Key Learnings from Location Validation Issues

1. **Be explicit about what to return**: "Find location" vs "Find location and compare to metadata"
2. **Provide examples of edge cases**: "Pune office of Frankfurt-based company"
3. **Build in validation steps**: Never trust LLM output without verification
4. **Use structured prompts**: Clear sections for input, rules, expected output
5. **Test with adversarial examples**: CVs with misleading information

---

## Conclusion

This script provides a detailed, step-by-step approach to job-CV matching with:
- Explicit prompts for each stage
- Expected outputs with exact formatting
- Validation steps to catch errors
- Error handling patterns
- Complete traceability from input to output

The key is breaking down the complex matching task into discrete, validatable steps where each LLM interaction has a specific purpose and clear success criteria.