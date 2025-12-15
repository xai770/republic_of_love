# Job Status Validation - Implementation Guide

**Created:** November 7, 2025  
**Status:** ✅ WORKING

## Problem Solved

Previously, we had no way to know if jobs in our database were still active on the source site. Users could be applying to expired positions!

## Solution

Created `tools/validate_job_status.py` - a validator that checks if jobs are still live and updates `posting_status` accordingly.

---

## How It Works

### For Workday Jobs (db.wd3.myworkdayjobs.com)

**Detection Method:** Check if page has valid `og:title` meta tag with content.

**Expired Job Signals:**
- HTTP 410 Gone
- HTTP 404 Not Found  
- HTTP 30x Redirect (to search page)
- og:title meta tag missing
- og:title content is empty/None
- Page text contains "no job openings"

**Example:**
```python
url = 'https://db.wd3.myworkdayjobs.com/.../R0403334-1'
response = requests.get(url)
# Returns 200, but og:title content is None → EXPIRED!
```

### For API-Based Jobs

**Detection Method:** Query Deutsche Bank API with specific PositionID.

```python
payload = {
    "SearchCriteria": [
        {"CriterionName": "PositionID", "CriterionValue": ["68145"]}
    ]
}
# If SearchResultItems is empty → EXPIRED!
```

---

## Database Schema

Added column to track validation:
```sql
ALTER TABLE postings ADD COLUMN status_checked_at TIMESTAMP;
```

**Status Values:**
- `active` - Job confirmed live on source site
- `expired` - Job no longer available  
- `duplicate` - Duplicate posting (future use)

---

## Usage

### Manual Run (All Jobs)
```bash
cd /home/xai/Documents/ty_learn
python3 tools/validate_job_status.py
```

### Test Specific Jobs
```python
from tools.validate_job_status import check_workday_job_exists

url = 'https://db.wd3.myworkdayjobs.com/.../R0385272-1'
exists, reason = check_workday_job_exists(url)

if exists:
    print("Job still active!")
elif exists is False:
    print(f"Job expired: {reason}")
else:
    print(f"Error checking: {reason}")
```

### Query Expired Jobs
```sql
SELECT external_job_id, job_title, status_checked_at
FROM postings 
WHERE posting_status = 'expired'
ORDER BY status_checked_at DESC;
```

---

## Validation Results (Nov 7, 2025)

**Test Run:**
- ✅ R0403334 - Correctly detected as EXPIRED
- ✅ R0385272 - Correctly detected as EXPIRED  
- ✅ R0361223 - Correctly detected as EXPIRED

All 3 jobs confirmed expired on careers.db.com (screenshot proof provided).

**Database Update:**
```sql
-- Marked 3 jobs as expired
UPDATE postings SET posting_status = 'expired' WHERE external_job_id IN (...)
```

---

## Best Practices

### Run Frequency
**Recommendation:** Daily validation

```bash
# Add to cron
0 2 * * * cd /home/xai/Documents/ty_learn && python3 tools/validate_job_status.py >> logs/validation.log 2>&1
```

### Rate Limiting
Current: 0.5s delay (2 req/sec)  
**Why:** Be nice to Deutsche Bank servers, avoid rate limiting

### Batch Processing
Commits every 25 jobs to avoid losing progress on errors.

### Error Handling
- Network errors: Skip job, try again next run
- Timeouts: Logged but don't mark as expired (could be temporary)

---

## Statistics Tracking

The validator outputs:
```
Total jobs checked: 739
✅ Still active: 736
❌ Expired/Removed: 3
⚠️  Errors: 0

Validation methods:
   🌐 Workday URL checks: 194
   🔍 API checks: 545

📉 Expiration rate: 0.4%
```

---

## Future Enhancements

### 1. Archive Old Expired Jobs
```sql
-- Move to archive table after 90 days
INSERT INTO postings_archive 
SELECT * FROM postings 
WHERE posting_status = 'expired' 
  AND status_checked_at < NOW() - INTERVAL '90 days';
```

### 2. Notification System
Alert when high-value jobs expire (e.g., senior positions).

### 3. Validation Dashboard
Web UI showing:
- Jobs validated today
- Expiration rate trend
- Average job lifespan
- Most stable companies (low expiration rate)

### 4. Smart Validation Frequency
- New jobs: Check daily
- Stable jobs (>30 days old): Check weekly
- Very old jobs (>90 days): Check monthly

### 5. Multi-Source Support
Extend to other job boards:
- LinkedIn
- Indeed
- Company career pages

---

## Troubleshooting

### "Network error: Connection timeout"
**Solution:** Increase timeout in `requests.get(..., timeout=15)`

### "Too many expired jobs detected"
**Check:** 
1. Is the source API down?
2. Did they change their HTML structure?
3. Rate limited? (add more delay)

### "og:title check failing"
**Debug:**
```python
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
print(soup.prettify())  # Inspect actual HTML
```

---

## Integration Points

### With Import Scripts
Import scripts should mark `posting_status = 'active'` and set `last_seen_at = NOW()`.

### With Description Fetcher
`fetch_workday_descriptions.py` should skip `expired` jobs:
```sql
WHERE posting_status = 'active' 
  AND job_description IS NULL
```

### With UI/Frontend
Filter out expired jobs by default:
```sql
SELECT * FROM postings 
WHERE posting_status = 'active'
```

---

## Key Files

- `tools/validate_job_status.py` - Main validator script
- `migrations/060_add_status_checked_at.sql` - Schema update (if needed)
- `interrogators/SESSION_SUCCESS_REPORT.md` - Context on job import system

---

## Summary

✅ **Validator working correctly**  
✅ **Detects expired Workday jobs (og:title check)**  
✅ **Detects expired API jobs (SearchResultItems empty)**  
✅ **Updates posting_status in database**  
✅ **Tracks validation timestamp**  
✅ **Ready for production use**

**Recommendation:** Run daily via cron to keep job data fresh!
