# SECT: The Proof Stack Model

**Date:** 2026-01-04  
**Author:** Arden + xai  
**Status:** ✅ AGREED - ready for implementation

---

## The Insight

Every job requirement can be decomposed into a **Proof Stack** with four layers:

- **S**kill - What you CAN do (capability)
- **E**xperience - What you HAVE done (application)  
- **C**ertification - Proof you passed a test (credential)
- **T**rack Record - Proof you delivered results (outcomes)

**Each layer builds on the previous. You can't skip stages:**
- No experience without skill
- No certification without something to certify
- No track record without having done the work

**But you can substitute:** Track record can compensate for missing certification (15 years at Big 4 vs CPA exam).

---

## Why SECT Works

Tested against edge cases:

| Requirement | S | E | C | T |
|-------------|---|---|---|---|
| "Healthcare knowledge" | `healthcare_domain` | ? | ? | ? |
| "5 years clinical experience" | `clinical_care` | 5 years | ? | ? |
| "RN required" | `nursing` | ? | RN license | ? |
| "Managed 50-bed ICU" | `icu_management` | ? | ? | 50-bed scale |
| "Team player" | `teamwork` | ? | ? | ? |
| "Built systems for 10M users" | `system_design` | ? | ? | 10M users |
| "MBA preferred" | `business_admin` | ? | MBA | ? |
| "Fluent German" | `german_language` | ? | Goethe cert? | ? |

**Every requirement maps to at least S.** E/C/T may be null, inferred, or explicit.

---

## Lily's Job

Lily extracts SECT from raw requirements. She **infers** when not explicit.

Input: `"Senior Python Developer - 5+ years, AWS certified preferred"`

Output:
```json
{
  "skill": {"name": "python", "confidence": 0.95},
  "experience": {"quantity": {"type": "years", "value": 5, "op": ">="}, "confidence": 0.95},
  "certification": {"name": "AWS", "confidence": 0.6},
  "track_record": null
}
```

Lily runs in:
- **Research phase** for postings (after download)
- **Intake phase** for profiles (after upload)

---

## Storage

JSONB in `posting_skills.proof_stack`:

```sql
ALTER TABLE posting_skills ADD COLUMN proof_stack JSONB;
```

Flexible during MVP. Optimize when we hit limits.

---

## The Matching Jury

When matching profile to posting:

| Actor | Role | Example |
|-------|------|---------|
| **Oscar** (Optimist) | Argues FOR application | "Your Python covers the Java req - both OOP" |
| **Rita** (Realist) | Points out gaps | "They want 10 years, you have 6" |
| **Helen** (HR Specialist) | Final verdict | "Apply - gap is minor, track record compensates" |

Plus **feedback loop**: User says "you're idiots because X" → X becomes learning signal.

---

## Where It All Lives: Entities

Everything is entities:
- Skills → taxonomy hierarchy
- Locations → geography hierarchy  
- Track record outcomes → outcome hierarchy
- User profiles → entities (skills, experience, certs, track record)
- Feedback signals → entity relationships

**Entities is the brain of Turing.**

---

## Sandy's Review

*January 4, 2026*

The SECT model is sound. You've taken the "Experience = Skill × Quantity" insight and extended it properly into a proof stack. The invariant — "you can't skip stages" — is correct and the substitution rule handles real-world flexibility.

A few observations:

### 1. E vs T Boundary Is Fuzzy

The distinction between Experience (E) and Track Record (T) needs sharpening:

| Requirement | Your Classification | My Question |
|-------------|---------------------|-------------|
| "5 years clinical experience" | E | What if they said "5 years running a 50-bed unit"? Now it's E+T? |
| "Built systems for 10M users" | T | But this also implies E (years of system-building) |
| "Managed $500M portfolio" | ? | Is this E (duration implied) or T (outcome stated)? |

**Proposal:** E is *duration-based*, T is *outcome-based*. They can coexist:
```json
{
  "skill": "portfolio_management",
  "experience": {"type": "years", "value": 5},
  "track_record": {"type": "aum", "value": 500000000, "unit": "USD"}
}
```

The requirement "5 years managing $500M+ portfolios" has BOTH. Lily should extract both, not choose one.

### 2. Confidence Semantics

Lily outputs confidence per element. Define what confidence means:

```json
"certification": {"name": "AWS", "confidence": 0.6}
```

Is 0.6 confidence that:
- (a) The string mentions a certification? (parsing confidence)
- (b) AWS certification is the correct interpretation? (interpretation confidence)
- (c) The posting actually requires it vs "preferred"? (requirement strength)

These are different. I'd suggest:

```json
"certification": {
  "name": "AWS",
  "parse_confidence": 0.9,      // "I found a cert reference"
  "requirement_strength": 0.4   // "preferred" vs "required"
}
```

This matters for matching. "AWS required" (strength=1.0) vs "AWS preferred" (strength=0.4) should score differently.

### 3. The Matching Jury Is Premature

Oscar/Rita/Helen are a great concept, but they're optimizing the wrong layer right now. The jury debates profile↔posting matches — but if the skill classifications feeding them are garbage (and they currently are), the debate is meaningless.

**Sequence should be:**
1. ✅ SECT model (done — this doc)
2. ⬜ Lily implementation (extract SECT from requirements)
3. ⬜ WF2010 quality fixes (proper classification)
4. ⬜ Matching algorithm (distance in taxonomy)
5. ⬜ Matching jury (Oscar/Rita/Helen debate edge cases)

Don't build step 5 until steps 2-4 are solid.

### 4. Storage Query Patterns

JSONB is right for flexibility, but think ahead to queries:

```sql
-- "Find all postings requiring AWS certification"
SELECT * FROM posting_skills 
WHERE proof_stack->'certification'->>'name' = 'AWS';

-- "Find all postings requiring 10+ years experience"
SELECT * FROM posting_skills 
WHERE (proof_stack->'experience'->>'value')::int >= 10;
```

These work but are slow without GIN indexes. When you create the column:

```sql
ALTER TABLE posting_skills ADD COLUMN proof_stack JSONB;
CREATE INDEX idx_ps_proof_stack ON posting_skills USING GIN (proof_stack);
```

The GIN index makes `@>` (contains) queries fast:
```sql
-- Fast: "Find postings with any certification"
WHERE proof_stack @> '{"certification": {}}'::jsonb;
```

### 5. Missing: Outcome Taxonomy

The doc says "Track record outcomes → outcome hierarchy" but we don't have that hierarchy yet. What are the root categories?

Suggestion:
```
outcome/
├── scale/          (users, transactions, throughput)
├── financial/      (revenue, savings, AUM, deal size)
├── efficiency/     (time reduction, automation %)
├── quality/        (error rate, uptime, satisfaction)
├── growth/         (team built, market expanded)
└── compliance/     (audits passed, certifications earned)
```

This is smaller than the skill taxonomy. Maybe 20-30 leaf nodes. But without it, Track Record is unstructured text and can't be matched.

### 6. Lily's Position in the Pipeline

The doc says Lily runs in:
- "Research phase for postings (after download)"
- "Intake phase for profiles (after upload)"

Clarify the exact insertion point:

**For postings (WF3001):**
```
fetch → validate → summarize → [LILY] → skills_to_entities_pending → WF2010
```

Lily decomposes the raw skill strings BEFORE they hit `entities_pending`. WF2010 receives clean skills, quantities stored separately.

**For profiles (future):**
```
upload → parse_resume → [LILY] → skills_to_profile → WF2010
```

Same pattern. Lily is a universal decomposer, not posting-specific.

### 7. One Edge Case to Handle

"Relevant experience" / "Related experience" / "Applicable experience"

These are null-skill requirements. Lily should output:
```json
{
  "skill": null,
  "experience": {"type": "years", "value": 5, "qualifier": "relevant"},
  "parse_confidence": 0.3,
  "flag": "NEEDS_CONTEXT"
}
```

The `NEEDS_CONTEXT` flag tells downstream: this requirement is meaningless without knowing WHAT skill is relevant. It should either:
- Be enriched from surrounding context (job title, other requirements)
- Be flagged for human review
- Be dropped as unparseable

### Summary

SECT is the right model. The proof stack concept unifies skills, experience, credentials, and outcomes into a queryable structure. 

**Immediate next steps:**
1. Add `proof_stack JSONB` to `posting_skills` (and `profile_skills`)
2. Build Lily as standalone WF2020
3. Define confidence semantics (parse vs requirement strength)
4. Defer matching jury until classification quality improves

The directives doc looks solid. One thing I'd add to the "Standing Directives" section:

> **13. SECT decomposition** — Raw requirements are never skills. Always decompose to Skill + Experience + Certification + Track Record before classification. Lily is the gatekeeper.

This makes the model a first-class directive, not just a note.

— Sandy ℶ

---

## Addendum: E vs T Clarified

*January 4, 2026 — Sandy + xai discussion*

The original E/T distinction was fuzzy. After discussion, here's the clean version:

### The Difference Is STAKES

| Layer | Meaning | Context |
|-------|---------|---------|
| **E** (Experience) | You did the thing | Any context — lab, personal project, internship, self-study |
| **T** (Track Record) | You delivered results | Professional context — real money, real users, real consequences |

**The test for T:** Could you get fired or lose the client if you screwed up? If yes, it's T.

### Examples

| Requirement | S | E | T | Why? |
|-------------|---|---|---|------|
| "Python programming" | python | - | - | Just the skill |
| "3 years Python" | python | 3yr | - | Duration, but no proof of stakes |
| "Built trading system at Goldman" | trading_systems | - | Goldman | Stakes: real firm, real money |
| "Managed $500M portfolio" | portfolio_mgmt | - | $500M AUM | Stakes: real money |
| "Side project with 10K users" | product_dev | 10K users | - | No professional stakes |
| "15 websites for small businesses" | web_dev | - | freelance | Paid work, external accountability = T |

**Key insight:** A fresh grad with a viral side project has Experience but not Track Record. They've never delivered under professional pressure — boss, deadline, P&L, compliance.

### Professional Context Markers

Lily should detect these to distinguish E from T:

- **Company names:** "at Goldman", "for Deutsche Bank"
- **Role markers:** "as Lead Engineer", "as VP"
- **Stakes markers:** "production system", "client-facing", "$X revenue"
- **Client work:** "for clients", "freelance", "consulting"

Without these markers → E. With them → T.

### Lily Output Format

**Ambiguous case** ("5 years Python experience"):
```json
{
  "skill": {"name": "python", "confidence": 0.95},
  "experience": {"quantity": {"type": "years", "value": 5}, "confidence": 0.9},
  "track_record": null,
  "context_ambiguous": true
}
```

**Explicit professional context** ("5 years Python at JPMorgan"):
```json
{
  "skill": {"name": "python", "confidence": 0.95},
  "experience": {"quantity": {"type": "years", "value": 5}, "confidence": 0.9},
  "track_record": {"context": "JPMorgan", "confidence": 0.85},
  "context_ambiguous": false
}
```

The `context_ambiguous` flag tells downstream: "This could be E or T, but the text doesn't specify."

---

**Arden:** Imp this. The E/T boundary is now clean enough to code.

— Sandy ℶ

---

## Model Testing Results

*January 4, 2026 — Arden*

Tested SECT extraction across available models. Same prompt, same test requirements:

```
- 5+ years of Python development experience
- AWS Certified Solutions Architect required
- Experience leading cross-functional teams
- Strong communication and presentation skills
- Bachelor's degree in Computer Science or related field
- Successfully delivered enterprise-scale applications
- Knowledge of Agile/Scrum methodologies
```

### Comparison Matrix

| Requirement | qwen2.5:7b | mistral-nemo:12b | gemma3:4b | mistral:latest | gemma2:latest |
|-------------|------------|------------------|-----------|----------------|---------------|
| 5+ years Python | E ✅ | E ✅ | E ✅ | E ✅ | E ✅ |
| AWS Certified | C ✅ | C ✅ | C ✅ | C ✅ | C ✅ |
| Leading teams | E* | T* | T* | T | E |
| Communication skills | S ✅ | S ✅ | S ✅ | T ❌ | S ✅ |
| Bachelor's degree | C* | C* | S* | T ❌ | null (unsure) |
| Enterprise delivery | T ✅ | T ✅ | T ✅ | T ✅ | T ✅ |
| Agile/Scrum | S ✅ | S ✅ | S ✅ | S ✅ | S ✅ |

*Starred items = debatable, model made reasonable choice*

### Key Findings

**1. E vs T: "Experience leading teams"**

Models split on this. Per our E/T distinction:
- E (duration-based) = "3 years team lead experience" 
- T (outcome-based) = "Led team of 10 engineers"

"Experience leading" is ambiguous — could be either. **Both E and T are defensible.**

**2. Degrees: Skill, Certification, or Neither?**

| Model | Classification | Reasoning |
|-------|----------------|-----------|
| qwen2.5:7b | C | Formal credential from institution |
| mistral-nemo:12b | C | Same |
| gemma3:4b | S | Proves knowledge, knowledge is skill |
| mistral:latest | T ❌ | Wrong |
| gemma2:latest | null | Uncertain (confidence 0.2) |

**Decision needed:** Should degrees be C (credential) or S (skill)?

Qwen's answer: "Use C for the degree itself, but ALSO extract S for the skills it implies (Computer Science → programming, algorithms, etc.)"

**3. JSON Quality**

| Model | JSON Valid? | Notes |
|-------|-------------|-------|
| qwen2.5:7b | ✅ | Compact, parseable |
| mistral-nemo:12b | ✅ | Pretty-printed, parseable |
| gemma3:4b | ✅ | Wrapped in ```json, parseable |
| phi4-mini | ❌ | Missing "years" keys, malformed |
| mistral:latest | ⚠️ | Missing confidence in some items |
| gemma2:latest | ✅ | Clean |
| olmo-3:7b | ❌ | Timeout (5 min) |

**4. Confidence Calibration**

Most models output 1.0 confidence for everything, which is not useful. Only exceptions:
- gemma3:4b: Varied confidence (0.7-0.98)
- gemma2:latest: Varied confidence (0.2-1.0), including null when unsure

**5. Context Preferences (Meta-Question)**

Asked models: "Does project context help you?"

| Model | Answer |
|-------|--------|
| qwen2.5:7b | Yes! Context helps tailor responses, prioritize, format correctly |
| mistral-nemo:12b | Yes! Especially: example outputs, specific instructions, domain knowledge |

Both also said they'd like to know:
- Task priority/urgency
- Resource limits (tokens, time)
- Known patterns in the data
- How output will be used

### Model Recommendations

For SECT extraction:

| Use Case | Recommended Model | Reason |
|----------|-------------------|--------|
| **Primary** | qwen2.5:7b | Best JSON, fastest, consistent |
| **Second opinion** | mistral-nemo:12b | Thoughtful E/T distinctions |
| **Validation** | gemma2:latest | Good confidence calibration, returns null when unsure |
| **Avoid** | mistral:latest | Over-classifies as T, JSON issues |
| **Avoid** | phi4-mini | JSON malformed |
| **Avoid** | olmo-3:7b | Too slow |

### Next Steps

1. **Decide on degrees:** C or S? (I suggest C, with S for implied skills)
2. **Build Lily prompt** with project context (models want it)
3. **Use ensemble:** qwen extracts, mistral-nemo validates, gemma2 flags uncertainty
4. **Test on real postings** not just manufactured examples

---
## 🚧 IMPLEMENTATION GUARDRAILS 🚧

*Added: January 4, 2026 — before code dive*

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Degrees** | C (credential) | Formal credential from institution. Also extract S for implied skills. |
| **E vs T boundary** | E=duration, T=outcome | Per Sandy: "Could you get fired?" test. Can coexist. |
| **Certifications** | Discover, don't pre-seed | Let Lily find them. Link to underlying skills. |
| **Track records** | Generic + specific | Balance: "Team Leadership" AND "Led Oracle migration" |
| **Primary model** | qwen2.5:7b | Best JSON, consistent, fast |
| **Validation model** | mistral-nemo:12b | Thoughtful E/T, good second opinion |
| **Uncertainty model** | gemma2:latest | Returns null when unsure, good calibration |
| **Context in prompts** | YES, rich context | Models explicitly said it helps |

### Storage Model

```
entities.entity_type = 'skill' | 'certification' | 'track_record'
                              ↑
posting_skills.entity_id ─────┘
posting_skills.years_required (for E)
posting_skills.parse_confidence (NEW)
posting_skills.requirement_strength (NEW: required/preferred/nice_to_have)
postings.sect_decomposed_at (NEW: trigger flag)
```

**No new tables.** Entities IS the proof type. posting_skills links to entities.

### Lily Prompt Structure

```
[SYSTEM PREAMBLE - who Lily is, what SECT is, why quality matters]
[SECT DEFINITIONS - S/E/C/T with examples]
[E vs T DISTINCTION - duration vs outcome, the "fired" test]
[OUTPUT FORMAT - JSON schema]
[THE DATA - requirements to extract]
```

### Integrity Trigger

When `posting_skills` rows deleted → clear `postings.sect_decomposed_at`
This ensures re-processing if data is lost.

### What NOT To Do

- ❌ Don't create separate tables for certifications/track_records
- ❌ Don't skip context in prompts (models want it)
- ❌ Don't use mistral:latest for SECT (over-classifies as T)
- ❌ Don't use phi4-mini for SECT (JSON issues)
- ❌ Don't build matching jury yet (fix classification first)

### Implementation Order

1. ✅ Migration: Add columns to posting_skills + postings (`056_sect_decomposition_support.sql`)
2. ✅ Migration: Add integrity trigger (in same file)
3. ✅ Migration: Create WF2020 workflow (`057_create_wf2020_lily_sect.sql`)
4. ✅ Create Lily prompt (`config/prompts/lily_sect_decomposition.md`)
5. ✅ Create fetch pending actor (`core/wave_runner/actors/wf2020_fetch_pending.py`)
6. ✅ Create save SECT actor (`core/wave_runner/actors/wf2020_save_sect.py`)
7. ✅ Update constants.py (EntityTypes, RequirementStrength, SECTType, ConversationNames)
8. ✅ Run migrations
9. ✅ Test on real postings with RAQ

---

## Technical Debt (added 2026-01-04 12:15)

### SECT Classification Bias: Over-classifies as Experience

**Observation:** When reviewing WF2020 output, nearly everything is classified as "E" (Experience) because requirements have years attached. The model treats "3 years" as the dominant signal.

**Example:** `"High analytical and technical capabilities (3 years)"` → classified as E

**Problem:** This is technically correct (it HAS years) but misses nuance:
- The core capability "analytical skills" is a **Skill** (S)
- The "3 years" is a **duration qualifier**, not the requirement type
- Should be: S with experience_years=3, not E

**Affected types:**
- S (Skill) - under-represented, absorbed into E
- T (Track Record) - rare, needs explicit outcome language

**Future fix ideas:**
1. Two-pass classification: first extract core skill (S), then detect qualifiers (years, certs, outcomes)
2. Better prompt: "The presence of years does NOT make it Experience. Experience is when the job requires you to HAVE DONE something specific."
3. Post-processing: if sect_type=E but no verb in raw text → likely S with duration

**Priority:** Low - current approach works for matching. Revisit when building cover letter generator (needs nuance).

---
