# 2026-02-06: Nightly Fetch — Second Stable Run

**Time:** 20:00 CET (cron)  
**Observer:** Gershon + Arden  
**Mood:** 🍩 Donuts and anticipation

---

## 🎯 What We Expect to Happen

Tonight's fetch will be our **second stable run** after yesterday's debugging marathon. The pipeline is now battle-tested with proper TTY detachment, timestamps, and VPN sudoers.

### Current Database State (Pre-Run @ 17:15 CET)

| Metric | Value | Notes |
|--------|-------|-------|
| Total postings | 123,875 | Across both sources |
| Active (not invalidated) | 114,435 | 92.4% |
| With berufenet_id | 95,324 | 77.0% |
| With domain_gate | 123,868 | 100.0% |
| With salary (via join) | 95,304 | 76.9% |
| Total embeddings | 163,448 | Healthy surplus |
| New today | 351 | Quiet day so far |

### By Source

| Source | Count |
|--------|-------|
| Arbeitsagentur | 120,137 |
| Deutsche Bank | 3,738 |

### Recent Activity (Last 7 Days)

| Date | New Postings |
|------|--------------|
| Feb 6 | 351 |
| Feb 5 | 15,537 |
| Feb 4 | 16,608 |
| Feb 3 | 13,239 |
| Feb 2 | 33,041 |
| Feb 1 | 6,111 |
| Jan 31 | 9,960 |

---

## 📊 Expected Outcomes

### Pipeline Steps

```
┌────────────────────────────────────────────────────────────────┐
│                    NIGHTLY FETCH PIPELINE                      │
│                     Feb 6, 2026 @ 20:00 CET                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. AA Fetch ──► 2. DB Fetch ──► 3. Backfill Descriptions     │
│     (16 states)    (skip if ran)   (HTTP, VPN rotation)       │
│     ~5 min         ~instant        ~1-2 hr                     │
│                                                                │
│  4. Berufenet Classification ──► 5. LLM Summaries              │
│     (SQL lookup + auto-matcher)    (DB postings only)         │
│     ~1 min                         ~5 min                      │
│                                                                │
│  6. Embeddings                                                 │
│     (7.8/sec on GPU)                                          │
│     ~varies based on new postings                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Expected New Postings

| Source | Expected Volume | Notes |
|--------|----------------|-------|
| Arbeitsagentur | 500-2,000 | Daily churn across 16 states |
| Deutsche Bank | 10-50 | May skip if already ran today |
| **Total new** | ~600-2,100 | |

### What's Different Since Last Night

| Feature | Status | Notes |
|---------|--------|-------|
| TTY detachment | ✅ Fixed | All scripts use `</dev/null` |
| Timestamps | ✅ Fixed | `tlog()` in all 6 Python scripts |
| VPN sudoers | ✅ Fixed | `/etc/sudoers.d/vpn` in place |
| Backfill logging | ✅ Fixed | Writes to stdout → main log |
| Syntax errors | ✅ Fixed | Triple quotes corrected |

---

## 🔬 What to Watch For

### Success Indicators ✅

1. **AA Fetch completes** without 403 errors
   - Check: `grep "SUCCESS" logs/nightly_fetch.log`

2. **Backfill handles rate limits** gracefully
   - Watch: VPN rotation messages
   - Expected: 1-3 rotations max

3. **Berufenet classification runs**
   - Last run: 78.1% coverage (93,767 matched)
   - Target: Maintain or improve

4. **Embeddings complete**
   - Last run: 7.8/sec on GPU
   - Expected: 500-2,000 new embeddings

### Potential Issues ⚠️

1. **Unmatched professions still at 21.9%**
   - Top culprits: ERP-Berater/in (153), IT-Berater/in (115), Reifenmonteur/in (77)
   - Consider manual synonym additions after run

2. **VPN rotation** during backfill
   - If stuck, check `sudo` permissions

3. **Deutsche Bank skip**
   - If ran earlier today, will skip (expected behavior)

---

## 📋 Pre-Run Checklist

```bash
# Verify cron is set
crontab -l | grep "20 \* \* \*"
# Expected: 0 20 * * * cd /home/xai/Documents/ty_learn && ./scripts/nightly_fetch.sh 1 25000 force >> logs/nightly_fetch.log 2>&1

# Check VPN sudoers
sudo -n openvpn --version 2>/dev/null && echo "✅ VPN sudoers OK"

# Check GPU for embeddings
nvidia-smi --query-gpu=name,memory.free --format=csv

# Clear old log (optional, for clean reading)
# > logs/nightly_fetch.log
```

---

## 🎯 Success Criteria

| Metric | Target | How to Check |
|--------|--------|--------------|
| AA fetch completes | ✅ | `grep "SUCCESS.*Fetched" logs/nightly_fetch.log` |
| Backfill > 50% success | ✅ | Check VPN rotation count |
| New postings have berufenet | > 75% | SQL query after run |
| Embeddings complete | All new | Log shows "Done: N embeddings" |
| No crashes | ✅ | No Python tracebacks |
| Runtime < 4 hr | ✅ | Start 20:00, end by 00:00 |

---

## 📝 Live Monitoring Commands

```bash
# Follow the log
tail -f logs/nightly_fetch.log

# Check if running
pgrep -f nightly_fetch.sh

# Quick status
grep -E "^\[.*\]|\[.*\/.*\]|SUCCESS|ERROR|Done:" logs/nightly_fetch.log | tail -50
```

---

## 📝 Post-Run Notes

### Actual Timing
- Start: 20:00 CET
- End: ~21:00 CET
- Total: ~1 hour (all 6 steps)

### Results
| Step | Status | Notes |
|------|--------|-------|
| 1. AA Fetch | ✅ | 35,424 postings processed |
| 2. DB Fetch | ✅ | Skip (ran earlier) |
| 3. Backfill | ✅ | 21,974 descriptions fetched |
| 4. Berufenet | ✅ | Classification complete |
| 5. Summaries | ✅ | DB summaries generated |
| 6. Embeddings | ✅ | All new postings embedded |

### New Postings Summary
- Total AA jobs processed: 35,424
- New postings inserted: ~14,225
- With description: 21,974 successfully fetched
- **NULL descriptions: 8,015** ← Investigated below

---

## 🔍 Feb 7 Investigation: NULL Descriptions

### Problem Statement
After successful run, found **8,015 postings** with `job_description IS NULL`.

### Breakdown

| Category | Count | Explanation |
|----------|-------|-------------|
| External partner redirects | 7,882 | AA redirects to external sites |
| Pending native jobs | 133 | Jobs posted today, not yet scraped |

### External Partner Analysis

Jobs with these prefixes don't have descriptions on AA - they redirect:

| Prefix | Site | Jobs | Status |
|--------|------|------|--------|
| 12288 | jobvector.de | 5,182 | Scrapeable ✅ |
| 14225 | jobvector.de | 1,847 | Scrapeable ✅ |
| 12336 | gute-jobs.de | 412 | TBD |
| 13645 | get-in-engineering.de | 287 | TBD |
| Others | Various | 154 | Mixed |

### Root Cause Discovery: `externeUrl` Field

**Key finding:** The AA API returns `externeUrl` for external partner jobs!

```bash
# Test API response
curl -s -H "X-API-Key: jobboerse-jobsuche" \
  'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs?was=Ingenieur&wo=Berlin&size=5'
```

Example responses:
```
10001-123456-S: NO externeUrl FIELD       # Native AA job
14225-abc123-S: https://jobvector.de/...  # External partner
12336-xyz789-S: https://gute-jobs.de/...  # External partner
```

**Bug:** Our actor hardcoded `external_url` to the AA detail page, ignoring `externeUrl`.

### Fix Applied

**File:** `actors/postings__arbeitsagentur_CU.py` (line 595)

```python
# BEFORE (broken):
'external_url': f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",

# AFTER (fixed):
externe_url = raw_job.get('externeUrl')
external_url = externe_url if externe_url else f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"
```

### Impact

| Before Fix | After Fix |
|------------|-----------|
| All jobs → AA detail page | External partners → actual job URL |
| ~7,800 jobs need URL mapping | URLs captured automatically |
| Scraper needs complex logic | Scraper just uses `external_url` |

### Scraper Infrastructure Built (Feb 7)

Created full external description scraping system:

```
lib/scrapers/
├── __init__.py      # Registry + get_scraper()
├── base.py          # BaseScraper with Playwright
└── jobvector.py     # JobvectorScraper (tested ✅)

actors/postings__external_description_U.py  # Orchestrator
migrations/052_external_job_sites.sql       # owl config
```

**Test result:** Successfully scraped 9,989 chars from jobvector.de

### Next Steps

1. ✅ Fix applied - next fetch will capture `externeUrl`
2. ⏳ Run external description actor on ~7,800 external partner jobs
3. ⏳ Add stepstone, hays scrapers as needed
4. ⏳ Add to nightly pipeline (Step 3.5: external descriptions)

---

*— Post-run analysis by Arden ℵ, Feb 7 2026*  
*Mystery solved: the URL was there all along, we just weren't looking.*
