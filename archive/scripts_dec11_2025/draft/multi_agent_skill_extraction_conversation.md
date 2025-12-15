# Multi-Agent Skill Extraction - Scripted Conversation

**Purpose:** Extract comprehensive skills from a 30-year career profile  
**Method:** Extract → Review → Merge (like WF3001's summary → grade pattern)  
**Test with:** `python3 tools/llm_chat.py` or direct ollama API

---

## The Pattern: Extract → Review → Merge

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  EXTRACT    │ ──► │   REVIEW    │ ──► │   MERGE     │
│  (mistral)  │     │ (qwen2.5)   │     │  (mistral)  │
│             │     │             │     │             │
│ First pass  │     │ What's      │     │ Combine     │
│ extraction  │     │ missing?    │     │ all tools   │
└─────────────┘     └─────────────┘     └─────────────┘
     7 tools    +      4 missing    =     11 tools
```

**Why this works:**
- Single extraction misses ~40% of tools
- Reviewer (different model) catches what extractor missed
- Merge step deduplicates and combines

**Test results (Dec 4, 2025):**
- Extract alone: 7 tools, 18.9s
- With review+merge: **11 tools**, 56s total
- Caught: SAM Pro, SavePlan, eSourcing, Tibco, IBM

---

## Agent 1: Technical Analyst

**Model:** mistral:latest (best for precise extraction)

### System Prompt
```
You extract SPECIFIC TOOL/TECHNOLOGY names from profiles.

GOOD skills: "ServiceNow", "SAP CLM", "Oracle", "Python", "HP Mercury", "SharePoint"
BAD skills: "Automated reporting", "Data integration", "Dashboard design"

Return JSON array. Each: {skill, category, proficiency, years, evidence}
```

### User Prompt
```
Extract ONLY tool/technology names (not descriptions) from this profile:

{profile_raw_text}
```

### Expected Response Pattern
```json
[
  {"skill": "ServiceNow", "category": "IT Service Management", "proficiency": "expert", "years": 4, "evidence": "SAM Pro data upload"},
  {"skill": "SAP CLM", "category": "Contract Management", "proficiency": "expert", "years": 6, "evidence": "Contract lifecycle management at Novartis"},
  {"skill": "Oracle", "category": "Database", "proficiency": "advanced", "years": 5, "evidence": "DBA work"},
  {"skill": "Python", "category": "Programming", "proficiency": "advanced", "years": 5, "evidence": "Automation scripts, ML framework"},
  {"skill": "HP Mercury", "category": "Contract Management", "proficiency": "advanced", "years": 5, "evidence": "Contract management tools at DB"}
]
```

### Test Results (Dec 4, 2025)
- **mistral:latest** ✅ Best - extracts specific tool names
- **gemma3:4b** ⚠️ OK but includes descriptions as skills
- **qwen2.5:7b** ⚠️ Slow, verbose output

**Key prompt insight:** Give GOOD/BAD examples, not long explanations.

---

## Agent 2: Reviewer (QA Check)

**Model:** qwen2.5:7b (different model = different perspective)

### System Prompt
```
You are a QA reviewer checking extraction completeness.
```

### User Prompt
```
Compare extracted skills vs profile. Find MISSING software/technology names.

EXTRACTED:
{agent_1_output}

PROFILE:
{profile_raw_text}

List ONLY missing tool names (not already extracted). Check for:
- Vendor names used as tools (Microsoft, IBM, Adobe, SAP, etc.)
- Database systems
- Enterprise platforms (SharePoint, ServiceNow, SAM Pro)
- Development tools

Format: MISSING: tool1, tool2, tool3
Or: MISSING: none
```

### Expected Response Pattern
```
MISSING: HP Mercury, SharePoint, SAM Pro, Tibco, SavePlan, eSourcing
```

### Test Results (Dec 4, 2025)
- Caught 4-6 additional tools that extractor missed
- 9.8s processing time
- **Different model catches different things** ← key insight

---

## Agent 3: Merger (Combine Results)

**Model:** mistral:latest

### User Prompt
```
Combine these into one clean JSON array of tools.

ORIGINAL EXTRACTION:
{agent_1_output}

ADDITIONAL TOOLS FOUND:
{agent_2_output}

Return ONE JSON array with all unique tools. Format: {"tool": "name", "years": "range"}
```

### Expected Response Pattern
```json
[
  {"tool": "ServiceNow", "years": "2020-today"},
  {"tool": "SAP CLM", "years": "2010-2016"},
  {"tool": "SavePlan", "years": "2010-2016"},
  {"tool": "eSourcing", "years": "2010-2016"},
  {"tool": "Oracle", "years": "1998-2002"},
  {"tool": "LDAP", "years": "1998"},
  {"tool": "HP Mercury", "years": "2008-2010"},
  {"tool": "IBM", "years": "2005-2010"},
  {"tool": "SharePoint", "years": "2010-2016"},
  {"tool": "SAM Pro", "years": "2020-today"},
  {"tool": "Tibco", "years": "2005-2010"}
]
```

---

## Full Pipeline Summary

| Step | Model | Time | Output |
|------|-------|------|--------|
| 1. Extract | mistral | 19s | 7 tools |
| 2. Review | qwen2.5:7b | 10s | +4 missing |
| 3. Merge | mistral | 28s | 11 tools |
| **TOTAL** | | **57s** | **11 tools** |

**Improvement:** 57% more tools extracted with review step!

---

# PART 2: Specialized Experts (All Tested Dec 4, 2025)

---

## Expert A: Domain Expert

**Model:** qwen2.5:7b  
**Time:** 26.7s  
**Focus:** Functional disciplines, NOT tools

### Prompt
```
You are a Domain Expert with 25 years in IT Procurement and Software Asset Management.

Extract DOMAIN EXPERTISE skills - NOT tools, but DISCIPLINES and FUNCTIONAL KNOWLEDGE.

CORRECT examples:
- "Software License Management" (a real discipline)
- "Software Asset Management" 
- "Vendor Management"
- "Contract Negotiation"
- "Telecom Expense Management"
- "IT Governance"
- "Banking Industry Knowledge"

WRONG examples:
- "ServiceNow" (that's a tool, not domain expertise)
- "Team Leadership" (that's a soft skill)
- "Python" (that's a technical skill)

Look for IMPLICIT expertise from:
- Job titles: "Global Lead, Software License Management" → SLM expertise
- Responsibilities: "managed 70+ contracts" → Contract Management
- Scale: "200+ person team" → Large-scale operations
- Industries: Deutsche Bank, Novartis → Banking, Pharma

Profile:
{profile_raw_text}

Return JSON array: {"skill": "name", "category": "domain_type", "years": N, "evidence": "quote"}
Focus on WHAT THEY KNOW, not what tools they used.
```

### Test Results
```json
[
  {"skill": "Contract Management", "category": "DISCIPLINE", "years": 16, "evidence": "Managed 70+ contracts..."},
  {"skill": "Software Asset Management", "category": "DISCIPLINE", "years": 25, "evidence": "Built 200+ person team..."},
  {"skill": "Vendor Management", "category": "DISCIPLINE", "years": 25, "evidence": "Managed vendor management team..."},
  {"skill": "Telecom Expense Management", "category": "DISCIPLINE", "years": 8, "evidence": "Led TEMS initiative..."},
  {"skill": "IT Governance", "category": "DISCIPLINE", "years": 25, "evidence": "Led Global Banking IT division..."},
  {"skill": "Contract Negotiation", "category": "DISCIPLINE", "years": 25, "evidence": "€12M IBM deal..."}
]
```

---

## Expert B: Leadership Coach

**Model:** mistral:latest  
**Time:** 46.6s  
**Focus:** Soft skills inferred from actions

### Prompt
```
You are an Executive Leadership Coach from McKinsey.

Extract SOFT SKILLS and LEADERSHIP COMPETENCIES - inferred from actions and responsibilities.

LOOK FOR:
- Team size: "200+ license managers" → Large Team Leadership
- Stakeholder level: "Board member reviews" → Executive Communication
- Scope: "global", "group-wide" → Global Leadership
- Influence: "matrix organization" → Influence Without Authority
- Negotiation: "€12M deal", "70+ contracts" → High-Stakes Negotiation
- Training: "trained global team" → Coaching & Development

Return JSON array:
{"skill": "name", "proficiency": "level", "evidence": "specific quote", "confidence": "HIGH/MEDIUM"}

HIGH confidence = explicit evidence (numbers, titles)
MEDIUM confidence = inferred from context

Profile:
{profile_raw_text}

Extract leadership and soft skills ONLY. Not technical skills, not domain expertise.
```

### Test Results
```json
[
  {"skill": "Large Team Leadership", "proficiency": "HIGH", "evidence": "200+ license managers", "confidence": "HIGH"},
  {"skill": "Executive Communication", "proficiency": "MEDIUM", "evidence": "Board member reviews", "confidence": "MEDIUM"},
  {"skill": "Global Leadership", "proficiency": "HIGH", "evidence": "Group-wide single point of contact", "confidence": "HIGH"},
  {"skill": "Influence Without Authority", "proficiency": "MEDIUM", "evidence": "Matrix org navigation", "confidence": "MEDIUM"},
  {"skill": "Project Management", "proficiency": "HIGH", "evidence": "Multiple major projects", "confidence": "HIGH"},
  {"skill": "Training and Mentoring", "proficiency": "MEDIUM", "evidence": "Trained global team", "confidence": "MEDIUM"},
  {"skill": "Collaboration", "proficiency": "HIGH", "evidence": "Worked with CIO architects", "confidence": "HIGH"}
]
```

---

## Expert C: Creative Director

**Model:** mistral:latest  
**Time:** 83.9s  
**Focus:** Media/production skills (often dismissed as "hobby")

### Prompt
```
You are a Creative Director who worked in television and film.

Extract CREATIVE and MEDIA skills. These are REAL professional skills, not hobbies.

"Produced for ZDF" = professional broadcast television (Germany's largest TV station)

LOOK FOR:
- Television Production
- Documentary Filmmaking
- Video Editing / Post-Production
- CGI / Visual Effects
- Scriptwriting
- Audio Production

Profile:
{profile_raw_text}

Return JSON array: {"skill": "name", "proficiency": "level", "years": N, "evidence": "quote"}
Only creative/media skills. These are legitimate professional skills.
```

### Test Results
```json
[
  {"skill": "Television Production", "proficiency": "Expert", "years": 3, "evidence": "Produced for ZDF"},
  {"skill": "Documentary Filmmaking", "proficiency": "Expert", "years": 3, "evidence": "Der brennende Dornbusch..."},
  {"skill": "Video Editing", "proficiency": "Expert", "years": 3, "evidence": "Active in editing"},
  {"skill": "CGI / Visual Effects", "proficiency": "Expert", "years": 3, "evidence": "CGI work"},
  {"skill": "Scriptwriting", "proficiency": "Expert", "years": 3, "evidence": "Scripting for documentaries"}
]
```

---

## Expert D: Business Analyst

**Model:** mistral:latest  
**Time:** 121.0s  
**Focus:** Quantified business achievements

### Prompt
```
You are a Financial Controller assessing commercial acumen.

Extract BUSINESS and FINANCIAL skills from quantified achievements.

NUMBERS TELL THE STORY:
- "€2M savings p.a." → Cost Optimization (expert)
- "70+ contracts, 8m€" → Contract Management (scale)
- "€12M outsourcing deal" → High-Value Negotiation
- "30% cost reduction" → Savings Delivery
- "12,000 requests/month" → High-Volume Operations
- "Board member reviews" → Executive Reporting

LOOK FOR:
- Budget Management
- Cost Optimization / Savings
- ROI Analysis
- Contract Negotiation (commercial)
- Forecasting / Planning
- KPI Development

Profile:
{profile_raw_text}

Return JSON array: {"skill": "name", "achievement": "quantified result", "evidence": "quote"}
Focus on BUSINESS IMPACT with numbers.
```

### Test Results
```json
[
  {"skill": "Budget Management", "achievement": "Monthly Board reviews", "evidence": "Review trends in spending..."},
  {"skill": "Cost Optimization", "achievement": "€2M savings p.a.", "evidence": "€2M systematic savings"},
  {"skill": "High-Value Negotiation", "achievement": "€12M outsourcing deal", "evidence": "IBM outsourcing deal"},
  {"skill": "ROI Analysis", "achievement": "30% cost reduction", "evidence": "30% telecom cost reduction"},
  {"skill": "Contract Management", "achievement": "70+ contracts, 8m€, 680k€ savings", "evidence": "Managed 70+ contracts..."},
  {"skill": "Process Framework Design", "achievement": "CMM-based vendor management", "evidence": "Modelled CMM framework"}
]
```

---

# COMBINED RESULTS SUMMARY

| Expert | Skills Found | Time |
|--------|--------------|------|
| Technical (Extract+Review+Merge) | 11 tools | 57s |
| Domain Expert | 6 disciplines | 27s |
| Leadership Coach | 7 soft skills | 47s |
| Creative Director | 5 media skills | 84s |
| Business Analyst | 6 commercial skills | 121s |
| **TOTAL** | **35 unique skills** | **~5.5 min** |

vs. WF1122 single-pass extraction: **28 skills**

**Improvement: 25% more skills, with categories and confidence levels!**

---

## Next Steps: Formalize into WF1125

Now that all experts are tested and proven, create the database workflow:

1. **Create conversations** for each expert (5 total)
2. **Create workflow 1125** with 5 steps (can run in parallel)
3. **Add final synthesizer** to merge all expert outputs
4. **Save to profile_skills** table with skill categories

**Input:** Full profile document (14KB OK)
**Output:** 35+ categorized skills with evidence and confidence

---

## Test Commands

```bash
# Quick test any expert
python3 /tmp/test_domain_expert.py
python3 /tmp/test_leadership_coach.py
python3 /tmp/test_creative_director.py
python3 /tmp/test_business_analyst.py

# Full technical pipeline
python3 /tmp/test_full_pipeline.py
```
