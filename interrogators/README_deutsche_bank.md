# Deutsche Bank Interrogator

**File:** `deutsche_bank.py`  
**Source:** https://careers.db.com  
**API:** https://api-deutschebank.beesite.de/search/

---

## Purpose

Interrogates Deutsche Bank's job board API to understand:
- Maximum fetch limits (can we get all 2202 jobs at once?)
- Geographic distribution of jobs
- Data structure and field completeness
- URL patterns and quirks (the dreaded /apply suffix!)
- Description sources (API vs separate pages)

**Run this BEFORE importing Deutsche Bank jobs!**

---

## Quick Start

```bash
# Basic interrogation
python3 interrogators/deutsche_bank.py

# Export findings for later analysis
python3 interrogators/deutsche_bank.py --export db_findings.json

# Deep analysis (more comprehensive, slower)
python3 interrogators/deutsche_bank.py --deep
```

---

## What It Tests

### 1. API Limits (CRITICAL) ⚡
**Tests:** Can we fetch all jobs in one request?

**How:** Tries increasing CountItem values: 10, 100, 500, 1000, 2000, 5000

**Expected Output:**
```
✅ [API Limits] CountItem=2000 → returned 2000 jobs (total available: 2202)
⚠️  [API Limits] API limit: max 2000 jobs per request (but 2202 total exist)
```

**Recommendation:** Use CountItem=2000, will need pagination or multiple requests for remaining jobs

---

### 2. Geographic Distribution 🌍
**Tests:** Where are the jobs located?

**Analyzes:** Countries and cities with job counts and percentages

**Expected Output:**
```
✅ [Geography] Found jobs in 45 countries, 234 cities

📍 Top 10 countries:
  • Germany: 845 jobs (38.4%)
  • United States: 312 jobs (14.2%)
  • United Kingdom: 289 jobs (13.1%)
  ...
```

**Use Case:** Filter imports by geography, understand Deutsche Bank's global footprint

---

### 3. Data Structure 📋
**Tests:** What fields are available and how complete are they?

**Analyzes:** 
- Sample job JSON structure
- Field presence across 50 sample jobs
- Data completeness percentages

**Expected Output:**
```
📊 Field completeness (out of 50 jobs):
  • PositionID: 50/50 (100%) ✅
  • PositionTitle: 50/50 (100%) ✅
  • ApplyURI: 50/50 (100%) ✅
  • CareerLevel: 45/50 (90%) ⚠️
  • PositionFormattedDescription: 0/50 (0%) ❌
```

**Key Finding:** Descriptions NOT in API - must fetch separately!

---

### 4. URL Patterns 🔗
**Tests:** What URL formats are used?

**Identifies:**
- Workday URLs: `db.wd3.myworkdayjobs.com`
- DB Finanzberatung: `jobs.db-finanzberatung.de`
- URLs ending with `/apply` (critical issue!)

**Expected Output:**
```
🔗 URL patterns found:
  • Workday: 1850/2000 (92.5%)
  • DB Finanzberatung: 150/2000 (7.5%)

⚠️  1850/2000 (92.5%) URLs end with /apply
   → Import script MUST remove /apply suffix to get job page!
```

**Critical:** The `/apply` suffix bug! See below.

---

### 5. Description Sources 📄
**Tests:** Where do job descriptions come from?

**Checks:**
1. Are descriptions in API response? (NO)
2. Can we scrape from job pages? (YES)
3. What HTML tags contain descriptions?

**Expected Output:**
```
ℹ️  [Descriptions] No descriptions in API response
✅ [Descriptions] Found og:description (3,847 chars)
```

**Finding:** Must fetch descriptions from individual job pages using BeautifulSoup

---

## Known Issues & Solutions

### Issue #1: The `/apply` URL Bug 🐛

**Problem:**
```python
# API returns:
"ApplyURI": ["https://db.wd3.myworkdayjobs.com/DBWebsite/job/Frankfurt-am-Main/Developer_R12345/apply"]
#                                                                                                ^^^^^^
#                                                                                        This is WRONG!
```

The `/apply` suffix points to the **application form**, not the job description page!

**Why This Matters:**
- Application pages have NO job descriptions
- Description fetcher will fail silently
- You'll import jobs with empty descriptions

**Solution:**
```python
# In import script:
apply_uri = desc.get("ApplyURI")[0]

# REMOVE /apply suffix
if apply_uri.endswith('/apply'):
    external_url = apply_uri.replace('/apply', '')
else:
    external_url = apply_uri

# Now external_url points to the correct page!
```

**Detection:** Interrogator warns you about this automatically

---

### Issue #2: API Pagination Limits

**Problem:** Deutsche Bank has 2202 jobs but API returns max 2000 per request

**Solution Options:**

**Option A: Use Search Criteria to Split**
```python
# Fetch Germany separately
german_jobs = fetch_with_criteria({"Country": "46"})

# Fetch rest
other_jobs = fetch_without_germany()
```

**Option B: Use FirstItem Pagination**
```python
# Fetch 1-2000
batch1 = fetch(FirstItem=1, CountItem=2000)

# Fetch 2001-2202
batch2 = fetch(FirstItem=2001, CountItem=202)
```

**Recommendation:** Interrogator will tell you which approach based on findings

---

### Issue #3: Multiple Job Sources

**Problem:** Jobs come from different systems:
- Workday (92.5%) - consistent structure
- DB Finanzberatung (7.5%) - different HTML structure

**Solution:** Generic description fetcher that tries multiple selectors:
```python
# Try og:description first (works for Workday)
meta_og = soup.find('meta', property='og:description')

# Fallback to description meta
if not meta_og:
    meta_desc = soup.find('meta', name='description')

# Fallback to content div
if not meta_desc:
    content_div = soup.find('div', class_='job-description')
```

---

## Enhancement Ideas (TODO)

### Rate Limit Detection 🚦
**Purpose:** Find safe request rate before getting blocked

```python
def detect_rate_limits(self):
    """Hammer API to find rate limit threshold"""
    for i in range(50):
        start = time.time()
        response = requests.get(self.API_URL)
        
        if response.status_code == 429:
            # Hit rate limit!
            elapsed = time.time() - start_time
            safe_rate = (i-5) / elapsed  # 5 request buffer
            return safe_rate
```

**Output:**
```
⚠️  [Rate Limits] Hit 429 after 45 requests in 10s
✅ [Rate Limits] Safe rate: ~4 req/s
```

**Use In Import:** `time.sleep(1/4)  # 4 req/s`

---

### Performance Benchmarking ⏱️
**Purpose:** Estimate total import time

```python
def benchmark_performance(self):
    """Measure API response times"""
    times = []
    for i in range(5):
        start = time.time()
        response = requests.get(self.API_URL)
        times.append(time.time() - start)
    
    avg_time = sum(times) / len(times)
    
    # Estimate full import time
    total_jobs = 2202
    estimated_minutes = (avg_time * total_jobs) / 60
```

**Output:**
```
📊 [Performance] Average response: 1.2s
📊 [Performance] Estimated time for 2202 jobs: 44 minutes
💡 [Performance] Recommendation: Use parallel fetching (4 workers → 11 mins)
```

---

### Data Quality Scoring 📊
**Purpose:** Measure data completeness

```python
def score_data_quality(self):
    """Score each field for completeness"""
    required_fields = ['PositionID', 'PositionTitle', 'ApplyURI']
    optional_fields = ['CareerLevel', 'Location', 'Description']
    
    scores = {}
    for field in required_fields + optional_fields:
        presence = count_field_presence(field)
        scores[field] = presence
    
    quality_score = calculate_overall_score(scores)
```

**Output:**
```
📊 [Quality] Overall score: 87/100
   Required fields: 100% ✅
   Optional fields: 74% ⚠️
   
💡 [Quality] 450 jobs missing CareerLevel
💡 [Quality] 2202 jobs missing Description (fetch separately)
```

---

### Authentication Detection 🔐
**Purpose:** Check if API needs auth

```python
def detect_authentication(self):
    """Test auth requirements"""
    # Try without headers
    response = requests.get(self.API_URL)
    
    if response.status_code == 401:
        # Check for auth hints
        auth_method = response.headers.get('WWW-Authenticate')
```

**Output:**
```
✅ [Auth] No authentication required
ℹ️  [Auth] Public API, no rate limiting detected
```

---

## Integration with Import Scripts

### Reading Findings Programmatically

```python
import json

# Load findings
with open('db_findings.json') as f:
    findings = json.load(f)

# Extract max count
for rec in findings['recommendations']:
    if 'CountItem=' in rec:
        max_count = int(rec.split('=')[1].split()[0])
        
# Use in import
fetch_jobs(count=max_count)
```

### Automated Script Generation

```python
# Future enhancement: generate import script template
template = f"""
#!/usr/bin/env python3
# Auto-generated from interrogation findings

API_URL = "{self.API_URL}"
MAX_COUNT = {self.max_count}
TOTAL_JOBS = {self.total_jobs}
REMOVE_APPLY_SUFFIX = True  # Based on URL pattern analysis

def fetch_all_jobs():
    # Use findings to configure fetcher
    ...
"""
```

---

## Output Examples

### Success Case (All Good)
```
======================================================================
🔍 DEUTSCHE BANK JOB BOARD INTERROGATION
======================================================================

1️⃣  Testing API Limits...
✅ [API Limits] CountItem=5000 → returned 2202 jobs (total: 2202)
✅ [API Limits] Can fetch ALL 2202 jobs in single request!

2️⃣  Analyzing Geographic Distribution...
✅ [Geography] Found jobs in 45 countries, 234 cities

📍 Top 10 countries:
  • Germany: 845 jobs (38.4%)
  ...

======================================================================
📋 RECOMMENDED ACTIONS
======================================================================
  ✅ Use CountItem=5000 to fetch all 2202 jobs in single request
  🔧 Transform ApplyURI: remove /apply suffix before storing
  📄 Descriptions NOT in API - build separate fetcher
  🧪 Test import with 10 jobs first
```

### Problem Case (Needs Attention)
```
⚠️  [API Limits] API limit: max 2000 jobs per request (but 2202 total)
❌ [Descriptions] Job page returned 403 Forbidden
⚠️  [URL Patterns] 1850/2000 URLs end with /apply

======================================================================
📋 RECOMMENDED ACTIONS
======================================================================
  ⚠️  Use CountItem=2000 and implement pagination
  🔧 CRITICAL: Transform ApplyURI (remove /apply suffix)
  ❌ Description fetching blocked - investigate auth
```

---

## Testing & Validation

```bash
# Test the interrogator itself
python3 -m pytest tests/test_deutsche_bank_interrogator.py

# Validate findings format
python3 -c "
import json
with open('db_findings.json') as f:
    findings = json.load(f)
    assert 'summary' in findings
    assert 'recommendations' in findings
    print('✅ Findings format valid')
"
```

---

## Maintenance

### When API Changes

1. **Run interrogator again**
   ```bash
   python3 interrogators/deutsche_bank.py --export findings_$(date +%Y%m%d).json
   ```

2. **Compare with previous findings**
   ```bash
   diff findings_20251107.json findings_20251108.json
   ```

3. **Update import scripts** based on new findings

4. **Document changes** in DEUTSCHE_BANK_CHALLENGES.md

---

## See Also

- [base.py](README_base.md) - Base interrogator class
- [DEUTSCHE_BANK_CHALLENGES.md](../docs/posting_sources/DEUTSCHE_BANK_CHALLENGES.md) - Known issues
- [DATA_MOBILIZATION_COOKBOOK.md](../docs/DATA_MOBILIZATION_COOKBOOK.md) - General patterns

---

*"We never fail, we just keep iterating"* ✨
