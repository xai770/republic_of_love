# Deutsche Bank Data Analysis - File Index

**Generated:** November 9, 2025 00:45 UTC  
**Purpose:** Quick reference for all analysis files created during this session

---

## Documentation Files

### 📘 **`docs/DEUTSCHE_BANK_DATA_ANALYSIS_COOKBOOK.md`**
**Purpose:** Comprehensive analysis guide (primary reference)  
**Contents:**
- Data overview and quality metrics
- Geographic analysis (inferred from job descriptions)
- Skills analysis (top 30 skills, importance levels, distribution)
- Career level patterns (inferred from titles)
- IHL analysis (fake job detection)
- Market intelligence insights
- SQL query library (10+ reusable queries)

**Size:** ~800 lines  
**Format:** Markdown with SQL code blocks  
**Audience:** Data analysts, hiring managers, product teams

---

## Report Files

### 📊 **`reports/DEUTSCHE_BANK_ANALYSIS_SUMMARY.md`**
**Purpose:** Executive summary for stakeholders  
**Contents:**
- Key findings across geography, skills, seniority
- Strategic recommendations
- Data quality assessment
- Sample use cases
- Next steps roadmap

**Size:** ~500 lines  
**Format:** Markdown with tables  
**Audience:** Executives, hiring leadership

### 📋 **`reports/ANALYSIS_SESSION_NOV9_SUMMARY.md`**
**Purpose:** Technical session notes for Arden/Toby collaboration  
**Contents:**
- Work completed (docs, queries, exports)
- Key insights generated
- Data quality findings
- Recommendations for next session
- Files inventory
- Action items

**Size:** ~300 lines  
**Format:** Markdown  
**Audience:** Technical team (Arden, Toby)

### 📄 **`reports/deutsche_bank_top_skills.csv`**
**Purpose:** Visualization-ready skills data export  
**Contents:**
- 126 skills with ≥10 job mentions
- Columns: skill_name, job_count, pct_of_jobs, importance_levels, avg_weight
- Ready for Tableau/PowerBI/Excel

**Size:** 126 rows + header  
**Format:** CSV  
**Audience:** Data visualization, reporting tools

### 📝 **`reports/QUICK_QUERIES.sql`**
**Purpose:** SQL query reference for common analyses  
**Contents:**
- Data overview queries
- Skills analysis queries
- Geographic analysis queries
- Career level queries
- IHL analysis queries
- Cross-tabulation queries
- Data quality checks
- Export queries

**Size:** ~250 lines  
**Format:** SQL  
**Audience:** Database analysts, developers

---

## Quick Access Guide

### For Stakeholder Presentations:
1. Start with: `reports/DEUTSCHE_BANK_ANALYSIS_SUMMARY.md`
2. Supporting data: `reports/deutsche_bank_top_skills.csv`
3. Deep dive: `docs/DEUTSCHE_BANK_DATA_ANALYSIS_COOKBOOK.md`

### For Technical Analysis:
1. Query library: `reports/QUICK_QUERIES.sql`
2. Full cookbook: `docs/DEUTSCHE_BANK_DATA_ANALYSIS_COOKBOOK.md`
3. Session notes: `reports/ANALYSIS_SESSION_NOV9_SUMMARY.md`

### For Visualization Work:
1. Data export: `reports/deutsche_bank_top_skills.csv`
2. Export more data: Run queries from `reports/QUICK_QUERIES.sql` (bottom section)
3. Insights reference: `reports/DEUTSCHE_BANK_ANALYSIS_SUMMARY.md`

---

## Key Metrics at a Glance

| Metric | Value | % |
|--------|-------|---|
| Total Jobs | 1,801 | 100% |
| Active Jobs | 1,678 | 93.2% |
| With Skills | 1,701 | 94.4% |
| With IHL | 38 | 2.1% |
| Avg Skills/Job | 12.1 | - |
| Avg Description Length | 5,351 chars | - |

### Top 5 Skills:
1. Communication skills (289 jobs, 17.0%)
2. Analytical skills (140 jobs, 8.2%)
3. Attention to detail (100 jobs, 5.9%)
4. Project management (88 jobs, 5.2%)
5. Problem-solving (78 jobs, 4.6%)

### Top 3 Locations (Inferred):
1. Mumbai (183 jobs, 35.1%)
2. New York (107 jobs, 20.5%)
3. London (88 jobs, 16.9%)

### Seniority Distribution:
- VP: 25.4%
- Analyst: 12.9%
- Senior: 12.1%
- Associate: 10.4%

### Hiring Quality:
- Competitive: 84.2% (genuine external)
- Internal Likely: 13.2%
- Fake: 0% (in sample)

---

## Database Details

**Database:** PostgreSQL `turing`  
**Table:** `postings`  
**Filter:** `source_id = 1` (Deutsche Bank)  
**Schema Reference:** `docs/___ARDEN_CHEAT_SHEET.md`

**Key Columns:**
- `posting_id` - Primary key
- `job_title` - Job title text
- `job_description` - Full description (avg 5,351 chars)
- `skill_keywords` - JSONB array of extracted skills
- `ihl_score` - Insider Hiring Likelihood (0-100)
- `ihl_category` - COMPETITIVE, INTERNAL LIKELY, PRE-WIRED
- `posting_status` - active, expired, etc.
- `location_city`, `location_country` - Mostly null (99.8%)
- `employment_career_level` - Mostly null (99.9%)

---

## Next Steps Reference

### Data Completion (Priority: High)
- [ ] Complete IHL batch (1,763 jobs, ~50-70 hours)
- [ ] Investigate 100 skills extraction failures
- [ ] Extract locations from descriptions (NLP workflow)
- [ ] Parse career levels from titles

### Advanced Analysis (Priority: Medium)
- [ ] Skills co-occurrence analysis
- [ ] Geographic trend analysis
- [ ] Seniority vs skills correlation
- [ ] Time-series hiring velocity

### Automation (Priority: Low)
- [ ] Daily IHL monitoring dashboard
- [ ] Weekly skills demand report
- [ ] Monthly geographic heat map
- [ ] Executive KPI scorecard

---

## Questions? Next Actions?

**For Technical Questions:**
- Review: `docs/DEUTSCHE_BANK_DATA_ANALYSIS_COOKBOOK.md`
- Try queries: `reports/QUICK_QUERIES.sql`
- Check schema: `docs/___ARDEN_CHEAT_SHEET.md`

**For Strategic Questions:**
- Review: `reports/DEUTSCHE_BANK_ANALYSIS_SUMMARY.md`
- Action items: `reports/ANALYSIS_SESSION_NOV9_SUMMARY.md`

**For Data Issues:**
- Session notes: `reports/ANALYSIS_SESSION_NOV9_SUMMARY.md` (Data Quality section)
- Validation queries: `reports/QUICK_QUERIES.sql` (Data Quality Checks section)

---

**Created:** November 9, 2025 00:45 UTC  
**Session:** Morning prep for Toby work session  
**Status:** ✅ All files ready for analysis
