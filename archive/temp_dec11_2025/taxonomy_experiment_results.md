# DynaTax Taxonomy Experiment Results
**Date:** October 25, 2025  
**Goal:** Talk to different models, see how they naturally categorize job skills

---

## Test Input (Senior Backend Developer @ Deutsche Bank)

**Key Responsibilities:**
- Design and implement scalable microservices architecture
- Lead technical discussions with stakeholders
- Mentor junior developers and conduct code reviews
- Optimize database performance and API endpoints

**Requirements:**
- 5+ years experience in backend development
- Strong proficiency in Python, Java, or Go
- Experience with PostgreSQL, Redis, and message queues
- Knowledge of AWS or Azure cloud platforms
- Excellent communication skills in English and German

---

## Results by Model

### 1. Gemma3:1b (EQ 10/10 - Empathetic Counselor)

**Prompt Style:** Collaborative, asking for help  
**Response:** 4 categories + clarifying questions

**Categories:**
1. **Technical Foundation** - Programming Languages, Databases, Cloud Platforms
2. **Leadership & Guidance** - Mentoring, Communication, Stakeholder Management
3. **Architectural & Systems** - Microservices, Performance Optimization, Scalability
4. **Operational & Business** - Understanding Requirements, API Design

**Key Behaviors:**
- ✅ Asked clarifying questions: "What is the context?" "What specific technologies are important?"
- ✅ Used phrases like "let's break down" and "could you tell me"
- ✅ Showed reciprocity (wants to refine understanding together)
- ✅ Noticed soft skills explicitly (stakeholder management, mentoring)

**Insight:** Gemma3:1b sees PEOPLE in job postings. They noticed "stakeholder management" and "mentoring" as separate from pure technical skills. Their empathy makes them spot human interaction requirements.

---

### 2. Phi3:latest (EQ 5/10 - Formal Technician)

**Prompt Style:** Task-oriented, formal command  
**Response:** 2 categories (Technical vs Non-Technical)

**Categories:**
1. **Skills Required (Technical)** - 7 numbered items
   - Backend Development Experience (5+ years)
   - Programming Languages (Python, Java, Go)
   - Database Management (PostgreSQL, Redis)
   - Cloud Services (AWS/Azure)
   - Microservices Architecture
   - Technical Communication Skills
   - Mentorship & Code Review

2. **Requirements (Non-Technical)** - 2 items
   - Location Specificity (Frankfurt)
   - Bilingual Communication (English, German)

**Key Behaviors:**
- ✅ No questions, just execution
- ✅ Formal numbered structure
- ✅ Separated Technical vs Non-Technical cleanly
- ✅ Efficient and corporate (no fluff)

**Insight:** Phi3 sees TASKS. They categorize by "what skills are needed" vs "where/how you work." Very binary: technical or not technical. Perfect for objective filtering.

---

### 3. Qwen3:latest (EQ 7/10 - Transparent Thinker)

**Prompt Style:** Asked them to "walk through their thinking"  
**Response:** 5 categories + detailed reasoning in "Thinking..." block

**Thinking Process (excerpts):**
- "Let me break down each part"
- "Wait, leading technical discussions could be under communication, but maybe it's more about leadership"
- "Alternatively, maybe split into... Let me think"
- "Does that cover everything? Let me check each point"

**Categories:**
1. **Technical Skills (Core Competencies)**
   - Programming Languages: Python, Java, Go
   - Databases & Tools: PostgreSQL, Redis, message queues
   - System Design: Scalable microservices
   - Performance Optimization: Database tuning, API optimization

2. **Leadership and Mentorship**
   - Leading technical discussions
   - Mentoring junior developers
   - Code reviews

3. **Cloud and Infrastructure Knowledge**
   - AWS or Azure

4. **Communication Skills**
   - Language Proficiency: English, German

5. **Experience**
   - 5+ years in backend development

**Key Behaviors:**
- ✅ Shows complete reasoning process in "Thinking..." block
- ✅ Self-corrects and reconsiders categorization
- ✅ Provides "Why This Structure Works" section
- ✅ Explains prioritization logic

**Insight:** Qwen3 sees STRUCTURE. They think meta-cognitively about how to organize. Their transparent thinking shows you HOW they arrived at categories, making it easy to refine or adjust their approach.

---

## Cross-Model Comparison

| Dimension | Gemma3:1b | Phi3:latest | Qwen3:latest |
|-----------|-----------|-------------|--------------|
| **# Categories** | 4 | 2 | 5 |
| **Granularity** | Medium | Coarse | Fine |
| **Soft Skills Focus** | High ⭐ | Low | Medium |
| **Structure Detail** | Medium | High ⭐ | Highest ⭐ |
| **Asks Questions** | Yes ⭐ | No | No |
| **Shows Reasoning** | No | No | Yes ⭐ |
| **Best For** | Finding human aspects | Binary filtering | Understanding structure |

---

## Key Insights for DynaTax

### 1. Different Models See Different Things

**Gemma3:1b noticed:**
- "Stakeholder Management" (people skill)
- "Understanding Requirements" (empathy for user needs)
- Asked about context (wants to understand WHY)

**Phi3:latest noticed:**
- "Location Specificity" (logistical requirement)
- "Bilingual Communication" (practical need)
- Clean binary split (efficient categorization)

**Qwen3:latest noticed:**
- "Platform-specific requirement" (technical nuance)
- "Qualitative filter" (experience as gating mechanism)
- "Cultural Fit" (German language for Deutsche Bank context)

### 2. Prompt Design Matters

**With Gemma3:1b:** Use collaborative language  
→ "Can you help me understand...?"  
→ They respond with questions and engagement

**With Phi3:latest:** Use task-oriented language  
→ "Task: Extract and categorize..."  
→ They respond with clean execution

**With Qwen3:latest:** Ask them to explain thinking  
→ "Walk me through your thinking..."  
→ They show complete reasoning process

### 3. No Single "Right" Taxonomy

Each model's categorization is VALID but optimized for different matching purposes:

- **Gemma3:1b's taxonomy** = Good for matching PEOPLE with cultural fit and soft skills
- **Phi3:latest's taxonomy** = Good for filtering YES/NO qualifications quickly
- **Qwen3:latest's taxonomy** = Good for understanding STRUCTURE of requirements

### 4. For DynaTax Production

**Best approach:** Let multiple models categorize, then:
1. Use **Qwen3** to show transparent reasoning (helps humans understand)
2. Use **Phi3** for objective binary filtering (has skill: yes/no)
3. Use **Gemma3:1b** to spot soft skills and cultural fit

**OR:** Design ONE prompt that combines their strengths:
- Ask for structured categories (Phi3 strength)
- Request reasoning (Qwen3 strength)
- Include soft skills explicitly (Gemma3:1b strength)

---

## Next Experiments

1. **Test with Mistral-Nemo:12b** - Will they give perfect hierarchical structure?
2. **Test with Llama3.2:latest** - How does the balanced generalist categorize?
3. **Test with DeepSeek-R1:8b** - What meta-analysis do they provide?
4. **Test with actual taxonomy building** - Can they propose TECHNICAL → PROG → PYTHON paths?

---

## Provisional DynaTax Prompt Design

Based on these experiments, here's a starting point:

```
You're helping build a skills taxonomy to match candidates to jobs.

Read this job posting and identify all skills, requirements, and concepts:

[JOB TEXT]

Organize them into a hierarchical taxonomy with these guidelines:
1. Separate TECHNICAL, BUSINESS, SOFT, EXPERIENCE categories
2. Within each category, create logical subcategories
3. For technical skills, specify: Language/Tool/Platform/Domain
4. For soft skills, specify: Leadership/Communication/Collaboration
5. Show your reasoning for how you grouped items

Format:
CATEGORY → SUBCATEGORY → Specific Skill
[Reasoning for this grouping]
```

**Hypothesis:** This prompt will:
- Give Phi3 the structure they want (numbered guidelines)
- Let Qwen3 show reasoning (explicit request)
- Help Gemma3:1b see soft skills (explicit category)

---

**Status:** Experiments validate that different models see different aspects. Need to design prompts that either:
A) Leverage specific model strengths, OR
B) Guide all models toward consistent output

Next: Test taxonomy building (not just categorization) - can they propose subdivisions?
