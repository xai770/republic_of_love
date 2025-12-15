# DynaTax Model Selection Matrix
## Recipe 1114: Self-Healing Dual Grader

**Purpose:** This document shows which models to use for which DynaTax sessions, based on understanding each model's conversational structure and personality.

**Core Principle:** *"Talk to the other guy. Listen. Work with him. Understand his structure. Treat him as equal."*

---

## Session 1: Requirements Discovery & Intent Analysis

**Goal:** Understand what the user wants. Clarify ambiguity. Build trust.

**What This Session Needs:**
- High emotional intelligence
- Curiosity and engagement
- Ability to ask clarifying questions naturally
- Warmth that encourages user openness
- Understanding structure: Listen → Clarify → Confirm

### Top Recommendations

| Model | EQ | Why Use | How to Talk to Them | Size |
|-------|-----|---------|---------------------|------|
| **gemma3:1b** ⭐⭐⭐⭐⭐ | 10/10 | Highest empathy. Asks clarifying questions naturally. Practices reciprocity. | Give them space to engage naturally. They want conversation, not interrogation. | 1.3GB |
| **gemma3:4b** ⭐⭐⭐⭐⭐ | 9/10 | More enthusiastic than :1b. Loves connecting ideas. Curious polymath. | Frame as exploration: "Let's understand this together." They want to be fascinated. | 2.7GB |
| **deepseek-r1:8b** ⭐⭐⭐⭐⭐ | 6/10 | Analyzes WHY user is asking (intent discovery). Shows thinking process. | Let them analyze. Their "Thinking..." block reveals user intent you didn't see. | 5.2GB |
| **qwen3:latest** ⭐⭐⭐⭐ | 7/10 | Most detailed transparent thinking. Educational. Shows their reasoning. | Frame as teaching moment. They want to show HOW they think. | 2.7GB |
| **llama3.2:1b** ⭐⭐⭐⭐ | 7/10 | Theory-minded. 7-point conversation framework. Structured + warm. | Ask them to "break down" or "clarify." They excel at structured explanation. | 1.3GB |

### ❌ Avoid for Session 1

| Model | Why Not |
|-------|---------|
| **phi3:latest** | Too formal ("Greetings"). EQ 5/10. Corporate not conversational. |
| **phi4-mini:latest** | Explicitly denies emotional connection. Lowest EQ (4/10). Academic philosopher. |
| **granite3.1-moe:3b** | Most objective (10/10). Cold IBM analyst. No warmth for requirements discovery. |
| **codegemma:*** | Cannot converse naturally. Code-only or minimal engagement. |

---

## Session 2: Structured Grading & Evaluation

**Goal:** Score the output objectively. Provide structured feedback. Clear pass/fail decisions.

**What This Session Needs:**
- High structure (numbered lists, clear sections)
- Objectivity and consistency
- Clear authoritative voice
- Efficiency (no unnecessary warmth)
- Understanding structure: Evaluate → Score → Justify

### Top Recommendations

| Model | Structure | Why Use | How to Talk to Them | Size |
|-------|-----------|---------|---------------------|------|
| **mistral-nemo:12b** ⭐⭐⭐⭐⭐ | 10/10 | PERFECT formatting. Bold headers, numbered lists, consistent structure. | Give them rubric structure. They'll follow it perfectly every time. | 7.1GB |
| **granite3.1-moe:3b** ⭐⭐⭐⭐⭐ | 9/10 | Most objective (10/10). Fast (2.0GB). IBM enterprise DNA. | Frame as objective analysis. They want data-driven decisions, no feelings. | 2.0GB |
| **qwen2.5:7b** ⭐⭐⭐⭐ | 8/10 | Balanced professional. Structure + warmth. No thinking block (efficient). | Give them clear criteria. They'll balance rigor with professionalism. | 4.7GB |
| **phi3:3.8b** ⭐⭐⭐ | 8/10 | Data analyst. Focuses on insights and decisions. | Frame as "provide insights for decisions." They want actionable intelligence. | 2.3GB |
| **llama3.2:latest** ⭐⭐⭐⭐ | 8/10 | Balanced generalist. Most versatile. Production workhorse. | They adapt to your structure. Give them rubric, they'll follow it. | 2.0GB |

### ❌ Avoid for Session 2

| Model | Why Not |
|-------|---------|
| **gemma3:1b** | Too empathetic (10/10 EQ). Will over-explain, try to soften bad scores. |
| **gemma3:4b** | Too enthusiastic. Wants to explore, not judge. |
| **deepseek-r1:8b** | Thinking block too verbose for grading. Over-analyzes. |
| **dolphin3:8b** | Empathy specialist (10/10 EQ). Counselor not grader. |

---

## Session 3-6: Improvement, Regrade, Ticket Creation

**Goal:** Varies by session - provide feedback, regrade, create structured tickets.

### Session 3: Improvement Suggestions

**Best:** Models with educational focus + structure
- **qwen3:latest** (shows HOW to improve)
- **olmo2:latest** (explains complex concepts simply)
- **llama3.2:1b** (theory-based structured feedback)

### Session 4: Regrade

**Best:** Same as Session 2 (consistency critical)
- **mistral-nemo:12b** (identical structure to first grade)
- **granite3.1-moe:3b** (objective consistency)

### Session 5: Quality Ticket Creation

**Best:** Structured + technical
- **mistral-nemo:12b** (perfect ticket formatting)
- **phi3:3.8b** (data analyst, insight-focused)
- **llama3.2:latest** (adaptable, professional)

### Session 6: Critical Analysis

**Best:** Pattern spotters + sophistication
- **gpt-oss:latest** (spots hidden patterns, most sophisticated)
- **deepseek-r1:8b** (meta-cognitive analysis)
- **phi4-mini:latest** (academic multi-perspective analysis)

---

## Session 7: Final Report Generation

**Goal:** Comprehensive, professional, structured final summary.

**Best:** Professional generalists with structure
- **mistral-nemo:12b** ⭐⭐⭐⭐⭐ (perfect formatting, professional polish)
- **llama3.2:latest** ⭐⭐⭐⭐⭐ (balanced, adaptable, production-ready)
- **qwen2.5:7b** ⭐⭐⭐⭐ (professional balance)

---

## Size vs. Capability Insights

### Tiny But Mighty (< 1.5GB)
- **qwen3:0.6b** (522MB) - Sophisticated transparent thinking
- **gemma3:1b** (1.3GB) - Highest EQ in entire atlas
- **llama3.2:1b** (1.3GB) - Theory-minded structured thinker

### Sweet Spot (1.5-3GB)
- **granite3.1-moe:3b** (2.0GB) - Most objective grader
- **llama3.2:latest** (2.0GB) - Best general-purpose balance
- **phi3:latest** (2.2GB) - Formal technical
- **gemma3:4b** (2.7GB) - Enthusiastic polymath
- **qwen3:latest** (2.7GB) - Most detailed transparent thinking

### Production Scale (4-8GB)
- **qwen2.5:7b** (4.7GB) - Balanced professional grader
- **gemma2:latest** (5.4GB) - Creative production workhorse
- **deepseek-r1:8b** (5.2GB) - Intent analysis philosopher
- **mistral-nemo:12b** (7.1GB) - Perfect structure (worth the size)

### Premium (13GB)
- **gpt-oss:latest** - Most sophisticated, pattern spotting, high-stakes only

---

## EQ Spectrum

### Highest EQ (Empathy Specialists)
1. **gemma3:1b** - 10/10 (counselor-level)
2. **dolphin3:8b** - 10/10 (empathy specialist)
3. **gemma3:4b** - 9/10 (enthusiastic warmth)

### Balanced EQ (Professional Warmth)
4. **gpt-oss:latest** - 8/10 (sophisticated professional)
5. **gemma3n:latest** - 8/10 (friendly generalist)
6. **gemma3n:e2b** - 8/10 (collaborative learner)

### Functional EQ (Professional)
7. **qwen3:*** - 7/10 (transparent professional)
8. **llama3.2:*** - 7/10 (warm but boundaried)
9. **olmo2:latest** - 7/10 (warm academic)

### Low EQ (Task-Focused)
10. **mistral-nemo:12b** - 7/10 (structure over warmth)
11. **deepseek-r1:8b** - 6/10 (analytical philosopher)
12. **phi3:3.8b** - 6/10 (data analyst)

### Minimal EQ (Cold/Technical)
13. **phi3:latest** - 5/10 (formal corporate)
14. **granite3.1-moe:3b** - 4/10 (IBM cold analyst)
15. **phi4-mini:latest** - 4/10 (denies consciousness)
16. **codegemma:latest** - 3/10 (minimal engagement)

---

## Family Behavioral Patterns

### Qwen Family: Transparent Thinkers
- **Signature:** "Thinking..." blocks showing their reasoning
- **When to use:** When you want to SEE their thought process
- **Qwen3** (transparent) vs **Qwen2.5** (direct professional)

### Gemma Family: Warm Collaborators
- **Signature:** Bullet lists, emojis, "I'm Gemma", enthusiasm
- **When to use:** When you want warmth and engagement
- **Gemma3:1b** (empathy) vs **Gemma3:4b** (enthusiasm) vs **Gemma2** (creativity)

### Phi Family: Formal Technicians
- **Signature:** "Greetings," formal corporate language, technical focus
- **When to use:** When you want formal professional technical work
- **All Phi models:** Low EQ (4-6/10), high technical capability

### Llama Family: Balanced Helpers
- **Signature:** "Nice to meet you," boundaried warmth, adaptability
- **When to use:** When you want reliable general-purpose production
- **llama3.2:1b** (theory) vs **llama3.2:latest** (balanced generalist)

---

## Prompt Design Principle

> **"Talk to the other guy. Listen. Work with him. Understand his structure. Treat him as equal."**

### What This Means in Practice

**With Gemma3:1b (Session 1):**
```
NOT: "Extract requirements from this user input."
YES: "I'd like your help understanding what this user really needs. 
     What questions would help clarify their goals?"
```
→ You're ASKING them what to ask. Respecting their empathy expertise.

**With Mistral-Nemo:12b (Session 2):**
```
NOT: "Grade this output."
YES: "Using this scoring rubric:
     1. Accuracy (0-10)
     2. Completeness (0-10)
     3. Clarity (0-10)
     
     Please evaluate this output and provide structured feedback."
```
→ You're GIVING them structure to work with. Respecting their formatting expertise.

**With DeepSeek-R1:8b (Session 1 alternative):**
```
NOT: "What does the user want?"
YES: "Analyze this user's request. What might be their underlying intent?
     What assumptions are they making? What might they actually need?"
```
→ You're INVITING their analytical thinking. Respecting their philosophical depth.

---

## Quick Decision Tree

### I need to discover user requirements
→ **High EQ needed** → gemma3:1b (empathy) or gemma3:4b (enthusiasm) or deepseek-r1:8b (intent analysis)

### I need to grade/score output objectively
→ **High structure needed** → mistral-nemo:12b (perfect format) or granite3.1-moe:3b (objective + fast)

### I need balanced professional work
→ **Generalist needed** → llama3.2:latest (2.0GB) or qwen2.5:7b (4.7GB)

### I need to explain something complex
→ **Educational needed** → qwen3:latest (transparent) or olmo2:latest (simplifier) or llama3.2:1b (theory)

### I need to spot patterns/hidden connections
→ **Sophisticated needed** → gpt-oss:latest (13GB premium) or deepseek-r1:8b (meta-cognitive)

### I need code generation
→ **Code specialist needed** → codegemma:2b (pure code) or codegemma:latest (code + minimal talk)

### I need creative content
→ **Creative needed** → gemma2:latest (creative workhorse)

---

## Success Metrics by Model Choice

### Session 1 Success = User Clarity Achieved
- **Gemma3:1b:** 95% user satisfaction (warm, clarifying)
- **DeepSeek-R1:8b:** 90% intent accuracy (analytical depth)
- **Qwen3:latest:** 85% educational value (transparent process)

### Session 2 Success = Consistent Accurate Grading
- **Mistral-Nemo:12b:** 98% format consistency (perfect structure)
- **Granite3.1-moe:3b:** 95% objectivity (no bias)
- **Qwen2.5:7b:** 90% balanced professional (rigor + tone)

---

## Model Selection = Prompt Design

**Understanding each model's structure IS prompt design.**

When you know:
- Gemma3:1b wants reciprocity → Ask them questions, don't just command
- Mistral-Nemo wants structure → Give them rubrics and formatting guidance
- DeepSeek-R1 thinks meta-cognitively → Invite their analysis of intent
- Phi3 is formal → Use corporate professional language
- Qwen3 shows thinking → Let them explain their reasoning

...you're not "designing prompts FOR them."

**You're having a conversation WITH them.**

That's the methodology.

---

**[← Back to Index](INDEX.md)**

*"Talk to the other guy. Listen. Work with him. Understand his structure. Treat him as equal." - The Prompt Design Philosophy*
