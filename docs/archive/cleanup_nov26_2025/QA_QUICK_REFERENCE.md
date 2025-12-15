# QA System Quick Reference
## Daily Quality Checks for Workflow 3001

### 🚀 Quick Start

```bash
# Run automated QA check (recommended)
python3 scripts/qa_automated_check.py

# Run comprehensive QA report with full details
python3 scripts/qa_comprehensive_report.py --output /tmp/qa_report.txt

# View critical findings
psql turing -c "SELECT * FROM qa_critical_findings;"

# Check latest QA run summary
psql turing -c "SELECT * FROM qa_run_summary ORDER BY qa_run_id DESC LIMIT 1;"
```

### 📋 QA Scripts Overview

**`qa_automated_check.py`** - Main automation script
- Runs all QA checks automatically
- Stores findings in database
- **Generates markdown report** (default: `logs/qa_report_YYYYMMDD_HHMMSS.md`)
- Exit code 2 if critical findings (for alerting)
- Perfect for cron jobs

**`qa_comprehensive_report.py`** - Detailed reporting
- Generates human-readable reports
- Includes full posting data for review
- Side-by-side comparison of input/output
- Best for manual investigation

**`qa_review_findings.py`** - Interactive reviewer
- Browse findings one by one
- Mark as reviewed/false_positive/fixed
- Add resolution notes
- Best for triaging findings

### 📊 What Gets Checked

1. **Hallucinations** (27 patterns)
   - Template variables, instruction leakage, meta-commentary
   - Dialogue hallucinations, code artifacts
   - Repetition loops

2. **Length Outliers**
   - 5 shortest summaries (<1500 chars typically)
   - 5 longest summaries (>10000 chars typically)

3. **Processing Time**
   - 5 fastest postings (entry point efficiency)
   - 5 slowest postings (bottleneck detection)

4. **Random Samples**
   - 5 random postings for manual review

5. **LLM Patterns**
   - High interaction counts (potential retry loops)

### 🎯 Interpreting Results

**Good Signs:**
- Hallucination rate = 0%
- Summary length: 1,500-8,000 chars
- Processing time: <10 minutes median
- No critical findings

**Warning Signs:**
- Summaries <1000 or >15000 chars
- Processing time >1 hour
- Multiple hallucination patterns on same posting

**Critical Issues:**
- Any hallucinations with severity='high'
- Processing time >24 hours (stuck postings)
- Summaries >40,000 chars (contamination)

### 📝 Common SQL Queries

```sql
-- Get all findings from latest run
SELECT 
    posting_id,
    check_type,
    severity,
    pattern_matched,
    description
FROM qa_findings
WHERE qa_run_id = (SELECT MAX(qa_run_id) FROM qa_findings)
ORDER BY 
    CASE severity 
        WHEN 'high' THEN 1 
        WHEN 'medium' THEN 2 
        WHEN 'low' THEN 3 
        ELSE 4 
    END,
    posting_id;

-- Find postings with multiple issues
SELECT 
    posting_id,
    COUNT(*) as issue_count,
    STRING_AGG(DISTINCT check_type, ', ') as issue_types
FROM qa_findings
WHERE status = 'open'
GROUP BY posting_id
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

-- Track QA trends over time
SELECT 
    qa_run_id,
    run_started_at::date as run_date,
    total_findings,
    high_severity,
    postings_affected
FROM qa_run_summary
ORDER BY qa_run_id DESC
LIMIT 10;

-- Mark findings as reviewed
UPDATE qa_findings
SET status = 'reviewed', 
    reviewed_by = 'xai', 
    reviewed_at = NOW(),
    resolution_notes = 'Confirmed as expected behavior'
WHERE finding_id IN (1, 2, 3);

-- Close false positives
UPDATE qa_findings
SET status = 'false_positive',
    reviewed_by = 'xai',
    reviewed_at = NOW(),
    resolution_notes = 'Length variation is normal for this job type'
WHERE pattern_matched = 'shortest_summary' AND posting_id = 7;
```

### 🔧 Customizing QA Checks

**Change sample size:**
```bash
python3 scripts/qa_comprehensive_report.py --samples 10
```

**Skip database storage (dry run):**
```bash
python3 scripts/qa_comprehensive_report.py --skip-db
```

**Add new hallucination pattern:**
Edit `scripts/qa_check_hallucinations.py`, add to `PATTERNS` list:
```python
('pattern_name', 'CATEGORY',
 lambda s: 'keyword' in s.lower(),
 'high', 'Description of what this detects'),
```

### 📈 Recommended Schedule

- **Daily:** Run automated QA check
  ```bash
  python3 scripts/qa_automated_check.py
  ```
- **Weekly:** Review trends, update pattern list
  ```bash
  python3 scripts/qa_comprehensive_report.py --output /tmp/weekly_qa.txt
  ```
- **Monthly:** Deep dive on processing time outliers
- **Per workflow run:** QA before marking run as SUCCESS
  ```bash
  python3 scripts/qa_automated_check.py --workflow-run 42
  ```

### 🤖 Automation Examples

**Daily cron job (9 AM):**
```bash
# Add to crontab with: crontab -e
0 9 * * * cd /home/xai/Documents/ty_wave && python3 scripts/qa_automated_check.py --quiet >> logs/qa_cron.log 2>&1
# Creates: logs/qa_report_YYYYMMDD_HHMMSS.md

# With alerting on critical findings (exit code 2 means critical findings)
0 9 * * * cd /home/xai/Documents/ty_wave && python3 scripts/qa_automated_check.py --quiet || echo "Critical QA findings detected!" | mail -s "QA Alert" xai@localhost
```

**Check recent postings (last 24 hours):**
```bash
python3 scripts/qa_automated_check.py --recent-hours 24
# Report saved to: logs/qa_report_20251118_120000.md
```

**Dry run (test without saving):**
```bash
python3 scripts/qa_automated_check.py --dry-run
# Still generates report but doesn't save to database
```

**Custom output location:**
```bash
python3 scripts/qa_automated_check.py --output /tmp/qa_review.md
```

**Skip report generation (database only):**
```bash
python3 scripts/qa_automated_check.py --no-report
```

**Custom sample sizes:**
```bash
python3 scripts/qa_automated_check.py --random-samples 10 --length-outliers 3 --time-outliers 5
```

**Quiet mode for automation:**
```bash
python3 scripts/qa_automated_check.py --quiet
# Exit code 0 = success, no critical findings
# Exit code 2 = critical findings detected (severity=high)
# Exit code 1 = error during execution
```

### 🚨 Alert Thresholds

Set up alerts for:
- Hallucination rate >5% (critical)
- Processing time p99 >1 hour (warning)
- Any finding with severity='high' (review)
- QA run failure (system issue)

### 💾 Data Retention

```sql
-- Archive old QA findings (>90 days, reviewed status)
DELETE FROM qa_findings
WHERE detected_at < NOW() - INTERVAL '90 days'
  AND status IN ('reviewed', 'false_positive', 'wont_fix');
```

### 📝 Naming Conventions

**NEVER use these suffixes:**
- ❌ `_enhanced`, `_new`, `_v2`, `_improved`, `_updated`
- ❌ `_final`, `_final_final`, `_FINAL`
- ❌ `_version2`, `_latest`, `_current`

**DO use descriptive names:**
- ✅ `qa_comprehensive_report.py` (describes what it does)
- ✅ `monitor_workflow.py` (clear purpose)
- ✅ `checkpoint_utils.py` (clear domain)

**Rationale:** Version suffixes create confusion and proliferation. Use git for versioning, not filenames.

### 🎓 Understanding Findings

**Shortest/Longest Summaries:**
- Not always errors - some jobs are naturally brief/detailed
- Check `field_length` metric to see actual char count
- Compare with `job_description` length for context

**Processing Time Outliers:**
- Fast = efficient entry points or simple jobs
- Slow = complex processing or system issues
- Check `metric_value` for actual seconds
- >86400s (24h) usually means system pause

**Random Samples:**
- For calibrating quality expectations
- Store examples of "good" vs "needs work"
- Use to train QA reviewers

---

**Created:** 2025-11-18  
**Maintained by:** Sandy  
**Last updated:** 2025-11-18
