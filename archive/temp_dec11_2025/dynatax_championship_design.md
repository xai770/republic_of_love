# DynaTax Skills Extraction - Championship Test Design
**Date:** October 25, 2025  
**Goal:** Find the best model for extracting and categorizing job skills

---

## Models Tested (Conversation Phase)

### 1. Gemma3:1b (EQ 10/10 - Empathetic Counselor)
**Approach:** Conversational, collaborative  
**Result:** ❌ Over-engineered, added complexity, hard to constrain  
**Score:** 3/5

**What they did well:**
- Engaged collaboratively
- Asked clarifying questions
- Learned through dialogue

**What didn't work:**
- Kept adding features (confidence levels, weighting, heatmaps)
- Hard to stay within scope
- Verbose responses

**Lesson:** High-EQ models need TIGHT constraints upfront

---

### 2. Phi3:latest (EQ 5/10 - Formal Technician)
**Approach:** Task-oriented command  
**Result:** ✅ PERFECT execution once format specified  
**Score:** 5/5

**What they did:**
```
TECHNICAL/WEB_FUNDAMENTALS/HTML
TECHNICAL/WEB_FUNDAMENTALS/CSS
TECHNICAL/PROGRAMMING/JavaScript
TECHNICAL/FRAMEWORK/React
TECHNICAL/FRAMEWORK/Angular
TECHNICAL/VERSION_CONTROL/Git
TECHNICAL/API/RESTful
SOFT/PROBLEM_SOLVING
```

**Lesson:** Low-EQ formal models EXCEL at format-following when given exact specs

---

### 3. Qwen3:latest (EQ 7/10 - Transparent Thinker)
**Approach:** Asked to show thinking process  
**Result:** ⏰ TIMEOUT (probably huge thinking block)  
**Score:** N/A

**Lesson:** Their "Thinking..." blocks are valuable but may be too verbose for production speed

---

### 4. Mistral-Nemo:12b (Structure 10/10)
**Approach:** Simple task specification  
**Result:** ✅ PERFECT structure BUT over-detailed  
**Score:** 4/5

**What they did:**
```
Frontend Development
  - Core Languages
    - HTML
    - CSS
      - Responsive Design
      - Frameworks/Libraries (e.g., Bootstrap, SASS)
    - JavaScript
      - ES6+
      - DOM Manipulation
      - Asynchronous Programming
  - JavaScript Frameworks/Libraries
    - React
      - Components
      - Context API & Hooks
      - State Management (Redux, MobX)
    - Angular
      - TypeScript
      - Components & Modules
      - Routing & Services
```

**Lesson:** They show IDEAL structure but extract MORE than what's in posting (anticipated sub-skills)

---

### 5. Llama3.2:latest (Balanced Generalist)
**Approach:** Friendly but clear  
**Result:** ✅ Clean, simple, appropriate depth  
**Score:** 5/5

**What they did:**
```
* Programming Languages
 * HTML
 * CSS
 * JavaScript
* Web Frameworks and Libraries
 * React
 * Angular
* Version Control Systems
 * Git
* API Development
 * RESTful APIs
* Problem-Solving Skills
```

**Lesson:** Balanced model gives practical output - not too simple, not too complex

---

## Model-Specific Prompt Design

### For Phi3:latest (WINNER Candidate #1)

```
+++DYNATAX SKILLS EXTRACTION+++

Task: Extract skills from job posting and categorize using hierarchical paths.

Input: [JOB_POSTING_TEXT]

Output format (use EXACTLY):
+++OUTPUT START+++
TECHNICAL/WEB_FUNDAMENTALS/HTML
TECHNICAL/WEB_FUNDAMENTALS/CSS
TECHNICAL/PROGRAMMING/JavaScript
TECHNICAL/FRAMEWORK/React
TECHNICAL/FRAMEWORK/Angular
TECHNICAL/VERSION_CONTROL/Git
TECHNICAL/API/RESTful
SOFT/PROBLEM_SOLVING
+++OUTPUT END+++

Rules:
1. Extract ONLY skills explicitly mentioned
2. Use path format: CATEGORY/SUBCATEGORY/TERM
3. One skill per line
4. No elaboration

Execute.
```

**Why this works for Phi3:**
- Clear task specification
- Exact format provided
- No ambiguity
- Formal command ("Execute")

---

### For Llama3.2:latest (WINNER Candidate #2)

```
+++DYNATAX SKILLS EXTRACTION+++

Hey! I need help organizing skills from this job posting into a hierarchy for matching.

Job posting:
[JOB_POSTING_TEXT]

Please categorize each skill using this format:
CATEGORY/SUBCATEGORY/SKILL_NAME

For example:
- HTML → TECHNICAL/WEB_FUNDAMENTALS/HTML
- React → TECHNICAL/FRAMEWORK/React
- Problem-solving → SOFT/PROBLEM_SOLVING

Output format:
+++OUTPUT START+++
[your categorizations here, one per line]
+++OUTPUT END+++

Thanks!
```

**Why this works for Llama3.2:**
- Friendly tone (they respond to warmth)
- Clear example provided
- Simple instructions
- Balanced formality

---

### For Mistral-Nemo:12b (Alternate)

```
+++DYNATAX SKILLS EXTRACTION+++

Task: Categorize skills from job posting.

Input: [JOB_POSTING_TEXT]

Output: Hierarchical skill paths

Format: CATEGORY/SUBCATEGORY/TERM

Constraint: Extract ONLY skills explicitly mentioned (do not infer sub-skills)

Provide structured output:
+++OUTPUT START+++
[skill paths]
+++OUTPUT END+++
```

**Why this works for Mistral-Nemo:**
- Structured task
- Explicit constraint (prevents over-elaboration)
- Clear format specification

---

## Championship Test Design

### Test Dataset
Use 10 diverse job postings:
1. Frontend Developer (web tech heavy)
2. Backend Developer (server/database focus)
3. Data Analyst (data tools)
4. DevOps Engineer (infrastructure)
5. Full Stack Developer (mixed)
6. Mobile Developer (platform-specific)
7. ML Engineer (AI/ML tools)
8. QA Engineer (testing focus)
9. Security Analyst (security tools)
10. Technical Writer (documentation tools)

### Success Metrics

**Primary (Must Have):**
1. **Format Compliance** - Does output match +++OUTPUT START/END+++ format?
2. **Accuracy** - Are all skills from posting extracted?
3. **Categorization Logic** - Are paths sensible? (HTML under WEB not DATABASE)
4. **Completeness** - No missed skills?

**Secondary (Nice to Have):**
5. **Speed** - How fast? (measured in seconds)
6. **Consistency** - Same skill always gets same path across postings?
7. **Handling Ambiguity** - How do they deal with unclear terms?

### Scoring System

Each job posting graded:
- Format: 10 points (binary: correct format or not)
- Accuracy: 30 points (% of skills correctly extracted)
- Categorization: 30 points (% of paths that make sense)
- Completeness: 20 points (% of skills not missed)
- Speed bonus: 10 points (fastest gets 10, others proportional)

**Total: 100 points per posting × 10 postings = 1000 points max**

---

## Hypothesis

### Expected Winner: Phi3:latest
**Reasoning:**
- Follows format perfectly when specified
- No elaboration (efficient)
- Low EQ = doesn't add opinions
- Executes task as commanded

### Expected Runner-Up: Llama3.2:latest
**Reasoning:**
- Balanced output (not too simple/complex)
- Production-ready (proven in Recipe 1115)
- Friendly compliance (follows instructions nicely)
- 2.0GB (efficient size)

### Why Others Won't Win:

**Gemma3:1b:** Too helpful, adds complexity, hard to constrain  
**Qwen3:latest:** Timeouts, verbose thinking blocks slow  
**Mistral-Nemo:12b:** Over-elaborates, extracts more than asked  

---

## Next Steps

1. **Create Recipe 1120:** DynaTax Skills Championship
   - 3 sessions: Phi3, Llama3.2, Mistral-Nemo
   - Same 10 job postings as variations
   - Run all, compare results

2. **Scoring Script:** Auto-calculate metrics
   - Parse +++OUTPUT+++ blocks
   - Check format compliance
   - Validate categorization logic
   - Measure speed

3. **Human Validation:** xai reviews edge cases
   - Ambiguous terms
   - Novel skills (GraphQL, Deno, etc.)
   - Multi-category skills

4. **Declare Champion:** Best overall score wins

---

## Production Integration Plan

Once winner declared:

1. **Create canonical:** `dynatax_skills_extractor`
2. **Add to Recipe 1117:** Replace Session 1
3. **Test on 50 job postings:** Build initial dictionary
4. **Measure hit rate:** Track KNOWN vs UNKNOWN ratio
5. **Iterate:** Refine prompt based on failure patterns

---

**Ready to build Recipe 1120 and run the championship?** 🏆
