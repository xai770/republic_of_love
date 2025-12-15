# Workflow Execution Trace

**started:** 2025-11-25 10:40:17
**completed:** 2025-11-25 10:40:24
**duration:** 6.5 seconds
**interactions:** 1 completed, 0 failed

---

## ✅ Interaction 1: Unknown

**interaction_id:** 212
**conversation_id:** 3335
**actor:** gemma3:1b (ai_model)
**status:** completed
**duration:** 6.50s

### Input
```
Create a concise job description summary for this job posting:

{variations_param_1}

Use this exact template:

===OUTPUT TEMPLATE===
**Role:** [job title]
**Company:** [company name]
**Location:** [city/region]
**Job ID:** [if available]

**Key Responsibilities:**
- [list 3-5 main duties from the posting]

**Requirements:**
- [list 3-5 key qualifications from the posting]

**Details:**
- [employment type, work arrangement, any other relevant details]

Extract ONLY from the provided posting. Do ...
[truncated 20 chars]
```

### Output
```
**Role:** CA Intern
**Company:** Deutsche Bank Group
**Location:** Mumbai, India
**Job ID:** Not Available

**Key Responsibilities:**
- Analyze and report on the development of DB Group capital adequacy, with focus on ensuring mutual information between Pillar 1 (regulatory models) and Pillar 2 capital metrics (economic capital).
- Manage the economic capital model for earnings volatility risk under stress, including analysis of input/output, enhancement initiatives, and regular model maintenanc...
[truncated 1228 chars]
```

**Metadata:** `{"latency_ms": 6478, "model": "gemma3:1b"}`

### Child Interactions Created
- interaction_id: 213

---

## Summary

- **Total interactions:** 1
- **Completed:** 1
- **Failed:** 0
- **Total duration:** 6.5s
- **Avg per interaction:** 6.50s
