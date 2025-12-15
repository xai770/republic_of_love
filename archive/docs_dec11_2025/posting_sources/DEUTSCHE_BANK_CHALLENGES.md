# Deutsche Bank Job Board - Challenges & Solutions

**Source:** https://careers.db.com/professionals/search-roles/  
**Last Updated:** 2025-11-07  
**Status:** ✅ Operational - Worldwide Coverage (1,731 active jobs)

---

## Quick Reference

### Running the Import (One Command)

```bash
# Import ALL worldwide jobs + fetch descriptions automatically
python3 tools/import_deutsche_bank_worldwide.py
```

**What it does:**
- ✅ Fetches 2,191 jobs from API (worldwide)
- ✅ Filters out 460 Finanzberater jobs (no accessible descriptions)
- ✅ Imports 1,731 Workday jobs
- ✅ Automatically fetches descriptions for NEW jobs only
- ✅ Updates `last_seen_at` for existing jobs
- ✅ Detects and marks removed jobs as `withdrawn`

**Runtime:** ~20 seconds (5s API + 10s DB + 0.2s per new job for descriptions)

**Current Database:** 1,801 total jobs (1,678 active, 1,778 with descriptions)

### Key Features

- **Incremental Updates:** Safe to run daily, won't create duplicates
- **Removed Job Detection:** Automatically marks jobs no longer in API
- **Integrated Description Fetching:** New jobs get descriptions immediately
- **Global Coverage:** 25 cities across 13 countries
- **High Success Rate:** 99%+ description fetch success

---

## Overview

Deutsche Bank's career site uses a **hybrid architecture**:
- Job list: API endpoint with JSON response
- Job descriptions: Server-rendered Workday pages (Workday jobs)
- Job descriptions: Authentication-required pages (Finanzberater jobs)
- Application forms: Separate `/apply` URLs

**Job Categories:**
1. **Workday Jobs** (~1,731) - Professional/tech positions with accessible descriptions
2. **Finanzberater Jobs** (~460) - Financial advisory positions requiring authentication

**Import Strategy:** We only import Workday jobs (category 1) as Finanzberater jobs have no accessible descriptions.

---

## Challenge History

### Challenge #0: Finanzberater Jobs (Nov 7, 2025)

**Problem:**
- API returns ~450 "Finanzberater" (financial advisor) jobs
- URLs point to `jobs.db-finanzberatung.de` (different system)
- All URLs return 404 or require authentication
- No job descriptions available in API metadata
- All attempts to fetch descriptions fail

**Investigation:**
```bash
# Example URL from API
https://jobs.db-finanzberatung.de/Vacancies/1470/Application/CheckLogin/1?lang=ger&tracking_id=Globaljobboard

# Returns: "Please login" message (118 chars)
# OR: 404 error page

# Tried PositionURI from metadata
https://jobs.db-finanzberatung.de/index.php?ac=jobad&id=50765
# Returns: 404 error
```

**Why They're Problematic:**
1. **No descriptions:** Can't scrape job requirements or responsibilities
2. **Generic titles:** All variations of "Finanzberater" (financial advisor)
3. **Sales positions:** Not tech/IT roles (outside target scope)
4. **Authentication wall:** Requires login credentials we don't have
5. **Different system:** Not Workday, different URL structure

**Solution: Filter them out**
```python
# In import script
apply_uri = desc.get("ApplyURI", [None])[0]

if apply_uri and 'finanzberatung' in apply_uri.lower():
    # Skip - no accessible description
    stats['skipped_finanzberater'] += 1
    continue
```

**Result:** Import only Workday jobs with accessible descriptions (~120 per country)

**Status:** ✅ Resolved (filtered at import time)

---

### Challenge #1: API Limitation (Nov 2025)

**Problem:**
- POST API originally returned 50+ jobs per request
- API changed, limiting results
- Website showed 588 German jobs, API returned fewer

**Root Cause:**
- API endpoint: `https://api-deutschebank.beesite.de/search/`
- POST method had undocumented limits
- Need to use GET method with JSON in URL parameter

**Investigation:**
- User inspected browser Network tab
- Found GET requests with `CountItem` parameter
- `CountItem` is a limit, NOT pagination
- Setting `CountItem=1000` returns all available jobs

**Solution:**
```python
# Switch from POST to GET
payload = {
    "LanguageCode": "en",
    "SearchParameters": {
        "FirstItem": 1,
        "CountItem": 1000,  # Get all jobs (not paginated)
        "MatchedObjectDescriptor": [
            "PositionID", "PositionTitle", "ApplyURI",
            "PositionLocation", "CareerLevel", ...
        ]
    },
    "SearchCriteria": [
        {"CriterionName": "PositionLocation.Country", "CriterionValue": ["46"]}
    ]
}

url = f"{API_URL}?data={json.dumps(payload)}"
response = requests.get(url, timeout=60)
```

**Status:** ✅ Resolved

---

### Challenge #2: The `/apply` URL Bug (Nov 7, 2025)

**Problem:**
- Imported 450 jobs but ALL descriptions failed to fetch
- No error messages, just empty descriptions
- Same job titles appearing 50+ times in database

**Root Cause:**
```python
# Import script was storing ApplyURI directly
apply_uris = desc.get("ApplyURI", [])
external_url = apply_uris[0]  # ❌ WRONG!

# Example URL stored:
# https://db.wd3.myworkdayjobs.com/.../job-title_ID/apply
#                                                    ^^^^^^
#                                                   This is the problem!
```

**Why This Failed:**
- `/apply` URLs point to **application forms**, not job pages
- Application forms don't have job descriptions
- Description fetcher tried to scrape these pages → found nothing
- No errors because pages loaded successfully (just wrong content)

**The Fix:**
```python
# Get ApplyURI and remove /apply suffix
apply_uri = apply_uris[0] if apply_uris else None

# CRITICAL: Remove /apply to get job description page
if apply_uri and apply_uri.endswith('/apply'):
    external_url = apply_uri.replace('/apply', '')
else:
    external_url = apply_uri

# Now URL is:
# https://db.wd3.myworkdayjobs.com/.../job-title_ID
# ✅ This page has the og:description meta tag!
```

**Impact:**
- Imported 450 duplicate/broken jobs
- Had to DELETE FROM postings WHERE posting_id >= 896
- Lost ~2 hours diagnosing the issue

**Prevention:**
- Always test URL transformation manually FIRST
- Check 3-5 jobs before running full import
- Verify descriptions fetch successfully in test run

**Status:** ✅ Resolved (import script updated)

**Files Modified:**
- `tools/import_588_jobs.py` - Added /apply removal logic
- `docs/DATA_MOBILIZATION_COOKBOOK.md` - Documented pattern
- `docs/posting_sources/DEUTSCHE_BANK_CHALLENGES.md` - This file

---

## Deutsche Bank Data Architecture

### Job List API

**Endpoint:** `https://api-deutschebank.beesite.de/search/`

**Method:** GET (with JSON in URL parameter)

**Key Fields Returned:**
```json
{
  "MatchedObjectId": "68147",
  "MatchedObjectDescriptor": {
    "PositionID": "68147",
    "PositionTitle": "Senior Developer (f/m/x)",
    "PositionLocation": [{
      "CityName": "Frankfurt",
      "CountryName": "Germany"
    }],
    "CareerLevel": [{
      "Name": "Vice President"
    }],
    "ApplyURI": [
      "https://db.wd3.myworkdayjobs.com/DBWebsite/job/.../Senior-Developer_ID/apply"
    ],
    "OrganizationName": "Deutsche Bank",
    "PublicationStartDate": "2025-11-06"
  }
}
```

**Important Notes:**
- `ApplyURI` is an ARRAY (always take first element)
- `ApplyURI` ends with `/apply` (must remove for descriptions)
- `PositionLocation` is an ARRAY of objects
- `CareerLevel` is an ARRAY of objects with `Name` property

### Job Description Pages

**URL Pattern:** 
```
https://db.wd3.myworkdayjobs.com/DBWebsite/job/{location}/{title}_{id}
```

**Type:** Server-Side Rendered (SSR)

**Description Location:**
```html
<meta property="og:description" content="Job Description: ... full text here ...">
```

**Characteristics:**
- Full HTML in view-source (not SPA!)
- Description in `og:description` meta tag
- Typically 5,000-15,000 characters
- No authentication required
- Rate limiting: ~5 requests/second safe

**Alternative URL Pattern (Some Jobs):**
```
https://jobs.db-finanzberatung.de/Vacancies/{id}/Application/CheckLogin/1
```
- Different system for financial advisory roles
- Less consistent structure
- May need different extraction logic

---

## Current Import Process

### One-Command Workflow

**Script:** `tools/import_deutsche_bank_worldwide.py`

**Process (All-in-One):**
1. **Fetch ALL Jobs Worldwide**
   - API request with no country filter (`CountItem=5000`)
   - Parse JSON response
   - Track API job IDs for removed job detection

2. **Import Jobs to Database**
   - Filter out Finanzberater jobs (authentication wall)
   - Transform ApplyURI (remove `/apply`)
   - Check for duplicates by `external_job_id`
   - For existing jobs: UPDATE `last_seen_at = NOW()`
   - For new jobs: INSERT with empty description, track `posting_id`

3. **Fetch Descriptions (Automatic)**
   - Call `fetch_descriptions_for_jobs(new_posting_ids)`
   - Only fetches descriptions for newly imported jobs
   - No wasted API calls on existing jobs
   - Rate limit: 0.2s between requests

4. **Detect Removed Jobs**
   - Compare database active jobs vs API job IDs
   - Mark jobs NOT in API as `withdrawn`
   - Update `status_checked_at`

**Duration:** 
- API fetch: ~5 seconds
- Database import: ~10 seconds for 2,191 jobs
- Description fetching: ~0.2s per new job
- Removed job detection: ~1 second

**Success Rate:** 99%+ for descriptions

### Old Two-Step Process (Deprecated)

<details>
<summary>Click to see legacy workflow</summary>

### Step 1: Fetch Job List

**Script:** `tools/import_588_jobs.py`

**Process:**
1. Build API request with `CountItem=1000`
2. GET request to API endpoint
3. Parse JSON response
4. Extract job metadata
5. **Transform ApplyURI** (remove `/apply`)
6. Check for duplicates (by `external_job_id`)
7. INSERT job metadata (WITHOUT description)

**Duration:** ~30 seconds for 587 jobs

### Step 2: Fetch Descriptions

**Script:** `tools/fetch_workday_descriptions.py`

**Process:**
1. Query database for jobs without descriptions
2. For each job:
   - GET request to `external_url`
   - Parse HTML with BeautifulSoup
   - Extract `og:description` meta tag
   - UPDATE job_description in database
3. Rate limit: 0.2s between requests
4. Commit every 10 successful fetches

**Duration:** ~2-3 minutes for 566 jobs

**Success Rate:** 99.4% (650/654 jobs)

</details>

---

## Known Issues

### 1. Multiple Job Sources

**Problem:** Some jobs use different URL patterns

**Impact:**
- `db.wd3.myworkdayjobs.com` → Workday system (most jobs)
- `jobs.db-finanzberatung.de` → Different system (financial advisory)

**Solution:** Description fetcher handles both via generic meta tag extraction

**Status:** ✅ Working (both patterns supported)

### 2. Missing Descriptions (~0.6%)

**Problem:** 4 out of 654 jobs have no description

**Possible Causes:**
- Job posting removed
- URL changed
- Different page structure
- Temporary network error

**Current Handling:** Skip these jobs, don't block import

**Future:** Could retry failed jobs after main import completes

### 3. Country Code Mapping

**Problem:** German jobs use country code "46" in API

**Documentation:**
- 46 = Germany (Deutschland)
- Need to discover codes for other countries

**Status:** ⚠️ Only Germany implemented so far

---

## Testing Checklist

Before running full import:

```bash
# 1. Test API endpoint
curl -s "https://api-deutschebank.beesite.de/search/?data={...}" | jq '.SearchResult.SearchResultCount'

# 2. Check one ApplyURI
echo "https://db.wd3.myworkdayjobs.com/.../job_ID/apply" | sed 's|/apply$||'

# 3. Test description fetch
curl -s "https://db.wd3.myworkdayjobs.com/.../job_ID" | grep -o 'og:description.*content="[^"]*"' | head -c 200

# 4. Run import with 3 jobs
python3 tools/import_588_jobs.py --limit 3 --test

# 5. Verify in database
psql -c "SELECT posting_id, job_title, external_url, LENGTH(job_description) FROM postings ORDER BY posting_id DESC LIMIT 3;"
```

---

## Maintenance Notes

### When API Changes Again

1. **Diagnose:**
   - Open browser DevTools → Network tab
   - Visit https://careers.db.com/professionals/search-roles/
   - Filter by XHR/Fetch
   - Look for new API calls

2. **Capture:**
   - Right-click request → Copy → Copy as cURL
   - Test in terminal
   - Document changes in this file

3. **Update:**
   - Modify `tools/import_588_jobs.py`
   - Test with 3-5 jobs
   - Run full import
   - Update documentation

### When Description Structure Changes

1. **Check:**
   - Visit one job URL manually
   - View page source
   - Search for "description"

2. **Test:**
```python
from bs4 import BeautifulSoup
import requests

url = "https://db.wd3.myworkdayjobs.com/.../job_ID"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Try different selectors
meta_og = soup.find('meta', property='og:description')
meta_desc = soup.find('meta', name='description')
div_desc = soup.find('div', class_='description')

print(f"og:description: {meta_og.get('content') if meta_og else 'NONE'}")
print(f"description: {meta_desc.get('content') if meta_desc else 'NONE'}")
print(f"div: {div_desc.get_text()[:100] if div_desc else 'NONE'}")
```

3. **Update:**
   - Modify `tools/fetch_workday_descriptions.py`
   - Add new extraction method
   - Test on 5-10 jobs
   - Deploy

---

## Performance Metrics

**Last Successful Run:** 2025-11-07 (Morning - Initial Import)

| Metric | Value |
|--------|-------|
| Total jobs fetched | 587 |
| New jobs imported | 567 |
| Duplicates skipped | 20 |
| Descriptions fetched | 650 |
| Failed descriptions | 4 |
| Success rate | 99.4% |
| Total time | ~3 minutes |
| API requests | 1 (fetch list) + 566 (descriptions) |
| Database growth | +567 jobs |

**Validation Run:** 2025-11-07 (Afternoon - After Migration 064)

| Metric | Value |
|--------|-------|
| Total jobs in database | 243 |
| Jobs validated | 239 (98.4%) |
| Still active | 170 (71.1%) |
| Expired/Removed | 65 (27.2%) |
| Skipped (no URL/ID) | 4 (1.6%) |
| Validation methods | 173 Workday URL + 62 API |
| Time to validate | ~2 minutes |

**Worldwide Import:** 2025-11-07 (Evening - Production Scale)

| Metric | Value |
|--------|-------|
| Jobs fetched from API | 2,191 worldwide |
| Jobs imported (Workday only) | 1,550 new jobs |
| Finanzberater skipped | 460 (no descriptions) |
| Duplicates skipped | 181 |
| Total jobs in database | 1,801 |
| Descriptions fetched | 1,524 (99.0% success) |
| Final coverage | 1,778/1,801 (98.7%) |
| Unique locations | 178 cities worldwide |
| Countries represented | Global (all continents) |
| Time to import | ~5 minutes (API + descriptions) |

**Key Insight:** Filtering Finanzberater jobs improved data quality to 98.7% valid descriptions. Deutsche Bank now our most comprehensive data source with 1,801 jobs worldwide.

---

## Lessons Learned (Nov 7, 2025)

### Critical Success Factors

1. **Always Remove URL Suffixes**
   - Job boards often have `/apply`, `/details`, `/view` suffixes
   - Application pages ≠ Job description pages
   - **Pattern:** Store the job page URL, not the action URL
   - **Test:** Visit 3 URLs manually before importing 500+

2. **Validate Job Status Regularly**
   - Import creates snapshots, validation keeps them current
   - 27% expiration rate means ~1/4 of jobs disappear monthly
   - Separate validation script > embedded in import
   - Use both URL checks and API checks for coverage

3. **Test with 3-5 Jobs First**
   - Caught cursor bug (RealDictCursor) in test phase
   - Verified URL transformation worked
   - Confirmed descriptions fetched successfully
   - **5 minutes of testing saves hours of cleanup**

4. **Duplicate Detection is Essential**
   - Check `external_job_id` BEFORE inserting
   - Migration 064 deleted 13 duplicates (old import vs new)
   - Use `INSERT ... ON CONFLICT` when appropriate
   - Track `last_seen_at` to distinguish active from stale

5. **Separate Import from Description Fetching**
   - Import script: Fast metadata only (~30 seconds for 587 jobs)
   - Description fetcher: Separate, retryable (~2-3 minutes)
   - Can retry descriptions without re-importing
   - Easier to debug when one part fails

6. **Use RealDictCursor for PostgreSQL**
   - Default cursor returns tuples (fragile, error-prone)
   - RealDictCursor returns dicts (clear, maintainable)
   - **Pattern:** `cursor_factory=RealDictCursor` in all scripts

7. **Document URL Transformations**
   - Every job board has quirks (Deutsche Bank: remove `/apply`)
   - Document in source-specific file (this one)
   - Reference in general cookbook (DMC)
   - Future-you will thank present-you

### Multi-User Architecture Insights

8. **Decision Fields Must Be User-Specific**
   - Initial design: `cover_letter_draft` in postings table (WRONG!)
   - Correct design: `user_posting_decisions` table with (user_id, posting_id) UNIQUE
   - One job, multiple users, each gets their own decision
   - Views join on user_id to show personalized reports

9. **Metadata is Your Safety Net**
   - Store full API response in `source_metadata` JSONB
   - Can extract missing fields later (Migration 064: extracted job IDs from URIs)
   - Enables forensic analysis when things go wrong
   - Zero data loss from API changes

10. **Validation Coverage > Accuracy**
    - Better to validate 98% of jobs than 44% perfectly
    - Extract IDs from metadata when primary fields missing
    - Use regex on URIs: `id=(\d+)` pattern works across sources
    - Track which jobs CAN'T be validated, investigate those separately

---

## Incremental Updates & Change Detection

### How Daily Runs Work (Nov 7, 2025)

When running `import_deutsche_bank_worldwide.py` multiple times:

**On First Run:**
- Fetches all jobs from API
- Inserts new jobs with `first_seen_at = NOW()`
- Sets `last_seen_at = NOW()`
- Skips Finanzberater jobs (no descriptions)

**On Subsequent Runs:**
- Fetches current jobs from API
- **For existing jobs:** Updates `last_seen_at = NOW()` (proves job still active)
- **For new jobs:** Inserts with `first_seen_at = NOW()`
- **For removed jobs:** Marks as `posting_status = 'withdrawn'` if not in API anymore

**Example Output (Second Run):**
```
Total jobs processed: 2,191
New jobs added: 0
Existing jobs seen: 1,731
Last_seen_at updated: 1,731
Finanzberater skipped: 460
Jobs withdrawn (removed from source): 0
Errors: 0
```

**Change Detection Logic:**
```sql
-- Jobs that are active in DB but NOT in latest API response
-- are automatically marked as withdrawn
UPDATE postings
SET posting_status = 'withdrawn',
    status_checked_at = NOW()
WHERE source_id = 1
  AND posting_status = 'active'
  AND external_job_id NOT IN (api_job_ids)
```

**Why This Matters:**
- Daily runs keep `last_seen_at` current
- Can identify "zombie" jobs (not seen in 7+ days)
- Automatically detect when jobs are removed from source
- No need for separate validation script for Deutsche Bank

**Query Stale Jobs:**
```sql
SELECT COUNT(*)
FROM postings
WHERE source_id = 1
  AND posting_status = 'active'
  AND last_seen_at < NOW() - INTERVAL '7 days';
```

---

## Future Enhancements

### 1. Automatic Duplicate Cleanup
- Detect duplicates by title + location + date
- Mark older duplicates as 'withdrawn'
- Keep newest version

### 2. Multi-Country Support
- Discover country codes for other regions
- Build mapping: "Germany" → "46"
- Support filtering by multiple countries

### 3. Incremental Updates
- Track `last_seen_at` for each job
- Only fetch jobs newer than last run
- Mark missing jobs as 'withdrawn'

### 4. Change Detection
- Store hash of job description
- Detect when existing job is updated
- Alert on significant changes

### 5. Retry Logic
- Store failed fetches in separate table
- Retry failed jobs after main import
- Exponential backoff for rate limits

---

## Contact

**Issues?** Document them in this file with:
- Date discovered
- Symptom (what failed)
- Diagnosis (why it failed)
- Solution (how to fix)
- Prevention (how to avoid)

**Success?** Share metrics in Performance section!

---

*Last incident: Nov 7, 2025 - /apply URL bug*  
*Next review: When API changes or after 1000 jobs imported*
