# Job Source Interrogators
**Turing System - API Reconnaissance Framework**

Last Updated: 2025-11-07  
Authors: Arden & xai

---

## Philosophy

> *"We never fail, we just keep iterating"*

Before building any data import script, we **interrogate the source** to understand:
- API structure and limits
- Data quality and completeness
- Rate limiting and performance
- URL patterns and quirks
- Authentication requirements

Each interrogator is a **modular, self-contained tool** with its own README as a guardrail.

---

## Structure

```
interrogators/
├── README.md (this file)
├── base.py (Base interrogator class)
├── deutsche_bank.py (Deutsche Bank specialization)
├── rate_limiter.py (Rate limit detection module)
├── performance.py (Performance benchmarking module)
├── data_quality.py (Data completeness scoring module)
├── authentication.py (Auth detection module)
├── generic.py (Generic job board interrogator)
└── [source_name].py (Add new sources here)

Each .py file has a corresponding README_[name].md with:
- Purpose
- Usage examples
- Expected output
- Common issues
- Integration points
```

---

## Quick Start

```bash
# Interrogate Deutsche Bank
python3 interrogators/deutsche_bank.py

# Deep analysis mode
python3 interrogators/deutsche_bank.py --deep

# Export findings to JSON
python3 interrogators/deutsche_bank.py --export findings.json

# Test a new job board
python3 interrogators/generic.py --url https://example.com/careers
```

---

## Modules Overview

### Core Modules

1. **base.py** - Abstract base class for all interrogators
   - Finding recording and reporting
   - Common utility methods
   - Export functionality

2. **deutsche_bank.py** - Deutsche Bank career site interrogator
   - API limit testing
   - Geographic distribution
   - Data structure analysis
   - Description source testing

### Enhancement Modules

3. **rate_limiter.py** - Rate limit detection
   - Discovers request throttling
   - Finds safe request rates
   - Tests for 429 responses

4. **performance.py** - Performance benchmarking
   - Response time analysis
   - Throughput estimation
   - Import time prediction

5. **data_quality.py** - Data completeness scoring
   - Field presence analysis
   - Required vs optional fields
   - Quality metrics

6. **authentication.py** - Authentication detection
   - Tests auth requirements
   - Identifies auth methods
   - API key detection

7. **generic.py** - Generic job board interrogator
   - Auto-discovers API endpoints
   - Classifies architecture (SPA/SSR/API)
   - Works with unknown sources

---

## Integration with Import Scripts

**Workflow:**
```
1. Run Interrogator
   ↓
2. Review Findings Report
   ↓
3. Generate Import Script Template
   ↓
4. Customize Script Based on Findings
   ↓
5. Test with Small Sample
   ↓
6. Run Full Import
```

**Example:**
```bash
# Step 1: Interrogate
python3 interrogators/deutsche_bank.py --export db_findings.json

# Step 2: Review findings
cat db_findings.json | jq '.summary'

# Step 3: Import script uses findings
# - Max CountItem from findings
# - Safe rate limit from findings
# - URL patterns from findings
```

---

## Adding a New Source

1. **Create interrogator file:**
   ```bash
   cp interrogators/deutsche_bank.py interrogators/my_source.py
   ```

2. **Create README:**
   ```bash
   cp interrogators/README_deutsche_bank.md interrogators/README_my_source.md
   ```

3. **Customize for your source:**
   - Update API_URL
   - Modify payload structure
   - Add source-specific tests

4. **Document findings:**
   - Update README with quirks
   - Add to DATA_MOBILIZATION_COOKBOOK.md
   - Share learnings with team

---

## Output Format

All interrogators generate consistent reports:

```json
{
  "source": "Deutsche Bank",
  "timestamp": "2025-11-07T14:30:00",
  "findings": [
    {
      "category": "API Limits",
      "message": "Max CountItem: 2000",
      "severity": "SUCCESS"
    }
  ],
  "summary": {
    "total_findings": 25,
    "errors": 1,
    "warnings": 3,
    "successes": 21
  },
  "recommendations": [
    "Use CountItem=2000 for full fetch",
    "Rate limit to 5 req/s",
    "Transform ApplyURI (remove /apply)"
  ]
}
```

---

## Testing Strategy

Each interrogator should be **safe to run repeatedly**:
- ✅ Read-only operations
- ✅ Small sample sizes by default
- ✅ Timeout on slow operations
- ✅ Clear error messages
- ✅ No database modifications

**Deep mode** (--deep flag):
- Larger sample sizes
- More comprehensive tests
- Longer running time
- More detailed output

---

## Best Practices

1. **Run Before Every Import** - APIs change, interrogate first
2. **Document Findings** - Update source README with quirks
3. **Export Results** - Keep JSON for historical comparison
4. **Test Incrementally** - Start small, scale up
5. **Share Learnings** - Update cookbooks with patterns

---

## Future Enhancements

- [ ] Automatic diff detection (compare findings over time)
- [ ] LLM-assisted script generation from findings
- [ ] Multi-source comparison reports
- [ ] Integration with workflow scheduler
- [ ] Automated alerting when source structure changes

---

## See Also

- [DATA_MOBILIZATION_COOKBOOK.md](../docs/DATA_MOBILIZATION_COOKBOOK.md) - General patterns
- [DEUTSCHE_BANK_CHALLENGES.md](../docs/posting_sources/DEUTSCHE_BANK_CHALLENGES.md) - Specific challenges
- [Arden's Cheat Sheet](../docs/___ARDEN_CHEAT_SHEET.md) - Quick reference

---

*"They change the system, we adapt. They outdumb us, we outsmart them. It's a game - let's have fun playing it."*
