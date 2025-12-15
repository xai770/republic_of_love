# Hybrid Extraction Workflow

**Purpose:** Combine qwen2.5:7b's speed for technical skills with DeepSeek-R1:8b's depth for organizational insights.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Profile Input                           │
│                  (career_input.txt)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ├─────────────────────┬──────────────────────┐
                         │                     │                      │
                    PARALLEL                   │                      │
                         │                     │                      │
            ┌────────────▼──────────┐  ┌──────▼─────────┐  ┌────────▼─────────┐
            │   qwen2.5:7b          │  │ DeepSeek-R1:8b │  │   Metadata       │
            │  (Fast Technical)     │  │ (Deep Org)     │  │   Extraction     │
            │                       │  │                │  │                  │
            │  • Python, Java       │  │ • Leadership   │  │ • Years exp      │
            │  • SQL, Docker        │  │ • Negotiation  │  │ • Org names      │
            │  • Frameworks         │  │ • Influence    │  │ • Roles          │
            │  • Tools              │  │ • Political    │  │ • Dates          │
            │                       │  │   savvy        │  │                  │
            │  ~5 minutes           │  │ • Strategic    │  │  ~1 minute       │
            │                       │  │   thinking     │  │                  │
            │                       │  │                │  │                  │
            │                       │  │ ~17 minutes    │  │                  │
            └────────────┬──────────┘  └──────┬─────────┘  └────────┬─────────┘
                         │                     │                      │
                         │                     │                      │
                         └─────────────────────┴──────────────────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │   Skill Merger        │
                                  │                       │
                                  │ • Deduplicate         │
                                  │ • Normalize           │
                                  │ • Confidence weight   │
                                  │ • Source tracking     │
                                  └───────────┬───────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │  taxonomy_expander    │
                                  │                       │
                                  │ • Add missing skills  │
                                  │ • Suggest domains     │
                                  │ • Update taxonomy     │
                                  └───────────┬───────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │  simple_skill_mapper  │
                                  │                       │
                                  │ • Map to taxonomy     │
                                  │ • Fuzzy matching      │
                                  │ • Confidence scores   │
                                  └───────────┬───────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │    skill_saver        │
                                  │                       │
                                  │ • Save to DB          │
                                  │ • profile_skills      │
                                  │ • skill_occurrences   │
                                  └───────────────────────┘
```

---

## Why Hybrid?

### Test Results (2025-11-05)

**qwen2.5:7b:**
- ⚡ **Fast**: 5 minutes
- 🔧 **Technical**: Excellent at frameworks, tools, languages
- 📊 **Coverage**: 16 skills (mixed technical + organizational)
- 💾 **Output**: Concise JSON (~2KB)

**DeepSeek-R1:8b:**
- 🧠 **Deep**: 17 minutes with reasoning chains
- 💼 **Organizational**: Found 8 skills qwen completely missed
- 🎯 **Insights**: Stakeholder levels, career progression, strategic context
- 📚 **Output**: Rich analysis (79KB with `<think>` reasoning)

**Skills Only DeepSeek Found:**
1. Influence without authority
2. Cross-functional collaboration
3. Negotiation
4. Political savvy
5. Strategic thinking
6. Governance
7. Leadership progression tracking
8. Cost optimization

### Combined Benefits

- ✅ **Complete coverage**: Technical + Organizational
- ✅ **Reasonable speed**: ~22 minutes total (parallel execution)
- ✅ **Rich context**: Career progression, stakeholder mapping
- ✅ **Executive-ready**: Suitable for senior role matching

---

## Implementation Plan

### Phase 1: Workflow Design (DONE)

**File:** `workflows/hybrid_profile_extraction.json`

```json
{
  "workflow_id": "workflow_1127_hybrid_extraction",
  "workflow_name": "Hybrid Profile Extraction",
  "description": "Parallel extraction with qwen2.5:7b (technical) and DeepSeek-R1:8b (organizational)",
  "steps": [
    {
      "step_id": 1,
      "step_name": "parallel_extraction",
      "actors": [
        {"actor_id": 45, "actor_name": "qwen2.5:7b", "task": "technical_skills"},
        {"actor_id": 52, "actor_name": "taxonomy_expander", "task": "expand_taxonomy"},
        {"actor_id": "TBD", "actor_name": "deepseek-r1:8b", "task": "organizational_skills"}
      ],
      "execution_mode": "parallel",
      "timeout": 1200
    },
    {
      "step_id": 2,
      "step_name": "merge_skills",
      "actor_id": "TBD",
      "actor_name": "skill_merger",
      "input": "outputs from step 1",
      "execution_mode": "sequential"
    },
    {
      "step_id": 3,
      "step_name": "map_to_taxonomy",
      "actor_id": 50,
      "actor_name": "simple_skill_mapper"
    },
    {
      "step_id": 4,
      "step_name": "save_to_database",
      "actor_id": 49,
      "actor_name": "skill_saver"
    }
  ]
}
```

### Phase 2: Create skill_merger Tool

**File:** `tools/skill_merger.py`

**Purpose:** Merge results from multiple extractors

**Responsibilities:**
1. **Deduplicate**: "python" from qwen + "Python" from DeepSeek → one entry
2. **Normalize**: Handle casing, spacing, formatting
3. **Source tracking**: Label each skill with extractor source
4. **Confidence weighting**:
   - qwen technical skills: confidence 0.9
   - DeepSeek organizational: confidence 0.95 (reasoning chains!)
   - Both found it: confidence 1.0
5. **Category assignment**:
   - Technical: Python, Java, SQL, Docker, etc.
   - Organizational: Leadership, negotiation, stakeholder mgmt
   - Domain: Healthcare, finance, technology

**Input format:** 
```json
{
  "qwen_results": ["Python", "Java", "stakeholder management"],
  "deepseek_results": ["strategic thinking", "negotiation", "Python"],
  "metadata": {"profile_id": 1, "extraction_date": "2025-11-05"}
}
```

**Output format:**
```json
{
  "merged_skills": [
    {
      "skill_name": "python",
      "display_name": "Python",
      "category": "technical",
      "confidence": 1.0,
      "sources": ["qwen", "deepseek"],
      "reasoning": "Found by both extractors"
    },
    {
      "skill_name": "strategic_thinking",
      "display_name": "Strategic Thinking",
      "category": "organizational",
      "confidence": 0.95,
      "sources": ["deepseek"],
      "reasoning": "Organizational skill from DeepSeek reasoning chains"
    }
  ],
  "stats": {
    "total_skills": 24,
    "technical": 16,
    "organizational": 8,
    "duplicates_removed": 3
  }
}
```

### Phase 3: Register DeepSeek as Actor

**SQL:**
```sql
INSERT INTO actors (
    actor_name,
    actor_type,
    execution_type,
    execution_path,
    url,
    enabled,
    input_format,
    output_format,
    example_call,
    error_handling,
    execution_config
) VALUES (
    'deepseek-r1:8b',
    'ai_model',
    'ollama_api',
    '',
    'http://localhost:11434/api/generate',
    true,
    'text',
    'json_object',
    '{"model": "deepseek-r1:8b", "prompt": "Analyze career history...", "stream": false}',
    'Returns empty analysis on timeout, logs errors',
    '{"timeout": 900, "temperature": 0.7, "reasoning_mode": true}'
)
RETURNING actor_id, actor_name;
```

### Phase 4: Create Workflow in Database

**Steps:**
1. Create `sessions` entry for workflow_1127
2. Add `instructions` for each step
3. Link `instruction_steps` to actors
4. Test with sample profile
5. Compare results with Workflow 1122

### Phase 5: Performance Optimization

**Parallel Execution:**
- Run qwen2.5:7b and DeepSeek-R1:8b simultaneously
- Reduces total time from 22 min → 17 min (limited by DeepSeek)

**Caching:**
- Cache taxonomy lookups
- Reuse normalized skill names
- Store reasoning chains for future reference

**Monitoring:**
- Track extraction time per actor
- Log skill counts by source
- Measure duplicate rates

---

## Usage Examples

### Example 1: High-Value Profile (Executive)

**Input:** Senior executive with 20+ years experience

**Process:**
1. qwen extracts: Java, Python, SQL, SAP, Oracle, Agile
2. DeepSeek extracts: C-level stakeholder management, board reporting, strategic M&A, change management leadership, cross-border negotiation
3. Merger combines: 18 total skills (10 technical, 8 organizational)
4. taxonomy_expander adds: 2 missing skills (SAP ERP, strategic planning)
5. simple_skill_mapper maps all 20 skills
6. skill_saver writes to profile_skills

**Time:** 17 minutes (parallel)
**Result:** Complete 360° profile suitable for C-suite matching

### Example 2: Technical Profile (Developer)

**Input:** Software engineer with 5 years experience

**Process:**
1. qwen extracts: Python, Docker, Kubernetes, React, PostgreSQL, Git, CI/CD, Agile
2. DeepSeek extracts: team collaboration, code review leadership, cross-functional communication
3. Merger combines: 11 skills (8 technical, 3 organizational)
4. All skills already in taxonomy
5. simple_skill_mapper maps all 11
6. skill_saver writes to profile_skills

**Time:** 17 minutes (parallel)
**Result:** Strong technical profile with soft skills

### Example 3: Career Transition Profile

**Input:** Career changer (teacher → product manager)

**Process:**
1. qwen extracts: curriculum design, lesson planning, basic Excel
2. DeepSeek extracts: stakeholder management (parents, admin), influence without authority, change management (new teaching methods), cross-functional collaboration (teachers, counselors)
3. Merger combines: 9 skills (3 technical, 6 organizational)
4. taxonomy_expander suggests: education_domain, pedagogy
5. Highlight: **Transferable skills** for product management role
6. skill_saver writes with confidence scores

**Time:** 17 minutes
**Result:** Career transition profile highlighting organizational strengths

---

## Success Metrics

### Extraction Quality

**Coverage:**
- Target: 90%+ of skills mentioned in profile
- Measure: Manual review of 10 sample profiles

**Accuracy:**
- Target: 95%+ correctly identified skills
- Measure: Compare with human expert annotation

**Completeness:**
- Technical skills: qwen2.5:7b primary, DeepSeek backup
- Organizational skills: DeepSeek primary, qwen backup
- Target: 100% coverage across both dimensions

### Performance

**Speed:**
- Parallel execution: ~17 minutes (limited by DeepSeek)
- Acceptable for batch processing (overnight runs)
- Consider qwen-only for real-time needs (<5 min requirement)

**Resource Usage:**
- GPU utilization: Monitor during parallel execution
- Memory: DeepSeek-R1:8b requires 5.2GB model + inference
- Disk: Store reasoning chains (79KB per profile)

### Business Impact

**Profile Quality:**
- Senior roles: Organizational skills critical → Use hybrid
- Technical roles: Speed matters → Use qwen-only
- Career transitions: Highlight transferables → Use hybrid

**Matching Accuracy:**
- Measure: Job match quality before/after hybrid extraction
- Hypothesis: Organizational skills improve executive-level matches
- Target: 20%+ improvement in senior role matches

---

## Future Enhancements

### 1. Dynamic Actor Selection

**LLM-driven decision:**
```python
def choose_extraction_strategy(profile_metadata):
    """Choose extractors based on profile characteristics."""
    if profile_metadata['seniority'] == 'C-level':
        return ['qwen2.5:7b', 'deepseek-r1:8b']  # Hybrid
    elif profile_metadata['role_type'] == 'technical':
        return ['qwen2.5:7b']  # Fast technical
    elif profile_metadata['career_transition']:
        return ['deepseek-r1:8b']  # Deep organizational
    else:
        return ['qwen2.5:7b']  # Default fast
```

### 2. Reasoning Chain Storage

**Store DeepSeek's thinking:**
- Table: `skill_reasoning`
- Columns: skill_id, profile_id, reasoning_text, confidence_source
- Use case: Explain to user WHY we think they have this skill

### 3. Incremental Updates

**Only re-extract what changed:**
- Store extraction_date per skill
- If profile updated, only re-run DeepSeek on new sections
- Merge with existing skills

### 4. Multi-Language Support

**Extend to non-English profiles:**
- DeepSeek-R1 handles multiple languages
- qwen2.5:7b may need language detection
- taxonomy_expander needs multilingual skill names

---

## Changelog

**2025-11-05:**
- Initial design based on qwen vs DeepSeek test results
- Proved DeepSeek finds 8 additional organizational skills
- Designed parallel execution workflow
- Planned skill_merger tool
- Created success metrics framework

**Next steps:**
- Implement skill_merger.py
- Register DeepSeek-R1:8b as actor
- Create Workflow 1127 in database
- Test on 5 sample profiles
- Measure performance vs Workflow 1122

---

## Related Documentation

- `TOOL_REGISTRY.md`: Tool catalog with actor contracts
- `WORKFLOW_CREATION_COOKBOOK.md`: Step-by-step workflow guide
- `DATABASE_SCHEMA_GUIDE.md`: skill_aliases ↔ skill_hierarchy relationship
- `PROJECT_PLAN_TURING.md`: Overall system architecture
- Test results: `/tmp/deepseek_final_result.json` (79KB reference data)
