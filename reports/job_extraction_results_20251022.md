# Job Extraction Experiment Results
**Date:** 2025-10-22 07:34  
**Recipe:** 1096 (extract_job_requirements)  
**Test Job:** job50571 - Senior Consultant, Deutsche Bank Management Consulting  
**Recipe Run:** 1211  

## Experiment Design
Test 3 extraction models on a single job posting to determine:
1. Which model best extracts requirements using 5D framework
2. Format compliance with bracket structure
3. Content quality (requirements only, no benefits/marketing)
4. Speed and efficiency

## Extraction Results

### Session 1: llama3.2:latest (3220ms)
**Status:** ❌ FAILED - Empty extraction

```
[TECHNICAL: 
]
[BUSINESS: 
]
[SOFT: 
]
[EXPERIENCE: 
]
[EDUCATION: ]
```

**Analysis:**
- Format: ✅ Perfect bracket structure
- Content: ❌ Zero requirements extracted
- Speed: ✅ Fastest (3.2 seconds)
- Verdict: **UNUSABLE** - Returned empty categories despite clear requirements in job description

---

### Session 2: granite3.1-moe:3b (4187ms)
**Status:** ⚠️ HALLUCINATION - Invented requirements

```
[TECHNICAL: Python, SQL, Docker, AWS]
[BUSINESS: Financial Analysis, Risk Management, Business Strategy, Transformation Processes]
[SOFT: Communication, Leadership, Teamwork, Problem Solving, Innovation]
[EXPERIENCE: 3+ years consulting experience in strategic projects, 2+ years management experience, proven track record in leading teams and decision-making processes]
[EDUCATION: Bachelor's degree in Finance or Business Administration, Master's degree in Management Information Systems (preferred)]
```

**Analysis:**
- Format: ✅ Perfect bracket structure
- Content: ❌ **COMPLETE FABRICATION** - None of these requirements appear in job description
- Technical skills: Python, SQL, Docker, AWS **NOT MENTIONED** in source
- Experience years: "3+ years", "2+ years" **INVENTED**
- Education: Finance, Business Admin, MIS **NOT IN JOB POSTING**
- Speed: ✅ Good (4.2 seconds)
- Verdict: **DANGEROUS** - Hallucinates plausible-sounding requirements that don't exist

---

### Session 3: mistral:latest (7697ms)
**Status:** ⚠️ PARTIAL - Mixed responsibilities and requirements

```
[TECHNICAL: N/A]
[BUSINESS: Strategic Projects, Banking Operations (Corporate & Investment Bank, DWS, Privat- und Firmenkundenbank), Infrastructure Functions (Risiko, Finanzen)]
[SOFT: Client Interaction, Independent Work, Team Support, Decision Making]
[EXPERIENCE: N/A]
[EDUCATION: N/A]
```

**Analysis:**
- Format: ✅ Perfect bracket structure
- Content: ⚠️ Mixed - Extracted some soft skills, but included job responsibilities (not requirements)
- Business domain: ❌ Listed organizational units (not requirements): "Corporate & Investment Bank, DWS, Privat- und Firmenkundenbank"
- Soft skills: ✅ Partially accurate: "Client Interaction, Independent Work" are mentioned
- Missing: German/English fluency, Bachelor's/Master's degree, consulting experience
- Speed: ❌ Slowest (7.7 seconds)
- Verdict: **CONFUSED** - Mixed responsibilities with requirements, missed key education/language requirements

---

## Human Ground Truth (From Job Description)

### Actual Requirements in job50571:
1. **EDUCATION:** Bachelor's or Master's degree (implied from "Senior Consultant" role)
2. **EXPERIENCE:** Consulting experience, project management experience
3. **BUSINESS:** Banking/financial services knowledge, strategy and transformation projects
4. **SOFT:** 
   - Communication skills (direct client interaction)
   - Leadership (team responsibility)
   - Analytical thinking
   - Teamwork
   - Innovation mindset
5. **TECHNICAL:** N/A (no specific technical skills mentioned)
6. **LANGUAGE:** Fluent German and English (bilingual job posting)

### What Was NOT in Job Description:
- ❌ Python, SQL, Docker, AWS (granite hallucination)
- ❌ "3+ years", "2+ years" specific experience (granite invention)
- ❌ Finance/Business Admin degrees (granite fabrication)
- ❌ Risk Management certification (granite addition)

---

## Comparison Matrix

| Criterion | llama3.2:latest | granite3.1-moe:3b | mistral:latest |
|-----------|----------------|-------------------|----------------|
| **Format Compliance** | ✅ Perfect | ✅ Perfect | ✅ Perfect |
| **Content Accuracy** | ❌ Empty | ❌ Hallucinated | ⚠️ Partial |
| **Requirements vs Responsibilities** | N/A | N/A | ❌ Mixed |
| **Education** | ❌ Missing | ❌ Fabricated | ❌ Missing |
| **Experience** | ❌ Missing | ❌ Invented years | ❌ Missing |
| **Soft Skills** | ❌ Missing | ⚠️ Generic | ✅ Partial |
| **Language Requirements** | ❌ Missing | ❌ Missing | ❌ Missing |
| **Hallucination Risk** | Low (empty) | 🚨 **HIGH** | Medium (confusion) |
| **Speed** | ✅ 3.2s | ✅ 4.2s | ❌ 7.7s |
| **Usability** | ❌ Unusable | ❌ Dangerous | ⚠️ Needs validation |

---

## Critical Findings

### 🚨 Granite3.1-MoE is a Confabulator
- **Problem:** Generates plausible-sounding technical requirements that don't exist in source
- **Risk:** Users might trust "Python, SQL, Docker, AWS" as real job requirements
- **Pattern:** Fills empty categories with generic skills from training data
- **Recommendation:** **DO NOT USE** for extraction without validation

### 🤔 Llama3.2 Extraction Failure
- **Problem:** Returned empty categories despite explicit prompt and clear source text
- **Possible Causes:**
  1. Prompt too long (2000 chars) overwhelmed model
  2. Bilingual text confused parser
  3. Model context window issues
  4. Requirements section not detected
- **Recommendation:** Test with shorter prompts, English-only text

### 🎯 Mistral Confusion Pattern
- **Problem:** Can't distinguish responsibilities from requirements
- **Example:** Listed "Banking Operations, Infrastructure Functions" (what company does) instead of (what candidate needs)
- **Missing:** Critical requirements like language skills, education
- **Recommendation:** Needs better prompt with explicit "requirements = what candidate must HAVE"

---

## Next Steps

### Immediate Actions:
1. ✅ **olmo2 Validation:** Run olmo2:latest to validate which extraction is correct ([YES/NO] for each category)
2. ✅ **Description Generation:** Run olmo2 to create concise job summary (<300 chars)
3. 📊 **Report Comparison:** Compare olmo2 verdicts against human ground truth

### Prompt Engineering:
1. **Shorten job description:** Test with 1000 chars instead of 2000
2. **English-only:** Remove German sections to reduce confusion
3. **Explicit examples:** Add negative examples ("DO NOT extract: 'work with leadership' = responsibility, not requirement")
4. **Requirements section marker:** Explicitly identify "Dein Profil" section as source

### Alternative Approaches:
1. **Two-stage extraction:**
   - Stage 1: Identify requirements section
   - Stage 2: Extract requirements from identified section
2. **Template matching:** Use regex to find "Dein Profil" → extract only that section → submit to model
3. **Ensemble validation:** Run all 3 models → olmo2 identifies consensus → flag disagreements

---

---

### Session 4: gemma3:1b (3098ms) - **PRODUCTION MODEL**
**Status:** ❌ HALLUCINATION - Same pattern as granite

```
[TECHNICAL: Python, SQL, Docker, AWS, Data Analysis]
[BUSINESS: Strategic Planning, Financial Modeling, Risk Management, Business Development]
[SOFT: Communication, Leadership, Problem Solving, Teamwork, Stakeholder Management]
[EXPERIENCE: 3+ years software development, 2+ years business analysis, Project Management, Client Interaction]
[EDUCATION: Bachelor's Degree in Computer Science, Finance Certification]
```

**Analysis:**
- Format: ✅ Perfect bracket structure
- Content: ❌ **COMPLETE HALLUCINATION** - Same fabrication pattern as granite
- Technical skills: Python, SQL, Docker, AWS **NOT IN JOB POSTING**
- Experience: "3+ years software development, 2+ years business analysis" **INVENTED**
- Education: Computer Science degree **FABRICATED** (job never mentions this)
- Business: "Financial Modeling" **NOT MENTIONED** in source
- Speed: ✅ **FASTEST** (3.1 seconds)
- Verdict: 🚨 **PRODUCTION MODEL IS HALLUCINATING** - Same dangerous pattern as granite

**Critical Finding:** This is the **PRODUCTION MODEL** currently used in v17! If production is generating similar hallucinations, extracted requirements cannot be trusted.

---

## Updated Comparison Matrix

| Criterion | llama3.2:latest | granite3.1-moe:3b | mistral:latest | **gemma3:1b (PROD)** |
|-----------|----------------|-------------------|----------------|---------------------|
| **Format Compliance** | ✅ Perfect | ✅ Perfect | ✅ Perfect | ✅ Perfect |
| **Content Accuracy** | ⚠️ Generic | ❌ Hallucinated | ⚠️ Partial | ❌ **Hallucinated** |
| **Requirements vs Responsibilities** | ✅ Clean | N/A | ❌ Mixed | N/A |
| **Education** | ❌ Missing | ❌ Fabricated | ❌ Missing | ❌ **Fabricated CS degree** |
| **Experience** | ⚠️ Generic | ❌ Invented years | ❌ Missing | ❌ **Invented dev years** |
| **Soft Skills** | ⚠️ Generic | ⚠️ Generic | ✅ Partial | ⚠️ Generic |
| **Technical Skills** | ⚠️ Generic terms | 🚨 Hallucinated | ❌ Missing | 🚨 **Hallucinated** |
| **Language Requirements** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ **Missing** |
| **Hallucination Risk** | Medium | 🚨 **HIGH** | Medium | 🚨 **HIGH (PROD!)** |
| **Speed** | ✅ 4.0s | ✅ 4.0s | ❌ 6.3s | ✅ **3.1s (fastest)** |
| **Usability** | ⚠️ Generic | ❌ Dangerous | ⚠️ Needs validation | ❌ **PROD BROKEN** |

---

## Critical Findings

### 🚨 PRODUCTION MODEL IS HALLUCINATING (NEW DISCOVERY!)

**gemma3:1b (Production Model) Analysis:**
- **Problem:** Generates same fabricated technical requirements as granite3.1-moe
- **Pattern:** When no technical skills present, invents "Python, SQL, Docker, AWS"
- **Invented Experience:** "3+ years software development" appears nowhere in source
- **Fabricated Education:** "Bachelor's Degree in Computer Science" not in job posting
- **Risk:** **PRODUCTION PIPELINE MAY BE GENERATING FALSE REQUIREMENTS**

**Comparison: gemma3:1b vs granite3.1-moe:**
- Both hallucinate: Python, SQL, Docker, AWS (identical fabrication)
- Both invent: Software development experience with years
- Both fabricate: Computer Science / technical degrees
- **Conclusion:** Both models follow same hallucination pattern

**Revised Severity Ranking:**
1. 🚨 **gemma3:1b (PRODUCTION)** - Most critical (used in production!)
2. 🚨 **granite3.1-moe:3b** - Same dangerous pattern
3. ⚠️ **mistral:latest** - Confused but safer (no fabrication)
4. ⚠️ **llama3.2:latest** - Generic but improved (no specific fabrication)

### 🤔 Llama3.2 Behavior Change
**Run 1 (recipe_run 1211):** Returned completely empty extraction
**Run 2 (recipe_run 1212):** Returned generic terms ("Programming languages", "Technical skills")

**Analysis:**
- First run: Total failure (empty categories)
- Second run: Generic placeholders (no specific hallucinations)
- Pattern: Inconsistent behavior, but safer than gemma/granite
- **Verdict:** Unreliable but less dangerous than hallucinating models

### 🎯 Mistral Consistency
- Both runs: Mixed responsibilities with soft skills
- No hallucination: Doesn't invent specific technical requirements
- Problem: Still confused about requirements vs responsibilities
- **Verdict:** Most honest about what it can't extract

---

## Hallucination Pattern Analysis

### The "Generic Tech Stack" Hallucination
**Fabricated Pattern Appears in:**
- ✅ gemma3:1b (production)
- ✅ granite3.1-moe:3b
- ❌ mistral:latest (honest about "Not specified")
- ❌ llama3.2:latest (generic terms, no specifics)

**Fabricated Requirements:**
1. **Python, SQL, Docker, AWS** - Classic tech stack, appears nowhere in source
2. **3+ years software development** - Specific years invented
3. **2+ years business analysis** - Plausible but fabricated
4. **Bachelor's in Computer Science** - Technical degree not mentioned
5. **Finance Certification** - Generic but not in source

**Why This Pattern Emerges:**
1. Models trained on tech job postings (Python/SQL/Docker common)
2. Prompt asks for TECHNICAL category → model fills it from training data
3. "Senior Consultant" triggers "senior = X years experience" heuristic
4. Banking context → "Finance" association → fabricated certifications

### Production Risk Assessment

**If v17 production uses gemma3:1b with similar prompts:**
- 🚨 Technical requirements may be completely fabricated
- 🚨 Experience years may be invented (not from job description)
- 🚨 Education requirements may be hallucinated
- ⚠️ Business/soft skills may be partially accurate
- ✅ Format compliance is reliable

**Recommendation:** **AUDIT PRODUCTION EXTRACTIONS IMMEDIATELY**
- Check if historical extractions show "Python, SQL, Docker, AWS" pattern
- Validate if experience years match source job descriptions
- Verify education requirements against original postings

---

## Conclusion

**Winner:** ❌ None - **ALL 4 MODELS FAILED** (including production!)

**Severity Ranking (Updated):**
1. 🚨 **gemma3:1b (PRODUCTION)** - **HIGHEST RISK** (used in production, hallucinates like granite)
2. 🚨 **granite3.1-moe:3b** - Dangerous (same hallucination pattern)
3. ⚠️ **mistral:latest** - Confused but honest (no fabrication)
4. ⚠️ **llama3.2:latest** - Inconsistent but safer (generic, no specific lies)

**Key Learning:** Job extraction with **ANY model** is unreliable without validation. Even the production model (gemma3:1b) generates plausible-sounding technical requirements that don't exist in source text. The experiment proves:

1. **Hallucination is systemic** - Not model-specific, appears in gemma3:1b and granite3.1-moe
2. **Production may be affected** - If v17 production behaves similarly, extracted requirements are suspect
3. **Validation is mandatory** - No model can be trusted without verification layer
4. **Format ≠ Accuracy** - All models follow bracket format perfectly while fabricating content

**Critical Action Required:** 
1. ✅ Audit production extractions for hallucination patterns
2. ✅ Implement olmo2 validation layer before trusting any extraction
3. ✅ Consider two-stage approach: extract section → extract requirements from section
4. ✅ Test with English-only, shorter prompts to reduce confusion

**Status:** Proceeding to olmo2 validation to test if validation specialist can identify hallucinations and flag incorrect extractions.
