# AI Decision Framework: Acceptable Failure Modes
## A Practical Approach to Choosing the Right Tool Based on What You Can Live With

### Overview
Instead of classifying problems by type, this framework classifies them by **acceptable failure modes**. The key insight: a 75% extraction accuracy often yields 100% decision accuracy. Missing one requirement rarely changes the go/no-go decision.

---

## Core Principle: Start with "What Can We Live With?"

### The Reality Check
- **Perfect is the enemy of done**
- **75% extraction = 100% decision accuracy** in most cases
- **Over-engineering costs more than occasional misses**
- **Different requirements have different criticality**

---

## Failure Mode Levels

### **Level 1: "Good Enough"**
*When 75% accuracy gives you the right decision*

**Characteristics:**
- Missing some items won't change outcomes
- Speed matters more than completeness
- Volume is high, stakes are low

**Approach:**
- Simple pattern matching
- No validation loops
- Skip edge cases
- Fast and cheap

**Examples:**
```python
# If job needs Python + Django + REST, catching 2/3 still = qualified
requirements = ["Python", "Django", "REST APIs"]
found = ["Python", "Django"]  # Missed REST
decision = "QUALIFIED"  # Still correct!
```

**When to use:**
- Skill matching (nice-to-haves)
- Years of experience (5 vs 6 years rarely matters)
- Soft skills extraction
- Industry buzzwords

### **Level 2: "Catch the Critical"**
*Must-haves need higher accuracy*

**Characteristics:**
- Some requirements are deal-breakers
- Missing these changes the decision
- Worth spending more compute time
- Still don't need perfection

**Approach:**
- Two-tier extraction
- Pattern matching for critical items
- LLM verification only for must-haves
- Ignore nice-to-haves

**Examples:**
```python
def extract_requirements(job_description):
    # Critical patterns get special treatment
    critical = {
        "education": extract_degree_requirements(),  # PhD required?
        "clearance": extract_security_clearance(),  # Secret/Top Secret?
        "location": extract_location_requirements(), # On-site only?
    }
    
    # If low confidence on critical items, verify with LLM
    for key, (value, confidence) in critical.items():
        if confidence < 0.8:
            critical[key] = llm_verify_specific(job_description, key)
    
    # Everything else gets basic extraction
    nice_to_haves = quick_pattern_match(job_description)
    
    return merge(critical, nice_to_haves)
```

**When to use:**
- Educational requirements (PhD, specific certifications)
- Legal requirements (work authorization, licenses)
- Hard location constraints
- Minimum years of experience
- Specific domain expertise

### **Level 3: "Zero Tolerance"**
*Regulatory/legal requirements need certainty*

**Characteristics:**
- Failure has legal/regulatory consequences
- Must be explainable
- Accuracy > Speed
- Audit trail required

**Approach:**
- Multi-stage validation
- Pattern → LLM → Human verification
- Confidence scoring at each stage
- Full documentation

**Examples:**
- Security clearance levels
- Professional licenses (medical, legal)
- Regulatory compliance requirements
- Equal opportunity compliance
- Visa/work authorization status

**Implementation:**
```python
def extract_regulatory_requirements(job_description):
    # Stage 1: Pattern extraction
    patterns = extract_known_regulatory_patterns()
    
    # Stage 2: LLM validation
    llm_findings = llm_extract_regulatory(job_description)
    
    # Stage 3: Reconciliation
    combined = reconcile_findings(patterns, llm_findings)
    
    # Stage 4: Human review for low confidence
    if combined.confidence < 0.95:
        combined = queue_for_human_review(combined)
    
    return combined
```

---

## Implementation Strategy

### **1. Classify Your Requirements**
```python
REQUIREMENT_CRITICALITY = {
    # Level 3: Legal/Regulatory (Zero Tolerance)
    "security_clearance": "critical",
    "work_authorization": "critical",
    "professional_license": "critical",
    
    # Level 2: Deal Breakers (Catch the Critical)
    "degree_required": "important",
    "years_experience_minimum": "important",
    "specific_industry": "important",
    
    # Level 1: Nice to Have (Good Enough)
    "preferred_skills": "optional",
    "soft_skills": "optional",
    "tool_experience": "optional",
}
```

### **2. Route by Criticality, Not Complexity**
```python
def smart_extraction_router(job_description, requirement_type):
    criticality = REQUIREMENT_CRITICALITY.get(requirement_type, "optional")
    
    if criticality == "critical":
        return multi_stage_extraction(job_description, requirement_type)
    elif criticality == "important":
        return hybrid_extraction(job_description, requirement_type)
    else:
        return fast_pattern_match(job_description, requirement_type)
```

### **3. Monitor What Matters**
Track metrics by criticality level:
- **Level 1**: Speed and cost (accuracy less important)
- **Level 2**: Accuracy on critical items only
- **Level 3**: Perfect accuracy and audit trail

---

## Cost-Benefit by Failure Mode

| Failure Mode | Pattern Match | Local LLM | Cloud LLM | Human Review |
|-------------|---------------|-----------|-----------|--------------|
| **Level 1: Good Enough** | ✅ Perfect fit | Overkill | Wasteful | Never |
| **Level 2: Critical Only** | ✅ First pass | ✅ Validation | If needed | Rarely |
| **Level 3: Zero Tolerance** | ✅ Required | ✅ Required | ✅ If needed | ✅ Final check |

### **Cost Implications**
- **Level 1**: ~$0.001 per extraction (patterns only)
- **Level 2**: ~$0.01 per extraction (hybrid approach)
- **Level 3**: ~$0.10-1.00 per extraction (full validation)

---

## Real-World Application

### **Example: Software Engineer Job Posting**

```python
# Input: Job description for Senior Python Developer

# Level 1 Extraction (Good Enough) - 90% of requirements
fast_extract = {
    "languages": ["Python", "JavaScript"],  # Might miss "JS"
    "frameworks": ["Django", "React"],      # Might miss variations
    "tools": ["Git", "Docker"],            # Good enough
    "soft_skills": ["communication"],       # Don't overthink
}

# Level 2 Extraction (Critical) - 10% of requirements
critical_extract = {
    "years_required": 5,                   # Must be accurate
    "degree_required": "Bachelor's CS",    # Deal breaker
    "location": "On-site NYC",            # Critical constraint
}

# Level 3 E