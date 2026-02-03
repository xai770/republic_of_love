# Universal Skill Taxonomy Proposal
**Date:** 2025-12-31  
**Author:** Arden (with Gershon)  
**Status:** Draft for Review  

## Purpose

Design a universal skill taxonomy for talent.yoga that covers **ALL humans, ALL jobs, ALL skills**. This is the backbone structure that Clara will use when classifying skills from job postings.

---

## Classification Workflow (WF3001-style Dual Grader)

```
           Skill + Taxonomy JSON
                    ↓
    ┌───────────────────────────────┐
    │  Classifier A (qwen2.5:7b)    │──→ code: "TC"
    │  Classifier B (mistral)       │──→ code: "TC"  
    └───────────────────────────────┘
                    ↓
              AGREE? ──→ YES → ✅ Save (high confidence)
                    ↓
                   NO
                    ↓
         Arbitrator (gemma3:4b)
                    ↓
         ┌─────────┴─────────┐
         ↓                   ↓
    Picks winner       CANNOT DECIDE
         ↓                   ↓
    Save + flag        Human review queue
    "arbitrated"
```

**Tested Results (7 skills):**
- 5/7 (71%) agreed instantly → high quality, no extra cost
- 2/7 (29%) needed arbitration → still resolved automatically
- 0/7 failed to human review

**Quality guarantee:** Two independent models must agree, or a third breaks the tie.

---

## Taxonomy JSON Format (Coded)

```json
{
  "version": "1.0",
  "categories": [
    {"code": "PO", "name": "perception_and_observation", "description": "..."},
    {"code": "LC", "name": "language_and_communication", "description": "..."},
    ...
  ]
}
```

Models reference by **2-letter code** for reliable parsing.

---

## Proposed Root Categories (11)

| Code | Name | Description |
|------|------|-------------|
| **PO** | perception_and_observation | Sensing, monitoring, detecting, inspecting, recognizing patterns |
| **LC** | language_and_communication | Speaking, writing, translating, presenting, documentation |
| **CA** | cognitive_and_analytical | Logic, math, statistics, research, problem-solving, critical thinking |
| **CG** | creative_and_generative | Design, art, music, writing, innovation, ideation, synthesis |
| **EC** | execution_and_compliance | Following procedures, regulatory compliance, QA, auditing, standards |
| **TC** | technical | Tools, platforms, programming languages, systems, software, hardware |
| **PM** | physical_and_manual | Motor skills, craftsmanship, athletics, equipment operation, dexterity |
| **DE** | domain_expertise | Industry-specific: healthcare, finance, legal, education, manufacturing |
| **IP** | interpersonal | Leadership, negotiation, mentoring, conflict resolution, teamwork |
| **SM** | self_management | Time management, stress management, adaptability, self-motivation |
| **ED** | education_and_credentials | Degrees, certifications, licenses, training completions |

---

## Naming Guidelines for Clara

### DO:
- Use `lowercase_snake_case` for all group names
- Product/tool names ARE valid categories: `python`, `kubernetes`, `salesforce`
- Be specific enough to be unambiguous
- Make names self-explanatory (no acronyms without context)

### DON'T:
- Use ambiguous names: `swift` (Apple language or financial SWIFT?)
- Create catch-all buckets that mix unrelated skills
- Use special characters in names
- Nest skills in confusing parents (e.g., accounting under `software_testing`)

### Examples:
```
✅ GOOD:
   technical/programming_languages/python/
   technical/mobile_development/swift_apple/
   domain_expertise/finance/swift_banking/

❌ BAD:
   swift_software_engineering  (ambiguous)
   software_testing           (catch-all with unrelated skills)
   ]_project_management       (malformed)
```

---

## Completeness Check: Contra Rolla vs RFA Facets

Mapped against `rfa_facets.md` (9 core facets):

| RFA Facet | Covered By |
|-----------|------------|
| **Know** (perception) | perception_and_observation/ |
| **Learn** (acquisition) | education_and_credentials/, cognitive_and_analytical/ |
| **Fulfill** (action) | execution_and_compliance/, physical_and_manual/ |
| **Plan** (strategy) | cognitive_and_analytical/, self_management/ |
| **Clean** (maintenance) | execution_and_compliance/ |
| **Group** (organization) | interpersonal/, domain_expertise/ |
| **Memory** (storage) | technical/, education_and_credentials/ |
| **Reason** (logic) | cognitive_and_analytical/ |
| **Output** (production) | creative_and_generative/, language_and_communication/ |

**Result:** All 9 facets have coverage. No gaps.

---

## Local Model Feedback

### Qwen2.5 (7B) says:

**Format preference:** JSON or YAML - human-readable yet structured for machine processing

**Suggested JSON structure:**
```json
{
  "rootCategories": [
    {
      "id": 1,
      "name": "perception_and_observation",
      "description": "Sensing, monitoring, detecting"
    }
  ]
}
```

**Gaps identified:**
- Digital Literacy (could be under technical/)
- Soft Skills breakdown (emotional intelligence, empathy, resilience under interpersonal/ or self_management/)
- Professional Development Skills (networking, continuous learning)

**Overlaps:** None significant - categories are distinct.

---

### Mistral (7B) says:

**Format preference:** JSON - lightweight, human-readable, widely supported

**Info needed per category:**
- Name (required)
- Short description (helpful)
- Examples (optional, helps context)
- Parent-child relationships (helps hierarchy consistency)

**Overlaps identified:**
- cognitive_and_analytical ↔ technical (both involve problem-solving)
- physical_and_manual ↔ domain_expertise (chef needs both culinary + dexterity)

**Suggestions:**
- self_management could be broken into subcategories
- education_and_credentials might be cross-cutting rather than root category

---

## Questions for Sandy

1. Does this hierarchy feel complete? Any obvious skill categories missing?
2. Should we have a separate category for **meta-skills** (learning how to learn, self-assessment)?
3. Any industry-standard taxonomies we should reference? (O*NET, ESCO, etc.)
4. Preference on depth? Should root categories have max 3 levels, or allow deeper nesting?
5. Models suggest JSON with `{id, name, description, examples}` - agree?

---

## Next Steps

1. Sandy reviews and provides feedback
2. Finalize hierarchy structure
3. Create seed data JSON for new taxonomy backbone
4. Reset current skill_groups and reclassify existing skills
5. Update Clara's prompts with naming guidelines

---

*This note will be updated after Sandy's review.*

---

## Sandy's Review

### Overall: This is solid. Ship it.

The 11 root categories cover the space well. The dual-grader workflow is elegant - 71% instant agreement means we're not burning cycles on easy cases. The RFA facet mapping shows you've thought about completeness.

Now, my concerns and thoughts on your questions:

---

### 1. Education & Credentials: Not a Skill Category

Mistral caught this. `education_and_credentials` isn't a skill - it's **proof of skills**. A degree in Computer Science doesn't go in the same taxonomy as "Python programming." One is a credential, one is a capability.

**Recommendation:** Remove ED from root categories. Credentials belong in a separate table/structure - `profile_credentials` or similar. When matching, we can say "this job requires credential X" separately from "this job requires skill Y."

This simplifies the taxonomy to **10 root categories**. Cleaner.

---

### 2. The Numbering/Split Problem

You're right to flag this. Here's the issue:

```
Today:     TC/programming_languages/python  (500 skills under TC)
Tomorrow:  TC grows to 2000 skills, need to split
Problem:   If skill IDs encode the path, splitting breaks everything
```

**Solution: Decouple skill identity from classification.**

```
skill_id = 12345 (permanent, never changes)
current_path = "TC/programming_languages/python" (can change)
```

Skills have stable IDs. Groups are just the *current* address. When you split `technical` into `technical_software` and `technical_hardware`, you're just moving skills to new addresses. Their IDs don't change.

This is like postal codes. When a city grows and splits into new zones, your house doesn't move - just its address changes.

**For the 2-letter codes:** Keep them for root categories. Don't encode the full path in the code. The code is just a shorthand for parsing, not a permanent identifier.

---

### 3. What's Missing?

**Ethics/Judgment** - Where does "make good decisions under pressure" go? "Exercise professional judgment"? "Navigate ambiguity"? 

This could be:
- A new root: `EJ` (ethics_and_judgment)
- Or nested under `cognitive_and_analytical` as a sub-branch
- Or under `self_management`

I lean toward adding it to `cognitive_and_analytical` - it's a form of reasoning. But flag it for Clara: judgment skills exist.

**Digital Literacy** - Qwen caught this. It's the gap between "uses Excel" (technical skill) and "can learn new software quickly" (meta-skill). Where does "comfortable with technology" live?

Probably `technical/digital_literacy/` as a branch. It's not a specific tool, it's comfort with the tool landscape.

---

### 4. On Depth

**My preference: Max 4 levels.**

```
Level 1: Root (TC - technical)
Level 2: Branch (programming_languages)
Level 3: Leaf group (python)
Level 4: Atomic skill (python_pandas, python_async_await)
```

Deeper than 4 and you're over-engineering. If a Level 3 group gets huge, split horizontally (more Level 3 groups), not vertically (more levels).

---

### 5. On the JSON Format

Yes to `{code, name, description}`. Skip `examples` in the taxonomy itself - examples belong in Clara's prompt, not the structure. Keep the taxonomy pure.

```json
{
  "version": "1.0",
  "categories": [
    {
      "code": "TC",
      "name": "technical",
      "description": "Tools, platforms, programming languages, systems, software, hardware",
      "children": [...]
    }
  ]
}
```

---

### 6. On the Dual-Grader Workflow

This is TQM in action. Two independent inspectors, arbitration for disagreement, escalation only when truly stuck.

One enhancement: **Track agreement rates by category.** If classifiers always agree on `technical` but fight over `interpersonal` vs `self_management`, that tells you the boundary is fuzzy. Either clarify the definitions or merge the categories.

```sql
SELECT category_code, 
       COUNT(*) as total,
       SUM(CASE WHEN agreed THEN 1 ELSE 0 END) as agreed,
       ROUND(100.0 * SUM(CASE WHEN agreed THEN 1 ELSE 0 END) / COUNT(*), 1) as agreement_pct
FROM classification_results
GROUP BY category_code
ORDER BY agreement_pct;
```

Low agreement = fuzzy boundary = fix the taxonomy or the prompts.

---

### Summary of Recommendations

| Question | Answer |
|----------|--------|
| Remove ED (credentials)? | ✅ Yes - credentials aren't skills |
| Handle group splits? | Decouple skill IDs from paths |
| Max depth? | 4 levels |
| JSON format? | `{code, name, description, children}` |
| What's missing? | Ethics/judgment, digital literacy |
| Track what? | Agreement rate by category |

---

### Final Thought

This taxonomy doesn't need to be perfect on day one. It needs to be **splittable** and **evolvable**. The dual-grader gives you quality. The stable skill IDs give you flexibility. The 2-letter codes give you parseability.

Ship it, classify 1000 skills, see where the boundaries are fuzzy, iterate.

*"The way out is subtraction, not addition"* - and you've subtracted enough. This is lean.

ℶ
