# DynaTax Prompt Design Protocol
**A Love Story in Code** 💙  
Created: 2025-10-23 17:31  
Authors: xai + Arden

## The Principle: No JSON for Ollama Output

**Why?** JSON is too brittle for LLM output:
- LLMs add commentary ("Here's the JSON...")
- LLMs wrap in code fences (```json)
- LLMs make syntax errors (missing commas, quotes)
- Parsing fails = lost data

**Solution:** Structured bracket format with clear delimiters

## The Format: Processing Instructions → Payload → QA Check

Every prompt follows this 3-part structure:

```
## Processing Instructions
Format your response as [FIELD: value].
Example: [EXAMPLE: shows format]

## Processing Payload
{actual_data_to_process}

## QA Check
Submit ONLY the required response in brackets. No commentary.
```

### Why This Works

1. **Clear separation**: Instructions vs Data vs Quality rules
2. **Example-driven**: LLM sees exact format to follow
3. **Bracket parsing**: Easy regex extraction, robust to LLM variations
4. **QA enforcement**: Explicit "no commentary" rule

## DynaTax Implementation

### Session 1: Derive All Skills (Inductive Reasoning)

**Facet**: ri (induce) - infer implicit knowledge from context

**Prompt**: `test_prompts/dynatax_session1_derive_skills.txt`

**Format**:
```
[SKILL: skill_name | EVIDENCE: quote | CONFIDENCE: high/medium/low | CATEGORY: technical/business/creative/interpersonal]
```

**Example**:
```
Input: "Managed software licenses for 80,000 users"
Output: [SKILL: SQL | EVIDENCE: Managing licenses for over 80k users requires database queries | CONFIDENCE: high | CATEGORY: technical]
```

**Key Innovation**: The LLM must INDUCE skills from context, not just extract stated skills.

### Session 2: Match Job to Profile (Scoring)

**Facet**: gs (score) - evaluate match quality

**Prompt**: `test_prompts/dynatax_session2_match_job.txt`

**Format**:
```
[MATCH_SCORE: 0-100]
[MATCHING_SKILLS: skill1, skill2, skill3]
[RELEVANT_EXPERIENCE: description]
[KEY_STRENGTHS: strengths]
[GAPS: gaps]
[RECOMMENDATION: STRONG/MODERATE/WEAK MATCH - advice]
```

**Example**:
```
[MATCH_SCORE: 45]
[MATCHING_SKILLS: Beratung, Kundenbeziehungen, Verhandlungsgeschicklichkeit]
[RELEVANT_EXPERIENCE: Direct experience in financial advisory at Deutsche Bank]
[KEY_STRENGTHS: Customer relationships, communication skills]
[GAPS: No SAP systems experience]
[RECOMMENDATION: MODERATE MATCH - Apply if strong interpersonal skills. Take short course in SAP basics.]
```

## Development Workflow

### Phase 1: Static Protocol (CLI Testing)

**Goal**: Perfect the prompts before building recipes

**Steps**:
1. Create sample inputs:
   - `temp/gershon_profile.txt` (career profile)
   - `temp/test_job.txt` (job requirements)

2. Run CLI test:
   ```bash
   ./dynatax_cli_test.sh phi3:latest temp/gershon_profile.txt temp/test_job.txt
   ```

3. Review outputs:
   - `temp/dynatax_session1_output.txt`
   - `temp/dynatax_session2_output.txt`

4. Iterate on prompts:
   - Edit `test_prompts/dynatax_session1_derive_skills.txt`
   - Edit `test_prompts/dynatax_session2_match_job.txt`
   - Re-run CLI test
   - Repeat until perfect

5. Test different models:
   ```bash
   ./dynatax_cli_test.sh qwen2.5:7b temp/gershon_profile.txt temp/test_job.txt
   ./dynatax_cli_test.sh gemma2:latest temp/gershon_profile.txt temp/test_job.txt
   ```

6. Manual OWUI testing (optional):
   - Copy prompt from `test_prompts/dynatax_session1_derive_skills.txt`
   - Replace `{career_profile_text}` with actual profile
   - Paste into ChatGPT/Claude
   - Compare quality vs local models

### Phase 2: Recipe Building

**Goal**: Automate the validated prompts

**Once prompts are perfect**:
1. Create Recipe with 2 sessions (isolated, not continuous)
2. Use finalized prompts from `test_prompts/`
3. Create variations (multiple career profiles × multiple jobs)
4. Run batch execution
5. Use SQL analysis to evaluate quality

### Phase 3: Production Deployment

**Goal**: Integrate into talent.yoga pipeline

**After Recipe validates**:
1. Update canonical in database with proven prompts
2. Add to production workflow
3. Monitor quality over time
4. Iterate as needed

## Parsing Strategy

### Extracting Data from Bracketed Format

**Python example**:
```python
import re

# Session 1: Extract skills
skill_pattern = r'\[SKILL: ([^\|]+) \| EVIDENCE: ([^\|]+) \| CONFIDENCE: ([^\|]+) \| CATEGORY: ([^\]]+)\]'
skills = re.findall(skill_pattern, session1_output)

for skill_name, evidence, confidence, category in skills:
    print(f"Skill: {skill_name.strip()}")
    print(f"Evidence: {evidence.strip()}")
    print(f"Confidence: {confidence.strip()}")
    print(f"Category: {category.strip()}\n")

# Session 2: Extract match data
match_score = re.search(r'\[MATCH_SCORE: (\d+)\]', session2_output).group(1)
matching_skills = re.search(r'\[MATCHING_SKILLS: ([^\]]+)\]', session2_output).group(1)
recommendation = re.search(r'\[RECOMMENDATION: ([^\]]+)\]', session2_output).group(1)
```

**Bash example**:
```bash
# Extract match score
grep -oP '\[MATCH_SCORE: \K[^\]]+' temp/dynatax_session2_output.txt

# Extract recommendation
grep -oP '\[RECOMMENDATION: \K[^\]]+' temp/dynatax_session2_output.txt
```

**SQL example** (for recipe_runs analysis):
```sql
-- Extract match score from session_output
SELECT 
    recipe_run_id,
    CAST(
        SUBSTR(
            session_output,
            INSTR(session_output, '[MATCH_SCORE: ') + 14,
            INSTR(SUBSTR(session_output, INSTR(session_output, '[MATCH_SCORE: ')), ']') - 14
        ) AS INTEGER
    ) as match_score
FROM session_runs
WHERE session_number = 2;
```

## Design Principles Learned

### ✅ DO:
- Use bracketed format with clear delimiters
- Provide concrete examples in prompt
- Separate instructions, payload, and QA rules
- Test in CLI before building recipes
- Use isolated sessions with explicit output passing

### ❌ DON'T:
- Use JSON for Ollama output (too brittle)
- Use continuous context sessions (hallucination risk)
- Skip CLI testing phase (recipes are expensive to debug)
- Assume LLM will follow implicit rules
- Mix multiple tasks in one prompt

## Files Created

**Prompt Templates**:
- `test_prompts/dynatax_session1_derive_skills.txt` - Session 1 template
- `test_prompts/dynatax_session2_match_job.txt` - Session 2 template

**Testing Tools**:
- `dynatax_cli_test.sh` - CLI test harness
- `temp/dynatax_session1_output.txt` - Session 1 results
- `temp/dynatax_session2_output.txt` - Session 2 results

**Documentation**:
- `docs/DYNATAX_PROMPT_DESIGN.md` - This document
- `docs/LLMCORE_RECIPE_CREATION_GUIDE.md` - Updated with DynaTax example
- `view_dynatax_canonical.sh` - View canonical in database

## Next Steps

1. **Create sample inputs**: 
   ```bash
   # Create career profile
   echo "Your career profile text here..." > temp/gershon_profile.txt
   
   # Create job posting
   echo "Job requirements text here..." > temp/test_job.txt
   ```

2. **Run first test**:
   ```bash
   ./dynatax_cli_test.sh phi3:latest temp/gershon_profile.txt temp/test_job.txt
   ```

3. **Review and iterate**: Look at outputs, improve prompts, re-test

4. **Test multiple models**: Find the best model for each session

5. **Build Recipe**: Once prompts are perfect, create automated recipe

6. **Scale up**: Test on all 69 cleaned jobs

7. **Deploy**: Integrate into talent.yoga production workflow

---

**Status**: Phase 1 (Static Protocol) - Ready for CLI testing  
**Last Updated**: 2025-10-23 17:31  
**A love story in code** 💙
