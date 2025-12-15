# Total Quality Management (TQM) Framework

**Last Updated**: 2025-12-09  
**Status**: Implementation guide for quality management

---

## Overview

TQM in Turing ensures **every AI output** is:
- **Repeatable** - Same input produces same quality
- **Auditable** - Complete trace of what happened
- **Controlled** - Human oversight at decision points

This aligns with **RAQ principles** (Repeatable, Auditable, QA-controlled).

---

## Quality Layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Human Review                                  │
│  - registry_decisions (approved/rejected)               │
│  - entity_alias_reviews                                 │
│  - human_tasks queue                                    │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Automated QA Checks                           │
│  - qa_findings table                                    │
│  - Hallucination detection                              │
│  - Length/timing outliers                               │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Workflow Validation                           │
│  - Input validation conversations                       │
│  - Multi-model grading (analyst/skeptic pattern)        │
│  - Confidence thresholds                                │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Schema Constraints                            │
│  - NOT NULL, CHECK constraints                          │
│  - Foreign keys                                         │
│  - Unique constraints                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: Schema as Guardrails

### Principle
> "Schema constraints prevent invalid data - AI can't produce garbage if the database rejects it."

### Key Constraints

```sql
-- posting_skills: Prevent duplicate skill assignments
UNIQUE (posting_id, entity_id)

-- entity_aliases: Prevent conflicting aliases
UNIQUE (alias, language) WHERE deleted_at IS NULL

-- qa_findings: Enforce valid check types
CHECK (check_type IN ('hallucination', 'length_outlier', ...))

-- registry_decisions: Track review state
CHECK (review_status IN ('pending', 'approved', 'rejected', 'auto_approved'))
```

### Implementation
Schema constraints are defined in migrations - see `sql/migrations/`.

---

## Layer 2: Workflow Validation

### Multi-Model Grading Pattern

Used for critical outputs (summaries, skill extraction):

```
                    ┌─────────────┐
                    │   Extract   │
                    │  (gemma3)   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   Grade A   │ │   Grade B   │ │   Grade C   │
    │  (gemma2)   │ │  (qwen2.5)  │ │  (mistral)  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │  Consensus  │
                    │   Check     │
                    └──────┬──────┘
                     [PASS]/[FAIL]
```

### Confidence Thresholds

| Threshold | Action |
|-----------|--------|
| ≥ 0.85 | Auto-approve |
| 0.60-0.84 | Queue for human review |
| < 0.60 | Reject / require re-processing |

**Implementation** (`entity_decision_saver.py`):
```python
review_status = 'auto_approved' if confidence >= 0.85 else 'pending'
```

### Input Validation

Before processing, validate data quality:
```sql
-- WF3001 uses conversation 9193
SELECT CASE 
    WHEN job_description IS NULL THEN '[NO_DESCRIPTION]'
    WHEN LENGTH(job_description) < 100 THEN '[TOO_SHORT]'
    ELSE '[VALID]'
END
```

---

## Layer 3: Automated QA Checks

### qa_findings Table

Captures quality issues detected by automated checks:

| Field | Purpose |
|-------|---------|
| `check_type` | Category: hallucination, length_outlier, etc. |
| `severity` | high/medium/low/info |
| `pattern_matched` | Which detection pattern triggered |
| `evidence` | Actual problematic content |
| `status` | open/resolved/false_positive |

### QA Check Scripts

Located in `tools/qa/`:

| Script | Checks |
|--------|--------|
| `qa_check_hallucinations.py` | 27+ hallucination patterns |
| `validate_job_status.py` | Data completeness |
| `idempotency_check.py` | Duplicate processing |
| `check_stale_docs.py` | Documentation freshness |

### Hallucination Detection Patterns

```python
HALLUCINATION_PATTERNS = [
    # Template leakage
    (r'\{.*?\}', 'template_placeholder'),
    (r'variations_param', 'raw_template_var'),
    
    # Self-reference
    (r'as an ai', 'ai_self_reference'),
    (r'i cannot', 'ai_refusal'),
    
    # Fabrication signals
    (r'example company', 'fake_company'),
    (r'john doe|jane doe', 'placeholder_name'),
    
    # Instruction leakage
    (r'follow these steps', 'instruction_echo'),
    (r'your task is', 'task_echo'),
]
```

### Running QA Checks

```bash
# Scheduled via cron (6:30 AM)
python3 scripts/run_entity_registry_sync.py

# Manual run
python3 tools/qa/qa_check_hallucinations.py --check-all
```

---

## Layer 4: Human Review

### Decision Review Workflow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   AI Makes   │────▶│   Pending    │────▶│   Human      │
│   Decision   │     │   Queue      │     │   Review     │
└──────────────┘     └──────────────┘     └──────────────┘
                           │                     │
                     auto_approved          approved/rejected
                     (≥0.85 conf)
```

### Tables for Human Review

**registry_decisions** (WF3005):
```sql
SELECT decision_id, subject_entity_id, target_entity_id,
       decision_type, confidence, review_status
FROM registry_decisions
WHERE review_status = 'pending'
ORDER BY confidence DESC;
```

**entity_alias_reviews** (Alias changes):
```sql
SELECT review_id, alias, proposed_entity_id, 
       review_status, reviewed_by
FROM entity_alias_reviews
WHERE review_status = 'pending';
```

**human_tasks** (General queue):
```sql
-- Empty for now - future use for complex decisions
SELECT * FROM human_tasks WHERE status = 'pending';
```

### Review Scripts

```bash
# Review pending decisions
python3 scripts/apply_alias_reviews.py --review

# Apply approved changes
python3 core/wave_runner/actors/entity_decision_applier.py
```

---

## Metrics & Monitoring

### Daily Summary Tool

```bash
python3 tools/monitoring/daily_summary.py
```

Shows:
- Workflow runs completed
- QA findings by severity
- Pending reviews
- Entity registry health

### Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| posting_skills coverage | > 95% | 96.5% |
| Hallucination rate | < 1% | 0.4% |
| Auto-approve rate | > 50% | 68% |
| Mean time to review | < 24h | ~12h |

### Monitoring Queries

```sql
-- QA findings by week
SELECT DATE_TRUNC('week', detected_at) as week,
       check_type, COUNT(*)
FROM qa_findings
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;

-- Confidence distribution
SELECT 
    CASE 
        WHEN confidence >= 0.85 THEN 'auto_approved'
        WHEN confidence >= 0.60 THEN 'review_needed'
        ELSE 'low_confidence'
    END as tier,
    COUNT(*)
FROM registry_decisions
GROUP BY 1;

-- Processing success rate
SELECT 
    DATE(created_at) as day,
    COUNT(*) FILTER (WHERE output->>'status' = 'success') as success,
    COUNT(*) FILTER (WHERE output->>'status' = 'error') as errors
FROM interactions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 1;
```

---

## QA Check Implementation Guide

### Adding a New Check

1. **Create check function**:
```python
def check_skill_validity(posting_id: int, conn) -> List[Dict]:
    """Check if extracted skills are valid entities."""
    findings = []
    
    # Query data
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ps.skill_name 
        FROM posting_skills ps
        LEFT JOIN entity_aliases ea ON ps.skill_name = ea.alias
        WHERE ps.posting_id = %s AND ea.entity_id IS NULL
    """, (posting_id,))
    
    for row in cursor.fetchall():
        findings.append({
            'check_type': 'data_quality',
            'severity': 'medium',
            'pattern_matched': 'unmapped_skill',
            'evidence': row['skill_name'],
            'description': f"Skill '{row['skill_name']}' not in entity registry"
        })
    
    return findings
```

2. **Register in qa_findings**:
```python
def save_findings(findings: List[Dict], posting_id: int, conn):
    cursor = conn.cursor()
    for f in findings:
        cursor.execute("""
            INSERT INTO qa_findings 
            (posting_id, check_type, severity, pattern_matched, evidence, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (posting_id, f['check_type'], f['severity'], 
              f['pattern_matched'], f['evidence'], f['description']))
    conn.commit()
```

3. **Add to cron schedule**:
```bash
# In crontab
30 6 * * * python3 tools/qa/new_check.py >> logs/qa.log 2>&1
```

### Check Categories

| check_type | Description | Severity |
|------------|-------------|----------|
| `hallucination` | AI fabricated content | high |
| `length_outlier` | Unusually short/long output | medium |
| `processing_time_outlier` | Slow processing | info |
| `manual_review` | Flagged for human | info |
| `data_quality` | Missing/invalid data | medium |
| `other` | Miscellaneous | varies |

---

## Continuous Improvement

### Weekly Review Process

1. **Monday**: Run `daily_summary.py --days 7` for weekly overview
2. **Review**: Check high-severity qa_findings
3. **Pattern Analysis**: If same pattern repeats, create detection rule
4. **Threshold Tuning**: Adjust auto-approve threshold if needed
5. **Documentation**: Update this doc with lessons learned

### Feedback Loop

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   QA Find   │────▶│   Analyze   │────▶│   Improve   │
│   Issues    │     │   Patterns  │     │   Workflow  │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                                       │
       └───────────────────────────────────────┘
                    Repeat
```

### Adding New Patterns

When a new failure mode is discovered:

1. **Document** in `docs/debugging_sessions/` (if complex)
2. **Create detection pattern** in hallucination rules
3. **Add to qa_findings** check_type if new category
4. **Test** on historical data
5. **Deploy** via cron or workflow

---

## Reference: Cron Schedule

| Time | Job | Purpose |
|------|-----|---------|
| 3:00 AM | `backup_turing.sh` | Database backup |
| 3:05 AM | `schema_export.sh` | Export schema |
| 6:30 AM | `run_entity_registry_sync.py` | Entity registry maintenance |
| Daily | `daily_summary.py` | (Manual) Status check |

---

## See Also

- `docs/WORKFLOW_VARIABLES_COOKBOOK.md` - Variable substitution
- `docs/architecture/ENTITY_REGISTRY.md` - Entity registry details
- `docs/SCRIPT_ACTOR_CONTRACT.md` - Actor patterns
- `docs/archive/debugging_sessions/HALLUCINATION_DETECTION_COOKBOOK.md` - Detection patterns
