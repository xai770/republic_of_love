# Workflow Monitoring Guide

**Last Updated:** 2025-12-02 03:27  
**Author:** Sandy & Team

---

## Overview

This document explains how to monitor workflow 3001 (Complete Job Processing Pipeline) and understand the various dashboards and their differences.

---

## Key Monitoring Tools

### 1. `workflow_flowchart.py` - Interaction-Level Progress

**Purpose:** Shows how many interactions have been completed for each conversation step.

**What it counts:**
- **Interactions** (not postings)
- Counts ALL interactions across ALL postings (active + invalidated)
- Shows raw execution counts: pending, running, completed, failed

**Use when:**
- You want to see workflow execution progress
- Debugging why certain steps aren't executing
- Understanding the interaction queue

**Example:**
```bash
python3 tools/workflow_flowchart.py
```

**Output interpretation:**
```
10 🤖 Format Standardization | qwen2.5:7b | 1611/1632  99% | ✅1611 ❌1
```
- `1611/1632 99%` = 1611 interactions completed out of 1632 active postings
- This shows execution progress, NOT data saved to database

---

### 2. `live_dashboard.py` - Data-Level Progress

**Purpose:** Shows actual data saved to the `postings` table.

**What it counts:**
- **Postings** with actual data (extracted_summary, skill_keywords, ihl_score)
- Only counts where data is NOT NULL in database
- Shows business outcome progress

**Use when:**
- You want to know "how many jobs are ready?"
- Reporting on completion status
- Understanding data quality

**Example:**
```bash
python3 tools/live_dashboard.py --once
```

**Output interpretation:**
```
📝 POSTINGS PROGRESS:
   Total:    2109
   Summary:  1596 (75%)
   Skills:   1552 (73%)
   IHL:      47 (2%)
```
- `Summary: 1596 (75%)` = 1596 postings have `extracted_summary` NOT NULL
- This includes OLD invalidated postings from previous batches!

---

## Key Database Concepts

### Posting States

Postings can be in different states:

1. **Active** (`invalidated = false`)
   - Currently on Deutsche Bank website
   - Should be processed by workflow
   - Count: 1,632 (as of Dec 2, 2025)

2. **Invalidated** (`invalidated = true`)
   - No longer on Deutsche Bank website
   - May still have processed data from before
   - Count: 2,059 (as of Dec 2, 2025)

### Data Fields

Each posting can have these fields populated:

- `extracted_summary` - AI-generated job summary (step 11: Save Summary)
- `skill_keywords` - Extracted skills (step 14: Save Posting Skills)
- `ihl_score` - Compliance theater score (step 19: Save IHL Score)

---

## Common Mystery: Numbers Don't Match!

**Problem:** workflow_flowchart shows 95% complete but live_dashboard shows 2% complete?

**Answer:** They're measuring different things!

### Example (Dec 2, 2025 03:27):

**workflow_flowchart.py:**
```
15 ⚙️  Check if IHL Score Exists | check_description | 1552/1632  95% | ✅1552
```
- 1,552 interactions completed (checking if IHL exists)
- Counting against 1,632 ACTIVE postings

**live_dashboard.py:**
```
📝 POSTINGS PROGRESS:
   IHL: 47 (2%)
```
- Only 47 postings actually have `ihl_score` NOT NULL
- Counting against 2,109 TOTAL postings (active + invalidated)

**Why the difference?**
1. workflow_flowchart counts EXECUTION (did the step run?)
2. live_dashboard counts DATA (is the field populated?)
3. Check if IHL Exists might return "SKIP" (already exists) or "RUN" (needs processing)
4. If it returns SKIP, no new IHL score is saved

---

## How to Get Accurate Counts

### Active Postings Only

```sql
SELECT 
    COUNT(*) as total,
    COUNT(extracted_summary) as has_summary,
    COUNT(skill_keywords) as has_skills,
    COUNT(ihl_score) as has_ihl
FROM postings
WHERE source = 'db' AND invalidated = false;
```

### All Postings (Active + Invalidated)

```sql
SELECT 
    COUNT(*) as total,
    COUNT(extracted_summary) as has_summary,
    COUNT(skill_keywords) as has_skills,
    COUNT(ihl_score) as has_ihl
FROM postings
WHERE source = 'db';
```

### Interaction Progress

```sql
SELECT 
    c.conversation_name,
    COUNT(*) FILTER (WHERE i.status = 'completed') as completed,
    COUNT(*) FILTER (WHERE i.status = 'pending') as pending,
    COUNT(*) FILTER (WHERE i.status = 'running') as running,
    COUNT(*) FILTER (WHERE i.status = 'failed') as failed
FROM interactions i
JOIN conversations c ON i.conversation_id = c.conversation_id
WHERE c.workflow_id = 3001
GROUP BY c.conversation_name
ORDER BY c.conversation_id;
```

---

## Monitoring Best Practices

### 1. **Check Both Dashboards**

Use `workflow_flowchart.py` for execution progress and `live_dashboard.py` for data progress.

### 2. **Filter by Active Postings**

When reporting completion, always specify: "X out of Y ACTIVE postings"

### 3. **Watch for SKIP vs RUN**

Some conversation steps (like "Check if Summary Exists") will return:
- `[SKIP]` - Data already exists, don't process again
- `[RUN]` - Data missing, proceed with processing

### 4. **Understand Invalidation**

When you run the daily fetch:
- Old jobs get `invalidated = true`
- New jobs get inserted with `invalidated = false`
- Old data is preserved but not counted in "active" metrics

---

## Quick Reference Commands

### See current workflow status
```bash
python3 tools/workflow_flowchart.py
```

### See posting completion status
```bash
python3 tools/live_dashboard.py --once
```

### Count active postings only
```bash
./scripts/q.sh "SELECT COUNT(*) FROM postings WHERE source='db' AND invalidated=false;"
```

### Count postings with summaries (active only)
```bash
./scripts/q.sh "SELECT COUNT(*) FROM postings WHERE source='db' AND invalidated=false AND extracted_summary IS NOT NULL;"
```

### Check workflow runs
```bash
./scripts/q.sh "SELECT status, COUNT(*) FROM workflow_runs WHERE workflow_id=3001 GROUP BY status;"
```

---

## Troubleshooting

### "Why are summaries at 75% but workflow shows 0%?"

**Explanation:** The 75% includes OLD invalidated postings. The NEW active postings (1,632) have 0% summaries saved.

**Solution:** Run workflow 3001 to process the new batch.

### "Why did skills go from 92% to 0%?"

**Explanation:** Skills were saved on the OLD batch (2,059 invalidated postings). The NEW batch (1,632 active) hasn't been processed yet.

**Solution:** This is normal after daily fetch. Workflow will rebuild data for new batch.

### "Flowchart shows step completed but data isn't in database?"

**Explanation:** The step might have returned `[SKIP]` (data already exists) or saved to a different posting than expected.

**Investigation:**
1. Check the interaction's output JSON
2. Verify which posting_id was processed
3. Check if that posting is active or invalidated

---

## Daily Workflow Pattern

**Morning (after daily fetch):**
1. Old postings → `invalidated = true` (2,059 as of Dec 2)
2. New postings → fetched with `invalidated = false` (1,632 as of Dec 2)
3. Data fields (summary, skills, IHL) → preserved on old postings, NULL on new ones

**During processing:**
1. Workflow 3001 runs
2. Processes NEW active postings (1,632)
3. Skips steps if data already exists
4. Saves summary → skills → IHL for each posting

**End state:**
- All active postings should have summary, skills, and IHL populated
- Invalidated postings retain their old data (for historical analysis)

---

## Key Takeaways

1. **workflow_flowchart.py** = Execution progress (did the step run?)
2. **live_dashboard.py** = Data progress (is the field populated?)
3. **Active postings** = Current jobs on website (process these)
4. **Invalidated postings** = Historical jobs (keep data, don't reprocess)
5. **Always specify** which count you're reporting (interactions vs postings vs active postings)

---

## Change Log

- **2025-12-02 03:27** - Initial creation (Sandy)
  - Documented mystery of mismatched percentages
  - Explained difference between interaction counts and data counts
  - Added active vs invalidated posting distinction
